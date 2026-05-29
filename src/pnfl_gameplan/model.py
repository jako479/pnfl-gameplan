"""In-memory wrapper that pairs an fbpro98-gameplan `GamePlan` with PNFL rules.

`PnflGamePlan` is composed of a `GamePlan`, a `PnflRules` instance, and the
`PlayPool` used to resolve each play's pool category and attributes. It does
not inherit from `GamePlan`. See ARCHITECTURE.md for the reasoning.
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import ClassVar, Self

from fbpro98_gameplan import (
    CustomPlay,
    GamePlan,
    Play,
    StockPlay,
    parse_gameplan,
    read_gameplan,
    write_gameplan,
)
from pnfl_playpool import PlayPool

from pnfl_gameplan.rules import PnflRules

logger = logging.getLogger(__name__)


class PnflRuleWarning(UserWarning):
    """Emitted by `PnflGamePlan.save()` for each PNFL rule violation."""


class RuleName(StrEnum):
    """Identifier for each kind of PNFL-rule violation. Values are stable strings."""

    DUPLICATE_PLAY = "duplicate_play"
    UNRESOLVED_PLAY = "unresolved_play"
    DEFENSE_MIN_PLAYS = "defense_min_plays"
    CATEGORY_REQUIRED = "category_required"
    CATEGORY_MIN_COUNT = "category_min_count"
    CATEGORY_MAX_QB_DRAWS = "category_max_qb_draws"
    CATEGORY_MAX_ROLLOUTS = "category_max_rollouts"
    CATEGORY_MAX_TIMED_PERCENT = "category_max_timed_percent"
    CATEGORY_MIN_TWO_DL = "category_min_two_dl"
    CATEGORY_MAX_TWO_DL_PERCENT = "category_max_two_dl_percent"
    SPECIAL_CATEGORY_REQUIRED = "special_category_required"


@dataclass(frozen=True, slots=True)
class Violation:
    """One PNFL-rule violation reported by `PnflGamePlan.validate()`.

    `pool_category` is set when the violation is tied to a specific pool
    category (e.g. "PSL"); gameplan-wide violations leave it as None.
    """

    rule_name: RuleName
    message: str
    pool_category: str | None = None


@dataclass(frozen=True, slots=True)
class PnflGamePlan:
    """A gameplan bound to a PNFL rule set and the play pool used to resolve plays.

    Composes a `GamePlan` rather than inheriting from it. Property and method
    forwarders below give the wrapper a `GamePlan`-shaped API so consumers can
    treat a `PnflGamePlan` as the gameplan directly; the `with_*` forwarders
    return a new `PnflGamePlan` (not a bare `GamePlan`) so the rules + pool
    binding survives every edit.
    """

    NUMBER_NORMAL_PLAYS: ClassVar[int] = GamePlan.NUMBER_NORMAL_PLAYS
    NUMBER_SPECIAL_SLOTS: ClassVar[int] = GamePlan.NUMBER_SPECIAL_SLOTS
    NUMBER_SPECIAL_CATEGORIES: ClassVar[int] = GamePlan.NUMBER_SPECIAL_CATEGORIES
    NUMBER_CLOCK_SLOTS: ClassVar[int] = GamePlan.NUMBER_CLOCK_SLOTS

    gameplan: GamePlan
    rules: PnflRules
    play_pool: PlayPool

    @classmethod
    def from_file(cls, path: str, rules: PnflRules, play_pool: PlayPool) -> Self:
        return cls(gameplan=read_gameplan(path), rules=rules, play_pool=play_pool)

    @classmethod
    def from_bytes(cls, data: bytes, rules: PnflRules, play_pool: PlayPool) -> Self:
        return cls(gameplan=parse_gameplan(data), rules=rules, play_pool=play_pool)

    # ---- GamePlan forwarders ----

    @property
    def normal_plays(self) -> tuple[Play | None, ...]:
        return self.gameplan.normal_plays

    @property
    def special_plays(self) -> tuple[Play | None, ...]:
        return self.gameplan.special_plays

    @property
    def clock_plays(self) -> tuple[Play | None, Play | None]:
        return self.gameplan.clock_plays

    @property
    def custom_special_plays(self) -> tuple[CustomPlay | None, ...]:
        return self.gameplan.custom_special_plays

    @property
    def stock_special_plays(self) -> tuple[StockPlay | None, ...]:
        return self.gameplan.stock_special_plays

    @property
    def is_offense(self) -> bool:
        return self.gameplan.is_offense

    @property
    def is_defense(self) -> bool:
        return self.gameplan.is_defense

    def with_normal_plays(self, plays: Sequence[Play | None]) -> PnflGamePlan:
        """Like `GamePlan.with_normal_plays`, but returns a new `PnflGamePlan`."""
        return replace(self, gameplan=self.gameplan.with_normal_plays(plays))

    def with_custom_special_plays(self, plays: Iterable[CustomPlay | None]) -> PnflGamePlan:
        """Like `GamePlan.with_custom_special_plays`, but returns a new `PnflGamePlan`."""
        return replace(self, gameplan=self.gameplan.with_custom_special_plays(plays))

    # ---- PNFL rule layer ----

    def validate(self) -> tuple[Violation, ...]:
        """Return every PNFL-rule violation found in the wrapped gameplan."""
        from pnfl_gameplan.validators import validate_gameplan

        return validate_gameplan(self.gameplan, self.rules, self.play_pool)

    def save(self, path: str) -> tuple[Violation, ...]:
        """Persist the gameplan; emit per-violation warnings; return the violation tuple.

        The file is written regardless of whether the gameplan satisfies the bound
        PNFL rule set. PNFL violations are emitted as `warnings.warn(..., PnflRuleWarning)`
        (one per violation, prefixed with `pool_category` when present) and returned
        to the caller. Callers that want to gate writes on violations should call
        `validate()` first and skip `save()` if the report is non-empty.

        The library does not install a `warnings` filter; applications that want
        every violation surfaced on every save should call
        `warnings.simplefilter("always", PnflRuleWarning)` at entry.
        """
        violations = self.validate()
        for v in violations:
            prefix = f"[{v.pool_category}] " if v.pool_category else ""
            warnings.warn(f"{prefix}{v.message}", PnflRuleWarning, stacklevel=2)
        write_gameplan(self.gameplan, path)
        if violations:
            logger.info("Persisted with %d PNFL rule violation(s)", len(violations))
        return violations
