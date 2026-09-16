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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
Import-Module (Join-Path $scriptDir 'Simulator.psm1') -Force
$python = Resolve-ProjectPython

$effectiveBuildRoot = if ([string]::IsNullOrWhiteSpace($BuildRoot)) { Join-Path $root '.sim_build' } else { $BuildRoot }
if (-not [string]::IsNullOrWhiteSpace($RunId) -and $RunId.Trim() -match '^\.+$') {
    [Console]::Error.WriteLine("RunId cannot be '.' or '..'.")
    exit 10
}
$effectiveRunId = if ([string]::IsNullOrWhiteSpace($RunId)) {
    '{0}-{1}-{2}' -f ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')), $PID, ([guid]::NewGuid().ToString('N').Substring(0, 8))
} else { $RunId }
$safeRunId = $effectiveRunId -replace '[^A-Za-z0-9_.-]', '_'
$buildRootFull = [IO.Path]::GetFullPath($effectiveBuildRoot)
$aggregateCaseRoot = [IO.Path]::GetFullPath((Join-Path $buildRootFull (Join-Path $Simulator.ToLowerInvariant() 'run_all_traces')))
$aggregateRunDirectory = [IO.Path]::GetFullPath((Join-Path $aggregateCaseRoot $safeRunId))
$casePrefix = $aggregateCaseRoot.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
if (-not $aggregateRunDirectory.StartsWith($casePrefix, [StringComparison]::OrdinalIgnoreCase)) {
    [Console]::Error.WriteLine('RunId resolves outside its trace-aggregation directory.')
    exit 10
}
try {
    New-Item -ItemType Directory -Path $aggregateCaseRoot -Force -ErrorAction Stop | Out-Null
    New-Item -ItemType Directory -Path $aggregateRunDirectory -ErrorAction Stop | Out-Null
    $aggregateRaw = New-Item -ItemType Directory -Path (Join-Path $aggregateRunDirectory 'raw') -ErrorAction Stop
}
catch {
    [Console]::Error.WriteLine("Unable to initialize trace-aggregation directory '$aggregateRunDirectory': $($_.Exception.Message)")
    exit 40
}

$aggregateMetadataPath = Join-Path $aggregateRunDirectory 'metadata.json'
$aggregateMetadata = [ordered]@{
    schemaVersion = 1
    kind = 'trace-aggregation'
    simulator = $Simulator
    simulatorVersion = $null
    executable = $null
    case = 'run_all_traces'
    runDirectory = $aggregateRunDirectory
    startedUtc = [DateTime]::UtcNow.ToString('o')
    finishedUtc = $null
    status = 'starting'
    exitCode = $null
    children = @()
    artifacts = [ordered]@{}
}
$aggregateMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $aggregateMetadataPath -Encoding utf8NoBOM

$childArguments = @(
    '-Simulator', $Simulator,
    '-WaveMode', $WaveMode,
    '-TimeoutSeconds', [string]$TimeoutSeconds,
    '-BuildRoot', $buildRootFull,
    '-RunId', $effectiveRunId
)
if ($KeepWork) { $childArguments += '-KeepWork' }
foreach ($name in @('VsimPath', 'LicenseFile', 'LicenseServer')) {
    $value = Get-Variable -Name $name -ValueOnly
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        $childArguments += "-$name"
        $childArguments += $value
    }
}

$pwsh = Join-Path $PSHOME 'pwsh.exe'
& $pwsh -NoProfile -File (Join-Path $scriptDir 'run_and_trace.ps1') @childArguments
$andExitCode = $LASTEXITCODE
if ($andExitCode -ne 0) {
    $aggregateMetadata.status = 'and-trace-failure'
    $aggregateMetadata.exitCode = $andExitCode
    $aggregateMetadata.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $aggregateMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $aggregateMetadataPath -Encoding utf8NoBOM
    exit $andExitCode
}
& $pwsh -NoProfile -File (Join-Path $scriptDir 'run_xor_trace.ps1') @childArguments
$xorExitCode = $LASTEXITCODE
if ($xorExitCode -ne 0) {
    $aggregateMetadata.status = 'xor-trace-failure'
    $aggregateMetadata.exitCode = $xorExitCode
    $aggregateMetadata.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $aggregateMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $aggregateMetadataPath -Encoding utf8NoBOM
    exit $xorExitCode
}

$andRunDirectory = Join-Path $buildRootFull (Join-Path $Simulator.ToLowerInvariant() (Join-Path 'run_and_trace' $safeRunId))
$xorRunDirectory = Join-Path $buildRootFull (Join-Path $Simulator.ToLowerInvariant() (Join-Path 'run_xor_trace' $safeRunId))
$andMetadataPath = Join-Path $andRunDirectory 'metadata.json'
$xorMetadataPath = Join-Path $xorRunDirectory 'metadata.json'
$andMetadata = Get-Content -LiteralPath $andMetadataPath -Raw | ConvertFrom-Json
$aggregateMetadata.simulatorVersion = $andMetadata.simulatorVersion
$aggregateMetadata.executable = $andMetadata.executable
$aggregateMetadata.children = @($andMetadataPath, $xorMetadataPath)

$aggregateArtifacts = @(
    (Join-Path $aggregateRaw.FullName 'generated_gate_probability_summary.csv'),
    (Join-Path $aggregateRaw.FullName 'generated_gate_state_probabilities.csv'),
    (Join-Path $aggregateRaw.FullName 'generated_gate_ab_probabilities.csv'),
    (Join-Path $aggregateRaw.FullName 'generated_gate_probabilities.png')
)

& $python (Join-Path $root "scripts\plot_small_gate_probabilities.py") `
    --summary ($aggregateArtifacts[0]) `
    --states ($aggregateArtifacts[1]) `
    --ab ($aggregateArtifacts[2]) `
    --plot ($aggregateArtifacts[3])
if ($LASTEXITCODE -ne 0) {
    $aggregateMetadata.status = 'aggregate-plot-failure'
    $aggregateMetadata.exitCode = 53
    $aggregateMetadata.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $aggregateMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $aggregateMetadataPath -Encoding utf8NoBOM
    [Console]::Error.WriteLine("Aggregate trace plotter returned exit code $LASTEXITCODE")
    exit 53
}

$missingAggregateArtifacts = @($aggregateArtifacts | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })
if ($missingAggregateArtifacts.Count -gt 0) {
    $aggregateMetadata.status = 'missing-derived-artifact'
    $aggregateMetadata.exitCode = 70
    $aggregateMetadata.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $aggregateMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $aggregateMetadataPath -Encoding utf8NoBOM
    [Console]::Error.WriteLine('Aggregate trace plotter did not create every required artifact.')
    exit 70
}

$aggregateMetadata.status = 'passed'
$aggregateMetadata.exitCode = 0
$aggregateMetadata.finishedUtc = [DateTime]::UtcNow.ToString('o')
$aggregateMetadata.artifacts['derived'] = $aggregateArtifacts
$aggregateMetadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $aggregateMetadataPath -Encoding utf8NoBOM
