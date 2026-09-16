# Questa core reproduction — Stage G

This is an integration experiment, not a separate hardware design. It consumes
the frozen inputs owned by the gate, COMB6, presentation and optimizer experiments.

```powershell
python scripts/core_reproduction/run_questa_core_reproduction.py --preflight
python scripts/core_reproduction/run_questa_core_reproduction.py --suite core --seed-mode replay --simulator questa --update-reports
```

The driver and golden specification are in `scripts/core_reproduction/`.
Shared simulation infrastructure and failure tests are in `sim_scripts/` and
`sim_scripts/tests/`. Full-suite staging and run metadata go to
`results_and_reports/core_reproduction/runs/`. Publication updates each owning
experiment's report only after every exact golden and conclusion check passes.

This proves the committed seed set on Questa, not cross-seed robustness.
The separate Stage F RTL research remains stopped at missing Stage3 artifacts.
