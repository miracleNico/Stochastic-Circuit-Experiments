transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_comb6_diag]} {
    vdel -lib work_comb6_diag -all
}

set generated_networks "../src/generated_networks.vhd"
if {[info exists ::env(GENERATED_NETWORKS_VHDL)]} {
    set generated_networks $::env(GENERATED_NETWORKS_VHDL)
}
set comb_rnd_weight 1
if {[info exists ::env(COMB_RND_WEIGHT)]} {
    set comb_rnd_weight $::env(COMB_RND_WEIGHT)
}
set settle_cycles 1000
if {[info exists ::env(COMB_SETTLE_CYCLES)]} {
    set settle_cycles $::env(COMB_SETTLE_CYCLES)
}
set count_cycles 1000
if {[info exists ::env(COMB_COUNT_CYCLES)]} {
    set count_cycles $::env(COMB_COUNT_CYCLES)
}

vlib work_comb6_diag
vmap work work_comb6_diag

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 $generated_networks
vcom -2008 ../tb/tb_comb6_diagnostics.vhd

vsim -gCOMB_RND_WEIGHT=$comb_rnd_weight -gSETTLE_CYCLES=$settle_cycles -gCOUNT_CYCLES=$count_cycles work.tb_comb6_diagnostics

set case_count 64
set run_ns [expr {($case_count * (8 + $settle_cycles + $count_cycles) + 200) * 10}]
run ${run_ns} ns

quit -f
