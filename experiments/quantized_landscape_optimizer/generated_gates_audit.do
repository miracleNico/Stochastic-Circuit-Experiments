# Focused dynamic regression for the generated primitive gates.  The final
# tb_generated_gates marker is reached only after all forward/reverse cases.
source [file join $::env(SIM_DIR) sim_common.do]
onerror {quit -code 1}
onbreak {quit -code 1}

vlib work
vmap work [file join $::sim_build_dir work]

vcom -2008 [sim_repo_path {src/inv_sc_pkg.vhd}]
vcom -2008 [sim_repo_path {src/lfsr32.vhd}]
vcom -2008 [sim_repo_path {src/spin_node.vhd}]
vcom -2008 [sim_repo_path {src/generated_networks.vhd}]
vcom -2008 [sim_repo_path {tb/tb_generated_gates.vhd}]

vsim work.tb_generated_gates
run 2 ms
quit -sim
quit -f
