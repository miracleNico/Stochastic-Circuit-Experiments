[CmdletBinding()]
param(
    [ValidateSet('Questa')][string]$Simulator = 'Questa',
    [string]$VsimPath = '',
    [string]$LicenseFile = '',
    [string]$LicenseServer = '',
    [string]$BuildRoot = '',
    [string]$RunId = '',
    [ValidateSet('None', 'Top', 'All')][string]$WaveMode = 'None',
    [switch]$KeepWork,
    [ValidateRange(0, 2147483)][int]$TimeoutSeconds = 0
)

$ErrorActionPreference = 'Stop'
$arguments = @{
    DoFile = Join-Path $PSScriptRoot 'run_gate_regression.do'
    Simulator = $Simulator
    WaveMode = $WaveMode
    KeepWork = $KeepWork
    TimeoutSeconds = $TimeoutSeconds
}
foreach ($name in @('VsimPath', 'LicenseFile', 'LicenseServer', 'BuildRoot', 'RunId')) {
    $value = Get-Variable -Name $name -ValueOnly
    if (-not [string]::IsNullOrWhiteSpace($value)) { $arguments[$name] = $value }
}
& (Join-Path (Split-Path -Parent $PSScriptRoot) 'Invoke-Simulation.ps1') @arguments
