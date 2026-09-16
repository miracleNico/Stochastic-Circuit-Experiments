if {[info exists ::env(SIM_DIR)]} {
    source [file join $::env(SIM_DIR) sim_common.do]
} else {
    source [file join [file dirname [info script]] .. .. sim_common.do]
}
transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

vlib work
vmap work work
vcom -2008 [sim_repo_path {sim/tests/fixtures/compile_error.vhd}]
quit -f
