if {[info exists ::env(SIM_DIR)]} {
    source [file join $::env(SIM_DIR) sim_common.do]
} else {
    source [file join [file dirname [file dirname [info script]]] sim_common.do]
}
transcript on
onerror {puts "Simulator setup failed"; return}

if {![file exists work]} {
    vlib work
}
vmap work work

vcom -2008 [sim_repo_path {src/inv_sc_pkg.vhd}]
vcom -2008 [sim_repo_path {src/lfsr32.vhd}]
vcom -2008 [sim_repo_path {src/spin_node.vhd}]
vcom -2008 [sim_repo_path {src/inv_and_gate.vhd}]
vcom -2008 [sim_repo_path {sim_scripts/gate_baseline/tb/tb_inv_and_gate.vhd}]

vsim work.tb_inv_and_gate

view wave
delete wave *

add wave -divider "Clock and control"
add wave -radix binary /tb_inv_and_gate/clk
add wave -radix binary /tb_inv_and_gate/rst
add wave -radix binary /tb_inv_and_gate/enable

add wave -divider "Clamp controls"
add wave -radix binary /tb_inv_and_gate/clamp_a_en
add wave -radix binary /tb_inv_and_gate/clamp_a_value
add wave -radix binary /tb_inv_and_gate/clamp_b_en
add wave -radix binary /tb_inv_and_gate/clamp_b_value
add wave -radix binary /tb_inv_and_gate/clamp_y_en
add wave -radix binary /tb_inv_and_gate/clamp_y_value

add wave -divider "AND gate spins"
add wave -radix binary /tb_inv_and_gate/a
add wave -radix binary /tb_inv_and_gate/b
add wave -radix binary /tb_inv_and_gate/y
add wave -radix unsigned /tb_inv_and_gate/dut/phase

add wave -divider "Local fields"
add wave -radix decimal /tb_inv_and_gate/field_a
add wave -radix decimal /tb_inv_and_gate/field_b
add wave -radix decimal /tb_inv_and_gate/field_y

add wave -divider "Spin-node internals"
add wave -radix decimal /tb_inv_and_gate/dut/node_a/counter_q
add wave -radix decimal /tb_inv_and_gate/dut/node_b/counter_q
add wave -radix decimal /tb_inv_and_gate/dut/node_y/counter_q
add wave -radix binary /tb_inv_and_gate/dut/node_a/rnd_bit
add wave -radix binary /tb_inv_and_gate/dut/node_b/rnd_bit
add wave -radix binary /tb_inv_and_gate/dut/node_y/rnd_bit

run 20 us
wave zoom full
