# Stage 2 — RCA Convergence Benchmark

Stage 2 turns the Stage 1.D architecture into a frozen, fixed-seed benchmark:

- [2.A Randomized RCA Convergence](A_randomized_rca_convergence/README.md)
- [2.B SUM-Conditioned Inverse Sampling](B_sum_conditioned_inverse_sampling/README.md)
- [2.C Schedule Reduction and Readout Validation](C_schedule_reduction_and_readout_validation/README.md)

The former `presentation_rca` label is retired. The report is now the
`rca_convergence_benchmark`, and the former numbered ideas are named by their
mechanisms: quantized coefficient scaling, carry-ordered block scheduling,
auxiliary carry-state decoupling, scheduled auxiliary-carry architecture, and
quantized scheduled auxiliary-carry architecture (QSAC).

Stage 4.B replays these frozen inputs only to validate the QuestaSim migration.
It does not add a new scientific result.
