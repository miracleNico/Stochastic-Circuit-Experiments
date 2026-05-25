param(
    [string]$GeneratedNetworks = "",
    [int]$AdderRndWeight = -1,
    [int]$ScrambleCycles = -1,
    [int]$SettleCycles = -1,
    [int]$Trials = -1
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

    $oldAdderRndWeight = $env:ADDER_RND_WEIGHT
    if ($AdderRndWeight -ge 0) { $env:ADDER_RND_WEIGHT = [string]$AdderRndWeight }

    $oldScrambleCycles = $env:SCRAMBLE_CYCLES
    if ($ScrambleCycles -ge 0) { $env:SCRAMBLE_CYCLES = [string]$ScrambleCycles }

    $oldSettleCycles = $env:SETTLE_CYCLES
    if ($SettleCycles -ge 0) { $env:SETTLE_CYCLES = [string]$SettleCycles }

    $oldTrials = $env:TRIALS
    if ($Trials -ge 0) { $env:TRIALS = [string]$Trials }

    & $vsim -c -do run_adder4_direct_randomized_exhaustive.do
    if ($LASTEXITCODE -ne 0) { throw "ModelSim returned exit code $LASTEXITCODE" }
}
finally {
    if ($null -eq $oldGeneratedNetworks) { Remove-Item Env:\GENERATED_NETWORKS_VHDL -ErrorAction SilentlyContinue } else { $env:GENERATED_NETWORKS_VHDL = $oldGeneratedNetworks }
    if ($null -eq $oldAdderRndWeight) { Remove-Item Env:\ADDER_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:ADDER_RND_WEIGHT = $oldAdderRndWeight }
    if ($null -eq $oldScrambleCycles) { Remove-Item Env:\SCRAMBLE_CYCLES -ErrorAction SilentlyContinue } else { $env:SCRAMBLE_CYCLES = $oldScrambleCycles }
    if ($null -eq $oldSettleCycles) { Remove-Item Env:\SETTLE_CYCLES -ErrorAction SilentlyContinue } else { $env:SETTLE_CYCLES = $oldSettleCycles }
    if ($null -eq $oldTrials) { Remove-Item Env:\TRIALS -ErrorAction SilentlyContinue } else { $env:TRIALS = $oldTrials }
    Pop-Location
}
