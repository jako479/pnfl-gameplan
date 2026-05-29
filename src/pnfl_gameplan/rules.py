"""PNFL gameplan rule definitions.

Rule data is decoupled from the validators that consume it. The current PNFL
rule set is published in `PNFL_RULES`; alternate rule sets (other seasons,
custom variants for testing) can be constructed by composing the same types.

Sources:
- Offense: https://pnfl.biz/messageboard/viewtopic.php?f=16&t=14
- Defense: https://pnfl.biz/messageboard/viewtopic.php?f=16&t=15

Pool-category keys (the strings used to bucket plays) come from
`pnfl_playpool.OffensivePlayRecord.pool_category` and
`pnfl_playpool.DefensivePlayRecord.pool_category`, which derive from the play
pool's directory layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Final


@dataclass(frozen=True, slots=True)
class OffenseCategoryRule:
    """Constraints applied to one offensive pool category.

    `required=True` means the category must appear with at least `min_count`
    plays. `required=False` means the category is optional; if any play uses
    it, the remaining constraints (min_count and the attribute caps) apply.

    Attribute caps are checked only when their field is non-None:
    `max_qb_draws` for run categories, `max_rollouts` and `max_timed_percent`
    for pass categories. `max_timed_percent` is stored as a Fraction so the
    "no more than 50%" check is exact integer math.
    """

    required: bool
    min_count: int
    max_qb_draws: int | None = None
    max_rollouts: int | None = None
    max_timed_percent: Fraction | None = None


@dataclass(frozen=True, slots=True)
class DefenseCategoryRule:
    """Constraints applied to one defensive pool category.

    `required=True` means the category must appear with at least `min_count`
    plays. `required=False` means the category is optional; if any play uses
    it, the remaining constraints apply.

    2-DL constraints model the PNFL rule that Run-and-Shoot personnel
    (`DefensivePersonnel.RUN_AND_SHOOT`) count as "2-DL" plays.
    `min_two_dl` is a floor on absolute count; `max_two_dl_percent` is a cap
    on the fraction of plays in the category that are 2-DL.
    """

    required: bool
    min_count: int
    min_two_dl: int | None = None
    max_two_dl_percent: Fraction | None = None


_HALF: Final = Fraction(1, 2)
_THIRD: Final = Fraction(1, 3)


def _build_offense_rules() -> dict[str, OffenseCategoryRule]:
    """Per `https://pnfl.biz/messageboard/viewtopic.php?f=16&t=14`."""
    return {
        # Run categories. "No more than 2 of the N runs can be QB draws."
        "RM": OffenseCategoryRule(required=True, min_count=10, max_qb_draws=2),
        "RL": OffenseCategoryRule(required=False, min_count=4, max_qb_draws=2),
        "RR": OffenseCategoryRule(required=False, min_count=4, max_qb_draws=2),
        "GLR": OffenseCategoryRule(required=False, min_count=3),
        # Pass categories. "No more than 2 in any category can be roll outs."
        # "No more than 50% in any category can be Timing Passes."
        "PSL": OffenseCategoryRule(required=True, min_count=5, max_rollouts=2, max_timed_percent=_HALF),
        "PSM": OffenseCategoryRule(required=True, min_count=5, max_rollouts=2, max_timed_percent=_HALF),
        "PSR": OffenseCategoryRule(required=True, min_count=5, max_rollouts=2, max_timed_percent=_HALF),
        "PML": OffenseCategoryRule(required=True, min_count=5, max_rollouts=2, max_timed_percent=_HALF),
        "PMM": OffenseCategoryRule(required=True, min_count=5, max_rollouts=2, max_timed_percent=_HALF),
        "PMR": OffenseCategoryRule(required=True, min_count=5, max_rollouts=2, max_timed_percent=_HALF),
        "PLR": OffenseCategoryRule(required=True, min_count=4, max_rollouts=2, max_timed_percent=_HALF),
        "PRD": OffenseCategoryRule(required=True, min_count=4, max_rollouts=2, max_timed_percent=_HALF),
        "GLP": OffenseCategoryRule(required=False, min_count=3, max_rollouts=2, max_timed_percent=_HALF),
    }


def _build_defense_rules() -> dict[str, DefenseCategoryRule]:
    """Per `https://pnfl.biz/messageboard/viewtopic.php?f=16&t=15`."""
    return {
        # Required runs. 6 each.
        "RunLeft": DefenseCategoryRule(required=True, min_count=6),
        "RunMiddle": DefenseCategoryRule(required=True, min_count=6),
        "RunRight": DefenseCategoryRule(required=True, min_count=6),
        # Required passes. 6 each. 2-DL caps per PNFL.
        "PassShort": DefenseCategoryRule(required=True, min_count=6, max_two_dl_percent=_THIRD),
        "PassMedium": DefenseCategoryRule(required=True, min_count=6, max_two_dl_percent=_THIRD),
        "PassLong": DefenseCategoryRule(required=True, min_count=6, max_two_dl_percent=_HALF),
        # Optional Goal Line. 3 each.
        "GLrun": DefenseCategoryRule(required=False, min_count=3),
        "GLpass": DefenseCategoryRule(required=False, min_count=3),
        # Optional Razzle Dazzle. 4 each. Pass Dazzle: at least two 2-DLs, max 50%.
        "RunDazzle": DefenseCategoryRule(required=False, min_count=4),
        "PassDazzle": DefenseCategoryRule(required=False, min_count=4, min_two_dl=2, max_two_dl_percent=_HALF),
    }


# special_category byte values (1..10) required by PNFL. Per
# fbpro98-gameplan/specs/pln.md section 2.2:
#   1 = FG/PAT, 2 = Kickoff / Kick Return, 3 = Punt / Punt Return,
#   4 = Onside Kick / Onside Return, 9 = Free Kick / Free Kick Return,
#   10 = Squib Kick / Squib Return.
# Categories 5-8 (Fake FG / Fake Punt) are not required by PNFL.
_REQUIRED_SPECIAL_CATEGORIES: Final[frozenset[int]] = frozenset({1, 2, 3, 4, 9, 10})


@dataclass(frozen=True, slots=True)
class PnflRules:
    """PNFL gameplan validation rule set.

    Pass instances to `PnflGamePlan` to bind a gameplan to a particular rule
    set (e.g., a future season's rules, or a custom variant for tests).
    """

    offense_categories: dict[str, OffenseCategoryRule]
    defense_categories: dict[str, DefenseCategoryRule]
    required_special_categories: frozenset[int]
    defense_min_normal_plays: int  # All 64 slots used on defense.


PNFL_RULES: Final[PnflRules] = PnflRules(
    offense_categories=_build_offense_rules(),
    defense_categories=_build_defense_rules(),
    required_special_categories=_REQUIRED_SPECIAL_CATEGORIES,
    defense_min_normal_plays=64,
)
