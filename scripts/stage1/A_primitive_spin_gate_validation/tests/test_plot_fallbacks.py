from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


SCRIPTS = _REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import scripts.stage1.A_primitive_spin_gate_validation.plot_and_trace as plot_and_trace
import scripts.stage1.A_primitive_spin_gate_validation.plot_small_gate_probabilities as plot_small_gate_probabilities
class PillowPlotFallbackTests(unittest.TestCase):
    def assert_png(self, path: Path, minimum_size: tuple[int, int]) -> None:
        self.assertGreater(path.stat().st_size, 1000)
        self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        with Image.open(path) as image:
            self.assertEqual(image.format, "PNG")
            self.assertGreaterEqual(image.width, minimum_size[0])
            self.assertGreaterEqual(image.height, minimum_size[1])
            image.verify()

    def test_trace_plot_falls_back_to_diagnostic_pillow_png(self) -> None:
        rows = []
        states = [
            (0, 0, 0, 0),
            (0, 1, 1, 0),
            (1, 0, 1, 0),
            (1, 1, 0, 1),
        ]
        for scenario in (0, 4):
            for index, (a, b, y, aux) in enumerate(states):
                rows.append(
                    {
                        "time_ns": scenario * 1000 + index * 100,
                        "scenario": scenario,
                        "measure": 1,
                        "clamp_a_en": 0,
                        "clamp_a_value": 0,
                        "clamp_b_en": 0,
                        "clamp_b_value": 0,
                        "clamp_y_en": 1 if scenario == 4 else 0,
                        "clamp_y_value": 0,
                        "a": a,
                        "b": b,
                        "y": y,
                        "aux_c": aux,
                        "field_a": 2 * a - 1,
                        "field_b": 2 * b - 1,
                        "field_y": 2 * y - 1,
                        "field_aux": 2 * aux - 1,
                    }
                )
        summaries, _state_probabilities, _ab_probabilities = plot_and_trace.summarize(rows, "xor")

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "trace.png"
            with mock.patch.object(plot_and_trace, "_load_matplotlib_pyplot", return_value=None):
                plot_and_trace.plot_trace(rows, summaries, "xor", output)
            self.assert_png(output, (1400, 900))

    def test_probability_plot_falls_back_to_diagnostic_pillow_png(self) -> None:
        rows = []
        for gate in ("AND", "XOR"):
            for y_value in ("0", "1"):
                for index, ab in enumerate(("00", "01", "10", "11")):
                    rows.append(
                        {
                            "gate": gate,
                            "scenario": str(4 + int(y_value)),
                            "label": f"reverse Y={y_value}",
                            "y_clamped": "1",
                            "y_value": y_value,
                            "ab": ab,
                            "probability": f"{(index + 1) / 10:.8f}",
                            "valid_for_clamped_y": "1" if index % 2 == 0 else "0",
                        }
                    )

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "probabilities.png"
            with mock.patch.object(
                plot_small_gate_probabilities, "_load_matplotlib_pyplot", return_value=None
            ):
                plot_small_gate_probabilities.plot_reverse_ab(rows, output)
            self.assert_png(output, (1000, 500))


if __name__ == "__main__":
    unittest.main()
