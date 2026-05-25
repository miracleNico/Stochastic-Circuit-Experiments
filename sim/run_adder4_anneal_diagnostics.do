transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder4_anneal_diag]} {
    vdel -lib work_adder4_anneal_diag -all
}

set hot_rnd_weight 2
if {[info exists ::env(HOT_RND_WEIGHT)]} {
    set hot_rnd_weight $::env(HOT_RND_WEIGHT)
}
set cold_rnd_weight 1
if {[info exists ::env(COLD_RND_WEIGHT)]} {
    set cold_rnd_weight $::env(COLD_RND_WEIGHT)
}
set wave_cycles 1000
if {[info exists ::env(WAVE_CYCLES)]} {
    set wave_cycles $::env(WAVE_CYCLES)
}
set final_cycles 1000
if {[info exists ::env(FINAL_CYCLES)]} {
    set final_cycles $::env(FINAL_CYCLES)
}
set count_cycles 1000
if {[info exists ::env(COUNT_CYCLES)]} {
    set count_cycles $::env(COUNT_CYCLES)
}
set reverse_cool false
if {[info exists ::env(REVERSE_COOL)]} {
    set reverse_cool $::env(REVERSE_COOL)
}

vlib work_adder4_anneal_diag
vmap work work_adder4_anneal_diag

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 ../src/generated_annealed_adder4.vhd
vcom -2008 ../tb/tb_adder4_anneal_diagnostics.vhd

vsim \
    -gHOT_RND_WEIGHT=$hot_rnd_weight \
    -gCOLD_RND_WEIGHT=$cold_rnd_weight \
    -gWAVE_CYCLES=$wave_cycles \
    -gFINAL_CYCLES=$final_cycles \
    -gCOUNT_CYCLES=$count_cycles \
    -gREVERSE_COOL=$reverse_cool \
    work.tb_adder4_anneal_diagnostics

set case_count 6
set settle_cycles [expr {(4 * $wave_cycles) + $final_cycles}]
set run_ns [expr {($case_count * (8 + $settle_cycles + $count_cycles) + 200) * 10}]
run ${run_ns} ns

quit -f
