# Experiment index

The [timeline](../experiment_timeline.md) is the chronological record. The
repository uses numeric stages and alphabetic substages; each substage owns its
experiment-specific hardware and a README.

| Stage | Substage | Scope |
|---|---|---|
| [Stage 1](stage1/README.md) | 1.A | Primitive spin-gate validation |
|  | 1.B | Quantized coefficient exploration |
|  | 1.C | Combinational gap equalization |
|  | 1.D | Scheduled auxiliary-carry RCA development |
| [Stage 2](stage2/README.md) | 2.A | Randomized RCA convergence benchmark |
|  | 2.B | SUM-conditioned inverse sampling |
|  | 2.C | Schedule reduction and readout validation |
| [Stage 3](stage3/README.md) | 3.A | Historical landscape-optimizer archive |
|  | 3.B | Verified pairwise optimizer successor |
| [Stage 4](stage4/README.md) | 4.A | ModelSim-to-QuestaSim infrastructure migration |
|  | 4.B | Fixed-seed simulator compatibility validation |
|  | 4.C | Repository taxonomy and consolidation |
| [Stage 5](stage5/README.md) | 5.A | Adaptive multibody Hamiltonian research |
|  | 5.B | RTL handoff and readiness gate |

Stage 4.B is not a new scientific experiment. It reruns committed sources and
fixed seeds solely to verify that the simulator migration preserves the accepted
results. Stage 5 contains the later adaptive-multibody research.

Python tools mirror this taxonomy under `scripts/`; Questa wrappers and
testbenches live under `sim_scripts/`; evidence lives under
`results_and_reports/`. Shared reusable VHDL remains in `src/`.
