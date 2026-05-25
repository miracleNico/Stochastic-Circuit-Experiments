transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder8_shadow1_q34_diag]} {
    vdel -lib work_adder8_shadow1_q34_diag -all
}

set block_rnd_weight 4
if {[info exists ::env(BLOCK_RND_WEIGHT)]} {
    set block_rnd_weight $::env(BLOCK_RND_WEIGHT)
}
set copy_rnd_weight 0
if {[info exists ::env(COPY_RND_WEIGHT)]} {
    set copy_rnd_weight $::env(COPY_RND_WEIGHT)
}
set block0_cycles 10
if {[info exists ::env(BLOCK0_CYCLES)]} {
    set block0_cycles $::env(BLOCK0_CYCLES)
}
set block1_cycles 8
if {[info exists ::env(BLOCK1_CYCLES)]} {
    set block1_cycles $::env(BLOCK1_CYCLES)
}
set block2_cycles 16
if {[info exists ::env(BLOCK2_CYCLES)]} {
    set block2_cycles $::env(BLOCK2_CYCLES)
}
set block3_cycles 6
if {[info exists ::env(BLOCK3_CYCLES)]} {
    set block3_cycles $::env(BLOCK3_CYCLES)
}
set block4_cycles 8
if {[info exists ::env(BLOCK4_CYCLES)]} {
    set block4_cycles $::env(BLOCK4_CYCLES)
}
set block5_cycles 8
if {[info exists ::env(BLOCK5_CYCLES)]} {
    set block5_cycles $::env(BLOCK5_CYCLES)
}
set block6_cycles 16
if {[info exists ::env(BLOCK6_CYCLES)]} {
    set block6_cycles $::env(BLOCK6_CYCLES)
}
set block7_cycles 6
if {[info exists ::env(BLOCK7_CYCLES)]} {
    set block7_cycles $::env(BLOCK7_CYCLES)
}
set copy_cycles 2
if {[info exists ::env(COPY_CYCLES)]} {
    set copy_cycles $::env(COPY_CYCLES)
}
set count_cycles 100
if {[info exists ::env(COUNT_CYCLES)]} {
    set count_cycles $::env(COUNT_CYCLES)
}

vlib work_adder8_shadow1_q34_diag
vmap work work_adder8_shadow1_q34_diag

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 ../src/generated_shadow1_q34_adder8.vhd
vcom -2008 ../tb/tb_adder8_shadow1_diagnostics.vhd

vsim \
    -gBLOCK_RND_WEIGHT=$block_rnd_weight \
    -gCOPY_RND_WEIGHT=$copy_rnd_weight \
    -gBLOCK0_CYCLES=$block0_cycles \
    -gBLOCK1_CYCLES=$block1_cycles \
    -gBLOCK2_CYCLES=$block2_cycles \
    -gBLOCK3_CYCLES=$block3_cycles \
    -gBLOCK4_CYCLES=$block4_cycles \
    -gBLOCK5_CYCLES=$block5_cycles \
    -gBLOCK6_CYCLES=$block6_cycles \
    -gBLOCK7_CYCLES=$block7_cycles \
    -gCOPY_CYCLES=$copy_cycles \
    -gCOUNT_CYCLES=$count_cycles \
    work.tb_adder8_shadow1_diagnostics

set case_count 32
set settle_cycles [expr {$block0_cycles + $block1_cycles + $block2_cycles + $block3_cycles + $block4_cycles + $block5_cycles + $block6_cycles + $block7_cycles + (7 * $copy_cycles)}]
set run_ns [expr {($case_count * (8 + $settle_cycles + $count_cycles) + 200) * 10}]
run ${run_ns} ns

quit -f
