# 6-Bit Adaptive QP Experiment Log

## 2026-07-08: Stage3 Hard-Cut Restart With 16 Solver Threads

Purpose:

- test hard-cutting known risky output-related pairs before optimization;
- keep the Stage3 QP restricted to 2/3-body terms;
- cap Gurobi to `16` logical threads, corresponding to the requested `16T/8C` setting.

Command:

```powershell
python .\experiments\multibody_hamiltonian_6bit_adaptive_qp\staged_cut_verifier.py `
  --stage stage3 `
  --out .\experiments\multibody_hamiltonian_6bit_adaptive_qp\out_staged_cut_sum_sibling_hard_run_t16 `
  --stage3-cut-sum-sum `
  --stage3-cut-output-siblings `
  --max-rounds 4 `
  --gurobi-threads 16
```

Gurobi confirmed:

```text
Set parameter Threads to value 16
Thread count: 12 physical cores, 24 logical processors, using up to 16 threads
```

Hard-cut pair set:

```text
s0-s1, s0-s2, s0-s3, s0-s4, s0-s5, s0-s6, s0-c1,
s1-s2, s1-s3, s1-s4, s1-s5, s1-s6, s1-c2,
s2-s3, s2-s4, s2-s5, s2-s6, s2-c3,
s3-s4, s3-s5, s3-s6, s3-c4,
s4-s5, s4-s6, s4-c5,
s5-s6, s5-c6
```

Node score:

```text
score_i =
  0.25 * valid_entropy_i
+ 0.25 * bad_state_entropy_i
+ 0.30 * nearest_valid_mismatch_rate_i
+ 0.20 * convergence_failure_mismatch_rate_i
```

Critical-node score:

```text
linear_score_i =
  normalize(score_i)
+ 1.5 * normalize(node_bad_state_mi_i)
+ 0.25 * normalize(full3_node_support_i)
```

Selected critical nodes:

```text
s6, c4, c6
```

Top critical-node rows:

| rank | node | base score | bad-state MI | full3 support | linear score | critical |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 0 | c6 | 0.8574 | 0.3808 | 0.001109 | 1.0000 | yes |
| 1 | s6 | 0.8491 | 0.3808 | 0.001109 | 0.9789 | yes |
| 2 | c4 | 0.9245 | 0.3023 | 0.001951 | 0.9477 | yes |
| 3 | c5 | 0.8817 | 0.2644 | 0.001822 | 0.7031 | no |
| 4 | c3 | 0.9069 | 0.2306 | 0.002163 | 0.6701 | no |

Triple ranking:

```text
triple_value =
  1.0  * sum(node_score_i for i in triple)
+ 0.5  * normalized_full3_support(triple)
+ 0.25 * sum(valid_mi_ij in triple)
- 0.25 * sum(bad_mi_ij in triple)
```

Stage3 term selection:

| item | value |
| --- | ---: |
| total terms | 2083 |
| 1-body terms | 25 |
| 2-body terms | 273 |
| 3-body terms | 1785 |
| removed 1/2-body terms by hard cut | 27 |
| ranked candidate triples after hard cuts | 1785 |
| selected triples | 1785 |
| rejected triples by hard cut | 515 |

Cutting-plane closure:

| round | active cuts | violations | new cuts | gamma | min invalid gap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 133012 | 100774 | 25000 | 2.4992188e-05 | -7.3371601e-06 |
| 1 | 141450 | 8438 | 8438 | 2.4987659e-05 | 1.7565356e-05 |
| 2 | 141521 | 71 | 71 | 2.4998632e-05 | 2.2479988e-05 |
| 3 | 141521 | 0 | 0 | 2.4994225e-05 | 2.4969393e-05 |

Final exhaustive audit:

| metric | value |
| --- | ---: |
| state count | 33554432 |
| valid states | 4096 |
| invalid states | 33550336 |
| gap violations | 0 |
| valid energy std | 4.6474353e-09 |
| valid max deviation | 2.5018821e-05 |
| valid over soft cap | 0 |
| invalid local minima | 1642 |
| rms one-bit energy jump | 2.4065113e-05 |
| nonzero terms `abs > 1e-9` | 1376 |

Interpretation:

The hard-cut Stage3 QP is statically feasible: it closes the exhaustive gap
audit with zero violations while excluding all SUM-SUM and SUM-to-next-carry
2-body substructures from the 2/3-body Hamiltonian. This does not yet prove a
dynamic convergence improvement. The invalid local-minimum count remains high,
so Stage4 or a revised term-selection strategy is still needed before claiming
sampler-level improvement.
