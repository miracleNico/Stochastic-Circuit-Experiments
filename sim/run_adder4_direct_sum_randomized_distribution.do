transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder4_direct_sum_random]} {
    vdel -lib work_adder4_direct_sum_random -all
}

set generated_networks "../src/generated_networks.vhd"
if {[info exists ::env(GENERATED_NETWORKS_VHDL)]} {
    set generated_networks $::env(GENERATED_NETWORKS_VHDL)
}
set adder_rnd_weight 1
if {[info exists ::env(ADDER_RND_WEIGHT)]} {
    set adder_rnd_weight $::env(ADDER_RND_WEIGHT)
}
set scramble_cycles 80
if {[info exists ::env(SCRAMBLE_CYCLES)]} {
    set scramble_cycles $::env(SCRAMBLE_CYCLES)
}
set settle_cycles 500
if {[info exists ::env(SETTLE_CYCLES)]} {
    set settle_cycles $::env(SETTLE_CYCLES)
}
set trials 1000
if {[info exists ::env(TRIALS)]} {
    set trials $::env(TRIALS)
}

vlib work_adder4_direct_sum_random
vmap work work_adder4_direct_sum_random

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 $generated_networks
vcom -2008 ../tb/tb_adder4_direct_sum_randomized_distribution.vhd

vsim \
    -gADDER_RND_WEIGHT=$adder_rnd_weight \
    -gSCRAMBLE_CYCLES=$scramble_cycles \
    -gSETTLE_CYCLES=$settle_cycles \
    -gTRIALS=$trials \
    work.tb_adder4_direct_sum_randomized_distribution

set sum_cases 31
set trial_cycles [expr {$scramble_cycles + $settle_cycles + 1}]
set run_ns [expr {($sum_cases * $trials * $trial_cycles + 1000) * 10}]
run ${run_ns} ns

quit -f
