# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial library implementation.
- `PnflGamePlan` composition wrapper pairing a `GamePlan` with a `PnflRules` and `PlayPool`; exposes `from_file`, `from_bytes`, `validate`, and `save`.
- `PnflRules` rule-set type plus the canonical `PNFL_RULES` instance, sourced from the league's offensive and defensive coaching-rules threads.
- `OffenseCategoryRule` and `DefenseCategoryRule` rule-data types covering per-category minimums, QB-draw cap, rollout cap, timed-pass percentage, R&S "2-DL" minimum and percentage caps.
- `validate_gameplan` validator returning `tuple[Violation, ...]`; reports duplicates, unresolved plays, category min counts, attribute caps, defense-side all-slots-filled rule, and required special-team categories.
- `Violation` and `RuleName` (StrEnum) for structured violation reporting.
- Documentation: `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `RULES.md`.
- Test suite: compliant-baseline builders for offense and defense, targeted-violation tests covering every rule (`test_validators.py`), wrapper composition and save warn-and-persist tests (`test_pnfl_gameplan.py`).

### Added

- `PnflRuleWarning(UserWarning)` exported from the package. Subclass of `UserWarning` so consumers can filter or assert on it.
- `PnflGamePlan` property forwarders (`normal_plays`, `special_plays`, `clock_plays`, `custom_special_plays`, `stock_special_plays`, `is_offense`, `is_defense`) and method forwarders (`with_normal_plays`, `with_custom_special_plays`) returning new `PnflGamePlan` instances. Class also exposes `NUMBER_NORMAL_PLAYS`, `NUMBER_SPECIAL_SLOTS`, `NUMBER_SPECIAL_CATEGORIES`, `NUMBER_CLOCK_SLOTS` as `ClassVar` constants.
- Re-exports of `fbpro98-gameplan` value types (`CustomPlay`, `StockPlay`, `Play`, `ProfileType`) and I/O (`read_gameplan`, `parse_gameplan`, `write_gameplan`, `InvalidGamePlanError`) so downstream consumers (`pnfl-gameplanwriter`, `pnfl-gameplanreader`) depend only on `pnfl-gameplan`.

### Changed

- `PnflGamePlan.save(path)` no longer gates writes on PNFL-rule violations. It now emits one `warnings.warn(..., PnflRuleWarning)` per violation (prefixed with `pool_category` when present), writes the file regardless, and returns `tuple[Violation, ...]`. PNFL rules are treated as league policy, not file-format invariants — callers that want a strict gate read the returned tuple (or call `validate()` upfront). When violations are present, `save()` also logs one `logger.info("Persisted with N PNFL rule violation(s)")` summary line.
- Switched per-violation reporting from `logger.warning(...)` to `warnings.warn(..., PnflRuleWarning)`. The library does **not** install a `warnings` filter; applications that want every violation surfaced should call `warnings.simplefilter("always", PnflRuleWarning)` at entry. Breaking change for consumers that captured violations via `caplog` — switch to `pytest.warns(PnflRuleWarning)` or `warnings.catch_warnings()`.

### Removed

- `PnflRuleError` exception type. `save()` no longer raises on PNFL violations; the violation tuple is the report. Strict callers compose `if pg.validate(): handle_violations(...)` themselves.
