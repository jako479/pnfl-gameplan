"""Validators that surface PNFL-rule violations in a `GamePlan`.

`validate_gameplan` is the public entry point used by `PnflGamePlan.validate()`.
Each side-specific helper consumes plays already resolved against the play pool.
"""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction

from fbpro98_gameplan import GamePlan
from pnfl_playpool import (
    DefensivePersonnel,
    DefensivePlayRecord,
    OffensivePlayRecord,
    PassType,
    PlayPool,
    PlayRecord,
)

from pnfl_gameplan.model import RuleName, Violation
from pnfl_gameplan.rules import (
    DefenseCategoryRule,
    OffenseCategoryRule,
    PnflRules,
)


def validate_gameplan(
    gameplan: GamePlan,
    rules: PnflRules,
    play_pool: PlayPool,
) -> tuple[Violation, ...]:
    """Run every PNFL validator against `gameplan` and return the combined report."""
    violations: list[Violation] = []

    resolved, name_violations = _resolve_normal_plays(gameplan, play_pool)
    violations.extend(name_violations)

    if gameplan.is_offense:
        offense_records = [r for r in resolved if isinstance(r, OffensivePlayRecord)]
        violations.extend(_validate_offense(offense_records, rules.offense_categories))
    else:
        defense_records = [r for r in resolved if isinstance(r, DefensivePlayRecord)]
        violations.extend(_validate_defense(defense_records, rules.defense_categories, rules.defense_min_normal_plays))

    violations.extend(_validate_special_categories(gameplan, rules.required_special_categories))

    return tuple(violations)


# ---------------------------------------------------------------------------
# Normal-slot resolution
# ---------------------------------------------------------------------------


def _resolve_normal_plays(
    gameplan: GamePlan,
    play_pool: PlayPool,
) -> tuple[list[PlayRecord], list[Violation]]:
    """Walk the 64 normal slots and resolve each play against the pool.

    Returns the list of resolved `PlayRecord` instances plus any duplicate or
    unresolved-play violations encountered. Plays that don't resolve are
    reported and dropped from category counts.
    """
    resolved: list[PlayRecord] = []
    violations: list[Violation] = []
    seen_names: dict[str, int] = {}

    for slot_index, play in enumerate(gameplan.normal_plays):
        if play is None:
            continue
        upper = play.name.upper()
        if upper in seen_names:
            violations.append(
                Violation(
                    rule_name=RuleName.DUPLICATE_PLAY,
                    message=(
                        f"Duplicate play '{play.name}' at {_normal_slot_label(slot_index)} "
                        f"(already at {_normal_slot_label(seen_names[upper])})"
                    ),
                )
            )
        else:
            seen_names[upper] = slot_index

        record = play_pool.find_by_name(play.name)
        if record is None:
            violations.append(
                Violation(
                    rule_name=RuleName.UNRESOLVED_PLAY,
                    message=f"Play '{play.name}' at {_normal_slot_label(slot_index)} not found in play pool",
                )
            )
            continue
        resolved.append(record)

    return resolved, violations


# ---------------------------------------------------------------------------
# Offense
# ---------------------------------------------------------------------------


def _validate_offense(
    records: list[OffensivePlayRecord],
    category_rules: dict[str, OffenseCategoryRule],
) -> list[Violation]:
    by_category = _group_by_pool_category(records)
    violations: list[Violation] = []

    for category, rule in category_rules.items():
        plays = by_category.get(category, [])
        if not plays:
            if rule.required:
                violations.append(
                    Violation(
                        rule_name=RuleName.CATEGORY_REQUIRED,
                        message=f"Required offensive category '{category}' has no plays",
                        pool_category=category,
                    )
                )
            continue

        if len(plays) < rule.min_count:
            violations.append(
                Violation(
                    rule_name=RuleName.CATEGORY_MIN_COUNT,
                    message=(
                        f"Offensive category '{category}' has {len(plays)} plays; "
                        f"PNFL requires at least {rule.min_count}."
                    ),
                    pool_category=category,
                )
            )

        if rule.max_qb_draws is not None:
            qb_draws = sum(1 for p in plays if p.qb_draw)
            if qb_draws > rule.max_qb_draws:
                violations.append(
                    Violation(
                        rule_name=RuleName.CATEGORY_MAX_QB_DRAWS,
                        message=(
                            f"Offensive category '{category}' has {qb_draws} QB draws; "
                            f"PNFL allows at most {rule.max_qb_draws}."
                        ),
                        pool_category=category,
                    )
                )

        if rule.max_rollouts is not None:
            rollouts = sum(1 for p in plays if p.rollout)
            if rollouts > rule.max_rollouts:
                violations.append(
                    Violation(
                        rule_name=RuleName.CATEGORY_MAX_ROLLOUTS,
                        message=(
                            f"Offensive category '{category}' has {rollouts} rollouts; "
                            f"PNFL allows at most {rule.max_rollouts}."
                        ),
                        pool_category=category,
                    )
                )

        if rule.max_timed_percent is not None:
            timed = sum(1 for p in plays if p.pass_type == PassType.TIMED)
            if Fraction(timed, len(plays)) > rule.max_timed_percent:
                limit = _format_percent(rule.max_timed_percent)
                violations.append(
                    Violation(
                        rule_name=RuleName.CATEGORY_MAX_TIMED_PERCENT,
                        message=(
                            f"Offensive category '{category}' has {timed} of {len(plays)} "
                            f"timed passes; PNFL allows at most {limit}."
                        ),
                        pool_category=category,
                    )
                )

    return violations


# ---------------------------------------------------------------------------
# Defense
# ---------------------------------------------------------------------------


def _validate_defense(
    records: list[DefensivePlayRecord],
    category_rules: dict[str, DefenseCategoryRule],
    min_normal_plays: int,
) -> list[Violation]:
    by_category = _group_by_pool_category(records)
    violations: list[Violation] = []

    total = sum(len(plays) for plays in by_category.values())
    if total < min_normal_plays:
        violations.append(
            Violation(
                rule_name=RuleName.DEFENSE_MIN_PLAYS,
                message=(f"Defensive gameplan has {total} resolved plays; PNFL requires at least {min_normal_plays}."),
            )
        )

    for category, rule in category_rules.items():
        plays = by_category.get(category, [])
        if not plays:
            if rule.required:
                violations.append(
                    Violation(
                        rule_name=RuleName.CATEGORY_REQUIRED,
                        message=f"Required defensive category '{category}' has no plays",
                        pool_category=category,
                    )
                )
            continue

        if len(plays) < rule.min_count:
            violations.append(
                Violation(
                    rule_name=RuleName.CATEGORY_MIN_COUNT,
                    message=(
                        f"Defensive category '{category}' has {len(plays)} plays; "
                        f"PNFL requires at least {rule.min_count}."
                    ),
                    pool_category=category,
                )
            )

        two_dl_count = sum(1 for p in plays if p.personnel_grouping == DefensivePersonnel.RUN_AND_SHOOT)

        if rule.max_two_dl_percent is not None and Fraction(two_dl_count, len(plays)) > rule.max_two_dl_percent:
            limit = _format_percent(rule.max_two_dl_percent)
            violations.append(
                Violation(
                    rule_name=RuleName.CATEGORY_MAX_TWO_DL_PERCENT,
                    message=(
                        f"Defensive category '{category}' has {two_dl_count} of {len(plays)} "
                        f"2-DL plays; PNFL allows at most {limit}."
                    ),
                    pool_category=category,
                )
            )

    return violations


# ---------------------------------------------------------------------------
# Special teams
# ---------------------------------------------------------------------------


def _validate_special_categories(
    gameplan: GamePlan,
    required: frozenset[int],
) -> list[Violation]:
    """Each required special_category must have either a custom or stock play set."""
    violations: list[Violation] = []
    # special_plays = (custom_1, stock_1, custom_2, stock_2, ..., custom_10, stock_10).
    for category in sorted(required):
        custom_index = (category - 1) * 2
        stock_index = custom_index + 1
        custom = gameplan.special_plays[custom_index]
        stock = gameplan.special_plays[stock_index]
        if custom is None and stock is None:
            violations.append(
                Violation(
                    rule_name=RuleName.SPECIAL_CATEGORY_REQUIRED,
                    message=f"Required special category {category} has no play",
                )
            )
    return violations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _group_by_pool_category[T: OffensivePlayRecord | DefensivePlayRecord](
    records: Iterable[T],
) -> dict[str, list[T]]:
    by_category: dict[str, list[T]] = {}
    for record in records:
        by_category.setdefault(record.pool_category, []).append(record)
    return by_category


def _normal_slot_label(slot_index: int) -> str:
    """Format a 0-based normal slot index as `slot N (G-C)`.

    `N` is the 1-based slot number (1..64); `G-C` is the in-game grid position —
    group 1..16 of 4 plays, column 1..4 inside the group. Slot 0 -> `slot 1 (1-1)`,
    slot 4 -> `slot 5 (2-1)`, slot 63 -> `slot 64 (16-4)`.
    """
    group = slot_index // 4 + 1
    col = slot_index % 4 + 1
    return f"slot {slot_index + 1} ({group}-{col})"


def _format_percent(value: Fraction) -> str:
    """Render a Fraction as a percent string for violation messages."""
    pct = float(value) * 100
    # Trim trailing zeros; ".0" for whole-number values stays clean.
    text = f"{pct:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return f"{text}%"


__all__ = ["validate_gameplan"]
