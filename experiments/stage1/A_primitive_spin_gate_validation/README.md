# Stage 1.A — Primitive Spin-Gate Validation

Generated AND/OR/NAND/NOR/XOR/XNOR/HA/FA networks establish the invertible
spin-gate baseline. `hardware/generated_networks.vhd` also contains the composed
baseline networks reused by later experiments; consumers reference this one copy.
Shared spin nodes, PRNG, package and hand-written gate primitives live in `src/`.

From the repository root:

```powershell
python scripts/stage1/A_primitive_spin_gate_validation/verify_hamiltonians.py
./sim_scripts/stage1/A_primitive_spin_gate_validation/run_questa.ps1
./sim_scripts/stage1/A_primitive_spin_gate_validation/run_all_traces.ps1
./sim_scripts/stage1/A_primitive_spin_gate_validation/open_and_wave.ps1
```

Generators and plotters: `scripts/stage1/A_primitive_spin_gate_validation/`. Questa scripts and testbenches:
`sim_scripts/stage1/A_primitive_spin_gate_validation/` and `tb/`. Coefficients and new run artifacts:
`results_and_reports/stage1/A_primitive_spin_gate_validation/` (isolated runs under `runs/`). Historical
reports not rerun with Questa retain their ModelSim provenance.
