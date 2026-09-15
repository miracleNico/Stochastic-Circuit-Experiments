# Hamiltonian coefficients

All coefficients use bipolar spins with logic 0 -> -1 and logic 1 -> +1.

Adder and bitcount note:

The paper uses bitcount primarily to reduce multiplier node count by removing vertical internal adder connections.
For adders, the direct n-bit adder row with 3n + 1 nodes is already the minimum-node direct Hamiltonian form.
This project intentionally emits HA/FA-composed ripple adders for clarity and block-scaling experiments,
so `ADDER4_RIPPLE` uses 16 nodes and `ADDER8_RIPPLE` uses 32 nodes.

## AND

entity: gen_and_gate
source: 3-node LP block
weight_scale: 1
field_frac_bits: 0
nodes (3): A, B, Y
valid_energy: -3
energy_gap: 4

h:
```text
[1, 1, -2]
```

J:
```text
[ 0 -1  2]
[-1  0  2]
[ 2  2  0]
```

## OR

entity: gen_or_gate
source: 3-node LP block
weight_scale: 1
field_frac_bits: 0
nodes (3): A, B, Y
valid_energy: -3
energy_gap: 4

h:
```text
[-1, -1, 2]
```

J:
```text
[ 0 -1  2]
[-1  0  2]
[ 2  2  0]
```

## NAND

entity: gen_nand_gate
source: 3-node LP block
weight_scale: 1
field_frac_bits: 0
nodes (3): A, B, Y
valid_energy: -3
energy_gap: 4

h:
```text
[1, 1, 2]
```

J:
```text
[ 0 -1 -2]
[-1  0 -2]
[-2 -2  0]
```

## NOR

entity: gen_nor_gate
source: 3-node LP block
weight_scale: 1
field_frac_bits: 0
nodes (3): A, B, Y
valid_energy: -3
energy_gap: 4

h:
```text
[-1, -1, -2]
```

J:
```text
[ 0 -1 -2]
[-1  0 -2]
[-2 -2  0]
```

## HA_XOR

entity: gen_xor_gate
source: 4-node LP HA/XOR block
weight_scale: 1
field_frac_bits: 0
nodes (4): A, B, S, C
valid_energy: -4
energy_gap: 2

h:
```text
[1, 1, -1, -2]
```

J:
```text
[ 0 -1  1  2]
[-1  0  1  2]
[ 1  1  0 -2]
[ 2  2 -2  0]
```

## XNOR

entity: gen_xnor_gate
source: 4-node LP XNOR block
weight_scale: 1
field_frac_bits: 0
nodes (4): A, B, Y, C
valid_energy: -4
energy_gap: 2

h:
```text
[1, 1, 1, -2]
```

J:
```text
[ 0 -1 -1  2]
[-1  0 -1  2]
[-1 -1  0  2]
[ 2  2  2  0]
```

## FA

entity: gen_fa_gate
source: 5-node LP FA block
weight_scale: 1
field_frac_bits: 0
nodes (5): A, B, CIN, S, COUT
valid_energy: -4
energy_gap: 2

h:
```text
[0, 0, 0, 0, 0]
```

J:
```text
[ 0 -1 -1  1  2]
[-1  0 -1  1  2]
[-1 -1  0  1  2]
[ 1  1  1  0 -2]
[ 2  2  2 -2  0]
```

## ADDER4_RIPPLE

entity: gen_adder4
source: Composed HA/FA 4-bit ripple adder, HA scale=1, FA scale=1
weight_scale: 1
field_frac_bits: 0
nodes (16): a0, a1, a2, a3, b0, b1, b2, b3, s0, s1, s2, s3, c1, c2, c3, c4
valid_energy: None
energy_gap: None

h:
```text
[1, 0, 0, 0, 1, 0, 0, 0, -1, 0, 0, 0, -2, 0, 0, 0]
```

J:
```text
[ 0  0  0  0 -1  0  0  0  1  0  0  0  2  0  0  0]
[ 0  0  0  0  0 -1  0  0  0  1  0  0 -1  2  0  0]
[ 0  0  0  0  0  0 -1  0  0  0  1  0  0 -1  2  0]
[ 0  0  0  0  0  0  0 -1  0  0  0  1  0  0 -1  2]
[-1  0  0  0  0  0  0  0  1  0  0  0  2  0  0  0]
[ 0 -1  0  0  0  0  0  0  0  1  0  0 -1  2  0  0]
[ 0  0 -1  0  0  0  0  0  0  0  1  0  0 -1  2  0]
[ 0  0  0 -1  0  0  0  0  0  0  0  1  0  0 -1  2]
[ 1  0  0  0  1  0  0  0  0  0  0  0 -2  0  0  0]
[ 0  1  0  0  0  1  0  0  0  0  0  0  1 -2  0  0]
[ 0  0  1  0  0  0  1  0  0  0  0  0  0  1 -2  0]
[ 0  0  0  1  0  0  0  1  0  0  0  0  0  0  1 -2]
[ 2 -1  0  0  2 -1  0  0 -2  1  0  0  0  2  0  0]
[ 0  2 -1  0  0  2 -1  0  0 -2  1  0  2  0  2  0]
[ 0  0  2 -1  0  0  2 -1  0  0 -2  1  0  2  0  2]
[ 0  0  0  2  0  0  0  2  0  0  0 -2  0  0  2  0]
```

## ADDER8_RIPPLE

entity: gen_adder8
source: Composed HA/FA 8-bit ripple adder, HA scale=1, FA scale=1
weight_scale: 1
field_frac_bits: 0
nodes (32): a0, a1, a2, a3, a4, a5, a6, a7, b0, b1, b2, b3, b4, b5, b6, b7, s0, s1, s2, s3, s4, s5, s6, s7, c1, c2, c3, c4, c5, c6, c7, c8
valid_energy: None
energy_gap: None

h:
```text
[1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 0, 0]
```

J:
```text
[ 0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  2  0  0  0  0  0  0  0]
[ 0  0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0  0  0  0]
[ 0  0  0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0  0  0]
[ 0  0  0  0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0  0]
[ 0  0  0  0  0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0]
[ 0  0  0  0  0  0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0]
[ 0  0  0  0  0  0  0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0]
[ 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2]
[-1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  2  0  0  0  0  0  0  0]
[ 0 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0  0  0  0]
[ 0  0 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0  0  0]
[ 0  0  0 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0  0]
[ 0  0  0  0 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0  0]
[ 0  0  0  0  0 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0  0]
[ 0  0  0  0  0  0 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2  0]
[ 0  0  0  0  0  0  0 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1  0  0  0  0  0  0 -1  2]
[ 1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0 -2  0  0  0  0  0  0  0]
[ 0  1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1 -2  0  0  0  0  0  0]
[ 0  0  1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1 -2  0  0  0  0  0]
[ 0  0  0  1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1 -2  0  0  0  0]
[ 0  0  0  0  1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1 -2  0  0  0]
[ 0  0  0  0  0  1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1 -2  0  0]
[ 0  0  0  0  0  0  1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1 -2  0]
[ 0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0  0  1 -2]
[ 2 -1  0  0  0  0  0  0  2 -1  0  0  0  0  0  0 -2  1  0  0  0  0  0  0  0  2  0  0  0  0  0  0]
[ 0  2 -1  0  0  0  0  0  0  2 -1  0  0  0  0  0  0 -2  1  0  0  0  0  0  2  0  2  0  0  0  0  0]
[ 0  0  2 -1  0  0  0  0  0  0  2 -1  0  0  0  0  0  0 -2  1  0  0  0  0  0  2  0  2  0  0  0  0]
[ 0  0  0  2 -1  0  0  0  0  0  0  2 -1  0  0  0  0  0  0 -2  1  0  0  0  0  0  2  0  2  0  0  0]
[ 0  0  0  0  2 -1  0  0  0  0  0  0  2 -1  0  0  0  0  0  0 -2  1  0  0  0  0  0  2  0  2  0  0]
[ 0  0  0  0  0  2 -1  0  0  0  0  0  0  2 -1  0  0  0  0  0  0 -2  1  0  0  0  0  0  2  0  2  0]
[ 0  0  0  0  0  0  2 -1  0  0  0  0  0  0  2 -1  0  0  0  0  0  0 -2  1  0  0  0  0  0  2  0  2]
[ 0  0  0  0  0  0  0  2  0  0  0  0  0  0  0  2  0  0  0  0  0  0  0 -2  0  0  0  0  0  0  2  0]
```

## COMB6_MIXED

entity: gen_comb6_mixed
source: Composed 6-input/4-output mixed combinational network from integer gate blocks
weight_scale: 1
field_frac_bits: 0
nodes (21): x0, x1, x2, x3, x4, x5, u0_and, u1_or, u2_nand, u3_xor, u3_aux, u4_xnor, u4_aux, v0_xor, v0_aux, v1_and, v2_nor, y1_or, y2_xnor, y2_aux, y3_nand
valid_energy: None
energy_gap: None

h:
```text
[2, 2, 0, -1, 1, 2, -1, 2, 3, 1, -2, 1, -2, 0, -2, -3, -3, 2, 2, -2, 2]
```

J:
```text
[ 0 -1 -1  0  0  0  2  0  0  1  2  0  0  0  0  0  0  0  0  0  0]
[-1  0  0  0  0 -1  2  0  0  0  0 -1  2  0  0  0  0  0  0  0  0]
[-1  0  0 -1  0  0  0  2  0  1  2  0  0  0  0  0  0  0  0  0  0]
[ 0  0 -1  0  0  0  0  2  0  0  0  0  0  0  0  0  0  0  0  0  0]
[ 0  0  0  0  0 -1  0  0 -2  0  0  0  0  0  0  0  0  0  0  0  0]
[ 0 -1  0  0 -1  0  0  0 -2  0  0 -1  2  0  0  0  0  0  0  0  0]
[ 2  2  0  0  0  0  0 -1  0  0  0  0  0  1  2  0  0  0  0  0  0]
[ 0  0  2  2  0  0 -1  0  0  0  0 -1  0  1  2  0 -2  0  0  0  0]
[ 0  0  0  0 -2 -2  0  0  0 -1  0  0  0  0  0  2  0  0  0  0  0]
[ 1  0  1  0  0  0  0  0 -1  0 -2 -1  0  0  0  2  0  0 -1  2  0]
[ 2  0  2  0  0  0  0  0  0 -2  0  0  0  0  0  0  0  0  0  0  0]
[ 0 -1  0  0  0 -1  0 -1  0 -1  0  0  2  0  0  0 -2  0 -1  2  0]
[ 0  2  0  0  0  2  0  0  0  0  0  2  0  0  0  0  0  0  0  0  0]
[ 0  0  0  0  0  0  1  1  0  0  0  0  0  0 -2  0  0  0 -1  0 -2]
[ 0  0  0  0  0  0  2  2  0  0  0  0  0 -2  0  0  0  0  0  0  0]
[ 0  0  0  0  0  0  0  0  2  2  0  0  0  0  0  0 -1  2  0  0  0]
[ 0  0  0  0  0  0  0 -2  0  0  0 -2  0  0  0 -1  0  2  0  0  0]
[ 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  2  2  0  0  0  0]
[ 0  0  0  0  0  0  0  0  0 -1  0 -1  0 -1  0  0  0  0  0  2 -2]
[ 0  0  0  0  0  0  0  0  0  2  0  2  0  0  0  0  0  0  2  0  0]
[ 0  0  0  0  0  0  0  0  0  0  0  0  0 -2  0  0  0  0 -2  0  0]
```

## BITCOUNT8

entity: gen_bitcount8
source: Exact squared bitcount constraint H=2*(sum(x)-y)^2
weight_scale: 1
field_frac_bits: 0
nodes (12): x0, x1, x2, x3, x4, x5, x6, x7, y0, y1, y2, y3
valid_energy: -71
energy_gap: 2

h:
```text
[7, 7, 7, 7, 7, 7, 7, 7, -7, -14, -28, -56]
```

J:
```text
[  0  -1  -1  -1  -1  -1  -1  -1   1   2   4   8]
[ -1   0  -1  -1  -1  -1  -1  -1   1   2   4   8]
[ -1  -1   0  -1  -1  -1  -1  -1   1   2   4   8]
[ -1  -1  -1   0  -1  -1  -1  -1   1   2   4   8]
[ -1  -1  -1  -1   0  -1  -1  -1   1   2   4   8]
[ -1  -1  -1  -1  -1   0  -1  -1   1   2   4   8]
[ -1  -1  -1  -1  -1  -1   0  -1   1   2   4   8]
[ -1  -1  -1  -1  -1  -1  -1   0   1   2   4   8]
[  1   1   1   1   1   1   1   1   0  -2  -4  -8]
[  2   2   2   2   2   2   2   2  -2   0  -8 -16]
[  4   4   4   4   4   4   4   4  -4  -8   0 -32]
[  8   8   8   8   8   8   8   8  -8 -16 -32   0]
```
