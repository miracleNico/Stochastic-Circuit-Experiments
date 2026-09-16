# Graph-Theoretic Edge Cuts Against Dangerous Feedback in the 6-bit Multibody p-bit Adder

Brainstorm / research plan for the next step after Stage3 of `experiments/stage5/A_adaptive_multibody_hamiltonian/`. Repo state used: `origin/main` at `0ab0875` (the local `/workspace` checkout was one merge behind and did not contain `experiments/`; all paths below refer to `origin/main`).

Nothing in this document has been run against Gurobi; the numbers quoted are either from `EXPERIMENT_LOG.md` or from pure graph computations on the node/term structure (reproducible with `networkx`, see section 2.4).

---

## 0. Where the repo actually is (what exists, what "hard cuts" mean today)

| Item | Where | What it does |
|---|---|---|
| Node set | `adaptive_qp_6bit.py::NODE_NAMES` | 25 spins: `a0..a5, b0..b5, s0..s6, c1..c6`. Valid set = 4096 states (`build_design`). Note `s6 == c6` in every valid state (final sum bit *is* the final carry), so the design has one redundant node. |
| Hamiltonian | `feature_matrix`, `energies_full_cube` | `H(x) = -Σ_T θ_T Π_{i∈T} s_i`, spins `s = 2x-1`, terms `T` of order 1..4. Local field `F_i = Σ_{T∋i} θ_T Π_{j∈T\i} s_j`; `P(s_i=+1) = (1+tanh(βF_i))/2` (`solution_field_terms`, `run_updates_numba`). |
| QP | `solve_soft_valid_qp` | `min −γ + 20000/|V|·Σ(H(v)−E0)² + 200000/|V|·Σ cap² + Σ_T (100·4k/N + 0.1/|T|) θ_T² s.t. H(u) ≥ E0+γ for active invalid cuts, |θ|≤2`. Support (= which terms exist) is fixed *before* solving. |
| Cut-plane loop | `solve_cutting_plane` → `find_gap_violations` (Walsh–Hadamard over 2^25) | Adds ≤25000 worst violators per round, closes at 0 violations. Seed cuts can be copied from an earlier run (`copy_seed`, `--resume-cuts`). |
| Exhaustive audit | `exact_audit_and_plots`, `local_minimum_codes` | γ, valid spread, **invalid local minima over the full unclamped 2^25 cube**, rms one-bit jump (analytic), sampled jumps, nonzero terms. |
| Node scoring | `compute_node_scores` | `0.25·H(valid marginal) + 0.25·H(bad-state marginal) + 0.30·nearest-valid mismatch + 0.20·quick-convergence failure rate` (the last at `--score-beta 5000`, i.e. essentially T=0 greedy descent). |
| Critical nodes | `tiny4_experiment.py::classify_critical_nodes` | `normalize(score) + 1.5·normalize(top-k bad-state MI) + 0.25·normalize(full3 3-body support)`, largest-gap split → Stage3 picked `s6, c4, c6`. |
| **Hard cuts (today)** | `staged_cut_verifier.py::sum_sum_pairs`, `output_sibling_pairs`, `nonlocal_sum_carry_pairs`, `nonadjacent_carry_pairs`, `augment_pairs`, `filter_terms`, `has_cut_pair`; `edge_hypercut_experiment.py::build_edge_cut`, `filter_terms_by_cut`, `any_cut_pair` | A hard cut is a **pair blacklist**. Every 2-body term equal to a blacklisted pair is removed from the support, and every 3/4-body term that *contains* a blacklisted pair is rejected (`has_cut_pair` = clique-expansion semantics). Blacklists come from CLI flags (`--stage3-cut-sum-sum`, `--stage3-cut-output-siblings`, `--stage3-cut-nonlocal-sum-carry`, `--stage3-cut-nonadjacent-carry`, `--stage3-cut-pairs`, `--stage3-candidate-cut-pairs`) or from the hazard-scored auto-cut (`--auto-cut-edges N`, needs the `ab_failed_bit_mismatch.csv` from `analyze_ab_failures.py`). |
| Stage3 result (2026-07-08) | `EXPERIMENT_LOG.md` | 27 pairs cut (21 SUM–SUM + 6 `s_i–c_{i+1}`); 25+273+1785 = 2083 terms (515 triples rejected); cutting planes 100774 → 8438 → 71 → 0 violations in 4 rounds; γ ≈ 2.499e-5; valid std 4.6e-9; **1642 invalid local minima**; 1376 nonzero terms. Statically feasible, no dynamic evidence. |
| Dynamics runners | `compare_adaptive23_convergence.py::simulate_convergence_paper` (paper SSA/SSAU, `paper_hyperparams`, `run_paper_ssa_updates_numba`), `compare_paper_ssa_solutions.py` (LABEL=PATH, paired seeds, 2·SE test), `analyze_ab_failures.py::simulate_ab` | Random single-site pick, no sequential order. Modes `a,b,sum,ab,asum,bsum,absum_valid`. |
| Earlier feedback-breaking tricks (VHDL) | `results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/time_dependent_annealing_report.md §2,§5`, `results_and_reports/stage2/rca_convergence_benchmark/report.md §2` | Carry-ordered block scheduling (sequential windows: stages hot in carry order) and auxiliary carry-state decoupling (shadow carry `c_i → q_{i+1} → FA cin`, q frozen while downstream FA runs) — directional couplings realised by the schedule, not by the Hamiltonian. QSAC reaches 99.65% / 99.67% on the 4-bit RCA. |

Key structural fact (section 2.4): the *canonical* pairwise encoding of the adder — `Σ_i (a_i+b_i+c_i−s_i−2c_{i+1})² + (s6−c6)²` — needs only **57 pair terms** (a chain of cliques, treewidth 4, chordal). Stage3 keeps **273** pairs: 51 canonical ones and **222 non-canonical** long-range pairs, while it *removed* 6 canonical ones (`s_i–c_{i+1}`, which the repo's own FA block has as `J(S,COUT) = −2` in `reports/coefficients/hamiltonians.json`). In other words, the current hard cuts point in the opposite direction from "remove feedback loops": they removed intra-block edges and kept all inter-stage shortcuts. This is the main thing the next experiments should test.

---

## 1. Formalization

### 1.1 Three graph views of the coefficient tensor

Let `T` be the support (set of terms) and `θ_T` the coefficient. Define for each pair `{i,j}` the **clique-expanded weight**

```
w_ij = Σ_{T ⊇ {i,j}} |θ_T|          (pairwise view, "influence budget" of j on i)
```

1. **Factor graph `F(T)`** — bipartite: variable nodes `i ∈ [25]`, factor nodes `T`, edge `(i,T)` iff `i ∈ T`. Exact for any order. A *hard cut* = deleting a factor node. `has_cut_pair` semantics = deleting every factor adjacent to both endpoints of a pair. Hypergraph min-cut / hMETIS-style partitioning operate here directly.
2. **Hypergraph `H(T)`** — vertices = spins, hyperedges = terms with `|T| ≥ 2`, weight `|θ_T|`. Same information as the factor graph; used for hypergraph Laplacians and hyperedge-aware cuts (section 3, A11).
3. **Clique expansion `G(T)`** — simple weighted graph with `w_ij` above. Loses which hyperedge produced an edge, but it is the object for cycles, frustration, treewidth, spectral sparsification, effective resistance, Dobrushin matrices. Every method below that "cuts an edge `{i,j}`" is implemented in the repo's language as "add `{i,j}` to the pair blacklist", which (via `has_cut_pair`) removes all hyperedges containing the pair — i.e. cutting in `G` is *conservative* w.r.t. `H`.

Build all three from a saved solution: `load_solution_from_run(run_dir)` gives `(terms, theta)`; `field_arrays(solution)` already produces the per-node adjacency used by the sampler.

### 1.2 Mode-conditioned (clamped) effective graph — the object that actually matters

The sampler never sees the full 25-node hypergraph; it sees the **free-node hypergraph after clamp folding**. For a mode `M` with clamped set `C` and values `s_C`:

```
θ'_{T\C} += θ_T · Π_{j ∈ T∩C} s_j        for every T with T\C ≠ ∅
```

So a 3-body term `(a_i, c_i, s_i)` becomes a *pair* `(c_i, s_i)` with sign depending on the clamped `a_i`; a 4-body term with two clamped nodes becomes a pair; etc. Consequences:

- Every graph metric below should be computed for `G_M = G(T | C = s_C)` for the modes actually tested (`ab`, `asum`, `bsum`, `sum`), and for the *worst case over clamp values* (either exhaustive over the 4096 cases, or bound with `w'_ij ≤ Σ_{T ⊇ {i,j}} |θ_T|`, which is clamp-independent).
- In `ab` mode the free nodes are only the 13 outputs `s0..s6, c1..c6`. Canonical support gives `G_ab` = 17 edges, treewidth 2 (triangles `c_i–s_i–c_{i+1}` chained along the carry). Stage3 support gives `G_ab` = 51 edges (all `c–c`, all non-local `s–c`), treewidth ≈ 6.
- The audit's **1642 invalid local minima are counted on the unclamped 2^25 cube**, but the dynamic tests clamp `a,b` (or `a,sum`, …). Local minima of the *clamped* landscape are a different (and more relevant) set. They are computable at the same cost: `energies_full_cube` already gives all 2^25 energies; for mode `ab` slice by the 12 clamped bits and run the `local_minimum_codes` bit-loop only over the 13 free bit positions (a `free_bits` argument to `local_minimum_codes` is a ~5-line change).

### 1.3 The "intended" structure (reference DAG and reference support)

Block/stage decomposition:

```
B0 = {a0, b0, s0, c1}                       (half adder)
Bk = {ak, bk, ck, sk, c(k+1)}   k = 1..5    (full adders)
B6 = {s6, c6}                               (copy: s6 = c6)
```

- **Reference pair support `E*`** = all pairs inside each block = 6 + 5·10 + 1 = **57** pairs. Block triples: 4 + 5·10 = **54**; block quads: 1 + 5·5 = **26**. `E*` is exactly the support of the canonical `Σ_k (a_k+b_k+c_k−s_k−2c_{k+1})² + (s6−c6)²`, so a QP restricted to `E*` (plus fields) is **guaranteed feasible** with `γ > 0` (representability certificate). Anything that keeps `E*` keeps the valid set; anything that drops canonical pairs (Stage3 did) relies on the QP finding a compensating multi-body encoding — feasible in Stage3, but not guaranteed.
- **Reference DAG `D*`**: orient `a_k, b_k, c_k → s_k, c_{k+1}`, and `c6 → s6`. Topological rank = `(stage k, input-before-output)`. `D*` is the forward data flow; in inverse modes the flow changes (e.g. `asum`: `a_k, s_k, c_k → b_k, c_{k+1}`), but the **stage order LSB → MSB is preserved in every mode that clamps two of the three buses**, because `c_k` is always produced by stage `k−1`. Only `sum`-only mode has no direction (it is a sampling problem with 2^k solutions per SUM).
- **Block graph** `B0 – B1 – … – B5 – B6` with separators `{c1}, …, {c6}` is a path ⇒ junction tree of width 4.

### 1.4 What "dangerous feedback" means, measurably

Each definition gives a scalar you can compute on a saved solution (unclamped or per mode), compare between runs, and use as a cut objective.

| # | Quantity | Definition | Why it is "feedback" | Cheap to compute? |
|---|---|---|---|---|
| F1 | Non-canonical weight | `Σ_{{i,j} ∉ E*} w_ij` and count of non-canonical pairs (222 in Stage3) | Every non-canonical edge closes a cycle with the carry chain (undirected cyclomatic number 249 vs 33) | yes |
| F2 | Stage-span weight | `Σ_T |θ_T| · span(T)`, `span = max stage − min stage` | Long-range terms let stage `k+3` pull stage `k` before its carry has settled (the exact failure mode documented in `time_dependent_annealing_report.md §1`) | yes |
| F3 | Frustrated shortcut cycles | For a non-canonical pair `{u,v}` and the canonical path `P(u,v)` in `E*`, sign product `σ = sign(θ_uv) · Π_{e∈P} sign(θ_e)` (on the clamp-folded pairwise graph `G_M`). Frustration index of `G_M` = min edge weight to delete to make it balanced. Note: a logic Hamiltonian with 4096 degenerate ground states is *necessarily* frustrated inside blocks; only frustration created by non-canonical edges is "dangerous". | Frustrated cycles ⇒ no assignment satisfies all couplings ⇒ extra local minima | yes (cycles of length ≤ 6 on 13–25 nodes) |
| F4 | Feed-forward dominance ratio (Lyapunov, T = 0) | For free node `u` at stage `k` in mode `M`: `m_u = min_{valid v} s_u(v)·F_u^{up}(v)` (field from clamped nodes + strictly earlier stages + same-stage inputs, evaluated on valid states), `d_u = Σ_{T∋u, T ∩ later-stages ≠ ∅} |θ_T|`. **Ratio `r_u = d_u / m_u`**. If `r_u < 1` for all free `u`, then under an LSB→MSB sweep at T = 0 the stage index is a Lyapunov function: once stages `< k` are correct, node `u` cannot be flipped by any state of later stages. This is the static analogue of Scheduled auxiliary-carry architecture (windows/shadow made `d_u = 0` by schedule). | Directly measures "downstream can overturn upstream" | yes; and **linear in θ** (see A6) |
| F5 | Dobrushin influence / contraction | `C_ij(β) ≤ β · w'_ij` (since `dP/dF = β/2·sech² ≤ β/2` and a flip of `j` changes `F_i` by ≤ `2w'_ij`). Dobrushin: `β · max_i Σ_j w'_ij < 1` ⇒ unique Gibbs measure and O(n log n) mixing; spectral version `ρ(C) < 1`. Define the **Dobrushin temperature** `β_D(M) = 1 / max_i Σ_{j free} w'_ij`. | Below `β_D` the Glauber chain is a contraction; large `w` row-sums (dense graphs) are what makes low-temperature lock-in possible | yes |
| F6 | Scale-free gap `κ` | `κ(M) = γ_M / max_i Σ_j w'_ij` (= `γ · β_D`). The QP's `−γ` is linear and the roughness penalty quadratic, so absolute `γ` (2.5e-5) is an artefact of the objective weights; `paper_hyperparams` derives `I0`, `n_rnd` from `σ_i = sqrt(Σ θ²)`, so **the dynamics are scale invariant** and only ratios like `κ` or `γ / rms one-bit jump` (used in `run_adaptive`) are meaningful. | Tells whether the gap can be resolved at a temperature where the chain still mixes | yes |
| F7 | Mean-field Jacobian spectral radius | At a valid fixed point `m*` (or at `m = 0`), `J_ij = β(1−m_i²) ∂F_i/∂s_j`; `ρ(J) > 1` ⇒ fixed point loses stability under synchronous updates ⇒ period-2 oscillation (Hopfield/Goles theorem: symmetric synchronous dynamics converge to fixed points or 2-cycles). The VHDL updates one node per phase, so oscillation is a hardware/parallel-update risk, not a Gibbs risk, but `ρ` is still a good "loop gain". | Oscillation / saturation lock-in | yes (25×25) |
| F8 | Clamped invalid local minima and barriers | Per mode: `#local minima of H_M` on the 2^13 (or 2^19) free subcube, and their barrier `b(x) = min_i ΔH_i(x)` and depth `H(x) − E0`. | The actual traps | yes (section 1.2) |
| F9 | Exact Glauber spectral gap on the clamped subcube | For `ab` mode the free space is 2^13 = 8192 states; the single-site Glauber transition matrix is sparse (13 off-diagonals per row). `1 − λ₂` via `scipy.sparse.linalg.eigs` gives the **exact relaxation time** per `(A,B)` case at any β. Sample ~64 cases. | Replaces Monte-Carlo success rates with an exact dynamic metric | yes (seconds per case) |
| F10 | FAS / SCC under an update order | Given a fixed sweep order `π` (e.g. LSB→MSB by stage) build the digraph `u → v` for every pair with `w_uv > 0`; arcs with `π(u) > π(v)` are *back arcs*. Weighted back-arc mass `B(π) = Σ_{π(u)>π(v)} w_uv`; min-FAS = best `π`. SCCs of the digraph restricted to arcs with `w > τ` = groups that can sustain a loop of strength `τ`. | Measures how far the coupling graph is from a pipeline for the given schedule | yes (25 nodes; exact FAS via ILP or Gurobi in ms) |
| F11 | Effective resistance / algebraic connectivity | Laplacian `L` of `G_M`; `R_ij = (e_i−e_j)ᵀ L⁺ (e_i−e_j)`; `w_ij R_ij ∈ (0,1]` is the "leverage" of the edge (1 = bridge, ≈0 = one of many parallel paths). `λ₂(L)` = algebraic connectivity. | Many parallel low-leverage paths = redundant feedback | yes |
| F12 | Treewidth of `G_M` | `networkx.algorithms.approximation.treewidth_min_fill_in` | Bounded treewidth ⇒ exact inference by junction tree, and Gibbs on chains/trees mixes; canonical support: 4 (unclamped) / 2 (`ab`); Stage3: ≈18 / 6 | yes |

**"Keep the valid-state set intact" operationally** = after the cut, `solve_cutting_plane` closes with `gap_violation_count = 0` and `γ > 0` in `exhaustive_audit.json`. Certificate-level guarantee only when `E* ⊆ support`. Additional soft requirement: valid states remain the *unique* ground states in every clamped mode (already implied by the global audit).

**Intrinsic limit to remember.** A symmetric Hamiltonian cannot have directional coupling: `θ(c_k, c_{k+1})` is simultaneously the forward carry path and the backward feedback path. Graph cuts can remove *non-canonical* feedback (222 edges in Stage 5.A) and can bound the *ratio* `r_u` (F4), but the reverse direction of canonical edges can only be neutralised by carry-ordered scheduling or auxiliary carry-state decoupling. Several algorithms below therefore output *both* a support and a suggested update order or latch set.

---

## 2. Candidate algorithms

Each entry: intuition → formulation → complexity → integration point → metric → risk → concrete 6-bit experiment.

### A1. Canonical-support whitelist (Steiner/arborescence of the intended data flow, all other edges cut)

- **Intuition.** The intended flow `D*` is already a DAG whose undirected support `E*` encodes the adder exactly. Start from the sparsest provably-feasible support and *add* terms only when they demonstrably help, instead of starting from the complete hypergraph and cutting.
- **Formulation.** Support = fields ∪ `E*` (57 pairs) ∪ block triples (54) ∪ optionally block quads (26). Variant A1+: allow terms whose vertex set lies within two *adjacent* blocks `B_k ∪ B_{k+1}` (118 pairs, treewidth 7). A Steiner-tree/arborescence framing: the minimum-weight connected sub-hypergraph of `H(T)` spanning all terminals that must communicate (`a_k, b_k, c_k` with `s_k, c_{k+1}`) *is* the block structure; the arborescence rooted at `{a0,b0}` along the carry chain gives the update order for A2.
- **Complexity.** O(1) to build; QP has 25+57+54(+26) ≈ 140–165 variables instead of 2083 — much faster cutting-plane rounds.
- **Integration.** New `keep_terms_whitelist(terms, allowed_sets)` next to `filter_terms` in `staged_cut_verifier.py` (complement of `has_cut_pair`: keep a term iff `set(term) ⊆ some block`), plus a `--support canonical|adjacent|full` flag on `run_stage3`; seed cuts from `out/full2/invalid_cuts_final.npz` still valid (they are states, not terms).
- **Metric.** γ, κ (F6), clamped local minima (F8), F9 spectral gap, paper-SSA `ab/asum/bsum/sum` success via `compare_paper_ssa_solutions.py --solution canonical=… --solution stage3=…`.
- **Risk.** γ will be small (pairwise-only adder gap collapses like the 8-bit least-node LP, 1/8192); block triples/quads should recover part of it. If canonical loses to Stage3 dynamically, the hypothesis "long-range edges hurt" is falsified — which is itself the most valuable single data point.
- **Experiment.** Three runs: `E*` pairs only; `E*` + block triples; adjacent-block support. Compare against a regenerated Stage3. Success: `ab` success ≥ Stage3 + 2·SE and clamped local minima ≤ 10 % of Stage3's.

### A2. Minimum feedback arc set → update order + back-edge cuts

- **Intuition.** Carry-ordered block scheduling (sequential windows) is an FAS solution in disguise: pick an update order so that arcs pointing "backwards" carry as little weight as possible; then either freeze (schedule) or cut (Hamiltonian) what remains.
- **Formulation.** Digraph on free nodes of mode `M`: both arcs `u→v`, `v→u` with weight `w'_uv` (Gibbs reads both ways). Ordering LP/ILP: `min Σ_{u,v} w_uv · [π(u) > π(v)]` — exact for 13–25 nodes by ILP (Gurobi, ordering variables `x_uv ∈ {0,1}` with triangle constraints) or by the Eades–Lin–Smyth heuristic. Because the digraph is symmetric, the optimum is a *minimum linear arrangement*; the back-arc set `B(π*)` tells which pairs cannot be made forward. **Cut rule:** blacklist non-canonical pairs in `B(π*)` whose weight exceeds `τ`; canonical pairs in `B(π*)` are handled by the schedule (A2 also outputs `π*` as a sweep order).
- **Complexity.** ILP with 25²/2 binaries — milliseconds. Heuristic O(m).
- **Integration.** New script `fas_schedule.py` reading `solution_*.json`, emitting `--stage3-candidate-cut-pairs "u:v,…"` (existing CLI, `parse_pair_list`) and `sweep_order.json`. Add an `order` argument to `run_paper_ssa_updates_numba` (replace `pick = pick_randoms*count` by `order[cycle % count]`) — ~10 lines; this is the first time the QP world would get Carry-ordered block scheduling.
- **Metric.** `B(π)` before/after; F10; paper-SSA success with random vs sweep order (2×2 design: support × schedule).
- **Risk.** FAS on a symmetric graph degenerates to linear arrangement; its information is mostly "stage order", which we already know. Real value is the schedule experiment.
- **Experiment.** On the Stage3 solution compute `π*` for `ab`; check it equals stage order (sanity). Run paper-SSA with random vs `π*` sweep on Stage3 and on A1's canonical run.

### A3. Minimum feedback vertex set → where a static Hamiltonian needs latches (shadow nodes)

- **Intuition.** Auxiliary carry-state decoupling's shadow `q` nodes are a *vertex* solution: duplicating `c_k` into `q_{k+1}` and freezing `q` breaks every cycle through `c_k`. Min-FVS on `G_M` tells the smallest set of nodes whose removal makes the free graph acyclic (a forest ⇒ Gibbs mixes fast, T=0 descent is exact).
- **Formulation.** FVS on undirected `G_M` (NP-hard in general; 13–25 nodes: exact via ILP `min Σ x_v s.t. Σ_{v∈C} x_v ≥ 1 ∀ cycles C` with lazy cycle generation, or `networkx` cycle basis + greedy). Weighted version with node weight = `Σ_j w'_vj`.
- **Static realization.** For each `v ∈ FVS`: split `v` into `v_in`/`v_out` with a strong copy term `θ(v_in, v_out)` and reattach upstream terms to `v_in`, downstream terms to `v_out`. This adds nodes (design change: 25 → 25 + |FVS|), but is the only way to get *directionality-by-topology* in a symmetric H. Note `s6/c6` is already such a duplicated pair (with a cut candidate `s6:c6` in Stage4 defaults — the exact opposite of what a latch wants).
- **Complexity.** ILP trivial at this size.
- **Integration.** Needs a `Design` with extra nodes — `build_design`/`valid_state` extension (`carry_bits` duplicated) — the same change the Stage-E `shadow_group_adder8.py` made (not committed). Medium effort.
- **Metric.** Cycle rank after FVS; F9 spectral gap; success rates.
- **Risk.** Adds nodes to the 2^25 audit (2^26–2^31 states: WHT still fine up to ~2^28 in RAM). Scope change vs "cut edges".
- **Experiment.** Compute FVS of canonical `G_ab` (expect `{c1..c6}` or `{s_k}`), compare with the `q` nodes of the VHDL design; if identical, this is a formal justification for Auxiliary carry-state decoupling and a recipe for which carries to shadow in larger adders.

### A4. Frustrated shortcut-cycle detection and cutting (sign products, frustration index)

- **Intuition.** A non-canonical edge whose sign disagrees with the canonical path between its endpoints creates a frustrated loop → a trap whose depth scales with `|θ_uv|`. Cut the ones that are frustrated *and* strong; keep the ones that reinforce the canonical path (they act like error-correcting redundancy).
- **Formulation.** For mode `M` and each clamp case (or a random sample of cases): fold to `G_M`; for each non-canonical pair `{u,v}` compute `σ_uv = sign(θ'_uv) · Π_{e∈P*(u,v)} sign(θ'_e)`, where `P*` is the canonical path in `E*` (unique up to the block cliques; take the carry-chain path). Frustration mass `Φ = Σ_{σ_uv<0} |θ'_uv|`. Frustration index via the balanced-signed-graph ILP (`min Σ_e y_e` s.t. every cycle has an even number of negative non-deleted edges — solve with cycle basis constraints). Cut = top-k frustrated non-canonical pairs by `|θ'_uv| · (#clamp cases where frustrated)`.
- **Complexity.** O(#pairs × #cases) sign evaluations; ILP small.
- **Integration.** Reads a solution, writes `--stage3-candidate-cut-pairs`. Pure post-processing → re-run QP with the enlarged blacklist (the existing loop).
- **Metric.** Φ before/after, clamped local minima (F8), γ/κ. Cross-check: do the 1642 local minima concentrate on frustrated cycles? (`local_minimum_codes` → for each minimum, list terms with `θ_T Π s < 0`, i.e. unsatisfied terms.)
- **Risk.** Multi-body terms make "sign of an edge" clamp-dependent; a pair can be frustrated for half the cases and helpful for the other half. Report the distribution, not a single sign.
- **Experiment.** Stage3 solution, mode `ab`, all 4096 cases (each is a 13-node signed graph) → histogram of `σ_uv`; cut the 30 worst pairs; re-solve; compare 1642 → ?

### A5. Spectral sparsification by effective resistance (Spielman–Srivastava)

- **Intuition.** Redundant parallel paths (low leverage `w_ij R_ij`) are feedback that adds nothing to connectivity; bridges (leverage ≈ 1) are essential. Sparsify to the edges that carry the Laplacian.
- **Formulation.** On `G_M` compute `L⁺`, leverage `ℓ_ij = w_ij R_ij` (`Σ ℓ = n−1`). Deterministic variant: keep the `k` highest-leverage edges (plus `E*`), cut the rest; SS variant: sample edges with `p ∝ ℓ_ij`, reweight by `1/p` — reweighting is *not* allowed for us (the QP re-optimizes weights anyway), so use SS only for edge *selection*, and let the QP re-fit.
- **Complexity.** `L⁺` of a 25×25 matrix — trivial.
- **Integration.** Same blacklist path as A4. Alternatively use `ℓ_ij` as the `hazard_score` in `build_edge_cut` (a new `--auto-cut-mode leverage`).
- **Metric.** `λ₂(L)` retention, κ, F9. Caveat: SS preserves random-walk spectra, not Glauber spectra — treat as a heuristic and validate with F9.
- **Risk.** In a near-complete graph all leverages are ≈ `2/n`; the method is uninformative until the graph is already sparse. Use after A1/A12, not before.
- **Experiment.** Compute leverage on the Stage3 clique expansion; check whether canonical edges have systematically higher leverage (they should, on the `ab` free graph). If yes, leverage is a valid unsupervised proxy for "canonical".

### A6. Contraction / feed-forward dominance constraints inside the QP (Dobrushin rows, Lyapunov ratio) — "soft cuts"

- **Intuition.** Instead of deleting edges, *bound* the total influence that later stages can exert on a node, and bound Dobrushin row sums. The QP then decides which edges to shrink. Both quantities are linear in `|θ|`, so the QP stays convex.
- **Formulation.** Add auxiliary `t_T ≥ |θ_T|` (two linear rows per term). For each free node `u` in mode `M` and stage `k(u)`:
  - Dominance: `Σ_{T∋u, span(T) reaches stage > k(u)} t_T ≤ ρ · m_0` and `s_u(v) · F_u^{up}(v; θ) ≥ m_0` for all valid `v` (4096 × 13 linear rows in `ab` mode; `F_u^{up}` is linear in θ) with `ρ < 1` a hyper-parameter (start 0.7) and `m_0` a free variable to maximize alongside `γ`.
  - Dobrushin row cap: `Σ_{j} Σ_{T⊇{u,j}} t_T ≤ κ_D` (or minimize the max row sum as a second objective term).
- **Complexity.** +2|T| rows for `t`, +~53k rows for dominance in `ab` (fewer if enforced only on the 4096 valid states' distinct upstream contexts). Comparable to the existing 141k active-cut rows.
- **Integration.** Extension of `solve_soft_valid_qp` (new args `--ff-dominance-rho`, `--dobrushin-cap`, `--dominance-modes ab,asum,bsum`); needs a helper that returns for each node the "upstream" term subset per mode (from `node_stage` in `edge_hypercut_experiment.py`). Terms that the solver drives to `|θ| < 1e-6` can then be hard-cut in a second pass (`filter_terms`) — an optimizer-chosen cut set.
- **Metric.** F4 ratio `r_u` (should be ≤ ρ by construction), F5 `β_D`, κ, plus dynamics. This is the only algorithm whose success criterion (`r_u < 1` in all clamped modes) is a *proof* of T=0 pipeline convergence under a stage-ordered sweep.
- **Risk.** Dominance conflicts with γ: the canonical FA has `|J(c_k, c_{k+1})| = 2` equal to the largest intra-block coupling, so `r_{c_k}` cannot be made small without weakening the carry path; the QP may respond by shrinking γ. Needs a Pareto sweep over ρ.
- **Experiment.** On A1's adjacent-block support, sweep `ρ ∈ {0.5, 0.7, 0.9, ∞}`; plot γ, κ, `ab`/`asum` success. Success: some ρ with `ab` success ≥ Stage3 and `r_u ≤ ρ` verified by `exhaustive_audit`.

### A7. Minimum cut / Gomory–Hu partition: isolate the carry chain from the sum outputs

- **Intuition.** `SUM–SUM` cuts (Stage3) were a guess at "sum outputs should not talk to each other". The Gomory–Hu tree gives *all* pairwise min-cuts of `G_M` at once and shows which pairs are over-connected (large min-cut value through many redundant edges) relative to `E*` (where non-adjacent-stage pairs have min-cut = the carry-chain edge capacity).
- **Formulation.** `networkx.gomory_hu_tree(G_M, capacity='w')`. Target: for every pair `(u,v)` with `|stage(u)−stage(v)| ≥ 2`, `mincut_G(u,v) ≤ (1+ε) · mincut_{E*}(u,v)`. Greedy: repeatedly cut the highest-weight non-canonical edge on the max-flow path of the most over-connected pair. Also the classic `s–t` cut between `S = {s0..s6}` and `C = {c1..c6}` in `G_ab` lists exactly which `s–c` edges (beyond the canonical `s_k–c_k`, `s_k–c_{k+1}`) carry coupling.
- **Complexity.** Gomory–Hu on 25 nodes: negligible.
- **Integration.** Blacklist output → `--stage3-candidate-cut-pairs`. Could replace `nonlocal_sum_carry_pairs`/`nonadjacent_carry_pairs` (which are hand-written versions of the same idea) by a data-driven list.
- **Metric.** Over-connectivity ratio per pair; F8; dynamics.
- **Risk.** Min-cut is about capacity, not sign or dynamics; it will happily cut helpful reinforcing edges. Combine with A4's sign test.
- **Experiment.** Compute over-connectivity table of Stage3 `G_ab`; verify `nonlocal_sum_carry_pairs()` ∪ `nonadjacent_carry_pairs()` is (or is not) what Gomory–Hu picks; run the flags `--stage3-cut-nonlocal-sum-carry --stage3-cut-nonadjacent-carry` that already exist but were never run (EXPERIMENT_LOG has only the SUM–SUM + sibling run).

### A8. Treewidth-bounded supports (junction-tree-inspired cuts)

- **Intuition.** The canonical adder is a width-4 chain; Gibbs sampling on bounded-treewidth graphs behaves like sampling on a chain, and exact inference (forward–backward over the junction tree) becomes available as a *ground truth sampler* to compare the p-bit dynamics against.
- **Formulation.** Choose a target tree decomposition (natural: bags `B_k ∪ B_{k+1}`, width ≤ 8) and allow only terms whose vertex set lies inside one bag. Equivalently `span(T) ≤ 1` (118 pairs; A1+). Tighter: width-4 (bags = blocks, `E*`). Looser: width-w by allowing `span ≤ w'`. Treewidth of any candidate support is checked with `treewidth_min_fill_in`.
- **Complexity.** Trivial to enforce (`span(T)` filter). Exact junction-tree inference for width ≤ 8: 2^9 table per bag — instant.
- **Integration.** `span` filter in the same whitelist helper as A1. A `junction_tree_reference.py` that computes exact `P(s | A,B)` (= should be a delta) and exact `P(a,b | SUM)` (uniform over valid pairs) to serve as the reference distribution for the `sum`-only coverage/entropy metrics in `results_and_reports/stage2/rca_convergence_benchmark/report.md §7`.
- **Metric.** F12 treewidth, F9 spectral gap, and *distributional* metrics for `sum` mode (coverage of valid pairs, entropy — the Stage 2.B metrics).
- **Risk.** Width-1 (tree) is impossible (blocks are cliques); the real gain vs A1 is the quantitative knob `span`.
- **Experiment.** Sweep `span ∈ {0 (=E*), 1, 2, ∞ (=full3)}` with 2/3-body terms → four QP runs; plot κ and `ab`/`sum` success vs treewidth. This is the cleanest "how much long-range coupling is useful" curve.

### A9. Chordal completion vs decycling (add fill edges, or remove edges?)

- **Intuition.** Two ways to make a graph "tree-like": remove edges (decycling, everything above) or *add* fill-in edges so the graph is chordal and can be sampled by *block* Gibbs over maximal cliques. For a QP that re-fits weights, adding fill edges to the support costs nothing statically and enables clique-wise updates.
- **Formulation.** Min-fill-in ordering of `G_M` → chordal supergraph `G⁺`; maximal cliques = update blocks. Block-Gibbs step: resample a whole clique `K` (≤ 2^5 states) from `exp(−βH)` conditioned on the rest — a 32-entry softmax per step. In hardware terms this is a "multi-p-bit lookup" per FA; in the simulator it is a new update kernel.
- **Complexity.** Min-fill on 25 nodes: trivial. Block-Gibbs kernel: O(2^|K| · #terms in K) per step.
- **Integration.** New kernel `run_block_gibbs_numba` alongside `run_updates_numba` in `compare_adaptive23_convergence.py`; clique list from `networkx.chordal_graph_cliques(G⁺)`.
- **Metric.** F9 spectral gap of block-Gibbs vs single-site Glauber on the same H; success rates.
- **Risk.** Departs from the single-p-bit hardware model; useful as an upper bound ("what if each FA settled jointly?") that tells whether the problem is intra-block or inter-block.
- **Experiment.** Stage3 vs canonical H, single-site vs block-Gibbs, `ab` mode. If block-Gibbs fixes Stage3 but single-site does not, traps are intra-block (multi-body, high barrier); if neither fixes it, traps are inter-stage (feedback) and edge cuts are the right lever.

### A10. Community detection (Louvain / spectral clustering) → stage blocks and inter-block pruning

- **Intuition.** If the optimizer's weights respect the adder's structure, communities of `G(|θ|)` should coincide with stages. Where they do not, the optimizer has invented cross-stage structure — candidate cuts. Separately, communities of the **bad-state MI graph** (`pair_mutual_information` over low-energy invalid states, already computed as `bad_mi` in `compute_node_scores`) identify node groups that *co-vary in traps*; the non-canonical edges inside such a group are the ones "holding the trap together".
- **Formulation.** Louvain (`networkx.community.louvain_communities`, resolution sweep) and spectral clustering (Fiedler vectors of `L(G_M)`), compare with the stage partition by NMI/ARI. Cut rule: blacklist non-canonical pairs that (i) cross two `|θ|`-communities that are not stage-adjacent, or (ii) lie inside a bad-MI community.
- **Complexity.** Negligible.
- **Integration.** Reuse `compute_node_scores` output (`bad_mi`, `valid_mi`); emit blacklist. Can also be folded into `build_edge_cut` as an extra hazard term (`community_cross_penalty`).
- **Metric.** NMI(communities, stages) as a *structure-fidelity* score per run; F8; dynamics.
- **Risk.** Louvain on a near-complete weighted graph is unstable; use the `ab`-folded graph and several seeds. Bad-MI communities are computed from the 5000 lowest invalid states (`--score-bad-states`), which are dominated by near-valid states; make sure to include the 1642 local minima explicitly (they already are, `compute_node_scores` unions `local_codes`).
- **Experiment.** Run on Stage3: report NMI vs stage partition; list the top-20 non-canonical pairs inside bad-MI communities; cut them; re-solve.

### A11. Hyperedge-aware cuts (hypergraph min-cut, hMETIS-style partitioning, factor-side cuts)

- **Intuition.** Current semantics (`has_cut_pair`) delete a 3-body term if it contains *any* blacklisted pair — Stage3 thus rejected 17 *within-block* triples (`(a_k, s_k, c_{k+1})`, `(b_k, s_k, c_{k+1})`, `(c_k, s_k, c_{k+1})`) that are canonical FA structure. A hyperedge-aware rule scores each hyperedge as a whole.
- **Formulation.** (i) Rule-based: keep hyperedge `T` iff `span(T) ≤ w'` or `T ⊆ some block`, regardless of pair blacklist. (ii) Hypergraph partitioning with fixed vertices: stages as parts (`KaHyPar`/`hMETIS`, or in pure Python: star-expansion + `networkx` min-cut), cut = hyperedges spanning non-adjacent parts, objective connectivity-1. (iii) Factor-graph vertex cut: min number of factor nodes to delete so that the free-variable graph has ≤ w-treewidth or no path between stage `k` and `k+2` except through `c_{k+1}` — solvable as a small ILP.
- **Complexity.** Star expansion: 25 + |T| nodes (≤ 2100) — trivial. External partitioners optional.
- **Integration.** Replace `has_cut_pair` in `select_triples_with_edgecut` / `select_quads_with_hypercut` by a pluggable `term_allowed(term)` predicate (`--hyperedge-rule pair|span|block`). Keeps the rest of `staged_cut_verifier.py` intact.
- **Metric.** Number of canonical hyperedges retained; κ; dynamics.
- **Risk.** Loosening the rule brings back terms that Stage3 rejected for a reason (sibling pairs). Compare both semantics head-to-head.
- **Experiment.** Stage3 flags as logged, but with `--hyperedge-rule block` so the 17 canonical triples come back → does γ rise and does the local-minimum count fall? Direct A/B on the semantics question.

### A12. Learning-based edge scoring (attribution to invalid minima; sparsity-inducing QP; failure-trajectory hazard)

Three variants, all producing a ranked pair/term list.

- **A12a — trap attribution.** For each invalid local minimum `x` (1642 codes from `local_minimum_codes`) and each free bit `i`, the barrier `ΔH_i(x) = 2 Σ_{T∋i} θ_T Π_{j∈T} s_j(x)` decomposes over terms; a term with positive share *holds* the trap. Score `hold(T) = Σ_x Σ_i max(share_{T,i}(x), 0) · [T non-canonical]`. Cut top-k. O(1642 × 25 × deg) — instant. Also gives, per local minimum, the *minimum-cut of terms* needed to destabilise it (which term to zero so that some `ΔH_i < 0`).
- **A12b — sparsity-inducing reweighted L1 in the QP** (the optimizer chooses the support). Add `λ Σ_T d(T) |θ_T|` with `d(T) = 1 + span(T)` (or `d = 0` on canonical terms) to `solve_soft_valid_qp` (aux `t_T`, LP-representable). Iteratively reweight `λ_T ← λ / (|θ_T| + ε)` (Candès–Wakin–Boyd) for 3 rounds, then hard-cut `|θ_T| < 1e-6` via `filter_terms` and re-solve without the penalty for the final γ. This is the principled version of `nonzero_terms_abs_gt_1e_9` (1376 of 2083 in Stage3 — the ridge penalty already zeroes a third of the support; L1 would do this deliberately).
- **A12c — failure-trajectory hazard** (already implemented, currently inert). `build_edge_cut` combines bad-state MI, geometric mean of per-node failure mismatch rates, sibling bonus and stage distance; it is gated by `fail_geom ≥ 0.35`, and `load_failure_rates` returns zeros when `out_tiny4_q64/…/ab_failed_bit_mismatch.csv` is missing → `auto_cut_candidate = False` for every pair. Repair: run `analyze_ab_failures.py --solution stage3=<dir>` first, point `--failure-bit-csv` at its output, set `--auto-cut-edges 20 --auto-cut-stage-weight 1.0` (stage distance is weighted 0 by default), and inspect `edge_cut.csv`.
- **Gradient of γ w.r.t. the support.** Exact leave-one-term-out is 273 QP re-solves — too expensive at 141k rows. Cheap proxy: Gurobi's reduced costs on the bound constraints `|θ_T| ≤ 2` and the dual of `t_T ≥ |θ_T|` in A12b give `∂(objective)/∂θ_T`; combine with `|θ_T|` to rank.
- **Integration.** A12a/A12c: post-processing → blacklist. A12b: QP change (`--l1-weight`, `--l1-span-power`, `--l1-reweight-rounds`).
- **Metric.** For A12a the hard number is "how many of the 1642 minima disappear after cutting k terms" — checkable in one `energies_full_cube` pass (no QP) by simply zeroing those θ (this breaks γ, but shows which minima are *held* by which terms), then a QP re-solve for the honest number.
- **Risk.** A12a over-fits the *current* minima; new ones appear after re-optimization (the same reason the cut-plane loop needs rounds). Run 2–3 attribution/re-solve rounds.
- **Experiment.** Stage3 solution → attribution table → cut top-30 non-canonical terms → re-solve (seeded from `invalid_cuts_final.npz`) → local minima and paper-SSA success.

### A13. Mode-aware effective-graph sparsity (bonus; combines 1.2 with A12b)

Penalize the *clamp-folded* pair weights instead of raw terms: for mode `ab`, `w'_ij(a,b)` is linear in θ for each clamp case; penalize `Σ_{(i,j) non-canonical in G_ab} max_cases |w'_ij|` (LP-representable with 4096 × #pairs rows — use the clamp-independent bound `Σ_{T⊇{i,j}} |θ_T|` instead, 78 rows). Ensures that whatever multi-body terms survive, the graph *the sampler sees in forward mode* stays close to `E*`.

---

## 3. Comparison table

Feasibility = compute cost on the 25-node / 2^25-state problem. "γ" = expected static effect; "dyn" = expected dynamic effect (informed guesses). Effort: S (< 50 lines), M (50–200), L (new design / kernel). "Reuses SCV" = plugs into `staged_cut_verifier.py` as-is or with a small flag.

| Alg | Feasible on 25 nodes | Expected γ / κ | Expected dynamics | Effort | Reuses SCV |
|---|---|---|---|---|---|
| 1.A.1 canonical / adjacent whitelist | trivial; QP shrinks 10× | γ ↓ (pairwise limit), κ ≈ or ↑ | strongest hypothesis test; likely ↑ in `ab/asum/bsum` | S (whitelist filter + flag) | yes (new `--support`) |
| 1.A.2 min-FAS → order + cuts | ILP ms | neutral (few cuts) | ↑ only with sweep order (Carry-ordered block scheduling in QP world) | S cut list; S kernel order arg | cut list yes; kernel change in `compare_adaptive23_convergence.py` |
| 1.B.1 min-FVS → latch nodes | ILP ms | γ ↑ possible (copy terms are strong) | ↑ (Auxiliary carry-state decoupling analogue) but changes node count | L (`build_design`) | partially |
| 1.C.1 frustrated shortcut cycles | O(pairs × cases) | κ ≈, local minima ↓ | ↑ moderate | S–M | yes (`--stage3-candidate-cut-pairs`) |
| 1.D.1 effective-resistance sparsification | trivial | ≈ | unclear; heuristic | S | yes (or `build_edge_cut` mode) |
| 1.D.2 dominance / Dobrushin constraints | +50k linear rows, fine | γ ↓ vs ρ trade-off; κ ↑ | ↑ with proof of T=0 pipeline convergence | M (QP rows) | via `solve_soft_valid_qp` (shared) |
| 1.D.3 Gomory–Hu over-connectivity | trivial | ≈ | ↑ small; mostly a diagnostic | S | yes; existing `--stage3-cut-nonlocal-sum-carry/nonadjacent-carry` flags cover the hand-written version |
| 1.D.4 treewidth / span sweep | trivial | γ vs span curve | the "how much long range is useful" curve | S | yes (`span` filter) |
| 1.D.5 chordal completion + block Gibbs | trivial graph; new kernel | none (same H) | diagnostic upper bound | M (kernel) | no (sampler side) |
| 1.D.6 community detection | trivial | ≈ | ↑ small–moderate | S | yes |
| 1.D.7 hyperedge-aware rule | trivial | γ ↑ (recovers 17 canonical triples) | ↑ small | S (`term_allowed` predicate) | yes (replace `has_cut_pair`) |
| A12a trap attribution | O(1642 × 25 × deg) | local minima ↓↓ | ↑ if minima are the cause | S–M | yes |
| A12b reweighted L1 | LP rows 2|T| | γ ≈, support ↓↓ (learned) | ↑; gives a principled sparse support | M | via `solve_soft_valid_qp` |
| A12c hazard auto-cut | already implemented | ≈ | ? | S (fix data path) | yes |
| 1.D.9 mode-aware sparsity | 78 rows | ≈ | ↑ | M | via QP |

---

## 4. Recommended ordering (3–4 experiments) and success criteria

Prerequisite **E0 — rebuild the baseline and fix the metrics** (no new algorithm). `out*/` is git-ignored and absent, and `staged_cut_verifier.py` needs `out/full2/solution_full2.json`, `out/full3/solution_full3.json`, `out/full2/invalid_cuts_final.npz`.
1. `adaptive_qp_6bit.py run-baseline --order 2`, `--order 3`, then the logged Stage3 command. Record γ, local minima, `nonzero_terms`.
2. Add to `exact_audit_and_plots`: κ = γ / max_i Σ_j w_ij (F6); clamped local minima per mode (F8, `local_minimum_codes(free_bits=…)`); treewidth of `G` and `G_ab` (F12); F4 ratios `r_u` for `ab/asum/bsum`. Optional: F9 spectral gap on 64 sampled `(A,B)` cases.
3. Dynamic baseline with `compare_paper_ssa_solutions.py --solution full2=… --solution full3=… --solution stage3=… --modes ab,asum,bsum,sum --trials 20 --cycles 1000` (the logged default of 5 trials gives SE too large to see anything below ~2 %).
Success: a table `run × {γ, κ, tw, #clamped minima, r_max, ab/asum/bsum/sum success ± 2SE}`. Everything below is measured against it.

**E1 — Canonical vs long-range support (A1 + A8 span sweep).** Runs: `span=0` pairs only; `span=0` + block triples (+ quads); `span=1`; regenerated Stage3 (`span=∞` with SUM cuts). Same seeds, same cut-plane settings. Success criterion: at least one restricted support beats Stage3 on `ab` *and* `asum` success by > 2·SE with clamped local minima ≤ 10 % of Stage3's; if instead Stage3 wins, record that long-range coupling is *helpful* and pivot to A6/A12b (which keep long-range terms but bound them). Also settles the `s_k–c_{k+1}` sibling question (canonical keeps them).

**E2 — Optimizer-chosen cuts (A12b reweighted L1, then A12a attribution).** Start from the full3 support (2625 terms), `λ` sweep {1e-4, 1e-3, 1e-2} × `d(T) = 1 + span(T)`, 3 reweighting rounds, hard-cut zeros, final re-solve. Then one attribution round on the result. Success: a support with ≤ 120 pair terms and ≤ 200 triples whose `ab/asum/bsum` success ≥ full3's (paired, within 2·SE) and κ ≥ full3's; report which non-canonical terms survive (these are the "useful" long-range couplings — a result in itself).

**E3 — Directionality: dominance constraints + sweep order (A6 + A2).** On the E1/E2 winner, add F4 dominance rows with `ρ ∈ {0.5, 0.7, 0.9}` and run the sampler with random pick vs LSB→MSB sweep (`order` argument in `run_paper_ssa_updates_numba`). 2 × 3 grid. Success: `r_u ≤ ρ` verified in audit and `ab` success ≥ 99 % (the VHDL quantized scheduled auxiliary-carry level) under sweep order without losing more than 30 % of κ; `sum`-only coverage of valid pairs not below the random-pick baseline (guards against the Stage 2.B distribution collapse).

**E4 (optional) — Semantics and diagnostics (A11 + A4 + A7 + A9).** Re-run Stage3 flags with `--hyperedge-rule block` (A11) to recover the 17 canonical triples; A4 sign histogram and A7 over-connectivity table on Stage3 and on the E1 winner; block-Gibbs vs single-site (A9) to classify remaining traps as intra- vs inter-block. Success: a written classification of the surviving local minima (intra-block / frustrated shortcut / other) that decides whether further edge cutting can help at all.

---

## 5. Repo hooks per idea (file → function → change)

| Proposal | Read from | Hook / change |
|---|---|---|
| Graph construction (1.1) | `adaptive_qp_6bit.py::load_solution_from_run`, `solution_field_terms`; `compare_adaptive23_convergence.py::field_arrays` | new `graph_views.py`: `clique_expansion(solution) -> (W, G)`, `factor_graph(solution)`, `fold_clamp(solution, clamp_row) -> terms'` (reuse `convergence_case_matrix(mode)` for clamp rows) |
| Canonical structure (1.3) | `NODE_NAMES`, `edge_hypercut_experiment.py::node_stage`, `same_stage_parent_output` | `canonical_blocks()`, `canonical_pairs()` (57), `canonical_triples()` (54), `term_span(term)` |
| Whitelist support (A1/A8/A11) | `staged_cut_verifier.py::filter_terms`, `select_triples_with_edgecut::has_cut_pair` | `term_allowed(term, rule)` predicate; flags `--support`, `--max-span`, `--hyperedge-rule` |
| Blacklist-producing algorithms (A2, A4, A5, A7, A10, A12a) | any `solution_*.json` | emit `pairs.txt`; add `--stage3-cut-pairs-file` to `staged_cut_verifier.py` (feed `parse_pair_list` from a file — CLI strings for 200 pairs are unwieldy) |
| Hazard auto-cut (A12c) | `analyze_ab_failures.py::analyze_solution` → `ab_failed_bit_mismatch.csv`; `edge_hypercut_experiment.py::build_edge_cut`, `load_failure_rates` | run analyzer first; make `load_failure_rates` *fail loudly* when the CSV is missing and `--auto-cut-edges > 0` |
| QP constraints / penalties (A6, A12b, A13) | `adaptive_qp_6bit.py::solve_soft_valid_qp` | aux `t = model.addMVar(len(terms), lb=0)`; `t ≥ θ`, `t ≥ −θ`; dominance rows built from `feature_matrix_codes(valid_codes, upstream_terms)`; L1 objective `λ Σ d_T t_T`; reweighting loop around `solve_cutting_plane` |
| Metrics (F4–F9, F12) | `exact_audit_and_plots`, `local_minimum_codes`, `energies_full_cube` | add `free_bits` to `local_minimum_codes`; `kappa`, `treewidth`, `ff_dominance_ratios`, `dobrushin_beta` fields in `exhaustive_audit.json`/`metrics.csv`; optional `glauber_spectral_gap.py` using `scipy.sparse.linalg.eigs` on the 8192-state clamped chain |
| Sweep order / block Gibbs (A2, A9) | `compare_adaptive23_convergence.py::run_paper_ssa_updates_numba`, `run_updates_numba` | `order` array argument (deterministic pick), `run_block_gibbs_numba` with clique list |
| Latch nodes (A3) | `build_design`, `valid_state`, `carry_bits` | extra `q_k` nodes = copies of `c_k`; `N` becomes a parameter (currently a module constant used by `codes_to_bits`, `local_minimum_codes`, `TOTAL_STATES`) |
| Paired dynamic comparison | `compare_paper_ssa_solutions.py` (`--solution LABEL=PATH`, `--baseline-label`, `degraded_beyond_2se`) | use as-is with `--trials 20`; add `--order lsb-msb` pass-through once A2 lands |

---

## 6. Inconsistencies / gaps found in the repo that matter for this plan

1. **Stage3 cut canonical edges and kept the long-range ones.** The `s_k–c_{k+1}` "output sibling" pairs are canonical FA structure (`J(S,COUT) = −2` in `reports/coefficients/hamiltonians.json`; cross term `4·s·cout` of `(a+b+c−s−2cout)²`). Stage3 removed those 6 pairs (and 17 canonical triples via `has_cut_pair`) while retaining 222 non-canonical inter-stage pairs. This is the opposite of a "remove feedback loops" cut; E1 tests it directly.
2. **The audit's local-minimum count is on the unclamped cube; the dynamics are clamped.** 1642 is not the number of traps a forward (`ab`) run can fall into. Needs the `free_bits` variant of `local_minimum_codes` (section 1.2).
3. **Absolute γ is not comparable across runs and is not what the sampler feels.** `paper_hyperparams` makes the dynamics scale-invariant; `run_adaptive` already uses `γ / rms_one_bit_energy_jump` as its stopping metric, but `EXPERIMENT_LOG.md` reports raw γ ≈ 2.5e-5 ≈ rms jump 2.4e-5 ≈ valid max deviation 2.5e-5 — i.e. gap, roughness and valid spread are all the same size, which by itself says the landscape is barely resolvable. Use κ (F6).
4. **The hazard auto-cut path is silently disabled.** `load_failure_rates` returns zeros when `out_tiny4_q64/ab_failure_analysis_t20/tiny4_q64/ab_failed_bit_mismatch.csv` is missing; then `fail_geom = 0 < --auto-cut-min-failure 0.35`, so `--auto-cut-edges N` never cuts anything. The default `--auto-cut-stage-weight` is 0, so even with data, stage distance (the feedback proxy) is ignored.
5. **`s6` and `c6` are the same variable.** In all 4096 valid states `s6 == c6`; `same_stage_parent_output` protects the pair, `nonlocal_sum_carry_pairs` allows it, but the Stage4 default `--stage4-candidate-cut-pairs "s6:c6"` proposes cutting exactly this copy edge for 4-body candidates. Decide explicitly whether `s6` is a latch of `c6` (keep a strong copy term; A3) or redundant (drop the node; 24 spins, 2^24 audit).
6. **No sequential update order exists in the QP-world sampler.** `run_updates_numba`/`run_paper_ssa_updates_numba` pick free nodes uniformly at random; carry-ordered block scheduling (windows) and auxiliary carry-state decoupling (frozen shadow) from the VHDL results have no counterpart here, so the Stage 3.A/5.A dynamic tests were never given the schedule that made the 4-bit RCA work. A2/E3 fixes this.
7. **Node-score "convergence failure" component is essentially T = 0.** `--score-beta 5000` in `quick_convergence_fail_bits` makes the 0.20 weight measure greedy-descent failures, not sampler failures under the paper schedule; the two can differ (the paper schedule anneals `I0`).
8. **Missing artefacts.** `out*/` (full2, full3, adaptive_iter*, tiny4, edge_hypercut, convergence CSVs) are git-ignored and absent, so E0 must regenerate them; `staged_cut_verifier.py` defaults hard-depend on `out/full2/*` and `out/full3/*`. The README's "same QP as the 5-bit experiment" refers to nothing in the repo. Gurobi license path is hard-coded to `C:\gurobi1302\gurobi.lic` (Windows) with `GRB_LICENSE_FILE` override.
9. **Dynamic trials are too few for the claimed comparisons.** Default `--trials 5` over 4096 cases gives 20480 trials per mode; fine for large effects, but the 2·SE gate in `compare_adaptive23_convergence.py` cannot resolve < ~1 % differences. Use ≥ 20.
10. **Documentation drift, minor.** `README.md` (experiment) describes `score_i` with `convergence_failure_flip_rate_i`; `EXPERIMENT_LOG.md` and code use `convergence_failure_mismatch_rate`. The local checkout in `/workspace` was at `8f512ce` (before the fast-forward that added `experiments/`); the cleanup-PR merge `0ab0875` is on `origin/main`.

---

## 7. One-paragraph summary

The Stage 5.A optimizer works on a nearly complete 25-node hypergraph (273 of 300 pairs, treewidth ≈ 18) and its hard cuts removed *canonical* intra-block edges rather than inter-stage shortcuts. The most informative next experiments are therefore (i) the canonical/adjacent-block whitelist and span sweep (A1/A8), which starts from the provably feasible 57-pair chain-of-cliques and adds long-range terms in a controlled way; (ii) letting the QP choose the support via reweighted L1 with span-weighted penalties and a trap-attribution pass (A12b/A12a); and (iii) turning "feedback" into a convex constraint — feed-forward dominance ratios `r_u < ρ` and Dobrushin row caps (A6) — combined with an LSB→MSB sweep order in the sampler (A2), which brings carry-ordered scheduling and auxiliary carry-state decoupling into the QP world. All of them plug into `staged_cut_verifier.py`'s pair-blacklist path or into `solve_soft_valid_qp`, and all should be judged by clamped local minima, the scale-free gap κ, and paired paper-SSA success with ≥ 20 trials rather than by raw γ.
