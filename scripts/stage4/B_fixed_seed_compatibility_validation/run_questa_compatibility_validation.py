"""Validate the ModelSim-to-QuestaSim migration against committed fixed-seed evidence.

This entry point deliberately has no generation mode.  It consumes the checked-in
VHDL and seed manifest, stages every report artifact, and publishes only after all
VHDL runs and semantic transcript comparisons have passed.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import scripts.stage2.run_rca_convergence_benchmark as benchmark
ROOT = _REPO_ROOT
REPORTS = ROOT / "results_and_reports"
BENCHMARK_REPORT = REPORTS / "stage2" / "rca_convergence_benchmark"
COMB6_REPORT = REPORTS / "stage1" / "C_combinational_gap_equalization" / "comb6_equal_gap_report.md"
SOURCE_MANIFEST = BENCHMARK_REPORT / "data" / "manifest.json"
GOLDEN_PATH = Path(__file__).with_name("questa_compatibility_golden.json")
FLOAT_TOLERANCE = 1e-9
BENCHMARK_ARTIFACTS = ("report.md", "data", "figures", "traces")


class ReproductionError(RuntimeError):
    """A replay precondition, simulation, parser, or golden check failed."""


@dataclass(frozen=True)
class RunSpec:
    name: str
    wrapper: Path
    arguments: tuple[str, ...] = ()
    fixed_questa: bool = False


@dataclass(frozen=True)
class Comb6Metrics:
    top_matches: int
    zero_hit_cases: int
    min_hits: int
    total_hits: int
    sample_count: int
    cases: int

    @property
    def average_hits(self) -> float:
        return self.total_hits / self.cases


COMB6_LINE_RE = re.compile(
    r"comb6 forward input=(?P<input>\d+) expected_sig=(?P<expected>\d+) "
    r"hits=(?P<hits>\d+)/(?P<samples>\d+) top_sig=(?P<top>\d+) "
    r"top_count=(?P<top_count>\d+)"
)
COMB6_SUMMARY_RE = re.compile(
    r"comb6 summary min_hits=(?P<min_hits>\d+)/(?P<samples>\d+)"
)
QUESTA_VERSION_RE = re.compile(r"\bQuesta(?:Sim)?\b.*?\b(\d{4}\.\d+(?:\.\d+)?)\b", re.IGNORECASE)

HISTORICAL_TIMING_REPLAY = {
    "mode": "historical-benchmark",
    "runner_switch": "-LegacyReplayTiming",
    "applies_to": [
        "scheduled_auxiliary_carry_integer4",
    ],
    "behavior": "skip the later clamp-prime cycle and post-edge sample delay",
    "default_wrapper_behavior": "corrected clamp-prime cycle and post-edge sample delay",
    "purpose": "match the committed integer scheduled auxiliary-carry ModelSim-era golden exactly",
}
SIM_SUMMARY_RE = re.compile(r"Errors:\s*(?P<errors>\d+)\s*,\s*Warnings:\s*(?P<warnings>\d+)", re.IGNORECASE)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_sha256(value: object) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReproductionError(f"Cannot read JSON {path}: {exc}") from exc


def write_normalized_transcript(path: Path, text: str) -> None:
    """Write simulator evidence with stable LF endings and no line-end padding."""
    normalized = "\n".join(line.rstrip() for line in text.splitlines())
    if text.endswith(("\n", "\r")):
        normalized += "\n"
    path.write_text(normalized, encoding="utf-8", newline="\n")


def ensure_inside(path: Path, parent: Path) -> Path:
    resolved = path.resolve()
    parent_resolved = parent.resolve()
    if not resolved.is_relative_to(parent_resolved):
        raise ReproductionError(f"Path escapes {parent_resolved}: {resolved}")
    return resolved


def verify_replay_inputs() -> tuple[dict, dict, dict[str, str]]:
    """Validate frozen manifest identity, VHDL hashes, and derived seed signatures."""

    golden = load_json(GOLDEN_PATH)
    if golden.get("schema_version") != 1:
        raise ReproductionError(f"Unsupported golden schema in {GOLDEN_PATH}")
    manifest = load_json(SOURCE_MANIFEST)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ReproductionError(f"Missing artifacts object in {SOURCE_MANIFEST}")
    if set(artifacts) != set(golden["artifacts"]):
        raise ReproductionError(
            "Frozen manifest artifact keys differ: "
            f"expected {sorted(golden['artifacts'])}, got {sorted(artifacts)}"
        )

    hashes: dict[str, str] = {}
    for name, expected in golden["artifacts"].items():
        actual = artifacts.get(name)
        if not isinstance(actual, dict):
            raise ReproductionError(f"Manifest is missing frozen artifact {name!r}")
        expected_payload = {
            key: value
            for key, value in expected.items()
            if key not in {"seed_signature", "sha256"}
        }
        actual_payload = dict(actual)
        recorded_hash = actual_payload.pop("sha256", None)
        if recorded_hash is not None and recorded_hash != expected["sha256"]:
            raise ReproductionError(
                f"{name} manifest SHA-256 mismatch: expected {expected['sha256']}, got {recorded_hash}"
            )
        if actual_payload != expected_payload:
            raise ReproductionError(
                f"{name} frozen manifest payload mismatch: "
                f"expected {expected_payload!r}, got {actual_payload!r}"
            )
        source = ensure_inside(ROOT / expected["path"], ROOT)
        if not source.is_file():
            raise ReproductionError(f"Frozen VHDL is missing: {source}")
        actual_hash = sha256(source)
        if actual_hash != expected["sha256"]:
            raise ReproductionError(
                f"{name} SHA-256 mismatch: expected {expected['sha256']}, got {actual_hash}"
            )
        signature = expected["seed_signature"].upper()
        source_text = source.read_text(encoding="utf-8")
        if len(re.findall(re.escape(signature), source_text, re.IGNORECASE)) < 2:
            raise ReproductionError(
                f"{name} does not contain the frozen scheduler seed signature {signature} twice"
            )
        hashes[expected["path"]] = actual_hash

    parameter_payload = {
        "integer_weights": manifest.get("integer_weights"),
        "q34_weights": manifest.get("q34_weights"),
    }
    if any(value is None for value in parameter_payload.values()):
        raise ReproductionError("Manifest is missing frozen integer_weights or q34_weights")
    parameter_hash = json_sha256(parameter_payload)
    expected_parameter_hash = golden.get("manifest_parameter_payload_sha256")
    if parameter_hash != expected_parameter_hash:
        raise ReproductionError(
            "Frozen manifest parameter payload mismatch: "
            f"expected SHA-256 {expected_parameter_hash}, got {parameter_hash}"
        )

    for name, expected in golden["comb6_sources"].items():
        source = ensure_inside(ROOT / expected["path"], ROOT)
        if not source.is_file():
            raise ReproductionError(f"Frozen COMB6 VHDL is missing: {source}")
        actual_hash = sha256(source)
        if actual_hash != expected["sha256"]:
            raise ReproductionError(
                f"COMB6 {name} SHA-256 mismatch: expected {expected['sha256']}, got {actual_hash}"
            )
        hashes[expected["path"]] = actual_hash
    return manifest, golden, hashes


def version_key(path: Path) -> tuple[int, ...]:
    match = re.search(r"questasim64_([0-9.]+)", str(path), re.IGNORECASE)
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def normalize_vsim_candidates(value: str | os.PathLike[str]) -> list[Path]:
    candidate = Path(value).expanduser()
    if candidate.is_dir():
        if candidate.name.casefold() == "win64":
            return [candidate / "vsim.exe"]
        return [candidate / "vsim.exe", candidate / "win64" / "vsim.exe"]
    return [candidate]


def resolve_questa_vsim(explicit: str | None) -> tuple[Path, str]:
    candidates: list[Path] = []
    if explicit:
        candidates.extend(normalize_vsim_candidates(explicit))
    else:
        if os.environ.get("QUESTA_HOME"):
            candidates.extend(normalize_vsim_candidates(os.environ["QUESTA_HOME"]))
        on_path = shutil.which("vsim")
        if on_path:
            candidates.append(Path(on_path))
        candidates.extend(
            sorted(
                Path("C:/").glob("questasim64_*/win64/vsim.exe"),
                key=version_key,
                reverse=True,
            )
        )

    if explicit and not any(candidate.is_file() for candidate in candidates):
        raise ReproductionError(f"Explicit Questa vsim does not exist: {explicit}")

    mismatches: list[str] = []
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if not candidate.is_file():
            continue
        try:
            proc = subprocess.run(
                [str(candidate), "-version"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            mismatches.append(f"{candidate}: {exc}")
            continue
        output = proc.stdout or ""
        match = QUESTA_VERSION_RE.search(output)
        if proc.returncode == 0 and match:
            first_line = next((line.strip() for line in output.splitlines() if line.strip()), match.group(0))
            return candidate.resolve(), first_line
        mismatches.append(f"{candidate}: not Questa ({output.splitlines()[:1]})")
    detail = "; ".join(mismatches) if mismatches else "no candidates found"
    raise ReproductionError(f"QuestaSim vsim could not be resolved: {detail}")


def powershell_executable() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell") or shutil.which("powershell.exe")
    if not executable:
        raise ReproductionError("PowerShell is required to invoke the simulation wrappers")
    return executable


def clean_run_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ReproductionError("RunId may contain only letters, digits, dot, underscore, and hyphen")
    return value


def common_wrapper_arguments(
    *,
    spec: RunSpec,
    simulator: str,
    vsim_path: Path,
    build_root: Path,
    run_id: str,
    timeout_seconds: int,
    license_file: str | None,
    license_server: str | None,
) -> list[str]:
    args: list[str] = []
    if not spec.fixed_questa:
        args.extend(["-Simulator", "Questa" if simulator == "questa" else "ModelSim"])
    args.extend(
        [
            "-VsimPath",
            str(vsim_path),
            "-BuildRoot",
            str(build_root),
            "-RunId",
            run_id,
            "-WaveMode",
            "None",
            "-TimeoutSeconds",
            str(timeout_seconds),
        ]
    )
    if license_file:
        args.extend(["-LicenseFile", license_file])
    if license_server:
        args.extend(["-LicenseServer", license_server])
    return args


def run_spec(
    spec: RunSpec,
    *,
    powershell: str,
    simulator: str,
    vsim_path: Path,
    build_root: Path,
    run_id_prefix: str,
    timeout_seconds: int,
    license_file: str | None,
    license_server: str | None,
    traces: Path,
) -> str:
    if not spec.wrapper.is_file():
        raise ReproductionError(f"Required simulation wrapper is missing: {spec.wrapper}")
    case_run_id = clean_run_id(f"{run_id_prefix}-{spec.name}")
    common = common_wrapper_arguments(
        spec=spec,
        simulator=simulator,
        vsim_path=vsim_path,
        build_root=build_root,
        run_id=case_run_id,
        timeout_seconds=timeout_seconds,
        license_file=license_file,
        license_server=license_server,
    )
    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(spec.wrapper),
        *spec.arguments,
        *common,
    ]
    print(f"[{spec.name}] running {spec.wrapper.name}", flush=True)
    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds + 120,
            check=False,
        )
        output = proc.stdout or ""
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        trace = traces / f"{spec.name}.txt"
        write_normalized_transcript(trace, output)
        raise ReproductionError(f"{spec.name} exceeded the Python safety timeout; see {trace}") from exc
    trace = traces / f"{spec.name}.txt"
    write_normalized_transcript(trace, output)
    if proc.returncode != 0:
        raise ReproductionError(f"{spec.name} failed with exit code {proc.returncode}; see {trace}")
    # Migrated wrappers intentionally keep their historical console contract;
    # the canonical report stream is the isolated runner transcript.
    transcript_path = runner_transcript(build_root, case_run_id)
    transcript = transcript_path.read_text(encoding="utf-8", errors="replace")
    write_normalized_transcript(trace, transcript)
    return transcript


def runner_transcript(build_root: Path, case_run_id: str) -> Path:
    matches = [
        path
        for path in build_root.rglob("transcript.log")
        if path.parent.name.casefold() == case_run_id.casefold()
    ]
    if len(matches) != 1:
        raise ReproductionError(
            f"Expected one runner transcript for {case_run_id}, found {len(matches)} under {build_root}"
        )
    return matches[0]


def pspath(path: Path) -> str:
    return str(path.resolve())


def benchmark_run_specs() -> list[RunSpec]:
    sim_a = ROOT / "sim_scripts" / "stage2" / "A_randomized_rca_convergence"
    sim_b = ROOT / "sim_scripts" / "stage2" / "B_sum_conditioned_inverse_sampling"
    direct4 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_direct_adder4.vhd")
    direct8 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_direct_adder8.vhd")
    window4 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_windowed_integer_adder4.vhd")
    int_shadow4 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_shadow1_integer_adder4.vhd")
    int_shadow8 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_shadow1_integer_adder8.vhd")
    q34_direct4 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_direct_q34_adder4.vhd")
    q34_direct8 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_direct_q34_adder8.vhd")
    q34_shadow4 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_shadow1_q34_adder4.vhd")
    q34_shadow8 = pspath(ROOT / "experiments/stage2/A_randomized_rca_convergence/hardware/generated_benchmark_shadow1_q34_adder8.vhd")

    def spec(name: str, wrapper: str, *arguments: str) -> RunSpec:
        sim = sim_b if "_sum_" in wrapper or "sum_randomized_distribution" in wrapper else sim_a
        return RunSpec(name, sim / wrapper, tuple(arguments))

    return [
        spec("baseline_direct4", "run_adder4_direct_randomized_exhaustive.ps1", "-GeneratedNetworks", direct4, "-AdderRndWeight", "1", "-ScrambleCycles", "80", "-SettleCycles", "500", "-Trials", "100"),
        spec("scheduled_auxiliary_carry_integer4", "run_adder4_shadow1_randomized_exhaustive.ps1", "-GeneratedShadowVhdl", int_shadow4, "-BlockRndWeight", "1", "-CopyRndWeight", "0", "-ScrambleRndWeight", "2", "-ScrambleCycles", "80", "-Block0Cycles", "40", "-Block1Cycles", "40", "-Block2Cycles", "40", "-Block3Cycles", "40", "-CopyCycles", "2", "-Trials", "100", "-LegacyReplayTiming"),
        spec("quantized_coefficient_direct4", "run_adder4_direct_randomized_exhaustive.ps1", "-GeneratedNetworks", q34_direct4, "-AdderRndWeight", "4", "-ScrambleCycles", "80", "-SettleCycles", "500", "-Trials", "100"),
        spec("carry_ordered_schedule4", "run_adder4_windowed_randomized_exhaustive.ps1", "-GeneratedWindowedVhdl", window4, "-ActiveRndWeight", "1", "-FinalRndWeight", "1", "-ScrambleRndWeight", "2", "-ScrambleCycles", "80", "-Wave0Cycles", "40", "-Wave1Cycles", "40", "-Wave2Cycles", "40", "-Wave3Cycles", "40", "-FinalCycles", "0", "-Trials", "100"),
        spec("auxiliary_carry_parallel4", "run_adder4_shadow1_parallel_randomized_exhaustive.ps1", "-GeneratedShadowVhdl", int_shadow4, "-BlockRndWeight", "1", "-CopyRndWeight", "0", "-ScrambleRndWeight", "2", "-ScrambleCycles", "80", "-SettleCycles", "160", "-Trials", "100"),
        spec("quantized_scheduled_auxiliary_carry4", "run_adder4_shadow1_randomized_exhaustive.ps1", "-GeneratedShadowVhdl", q34_shadow4, "-BlockRndWeight", "4", "-CopyRndWeight", "0", "-ScrambleRndWeight", "8", "-ScrambleCycles", "80", "-Block0Cycles", "40", "-Block1Cycles", "40", "-Block2Cycles", "40", "-Block3Cycles", "40", "-CopyCycles", "2", "-Trials", "100"),
        spec("schedule_reduction_qsac_w10_8_16_6", "run_adder4_shadow1_randomized_exhaustive.ps1", "-GeneratedShadowVhdl", q34_shadow4, "-BlockRndWeight", "4", "-CopyRndWeight", "0", "-ScrambleRndWeight", "8", "-ScrambleCycles", "80", "-Block0Cycles", "10", "-Block1Cycles", "8", "-Block2Cycles", "16", "-Block3Cycles", "6", "-CopyCycles", "2", "-Trials", "100", "-ForwardOnly"),
        spec("schedule_reduction_qsac_w2_2_4_2", "run_adder4_shadow1_randomized_exhaustive.ps1", "-GeneratedShadowVhdl", q34_shadow4, "-BlockRndWeight", "4", "-CopyRndWeight", "0", "-ScrambleRndWeight", "8", "-ScrambleCycles", "80", "-Block0Cycles", "2", "-Block1Cycles", "2", "-Block2Cycles", "4", "-Block3Cycles", "2", "-CopyCycles", "2", "-Trials", "100", "-ForwardOnly"),
        spec("sum_baseline_direct4", "run_adder4_direct_sum_randomized_distribution.ps1", "-GeneratedNetworks", direct4, "-AdderRndWeight", "1", "-ScrambleCycles", "80", "-SettleCycles", "500", "-Trials", "1000"),
        spec("sum_scheduled_auxiliary_carry_integer4", "run_adder4_shadow1_sum_randomized_distribution.ps1", "-GeneratedShadowVhdl", int_shadow4, "-BlockRndWeight", "1", "-CopyRndWeight", "0", "-ScrambleRndWeight", "2", "-ScrambleCycles", "80", "-Block0Cycles", "40", "-Block1Cycles", "40", "-Block2Cycles", "40", "-Block3Cycles", "40", "-CopyCycles", "2", "-Trials", "1000"),
        spec("sum_quantized_scheduled_auxiliary_carry4", "run_adder4_shadow1_sum_randomized_distribution.ps1", "-GeneratedShadowVhdl", q34_shadow4, "-BlockRndWeight", "4", "-CopyRndWeight", "0", "-ScrambleRndWeight", "8", "-ScrambleCycles", "80", "-Block0Cycles", "10", "-Block1Cycles", "8", "-Block2Cycles", "16", "-Block3Cycles", "6", "-CopyCycles", "2", "-Trials", "1000"),
        spec("sum_quantized_scheduled_auxiliary_carry_reverse40_4", "run_adder4_shadow1_sum_randomized_distribution.ps1", "-GeneratedShadowVhdl", q34_shadow4, "-BlockRndWeight", "4", "-CopyRndWeight", "0", "-ScrambleRndWeight", "8", "-ScrambleCycles", "80", "-Block0Cycles", "40", "-Block1Cycles", "40", "-Block2Cycles", "40", "-Block3Cycles", "40", "-CopyCycles", "2", "-Trials", "1000", "-ReverseOrder"),
        spec("sum_auxiliary_carry_parallel4", "run_adder4_shadow1_sum_randomized_distribution.ps1", "-GeneratedShadowVhdl", int_shadow4, "-BlockRndWeight", "1", "-CopyRndWeight", "0", "-ScrambleRndWeight", "2", "-ScrambleCycles", "80", "-SettleCycles", "160", "-Trials", "1000", "-ParallelMode"),
        spec("sum_quantized_auxiliary_carry_parallel4", "run_adder4_shadow1_sum_randomized_distribution.ps1", "-GeneratedShadowVhdl", q34_shadow4, "-BlockRndWeight", "4", "-CopyRndWeight", "0", "-ScrambleRndWeight", "8", "-ScrambleCycles", "80", "-SettleCycles", "160", "-Trials", "1000", "-ParallelMode"),
        spec("baseline_direct8", "run_adder8_direct_repeated_solve.ps1", "-GeneratedNetworks", direct8, "-AdderRndWeight", "1", "-ScrambleCycles", "80", "-SettleCycles", "500", "-Trials", "100"),
        spec("quantized_coefficient_direct8", "run_adder8_direct_repeated_solve.ps1", "-GeneratedNetworks", q34_direct8, "-AdderRndWeight", "4", "-ScrambleCycles", "80", "-SettleCycles", "500", "-Trials", "100"),
        spec("scheduled_auxiliary_carry_integer8", "run_adder8_shadow1_repeated_solve.ps1", "-GeneratedShadowVhdl", int_shadow8, "-BlockRndWeight", "1", "-CopyRndWeight", "0", "-ScrambleRndWeight", "2", "-ScrambleCycles", "80", "-Block0Cycles", "40", "-Block1Cycles", "40", "-Block2Cycles", "40", "-Block3Cycles", "40", "-Block4Cycles", "40", "-Block5Cycles", "40", "-Block6Cycles", "40", "-Block7Cycles", "40", "-CopyCycles", "2", "-Trials", "100"),
        spec("quantized_scheduled_auxiliary_carry8", "run_adder8_shadow1_repeated_solve.ps1", "-GeneratedShadowVhdl", q34_shadow8, "-BlockRndWeight", "4", "-CopyRndWeight", "0", "-ScrambleRndWeight", "8", "-ScrambleCycles", "80", "-Block0Cycles", "40", "-Block1Cycles", "40", "-Block2Cycles", "40", "-Block3Cycles", "40", "-Block4Cycles", "40", "-Block5Cycles", "40", "-Block6Cycles", "40", "-Block7Cycles", "40", "-CopyCycles", "2", "-Trials", "100"),
    ]


def comb6_run_specs(golden: dict) -> list[RunSpec]:
    sim = ROOT / "sim_scripts" / "stage1" / "C_combinational_gap_equalization"
    wrapper = sim / "run_comb6_diagnostics.ps1"
    integer = pspath(ROOT / golden["comb6_sources"]["integer"]["path"])
    e3m4 = pspath(ROOT / golden["comb6_sources"]["e3m4"]["path"])
    return [
        RunSpec("comb6_integer_1000", wrapper, ("-GeneratedNetworks", integer, "-CombRndWeight", "1", "-SettleCycles", "1000", "-CountCycles", "1000")),
        RunSpec("comb6_integer_20000", wrapper, ("-GeneratedNetworks", integer, "-CombRndWeight", "1", "-SettleCycles", "20000", "-CountCycles", "1000")),
        RunSpec("comb6_e3m4_1000", wrapper, ("-GeneratedNetworks", e3m4, "-CombRndWeight", "16", "-SettleCycles", "1000", "-CountCycles", "1000")),
        RunSpec("comb6_e3m4_5000", wrapper, ("-GeneratedNetworks", e3m4, "-CombRndWeight", "16", "-SettleCycles", "5000", "-CountCycles", "1000")),
        RunSpec("comb6_e3m4_20000", wrapper, ("-GeneratedNetworks", e3m4, "-CombRndWeight", "16", "-SettleCycles", "20000", "-CountCycles", "1000")),
    ]


def parse_comb6(text: str) -> Comb6Metrics:
    rows = [match.groupdict() for match in COMB6_LINE_RE.finditer(text)]
    if len(rows) != 64:
        raise ReproductionError(f"COMB6 transcript has {len(rows)} case rows; expected 64")
    inputs = [int(row["input"]) for row in rows]
    if sorted(inputs) != list(range(64)):
        raise ReproductionError("COMB6 transcript does not contain each input 0..63 exactly once")
    sample_counts = {int(row["samples"]) for row in rows}
    if len(sample_counts) != 1:
        raise ReproductionError(f"COMB6 transcript has inconsistent sample counts: {sample_counts}")
    metrics = Comb6Metrics(
        top_matches=sum(int(row["top"]) == int(row["expected"]) for row in rows),
        zero_hit_cases=sum(int(row["hits"]) == 0 for row in rows),
        min_hits=min(int(row["hits"]) for row in rows),
        total_hits=sum(int(row["hits"]) for row in rows),
        sample_count=next(iter(sample_counts)),
        cases=64,
    )
    summaries = list(COMB6_SUMMARY_RE.finditer(text))
    if len(summaries) != 1:
        raise ReproductionError(f"COMB6 transcript has {len(summaries)} summary rows; expected one")
    reported_min = int(summaries[0].group("min_hits"))
    reported_samples = int(summaries[0].group("samples"))
    if (reported_min, reported_samples) != (metrics.min_hits, metrics.sample_count):
        raise ReproductionError("COMB6 summary disagrees with its 64 case rows")
    if "tb_comb6_diagnostics completed" not in text:
        raise ReproductionError("COMB6 completion marker is missing")
    return metrics


def validate_comb6(name: str, metrics: Comb6Metrics, expected: dict) -> None:
    for field in ("top_matches", "zero_hit_cases", "min_hits", "total_hits"):
        if field in expected and getattr(metrics, field) != expected[field]:
            raise ReproductionError(
                f"{name} {field}: expected {expected[field]}, got {getattr(metrics, field)}"
            )
    if metrics.sample_count != 1000:
        raise ReproductionError(f"{name} samples per case: expected 1000, got {metrics.sample_count}")
    assert_float(metrics.average_hits, expected["average_hits"], f"{name} average hits")


def unique_rows(rows: Iterable[dict], key_fields: Sequence[str], label: str) -> dict[tuple, dict]:
    result: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        if key in result:
            raise ReproductionError(f"Duplicate {label} row for {key}")
        result[key] = row
    return result


def assert_float(actual: float, expected: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=FLOAT_TOLERANCE):
        raise ReproductionError(f"{label}: expected {expected:.12g}, got {actual:.12g}")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_benchmark(
    *,
    golden: dict,
    case_rows: list[dict],
    summary_rows: list[dict],
    repeat8_rows: list[dict],
    sum_by_sum_rows: list[dict],
    sum_aggregate_rows: list[dict],
    window_rows: list[dict[str, str]],
) -> dict:
    summaries = unique_rows(summary_rows, ("run", "direction"), "4-bit summary")
    expected_summary_keys = {
        (run, direction)
        for run, directions in golden["adder4"].items()
        for direction in directions
        if direction in {"forward", "inverse_bsum"}
    }
    if set(summaries) != expected_summary_keys:
        raise ReproductionError(
            f"4-bit summary key mismatch: expected {sorted(expected_summary_keys)}, got {sorted(summaries)}"
        )
    for run, directions in golden["adder4"].items():
        for direction, pair in directions.items():
            if direction.startswith("min_hits_"):
                continue
            row = summaries[(run, direction)]
            hits, trials = pair
            if (row["hits"], row["trials_total"], row["cases"]) != (hits, trials, 256):
                raise ReproductionError(
                    f"{run}/{direction}: expected {hits}/{trials} over 256 cases, got "
                    f"{row['hits']}/{row['trials_total']} over {row['cases']}"
                )
            assert_float(row["success_probability"], hits / trials, f"{run}/{direction} rate")
        for direction in ("forward", "inverse_bsum"):
            min_key = f"min_hits_{direction}"
            if min_key in directions and summaries[(run, direction)]["min_hits"] != directions[min_key]:
                raise ReproductionError(
                    f"{run}/{direction} min hits: expected {directions[min_key]}, "
                    f"got {summaries[(run, direction)]['min_hits']}"
                )

    cases_by_summary: dict[tuple[str, str], list[dict]] = {}
    for row in case_rows:
        cases_by_summary.setdefault((row["run"], row["direction"]), []).append(row)
    if set(cases_by_summary) != expected_summary_keys:
        raise ReproductionError("4-bit case rows do not cover exactly the accepted run/direction pairs")
    for key, rows in cases_by_summary.items():
        expected_pairs = {(a, b) for a in range(16) for b in range(16)}
        actual_pairs = {(row["a"], row["b"]) for row in rows}
        if len(rows) != 256 or actual_pairs != expected_pairs:
            raise ReproductionError(f"{key} does not contain all 256 A/B cases exactly once")

    windows = unique_rows(window_rows, ("run",), "window")
    if set(key[0] for key in windows) != set(golden["windows"]):
        raise ReproductionError("Window results do not contain exactly the three core schedules")
    for run, (hits, trials) in golden["windows"].items():
        row = windows[(run,)]
        actual_hits = int(row["hits"])
        actual_trials = int(row["trials_total"])
        if (actual_hits, actual_trials) != (hits, trials):
            raise ReproductionError(f"{run}: expected {hits}/{trials}, got {actual_hits}/{actual_trials}")
        assert_float(float(row["success_rate"]), hits / trials, f"{run} rate")

    sums = unique_rows(sum_aggregate_rows, ("run",), "SUM-only aggregate")
    if set(key[0] for key in sums) != set(golden["sum_only"]):
        raise ReproductionError("SUM-only aggregates do not contain exactly the six core runs")
    by_sum_counts: dict[str, int] = {}
    by_sum_rows: dict[str, list[dict]] = {}
    for row in sum_by_sum_rows:
        by_sum_counts[row["run"]] = by_sum_counts.get(row["run"], 0) + 1
        by_sum_rows.setdefault(row["run"], []).append(row)
    if set(by_sum_rows) != set(golden["sum_only"]):
        raise ReproductionError("SUM-only by-SUM rows do not contain exactly the six core runs")
    for run, (valid, coverage, zero_sums) in golden["sum_only"].items():
        row = sums[(run,)]
        actual = (row["valid_total"], row["valid_pairs_seen"], row["zero_valid_sums"])
        if actual != (valid, coverage, zero_sums):
            raise ReproductionError(
                f"{run}: expected SUM tuple {(valid, coverage, zero_sums)}, got {actual}"
            )
        if row["trials"] != 31000 or by_sum_counts.get(run) != 31:
            raise ReproductionError(f"{run}: expected 31 sums and 31,000 trials")
        per_sum_rows = by_sum_rows[run]
        target_sums = [int(item["sum"]) for item in per_sum_rows]
        if sorted(target_sums) != list(range(31)):
            raise ReproductionError(f"{run}: expected each target SUM 0..30 exactly once")
        for item in per_sum_rows:
            trials = int(item["trials"])
            valid_total = int(item["valid_total"])
            invalid_total = int(item["invalid_total"])
            if trials != 1000 or valid_total + invalid_total != trials:
                raise ReproductionError(
                    f"{run}/SUM={item['sum']}: expected 1,000 partitioned trials"
                )
        assert_float(row["valid_rate"], valid / 31000, f"{run} valid rate")
        assert_float(row["coverage_rate"], coverage / 256, f"{run} coverage rate")

    repeats = unique_rows(repeat8_rows, ("run", "a", "b"), "8-bit vector")
    aggregate: dict[str, int] = {}
    count: dict[str, int] = {}
    for row in repeat8_rows:
        aggregate[row["run"]] = aggregate.get(row["run"], 0) + row["hits"]
        count[row["run"]] = count.get(row["run"], 0) + row["trials"]
        assert_float(row["success_probability"], row["hits"] / row["trials"], "8-bit vector rate")
    if aggregate != golden["adder8"]["aggregate_hits"]:
        raise ReproductionError(
            f"8-bit aggregates: expected {golden['adder8']['aggregate_hits']}, got {aggregate}"
        )
    if any(value != golden["adder8"]["trials_per_run"] for value in count.values()):
        raise ReproductionError(f"8-bit trial totals are not all {golden['adder8']['trials_per_run']}")
    expected_vectors = [tuple(vector) for vector in golden["adder8"]["vector_inputs"]]
    rows_by_run: dict[str, list[dict]] = {}
    for row in repeat8_rows:
        rows_by_run.setdefault(row["run"], []).append(row)
    if set(rows_by_run) != set(golden["adder8"]["aggregate_hits"]):
        raise ReproductionError("8-bit rows do not contain exactly the four core runs")
    for run, rows in rows_by_run.items():
        vector_map = {
            (row["a"], row["b"], row["expected"]): row
            for row in rows
        }
        if set(vector_map) != set(expected_vectors) or len(rows) != len(expected_vectors):
            raise ReproductionError(f"{run}: fixed 8-bit vector set mismatch")
        if any(
            row["trials"] != golden["adder8"]["trials_per_vector"]
            for row in rows
        ):
            raise ReproductionError(
                f"{run}: expected {golden['adder8']['trials_per_vector']} trials per fixed vector"
            )
    combined_map = {
        (row["a"], row["b"], row["expected"]): row["hits"]
        for row in rows_by_run["quantized_scheduled_auxiliary_carry8"]
    }
    combined_hits = [combined_map[vector] for vector in expected_vectors]
    if combined_hits != golden["adder8"]["combined_vectors"]:
        raise ReproductionError(
            f"8-bit combined vector hits: expected {golden['adder8']['combined_vectors']}, got {combined_hits}"
        )

    # Claims are acceptance assertions, not prose inferred from an exit code.
    direct = summaries[("baseline_direct4", "forward")]["hits"]
    quantized_coefficient = summaries[("quantized_coefficient_direct4", "forward")]["hits"]
    combined_forward = summaries[("quantized_scheduled_auxiliary_carry4", "forward")]["hits"]
    combined_inverse = summaries[("quantized_scheduled_auxiliary_carry4", "inverse_bsum")]["hits"]
    forward_ablations = [
        summaries[(name, "forward")]["hits"]
        for name in ("baseline_direct4", "quantized_coefficient_direct4", "carry_ordered_schedule4", "auxiliary_carry_parallel4", "scheduled_auxiliary_carry_integer4")
    ]
    inverse_ablations = [
        summaries[(name, "inverse_bsum")]["hits"]
        for name in ("carry_ordered_schedule4", "auxiliary_carry_parallel4", "scheduled_auxiliary_carry_integer4")
    ]
    if not quantized_coefficient < direct:
        raise ReproductionError("Conclusion failed: Quantized coefficient scaling alone is not weaker than the direct baseline")
    if not combined_forward > max(forward_ablations) or not combined_inverse > max(inverse_ablations):
        raise ReproductionError("Conclusion failed: combined Quantized scheduled auxiliary-carry architecture does not beat every ablation")
    if not all(int(windows[(name,)]["hits"]) > direct for name in ("w10_8_16_6", "w2_2_4_2")):
        raise ReproductionError("Conclusion failed: a shortened schedule does not beat the direct baseline")
    if not sums[("sum_baseline_direct4",)]["valid_total"] == max(row["valid_total"] for row in sum_aggregate_rows):
        raise ReproductionError("Conclusion failed: direct SUM-only validity is not best")
    reverse = sums[("sum_quantized_scheduled_auxiliary_carry_reverse40_4",)]
    forward = sums[("sum_quantized_scheduled_auxiliary_carry4",)]
    if not reverse["valid_pairs_seen"] > forward["valid_pairs_seen"] or reverse["zero_valid_sums"] != 0:
        raise ReproductionError("Conclusion failed: reverse SUM schedule does not restore coverage/zero sums")
    if aggregate["quantized_scheduled_auxiliary_carry8"] != 596 or min(combined_hits) < 98:
        raise ReproductionError("Conclusion failed: 8-bit combined acceptance is not 596/600 with min 98/100")

    return {
        "adder4": {f"{run}/{direction}": row["hits"] for (run, direction), row in summaries.items()},
        "sum_only": {run[0]: sums[run]["valid_total"] for run in sums},
        "adder8": aggregate,
        "windows": {run[0]: int(windows[run]["hits"]) for run in windows},
    }


def validate_zero_error_summary(name: str, text: str, marker: str) -> None:
    if marker.lower() not in text.lower():
        raise ReproductionError(f"{name} completion marker is missing: {marker!r}")
    summaries = list(SIM_SUMMARY_RE.finditer(text))
    if not summaries:
        raise ReproductionError(f"{name} has no Questa error/warning summary")
    final = summaries[-1]
    if int(final.group("errors")) != 0 or int(final.group("warnings")) != 0:
        raise ReproductionError(
            f"{name} ended with Errors={final.group('errors')}, Warnings={final.group('warnings')}"
        )


def validate_optimizer_audit(text: str) -> None:
    markers = (
        "OPTIMIZER_AUDIT HA valid_energy=-2 gap=1 invalid_local_minima=0 states=16",
        "OPTIMIZER_AUDIT FA valid_energy=-2 gap=1 invalid_local_minima=0 states=32",
        "RTL_SCALE_AUDIT HA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=16",
        "RTL_SCALE_AUDIT FA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=32",
        "tb_optimizer_energy_audit passed",
    )
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise ReproductionError(f"optimizer energy audit is missing markers: {missing}")
    validate_zero_error_summary("optimizer energy audit", text, markers[-1])


def git_identity() -> tuple[str, bool]:
    base = ["git", "-c", "safe.directory=C:/Projects/stochastic-circuits-experiments"]
    try:
        revision = subprocess.run(
            [*base, "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True, timeout=30
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                [*base, "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True, timeout=30
            ).stdout.strip()
        )
        return revision, dirty
    except (OSError, subprocess.SubprocessError) as exc:
        raise ReproductionError(f"Cannot record Git identity: {exc}") from exc


def prepare_candidate(stage: Path) -> tuple[Path, Path]:
    candidate_root = stage / "candidate"
    candidate_benchmark = candidate_root / "rca_convergence_benchmark"
    candidate_comb6 = candidate_root / "comb6_equal_gap_report.md"
    if candidate_root.exists():
        raise ReproductionError(f"Staging path already exists: {candidate_root}")
    candidate_root.mkdir(parents=True)
    candidate_benchmark.mkdir()
    # Runs and exploratory scratch directories now share the experiment root.
    # Only curated evidence belongs in a publication transaction.
    for name in BENCHMARK_ARTIFACTS:
        source = BENCHMARK_REPORT / name
        destination = candidate_benchmark / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    shutil.copy2(COMB6_REPORT, candidate_comb6)
    traces = candidate_benchmark / "traces"
    ensure_inside(traces, stage)
    if traces.exists():
        shutil.rmtree(traces)
    traces.mkdir(parents=True)
    return candidate_benchmark, candidate_comb6


def update_manifest(
    manifest: dict,
    *,
    source_hashes: dict[str, str],
    simulator_version: str,
    reproduced_at: str,
    revision: str,
    dirty: bool,
) -> dict:
    updated = json.loads(json.dumps(manifest))
    for artifact in updated["artifacts"].values():
        artifact["sha256"] = source_hashes[artifact["path"]]
    updated.update(
        {
            "simulator": "QuestaSim",
            "simulator_version": simulator_version,
            "seed_mode": "replay",
            "replay_compatibility": {
                "testbench_timing": HISTORICAL_TIMING_REPLAY,
            },
            "git_revision": revision,
            "git_dirty": dirty,
            "reproduced_at_utc": reproduced_at,
            "source_sha256": source_hashes,
        }
    )
    return updated


def render_comb6_report(
    source: str,
    *,
    metrics: dict[str, Comb6Metrics],
    simulator_version: str,
    reproduced_at: str,
    revision: str,
) -> str:
    date = reproduced_at[:10]
    provenance = (
        f"Date: {date}\n\n"
        f"Simulator: `{simulator_version}`\n\n"
        f"Reproduction: fixed committed VHDL replay at Git `{revision}`; no new seed salt was generated.\n"
    )
    source = re.sub(r"Date: .*?(?=\n\n)", provenance.rstrip(), source, count=1)
    labels = [
        ("Integer baseline, RND=1, SETTLE=1000", "comb6_integer_1000"),
        ("Integer baseline, RND=1, SETTLE=20000", "comb6_integer_20000"),
        ("E3M4 equal-gap, RND=16, SETTLE=1000", "comb6_e3m4_1000"),
        ("E3M4 equal-gap, RND=16, SETTLE=5000", "comb6_e3m4_5000"),
        ("E3M4 equal-gap, RND=16, SETTLE=20000", "comb6_e3m4_20000"),
    ]
    blocks: list[str] = []
    for label, name in labels:
        item = metrics[name]
        fields = [
            f"top_matches={item.top_matches}/64",
            f"zero_hit_cases={item.zero_hit_cases}",
        ]
        if name == "comb6_e3m4_20000":
            fields.append(f"min_hits={item.min_hits}/{item.sample_count}")
        fields.append(f"avg_hits={item.average_hits:.1f}/{item.sample_count}")
        blocks.append(f"{label}:\n{', '.join(fields)}")
    result_block = "```text\n" + "\n\n".join(blocks) + "\n```"
    pattern = re.compile(
        r"```text\nInteger baseline, RND=1, SETTLE=1000:.*?\n```",
        re.DOTALL,
    )
    updated, count = pattern.subn(result_block, source, count=1)
    if count != 1:
        raise ReproductionError("Could not locate the COMB6 results block for staged update")
    return updated


def publish_transaction(candidates: Sequence[tuple[Path, Path]], stage: Path) -> None:
    """Replace report targets with rollback; candidates and targets must share a volume."""

    backup_root = stage / "publish_backup"
    backup_root.mkdir()
    backups: list[tuple[Path, Path]] = []
    installed: list[tuple[Path, Path]] = []
    for _candidate, target in candidates:
        ensure_inside(target, REPORTS)
        if not target.exists():
            raise ReproductionError(f"Refusing to publish over missing report target: {target}")
    try:
        for index, (_candidate, target) in enumerate(candidates):
            backup = backup_root / f"{index}-{target.name}"
            os.replace(target, backup)
            backups.append((backup, target))
        for candidate, target in candidates:
            os.replace(candidate, target)
            installed.append((target, candidate))
    except BaseException:
        for target, recovery in reversed(installed):
            if target.exists():
                os.replace(target, recovery)
        for backup, target in reversed(backups):
            if backup.exists():
                os.replace(backup, target)
        raise
    for backup, _target in backups:
        try:
            if backup.is_dir():
                shutil.rmtree(backup)
            elif backup.exists():
                backup.unlink()
        except OSError as exc:
            print(f"WARNING: published reports, but could not remove backup {backup}: {exc}", file=sys.stderr)
    try:
        backup_root.rmdir()
    except OSError:
        # A retained backup is recoverable and must not turn a successful,
        # fully installed transaction into a reported compatibility-validation failure.
        pass


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=["core"], default="core")
    parser.add_argument("--seed-mode", choices=["replay"], default="replay")
    parser.add_argument("--simulator", choices=["questa"], default="questa")
    parser.add_argument("--update-reports", action="store_true")
    parser.add_argument("--vsim-path")
    license_group = parser.add_mutually_exclusive_group()
    license_group.add_argument("--license-file")
    license_group.add_argument("--license-server")
    parser.add_argument(
        "--build-root",
        type=Path,
        default=REPORTS / "stage4" / "B_fixed_seed_compatibility_validation" / "runs",
    )
    parser.add_argument("--run-id")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument(
        "--preflight",
        "--dry-run",
        dest="preflight",
        action="store_true",
        help="validate frozen inputs, tool identity, and required entrypoints without running simulation",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout_seconds <= 0:
        raise ReproductionError("--timeout-seconds must be positive")
    started = utc_now()
    default_id = f"core-{started.strftime('%Y%m%dT%H%M%SZ')}-{os.getpid()}"
    run_id = clean_run_id(args.run_id or default_id)
    build_root = ensure_inside((args.build_root if args.build_root.is_absolute() else ROOT / args.build_root), ROOT)
    manifest, golden, source_hashes = verify_replay_inputs()
    vsim_path, simulator_version = resolve_questa_vsim(args.vsim_path)
    planned_specs = [
        RunSpec(
            "optimizer_energy_audit",
            ROOT / "sim_scripts/stage3/B_verified_pairwise_optimizer_successor/run_questa_audit.ps1",
            ("-PythonPath", sys.executable),
        ),
        RunSpec(
            "generated_gates",
            ROOT / "sim_scripts/stage3/B_verified_pairwise_optimizer_successor/run_generated_gates_audit.ps1",
            ("-PythonPath", sys.executable),
        ),
        *comb6_run_specs(golden),
        *benchmark_run_specs(),
    ]
    missing_wrappers = sorted({str(spec.wrapper) for spec in planned_specs if not spec.wrapper.is_file()})
    if missing_wrappers:
        raise ReproductionError(f"Required simulation wrappers are missing: {missing_wrappers}")
    if args.preflight:
        print(f"Preflight passed: {len(source_hashes)} frozen VHDL hashes and seed signatures match.")
        print(f"Questa identity: {simulator_version} ({vsim_path})")
        print(f"Planned simulations: {len(planned_specs)}")
        for spec in planned_specs:
            print(f"  {spec.name}: {spec.wrapper.relative_to(ROOT)}")
        print("No simulation was run and no report was modified.")
        return 0

    stage = build_root / "compatibility_validation" / run_id
    if stage.exists():
        raise ReproductionError(f"Run staging directory already exists: {stage}")
    stage.mkdir(parents=True)

    revision, dirty = git_identity()
    candidate_benchmark, candidate_comb6 = prepare_candidate(stage)
    traces = candidate_benchmark / "traces"
    powershell = powershell_executable()
    print(f"Frozen replay inputs verified; Questa: {simulator_version}", flush=True)
    print(f"Staging reports under {stage}", flush=True)

    common = {
        "powershell": powershell,
        "simulator": args.simulator,
        "vsim_path": vsim_path,
        "build_root": build_root,
        "run_id_prefix": run_id,
        "timeout_seconds": args.timeout_seconds,
        "license_file": args.license_file,
        "license_server": args.license_server,
        "traces": traces,
    }

    optimizer = planned_specs[0]
    optimizer_output = run_spec(optimizer, **common)
    optimizer_run_id = f"{run_id}-{optimizer.name}"
    optimizer_transcript_path = runner_transcript(build_root, optimizer_run_id)
    optimizer_transcript = optimizer_transcript_path.read_text(encoding="utf-8", errors="replace")
    write_normalized_transcript(traces / "optimizer_energy_audit.txt", optimizer_transcript)
    validate_optimizer_audit(optimizer_transcript)

    gates = planned_specs[1]
    gates_output = run_spec(gates, **common)
    gates_run_id = f"{run_id}-{gates.name}"
    gates_transcript_path = runner_transcript(build_root, gates_run_id)
    gates_transcript = gates_transcript_path.read_text(encoding="utf-8", errors="replace")
    write_normalized_transcript(traces / "generated_gates.txt", gates_transcript)
    validate_zero_error_summary("generated gates", gates_transcript, "tb_generated_gates passed")

    comb_metrics: dict[str, Comb6Metrics] = {}
    for spec in comb6_run_specs(golden):
        output = run_spec(spec, **common)
        metrics = parse_comb6(output)
        validate_comb6(spec.name, metrics, golden["comb6"][spec.name])
        comb_metrics[spec.name] = metrics

    benchmark_runs: dict[str, str] = {}
    for spec in benchmark_run_specs():
        benchmark_runs[spec.name] = run_spec(spec, **common)

    # The conservative 40-cycle main run also supplies the third core window row;
    # aliasing its transcript avoids a redundant 256x100 simulation.
    parse_runs = dict(benchmark_runs)
    parse_runs["schedule_reduction_qsac_w40_40_40_40"] = benchmark_runs["quantized_scheduled_auxiliary_carry4"]
    benchmark.configure_output_root(candidate_benchmark)
    (
        case_rows,
        summary_rows,
        repeat8_rows,
        sum_by_sum_rows,
        _sum_pair_rows,
        sum_aggregate_rows,
    ) = benchmark.parse_outputs(parse_runs)
    window_rows = read_csv_rows(candidate_benchmark / "data/quantized_scheduled_auxiliary_carry_window_sweep.csv")
    acceptance = validate_benchmark(
        golden=golden,
        case_rows=case_rows,
        summary_rows=summary_rows,
        repeat8_rows=repeat8_rows,
        sum_by_sum_rows=sum_by_sum_rows,
        sum_aggregate_rows=sum_aggregate_rows,
        window_rows=window_rows,
    )

    benchmark.write_gate_visualizations()
    figures = benchmark.make_figures(
        case_rows, summary_rows, repeat8_rows, sum_by_sum_rows, sum_aggregate_rows
    )
    reproduced_at = utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    updated_manifest = update_manifest(
        manifest,
        source_hashes=source_hashes,
        simulator_version=simulator_version,
        reproduced_at=reproduced_at,
        revision=revision,
        dirty=dirty,
    )
    (candidate_benchmark / "data/manifest.json").write_text(
        json.dumps(updated_manifest, indent=2) + "\n", encoding="utf-8"
    )
    benchmark.write_report(
        updated_manifest,
        summary_rows,
        repeat8_rows,
        sum_aggregate_rows,
        figures,
        simulator_name="QuestaSim",
        simulator_version=simulator_version,
        seed_mode="replay",
        reproduced_at=reproduced_at,
        git_revision=revision,
    )
    candidate_comb6.write_text(
        render_comb6_report(
            candidate_comb6.read_text(encoding="utf-8"),
            metrics=comb_metrics,
            simulator_version=simulator_version,
            reproduced_at=reproduced_at,
            revision=revision,
        ),
        encoding="utf-8",
    )

    summary = {
        "schema_version": 1,
        "suite": args.suite,
        "seed_mode": args.seed_mode,
        "simulator": "QuestaSim",
        "simulator_version": simulator_version,
        "replay_compatibility": {
            "testbench_timing": HISTORICAL_TIMING_REPLAY,
        },
        "git_revision": revision,
        "git_dirty": dirty,
        "started_at_utc": started.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "completed_at_utc": reproduced_at,
        "source_sha256": source_hashes,
        "comb6": {name: metrics.__dict__ for name, metrics in comb_metrics.items()},
        "acceptance": acceptance,
        "report_update_requested": args.update_reports,
    }
    (stage / "compatibility_validation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    if args.update_reports:
        publish_transaction(
            [(candidate_benchmark / name, BENCHMARK_REPORT / name)
             for name in BENCHMARK_ARTIFACTS] + [(candidate_comb6, COMB6_REPORT)],
            stage,
        )
        print("All migration goldens passed; RCA benchmark and COMB6 reports were updated transactionally.")
    else:
        print(f"All goldens passed; staged reports were not published: {stage / 'candidate'}")
    print(f"Compatibility-validation summary: {stage / 'compatibility_validation_summary.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReproductionError as exc:
        print(f"COMPATIBILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
