# COMB6 equal-gap study — Stage A4

Six-input combinational networks compare integer and E3M4 equal-gap coefficients.
Frozen variants live in `hardware/`; coefficient sets and the Questa report live
in `results_and_reports/comb6_equal_gap/`.

```powershell
./sim_scripts/comb6_equal_gap/run_comb6_diagnostics.ps1
python scripts/core_reproduction/run_questa_core_reproduction.py --preflight
```

The core replay driver selects the exact frozen sources and settle/count values;
the generic diagnostic wrapper alone is not a golden comparison. Fixed E3M4
replay reaches 64/64 top matches at settle=20000 and min=997/1000 hits. It does
not establish cross-seed robustness. Tests: `sim_scripts/comb6_equal_gap/tb/`.
