# Stage 1.B — Quantized Coefficient Exploration

`hardware/` contains the historical generated FP4/FP8/Q8 and split-carry variants.
These are input candidates, not proof of successful dynamic convergence.
`results_and_reports/stage1/B_quantized_coefficient_exploration/` contains coefficient JSON/Markdown and
the tanh table. The timeline records the absence of dynamic sweep evidence.

```powershell
python scripts/stage1/B_quantized_coefficient_exploration/optimize_fp8_hamiltonians.py --help
./sim_scripts/stage1/B_quantized_coefficient_exploration/run_e4m3_block_timing.ps1
./sim_scripts/stage1/B_quantized_coefficient_exploration/run_integer_block_timing.ps1
```

Run from the repository root. Regeneration is an explicit research operation;
it is not part of fixed-seed replay. Testbenches are under
`sim_scripts/stage1/B_quantized_coefficient_exploration/tb/`; batch results go to this experiment's `runs/`.
