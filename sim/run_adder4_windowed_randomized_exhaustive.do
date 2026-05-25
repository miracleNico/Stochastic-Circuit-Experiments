transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder4_windowed_random_exhaustive]} {
    vdel -lib work_adder4_windowed_random_exhaustive -all
}

set generated_windowed_vhdl "../src/generated_windowed_adder4.vhd"
if {[info exists ::env(GENERATED_WINDOWED_VHDL)]} {
    set generated_windowed_vhdl $::env(GENERATED_WINDOWED_VHDL)
}
set active_rnd_weight 1
if {[info exists ::env(ACTIVE_RND_WEIGHT)]} {
    set active_rnd_weight $::env(ACTIVE_RND_WEIGHT)
}
set final_rnd_weight 1
if {[info exists ::env(FINAL_RND_WEIGHT)]} {
    set final_rnd_weight $::env(FINAL_RND_WEIGHT)
}
set scramble_rnd_weight 2
if {[info exists ::env(SCRAMBLE_RND_WEIGHT)]} {
    set scramble_rnd_weight $::env(SCRAMBLE_RND_WEIGHT)
}
set scramble_cycles 80
if {[info exists ::env(SCRAMBLE_CYCLES)]} {
    set scramble_cycles $::env(SCRAMBLE_CYCLES)
}
set wave0_cycles 40
if {[info exists ::env(WAVE0_CYCLES)]} {
    set wave0_cycles $::env(WAVE0_CYCLES)
}
set wave1_cycles 40
if {[info exists ::env(WAVE1_CYCLES)]} {
    set wave1_cycles $::env(WAVE1_CYCLES)
}
set wave2_cycles 40
if {[info exists ::env(WAVE2_CYCLES)]} {
    set wave2_cycles $::env(WAVE2_CYCLES)
}
set wave3_cycles 40
if {[info exists ::env(WAVE3_CYCLES)]} {
    set wave3_cycles $::env(WAVE3_CYCLES)
}
set final_cycles 0
if {[info exists ::env(FINAL_CYCLES)]} {
    set final_cycles $::env(FINAL_CYCLES)
}
set trials 100
if {[info exists ::env(TRIALS)]} {
    set trials $::env(TRIALS)
}

vlib work_adder4_windowed_random_exhaustive
vmap work work_adder4_windowed_random_exhaustive

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 $generated_windowed_vhdl
vcom -2008 ../tb/tb_adder4_windowed_randomized_exhaustive.vhd

vsim \
    -gACTIVE_RND_WEIGHT=$active_rnd_weight \
    -gFINAL_RND_WEIGHT=$final_rnd_weight \
    -gSCRAMBLE_RND_WEIGHT=$scramble_rnd_weight \
    -gSCRAMBLE_CYCLES=$scramble_cycles \
    -gWAVE0_CYCLES=$wave0_cycles \
    -gWAVE1_CYCLES=$wave1_cycles \
    -gWAVE2_CYCLES=$wave2_cycles \
    -gWAVE3_CYCLES=$wave3_cycles \
    -gFINAL_CYCLES=$final_cycles \
    -gTRIALS=$trials \
    work.tb_adder4_windowed_randomized_exhaustive

set case_count 512
set solve_cycles [expr {$wave0_cycles + $wave1_cycles + $wave2_cycles + $wave3_cycles + $final_cycles}]
set trial_cycles [expr {$scramble_cycles + $solve_cycles}]
set run_ns [expr {($case_count * $trials * $trial_cycles + 1000) * 10}]
run ${run_ns} ns

quit -f
