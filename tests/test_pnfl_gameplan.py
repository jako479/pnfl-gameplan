"""Tests for the `PnflGamePlan` wrapper itself (composition + save warn-and-persist behavior)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from conftest import clear_category, replace_slot
from fbpro98_gameplan import GamePlan, read_gameplan, write_gameplan
from pnfl_playpool import PlayPool

from pnfl_gameplan import (
    PNFL_RULES,
    PnflGamePlan,
    PnflRuleWarning,
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


def test_save_returns_empty_when_compliant(tmp_path: Path, compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    pg = PnflGamePlan(gameplan=compliant_offense, rules=PNFL_RULES, play_pool=play_pool)
    out = tmp_path / "out.pln"

    result = pg.save(str(out))

    assert result == ()
    assert out.exists()
    # Round-trips: file we just wrote loads back to the same gameplan.
    assert read_gameplan(out) == compliant_offense


def test_save_persists_despite_violations(
    tmp_path: Path,
    compliant_offense: GamePlan,
    play_pool: PlayPool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    broken = clear_category(compliant_offense, play_pool, "PSL")
    pg = PnflGamePlan(gameplan=broken, rules=PNFL_RULES, play_pool=play_pool)
    out = tmp_path / "out.pln"

    with pytest.warns(PnflRuleWarning) as captured, caplog.at_level(logging.INFO, logger="pnfl_gameplan.model"):
        result = pg.save(str(out))

    # File IS written despite violations.
    assert out.exists()
    # Save returns the same violation report validate() would have produced.
    assert any(v.rule_name == RuleName.CATEGORY_REQUIRED and v.pool_category == "PSL" for v in result)
    # Each violation surfaces as a PnflRuleWarning.
    assert any("PSL" in str(w.message) for w in captured.list)
    # A single INFO summary line records the persist-with-violations event.
    assert any(
        r.levelno == logging.INFO and "Persisted with" in r.message and "violation" in r.message for r in caplog.records
    )


def test_save_warning_prefix_includes_pool_category(
    tmp_path: Path,
    compliant_offense: GamePlan,
    play_pool: PlayPool,
) -> None:
    broken = clear_category(compliant_offense, play_pool, "PSL")
    pg = PnflGamePlan(gameplan=broken, rules=PNFL_RULES, play_pool=play_pool)

    with pytest.warns(PnflRuleWarning) as captured:
        pg.save(str(tmp_path / "out.pln"))

    psl_warnings = [w for w in captured.list if "PSL" in str(w.message)]
    assert psl_warnings, "expected at least one PnflRuleWarning mentioning PSL"
    # The prefix wraps the pool_category in brackets for grep-ability.
    assert any(str(w.message).startswith("[PSL]") for w in psl_warnings)


def test_save_gameplan_wide_warning_has_no_prefix(
    tmp_path: Path,
    compliant_offense: GamePlan,
    play_pool: PlayPool,
) -> None:
    duplicate = compliant_offense.normal_plays[0]
    assert duplicate is not None
    broken = replace_slot(compliant_offense, 63, duplicate)
    pg = PnflGamePlan(gameplan=broken, rules=PNFL_RULES, play_pool=play_pool)

    with pytest.warns(PnflRuleWarning) as captured:
        pg.save(str(tmp_path / "out.pln"))

    # The DUPLICATE_PLAY violation has no pool_category, so no "[...] " prefix.
    duplicate_warnings = [w for w in captured.list if "Duplicate" in str(w.message)]
    assert duplicate_warnings
    assert not str(duplicate_warnings[0].message).startswith("[")
