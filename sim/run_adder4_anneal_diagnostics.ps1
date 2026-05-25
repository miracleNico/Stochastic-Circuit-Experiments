param(
    [int]$HotRndWeight = -1,
    [int]$ColdRndWeight = -1,
    [int]$WaveCycles = -1,
    [int]$FinalCycles = -1,
    [int]$CountCycles = -1,
    [int]$ReverseCool = -1
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
    $oldHotRndWeight = $env:HOT_RND_WEIGHT
    if ($HotRndWeight -ge 0) {
        $env:HOT_RND_WEIGHT = [string]$HotRndWeight
    }

    $oldColdRndWeight = $env:COLD_RND_WEIGHT
    if ($ColdRndWeight -ge 0) {
        $env:COLD_RND_WEIGHT = [string]$ColdRndWeight
    }

    $oldWaveCycles = $env:WAVE_CYCLES
    if ($WaveCycles -ge 0) {
        $env:WAVE_CYCLES = [string]$WaveCycles
    }

    $oldFinalCycles = $env:FINAL_CYCLES
    if ($FinalCycles -ge 0) {
        $env:FINAL_CYCLES = [string]$FinalCycles
    }

    $oldCountCycles = $env:COUNT_CYCLES
    if ($CountCycles -ge 0) {
        $env:COUNT_CYCLES = [string]$CountCycles
    }

    $oldReverseCool = $env:REVERSE_COOL
    if ($ReverseCool -ge 0) {
        if ($ReverseCool -eq 0) {
            $env:REVERSE_COOL = "false"
        }
        else {
            $env:REVERSE_COOL = "true"
        }
    }

    & $vsim -c -do run_adder4_anneal_diagnostics.do
    if ($LASTEXITCODE -ne 0) {
        throw "ModelSim returned exit code $LASTEXITCODE"
    }
}
finally {
    if ($null -eq $oldHotRndWeight) {
        Remove-Item Env:\HOT_RND_WEIGHT -ErrorAction SilentlyContinue
    }
    else {
        $env:HOT_RND_WEIGHT = $oldHotRndWeight
    }

    if ($null -eq $oldColdRndWeight) {
        Remove-Item Env:\COLD_RND_WEIGHT -ErrorAction SilentlyContinue
    }
    else {
        $env:COLD_RND_WEIGHT = $oldColdRndWeight
    }

    if ($null -eq $oldWaveCycles) {
        Remove-Item Env:\WAVE_CYCLES -ErrorAction SilentlyContinue
    }
    else {
        $env:WAVE_CYCLES = $oldWaveCycles
    }

    if ($null -eq $oldFinalCycles) {
        Remove-Item Env:\FINAL_CYCLES -ErrorAction SilentlyContinue
    }
    else {
        $env:FINAL_CYCLES = $oldFinalCycles
    }

    if ($null -eq $oldCountCycles) {
        Remove-Item Env:\COUNT_CYCLES -ErrorAction SilentlyContinue
    }
    else {
        $env:COUNT_CYCLES = $oldCountCycles
    }

    if ($null -eq $oldReverseCool) {
        Remove-Item Env:\REVERSE_COOL -ErrorAction SilentlyContinue
    }
    else {
        $env:REVERSE_COOL = $oldReverseCool
    }

    Pop-Location
}
