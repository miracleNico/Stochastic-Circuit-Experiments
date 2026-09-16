# COMB6 tooling

The frozen COMB6 sources need no regeneration during replay. Their seeds and
SHA-256 values are checked by
`../../stage4/B_fixed_seed_compatibility_validation/run_questa_compatibility_validation.py`.
The general coefficient generator lives in
`../A_primitive_spin_gate_validation/generate_hamiltonians.py`; do not duplicate
it here. Experiment inputs:
`../../../experiments/stage1/C_combinational_gap_equalization/hardware/`.
