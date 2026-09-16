param(
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

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$scriptDir = Join-Path $root "sim"
$plotter = Join-Path $root "scripts\plot_and_trace.py"
Import-Module (Join-Path $scriptDir 'Simulator.psm1') -Force
$python = Resolve-ProjectPython
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
    $result = & (Join-Path $scriptDir 'Invoke-Simulation.ps1') @invokeArguments
    if ($result.ExitCode -ne 0) {
        [Console]::Error.WriteLine("$Simulator simulation failed with exit code $($result.ExitCode). See $($result.TranscriptPath)")
        exit $result.ExitCode
    }
    return $result
}

Push-Location $scriptDir
try {
    $simulationResult = Invoke-ConfiguredSimulation -DoFile (Join-Path $scriptDir run_and_trace.do)
}
finally {
    Pop-Location
}

$rawDirectory = Join-Path $simulationResult.RunDirectory 'raw'
$derivedArtifacts = @(
    (Join-Path $rawDirectory 'and_trace.png'),
    (Join-Path $rawDirectory 'and_trace_summary.csv'),
    (Join-Path $rawDirectory 'and_state_probabilities.csv'),
    (Join-Path $rawDirectory 'and_ab_probabilities.csv')
)

& $python $plotter `
    --gate and `
    --input (Join-Path $rawDirectory 'and_trace.csv') `
    --plot ($derivedArtifacts[0]) `
    --summary ($derivedArtifacts[1]) `
    --probabilities ($derivedArtifacts[2]) `
    --ab-probabilities ($derivedArtifacts[3])
$plotExitCode = $LASTEXITCODE
$metadata = Get-Content -LiteralPath $simulationResult.MetadataPath -Raw | ConvertFrom-Json -AsHashtable
if ($plotExitCode -ne 0) {
    $metadata.status = 'trace-postprocess-failure'
    $metadata.exitCode = 53
    $metadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $simulationResult.MetadataPath -Encoding utf8NoBOM
    [Console]::Error.WriteLine("Trace plotter returned exit code $plotExitCode")
    exit 53
}
$missingDerived = @($derivedArtifacts | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($missingDerived.Count -gt 0) {
    $metadata.status = 'missing-derived-artifact'
    $metadata.exitCode = 70
    $metadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $simulationResult.MetadataPath -Encoding utf8NoBOM
    [Console]::Error.WriteLine('Trace plotter did not create every required derived artifact.')
    exit 70
}
$metadata.artifacts['derived'] = $derivedArtifacts
$metadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $simulationResult.MetadataPath -Encoding utf8NoBOM
