# Time-Dependent RCA Experiments

Date: 2026-05-24

## 1. Problem Encountered

The original goal was to reproduce the invertible-logic paper and then improve convergence for composed arithmetic circuits. Single HA/FA blocks behaved well, but the 4-bit ripple-carry adder did not converge reliably when the same blocks were directly coupled.

The main failure was not that the local HA/FA Hamiltonians were invalid. The local integer gaps are already equalized:

```text
HA_XOR valid_energy=-4, invalid_min=-2, gap=2
FA     valid_energy=-4, invalid_min=-2, gap=2
```

The problem appears when blocks are composed into a pseudo-time-dependent circuit. Stage `k+1` should solve only after the carry from stage `k` has collapsed. With direct interblock coupling, later stages can collapse around an incorrect guessed carry. Once the local field is large, the `tanh` update saturates:

```text
F_i = h_i + sum_j J_ij s_j + eta_i
P(s_i=+1) = (1 + tanh(F_i)) / 2
P(flip against field) approximately exp(-2 |F_i|)
```

So larger intrablock gap can make a local gate stronger but can also make a wrong downstream branch harder to escape.

## 2. Ideas Tested

```text
idea 1: equalize intrablock energy gap
  Goal: make all composed blocks have similar valid/invalid gaps.
  Result: positive for pure combinational logic, not sufficient for RCA timing logic.

idea 2: larger dynamic range / quantized weights
  Goal: use FP8/Q8-style coefficients to improve gate convergence.
  Result: not useful alone for directly coupled adders; useful only after ideas 3+4 are present.

idea 3: sequential annealing window
  Goal: activate/cool RCA stages in carry order.
  Result: semi-positive. It helps, but direct coupling still leaves hard failing cases.

idea 4: shadow interblock node
  Goal: separate carry production from carry consumption.
  Result: positive. A one-node shadow latch gives a directional handoff.
```

The final useful topology is:

```text
c0 -> q1 -> FA1 cin
c1 -> q2 -> FA2 cin
c2 -> q3 -> FA3 cin
```

Each `q` node is hot only during its copy phase, then frozen while the downstream FA runs. This is not a static symmetric Hamiltonian; it is a pseudo-time-dependent directed update schedule.

## 3. Baseline vs Idea 1

### Combinational Logic

The pure combinational benchmark was `COMB6_MIXED`, a 6-input, 4-output network built from AND/OR/NAND/NOR/XOR/XNOR-style blocks. It has no long carry wavefront.

Integer baseline block gaps were uneven:

```text
AND/OR/NAND/NOR gap = 4
XOR/XNOR gap        = 2
```

Idea 1 equalized the intrablock gap to physical `4.0` using E3M4-style encoded coefficients. Results over all 64 input vectors, `COUNT_CYCLES=1000`:

```text
Integer baseline, RND=1, SETTLE=1000:
  top_matches=21/64, zero_hit_cases=39, avg_hits=313.9/1000

Integer baseline, RND=1, SETTLE=20000:
  top_matches=50/64, zero_hit_cases=14, avg_hits=741.9/1000

E3M4 equal-gap, RND=16, SETTLE=1000:
  top_matches=57/64, zero_hit_cases=2, avg_hits=855.2/1000

E3M4 equal-gap, RND=16, SETTLE=20000:
  top_matches=64/64, zero_hit_cases=0, min_hits=997/1000, avg_hits=999.1/1000
```

Conclusion: idea 1 is strongly positive for pure combinational logic.

### Adders

For the RCA, equalizing intrablock gap alone does not solve the problem, because the integer HA/FA gaps are already equalized at `2`. The failure is temporal: downstream FA blocks depend on upstream carry values that may not have settled yet.

Static integer 4-bit RCA quick baseline over 16 selected vectors, `COUNT_CYCLES=100`:

```text
settle=128: avg=22.9, min=0
settle=500: avg=78.0, min=0
```

Longer settling improves some cases, but zero-hit cases remain. This is the first sign that RCA convergence is not just a local gap problem.

## 4. Idea 2 Alone

Idea 2 tried FP8/Q8/fixed-point weight redesigns to exploit larger dynamic range and better gate gaps. The direct interblock versions did not solve the RCA.

Representative fixed-Q8 split-copy branch:

```text
format: fixed-Q8
adder: 4-bit split-carry RCA
goal: maximize HA/FA gate gap, reduce interblock link gap
result: underperformed integer/shadow schedules; zero-hit cases remained
```

Why it failed:

```text
larger intrablock gap -> stronger local collapse
direct interblock coupling -> downstream stage can collapse before upstream carry is correct
tanh saturation -> wrong local branch becomes difficult to escape
```

So idea 2 alone is negative for RCA-style interblock logic. It can make individual blocks cleaner, but it does not provide the missing direction or timing.

## 5. Baseline vs Ideas 3+4

Idea 3 added stage timing. Idea 4 added a shadow carry latch.

The best integer one-node shadow latch uses:

```text
topology:
  c0 -> q1 -> FA1 cin
  c1 -> q2 -> FA2 cin
  c2 -> q3 -> FA3 cin

schedule:
  B0=10
  q1 copy=1
  B1=16
  q2 copy=1
  B2=16
  q3 copy=1
  B3=8

block_rnd=1
copy_rnd=0
pre-sampling cycles = 10 + 1 + 16 + 1 + 16 + 1 + 8 = 53
```

Exhaustive result over all 256 input pairs, `COUNT_CYCLES=1000`:

```text
perfect=256/256
failed=0
total_hits=256000/256000
min_hits=1000
q1/c0 min match=1000/1000
q2/c1 min match=1000/1000
q3/c2 min match=1000/1000
```

Comparison:

```text
static integer RCA, 16-vector quick baseline:
  settle=500, avg=78.0/100, min=0

idea 3 only, asymmetric integer window:
  pre=212, avg=93.8/100, min=0, perfect=15/16

idea 3+4, integer one-node shadow latch:
  pre=53, exhaustive 256/256 perfect at 1000/1000 samples
```

Interpretation: idea 3 creates the carry-order schedule; idea 4 prevents downstream blocks from tugging backward on the producer carry. Together they convert the RCA from a frustrated directly coupled network into a staged carry handoff.

## 6. Baseline vs Ideas 2+3+4

After ideas 3+4 worked, idea 2 was revisited with signed Q3.4 fixed-point coefficients:

```text
format: 1s3d4f / signed Q3.4
physical value = encoded / 16
coefficient cap: |physical coefficient| <= 7
```

The MILP optimizer maximized valid/invalid gate gap. It selected scaled HA/FA coefficients:

```text
HA h encoded: [56, 56, -56, -112]
HA h physical: [3.5, 3.5, -3.5, -7.0]

FA h encoded: [0, 0, 0, 0, 0]

main physical J levels: ±3.5 and ±7.0
gate gap: encoded 112 = physical 7.0
shadow copy weight: encoded 64 = physical 4.0
```

The first Q3.4 test used the requested shadow hot time of `2` cycles but kept encoded block noise at `16`:

```text
B0=10, B1=16, B2=16, B3=8
copy_cycles=2
block_rnd=16

exhaustive result:
perfect=128/256
failed=128/256
failure pattern: top_sum = expected_sum + 1
shadow latch matches: 1000/1000
```

This shows the failure was not carry-copy loss. The stronger Q3.4 blocks plus noise could lock the first HA into a wrong local state.

After retuning, the successful Q3.4 schedule was:

```text
B0=10
q1 copy=2
B1=8
q2 copy=2
B2=16
q3 copy=2
B3=6

block_rnd=0
copy_rnd=0
pre-sampling cycles = 10 + 2 + 8 + 2 + 16 + 2 + 6 = 46
```

Exhaustive result over all 256 input pairs, `COUNT_CYCLES=1000`:

```text
perfect=256/256
failed=0
total_hits=256000/256000
min_hits=1000
q1/c0 min match=1000/1000
q2/c1 min match=1000/1000
q3/c2 min match=1000/1000
```

Comparison of the best deterministic schedules:

```text
static integer RCA:
  settle=500, 16-vector avg=78.0/100, min=0

idea 3+4 integer shadow latch:
  pre=53, exhaustive 256/256 perfect

idea 2+3+4 Q3.4 shadow latch:
  pre=46, exhaustive 256/256 perfect
```

Conclusion: idea 2 is negative when used alone on direct interblock logic, but positive after the timing and shadow-latch problems are solved. In the final run it reduces the deterministic pre-sampling budget from `53` to `46` cycles.

### Small Added-Noise Check

The deterministic Q3.4 result above uses no additive random-field noise. A quick follow-up tested whether a small amount of block noise can be restored without damaging the useful forward mode. Noise values are encoded in Q3.4 units, so:

```text
block_rnd=4  -> physical noise amplitude 0.25
block_rnd=8  -> physical noise amplitude 0.50
copy_rnd=0
COUNT_CYCLES=100
```

Forward exhaustive quick check:

```text
block_rnd=4 / 0.25:
  perfect=256/256
  failed=0
  min_hits=100/100

block_rnd=8 / 0.50:
  perfect=128/256
  failed=128
  min_hits=0/100
  failure pattern: top_sum = expected_sum + 1
```

Constrained inverse quick check with the original forward-order schedule:

```text
block_rnd=4 / 0.25:
  B+SUM -> A perfect=256/256

block_rnd=8 / 0.50:
  B+SUM -> A perfect=176/256
```

Current recommended noisy Q3.4 operating point is therefore `block_rnd=4`, `copy_rnd=0`. It is not yet an exhaustive 1000-sample replacement for the no-noise proof, but it is the largest tested noise setting that preserved both forward and constrained inverse behavior in the quick check.

## 7. Inverse Behavior Check

The first inverse attempt revealed an implementation issue: the shadow generator treated `a*` and `b*` nodes as forward-only clamp pins, so an unclamped input did not update. This has been fixed by assigning unclamped `a_i` and `b_i` to their corresponding block window. Forward exhaustive behavior remained unchanged after the fix.

Two inverse modes were tested on the Q3.4 shadow latch:

```text
constrained inverse:
  clamp B and SUM, infer A

underconstrained inverse:
  clamp only SUM, infer any A,B pair with A+B=SUM
```

For the final no-added-noise Q3.4 schedule:

```text
B0=10, B1=8, B2=16, B3=6
copy_cycles=2
block_rnd=0
copy_rnd=0
COUNT_CYCLES=1000

constrained inverse B+SUM:
  perfect=256/256
  failed=0
  total_hits=256000/256000
  min_hits=1000

SUM-only inverse:
  perfect=24/31
  failed=7
  total_hits=24000/31000
  min_hits=0
```

Adding block noise back at physical amplitude `1.0` hurt inverse behavior under the same schedule:

```text
block_rnd=16 encoded = 1.0 physical

constrained inverse B+SUM:
  perfect=176/256
  failed=80
  total_hits=176000/256000
  min_hits=0

SUM-only inverse:
  perfect=18/31
  failed=13
  total_hits=18000/31000
  min_hits=0
```

Conclusion: removing additive block noise does not damage the constrained inverse test; it improves it for this Q3.4 schedule. However, the SUM-only test is still not fully invertible. The shadow latch is directional and staged, so full underconstrained inverse use may need a separate reverse schedule or a bidirectional shadow mechanism.

## 8. 8-bit Synthesized RCA Extension

Ideas 2+3+4 were then applied to the 8-bit HA/FA-composed synthesized RCA. The generated topology is the direct 8-bit extension of the one-node carry shadow:

```text
c0 -> q1 -> FA1 cin
c1 -> q2 -> FA2 cin
c2 -> q3 -> FA3 cin
c3 -> q4 -> FA4 cin
c4 -> q5 -> FA5 cin
c5 -> q6 -> FA6 cin
c6 -> q7 -> FA7 cin
```

The 8-bit generated Q3.4 design has 39 stochastic nodes:

```text
8 A input nodes
8 B input nodes
8 SUM nodes
8 carry-out nodes c0..c7
7 shadow carry nodes q1..q7
```

The old synthesized integer `gen_adder8` diagnostic still shows the convergence problem:

```text
RND_WEIGHT=1, settle=500, COUNT=1000

15+1:
  expected_sum=16
  hits=0/1000
  top_sum=8 count=851

170+85:
  expected_sum=255
  hits=0/1000
  top_sum=256 count=864
```

The first 8-bit idea 2+3+4 quick test used the Q3.4 HA/FA weights from the 4-bit run, `copy_weight=4.0`, `block_rnd=4` physical `0.25`, and 32 selected vectors stressing carry chains and edge cases. A direct short extension of the 4-bit timing was not enough:

```text
blocks=10,8,16,6,8,8,16,6
copy=2
block_rnd=4

perfect=7/32
failed=25
shadow_min q1..q7=100/100
```

The perfect shadow-copy result means the carry latches transferred correctly; the remaining error was insufficient per-stage relaxation for the larger 8-bit network and its new scheduler seed.

Successful noisy quick schedule:

```text
blocks=40,40,40,40,40,40,40,40
copy=2
block_rnd=4  -> physical 0.25
copy_rnd=0
COUNT_CYCLES=100

perfect=32/32
failed=0
total_hits=3200/3200
min_hits=100/100
shadow_min q1..q7=100/100
pre-sampling cycles = 8*40 + 7*2 = 334
```

Boundary checks:

```text
block_rnd=4, blocks=39 all, copy=2:
  perfect=15/32, failed=17

block_rnd=4, blocks=40 all, copy=1:
  perfect=15/32, failed=17

block_rnd=0, blocks=32 all, copy=2:
  perfect=32/32, failed=0
```

Conclusion: idea 2+3+4 migrates positively to the 8-bit synthesized RCA in the quick check, but the 8-bit noisy schedule needs a much longer per-stage relaxation window than the 4-bit case. The small `0.25` noise is tolerable only after each stage is given about one full 39-node scheduler period.

## Remaining Risk

All successful RCA results above use deterministic LFSR seeds. The next robustness check should repeat the integer and Q3.4 shadow-latch schedules across randomized seed sets. The current conclusion is therefore:

```text
idea 1: positive for pure combinational logic, not sufficient for RCA
idea 2: negative alone for RCA, positive when combined with ideas 3+4
idea 3: semi-positive alone
idea 4: positive and essential for RCA timing logic
```

## Artifacts

```text
reports/comb6_equal_gap_report.md
reports/comb6_e3m4_equal_gap.json
reports/optimized_q34_shadow1_blocks.json

scripts/generate_shadow1_adder4.py
scripts/generate_shadow1_q34_adder4.py
scripts/generate_shadow1_q34_adder8.py

src/generated_shadow1_adder4.vhd
src/generated_shadow1_q34_adder4.vhd
src/generated_shadow1_q34_adder8.vhd
src/spin_node.vhd

tb/tb_adder4_shadow1_diagnostics.vhd
tb/tb_adder4_shadow1_exhaustive.vhd
tb/tb_adder4_shadow1_inverse.vhd
tb/tb_adder8_shadow1_diagnostics.vhd

sim/run_adder4_shadow1_exhaustive.ps1
sim/run_adder4_shadow1_q34_exhaustive.ps1
sim/run_adder4_shadow1_q34_inverse.ps1
sim/run_adder8_shadow1_q34_diagnostics.ps1
```
