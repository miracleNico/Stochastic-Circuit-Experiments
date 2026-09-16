# Frozen RCA presentation study — Stages B–D

Stages B (main comparison), C (SUM-only inverse distribution) and D (short
windows) share one frozen seed set and an integrated report. They stay together
to avoid splitting the manifest or duplicating generated RTL.

`hardware/` contains the nine frozen generated sources. Python analysis and the
guarded regeneration driver live in `scripts/presentation_rca/`. Questa wrappers
and VHDL tests live in `sim_scripts/presentation_rca/` and `tb/`. The curated
report, data, figures and raw evidence live in `results_and_reports/presentation_rca/`.

```powershell
python scripts/core_reproduction/run_questa_core_reproduction.py --preflight
python scripts/core_reproduction/run_questa_core_reproduction.py --suite core --seed-mode replay --simulator questa --update-reports
```

Replay never regenerates seeds or overwrites hardware. The historical random
regeneration driver requires explicit destructive-regeneration flags. Core
acceptance checks exact counts, including combined 4-bit 25511/25516 and
combined 8-bit 596/600. SUM-only remains weaker than the direct baseline.
