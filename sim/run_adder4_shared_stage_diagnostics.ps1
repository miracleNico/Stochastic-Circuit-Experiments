param(
    [string]$GeneratedNetworks = "",
    [int]$HotRndWeight = -1,
    [int]$ColdRndWeight = -1,
    [int]$Wave0Cycles = -1,
    [int]$Wave1Cycles = -1,
    [int]$Wave2Cycles = -1,
    [int]$Wave3Cycles = -1,
    [int]$FinalCycles = -1,
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

    $oldHotRndWeight = $env:HOT_RND_WEIGHT
    if ($HotRndWeight -ge 0) { $env:HOT_RND_WEIGHT = [string]$HotRndWeight }

    $oldColdRndWeight = $env:COLD_RND_WEIGHT
    if ($ColdRndWeight -ge 0) { $env:COLD_RND_WEIGHT = [string]$ColdRndWeight }

    $oldWave0Cycles = $env:WAVE0_CYCLES
    if ($Wave0Cycles -ge 0) { $env:WAVE0_CYCLES = [string]$Wave0Cycles }

    $oldWave1Cycles = $env:WAVE1_CYCLES
    if ($Wave1Cycles -ge 0) { $env:WAVE1_CYCLES = [string]$Wave1Cycles }

    $oldWave2Cycles = $env:WAVE2_CYCLES
    if ($Wave2Cycles -ge 0) { $env:WAVE2_CYCLES = [string]$Wave2Cycles }

    $oldWave3Cycles = $env:WAVE3_CYCLES
    if ($Wave3Cycles -ge 0) { $env:WAVE3_CYCLES = [string]$Wave3Cycles }

    $oldFinalCycles = $env:FINAL_CYCLES
    if ($FinalCycles -ge 0) { $env:FINAL_CYCLES = [string]$FinalCycles }

    $oldCountCycles = $env:COUNT_CYCLES
    if ($CountCycles -ge 0) { $env:COUNT_CYCLES = [string]$CountCycles }

    & $vsim -c -do run_adder4_shared_stage_diagnostics.do
    if ($LASTEXITCODE -ne 0) { throw "ModelSim returned exit code $LASTEXITCODE" }
}
finally {
    if ($null -eq $oldGeneratedNetworks) { Remove-Item Env:\GENERATED_NETWORKS_VHDL -ErrorAction SilentlyContinue } else { $env:GENERATED_NETWORKS_VHDL = $oldGeneratedNetworks }
    if ($null -eq $oldHotRndWeight) { Remove-Item Env:\HOT_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:HOT_RND_WEIGHT = $oldHotRndWeight }
    if ($null -eq $oldColdRndWeight) { Remove-Item Env:\COLD_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:COLD_RND_WEIGHT = $oldColdRndWeight }
    if ($null -eq $oldWave0Cycles) { Remove-Item Env:\WAVE0_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE0_CYCLES = $oldWave0Cycles }
    if ($null -eq $oldWave1Cycles) { Remove-Item Env:\WAVE1_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE1_CYCLES = $oldWave1Cycles }
    if ($null -eq $oldWave2Cycles) { Remove-Item Env:\WAVE2_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE2_CYCLES = $oldWave2Cycles }
    if ($null -eq $oldWave3Cycles) { Remove-Item Env:\WAVE3_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE3_CYCLES = $oldWave3Cycles }
    if ($null -eq $oldFinalCycles) { Remove-Item Env:\FINAL_CYCLES -ErrorAction SilentlyContinue } else { $env:FINAL_CYCLES = $oldFinalCycles }
    if ($null -eq $oldCountCycles) { Remove-Item Env:\COUNT_CYCLES -ErrorAction SilentlyContinue } else { $env:COUNT_CYCLES = $oldCountCycles }
    Pop-Location
}
