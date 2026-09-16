# Stochastic Circuit Experiments: Invertible p-bit Logic Gates and Ripple-Carry Adders in VHDL

Invertible stochastic-computing logic gates (p-bit / spin-gate model) implemented in VHDL, composed into 4/8-bit ripple-carry adders (RCA), and studied for reliable forward and inverse convergence via timing windows, shadow carry nodes, fixed-point coefficient quantization, and Hamiltonian energy-landscape optimization.

The full chronological record of every experiment, with results and evidence files, is in **[reports/experiment_timeline.md](reports/experiment_timeline.md)**.

## 1. Background and Method

### Spin-gate model (Onizawa et al., *A Design Framework for Invertible Logic*)

Every Boolean relation is encoded as an Ising-type Hamiltonian with biases `h` and couplings `J` whose ground states are exactly the valid truth-table rows. The hardware path is:

```text
Boolean relation -> Hamiltonian h/J -> spin-gate network -> VHDL RTL
```

Each spin node computes an integer local field and samples a bipolar spin from a stochastic tanh (p-bit) update:

```text
I_i = h_i + sum(J_ij * m_j) + w_rnd * random_sign       (logic 0 -> m = -1, logic 1 -> m = +1)
P(m_i = +1) = (1 + tanh(I_i)) / 2
```

The tanh is implemented as a fixed-point probability lookup compared against a per-node xorshift PRNG (`src/lfsr32.vhd`). Clamping is a mux around each node. Free nodes are updated one per clock phase while clamped nodes are forced continuously, which avoids the parallel-update oscillations of the small XOR/half-adder network. Running a gate *forward* clamps its inputs and lets the output settle; running it *inverse* clamps the output and samples the inputs that are consistent with it.

### Gate library

Two hand-written wrappers (`src/inv_and_gate.vhd`, `src/inv_xor_gate.vhd`) are kept for continuity. The rest of the library (`AND`, `OR`, `NAND`, `NOR`, `XOR`/half-adder, `XNOR`, `FA`, `ADDER8_RIPPLE`, `BITCOUNT8`, `COMB6_MIXED`) is generated from coefficient tables by `scripts/generate_hamiltonians.py` into `src/generated_networks.vhd`. Because a pairwise Ising XOR needs a 3-body parity term, XOR is realized as the sum output of a 4-node half adder with an exposed auxiliary carry node. All generated entities share one vector interface:

```vhdl
clk, rst, enable : in  std_logic;
clamp_en         : in  std_logic_vector(N-1 downto 0);
clamp_value      : in  std_logic_vector(N-1 downto 0);
spins            : out std_logic_vector(N-1 downto 0);
```

Structural correctness of every block is checked exhaustively by `scripts/verify_hamiltonians.py` (all 3/4/5-node blocks, 4096 bitcount states, 65536 8-bit adder placements).

### Ripple-carry adder (RCA) as a pseudo-time-dependent system

Directly coupling HA/FA blocks into a 4-bit RCA does *not* converge reliably even though every local block is correct. The adder is combinational in Boolean logic but behaves as a time-dependent system stochastically: the LSB stage must collapse first, its carry must be transferred, and only then can the next FA be trusted. Four "ideas" were tested (see `reports/time_dependent_annealing_report.md` and `reports/presentation_8bit_rca/report.md`):

- **Idea 1 - equal gaps** in composed combinational logic (E3M4 coefficients, `COMB6_MIXED` benchmark).
- **Idea 2 - larger dynamic range / fixed-point weights** (FP4/FP8/Q8 sweeps, MILP-optimized Q3.4 HA/FA blocks).
- **Idea 3 - sequential annealing windows** that activate adder stages in carry order.
- **Idea 4 - shadow carry nodes** (`c_i -> q_{i+1} -> FA cin`) that separate carry generation from consumption.

### Hamiltonian landscape optimization (later stages)

The SUM-only inverse test showed that the shadow/window designs, while excellent for forward and constrained-inverse tasks, collapse the sampled distribution compared to the plain integer baseline. This motivated the Python/Gurobi experiments under `experiments/`, which optimize continuous or quantized coefficients so that the *whole* energy landscape (not only the per-block gap) is sampler friendly: equal valid energies, smooth one-bit neighbourhoods, and cutting planes / hard cuts against invalid local minima, extended to 2/3/4-body Hamiltonians for a 6-bit least-node adder.

## 2. Repository Layout

```text
src/                  Hand-written RTL (inv_sc_pkg, lfsr32, spin_node, inv_and_gate, inv_xor_gate)
                      and generated networks compiled by the simulations (generated_*.vhd)
src/variants/         Coefficient-variant networks referenced by specific sim/*.do runners
                      (FP8 split-carry, E4M3 block timing, COMB6 E3M4 equal gap)
tb/                   ModelSim testbenches (gate checks, RCA diagnostics, exhaustive/randomized RCA runs)
sim/                  ModelSim runners: paired *.do (Tcl) and *.ps1 (PowerShell wrapper) scripts, modelsim.ini
scripts/              Python generators, MILP coefficient optimizers, verifiers, plotters, and the
                      end-to-end presentation driver (run_presentation_rca_experiments.py)
experiments/          Standalone Python/Gurobi landscape-optimization studies (no VHDL)
  quantized_landscape_optimizer/           Documentation of the quantized landscape optimizer (README only)
  multibody_hamiltonian_6bit_adaptive_qp/  6-bit 2/3/4-body adaptive QP + hard-cut verifier (code + logs)
reports/
  experiment_timeline.md                 Chronological record of all experiments and results
  time_dependent_annealing_report.md     Stage A: ideas 1-4 on the 4/8-bit RCA (deterministic seeds)
  comb6_equal_gap_report.md              Stage A: COMB6 E3M4 equal-gap experiment
  presentation_8bit_rca/                 Stages B-D: randomized presentation dataset
    report.md, data/*.csv|json, figures/*.svg|png, traces/*.txt|log
  coefficients/                          Coefficient reports produced by the generators/optimizers
    hamiltonians.{json,md}               Base integer gate library
    comb6_e3m4_equal_gap.json            COMB6 E3M4 coefficients
    optimized_q34_shadow1_*.json         Q3.4 MILP-optimized HA/FA blocks (4-bit and 8-bit shadow RCA)
    fp8_split_carry/optimized_*.json     FP8/Q8 split-carry MILP sweep (negative result, kept for record)
```

Regenerable artifacts are ignored by `.gitignore`: Python bytecode, ModelSim work libraries / transcripts / `*.wlf`, local trace CSV/PNG under `sim/`, `sim/experiments/` variant dumps, scratch sweep folders, and `experiments/**/out*/` Gurobi outputs.

## 3. Running Simulations and Scripts

### Requirements

- ModelSim (the `.ps1` wrappers assume `C:\intelFPGA_lite\modelsim_ase\win32aloem\vsim.exe`; edit `$modelsimBin` or run the `.do` files directly from `sim/`).
- Python 3.10+ with `numpy`, `scipy` (MILP in `optimize_fp8_hamiltonians.py` and Q3.4 block optimization), `matplotlib` (plots).
- `experiments/multibody_hamiltonian_6bit_adaptive_qp/` additionally needs `gurobipy` (licensed Gurobi) and `numba`.

### Basic gate regression

```powershell
.\sim\run_modelsim.ps1
# or, from sim/:
vsim -c -do run_modelsim.do
```

Runs `tb_inv_and_gate`, `tb_inv_xor_gate`, `tb_generated_gates`, `tb_generated_systems`: forward/inverse AND and XOR, generated gate checks, and sampled probabilities of the 8-bit adder and bitcount.

### Regenerating the gate library and coefficient reports

```powershell
python .\scripts\generate_hamiltonians.py            # -> src/generated_networks.vhd, reports/coefficients/hamiltonians.{json,md}
python .\scripts\verify_hamiltonians.py              # exhaustive structural verification
python .\scripts\generate_hamiltonians.py --weight-frac-bits 8 --weight-scale 1/256 --vhdl src\variants\generated_networks_fp8_mingap.vhd
python .\scripts\optimize_fp8_hamiltonians.py --coefficient-format fp8-e3m4 --fp8-bias 1 --coeff-max-value 100 --link-value 1/16 `
    --vhdl src\variants\generated_networks_fp8_e3m4_b1_gap100_adder4_link_1_16.vhd `
    --report reports\coefficients\fp8_split_carry\optimized_fp8_e3m4_b1_gap100_adder4_link_1_16.json
python .\scripts\generate_shadow1_q34_adder4.py      # -> src/generated_shadow1_q34_adder4.vhd, reports/coefficients/optimized_q34_shadow1_blocks.json
```

### RCA diagnostics (Stage A style runners)

```powershell
.\sim\run_adder4_shadow1_q34_exhaustive.ps1
.\sim\run_adder8_diagnostics.ps1 -GeneratedNetworks "../src/variants/generated_networks_fp8_optimized_split.vhd" -AdderRndWeight 1
.\sim\run_comb6_diagnostics.ps1
```

Most runners accept `-GeneratedNetworks` (path relative to `sim/`) and cycle/noise parameters that are forwarded to VHDL generics via environment variables.

### Presentation dataset (Stages B-D)

```powershell
python .\scripts\run_presentation_rca_experiments.py
```

Regenerates the presentation VHDL in `src/generated_presentation_*.vhd` with fresh OS-random seed salts, runs the ModelSim runners listed below, parses transcripts into `reports/presentation_8bit_rca/data/*.csv`, and writes figures to `reports/presentation_8bit_rca/figures/`. Individual runners used by the driver:

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

`scripts/visualize_rca_energy_landscape.py` regenerates the energy-landscape figures from `reports/presentation_8bit_rca/data/optimized_q34_shadow1_blocks.json`.

### Gate traces and waveforms

```powershell
.\sim\open_and_wave.ps1      # ModelSim GUI with the AND-gate wave window
.\sim\run_and_trace.ps1      # tb_inv_and_trace -> sim/and_trace.csv -> scripts/plot_and_trace.py
.\sim\run_xor_trace.ps1
.\sim\run_all_traces.ps1     # both traces + exact small-gate probability reports (scripts/plot_small_gate_probabilities.py)
```

Trace outputs are written to `sim/*.csv|png` and are git-ignored.

### Landscape optimization experiments

See `experiments/multibody_hamiltonian_6bit_adaptive_qp/README.md` (entry points `adaptive_qp_6bit.py`, `compare_adaptive23_convergence.py`, `staged_cut_verifier.py`; results are summarized in `EXPERIMENT_LOG.md`, raw `out*/` folders are git-ignored) and `experiments/quantized_landscape_optimizer/README.md` (documentation of an earlier study whose scripts were not committed).

## 4. Experiment Stages and Main Conclusions

Details, per-run numbers, timestamps, and evidence files are in [reports/experiment_timeline.md](reports/experiment_timeline.md).

| Stage | Content | Key result |
|---|---|---|
| A (≤ 2026-05-24) | Gate library, FP4/FP8/Q8 sweeps, COMB6 equal gap, ideas 1-4 on the 4/8-bit RCA with deterministic LFSR seeds | COMB6 E3M4: 64/64 (idea 1 positive for combinational logic). Direct integer 4-bit RCA fails (min 0/100). Ideas 3+4 integer shadow latch and ideas 2+3+4 Q3.4 shadow latch: exhaustive 256/256 forward; Q3.4 shortens pre-settle from 53 to 46 cycles; 8-bit 40×8 schedule 32/32 |
| B (2026-05-25) | Presentation dataset: exhaustive 256 (A,B) × 100 randomized trajectories, 8-bit 6 vectors × 100 | Idea 2 alone is the negative control (70.53%); ideas 2+3+4 is the only strongly positive design |
| C (2026-05-25) | SUM-only inverse distribution test, shadow copy-J sweep, energy-landscape plots | Direct integer baseline is best on SUM-only sampling (valid 85.95%, coverage 256/256); forward-order Q3.4 collapses coverage to 64/256 |
| D (2026-05-25) | Main protocol at 40 cycles/block, forward window-reduction sweep, AND single-cycle sanity check | Ideas 2+3+4 (40×4): forward **99.65%**, constrained inverse **99.67%**; 10,8,16,6 → 98.78%; 2,2,4,2 → 96.30%; reverse-order SUM-only raises coverage to 194/256 but stays below baseline |
| E (2026-06) | Quantized landscape optimizer, least-node LP, 8-bit shadow topologies, real inverse RCA8 (documentation only) | Least-node LP gap collapses to 1/8192; 8-shadow carry Q16 inverse 42.33% vs integer baseline 32.33%; smoother landscapes but no dynamic gain from 12 shadows |
| F (2026-07) | 6-bit 2/3/4-body adaptive QP with hard cuts (Gurobi) | Stage3 hard cut: cutting planes converge in 4 rounds to 0 violations over 33,554,432 states, but 1642 invalid local minima remain; dynamic convergence improvement not demonstrated |
| G (planned, 2026-09) | E0 baseline rebuild + extended static/dynamic metrics; E1 canonical vs long-range support sweep (`canon2/3/4`, `span1_2/3` vs `stage3`/`full3`) | Plan only (`PLAN_E0_E1.md` on branch `cursor/experiment-e0-e1-plan-b98b`, PR #2); runs target the licensed local Gurobi workstation; no results yet |

Final 4-bit RCA comparison (exhaustive 256 cases × 100 randomized trajectories, 40-cycle protocol):

| Test | Forward success | Constrained inverse |
|---|---:|---:|
| Direct integer baseline | 85.69% | n/a |
| Idea 2 only, Q3.4 direct weights | 70.53% | n/a |
| Idea 3 only, sequential window | 46.79% | 54.79% |
| Idea 4 only, parallel shadow node | 65.36% | 74.46% |
| Ideas 3+4, integer shadow/window | 85.94% | 89.01% |
| Ideas 2+3+4, Q3.4 shadow/window | 99.65% | 99.67% |

Verdict per idea: idea 1 is positive for pure combinational logic but insufficient for the RCA; idea 2 is negative alone and positive only together with 3+4; idea 3 is semi-positive alone; idea 4 is essential for RCA timing. Landscape optimization improves static metrics (gap, smoothness, local-minima count) but has not yet been shown to improve dynamic convergence.

## 5. Known Gaps

- The scripts and `out/` results of `experiments/quantized_landscape_optimizer/` were never committed; its numbers exist only in that README.
- `experiments/multibody_hamiltonian_6bit_adaptive_qp/out*/` is git-ignored, so only the Stage3 hard-cut run summarized in `EXPERIMENT_LOG.md` is on record; the "5-bit experiment" referenced there is not in the repository.
- Early Stage A evidence (quick-summary CSVs, 8-bit baseline transcript, trace CSVs) and the copy-J scratch sweep exist only in history (`04243d1`, `3575e71`). The regenerable FP4/FP8/Q8 variant VHDL formerly under `sim/experiments/` was removed in the cleanup and is recoverable via `git show 8f512ce:sim/experiments/<file>`.
- The FP8/Q8 split-carry sweep (`reports/coefficients/fp8_split_carry/`) has no simulation result files, only a qualitative negative conclusion.
- Shortened Q3.4 schedules were tested forward only; 8-bit results are non-exhaustive (6 vectors); no 8-bit SUM-only test exists; the SUM-only reverse-order 40×4 run has no transcript.
- Stage A and Stages B-D use different protocols (deterministic LFSR seeds + frozen readout vs randomized scramble + repeated solves), so their success numbers are not directly comparable.
