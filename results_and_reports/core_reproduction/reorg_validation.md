# Reorganization validation — 2026-09-16

Base: `6ed61d9` on `main`; implementation branch: `reorg`. This is a layout and
workflow validation, not a change to Hamiltonians, frozen seeds or goldens.

## Completed checks

- 350 moved files accounted for; 122 moved VHDL files and 55 evidence files are
  byte-identical to the pre-move snapshot.
- All relocated Python files compile; all PowerShell files parse.
- All 47 Python tests (29 replay/layout, 16 optimizer, 2 plot fallback) pass; layout and
  report-publication tests cover new paths and preservation of run/scratch data.
- Fake-vsim runner suite passes (priority, identity, licenses, isolation,
  timeout, stable exit codes and trace failure propagation).
- Real Questa failure smoke passes: compile=50, elaboration=51, assertion=52.
- All 11 frozen core source SHA-256 and seed signatures pass preflight.
- An index export with `core.autocrlf=true` also passes all 11 hashes and all 29
  replay/layout tests, proving the new checkout paths and pinned VHDL line endings.
- Primitive Hamiltonian verifier passes, including all 65,536 valid 8-bit sums.
- AND/XOR trace aggregation, CSV/PNG outputs and Top-mode WLF pass at
  `../gate_baseline/runs/questa/run_all_traces/reorg-traces-20260916/`.
- E4M3 coefficient-sweep path smoke passes, settle=20/count=10; this is a path
  smoke only, not a reproduction of historical sweep results.
- Matplotlib 3.11.2 and Numba 0.67.0 installed in ignored `.venv`; all seven
  Stage F modules import, `unit-check` and `pip check` pass. Gurobi optimization
  and missing Stage3 reconstruction were not run.

## Full core replay

Run ID: `reorg-validation-20260916`; QuestaSim 2024.1; fixed-seed replay;
`--update-reports` omitted to preserve the published evidence while validating
the new paths. **All 25 simulations and all original exact golden/conclusion
checks passed.** The machine-readable
[replay summary](reorg_reproduction_summary.json) records parameters, source
hashes, timing and counts. It identifies the pre-commit `6ed61d9` base with
`git_dirty=true`, as the validation ran before the reorganization commit.

Key matches: COMB6 E3M4 64/64 (min 997/1000), combined 4-bit 25511/25516,
short schedules 25287 and 24654 of 25600, combined 8-bit 596/600. SUM-only
validity/coverage checks retain the original conclusion: direct validity wins,
and reverse scheduling restores coverage without surpassing direct validity.

## Repository boundaries

GitHub lists only `main` at `6ed61d9`; local `reorg` is retained. The user-supplied
brainstorm and formulation image are tracked unchanged inside the Stage F
experiment on explicit request. The user's untracked root `main` file remains
untouched and excluded. A pre-existing broken app-internal `refs/codex/turn-diffs/checkpoints/`
reference was observed during fetch; no app-internal references were removed.
Legacy ModelSim dynamic execution remains untested (executable unavailable).
