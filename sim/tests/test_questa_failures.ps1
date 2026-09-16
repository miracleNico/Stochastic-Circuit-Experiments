[CmdletBinding()]
param(
    [string]$VsimPath = '',
    [string]$LicenseFile = '',
    [string]$LicenseServer = '',
    [string]$BuildRoot = '',
    [ValidateRange(1, 600)][int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'
$simDir = Split-Path -Parent $PSScriptRoot
$invoke = Join-Path $simDir 'Invoke-Simulation.ps1'
if ([string]::IsNullOrWhiteSpace($BuildRoot)) {
    $repoRoot = Split-Path -Parent $simDir
    $BuildRoot = Join-Path $repoRoot '.sim_build\failure-smoke'
}

$common = @{
    Simulator = 'Questa'
    BuildRoot = $BuildRoot
    WaveMode = 'None'
    KeepWork = $true
    TimeoutSeconds = $TimeoutSeconds
    PassThru = $true
}
foreach ($name in @('VsimPath','LicenseFile','LicenseServer')) {
    $value = Get-Variable -Name $name -ValueOnly
    if (-not [string]::IsNullOrWhiteSpace($value)) { $common[$name] = $value }
}

$cases = @(
    @{ Name = 'compile'; Do = 'compile_failure.do'; Expected = 50 },
    @{ Name = 'elaboration'; Do = 'elaboration_failure.do'; Expected = 51 },
    @{ Name = 'assertion'; Do = 'assertion_failure.do'; Expected = 52 }
)
$nonce = [guid]::NewGuid().ToString('N').Substring(0, 8)
foreach ($case in $cases) {
    $arguments = $common.Clone()
    $arguments.DoFile = Join-Path $PSScriptRoot "fixtures\$($case.Do)"
    $arguments.RunId = "failure-smoke-$($case.Name)-$nonce"
    $result = & $invoke @arguments
    if ($result.ExitCode -ne $case.Expected) {
        throw "$($case.Name) failure returned $($result.ExitCode), expected $($case.Expected). Transcript: $($result.TranscriptPath)"
    }
    if (-not (Test-Path -LiteralPath $result.TranscriptPath -PathType Leaf)) {
        throw "$($case.Name) failure did not retain its transcript."
    }
    Write-Host ("Questa {0} failure classified correctly as {1}." -f $case.Name, $case.Expected)
}

Write-Host 'Real Questa failure smoke tests passed.'
