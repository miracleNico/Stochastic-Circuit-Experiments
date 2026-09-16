$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Assert-Equal($Expected, $Actual, [string]$Message) {
    if ($Expected -ne $Actual) { throw "ASSERTION FAILED: $Message (expected '$Expected', actual '$Actual')" }
}

$simDir = Split-Path -Parent $PSScriptRoot
$modulePath = Join-Path $simDir 'Simulator.psm1'
$invokePath = Join-Path $simDir 'Invoke-Simulation.ps1'
Import-Module $modulePath -Force

$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$testRoot = Join-Path $tempBase ("questa-runner-tests-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $testRoot 'fake\win64') -Force | Out-Null

try {
    $fakeSource = @'
using System;
using System.IO;
using System.Threading;

public static class FakeVsim {
    public static int Main(string[] args) {
        foreach (string arg in args) {
            if (arg == "-version") {
                string localBanner = Path.Combine(AppContext.BaseDirectory, "banner.txt");
                Console.WriteLine(File.Exists(localBanner)
                    ? File.ReadAllText(localBanner).Trim()
                    : (Environment.GetEnvironmentVariable("FAKE_VSIM_BANNER") ?? "Questa Sim-64 vsim 2024.1 Simulator"));
                return 0;
            }
        }
        string transcript = null;
        for (int i = 0; i + 1 < args.Length; ++i) {
            if (args[i] == "-l") transcript = args[i + 1];
        }
        string phase = Environment.GetEnvironmentVariable("FAKE_PHASE") ?? "runtime";
        string assertion = Environment.GetEnvironmentVariable("FAKE_ASSERTION") == "1" ? "\n** Failure: neutral simulated stop" : "";
        string licenseText = Environment.GetEnvironmentVariable("FAKE_LICENSE_TEXT") ?? "";
        if (Environment.GetEnvironmentVariable("FAKE_NO_TRANSCRIPT") != "1" && transcript != null) {
            File.WriteAllText(transcript, "SIM_PHASE: " + phase + assertion + "\n" + licenseText + "\n");
        }
        string capture = Environment.GetEnvironmentVariable("FAKE_CAPTURE_ENV");
        if (!String.IsNullOrEmpty(capture)) {
            File.WriteAllText(capture,
                "salt=" + (!String.IsNullOrEmpty(Environment.GetEnvironmentVariable("SALT_LICENSE_SERVER")) ? "1" : "0") + "\n" +
                "mgls=" + (!String.IsNullOrEmpty(Environment.GetEnvironmentVariable("MGLS_LICENSE_FILE")) ? "1" : "0") + "\n" +
                "lm=" + (!String.IsNullOrEmpty(Environment.GetEnvironmentVariable("LM_LICENSE_FILE")) ? "1" : "0") + "\n");
        }
        Console.WriteLine("FAKE_STDOUT_SENTINEL");
        int sleep;
        if (Int32.TryParse(Environment.GetEnvironmentVariable("FAKE_SLEEP_MS"), out sleep) && sleep > 0) Thread.Sleep(sleep);
        int exitCode;
        return Int32.TryParse(Environment.GetEnvironmentVariable("FAKE_EXIT"), out exitCode) ? exitCode : 0;
    }
}
'@
    $fakeProject = Join-Path $testRoot 'fake-project'
    New-Item -ItemType Directory -Path $fakeProject -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $fakeProject 'Program.cs') -Encoding utf8NoBOM -Value $fakeSource
    Set-Content -LiteralPath (Join-Path $fakeProject 'fake.csproj') -Encoding utf8NoBOM -Value @'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <AssemblyName>vsim</AssemblyName>
    <UseAppHost>true</UseAppHost>
    <Nullable>disable</Nullable>
  </PropertyGroup>
</Project>
'@
    $nugetConfig = Join-Path $fakeProject 'NuGet.Config'
    Set-Content -LiteralPath $nugetConfig -Encoding utf8NoBOM -Value '<configuration><packageSources><clear /></packageSources></configuration>'
    $oldAppDataForDotnet = $env:APPDATA
    $oldDotnetCliHome = $env:DOTNET_CLI_HOME
    $oldDotnetToolsPath = $env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH
    $oldDotnetFirstRun = $env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE
    $env:APPDATA = Join-Path $fakeProject 'appdata'
    $env:DOTNET_CLI_HOME = Join-Path $fakeProject 'dotnet-home'
    $env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = 'false'
    $env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = 'true'
    New-Item -ItemType Directory -Path (Join-Path $env:APPDATA 'NuGet') -Force | Out-Null
    Copy-Item -LiteralPath $nugetConfig -Destination (Join-Path $env:APPDATA 'NuGet\NuGet.Config')
    & dotnet restore (Join-Path $fakeProject 'fake.csproj') --configfile $nugetConfig --nologo --verbosity quiet
    if ($LASTEXITCODE -ne 0) { throw "Unable to restore fake vsim project (dotnet exit $LASTEXITCODE)." }
    & dotnet build (Join-Path $fakeProject 'fake.csproj') --no-restore --nologo --verbosity quiet --output (Join-Path $testRoot 'fake\win64')
    if ($LASTEXITCODE -ne 0) { throw "Unable to build fake vsim (dotnet exit $LASTEXITCODE)." }
    if ($null -eq $oldAppDataForDotnet) { Remove-Item Env:\APPDATA -ErrorAction SilentlyContinue } else { $env:APPDATA = $oldAppDataForDotnet }
    if ($null -eq $oldDotnetCliHome) { Remove-Item Env:\DOTNET_CLI_HOME -ErrorAction SilentlyContinue } else { $env:DOTNET_CLI_HOME = $oldDotnetCliHome }
    if ($null -eq $oldDotnetToolsPath) { Remove-Item Env:\DOTNET_ADD_GLOBAL_TOOLS_TO_PATH -ErrorAction SilentlyContinue } else { $env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = $oldDotnetToolsPath }
    if ($null -eq $oldDotnetFirstRun) { Remove-Item Env:\DOTNET_SKIP_FIRST_TIME_EXPERIENCE -ErrorAction SilentlyContinue } else { $env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = $oldDotnetFirstRun }
    $fakeExe = Join-Path $testRoot 'fake\win64\vsim.exe'
    Set-Content -LiteralPath (Join-Path $testRoot 'fake\modelsim.ini') -Encoding ascii -Value "[vsim]`nResolution = ns`nBreakOnAssertion = 1"
    $fakeDo = Join-Path $testRoot 'fake.do'
    Set-Content -LiteralPath $fakeDo -Encoding ascii -Value 'quit -f'
    $fakeLicense = Join-Path $testRoot 'license.dat'
    Set-Content -LiteralPath $fakeLicense -Encoding ascii -Value 'test-only'

    # License precedence and auto-discovery are tested against isolated roots;
    # no real license path or value is emitted by these assertions.
    $licenseEnvironment = @{}
    foreach ($name in @('SALT_LICENSE_SERVER','MGLS_LICENSE_FILE','LM_LICENSE_FILE','APPDATA','LOCALAPPDATA','ProgramData')) {
        $licenseEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    }
    try {
        $licenseRoots = Join-Path $testRoot 'license-roots'
        $env:APPDATA = Join-Path $licenseRoots 'appdata'
        $env:LOCALAPPDATA = Join-Path $licenseRoots 'localappdata'
        $env:ProgramData = Join-Path $licenseRoots 'programdata'
        foreach ($rootName in @('APPDATA','LOCALAPPDATA','ProgramData')) {
            New-Item -ItemType Directory -Path (Join-Path ([Environment]::GetEnvironmentVariable($rootName, 'Process')) 'MentorGraphics') -Force | Out-Null
        }
        foreach ($name in @('SALT_LICENSE_SERVER','MGLS_LICENSE_FILE','LM_LICENSE_FILE')) { Remove-Item "Env:\$name" -ErrorAction SilentlyContinue }

        $autoOne = Join-Path $env:APPDATA 'MentorGraphics\auto.lic'
        Set-Content -LiteralPath $autoOne -Encoding ascii -Value 'auto-one'
        $autoResult = Resolve-SimulatorLicense
        Assert-Equal 'AutoDetected' $autoResult.Source 'one discovered license is selected'
        Assert-Equal ([IO.Path]::GetFullPath($autoOne)) $autoResult.Value 'unique discovered license path'

        Set-Content -LiteralPath (Join-Path $env:LOCALAPPDATA 'MentorGraphics\second.lic') -Encoding ascii -Value 'auto-two'
        $ambiguityRejected = $false
        try { Resolve-SimulatorLicense | Out-Null } catch { $ambiguityRejected = $true }
        Assert-True $ambiguityRejected 'multiple discovered licenses require an explicit choice'

        $env:SALT_LICENSE_SERVER = '1234@example.invalid'
        $inheritedResult = Resolve-SimulatorLicense
        Assert-Equal 'SALT_LICENSE_SERVER' $inheritedResult.Source 'inherited SALT precedes discovery'
        $explicitResult = Resolve-SimulatorLicense -LicenseFile $fakeLicense
        Assert-Equal 'Argument' $explicitResult.Source 'explicit license precedes inherited values'
    }
    finally {
        foreach ($entry in $licenseEnvironment.GetEnumerator()) {
            if ($null -eq $entry.Value) { Remove-Item "Env:\$($entry.Key)" -ErrorAction SilentlyContinue }
            else { [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process') }
        }
    }

    $env:FAKE_VSIM_BANNER = 'Questa Sim-64 vsim 2024.1 Simulator'
    $resolved = Resolve-SimulatorExecutable -Simulator Questa -VsimPath (Join-Path $testRoot 'fake')
    Assert-Equal ([IO.Path]::GetFullPath($fakeExe)) $resolved.Executable 'explicit install root resolves win64/vsim.exe'

    $missingRejected = $false
    try { Resolve-SimulatorExecutable -Simulator Questa -VsimPath (Join-Path $testRoot 'missing') | Out-Null }
    catch { $missingRejected = $true }
    Assert-True $missingRejected 'missing explicit VsimPath must not fall through'

    $env:FAKE_VSIM_BANNER = 'ModelSim SE-64 2020.4'
    $mismatchRejected = $false
    try { Resolve-SimulatorExecutable -Simulator Questa -VsimPath $fakeExe | Out-Null }
    catch { $mismatchRejected = $true }
    Assert-True $mismatchRejected 'explicit ModelSim binary must be rejected as Questa'
    $env:FAKE_VSIM_BANNER = 'Questa Sim-64 vsim 2024.1 Simulator'

    # Exercise the non-explicit precedence without relying on any simulator
    # installed on the host running this test.
    $toolEnvironment = @{
        PATH = [Environment]::GetEnvironmentVariable('PATH', 'Process')
        QUESTA_HOME = [Environment]::GetEnvironmentVariable('QUESTA_HOME', 'Process')
        MODELSIM_HOME = [Environment]::GetEnvironmentVariable('MODELSIM_HOME', 'Process')
    }
    try {
        $pathBin = Join-Path $testRoot 'path-install\win64'
        New-Item -ItemType Directory -Path $pathBin -Force | Out-Null
        Copy-Item -Path (Join-Path $testRoot 'fake\win64\*') -Destination $pathBin -Recurse
        $pathExe = Join-Path $pathBin 'vsim.exe'
        $env:PATH = "$pathBin$([IO.Path]::PathSeparator)$($toolEnvironment.PATH)"

        $env:QUESTA_HOME = Join-Path $testRoot 'fake'
        $env:MODELSIM_HOME = Join-Path $testRoot 'unused-modelsim-home'
        $homeResolved = Resolve-SimulatorExecutable -Simulator Questa
        Assert-Equal ([IO.Path]::GetFullPath($fakeExe)) $homeResolved.Executable 'QUESTA_HOME precedes PATH'

        $wrongProductHome = Join-Path $testRoot 'wrong-product-home'
        $wrongProductBin = Join-Path $wrongProductHome 'win64'
        New-Item -ItemType Directory -Path $wrongProductBin -Force | Out-Null
        Copy-Item -Path (Join-Path $testRoot 'fake\win64\*') -Destination $wrongProductBin -Recurse
        Set-Content -LiteralPath (Join-Path $wrongProductBin 'banner.txt') -Encoding ascii -Value 'ModelSim SE-64 2020.4'
        $env:QUESTA_HOME = $wrongProductHome
        $priorityMismatchRejected = $false
        $priorityMismatchMessage = ''
        try { Resolve-SimulatorExecutable -Simulator Questa | Out-Null }
        catch {
            $priorityMismatchRejected = $true
            $priorityMismatchMessage = $_.Exception.Message
        }
        Assert-True $priorityMismatchRejected 'an existing wrong-product QUESTA_HOME must stop resolution instead of falling through to PATH'
        Assert-True ($priorityMismatchMessage -match '^Requested Questa') 'the higher-priority product mismatch is reported directly'

        $env:QUESTA_HOME = Join-Path $testRoot 'missing-questa-home'
        $pathResolved = Resolve-SimulatorExecutable -Simulator Questa
        Assert-Equal ([IO.Path]::GetFullPath($pathExe)) $pathResolved.Executable 'invalid QUESTA_HOME falls through to PATH'

        $env:FAKE_VSIM_BANNER = 'ModelSim SE-64 2020.4'
        $env:MODELSIM_HOME = Join-Path $testRoot 'fake'
        $modelResolved = Resolve-SimulatorExecutable -Simulator ModelSim
        Assert-Equal ([IO.Path]::GetFullPath($fakeExe)) $modelResolved.Executable 'MODELSIM_HOME is used only for explicit legacy selection'

        $env:FAKE_VSIM_BANNER = 'Questa Sim-64 vsim 2024.1 Simulator'
        $env:QUESTA_HOME = Join-Path $testRoot 'missing-questa-home'
        $separateResolved = Resolve-SimulatorExecutable -Simulator Questa
        Assert-Equal ([IO.Path]::GetFullPath($pathExe)) $separateResolved.Executable 'Questa resolution ignores MODELSIM_HOME'
    }
    finally {
        foreach ($entry in $toolEnvironment.GetEnumerator()) {
            if ($null -eq $entry.Value) { Remove-Item "Env:\$($entry.Key)" -ErrorAction SilentlyContinue }
            else { [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process') }
        }
        $env:FAKE_VSIM_BANNER = 'Questa Sim-64 vsim 2024.1 Simulator'
    }

    $oldMgls = $env:MGLS_LICENSE_FILE
    $oldLm = $env:LM_LICENSE_FILE
    $env:MGLS_LICENSE_FILE = 'parent-secret-mgls'
    $env:LM_LICENSE_FILE = 'parent-secret-lm'
    $capturePath = Join-Path $testRoot 'child-env.txt'
    $env:FAKE_CAPTURE_ENV = $capturePath
    $buildRoot = Join-Path $testRoot 'build'
    $result = Invoke-HdlSimulation -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId success
    Assert-Equal 0 $result.ExitCode 'fake success exits zero'
    $duplicateRejected = $false
    try {
        Invoke-HdlSimulation -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId success | Out-Null
    }
    catch { $duplicateRejected = $true }
    Assert-True $duplicateRejected 'an existing RunId is rejected instead of sharing a run directory'
    $capture = Get-Content -LiteralPath $capturePath -Raw
    Assert-True ($capture -match 'salt=1') 'Questa child receives SALT_LICENSE_SERVER'
    Assert-True ($capture -match 'mgls=0') 'Questa child does not receive MGLS_LICENSE_FILE'
    Assert-True ($capture -match 'lm=0') 'Questa child does not receive LM_LICENSE_FILE'
    Assert-Equal 'parent-secret-mgls' $env:MGLS_LICENSE_FILE 'parent MGLS environment remains unchanged'
    Assert-Equal 'parent-secret-lm' $env:LM_LICENSE_FILE 'parent LM environment remains unchanged'
    $metadataText = Get-Content -LiteralPath $result.MetadataPath -Raw
    Assert-True ($metadataText -notmatch 'parent-secret|test-only|license\.dat') 'metadata does not expose license values'

    $optimizerPackage = Join-Path $testRoot 'optimizer_coefficients_pkg.vhd'
    Set-Content -LiteralPath $optimizerPackage -Encoding ascii -Value 'package optimizer_coefficients_pkg is end package;'
    $oldOptimizerPackage = $env:OPTIMIZER_COEFFICIENT_PACKAGE
    try {
        $env:OPTIMIZER_COEFFICIENT_PACKAGE = $optimizerPackage
        $optimizerResult = Invoke-HdlSimulation -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId optimizer-package-hash
        $optimizerMetadata = Get-Content -LiteralPath $optimizerResult.MetadataPath -Raw | ConvertFrom-Json
        Assert-Equal ([IO.Path]::GetFullPath($optimizerPackage)) $optimizerMetadata.parameters.OPTIMIZER_COEFFICIENT_PACKAGE 'optimizer package path is captured'
        $expectedOptimizerHash = (Get-FileHash -LiteralPath $optimizerPackage -Algorithm SHA256).Hash.ToLowerInvariant()
        Assert-True ($expectedOptimizerHash -in @($optimizerMetadata.hashes.PSObject.Properties.Value)) 'optimizer package SHA-256 is captured'
    }
    finally {
        if ($null -eq $oldOptimizerPackage) { Remove-Item Env:\OPTIMIZER_COEFFICIENT_PACKAGE -ErrorAction SilentlyContinue }
        else { $env:OPTIMIZER_COEFFICIENT_PACKAGE = $oldOptimizerPackage }
    }

    $detachedResult = Invoke-HdlSimulation -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId detached-metadata -Detach
    $detachedMetadata = Get-Content -LiteralPath $detachedResult.MetadataPath -Raw | ConvertFrom-Json
    Assert-Equal 'detached-pending' $detachedMetadata.status 'detached metadata is explicitly pending'
    Assert-True ([bool]$detachedMetadata.pending) 'detached metadata has pending flag'
    Assert-True ($null -eq $detachedMetadata.artifacts.stdout -and $null -eq $detachedMetadata.artifacts.stderr) 'detached metadata does not claim capture files'
    Start-Sleep -Milliseconds 100

    $openAndWave = Get-Command (Join-Path $simDir 'open_and_wave.ps1')
    $waveModeValidation = @($openAndWave.Parameters['WaveMode'].Attributes | Where-Object { $_ -is [Management.Automation.ValidateSetAttribute] })
    Assert-True ($waveModeValidation.Count -eq 1 -and 'None' -in $waveModeValidation[0].ValidValues) 'open_and_wave accepts WaveMode None while retaining its All default'

    $env:FAKE_CAPTURE_ENV = $null
    $failureCases = @(
        @{ Phase = 'runtime'; Assertion = '0'; Expected = 30; RunId = 'license-failure'; LicenseText = 'Unable to checkout a license' },
        @{ Phase = 'compile'; Assertion = '0'; Expected = 50; RunId = 'compile-failure' },
        @{ Phase = 'elaboration'; Assertion = '0'; Expected = 51; RunId = 'elaboration-failure' },
        @{ Phase = 'runtime'; Assertion = '1'; Expected = 52; RunId = 'assertion-failure' },
        @{ Phase = 'runtime'; Assertion = '0'; Expected = 53; RunId = 'license-word-runtime'; LicenseText = 'runtime stopped near a license label' },
        @{ Phase = 'runtime'; Assertion = '0'; Expected = 53; RunId = 'runtime-failure' }
    )
    foreach ($case in $failureCases) {
        $env:FAKE_PHASE = $case.Phase
        $env:FAKE_ASSERTION = $case.Assertion
        $env:FAKE_EXIT = '7'
        if ($case.ContainsKey('LicenseText')) { $env:FAKE_LICENSE_TEXT = $case.LicenseText } else { Remove-Item Env:\FAKE_LICENSE_TEXT -ErrorAction SilentlyContinue }
        $failed = Invoke-HdlSimulation -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId $case.RunId
        Assert-Equal $case.Expected $failed.ExitCode "$($case.RunId) classification"
        Assert-True (-not [string]::IsNullOrWhiteSpace($failed.RunDirectory)) "$($case.RunId) preserves run directory"
    }

    $env:FAKE_EXIT = '0'
    Remove-Item Env:\FAKE_LICENSE_TEXT -ErrorAction SilentlyContinue
    $env:FAKE_ASSERTION = '0'

    $traceDoRoot = Join-Path $testRoot 'trace-do-files'
    New-Item -ItemType Directory -Path $traceDoRoot -Force | Out-Null
    foreach ($traceCase in @('run_and_trace', 'run_xor_trace')) {
        $traceDo = Join-Path $traceDoRoot "$traceCase.do"
        Set-Content -LiteralPath $traceDo -Encoding ascii -Value 'quit -f'
        $traceResult = Invoke-HdlSimulation -DoFile $traceDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId "$traceCase-missing-raw"
        Assert-Equal 70 $traceResult.ExitCode "$traceCase requires its raw trace artifact"
        $traceMetadata = Get-Content -LiteralPath $traceResult.MetadataPath -Raw | ConvertFrom-Json
        Assert-Equal 70 $traceMetadata.exitCode "$traceCase missing-artifact metadata exit code"
    }

    $runAllTraces = Join-Path $simDir 'run_all_traces.ps1'
    $aggregateFailureRunId = 'aggregate-child-failure'
    & pwsh -NoProfile -File $runAllTraces -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId $aggregateFailureRunId 2>$null | Out-Null
    Assert-Equal 70 $LASTEXITCODE 'trace aggregation preserves a child missing-artifact exit code'
    $aggregateFailureMetadataPath = Join-Path $buildRoot "questa\run_all_traces\$aggregateFailureRunId\metadata.json"
    $aggregateFailureMetadata = Get-Content -LiteralPath $aggregateFailureMetadataPath -Raw | ConvertFrom-Json
    Assert-Equal 'and-trace-failure' $aggregateFailureMetadata.status 'trace aggregation records which child failed'
    Assert-Equal 70 $aggregateFailureMetadata.exitCode 'trace aggregation finalizes failure metadata'

    $env:FAKE_NO_TRANSCRIPT = '1'
    $missingArtifact = Invoke-HdlSimulation -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId missing-artifact
    Assert-Equal 70 $missingArtifact.ExitCode 'missing transcript classification'
    $env:FAKE_NO_TRANSCRIPT = '0'

    $env:FAKE_SLEEP_MS = '2000'
    $timedOut = Invoke-HdlSimulation -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId timeout -TimeoutSeconds 1
    Assert-Equal 60 $timedOut.ExitCode 'timeout classification'
    $env:FAKE_SLEEP_MS = '0'

    $env:FAKE_EXIT = '0'
    $cliOutput = @(& pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId cli-stdout 2>&1)
    Assert-Equal 0 $LASTEXITCODE 'CLI success exit code'
    Assert-True (($cliOutput | Out-String) -match 'FAKE_STDOUT_SENTINEL') 'child stdout passes through CLI'

    $env:FAKE_PHASE = 'compile'
    $env:FAKE_EXIT = '7'
    & pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId cli-compile-failure 2>$null | Out-Null
    Assert-Equal 50 $LASTEXITCODE 'compile failure CLI exit code'
    $env:FAKE_PHASE = 'runtime'
    $env:FAKE_EXIT = '0'

    & pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator invalid -VsimPath $fakeExe 2>$null
    Assert-Equal 10 $LASTEXITCODE 'invalid argument CLI exit code'
    & pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator Questa -VsimPath (Join-Path $testRoot 'absent.exe') 2>$null
    Assert-Equal 20 $LASTEXITCODE 'missing tool CLI exit code'

    $wrapperPath = Join-Path $simDir 'run_and_onecycle_sanity.ps1'
    & pwsh -NoProfile -File $wrapperPath -VsimPath (Join-Path $testRoot 'wrapper-absent.exe') -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId wrapper-missing-tool 2>$null | Out-Null
    Assert-Equal 20 $LASTEXITCODE 'case wrapper preserves the stable missing-tool exit code'

    $noIniBin = Join-Path $testRoot 'no-ini-install\win64'
    New-Item -ItemType Directory -Path $noIniBin -Force | Out-Null
    Copy-Item -Path (Join-Path $testRoot 'fake\win64\*') -Destination $noIniBin -Recurse
    $noIniExe = Join-Path $noIniBin 'vsim.exe'
    & pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator Questa -VsimPath $noIniExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId missing-vendor-ini 2>$null | Out-Null
    Assert-Equal 40 $LASTEXITCODE 'a vendor modelsim.ini is required; the tracked repository ini is not a fallback'

    & pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile (Join-Path $testRoot 'absent.lic') 2>$null
    Assert-Equal 30 $LASTEXITCODE 'missing license CLI exit code'
    & pwsh -NoProfile -File $invokePath -DoFile (Join-Path $testRoot 'license_missing.do') -Simulator Questa -VsimPath $fakeExe 2>$null
    Assert-Equal 10 $LASTEXITCODE 'license word in a missing do-file path is not a license failure'
    foreach ($badRunId in @('.', '..')) {
        & pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $buildRoot -RunId $badRunId 2>$null
        Assert-Equal 10 $LASTEXITCODE "RunId $badRunId is rejected as an argument error"
    }
    $notDirectory = Join-Path $testRoot 'not-a-directory'
    Set-Content -LiteralPath $notDirectory -Encoding ascii -Value 'file'
    & pwsh -NoProfile -File $invokePath -DoFile $fakeDo -Simulator Questa -VsimPath $fakeExe -LicenseFile $fakeLicense -BuildRoot $notDirectory 2>$null
    Assert-Equal 40 $LASTEXITCODE 'run directory CLI exit code'

    Write-Host 'Simulator infrastructure tests passed.'
}
finally {
    foreach ($name in @('FAKE_VSIM_BANNER','FAKE_CAPTURE_ENV','FAKE_PHASE','FAKE_ASSERTION','FAKE_EXIT','FAKE_LICENSE_TEXT','FAKE_NO_TRANSCRIPT','FAKE_SLEEP_MS')) {
        Remove-Item "Env:\$name" -ErrorAction SilentlyContinue
    }
    if (Get-Variable oldMgls -ErrorAction SilentlyContinue) {
        if ($null -eq $oldMgls) { Remove-Item Env:\MGLS_LICENSE_FILE -ErrorAction SilentlyContinue } else { $env:MGLS_LICENSE_FILE = $oldMgls }
    }
    if (Get-Variable oldLm -ErrorAction SilentlyContinue) {
        if ($null -eq $oldLm) { Remove-Item Env:\LM_LICENSE_FILE -ErrorAction SilentlyContinue } else { $env:LM_LICENSE_FILE = $oldLm }
    }
    if (Get-Variable oldAppDataForDotnet -ErrorAction SilentlyContinue) {
        if ($null -eq $oldAppDataForDotnet) { Remove-Item Env:\APPDATA -ErrorAction SilentlyContinue } else { $env:APPDATA = $oldAppDataForDotnet }
    }
    if (Get-Variable oldDotnetCliHome -ErrorAction SilentlyContinue) {
        if ($null -eq $oldDotnetCliHome) { Remove-Item Env:\DOTNET_CLI_HOME -ErrorAction SilentlyContinue } else { $env:DOTNET_CLI_HOME = $oldDotnetCliHome }
    }
    if (Get-Variable oldDotnetToolsPath -ErrorAction SilentlyContinue) {
        if ($null -eq $oldDotnetToolsPath) { Remove-Item Env:\DOTNET_ADD_GLOBAL_TOOLS_TO_PATH -ErrorAction SilentlyContinue } else { $env:DOTNET_ADD_GLOBAL_TOOLS_TO_PATH = $oldDotnetToolsPath }
    }
    if (Get-Variable oldDotnetFirstRun -ErrorAction SilentlyContinue) {
        if ($null -eq $oldDotnetFirstRun) { Remove-Item Env:\DOTNET_SKIP_FIRST_TIME_EXPERIENCE -ErrorAction SilentlyContinue } else { $env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = $oldDotnetFirstRun }
    }
    $resolvedTestRoot = [IO.Path]::GetFullPath($testRoot)
    if ($resolvedTestRoot.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path -Leaf $resolvedTestRoot).StartsWith('questa-runner-tests-')) {
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
