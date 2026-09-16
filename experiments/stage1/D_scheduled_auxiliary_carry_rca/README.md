# Stage 1.D — Scheduled Auxiliary-Carry RCA Development

This experiment groups the progression from direct ripple-carry adders to
windowed updates, shared stages, shadow carry and Q3.4 coefficients. Its
experiment-specific generated RTL is in `hardware/`; reusable baseline networks
are referenced from `experiments/stage1/A_primitive_spin_gate_validation/hardware/` without duplication.

```powershell
./sim_scripts/stage1/D_scheduled_auxiliary_carry_rca/run_adder4_diagnostics.ps1
./sim_scripts/stage1/D_scheduled_auxiliary_carry_rca/run_adder4_shadow1_q34_diagnostics.ps1
```

Python generators: `scripts/stage1/D_scheduled_auxiliary_carry_rca/`. Questa launchers and tests:
`sim_scripts/stage1/D_scheduled_auxiliary_carry_rca/` and `tb/`. Historical reports and coefficient outputs:
`results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/`. These early protocols differ from the later
frozen randomized convergence benchmark; historical ModelSim results are not
relabeled as new Questa evidence merely because the files moved.
