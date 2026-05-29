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

### Changed

- `PnflGamePlan.save(path)` no longer gates writes on PNFL-rule violations. It now emits one `logger.warning(...)` per violation (prefixed with `pool_category` when present), writes the file regardless, and returns `tuple[Violation, ...]`. PNFL rules are treated as league policy, not file-format invariants — callers that want a strict gate read the returned tuple (or call `validate()` upfront).

### Removed

- `PnflRuleError` exception type. `save()` no longer raises on PNFL violations; the violation tuple is the report. Strict callers compose `if pg.validate(): handle_violations(...)` themselves.
