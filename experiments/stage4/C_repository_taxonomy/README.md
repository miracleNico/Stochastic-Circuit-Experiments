# Stage 4.C — Repository Taxonomy and Consolidation

Defines the numeric-stage/alphabetic-substage hierarchy and mirrors it across
`experiments/`, `scripts/`, `sim_scripts/`, and `results_and_reports/` while
keeping reusable VHDL in `src/` and legacy ModelSim assets in `legacy/`.

Moves must preserve frozen generated VHDL and published trace bytes. Historical
embedded paths in immutable evidence are provenance, not active entry points.
