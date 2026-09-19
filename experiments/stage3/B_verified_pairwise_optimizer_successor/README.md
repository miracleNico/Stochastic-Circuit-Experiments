# Stage 3.B — Verified Pairwise Optimizer Successor

This is the runnable successor to the missing historical optimizer. It learns a
pairwise Ising Hamiltonian with flat valid-state energy, a configured invalid
gap, smoothed invalid-neighbor energies, and verified descent cuts.

- Specification: `specs/ha_demo.json`
- Python implementation and tests:
  `scripts/stage3/B_verified_pairwise_optimizer_successor/`
- Questa static energy audit:
  `sim_scripts/stage3/B_verified_pairwise_optimizer_successor/`
- Evidence: `results_and_reports/stage3/B_verified_pairwise_optimizer_successor/`

The detailed formulation, CLI, and historical provenance are retained in the
[Stage 3 overview](../README.md).
