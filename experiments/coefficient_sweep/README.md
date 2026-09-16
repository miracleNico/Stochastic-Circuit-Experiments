# Coefficient format and split-carry sweep — Stage A3

`hardware/` contains the historical generated FP4/FP8/Q8 and split-carry variants.
These are input candidates, not proof of successful dynamic convergence.
`results_and_reports/coefficient_sweep/` contains coefficient JSON/Markdown and
the tanh table. The timeline records the absence of dynamic sweep evidence.

```powershell
python scripts/coefficient_sweep/optimize_fp8_hamiltonians.py --help
./sim_scripts/coefficient_sweep/run_e4m3_block_timing.ps1
./sim_scripts/coefficient_sweep/run_integer_block_timing.ps1
```

Run from the repository root. Regeneration is an explicit research operation;
it is not part of fixed-seed replay. Testbenches are under
`sim_scripts/coefficient_sweep/tb/`; batch results go to this experiment's `runs/`.
