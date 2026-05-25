$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir

& (Join-Path $scriptDir "run_and_trace.ps1")
& (Join-Path $scriptDir "run_xor_trace.ps1")

python (Join-Path $root "scripts\plot_small_gate_probabilities.py") `
    --summary (Join-Path $scriptDir "generated_gate_probability_summary.csv") `
    --states (Join-Path $scriptDir "generated_gate_state_probabilities.csv") `
    --ab (Join-Path $scriptDir "generated_gate_ab_probabilities.csv") `
    --plot (Join-Path $scriptDir "generated_gate_probabilities.png")
