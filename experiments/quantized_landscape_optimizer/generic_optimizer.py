"""Portable pairwise-Ising landscape optimizer.

The historical Stage-E optimizer described in this directory's README was
never committed.  This module reconstructs the documented generic core while
borrowing the state/feature conventions and exhaustive-audit ideas from the
later multibody optimizer.

Only NumPy is required.  The continuous problem is a convex quadratic program

    minimize  1/2 theta.T P theta
    subject to lower <= A theta <= upper

solved by a small OSQP-style ADMM routine.  Valid states are eliminated into
the null space of their hard equal-energy constraints before the QP is solved,
so those equalities are satisfied to numerical precision.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


State = tuple[int, ...]
Edge = tuple[State, State]


class SpecError(ValueError):
    """Raised when a portable optimizer specification is malformed."""


class OptimizationError(RuntimeError):
    """Raised when the QP or the verified quantized result is unsuccessful."""


@dataclass(frozen=True)
class DescentCut:
    state: State
    parent: State
    margin: float | None = None


@dataclass(frozen=True)
class ProblemSpec:
    name: str
    nodes: tuple[str, ...]
    valid_states: tuple[State, ...]
    state_space: tuple[State, ...]
    smooth_edges: tuple[Edge, ...] | None = None
    descent_cuts: tuple[DescentCut, ...] = ()
    description: str = ""

    @property
    def n(self) -> int:
        return len(self.nodes)


@dataclass(frozen=True)
class SolverSettings:
    coeff_max: float = 7.0
    min_gap: float = 1.0
    quantum: float = 1.0 / 16.0
    smooth_weight: float = 1.0
    l2_weight: float = 0.01
    descent_margin: float = 1.0 / 16.0
    max_iterations: int = 8
    verification_tolerance: float = 1e-6
    qp_max_iterations: int = 50_000
    qp_abs_tolerance: float = 1e-8
    qp_rel_tolerance: float = 1e-7
    qp_rho: float = 1.0
    qp_sigma: float = 1e-7
    qp_adaptive_interval: int = 50


@dataclass(frozen=True)
class QpStats:
    iterations: int
    converged: bool
    primal_residual: float
    dual_residual: float
    constraint_violation: float
    objective: float
    rho: float
    nullity: int


@dataclass
class OptimizationResult:
    spec: ProblemSpec
    settings: SolverSettings
    continuous_coefficients: np.ndarray
    quantized_coefficients: np.ndarray
    continuous_audit: dict[str, Any]
    quantized_audit: dict[str, Any]
    qp_stats: QpStats
    history: list[dict[str, Any]]
    descent_cuts: tuple[DescentCut, ...]

    def to_dict(self) -> dict[str, Any]:
        continuous_h, continuous_j = coefficients_to_h_j(
            self.spec.n, self.continuous_coefficients
        )
        quantized_h, quantized_j = coefficients_to_h_j(
            self.spec.n, self.quantized_coefficients
        )
        return {
            "schema_version": 1,
            "status": "success",
            "problem": {
                "name": self.spec.name,
                "description": self.spec.description,
                "nodes": list(self.spec.nodes),
                "state_count": len(self.spec.state_space),
                "valid_state_count": len(self.spec.valid_states),
            },
            "settings": asdict(self.settings),
            "continuous": {
                "coefficients": _float_list(self.continuous_coefficients),
                "h": continuous_h,
                "j": continuous_j,
                "audit": self.continuous_audit,
            },
            "quantized": {
                "coefficients": _float_list(self.quantized_coefficients),
                "h": quantized_h,
                "j": quantized_j,
                "audit": self.quantized_audit,
            },
            "qp": asdict(self.qp_stats),
            "iterations": self.history,
            "descent_cuts": [descent_cut_payload(cut) for cut in self.descent_cuts],
        }


def _float_list(values: np.ndarray | Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def state_text(state: State) -> str:
    return "".join(str(bit) for bit in state)


def state_code(state: State) -> int:
    code = 0
    for bit in state:
        code = (code << 1) | bit
    return code


def hamming_distance(left: State, right: State) -> int:
    return sum(a != b for a, b in zip(left, right))


def pair_indices(n: int) -> tuple[tuple[int, int], ...]:
    return tuple((i, j) for i in range(n) for j in range(i + 1, n))


def coefficient_count(n: int) -> int:
    return n + n * (n - 1) // 2


def feature_row(state: State) -> np.ndarray:
    """Return coefficients multiplying [h..., J01, J02, ...] in H(state)."""

    spins = np.array([1.0 if bit else -1.0 for bit in state], dtype=np.float64)
    pair_terms = [-spins[i] * spins[j] for i, j in pair_indices(len(state))]
    return np.concatenate((-spins, np.asarray(pair_terms, dtype=np.float64)))


def feature_matrix(states: Sequence[State], n: int | None = None) -> np.ndarray:
    if not states:
        width = coefficient_count(0 if n is None else n)
        return np.empty((0, width), dtype=np.float64)
    return np.vstack([feature_row(state) for state in states])


def energy(state: State, coefficients: Sequence[float]) -> float:
    values = np.asarray(coefficients, dtype=np.float64)
    expected = coefficient_count(len(state))
    if values.shape != (expected,):
        raise ValueError(f"expected {expected} coefficients, got shape {values.shape}")
    return float(feature_row(state) @ values)


def coefficients_to_h_j(
    n: int, coefficients: Sequence[float]
) -> tuple[list[float], list[list[float]]]:
    values = np.asarray(coefficients, dtype=np.float64)
    expected = coefficient_count(n)
    if values.shape != (expected,):
        raise ValueError(f"expected {expected} coefficients, got shape {values.shape}")
    h = _float_list(values[:n])
    j = [[0.0 for _ in range(n)] for _ in range(n)]
    for value, (left, right) in zip(values[n:], pair_indices(n)):
        j[left][right] = float(value)
        j[right][left] = float(value)
    return h, j


def h_j_to_coefficients(h: Sequence[float], j: Sequence[Sequence[float]]) -> np.ndarray:
    n = len(h)
    if len(j) != n or any(len(row) != n for row in j):
        raise ValueError("J must be a square matrix matching h")
    for idx in range(n):
        if not math.isclose(float(j[idx][idx]), 0.0, abs_tol=1e-12):
            raise ValueError("J diagonal must be zero")
        for other in range(idx + 1, n):
            if not math.isclose(
                float(j[idx][other]), float(j[other][idx]), abs_tol=1e-12
            ):
                raise ValueError("J must be symmetric")
    values = [float(value) for value in h]
    values.extend(float(j[left][right]) for left, right in pair_indices(n))
    return np.asarray(values, dtype=np.float64)


def _parse_state(value: Any, n: int, label: str) -> State:
    if isinstance(value, str):
        if len(value) != n or any(char not in "01" for char in value):
            raise SpecError(f"{label} must be a {n}-bit string")
        return tuple(int(char) for char in value)
    if not isinstance(value, (list, tuple)) or len(value) != n:
        raise SpecError(f"{label} must contain exactly {n} bits")
    if any(type(bit) is not int or bit not in (0, 1) for bit in value):
        raise SpecError(f"{label} must contain only integer bits 0 or 1")
    return tuple(value)


def _parse_state_list(value: Any, n: int, label: str) -> tuple[State, ...]:
    if not isinstance(value, list):
        raise SpecError(f"{label} must be a JSON array")
    states = tuple(_parse_state(item, n, f"{label}[{idx}]") for idx, item in enumerate(value))
    if len(set(states)) != len(states):
        raise SpecError(f"{label} contains duplicate states")
    return states


def _canonical_edge(left: State, right: State) -> Edge:
    return (left, right) if state_code(left) < state_code(right) else (right, left)


def _parse_edge(value: Any, n: int, label: str) -> Edge:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise SpecError(f"{label} must be [state, neighbor]")
    left = _parse_state(value[0], n, f"{label}[0]")
    right = _parse_state(value[1], n, f"{label}[1]")
    return _canonical_edge(left, right)


def _parse_cut(value: Any, n: int, label: str) -> DescentCut:
    margin: float | None
    if isinstance(value, dict):
        unknown = set(value) - {"state", "parent", "margin"}
        if unknown:
            raise SpecError(f"{label} has unknown keys: {sorted(unknown)}")
        if "state" not in value or "parent" not in value:
            raise SpecError(f"{label} requires state and parent")
        state = _parse_state(value["state"], n, f"{label}.state")
        parent = _parse_state(value["parent"], n, f"{label}.parent")
        margin = value.get("margin")
    elif isinstance(value, (list, tuple)) and len(value) in (2, 3):
        state = _parse_state(value[0], n, f"{label}[0]")
        parent = _parse_state(value[1], n, f"{label}[1]")
        margin = value[2] if len(value) == 3 else None
    else:
        raise SpecError(f"{label} must be an object or [state, parent, optional_margin]")
    if margin is not None:
        if isinstance(margin, bool) or not isinstance(margin, (int, float)):
            raise SpecError(f"{label}.margin must be numeric")
        margin = float(margin)
        if not math.isfinite(margin) or margin <= 0:
            raise SpecError(f"{label}.margin must be finite and positive")
    return DescentCut(state=state, parent=parent, margin=margin)


def parse_spec(payload: dict[str, Any]) -> ProblemSpec:
    if not isinstance(payload, dict):
        raise SpecError("spec root must be a JSON object")
    allowed = {
        "name",
        "description",
        "nodes",
        "valid_states",
        "state_space",
        "smooth_edges",
        "descent_cuts",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise SpecError(f"spec has unknown keys: {sorted(unknown)}")
    missing = {"name", "nodes", "valid_states"} - set(payload)
    if missing:
        raise SpecError(f"spec is missing required keys: {sorted(missing)}")

    name = payload["name"]
    if not isinstance(name, str) or not name.strip():
        raise SpecError("name must be a non-empty string")
    description = payload.get("description", "")
    if not isinstance(description, str):
        raise SpecError("description must be a string")
    nodes_raw = payload["nodes"]
    if not isinstance(nodes_raw, list) or not nodes_raw:
        raise SpecError("nodes must be a non-empty JSON array")
    if any(not isinstance(node, str) or not node.strip() for node in nodes_raw):
        raise SpecError("every node name must be a non-empty string")
    if len(set(nodes_raw)) != len(nodes_raw):
        raise SpecError("nodes contains duplicate names")
    nodes = tuple(nodes_raw)
    n = len(nodes)
    if n > 16 and "state_space" not in payload:
        raise SpecError("nodes > 16 requires an explicit state_space")

    valid_states = _parse_state_list(payload["valid_states"], n, "valid_states")
    if not valid_states:
        raise SpecError("valid_states must not be empty")
    if "state_space" in payload:
        state_space = _parse_state_list(payload["state_space"], n, "state_space")
    else:
        state_space = tuple(product((0, 1), repeat=n))
    if not state_space:
        raise SpecError("state_space must not be empty")
    state_set = set(state_space)
    missing_valid = set(valid_states) - state_set
    if missing_valid:
        raise SpecError(
            "valid_states must be contained in state_space; missing "
            + ", ".join(state_text(state) for state in sorted(missing_valid))
        )
    if len(state_set - set(valid_states)) == 0:
        raise SpecError("state_space must contain at least one invalid state")

    valid_set = set(valid_states)
    smooth_edges: tuple[Edge, ...] | None = None
    if "smooth_edges" in payload:
        raw_edges = payload["smooth_edges"]
        if not isinstance(raw_edges, list):
            raise SpecError("smooth_edges must be a JSON array")
        parsed_edges = tuple(
            _parse_edge(item, n, f"smooth_edges[{idx}]")
            for idx, item in enumerate(raw_edges)
        )
        if len(set(parsed_edges)) != len(parsed_edges):
            raise SpecError("smooth_edges contains duplicate undirected edges")
        for left, right in parsed_edges:
            if left not in state_set or right not in state_set:
                raise SpecError("smooth edge endpoints must be in state_space")
            if left in valid_set or right in valid_set:
                raise SpecError("smooth edge endpoints must both be invalid states")
            if hamming_distance(left, right) != 1:
                raise SpecError("smooth edge endpoints must have Hamming distance one")
        smooth_edges = tuple(sorted(parsed_edges, key=lambda edge: (state_code(edge[0]), state_code(edge[1]))))

    raw_cuts = payload.get("descent_cuts", [])
    if not isinstance(raw_cuts, list):
        raise SpecError("descent_cuts must be a JSON array")
    cuts = tuple(_parse_cut(item, n, f"descent_cuts[{idx}]") for idx, item in enumerate(raw_cuts))
    cut_keys: set[tuple[State, State]] = set()
    for cut in cuts:
        if cut.state not in state_set or cut.parent not in state_set:
            raise SpecError("descent cut endpoints must be in state_space")
        if cut.state in valid_set:
            raise SpecError("descent cut state must be invalid")
        if hamming_distance(cut.state, cut.parent) != 1:
            raise SpecError("descent cut parent must be a one-bit neighbor")
        key = (cut.state, cut.parent)
        if key in cut_keys:
            raise SpecError("descent_cuts contains duplicate state/parent pairs")
        cut_keys.add(key)

    return ProblemSpec(
        name=name.strip(),
        description=description,
        nodes=nodes,
        valid_states=tuple(sorted(valid_states, key=state_code)),
        state_space=tuple(sorted(state_space, key=state_code)),
        smooth_edges=smooth_edges,
        descent_cuts=cuts,
    )


def load_spec(path: Path | str) -> ProblemSpec:
    spec_path = Path(path)
    try:
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SpecError(f"could not read spec {spec_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SpecError(f"invalid JSON in {spec_path}: {exc}") from exc
    return parse_spec(payload)


def build_demo_spec(gate: str) -> ProblemSpec:
    gate_key = gate.lower()
    if gate_key == "ha":
        payload = {
            "name": "half_adder_demo",
            "description": "Pairwise Ising half-adder / XOR block",
            "nodes": ["A", "B", "S", "C"],
            "valid_states": [
                [a, b, a ^ b, a & b] for a, b in product((0, 1), repeat=2)
            ],
        }
    elif gate_key == "fa":
        valid = []
        for a, b, cin in product((0, 1), repeat=3):
            total = a + b + cin
            valid.append([a, b, cin, total & 1, (total >> 1) & 1])
        payload = {
            "name": "full_adder_demo",
            "description": "Pairwise Ising full-adder block",
            "nodes": ["A", "B", "CIN", "S", "COUT"],
            "valid_states": valid,
        }
    else:
        raise SpecError(f"unsupported demo gate: {gate}")
    return parse_spec(payload)


def generate_smooth_edges(spec: ProblemSpec) -> tuple[Edge, ...]:
    if spec.smooth_edges is not None:
        return spec.smooth_edges
    valid = set(spec.valid_states)
    invalid = set(spec.state_space) - valid
    edges: list[Edge] = []
    for state in sorted(invalid, key=state_code):
        for bit in range(spec.n):
            neighbor = state[:bit] + (1 - state[bit],) + state[bit + 1 :]
            if neighbor in invalid and state_code(state) < state_code(neighbor):
                edges.append((state, neighbor))
    return tuple(edges)


def neighbors_in_state_space(state: State, spec: ProblemSpec) -> tuple[State, ...]:
    state_set = set(spec.state_space)
    neighbors = []
    for bit in range(spec.n):
        candidate = state[:bit] + (1 - state[bit],) + state[bit + 1 :]
        if candidate in state_set:
            neighbors.append(candidate)
    return tuple(sorted(neighbors, key=state_code))


def distance_to_valid(state: State, spec: ProblemSpec) -> int:
    return min(hamming_distance(state, valid) for valid in spec.valid_states)


def select_descent_parent(state: State, spec: ProblemSpec) -> State:
    if state not in set(spec.state_space):
        raise SpecError("descent state is not in state_space")
    if state in set(spec.valid_states):
        raise SpecError("descent state must be invalid")
    neighbors = neighbors_in_state_space(state, spec)
    if not neighbors:
        raise OptimizationError(
            f"invalid local minimum {state_text(state)} has no one-bit neighbor in state_space"
        )
    return min(neighbors, key=lambda candidate: (distance_to_valid(candidate, spec), state_code(candidate)))


def quantize_coefficients(
    coefficients: Sequence[float], quantum: float, coeff_max: float
) -> np.ndarray:
    if not math.isfinite(quantum) or quantum <= 0:
        raise ValueError("quantum must be finite and positive")
    if not math.isfinite(coeff_max) or coeff_max <= 0:
        raise ValueError("coeff_max must be finite and positive")
    values = np.asarray(coefficients, dtype=np.float64)
    lattice_limit = math.floor((coeff_max + 1e-12) / quantum) * quantum
    if lattice_limit <= 0:
        raise ValueError("quantum is larger than coeff_max, leaving no nonzero lattice point")
    scaled = np.sign(values) * np.floor(np.abs(values) / quantum + 0.5)
    result = np.clip(scaled * quantum, -lattice_limit, lattice_limit)
    result[np.abs(result) < quantum * 0.5] = 0.0
    return result


def audit_solution(
    spec: ProblemSpec,
    coefficients: Sequence[float],
    min_gap: float,
    tolerance: float,
) -> dict[str, Any]:
    values = np.asarray(coefficients, dtype=np.float64)
    expected = coefficient_count(spec.n)
    if values.shape != (expected,):
        raise ValueError(f"expected {expected} coefficients, got shape {values.shape}")
    energies = {state: energy(state, values) for state in spec.state_space}
    valid_set = set(spec.valid_states)
    invalid_states = tuple(state for state in spec.state_space if state not in valid_set)
    valid_energy = np.asarray([energies[state] for state in spec.valid_states])
    invalid_energy = np.asarray([energies[state] for state in invalid_states])
    valid_min = float(np.min(valid_energy))
    valid_max = float(np.max(valid_energy))
    valid_reference = float(np.mean(valid_energy))
    minimum_gap = float(np.min(invalid_energy) - valid_max)

    local_states: list[State] = []
    for state in invalid_states:
        state_energy = energies[state]
        neighbors = neighbors_in_state_space(state, spec)
        if all(state_energy <= energies[neighbor] + tolerance for neighbor in neighbors):
            local_states.append(state)

    smooth_edges = generate_smooth_edges(spec)
    jumps = np.asarray(
        [energies[left] - energies[right] for left, right in smooth_edges],
        dtype=np.float64,
    )
    return {
        "state_count": len(spec.state_space),
        "valid_count": len(spec.valid_states),
        "invalid_count": len(invalid_states),
        "valid_energy_reference": valid_reference,
        "valid_energy_min": valid_min,
        "valid_energy_max": valid_max,
        "valid_energy_spread": valid_max - valid_min,
        "valid_equal": bool(valid_max - valid_min <= tolerance),
        "minimum_invalid_gap": minimum_gap,
        "target_gap": float(min_gap),
        "gap_ok": bool(minimum_gap >= min_gap - tolerance),
        "invalid_local_minima": len(local_states),
        "invalid_local_minimum_states": [list(state) for state in local_states],
        "invalid_local_minimum_details": [
            {
                "state": list(state),
                "bits": state_text(state),
                "energy": float(energies[state]),
                "distance_to_valid": distance_to_valid(state, spec),
            }
            for state in local_states
        ],
        "smooth_edge_count": len(smooth_edges),
        "mean_squared_smooth_jump": float(np.mean(jumps * jumps)) if len(jumps) else 0.0,
        "coefficient_l2": float(values @ values),
        "coefficient_max_abs": float(np.max(np.abs(values))) if len(values) else 0.0,
    }


def _validate_settings(settings: SolverSettings) -> None:
    positive = {
        "coeff_max": settings.coeff_max,
        "min_gap": settings.min_gap,
        "quantum": settings.quantum,
        "descent_margin": settings.descent_margin,
        "verification_tolerance": settings.verification_tolerance,
        "qp_abs_tolerance": settings.qp_abs_tolerance,
        "qp_rel_tolerance": settings.qp_rel_tolerance,
        "qp_rho": settings.qp_rho,
        "qp_sigma": settings.qp_sigma,
    }
    for name, value in positive.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    nonnegative = {
        "smooth_weight": settings.smooth_weight,
        "l2_weight": settings.l2_weight,
    }
    for name, value in nonnegative.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")
    if settings.smooth_weight == 0 and settings.l2_weight == 0:
        raise ValueError("at least one objective weight must be positive")
    if settings.max_iterations < 1:
        raise ValueError("max_iterations must be at least one")
    if settings.qp_max_iterations < 1:
        raise ValueError("qp_max_iterations must be at least one")
    if settings.qp_adaptive_interval < 1:
        raise ValueError("qp_adaptive_interval must be at least one")
    quantize_coefficients([0.0], settings.quantum, settings.coeff_max)


def _null_space(rows: np.ndarray, width: int) -> np.ndarray:
    if rows.size == 0:
        return np.eye(width, dtype=np.float64)
    _u, singular, vh = np.linalg.svd(rows, full_matrices=True)
    if len(singular) == 0:
        return np.eye(width, dtype=np.float64)
    threshold = max(rows.shape) * np.finfo(np.float64).eps * singular[0] * 10.0
    rank = int(np.sum(singular > threshold))
    return vh[rank:].T.copy()


def _constraint_violation(
    matrix: np.ndarray, lower: np.ndarray, upper: np.ndarray, point: np.ndarray
) -> float:
    values = matrix @ point
    low = np.maximum(lower - values, 0.0)
    high = np.maximum(values - upper, 0.0)
    return float(max(np.max(low, initial=0.0), np.max(high, initial=0.0)))


def _solve_box_qp(
    quadratic: np.ndarray,
    matrix: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    settings: SolverSettings,
) -> tuple[np.ndarray, QpStats]:
    """Solve a small convex QP with an OSQP-style scaled ADMM iteration."""

    dimension = quadratic.shape[0]
    if quadratic.shape != (dimension, dimension):
        raise ValueError("quadratic matrix must be square")
    if matrix.ndim != 2 or matrix.shape[1] != dimension:
        raise ValueError("constraint matrix width does not match QP dimension")
    if lower.shape != (matrix.shape[0],) or upper.shape != (matrix.shape[0],):
        raise ValueError("constraint bounds do not match row count")
    if np.any(lower > upper):
        raise OptimizationError("QP has a constraint with lower bound above upper bound")

    row_norm = np.linalg.norm(matrix, axis=1)
    keep = row_norm > 1e-14
    for idx in np.flatnonzero(~keep):
        if lower[idx] > 0.0 or upper[idx] < 0.0:
            raise OptimizationError("QP is infeasible: a zero row excludes zero")
    a = matrix[keep] / row_norm[keep, None]
    lo = lower[keep] / row_norm[keep]
    hi = upper[keep] / row_norm[keep]
    if dimension == 0:
        if len(a) and _constraint_violation(a, lo, hi, np.empty(0)) > settings.qp_abs_tolerance:
            raise OptimizationError("QP is infeasible after valid-energy elimination")
        empty = np.empty(0, dtype=np.float64)
        return empty, QpStats(0, True, 0.0, 0.0, 0.0, 0.0, settings.qp_rho, 0)

    p = 0.5 * (quadratic + quadratic.T)
    smallest_eigenvalue = float(np.min(np.linalg.eigvalsh(p)))
    if smallest_eigenvalue < -1e-10:
        raise OptimizationError(
            "QP objective is not convex: "
            f"smallest eigenvalue={smallest_eigenvalue:.6g}"
        )
    x = np.zeros(dimension, dtype=np.float64)
    z = np.clip(a @ x, lo, hi)
    scaled_dual = np.zeros(len(z), dtype=np.float64)
    rho = settings.qp_rho
    sigma = settings.qp_sigma
    primal = math.inf
    dual = math.inf
    converged = False
    iterations = 0

    def factor(current_rho: float) -> np.ndarray:
        system = p + current_rho * (a.T @ a) + sigma * np.eye(dimension)
        jitter = 0.0
        for _attempt in range(6):
            try:
                return np.linalg.cholesky(system + jitter * np.eye(dimension))
            except np.linalg.LinAlgError:
                jitter = 1e-12 if jitter == 0.0 else jitter * 100.0
        raise OptimizationError("QP factorization failed; objective may not be convex")

    chol = factor(rho)
    for iteration in range(1, settings.qp_max_iterations + 1):
        previous_x = x
        rhs = rho * (a.T @ (z - scaled_dual)) + sigma * previous_x
        intermediate = np.linalg.solve(chol, rhs)
        x = np.linalg.solve(chol.T, intermediate)
        ax = a @ x
        previous_z = z
        z = np.clip(ax + scaled_dual, lo, hi)
        scaled_dual = scaled_dual + ax - z

        primal_vector = ax - z
        dual_step_vector = rho * (a.T @ (z - previous_z))
        dual_vector = p @ x + a.T @ (rho * scaled_dual)
        primal = float(np.linalg.norm(primal_vector, ord=np.inf)) if len(primal_vector) else 0.0
        dual = float(np.linalg.norm(dual_vector, ord=np.inf)) if len(dual_vector) else 0.0
        eps_primal = settings.qp_abs_tolerance + settings.qp_rel_tolerance * max(
            float(np.linalg.norm(ax, ord=np.inf)) if len(ax) else 0.0,
            float(np.linalg.norm(z, ord=np.inf)) if len(z) else 0.0,
        )
        dual_scale = rho * (a.T @ scaled_dual)
        eps_dual = settings.qp_abs_tolerance + settings.qp_rel_tolerance * (
            max(
                float(np.linalg.norm(p @ x, ord=np.inf)),
                float(np.linalg.norm(dual_scale, ord=np.inf)) if len(dual_scale) else 0.0,
            )
        )
        iterations = iteration
        if primal <= eps_primal and dual <= eps_dual:
            converged = True
            break

        if iteration % settings.qp_adaptive_interval == 0:
            old_rho = rho
            dual_step = (
                float(np.linalg.norm(dual_step_vector, ord=np.inf))
                if len(dual_step_vector)
                else 0.0
            )
            if primal > 10.0 * max(dual_step, 1e-16):
                rho = min(rho * 2.0, 1e8)
            elif dual_step > 10.0 * max(primal, 1e-16):
                rho = max(rho / 2.0, 1e-8)
            if rho != old_rho:
                scaled_dual *= old_rho / rho
                chol = factor(rho)

    violation = _constraint_violation(a, lo, hi, x)
    if not converged:
        raise OptimizationError(
            "convex QP reached its iteration limit before satisfying the residual tolerances: "
            f"primal={primal:.3g}, dual={dual:.3g}, iterations={iterations}"
        )
    acceptable = max(settings.qp_abs_tolerance * 50.0, settings.verification_tolerance * 0.25)
    if violation > acceptable:
        raise OptimizationError(
            "convex QP did not reach a feasible point: "
            f"violation={violation:.3g}, primal={primal:.3g}, dual={dual:.3g}, "
            f"iterations={iterations}"
        )
    objective = 0.5 * float(x @ p @ x)
    return x, QpStats(
        iterations=iterations,
        converged=converged,
        primal_residual=primal,
        dual_residual=dual,
        constraint_violation=violation,
        objective=objective,
        rho=rho,
        nullity=dimension,
    )


def _resolved_cut(cut: DescentCut, settings: SolverSettings) -> DescentCut:
    return cut if cut.margin is not None else replace(cut, margin=settings.descent_margin)


def _solve_continuous(
    spec: ProblemSpec,
    settings: SolverSettings,
    cuts: Sequence[DescentCut],
) -> tuple[np.ndarray, QpStats]:
    width = coefficient_count(spec.n)
    reference = feature_row(spec.valid_states[0])
    equality_rows = np.vstack(
        [feature_row(state) - reference for state in spec.valid_states[1:]]
    ) if len(spec.valid_states) > 1 else np.empty((0, width), dtype=np.float64)
    basis = _null_space(equality_rows, width)
    if basis.shape[1] == 0:
        raise OptimizationError("valid equal-energy constraints leave no nonzero coefficient direction")

    smooth_edges = generate_smooth_edges(spec)
    if smooth_edges:
        differences = np.vstack(
            [feature_row(left) - feature_row(right) for left, right in smooth_edges]
        )
        roughness = (differences.T @ differences) / len(differences)
    else:
        roughness = np.zeros((width, width), dtype=np.float64)
    full_quadratic = 2.0 * (
        settings.smooth_weight * roughness
        + settings.l2_weight * np.eye(width, dtype=np.float64)
    )
    quadratic = basis.T @ full_quadratic @ basis

    valid_set = set(spec.valid_states)
    rows: list[np.ndarray] = []
    lower: list[float] = []
    upper: list[float] = []
    for state in spec.state_space:
        if state in valid_set:
            continue
        rows.append((feature_row(state) - reference) @ basis)
        lower.append(settings.min_gap)
        upper.append(math.inf)
    for cut in cuts:
        resolved = _resolved_cut(cut, settings)
        rows.append((feature_row(resolved.state) - feature_row(resolved.parent)) @ basis)
        lower.append(float(resolved.margin))
        upper.append(math.inf)

    # Coefficient bounds are constraints on theta = basis @ reduced.
    rows.extend(row.copy() for row in basis)
    lower.extend([-settings.coeff_max] * width)
    upper.extend([settings.coeff_max] * width)
    matrix = np.vstack(rows)
    reduced, stats = _solve_box_qp(
        quadratic,
        matrix,
        np.asarray(lower, dtype=np.float64),
        np.asarray(upper, dtype=np.float64),
        settings,
    )
    coefficients = basis @ reduced
    stats = replace(stats, nullity=basis.shape[1])
    return coefficients, stats


def descent_cut_payload(cut: DescentCut) -> dict[str, Any]:
    return {
        "state": list(cut.state),
        "state_bits": state_text(cut.state),
        "parent": list(cut.parent),
        "parent_bits": state_text(cut.parent),
        "margin": None if cut.margin is None else float(cut.margin),
    }


def solve_problem(spec: ProblemSpec, settings: SolverSettings | None = None) -> OptimizationResult:
    settings = SolverSettings() if settings is None else settings
    _validate_settings(settings)
    cut_margins: dict[tuple[State, State], float] = {}
    for cut in spec.descent_cuts:
        resolved = _resolved_cut(cut, settings)
        cut_margins[(resolved.state, resolved.parent)] = float(resolved.margin)

    history: list[dict[str, Any]] = []
    continuous = np.empty(0)
    quantized = np.empty(0)
    continuous_audit: dict[str, Any] = {}
    quantized_audit: dict[str, Any] = {}
    qp_stats: QpStats | None = None

    for iteration in range(settings.max_iterations):
        active_cuts = tuple(
            DescentCut(state=key[0], parent=key[1], margin=margin)
            for key, margin in sorted(
                cut_margins.items(), key=lambda item: (state_code(item[0][0]), state_code(item[0][1]))
            )
        )
        continuous, qp_stats = _solve_continuous(spec, settings, active_cuts)
        continuous_audit = audit_solution(
            spec, continuous, settings.min_gap, settings.verification_tolerance
        )
        if not continuous_audit["valid_equal"] or not continuous_audit["gap_ok"]:
            raise OptimizationError(
                "continuous QP failed its exhaustive audit: "
                f"valid_spread={continuous_audit['valid_energy_spread']:.3g}, "
                f"gap={continuous_audit['minimum_invalid_gap']:.6g}"
            )

        quantized = quantize_coefficients(
            continuous, settings.quantum, settings.coeff_max
        )
        quantized_audit = audit_solution(
            spec, quantized, settings.min_gap, settings.verification_tolerance
        )
        if not quantized_audit["valid_equal"]:
            raise OptimizationError(
                "quantization broke the hard common valid-energy manifold: "
                f"spread={quantized_audit['valid_energy_spread']:.6g}; "
                "use a finer quantum or a different coefficient bound"
            )
        if not quantized_audit["gap_ok"]:
            raise OptimizationError(
                "quantization broke the required invalid-state gap: "
                f"gap={quantized_audit['minimum_invalid_gap']:.6g}, "
                f"target={settings.min_gap:.6g}; use a finer quantum"
            )

        traps = [tuple(state) for state in quantized_audit["invalid_local_minimum_states"]]
        iteration_row: dict[str, Any] = {
            "iteration": iteration,
            "active_descent_cuts": len(active_cuts),
            "qp": asdict(qp_stats),
            "continuous": continuous_audit,
            "quantized": quantized_audit,
            "added_or_strengthened_cuts": [],
        }
        history.append(iteration_row)
        if not traps:
            final_cuts = tuple(
                DescentCut(state=key[0], parent=key[1], margin=margin)
                for key, margin in sorted(
                    cut_margins.items(), key=lambda item: (state_code(item[0][0]), state_code(item[0][1]))
                )
            )
            return OptimizationResult(
                spec=spec,
                settings=settings,
                continuous_coefficients=continuous,
                quantized_coefficients=quantized,
                continuous_audit=continuous_audit,
                quantized_audit=quantized_audit,
                qp_stats=qp_stats,
                history=history,
                descent_cuts=final_cuts,
            )

        for trap in traps:
            parent = select_descent_parent(trap, spec)
            key = (trap, parent)
            old_margin = cut_margins.get(key, 0.0)
            new_margin = old_margin + settings.descent_margin
            cut_margins[key] = new_margin
            iteration_row["added_or_strengthened_cuts"].append(
                {
                    **descent_cut_payload(DescentCut(trap, parent, new_margin)),
                    "previous_margin": old_margin,
                }
            )

    assert qp_stats is not None
    raise OptimizationError(
        "quantized solution still has "
        f"{quantized_audit.get('invalid_local_minima', 'unknown')} invalid local minima "
        f"after {settings.max_iterations} cutting iterations"
    )


def _add_solver_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--coeff-max", type=float, default=SolverSettings.coeff_max)
    parser.add_argument("--min-gap", type=float, default=SolverSettings.min_gap)
    parser.add_argument("--quantum", type=float, default=SolverSettings.quantum)
    parser.add_argument("--smooth-weight", type=float, default=SolverSettings.smooth_weight)
    parser.add_argument("--l2-weight", type=float, default=SolverSettings.l2_weight)
    parser.add_argument("--descent-margin", type=float, default=SolverSettings.descent_margin)
    parser.add_argument("--max-iterations", type=int, default=SolverSettings.max_iterations)
    parser.add_argument(
        "--verification-tolerance", type=float, default=SolverSettings.verification_tolerance
    )
    parser.add_argument("--qp-max-iterations", type=int, default=SolverSettings.qp_max_iterations)
    parser.add_argument("--qp-abs-tolerance", type=float, default=SolverSettings.qp_abs_tolerance)
    parser.add_argument("--qp-rel-tolerance", type=float, default=SolverSettings.qp_rel_tolerance)
    parser.add_argument("--qp-rho", type=float, default=SolverSettings.qp_rho)
    parser.add_argument("--json-out", type=Path)


def _settings_from_args(args: argparse.Namespace) -> SolverSettings:
    return SolverSettings(
        coeff_max=args.coeff_max,
        min_gap=args.min_gap,
        quantum=args.quantum,
        smooth_weight=args.smooth_weight,
        l2_weight=args.l2_weight,
        descent_margin=args.descent_margin,
        max_iterations=args.max_iterations,
        verification_tolerance=args.verification_tolerance,
        qp_max_iterations=args.qp_max_iterations,
        qp_abs_tolerance=args.qp_abs_tolerance,
        qp_rel_tolerance=args.qp_rel_tolerance,
        qp_rho=args.qp_rho,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Quantized pairwise-Ising landscape optimizer (NumPy-only)"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo-gate", help="solve a built-in HA or FA truth table")
    demo.add_argument("--gate", choices=("ha", "fa"), required=True)
    _add_solver_arguments(demo)
    solve = commands.add_parser("solve-spec", help="solve a portable JSON specification")
    solve.add_argument("--spec", type=Path, required=True)
    _add_solver_arguments(solve)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        spec = build_demo_spec(args.gate) if args.command == "demo-gate" else load_spec(args.spec)
        result = solve_problem(spec, _settings_from_args(args))
        payload = result.to_dict()
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0
    except (SpecError, OptimizationError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
