"""Targeted PNFL rule-violation tests.

Each test starts from a compliant gameplan and mutates only the slots needed
to trigger one specific rule, then asserts the matching violation appears
(and no others slip in unrelated to the mutation).
"""

from __future__ import annotations

from dataclasses import replace

from conftest import (
    clear_category,
    replace_slot,
    to_custom_play,
)
from fbpro98_gameplan import CustomPlay, GamePlan
from pnfl_playpool import (
    DefensivePersonnel,
    PassType,
    PlayPool,
)

from pnfl_gameplan import (
    PNFL_RULES,
    PnflRules,
    RuleName,
    Violation,
    validate_gameplan,
)

# ---------------------------------------------------------------------------
# Compliant baselines
# ---------------------------------------------------------------------------


def test_compliant_offense_has_no_violations(compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    assert validate_gameplan(compliant_offense, PNFL_RULES, play_pool) == ()


def test_compliant_defense_has_no_violations(compliant_defense: GamePlan, play_pool: PlayPool) -> None:
    assert validate_gameplan(compliant_defense, PNFL_RULES, play_pool) == ()


# ---------------------------------------------------------------------------
# Slot-level checks (apply to both sides)
# ---------------------------------------------------------------------------


def test_duplicate_play_raises_one_violation(compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    # Copy slot 0's play into slot 63 to create a duplicate without dropping
    # below any category minimum.
    duplicate = compliant_offense.normal_plays[0]
    assert duplicate is not None
    other = compliant_offense.normal_plays[63]
    assert other is not None
    gp = replace_slot(compliant_offense, 63, duplicate)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    dup = [v for v in violations if v.rule_name == RuleName.DUPLICATE_PLAY]
    assert len(dup) == 1
    assert "slot 64 (16-4)" in dup[0].message
    assert "slot 1 (1-1)" in dup[0].message


def test_unresolved_play_reports_violation(compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    bogus = CustomPlay(filename="PNFL\\NOTREAL.PLY", play_category=1, special_category=0, user_category=0)
    # Drop a non-required-minimum slot — GLP starts at slot 59 and pads up to
    # 64; replacing slot 63 keeps required categories satisfied.
    gp = replace_slot(compliant_offense, 63, bogus)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    unresolved = [v for v in violations if v.rule_name == RuleName.UNRESOLVED_PLAY]
    assert len(unresolved) == 1
    assert "NOTREAL" in unresolved[0].message


# ---------------------------------------------------------------------------
# Offense: category min count
# ---------------------------------------------------------------------------


def test_offense_required_category_missing_reports_violation(compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    gp = clear_category(compliant_offense, play_pool, "PSL")
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    required = [v for v in violations if v.rule_name == RuleName.CATEGORY_REQUIRED]
    assert any(v.pool_category == "PSL" for v in required)


def test_offense_below_min_count_reports_violation(compliant_offense: GamePlan, play_pool: PlayPool) -> None:
    # Drop one of the five PSL plays. PSL is at slots 21-25 in the compliant
    # builder; clearing slot 21 leaves 4 < 5.
    gp = replace_slot(compliant_offense, 21, None)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    short = [v for v in violations if v.rule_name == RuleName.CATEGORY_MIN_COUNT and v.pool_category == "PSL"]
    assert len(short) == 1
    assert "4 plays" in short[0].message
    assert "5" in short[0].message


def test_offense_optional_category_below_min_reports_violation(
    play_pool: PlayPool, compliant_offense: GamePlan
) -> None:
    # GLR is optional; if any GLR appears it must hit 3. Compliant baseline
    # already uses GLR x3, so drop one to get 2 < 3.
    # GLR slots are 18-20 in the compliant builder.
    gp = replace_slot(compliant_offense, 18, None)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    glr_short = [v for v in violations if v.rule_name == RuleName.CATEGORY_MIN_COUNT and v.pool_category == "GLR"]
    assert len(glr_short) == 1


def test_offense_unused_optional_category_is_silent(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Drop the entire RL block (optional). No violations should appear for RL.
    gp = clear_category(compliant_offense, play_pool, "RL")
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    assert all(v.pool_category != "RL" for v in violations)


# ---------------------------------------------------------------------------
# Offense: attribute caps
# ---------------------------------------------------------------------------


def test_offense_too_many_qb_draws_reports_violation(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Replace 3 of the 10 RM plays with QB-draw RM plays; cap is 2.
    qb_draws = [p for p in play_pool.offensive_plays if p.pool_category == "RM" and p.qb_draw][:3]
    assert len(qb_draws) == 3
    gp = compliant_offense
    for i, record in enumerate(qb_draws):
        gp = replace_slot(gp, i, to_custom_play(record))
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    qb_violations = [v for v in violations if v.rule_name == RuleName.CATEGORY_MAX_QB_DRAWS and v.pool_category == "RM"]
    assert len(qb_violations) == 1
    assert "3 QB draws" in qb_violations[0].message


def test_offense_too_many_rollouts_reports_violation(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Replace 3 of the 5 PSL plays with rollouts; cap is 2. PSL is slots 21-25.
    rollouts = [p for p in play_pool.offensive_plays if p.pool_category == "PSL" and p.rollout][:3]
    assert len(rollouts) == 3
    gp = compliant_offense
    for i, record in enumerate(rollouts):
        gp = replace_slot(gp, 21 + i, to_custom_play(record))
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    rollout_violations = [
        v for v in violations if v.rule_name == RuleName.CATEGORY_MAX_ROLLOUTS and v.pool_category == "PSL"
    ]
    assert len(rollout_violations) == 1
    assert "3 rollouts" in rollout_violations[0].message


def test_offense_timed_at_exactly_50_percent_is_ok(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # PSL has 5 plays in compliant baseline. Replace 2 of 4 in a hypothetical
    # 4-play PMR cat? Use PLR (4-play minimum). Swap 2 of 4 PLR plays to timed.
    # 2/4 = 50% = exactly at cap, should NOT violate.
    timed = [p for p in play_pool.offensive_plays if p.pool_category == "PLR" and p.pass_type == PassType.TIMED][:2]
    assert len(timed) == 2
    # PLR slots are 50-53 in the compliant builder (after PMR ends).
    gp = compliant_offense
    for i, record in enumerate(timed):
        gp = replace_slot(gp, 50 + i, to_custom_play(record))
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    assert all(v.rule_name != RuleName.CATEGORY_MAX_TIMED_PERCENT or v.pool_category != "PLR" for v in violations)


def test_offense_timed_above_50_percent_reports_violation(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Swap 3 of 4 PLR plays to timed → 3/4 = 75% > 50%.
    timed = [p for p in play_pool.offensive_plays if p.pool_category == "PLR" and p.pass_type == PassType.TIMED][:3]
    assert len(timed) == 3
    gp = compliant_offense
    for i, record in enumerate(timed):
        gp = replace_slot(gp, 50 + i, to_custom_play(record))
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    timed_violations = [
        v for v in violations if v.rule_name == RuleName.CATEGORY_MAX_TIMED_PERCENT and v.pool_category == "PLR"
    ]
    assert len(timed_violations) == 1
    assert "50%" in timed_violations[0].message


# ---------------------------------------------------------------------------
# Defense: min plays + category min count
# ---------------------------------------------------------------------------


def test_defense_below_64_plays_reports_violation(play_pool: PlayPool, compliant_defense: GamePlan) -> None:
    # Blank one slot — defense gameplan is no longer at 64. PassDazzle is the
    # last block (slots 60-63), and clearing slot 63 leaves PassDazzle at 3,
    # which also trips its min-count rule; the test only asserts the slot count.
    gp = replace_slot(compliant_defense, 63, None)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    slot_violations = [v for v in violations if v.rule_name == RuleName.DEFENSE_MIN_PLAYS]
    assert len(slot_violations) == 1
    assert "63" in slot_violations[0].message


def test_defense_required_category_missing_reports_violation(play_pool: PlayPool, compliant_defense: GamePlan) -> None:
    gp = clear_category(compliant_defense, play_pool, "RunLeft")
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    required = [v for v in violations if v.rule_name == RuleName.CATEGORY_REQUIRED and v.pool_category == "RunLeft"]
    assert len(required) == 1


# ---------------------------------------------------------------------------
# Defense: 2-DL constraints
# ---------------------------------------------------------------------------


def test_defense_too_many_two_dl_reports_violation(play_pool: PlayPool, compliant_defense: GamePlan) -> None:
    # PassShort allows max 33% R&S. Compliant baseline has 7 PassShort plays
    # with 0 R&S; swap 3 to R&S → 3/7 ≈ 0.43 > 1/3.
    rs_plays = [
        p
        for p in play_pool.defensive_plays
        if p.pool_category == "PassShort" and p.personnel_grouping == DefensivePersonnel.RUN_AND_SHOOT
    ][:3]
    assert len(rs_plays) == 3
    # PassShort slots are 30-36 in the compliant builder.
    gp = compliant_defense
    for i, record in enumerate(rs_plays):
        gp = replace_slot(gp, 30 + i, to_custom_play(record))
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    two_dl = [
        v for v in violations if v.rule_name == RuleName.CATEGORY_MAX_TWO_DL_PERCENT and v.pool_category == "PassShort"
    ]
    assert len(two_dl) == 1


def test_defense_pass_dazzle_below_min_two_dl_reports_violation(
    play_pool: PlayPool, compliant_defense: GamePlan
) -> None:
    # Compliant baseline has PassDazzle at exactly the 2-DL minimum (2 R&S).
    # Replace one of those R&S plays with a non-R&S play → 1 R&S < min 2.
    non_rs = [
        p
        for p in play_pool.defensive_plays
        if p.pool_category == "PassDazzle" and p.personnel_grouping != DefensivePersonnel.RUN_AND_SHOOT
    ]
    swap_in = to_custom_play(non_rs[0])
    # PassDazzle slots in builder are 60-63; the first two are R&S.
    gp = replace_slot(compliant_defense, 60, swap_in)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    min_two_dl = [
        v for v in violations if v.rule_name == RuleName.CATEGORY_MIN_TWO_DL and v.pool_category == "PassDazzle"
    ]
    assert len(min_two_dl) == 1


# ---------------------------------------------------------------------------
# Special-teams
# ---------------------------------------------------------------------------


def test_special_category_missing_reports_violation(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Drop the FG/PAT slot (special_category 1, custom index 0).
    new_special = list(compliant_offense.special_plays)
    new_special[0] = None
    gp = replace(compliant_offense, special_plays=tuple(new_special))
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    missing = [v for v in violations if v.rule_name == RuleName.SPECIAL_CATEGORY_REQUIRED]
    assert len(missing) == 1
    assert "1" in missing[0].message


def test_stock_special_play_satisfies_requirement(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Drop the FG/PAT custom slot but leave the stock slot non-None. The
    # rule should be satisfied either way.
    from fbpro98_gameplan import StockPlay

    stock = StockPlay(
        play_name="STOCKFG",
        map_offset=0,
        map_size=0,
        play_category=1,
        special_category=1,
        user_category=0,
    )
    new_special = list(compliant_offense.special_plays)
    new_special[0] = None  # custom FG/PAT
    new_special[1] = stock  # stock FG/PAT
    gp = replace(compliant_offense, special_plays=tuple(new_special))
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    missing_fg = [v for v in violations if v.rule_name == RuleName.SPECIAL_CATEGORY_REQUIRED and "1" in v.message]
    assert missing_fg == []


# ---------------------------------------------------------------------------
# Custom rule sets
# ---------------------------------------------------------------------------


def test_custom_rules_override_min_count(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Override PSL min_count to 7 (compliant baseline has 5).
    new_off = dict(PNFL_RULES.offense_categories)
    new_off["PSL"] = replace(new_off["PSL"], min_count=7)
    rules = PnflRules(
        offense_categories=new_off,
        defense_categories=PNFL_RULES.defense_categories,
        required_special_categories=PNFL_RULES.required_special_categories,
        defense_min_normal_plays=PNFL_RULES.defense_min_normal_plays,
    )
    violations = validate_gameplan(compliant_offense, rules, play_pool)
    psl_short = [v for v in violations if v.rule_name == RuleName.CATEGORY_MIN_COUNT and v.pool_category == "PSL"]
    assert len(psl_short) == 1


# ---------------------------------------------------------------------------
# Violation aggregation
# ---------------------------------------------------------------------------


def test_multiple_independent_violations_all_reported(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    # Clear PSL entirely AND introduce a duplicate. Both should appear.
    gp = clear_category(compliant_offense, play_pool, "PSL")
    duplicate = gp.normal_plays[0]
    assert duplicate is not None
    gp = replace_slot(gp, 63, duplicate)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    rule_names = {v.rule_name for v in violations}
    assert RuleName.CATEGORY_REQUIRED in rule_names
    assert RuleName.DUPLICATE_PLAY in rule_names


# ---------------------------------------------------------------------------
# Violation dataclass invariants
# ---------------------------------------------------------------------------


def test_category_violations_set_pool_category_field(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    gp = clear_category(compliant_offense, play_pool, "PSL")
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    psl_v: Violation = next(v for v in violations if v.pool_category == "PSL")
    assert psl_v.rule_name == RuleName.CATEGORY_REQUIRED


def test_gameplan_wide_violations_have_no_pool_category(play_pool: PlayPool, compliant_offense: GamePlan) -> None:
    duplicate = compliant_offense.normal_plays[0]
    assert duplicate is not None
    gp = replace_slot(compliant_offense, 63, duplicate)
    violations = validate_gameplan(gp, PNFL_RULES, play_pool)
    dup = next(v for v in violations if v.rule_name == RuleName.DUPLICATE_PLAY)
    assert dup.pool_category is None
