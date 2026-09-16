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
    [ValidateRange(0, 2147483)][int]$TimeoutSeconds = 120,
    [string]$PythonPath = '',
    [switch]$PassThru
)

$ErrorActionPreference = 'Stop'
$experimentRoot = $PSScriptRoot
$repoRoot = [IO.Path]::GetFullPath((Join-Path $experimentRoot '..\..'))
$invokeSimulation = Join-Path $repoRoot 'sim\Invoke-Simulation.ps1'
$doFile = Join-Path $experimentRoot 'questa_energy_audit.do'
$optimizer = Join-Path $experimentRoot 'generic_optimizer.py'
$exporter = Join-Path $experimentRoot 'export_vhdl_coefficients.py'
$verifier = Join-Path $experimentRoot 'verify_questa_evidence.py'
$rtlSource = Join-Path $repoRoot 'src\generated_networks.vhd'

if ([string]::IsNullOrWhiteSpace($BuildRoot)) {
    $BuildRoot = Join-Path $repoRoot '.sim_build'
}
$BuildRoot = [IO.Path]::GetFullPath($BuildRoot)

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

function Invoke-PythonChecked {
    param(
        [Parameter(Mandatory)][string]$Executable,
        [Parameter(Mandatory)][string[]]$Arguments,
        [switch]$DiscardOutput
    )
    if ($DiscardOutput) { & $Executable @Arguments | Out-Null }
    else { & $Executable @Arguments }
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

$python = Resolve-PythonExecutable -RequestedPath $PythonPath
$inputParent = Join-Path $BuildRoot '_optimizer_audit_inputs'
$inputDirectory = Join-Path $inputParent ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $inputDirectory -Force | Out-Null
$haJson = Join-Path $inputDirectory 'ha_optimizer.json'
$faJson = Join-Path $inputDirectory 'fa_optimizer.json'
$coefficientPackage = Join-Path $inputDirectory 'optimizer_coefficients_pkg.vhd'
$result = $null

$previousPackage = [Environment]::GetEnvironmentVariable(
    'OPTIMIZER_COEFFICIENT_PACKAGE',
    'Process'
)
$hadPreviousPackage = $null -ne $previousPackage

try {
    Invoke-PythonChecked -Executable $python -DiscardOutput -Arguments @(
        $optimizer, 'demo-gate', '--gate', 'ha', '--json-out', $haJson
    )
    Invoke-PythonChecked -Executable $python -DiscardOutput -Arguments @(
        $optimizer, 'demo-gate', '--gate', 'fa', '--json-out', $faJson
    )
    Invoke-PythonChecked -Executable $python -DiscardOutput -Arguments @(
        $exporter,
        '--ha-json', $haJson,
        '--fa-json', $faJson,
        '--rtl-source', $rtlSource,
        '--output', $coefficientPackage
    )

    [Environment]::SetEnvironmentVariable(
        'OPTIMIZER_COEFFICIENT_PACKAGE',
        $coefficientPackage,
        'Process'
    )
    $simulationArguments = @{
        DoFile = $doFile
        Simulator = $Simulator
        BuildRoot = $BuildRoot
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
        throw "Optimizer energy audit simulation failed: $detail"
    }

    $evidenceDirectory = Join-Path $result.RunDirectory 'raw\optimizer-audit'
    New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null
    Copy-Item -LiteralPath $haJson -Destination $evidenceDirectory
    Copy-Item -LiteralPath $faJson -Destination $evidenceDirectory
    Copy-Item -LiteralPath $coefficientPackage -Destination $evidenceDirectory
    $verificationJson = Join-Path $evidenceDirectory 'verification.json'
    Invoke-PythonChecked -Executable $python -DiscardOutput -Arguments @(
        $verifier,
        '--kind', 'static',
        '--transcript', $result.TranscriptPath,
        '--json-out', $verificationJson
    )

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
        Write-Host "optimizer Questa audit passed: $($result.RunDirectory)"
    }
}
catch {
    $failedRunDirectory = $null
    if ($null -ne $result) { $failedRunDirectory = $result.RunDirectory }
    elseif ($_.Exception.Data.Contains('RunDirectory')) {
        $failedRunDirectory = [string]$_.Exception.Data['RunDirectory']
    }
    if (-not [string]::IsNullOrWhiteSpace($failedRunDirectory) -and
        (Test-Path -LiteralPath $failedRunDirectory -PathType Container)) {
        $failedEvidence = Join-Path $failedRunDirectory 'raw\optimizer-audit'
        New-Item -ItemType Directory -Path $failedEvidence -Force | Out-Null
        foreach ($artifact in @($haJson, $faJson, $coefficientPackage)) {
            if (Test-Path -LiteralPath $artifact -PathType Leaf) {
                Copy-Item -LiteralPath $artifact -Destination $failedEvidence -Force
            }
        }
    }
    throw
}
finally {
    if ($hadPreviousPackage) {
        [Environment]::SetEnvironmentVariable(
            'OPTIMIZER_COEFFICIENT_PACKAGE',
            $previousPackage,
            'Process'
        )
    }
    else {
        [Environment]::SetEnvironmentVariable(
            'OPTIMIZER_COEFFICIENT_PACKAGE',
            $null,
            'Process'
        )
    }

    $resolvedInputParent = [IO.Path]::GetFullPath($inputParent).TrimEnd('\') + '\'
    $resolvedInputDirectory = [IO.Path]::GetFullPath($inputDirectory)
    if ($resolvedInputDirectory.StartsWith(
        $resolvedInputParent,
        [StringComparison]::OrdinalIgnoreCase
    ) -and (Test-Path -LiteralPath $resolvedInputDirectory -PathType Container)) {
        Remove-Item -LiteralPath $resolvedInputDirectory -Recurse -Force
    }
}
