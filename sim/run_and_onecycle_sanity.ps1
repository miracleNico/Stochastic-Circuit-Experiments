param(
    [int]$Trials = -1,
    [int]$ScrambleCycles = -1,
    [int]$PrimeInputCycles = -1,
    [int]$SolveCycles = -1,
    [int]$RndWeight = -1,
    [int]$FieldFracBits = -1,
    [int]$BiasA = 999999,
    [int]$BiasB = 999999,
    [int]$BiasY = 999999,
    [int]$JAb = 999999,
    [int]$JAy = 999999,
    [int]$JBy = 999999,
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
    $result = & (Join-Path $scriptDir 'Invoke-Simulation.ps1') @invokeArguments
    if ($result.ExitCode -ne 0) {
        [Console]::Error.WriteLine("$Simulator simulation failed with exit code $($result.ExitCode). See $($result.TranscriptPath)")
        exit $result.ExitCode
    }
    return $result
}

Push-Location $scriptDir
try {
    $oldTrials = $env:TRIALS
    if ($Trials -ge 0) { $env:TRIALS = [string]$Trials }

    $oldScrambleCycles = $env:SCRAMBLE_CYCLES
    if ($ScrambleCycles -ge 0) { $env:SCRAMBLE_CYCLES = [string]$ScrambleCycles }

    $oldPrimeInputCycles = $env:PRIME_INPUT_CYCLES
    if ($PrimeInputCycles -ge 0) { $env:PRIME_INPUT_CYCLES = [string]$PrimeInputCycles }

    $oldSolveCycles = $env:SOLVE_CYCLES
    if ($SolveCycles -ge 0) { $env:SOLVE_CYCLES = [string]$SolveCycles }

    $oldRndWeight = $env:RND_WEIGHT
    if ($RndWeight -ge 0) { $env:RND_WEIGHT = [string]$RndWeight }

    $oldFieldFracBits = $env:FIELD_FRAC_BITS
    if ($FieldFracBits -ge 0) { $env:FIELD_FRAC_BITS = [string]$FieldFracBits }

    $oldBiasA = $env:BIAS_A
    if ($BiasA -ne 999999) { $env:BIAS_A = [string]$BiasA }

    $oldBiasB = $env:BIAS_B
    if ($BiasB -ne 999999) { $env:BIAS_B = [string]$BiasB }

    $oldBiasY = $env:BIAS_Y
    if ($BiasY -ne 999999) { $env:BIAS_Y = [string]$BiasY }

    $oldJAb = $env:J_AB
    if ($JAb -ne 999999) { $env:J_AB = [string]$JAb }

    $oldJAy = $env:J_AY
    if ($JAy -ne 999999) { $env:J_AY = [string]$JAy }

    $oldJBy = $env:J_BY
    if ($JBy -ne 999999) { $env:J_BY = [string]$JBy }

    $simulationResult = Invoke-ConfiguredSimulation -DoFile (Join-Path $scriptDir run_and_onecycle_sanity.do)
}
finally {
    if ($null -eq $oldTrials) { Remove-Item Env:\TRIALS -ErrorAction SilentlyContinue } else { $env:TRIALS = $oldTrials }
    if ($null -eq $oldScrambleCycles) { Remove-Item Env:\SCRAMBLE_CYCLES -ErrorAction SilentlyContinue } else { $env:SCRAMBLE_CYCLES = $oldScrambleCycles }
    if ($null -eq $oldPrimeInputCycles) { Remove-Item Env:\PRIME_INPUT_CYCLES -ErrorAction SilentlyContinue } else { $env:PRIME_INPUT_CYCLES = $oldPrimeInputCycles }
    if ($null -eq $oldSolveCycles) { Remove-Item Env:\SOLVE_CYCLES -ErrorAction SilentlyContinue } else { $env:SOLVE_CYCLES = $oldSolveCycles }
    if ($null -eq $oldRndWeight) { Remove-Item Env:\RND_WEIGHT -ErrorAction SilentlyContinue } else { $env:RND_WEIGHT = $oldRndWeight }
    if ($null -eq $oldFieldFracBits) { Remove-Item Env:\FIELD_FRAC_BITS -ErrorAction SilentlyContinue } else { $env:FIELD_FRAC_BITS = $oldFieldFracBits }
    if ($null -eq $oldBiasA) { Remove-Item Env:\BIAS_A -ErrorAction SilentlyContinue } else { $env:BIAS_A = $oldBiasA }
    if ($null -eq $oldBiasB) { Remove-Item Env:\BIAS_B -ErrorAction SilentlyContinue } else { $env:BIAS_B = $oldBiasB }
    if ($null -eq $oldBiasY) { Remove-Item Env:\BIAS_Y -ErrorAction SilentlyContinue } else { $env:BIAS_Y = $oldBiasY }
    if ($null -eq $oldJAb) { Remove-Item Env:\J_AB -ErrorAction SilentlyContinue } else { $env:J_AB = $oldJAb }
    if ($null -eq $oldJAy) { Remove-Item Env:\J_AY -ErrorAction SilentlyContinue } else { $env:J_AY = $oldJAy }
    if ($null -eq $oldJBy) { Remove-Item Env:\J_BY -ErrorAction SilentlyContinue } else { $env:J_BY = $oldJBy }
    Pop-Location
}
