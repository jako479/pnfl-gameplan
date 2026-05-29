# pnfl-gameplan — Status

**Status: Initial Implementation Complete**

PNFL league-rule wrapper for `fbpro98-gameplan`. Provides save-time warning reports and a queryable list of rule violations for any `.pln` gameplan.

## Implemented

- `PnflGamePlan` composition wrapper — pairs a `GamePlan` with a `PnflRules` and the `PlayPool` used to resolve plays; exposes `from_file`, `from_bytes`, `validate`, and `save`.
- `PNFL_RULES` rule set — see [RULES.md](RULES.md) for the full list. Covers offense (per-category minimums, QB-draw cap, rollout cap, timed-pass percentage), defense (per-category minimums, R&S "2-DL" minimum and percentage), required special-team categories, and the all-slots-filled requirement on defense.
- `validate_gameplan` — pure-function validator yielding `tuple[Violation, ...]`; one violation per rule breach with optional `pool_category`.
- `save` — emits per-violation `warnings.warn(..., PnflRuleWarning)` calls, writes via `fbpro98-gameplan`, and returns the violation tuple. PNFL violations never block the write — callers that want a strict gate read the returned tuple. Apps that want every violation surfaced every save install `warnings.simplefilter("always", PnflRuleWarning)` at entry.
- Slot-level rules (duplicates, unresolved-play) checked alongside category aggregates.
- `pnfl-gameplanwriter` integration — the CLI writer composes `writer.apply(...)` (returns a `PnflGamePlan`) then `pg.save(path)`, so the CLI surfaces PNFL warnings without blocking the write.

## Not yet covered

- `pnfl` CLI subcommand integration beyond `write-gameplan` — `read-gameplan` reads but doesn't persist, so it sees no violations.
- Coach release bundle inclusion — pnfl-gameplan is admin/league-side only until wired into a coach-facing CLI.
