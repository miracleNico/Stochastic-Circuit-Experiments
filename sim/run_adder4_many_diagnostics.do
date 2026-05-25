transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder4_many_diag]} {
    vdel -lib work_adder4_many_diag -all
}

set generated_networks "../src/generated_networks.vhd"
if {[info exists ::env(GENERATED_NETWORKS_VHDL)]} {
    set generated_networks $::env(GENERATED_NETWORKS_VHDL)
}
set adder_rnd_weight 1
if {[info exists ::env(ADDER_RND_WEIGHT)]} {
    set adder_rnd_weight $::env(ADDER_RND_WEIGHT)
}
set settle_cycles 128
if {[info exists ::env(SETTLE_CYCLES)]} {
    set settle_cycles $::env(SETTLE_CYCLES)
}
set count_cycles 100
if {[info exists ::env(COUNT_CYCLES)]} {
    set count_cycles $::env(COUNT_CYCLES)
}

vlib work_adder4_many_diag
vmap work work_adder4_many_diag

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 $generated_networks
vcom -2008 ../tb/tb_adder4_many_diagnostics.vhd

vsim \
    -gADDER_RND_WEIGHT=$adder_rnd_weight \
    -gSETTLE_CYCLES=$settle_cycles \
    -gCOUNT_CYCLES=$count_cycles \
    work.tb_adder4_many_diagnostics

set case_count 16
set run_ns [expr {($case_count * (8 + $settle_cycles + $count_cycles) + 200) * 10}]
run ${run_ns} ns

quit -f
