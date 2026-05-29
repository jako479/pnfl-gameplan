# pnfl-gameplan — Architecture

Library that owns the PNFL league's gameplan rule set and pairs it with a `GamePlan` from `fbpro98-gameplan` plus a `PlayPool` from `pnfl-playpool` for validation and rule-aware I/O.

## Module layout

```
src/pnfl_gameplan/
├── __init__.py    # public API re-exports
├── model.py       # PnflGamePlan, Violation, RuleName
├── rules.py       # OffenseCategoryRule, DefenseCategoryRule, PnflRules, PNFL_RULES
└── validators.py  # validate_gameplan and per-side helpers
```

## Composition, not inheritance

`PnflGamePlan` wraps a `GamePlan`, a `PnflRules`, and the `PlayPool` it resolves plays against — it does not inherit from `GamePlan`. The same Liskov argument from [pnfl-profile](../pnfl-profile/ARCHITECTURE.md) applies: code written against the `GamePlan` contract should not silently see new exception types from a `PnflGamePlan` handed to it.

To give consumers a `GamePlan`-shaped API anyway, `PnflGamePlan` exposes property forwarders (`normal_plays`, `special_plays`, `clock_plays`, `custom_special_plays`, `stock_special_plays`, `is_offense`, `is_defense`) and method forwarders (`with_normal_plays`, `with_custom_special_plays`) that return a new `PnflGamePlan` — so the rules + pool binding survives every edit. The class also re-exports the format-layer value types (`CustomPlay`, `StockPlay`, `Play`, `ProfileType`) and the I/O functions (`read_gameplan`, `parse_gameplan`, `write_gameplan`, `InvalidGamePlanError`) from `fbpro98-gameplan`, so downstream consumers (`pnfl-gameplanwriter`, `pnfl-gameplanreader`) depend only on `pnfl-gameplan`.

Three layers, three jobs:

- `fbpro98-gameplan` — file I/O for the `.pln` format. No league knowledge.
- `pnfl-playpool` — classifies every `.ply` in the league pool into typed records with pool category and attribute flags (rollout, QB draw, timed pass, Run-and-Shoot personnel, etc.). No gameplan knowledge.
- `pnfl-gameplan` — PNFL semantics over a `GamePlan` whose plays are looked up in a `PlayPool`. Uses both lower layers for read/write and per-play attributes.

## Rule data

`PNFL_RULES` is a frozen `PnflRules` instance defined in [rules.py](src/pnfl_gameplan/rules.py). Rule data is decoupled from validator logic — alternate rule sets (a future season, a custom variant for testing) can be constructed by composing the same types, and `PnflGamePlan` is bound to a specific rule set at construction time.

The rules are **aggregate counts** over the 64 normal slots — minimum plays per pool category, plus per-category attribute caps. This is a different shape than pnfl-profile's per-situation matrix, so the data types are different:

- `OffenseCategoryRule(required, min_count, max_qb_draws, max_rollouts, max_timed_percent)`
- `DefenseCategoryRule(required, min_count, min_two_dl, max_two_dl_percent)`

Percentages use `fractions.Fraction` so comparisons like "≤ 1/3" are exact integer math.

Optional categories enforce `min_count` only when the category actually appears in the gameplan; required categories always fire. Required special-team categories (FG/PAT, Kickoff, Punt, Onside, Free Kick, Squib) must have either a custom or stock play set.

The full list of rules is in [RULES.md](RULES.md).

## Why pnfl-gameplan needs the play pool

Gameplan rules are about per-play attributes (rollout, QB draw, timed pass, 2-DL personnel). The `.pln` binary stores plays as filename references — none of those attributes are encoded in the file itself. To enforce the rules we have to resolve each play name back to its `OffensivePlayRecord` or `DefensivePlayRecord` in the pool, which is where the directory layout and naming convention give us the attribute flags.

`PlayPool` is therefore a required parameter at every `PnflGamePlan` construction site — it's not optional, and there is no fallback when a play can't be resolved (the validator reports an `UNRESOLVED_PLAY` violation and excludes that play from category counts).

## Validation contract

`validate_gameplan(gameplan, rules, play_pool)` runs every PNFL validator and returns one `Violation` per breach. `PnflGamePlan.save(path)` calls it first, emits a `warnings.warn(..., PnflRuleWarning)` for each violation (prefixed with `pool_category` when present), and then delegates to `fbpro98-gameplan`'s `write_gameplan` **regardless of whether violations were found**. `save()` returns the same violation tuple so callers can inspect/aggregate it programmatically. The library doesn't install a `warnings` filter; applications that want every violation surfaced every save call `warnings.simplefilter("always", PnflRuleWarning)` at entry.

PNFL rules are league policy, not file-format invariants — the format library accepts any well-formed `.pln`, and pnfl-gameplan treats league-rule failures as **warnings the caller can act on**, not write barriers. Tools that want a strict gate (e.g., a hypothetical league-submission audit) inspect the returned tuple (or call `validate()` upfront) and refuse to proceed when it is non-empty.

Validators are pure functions of the three inputs. They never mutate.

## What this package does

- Wraps an fbpro98 `GamePlan` in a `PnflGamePlan` bound to a `PnflRules` and a `PlayPool`.
- Validates every PNFL gameplan rule scraped from the league rules threads ([offense](https://pnfl.biz/messageboard/viewtopic.php?f=16&t=14), [defense](https://pnfl.biz/messageboard/viewtopic.php?f=16&t=15)).
- Save-time warning report: per-violation `PnflRuleWarning` plus a `tuple[Violation, ...]` return; the file is always written.

## What this package does NOT do

- File format parsing or writing — fbpro98-gameplan owns that.
- Pool classification / attribute detection — pnfl-playpool owns that.
- Line-of-scrimmage / personnel-on-LOS rules — those are play-design concerns; PNFL assumes plays are valid for their category.
- Game-plan situational logic ("Pass Long is callable on 1st or 2nd down with 10+ yards") — those are in-game rules, not gameplan-construction rules.

## Testing

- [tests/test_validators.py](tests/test_validators.py) — each rule exercised against a PNFL-compliant baseline mutated to fire that one rule.
- [tests/test_pnfl_gameplan.py](tests/test_pnfl_gameplan.py) — `PnflGamePlan` construction, `from_file` / `from_bytes`, `save` semantics including the warn-and-persist behavior (captured via `pytest.warns(PnflRuleWarning)`) when violations are present.

Compliant-baseline builders (`tests/conftest.py::make_compliant_offense_gameplan`, `make_compliant_defense_gameplan`) construct gameplans that satisfy every rule, so individual tests only need to mutate the slot(s) under inspection without tripping unrelated rules.

The session-scoped `play_pool` fixture loads the real PNFL play pool from sibling `pnfl-playpool/tests/data/plays/`, which serves as ground truth for what attributes each play has.
