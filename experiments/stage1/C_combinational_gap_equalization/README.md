# Stage 1.C — Combinational Gap Equalization

Six-input combinational networks compare integer and E3M4 equal-gap coefficients.
Frozen variants live in `hardware/`; coefficient sets and the Questa report live
in `results_and_reports/stage1/C_combinational_gap_equalization/`.

```powershell
./sim_scripts/stage1/C_combinational_gap_equalization/run_comb6_diagnostics.ps1
python scripts/stage4/B_fixed_seed_compatibility_validation/run_questa_compatibility_validation.py --preflight
```

The core replay driver selects the exact frozen sources and settle/count values;
the generic diagnostic wrapper alone is not a golden comparison. Fixed E3M4
replay reaches 64/64 top matches at settle=20000 and min=997/1000 hits. It does
not establish cross-seed robustness. Tests: `sim_scripts/stage1/C_combinational_gap_equalization/tb/`.
