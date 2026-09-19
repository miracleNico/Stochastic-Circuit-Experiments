if {[info exists ::env(SIM_DIR)]} {
    source [file join $::env(SIM_DIR) sim_common.do]
} else {
    source [file join [file dirname [file dirname [file dirname [info script]]]] sim_common.do]
}
transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder4_shadow1_random_exhaustive]} {
    vdel -lib work_adder4_shadow1_random_exhaustive -all
}

set generated_shadow_vhdl "[sim_repo_path {experiments/stage1/D_scheduled_auxiliary_carry_rca/hardware/generated_shadow1_adder4.vhd}]"
if {[info exists ::env(GENERATED_SHADOW_VHDL)]} {
    set generated_shadow_vhdl [sim_input_path $::env(GENERATED_SHADOW_VHDL)]
}
set block_rnd_weight 1
if {[info exists ::env(BLOCK_RND_WEIGHT)]} {
    set block_rnd_weight $::env(BLOCK_RND_WEIGHT)
}
set copy_rnd_weight 0
if {[info exists ::env(COPY_RND_WEIGHT)]} {
    set copy_rnd_weight $::env(COPY_RND_WEIGHT)
}
set scramble_rnd_weight 2
if {[info exists ::env(SCRAMBLE_RND_WEIGHT)]} {
    set scramble_rnd_weight $::env(SCRAMBLE_RND_WEIGHT)
}
set scramble_cycles 80
if {[info exists ::env(SCRAMBLE_CYCLES)]} {
    set scramble_cycles $::env(SCRAMBLE_CYCLES)
}
set block0_cycles 10
if {[info exists ::env(BLOCK0_CYCLES)]} {
    set block0_cycles $::env(BLOCK0_CYCLES)
}
set block1_cycles 16
if {[info exists ::env(BLOCK1_CYCLES)]} {
    set block1_cycles $::env(BLOCK1_CYCLES)
}
set block2_cycles 16
if {[info exists ::env(BLOCK2_CYCLES)]} {
    set block2_cycles $::env(BLOCK2_CYCLES)
}
set block3_cycles 8
if {[info exists ::env(BLOCK3_CYCLES)]} {
    set block3_cycles $::env(BLOCK3_CYCLES)
}
set copy_cycles 1
if {[info exists ::env(COPY_CYCLES)]} {
    set copy_cycles $::env(COPY_CYCLES)
}
set trials 100
if {[info exists ::env(TRIALS)]} {
    set trials $::env(TRIALS)
}
set run_inverse true
if {[info exists ::env(RUN_INVERSE)]} {
    set run_inverse $::env(RUN_INVERSE)
}
set legacy_replay_timing false
if {[info exists ::env(LEGACY_REPLAY_TIMING)]} {
    set legacy_replay_timing $::env(LEGACY_REPLAY_TIMING)
}

vlib work_adder4_shadow1_random_exhaustive
vmap work work_adder4_shadow1_random_exhaustive

vcom -2008 [sim_repo_path {src/inv_sc_pkg.vhd}]
vcom -2008 [sim_repo_path {src/lfsr32.vhd}]
vcom -2008 [sim_repo_path {src/spin_node.vhd}]
vcom -2008 $generated_shadow_vhdl
vcom -2008 [sim_repo_path {sim_scripts/stage2/A_randomized_rca_convergence/tb/tb_adder4_shadow1_randomized_exhaustive.vhd}]

vsim \
    -gBLOCK_RND_WEIGHT=$block_rnd_weight \
    -gCOPY_RND_WEIGHT=$copy_rnd_weight \
    -gSCRAMBLE_RND_WEIGHT=$scramble_rnd_weight \
    -gSCRAMBLE_CYCLES=$scramble_cycles \
    -gBLOCK0_CYCLES=$block0_cycles \
    -gBLOCK1_CYCLES=$block1_cycles \
    -gBLOCK2_CYCLES=$block2_cycles \
    -gBLOCK3_CYCLES=$block3_cycles \
    -gCOPY_CYCLES=$copy_cycles \
    -gTRIALS=$trials \
    -gRUN_INVERSE=$run_inverse \
    -gLEGACY_REPLAY_TIMING=$legacy_replay_timing \
    work.tb_adder4_shadow1_randomized_exhaustive

set case_count 512
if {$run_inverse eq "false"} {
    set case_count 256
}
set solve_cycles [expr {$block0_cycles + $block1_cycles + $block2_cycles + $block3_cycles + (3 * $copy_cycles)}]
set timing_extra 2
if {$legacy_replay_timing eq "true"} {
    set timing_extra 0
}
set trial_cycles [expr {$scramble_cycles + $solve_cycles + $timing_extra}]
set run_ns [expr {($case_count * $trials * $trial_cycles + 1000) * 10}]
run ${run_ns} ns

quit -f
