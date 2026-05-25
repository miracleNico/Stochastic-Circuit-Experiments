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
vcom -2008 ../src/inv_xor_gate.vhd
vcom -2008 ../tb/tb_inv_xor_trace.vhd

vsim work.tb_inv_xor_trace
run -all

quit -f
