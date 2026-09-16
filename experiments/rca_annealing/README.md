# RCA annealing, windows and shadow carry — Stage A5–A14

This experiment groups the progression from direct ripple-carry adders to
windowed updates, shared stages, shadow carry and Q3.4 coefficients. Its
experiment-specific generated RTL is in `hardware/`; reusable baseline networks
are referenced from `experiments/gate_baseline/hardware/` without duplication.

```powershell
./sim_scripts/rca_annealing/run_adder4_diagnostics.ps1
./sim_scripts/rca_annealing/run_adder4_shadow1_q34_diagnostics.ps1
```

Python generators: `scripts/rca_annealing/`. Questa launchers and tests:
`sim_scripts/rca_annealing/` and `tb/`. Historical reports and coefficient outputs:
`results_and_reports/rca_annealing/`. These early protocols differ from the later
frozen randomized presentation comparison; historical ModelSim results are not
relabeled as new Questa evidence merely because the files moved.
