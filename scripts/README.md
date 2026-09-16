# Experiment tools

Python tools are grouped by the same identifiers as [experiments](../experiments/README.md).
Run tools from the repository root, for example:

```powershell
python scripts/stage1/A_primitive_spin_gate_validation/generate_hamiltonians.py --help
python scripts/stage3/B_verified_pairwise_optimizer_successor/generic_optimizer.py demo-gate --gate ha
python scripts/stage4/B_fixed_seed_compatibility_validation/run_questa_compatibility_validation.py --preflight
```

Direct-file execution bootstraps the repository import path; Python modules use
`scripts.stageN.<substage>.<module>` imports. No duplicate compatibility scripts
are left in the old flat layout. Generators write experiment-specific VHDL to
`experiments/stageN/<substage>/hardware/`, never to the shared `src/` library.
Analysis outputs belong in the corresponding stage-owned directory under
`results_and_reports/`.

Tests live alongside their tools under `tests/`. Run each suite explicitly:

```powershell
python -m unittest discover -s scripts/stage4/B_fixed_seed_compatibility_validation/tests -v
python -m unittest discover -s scripts/stage3/B_verified_pairwise_optimizer_successor/tests -v
python -m unittest discover -s scripts/stage1/A_primitive_spin_gate_validation/tests -v
```
