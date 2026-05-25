transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work]} {
    vdel -lib work -all
}

vlib work
vmap work work

vcom -2008 ../src/inv_sc_pkg.vhd
vcom -2008 ../src/lfsr32.vhd
vcom -2008 ../src/spin_node.vhd
vcom -2008 ../src/inv_and_gate.vhd
vcom -2008 ../src/inv_xor_gate.vhd
vcom -2008 ../src/generated_networks.vhd
vcom -2008 ../tb/tb_inv_and_gate.vhd
vcom -2008 ../tb/tb_inv_xor_gate.vhd
vcom -2008 ../tb/tb_generated_gates.vhd
vcom -2008 ../tb/tb_generated_systems.vhd

vsim work.tb_inv_and_gate
run 20 us
quit -sim

vsim work.tb_inv_xor_gate
run 100 us
quit -sim

vsim work.tb_generated_gates
run 2 ms
quit -sim

vsim work.tb_generated_systems
run 300 us
quit -sim

quit -f
