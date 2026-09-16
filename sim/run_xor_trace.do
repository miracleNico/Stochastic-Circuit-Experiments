if {[info exists ::env(SIM_DIR)]} {
    source [file join $::env(SIM_DIR) sim_common.do]
} else {
    source [file join [file dirname [info script]] sim_common.do]
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
vcom -2008 [sim_repo_path {src/inv_xor_gate.vhd}]
vcom -2008 [sim_repo_path {tb/tb_inv_xor_trace.vhd}]

vsim work.tb_inv_xor_trace
run -all

quit -f
