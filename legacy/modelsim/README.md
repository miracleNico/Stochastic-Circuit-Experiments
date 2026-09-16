# Legacy ModelSim

ModelSim is an explicit legacy target. It is never selected automatically when
QuestaSim is unavailable.

From the repository root, run the archived entry point with a known legacy
installation:

```powershell
.\legacy\modelsim\run_modelsim.ps1 -VsimPath <legacy-vsim.exe>
```

The launcher delegates to the shared isolated runner in `sim_scripts/` and executes
`sim_scripts/stage1/A_primitive_spin_gate_validation/run_gate_regression.do`. The experiment `.do` files remain in `sim_scripts/`
because QuestaSim uses the same `vcom`, `vsim`, and Tcl interfaces.

`modelsim.ini` is an archived repository snapshot only. Neither the Questa
mainline nor the legacy launcher uses it as a fallback: every run copies the
selected vendor installation's own `modelsim.ini` into its isolated build
directory.

The current development host has no legacy ModelSim executable, so dynamic
legacy validation is recorded as "environment not provided". Static `.do`
compatibility remains covered by the shared workflow and does not block Questa
acceptance.
