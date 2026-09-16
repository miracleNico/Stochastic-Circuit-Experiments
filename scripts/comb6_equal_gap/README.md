# COMB6 tooling

The frozen COMB6 sources need no regeneration during replay. Their seeds and
SHA-256 values are checked by `../core_reproduction/run_questa_core_reproduction.py`.
The general coefficient generator lives in `../gate_baseline/generate_hamiltonians.py`;
do not duplicate it here. Experiment inputs: `../../experiments/comb6_equal_gap/hardware/`.
