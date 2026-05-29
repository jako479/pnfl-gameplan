"""In-memory wrapper that pairs an fbpro98-gameplan `GamePlan` with PNFL rules.

`PnflGamePlan` is composed of a `GamePlan`, a `PnflRules` instance, and the
`PlayPool` used to resolve each play's pool category and attributes. It does
not inherit from `GamePlan`. See ARCHITECTURE.md for the reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from fbpro98_gameplan import (
    GamePlan,
    parse_gameplan,
    read_gameplan,
    write_gameplan,
)
from pnfl_playpool import PlayPool

from pnfl_gameplan.rules import PnflRules


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


class PnflRuleError(Exception):
    """Raised by `PnflGamePlan.save()` when validation finds any violations."""

    def __init__(self, violations: tuple[Violation, ...]) -> None:
        self.violations = violations
        super().__init__(f"{len(violations)} PNFL rule violation(s)")


@dataclass(frozen=True, slots=True)
class PnflGamePlan:
    """A gameplan bound to a PNFL rule set and the play pool used to resolve plays."""

    gameplan: GamePlan
    rules: PnflRules
    play_pool: PlayPool

    @classmethod
    def from_file(cls, path: str, rules: PnflRules, play_pool: PlayPool) -> Self:
        return cls(gameplan=read_gameplan(path), rules=rules, play_pool=play_pool)

    @classmethod
    def from_bytes(cls, data: bytes, rules: PnflRules, play_pool: PlayPool) -> Self:
        return cls(gameplan=parse_gameplan(data), rules=rules, play_pool=play_pool)

    def validate(self) -> tuple[Violation, ...]:
        """Return every PNFL-rule violation found in the wrapped gameplan."""
        from pnfl_gameplan.validators import validate_gameplan

        return validate_gameplan(self.gameplan, self.rules, self.play_pool)

    def save(self, path: str) -> None:
        """Validate then write. Raises `PnflRuleError` if any violations exist."""
        violations = self.validate()
        if violations:
            raise PnflRuleError(violations)
        write_gameplan(self.gameplan, path)
