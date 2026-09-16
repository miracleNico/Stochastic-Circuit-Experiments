# Simulation Workflow

QuestaSim 2024.1 is the default simulator for this repository. The flow keeps
the existing VHDL commands (`vcom` and `vsim`) and `.do` files while providing
one PowerShell runner for tool discovery, licensing, isolated work libraries,
metadata, waveforms, timeouts, and normalized exit codes.

This migration does not introduce `qrun`, CI runners, or Verilator+cocotb.
ModelSim remains available only through the explicitly selected workflow in
[`legacy/modelsim/`](../legacy/modelsim/README.md).

## Quick Start

Run the primitive-gate regression from the repository root:

```powershell
.\sim\run_questa.ps1
```

Run a particular migrated `.do` file through the stable low-level interface:

```powershell
.\sim\Invoke-Simulation.ps1 `
  -DoFile .\sim\run_comb6_diagnostics.do `
  -Simulator Questa `
  -TimeoutSeconds 3600
```

`run_questa.ps1` is fixed to Questa. All experiment wrappers default to Questa;
their experiment-specific parameters and stdout records are unchanged.

## Common Arguments

The experiment wrappers accept these common trailing arguments:

| Argument | Meaning | Default |
|---|---|---|
| `-Simulator Questa\|ModelSim` | Select the product; identity is verified with `vsim -version` | `Questa` |
| `-VsimPath <path>` | Explicit `vsim.exe`, its directory, or an install directory containing `win64/vsim.exe` | automatic |
| `-LicenseFile <path>` | Explicit license file | automatic |
| `-LicenseServer <port@host>` | Explicit license server; mutually exclusive with `-LicenseFile` | automatic |
| `-BuildRoot <path>` | Root for isolated runs | `.sim_build` |
| `-RunId <id>` | Reproducible run-directory suffix; unsafe characters are replaced | UTC/PID/random ID |
| `-WaveMode None\|Top\|All` | Disable waves, log top-level objects, or recursively log all objects | `None` |
| `-KeepWork` | Retain the compiled work library after success | off |
| `-TimeoutSeconds <n>` | Kill a batch run after this many seconds; `0` disables the timeout | `0` |

`Invoke-Simulation.ps1` additionally exposes `-Gui`, `-Detach`, and
`-PassThru`. `-PassThru` returns the structured result instead of exiting;
experiment wrappers use it internally. `open_and_wave.ps1` is the interactive
exception: it defaults to Questa, `-WaveMode All`, GUI detachment, and retained
work.

Relative `GeneratedNetworks`, `GeneratedShadow`, and `GeneratedWindowed` source
paths used by existing wrappers remain relative to `sim/`. Trace wrappers find
Python through `PYTHON`, then `PATH`, then the bundled Codex runtime.

## Tool Selection

Questa resolution is deterministic:

1. `-VsimPath`
2. `QUESTA_HOME`
3. `vsim.exe` on `PATH`, only if its version identifies it as Questa
4. the highest versioned `C:\questasim64_*\win64\vsim.exe`

Legacy ModelSim is resolved separately through `-VsimPath`, `MODELSIM_HOME`, a
product-matching `vsim.exe` on `PATH`, and the old Intel FPGA install paths. A
product mismatch is an error. The runner never falls back from missing Questa
to ModelSim. Its dedicated entry point is archived outside the mainline under
`legacy/modelsim/`.

## License Selection

The license source precedence is:

1. `-LicenseFile` or `-LicenseServer`
2. inherited `SALT_LICENSE_SERVER`
3. inherited `MGLS_LICENSE_FILE`
4. inherited `LM_LICENSE_FILE`
5. a unique `license.dat` or `*.lic` beneath the MentorGraphics directories in
   AppData, LocalAppData, or ProgramData

More than one discovered file is an error and requires `-LicenseFile`. For
Questa, the selected value is passed to the child process as
`SALT_LICENSE_SERVER`; compatibility variables are not forwarded. The runner
does not modify user or system environment variables. Metadata records neither
license contents nor the selected path/server value.

On the current development machine the uniquely discovered license is
`C:\ProgramData\MentorGraphics\License\license.dat`; do not depend on that path
on another host.

## Isolated Runs And Metadata

Each invocation creates:

```text
.sim_build/<simulator>/<do-basename>/<run-id>/
  modelsim.ini
  work/                 # removed after success unless -KeepWork
  transcript.log
  metadata.json
  wave.wlf              # only for Top or All
  raw/                   # trace CSVs and other raw run-local outputs
```

The run-level `modelsim.ini` is copied from the selected simulator installation
and sets `Resolution=ps` and `BreakOnAssertion=3`. A missing vendor file is a
run-directory failure; the archived `legacy/modelsim/modelsim.ini` is never
used as a fallback and is not modified. The filename is still required by
Questa itself and does not imply that a run used the legacy product. Absolute
repository and build paths are supplied to the `.do` files through
`sim_common.do`, so concurrent cases do not share libraries, transcripts, raw
data, or waves.

Successful runs retain `transcript.log`, `metadata.json`, and `raw/`, and remove
the work library unless `-KeepWork` was supplied. Failed runs keep the complete
directory for diagnosis. Batch runs default to `WaveMode=None` and therefore do
not retain a WLF.

`metadata.json` uses schema version 1 and records the simulator identity,
executable, source and `.do` SHA-256 hashes, Git revision/dirty state,
experiment environment parameters, timestamps, status, exit codes, and
artifact paths. It deliberately excludes license data.

Wave modes behave as follows:

- `None`: no signal logging and no retained WLF.
- `Top`: write `wave.wlf` and log top-level simulation objects.
- `All`: elaborate with signal accessibility, write `wave.wlf`, and recursively
  log internal hierarchy. Use this for clock/reset/clamp/spin/field/counter/PRNG
  inspection.

## Exit Codes

The stable low-level CLI normalizes failures independently of the simulator's
native exit code:

| Code | Meaning |
|---:|---|
| `0` | success |
| `10` | invalid arguments or other preflight input error |
| `20` | tool missing or simulator product mismatch |
| `30` | license selection or checkout failure |
| `40` | run-directory or run-level `modelsim.ini` failure |
| `50` | VHDL compile failure |
| `51` | elaboration/load failure |
| `52` | assertion failure |
| `53` | simulation runtime failure |
| `54` | child-process start or control failure |
| `60` | timeout |
| `70` | expected artifact missing |

The simulator's native exit code and the normalized status are both retained
in metadata. RCA reproduction does not treat exit code `0` alone as evidence;
its transcript parsers must also match the exact semantic goldens.

## Fixed-Seed Core Replay

Validate frozen inputs and entry points without running simulations:

```powershell
python .\scripts\run_questa_core_reproduction.py --preflight
```

Run the full core suite and publish reports only after all checks pass:

```powershell
python .\scripts\run_questa_core_reproduction.py `
  --suite core `
  --seed-mode replay `
  --simulator questa `
  --update-reports
```

Optional replay overrides include `--vsim-path`, one of `--license-file` or
`--license-server`, `--build-root`, `--run-id`, and `--timeout-seconds`. Replay
checks committed VHDL hashes and seed signatures, never generates a random
salt, stages all report data, and installs the original report trees only after
the optimizer, gates, COMB6, 4-bit, SUM-only, and selected 8-bit goldens pass.
Without `--update-reports`, validated candidate reports remain in staging.

The integer Idea 3+4 RCA golden (`idea34_integer4`) predates the testbench's
clamp-prime cycle and post-edge sample delay. The core driver uses
`-LegacyReplayTiming` only for that case to reproduce its historical
ModelSim-era evidence. The Q3.4 main run and both short forward schedules use
the corrected timing, which remains the wrapper default. Both the candidate
manifest and `reproduction_summary.json` record this compatibility mode.

The complete 25-run core replay passed on 2026-09-16 with QuestaSim 2024.1 and
published both report targets transactionally. Its result applies only to the
committed fixed seeds, not to unseen seeds. Future source or golden changes
require a new successful run before they can be described as reproduced.

## Legacy ModelSim

The dedicated launcher and archived configuration are kept together under
`legacy/modelsim/`. Use the launcher only when ModelSim is intentionally
selected:

```powershell
.\legacy\modelsim\run_modelsim.ps1 -VsimPath <legacy-vsim.exe>
```

Or select it on a compatible experiment wrapper with `-Simulator ModelSim`.
The `.do` files remain compatible, but the default workflow does not require a
local ModelSim installation. Failure to locate legacy ModelSim does not block
Questa acceptance, and failure to locate Questa does not trigger legacy
execution.

The current development host has no legacy ModelSim executable. Its dynamic
legacy result is therefore "environment not provided"; static `.do`
compatibility is retained and this does not block the Questa mainline switch.
See [`legacy/modelsim/README.md`](../legacy/modelsim/README.md) for the archive
boundary and configuration policy.
