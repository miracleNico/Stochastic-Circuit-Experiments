# Stage 4.A — QuestaSim Migration

QuestaSim 2024.1 is the default simulator. Shared runner code remains at the
root of `sim_scripts/`; runner and failure-classification tests live in
`sim_scripts/stage4/A_questa_migration/tests/`. ModelSim is retained explicitly
under `legacy/modelsim/` and is never selected as a silent fallback.
