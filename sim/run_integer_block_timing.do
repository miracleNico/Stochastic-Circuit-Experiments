transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_integer_block_timing]} {
    vdel -lib work_integer_block_timing -all
}

set generated_networks "../src/generated_networks.vhd"
if {[info exists ::env(GENERATED_NETWORKS_VHDL)]} {
    set generated_networks $::env(GENERATED_NETWORKS_VHDL)
}
set rnd_weight 1
if {[info exists ::env(RND_WEIGHT)]} {
    set rnd_weight $::env(RND_WEIGHT)
}
set settle_cycles 20
if {[info exists ::env(SETTLE_CYCLES)]} {
    set settle_cycles $::env(SETTLE_CYCLES)
}
set count_cycles 100
if {[info exists ::env(COUNT_CYCLES)]} {
    set count_cycles $::env(COUNT_CYCLES)
}

vlib work_integer_block_timing
vmap work work_integer_block_timing

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 $generated_networks
vcom -2008 ../tb/tb_integer_block_timing.vhd

vsim \
    -gRND_WEIGHT=$rnd_weight \
    -gSETTLE_CYCLES=$settle_cycles \
    -gCOUNT_CYCLES=$count_cycles \
    work.tb_integer_block_timing

set case_count 12
set run_ns [expr {($case_count * (8 + $settle_cycles + $count_cycles) + 200) * 10}]
run ${run_ns} ns

quit -f
