param(
    [ValidateSet('ModelSim')][string]$Simulator = 'ModelSim',
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
$repoRoot = [IO.Path]::GetFullPath((Join-Path $scriptDir '..\..'))
$simDir = Join-Path $repoRoot 'sim_scripts'
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
    $result = & (Join-Path $simDir 'Invoke-Simulation.ps1') @invokeArguments
    if ($result.ExitCode -ne 0) {
        [Console]::Error.WriteLine("$Simulator simulation failed with exit code $($result.ExitCode). See $($result.TranscriptPath)")
        exit $result.ExitCode
    }
    return $result
}

Push-Location $simDir
try {
    $simulationResult = Invoke-ConfiguredSimulation -DoFile (Join-Path $simDir 'stage1/A_primitive_spin_gate_validation/run_gate_regression.do')
}
finally {
    Pop-Location
}
