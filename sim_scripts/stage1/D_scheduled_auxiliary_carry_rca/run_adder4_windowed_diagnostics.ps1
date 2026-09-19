param(
    [int]$ActiveRndWeight = -1,
    [int]$FinalRndWeight = -1,
    [int]$Wave0Cycles = -1,
    [int]$Wave1Cycles = -1,
    [int]$Wave2Cycles = -1,
    [int]$Wave3Cycles = -1,
    [int]$FinalCycles = -1,
    [int]$CountCycles = -1,
    [ValidateSet('Questa', 'ModelSim')][string]$Simulator = 'Questa',
    [string]$VsimPath = '',
    [string]$LicenseFile = '',
    [string]$LicenseServer = '',
    [string]$BuildRoot = '',
    [string]$RunId = '',
    [ValidateSet('None', 'Top', 'All')][string]$WaveMode = 'None',
    [switch]$KeepWork,
    [ValidateRange(0, 2147483)][int]$TimeoutSeconds = 0)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
function Invoke-ConfiguredSimulation {
    param([Parameter(Mandatory)][string]$DoFile, [switch]$Gui, [switch]$Detach)
    $invokeArguments = @{
        DoFile = $DoFile
        Simulator = $Simulator
        WaveMode = $WaveMode
        KeepWork = $KeepWork
        TimeoutSeconds = $TimeoutSeconds
        Gui = $Gui
        Detach = $Detach
        PassThru = $true
    }
    foreach ($name in @('VsimPath', 'LicenseFile', 'LicenseServer', 'BuildRoot', 'RunId')) {
        $value = Get-Variable -Name $name -ValueOnly -Scope 1
        if (-not [string]::IsNullOrWhiteSpace($value)) { $invokeArguments[$name] = $value }
    }
    $result = & (Join-Path (Split-Path -Parent (Split-Path -Parent $scriptDir)) 'Invoke-Simulation.ps1') @invokeArguments
    if ($result.ExitCode -ne 0) {
        [Console]::Error.WriteLine("$Simulator simulation failed with exit code $($result.ExitCode). See $($result.TranscriptPath)")
        exit $result.ExitCode
    }
    return $result
}

Push-Location $scriptDir
try {
    $oldActiveRndWeight = $env:ACTIVE_RND_WEIGHT
    if ($ActiveRndWeight -ge 0) { $env:ACTIVE_RND_WEIGHT = [string]$ActiveRndWeight }

    $oldFinalRndWeight = $env:FINAL_RND_WEIGHT
    if ($FinalRndWeight -ge 0) { $env:FINAL_RND_WEIGHT = [string]$FinalRndWeight }

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

    $simulationResult = Invoke-ConfiguredSimulation -DoFile (Join-Path $scriptDir run_adder4_windowed_diagnostics.do)
}
finally {
    if ($null -eq $oldActiveRndWeight) { Remove-Item Env:\ACTIVE_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:ACTIVE_RND_WEIGHT = $oldActiveRndWeight }
    if ($null -eq $oldFinalRndWeight) { Remove-Item Env:\FINAL_RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:FINAL_RND_WEIGHT = $oldFinalRndWeight }
    if ($null -eq $oldWave0Cycles) { Remove-Item Env:\WAVE0_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE0_CYCLES = $oldWave0Cycles }
    if ($null -eq $oldWave1Cycles) { Remove-Item Env:\WAVE1_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE1_CYCLES = $oldWave1Cycles }
    if ($null -eq $oldWave2Cycles) { Remove-Item Env:\WAVE2_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE2_CYCLES = $oldWave2Cycles }
    if ($null -eq $oldWave3Cycles) { Remove-Item Env:\WAVE3_CYCLES -ErrorAction SilentlyContinue } else { $env:WAVE3_CYCLES = $oldWave3Cycles }
    if ($null -eq $oldFinalCycles) { Remove-Item Env:\FINAL_CYCLES -ErrorAction SilentlyContinue } else { $env:FINAL_CYCLES = $oldFinalCycles }
    if ($null -eq $oldCountCycles) { Remove-Item Env:\COUNT_CYCLES -ErrorAction SilentlyContinue } else { $env:COUNT_CYCLES = $oldCountCycles }
    Pop-Location
}
