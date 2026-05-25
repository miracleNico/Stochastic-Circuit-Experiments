$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$scriptDir = Join-Path $root "sim"
$modelsimBin = "C:\intelFPGA_lite\modelsim_ase\win32aloem"
$vsim = Join-Path $modelsimBin "vsim.exe"
$plotter = Join-Path $root "scripts\plot_and_trace.py"

if (-not (Test-Path -LiteralPath $vsim)) {
    throw "ModelSim executable not found at $vsim"
}

Push-Location $scriptDir
try {
    & $vsim -c -do run_xor_trace.do
    if ($LASTEXITCODE -ne 0) {
        throw "ModelSim returned exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

python $plotter `
    --gate xor `
    --input (Join-Path $scriptDir "xor_trace.csv") `
    --plot (Join-Path $scriptDir "xor_trace.png") `
    --summary (Join-Path $scriptDir "xor_trace_summary.csv") `
    --probabilities (Join-Path $scriptDir "xor_state_probabilities.csv") `
    --ab-probabilities (Join-Path $scriptDir "xor_ab_probabilities.csv")
