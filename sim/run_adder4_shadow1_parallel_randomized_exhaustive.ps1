param(
    [string]$GeneratedShadowVhdl = "",
    [int]$BlockRndWeight = -1,
    [int]$CopyRndWeight = -1,
    [int]$ScrambleRndWeight = -1,
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
    $oldGeneratedShadowVhdl = $env:GENERATED_SHADOW_VHDL
    if ($GeneratedShadowVhdl -ne "") { $env:GENERATED_SHADOW_VHDL = $GeneratedShadowVhdl }

    $oldBlockRndWeight = $env:BLOCK_RND_WEIGHT
    if ($BlockRndWeight -ge 0) { $env:BLOCK_RND_WEIGHT = [string]$BlockRndWeight }

    $oldCopyRndWeight = $env:COPY_RND_WEIGHT
    if ($CopyRndWeight -ge 0) { $env:COPY_RND_WEIGHT = [string]$CopyRndWeight }

    $oldScrambleRndWeight = $env:SCRAMBLE_RND_WEIGHT
    if ($ScrambleRndWeight -ge 0) { $env:SCRAMBLE_RND_WEIGHT = [string]$ScrambleRndWeight }

    $oldScrambleCycles = $env:SCRAMBLE_CYCLES
    if ($ScrambleCycles -ge 0) { $env:SCRAMBLE_CYCLES = [string]$ScrambleCycles }

    $oldSettleCycles = $env:SETTLE_CYCLES
    if ($SettleCycles -ge 0) { $env:SETTLE_CYCLES = [string]$SettleCycles }

    $oldTrials = $env:TRIALS
    if ($Trials -ge 0) { $env:TRIALS = [string]$Trials }

    & $vsim -c -do run_adder4_shadow1_parallel_randomized_exhaustive.do
    if ($LASTEXITCODE -ne 0) { throw "ModelSim returned exit code $LASTEXITCODE" }
}
finally {
    if ($null -eq $oldGeneratedShadowVhdl) { Remove-Item Env:\GENERATED_SHADOW_VHDL -ErrorAction SilentlyContinue } else { $env:GENERATED_SHADOW_VHDL = $oldGeneratedShadowVhdl }
    if ($null -eq $oldBlockRndWeight) { Remove-Item Env:\BLOCK_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:BLOCK_RND_WEIGHT = $oldBlockRndWeight }
    if ($null -eq $oldCopyRndWeight) { Remove-Item Env:\COPY_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:COPY_RND_WEIGHT = $oldCopyRndWeight }
    if ($null -eq $oldScrambleRndWeight) { Remove-Item Env:\SCRAMBLE_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:SCRAMBLE_RND_WEIGHT = $oldScrambleRndWeight }
    if ($null -eq $oldScrambleCycles) { Remove-Item Env:\SCRAMBLE_CYCLES -ErrorAction SilentlyContinue } else { $env:SCRAMBLE_CYCLES = $oldScrambleCycles }
    if ($null -eq $oldSettleCycles) { Remove-Item Env:\SETTLE_CYCLES -ErrorAction SilentlyContinue } else { $env:SETTLE_CYCLES = $oldSettleCycles }
    if ($null -eq $oldTrials) { Remove-Item Env:\TRIALS -ErrorAction SilentlyContinue } else { $env:TRIALS = $oldTrials }
    Pop-Location
}
