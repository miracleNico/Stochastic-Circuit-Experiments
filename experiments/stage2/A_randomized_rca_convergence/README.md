# Stage 2.A — Randomized RCA Convergence

Owns the frozen 4-bit exhaustive and selected 8-bit repeated-solve hardware.
The benchmark compares direct integer RCA, quantized coefficient scaling,
carry-ordered block scheduling, auxiliary carry-state decoupling, scheduled
auxiliary-carry architecture, and QSAC.

The driver is `scripts/stage2/run_rca_convergence_benchmark.py`; Questa wrappers
and testbenches are in `sim_scripts/stage2/A_randomized_rca_convergence/`.
Published evidence is consolidated under
`results_and_reports/stage2/rca_convergence_benchmark/`.
