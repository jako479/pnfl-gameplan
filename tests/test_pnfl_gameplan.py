"""Tests for the `PnflGamePlan` wrapper itself (composition + save-gate behavior)."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import clear_category, replace_slot
from fbpro98_gameplan import GamePlan, read_gameplan, write_gameplan
from pnfl_playpool import PlayPool

from pnfl_gameplan import (
    PNFL_RULES,
    PnflGamePlan,
    PnflRuleError,
    RuleName,
)


def test_from_file_loads_gameplan(tmp_path: Path, compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    path = tmp_path / "tmp.pln"
    write_gameplan(compliant_offense, path)

    pg = PnflGamePlan.from_file(str(path), PNFL_RULES, play_pool)
    assert pg.gameplan == compliant_offense
    assert pg.rules is PNFL_RULES
    assert pg.play_pool is play_pool


def test_from_bytes_loads_gameplan(tmp_path: Path, compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    path = tmp_path / "tmp.pln"
    write_gameplan(compliant_offense, path)
    data = path.read_bytes()

    pg = PnflGamePlan.from_bytes(data, PNFL_RULES, play_pool)
    assert pg.gameplan == compliant_offense


def test_validate_returns_empty_for_compliant(compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    pg = PnflGamePlan(gameplan=compliant_offense, rules=PNFL_RULES, play_pool=play_pool)
    assert pg.validate() == ()


def test_save_writes_when_compliant(tmp_path: Path, compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    pg = PnflGamePlan(gameplan=compliant_offense, rules=PNFL_RULES, play_pool=play_pool)
    out = tmp_path / "out.pln"

    pg.save(str(out))

    assert out.exists()
    # Round-trips: file we just wrote loads back to the same gameplan.
    assert read_gameplan(out) == compliant_offense


def test_save_raises_when_violations(tmp_path: Path, compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    broken = clear_category(compliant_offense, play_pool, "PSL")
    pg = PnflGamePlan(gameplan=broken, rules=PNFL_RULES, play_pool=play_pool)
    out = tmp_path / "out.pln"

    with pytest.raises(PnflRuleError) as exc_info:
        pg.save(str(out))

    assert any(v.rule_name == RuleName.CATEGORY_REQUIRED for v in exc_info.value.violations)
    # File must not exist when save is gated by a violation.
    assert not out.exists()


def test_pnfl_rule_error_exposes_violation_tuple(compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    duplicate = compliant_offense.normal_plays[0]
    assert duplicate is not None
    broken = replace_slot(compliant_offense, 63, duplicate)
    pg = PnflGamePlan(gameplan=broken, rules=PNFL_RULES, play_pool=play_pool)

    with pytest.raises(PnflRuleError) as exc_info:
        pg.save("unused.pln")

    assert isinstance(exc_info.value.violations, tuple)
    assert len(exc_info.value.violations) >= 1
