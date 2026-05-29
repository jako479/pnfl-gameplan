# pnfl-gameplan — Status

**Status: Initial Implementation Complete**

PNFL league-rule wrapper for `fbpro98-gameplan`. Provides save-time validation and a queryable list of rule violations for any `.pln` gameplan.

## Implemented

- `PnflGamePlan` composition wrapper — pairs a `GamePlan` with a `PnflRules` and the `PlayPool` used to resolve plays; exposes `from_file`, `from_bytes`, `validate`, and `save`.
- `PNFL_RULES` rule set — see [RULES.md](RULES.md) for the full list. Covers offense (per-category minimums, QB-draw cap, rollout cap, timed-pass percentage), defense (per-category minimums, R&S "2-DL" minimum and percentage), required special-team categories, and the all-slots-filled requirement on defense.
- `validate_gameplan` — pure-function validator yielding `tuple[Violation, ...]`; one violation per rule breach with optional `pool_category`.
- `save` — validates first, raises `PnflRuleError(violations)` on any violation, otherwise writes via `fbpro98-gameplan`.
- Slot-level rules (duplicates, unresolved-play) checked alongside category aggregates.

## Not yet covered

- Wiring into `fbpro98-gameplanwriter` — the writer currently has its own format-level checks (see [pnfl-docs/Design/gameplan-validation.md](../pnfl-docs/Design/gameplan-validation.md)); PNFL-rule enforcement at write time is a future step.
- `pnfl` CLI subcommand integration — none yet; this package is library-only.
- Coach release bundle inclusion — pnfl-gameplan is admin/league-side only until wired into a coach-facing CLI.
