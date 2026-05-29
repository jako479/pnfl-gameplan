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
- `PnflRuleError` raised by `save()` when validation finds any violation; gameplan is not written.
- `Violation` and `RuleName` (StrEnum) for structured violation reporting.
- Documentation: `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `RULES.md`.
- Test suite: compliant-baseline builders for offense and defense, targeted-violation tests covering every rule (`test_validators.py`), wrapper save-gate and round-trip tests (`test_pnfl_gameplan.py`).
