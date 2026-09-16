"""Tests for the optimizer-to-Questa static and dynamic evidence helpers."""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import json
import tempfile
import unittest
from pathlib import Path

try:  # Supports directory discovery and package-style execution.
    from . import export_vhdl_coefficients as exporter
    from . import generic_optimizer as optimizer
    from . import verify_questa_evidence as verifier
except ImportError:  # pragma: no cover - depends on unittest invocation form.
    import scripts.stage3.B_verified_pairwise_optimizer_successor.export_vhdl_coefficients as exporter
    import scripts.stage3.B_verified_pairwise_optimizer_successor.generic_optimizer as optimizer
    import scripts.stage3.B_verified_pairwise_optimizer_successor.verify_questa_evidence as verifier
REPO_ROOT = _REPO_ROOT
RTL_SOURCE = REPO_ROOT / "experiments/stage1/A_primitive_spin_gate_validation/hardware/generated_networks.vhd"


class RtlExtractionTests(unittest.TestCase):
    def test_current_generated_rtl_matches_canonical_double_scale_vectors(self):
        half_adder = exporter.parse_rtl_coefficients(RTL_SOURCE, exporter.GATES[0])
        full_adder = exporter.parse_rtl_coefficients(RTL_SOURCE, exporter.GATES[1])

        self.assertEqual(
            half_adder,
            (1, 1, -1, -2, -1, 1, 2, 1, 2, -2),
        )
        self.assertEqual(
            full_adder,
            (0, 0, 0, 0, 0, -1, -1, 1, 2, -1, 1, 2, 1, 2, -2),
        )


class PackageExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings = optimizer.SolverSettings()
        cls.ha_payload = optimizer.solve_problem(
            optimizer.build_demo_spec("ha"), settings
        ).to_dict()
        cls.fa_payload = optimizer.solve_problem(
            optimizer.build_demo_spec("fa"), settings
        ).to_dict()

    def _write_payloads(self, directory: Path) -> tuple[Path, Path]:
        ha_path = directory / "ha.json"
        fa_path = directory / "fa.json"
        ha_path.write_text(json.dumps(self.ha_payload), encoding="utf-8")
        fa_path.write_text(json.dumps(self.fa_payload), encoding="utf-8")
        return ha_path, fa_path

    def test_export_contains_exact_scaled_optimizer_and_rtl_coefficients(self):
        with tempfile.TemporaryDirectory() as temporary:
            ha_path, fa_path = self._write_payloads(Path(temporary))
            package = exporter.build_vhdl_package(ha_path, fa_path, RTL_SOURCE)

        self.assertIn("constant COEFFICIENT_SCALE : positive := 2;", package)
        self.assertIn("(1, 1, -1, -2, -1, 1, 2, 1, 2, -2);", package)
        self.assertIn("(2, 2, -2, -4, -2, 2, 4, 2, 4, -4);", package)
        self.assertIn(
            "(0, 0, 0, 0, 0, -1, -1, 1, 2, -1, 1, 2, 1, 2, -2);",
            package,
        )
        self.assertIn("RTL source SHA-256:", package)

    def test_export_rejects_audit_or_coefficient_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ha_path, fa_path = self._write_payloads(directory)
            payload = json.loads(ha_path.read_text(encoding="utf-8"))
            payload["quantized"]["coefficients"][0] += 0.5
            ha_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(exporter.ExportError, "not 2x"):
                exporter.build_vhdl_package(ha_path, fa_path, RTL_SOURCE)


class TranscriptVerificationTests(unittest.TestCase):
    def test_static_audit_requires_all_markers_and_zero_summary(self):
        transcript = "\n".join(verifier.STATIC_MARKERS) + "\nErrors: 0, Warnings: 0\n"
        result = verifier.verify_transcript(transcript, "static")
        self.assertTrue(result["passed"])
        self.assertEqual(result["coverage"]["ha_states"], 16)
        self.assertEqual(result["coverage"]["fa_states"], 32)

        missing = verifier.verify_transcript(
            transcript.replace(verifier.STATIC_MARKERS[0], ""), "static"
        )
        self.assertFalse(missing["passed"])
        self.assertEqual(missing["missing_markers"], [verifier.STATIC_MARKERS[0]])

    def test_generated_gate_marker_encodes_required_case_coverage(self):
        transcript = "# tb_generated_gates passed\n# Errors: 0, Warnings: 0\n"
        result = verifier.verify_transcript(transcript, "generated-gates")
        self.assertTrue(result["passed"])
        self.assertEqual(result["coverage"]["xor_half_adder_forward_cases"], 4)
        self.assertEqual(result["coverage"]["xor_half_adder_reverse_cases"], 2)
        self.assertEqual(result["coverage"]["full_adder_forward_cases"], 8)

    def test_warning_or_nonzero_summary_fails_even_with_pass_marker(self):
        transcript = (
            "# tb_generated_gates passed\n"
            "# ** Warning: unexpected warning\n"
            "# Errors: 0, Warnings: 1\n"
        )
        result = verifier.verify_transcript(transcript, "generated-gates")
        self.assertFalse(result["passed"])
        self.assertFalse(result["zero_errors_zero_warnings"])
        self.assertEqual(result["bad_severity_count"], 1)


if __name__ == "__main__":
    unittest.main()
