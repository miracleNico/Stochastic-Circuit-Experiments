# Quantized Hamiltonian Landscape Optimizer

## Repository locations

Stage E is the historical archive; Stage G is the reconstructed successor below.
This directory owns the portable `specs/` and documentation. Current Python tools
and tests live in `scripts/quantized_landscape_optimizer/`; Questa launchers and
the static VHDL audit testbench live in `sim_scripts/quantized_landscape_optimizer/`
and its `tb/`. New audit outputs go to
`results_and_reports/quantized_landscape_optimizer/runs/`. Commands run from the
repository root. Historical unavailable commands later in this README are
preserved as provenance, not current entry points.

This folder is a decoupled test area for learning pairwise Ising coefficients
that are logically correct, quantizable, and friendlier to a one-bit-flip
sampler. The original Stage E sources were not committed. The runnable artifact
now present is a reconstruction of the portable generic core described by the
historical notes; it is not a reconstruction of every specialized Stage E
experiment.

The reconstructed optimizer keeps the important restriction:

```text
H(v) = E0, for every valid state v
```

and requires every configured invalid state to lie at least `min_gap` above that
common level. It then smooths energy differences between selected invalid
one-bit neighbors and adds verified descent cuts for invalid local minima.

## Reconstructed Generic Optimizer

`generic_optimizer.py` is a standalone NumPy-only command-line tool and Python
module. It does not require SciPy, CVXPY, Gurobi, or a solver license. For bits
`x_i`, it uses spins `s_i = 2*x_i - 1` and the pairwise Hamiltonian

```text
H(x) = -sum_i h_i*s_i - sum_{i<j} J_ij*s_i*s_j
```

The flat coefficient order in JSON is `h0..hN-1`, followed by `J01, J02, ...`
in lexicographic pair order. The named `h` vector and symmetric `j` matrix are
also emitted so consumers do not need to reconstruct that ordering.

### Method

The optimizer uses a convex core plus an exhaustive quantization-and-cut loop:

1. Eliminate the hard equal-valid-energy equations with an SVD null space.
2. Solve a convex QP that combines mean squared jumps over smoothing edges and
   coefficient L2, subject to the invalid-state gap, coefficient bounds, and
   any active descent cuts. A small OSQP-style ADMM solver implemented with
   NumPy performs this step.
3. Round each coefficient to the configured lattice and clamp it to the largest
   lattice point not exceeding `coeff_max`.
4. Exhaustively audit every state in the configured `state_space`. This audit,
   not the continuous QP, is authoritative: quantization must preserve both
   valid-state equality and the requested gap.
5. Treat an invalid state whose energy is no greater than all available
   one-bit neighbors (within the verification tolerance) as a local minimum;
   plateaus therefore count. For each such state, choose a deterministic
   one-bit parent that minimizes distance to the valid set, add or strengthen
   `H(state) - H(parent) >= descent_margin`, and solve again.

The loop succeeds only when the quantized exhaustive audit has no invalid local
minimum. It otherwise fails after `max_iterations`. Because a one-bit flip
changes Ising features by two, quantized energy differences occur in multiples
of `2*quantum`; choose gap and descent settings with that lattice in mind.

### Commands

Run built-in gate demos:

```powershell
python scripts\quantized_landscape_optimizer\generic_optimizer.py demo-gate --gate ha
python scripts\quantized_landscape_optimizer\generic_optimizer.py demo-gate --gate fa
```

Solve the included portable half-adder spec and save the same JSON that is
printed to standard output:

```powershell
python scripts\quantized_landscape_optimizer\generic_optimizer.py solve-spec --spec experiments\quantized_landscape_optimizer\specs\ha_demo.json --json-out results_and_reports\quantized_landscape_optimizer\out\ha_demo_result.json
```

Both subcommands accept the same solver options. The defaults are:

| option | default | meaning |
| --- | ---: | --- |
| `--coeff-max` | `7.0` | absolute bound for every continuous and quantized coefficient |
| `--min-gap` | `1.0` | minimum energy of every invalid state above the common valid level |
| `--quantum` | `0.0625` | coefficient quantization step (`1/16`) |
| `--smooth-weight` | `1.0` | weight on mean squared energy jumps over smoothing edges |
| `--l2-weight` | `0.01` | weight on squared coefficient magnitude |
| `--descent-margin` | `0.0625` | default margin for generated or margin-less descent cuts |
| `--max-iterations` | `8` | maximum quantize/audit/cut rounds |
| `--verification-tolerance` | `1e-6` | tolerance for exhaustive equality, gap, and local-minimum checks |
| `--qp-max-iterations` | `50000` | ADMM iteration limit per continuous QP |
| `--qp-abs-tolerance` | `1e-8` | ADMM absolute stopping tolerance |
| `--qp-rel-tolerance` | `1e-7` | ADMM relative stopping tolerance |
| `--qp-rho` | `1.0` | initial ADMM penalty parameter |
| `--json-out` | none | optional result path; parent directories are created |

At least one of `smooth-weight` and `l2-weight` must be positive. The ADMM
regularization (`1e-7`) and rho-adaptation interval (`50`) are fixed internal
settings and are included in the result's settings object.

### Portable JSON Specification

Only `name`, `nodes`, and `valid_states` are required. A state may be a bit
array such as `[0, 1, 1, 0]` or a bit string such as `"0110"`; positions follow
the order in `nodes`.

```json
{
  "name": "half_adder_demo",
  "description": "Optional human-readable description",
  "nodes": ["A", "B", "S", "C"],
  "valid_states": [
    [0, 0, 0, 0],
    [0, 1, 1, 0],
    [1, 0, 1, 0],
    [1, 1, 0, 1]
  ]
}
```

Optional fields:

- `description`: a string copied into the result.
- `state_space`: the exact states to constrain and audit. When omitted, the
  full `2^N` cube is generated. More than 16 nodes requires an explicit state
  space. Every valid state must be included, and at least one state must be
  invalid.
- `smooth_edges`: an array of `[state, neighbor]` pairs. Both endpoints must be
  configured invalid states at Hamming distance one. When omitted, every
  invalid-to-invalid one-bit edge in `state_space` is used; an empty array
  explicitly disables the smoothing-edge set.
- `descent_cuts`: initial fixed-parent constraints. Each entry may be
  `{"state": ..., "parent": ..., "margin": ...}` or
  `[state, parent, optional_margin]`. `state` must be invalid, both endpoints
  must be in `state_space`, and they must differ by one bit. A missing margin
  uses `--descent-margin`.

Unknown keys, duplicate states, edges, or cuts, and invalid smooth-edge or
descent-cut topology are rejected instead of being silently ignored. All
exhaustive claims are relative to the configured `state_space`; a restricted
space is not an audit of the full cube.

### Result JSON and Failure Behavior

On success, the tool prints a versioned JSON object and optionally writes it to
`--json-out`. Its top-level fields are:

- `schema_version` and `status` (`1` and `"success"`);
- `problem`, with the name, description, nodes, and state counts;
- `settings`, including public and fixed internal solver settings;
- `continuous` and `quantized`, each with the flat coefficient vector, named
  `h`, symmetric `j`, and an exhaustive `audit`;
- `qp`, with convergence, residual, constraint-violation, objective, rho, and
  null-space statistics from the final continuous solve;
- `iterations`, the per-round audits, QP statistics, active-cut count, and cuts
  added or strengthened in that round;
- `descent_cuts`, the final cumulative fixed-parent cut set.

Each audit reports valid-energy spread and equality, minimum invalid gap,
invalid local-minimum states and their distance to validity, smoothing-edge
roughness, and coefficient scale. A malformed specification, invalid setting,
infeasible or insufficiently converged QP, failed quantized equality/gap, or
remaining traps after the iteration limit prints `error: ...` to standard error
and exits with status `2`. Failed runs do not write a success JSON file.

## Questa Evidence

Two focused entrypoints provide the static and dynamic evidence used by the
main reproduction workflow. They use the repository's isolated simulator
runner, default to Questa, and accept the common `-VsimPath`, `-LicenseFile`,
`-LicenseServer`, `-BuildRoot`, `-RunId`, `-WaveMode`, `-KeepWork`, and
`-TimeoutSeconds` parameters. `-PythonPath` is optional when `python.exe` or the
process-only `PYTHON` variable is available. `-PassThru` returns the run,
transcript, metadata, wave, and verification paths for orchestration code.

```powershell
./sim_scripts/quantized_landscape_optimizer/run_questa_audit.ps1
./sim_scripts/quantized_landscape_optimizer/run_generated_gates_audit.ps1
```

`run_questa_audit.ps1` solves the built-in HA and FA problems, writes temporary
optimizer JSON, and passes it to `export_vhdl_coefficients.py`. The exporter
parses the current `experiments/gate_baseline/hardware/generated_networks.vhd` `BIAS`/`W*` values and refuses
to emit a package unless every RTL coefficient is exactly twice the optimizer
coefficient. The VHDL audit then enumerates all 16 HA and 32 FA states and
requires:

- optimizer valid energy `-2`, gap `1`, and zero invalid local minima;
- current RTL valid energy `-4`, gap `2`, and zero invalid local minima;
- per-state energy scaling by two and identical local-minimum structure.

`run_generated_gates_audit.ps1` compiles only the generated-gate dependencies
and `tb_generated_gates`. Its final pass marker is reached after the four HA/XOR
forward cases, two reverse cases, and eight FA forward cases. Both wrappers run
`verify_questa_evidence.py`; a zero simulator process exit is insufficient
without every required report marker and the `Errors: 0, Warnings: 0` summary.
The run's `raw` directory retains the verification JSON and, for the static
audit, the exact optimizer JSON and generated VHDL package.

## Historical Stage E Archive (Scripts Unavailable)

Everything below this heading is retained as a record of the original Stage E
experiments and results. The referenced Python scripts, saved solutions, and
`out` directories are not present in this checkout, so the recorded commands
are **not runnable here** and the results have not been regenerated by the
reconstructed generic optimizer. In particular, the reconstruction does not
claim to replace the RCA4/RCA8, least-node, shadow-node, backward-sampling, or
visualization workflows described below.

### Former `landscape_optimizer.py` Commands (Unavailable)

Historical command record for auditing the Q3.4 HA/FA blocks and direct 4-bit
RCA landscape (unavailable):

```text
python experiments\quantized_landscape_optimizer\landscape_optimizer.py audit-current
```

Historical command record for a landscape-shaped Q3.4 gate optimization
(unavailable):

```text
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-gates --target-gap 4 --coeff-max 7
```

Historical JSON-output command (unavailable):

```text
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-gates --target-gap 4 --json-out results_and_reports\quantized_landscape_optimizer\out\q34_gap4.json
```

The recorded composed-RCA optimizer kept the HA/FA valid states at one
common energy level per block, required a moderate gate gap, smoothed the
selected clamp-SUM subspace, and added cutting-plane descent constraints for
invalid local minima discovered from the current Q3.4 RCA. Trap slack is
weighted by the least number of one-bit flips needed to reach a valid state;
the default is `inverse-square`, so a trap one flip from validity is punished
more strongly than a remote trap. Its historical command is unavailable:

```text
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-rca4 --sums edge --target-gap 4 --descent-margin 1
```

Historical strided-TV smoke command (unavailable):

```text
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-rca4 --sums edge --tv-stride 16 --iterations 1
```

The former script used `--tv-stride 1` for the exact edge-SUM TV objective and
`--sums all` for all 4-bit SUM clamps.

The former diagnostic removed the smoothing and L1 terms to test whether trap
descent was possible in the shared HA/FA coefficient space. Its recorded
command is unavailable:

```text
python experiments\quantized_landscape_optimizer\landscape_optimizer.py optimize-rca4 --sums edge --target-gap 4 --boundary-weight 0 --coeff-weight 0 --tv-weight 0 --trap-weight 1000 --tv-stride 64 --iterations 3
```

The former `--trap-distance-mode` choices were `uniform` for the older
equal-trap objective and `inverse`, `inverse-square`, or `exp` for prioritizing
near-valid traps.

## Historical Direct 8-bit HA/FA RCA Comparison (Unavailable)

The missing `compare_8bit_direct.py` compared only the ordinary non-synthesized
8-bit ripple-carry adder built from one HA block and seven FA blocks. It did not use
the fewest-node synthesized adder, shadow nodes, sequential windows, or other
ideas.

Recorded command (not runnable in this checkout):

```text
python experiments\quantized_landscape_optimizer\compare_8bit_direct.py --optimized-format fp16 --trials 100 --checkpoints 100,250,500,1000
```

The former `--optimized-format q34` mode repeated the same direct-8-bit
comparison with fixed Q3.4 coefficients instead of FP16.

The recorded local-energy hyperparameter command is also unavailable:

```text
python experiments\quantized_landscape_optimizer\compare_8bit_direct.py --optimized-format fp16 --coeff-max 7 --min-gap 7 --lambda-smooth 0 --lambda-l2 0 --noise-mode paper-anneal --noise-hold-cycles 100 --noise-decay-cycles 400
```

The script estimates `s_i` as the random-spin local-field standard deviation
`sqrt(sum_j J_ij^2)` for each free node, then sets the initial noise to
`0.6745 * mean(s_i)`, holds it, and linearly decays it to zero.

Each historical run wrote:

- `landscape.csv` with global sampled and clamped-subspace landscape parameters;
  local-minimum rows include distance-to-valid histograms and inverse-distance
  trap penalties;
- `convergence_cases.csv` and `convergence_aggregate.csv`;
- `landscape.svg` and `convergence.svg`;
- `summary.json`.

## Historical Least-Node 8-bit LP And Shadow Experiments (Unavailable)

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

Recorded bounded paper-style LP command (not runnable in this checkout):

```text
$env:GRB_LICENSE_FILE='C:\gurobi1302\gurobi.lic'
python experiments\quantized_landscape_optimizer\least_node_lp_adder8.py --out results_and_reports\quantized_landscape_optimizer\out\least_node_lp_adder8_coeff2_cut --coeff-max 2 --initial-invalid 10000 --rounds 12 --cuts-per-round 4096 --chunk-size 1048576 --seed 20260602 --time-limit 300
```

### Shadow Topologies

The missing `shadow_group_adder8.py` optimized a least-node visible adder with auxiliary
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

The missing optimizer constrained sampled strict valid states and sampled
strict invalid states, then penalized valid-energy variance, one-bit roughness
variance, and coefficient L2. The hidden/shadow projection used in the plots
was a separate post-check.

### Gap Definitions

There are two different gaps. Keep them separate:

```text
strict sampled optimizer gap:
    H(strict invalid visible+shadow state) - H(strict valid visible+shadow state)

projected visible gap:
    min_shadow H(invalid visible state, shadow)
      - min_shadow H(valid visible state, shadow)
```

The historical optimizer could report `gamma = 1.0` while the projected visible
gap was much smaller. This happened when a non-strict shadow assignment gave a
low energy to an invalid visible state. The projected gap was closer to what
the sampler saw when the hidden nodes were free.

### Latest Shadow Runs

Eight true-carry shadows were the best recorded dynamic result. The command is
retained only as historical provenance and is not runnable in this checkout:

```text
$env:GRB_LICENSE_FILE='C:\gurobi1302\gurobi.lic'
python experiments\quantized_landscape_optimizer\shadow_group_adder8.py --shadow-mode carry8 --method gurobi-qp --coeff-max 2 --min-gap 1 --valid-weight 20000 --tv-weight 10 --coeff-l2-weight 0.01 --valid-samples 8192 --invalid-samples 0 --clamp-invalid-samples 4096 --tv-samples 4000 --time-limit 300 --cutting-rounds 2 --cuts-per-case 128 --cut-margin 1 --seed 20260601 --out results_and_reports\quantized_landscape_optimizer\out\shadow_carry8_gurobi_qp_maxj2_gap1_v8192_c4096_cut2
```

Recorded twelve-shadow command (not runnable in this checkout):

```text
$env:GRB_LICENSE_FILE='C:\gurobi1302\gurobi.lic'
python experiments\quantized_landscape_optimizer\shadow_group_adder8.py --shadow-mode carry8group4 --method gurobi-qp --coeff-max 7 --min-gap 1 --valid-weight 20000 --tv-weight 10 --coeff-l2-weight 0.01 --valid-samples 32768 --invalid-samples 0 --clamp-invalid-samples 8192 --tv-samples 8192 --cutting-rounds 2 --cuts-per-case 256 --cut-margin 1 --seed 20260610 --out results_and_reports\quantized_landscape_optimizer\out\shadow_carry8group4_qp_maxj7_gap1_v32768_c8192_cut2
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

## Historical Real Backward RCA8 Test (Unavailable)

The missing `compare_backward_real8.py` ran a repeated stochastic inverse solve:

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

For the recorded quick comparison, `n_opt` was constant and `I0` reached
`I0_max` at cycle 100. This command is not runnable in this checkout:

```text
python experiments\quantized_landscape_optimizer\compare_backward_real8.py --out results_and_reports\quantized_landscape_optimizer\out\backward_real8_q16_i0max100_constantnopt_shadow12_maxj7 --shadow-solution results_and_reports\quantized_landscape_optimizer\out\shadow_carry8group4_qp_maxj7_gap1_v32768_c8192_cut2\solution.json --frac-bits 16 --trials 100 --checkpoints 100,300,1000,2000 --update-rule paper-ssa --i0-max-time 100 --paper-noise-start-multiplier 1 --paper-noise-end-multiplier 1 --paper-noise-ramp-cycles 0 --seed 20260609
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

## Historical RCA8 Landscape Visualization (Unavailable)

The missing `visualize_shadow_vs_rca8.py` compared the integer HA/FA RCA8 baseline against
a shadow least-node design on the same visible free-state axis.

For the integer RCA8 baseline, `s8` is treated as final carry `c8`, and the
landscape is projected by minimizing over internal carries `c1..c7`. For the
shadow design, the landscape is projected by minimizing over all shadow nodes.

Recorded plot-generation command (not runnable in this checkout):

```text
python experiments\quantized_landscape_optimizer\visualize_shadow_vs_rca8.py --shadow-solution results_and_reports\quantized_landscape_optimizer\out\shadow_carry8group4_qp_maxj7_gap1_v32768_c8192_cut2\solution.json --out results_and_reports\quantized_landscape_optimizer\out\rca8_vs_shadow12_maxj7_landscape
```

Latest projected inverse landscape summary:

| design | avg inverse gap | min inverse gap | avg one-bit jump | avg invalid local minima |
| --- | ---: | ---: | ---: | ---: |
| integer HA/FA RCA8 projected | 2.000 | 2.000 | 1.370 | 10.67 |
| 12-shadow `coeff-max=2` projected | 0.541 | 0.127 | 0.449 | 3.00 |
| 12-shadow `coeff-max=7` projected | 0.588 | 0.223 | 0.451 | 3.50 |

The historical plots were written to:

```text
results_and_reports/quantized_landscape_optimizer/out/rca8_vs_shadow12_maxj7_landscape
```
