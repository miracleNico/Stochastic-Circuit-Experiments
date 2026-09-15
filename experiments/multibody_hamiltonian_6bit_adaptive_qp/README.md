# 6-Bit Least+6-Shadow Adaptive 2/3/4-Body QP

> Part of the project experiment history: see [reports/experiment_timeline.md](../../reports/experiment_timeline.md).

This folder contains an isolated continuous floating-point experiment for a
6-bit least-node direct adder with six true carry-shadow nodes.

```text
nodes = a0..a5, b0..b5, s0..s6, c1..c6
node_count = 25
valid states = 2^(2*6) = 4096
full state cube = 2^25 = 33,554,432
```

This is not ModelSim/VHDL and is not quantized RTL. Coefficients are optimized
as continuous float64 values with Gurobi.

## QP Formulation

For spin state `x` and coefficient vector `theta`,

```text
H_theta(x) = a_x^T theta
```

Each run solves a soft-valid QP over a cutting-plane invalid set:

```text
minimize
  - gamma
  + 20000 / |V| * sum_v (H(v)-E0)^2
  + 200000 / |V| * sum_v max(|H(v)-E0|-0.5, 0)^2
  + 100 * E_{x,i}[(H(x)-H(flip_i(x)))^2]
  + 0.1 / |T| * ||theta||_2^2

subject to
  H(u) >= E0 + gamma        for active invalid cuts u
  |theta_i| <= 2
  gamma >= 0
```

The full-cube roughness term is evaluated analytically. For a term of order
`k`, its contribution is `4*k/N * theta_i^2`, so the roughness remains a convex
quadratic penalty without materializing all one-bit edges.

Valid energies are not hard-forced to a single value. Instead, deviations are
penalized strongly, and deviations above `0.5` receive an additional squared
soft-cap penalty.

## Runs

```powershell
python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\adaptive_qp_6bit.py unit-check

python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\adaptive_qp_6bit.py run-all `
  --out .\experiments\multibody_hamiltonian_6bit_adaptive_qp\out

python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\adaptive_qp_6bit.py run-baseline `
  --order 3 `
  --out .\experiments\multibody_hamiltonian_6bit_adaptive_qp\out

python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\adaptive_qp_6bit.py run-adaptive `
  --out .\experiments\multibody_hamiltonian_6bit_adaptive_qp\out `
  --full3-solution .\experiments\multibody_hamiltonian_6bit_adaptive_qp\out\full3\solution_full3.json

python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\compare_adaptive23_convergence.py `
  --schedule paper-ssa `
  --paper-noise common `
  --out-dir .\experiments\multibody_hamiltonian_6bit_adaptive_qp\out_adaptive23\convergence_compare_paper_ssa_common `
  --cycles 1000 `
  --trials 5

python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\staged_cut_verifier.py `
  --stage stage3 `
  --out .\experiments\multibody_hamiltonian_6bit_adaptive_qp\out_staged_cut_sum_sibling_hard_run_t16 `
  --stage3-cut-sum-sum `
  --stage3-cut-output-siblings `
  --max-rounds 4 `
  --gurobi-threads 16
```

`run-all` performs:

1. `full2`: all 1/2-body terms, 325 coefficients.
2. `full3`: all 1/2/3-body terms, 2625 coefficients.
3. `adaptive_iter*`: all 1/2-body terms plus selected 3/4-body terms.

`run-baseline` and `run-adaptive` are restart helpers. They avoid rerunning
completed stages when a long adaptive QP needs to be resumed from the saved
`full3` solution. Every QP round writes `gurobi_round*.log` inside the run
directory for solver-progress inspection.

The adaptive loop scores nodes by:

```text
score_i =
  0.25 * valid_entropy_i
+ 0.25 * bad_state_entropy_i
+ 0.30 * nearest_valid_mismatch_rate_i
+ 0.20 * convergence_failure_flip_rate_i
```

Then it assigns the lowest 50% of nodes to max order 2, the 50%-80% band to
max order 3, and the top 20% to max order 4, with at least 12 nodes eligible
for order >=3 and at least 6 nodes eligible for order 4.

The staged hard-cut verifier is used for controlled edge/hyperedge removal
experiments. The current documented Stage3 run hard-cuts all SUM-SUM pairs and
the local SUM-to-next-carry/output-sibling pairs before selecting 2/3-body
terms. Its detailed selection rule, node scores, and final closure metrics are
recorded in `EXPERIMENT_LOG.md`.

## Outputs

Each run directory writes:

- `solution_<run>.json`
- `cut_history.csv`
- `exhaustive_audit.json`
- `metrics.csv`
- `energy_histogram.png`
- `valid_energy_spread.png`
- `local_minimum_energy_histogram.png`
- `low_energy_invalid_states.png`

The root output directory writes:

- `comparison_summary.csv`
- `comparison_summary.png`
- `convergence_paired.csv` and `convergence_comparison.csv` after
  `compare_adaptive23_convergence.py`

Convergence comparisons should use the local-energy-distribution
hyperparameters from Onizawa et al. by default. The comparison runner computes
the paper schedule separately for each Hamiltonian:

```text
n_rnd = 0.6745 * mean(s_i)
I0min = 0.01 * max(s_i) + min(|mu_i|)
I0max = 2 * max(s_i) + min(|mu_i|)
```

`--paper-noise common` uses the SSA common-noise setting. `--paper-noise unique`
uses the SSAU per-node setting `n_rnd,i = 0.6745 * s_i`. The old fixed-tanh
beta sweep is retained only as an explicit legacy mode with
`--schedule fixed-tanh`.

If the paper-derived noise is too high for a clamped logic task, the runner can
keep the paper's initial noise magnitude but decay it exponentially:

```powershell
python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\compare_adaptive23_convergence.py `
  --schedule paper-ssa `
  --paper-noise common `
  --paper-noise-decay exp `
  --paper-noise-final-ratio 0.1 `
  --cycles 1000 `
  --trials 5
```

This is an annealing extension to the paper schedule: `I0min`, `I0max`, and the
initial `n_rnd` are still determined from the local energy distribution.

The exhaustive audit evaluates all `2^25` states with a Walsh-Hadamard transform
and reports gap violations, valid spread, invalid local minima, sampled
local-minimum distance to the valid set, one-bit jump statistics, and coefficient
scale.

## Practical Controls

The default run has no Gurobi time limit and no active-cut cap. If memory becomes
the bottleneck, use:

```powershell
--max-active-cuts 80000
```

This keeps the lowest-gap active cuts after each exhaustive audit. Closure is
still determined only by a full-cube pass with zero gap violations, so capped
runs should be treated as incomplete unless `gap_violation_count = 0`.

If a long QP is interrupted after a round has written active cuts, resume that
run directory with:

```powershell
--resume-cuts
```

If barrier spends a long numerical tail after the objective has stabilized, a
looser barrier tolerance can be tested explicitly:

```powershell
--bar-conv-tol 1e-7
```

To restrict Gurobi CPU usage, pass an explicit thread cap:

```powershell
--gurobi-threads 16
```

The `16` setting means 16 logical solver threads. On the current workstation,
Gurobi reports `12 physical cores, 24 logical processors`; therefore `16`
matches the requested `16T/8C` operating point.

Visualization samples invalid-state histograms by default to keep Matplotlib
from processing tens of millions of points:

```powershell
--plot-invalid-sample 1000000
```

Metrics remain exhaustive except for explicitly named sampled quantities such as
sampled one-bit jump percentiles and sampled local-minimum distance histograms.
