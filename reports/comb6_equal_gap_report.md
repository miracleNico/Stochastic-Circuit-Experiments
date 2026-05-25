# COMB6 E3M4 Equal-Gap Experiment

Date: 2026-05-24

## Purpose

This experiment tests whether larger dynamic-range E3M4 coefficients help a purely combinational composed network converge, without the timing-like carry dependency present in ripple adders.

The benchmark is `COMB6_MIXED`, a 6-input, 4-output mixed gate network with 21 total spins and 11 composed gate blocks:

```text
u0 = x0 AND x1
u1 = x2 OR x3
u2 = x4 NAND x5
u3 = x0 XOR x2
u4 = x1 XNOR x5
v0 = u0 XOR u1
v1 = u2 AND u3
v2 = u1 NOR u4
y1 = v1 OR v2
y2 = u3 XNOR u4
y3 = v0 NAND y2

observed signature = {y3, y2, y1, v0}
```

## Idea 2: Equalize Intrablock Gap

The integer baseline has different block gaps:

```text
AND/OR/NAND/NOR gap = 4
XOR/XNOR gap        = 2
```

The E3M4 equal-gap run encodes coefficients with:

```text
format: E3M4 b1
FIELD_FRAC_BITS: 4
physical value = encoded / 16
target intrablock gap = 4.0 physical = 64 encoded
```

This keeps the 3-node gates at their original physical scale and scales the XOR/XNOR-style 4-node blocks by 2x.

## Results

All diagnostics clamp the six primary inputs, sample the four-output signature for all 64 input vectors, and use `COUNT_CYCLES=1000`.

```text
Integer baseline, RND=1, SETTLE=1000:
top_matches=21/64, zero_hit_cases=39, avg_hits=313.9/1000

Integer baseline, RND=1, SETTLE=20000:
top_matches=50/64, zero_hit_cases=14, avg_hits=741.9/1000

E3M4 equal-gap, RND=16, SETTLE=1000:
top_matches=57/64, zero_hit_cases=2, avg_hits=855.2/1000

E3M4 equal-gap, RND=16, SETTLE=5000:
top_matches=62/64, zero_hit_cases=2, avg_hits=968.8/1000

E3M4 equal-gap, RND=16, SETTLE=20000:
top_matches=64/64, zero_hit_cases=0, min_hits=997/1000, avg_hits=999.1/1000
```

Conclusion: equalizing intrablock gaps is strongly beneficial for this combinational benchmark. Unlike the ripple-carry adder, this network has no long carry wavefront, so increasing the weaker block gaps improves consistency without creating the same timing-lock failure mode.

## E3M4 Coefficients

Encoded values are shown below. Divide by 16 for physical values.

```text
AND h = [16, 16, -32]
J = [[0, -16, 32],
     [-16, 0, 32],
     [32, 32, 0]]

OR h = [-16, -16, 32]
J = [[0, -16, 32],
     [-16, 0, 32],
     [32, 32, 0]]

NAND h = [16, 16, 32]
J = [[0, -16, -32],
     [-16, 0, -32],
     [-32, -32, 0]]

NOR h = [-16, -16, -32]
J = [[0, -16, -32],
     [-16, 0, -32],
     [-32, -32, 0]]

HA_XOR h = [32, 32, -32, -64]
J = [[0, -32, 32, 64],
     [-32, 0, 32, 64],
     [32, 32, 0, -64],
     [64, 64, -64, 0]]

XNOR h = [32, 32, 32, -64]
J = [[0, -32, -32, 64],
     [-32, 0, -32, 64],
     [-32, -32, 0, 64],
     [64, 64, 64, 0]]
```

Generated artifacts:

```text
sim/experiments/generated_networks_comb6_e3m4_equal_gap.vhd
reports/comb6_e3m4_equal_gap.json
```

Follow-on time-dependent RCA results are documented in:

```text
reports/time_dependent_annealing_report.md
```
