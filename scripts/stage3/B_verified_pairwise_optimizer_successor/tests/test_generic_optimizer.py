"""Focused regression tests for the portable quantized landscape optimizer."""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import math
import unittest

try:  # Supports both discovery from this directory and package-style execution.
    from . import generic_optimizer as optimizer
except ImportError:  # pragma: no cover - depends on the unittest invocation form.
    import scripts.stage3.B_verified_pairwise_optimizer_successor.generic_optimizer as optimizer
HA_COEFFICIENTS = (
    1.0,
    1.0,
    -1.0,
    -2.0,
    -1.0,  # A-B
    1.0,  # A-S
    2.0,  # A-C
    1.0,  # B-S
    2.0,  # B-C
    -2.0,  # S-C
)


def parse(**overrides):
    """Build a small valid spec and apply test-specific overrides."""

    payload = {
        "name": "two_bit_fixture",
        "nodes": ["a", "b"],
        "valid_states": [[0, 0]],
    }
    payload.update(overrides)
    return optimizer.parse_spec(payload)


class FeatureAndAuditTests(unittest.TestCase):
    def test_canonical_half_adder_has_equal_valid_energy_and_gap_two(self):
        spec = optimizer.build_demo_spec("ha")

        valid_energies = {
            optimizer.energy(state, HA_COEFFICIENTS)
            for state in spec.valid_states
        }
        self.assertEqual(valid_energies, {-4.0})

        audit = optimizer.audit_solution(
            spec,
            HA_COEFFICIENTS,
            min_gap=2.0,
            tolerance=1e-9,
        )
        self.assertEqual(audit["state_count"], 16)
        self.assertEqual(audit["valid_count"], 4)
        self.assertEqual(audit["invalid_count"], 12)
        self.assertAlmostEqual(audit["valid_energy_reference"], -4.0)
        self.assertAlmostEqual(audit["valid_energy_spread"], 0.0)
        self.assertAlmostEqual(audit["minimum_invalid_gap"], 2.0)
        self.assertTrue(audit["gap_ok"])

    def test_pair_and_feature_order_matches_repository_h_j_layout(self):
        self.assertEqual(
            optimizer.pair_indices(4),
            ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)),
        )

        # Logic 0 maps to spin -1 and logic 1 to +1.  The repository energy
        # convention negates fields and pair products, so coefficients can be
        # copied directly from results_and_reports/stage1/A_primitive_spin_gate_validation/hamiltonians.md.
        self.assertEqual(
            tuple(optimizer.feature_row((0, 1, 0))),
            (1.0, -1.0, 1.0, 1.0, -1.0, 1.0),
        )


class SpecValidationTests(unittest.TestCase):
    def test_minimal_spec_expands_the_full_binary_cube(self):
        spec = parse()
        self.assertEqual(
            spec.state_space,
            ((0, 0), (0, 1), (1, 0), (1, 1)),
        )

    def test_rejects_structurally_invalid_specs(self):
        bad_payloads = (
            {
                "name": "duplicate_nodes",
                "nodes": ["x", "x"],
                "valid_states": [[0, 0]],
            },
            {
                "name": "wrong_width",
                "nodes": ["x", "y"],
                "valid_states": [[0]],
            },
            {
                "name": "non_binary",
                "nodes": ["x"],
                "valid_states": [[2]],
            },
            {
                "name": "missing_valid_from_space",
                "nodes": ["x", "y"],
                "valid_states": [[0, 0]],
                "state_space": [[0, 1], [1, 1]],
            },
            {
                "name": "bad_smooth_edge",
                "nodes": ["x", "y"],
                "valid_states": [[0, 0]],
                "smooth_edges": [[[0, 1], [1, 0]]],
            },
        )
        for payload in bad_payloads:
            with self.subTest(name=payload["name"]):
                with self.assertRaises((TypeError, ValueError)):
                    optimizer.parse_spec(payload)


class LandscapeConstructionTests(unittest.TestCase):
    def test_generated_smooth_edges_are_unique_invalid_one_bit_edges(self):
        spec = parse()
        edges = optimizer.generate_smooth_edges(spec)

        self.assertEqual(
            edges,
            (
                ((0, 1), (1, 1)),
                ((1, 0), (1, 1)),
            ),
        )
        valid = set(spec.valid_states)
        for left, right in edges:
            self.assertNotIn(left, valid)
            self.assertNotIn(right, valid)
            self.assertEqual(sum(a != b for a, b in zip(left, right)), 1)

    def test_descent_parent_ties_are_lexicographically_deterministic(self):
        spec = parse()

        first = optimizer.select_descent_parent((1, 1), spec)
        self.assertEqual(first, (0, 1))
        for _ in range(5):
            self.assertEqual(
                optimizer.select_descent_parent((1, 1), spec),
                first,
            )

        child_distance = sum(a != b for a, b in zip((1, 1), (0, 0)))
        parent_distance = sum(a != b for a, b in zip(first, (0, 0)))
        self.assertEqual(parent_distance, child_distance - 1)


class QuantizationAndMinimaTests(unittest.TestCase):
    def test_quantization_uses_requested_lattice_and_clips_to_bound(self):
        values = (0.24, 0.26, -0.74, 1.26, -1.26)
        quantized = tuple(
            float(value)
            for value in optimizer.quantize_coefficients(
                values,
                quantum=0.5,
                coeff_max=1.0,
            )
        )

        self.assertEqual(quantized, (0.0, 0.5, -0.5, 1.0, -1.0))
        for value in quantized:
            self.assertLessEqual(abs(value), 1.0)
            self.assertAlmostEqual(value / 0.5, round(value / 0.5))

    def test_equal_energy_plateau_states_are_local_minima(self):
        spec = parse()
        audit = optimizer.audit_solution(
            spec,
            (0.0, 0.0, 0.0),
            min_gap=0.0,
            tolerance=1e-9,
        )

        self.assertEqual(
            audit["invalid_local_minimum_states"],
            [[0, 1], [1, 0], [1, 1]],
        )
        self.assertEqual(audit["invalid_local_minima"], 3)
        self.assertTrue(audit["gap_ok"])
        self.assertTrue(math.isclose(audit["minimum_invalid_gap"], 0.0))

    def test_partial_state_space_controls_edges_counts_and_neighbors(self):
        spec = parse(state_space=[[0, 0], [0, 1], [1, 1]])
        self.assertEqual(
            optimizer.generate_smooth_edges(spec),
            (((0, 1), (1, 1)),),
        )

        # H = s_a makes 01 lower than 11.  The omitted state 10 must not be
        # counted or used as a neighbor during the local-minimum audit.
        audit = optimizer.audit_solution(
            spec,
            (-1.0, 0.0, 0.0),
            min_gap=0.0,
            tolerance=1e-9,
        )
        self.assertEqual(audit["state_count"], 3)
        self.assertEqual(audit["invalid_count"], 2)
        self.assertEqual(audit["invalid_local_minimum_states"], [[0, 1]])


class SolverIntegrationTests(unittest.TestCase):
    def test_builtin_gate_qps_survive_quantization_and_exhaustive_audit(self):
        settings = optimizer.SolverSettings()
        for gate in ("ha", "fa"):
            with self.subTest(gate=gate):
                result = optimizer.solve_problem(
                    optimizer.build_demo_spec(gate),
                    settings,
                )
                audit = result.quantized_audit
                self.assertTrue(audit["valid_equal"])
                self.assertTrue(audit["gap_ok"])
                self.assertGreaterEqual(
                    audit["minimum_invalid_gap"],
                    settings.min_gap,
                )
                self.assertEqual(audit["invalid_local_minima"], 0)
                self.assertLessEqual(
                    max(abs(float(value)) for value in result.quantized_coefficients),
                    settings.coeff_max,
                )
                for value in result.quantized_coefficients:
                    self.assertAlmostEqual(
                        float(value) / settings.quantum,
                        round(float(value) / settings.quantum),
                    )


if __name__ == "__main__":
    unittest.main()
