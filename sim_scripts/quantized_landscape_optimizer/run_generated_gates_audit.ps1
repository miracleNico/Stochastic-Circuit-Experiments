[CmdletBinding()]
param(
    [ValidateSet('Questa', 'ModelSim')][string]$Simulator = 'Questa',
    [string]$VsimPath = '',
    [string]$LicenseFile = '',
    [string]$LicenseServer = '',
    [string]$BuildRoot = '',
    [string]$RunId = '',
    [ValidateSet('None', 'Top', 'All')][string]$WaveMode = 'None',
    [switch]$KeepWork,
    [ValidateRange(0, 2147483)][int]$TimeoutSeconds = 180,
    [string]$PythonPath = '',
    [switch]$PassThru
)

$ErrorActionPreference = 'Stop'
$experimentRoot = $PSScriptRoot
$repoRoot = [IO.Path]::GetFullPath((Join-Path $experimentRoot '..\..'))
$invokeSimulation = Join-Path $repoRoot 'sim_scripts\Invoke-Simulation.ps1'
$doFile = Join-Path $experimentRoot 'generated_gates_audit.do'
$verifier = Join-Path $repoRoot 'scripts/quantized_landscape_optimizer/verify_questa_evidence.py'

if ([string]::IsNullOrWhiteSpace($BuildRoot)) {
    $BuildRoot = Join-Path $repoRoot 'results_and_reports/quantized_landscape_optimizer/runs'
}

function Resolve-PythonExecutable {
    param([string]$RequestedPath)

    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        $resolved = [IO.Path]::GetFullPath($RequestedPath)
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw "Python executable not found at $resolved"
        }
        return $resolved
    }
    if (-not [string]::IsNullOrWhiteSpace($env:PYTHON) -and
        (Test-Path -LiteralPath $env:PYTHON -PathType Leaf)) {
        return [IO.Path]::GetFullPath($env:PYTHON)
    }
    $projectPython = Join-Path $repoRoot '.venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $projectPython -PathType Leaf) { return $projectPython }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($null -ne $command) { return $command.Source }

    $codexRuntime = Join-Path $env:USERPROFILE '.cache\codex-runtimes'
    if (Test-Path -LiteralPath $codexRuntime -PathType Container) {
        $candidate = Get-ChildItem -LiteralPath $codexRuntime -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName 'dependencies\python\python.exe' } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
            Select-Object -First 1
        if ($null -ne $candidate) { return [IO.Path]::GetFullPath($candidate) }
    }
    throw 'Python 3 was not found; pass -PythonPath or set the process-only PYTHON variable.'
}

$python = Resolve-PythonExecutable -RequestedPath $PythonPath
$simulationArguments = @{
    DoFile = $doFile
    Simulator = $Simulator
    BuildRoot = [IO.Path]::GetFullPath($BuildRoot)
    WaveMode = $WaveMode
    KeepWork = $KeepWork
    TimeoutSeconds = $TimeoutSeconds
    PassThru = $true
}
foreach ($name in @('VsimPath', 'LicenseFile', 'LicenseServer', 'RunId')) {
    $value = Get-Variable -Name $name -ValueOnly
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        $simulationArguments[$name] = $value
    }
}

$result = & $invokeSimulation @simulationArguments
if ($null -eq $result -or $result.ExitCode -ne 0) {
    $detail = if ($null -ne $result -and $null -ne $result.Error) {
        [string]$result.Error
    }
    else {
        'simulation runner returned no successful result'
    }
    throw "Generated-gates simulation failed: $detail"
}

$evidenceDirectory = Join-Path $result.RunDirectory 'raw\generated-gates-audit'
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
$verificationJson = Join-Path $evidenceDirectory 'verification.json'
& $python $verifier `
    --kind generated-gates `
    --transcript $result.TranscriptPath `
    --json-out $verificationJson | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Generated-gates transcript verification failed with exit code $LASTEXITCODE"
}

if ($PassThru) {
    [pscustomobject]@{
        ExitCode = $result.ExitCode
        Status = $result.Status
        RunDirectory = $result.RunDirectory
        TranscriptPath = $result.TranscriptPath
        MetadataPath = $result.MetadataPath
        WavePath = $result.WavePath
        VerificationPath = $verificationJson
    }
}
else {
    Write-Host "generated-gates Questa audit passed: $($result.RunDirectory)"
}
