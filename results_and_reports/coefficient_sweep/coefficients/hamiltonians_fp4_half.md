# Hamiltonian coefficients

All coefficients use bipolar spins with logic 0 -> -1 and logic 1 -> +1.

Adder and bitcount note:

The paper uses bitcount primarily to reduce multiplier node count by removing vertical internal adder connections.
For adders, the direct n-bit adder row with 3n + 1 nodes is already the minimum-node direct Hamiltonian form.
This project intentionally emits an HA/FA-composed 8-bit ripple adder for clarity and block-scaling experiments,
so `ADDER8_RIPPLE` uses 32 nodes rather than the direct 25-node theoretical form.

## AND

entity: gen_and_gate
source: 3-node LP block, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (3): A, B, Y
valid_energy: -24
energy_gap: 32

h:
```text
[8, 8, -16]
```

J:
```text
[ 0 -8 16]
[-8  0 16]
[16 16  0]
```

## OR

entity: gen_or_gate
source: 3-node LP block, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (3): A, B, Y
valid_energy: -24
energy_gap: 32

h:
```text
[-8, -8, 16]
```

J:
```text
[ 0 -8 16]
[-8  0 16]
[16 16  0]
```

## NAND

entity: gen_nand_gate
source: 3-node LP block, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (3): A, B, Y
valid_energy: -24
energy_gap: 32

h:
```text
[8, 8, 16]
```

J:
```text
[  0  -8 -16]
[ -8   0 -16]
[-16 -16   0]
```

## NOR

entity: gen_nor_gate
source: 3-node LP block, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (3): A, B, Y
valid_energy: -24
energy_gap: 32

h:
```text
[-8, -8, -16]
```

J:
```text
[  0  -8 -16]
[ -8   0 -16]
[-16 -16   0]
```

## HA_XOR

entity: gen_xor_gate
source: 4-node LP HA/XOR block, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (4): A, B, S, C
valid_energy: -32
energy_gap: 16

h:
```text
[8, 8, -8, -16]
```

J:
```text
[  0  -8   8  16]
[ -8   0   8  16]
[  8   8   0 -16]
[ 16  16 -16   0]
```

## XNOR

entity: gen_xnor_gate
source: 4-node LP XNOR block, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (4): A, B, Y, C
valid_energy: -32
energy_gap: 16

h:
```text
[8, 8, 8, -16]
```

J:
```text
[ 0 -8 -8 16]
[-8  0 -8 16]
[-8 -8  0 16]
[16 16 16  0]
```

## FA

entity: gen_fa_gate
source: 5-node LP FA block, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (5): A, B, CIN, S, COUT
valid_energy: -32
energy_gap: 16

h:
```text
[0, 0, 0, 0, 0]
```

J:
```text
[  0  -8  -8   8  16]
[ -8   0  -8   8  16]
[ -8  -8   0   8  16]
[  8   8   8   0 -16]
[ 16  16  16 -16   0]
```

## ADDER8_RIPPLE

entity: gen_adder8
source: Composed HA/FA ripple adder, HA scale=1, FA scale=1, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (32): a0, a1, a2, a3, a4, a5, a6, a7, b0, b1, b2, b3, b4, b5, b6, b7, s0, s1, s2, s3, s4, s5, s6, s7, c1, c2, c3, c4, c5, c6, c7, c8
valid_energy: None
energy_gap: None

h:
```text
[8, 0, 0, 0, 0, 0, 0, 0, 8, 0, 0, 0, 0, 0, 0, 0, -8, 0, 0, 0, 0, 0, 0, 0, -16, 0, 0, 0, 0, 0, 0, 0]
```

J:
```text
[  0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0  16   0   0   0   0   0   0   0]
[  0   0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0   0   0   0]
[  0   0   0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0   0   0]
[  0   0   0   0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0   0]
[  0   0   0   0   0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0]
[  0   0   0   0   0   0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0]
[  0   0   0   0   0   0   0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0]
[  0   0   0   0   0   0   0   0   0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16]
[ -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0  16   0   0   0   0   0   0   0]
[  0  -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0   0   0   0]
[  0   0  -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0   0   0]
[  0   0   0  -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0   0]
[  0   0   0   0  -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0   0]
[  0   0   0   0   0  -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0   0]
[  0   0   0   0   0   0  -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16   0]
[  0   0   0   0   0   0   0  -8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8   0   0   0   0   0   0  -8  16]
[  8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0 -16   0   0   0   0   0   0   0]
[  0   8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8 -16   0   0   0   0   0   0]
[  0   0   8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8 -16   0   0   0   0   0]
[  0   0   0   8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8 -16   0   0   0   0]
[  0   0   0   0   8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8 -16   0   0   0]
[  0   0   0   0   0   8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8 -16   0   0]
[  0   0   0   0   0   0   8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8 -16   0]
[  0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   8   0   0   0   0   0   0   0   0   0   0   0   0   0   0   8 -16]
[ 16  -8   0   0   0   0   0   0  16  -8   0   0   0   0   0   0 -16   8   0   0   0   0   0   0   0  16   0   0   0   0   0   0]
[  0  16  -8   0   0   0   0   0   0  16  -8   0   0   0   0   0   0 -16   8   0   0   0   0   0  16   0  16   0   0   0   0   0]
[  0   0  16  -8   0   0   0   0   0   0  16  -8   0   0   0   0   0   0 -16   8   0   0   0   0   0  16   0  16   0   0   0   0]
[  0   0   0  16  -8   0   0   0   0   0   0  16  -8   0   0   0   0   0   0 -16   8   0   0   0   0   0  16   0  16   0   0   0]
[  0   0   0   0  16  -8   0   0   0   0   0   0  16  -8   0   0   0   0   0   0 -16   8   0   0   0   0   0  16   0  16   0   0]
[  0   0   0   0   0  16  -8   0   0   0   0   0   0  16  -8   0   0   0   0   0   0 -16   8   0   0   0   0   0  16   0  16   0]
[  0   0   0   0   0   0  16  -8   0   0   0   0   0   0  16  -8   0   0   0   0   0   0 -16   8   0   0   0   0   0  16   0  16]
[  0   0   0   0   0   0   0  16   0   0   0   0   0   0   0  16   0   0   0   0   0   0   0 -16   0   0   0   0   0   0  16   0]
```

## BITCOUNT8

entity: gen_bitcount8
source: Exact squared bitcount constraint H=2*(sum(x)-y)^2, weight scale=1/2, frac_bits=4
weight_scale: 1/2
field_frac_bits: 4
nodes (12): x0, x1, x2, x3, x4, x5, x6, x7, y0, y1, y2, y3
valid_energy: -568
energy_gap: 16

h:
```text
[56, 56, 56, 56, 56, 56, 56, 56, -56, -112, -224, -448]
```

J:
```text
[   0   -8   -8   -8   -8   -8   -8   -8    8   16   32   64]
[  -8    0   -8   -8   -8   -8   -8   -8    8   16   32   64]
[  -8   -8    0   -8   -8   -8   -8   -8    8   16   32   64]
[  -8   -8   -8    0   -8   -8   -8   -8    8   16   32   64]
[  -8   -8   -8   -8    0   -8   -8   -8    8   16   32   64]
[  -8   -8   -8   -8   -8    0   -8   -8    8   16   32   64]
[  -8   -8   -8   -8   -8   -8    0   -8    8   16   32   64]
[  -8   -8   -8   -8   -8   -8   -8    0    8   16   32   64]
[   8    8    8    8    8    8    8    8    0  -16  -32  -64]
[  16   16   16   16   16   16   16   16  -16    0  -64 -128]
[  32   32   32   32   32   32   32   32  -32  -64    0 -256]
[  64   64   64   64   64   64   64   64  -64 -128 -256    0]
```
