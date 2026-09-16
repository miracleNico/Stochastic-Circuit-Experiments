# Shared Questa initialization. The PowerShell runner supplies these
# variables so every simulation can run from its own isolated build directory.
set sim_dir [file normalize [file dirname [info script]]]
if {[info exists ::env(SIM_DIR)]} {
    set sim_dir [file normalize $::env(SIM_DIR)]
}

set repo_root [file normalize [file join $sim_dir ..]]
if {[info exists ::env(SIM_REPO_ROOT)]} {
    set repo_root [file normalize $::env(SIM_REPO_ROOT)]
}
set sim_build_dir [pwd]
if {[info exists ::env(SIM_BUILD_DIR)]} {
    set sim_build_dir [file normalize $::env(SIM_BUILD_DIR)]
}
set sim_wave_mode "None"
if {[info exists ::env(SIM_WAVE_MODE)]} {
    set sim_wave_mode $::env(SIM_WAVE_MODE)
}
set sim_wave_path [file join $sim_build_dir wave.wlf]
if {[info exists ::env(SIM_WAVE_PATH)]} {
    set sim_wave_path [file normalize $::env(SIM_WAVE_PATH)]
}

proc sim_repo_path {relative_path} {
    return [file normalize [file join $::repo_root $relative_path]]
}

proc sim_input_path {path} {
    if {[file pathtype $path] eq "absolute"} {
        return [file normalize $path]
    }
    return [file normalize [file join $::sim_dir $path]]
}

# Wrap elaboration once so every existing .do gets consistent WLF behavior
# without changing its generics or simulation timing.
if {[llength [info commands sim_native_vsim]] == 0} {
    rename vsim sim_native_vsim
    proc vsim {args} {
        puts "SIM_PHASE: elaboration"
        set invoke_args $args
        if {$::sim_wave_mode ne "None"} {
            set invoke_args [linsert $invoke_args 0 -wlf $::sim_wave_path]
            if {$::sim_wave_mode eq "All"} {
                set invoke_args [linsert $invoke_args 0 -voptargs=+acc]
            }
        }
        set result [uplevel 1 [linsert $invoke_args 0 sim_native_vsim]]
        if {$::sim_wave_mode eq "Top"} {
            catch {log /*}
        } elseif {$::sim_wave_mode eq "All"} {
            catch {log -r /*}
        }
        return $result
    }
}

if {[llength [info commands sim_native_vcom]] == 0} {
    rename vcom sim_native_vcom
    proc vcom {args} {
        puts "SIM_PHASE: compile"
        return [uplevel 1 [linsert $args 0 sim_native_vcom]]
    }
}

if {[llength [info commands sim_native_run]] == 0} {
    rename run sim_native_run
    proc run {args} {
        puts "SIM_PHASE: runtime"
        return [uplevel 1 [linsert $args 0 sim_native_run]]
    }
}
