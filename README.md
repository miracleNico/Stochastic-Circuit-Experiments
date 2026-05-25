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

## Current Presentation Workflow

The current main result is the RCA timing/shadow-node study in:

```text
reports/presentation_8bit_rca/report.md
```

It is designed as a clean presentation artifact for the pseudo-time-dependent
adder problem. The report includes:

- restored primitive-gate visualizations for AND, OR, NAND, NOR, HA/XOR, XNOR,
  and FA;
- exhaustive randomized ModelSim tests for the 4-bit RCA;
- a separate clamp SUM-only inverse-distribution test for the 4-bit RCA;
- non-exhaustive repeated-solve ModelSim checks for selected 8-bit RCA vectors;
- ablations for idea 2, idea 3, and idea 4 separately;
- final comparison against the combined idea 2+3+4 design;
- a separate forward-only window-reduction check for shortened Q3.4 schedules.

Rebuild the full presentation dataset from fresh OS-random seed salts:

```powershell
cd "C:\Projects\stochastic_circuits"
python .\scripts\run_presentation_rca_experiments.py
```

The driver regenerates presentation VHDL, runs ModelSim, parses transcripts into
CSV, and writes SVG figures under `reports/presentation_8bit_rca/`. Curated
report artifacts are organized as:

```text
reports/presentation_8bit_rca/data/     Parsed CSV and JSON data
reports/presentation_8bit_rca/figures/  SVG/PNG visualizations
reports/presentation_8bit_rca/traces/   ModelSim transcripts used as evidence
```

Latest 4-bit exhaustive repeated-solve results under the main 40-cycle
comparison protocol:

| Test | Forward success | Constrained inverse |
|---|---:|---:|
| Direct integer baseline | 85.69% | n/a |
| Idea 2 only, Q3.4 direct weights | 70.53% | n/a |
| Idea 3 only, sequential window | 46.79% | 54.79% |
| Idea 4 only, parallel shadow node | 65.36% | 74.46% |
| Idea 3+4, integer shadow/window | 85.94% | 89.01% |
| Idea 2+3+4, Q3.4 shadow/window | 99.65% | 99.67% |

The shortened Q3.4 schedules are reported separately as forward-only timing
experiments. The corrected `10,8,16,6` schedule reaches `98.78%`, and the
shortest physically justified schedule tested here, `2,2,4,2`, reaches
`96.30%`. These are not used as the constrained-inverse hyperparameter setting.

The key interpretation is that idea 2 does not work by itself: Q3.4 increases
the local HA/FA field magnitude and saturates the tanh update, but it does not
fix carry arrival time. A downstream FA can confidently collapse around a wrong
early carry. Q3.4 becomes useful only after idea 3 and idea 4 provide timing
isolation and a directional shadow carry boundary.

Clamp SUM-only inverse sampling is intentionally reported separately because it
tests distribution quality with both A and B free, not recovery of one missing
operand. Current 1000-trial-per-SUM results remain mixed:

| Test | Valid rate | Valid-pair coverage |
|---|---:|---:|
| Direct integer baseline | 85.95% | 100.00% |
| Idea 3+4, integer shadow/window | 68.60% | 100.00% |
| Idea 2+3+4, Q3.4 shadow/window | 77.25% | 25.00% |
| Idea 2+3+4, Q3.4 reverse-order shadow/window | 76.70% | 75.78% |
| Idea 4 only, parallel shadow node | 62.95% | 100.00% |
| Idea 2+4, Q3.4 parallel shadow | 76.83% | 64.45% |

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
- `tb/tb_inv_xor_gate.vhd`

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
python .\scripts\generate_hamiltonians.py
```

It writes:

```text
src/generated_networks.vhd
reports/hamiltonians.json
reports/hamiltonians.md
```

The default HA/FA block scales are `1`; optional `--ha-scale` and `--fa-scale`
arguments can be used later for energy-gap experiments.

For fixed-point coefficient experiments, the generator can emit scaled integer
weights with an explicit field radix. For example, this emits FP4 coefficients
whose physical Hamiltonian weights are half of the base library:

```powershell
python .\scripts\generate_hamiltonians.py `
  --weight-frac-bits 4 `
  --weight-scale 1/2 `
  --vhdl sim\experiments\generated_networks_fp4_half.vhd
```

The default generated RTL remains integer-weighted (`--weight-frac-bits 0`,
`--weight-scale 1`).

For an FP8 minimum-gap experiment, use one FP8 LSB of physical coefficient
weight:

```powershell
python .\scripts\generate_hamiltonians.py `
  --weight-frac-bits 8 `
  --weight-scale 1/256 `
  --vhdl sim\experiments\generated_networks_fp8_mingap.vhd
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
python .\scripts\optimize_fp8_hamiltonians.py --link-q8 16
python .\scripts\optimize_fp8_hamiltonians.py `
  --coefficient-format fp8-e4m3 `
  --coeff-max-value 448 `
  --link-value 1/16 `
  --vhdl sim\experiments\generated_networks_fp8_e4m3_optimized_split.vhd `
  --report reports\optimized_fp8_e4m3_hamiltonians.json
python .\scripts\optimize_fp8_hamiltonians.py `
  --coefficient-format fp8-e3m4 `
  --fp8-bias 1 `
  --coeff-max-value 100 `
  --link-value 1/16 `
  --vhdl sim\experiments\generated_networks_fp8_e3m4_b1_gap100_link_1_16.vhd `
  --report reports\optimized_fp8_e3m4_b1_gap100_link_1_16.json
python .\scripts\optimize_fp8_hamiltonians.py `
  --coefficient-format fp8-e2m5 `
  --fp8-bias -3 `
  --coeff-max-value 100 `
  --link-value 1/2 `
  --vhdl sim\experiments\generated_networks_fp8_e2m5_bminus3_gap100_link_1_2.vhd `
  --report reports\optimized_fp8_e2m5_bminus3_gap100_link_1_2.json
```

This writes `reports/optimized_fp8_hamiltonians.json` and
`sim/experiments/generated_networks_fp8_optimized_split.vhd`.

For exact coefficient checks:

```powershell
python .\scripts\verify_hamiltonians.py
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
src/inv_sc_pkg.vhd      Shared spin helpers
src/lfsr32.vhd          Synthesizable PRNG
src/spin_node.vhd       Reusable stochastic spin-gate node
src/inv_and_gate.vhd    Three-node invertible AND network
src/inv_xor_gate.vhd    Four-node invertible XOR/half-adder network
src/generated_networks.vhd
                         Generated OR/NAND/NOR/XNOR/FA/adder/bitcount networks
src/generated_presentation_*.vhd
                         Fresh-seeded RCA presentation artifacts
tb/*.vhd                ModelSim testbenches
reports/hamiltonians.*  Coefficient reports
reports/presentation_8bit_rca/
                         Current report, CSV data, SVG figures, and transcripts
scripts/*.py            Generator, verifier, and probability plotters
scripts/run_presentation_rca_experiments.py
                         End-to-end presentation experiment driver
sim/run_modelsim.do     ModelSim compile/run script
sim/run_modelsim.ps1    PowerShell wrapper for local ModelSim path
```

Regenerable Python bytecode, ModelSim work libraries, transcripts outside the
curated report folder, and local scratch sweep directories are ignored by
`.gitignore`.

## Run Simulation

From PowerShell:

```powershell
cd "C:\Projects\stochastic_circuits"
.\sim\run_modelsim.ps1
```

Or from the `sim` folder:

```powershell
cd "C:\Projects\stochastic_circuits\sim"
C:\intelFPGA_lite\modelsim_ase\win32aloem\vsim.exe -c -do run_modelsim.do
```

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
`scripts/verify_hamiltonians.py`.

For targeted 8-bit synthesized-adder convergence debugging:

```powershell
.\sim\run_adder8_diagnostics.ps1
.\sim\run_adder8_diagnostics.ps1 `
  -GeneratedNetworks "experiments/generated_networks_fp4_half.vhd" `
  -AdderRndWeight 1
.\sim\run_adder8_split_diagnostics.ps1
```

The diagnostic bench reports output-sum histograms and per-sum/per-carry hit
counts for hard carry-chain cases.

For the presentation RCA workflow, the most useful direct entry point is:

```powershell
python .\scripts\run_presentation_rca_experiments.py
```

Individual runners used by that script include:

```text
sim/run_adder4_direct_randomized_exhaustive.ps1
sim/run_adder4_direct_sum_randomized_distribution.ps1
sim/run_adder4_windowed_randomized_exhaustive.ps1
sim/run_adder4_shadow1_parallel_randomized_exhaustive.ps1
sim/run_adder4_shadow1_randomized_exhaustive.ps1
sim/run_adder4_shadow1_sum_randomized_distribution.ps1
sim/run_adder8_direct_repeated_solve.ps1
sim/run_adder8_shadow1_repeated_solve.ps1
```

The 4-bit presentation tests are exhaustive over all `A,B` pairs and use fresh
randomized trajectories. The SUM-only test is exhaustive over SUM=0..30 and
records the sampled valid-pair distribution. The 8-bit presentation tests are
selected-vector repeated solves, not exhaustive.

## Open AND Waveform

To open ModelSim in GUI mode with an AND-gate wave window:

```powershell
cd "C:\Projects\stochastic_circuits"
.\sim\open_and_wave.ps1
```

The script compiles the AND design, runs `tb_inv_and_gate` for 20 us, and adds
the clamp controls, spins, local fields, update phase, counters, and PRNG bits
to the wave window.

## Python Trace Visualization

For a cleaner sampled view, run the trace flow:

```powershell
cd "C:\Projects\stochastic_circuits"
.\sim\run_and_trace.ps1
```

This runs `tb_inv_and_trace`, writes `sim/and_trace.csv`, then uses
`scripts/plot_and_trace.py` to generate:

```text
sim/and_trace.png
sim/and_trace_summary.csv
sim/and_state_probabilities.csv
```

The trace covers all four forward AND cases plus reverse operation with
`Y=0` and `Y=1`.

For XOR:

```powershell
.\sim\run_xor_trace.ps1
```

This produces:

```text
sim/xor_trace.csv
sim/xor_trace.png
sim/xor_trace_summary.csv
sim/xor_state_probabilities.csv
sim/xor_ab_probabilities.csv
```

To regenerate both legacy probability reports:

```powershell
.\sim\run_all_traces.ps1
```

This also writes exact small-gate Hamiltonian probability reports for
AND/OR/NAND/NOR/XOR/XNOR:

```text
sim/generated_gate_probability_summary.csv
sim/generated_gate_state_probabilities.csv
sim/generated_gate_ab_probabilities.csv
sim/generated_gate_probabilities.png
```

For clamped-output runs, the `*_ab_probabilities.csv` files are the most useful
view. For example, AND with `Y=0` should distribute probability across
`AB=00`, `AB=01`, and `AB=10`, with each near one third.

The current presentation gate visualizations are produced by
`scripts/run_presentation_rca_experiments.py` and written to:

```text
reports/presentation_8bit_rca/figures/gate_energy_landscape.svg
reports/presentation_8bit_rca/figures/gate_reverse_distributions.svg
reports/presentation_8bit_rca/data/gate_energy_landscape.csv
reports/presentation_8bit_rca/data/gate_reverse_distributions.csv
```

## Notes

This is a compact RTL implementation of the paper's stochastic spin-gate idea,
not a transistor-level model. The design is intentionally small and readable:
integer Hamiltonian coefficients are hardwired, stochasticity comes from one
xorshift PRNG per node, clamping is a mux around each node, and the nonlinear
block is a fixed-point stochastic tanh sampler.
