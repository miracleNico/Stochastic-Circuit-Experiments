# Experiment Timeline (stochastic_circuits / invertible stochastic logic gates)

Scope: the complete original experiment history, plus the 2026-09-16 optimizer successor, QuestaSim migration, fixed-seed simulator compatibility validation and local branch consolidation. Historical times are git commit times (author time = commit time, timezone -04:00), supplemented by simulator transcript stamps and dates written in the documents themselves. Historical letter labels are retained only as commit-era provenance; the current taxonomy is Stage 1–5 with alphabetic substages.

Current paths in this document use the numeric-stage `reorg` layout (Stage 4.C). Explicit `<commit>:<path>` references retain historical paths. Files deleted by the original experiment commits are marked as historical and can be recovered with `git show <commit>:<path>`.

## 0. Repository theme in one sentence

Following the spin-gate (p-bit / tanh update) model of Onizawa et al., *A Design Framework for Invertible Logic*, invertible stochastic logic gates (AND/OR/NAND/NOR/XOR/XNOR/FA) are implemented in VHDL and composed into 4/8-bit ripple-carry adders (RCA) and a bitcount, to study "how to make a composed RCA converge reliably in both forward and inverse (invertible) tasks". Later work turned to Gurobi-based optimization of the Hamiltonian "energy landscape" with continuous / quantized coefficients.

## 1. Historical branch notes

The original six-commit experiment history through `a50e26d` was completely linear:

```text
04243d1 (05-25 00:19) -> bc2ac96 (05-25 03:22) -> 3575e71 (05-25 04:32) -> 8f512ce (05-25 07:03)
                                                                                |
                                                                                v
                                                                   a0998af (06-11 03:55)  [formerly branch test]
                                                                                |
                                                                                v
                                                                   a50e26d (07-30 00:59)  [formerly branch codex/quantized-landscape-optimizer]
```

| Historical branch tip | Based on | Pre-consolidation tip | Purpose | Status |
|---|---|---|---|---|
| `main` | — | `8f512ce` 2026-05-25 07:03 | VHDL gate library + the "timing window + shadow carry + Q3.4 weights" demonstration study for the 4/8-bit RCA, producing `results_and_reports/stage2/rca_convergence_benchmark/report.md` | Completed/stable (all 4 commits on 05-25) |
| `test` | `main` (1 commit after `8f512ce`) | `a0998af` 2026-06-11 03:55 | Documentation (README only) for the "quantized Hamiltonian landscape optimizer" experiments | Documentation only; the 7 scripts and `out/` results referenced by the README were never committed |
| `codex/quantized-landscape-optimizer` | `test` (1 commit after `a0998af`) | `a50e26d` 2026-07-30 00:59 | Continuous-float 2/3/4-body QP optimization (Gurobi) of a 6-bit least-node + 6-shadow-carry adder, including the Stage3 hard-cut experiment | Code + README + EXPERIMENT_LOG committed; `out*/` results excluded by .gitignore |

Repository consolidation state (2026-09-16–17):

- The checkout initially exposed only `codex/quantized-landscape-optimizer`; no local `main` or `test` ref existed. The historical tips were nevertheless already in one ancestor chain: `8f512ce` → `a0998af` → `a50e26d`, so replaying merge commits would have added no content.
- `main` was created at the migration/consolidation commit `6ed61d9`, force-pushed at the user's direction, and retains all original experiment commits in its ancestry. The local `codex/quantized-landscape-optimizer` ref was deleted; `test` was already absent.
- The three obsolete remote experiment branches were deleted. A later `reorg` baseline was published at `443b3c0`; the numeric-stage and terminology work in this document continues from that commit on the local `reorg` branch. A live `git ls-remote --heads origin` check on 2026-09-17 listed `main` and `reorg` only.
- The two later historical tips only added files under `experiments/`; they did not modify files that already existed at `8f512ce` (`git diff 8f512ce a50e26d -- README.md .gitignore` is empty).
- Stage 3.B adds a new, independently reconstructed generic optimizer successor. Stage 4 adds the QuestaSim runner and fixed-seed compatibility evidence. Neither is recovered historical optimizer source or a new scientific reproduction experiment.

## 2. Experiment timeline in chronological order

### Stage 1: component and architecture development (historical Stage A) (≤ 2026-05-24, committed in `04243d1` 2026-05-25 00:19)

`04243d1 gates,4bRCA,8bRCA,bitcounter` (402 files, 676k lines, including many ModelSim work libraries and trace CSVs)

| Sub-experiment | Goal / hypothesis | Method / key change | Result | Evidence |
|---|---|---|---|---|
| 1.A.1 Basic gate RTL | Reproduce the paper's spin gates | `src/spin_node.vhd`, `inv_and_gate.vhd`, `inv_xor_gate.vhd` (XOR implemented as a 4-node half adder); 8-bit tanh LUT + LFSR | Small-gate assertion tests pass; AND inverse with Y=0 gives AB∈{00,01,10} each ≈1/3 | `README.md`, `sim/*_ab_probabilities.csv` (deleted later in bc2ac96) |
| 1.A.2 Generator + exhaustive verification | Generate OR/NAND/NOR/XNOR/FA/ADDER8/BITCOUNT8 from coefficient tables | `scripts/stage1/A_primitive_spin_gate_validation/generate_hamiltonians.py`, `verify_hamiltonians.py` (exhaustive over 3/4/5-node blocks, 4096 bitcount states, 65536 8-bit adder states) | Exhaustive structural correctness passes | `results_and_reports/stage1/A_primitive_spin_gate_validation/hamiltonians.md`, `results_and_reports/stage1/A_primitive_spin_gate_validation/hamiltonians.json` |
| 1.B.1 FP4/FP8/Q8 dynamic-range sweep (early form of quantized coefficient scaling) | Does larger dynamic range / larger gate gap improve convergence? | `generate_hamiltonians.py --weight-frac-bits/--weight-scale`; `optimize_fp8_hamiltonians.py` MILP: maximize HA/FA valid/invalid gap, then minimize carry-boundary coefficients; emits a split-carry weak-equality-link topology | ~23 `optimized_fp8_e3m4/e4m3/fixed_q8_*_link_*.json` files under `reports/` and corresponding generated VHDL under `sim/experiments/`; `time_dependent_annealing_report.md §4`: the fixed-Q8 split-copy branch "underperformed the integer/shadow schedules, zero-hit cases remained" → quantized coefficient scaling alone is negative | `reports/optimized_*.json`, `sim/experiments/`, `results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/time_dependent_annealing_report.md` |
| 1.C.1 COMB6 equal gap (intra-block gap equalization) | Is unifying intra-block gaps beneficial in combinational logic? | `COMB6_MIXED` 6-in 4-out 21-spin network; E3M4 encoding raises the XOR/XNOR gap from 2 to 4 (physical) | Integer baseline RND=1 SETTLE=1000: 21/64 match, 39 zero-hit; SETTLE=20000: 50/64; E3M4 RND=16 SETTLE=1000: 57/64; SETTLE=5000: 62/64; SETTLE=20000: **64/64, min 997/1000** → intra-block gap equalization strongly positive for pure combinational logic | Historical `results_and_reports/stage1/C_combinational_gap_equalization/comb6_equal_gap_report.md` was dated 2026-05-24; the current file contains the Stage 4.B Questa compatibility evidence. Coefficients: `results_and_reports/stage1/C_combinational_gap_equalization/comb6_e3m4_equal_gap.json`; VHDL: `experiments/stage1/C_combinational_gap_equalization/hardware/generated_networks_comb6_e3m4_equal_gap.vhd` |
| 1.D.1 Static integer 4-bit RCA baseline | Can directly coupled HA/FA converge? | 16 vectors, COUNT=100 | settle=128: avg 22.9, min 0; settle=500: avg 78.0, min 0 → the failure is a timing problem, not a local-gap problem | `time_dependent_annealing_report.md §3` |
| 1.D.2 Carry-ordered block scheduling alone (sequential annealing windows) | Activate stages in carry order | Asymmetric integer windows, pre=212 | avg 93.8/100, min 0, perfect 15/16 → semi-positive | same, §5 |
| 1.D.3 Scheduled auxiliary-carry architecture, integer shadow latch | Shadow node q separates carry generation and consumption | `c_i -> q_{i+1} -> FA cin`; schedule B0=10,copy1,B1=16,copy1,B2=16,copy1,B3=8 (pre=53), block_rnd=1 | **Exhaustive 256/256 perfect, 256000/256000, q matches 1000/1000** | same, §5; `scripts/stage1/D_scheduled_auxiliary_carry_rca/generate_shadow1_adder4.py`, `sim_scripts/stage1/D_scheduled_auxiliary_carry_rca/tb/tb_adder4_shadow1_exhaustive.vhd` |
| 1.D.4 Quantized scheduled auxiliary-carry architecture, Q3.4 shadow latch | Add Q3.4 (1s3d4f) MILP-optimized coefficients on top of 3+4 | HA h=[56,56,-56,-112] (physical /16), gate gap 112=7.0, copy=64=4.0. First run block_rnd=16, copy=2: perfect 128/256 (failure mode top_sum=expected+1); retuned to B0=10,B1=8,B2=16,B3=6, copy=2, block_rnd=0 (pre=46) | **Exhaustive 256/256 perfect**; pre reduced from 53 to 46 | same, §6; `results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/optimized_q34_shadow1_blocks.json`, `scripts/stage1/D_scheduled_auxiliary_carry_rca/generate_shadow1_q34_adder4.py` |
| 1.D.5 Q3.4 small-noise check | Can a small random-field noise be reintroduced? | block_rnd=4(0.25)/8(0.5), COUNT=100 | Forward: rnd=4 → 256/256; rnd=8 → 128/256. Constrained inverse B+SUM→A: rnd=4 → 256/256; rnd=8 → 176/256. Recommended operating point block_rnd=4 | `reports/q34_forward_noise_quick_summary.csv`, `q34_inverse_forward_noise_quick_summary.csv` (both deleted in bc2ac96) |
| 1.D.6 Inverse behaviour (constrained inverse / SUM-only) | Is the shadow latch invertible? | Fixed a generator bug (a*/b* not updated when unclamped); noise-free Q3.4 schedule | Constrained inverse B+SUM→A: 256/256; SUM-only: perfect 24/31, 7 SUM failures; with noise rnd=16 the inverse degrades to 176/256 and SUM-only to 18/31 | `time_dependent_annealing_report.md §7` |
| 1.D.7 SUM-only reverse-order schedule | Does reversing block activation order help the under-constrained inverse? | B3→q3→B2→…→B0; 1000 trials/SUM | Forward order valid 23864/31000 vs reverse order 23637/31000 (not better globally; 5 SUMs improved, 24 worse, 2 tied); but boundary cases: SUM=4 143→587, SUM=25 850→982, SUM=29 0→223; SUM=0/1/30 still 0 | `reports/q34_sum_only_reverse_distribution_summary.csv` (deleted in bc2ac96), report §7 |
| 1.D.8 Reverse-order schedule + noise, constrained inverse | — | reverse=true, rnd=4/8 | B+SUM only 10/256 perfect, SUM-only 6/31 or 4/31 → reverse order is severely harmful for the constrained inverse | `reports/q34_inverse_reverse_noise_quick_summary.csv` (deleted in bc2ac96) |
| 1.D.9 8-bit composed RCA extension | Does 2+3+4 transfer to 8-bit (39 nodes)? | Old integer gen_adder8: 15+1 and 170+85 both 0/1000; short schedule 10,8,16,6,8,8,16,6 copy=2 rnd=4: perfect 7/32; **40×8 copy=2 rnd=4: 32/32** (pre=334); boundaries: blocks=39 → 15/32; copy=1 → 15/32; rnd=0 blocks=32 → 32/32 | Forward transfer succeeds but needs roughly one 39-node scheduling period of relaxation per stage | `time_dependent_annealing_report.md §8`, `reports/adder8_integer_baseline_diagnostics_transcript.txt` (deleted in bc2ac96; ModelSim end time 05-25 00:15) |
| 1.D.10 "Why the RCA readout looks deterministic" + repeated-solve check | Clarify that a frozen readout of 1000/1000 ≠ probability 1 | 8-bit Q3.4 shadow RCA; per trial: unclamp → 80-cycle scramble (rnd=8) → clamp → solve once → sample once; 200 trials/vector | 37+219: 197/200; 142+73: 198; 201+54: 196; 91+188: 199; 6+177: 200; 127+1: 198 → high but non-unity success probability | report §9 (appended in bc2ac96, 133 lines) |

### Stage 2.A: randomized RCA convergence (historical Stage B) (ModelSim 2026-05-25 02:05–02:36; committed in `bc2ac96` 03:22)

`bc2ac96 presentation version` (230 files; deleted sim/work libraries, old quick CSVs and traces; added `scripts/stage2/run_rca_convergence_benchmark.py` 1138 lines, `results_and_reports/stage2/rca_convergence_benchmark/`)

Method change: all 4-bit tests are exhaustive over the 256 (A,B) pairs with 100 random trajectories per case (OS-random seed salt + 80-cycle scramble); 8-bit uses 6 selected vectors × 100. This responds to the "deterministic LFSR seed" risk of Stage 1. The ModelSim end times below come from the historical `bc2ac96` evidence; the current report trace files were transactionally replaced by the Stage 4.B Questa compatibility run of those now-frozen generated VHDL seeds.

| ModelSim end time | Run | Forward success | Constrained inverse B+SUM→A |
|---|---|---:|---:|
| 02:10:44 | baseline direct 4-bit (integer) | 85.69% (21937/25600), min 41 | n/a |
| 02:15:03 | scheduled auxiliary-carry architecture integer shadow (40,40,40,40 copy=2) | 85.94% (22001), min 67 | 89.01% (22787) |
| 02:20:04 | quantized coefficient scaling only, Q3.4 direct | 70.53% (18056), min 0, 162 non-perfect cases | n/a |
| 02:24:06 | carry-ordered block scheduling only, sequential window | 46.79% (11977) | 54.79% (14027) |
| 02:28:20 | auxiliary carry-state decoupling only, parallel shadow (settle 160) | 65.36% (16732) | 74.46% (19061) |
| 02:29:58–02:35:54 | 8-bit companion checks (baseline / quantized coefficients / scheduled auxiliary-carry / QSAC) | see §3.3 | — |
| (bc2ac96 version) | quantized scheduled auxiliary-carry architecture Q3.4 shadow (schedule 10,8,16,6 at that time) | 98.64% (25251), min 92 | 99.62% (25502) |

Conclusion (as of bc2ac96): quantized coefficient scaling alone is the clearest negative control; QSAC is the only strongly positive result.

### Stage 2.B: SUM-conditioned inverse sampling (historical Stage C) (2026-05-25 03:34–04:05; committed in `3575e71` 04:32)

`3575e71 updated presentation version` (43 files, +21.6k lines)

| Time | Sub-experiment | Goal | Result |
|---|---|---|---|
| 03:34:42 | SUM-only scheduled auxiliary-carry architecture integer | Clamp only the 5-bit SUM, A and B fully free, 31 SUMs × 1000 | valid 68.60%, coverage 256/256, entropy 0.987 |
| 03:35:40 | SUM-only quantized scheduled auxiliary-carry architecture Q3.4 (forward order 10,8,16,6) | same | valid 77.25%, **coverage only 64/256**, entropy 0.317, 3 zero-valid SUMs |
| 03:37:50 | SUM-only auxiliary carry-state decoupling only, parallel shadow | same | valid 62.95%, coverage 256/256 |
| 03:39:53 | SUM-only quantized auxiliary-carry decoupling Q3.4 parallel shadow | same | valid 76.83%, coverage 165/256, 3 zero-valid SUMs |
| 04:05:13 | SUM-only baseline direct integer | same | **valid 85.95%, coverage 256/256, entropy 0.974** → the direct integer baseline is strongest on this metric |
| (scratch, later deleted) | Shadow copy-J sweep `scripts/stage2/B_sum_conditioned_inverse_sampling/sweep_auxiliary_carry_coupling.py` | Sweep (c→q, q→c) physical couplings (3,3),(2,2),(1,1),(1,4),(2,3),(3,2),(2,1), Q3.4 quantized auxiliary-carry decoupling parallel, 200 trials/SUM | valid rate 53.8%–74.0%, coverage 30%–98%; (1,4) has the best coverage 252/256 but valid 55.1%; (2,1) has the highest valid 74.0% with coverage 147/256 → valid rate and coverage trade off; the result directory `scratch_shadow_j_sweep/` was deleted in 8f512ce and added to .gitignore |
| — | RCA energy landscape visualization `scripts/stage2/A_randomized_rca_convergence/visualize_rca_energy_landscape.py` | Full-cube energies before/after quantization | 4-bit: integer valid −16 / invalid −14 gap 2 → Q3.4 −56/−49 gap 7.0; 8-bit: gap 2 → 7.0 |

Also added `tb_adder4_direct_sum_randomized_distribution.vhd`, `tb_adder4_shadow1_sum_randomized_distribution.vhd`; report.md gained §7 "Clamp SUM-Only Inverse Test". The README first showed the SUM-only table.

### Stage 2.C: schedule reduction and readout validation (historical Stage D) (2026-05-25 06:30–06:48; committed in `8f512ce` 07:03)

`8f512ce Finalize RCA presentation experiments` (49 files; deleted scratch sweeps and .pyc, added `.gitignore`)

| Time | Sub-experiment | Goal | Result |
|---|---|---|---|
| — | AND gate single-cycle sanity (`sim_scripts/stage2/C_schedule_reduction_and_readout_validation/tb/tb_and_onecycle_sanity.vhd`, `sim_scripts/stage2/C_schedule_reduction_and_readout_validation/run_and_onecycle_sanity.*`) | Check whether a "1-cycle clamp/readout" is trustworthy | Found that an unclamped output at that clock edge may still reflect the previous input → introduced the corrected protocol "pre-warm clamped inputs for 1 clock + delayed readout after the edge"; the `1,1,1,1` schedule was excluded |
| 06:30:18–06:32:06 | Quantized scheduled auxiliary-carry architecture forward window reduction (corrected protocol) `quantized_scheduled_auxiliary_carry_window_sweep.csv`, 15 schedules | How short can the schedule get while staying above baseline? | 1,1,2,1 (11 cycles) 93.23%; 2,2,4,2 (16) **96.30%**; 4,4,4,4 (22) 97.40%; 10,8,16,6 (46) **98.78%**; 40,40,40,40 (166) **99.65%**; all above the 85.69% baseline |
| 06:47:30 | Quantized scheduled auxiliary-carry architecture main comparison rerun (40,40,40,40 copy=2) | Use the same hyperparameters for forward and constrained inverse | Forward **99.65% (25511/25600), min 97, 77 non-perfect cases**; inverse **99.67% (25516/25600), min 98** (replacing bc2ac96's 98.64%/99.62%) |
| — | SUM-only quantized scheduled auxiliary-carry architecture reverse order (40,40,40,40) | Fix the distribution collapse of forward-order Q3.4 | valid 76.70%, coverage **194/256**, zero-valid SUMs 0; but SUM=0 only 8.8%, SUM=30 20.0%, still behind the direct baseline |

report.md wording was also "depersonalized" (e.g. "honest result" → "result is mixed", "My future research goal" → "Future work").

### Stage 3.A: historical quantized landscape optimizer (historical Stage E) (runs approx. 2026-06-01–06-10, committed in `a0998af` 2026-06-11 03:55, former branch `test`)

At this historical commit only `experiments/stage3/README.md` (316 lines) was added. The original scripts and `out/` results were never committed. Goal: not only make coefficients logically correct but make the "energy landscape" sampler-friendly (valid states at the same energy level + TV-smooth one-bit neighbours of invalid states + trap cutting planes), and extend landscape optimization from local HA/FA blocks to the clamp-SUM subspace of the whole RCA. Stage 3.B adds a generic finite-state pairwise successor whose reconstructed and validated scope is currently HA/FA only, but it is not the lost Stage 3.A source and does not recreate the specialized RCA4/RCA8 studies.

| Sub-experiment (historical script names; none committed in Stage 3.A) | Method | Result |
|---|---|---|
| historical `generic_optimizer.py` / `landscape_optimizer.py` | Convex QP continuous solve → quantize → exhaustive verification → add post-quantization invalid local minima as "fixed-parent descent cuts" for the next round; `optimize-rca4` adds trap penalties for the 4-bit RCA (weighted by flip distance to a valid state, default inverse-square) | README has only command lines, no numerical results. The file now named `generic_optimizer.py` is the Stage 3.B successor, not a recovered copy of this historical implementation |
| `compare_8bit_direct.py` | Plain HA/FA 8-bit direct RCA, FP16 vs Q3.4 coefficients; paper-anneal noise schedule n=0.6745·mean(s_i) | Only output files described, no numbers |
| `least_node_lp_adder8.py` (paper-style 25-node least-node LP, seed 20260602) | `max|h|,|J| ≤ 2` | Exact global gap collapses to **1/8192 ≈ 1.22e-4** (binary-weight scaling problem of H=α(A+B−S)²) → extremely weak dynamically |
| `shadow_group_adder8.py` shadow topologies (group4 / carry8 / carry8group4; seeds 20260601, 20260610) | Gurobi QP penalizing valid-energy variance, one-bit roughness variance, coefficient L2, 2 rounds of cutting planes | 12 shadows coeff-max=7 actual max|J|=0.7335, max|h|=0.3482, γ=1.0, valid_dev_max 0.7773, tv_mean 2.466; distinguishes "strict sampling gap" from "projection-visible gap" |
| `compare_backward_real8.py` real inverse RCA8 (clamp B+SUM, Q*.16 quantization, paper-ssa update, 2000 cycles, 6 vectors × 100, seed 20260609) | — | Integer HA/FA baseline **32.33%**; least-node LP Q16 **2.17%**; 8-shadow carry Q16 **42.33%** (best); 12 shadows coeff-max=2 37.17%; coeff-max=7 34.33% |
| `visualize_shadow_vs_rca8.py` projected inverse landscape | — | Integer RCA8: mean/min inverse gap 2.000/2.000, one-bit jump 1.370, invalid local minima 10.67; 12 shadows max=2: 0.541/0.127/0.449/3.00; max=7: 0.588/0.223/0.451/3.50 → smoother but smaller gap, no dynamic improvement |

### Stage 5.A: 6-bit adaptive multibody Hamiltonian (historical Stage F) (runs 2026-07-07–07-08, committed in `a50e26d` 2026-07-30 00:59, former branch `codex/quantized-landscape-optimizer`)

Added `experiments/stage5/A_adaptive_multibody_hamiltonian/`: 7 Python scripts (3.5k lines), README, EXPERIMENT_LOG, .gitignore (excludes `out*/`, `*.log`). Pure Python/Gurobi continuous float64, not VHDL.

| Sub-experiment | Method | Result |
|---|---|---|
| `adaptive_qp_6bit.py run-all`: full2 (325 1/2-body coefficients) → full3 (2625 1/2/3-body) → adaptive_iter* (assign 50%/30%/20% of nodes to the highest 2/3/4 orders by node score) | Soft-valid QP: −γ + 20000/|V|·Σ(H(v)−E0)² + 200000/|V|·Σmax(|H−E0|−0.5,0)² + 100·roughness + 0.1/|T|·‖θ‖², s.t. invalid cuts H(u) ≥ E0+γ, |θ|≤2; Walsh–Hadamard exhaustive audit over 2²⁵ states | README only gives the workflow; no committed numbers (`out/` ignored). README mentions "the same QP as the 5-bit experiment", but the repository has no 5-bit experiment |
| `compare_adaptive23_convergence.py` / `compare_paper_ssa_solutions.py` (seed 2026070701) | Paper SSA/SSAU local-energy-distribution hyperparameter n_rnd=0.6745·mean(s_i), I0 grows geometrically from 0.01·max(s)+min|μ| to 2·max(s)+min|μ|, optional exponential noise decay; numba acceleration | No committed numbers |
| `analyze_ab_failures.py`, `tiny4_experiment.py`, `edge_hypercut_experiment.py` | Failure analysis, critical-node classification, edge/hyperedge cuts | No committed numbers |
| **`staged_cut_verifier.py --stage stage3 --stage3-cut-sum-sum --stage3-cut-output-siblings --max-rounds 4 --gurobi-threads 16`** (EXPERIMENT_LOG 2026-07-08) | Hard-cut 27 SUM–SUM and SUM–next-carry/output-sibling 2-body terms before optimization; limited to 2/3-body; Gurobi 16 threads (12C/24T machine) | Critical nodes s6, c4, c6; 2083 terms (1-body 25, 2-body 273, 3-body 1785, 515 triples rejected by hard cuts); cutting planes converge in 4 rounds: violations 100774 → 8438 → 71 → **0**, γ ≈ 2.499e-5, minimum invalid gap 2.497e-5; exhaustive audit over 33,554,432 states, **0 violations**, valid std 4.6e-9, **1642 invalid local minima**, 1376 non-zero terms. Conclusion: statically feasible, but no proven dynamic convergence improvement; needs Stage4 or a revised option strategy |

### Stage 3.B, Stage 4 and Stage 5.B: optimizer successor, simulator migration and RTL readiness (historical Stage G; 2026-09-16 consolidation)

The recovery audit confirmed that the original Stage 3.A optimizer source and saved solutions cannot be reconstructed byte-for-byte from any reachable commit: `a0998af` contains only the README, while the specialized scripts and `out/` artifacts were never committed. The implementation therefore adds a clearly labelled Stage 3.B successor rather than pretending to recover the missing program. The fixed-seed Questa work is classified under Stage 4 solely as simulator-migration validation.

| Sub-experiment / implementation | Method | Result |
|---|---|---|
| 3.B.1 Optimizer provenance and scope gate | Search the linear git history and current checkout for the seven Stage 3.A scripts, specs, saved solutions and result directories; keep the historical README as an archive | Original Stage 3.A implementation remains unrecoverable. The new engine accepts explicit finite pairwise state-space specifications, but the reconstructed and validated scope is HA/FA only; it does **not** claim to reproduce the historical RCA4/RCA8, least-node, shadow-node, backward-sampling or visualization programs |
| 3.B.2 Verified pairwise optimizer successor | New NumPy-only `generic_optimizer.py`; portable JSON specs; hard equal-valid-energy manifold eliminated through an SVD null space; OSQP-style ADMM convex QP; lattice quantization; exhaustive state audit; deterministic fixed-parent descent cuts for post-quantization invalid local minima | Runnable HA and FA demos plus `solve-spec`; malformed topology and failed convergence are hard errors; 16 optimizer/export/evidence tests pass. The implementation needs no SciPy, CVXPY, Gurobi or license |
| 3.B.3 Static optimizer-to-RTL Questa audit | Export temporary VHDL coefficient package from optimizer JSON, parse current `experiments/stage1/A_primitive_spin_gate_validation/hardware/generated_networks.vhd`, require exact RTL coefficient proportionality, then enumerate all 16 HA and 32 FA states in `tb_optimizer_energy_audit.vhd` | Optimizer HA/FA: valid energy **−2**, gap **1**, invalid local minima **0**. Current RTL HA/FA: valid energy **−4**, gap **2**, invalid local minima **0**. Every state is an exact **×2** energy scaling and the legal manifold/local-minimum structure is unchanged; Questa reports 0 errors, 0 warnings |
| 3.B.4 Dynamic primitive-gate Questa audit | Compile the generated gates and `tb_generated_gates`; accept only stable semantic report markers, not process exit alone | `tb_generated_gates passed`; all four HA/XOR forward cases, two reverse cases and eight FA forward cases pass; 0 errors, 0 warnings |
| 4.A ModelSim → QuestaSim mainline migration | QuestaSim 2024.1 becomes default while retaining `vcom/vsim/.do`; common runner resolves product/license deterministically, injects license state only into the child, copies only the selected vendor's `modelsim.ini`, isolates every run, records redacted hashes/metadata, and normalizes exit codes. ModelSim is explicit legacy only; no `qrun`, CI or Verilator/cocotb change | Runner/failure/trace tests pass; compile/elaboration/assertion failures classify as 50/51/52; batch runs have no WLF by default; trace CSV/PNG stay run-local. All business `.do` files use `sim_common.do`; the dedicated launcher and old tracked ini are archived under `legacy/modelsim/`; the ini is never a runtime fallback |
| 4.B Fixed-seed simulator compatibility validation | The safe validation driver checks 11 committed VHDL hashes and seed signatures, prohibits salt regeneration, stages all outputs, checks exact integer goldens and publishes only after all 25 simulations pass. Only the historical integer scheduled auxiliary-carry case uses `-LegacyReplayTiming`; Q3.4 and shortened schedules use the corrected protocol | All 25 runs pass on QuestaSim 2024.1 and match the accepted values exactly. This verifies simulator migration for the committed sources and seeds; it is not a new experiment, does not recover a historical transcript, and makes no cross-seed robustness claim |
| 5.B 6-bit multibody RTL readiness gate | Before Q3.29/Q3.37 quantization or RTL, require the exact Stage 5.A solution JSON, term support, active cuts, audit payload and SHA-256 identities | Gate fails because only the aggregate experiment log survived. No speculative term ROM, local-field core or scheduler was generated. The admissible conclusion remains: **the static gap can close, but dynamic improvement is not proven** |
| 4.C Repository and legacy consolidation | Verify the historical tips by ancestry; make the migration commit the sole local `main` tip; archive the explicit ModelSim launcher/configuration without moving the shared Questa-compatible `.do` files | The old experiment commits stay reachable from `main`; the numeric-stage reorganization is performed later on local `reorg` |

### Stage 4.C — Repository taxonomy and consolidation (historical Stage H) (2026-09-16–17, `reorg`)

The Questa migration was saved on `main` as `6ed61d9` before branching. GitHub
`main` was verified at that commit. On explicit request, the remote branches
`codex/quantized-landscape-optimizer-20260916` (`a50e26d`),
`cursor/experiment-e0-e1-plan-b98b` (`910e322`) and
`cursor/timeline-e0-e1-audit-50af` (`969f59a`) were deleted. A subsequent
`reorg` baseline was published at `443b3c0`; on 2026-09-17,
`git ls-remote --heads origin` listed `main` at `6ed61d9` and `reorg` at
`443b3c0`. The current numeric-stage changes are committed locally on top of
that baseline; `main` remains unchanged. The branch deletions remove names, not
the historical commits identified above. No merge or recovery of the cursor
branches is claimed.

The [experiment index](experiments/README.md) maps the history into five numeric
stages with alphabetic substages. Documentation/specs/hardware belong under
`experiments/stageN/<substage>/`, Python tools under `scripts/`, Questa launchers
plus `tb/` under `sim_scripts/`, and results under `results_and_reports/`. Shared
`src/` contains only the five reusable primitive VHDL files. Stages 2.A–2.C share
the `rca_convergence_benchmark` evidence tree because they use the same frozen
sources, manifest and integrated report.

350 files were relocated. All 122 moved VHDL files and 55 CSV/SVG/PNG/raw-trace
files retain their original bytes. `.gitattributes` pins their original checkout
line-ending styles so automatic conversion cannot invalidate fixed-input SHA-256 values.
Default simulator outputs now go under each experiment's ignored `runs/`; core
staging uses `results_and_reports/stage4/B_fixed_seed_compatibility_validation/runs/`. Report publication
replaces only curated evidence, preserving unrelated `runs/` and scratch data.
ModelSim remains explicitly legacy under `legacy/modelsim/`.

The optimizer's layout changes do not change its mathematical method or its
Stage 3.B status: it is a reconstructed pairwise successor, not the lost Stage
3.A RCA optimizer. Matplotlib was installed into project-local `.venv`; Stage
5.A's `unit-check` passes, but missing solution coefficients still block the
Stage 5.B RTL handoff. The user-supplied graph-cut brainstorm and formulation
image are tracked inside Stage 5.A. No new dynamic-improvement claim is
introduced. All 25 relocated Questa runs pass the original exact goldens as a
Stage 4.B migration check; curated historical evidence was not overwritten.

Validation details and final regression status are recorded in
[the reorganization check report](results_and_reports/stage4/B_fixed_seed_compatibility_validation/reorg_validation.md).

## 3. Result summary and comparison

### 3.1 4-bit RCA forward / constrained inverse (exhaustive 256 cases × 100 random trajectories, final `main` version)

| Configuration | Forward | Constrained inverse B+SUM→A |
|---|---:|---:|
| Direct integer baseline | 85.69% | n/a |
| Quantized coefficient scaling only (Q3.4 direct) | 70.53% (negative control) | n/a |
| Carry-ordered block scheduling only (sequential window) | 46.79% | 54.79% |
| Auxiliary carry-state decoupling only (parallel shadow) | 65.36% | 74.46% |
| Scheduled auxiliary-carry architecture integer shadow/window | 85.94% | 89.01% |
| **Quantized scheduled auxiliary-carry architecture Q3.4 shadow/window (40×4)** | **99.65%** | **99.67%** |
| Quantized scheduled auxiliary-carry architecture forward 10,8,16,6 | 98.78% | (not tested) |
| Quantized scheduled auxiliary-carry architecture forward 2,2,4,2 (16 cycles) | 96.30% | (not tested) |

The deterministic-LFSR-seed version of Stage 1 reported 256/256 "perfect" (pre=53 / 46 cycles); the randomized repeated solves of Stages 2.A–2.C reveal a success probability of about 96–99.7% for the tested seeds.

### 3.2 4-bit SUM-only under-constrained inverse (31 SUMs × 1000)

| Configuration | Valid rate | Valid-pair coverage | Entropy | Zero-valid SUMs |
|---|---:|---:|---:|---:|
| **Direct integer baseline** | **85.95%** | 256/256 | 0.974 | 0 |
| Scheduled auxiliary-carry architecture integer | 68.60% | 256/256 | 0.987 | 0 |
| Auxiliary carry-state decoupling only | 62.95% | 256/256 | 0.984 | 0 |
| Quantized scheduled auxiliary-carry architecture Q3.4 forward order (10,8,16,6) | 77.25% | 64/256 | 0.317 | 3 |
| Quantized scheduled auxiliary-carry architecture Q3.4 reverse order (40×4) | 76.70% | 194/256 | 0.726 | 0 |
| Quantized auxiliary-carry decoupling Q3.4 parallel | 76.83% | 165/256 | 0.658 | 3 |

Conclusion: the shadow/window schemes are tuned for forward and constrained-inverse tasks and lose to the integer baseline on SUM-only sampling; Q3.4 raises the valid rate but collapses the distribution. This directly motivated the energy-landscape work in Stages 3 and 5.

### 3.3 8-bit (6 selected vectors × 100)

| Configuration | Hits on the six vectors |
|---|---|
| Direct integer baseline | 0, 67, 23, 71, 38, 61 /100 |
| Quantized coefficient scaling only Q3.4 | 0, 100, 100, 0, 100, 0 (all-or-nothing, typical tanh saturation lock-in) |
| Scheduled auxiliary-carry architecture integer | 70, 73, 63, 82, 67, 66 |
| **Quantized scheduled auxiliary-carry architecture Q3.4 (40×8)** | **100, 98, 100, 100, 100, 98** |

### 3.4 8-bit real inverse (former `test` branch, clamp B+SUM, 2000 cycles, 6 vectors × 100)

Integer HA/FA baseline 32.33% < 12 shadows (max7) 34.33% < 12 shadows (max2) 37.17% < **8-shadow carry Q16 42.33%**; least-node LP only 2.17%.

### 3.5 Final verdict per mechanism

- Intra-block gap equalization (equal gap): strongly positive for pure combinational logic (COMB6 64/64); not sufficient for the RCA.
- Quantized coefficient scaling (large dynamic range / Q3.4 / FP8): negative alone (70.53%, 8-bit all-or-nothing); positive when combined with 3+4.
- Carry-ordered block scheduling (sequential window): semi-positive alone (46.79%, below baseline).
- Auxiliary carry-state decoupling (shadow carry): 65.36% alone; combined with 3 it is the key to RCA timing logic.
- Historical landscape optimization (Stages 3.A and 5.A): static metrics (γ, smoothness, number of local minima) can be improved, but dynamic convergence improvement has not been demonstrated; 8 shadows still beat 12 shadows.
- Verified pairwise optimizer successor (Stage 3.B): the generic pairwise engine is runnable and exhaustively verifies its configured state space before and after quantization; current Questa evidence is limited to HA/FA. It proves an exact ×2 relationship to current RTL, not recovery of the missing Stage 3.A RCA optimizers or evidence of improved multibody dynamics.

## 4. Remaining limitations and provenance gaps

1. **The historical Stage 3.A implementation is still missing, although a Stage 3.B successor now exists**: the former `test` branch contains only its README. The current `generic_optimizer.py`, `specs/ha_demo.json`, exporter and Questa audits are new successor artifacts; they are not recovered versions of the historical generic/RCA scripts. `landscape_optimizer.py`, `compare_8bit_direct.py`, `least_node_lp_adder8.py`, `shadow_group_adder8.py`, `compare_backward_real8.py`, `visualize_shadow_vs_rca8.py` and historical `out/*` remain absent. The Stage 3.A RCA8 numbers in §3.4 are still README-only and cannot be independently rechecked.
2. **`out*/` of the 6-bit adaptive QP experiment is excluded by `.gitignore`**: the concrete Stage3 solution vector, term support, active cuts, machine-readable exhaustive audit and their SHA-256 identities are missing, as are the `full2`/`full3`/`adaptive_iter*` and convergence comparisons. The 2026-09-16 preflight therefore stopped the Q3.29/Q3.37 and RTL phase. `EXPERIMENT_LOG.md` records only the aggregate Stage3 hard-cut result and explicitly states "no proven dynamic convergence improvement". The "5-bit experiment" mentioned in the README does not exist in the repository.
3. **Early evidence deleted from the original history**: the quick-summary CSVs of `04243d1`, `adder8_integer_baseline_diagnostics_transcript.txt`, `sim/*_trace.csv` and ModelSim work libraries were deleted in `bc2ac96`; the `scratch_shadow_j_sweep/` of `3575e71` (7 copy-J sweep traces + VHDL) was deleted in `8f512ce`. They can only be recovered from historical commits. The regenerable FP4/FP8/Q8 coefficient and VHDL variants that now live under `results_and_reports/stage1/B_quantized_coefficient_exploration/` and `experiments/stage1/B_quantized_coefficient_exploration/hardware/` are inputs, not dynamic result evidence.
4. **Shortened schedules (10,8,16,6 / 2,2,4,2) were only tested forward**, not for the constrained inverse. Stage 4.B republishes only these two key short schedules plus the 40×4 main schedule for migration compatibility; the other 13 exploratory windows remain available through git history.
5. **The numerical differences between `time_dependent_annealing_report.md` and the convergence benchmark report are protocol differences, not contradictions**. Stage 4.B records the provenance explicitly: only `scheduled_auxiliary_carry_integer4` uses the historical pre-hardening sample timing to match its committed golden, while Q3.4 and both short schedules use the corrected clamp-prime/readout protocol. The compatibility run proves the checked-in seed set only, not cross-seed robustness.
6. **No fine-grained timing inside Stage 1**: `04243d1` is a single large commit (402 files); the order of its substages can only be inferred from the narrative order of the two historical reports and the original COMB6 report date (05-24); the `adder8` baseline transcript end time 05-25 00:15 is the only hard timestamp.
7. **The FP8/Q8 split-carry series (~23 `optimized_*.json`) has no corresponding simulation result files**, only the one qualitative sentence in the historical `time_dependent_annealing_report.md §4`: "underperformed… zero-hit cases remained".
8. The 8-bit benchmark results are non-exhaustive (6 vectors); neither an exhaustive 8-bit forward test nor an 8-bit SUM-only test has been done.
9. **Remote state was unavailable during the initial migration**, but was verified during Stage 4.C: GitHub `main` is `6ed61d9`; the three obsolete experiment branches were deleted on request; and the published `reorg` baseline is `443b3c0`. The current restructuring continues locally from that baseline. The original historical experiment tips remain ancestors of `main`. A pre-existing broken app-internal `refs/codex/turn-diffs/checkpoints/...` reference can disrupt generic `git fetch`; it is not an experiment branch and was not deleted by the branch cleanup.

## 5. Main evidence files

- Commit history: `git log main --stat` (the original 6-commit experiment chain plus the migration/consolidation commit)
- `README.md` (final `main` version and the `04243d1` original)
- `results_and_reports/stage2/rca_convergence_benchmark/report.md` (and its diffs across `bc2ac96`→`3575e71`→`8f512ce`)
- `results_and_reports/stage2/rca_convergence_benchmark/data/adder4_summary.csv`, `sum_only_aggregate.csv`, `quantized_scheduled_auxiliary_carry_window_sweep.csv`, `adder8_repeated.csv`, `rca_energy_landscape_summary.csv`, `manifest.json`
- `results_and_reports/stage2/rca_convergence_benchmark/traces/*.txt` (current fixed-seed QuestaSim evidence); historical ModelSim `Start/End time` transcripts remain in commits `bc2ac96`, `3575e71` and `8f512ce`
- `results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/time_dependent_annealing_report.md`, `results_and_reports/stage1/C_combinational_gap_equalization/comb6_equal_gap_report.md`
- `results_and_reports/stage1/A_primitive_spin_gate_validation/hamiltonians.{json,md}`, `results_and_reports/stage1/C_combinational_gap_equalization/comb6_e3m4_equal_gap.json`, `results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/optimized_q34_shadow1_blocks.json`, `results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/optimized_q34_shadow1_adder8_blocks.json`; historical FP8 split-carry coefficient sets remain accessible at `04243d1:reports/optimized_*.json`
- Historical versions: `04243d1:reports/q34_*_quick_summary.csv`, `04243d1:reports/q34_sum_only_reverse_distribution_summary.csv`, `04243d1:reports/adder8_integer_baseline_diagnostics_transcript.txt`, `3575e71:results_and_reports/stage2/rca_convergence_benchmark/scratch_shadow_j_sweep/data/shadow_copy_j_sweep_aggregate.csv`, `8f512ce:sim/experiments/*`
- Safe migration validation and frozen acceptance data: `scripts/stage4/B_fixed_seed_compatibility_validation/run_questa_compatibility_validation.py`, `scripts/stage4/B_fixed_seed_compatibility_validation/questa_compatibility_golden.json`; the archived pre-taxonomy run summary remains under `results_and_reports/stage4/B_fixed_seed_compatibility_validation/reorg_reproduction_summary.json`
- Simulator migration: `sim_scripts/Simulator.psm1`, `sim_scripts/Invoke-Simulation.ps1`, `sim_scripts/stage1/A_primitive_spin_gate_validation/run_questa.ps1`, `sim_scripts/stage1/A_primitive_spin_gate_validation/run_gate_regression.do`, `sim_scripts/sim_common.do`, `sim_scripts/README.md`, `sim_scripts/stage4/A_questa_migration/tests/`
- Legacy ModelSim archive: `legacy/modelsim/{README.md,run_modelsim.ps1,modelsim.ini}`
- Historical/benchmark scripts: `scripts/stage2/run_rca_convergence_benchmark.py`, `scripts/stage2/B_sum_conditioned_inverse_sampling/sweep_auxiliary_carry_coupling.py`, `scripts/stage2/A_randomized_rca_convergence/visualize_rca_energy_landscape.py`, `scripts/stage1/B_quantized_coefficient_exploration/optimize_fp8_hamiltonians.py`, `scripts/stage1/D_scheduled_auxiliary_carry_rca/generate_shadow1_q34_adder4.py`
- Optimizer successor and evidence: `scripts/stage3/B_verified_pairwise_optimizer_successor/`, `sim_scripts/stage3/B_verified_pairwise_optimizer_successor/` (including `tb/`), `experiments/stage3/B_verified_pairwise_optimizer_successor/{specs/ha_demo.json,README.md}`
- `experiments/stage5/README.md`, `scripts/stage5/A_adaptive_multibody_hamiltonian/`, `results_and_reports/stage5/A_adaptive_multibody_hamiltonian/EXPERIMENT_LOG.md`
