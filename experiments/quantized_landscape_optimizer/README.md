# Quantized Hamiltonian Landscape Optimizer

This folder is a decoupled test area for learning Ising coefficients that are
not only logically correct, but also friendlier to the sampler.

The current production optimizer is Onizawa-style: it forces all truth-table
states to share one energy level, forces invalid states above that level, and
maximizes the valid-invalid gap. The current repo then adds a second MILP stage
that preserves the maximum gate gap and minimizes carry-boundary coefficient
L1. That second stage is local to HA/FA blocks and does not directly optimize
the RCA clamp-SUM landscape.

This experiment keeps the important restriction:

```text
H(v) = E0, for every valid state v
```

Then it adds explicit landscape objectives, starting with total-variation
smoothing over invalid one-bit neighbors.

## Generic Optimizer

`generic_optimizer.py` is the migratable optimizer. It follows a convex core plus
nonconvex verification loop:

- continuous `h,J` are solved with a convex QP;
- every valid state is hard-constrained to one common energy level;
- invalid states have a hard minimum gap;
- invalid-state one-bit energy differences are smoothed by a quadratic penalty;
- coefficients are quantized only after the continuous solve;
- quantized solutions are verified by enumeration over the configured state
  space;
- invalid local minima found after quantization become fixed-parent descent
  cuts in the next loop. The parent is chosen by minimum Hamming distance to the
  valid manifold.

Run built-in gate demos:

```powershell
python experiments\quantized_landscape_optimizer\generic_optimizer.py demo-gate --gate ha
python experiments\quantized_landscape_optimizer\generic_optimizer.py demo-gate --gate fa
```

Run from a portable JSON spec:

```powershell
python experiments\quantized_landscape_optimizer\generic_optimizer.py solve-spec --spec experiments\quantized_landscape_optimizer\specs\ha_demo.json
```

The spec needs only `name`, `nodes`, and `valid_states`. Optional fields are
`state_space`, `smooth_edges`, and `descent_cuts`.

## Commands

Audit the current Q3.4 HA/FA blocks and direct 4-bit RCA landscape:

```powershell
python experiments\quantized_landscape_optimizer\landscape_optimizer.py audit-current
```

Run a first landscape-shaped Q3.4 gate optimization with a moderate target gap:

```powershell
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-gates --target-gap 4 --coeff-max 7
```

Write JSON output if needed:

```powershell
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-gates --target-gap 4 --json-out experiments\quantized_landscape_optimizer\out\q34_gap4.json
```

Run the first composed-RCA optimizer. This keeps the HA/FA valid states at one
common energy level per block, requires a moderate gate gap, smooths the
selected clamp-SUM subspace, and adds cutting-plane descent constraints for
invalid local minima discovered from the current Q3.4 RCA. Trap slack is
weighted by the least number of one-bit flips needed to reach a valid state;
the default is `inverse-square`, so a trap one flip from validity is punished
more strongly than a remote trap:

```powershell
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-rca4 --sums edge --target-gap 4 --descent-margin 1
```

For a quicker smoke test, use a strided TV objective:

```powershell
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-rca4 --sums edge --tv-stride 16 --iterations 1
```

For the exact edge-SUM TV objective, set `--tv-stride 1`. For all 4-bit SUM
clamps, use `--sums all`.

To diagnose whether trap descent is possible in the shared HA/FA coefficient
space, temporarily remove the smoothing and L1 terms:

```powershell
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-rca4 --sums edge --target-gap 4 --boundary-weight 0 --coeff-weight 0 --tv-weight 0 --trap-weight 1000 --tv-stride 64 --iterations 3
```

Use `--trap-distance-mode uniform` to reproduce the older equal-trap objective,
or `inverse`, `inverse-square`, and `exp` to prioritize near-valid traps.

## Direct 8-bit HA/FA RCA Comparison

`compare_8bit_direct.py` compares only the ordinary non-synthesized 8-bit
ripple-carry adder built from one HA block and seven FA blocks. It does not use
the fewest-node synthesized adder, shadow nodes, sequential windows, or other
ideas.

```powershell
python experiments\quantized_landscape_optimizer\compare_8bit_direct.py --optimized-format fp16 --trials 100 --checkpoints 100,250,500,1000
```

Use `--optimized-format q34` to repeat the same direct-8-bit comparison with
fixed Q3.4 coefficients instead of FP16.

To use the local-energy hyperparameter heuristic for a hot-start noise schedule,
use:

```powershell
python experiments\quantized_landscape_optimizer\compare_8bit_direct.py --optimized-format fp16 --coeff-max 7 --min-gap 7 --lambda-smooth 0 --lambda-l2 0 --noise-mode paper-anneal --noise-hold-cycles 100 --noise-decay-cycles 400
```

The script estimates `s_i` as the random-spin local-field standard deviation
`sqrt(sum_j J_ij^2)` for each free node, then sets the initial noise to
`0.6745 * mean(s_i)`, holds it, and linearly decays it to zero.

Each run writes:

- `landscape.csv` with global sampled and clamped-subspace landscape parameters;
  local-minimum rows include distance-to-valid histograms and inverse-distance
  trap penalties;
- `convergence_cases.csv` and `convergence_aggregate.csv`;
- `landscape.svg` and `convergence.svg`;
- `summary.json`.

## Least-Node 8-bit LP And Shadow Experiments

The 25-visible-node adder uses:

```text
a0..a7, b0..b7, s0..s8
```

The paper-style least-node LP is logically valid but coefficient-limited. With
`max |h|, |J| <= 2`, the exact global valid-invalid gap collapses to about:

```text
1 / 8192 = 0.0001220703125
```

This is the expected scaling problem of encoding:

```text
H = alpha * (A + B - S)^2
```

with binary weights up to 256. Decreasing coefficients is possible, but it
also decreases the physical energy gap. That is why the least-node LP baseline
is very weak dynamically.

Run the bounded paper-style LP:

```powershell
$env:GRB_LICENSE_FILE='C:\gurobi1302\gurobi.lic'
python experiments\quantized_landscape_optimizer\least_node_lp_adder8.py --out experiments\quantized_landscape_optimizer\out\least_node_lp_adder8_coeff2_cut --coeff-max 2 --initial-invalid 10000 --rounds 12 --cuts-per-round 4096 --chunk-size 1048576 --seed 20260602 --time-limit 300
```

### Shadow Topologies

`shadow_group_adder8.py` optimizes a least-node visible adder with auxiliary
shadow nodes and a fully connected Ising graph.

Available modes:

```text
group4       25 visible + 4 prefix carry/group shadows
carry8       25 visible + 8 true ripple carry shadows c1..c8
carry8group4 25 visible + 8 carry shadows + 4 local two-bit overflow shadows
```

The current 12-shadow topology is:

```text
c1..c8 = true ripple carry shadows
g0..g3 = local two-bit overflow shadows for bit pairs 0-1, 2-3, 4-5, 6-7
```

The optimizer constrains sampled strict valid states and sampled strict invalid
states, then penalizes valid-energy variance, one-bit roughness variance, and
coefficient L2. The hidden/shadow projection used in the plots is a separate
post-check.

### Gap Definitions

There are two different gaps. Keep them separate:

```text
strict sampled optimizer gap:
    H(strict invalid visible+shadow state) - H(strict valid visible+shadow state)

projected visible gap:
    min_shadow H(invalid visible state, shadow)
      - min_shadow H(valid visible state, shadow)
```

The optimizer can report `gamma = 1.0` while the projected visible gap is much
smaller. This happens when a non-strict shadow assignment gives a low energy to
an invalid visible state. The projected gap is closer to what the sampler sees
when the hidden nodes are free.

### Latest Shadow Runs

Eight true-carry shadows remain the best dynamic result so far:

```powershell
$env:GRB_LICENSE_FILE='C:\gurobi1302\gurobi.lic'
python experiments\quantized_landscape_optimizer\shadow_group_adder8.py --shadow-mode carry8 --method gurobi-qp --coeff-max 2 --min-gap 1 --valid-weight 20000 --tv-weight 10 --coeff-l2-weight 0.01 --valid-samples 8192 --invalid-samples 0 --clamp-invalid-samples 4096 --tv-samples 4000 --time-limit 300 --cutting-rounds 2 --cuts-per-case 128 --cut-margin 1 --seed 20260601 --out experiments\quantized_landscape_optimizer\out\shadow_carry8_gurobi_qp_maxj2_gap1_v8192_c4096_cut2
```

Twelve shadows with a larger optimizing set and no Gurobi time limit:

```powershell
$env:GRB_LICENSE_FILE='C:\gurobi1302\gurobi.lic'
python experiments\quantized_landscape_optimizer\shadow_group_adder8.py --shadow-mode carry8group4 --method gurobi-qp --coeff-max 7 --min-gap 1 --valid-weight 20000 --tv-weight 10 --coeff-l2-weight 0.01 --valid-samples 32768 --invalid-samples 0 --clamp-invalid-samples 8192 --tv-samples 8192 --cutting-rounds 2 --cuts-per-case 256 --cut-margin 1 --seed 20260610 --out experiments\quantized_landscape_optimizer\out\shadow_carry8group4_qp_maxj7_gap1_v32768_c8192_cut2
```

The `coeff-max=7` 12-shadow run did not actually use large coefficients:

```text
realized max |J| = 0.7335
realized max |h| = 0.3482
strict sampled gamma = 1.0
valid_dev_max = 0.7773
tv_mean = 2.4660
```

Compared with the `coeff-max=2` 12-shadow run, the larger coefficient bound
improved projected visible gaps, but did not improve dynamic convergence.

## Real Backward RCA8 Test

`compare_backward_real8.py` runs a repeated stochastic inverse solve:

```text
clamp B and SUM, leave A free, score only final A
```

The shadow/least-node coefficients are quantized to fixed point before the
dynamic run:

```text
Q*.16, physical value = integer / 65536
```

The paper-inspired local-energy schedule estimates:

```text
s_i = sqrt(sum_j J_ij^2)
n_opt = 0.6745 * mean(s_i)
I0_min = 0.01 * max(s_i) + min(|mu_i|)
I0_max = 2.0 * max(s_i) + min(|mu_i|)
```

For the current quick comparison, `n_opt` is constant and `I0` reaches
`I0_max` at cycle 100:

```powershell
python experiments\quantized_landscape_optimizer\compare_backward_real8.py --out experiments\quantized_landscape_optimizer\out\backward_real8_q16_i0max100_constantnopt_shadow12_maxj7 --shadow-solution experiments\quantized_landscape_optimizer\out\shadow_carry8group4_qp_maxj7_gap1_v32768_c8192_cut2\solution.json --frac-bits 16 --trials 100 --checkpoints 100,300,1000,2000 --update-rule paper-ssa --i0-max-time 100 --paper-noise-start-multiplier 1 --paper-noise-end-multiplier 1 --paper-noise-ramp-cycles 0 --seed 20260609
```

Selected-vector result at 2000 cycles, six `(A,B)` cases, 100 random
initializations per case:

| design | success |
| --- | ---: |
| integer HA/FA RCA8 baseline | 32.33% |
| paper-style least-node LP Q16 | 2.17% |
| 8-shadow carry Q16 | 42.33% |
| 12-shadow carry8group4 Q16, `coeff-max=2` | 37.17% |
| 12-shadow carry8group4 Q16, `coeff-max=7` | 34.33% |

Interpretation: the 12-shadow design produces a smoother projected landscape
and the `coeff-max=7` run improves the static projected gap, but the previous
8-shadow carry design is still the best dynamic result under this schedule.

## RCA8 Landscape Visualization

`visualize_shadow_vs_rca8.py` compares the integer HA/FA RCA8 baseline against
a shadow least-node design on the same visible free-state axis.

For the integer RCA8 baseline, `s8` is treated as final carry `c8`, and the
landscape is projected by minimizing over internal carries `c1..c7`. For the
shadow design, the landscape is projected by minimizing over all shadow nodes.

Generate the latest 12-shadow max-`J=7` plots:

```powershell
python experiments\quantized_landscape_optimizer\visualize_shadow_vs_rca8.py --shadow-solution experiments\quantized_landscape_optimizer\out\shadow_carry8group4_qp_maxj7_gap1_v32768_c8192_cut2\solution.json --out experiments\quantized_landscape_optimizer\out\rca8_vs_shadow12_maxj7_landscape
```

Latest projected inverse landscape summary:

| design | avg inverse gap | min inverse gap | avg one-bit jump | avg invalid local minima |
| --- | ---: | ---: | ---: | ---: |
| integer HA/FA RCA8 projected | 2.000 | 2.000 | 1.370 | 10.67 |
| 12-shadow `coeff-max=2` projected | 0.541 | 0.127 | 0.449 | 3.00 |
| 12-shadow `coeff-max=7` projected | 0.588 | 0.223 | 0.451 | 3.50 |

The plots are written to:

```text
experiments/quantized_landscape_optimizer/out/rca8_vs_shadow12_maxj7_landscape
```
