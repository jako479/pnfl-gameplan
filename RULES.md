# PNFL Gameplan Rules

The complete list of PNFL rules enforced by `validate_gameplan`. Sources: the league's [offensive rules thread](https://pnfl.biz/messageboard/viewtopic.php?f=16&t=14) and [defensive rules thread](https://pnfl.biz/messageboard/viewtopic.php?f=16&t=15).

Pool-category keys (e.g. `RM`, `PSL`, `RunMiddle`, `PassDazzle`) come from `pnfl_playpool` and reflect the play pool's directory layout.

## Universal (both sides)

- **No duplicate plays.** A play name may appear at most once across the 64 normal slots.
- **Plays must resolve in the play pool.** Any normal-slot play whose name doesn't match a record in the bound `PlayPool` raises a violation.
- **Required special-team categories.** Each of the six PNFL-required special categories must have either a custom or stock play set: FG/PAT (1), Kickoff / Kick Return (2), Punt / Punt Return (3), Onside Kick / Onside Return (4), Free Kick / Free Kick Return (9), Squib Kick / Squib Return (10). The four fake categories (5–8) are not required.

## Offensive

### Required run categories

| Pool category | Min plays | Extra constraint |
|---|---|---|
| `RM` (Run Middle) | 10 | ≤ 2 QB draws |

### Optional run categories (if any play uses them)

| Pool category | Min plays if used | Extra constraint |
|---|---|---|
| `RL` (Run Left) | 4 | ≤ 2 QB draws |
| `RR` (Run Right) | 4 | ≤ 2 QB draws |
| `GLR` (Goal Line Run) | 3 | — |

### Required pass categories

Every pass category caps **rollouts at 2** and **timed passes at 50%** (≤ 1/2 of the plays in the category).

| Pool category | Min plays |
|---|---|
| `PSL` (Pass Short Left) | 5 |
| `PSM` (Pass Short Middle) | 5 |
| `PSR` (Pass Short Right) | 5 |
| `PML` (Pass Medium Left) | 5 |
| `PMM` (Pass Medium Middle) | 5 |
| `PMR` (Pass Medium Right) | 5 |
| `PLR` (Pass Long Right) | 4 |
| `PRD` (Pass Razzle Dazzle) | 4 |

### Optional pass categories (if any play uses them)

| Pool category | Min plays if used | Rollout cap | Timed cap |
|---|---|---|---|
| `GLP` (Goal Line Pass) | 3 | 2 | 50% |

### Disallowed offensive categories

Pass Long Left and Pass Long Middle are not allowed in PNFL gameplans. The `pnfl-playpool` directory layout doesn't even define those pool categories, so this rule is enforced upstream by the pool's classification — no validator runs in `pnfl-gameplan`.

## Defensive

### Slot requirement

All 64 normal slots must be filled. (Equivalent to the league's "minimum 64 plays" rule.)

### Required run categories

| Pool category | Min plays |
|---|---|
| `RunLeft` | 6 |
| `RunMiddle` | 6 |
| `RunRight` | 6 |

### Required pass categories

The PNFL "2-DL" rule treats Run-and-Shoot personnel (`DefensivePersonnel.RUN_AND_SHOOT`) as 2-DL plays.

| Pool category | Min plays | 2-DL cap |
|---|---|---|
| `PassShort` | 6 | ≤ 33% (≤ 1/3) |
| `PassMedium` | 6 | ≤ 33% (≤ 1/3) |
| `PassLong` | 6 | ≤ 50% |

### Optional categories (if any play uses them)

| Pool category | Min plays if used | 2-DL cap |
|---|---|---|
| `GLrun` (Goal Line Run) | 3 | — |
| `GLpass` (Goal Line Pass) | 3 | — |
| `RunDazzle` | 4 | — |
| `PassDazzle` | 4 | ≤ 50% |

## Rules explicitly NOT enforced

- **Per-play personnel constraints.** PNFL rules dictate the personnel each pass category's plays must use — e.g. *Pass Short: minimum two DLs and three LBs, at least one DL defending the LOS*; *Pass Dazzle: at least two 2-DLs in the play and at least two players covering the LOS*. Those describe how each individual play must be built, not how many plays of a given type the gameplan must contain, so they are play-design constraints. pnfl-gameplan assumes plays are valid for their pool category.
- **Situational eligibility.** "Pass Long callable on 1st or 2nd down when greater than 10 yards" is an in-game decision rule, not a gameplan-construction rule.
- **Disallowed offensive pass-long-left / pass-long-middle.** Enforced upstream by the play pool's directory layout (no such pool category exists).
