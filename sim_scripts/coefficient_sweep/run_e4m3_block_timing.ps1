param(
    [string]$GeneratedNetworks = "",
    [int]$RndWeight = -1,
    [int]$SettleCycles = -1,
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
    $result = & (Join-Path (Split-Path -Parent $scriptDir) 'Invoke-Simulation.ps1') @invokeArguments
    if ($result.ExitCode -ne 0) {
        [Console]::Error.WriteLine("$Simulator simulation failed with exit code $($result.ExitCode). See $($result.TranscriptPath)")
        exit $result.ExitCode
    }
    return $result
}

Push-Location $scriptDir
try {
    $oldGeneratedNetworks = $env:GENERATED_NETWORKS_VHDL
    if ($GeneratedNetworks -ne "") {
        $env:GENERATED_NETWORKS_VHDL = $GeneratedNetworks
    }

    $oldRndWeight = $env:RND_WEIGHT
    if ($RndWeight -ge 0) {
        $env:RND_WEIGHT = [string]$RndWeight
    }

    $oldSettleCycles = $env:SETTLE_CYCLES
    if ($SettleCycles -ge 0) {
        $env:SETTLE_CYCLES = [string]$SettleCycles
    }

    $oldCountCycles = $env:COUNT_CYCLES
    if ($CountCycles -ge 0) {
        $env:COUNT_CYCLES = [string]$CountCycles
    }

    $simulationResult = Invoke-ConfiguredSimulation -DoFile (Join-Path $scriptDir run_e4m3_block_timing.do)
}
finally {
    if ($null -eq $oldGeneratedNetworks) {
        Remove-Item Env:\GENERATED_NETWORKS_VHDL -ErrorAction SilentlyContinue
    }
    else {
        $env:GENERATED_NETWORKS_VHDL = $oldGeneratedNetworks
    }

    if ($null -eq $oldRndWeight) {
        Remove-Item Env:\RND_WEIGHT -ErrorAction SilentlyContinue
    }
    else {
        $env:RND_WEIGHT = $oldRndWeight
    }

    if ($null -eq $oldSettleCycles) {
        Remove-Item Env:\SETTLE_CYCLES -ErrorAction SilentlyContinue
    }
    else {
        $env:SETTLE_CYCLES = $oldSettleCycles
    }

    if ($null -eq $oldCountCycles) {
        Remove-Item Env:\COUNT_CYCLES -ErrorAction SilentlyContinue
    }
    else {
        $env:COUNT_CYCLES = $oldCountCycles
    }

    Pop-Location
}
