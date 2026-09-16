# Invertible Stochastic Computing Gates in VHDL

This project implements small invertible stochastic-computing logic gates in
VHDL, following the spin-gate model described by Onizawa et al.,
*A Design Framework for Invertible Logic*.

The hardware path used here is:

```text
Boolean relation -> Hamiltonian h/J -> spin-gate network -> VHDL RTL
```

Each spin node computes an integer local field:

```text
I_i = h_i + sum(J_ij * m_j) + w_rnd * random_sign
```

where each spin is bipolar:

```text
logic 0 -> m = -1
logic 1 -> m = +1
```

By default `w_rnd = 0`; the stochasticity comes from the p-bit/tanh update.
The emitted spin is sampled from:

```text
P(m_i = +1) = (1 + tanh(I_i)) / 2
```

implemented as an 8-bit fixed-point tanh probability lookup and PRNG compare.
For example, if an AND output node sees `I_Y = 2`, the measured probability of
`Y=1` should be close to `(1 + tanh(2)) / 2 = 0.982`; the 8-bit table uses
`251/256 = 0.9805`, not exactly `1.0`.

A saturated up/down counter is still kept as an observable internal stochastic
tanh-style state, but it no longer deterministically forces the output spin.

The gate wrappers update one free node per clock phase while continuously
forcing clamped nodes. This avoids symmetric parallel-update oscillations in
the small XOR/half-adder network and is closer to the asynchronous update style
used by Boltzmann-machine p-bit systems.

## Simulation And Migration-Validation Workflow

QuestaSim 2024.1 is the default VHDL simulator. The migration keeps the
existing `vcom`, `vsim`, and `.do` flow; `qrun` is not used. A normal smoke run
from the repository root is:

```powershell
.\sim_scripts\stage1\A_primitive_spin_gate_validation\run_questa.ps1
```

Every experiment wrapper defaults to Questa and accepts the common tool,
license, build, waveform, and timeout arguments described in
[`sim_scripts/README.md`](sim_scripts/README.md). The explicit ModelSim launcher and archived
repository-local configuration now live under
[`legacy/modelsim/`](legacy/modelsim/README.md). Runs are isolated under
`results_and_reports/stageN/<owner>/runs/`; they do not use the archived `legacy/modelsim/modelsim.ini` or
share a `work` library.

The fixed-seed simulator compatibility entry point is:

```powershell
python .\scripts\stage4\B_fixed_seed_compatibility_validation\run_questa_compatibility_validation.py `
  --suite core `
  --seed-mode replay `
  --simulator questa `
  --update-reports
```

Compatibility validation checks the committed generated VHDL and seed identities, stages all
new evidence, and replaces the original reports only after every semantic
golden check passes. Use `--preflight` to validate inputs, tool identity, and
entry points without running simulations or modifying reports. The complete
25-run migration validation passed on 2026-09-16 with QuestaSim 2024.1, and the
RCA benchmark and COMB6 reports were then replaced transactionally. This is a
fixed-seed result for the committed generated VHDL, not a cross-seed robustness
claim.

The frozen integer Scheduled auxiliary-carry architecture RCA golden predates the testbench's clamp-prime
cycle and post-edge sample delay. The core driver marks only
`scheduled_auxiliary_carry_integer4` with `-LegacyReplayTiming` so Questa can match that
historical evidence exactly; the Q3.4 main run and short schedules use the
corrected timing, which is also the ordinary wrapper default. This mixed
protocol is recorded in the published manifest and run summary.

ModelSim is retained only as an explicit legacy target through
`legacy/modelsim/run_modelsim.ps1` or the shared runner's explicit
`-Simulator ModelSim` compatibility option. A missing Questa installation never
causes an automatic fallback to ModelSim. Verilator+cocotb remains a future
parallel workflow; this migration does not add it, CI runners, or a `qrun`
flow.

The current development host does not provide a legacy ModelSim executable, so
legacy acceptance is limited to static `.do` compatibility. Dynamic ModelSim
validation is marked "environment not provided" and does not block Questa.

See [`experiment_timeline.md`](experiment_timeline.md) for the chronological
experiment record, optimizer provenance, fixed-seed results, and local branch
consolidation notes.

## Current RCA Convergence Benchmark

The current main result is the RCA timing/shadow-node study in:

```text
results_and_reports/stage2/rca_convergence_benchmark/report.md
```

It is designed as a concise benchmark artifact for the pseudo-time-dependent
adder problem. The report includes:

- restored primitive-gate visualizations for AND, OR, NAND, NOR, HA/XOR, XNOR,
  and FA;
- exhaustive fixed-seed tests for the 4-bit RCA;
- a separate clamp SUM-only inverse-distribution test for the 4-bit RCA;
- non-exhaustive repeated-solve checks for selected 8-bit RCA vectors;
- ablations for quantized coefficient scaling, carry-ordered block scheduling, and auxiliary carry-state decoupling separately;
- final comparison against the combined quantized scheduled auxiliary-carry architecture design;
- a separate forward-only window-reduction check for shortened Q3.4 schedules.

Replay the committed seed set with Questa and publish only fully validated
results:

```powershell
python .\scripts\stage4\B_fixed_seed_compatibility_validation\run_questa_compatibility_validation.py `
  --suite core `
  --seed-mode replay `
  --simulator questa `
  --update-reports
```

The replay driver does not generate a new random salt or overwrite committed
generated VHDL. It checks source hashes, runs Questa, parses stable VHDL report
records into CSV, checks exact integer goldens and derived values, and stages
SVG figures under `results_and_reports/stage4/B_fixed_seed_compatibility_validation/runs/` before publication. Curated report artifacts
are organized as:

```text
results_and_reports/stage2/rca_convergence_benchmark/data/     Parsed CSV and JSON data
results_and_reports/stage2/rca_convergence_benchmark/figures/  SVG/PNG visualizations
results_and_reports/stage2/rca_convergence_benchmark/traces/   Simulator transcripts used as evidence
```

The old random-regeneration driver is deliberately guarded. It refuses to run
unless both `--legacy-regenerate` and `--replace-report` are supplied; it is not
part of the fixed replay workflow.

Latest 4-bit exhaustive repeated-solve results under the main 40-cycle
comparison protocol:

| Test | Forward success | Constrained inverse |
|---|---:|---:|
| Direct integer baseline | 85.69% | n/a |
| Quantized coefficient scaling only, Q3.4 direct weights | 70.53% | n/a |
| Carry-ordered block scheduling only, sequential window | 46.79% | 54.79% |
| Auxiliary carry-state decoupling only, parallel shadow node | 65.36% | 74.46% |
| Scheduled auxiliary-carry architecture, integer shadow/window | 85.94% | 89.01% |
| Quantized scheduled auxiliary-carry architecture, Q3.4 shadow/window | 99.65% | 99.67% |

The shortened Q3.4 schedules are reported separately as forward-only timing
experiments. The corrected `10,8,16,6` schedule reaches `98.78%`, and the
shortest physically justified schedule tested here, `2,2,4,2`, reaches
`96.30%`. These are not used as the constrained-inverse hyperparameter setting.

The key interpretation is that quantized coefficient scaling does not work by itself: Q3.4 increases
the local HA/FA field magnitude and saturates the tanh update, but it does not
fix carry arrival time. A downstream FA can confidently collapse around a wrong
early carry. Q3.4 becomes useful only after carry-ordered block scheduling and auxiliary carry-state decoupling provide timing
isolation and a directional shadow carry boundary.

Clamp SUM-only inverse sampling is intentionally reported separately because it
tests distribution quality with both A and B free, not recovery of one missing
operand. Current 1000-trial-per-SUM results remain mixed:

| Test | Valid rate | Valid-pair coverage |
|---|---:|---:|
| Direct integer baseline | 85.95% | 100.00% |
| Scheduled auxiliary-carry architecture, integer shadow/window | 68.60% | 100.00% |
| Quantized scheduled auxiliary-carry architecture, Q3.4 shadow/window | 77.25% | 25.00% |
| Quantized scheduled auxiliary-carry architecture, Q3.4 reverse-order shadow/window | 76.70% | 75.78% |
| Auxiliary carry-state decoupling only, parallel shadow node | 62.95% | 100.00% |
| Quantized auxiliary-carry decoupling, Q3.4 parallel shadow | 76.83% | 64.45% |

The direct integer baseline is strongest on this SUM-only metric, while the
shadow/window ideas mainly help the timing-dependent forward and constrained
inverse tasks. Reverse-order SUM-only annealing improves Q3.4 valid-pair
coverage and removes zero-valid target sums, but it still does not beat the
direct baseline. The report frames this as future energy-distribution tuning,
likely using fixed-point or floating-point weights rather than plain integers.

## Implemented Gates

Two hand-written wrappers are kept for continuity:

- `src/inv_and_gate.vhd`
- `src/inv_xor_gate.vhd`

The expanded library is generated from coefficient definitions:

- `AND`, `OR`, `NAND`, `NOR`
- `XOR` / half-adder, `XNOR`
- `FA`
- `ADDER8_RIPPLE`
- `BITCOUNT8`

Generated entities all use this vector interface:

```vhdl
clk, rst, enable : in  std_logic;
clamp_en         : in  std_logic_vector(N-1 downto 0);
clamp_value      : in  std_logic_vector(N-1 downto 0);
spins            : out std_logic_vector(N-1 downto 0);
```

### Invertible AND

Node order: `A, B, Y`

```text
h = [ +1, +1, -2 ]

J = [  0, -1, +2
      -1,  0, +2
      +2, +2,  0 ]
```

Forward mode clamps `A` and `B`, then allows `Y` to settle. Reverse mode clamps
`Y` and allows `A` and `B` to settle.

### Invertible XOR

Files:

- `src/inv_xor_gate.vhd`
- `sim_scripts/stage1/A_primitive_spin_gate_validation/tb/tb_inv_xor_gate.vhd`

A pure three-node pairwise Ising XOR requires a three-body parity term, so this
project implements XOR as the sum output of a four-node invertible half-adder.
The auxiliary node is exposed as `aux_c`.

Node order: `A, B, Y, aux_c`

```text
h = [ +1, +1, -1, -2 ]

J_AB = -1
J_AY = +1
J_AC = +2
J_BY = +1
J_BC = +2
J_YC = -2
```

The low-energy states are:

```text
A B Y C
0 0 0 0
0 1 1 0
1 0 1 0
1 1 0 1
```

So `Y = A xor B` and `aux_c = A and B`.

## Generated Hamiltonians

Run the generator after editing coefficient definitions:

```powershell
python .\scripts\stage1\A_primitive_spin_gate_validation\generate_hamiltonians.py
```

It writes:

```text
experiments/stage1/A_primitive_spin_gate_validation/hardware/generated_networks.vhd
results_and_reports/stage1/A_primitive_spin_gate_validation/hamiltonians.json
results_and_reports/stage1/A_primitive_spin_gate_validation/hamiltonians.md
```

The default HA/FA block scales are `1`; optional `--ha-scale` and `--fa-scale`
arguments can be used later for energy-gap experiments.

For fixed-point coefficient experiments, the generator can emit scaled integer
weights with an explicit field radix. For example, this emits FP4 coefficients
whose physical Hamiltonian weights are half of the base library:

```powershell
python .\scripts\stage1\A_primitive_spin_gate_validation\generate_hamiltonians.py `
  --weight-frac-bits 4 `
  --weight-scale 1/2 `
  --vhdl experiments\stage1\B_quantized_coefficient_exploration\hardware\generated_networks_fp4_half.vhd
```

The default generated RTL remains integer-weighted (`--weight-frac-bits 0`,
`--weight-scale 1`).

For an FP8 minimum-gap experiment, use one FP8 LSB of physical coefficient
weight:

```powershell
python .\scripts\stage1\A_primitive_spin_gate_validation\generate_hamiltonians.py `
  --weight-frac-bits 8 `
  --weight-scale 1/256 `
  --vhdl experiments\stage1\B_quantized_coefficient_exploration\hardware\generated_networks_fp8_mingap.vhd
```

Because `RND_WEIGHT` is encoded in the same fixed-point field units, a noise
weight of `16` in FP8 corresponds to a noise weight of `1` in FP4.
The VHDL stores Q8 weights as integers with an implied `/256` scale; for
example, an emitted coefficient of `16` is physical `0.0625`.
The stochastic tanh sampler uses 16-bit probability thresholds and compares
against a 16-bit PRNG slice, so small inter-block fields are not rounded onto
an 8-bit probability grid.

The Q8 optimizer builds a mathematical MILP instead of scaling by hand. It
maximizes each HA/FA block's valid-vs-invalid gate gap under coefficient bounds,
then minimizes carry-boundary coefficient strength at that optimum. Because the
shared-carry topology cannot decouple gate and inter-block gaps, the optimizer
also emits an experimental split-carry adder with weak Q8 equality links between
blocks:

```powershell
python .\scripts\stage1\B_quantized_coefficient_exploration\optimize_fp8_hamiltonians.py --link-q8 16
python .\scripts\stage1\B_quantized_coefficient_exploration\optimize_fp8_hamiltonians.py `
  --coefficient-format fp8-e4m3 `
  --coeff-max-value 448 `
  --link-value 1/16 `
  --vhdl experiments\stage1\B_quantized_coefficient_exploration\hardware\generated_networks_fp8_e4m3_optimized_split.vhd `
  --report reports\optimized_fp8_e4m3_hamiltonians.json
python .\scripts\stage1\B_quantized_coefficient_exploration\optimize_fp8_hamiltonians.py `
  --coefficient-format fp8-e3m4 `
  --fp8-bias 1 `
  --coeff-max-value 100 `
  --link-value 1/16 `
  --vhdl experiments\stage1\B_quantized_coefficient_exploration\hardware\generated_networks_fp8_e3m4_b1_gap100_link_1_16.vhd `
  --report reports\optimized_fp8_e3m4_b1_gap100_link_1_16.json
python .\scripts\stage1\B_quantized_coefficient_exploration\optimize_fp8_hamiltonians.py `
  --coefficient-format fp8-e2m5 `
  --fp8-bias -3 `
  --coeff-max-value 100 `
  --link-value 1/2 `
  --vhdl experiments\stage1\B_quantized_coefficient_exploration\hardware\generated_networks_fp8_e2m5_bminus3_gap100_link_1_2.vhd `
  --report reports\optimized_fp8_e2m5_bminus3_gap100_link_1_2.json
```

This writes `results_and_reports/stage1/B_quantized_coefficient_exploration/optimized_fp8_hamiltonians.json` and
`experiments/stage1/B_quantized_coefficient_exploration/hardware/generated_networks_fp8_optimized_split.vhd`.

For exact coefficient checks:

```powershell
python .\scripts\stage1\A_primitive_spin_gate_validation\verify_hamiltonians.py
```

This exhaustively verifies every 3-, 4-, and 5-node block, all `4096`
8-input bitcount states, and all `65536` valid 8-bit ripple-adder placements.

## 8-Bit Adder And Bitcount Note

The paper uses bitcount mainly to reduce multiplier node count by removing
vertical internal adder connections. For adders, the table's direct
`n-bit adder = 3n + 1` row is already the minimum-node direct Hamiltonian form.

This project intentionally uses an HA/FA-composed 8-bit ripple adder so the
block coefficients and block scaling remain easy to inspect. That version uses
`32` nodes:

```text
[a0..a7, b0..b7, s0..s7, c1..c8]
```

instead of the direct theoretical `25`-node form.

## Project Layout

```text
experiments/stageN/<substage>/README.md   Purpose and experiment boundary
experiments/stageN/<substage>/hardware/   Experiment-specific generated VHDL
results_and_reports/stageN/<owner>/       Curated evidence, figures and reports
results_and_reports/stageN/<owner>/runs/  Ignored isolated simulator outputs
scripts/stageN/<substage>/                Python generators, analysis and tests
sim_scripts/stageN/<substage>/            Questa PowerShell and .do launchers
sim_scripts/stageN/<substage>/tb/         Experiment VHDL testbenches
sim_scripts/Simulator.psm1          Shared runner; Invoke-Simulation.ps1 CLI
sim_scripts/stage4/A_questa_migration/tests/                  Runner unit tests and failure fixtures
src/                                Shared primitive VHDL only
legacy/modelsim/                    Explicit legacy launcher and configuration
experiment_timeline.md              Chronology and evidence provenance
```

Regenerable Python bytecode, isolated simulator work directories, and local
scratch sweep directories are ignored by `.gitignore`. Curated evidence remains
under `results_and_reports/`. See the [experiment index](experiments/README.md)
for the full Stage 1–5 mapping. Stages 2.A–2.C share the
`rca_convergence_benchmark` because they share frozen RTL and an integrated
report. Testbenches are retained, but the old top-level `tb/` is folded into
each experiment's `sim_scripts/stageN/<substage>/tb/`.
Old flat script paths are intentionally replaced by the organized paths above.

The reorganization passed the 25-run fixed-seed Questa compatibility validation, 47 Python
tests, runner/failure tests and a fresh-checkout hash check. See the
[validation record](results_and_reports/stage4/B_fixed_seed_compatibility_validation/reorg_validation.md).
The optional research environment is local `.venv`; its dependencies and setup
are documented in the [multibody experiment](experiments/stage5/README.md).

## Run Simulation

From the repository root, run the default primitive-gate regression with
Questa:

```powershell
.\sim_scripts\stage1\A_primitive_spin_gate_validation\run_questa.ps1
```

The stable low-level interface accepts any migrated `.do` file:

```powershell
.\sim_scripts\Invoke-Simulation.ps1 `
  -DoFile .\sim_scripts\stage1\C_combinational_gap_equalization\run_comb6_diagnostics.do `
  -Simulator Questa `
  -WaveMode None `
  -TimeoutSeconds 3600
```

Use `-VsimPath` to choose an executable explicitly and either `-LicenseFile`
or `-LicenseServer` to override license discovery. Details, all common wrapper
arguments, run-directory contents, and exit codes are in
[`sim_scripts/README.md`](sim_scripts/README.md).

The testbenches verify:

- forward AND truth table
- reverse AND with `Y=1` and `Y=0`
- forward XOR truth table
- reverse XOR parity behavior
- generated forward/reverse checks for AND, OR, NAND, NOR, XOR, XNOR
- generated forward checks for FA
- diagnostic 8-bit adder and 8-input bitcount probability samples

The small-gate checks are hard assertions. The generated 8-bit adder and
bitcount bench reports sampled probabilities because auxiliary-node landscapes
can have local minima; exact structural correctness is covered by
`scripts/stage1/A_primitive_spin_gate_validation/verify_hamiltonians.py`.

For targeted 8-bit synthesized-adder convergence debugging:

```powershell
.\sim_scripts\stage1\D_scheduled_auxiliary_carry_rca\run_adder8_diagnostics.ps1
.\sim_scripts\stage1\D_scheduled_auxiliary_carry_rca\run_adder8_diagnostics.ps1 `
  -GeneratedNetworks "experiments/stage1/B_quantized_coefficient_exploration/hardware/generated_networks_fp4_half.vhd" `
  -AdderRndWeight 1
.\sim_scripts\stage1\B_quantized_coefficient_exploration\run_adder8_split_diagnostics.ps1
```

The diagnostic bench reports output-sum histograms and per-sum/per-carry hit
counts for hard carry-chain cases.

For migration acceptance of the RCA benchmark, use the fixed-seed compatibility entry point:

```powershell
python .\scripts\stage4\B_fixed_seed_compatibility_validation\run_questa_compatibility_validation.py `
  --suite core `
  --seed-mode replay `
  --simulator questa `
  --update-reports
```

Individual wrappers used by the replay include:

```text
sim_scripts/stage2/A_randomized_rca_convergence/run_adder4_direct_randomized_exhaustive.ps1
sim_scripts/stage2/B_sum_conditioned_inverse_sampling/run_adder4_direct_sum_randomized_distribution.ps1
sim_scripts/stage2/A_randomized_rca_convergence/run_adder4_windowed_randomized_exhaustive.ps1
sim_scripts/stage2/A_randomized_rca_convergence/run_adder4_shadow1_parallel_randomized_exhaustive.ps1
sim_scripts/stage2/A_randomized_rca_convergence/run_adder4_shadow1_randomized_exhaustive.ps1
sim_scripts/stage2/B_sum_conditioned_inverse_sampling/run_adder4_shadow1_sum_randomized_distribution.ps1
sim_scripts/stage2/A_randomized_rca_convergence/run_adder8_direct_repeated_solve.ps1
sim_scripts/stage2/A_randomized_rca_convergence/run_adder8_shadow1_repeated_solve.ps1
```

The 4-bit benchmark tests are exhaustive over all `A,B` pairs and replay the
committed deterministic seed streams. The SUM-only test is exhaustive over
SUM=0..30 and records the sampled valid-pair distribution. The 8-bit
benchmark tests are selected-vector repeated solves, not exhaustive. This
replay establishes reproducibility for the committed seeds only; it is not a
cross-seed robustness claim.

## Open AND Waveform

To open Questa in GUI mode with an AND-gate wave window:

```powershell
.\sim_scripts\stage1\A_primitive_spin_gate_validation\open_and_wave.ps1
```

The script compiles the AND design, runs `tb_inv_and_gate` for 20 us, and adds
the clamp controls, spins, local fields, update phase, counters, and PRNG bits
to the wave window. It defaults to `-WaveMode All` and keeps the isolated work
library for interactive inspection.

## Python Trace Visualization

For a cleaner sampled view, run the trace flow:

```powershell
.\sim_scripts\stage1\A_primitive_spin_gate_validation\run_and_trace.ps1
```

This runs `tb_inv_and_trace`, then keeps both the raw CSV and every derived
artifact in the same isolated `results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/` directory. The derived
files are:

```text
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/and_trace.png
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/and_trace_summary.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/and_state_probabilities.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/and_ab_probabilities.csv
```

The trace covers all four forward AND cases plus reverse operation with
`Y=0` and `Y=1`.

For XOR:

```powershell
.\sim_scripts\stage1\A_primitive_spin_gate_validation\run_xor_trace.ps1
```

This produces:

```text
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/xor_trace.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/xor_trace.png
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/xor_trace_summary.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/xor_state_probabilities.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../raw/xor_ab_probabilities.csv
```

To regenerate both trace reports and the exact small-gate probability report:

```powershell
.\sim_scripts\stage1\A_primitive_spin_gate_validation\run_all_traces.ps1
```

This also writes exact small-gate Hamiltonian probability reports for
AND/OR/NAND/NOR/XOR/XNOR:

```text
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../run_all_traces/.../raw/generated_gate_probability_summary.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../run_all_traces/.../raw/generated_gate_state_probabilities.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../run_all_traces/.../raw/generated_gate_ab_probabilities.csv
results_and_reports/stage1/A_primitive_spin_gate_validation/runs/.../run_all_traces/.../raw/generated_gate_probabilities.png
```

For clamped-output runs, the `*_ab_probabilities.csv` files are the most useful
view. For example, AND with `Y=0` should distribute probability across
`AB=00`, `AB=01`, and `AB=10`, with each near one third.

The current benchmark gate visualizations are staged by
`scripts/stage4/B_fixed_seed_compatibility_validation/run_questa_compatibility_validation.py` and, after all goldens pass, published
to:

```text
results_and_reports/stage2/rca_convergence_benchmark/figures/gate_energy_landscape.svg
results_and_reports/stage2/rca_convergence_benchmark/figures/gate_reverse_distributions.svg
results_and_reports/stage2/rca_convergence_benchmark/data/gate_energy_landscape.csv
results_and_reports/stage2/rca_convergence_benchmark/data/gate_reverse_distributions.csv
```

## Notes

This is a compact RTL implementation of the paper's stochastic spin-gate idea,
not a transistor-level model. The design is intentionally small and readable:
integer Hamiltonian coefficients are hardwired, stochasticity comes from one
xorshift PRNG per node, clamping is a mux around each node, and the nonlinear
block is a fixed-point stochastic tanh sampler.
