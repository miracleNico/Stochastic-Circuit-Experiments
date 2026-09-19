if {[info exists ::env(SIM_DIR)]} {
    source [file join $::env(SIM_DIR) sim_common.do]
} else {
    source [file join [file dirname [file dirname [file dirname [info script]]]] sim_common.do]
}
transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

if {[file exists work]} {
    vdel -lib work -all
}

vlib work
vmap work work

vcom -2008 [sim_repo_path {src/inv_sc_pkg.vhd}]
vcom -2008 [sim_repo_path {src/lfsr32.vhd}]
vcom -2008 [sim_repo_path {src/spin_node.vhd}]
vcom -2008 [sim_repo_path {src/inv_and_gate.vhd}]
vcom -2008 [sim_repo_path {src/inv_xor_gate.vhd}]
vcom -2008 [sim_repo_path {experiments/stage1/A_primitive_spin_gate_validation/hardware/generated_networks.vhd}]
vcom -2008 [sim_repo_path {sim_scripts/stage1/A_primitive_spin_gate_validation/tb/tb_inv_and_gate.vhd}]
vcom -2008 [sim_repo_path {sim_scripts/stage1/A_primitive_spin_gate_validation/tb/tb_inv_xor_gate.vhd}]
vcom -2008 [sim_repo_path {sim_scripts/stage1/A_primitive_spin_gate_validation/tb/tb_generated_gates.vhd}]
vcom -2008 [sim_repo_path {sim_scripts/stage1/A_primitive_spin_gate_validation/tb/tb_generated_systems.vhd}]

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
