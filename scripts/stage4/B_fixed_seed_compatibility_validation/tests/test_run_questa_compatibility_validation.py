from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPTS = _REPO_ROOT / "scripts"
ROOT = _REPO_ROOT
sys.path.insert(0, str(SCRIPTS))

import scripts.stage2.run_rca_convergence_benchmark as presentation
import scripts.stage4.B_fixed_seed_compatibility_validation.run_questa_compatibility_validation as reproduction
def csv_rows(path: Path, integer_fields=(), float_fields=()):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for field in integer_fields:
            row[field] = int(row[field])
        for field in float_fields:
            row[field] = float(row[field])
    return rows


def committed_acceptance_inputs():
    data = ROOT / "results_and_reports/stage2/rca_convergence_benchmark/data"
    case_rows = csv_rows(
        data / "adder4_cases.csv",
        integer_fields=("a", "b", "target", "hits", "trials", "top", "top_count"),
        float_fields=("success_probability",),
    )
    summary_rows = csv_rows(
        data / "adder4_summary.csv",
        integer_fields=("cases", "hits", "trials_total", "per_case_trials", "min_hits", "fail_cases"),
        float_fields=("success_probability",),
    )
    repeat_rows = csv_rows(
        data / "adder8_repeated.csv",
        integer_fields=("a", "b", "expected", "hits", "trials", "distinct_sums"),
        float_fields=("success_probability",),
    )
    sum_by_rows = csv_rows(data / "sum_only_by_sum.csv")
    sum_aggregate_rows = csv_rows(
        data / "sum_only_aggregate.csv",
        integer_fields=(
            "valid_total",
            "trials",
            "valid_pairs_seen",
            "valid_pairs_total",
            "sums_below_90pct_valid",
            "zero_valid_sums",
        ),
        float_fields=("valid_rate", "coverage_rate"),
    )
    wanted_windows = {"w40_40_40_40", "w10_8_16_6", "w2_2_4_2"}
    window_rows = [
        row
        for row in csv_rows(data / "quantized_scheduled_auxiliary_carry_window_sweep.csv")
        if row["run"] in wanted_windows
    ]
    return {
        "case_rows": case_rows,
        "summary_rows": summary_rows,
        "repeat8_rows": repeat_rows,
        "sum_by_sum_rows": sum_by_rows,
        "sum_aggregate_rows": sum_aggregate_rows,
        "window_rows": window_rows,
    }


class ReplayInputTests(unittest.TestCase):
    def test_committed_manifest_hashes_and_seed_signatures(self):
        manifest, golden, hashes = reproduction.verify_replay_inputs()
        self.assertEqual(set(manifest["artifacts"]), set(golden["artifacts"]))
        self.assertEqual(len(hashes), 11)

    def test_preflight_alias_is_safe(self):
        args = reproduction.parse_args(["--dry-run"])
        self.assertTrue(args.preflight)
        self.assertFalse(args.update_reports)

    def test_core_plan_has_only_selected_window_sweeps(self):
        names = [spec.name for spec in reproduction.benchmark_run_specs()]
        sweep_names = [name for name in names if name.startswith("schedule_reduction_qsac_")]
        self.assertEqual(
            sweep_names,
            ["schedule_reduction_qsac_w10_8_16_6", "schedule_reduction_qsac_w2_2_4_2"],
        )
        self.assertEqual(len(names), 18)

    def test_historical_shadow_replays_explicitly_enable_legacy_timing(self):
        specs = reproduction.benchmark_run_specs()
        legacy_names = {
            spec.name for spec in specs if "-LegacyReplayTiming" in spec.arguments
        }
        self.assertEqual(
            legacy_names,
            {"scheduled_auxiliary_carry_integer4"},
        )
        for spec in specs:
            if spec.name in legacy_names:
                self.assertEqual(
                    spec.wrapper.name,
                    "run_adder4_shadow1_randomized_exhaustive.ps1",
                )

    def test_shadow_wrapper_and_simulation_default_to_nonlegacy_timing(self):
        wrapper = (ROOT / "sim_scripts/stage2/A_randomized_rca_convergence/run_adder4_shadow1_randomized_exhaustive.ps1").read_text(
            encoding="utf-8"
        )
        do_file = (ROOT / "sim_scripts/stage2/A_randomized_rca_convergence/run_adder4_shadow1_randomized_exhaustive.do").read_text(
            encoding="utf-8"
        )
        self.assertIn("[switch]$LegacyReplayTiming", wrapper)
        self.assertIn(
            '$env:LEGACY_REPLAY_TIMING = if ($LegacyReplayTiming) { "true" } else { "false" }',
            wrapper,
        )
        self.assertIn(
            '$env:RUN_INVERSE = if ($ForwardOnly) { "false" } else { "true" }',
            wrapper,
        )
        self.assertIn("set legacy_replay_timing false", do_file)
        self.assertIn('if {$legacy_replay_timing eq "true"}', do_file)

    def test_manifest_artifact_payload_drift_is_rejected(self):
        manifest = json.loads(reproduction.SOURCE_MANIFEST.read_text(encoding="utf-8"))
        manifest["artifacts"]["direct_adder4"]["entity"] = "wrong_entity"
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(reproduction, "SOURCE_MANIFEST", path):
                with self.assertRaises(reproduction.ReproductionError):
                    reproduction.verify_replay_inputs()

    def test_manifest_weight_payload_drift_is_rejected(self):
        manifest = json.loads(reproduction.SOURCE_MANIFEST.read_text(encoding="utf-8"))
        manifest["q34_weights"]["ha"]["gap_encoded"] += 1
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(reproduction, "SOURCE_MANIFEST", path):
                with self.assertRaises(reproduction.ReproductionError):
                    reproduction.verify_replay_inputs()

    def test_reproduced_manifest_sha_fields_remain_replayable(self):
        manifest = json.loads(reproduction.SOURCE_MANIFEST.read_text(encoding="utf-8"))
        golden = json.loads(reproduction.GOLDEN_PATH.read_text(encoding="utf-8"))
        for name, artifact in manifest["artifacts"].items():
            artifact["sha256"] = golden["artifacts"][name]["sha256"]
        manifest["simulator"] = "QuestaSim"
        manifest["reproduced_at_utc"] = "2026-09-16T00:00:00Z"
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            path = Path(temp) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(reproduction, "SOURCE_MANIFEST", path):
                reproduction.verify_replay_inputs()


class QuestaResolutionTests(unittest.TestCase):
    def test_explicit_install_root_resolves_win64_vsim(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            install = Path(temp) / "questasim64_2024.1"
            executable = install / "win64/vsim.exe"
            executable.parent.mkdir(parents=True)
            executable.write_text("fake", encoding="utf-8")
            root_executable = install / "vsim.exe"
            root_executable.write_text("fake", encoding="utf-8")

            def fake_version(command, **_kwargs):
                if Path(command[0]).resolve() == root_executable.resolve():
                    return SimpleNamespace(returncode=0, stdout="ModelSim Intel FPGA Starter Edition")
                return SimpleNamespace(returncode=0, stdout="QuestaSim-64 vsim 2024.1 Simulator")

            with mock.patch.object(reproduction.subprocess, "run", side_effect=fake_version):
                resolved, _version = reproduction.resolve_questa_vsim(str(install))
            self.assertEqual(resolved, executable.resolve())

    def test_invalid_questa_home_falls_through_to_path(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            bad = root / "bad-home"
            bad.mkdir()
            bad_executable = bad / "vsim.exe"
            bad_executable.write_text("fake", encoding="utf-8")
            good_executable = root / "path-vsim.exe"
            good_executable.write_text("fake", encoding="utf-8")

            def fake_version(command, **_kwargs):
                if Path(command[0]).resolve() == bad_executable.resolve():
                    return SimpleNamespace(returncode=0, stdout="ModelSim Intel FPGA Starter Edition")
                return SimpleNamespace(returncode=0, stdout="QuestaSim-64 vsim 2024.1 Simulator")

            with mock.patch.dict(reproduction.os.environ, {"QUESTA_HOME": str(bad)}), mock.patch.object(
                reproduction.shutil, "which", return_value=str(good_executable)
            ), mock.patch.object(reproduction.subprocess, "run", side_effect=fake_version):
                resolved, _version = reproduction.resolve_questa_vsim(None)
            self.assertEqual(resolved, good_executable.resolve())


class TranscriptParserTests(unittest.TestCase):
    def test_published_transcript_normalizes_line_end_padding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.txt"
            reproduction.write_normalized_transcript(path, "first  \r\nsecond\t\r\n")
            self.assertEqual(path.read_bytes(), b"first\nsecond\n")

    def test_wrapper_result_reads_isolated_transcript_not_console_formatting(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            wrapper = root / "fake.ps1"
            wrapper.write_text("# fake", encoding="utf-8")
            build = root / "build"
            transcript = build / "questa/case/replay-case/transcript.log"
            transcript.parent.mkdir(parents=True)
            transcript.write_text("stable VHDL report line", encoding="utf-8")
            traces = root / "traces"
            traces.mkdir()
            with mock.patch.object(
                reproduction.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0, stdout="PowerShell object formatting"),
            ):
                text = reproduction.run_spec(
                    reproduction.RunSpec("case", wrapper),
                    powershell="powershell",
                    simulator="questa",
                    vsim_path=ROOT / "fake-vsim.exe",
                    build_root=build,
                    run_id_prefix="replay",
                    timeout_seconds=10,
                    license_file=None,
                    license_server=None,
                    traces=traces,
                )
            self.assertEqual(text, "stable VHDL report line")
            self.assertEqual((traces / "case.txt").read_text(encoding="utf-8"), text)

    def test_comb6_parser_uses_case_rows_not_banner_text(self):
        lines = []
        for value in range(64):
            expected = value % 16
            hits = value + 1
            lines.append(
                f"# ** Note: comb6 forward input={value} expected_sig={expected} "
                f"hits={hits}/1000 top_sig={expected} top_count={hits}"
            )
        lines.extend(
            [
                "# ** Note: comb6 summary min_hits=1/1000 worst_input=0 expected_sig=0",
                "# ** Note: tb_comb6_diagnostics completed",
            ]
        )
        metrics = reproduction.parse_comb6("\n".join(lines))
        self.assertEqual(metrics.top_matches, 64)
        self.assertEqual(metrics.zero_hit_cases, 0)
        self.assertEqual(metrics.min_hits, 1)
        self.assertEqual(metrics.total_hits, sum(range(1, 65)))

    def test_comb6_one_hit_drift_fails_even_when_rounded_average_matches(self):
        golden = json.loads(reproduction.GOLDEN_PATH.read_text(encoding="utf-8"))
        expected = golden["comb6"]["comb6_integer_1000"]
        metrics = reproduction.Comb6Metrics(
            top_matches=expected["top_matches"],
            zero_hit_cases=expected["zero_hit_cases"],
            min_hits=0,
            total_hits=expected["total_hits"] + 1,
            sample_count=1000,
            cases=64,
        )
        self.assertEqual(round(metrics.average_hits, 1), round(expected["average_hits"], 1))
        with self.assertRaises(reproduction.ReproductionError):
            reproduction.validate_comb6("comb6_integer_1000", metrics, expected)

    def test_optimizer_audit_requires_all_stable_markers(self):
        text = "\n".join(
            [
                "OPTIMIZER_AUDIT HA valid_energy=-2 gap=1 invalid_local_minima=0 states=16",
                "OPTIMIZER_AUDIT FA valid_energy=-2 gap=1 invalid_local_minima=0 states=32",
                "RTL_SCALE_AUDIT HA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=16",
                "RTL_SCALE_AUDIT FA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=32",
                "tb_optimizer_energy_audit passed",
                "Errors: 0, Warnings: 0",
            ]
        )
        reproduction.validate_optimizer_audit(text)
        with self.assertRaises(reproduction.ReproductionError):
            reproduction.validate_optimizer_audit(text.replace("RTL_SCALE_AUDIT FA", "MISSING FA"))

    def test_published_questa_traces_parse_by_report_lines(self):
        trace_dir = ROOT / "results_and_reports/stage2/rca_convergence_benchmark/traces"
        names = [
            "baseline_direct4",
            "scheduled_auxiliary_carry_integer4",
            "quantized_coefficient_direct4",
            "carry_ordered_schedule4",
            "auxiliary_carry_parallel4",
            "quantized_scheduled_auxiliary_carry4",
            "baseline_direct8",
            "quantized_coefficient_direct8",
            "scheduled_auxiliary_carry_integer8",
            "quantized_scheduled_auxiliary_carry8",
            "sum_baseline_direct4",
            "sum_scheduled_auxiliary_carry_integer4",
            "sum_quantized_scheduled_auxiliary_carry4",
            "sum_auxiliary_carry_parallel4",
            "sum_quantized_auxiliary_carry_parallel4",
        ]
        runs = {name: (trace_dir / f"{name}.txt").read_text(encoding="utf-8") for name in names}
        runs["schedule_reduction_qsac_w10_8_16_6"] = (
            trace_dir / "schedule_reduction_qsac_w10_8_16_6.txt"
        ).read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            presentation.configure_output_root(Path(temp))
            _cases, summaries, repeats, _sum_by, _pairs, sum_aggregates = presentation.parse_outputs(runs)
        summary_map = {(row["run"], row["direction"]): row["hits"] for row in summaries}
        self.assertEqual(summary_map[("baseline_direct4", "forward")], 21937)
        self.assertEqual(summary_map[("quantized_scheduled_auxiliary_carry4", "inverse_bsum")], 25516)
        self.assertEqual(sum(row["hits"] for row in repeats if row["run"] == "quantized_scheduled_auxiliary_carry8"), 596)
        sum_map = {row["run"]: row["valid_total"] for row in sum_aggregates}
        self.assertEqual(sum_map["sum_baseline_direct4"], 26645)


class GoldenComparatorTests(unittest.TestCase):
    def test_committed_integer_evidence_satisfies_exact_goldens(self):
        data = ROOT / "results_and_reports/stage2/rca_convergence_benchmark/data"
        case_rows = csv_rows(
            data / "adder4_cases.csv",
            integer_fields=("a", "b", "target", "hits", "trials", "top", "top_count"),
            float_fields=("success_probability",),
        )
        summary_rows = csv_rows(
            data / "adder4_summary.csv",
            integer_fields=("cases", "hits", "trials_total", "per_case_trials", "min_hits", "fail_cases"),
            float_fields=("success_probability",),
        )
        repeat_rows = csv_rows(
            data / "adder8_repeated.csv",
            integer_fields=("a", "b", "expected", "hits", "trials", "distinct_sums"),
            float_fields=("success_probability",),
        )
        sum_by_rows = csv_rows(data / "sum_only_by_sum.csv")
        sum_aggregate_rows = csv_rows(
            data / "sum_only_aggregate.csv",
            integer_fields=(
                "valid_total",
                "trials",
                "valid_pairs_seen",
                "valid_pairs_total",
                "sums_below_90pct_valid",
                "zero_valid_sums",
            ),
            float_fields=("valid_rate", "coverage_rate"),
        )
        wanted_windows = {"w40_40_40_40", "w10_8_16_6", "w2_2_4_2"}
        window_rows = [
            row
            for row in csv_rows(data / "quantized_scheduled_auxiliary_carry_window_sweep.csv")
            if row["run"] in wanted_windows
        ]
        golden = json.loads(reproduction.GOLDEN_PATH.read_text(encoding="utf-8"))
        result = reproduction.validate_benchmark(
            golden=golden,
            case_rows=case_rows,
            summary_rows=summary_rows,
            repeat8_rows=repeat_rows,
            sum_by_sum_rows=sum_by_rows,
            sum_aggregate_rows=sum_aggregate_rows,
            window_rows=window_rows,
        )
        self.assertEqual(result["adder8"]["quantized_scheduled_auxiliary_carry8"], 596)

    def test_one_count_drift_fails_even_when_rate_is_close(self):
        golden = json.loads(reproduction.GOLDEN_PATH.read_text(encoding="utf-8"))
        expected = golden["adder4"]["baseline_direct4"]["forward"]
        self.assertEqual(expected, [21937, 25600])
        self.assertFalse(
            abs(((expected[0] - 1) / expected[1]) - (expected[0] / expected[1]))
            <= reproduction.FLOAT_TOLERANCE
        )

    def test_duplicate_sum_with_missing_target_is_rejected(self):
        inputs = committed_acceptance_inputs()
        rows = [dict(row) for row in inputs["sum_by_sum_rows"]]
        selected = [row for row in rows if row["run"] == "sum_baseline_direct4"]
        selected[1]["sum"] = selected[0]["sum"]
        inputs["sum_by_sum_rows"] = rows
        golden = json.loads(reproduction.GOLDEN_PATH.read_text(encoding="utf-8"))
        with self.assertRaises(reproduction.ReproductionError):
            reproduction.validate_benchmark(golden=golden, **inputs)

    def test_changed_8bit_vector_is_rejected_even_with_same_aggregate(self):
        inputs = committed_acceptance_inputs()
        rows = [dict(row) for row in inputs["repeat8_rows"]]
        baseline = next(row for row in rows if row["run"] == "baseline_direct8")
        baseline["a"] += 1
        baseline["expected"] += 1
        inputs["repeat8_rows"] = rows
        golden = json.loads(reproduction.GOLDEN_PATH.read_text(encoding="utf-8"))
        with self.assertRaises(reproduction.ReproductionError):
            reproduction.validate_benchmark(golden=golden, **inputs)


class ReportStagingTests(unittest.TestCase):
    def test_replay_report_labels_questa_and_fixed_seed_mode(self):
        data = ROOT / "results_and_reports/stage2/rca_convergence_benchmark/data"
        summaries = csv_rows(
            data / "adder4_summary.csv",
            integer_fields=("cases", "hits", "trials_total", "per_case_trials", "min_hits", "fail_cases"),
            float_fields=("success_probability",),
        )
        repeats = csv_rows(
            data / "adder8_repeated.csv",
            integer_fields=("a", "b", "expected", "hits", "trials", "distinct_sums"),
            float_fields=("success_probability",),
        )
        sums = csv_rows(
            data / "sum_only_aggregate.csv",
            integer_fields=("valid_total", "trials", "valid_pairs_seen", "valid_pairs_total", "zero_valid_sums"),
            float_fields=("valid_rate", "coverage_rate", "weighted_entropy_norm", "weighted_tv_from_uniform"),
        )
        manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
        manifest["replay_compatibility"] = {
            "testbench_timing": reproduction.HISTORICAL_TIMING_REPLAY,
        }
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            presentation.configure_output_root(output)
            presentation.write_report(
                manifest,
                summaries,
                repeats,
                sums,
                {},
                simulator_name="QuestaSim",
                simulator_version="Questa Sim-64 vsim 2024.1",
                seed_mode="replay",
                reproduced_at="2026-09-16T00:00:00Z",
                git_revision="abc123",
            )
            report = (output / "report.md").read_text(encoding="utf-8")
        self.assertIn("## 4. QuestaSim Protocol", report)
        self.assertIn("does not generate a new random salt", report)
        self.assertIn("Historical timing provenance", report)
        self.assertIn("-LegacyReplayTiming", report)
        self.assertIn("wrapper default uses the corrected clamp-prime cycle", report)
        self.assertIn("under the corrected clamp-prime/readout protocol", report)
        self.assertIn("260/600 (43.33%)", report)
        self.assertIn("596/600 (99.33%)", report)
        self.assertIn("every vector at least 98/100", report)
        self.assertNotIn("`quantized_scheduled_auxiliary_carry4` use `-LegacyReplayTiming`", report)
        self.assertNotIn("## 4. ModelSim Protocol", report)

    def test_publish_failure_restores_every_original_target(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            root = Path(temp)
            reports = root / "reports"
            reports.mkdir()
            target_dir = reports / "presentation"
            target_dir.mkdir()
            (target_dir / "old.txt").write_text("old presentation", encoding="utf-8")
            target_file = reports / "comb6.md"
            target_file.write_text("old comb6", encoding="utf-8")
            stage = root / "stage"
            stage.mkdir()
            candidate_dir = stage / "candidate-presentation"
            candidate_dir.mkdir()
            (candidate_dir / "new.txt").write_text("new presentation", encoding="utf-8")
            missing_candidate = stage / "missing-comb6.md"

            with mock.patch.object(reproduction, "REPORTS", reports):
                with self.assertRaises(FileNotFoundError):
                    reproduction.publish_transaction(
                        [(candidate_dir, target_dir), (missing_candidate, target_file)],
                        stage,
                    )

            self.assertEqual(
                (target_dir / "old.txt").read_text(encoding="utf-8"),
                "old presentation",
            )
            self.assertEqual(target_file.read_text(encoding="utf-8"), "old comb6")
            self.assertEqual(
                (candidate_dir / "new.txt").read_text(encoding="utf-8"),
                "new presentation",
            )


if __name__ == "__main__":
    unittest.main()
