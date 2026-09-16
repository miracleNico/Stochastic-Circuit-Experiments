# Numeric-stage reorganization validation — 2026-09-16

Base: `6ed61d9` on `main`; implementation branch: `reorg`. This is a layout and
workflow validation, not a change to Hamiltonians, frozen seeds or goldens.

## Completed checks

- 365 tracked paths were relocated into the numeric-stage/alphabetic-substage
  hierarchy. All 147 moved VHDL and published trace files are byte-identical to
  the pre-move working-tree snapshot.
- All relocated Python files compile; all PowerShell files parse.
- All 47 Python tests (29 compatibility/layout, 16 optimizer, 2 plot fallback) pass; layout and
  report-publication tests cover new paths and preservation of run/scratch data.
- Fake-vsim runner suite passes (priority, identity, licenses, isolation,
  timeout, stable exit codes and trace failure propagation).
- Real Questa failure smoke passes: compile=50, elaboration=51, assertion=52.
- All 11 frozen core source SHA-256 and seed signatures pass preflight.
- A fresh index export preserves the pinned VHDL line endings; all 11 frozen
  source hashes and all 29 compatibility/layout tests pass at the new paths.
- Primitive Hamiltonian verifier passes, including all 65,536 valid 8-bit sums.
- AND/XOR trace aggregation, CSV/PNG outputs and Top-mode WLF pass at
  `../../stage1/A_primitive_spin_gate_validation/runs/questa/run_all_traces/reorg-traces-20260916/`.
- E4M3 coefficient-sweep path smoke passes, settle=20/count=10; this is a path
  smoke only, not a rerun of historical sweep results.
- Matplotlib 3.11.2 and Numba 0.67.0 installed in ignored `.venv`; all seven
  Stage 5.A modules import, `unit-check` and `pip check` pass. Gurobi optimization
  and reconstruction of the missing Stage 5.A solution were not run.

## Stage 4.B simulator compatibility validation

Run ID: `stage-taxonomy-final`; QuestaSim 2024.1; fixed-seed replay;
`--update-reports` omitted to preserve the published evidence while validating
the new paths. **All 25 simulations and all original exact golden/conclusion
checks passed.** The machine-readable
[compatibility summary](stage_taxonomy_compatibility_summary.json) records
parameters, source hashes, timing and counts. It identifies the pre-commit
`443b3c0` base with `git_dirty=true`, because validation ran before this taxonomy
commit. The older [pre-taxonomy summary](reorg_reproduction_summary.json) is
retained as historical migration evidence.

Key matches: COMB6 E3M4 64/64 (min 997/1000), combined 4-bit 25511/25516,
short schedules 25287 and 24654 of 25600, combined 8-bit 596/600. SUM-only
validity/coverage checks retain the original conclusion: direct validity wins,
and reverse scheduling restores coverage without surpassing direct validity.

## Repository boundaries

The taxonomy is Stage 1 component/architecture, Stage 2 RCA benchmark, Stage 3
optimizer history/successor, Stage 4 simulator migration and repository
engineering, and Stage 5 adaptive multibody research. Stage 4.B is explicitly a
simulator-migration check rather than a new scientific experiment. The
user-supplied brainstorm and formulation image are tracked under Stage 5.A. The
user's untracked root `main` file remains untouched and excluded. Legacy ModelSim
dynamic execution remains untested (executable unavailable).
