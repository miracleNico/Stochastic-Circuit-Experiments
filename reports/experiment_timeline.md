# Experiment Timeline (stochastic_circuits / invertible stochastic logic gates)

Scope: the complete history of this repository (all former branches). Times are git commit times (author time = commit time, timezone -04:00), supplemented by the `End time` stamps inside ModelSim transcripts and dates written in the documents themselves.

Paths in this document refer to the current repository layout (after the cleanup/restructure PR). Files that were deleted during cleanup are marked as such and can be recovered from git history (e.g. `git show 8f512ce:sim/experiments/<file>`).

## 0. Repository theme in one sentence

Following the spin-gate (p-bit / tanh update) model of Onizawa et al., *A Design Framework for Invertible Logic*, invertible stochastic logic gates (AND/OR/NAND/NOR/XOR/XNOR/FA) are implemented in VHDL and composed into 4/8-bit ripple-carry adders (RCA) and a bitcount, to study "how to make a composed RCA converge reliably in both forward and inverse (invertible) tasks". Later work turned to Gurobi-based optimization of the Hamiltonian "energy landscape" with continuous / quantized coefficients.

## 1. Historical branch notes

The history was completely linear (no merge commits, no forks):

```text
04243d1 (05-25 00:19) -> bc2ac96 (05-25 03:22) -> 3575e71 (05-25 04:32) -> 8f512ce (05-25 07:03)
                                                                                |
                                                                                v
                                                                   a0998af (06-11 03:55)  [formerly branch test]
                                                                                |
                                                                                v
                                                                   a50e26d (07-30 00:59)  [formerly branch codex/quantized-landscape-optimizer]
```

| Former branch | Based on | Head commit | Purpose | Status |
|---|---|---|---|---|
| `main` | — | `8f512ce` 2026-05-25 07:03 | VHDL gate library + the "timing window + shadow carry + Q3.4 weights" demonstration study for the 4/8-bit RCA, producing `reports/presentation_8bit_rca/report.md` | Completed/stable (all 4 commits on 05-25) |
| `test` | `main` (1 commit after `8f512ce`) | `a0998af` 2026-06-11 03:55 | Documentation (README only) for the "quantized Hamiltonian landscape optimizer" experiments | Documentation only; the 7 scripts and `out/` results referenced by the README were never committed |
| `codex/quantized-landscape-optimizer` | `test` (1 commit after `a0998af`) | `a50e26d` 2026-07-30 00:59 | Continuous-float 2/3/4-body QP optimization (Gurobi) of a 6-bit least-node + 6-shadow-carry adder, including the Stage3 hard-cut experiment | Code + README + EXPERIMENT_LOG committed; `out*/` results excluded by .gitignore |

Current state (2026-09-15):

- `origin/main` was fast-forwarded from `8f512ce` to `a50e26d`, so `main` now contains everything from the former `test` and `codex/quantized-landscape-optimizer` branches.
- The remote branches `test` and `codex/quantized-landscape-optimizer` were deleted after the fast-forward. All their commits remain reachable from `main`.
- The two later branches only added files under `experiments/`; they did not modify any file that already existed on `main` (`git diff 8f512ce a50e26d -- README.md .gitignore` was empty).

## 2. Experiment timeline in chronological order

### Stage A: gate library, FP8/Q8 coefficient optimization, first RCA attempts (≤ 2026-05-24, committed in `04243d1` 2026-05-25 00:19)

`04243d1 gates,4bRCA,8bRCA,bitcounter` (402 files, 676k lines, including many ModelSim work libraries and trace CSVs)

| Sub-experiment | Goal / hypothesis | Method / key change | Result | Evidence |
|---|---|---|---|---|
| A1 Basic gate RTL | Reproduce the paper's spin gates | `src/spin_node.vhd`, `inv_and_gate.vhd`, `inv_xor_gate.vhd` (XOR implemented as a 4-node half adder); 8-bit tanh LUT + LFSR | Small-gate assertion tests pass; AND inverse with Y=0 gives AB∈{00,01,10} each ≈1/3 | `README.md`, `sim/*_ab_probabilities.csv` (deleted later in bc2ac96) |
| A2 Generator + exhaustive verification | Generate OR/NAND/NOR/XNOR/FA/ADDER8/BITCOUNT8 from coefficient tables | `scripts/generate_hamiltonians.py`, `verify_hamiltonians.py` (exhaustive over 3/4/5-node blocks, 4096 bitcount states, 65536 8-bit adder states) | Exhaustive structural correctness passes | `reports/coefficients/hamiltonians.md/.json` |
| A3 FP4/FP8/Q8 dynamic-range sweep (early form of idea 2) | Does larger dynamic range / larger gate gap improve convergence? | `generate_hamiltonians.py --weight-frac-bits/--weight-scale`; `optimize_fp8_hamiltonians.py` MILP: maximize HA/FA valid/invalid gap, then minimize carry-boundary coefficients; emits a split-carry weak-equality-link topology | ~23 `optimized_fp8_e3m4/e4m3/fixed_q8_*_link_*.json` under `reports/coefficients/fp8_split_carry/` and corresponding generated VHDL (formerly `sim/experiments/*.vhd`; only the variants referenced by `sim/*.do` are kept in `src/variants/`, the rest were deleted in cleanup); `time_dependent_annealing_report.md §4`: the fixed-Q8 split-copy branch "underperformed the integer/shadow schedules, zero-hit cases remained" → idea 2 alone is negative | `reports/coefficients/fp8_split_carry/optimized_*.json`, `src/variants/`, `reports/time_dependent_annealing_report.md` |
| A4 COMB6 equal gap (idea 1) | Is unifying intra-block gaps beneficial in combinational logic? | `COMB6_MIXED` 6-in 4-out 21-spin network; E3M4 encoding raises the XOR/XNOR gap from 2 to 4 (physical) | Integer baseline RND=1 SETTLE=1000: 21/64 match, 39 zero-hit; SETTLE=20000: 50/64; E3M4 RND=16 SETTLE=1000: 57/64; SETTLE=5000: 62/64; SETTLE=20000: **64/64, min 997/1000** → idea 1 strongly positive for pure combinational logic | `reports/comb6_equal_gap_report.md` (dated 2026-05-24), `reports/coefficients/comb6_e3m4_equal_gap.json`, `src/variants/generated_networks_comb6_e3m4_equal_gap.vhd` |
| A5 Static integer 4-bit RCA baseline | Can directly coupled HA/FA converge? | 16 vectors, COUNT=100 | settle=128: avg 22.9, min 0; settle=500: avg 78.0, min 0 → the failure is a timing problem, not a local-gap problem | `time_dependent_annealing_report.md §3` |
| A6 Idea 3 alone (sequential annealing windows) | Activate stages in carry order | Asymmetric integer windows, pre=212 | avg 93.8/100, min 0, perfect 15/16 → semi-positive | same, §5 |
| A7 Ideas 3+4, integer shadow latch | Shadow node q separates carry generation and consumption | `c_i -> q_{i+1} -> FA cin`; schedule B0=10,copy1,B1=16,copy1,B2=16,copy1,B3=8 (pre=53), block_rnd=1 | **Exhaustive 256/256 perfect, 256000/256000, q matches 1000/1000** | same, §5; `scripts/generate_shadow1_adder4.py`, `tb/tb_adder4_shadow1_exhaustive.vhd` |
| A8 Ideas 2+3+4, Q3.4 shadow latch | Add Q3.4 (1s3d4f) MILP-optimized coefficients on top of 3+4 | HA h=[56,56,-56,-112] (physical /16), gate gap 112=7.0, copy=64=4.0. First run block_rnd=16, copy=2: perfect 128/256 (failure mode top_sum=expected+1); retuned to B0=10,B1=8,B2=16,B3=6, copy=2, block_rnd=0 (pre=46) | **Exhaustive 256/256 perfect**; pre reduced from 53 to 46 | same, §6; `reports/coefficients/optimized_q34_shadow1_blocks.json`, `scripts/generate_shadow1_q34_adder4.py` |
| A9 Q3.4 small-noise check | Can a small random-field noise be reintroduced? | block_rnd=4(0.25)/8(0.5), COUNT=100 | Forward: rnd=4 → 256/256; rnd=8 → 128/256. Constrained inverse B+SUM→A: rnd=4 → 256/256; rnd=8 → 176/256. Recommended operating point block_rnd=4 | `reports/q34_forward_noise_quick_summary.csv`, `q34_inverse_forward_noise_quick_summary.csv` (both deleted in bc2ac96) |
| A10 Inverse behaviour (constrained inverse / SUM-only) | Is the shadow latch invertible? | Fixed a generator bug (a*/b* not updated when unclamped); noise-free Q3.4 schedule | Constrained inverse B+SUM→A: 256/256; SUM-only: perfect 24/31, 7 SUM failures; with noise rnd=16 the inverse degrades to 176/256 and SUM-only to 18/31 | `time_dependent_annealing_report.md §7` |
| A11 SUM-only reverse-order schedule | Does reversing block activation order help the under-constrained inverse? | B3→q3→B2→…→B0; 1000 trials/SUM | Forward order valid 23864/31000 vs reverse order 23637/31000 (not better globally; 5 SUMs improved, 24 worse, 2 tied); but boundary cases: SUM=4 143→587, SUM=25 850→982, SUM=29 0→223; SUM=0/1/30 still 0 | `reports/q34_sum_only_reverse_distribution_summary.csv` (deleted in bc2ac96), report §7 |
| A12 Reverse-order schedule + noise, constrained inverse | — | reverse=true, rnd=4/8 | B+SUM only 10/256 perfect, SUM-only 6/31 or 4/31 → reverse order is severely harmful for the constrained inverse | `reports/q34_inverse_reverse_noise_quick_summary.csv` (deleted in bc2ac96) |
| A13 8-bit composed RCA extension | Does 2+3+4 transfer to 8-bit (39 nodes)? | Old integer gen_adder8: 15+1 and 170+85 both 0/1000; short schedule 10,8,16,6,8,8,16,6 copy=2 rnd=4: perfect 7/32; **40×8 copy=2 rnd=4: 32/32** (pre=334); boundaries: blocks=39 → 15/32; copy=1 → 15/32; rnd=0 blocks=32 → 32/32 | Forward transfer succeeds but needs roughly one 39-node scheduling period of relaxation per stage | `time_dependent_annealing_report.md §8`, `reports/adder8_integer_baseline_diagnostics_transcript.txt` (deleted in bc2ac96; ModelSim end time 05-25 00:15) |
| A14 "Why the RCA readout looks deterministic" + repeated-solve check | Clarify that a frozen readout of 1000/1000 ≠ probability 1 | 8-bit Q3.4 shadow RCA; per trial: unclamp → 80-cycle scramble (rnd=8) → clamp → solve once → sample once; 200 trials/vector | 37+219: 197/200; 142+73: 198; 201+54: 196; 91+188: 199; 6+177: 200; 127+1: 198 → high but non-unity success probability | report §9 (appended in bc2ac96, 133 lines) |

### Stage B: presentation dataset with fresh random seeds (ModelSim 2026-05-25 02:05–02:36; committed in `bc2ac96` 03:22)

`bc2ac96 presentation version` (230 files; deleted sim/work libraries, old quick CSVs and traces; added `scripts/run_presentation_rca_experiments.py` 1138 lines, `reports/presentation_8bit_rca/`)

Method change: all 4-bit tests are exhaustive over the 256 (A,B) pairs with 100 random trajectories per case (OS-random seed salt + 80-cycle scramble); 8-bit uses 6 selected vectors × 100. This responds to the "deterministic LFSR seed" risk of Stage A.

| ModelSim end time | Run | Forward success | Constrained inverse B+SUM→A |
|---|---|---:|---:|
| 02:10:44 | baseline direct 4-bit (integer) | 85.69% (21937/25600), min 41 | n/a |
| 02:15:03 | ideas 3+4 integer shadow (40,40,40,40 copy=2) | 85.94% (22001), min 67 | 89.01% (22787) |
| 02:20:04 | idea 2 only, Q3.4 direct | 70.53% (18056), min 0, 162 non-perfect cases | n/a |
| 02:24:06 | idea 3 only, sequential window | 46.79% (11977) | 54.79% (14027) |
| 02:28:20 | idea 4 only, parallel shadow (settle 160) | 65.36% (16732) | 74.46% (19061) |
| 02:29:58–02:35:54 | 8-bit companion checks (baseline / idea2 / idea34 / idea234) | see §3.3 | — |
| (bc2ac96 version) | ideas 2+3+4 Q3.4 shadow (schedule 10,8,16,6 at that time) | 98.64% (25251), min 92 | 99.62% (25502) |

Conclusion (as of bc2ac96): idea 2 alone is the clearest negative control; 2+3+4 is the only strongly positive result.

### Stage C: SUM-only inverse distribution test + shadow-J sweep + energy landscape plots (2026-05-25 03:34–04:05; committed in `3575e71` 04:32)

`3575e71 updated presentation version` (43 files, +21.6k lines)

| Time | Sub-experiment | Goal | Result |
|---|---|---|---|
| 03:34:42 | SUM-only ideas 3+4 integer | Clamp only the 5-bit SUM, A and B fully free, 31 SUMs × 1000 | valid 68.60%, coverage 256/256, entropy 0.987 |
| 03:35:40 | SUM-only ideas 2+3+4 Q3.4 (forward order 10,8,16,6) | same | valid 77.25%, **coverage only 64/256**, entropy 0.317, 3 zero-valid SUMs |
| 03:37:50 | SUM-only idea 4 only, parallel shadow | same | valid 62.95%, coverage 256/256 |
| 03:39:53 | SUM-only ideas 2+4 Q3.4 parallel shadow | same | valid 76.83%, coverage 165/256, 3 zero-valid SUMs |
| 04:05:13 | SUM-only baseline direct integer | same | **valid 85.95%, coverage 256/256, entropy 0.974** → the direct integer baseline is strongest on this metric |
| (scratch, later deleted) | Shadow copy-J sweep `scripts/sweep_shadow_copy_j_sum.py` | Sweep (c→q, q→c) physical couplings (3,3),(2,2),(1,1),(1,4),(2,3),(3,2),(2,1), Q3.4 ideas 2+4 parallel, 200 trials/SUM | valid rate 53.8%–74.0%, coverage 30%–98%; (1,4) has the best coverage 252/256 but valid 55.1%; (2,1) has the highest valid 74.0% with coverage 147/256 → valid rate and coverage trade off; the result directory `scratch_shadow_j_sweep/` was deleted in 8f512ce and added to .gitignore |
| — | RCA energy landscape visualization `scripts/visualize_rca_energy_landscape.py` | Full-cube energies before/after quantization | 4-bit: integer valid −16 / invalid −14 gap 2 → Q3.4 −56/−49 gap 7.0; 8-bit: gap 2 → 7.0 |

Also added `tb_adder4_direct_sum_randomized_distribution.vhd`, `tb_adder4_shadow1_sum_randomized_distribution.vhd`; report.md gained §7 "Clamp SUM-Only Inverse Test". The README first showed the SUM-only table.

### Stage D: main protocol switched to 40 cycles + forward window-reduction sweep + AND single-cycle robustness check (2026-05-25 06:30–06:48; committed in `8f512ce` 07:03)

`8f512ce Finalize RCA presentation experiments` (49 files; deleted scratch sweeps and .pyc, added `.gitignore`)

| Time | Sub-experiment | Goal | Result |
|---|---|---|---|
| — | AND gate single-cycle sanity (`tb/tb_and_onecycle_sanity.vhd`, `sim/run_and_onecycle_sanity.*`) | Check whether a "1-cycle clamp/readout" is trustworthy | Found that an unclamped output at that clock edge may still reflect the previous input → introduced the corrected protocol "pre-warm clamped inputs for 1 clock + delayed readout after the edge"; the `1,1,1,1` schedule was excluded |
| 06:30:18–06:32:06 | Ideas 2+3+4 forward window reduction (corrected protocol) `idea234_forward_window_sweep.csv`, 15 schedules | How short can the schedule get while staying above baseline? | 1,1,2,1 (11 cycles) 93.23%; 2,2,4,2 (16) **96.30%**; 4,4,4,4 (22) 97.40%; 10,8,16,6 (46) **98.78%**; 40,40,40,40 (166) **99.65%**; all above the 85.69% baseline |
| 06:47:30 | Ideas 2+3+4 main comparison rerun (40,40,40,40 copy=2) | Use the same hyperparameters for forward and constrained inverse | Forward **99.65% (25511/25600), min 97, 77 non-perfect cases**; inverse **99.67% (25516/25600), min 98** (replacing bc2ac96's 98.64%/99.62%) |
| — | SUM-only ideas 2+3+4 reverse order (40,40,40,40) | Fix the distribution collapse of forward-order Q3.4 | valid 76.70%, coverage **194/256**, zero-valid SUMs 0; but SUM=0 only 8.8%, SUM=30 20.0%, still behind the direct baseline |

report.md wording was also "depersonalized" (e.g. "honest result" → "result is mixed", "My future research goal" → "Future work").

### Stage E: quantized landscape optimizer (documentation) (runs approx. 2026-06-01–06-10, committed in `a0998af` 2026-06-11 03:55, former branch `test`)

Only `experiments/quantized_landscape_optimizer/README.md` (316 lines) was added. Goal: not only make coefficients logically correct but make the "energy landscape" sampler-friendly (valid states at the same energy level + TV-smooth one-bit neighbours of invalid states + trap cutting planes), and extend landscape optimization from local HA/FA blocks to the clamp-SUM subspace of the whole RCA.

| Sub-experiment (script names, none committed) | Method | Result |
|---|---|---|
| `generic_optimizer.py` / `landscape_optimizer.py` | Convex QP continuous solve → quantize → exhaustive verification → add post-quantization invalid local minima as "fixed-parent descent cuts" for the next round; `optimize-rca4` adds trap penalties for the 4-bit RCA (weighted by flip distance to a valid state, default inverse-square) | README has only command lines, no numerical results |
| `compare_8bit_direct.py` | Plain HA/FA 8-bit direct RCA, FP16 vs Q3.4 coefficients; paper-anneal noise schedule n=0.6745·mean(s_i) | Only output files described, no numbers |
| `least_node_lp_adder8.py` (paper-style 25-node least-node LP, seed 20260602) | `max|h|,|J| ≤ 2` | Exact global gap collapses to **1/8192 ≈ 1.22e-4** (binary-weight scaling problem of H=α(A+B−S)²) → extremely weak dynamically |
| `shadow_group_adder8.py` shadow topologies (group4 / carry8 / carry8group4; seeds 20260601, 20260610) | Gurobi QP penalizing valid-energy variance, one-bit roughness variance, coefficient L2, 2 rounds of cutting planes | 12 shadows coeff-max=7 actual max|J|=0.7335, max|h|=0.3482, γ=1.0, valid_dev_max 0.7773, tv_mean 2.466; distinguishes "strict sampling gap" from "projection-visible gap" |
| `compare_backward_real8.py` real inverse RCA8 (clamp B+SUM, Q*.16 quantization, paper-ssa update, 2000 cycles, 6 vectors × 100, seed 20260609) | — | Integer HA/FA baseline **32.33%**; least-node LP Q16 **2.17%**; 8-shadow carry Q16 **42.33%** (best); 12 shadows coeff-max=2 37.17%; coeff-max=7 34.33% |
| `visualize_shadow_vs_rca8.py` projected inverse landscape | — | Integer RCA8: mean/min inverse gap 2.000/2.000, one-bit jump 1.370, invalid local minima 10.67; 12 shadows max=2: 0.541/0.127/0.449/3.00; max=7: 0.588/0.223/0.451/3.50 → smoother but smaller gap, no dynamic improvement |

### Stage F: 6-bit multibody (2/3/4-body) adaptive QP + hard cuts (runs 2026-07-07–07-08, committed in `a50e26d` 2026-07-30 00:59, former branch `codex/quantized-landscape-optimizer`)

Added `experiments/multibody_hamiltonian_6bit_adaptive_qp/`: 7 Python scripts (3.5k lines), README, EXPERIMENT_LOG, .gitignore (excludes `out*/`, `*.log`). Pure Python/Gurobi continuous float64, not VHDL.

| Sub-experiment | Method | Result |
|---|---|---|
| `adaptive_qp_6bit.py run-all`: full2 (325 1/2-body coefficients) → full3 (2625 1/2/3-body) → adaptive_iter* (assign 50%/30%/20% of nodes to the highest 2/3/4 orders by node score) | Soft-valid QP: −γ + 20000/|V|·Σ(H(v)−E0)² + 200000/|V|·Σmax(|H−E0|−0.5,0)² + 100·roughness + 0.1/|T|·‖θ‖², s.t. invalid cuts H(u) ≥ E0+γ, |θ|≤2; Walsh–Hadamard exhaustive audit over 2²⁵ states | README only gives the workflow; no committed numbers (`out/` ignored). README mentions "the same QP as the 5-bit experiment", but the repository has no 5-bit experiment |
| `compare_adaptive23_convergence.py` / `compare_paper_ssa_solutions.py` (seed 2026070701) | Paper SSA/SSAU local-energy-distribution hyperparameter n_rnd=0.6745·mean(s_i), I0 grows geometrically from 0.01·max(s)+min|μ| to 2·max(s)+min|μ|, optional exponential noise decay; numba acceleration | No committed numbers |
| `analyze_ab_failures.py`, `tiny4_experiment.py`, `edge_hypercut_experiment.py` | Failure analysis, critical-node classification, edge/hyperedge cuts | No committed numbers |
| **`staged_cut_verifier.py --stage stage3 --stage3-cut-sum-sum --stage3-cut-output-siblings --max-rounds 4 --gurobi-threads 16`** (EXPERIMENT_LOG 2026-07-08) | Hard-cut 27 SUM–SUM and SUM–next-carry/output-sibling 2-body terms before optimization; limited to 2/3-body; Gurobi 16 threads (12C/24T machine) | Critical nodes s6, c4, c6; 2083 terms (1-body 25, 2-body 273, 3-body 1785, 515 triples rejected by hard cuts); cutting planes converge in 4 rounds: violations 100774 → 8438 → 71 → **0**, γ ≈ 2.499e-5, minimum invalid gap 2.497e-5; exhaustive audit over 33,554,432 states, **0 violations**, valid std 4.6e-9, **1642 invalid local minima**, 1376 non-zero terms. Conclusion: statically feasible, but no proven dynamic convergence improvement; needs Stage4 or a revised option strategy |

## 3. Result summary and comparison

### 3.1 4-bit RCA forward / constrained inverse (exhaustive 256 cases × 100 random trajectories, final `main` version)

| Configuration | Forward | Constrained inverse B+SUM→A |
|---|---:|---:|
| Direct integer baseline | 85.69% | n/a |
| Idea 2 only (Q3.4 direct) | 70.53% (negative control) | n/a |
| Idea 3 only (sequential window) | 46.79% | 54.79% |
| Idea 4 only (parallel shadow) | 65.36% | 74.46% |
| Ideas 3+4 integer shadow/window | 85.94% | 89.01% |
| **Ideas 2+3+4 Q3.4 shadow/window (40×4)** | **99.65%** | **99.67%** |
| Ideas 2+3+4 forward 10,8,16,6 | 98.78% | (not tested) |
| Ideas 2+3+4 forward 2,2,4,2 (16 cycles) | 96.30% | (not tested) |

The deterministic-LFSR-seed version of Stage A reported 256/256 "perfect" (pre=53 / 46 cycles); the randomized repeated solves of Stages B–D reveal a true success probability of about 96–99.7%.

### 3.2 4-bit SUM-only under-constrained inverse (31 SUMs × 1000)

| Configuration | Valid rate | Valid-pair coverage | Entropy | Zero-valid SUMs |
|---|---:|---:|---:|---:|
| **Direct integer baseline** | **85.95%** | 256/256 | 0.974 | 0 |
| Ideas 3+4 integer | 68.60% | 256/256 | 0.987 | 0 |
| Idea 4 only | 62.95% | 256/256 | 0.984 | 0 |
| Ideas 2+3+4 Q3.4 forward order (10,8,16,6) | 77.25% | 64/256 | 0.317 | 3 |
| Ideas 2+3+4 Q3.4 reverse order (40×4) | 76.70% | 194/256 | 0.726 | 0 |
| Ideas 2+4 Q3.4 parallel | 76.83% | 165/256 | 0.658 | 3 |

Conclusion: the shadow/window schemes are tuned for forward and constrained-inverse tasks and lose to the integer baseline on SUM-only sampling; Q3.4 raises the valid rate but collapses the distribution. This directly motivated the "energy landscape shaping" direction of Stages E/F.

### 3.3 8-bit (6 selected vectors × 100)

| Configuration | Hits on the six vectors |
|---|---|
| Direct integer baseline | 0, 67, 23, 71, 38, 61 /100 |
| Idea 2 only Q3.4 | 0, 100, 100, 0, 100, 0 (all-or-nothing, typical tanh saturation lock-in) |
| Ideas 3+4 integer | 70, 73, 63, 82, 67, 66 |
| **Ideas 2+3+4 Q3.4 (40×8)** | **100, 98, 100, 100, 100, 98** |

### 3.4 8-bit real inverse (former `test` branch, clamp B+SUM, 2000 cycles, 6 vectors × 100)

Integer HA/FA baseline 32.33% < 12 shadows (max7) 34.33% < 12 shadows (max2) 37.17% < **8-shadow carry Q16 42.33%**; least-node LP only 2.17%.

### 3.5 Final verdict per idea (consistent across stages)

- Idea 1 (equal gap): strongly positive for pure combinational logic (COMB6 64/64); not sufficient for the RCA.
- Idea 2 (large dynamic range / Q3.4 / FP8): negative alone (70.53%, 8-bit all-or-nothing); positive when combined with 3+4.
- Idea 3 (sequential window): semi-positive alone (46.79%, below baseline).
- Idea 4 (shadow carry): 65.36% alone; combined with 3 it is the key to RCA timing logic.
- Landscape optimization (E/F): static metrics (γ, smoothness, number of local minima) can be improved, but dynamic convergence improvement has not been demonstrated; 8 shadows still beat 12 shadows.

## 4. Unclear points / missing results

1. **The former `test` branch only has a README, no code or results**: `generic_optimizer.py`, `landscape_optimizer.py`, `compare_8bit_direct.py`, `least_node_lp_adder8.py`, `shadow_group_adder8.py`, `compare_backward_real8.py`, `visualize_shadow_vs_rca8.py`, `specs/ha_demo.json`, `out/*` are not in the repository. The numbers in table 3.4 are only available from the README text and cannot be re-checked.
2. **`out*/` of the 6-bit adaptive QP experiment is excluded by .gitignore**: the `full2`/`full3`/`adaptive_iter*` comparison (`comparison_summary.csv`), the convergence comparison (`convergence_comparison.csv`), and the results of `analyze_ab_failures`, `tiny4` and `edge_hypercut` are all missing; EXPERIMENT_LOG only records the single Stage3 hard-cut run of 2026-07-08 and explicitly states "no proven dynamic convergence improvement". The "5-bit experiment" mentioned in the README does not exist in the repository.
3. **Early evidence deleted from `main`**: the quick-summary CSVs of `04243d1`, `adder8_integer_baseline_diagnostics_transcript.txt`, `sim/*_trace.csv` and ModelSim work libraries were deleted in `bc2ac96`; the `scratch_shadow_j_sweep/` of `3575e71` (7 copy-J sweep traces + VHDL) was deleted in `8f512ce`. They can only be recovered from historical commits. The cleanup PR additionally removed the regenerable FP4/FP8/Q8 variant VHDL and scaled coefficient reports formerly under `sim/experiments/` (recoverable via `git show 8f512ce:sim/experiments/<file>`).
4. **No transcript for the SUM-only reverse-order 40×4 run**: `sum_only_aggregate.csv` has a `sum_idea234_q34_reverse40_4` row, but `traces/` contains no corresponding trace file.
5. **Shortened schedules (10,8,16,6 / 2,2,4,2) were only tested forward**, not for the constrained inverse; the 15 schedules in `idea234_forward_window_sweep.csv` are forward-only as well.
6. **The numerical differences between `time_dependent_annealing_report.md` and `report.md` are protocol differences, not contradictions** (deterministic LFSR seeds + frozen readout vs randomized scramble + repeated solves), but the reports themselves never present this side by side in one table.
7. **No fine-grained timing inside Stage A**: `04243d1` is a single large commit (402 files); the order of A1–A14 can only be inferred from the narrative order of the two reports and the COMB6 report date (05-24); the `adder8` baseline transcript end time 05-25 00:15 is the only hard timestamp.
8. **The FP8/Q8 split-carry series (~23 `optimized_*.json`) has no corresponding simulation result files**, only the one qualitative sentence in `time_dependent_annealing_report.md §4`: "underperformed… zero-hit cases remained".
9. The 8-bit presentation results are non-exhaustive (6 vectors); neither an exhaustive 8-bit forward test nor an 8-bit SUM-only test has been done.
10. `main` had no updates after 05-25 until the fast-forward of 2026-09-15; there was no PR or merge record between `test`/`codex` and `main` — the two later branches were integrated by a plain fast-forward and then deleted (see §1).

## 5. Main evidence files

- Commit history: `git log --stat` (6 commits, formerly 3 branches, linear)
- `README.md` (final `main` version and the `04243d1` original)
- `reports/presentation_8bit_rca/report.md` (and its diffs across `bc2ac96`→`3575e71`→`8f512ce`)
- `reports/presentation_8bit_rca/data/adder4_summary.csv`, `sum_only_aggregate.csv`, `idea234_forward_window_sweep.csv`, `adder8_repeated.csv`, `rca_energy_landscape_summary.csv`, `manifest.json`
- `reports/presentation_8bit_rca/traces/*.txt|*.log` (ModelSim `Start/End time` stamps)
- `reports/time_dependent_annealing_report.md`, `reports/comb6_equal_gap_report.md`
- `reports/coefficients/hamiltonians.{json,md}`, `reports/coefficients/comb6_e3m4_equal_gap.json`, `reports/coefficients/optimized_q34_shadow1_blocks.json`, `reports/coefficients/optimized_q34_shadow1_adder8_blocks.json`, `reports/coefficients/fp8_split_carry/optimized_*.json`
- Historical versions: `04243d1:reports/q34_*_quick_summary.csv`, `04243d1:reports/q34_sum_only_reverse_distribution_summary.csv`, `04243d1:reports/adder8_integer_baseline_diagnostics_transcript.txt`, `3575e71:reports/presentation_8bit_rca/scratch_shadow_j_sweep/data/shadow_copy_j_sweep_aggregate.csv`, `8f512ce:sim/experiments/*`
- Scripts: `scripts/run_presentation_rca_experiments.py`, `scripts/sweep_shadow_copy_j_sum.py`, `scripts/visualize_rca_energy_landscape.py`, `scripts/optimize_fp8_hamiltonians.py`, `scripts/generate_shadow1_q34_adder4.py`
- `experiments/quantized_landscape_optimizer/README.md`
- `experiments/multibody_hamiltonian_6bit_adaptive_qp/{README.md,EXPERIMENT_LOG.md,.gitignore,adaptive_qp_6bit.py,staged_cut_verifier.py,compare_adaptive23_convergence.py,...}`
