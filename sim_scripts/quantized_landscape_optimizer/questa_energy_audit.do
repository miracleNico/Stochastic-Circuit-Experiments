# Static HA/FA energy-landscape audit.  Invoke through sim_scripts/Invoke-Simulation.ps1;
# run_questa_audit.ps1 prepares the generated coefficient package and sets the
# package path for this isolated run.
source [file join $::env(SIM_DIR) sim_common.do]
onerror {quit -code 1}
onbreak {quit -code 1}

if {![info exists ::env(OPTIMIZER_COEFFICIENT_PACKAGE)]} {
    error "OPTIMIZER_COEFFICIENT_PACKAGE must name the generated VHDL package"
}

set coefficient_package [file normalize $::env(OPTIMIZER_COEFFICIENT_PACKAGE)]
if {![file isfile $coefficient_package]} {
    error "optimizer coefficient package not found: $coefficient_package"
}

vlib work
vmap work [file join $::sim_build_dir work]
vcom -2008 $coefficient_package
vcom -2008 [sim_repo_path {sim_scripts/quantized_landscape_optimizer/tb/tb_optimizer_energy_audit.vhd}]

vsim work.tb_optimizer_energy_audit
run 1 ns
quit -sim
quit -f
