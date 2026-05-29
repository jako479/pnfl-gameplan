"""Shared fixtures and builders for pnfl-gameplan tests.

Each test that needs a `GamePlan` starts from `make_compliant_offense_gameplan`
or `make_compliant_defense_gameplan`, which produce PNFL-rules-compliant
baselines, then mutates only the slots the test cares about. This keeps every
test isolated to one rule and avoids spurious unrelated violations.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fbpro98_gameplan import CustomPlay, GamePlan, Play, ProfileType
from pnfl_playpool import (
    DefensivePersonnel,
    DefensivePlayRecord,
    OffensivePlayRecord,
    PassType,
    PlayPool,
    SpecialTeamsPlayRecord,
    read_play_pool,
)

# Real PNFL play pool used as fixture data; lives in the sibling
# pnfl-playpool repo and is treated as read-only ground truth.
PLAY_POOL_ROOT = Path(__file__).resolve().parents[2] / "pnfl-playpool" / "tests" / "data" / "plays"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def play_pool() -> PlayPool:
    """Build the PNFL play pool once per session from the shared test data."""
    return read_play_pool(PLAY_POOL_ROOT)


@pytest.fixture
def compliant_offense(play_pool: PlayPool) -> GamePlan:
    """An offensive gameplan that passes every PNFL rule."""
    return make_compliant_offense_gameplan(play_pool)


@pytest.fixture
def compliant_defense(play_pool: PlayPool) -> GamePlan:
    """A defensive gameplan that passes every PNFL rule."""
    return make_compliant_defense_gameplan(play_pool)


# ---------------------------------------------------------------------------
# Compliant-baseline builders
# ---------------------------------------------------------------------------


def make_compliant_offense_gameplan(pool: PlayPool) -> GamePlan:
    """64 plays that meet every PNFL offensive rule.

    Category mix: RM 10, RL 4, RR 4, GLR 3, PSL 5, PSM 5, PSR 5, PML 5, PMM 5,
    PMR 5, PLR 4, PRD 4, GLP 5 = 64.

    All passes picked to be non-rollout and non-timed; all runs non-QB-draw.
    """
    plays: list[Play | None] = []
    plays.extend(_pick_off_run(pool, "RM", 10))
    plays.extend(_pick_off_run(pool, "RL", 4))
    plays.extend(_pick_off_run(pool, "RR", 4))
    plays.extend(_pick_off_run(pool, "GLR", 3))
    plays.extend(_pick_off_pass(pool, "PSL", 5))
    plays.extend(_pick_off_pass(pool, "PSM", 5))
    plays.extend(_pick_off_pass(pool, "PSR", 5))
    plays.extend(_pick_off_pass(pool, "PML", 5))
    plays.extend(_pick_off_pass(pool, "PMM", 5))
    plays.extend(_pick_off_pass(pool, "PMR", 5))
    plays.extend(_pick_off_pass(pool, "PLR", 4))
    plays.extend(_pick_off_pass(pool, "PRD", 4))
    plays.extend(_pick_off_pass(pool, "GLP", 5))
    assert len(plays) == 64, f"expected 64 plays, got {len(plays)}"
    return _build_gameplan(ProfileType.OFFENSE, pool, plays)


def make_compliant_defense_gameplan(pool: PlayPool) -> GamePlan:
    """64 plays that meet every PNFL defensive rule.

    Category mix: RunLeft 10, RunMiddle 10, RunRight 10, PassShort 7,
    PassMedium 7, PassLong 6, GLrun 3, GLpass 3, RunDazzle 4, PassDazzle 4 = 64.

    All picks use non-R&S plays so the max-2-DL caps stay satisfied across
    every category.
    """
    plays: list[Play | None] = []
    plays.extend(_pick_def(pool, "RunLeft", 10))
    plays.extend(_pick_def(pool, "RunMiddle", 10))
    plays.extend(_pick_def(pool, "RunRight", 10))
    plays.extend(_pick_def_pass(pool, "PassShort", 7, two_dl=0))
    plays.extend(_pick_def_pass(pool, "PassMedium", 7, two_dl=0))
    plays.extend(_pick_def_pass(pool, "PassLong", 6, two_dl=0))
    plays.extend(_pick_def(pool, "GLrun", 3))
    plays.extend(_pick_def(pool, "GLpass", 3))
    plays.extend(_pick_def(pool, "RunDazzle", 4))
    plays.extend(_pick_def_pass(pool, "PassDazzle", 4, two_dl=0))
    assert len(plays) == 64, f"expected 64 plays, got {len(plays)}"
    return _build_gameplan(ProfileType.DEFENSE, pool, plays)


# ---------------------------------------------------------------------------
# Builder helpers (public so tests can compose targeted variants)
# ---------------------------------------------------------------------------


def to_custom_play(record: OffensivePlayRecord | DefensivePlayRecord | SpecialTeamsPlayRecord) -> CustomPlay:
    """Build the CustomPlay the .pln stores for a play pool record.

    Mirrors fbpro98_gameplanwriter's _build_custom_play (the writer is what
    actually creates .pln files in production).
    """
    file_path = record.file_path
    return CustomPlay(
        filename=f"PNFL\\{file_path.name}",
        play_category=record.play_category,
        special_category=record.special_category,
        user_category=record.user_category,
    )


def replace_slot(gameplan: GamePlan, slot: int, play: Play | None) -> GamePlan:
    """Return a new gameplan with `play` at `slot` of normal_plays."""
    new_slots = list(gameplan.normal_plays)
    new_slots[slot] = play
    return replace(gameplan, normal_plays=tuple(new_slots))


def clear_category(gameplan: GamePlan, pool: PlayPool, pool_category: str) -> GamePlan:
    """Drop every play in `pool_category` from the normal slots."""
    new_slots: list[Play | None] = []
    for play in gameplan.normal_plays:
        if play is None:
            new_slots.append(None)
            continue
        record = pool.find_by_name(play.name)
        if isinstance(record, (OffensivePlayRecord, DefensivePlayRecord)) and record.pool_category == pool_category:
            new_slots.append(None)
        else:
            new_slots.append(play)
    return replace(gameplan, normal_plays=tuple(new_slots))


# ---------------------------------------------------------------------------
# Internal pick helpers
# ---------------------------------------------------------------------------


def _build_gameplan(profile_type: ProfileType, pool: PlayPool, plays: list[Play | None]) -> GamePlan:
    """Wrap a list of plays in a structurally-valid GamePlan with compliant special slots."""
    padded = tuple(plays + [None] * (GamePlan.NUMBER_NORMAL_PLAYS - len(plays)))
    special_plays = _build_compliant_special_plays(pool, profile_type)
    clock_plays = _build_compliant_clock_plays(pool) if profile_type == ProfileType.OFFENSE else (None, None)
    return GamePlan(
        profile_type=profile_type,
        normal_plays=padded,
        special_plays=special_plays,
        clock_plays=clock_plays,
    )


def _build_compliant_special_plays(pool: PlayPool, profile_type: ProfileType) -> tuple[Play | None, ...]:
    """Populate the 6 PNFL-required special_category slots with custom plays from the pool."""
    required = (1, 2, 3, 4, 9, 10)
    is_offense = profile_type == ProfileType.OFFENSE
    slots: list[Play | None] = [None] * 20
    for category in required:
        record = _pick_special(pool, category, is_offense=is_offense)
        slots[(category - 1) * 2] = to_custom_play(record)
    return tuple(slots)


def _build_compliant_clock_plays(pool: PlayPool) -> tuple[Play | None, Play | None]:
    """Build the two offensive clock plays (special_category 11 and 12)."""
    return (
        _make_clock_play(pool, special_category=11),
        _make_clock_play(pool, special_category=12),
    )


def _make_clock_play(pool: PlayPool, special_category: int) -> CustomPlay:
    """Synthesize a clock-slot play. The pool doesn't expose clock plays, so we
    reuse an offensive run play's metadata and override its special_category."""
    base = next(p for p in pool.offensive_plays if p.pool_category == "RM")
    return CustomPlay(
        filename=f"PNFL\\{base.file_path.name}",
        play_category=1,
        special_category=special_category,
        user_category=base.user_category,
    )


def _pick_off_run(pool: PlayPool, pool_category: str, count: int) -> list[CustomPlay]:
    candidates = [p for p in pool.offensive_plays if p.pool_category == pool_category and not p.qb_draw]
    return [to_custom_play(c) for c in candidates[:count]]


def _pick_off_pass(pool: PlayPool, pool_category: str, count: int) -> list[CustomPlay]:
    candidates = [
        p
        for p in pool.offensive_plays
        if p.pool_category == pool_category and not p.rollout and p.pass_type != PassType.TIMED
    ]
    return [to_custom_play(c) for c in candidates[:count]]


def _pick_def(pool: PlayPool, pool_category: str, count: int) -> list[CustomPlay]:
    candidates = [
        p
        for p in pool.defensive_plays
        if p.pool_category == pool_category and p.personnel_grouping != DefensivePersonnel.RUN_AND_SHOOT
    ]
    return [to_custom_play(c) for c in candidates[:count]]


def _pick_def_pass(pool: PlayPool, pool_category: str, count: int, *, two_dl: int) -> list[CustomPlay]:
    """Pick `count` defensive plays from `pool_category`, with exactly `two_dl` being R&S (2-DL)."""
    non_two_dl_needed = count - two_dl
    rs_plays = [
        p
        for p in pool.defensive_plays
        if p.pool_category == pool_category and p.personnel_grouping == DefensivePersonnel.RUN_AND_SHOOT
    ][:two_dl]
    non_rs_plays = [
        p
        for p in pool.defensive_plays
        if p.pool_category == pool_category and p.personnel_grouping != DefensivePersonnel.RUN_AND_SHOOT
    ][:non_two_dl_needed]
    return [to_custom_play(c) for c in rs_plays + non_rs_plays]


def _pick_special(pool: PlayPool, special_category: int, *, is_offense: bool) -> SpecialTeamsPlayRecord:
    candidates = [
        p
        for p in pool.special_teams_plays
        if p.special_category == special_category
        and (p.play_file.is_offensive if is_offense else p.play_file.is_defensive)
    ]
    if not candidates:
        # Fall back to any play in the category (some test pools may not have
        # both sides for every category).
        candidates = [p for p in pool.special_teams_plays if p.special_category == special_category]
    return candidates[0]
