# Plan: E0 (baseline rebuild + metrics) and E1 (canonical vs long-range support)

> Execution target: the licensed local workstation used for the 2026-07-08 Stage3 run
> (Windows, 12 physical cores / 24 logical, Gurobi 13.0.x, license at `C:\gurobi1302\gurobi.lic`).
> Nothing in this plan runs on a cloud VM: the QPs need a full Gurobi license and the
> logged Stage3 model has ~141k dense rows.
> Background and rationale: the graph-cut brainstorm (project store,
> `docs/graph-cut-feedback-brainstorm.md`, sections 1.3, 4 and 6).

All commands are PowerShell, run from the repository root. `$EXP` abbreviates the
experiment folder:

```powershell
$env:GRB_LICENSE_FILE = 'C:\gurobi1302\gurobi.lic'
$EXP = '.\experiments\multibody_hamiltonian_6bit_adaptive_qp'
python -c "import gurobipy, numba, numpy, networkx, scipy; print(gurobipy.gurobi.version())"
```

If `networkx` or `scipy` are missing: `pip install networkx scipy` (needed only for the
E0.2 metrics). Everything else (`numpy`, `numba`, `matplotlib`, `gurobipy`) is what the
existing scripts already import.

---

## 0. Ground truth this plan is built on

Structural counts (verified by enumeration over `NODE_NAMES`, `node_stage`):

| Term order | All terms | Inside one block (`E*` family) | `span <= 1` | `span <= 2` |
|---:|---:|---:|---:|---:|
| 2 | 300 | **57** | **118** | 186 |
| 3 | 2300 | **54** | **259** | 721 |
| 4 | 12650 | **26** | 325 | 1745 |

Blocks: `B0 = {a0,b0,s0,c1}`, `Bk = {ak,bk,ck,sk,c(k+1)}` for `k = 1..5`, `B6 = {s6,c6}`.
`span(T) = max stage - min stage` with `stage(a_k)=stage(b_k)=stage(s_k)=k`, `stage(c_k)=k`
(this is the existing `edge_hypercut_experiment.node_stage`).

Stage3 reference (EXPERIMENT_LOG 2026-07-08): 2083 terms (25 / 273 / 1785), 27 hard-cut
pairs, 4 cutting-plane rounds, 141521 active cuts, gamma 2.4994e-5, valid std 4.65e-9,
1642 unclamped invalid local minima, rms one-bit jump 2.41e-5, 1376 nonzero terms.

Costs measured for the pure-numpy parts (4-core VM, single solution, will be faster locally):
`energies_full_cube` for 2625 terms 4.8 s, `local_minimum_codes` over 2^25 states 2.8 s.
So each cutting-plane round costs ~10 s outside Gurobi; Gurobi time dominates and must be
measured in E0.1 round 0.

Missing today (git-ignored): `out/full2/`, `out/full3/`, `out_staged_cut_*`. Every downstream
script (`staged_cut_verifier.py`, `tiny4_experiment.py`, `compare_paper_ssa_solutions.py`
defaults) hard-depends on `out/full2/solution_full2.json`, `out/full3/solution_full3.json`,
`out/full2/invalid_cuts_final.npz`.

---

## 1. E0 - rebuild the baseline and fix the metrics

Goal: a reproducible table `run x {gamma, kappa, tw, tw_ab, #clamped minima per mode,
r_max per mode, ab/asum/bsum/sum success +- 2SE}` for `full2`, `full3`, `stage3`.
No new algorithm. Everything in E1 is measured against this table.

### E0.1 Regenerate the artefacts (Gurobi, long-running)

Run in this order (Stage3 needs the `full2` cuts as seed and both solutions for scoring).
Do **not** use `run-all`: it appends 4 adaptive iterations that E0/E1 do not need.

```powershell
# 1. full2: fields + all 300 pairs (325 terms)
python $EXP\adaptive_qp_6bit.py run-baseline --order 2 --out $EXP\out --gurobi-threads 16

# 2. full3: + all 2300 triples (2625 terms)
python $EXP\adaptive_qp_6bit.py run-baseline --order 3 --out $EXP\out --gurobi-threads 16

# 3. Stage3, exactly the logged command (regenerates out_staged_cut_sum_sibling_hard_run_t16)
python $EXP\staged_cut_verifier.py `
  --stage stage3 `
  --out $EXP\out_staged_cut_sum_sibling_hard_run_t16 `
  --stage3-cut-sum-sum `
  --stage3-cut-output-siblings `
  --max-rounds 4 `
  --gurobi-threads 16
```

Defaults that these commands inherit and that must stay fixed for E1 comparability:
`--seed 2026070602`, `--coeff-max 2`, `--valid-weight 20000`, `--cap-weight 200000`,
`--tv-weight 100`, `--coeff-weight 0.1`, `--initial-invalid 12000`,
`--max-cuts-per-round 25000`, `--max-active-cuts 0`, `--violation-tol 1e-7`,
`--local-min-tol 1e-10`, `--gurobi-method 2` (barrier), `--gurobi-crossover 0`.

Expected artefacts per run dir: `solution_<run>.json` (with `dense_terms`),
`solution_round*.json`, `invalid_cuts_final.npz`, `invalid_cuts_partial.npz`,
`cut_history.csv`, `exhaustive_audit.json`, `metrics.csv`, `gurobi_round*.log`, 4 PNGs.

Reproduction checks for Stage3 (barrier with 16 threads is not bit-deterministic, so expect
small drifts; record them in EXPERIMENT_LOG):

- term selection must match exactly: 2083 terms, 273 pairs, 1785 triples, 515 rejected
  triples, critical nodes `s6 c4 c6` (deterministic given `full2`/`full3`; if `full2`/`full3`
  drift, the node scores and hence the triple ranking can drift - compare
  `_scoring/selected_triples.csv` against the logged counts);
- closure in <= 4 rounds with 0 violations; gamma within ~1e-7 of 2.4994e-5;
- `invalid_local_minima` within a few percent of 1642; `nonzero_terms_abs_gt_1e_9` near 1376.

Runtime and memory: unknown from the log; measure round 0 of `full2` first. The Stage3 model
has ~141k rows x 2083 columns of dense +-1 coefficients (~300M nonzeros, several GB inside
Gurobi). If memory is tight, the supported levers are `--max-active-cuts` (prunes to the
lowest-gap cuts each round; expect 1-2 extra rounds) and `--constraint-chunk`. Do not change
`--coeff-max`, weights or seed.

If `full2`/`full3` are needed quickly and Stage3 is the bottleneck: Stage3 can be restarted
from its own `invalid_cuts_partial.npz` with `--resume-cuts` (the loop saves it every round).

### E0.2 Extended metrics (no Gurobi; post-processing of any run dir)

Implement as a **new module + CLI** so that existing outputs can be re-audited without
re-solving, and so `adaptive_qp_6bit.py` stays untouched except for one small change.

`experiments/multibody_hamiltonian_6bit_adaptive_qp/landscape_metrics.py`

| Function | Definition | Notes |
|---|---|---|
| `clique_weights(terms, theta) -> W (25x25)` | `W[i,j] = sum_{T ⊇ {i,j}} \|theta_T\|` | clamp-independent upper bound of the folded pair weight |
| `dobrushin_row_max(W, free=None)` | `max_i sum_{j in free} W[i,j]` | `beta_D = 1 / row_max` |
| `kappa(gamma, W)` | `gamma / dobrushin_row_max(W)` | F6; also report `gamma / rms_one_bit_energy_jump` (already the `run_adaptive` stopping metric) |
| `treewidth(W, free=None, tol=1e-9)` | `networkx.algorithms.approximation.treewidth_min_fill_in` on `G = {ij : W[i,j] > tol}` restricted to `free` | F12; unclamped `G`, and `G_ab` on `s0..s6, c1..c6` |
| `mode_free_bits(mode)` | from `convergence_case_matrix(mode)`: bit positions with clamp `-1` | `ab` -> 13 free bits, `asum`/`bsum` -> 12, `sum` -> 18 |
| `clamped_local_minima(energies, valid_lookup, free_bits, tol)` | same bit-loop as `local_minimum_codes` but only over `free_bits`; count also restricted to states whose clamped bits belong to a **feasible** case (`feasible_cases` from `convergence_case_matrix`; only `sum` mode has infeasible cases, `sum > 126`) | F8; the exhaustive count is on the unclamped cube and is not what the sampler sees |
| `clamped_local_minima_depth(...)` | per minimum: depth `H(x) - E0` and barrier `min_i ΔH_i(x)` over free `i` | for the histogram in E1 |
| `dominance_ratios(terms, theta, design, mode)` | for each free node `u` at stage `k`: `m_u = min_{valid v} s_u(v) * F_u^up(v)`, `F_u^up` = field from terms whose other nodes are all clamped or at stage `< k`, or at stage `k` and inputs (`a_k, b_k, c_k`); `d_u = sum_{T ∋ u, T touches stage > k} \|theta_T\|`; `r_u = d_u / max(m_u, eps)` | F4; report `r_max`, and the list of `u` with `r_u >= 1`; `m_u <= 0` means the upstream field alone does not fix `u` on some valid state -> flag |
| `frustration_counts(...)` (optional) | skip in E0; belongs to A4 | - |

`experiments/multibody_hamiltonian_6bit_adaptive_qp/audit_solution.py` (CLI)

```powershell
python $EXP\audit_solution.py --run-dir $EXP\out\full2 --modes ab,asum,bsum,sum
python $EXP\audit_solution.py --run-dir $EXP\out\full3 --modes ab,asum,bsum,sum
python $EXP\audit_solution.py --run-dir $EXP\out_staged_cut_sum_sibling_hard_run_t16\stage3_from_full2 --modes ab,asum,bsum,sum
```

Behaviour: `load_solution_from_run(run_dir)`, recompute `energies_full_cube` (uses the stored
`reference_energy` and `gamma`), write `extended_audit.json` and one row into
`extended_metrics.csv` next to `exhaustive_audit.json`, and append/replace the row in
`$EXP\out_metrics\extended_summary.csv` (one table across runs; key = run dir name). Fields:

`run_key, gamma, kappa_dobrushin, kappa_rms, dobrushin_row_max, beta_D, tw_full, tw_ab,
tw_asum, clamped_minima_ab, clamped_minima_asum, clamped_minima_bsum, clamped_minima_sum,
clamped_min_depth_p50_ab, clamped_barrier_p50_ab, r_max_ab, r_max_asum, r_max_bsum,
nodes_r_ge_1_ab, m_nonpos_nodes_ab, nonzero_terms, pairs_noncanonical_nonzero,
weight_noncanonical (F1), weight_span (F2)`.

The only change inside `adaptive_qp_6bit.py`: give `local_minimum_codes` an optional
`free_bits: Sequence[int] | None = None` argument (loop over `free_bits` instead of
`range(N)`), default behaviour unchanged. `exact_audit_and_plots` is **not** touched in E0;
the extended metrics live in the new files so that old and new runs are audited identically.

Optional F9 (exact Glauber spectral gap on 64 sampled `(A,B)` cases, 8192-state chain,
`scipy.sparse.linalg.eigs`): implement only if E0.2 finishes early; it is not a gate for E1.

Sanity checks (cheap, do them before trusting any number):

- `clamped_local_minima(..., free_bits=range(25))` must equal `local_minimum_codes` output.
- On `full2`, `tw_full` must be <= 24 and for the canonical support built in E1 exactly 4
  (`G_ab` exactly 2) - this validates `treewidth` and the block/stage helpers.
- `r_u` on a hand-built canonical FA Hamiltonian (`(a+b+c-s-2c')^2` expanded, coefficients
  from `reports/coefficients/hamiltonians.json`) must give `d_u = 0` for `a,b` and a finite
  `r_{c_k}` (carry couples to the next stage), otherwise the upstream/downstream partition
  is wrong.

### E0.3 Dynamic baseline (numba, no Gurobi)

Paired paper-SSA comparison with enough trials for the 2*SE gate to resolve ~1 % effects.
Use the existing script; add all three solutions in one invocation so the seeds are paired.

```powershell
# timing probe first (numba compile + scaling)
python $EXP\compare_paper_ssa_solutions.py `
  --solution full3=$EXP\out\full3 `
  --solution stage3=$EXP\out_staged_cut_sum_sibling_hard_run_t16\stage3_from_full2 `
  --baseline-label stage3 --modes ab --trials 2 --cycles 1000 `
  --out-dir $EXP\out_paper_ssa_e0\probe

# full baseline
python $EXP\compare_paper_ssa_solutions.py `
  --solution full2=$EXP\out\full2 `
  --solution full3=$EXP\out\full3 `
  --solution stage3=$EXP\out_staged_cut_sum_sibling_hard_run_t16\stage3_from_full2 `
  --baseline-label stage3 `
  --modes ab,asum,bsum,sum `
  --trials 20 --cycles 1000 `
  --out-dir $EXP\out_paper_ssa_e0\t20
```

Memory: `pick_randoms` and `noise_randoms` are `float32[(4096*trials) x cycles]`, i.e. ~330 MB
each at 20 trials / 1000 cycles - fine. If the probe shows the full run is too slow, split by
mode (one process per mode, same `--seed`; pairing across labels is preserved because the
seed is derived from `mode_idx` within one invocation - so keep all labels in the same call
and split only across modes).

Outputs: `convergence_paired.csv`, `convergence_vs_baseline.csv` (delta, `two_se`,
`degraded_beyond_2se`). SE at 81920 trials per mode is <= 0.17 %, so 2*SE <= 0.35 %.

Known limitation to note in the log: `sum` mode success is "any valid `(a,b)` with that sum"
(`success_rate_feasible`); coverage/entropy of the sampled `(a,b)` distribution (the Stage-C
collapse metric) is not produced by this script. Not needed for the E0/E1 gates.

### E0.4 Deliverables and success criterion

1. `EXPERIMENT_LOG.md` entry "E0 baseline rebuild": commands, Gurobi thread line, runtime per
   round, the reproduction-check table (logged vs regenerated Stage3), the extended-metric
   table for `full2 / full3 / stage3`, and the dynamic table (`ab, asum, bsum, sum`, rate +- 2SE).
2. `out_metrics\extended_summary.csv` (git-ignored like all `out*`; the table goes in the log).
3. New code: `landscape_metrics.py`, `audit_solution.py`, `free_bits` in `local_minimum_codes`,
   plus a `unit-check`-style self-test in `audit_solution.py --self-test` covering the three
   sanity checks above.

E0 is done when the table has all three rows, the Stage3 row reproduces the logged static
numbers within the tolerances above, and `clamped_minima_ab` is reported (this is the number
that replaces "1642" in every later comparison).

---

## 2. E1 - canonical vs long-range support (A1 + A8 span sweep)

Hypothesis under test: Stage3 kept 222 non-canonical inter-stage pairs and removed 6
canonical `s_k - c_{k+1}` pairs (plus 17 canonical triples through `has_cut_pair`). If
long-range coupling is the source of the traps, supports restricted to blocks / adjacent
blocks should have fewer clamped minima and better `ab` / `asum` success. If Stage3 still
wins, long-range terms are useful and the next step is A6 / A12b (bound them, do not cut them).

### E1.1 Code: support rules and a runner

`experiments/multibody_hamiltonian_6bit_adaptive_qp/support_rules.py`

| Function | Returns |
|---|---|
| `canonical_blocks() -> list[set[int]]` | the 7 blocks above, as node-index sets |
| `term_in_block(term) -> bool` | `set(term) ⊆ some block` |
| `term_span(term) -> int` | via `node_stage` |
| `canonical_pairs()` / `canonical_triples()` / `canonical_quads()` | 57 / 54 / 26 terms |
| `term_allowed(term, rule: str, max_span: int) -> bool` | `rule in {"block", "span", "full"}` |
| `build_support(rule, max_order, max_span) -> list[tuple]` | fields (25) + all terms of order 2..`max_order` passing `term_allowed`; sorted like `staged_cut_verifier.run_stage3` |

Self-test (`python support_rules.py`): asserts the counts 57/54/26 and 118/259/325.

`experiments/multibody_hamiltonian_6bit_adaptive_qp/run_support_sweep.py` (CLI, reuses
`add_common_args`, `build_design`, `solve_cutting_plane`, `solution_payload_with_dense`,
`copy_seed` semantics):

```text
--support block|span|full      term rule
--max-order 2|3|4              highest term order included
--max-span K                   only for --support span
--run-key NAME                 output sub-dir under --out
--seed-cuts-from PATH          copy as invalid_cuts_partial.npz and set --resume-cuts
                               (default: $EXP\out\full2\invalid_cuts_final.npz, same as Stage3)
```

It writes the same artefact set as `solve_cutting_plane` plus `support_summary.json`
(rule, counts by order, list of pairs, canonical/non-canonical split) so the audit can tell
which pairs were available versus which ended up nonzero.

Optional hook for later stages (not required for E1 runs): a `--support-rule` /
`--max-span` pass-through in `staged_cut_verifier.run_stage3` that applies `term_allowed`
before `filter_terms` / `select_triples_with_edgecut`. E1 uses the standalone runner so that
the Stage3 pipeline (node scoring, critical nodes, triple ranking) is not in the loop.

### E1.2 Runs

Common settings: identical to E0.1 (same seed, weights, `--coeff-max 2`, 16 threads), seed
cuts from `out\full2\invalid_cuts_final.npz` so all runs start from the same active-cut set
(cuts are states, valid for any support). Allow more rounds than Stage3: `--max-rounds 8`
(small supports have fewer degrees of freedom and may need more rounds to close; if a run
stops with `new_cuts == 0` but violations > 0 it is *infeasible at this coefficient cap* -
record it, it is a result).

| Run key | `--support` | `--max-order` | `--max-span` | Terms | Reads as |
|---|---|---:|---:|---:|---|
| `canon2` | block | 2 | - | 25+57 = 82 | pairwise chain-of-cliques (`E*`) |
| `canon3` | block | 3 | - | 82+54 = 136 | + block triples |
| `canon4` | block | 4 | - | 136+26 = 162 | + block quads (full block algebra) |
| `span1_2` | span | 2 | 1 | 25+118 = 143 | adjacent-block pairs |
| `span1_3` | span | 3 | 1 | 143+259 = 402 | adjacent-block pairs + triples |
| `span2_3` | span | 3 | 2 | 25+186+721 = 932 | two-stage reach (optional, only if time allows) |
| `stage3` | (E0) | 3 | inf | 2083 | reference, with SUM cuts |
| `full3` | (E0) | 3 | inf | 2625 | reference, no cuts |

```powershell
$SEED = "$EXP\out\full2\invalid_cuts_final.npz"
$OUT  = "$EXP\out_e1_support"
python $EXP\run_support_sweep.py --support block --max-order 2 --run-key canon2  --out $OUT --seed-cuts-from $SEED --max-rounds 8 --gurobi-threads 16
python $EXP\run_support_sweep.py --support block --max-order 3 --run-key canon3  --out $OUT --seed-cuts-from $SEED --max-rounds 8 --gurobi-threads 16
python $EXP\run_support_sweep.py --support block --max-order 4 --run-key canon4  --out $OUT --seed-cuts-from $SEED --max-rounds 8 --gurobi-threads 16
python $EXP\run_support_sweep.py --support span  --max-order 2 --max-span 1 --run-key span1_2 --out $OUT --seed-cuts-from $SEED --max-rounds 8 --gurobi-threads 16
python $EXP\run_support_sweep.py --support span  --max-order 3 --max-span 1 --run-key span1_3 --out $OUT --seed-cuts-from $SEED --max-rounds 8 --gurobi-threads 16
```

Order of execution: `canon2` first (smallest; also the feasibility certificate - the
canonical quadratic encoding proves a `gamma > 0` solution exists within `|theta| <= 2`
after rescaling, so if `canon2` does not close, the runner or the weights are wrong, not the
hypothesis). Then `canon3`, `span1_2`, `span1_3`, `canon4`; `span2_3` last.

Cost: QP columns drop from 2083 to 82-402 while rows stay ~120-140k, so each barrier solve
should be an order of magnitude cheaper than Stage3; the 2^25 audit (~10 s/round) becomes a
visible share of the round time.

### E1.3 Measurements

1. Static: `audit_solution.py --run-dir $OUT\<run> --modes ab,asum,bsum,sum` for every run
   (adds rows to `out_metrics\extended_summary.csv`). Expected treewidths: `canon*` -> 4 / 2,
   `span1_*` -> 7 / <= 4; `stage3` ~18 / ~6 - a mismatch here means a bug, not a finding.
2. Dynamic: one paired invocation with all labels, baseline `stage3`:

```powershell
python $EXP\compare_paper_ssa_solutions.py `
  --solution stage3=$EXP\out_staged_cut_sum_sibling_hard_run_t16\stage3_from_full2 `
  --solution full3=$EXP\out\full3 `
  --solution canon2=$OUT\canon2 --solution canon3=$OUT\canon3 --solution canon4=$OUT\canon4 `
  --solution span1_2=$OUT\span1_2 --solution span1_3=$OUT\span1_3 `
  --baseline-label stage3 --modes ab,asum,bsum,sum --trials 20 --cycles 1000 `
  --out-dir $EXP\out_paper_ssa_e1\t20
```

   Because `paper_hyperparams` derives `I0` and the noise from `sigma_i = sqrt(sum theta^2)`,
   the dynamics are scale-invariant; absolute `gamma` differences between runs are not a
   confound, `kappa` is the comparable static number.
3. Per-run one-liner for the log: `gamma, kappa_dobrushin, tw_full/tw_ab, clamped_minima_ab,
   clamped_minima_asum, r_max_ab, nonzero_terms, ab/asum/bsum/sum rate +- 2SE, delta vs stage3`.

### E1.4 Decision rules

- **Hypothesis confirmed** if at least one restricted run (`canon*` or `span1_*`) has
  `ab` and `asum` success > stage3 + 2SE **and** `clamped_minima_ab <= 0.10 * stage3's`.
  Next: E3 (dominance constraints + sweep order) on the winner; E2 (reweighted L1) to learn
  which long-range terms are worth adding back.
- **Hypothesis falsified** if `stage3` (or `full3`) beats every restricted run on `ab` or
  `asum` by > 2SE. Record "long-range coupling helps"; next: A6 / A12b (keep long-range terms,
  bound their influence), and A11 (`--hyperedge-rule block`) to test whether Stage3's removal
  of the 17 canonical triples matters.
- **Mixed** (static improves - fewer clamped minima, higher `kappa` - but dynamics do not):
  the traps that matter are intra-block; go to A9 (block-Gibbs diagnostic) before more cutting.
- Side question settled either way: `s_k - c_{k+1}` sibling pairs are *kept* by every
  restricted run; if `canon*` closes with `gamma > 0` and the pairs are nonzero, the Stage3
  "output sibling" cut was cutting canonical structure.

### E1.5 Deliverables

`EXPERIMENT_LOG.md` entry "E1 support sweep" with the run table (terms, rounds, closure,
gamma, kappa, tw, clamped minima), the dynamic table with 2SE, the decision taken, and the
list of nonzero non-canonical pairs in `span1_*` (these are the first "useful long-range
couplings" data). README: one paragraph under Runs for `run_support_sweep.py` and
`audit_solution.py`.

---

## 3. Work breakdown on this branch

Files to add / change (all under `experiments/multibody_hamiltonian_6bit_adaptive_qp/`):

| # | File | Change | Needed by |
|---|---|---|---|
| 1 | `adaptive_qp_6bit.py` | `local_minimum_codes(..., free_bits=None)` | E0.2 |
| 2 | `landscape_metrics.py` | new: `clique_weights`, `kappa`, `treewidth`, `mode_free_bits`, `clamped_local_minima(+depth)`, `dominance_ratios`, F1/F2 sums | E0.2, E1.3 |
| 3 | `audit_solution.py` | new CLI + `--self-test`; writes `extended_audit.json`, `extended_metrics.csv`, `out_metrics\extended_summary.csv` | E0.2, E1.3 |
| 4 | `support_rules.py` | new: blocks, span, `term_allowed`, `build_support`, count self-test | E1.1 |
| 5 | `run_support_sweep.py` | new CLI around `solve_cutting_plane` | E1.2 |
| 6 | `.gitignore` | already covers `out*/` and `*.log`; add `out_metrics/` only if the folder name does not match `out*` (it does; no change expected) | - |
| 7 | `EXPERIMENT_LOG.md`, `README.md` | E0 and E1 entries, new script usage | E0.4, E1.5 |

Order: 1-4 can be written and self-tested without Gurobi (the self-tests use synthetic
`theta` and the canonical FA coefficients). 5 needs a license only to run. Then E0.1 runs
(longest wall-clock item; start it as soon as the branch is checked out locally), E0.2/E0.3
as soon as each run dir exists, then E1.2 -> E1.3.

Nothing in E0/E1 changes `solve_soft_valid_qp`, the weights, or the Stage3 pipeline, so all
new numbers are directly comparable with the 2026-07-08 log.

## 4. Risks and guards

- **Reproduction drift of Stage3.** Barrier + 16 threads is not bit-reproducible; term
  selection depends on `full2`/`full3` node scores. Guard: compare `_scoring/*.csv` counts
  first; if the triple set differs, keep the regenerated Stage3 as the E1 reference and note
  it - the comparison inside E1 is paired anyway.
- **Small supports not closing.** With `|theta| <= 2` and the roughness penalty, a
  pairwise-only support may reach `new_cuts == 0` with residual violations only if the QP is
  numerically stuck; `canon2` is provably feasible, so treat non-closure as a bug in the
  runner (check `support_summary.json` counts) before interpreting it.
- **Local-minimum tolerance.** `--local-min-tol 1e-10` with gamma ~2.5e-5 is safe; keep it
  identical across runs since counts are tolerance-sensitive at this scale.
- **Dynamic run time.** 7 labels x 4 modes x 81920 trials x 1000 cycles; use the `--trials 2`
  probe to size it and split by mode if needed (never split labels across invocations).
- **Windows paths.** All scripts use `pathlib`; keep `--out` on a local disk with tens of GB
  free (`solution_round*.json` with 2625 dense terms and the PNGs are small, but
  `invalid_cuts_*.npz` and `gurobi_round*.log` accumulate per round).
