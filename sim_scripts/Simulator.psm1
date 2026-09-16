Set-StrictMode -Version Latest

$script:ExitCodes = [ordered]@{
    Success           = 0
    InvalidArguments  = 10
    ToolNotFound      = 20
    LicenseFailure    = 30
    RunDirectory      = 40
    CompileFailure    = 50
    ElaborationFailure = 51
    AssertionFailure  = 52
    RuntimeFailure    = 53
    ProcessFailure    = 54
    Timeout           = 60
    MissingArtifact   = 70
}

function Get-SimulationExitCodes {
    [CmdletBinding()]
    param()
    return $script:ExitCodes.Clone()
}

function ConvertTo-TclPath {
    param([Parameter(Mandatory)][string]$Path)
    return ([IO.Path]::GetFullPath($Path) -replace '\\', '/')
}

function Get-SimulatorVersion {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Executable)

    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) {
        throw "Simulator executable not found at $Executable"
    }

    $versionLines = @(& $Executable -version 2>&1)
    $version = ($versionLines | ForEach-Object { $_.ToString() }) -join "`n"
    if ([string]::IsNullOrWhiteSpace($version)) {
        throw "Simulator at $Executable did not report a version"
    }
    return $version.Trim()
}

function Resolve-ProjectPython {
    [CmdletBinding()]
    param()

    $candidates = [Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrWhiteSpace($env:PYTHON)) { [void]$candidates.Add($env:PYTHON) }
    [void]$candidates.Add((Join-Path (Split-Path -Parent $PSScriptRoot) '.venv/Scripts/python.exe'))
    $pathPython = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pathPython) { [void]$candidates.Add($pathPython.Source) }
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        [void]$candidates.Add((Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'))
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        $expanded = [Environment]::ExpandEnvironmentVariables($candidate)
        if (Test-Path -LiteralPath $expanded -PathType Leaf) { return [IO.Path]::GetFullPath($expanded) }
    }
    throw 'Python was not found via PYTHON, the project .venv, PATH, or the bundled Codex runtime.'
}

function Test-SimulatorIdentity {
    param(
        [Parameter(Mandatory)][ValidateSet('Questa', 'ModelSim')][string]$Simulator,
        [Parameter(Mandatory)][string]$Executable
    )

    $version = Get-SimulatorVersion -Executable $Executable
    if ($Simulator -eq 'Questa' -and $version -notmatch '(?i)Questa') {
        throw "Requested Questa, but '$Executable' reports: $($version -replace "`n", ' ')"
    }
    if ($Simulator -eq 'ModelSim' -and $version -notmatch '(?i)ModelSim') {
        throw "Requested legacy ModelSim, but '$Executable' reports: $($version -replace "`n", ' ')"
    }
    return $version
}

function Resolve-SimulatorExecutable {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][ValidateSet('Questa', 'ModelSim')][string]$Simulator,
        [string]$VsimPath = ''
    )

    $candidates = [Collections.Generic.List[string]]::new()
    function Add-Candidate([string]$Candidate) {
        if ([string]::IsNullOrWhiteSpace($Candidate)) { return }
        $expanded = [Environment]::ExpandEnvironmentVariables($Candidate)
        if (Test-Path -LiteralPath $expanded -PathType Container) {
            $direct = Join-Path $expanded 'vsim.exe'
            $win64 = Join-Path $expanded 'win64\vsim.exe'
            if (Test-Path -LiteralPath $direct -PathType Leaf) { $expanded = $direct }
            elseif (Test-Path -LiteralPath $win64 -PathType Leaf) { $expanded = $win64 }
            else { $expanded = $direct }
        }
        if (-not $candidates.Contains($expanded)) { [void]$candidates.Add($expanded) }
    }

    if (-not [string]::IsNullOrWhiteSpace($VsimPath)) {
        $explicit = [Environment]::ExpandEnvironmentVariables($VsimPath)
        if (Test-Path -LiteralPath $explicit -PathType Container) {
            $direct = Join-Path $explicit 'vsim.exe'
            $win64 = Join-Path $explicit 'win64\vsim.exe'
            if (Test-Path -LiteralPath $direct -PathType Leaf) { $explicit = $direct }
            elseif (Test-Path -LiteralPath $win64 -PathType Leaf) { $explicit = $win64 }
            else { $explicit = $direct }
        }
        if (-not (Test-Path -LiteralPath $explicit -PathType Leaf)) {
            throw 'The explicit simulator executable does not exist.'
        }
        $version = Test-SimulatorIdentity -Simulator $Simulator -Executable $explicit
        return [pscustomobject]@{ Simulator = $Simulator; Executable = [IO.Path]::GetFullPath($explicit); Version = $version }
    }
    if ($Simulator -eq 'Questa') {
        Add-Candidate $env:QUESTA_HOME
    }
    else {
        Add-Candidate $env:MODELSIM_HOME
    }

    $pathCommand = Get-Command vsim.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pathCommand) { Add-Candidate $pathCommand.Source }

    if ($Simulator -eq 'Questa') {
        $installRoots = @(Get-ChildItem -LiteralPath 'C:\' -Directory -Filter 'questasim64_*' -ErrorAction SilentlyContinue |
            ForEach-Object {
                $parsed = [version]'0.0'
                if ($_.Name -match '(\d+(?:\.\d+)+)') { [void][version]::TryParse($Matches[1], [ref]$parsed) }
                [pscustomobject]@{ Directory = $_; Version = $parsed }
            } | Sort-Object Version -Descending | Select-Object -ExpandProperty Directory)
        foreach ($root in $installRoots) { Add-Candidate (Join-Path $root.FullName 'win64\vsim.exe') }
    }
    else {
        Add-Candidate 'C:\intelFPGA_lite\modelsim_ase\win32aloem\vsim.exe'
        Add-Candidate 'C:\intelFPGA\modelsim_ase\win32aloem\vsim.exe'
    }

    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        # Precedence is authoritative: once a candidate exists, a product
        # mismatch is a configuration error rather than permission to search
        # a lower-priority location.
        $version = Test-SimulatorIdentity -Simulator $Simulator -Executable $candidate
        return [pscustomobject]@{
            Simulator  = $Simulator
            Executable = [IO.Path]::GetFullPath($candidate)
            Version    = $version
        }
    }

    throw "$Simulator executable was not found using the configured precedence."
}

function Resolve-SimulatorLicense {
    [CmdletBinding()]
    param(
        [string]$LicenseFile = '',
        [string]$LicenseServer = ''
    )

    if (-not [string]::IsNullOrWhiteSpace($LicenseFile) -and -not [string]::IsNullOrWhiteSpace($LicenseServer)) {
        throw 'Specify only one of -LicenseFile or -LicenseServer.'
    }
    if (-not [string]::IsNullOrWhiteSpace($LicenseFile)) {
        if (-not (Test-Path -LiteralPath $LicenseFile -PathType Leaf)) {
            throw 'The explicitly selected license file does not exist.'
        }
        return [pscustomobject]@{ Kind = 'File'; Value = [IO.Path]::GetFullPath($LicenseFile); Source = 'Argument' }
    }
    if (-not [string]::IsNullOrWhiteSpace($LicenseServer)) {
        if ($LicenseServer -notmatch '^\d+@[^\s@]+$') {
            throw "License server must use the form <port>@<host>."
        }
        return [pscustomobject]@{ Kind = 'Server'; Value = $LicenseServer; Source = 'Argument' }
    }

    foreach ($name in @('SALT_LICENSE_SERVER', 'MGLS_LICENSE_FILE', 'LM_LICENSE_FILE')) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return [pscustomobject]@{ Kind = 'Inherited'; Value = $value; Source = $name }
        }
    }

    $roots = @(
        if ($env:APPDATA) { Join-Path $env:APPDATA 'MentorGraphics' }
        if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'MentorGraphics' }
        if ($env:ProgramData) { Join-Path $env:ProgramData 'MentorGraphics' }
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Container) } | Select-Object -Unique

    $files = @($roots | ForEach-Object {
        Get-ChildItem -LiteralPath $_ -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq 'license.dat' -or $_.Extension -eq '.lic' } |
            Select-Object -ExpandProperty FullName
    } | Select-Object -Unique)

    if ($files.Count -eq 1) {
        return [pscustomobject]@{ Kind = 'File'; Value = $files[0]; Source = 'AutoDetected' }
    }
    if ($files.Count -gt 1) {
        throw "Multiple Mentor license files were found ($($files.Count)). Select one explicitly with -LicenseFile."
    }
    return $null
}

function New-SimulationIni {
    param(
        [Parameter(Mandatory)][string]$Executable,
        [Parameter(Mandatory)][string]$Destination
    )

    $bin = Split-Path -Parent $Executable
    $install = Split-Path -Parent $bin
    $sources = @(
        (Join-Path $install 'modelsim.ini'),
        (Join-Path $bin 'modelsim.ini')
    )
    $source = $sources | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if ($null -eq $source) { throw 'No simulator modelsim.ini could be located.' }

    Copy-Item -LiteralPath $source -Destination $Destination
    $destinationItem = Get-Item -LiteralPath $Destination
    if ($destinationItem.IsReadOnly) { $destinationItem.IsReadOnly = $false }
    $text = [IO.File]::ReadAllText($Destination)
    if ($text -match '(?m)^\s*Resolution\s*=.*$') {
        $text = [regex]::Replace($text, '(?m)^\s*Resolution\s*=.*$', 'Resolution = ps')
    }
    else { $text += "`r`nResolution = ps`r`n" }
    if ($text -match '(?m)^\s*BreakOnAssertion\s*=.*$') {
        $text = [regex]::Replace($text, '(?m)^\s*BreakOnAssertion\s*=.*$', 'BreakOnAssertion = 3')
    }
    else { $text += "BreakOnAssertion = 3`r`n" }
    [IO.File]::WriteAllText($Destination, $text, [Text.UTF8Encoding]::new($false))
    return [IO.Path]::GetFullPath($source)
}

function Get-RepositoryState {
    param([Parameter(Mandatory)][string]$RepoRoot)
    try {
        $commit = (& git -c "safe.directory=$($RepoRoot -replace '\\','/')" -C $RepoRoot rev-parse HEAD 2>$null).Trim()
        $status = @(& git -c "safe.directory=$($RepoRoot -replace '\\','/')" -C $RepoRoot status --porcelain 2>$null)
        return [ordered]@{ commit = $commit; dirty = ($status.Count -gt 0) }
    }
    catch { return [ordered]@{ commit = $null; dirty = $null } }
}

function Get-SourceHashes {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$DoFile
    )
    $paths = [Collections.Generic.List[string]]::new()
    [void]$paths.Add($DoFile)
    $common = Join-Path $RepoRoot 'sim_scripts\sim_common.do'
    if (Test-Path -LiteralPath $common) { [void]$paths.Add($common) }
    foreach ($folder in @('src', 'experiments', 'sim_scripts')) {
        $full = Join-Path $RepoRoot $folder
        if (Test-Path -LiteralPath $full) {
            Get-ChildItem -LiteralPath $full -Recurse -Filter '*.vhd' -File | ForEach-Object { [void]$paths.Add($_.FullName) }
        }
    }
    foreach ($name in @('GENERATED_NETWORKS_VHDL','GENERATED_SHADOW_VHDL','GENERATED_WINDOWED_VHDL','OPTIMIZER_COEFFICIENT_PACKAGE')) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ([string]::IsNullOrWhiteSpace($value)) { continue }
        $candidate = if ([IO.Path]::IsPathRooted($value)) {
            $value
        }
        elseif ($name -eq 'OPTIMIZER_COEFFICIENT_PACKAGE') {
            Join-Path $RepoRoot $value
        }
        else {
            Join-Path (Join-Path $RepoRoot 'sim_scripts') $value
        }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { [void]$paths.Add([IO.Path]::GetFullPath($candidate)) }
    }
    $result = [ordered]@{}
    foreach ($path in ($paths | Select-Object -Unique)) {
        $relative = [IO.Path]::GetRelativePath($RepoRoot, $path) -replace '\\', '/'
        $result[$relative] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    return $result
}

function Write-SimulationMetadata {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][System.Collections.IDictionary]$Metadata
    )
    $Metadata | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

function Invoke-HdlSimulation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$DoFile,
        [ValidateSet('Questa', 'ModelSim')][string]$Simulator = 'Questa',
        [string]$VsimPath = '',
        [string]$LicenseFile = '',
        [string]$LicenseServer = '',
        [string]$BuildRoot = '',
        [string]$RunId = '',
        [ValidateSet('None', 'Top', 'All')][string]$WaveMode = 'None',
        [switch]$KeepWork,
        [ValidateRange(0, 2147483)][int]$TimeoutSeconds = 0,
        [switch]$Gui,
        [switch]$Detach
    )

    $doPath = [IO.Path]::GetFullPath($DoFile)
    if (-not (Test-Path -LiteralPath $doPath -PathType Leaf)) {
        throw "Simulation do-file not found at $doPath"
    }
    $simDir = Split-Path -Parent $PSCommandPath
    $repoRoot = Split-Path -Parent $simDir
    $relativeDoPath = [IO.Path]::GetRelativePath($simDir, $doPath) -replace '\\', '/'
    $experiment = ($relativeDoPath -split '/')[0]
    if ($experiment -eq '..' -or -not (Test-Path -LiteralPath (Join-Path $repoRoot "experiments/$experiment/README.md") -PathType Leaf)) {
        $experiment = 'core_reproduction'
    }
    if ([string]::IsNullOrWhiteSpace($BuildRoot)) {
        $BuildRoot = Join-Path $repoRoot "results_and_reports/$experiment/runs"
    }
    $caseName = [IO.Path]::GetFileNameWithoutExtension($doPath)
    $safeCase = $caseName -replace '[^A-Za-z0-9_.-]', '_'
    if (-not [string]::IsNullOrWhiteSpace($RunId) -and $RunId.Trim() -match '^\.+$') {
        throw "RunId cannot be '.' or '..'."
    }
    $safeRunId = if ([string]::IsNullOrWhiteSpace($RunId)) {
        '{0}-{1}-{2}' -f ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')), $PID, ([guid]::NewGuid().ToString('N').Substring(0, 8))
    } else { $RunId -replace '[^A-Za-z0-9_.-]', '_' }
    $buildRootFull = [IO.Path]::GetFullPath($BuildRoot)
    $caseRoot = [IO.Path]::GetFullPath((Join-Path $buildRootFull (Join-Path $Simulator.ToLowerInvariant() $safeCase)))
    $runDirectory = [IO.Path]::GetFullPath((Join-Path $caseRoot $safeRunId))
    $casePrefix = $caseRoot.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $runDirectory.StartsWith($casePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'RunId resolves outside its simulation case directory.'
    }

    $tool = Resolve-SimulatorExecutable -Simulator $Simulator -VsimPath $VsimPath
    $license = Resolve-SimulatorLicense -LicenseFile $LicenseFile -LicenseServer $LicenseServer

    try {
        New-Item -ItemType Directory -Path $caseRoot -Force -ErrorAction Stop | Out-Null
        # Deliberately omit -Force for the leaf: exactly one concurrent caller
        # may claim a given RunId, while all others fail without sharing a work library.
        New-Item -ItemType Directory -Path $runDirectory -ErrorAction Stop | Out-Null
        New-Item -ItemType Directory -Path (Join-Path $runDirectory 'raw') -ErrorAction Stop | Out-Null
        $iniPath = Join-Path $runDirectory 'modelsim.ini'
        $vendorIni = New-SimulationIni -Executable $tool.Executable -Destination $iniPath
    }
    catch {
        throw "Unable to initialize simulation run directory '$runDirectory': $($_.Exception.Message)"
    }

    $metadataPath = Join-Path $runDirectory 'metadata.json'
    $transcriptPath = Join-Path $runDirectory 'transcript.log'
    $wavePath = Join-Path $runDirectory 'wave.wlf'
    $stdoutPath = Join-Path $runDirectory 'raw\stdout.log'
    $stderrPath = Join-Path $runDirectory 'raw\stderr.log'
    $experimentVariables = @(
        'GENERATED_NETWORKS_VHDL','GENERATED_SHADOW_VHDL','GENERATED_WINDOWED_VHDL','OPTIMIZER_COEFFICIENT_PACKAGE',
        'ACTIVE_RND_WEIGHT','ADDER_RND_WEIGHT','COMB_RND_WEIGHT','BLOCK_RND_WEIGHT','COLD_RND_WEIGHT','COPY_RND_WEIGHT',
        'FINAL_RND_WEIGHT','HOT_RND_WEIGHT','SCRAMBLE_RND_WEIGHT','RND_WEIGHT',
        'SCRAMBLE_CYCLES','SETTLE_CYCLES','COUNT_CYCLES','TRIALS','COPY_CYCLES','FINAL_CYCLES','WAVE_CYCLES',
        'WAVE0_CYCLES','WAVE1_CYCLES','WAVE2_CYCLES','WAVE3_CYCLES','BLOCK0_CYCLES','BLOCK1_CYCLES',
        'BLOCK2_CYCLES','BLOCK3_CYCLES','BLOCK4_CYCLES','BLOCK5_CYCLES','BLOCK6_CYCLES','BLOCK7_CYCLES',
        'COMB_SETTLE_CYCLES','COMB_COUNT_CYCLES','ADDER_SETTLE_CYCLES','ADDER_COUNT_CYCLES',
        'PRIME_INPUT_CYCLES','SOLVE_CYCLES','FIELD_FRAC_BITS','BIAS_A','BIAS_B','BIAS_Y','J_AB','J_AY','J_BY',
        'PARALLEL_MODE','REVERSE_COOL','REVERSE_ORDER','RUN_INVERSE','LEGACY_REPLAY_TIMING'
    )
    $parameters = [ordered]@{}
    foreach ($name in $experimentVariables) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($null -ne $value) { $parameters[$name] = $value }
    }
    $metadata = [ordered]@{
        schemaVersion = 1
        experiment = $experiment
        simulator = $Simulator
        simulatorVersion = $tool.Version.Split("`n")[0]
        executable = $tool.Executable
        case = $caseName
        doFile = [IO.Path]::GetRelativePath($repoRoot, $doPath) -replace '\\', '/'
        runDirectory = $runDirectory
        startedUtc = [DateTime]::UtcNow.ToString('o')
        finishedUtc = $null
        status = 'starting'
        exitCode = $null
        nativeExitCode = $null
        waveMode = $WaveMode
        timeoutSeconds = $TimeoutSeconds
        keepWork = [bool]$KeepWork
        detached = [bool]$Detach
        pending = $false
        vendorIni = $vendorIni
        repository = Get-RepositoryState -RepoRoot $repoRoot
        parameters = $parameters
        hashes = Get-SourceHashes -RepoRoot $repoRoot -DoFile $doPath
        artifacts = [ordered]@{
            transcript = $transcriptPath
            stdout = if ($Detach) { $null } else { $stdoutPath }
            stderr = if ($Detach) { $null } else { $stderrPath }
            wave = if ($WaveMode -eq 'None') { $null } else { $wavePath }
        }
    }
    Write-SimulationMetadata -Path $metadataPath -Metadata $metadata

    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $tool.Executable
    $startInfo.WorkingDirectory = $runDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = -not $Gui
    $startInfo.RedirectStandardOutput = -not $Detach
    $startInfo.RedirectStandardError = -not $Detach
    if (-not $Gui) { $startInfo.ArgumentList.Add('-c') }
    $startInfo.ArgumentList.Add('-modelsimini')
    $startInfo.ArgumentList.Add($iniPath)
    $startInfo.ArgumentList.Add('-l')
    $startInfo.ArgumentList.Add($transcriptPath)
    $startInfo.ArgumentList.Add('-do')
    $startInfo.ArgumentList.Add("do {$(ConvertTo-TclPath $doPath)}")

    $startInfo.Environment['SIM_REPO_ROOT'] = ConvertTo-TclPath $repoRoot
    $startInfo.Environment['SIM_DIR'] = ConvertTo-TclPath $simDir
    $startInfo.Environment['SIM_BUILD_DIR'] = ConvertTo-TclPath $runDirectory
    $startInfo.Environment['SIM_WAVE_MODE'] = $WaveMode
    $startInfo.Environment['SIM_WAVE_PATH'] = ConvertTo-TclPath $wavePath
    if ($null -ne $license) {
        if ($Simulator -eq 'Questa') {
            [void]$startInfo.Environment.Remove('MGLS_LICENSE_FILE')
            [void]$startInfo.Environment.Remove('LM_LICENSE_FILE')
            $startInfo.Environment['SALT_LICENSE_SERVER'] = $license.Value
        }
        else { $startInfo.Environment['MGLS_LICENSE_FILE'] = $license.Value }
    }

    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    $stdoutStream = $null
    $stderrStream = $null
    $stdoutTask = $null
    $stderrTask = $null
    $processStarted = $false
    try {
        if (-not $Detach) {
            # Claim both capture files before the simulator is started. If either
            # cannot be opened, no untracked child process can be left running.
            $stdoutStream = [IO.File]::Create($stdoutPath)
            $stderrStream = [IO.File]::Create($stderrPath)
        }
        if (-not $process.Start()) { throw 'Process start returned false.' }
        $processStarted = $true
        if ($Detach) {
            $metadata.status = 'detached-pending'
            $metadata.pending = $true
            $metadata.nativeExitCode = $null
            $metadata.processId = $process.Id
            Write-SimulationMetadata -Path $metadataPath -Metadata $metadata
            return [pscustomobject]@{ ExitCode = 0; NativeExitCode = $null; Status = 'detached-pending'; Pending = $true; RunDirectory = $runDirectory; MetadataPath = $metadataPath; TranscriptPath = $transcriptPath; WavePath = $wavePath; ProcessId = $process.Id }
        }

        $stdoutTask = $process.StandardOutput.BaseStream.CopyToAsync($stdoutStream)
        $stderrTask = $process.StandardError.BaseStream.CopyToAsync($stderrStream)

        $completed = if ($TimeoutSeconds -gt 0) { $process.WaitForExit($TimeoutSeconds * 1000) } else { $process.WaitForExit(); $true }
        if (-not $completed) {
            $process.Kill($true)
            $process.WaitForExit()
            $statusCode = $script:ExitCodes.Timeout
            $status = 'timeout'
        }
        else {
            $nativeExitCode = $process.ExitCode
            if (-not (Test-Path -LiteralPath $transcriptPath -PathType Leaf)) {
                $statusCode = $script:ExitCodes.MissingArtifact
                $status = 'missing-artifact'
            }
            elseif ($nativeExitCode -eq 0 -and $WaveMode -ne 'None' -and -not (Test-Path -LiteralPath $wavePath -PathType Leaf)) {
                $statusCode = $script:ExitCodes.MissingArtifact
                $status = 'missing-wave-artifact'
            }
            elseif ($nativeExitCode -eq 0) {
                $statusCode = $script:ExitCodes.Success
                $status = 'passed'
            }
            else {
                $transcript = Get-Content -LiteralPath $transcriptPath -Raw -ErrorAction SilentlyContinue
                if ($transcript -match '(?i)(?:unable|failed)\s+to\s+(?:check\s*out|checkout)\s+(?:a\s+)?license|license\s+checkout\s+(?:failed|denied)|failed\s+to\s+initialize\s+(?:the\s+)?licens(?:e|ing)\s+environment|no\s+valid\s+(?:questa|modelsim).*license|flexnet[^\r\n]*(?:error|failed|denied)') {
                    $statusCode = $script:ExitCodes.LicenseFailure
                    $status = 'license-failure'
                }
                else {
                    $phaseMatches = [regex]::Matches($transcript, 'SIM_PHASE:\s*(compile|elaboration|runtime)')
                    $phase = if ($phaseMatches.Count -gt 0) {
                        $phaseMatches[$phaseMatches.Count - 1].Groups[1].Value
                    }
                    elseif ($transcript -match '(?i)\(vcom-\d+\)|VHDL Compiler exiting|[/\\]vcom(?:\.exe)?\s+failed') {
                        'compile'
                    }
                    elseif ($transcript -match '(?i)error loading design|failed to (?:load|find|elaborate)|no design loaded|[/\\]vsim(?:\.exe)?\s+failed') {
                        'elaboration'
                    }
                    else { 'runtime' }
                    if ($phase -eq 'compile') {
                        $statusCode = $script:ExitCodes.CompileFailure
                        $status = 'compile-failure'
                    }
                    elseif ($phase -eq 'elaboration') {
                        $statusCode = $script:ExitCodes.ElaborationFailure
                        $status = 'elaboration-failure'
                    }
                    elseif ($transcript -match '(?im)assertion\s+(?:failure|error)|severity\s+(?:failure|error)|^\s*#?\s*\*\*\s+Failure:|\*\*\s+Fatal:') {
                        $statusCode = $script:ExitCodes.AssertionFailure
                        $status = 'assertion-failure'
                    }
                    else {
                        $statusCode = $script:ExitCodes.RuntimeFailure
                        $status = 'runtime-failure'
                    }
                }
            }
        }
    }
    catch {
        if ($processStarted) {
            try {
                if (-not $process.HasExited) {
                    $process.Kill($true)
                    $process.WaitForExit()
                }
            }
            catch {}
        }
        $statusCode = $script:ExitCodes.ProcessFailure
        $status = 'process-failure'
        $processError = $_.Exception.Message
    }
    finally {
        if ($null -ne $stdoutTask) { try { [void]($stdoutTask.GetAwaiter().GetResult()) } catch {} }
        if ($null -ne $stderrTask) { try { [void]($stderrTask.GetAwaiter().GetResult()) } catch {} }
        if ($null -ne $stdoutStream) { $stdoutStream.Dispose() }
        if ($null -ne $stderrStream) { $stderrStream.Dispose() }
        $process.Dispose()
    }

    if (Test-Path -LiteralPath $stdoutPath -PathType Leaf) {
        Get-Content -LiteralPath $stdoutPath | ForEach-Object { Write-Host $_ }
    }
    if (Test-Path -LiteralPath $stderrPath -PathType Leaf) {
        Get-Content -LiteralPath $stderrPath | ForEach-Object { [Console]::Error.WriteLine($_) }
    }

    # The trace benches write fixed relative file names. Move those files into
    # the run's raw/ directory and treat a missing case-specific trace as a
    # failed run even when vsim itself returned zero.
    $rawArtifacts = [Collections.Generic.List[string]]::new()
    try {
        foreach ($traceName in @('and_trace.csv', 'xor_trace.csv')) {
            $traceSource = Join-Path $runDirectory $traceName
            if (Test-Path -LiteralPath $traceSource -PathType Leaf) {
                $traceDestination = Join-Path (Join-Path $runDirectory 'raw') $traceName
                Move-Item -LiteralPath $traceSource -Destination $traceDestination -ErrorAction Stop
                [void]$rawArtifacts.Add($traceDestination)
            }
        }
    }
    catch {
        $artifactError = $_.Exception.Message
        if ($statusCode -eq 0) {
            $statusCode = $script:ExitCodes.MissingArtifact
            $status = 'trace-artifact-failure'
        }
    }

    if ($statusCode -eq 0) {
        $expectedTrace = switch ($caseName) {
            'run_and_trace' { 'and_trace.csv' }
            'run_xor_trace' { 'xor_trace.csv' }
            default { $null }
        }
        if ($null -ne $expectedTrace -and
            -not (Test-Path -LiteralPath (Join-Path (Join-Path $runDirectory 'raw') $expectedTrace) -PathType Leaf)) {
            $statusCode = $script:ExitCodes.MissingArtifact
            $status = 'missing-trace-artifact'
        }
    }
    if ($rawArtifacts.Count -gt 0) { $metadata.artifacts['raw'] = @($rawArtifacts) }

    if (-not (Get-Variable nativeExitCode -ErrorAction SilentlyContinue)) { $nativeExitCode = $null }
    $metadata.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $metadata.status = $status
    $metadata.exitCode = $statusCode
    $metadata.nativeExitCode = $nativeExitCode
    if (Get-Variable processError -ErrorAction SilentlyContinue) { $metadata.processError = $processError }
    if (Get-Variable artifactError -ErrorAction SilentlyContinue) { $metadata.artifactError = $artifactError }
    Write-SimulationMetadata -Path $metadataPath -Metadata $metadata

    if ($statusCode -eq 0 -and -not $KeepWork) {
        Get-ChildItem -LiteralPath $runDirectory -Directory -Filter 'work*' -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($statusCode -eq 0 -and $WaveMode -eq 'None') {
        foreach ($candidate in @((Join-Path $runDirectory 'vsim.wlf'), $wavePath)) {
            Remove-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue
        }
    }

    $result = [pscustomobject]@{
        ExitCode = $statusCode
        NativeExitCode = $nativeExitCode
        Status = $status
        RunDirectory = $runDirectory
        MetadataPath = $metadataPath
        TranscriptPath = $transcriptPath
        WavePath = if ($WaveMode -eq 'None') { $null } else { $wavePath }
    }
    return $result
}

Export-ModuleMember -Function Get-SimulationExitCodes, Get-SimulatorVersion, Resolve-ProjectPython, Resolve-SimulatorExecutable, Resolve-SimulatorLicense, Invoke-HdlSimulation
