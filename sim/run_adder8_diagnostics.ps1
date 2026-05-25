param(
    [string]$GeneratedNetworks = "",
    [int]$AdderRndWeight = -1
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelsimBin = "C:\intelFPGA_lite\modelsim_ase\win32aloem"
$vsim = Join-Path $modelsimBin "vsim.exe"

if (-not (Test-Path -LiteralPath $vsim)) {
    throw "ModelSim executable not found at $vsim"
}

Push-Location $scriptDir
try {
    $oldGeneratedNetworks = $env:GENERATED_NETWORKS_VHDL
    if ($GeneratedNetworks -ne "") {
        $env:GENERATED_NETWORKS_VHDL = $GeneratedNetworks
    }
    $oldAdderRndWeight = $env:ADDER_RND_WEIGHT
    if ($AdderRndWeight -ge 0) {
        $env:ADDER_RND_WEIGHT = [string]$AdderRndWeight
    }
    & $vsim -c -do run_adder8_diagnostics.do
    if ($LASTEXITCODE -ne 0) {
        throw "ModelSim returned exit code $LASTEXITCODE"
    }
}
finally {
    if ($null -eq $oldGeneratedNetworks) {
        Remove-Item Env:\GENERATED_NETWORKS_VHDL -ErrorAction SilentlyContinue
    }
    else {
        $env:GENERATED_NETWORKS_VHDL = $oldGeneratedNetworks
    }
    if ($null -eq $oldAdderRndWeight) {
        Remove-Item Env:\ADDER_RND_WEIGHT -ErrorAction SilentlyContinue
    }
    else {
        $env:ADDER_RND_WEIGHT = $oldAdderRndWeight
    }
    Pop-Location
}
