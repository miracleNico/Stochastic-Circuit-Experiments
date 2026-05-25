transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder4_windowed_diag]} {
    vdel -lib work_adder4_windowed_diag -all
}

set active_rnd_weight 1
if {[info exists ::env(ACTIVE_RND_WEIGHT)]} {
    set active_rnd_weight $::env(ACTIVE_RND_WEIGHT)
}
set final_rnd_weight 1
if {[info exists ::env(FINAL_RND_WEIGHT)]} {
    set final_rnd_weight $::env(FINAL_RND_WEIGHT)
}
set wave0_cycles 192
if {[info exists ::env(WAVE0_CYCLES)]} {
    set wave0_cycles $::env(WAVE0_CYCLES)
}
set wave1_cycles 192
if {[info exists ::env(WAVE1_CYCLES)]} {
    set wave1_cycles $::env(WAVE1_CYCLES)
}
set wave2_cycles 192
if {[info exists ::env(WAVE2_CYCLES)]} {
    set wave2_cycles $::env(WAVE2_CYCLES)
}
set wave3_cycles 192
if {[info exists ::env(WAVE3_CYCLES)]} {
    set wave3_cycles $::env(WAVE3_CYCLES)
}
set final_cycles 0
if {[info exists ::env(FINAL_CYCLES)]} {
    set final_cycles $::env(FINAL_CYCLES)
}
set count_cycles 100
if {[info exists ::env(COUNT_CYCLES)]} {
    set count_cycles $::env(COUNT_CYCLES)
}

vlib work_adder4_windowed_diag
vmap work work_adder4_windowed_diag

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 ../src/generated_windowed_adder4.vhd
vcom -2008 ../tb/tb_adder4_windowed_diagnostics.vhd

vsim \
    -gACTIVE_RND_WEIGHT=$active_rnd_weight \
    -gFINAL_RND_WEIGHT=$final_rnd_weight \
    -gWAVE0_CYCLES=$wave0_cycles \
    -gWAVE1_CYCLES=$wave1_cycles \
    -gWAVE2_CYCLES=$wave2_cycles \
    -gWAVE3_CYCLES=$wave3_cycles \
    -gFINAL_CYCLES=$final_cycles \
    -gCOUNT_CYCLES=$count_cycles \
    work.tb_adder4_windowed_diagnostics

set case_count 16
set settle_cycles [expr {$wave0_cycles + $wave1_cycles + $wave2_cycles + $wave3_cycles + $final_cycles}]
set run_ns [expr {($case_count * (8 + $settle_cycles + $count_cycles) + 200) * 10}]
run ${run_ns} ns

quit -f
