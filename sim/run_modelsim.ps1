$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelsimBin = "C:\intelFPGA_lite\modelsim_ase\win32aloem"
$vsim = Join-Path $modelsimBin "vsim.exe"

if (-not (Test-Path -LiteralPath $vsim)) {
    throw "ModelSim executable not found at $vsim"
}

Push-Location $scriptDir
try {
    & $vsim -c -do run_modelsim.do
    if ($LASTEXITCODE -ne 0) {
        throw "ModelSim returned exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
