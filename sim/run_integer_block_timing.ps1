param(
    [string]$GeneratedNetworks = "",
    [int]$RndWeight = -1,
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
    if ($GeneratedNetworks -ne "") { $env:GENERATED_NETWORKS_VHDL = $GeneratedNetworks }

    $oldRndWeight = $env:RND_WEIGHT
    if ($RndWeight -ge 0) { $env:RND_WEIGHT = [string]$RndWeight }

    $oldSettleCycles = $env:SETTLE_CYCLES
    if ($SettleCycles -ge 0) { $env:SETTLE_CYCLES = [string]$SettleCycles }

    $oldCountCycles = $env:COUNT_CYCLES
    if ($CountCycles -ge 0) { $env:COUNT_CYCLES = [string]$CountCycles }

    & $vsim -c -do run_integer_block_timing.do
    if ($LASTEXITCODE -ne 0) { throw "ModelSim returned exit code $LASTEXITCODE" }
}
finally {
    if ($null -eq $oldGeneratedNetworks) { Remove-Item Env:\GENERATED_NETWORKS_VHDL -ErrorAction SilentlyContinue } else { $env:GENERATED_NETWORKS_VHDL = $oldGeneratedNetworks }
    if ($null -eq $oldRndWeight) { Remove-Item Env:\RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:RND_WEIGHT = $oldRndWeight }
    if ($null -eq $oldSettleCycles) { Remove-Item Env:\SETTLE_CYCLES -ErrorAction SilentlyContinue } else { $env:SETTLE_CYCLES = $oldSettleCycles }
    if ($null -eq $oldCountCycles) { Remove-Item Env:\COUNT_CYCLES -ErrorAction SilentlyContinue } else { $env:COUNT_CYCLES = $oldCountCycles }
    Pop-Location
}
