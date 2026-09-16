if {[info exists ::env(SIM_DIR)]} {
    source [file join $::env(SIM_DIR) sim_common.do]
} else {
    source [file join [file dirname [info script]] .. .. .. .. sim_common.do]
}
transcript on
onerror {quit -code 1}
onbreak {quit -code 1}

vlib work
vmap work work
vsim work.deliberately_missing_entity
quit -f
