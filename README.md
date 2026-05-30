# pnfl-gameplan

PNFL league rules layered on [fbpro98-gameplan](../fbpro98-gameplan/). Wraps a `GamePlan` so `validate()` reports rule violations and `save()` writes the file regardless — emitting one `PnflRuleWarning` per violation. Callers that want a strict gate inspect the returned violation tuple.

## Setup

```bash
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

## Usage

```python
from pnfl_gameplan import PnflGamePlan, PNFL_RULES
from pnfl_playpool import read_play_pool

play_pool = read_play_pool("PNFL")  # the league play pool

# Load and inspect violations without persisting
pg = PnflGamePlan.from_file("DEN-OFF1.pln", PNFL_RULES, play_pool)
for v in pg.validate():
    print(f"[{v.rule_name}] {v.pool_category or '-'}: {v.message}")

# Persist. PNFL violations are logged as warnings and returned; the file is
# written regardless of whether the gameplan is rule-compliant.
violations = pg.save("DEN-OFF1.pln")
```

`PnflGamePlan` is composed of an underlying `GamePlan`, a `PnflRules` instance, and the `PlayPool` used to resolve each play's pool category and attributes — it does not inherit from `GamePlan`. See [ARCHITECTURE.md](ARCHITECTURE.md) for the reasoning.

```python
pg.gameplan    # underlying fbpro98_gameplan.GamePlan
pg.rules       # PnflRules currently bound to this gameplan
pg.play_pool   # PlayPool used to resolve play names
pg.validate()  # tuple[Violation, ...]
pg.save(path)  # logs per-violation warnings; writes the file; returns tuple[Violation, ...]
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
