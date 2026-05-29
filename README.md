# pnfl-gameplan

PNFL league rules and validation layered on top of [fbpro98-gameplan](../fbpro98-gameplan/). Wraps an fbpro98 `GamePlan` with the PNFL rule set so save-time validation, rule-violation reporting, and rule-aware tooling all see the same source of truth.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Usage

```python
from pnfl_gameplan import PnflGamePlan, PNFL_RULES
from pnfl_playpool import read_play_pool

play_pool = read_play_pool("PNFL")  # the league play pool

# Load and validate
pg = PnflGamePlan.from_file("DEN-OFF1.pln", PNFL_RULES, play_pool)
for v in pg.validate():
    print(f"[{v.rule_name}] {v.pool_category or '-'}: {v.message}")

# Save — validates first and raises PnflRuleError if anything fails
pg.save("DEN-OFF1.pln")
```

`PnflGamePlan` is composed of an underlying `GamePlan`, a `PnflRules` instance, and the `PlayPool` used to resolve each play's pool category and attributes — it does not inherit from `GamePlan`. See [ARCHITECTURE.md](ARCHITECTURE.md) for the reasoning.

```python
pg.gameplan    # underlying fbpro98_gameplan.GamePlan
pg.rules       # PnflRules currently bound to this gameplan
pg.play_pool   # PlayPool used to resolve play names
pg.validate()  # tuple[Violation, ...]
pg.save(path)  # raises PnflRuleError on violations; otherwise writes
```

## Rule data

`PNFL_RULES` is the canonical rule set. The full list of rules and conditions is documented in [RULES.md](RULES.md).

Construct a `PnflRules` directly to model a different season or a custom variant.

## Testing

```bash
pytest
```

## Building a Release

Ships these artifacts to the umbrella bundle:

- Python wheel (built by `pnfl/scripts/build_release.py`)

Consumed transitively by CLI subprojects in the [`pnfl`](../pnfl) umbrella.
