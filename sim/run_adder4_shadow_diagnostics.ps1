param(
    [int]$BlockRndWeight = -1,
    [int]$CopyRndWeight = -1,
    [int]$Block0Cycles = -1,
    [int]$Block1Cycles = -1,
    [int]$Block2Cycles = -1,
    [int]$Block3Cycles = -1,
    [int]$CopyCycles = -1,
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
    $oldBlockRndWeight = $env:BLOCK_RND_WEIGHT
    if ($BlockRndWeight -ge 0) { $env:BLOCK_RND_WEIGHT = [string]$BlockRndWeight }

    $oldCopyRndWeight = $env:COPY_RND_WEIGHT
    if ($CopyRndWeight -ge 0) { $env:COPY_RND_WEIGHT = [string]$CopyRndWeight }

    $oldBlock0Cycles = $env:BLOCK0_CYCLES
    if ($Block0Cycles -ge 0) { $env:BLOCK0_CYCLES = [string]$Block0Cycles }

    $oldBlock1Cycles = $env:BLOCK1_CYCLES
    if ($Block1Cycles -ge 0) { $env:BLOCK1_CYCLES = [string]$Block1Cycles }

    $oldBlock2Cycles = $env:BLOCK2_CYCLES
    if ($Block2Cycles -ge 0) { $env:BLOCK2_CYCLES = [string]$Block2Cycles }

    $oldBlock3Cycles = $env:BLOCK3_CYCLES
    if ($Block3Cycles -ge 0) { $env:BLOCK3_CYCLES = [string]$Block3Cycles }

    $oldCopyCycles = $env:COPY_CYCLES
    if ($CopyCycles -ge 0) { $env:COPY_CYCLES = [string]$CopyCycles }

    $oldCountCycles = $env:COUNT_CYCLES
    if ($CountCycles -ge 0) { $env:COUNT_CYCLES = [string]$CountCycles }

    & $vsim -c -do run_adder4_shadow_diagnostics.do
    if ($LASTEXITCODE -ne 0) { throw "ModelSim returned exit code $LASTEXITCODE" }
}
finally {
    if ($null -eq $oldBlockRndWeight) { Remove-Item Env:\BLOCK_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:BLOCK_RND_WEIGHT = $oldBlockRndWeight }
    if ($null -eq $oldCopyRndWeight) { Remove-Item Env:\COPY_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:COPY_RND_WEIGHT = $oldCopyRndWeight }
    if ($null -eq $oldBlock0Cycles) { Remove-Item Env:\BLOCK0_CYCLES -ErrorAction SilentlyContinue } else { $env:BLOCK0_CYCLES = $oldBlock0Cycles }
    if ($null -eq $oldBlock1Cycles) { Remove-Item Env:\BLOCK1_CYCLES -ErrorAction SilentlyContinue } else { $env:BLOCK1_CYCLES = $oldBlock1Cycles }
    if ($null -eq $oldBlock2Cycles) { Remove-Item Env:\BLOCK2_CYCLES -ErrorAction SilentlyContinue } else { $env:BLOCK2_CYCLES = $oldBlock2Cycles }
    if ($null -eq $oldBlock3Cycles) { Remove-Item Env:\BLOCK3_CYCLES -ErrorAction SilentlyContinue } else { $env:BLOCK3_CYCLES = $oldBlock3Cycles }
    if ($null -eq $oldCopyCycles) { Remove-Item Env:\COPY_CYCLES -ErrorAction SilentlyContinue } else { $env:COPY_CYCLES = $oldCopyCycles }
    if ($null -eq $oldCountCycles) { Remove-Item Env:\COUNT_CYCLES -ErrorAction SilentlyContinue } else { $env:COUNT_CYCLES = $oldCountCycles }
    Pop-Location
}
