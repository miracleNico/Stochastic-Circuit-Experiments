# Stage 4.B — Fixed-Seed Simulator Compatibility Validation

This acceptance suite checks that the ModelSim-to-QuestaSim migration preserves
the committed fixed-seed results. It is not a new scientific experiment and it
does not claim robustness beyond the checked-in seeds.

```powershell
python scripts/stage4/B_fixed_seed_compatibility_validation/run_questa_compatibility_validation.py --preflight
python scripts/stage4/B_fixed_seed_compatibility_validation/run_questa_compatibility_validation.py --suite core --seed-mode replay --simulator questa --update-reports
```

The driver verifies source hashes and seed identifiers, runs the optimizer and
primitive-gate audits plus COMB6 and Stage 2 benchmark cases, compares semantic
report records against exact goldens, and publishes staged evidence only after
every check succeeds. Failure leaves existing reports untouched.
