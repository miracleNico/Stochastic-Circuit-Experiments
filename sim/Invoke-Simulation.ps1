[CmdletBinding()]
param(
    [string]$DoFile = '',
    [string]$Simulator = 'Questa',
    [string]$VsimPath = '',
    [string]$LicenseFile = '',
    [string]$LicenseServer = '',
    [string]$BuildRoot = '',
    [string]$RunId = '',
    [string]$WaveMode = 'None',
    [switch]$KeepWork,
    [int]$TimeoutSeconds = 0,
    [switch]$Gui,
    [switch]$Detach,
    [switch]$PassThru
)

$ErrorActionPreference = 'Stop'
$modulePath = Join-Path $PSScriptRoot 'Simulator.psm1'
Import-Module $modulePath -Force

$argumentError = if ([string]::IsNullOrWhiteSpace($DoFile)) { 'A do-file is required.' }
    elseif ($Simulator -notin @('Questa', 'ModelSim')) { 'Simulator must be Questa or ModelSim.' }
    elseif ($WaveMode -notin @('None', 'Top', 'All')) { 'WaveMode must be None, Top or All.' }
    elseif ($TimeoutSeconds -lt 0 -or $TimeoutSeconds -gt 2147483) { 'TimeoutSeconds is out of range.' }
    elseif (-not [string]::IsNullOrWhiteSpace($LicenseFile) -and -not [string]::IsNullOrWhiteSpace($LicenseServer)) { 'Select only one license source.' }
    elseif (-not [string]::IsNullOrWhiteSpace($RunId) -and $RunId.Trim() -match '^\.+$') { "RunId cannot be '.' or '..'." }
    else { $null }
if ($null -ne $argumentError) {
    $result = [pscustomobject]@{ ExitCode = 10; NativeExitCode = $null; Status = 'invalid-arguments'; RunDirectory = $null; MetadataPath = $null; TranscriptPath = $null; WavePath = $null; Error = $argumentError }
    if ($PassThru) { $result; return }
    [Console]::Error.WriteLine($argumentError)
    exit 10
}

$arguments = @{
    DoFile = $DoFile
    Simulator = $Simulator
    WaveMode = $WaveMode
    KeepWork = $KeepWork
    TimeoutSeconds = $TimeoutSeconds
    Gui = $Gui
    Detach = $Detach
}
foreach ($name in @('VsimPath', 'LicenseFile', 'LicenseServer', 'BuildRoot', 'RunId')) {
    $value = Get-Variable -Name $name -ValueOnly
    if (-not [string]::IsNullOrWhiteSpace($value)) { $arguments[$name] = $value }
}

try {
    $result = Invoke-HdlSimulation @arguments
}
catch {
    $message = $_.Exception.Message
    $code = if ($message -match '(?i)^The explicitly selected license file|^License server must use|^Multiple Mentor license files') { 30 }
        elseif ($message -match '(?i)^Unable to initialize simulation run directory|^No simulator modelsim\.ini could be located') { 40 }
        elseif ($message -match '(?i)^The explicit simulator executable does not exist|^Requested (?:Questa|legacy ModelSim), but|^(?:Questa|ModelSim) executable was not found using the configured precedence|^Simulator executable not found at|^Simulator at .+ did not report a version') { 20 }
        else { 10 }
    $result = [pscustomobject]@{
        ExitCode = $code
        NativeExitCode = $null
        Status = 'preflight-failure'
        RunDirectory = $null
        MetadataPath = $null
        TranscriptPath = $null
        WavePath = $null
        Error = $message
    }
}

if ($PassThru) {
    $result
    return
}
if ($result.ExitCode -ne 0) {
    [Console]::Error.WriteLine(("Simulation failed with status '{0}' (exit code {1})." -f $result.Status, $result.ExitCode))
    exit $result.ExitCode
}
