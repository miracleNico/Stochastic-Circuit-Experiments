param(
    [string]$GeneratedNetworks = "",
    [int]$CombRndWeight = -1,
    [int]$SettleCycles = -1,
    [int]$CountCycles = -1
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

    $oldCombRndWeight = $env:COMB_RND_WEIGHT
    if ($CombRndWeight -ge 0) {
        $env:COMB_RND_WEIGHT = [string]$CombRndWeight
    }

    $oldSettleCycles = $env:COMB_SETTLE_CYCLES
    if ($SettleCycles -ge 0) {
        $env:COMB_SETTLE_CYCLES = [string]$SettleCycles
    }

    $oldCountCycles = $env:COMB_COUNT_CYCLES
    if ($CountCycles -ge 0) {
        $env:COMB_COUNT_CYCLES = [string]$CountCycles
    }

    & $vsim -c -do run_comb6_diagnostics.do
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

    if ($null -eq $oldCombRndWeight) {
        Remove-Item Env:\COMB_RND_WEIGHT -ErrorAction SilentlyContinue
    }
    else {
        $env:COMB_RND_WEIGHT = $oldCombRndWeight
    }

    if ($null -eq $oldSettleCycles) {
        Remove-Item Env:\COMB_SETTLE_CYCLES -ErrorAction SilentlyContinue
    }
    else {
        $env:COMB_SETTLE_CYCLES = $oldSettleCycles
    }

    if ($null -eq $oldCountCycles) {
        Remove-Item Env:\COMB_COUNT_CYCLES -ErrorAction SilentlyContinue
    }
    else {
        $env:COMB_COUNT_CYCLES = $oldCountCycles
    }

    Pop-Location
}
