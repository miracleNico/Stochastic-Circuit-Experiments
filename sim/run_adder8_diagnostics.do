transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work_adder_diag]} {
    vdel -lib work_adder_diag -all
}

set generated_networks "../src/generated_networks.vhd"
if {[info exists ::env(GENERATED_NETWORKS_VHDL)]} {
    set generated_networks $::env(GENERATED_NETWORKS_VHDL)
}
set adder_rnd_weight 1
if {[info exists ::env(ADDER_RND_WEIGHT)]} {
    set adder_rnd_weight $::env(ADDER_RND_WEIGHT)
}

vlib work_adder_diag
vmap work work_adder_diag

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 $generated_networks
vcom -2008 ../tb/tb_adder8_diagnostics.vhd

vsim -gADDER_RND_WEIGHT=$adder_rnd_weight work.tb_adder8_diagnostics
run 100 us

quit -f
