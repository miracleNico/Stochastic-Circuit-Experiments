# Experiment tools

Python tools are grouped by the same identifiers as [experiments](../experiments/README.md).
Run tools from the repository root, for example:

```powershell
python scripts/gate_baseline/generate_hamiltonians.py --help
python scripts/quantized_landscape_optimizer/generic_optimizer.py demo-gate --gate ha
python scripts/core_reproduction/run_questa_core_reproduction.py --preflight
```

Direct-file execution bootstraps the repository import path; Python modules use
`scripts.<experiment>.<module>` imports. No duplicate compatibility scripts are
left in the old flat layout. Generators write experiment-specific VHDL to
`experiments/<experiment>/hardware/`, never to the shared `src/` library.
Analysis outputs belong in `results_and_reports/<experiment>/`.

Tests live alongside their tools under `tests/`. Run each suite explicitly:

```powershell
python -m unittest discover -s scripts/core_reproduction/tests -v
python -m unittest discover -s scripts/quantized_landscape_optimizer/tests -v
python -m unittest discover -s scripts/gate_baseline/tests -v
```
