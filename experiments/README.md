# Experiment index

The [timeline](../experiment_timeline.md) remains the chronological record.
Directories group related stages by experiment, rather than duplicating hardware
and evidence for every historical milestone. All commands below and in experiment
READMEs run from the repository root.

| Experiment | Timeline stages | Scope |
|---|---|---|
| [gate_baseline](gate_baseline/README.md) | A1–A2 | Primitive gates, generated Hamiltonians, probability traces |
| [coefficient_sweep](coefficient_sweep/README.md) | A3 | FP4/FP8/Q8 coefficient and split-carry variants |
| [comb6_equal_gap](comb6_equal_gap/README.md) | A4 | Six-input combinational equal-gap comparison |
| [rca_annealing](rca_annealing/README.md) | A5–A14 | RCA scheduling, windows, shadow carry, Q3.4 exploration |
| [presentation_rca](presentation_rca/README.md) | B–D | Frozen 4/8-bit comparison, SUM-only study, short schedules |
| [quantized_landscape_optimizer](quantized_landscape_optimizer/README.md) | E, G | Historical missing optimizer and reconstructed generic successor |
| [multibody_hamiltonian_6bit_adaptive_qp](multibody_hamiltonian_6bit_adaptive_qp/README.md) | F | Adaptive multibody Hamiltonian research |
| [core_reproduction](core_reproduction/README.md) | G | Cross-experiment fixed-seed Questa acceptance |

Each experiment owns its design description, specs and experiment-specific
`hardware/` here. Python tools live in `scripts/<experiment>/`, Questa scripts
and VHDL testbenches in `sim_scripts/<experiment>/` and its `tb/`, and evidence
in `results_and_reports/<experiment>/`. Software-only experiments do not need an
empty hardware directory. Shared reusable VHDL stays in `src/`.
