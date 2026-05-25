transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_and_onecycle_sanity]} {
    vdel -lib work_and_onecycle_sanity -all
}

set trials 1000
if {[info exists ::env(TRIALS)]} {
    set trials $::env(TRIALS)
}
set scramble_cycles 80
if {[info exists ::env(SCRAMBLE_CYCLES)]} {
    set scramble_cycles $::env(SCRAMBLE_CYCLES)
}
set prime_input_cycles 0
if {[info exists ::env(PRIME_INPUT_CYCLES)]} {
    set prime_input_cycles $::env(PRIME_INPUT_CYCLES)
}
set solve_cycles 1
if {[info exists ::env(SOLVE_CYCLES)]} {
    set solve_cycles $::env(SOLVE_CYCLES)
}
set rnd_weight 0
if {[info exists ::env(RND_WEIGHT)]} {
    set rnd_weight $::env(RND_WEIGHT)
}
set field_frac_bits 0
if {[info exists ::env(FIELD_FRAC_BITS)]} {
    set field_frac_bits $::env(FIELD_FRAC_BITS)
}
set bias_a 1
if {[info exists ::env(BIAS_A)]} {
    set bias_a $::env(BIAS_A)
}
set bias_b 1
if {[info exists ::env(BIAS_B)]} {
    set bias_b $::env(BIAS_B)
}
set bias_y -2
if {[info exists ::env(BIAS_Y)]} {
    set bias_y $::env(BIAS_Y)
}
set j_ab -1
if {[info exists ::env(J_AB)]} {
    set j_ab $::env(J_AB)
}
set j_ay 2
if {[info exists ::env(J_AY)]} {
    set j_ay $::env(J_AY)
}
set j_by 2
if {[info exists ::env(J_BY)]} {
    set j_by $::env(J_BY)
}

vlib work_and_onecycle_sanity
vmap work work_and_onecycle_sanity

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 ../tb/tb_and_onecycle_sanity.vhd

vsim \
    -gTRIALS=$trials \
    -gSCRAMBLE_CYCLES=$scramble_cycles \
    -gPRIME_INPUT_CYCLES=$prime_input_cycles \
    -gSOLVE_CYCLES=$solve_cycles \
    -gRND_WEIGHT=$rnd_weight \
    -gFIELD_FRAC_BITS=$field_frac_bits \
    -gBIAS_A=$bias_a \
    -gBIAS_B=$bias_b \
    -gBIAS_Y=$bias_y \
    -gJ_AB=$j_ab \
    -gJ_AY=$j_ay \
    -gJ_BY=$j_by \
    work.tb_and_onecycle_sanity

set case_count 4
set trial_cycles [expr {$scramble_cycles + $prime_input_cycles + $solve_cycles + 2}]
set run_ns [expr {($case_count * $trials * $trial_cycles + 1000) * 10}]
run ${run_ns} ns

quit -f
