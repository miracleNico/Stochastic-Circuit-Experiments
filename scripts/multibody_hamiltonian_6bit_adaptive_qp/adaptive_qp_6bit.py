"""6-bit least+carry-shadow adaptive 2/3/4-body QP experiment.

This is a continuous floating-point Hamiltonian experiment for the least-node
6-bit adder with six true carry-shadow nodes:

    a0..a5, b0..b5, s0..s6, c1..c6

The optimizer uses the same soft-valid QP as the 5-bit experiment, but the
exhaustive full-cube audit uses a Walsh-Hadamard transform so that the 2^25
state landscape can be evaluated without forming a dense state-by-term matrix.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import argparse
import csv
import json
import math
import os
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:  # pragma: no cover
    gp = None
    GRB = None


WIDTH = 6
NODE_NAMES = [f"a{i}" for i in range(WIDTH)]
NODE_NAMES += [f"b{i}" for i in range(WIDTH)]
NODE_NAMES += [f"s{i}" for i in range(WIDTH + 1)]
NODE_NAMES += [f"c{i}" for i in range(1, WIDTH + 1)]
N = len(NODE_NAMES)
VALID_COUNT = 1 << (2 * WIDTH)
TOTAL_STATES = 1 << N
DEFAULT_OUT = _REPO_ROOT / "results_and_reports/multibody_hamiltonian_6bit_adaptive_qp/out"
BYTE_COUNTS = np.array([int(i).bit_count() for i in range(256)], dtype=np.uint8)


@dataclass(frozen=True)
class Design:
    width: int
    node_names: list[str]
    valid_codes: np.ndarray
    valid_lookup: np.ndarray

    @property
    def n(self) -> int:
        return len(self.node_names)

    @property
    def total_states(self) -> int:
        return 1 << self.n


@dataclass
class QpSolution:
    run_key: str
    terms: list[tuple[int, ...]]
    theta: np.ndarray
    reference_energy: float
    gamma: float
    objective: float
    status: int
    valid_mean: float
    valid_std: float
    valid_max_deviation: float
    valid_over_soft_cap: int
    coeff_l2: float
    coeff_max_abs: float


def value_bits(value: int, width: int) -> list[int]:
    return [(value >> bit) & 1 for bit in range(width)]


def carry_bits(aval: int, bval: int, width: int = WIDTH) -> list[int]:
    carry = 0
    out = []
    for bit in range(width):
        carry = (((aval >> bit) & 1) + ((bval >> bit) & 1) + carry) >> 1
        out.append(carry)
    return out


def valid_state(aval: int, bval: int, width: int = WIDTH) -> list[int]:
    total = aval + bval
    bits = value_bits(aval, width)
    bits += value_bits(bval, width)
    bits += value_bits(total, width + 1)
    bits += carry_bits(aval, bval, width)
    return bits


def bits_to_codes(bits: np.ndarray) -> np.ndarray:
    weights = np.left_shift(np.uint32(1), np.arange(bits.shape[1], dtype=np.uint32))
    return (bits.astype(np.uint32) @ weights).astype(np.uint32)


def codes_to_bits(codes: np.ndarray, n: int = N) -> np.ndarray:
    shifts = np.arange(n, dtype=np.uint32)
    return ((codes.astype(np.uint32)[:, None] >> shifts) & np.uint32(1)).astype(np.uint8)


def build_design() -> Design:
    states = np.empty((VALID_COUNT, N), dtype=np.uint8)
    row = 0
    for aval in range(1 << WIDTH):
        for bval in range(1 << WIDTH):
            states[row] = valid_state(aval, bval)
            row += 1
    valid_codes = np.unique(bits_to_codes(states))
    valid_lookup = np.zeros(TOTAL_STATES, dtype=bool)
    valid_lookup[valid_codes] = True
    return Design(WIDTH, NODE_NAMES, valid_codes, valid_lookup)


def term_mask(term: tuple[int, ...]) -> int:
    mask = 0
    for idx in term:
        mask |= 1 << idx
    return mask


def full_terms(max_order: int) -> list[tuple[int, ...]]:
    terms: list[tuple[int, ...]] = []
    for order in range(1, max_order + 1):
        terms.extend(combinations(range(N), order))
    return list(terms)


def term_count_by_order(terms: list[tuple[int, ...]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for term in terms:
        key = str(len(term))
        out[key] = out.get(key, 0) + 1
    return out


def feature_matrix(bits: np.ndarray, terms: list[tuple[int, ...]]) -> np.ndarray:
    spins = 2.0 * bits.astype(np.float64) - 1.0
    matrix = np.empty((len(bits), len(terms)), dtype=np.float64)
    for col, term in enumerate(terms):
        value = np.ones(len(bits), dtype=np.float64)
        for idx in term:
            value *= spins[:, idx]
        matrix[:, col] = -value
    return matrix


def feature_matrix_codes(codes: np.ndarray, terms: list[tuple[int, ...]]) -> np.ndarray:
    return feature_matrix(codes_to_bits(codes), terms)


def fwht_inplace(values: np.ndarray) -> None:
    h = 1
    n = len(values)
    while h < n:
        values.shape = (-1, h * 2)
        left = values[:, :h].copy()
        right = values[:, h:].copy()
        values[:, :h] = left + right
        values[:, h:] = left - right
        values.shape = (n,)
        h *= 2


def energies_full_cube(terms: list[tuple[int, ...]], theta: np.ndarray) -> np.ndarray:
    coeff = np.zeros(TOTAL_STATES, dtype=np.float64)
    for term, value in zip(terms, theta):
        sign = -((-1.0) ** len(term))
        coeff[term_mask(term)] += sign * float(value)
    fwht_inplace(coeff)
    return coeff


def bitcount32(values: np.ndarray) -> np.ndarray:
    raw = values.astype(np.uint32, copy=False).view(np.uint8).reshape(-1, 4)
    return BYTE_COUNTS[raw].sum(axis=1)


def nearest_valid_codes(codes: np.ndarray, valid_codes: np.ndarray, chunk: int = 256) -> np.ndarray:
    nearest = np.empty(len(codes), dtype=np.uint32)
    for start in range(0, len(codes), chunk):
        stop = min(start + chunk, len(codes))
        xor = np.bitwise_xor(codes[start:stop, None], valid_codes[None, :])
        dist = BYTE_COUNTS[xor.astype(np.uint32, copy=False).view(np.uint8).reshape(xor.shape + (4,))].sum(axis=2)
        nearest[start:stop] = valid_codes[np.argmin(dist, axis=1)]
    return nearest


def initial_invalid_codes(design: Design, count: int, rng: np.random.Generator) -> np.ndarray:
    rows = []
    for bit in range(design.n):
        flipped = design.valid_codes ^ np.uint32(1 << bit)
        rows.append(flipped[~design.valid_lookup[flipped]])
    while sum(len(row) for row in rows) < count + design.n * len(design.valid_codes):
        sample = rng.integers(0, design.total_states, size=max(count, 8192), dtype=np.uint32)
        rows.append(sample[~design.valid_lookup[sample]])
    return np.unique(np.concatenate(rows))[:count].astype(np.uint32, copy=False)


def solve_soft_valid_qp(
    design: Design,
    run_key: str,
    terms: list[tuple[int, ...]],
    invalid_codes: np.ndarray,
    args: argparse.Namespace,
    log_file: Path,
) -> QpSolution:
    if gp is None or GRB is None:
        raise RuntimeError("gurobipy is required")
    license_path = Path(r"C:\gurobi1302\gurobi.lic")
    if "GRB_LICENSE_FILE" not in os.environ and license_path.exists():
        os.environ["GRB_LICENSE_FILE"] = str(license_path)

    valid_a = feature_matrix_codes(design.valid_codes, terms)

    model = gp.Model(f"soft_valid_6bit_{run_key}")
    # Keep a solver trace on disk for long adaptive QPs while avoiding noisy
    # console output unless explicitly requested.
    model.Params.OutputFlag = 1
    model.Params.LogToConsole = 1 if args.gurobi_output else 0
    model.Params.LogFile = str(log_file)
    model.Params.Method = args.gurobi_method
    model.Params.Crossover = args.gurobi_crossover
    if args.gurobi_threads > 0:
        model.Params.Threads = args.gurobi_threads
    if args.bar_conv_tol > 0:
        model.Params.BarConvTol = args.bar_conv_tol
    if args.time_limit > 0:
        model.Params.TimeLimit = args.time_limit

    theta = model.addMVar(len(terms), lb=-args.coeff_max, ub=args.coeff_max, name="theta")
    ref = model.addVar(lb=-GRB.INFINITY, name="valid_ref")
    gamma = model.addVar(lb=0.0, name="gamma")
    if args.gamma_max > 0:
        gamma.ub = args.gamma_max
    valid_resid = model.addMVar(len(design.valid_codes), lb=-GRB.INFINITY, name="valid_resid")
    valid_cap = model.addMVar(len(design.valid_codes), lb=0.0, name="valid_soft_cap_excess")

    model.addConstr(valid_a @ theta - ref - valid_resid == 0.0, name="valid_resid_def")
    model.addConstr(valid_resid - args.valid_soft_cap <= valid_cap, name="valid_cap_pos")
    model.addConstr(-valid_resid - args.valid_soft_cap <= valid_cap, name="valid_cap_neg")
    for start in range(0, len(invalid_codes), args.constraint_chunk):
        stop = min(start + args.constraint_chunk, len(invalid_codes))
        invalid_a = feature_matrix_codes(invalid_codes[start:stop], terms)
        model.addConstr(invalid_a @ theta - ref - gamma >= 0.0, name=f"invalid_gap_{start}_{stop}")

    objective = -args.gamma_weight * gamma
    objective += (args.valid_weight / len(design.valid_codes)) * (valid_resid @ valid_resid)
    objective += (args.cap_weight / len(design.valid_codes)) * (valid_cap @ valid_cap)
    quad_weights = np.array(
        [(args.tv_weight * 4.0 * len(term) / design.n) + (args.coeff_weight / len(terms)) for term in terms],
        dtype=np.float64,
    )
    objective += gp.quicksum(float(weight) * theta[idx] * theta[idx] for idx, weight in enumerate(quad_weights))
    model.setObjective(objective, GRB.MINIMIZE)
    model.update()
    print(
        f"solve {run_key}: terms={len(terms)} cuts={len(invalid_codes)} "
        f"rows={model.NumConstrs} cols={model.NumVars}",
        flush=True,
    )
    model.optimize()
    if model.Status not in {GRB.OPTIMAL, GRB.SUBOPTIMAL, GRB.TIME_LIMIT} or model.SolCount == 0:
        raise RuntimeError(f"Gurobi failed for {run_key}: status={model.Status}, sol_count={model.SolCount}")

    theta_value = np.array(theta.X, dtype=np.float64)
    valid_energy = valid_a @ theta_value
    ref_value = float(ref.X)
    valid_delta = valid_energy - ref_value
    return QpSolution(
        run_key=run_key,
        terms=terms,
        theta=theta_value,
        reference_energy=ref_value,
        gamma=float(gamma.X),
        objective=float(model.ObjVal),
        status=int(model.Status),
        valid_mean=float(np.mean(valid_energy)),
        valid_std=float(np.std(valid_energy)),
        valid_max_deviation=float(np.max(np.abs(valid_delta))),
        valid_over_soft_cap=int(np.sum(np.abs(valid_delta) > args.valid_soft_cap)),
        coeff_l2=float(theta_value @ theta_value),
        coeff_max_abs=float(np.max(np.abs(theta_value))) if len(theta_value) else 0.0,
    )


def find_gap_violations(
    design: Design,
    terms: list[tuple[int, ...]],
    solution: QpSolution,
    args: argparse.Namespace,
) -> dict:
    energies = energies_full_cube(terms, solution.theta)
    gaps = energies - solution.reference_energy
    invalid = ~design.valid_lookup
    invalid_gaps = gaps[invalid]
    min_invalid_gap = float(np.min(invalid_gaps))
    bad = invalid & (gaps < solution.gamma - args.violation_tol)
    bad_codes = np.flatnonzero(bad).astype(np.uint32)
    if len(bad_codes):
        bad_gaps = gaps[bad_codes]
        take = min(args.max_cuts_per_round, len(bad_codes))
        idx = np.argpartition(bad_gaps, take - 1)[:take]
        selected = bad_codes[idx]
    else:
        selected = np.empty(0, dtype=np.uint32)
    return {
        "violation_count": int(len(bad_codes)),
        "min_invalid_gap": min_invalid_gap,
        "selected_codes": selected,
        "energies": energies,
    }


def cap_active_codes(codes: np.ndarray, energies: np.ndarray, reference: float, limit: int) -> np.ndarray:
    if limit <= 0 or len(codes) <= limit:
        return codes.astype(np.uint32, copy=False)
    gaps = energies[codes] - reference
    idx = np.argpartition(gaps, limit - 1)[:limit]
    return np.unique(codes[idx].astype(np.uint32, copy=False))


def local_minimum_codes(energies: np.ndarray, valid_lookup: np.ndarray, tol: float) -> np.ndarray:
    local = ~valid_lookup.copy()
    for bit in range(N):
        block = 1 << (bit + 1)
        half = 1 << bit
        e_view = energies.reshape(-1, block)
        l_view = local.reshape(-1, block)
        low = e_view[:, :half]
        high = e_view[:, half:]
        low_ok = low <= high + tol
        high_ok = high <= low + tol
        l_view[:, :half] &= low_ok
        l_view[:, half:] &= high_ok
    return np.flatnonzero(local).astype(np.uint32)


def sampled_one_bit_jumps(energies: np.ndarray, args: argparse.Namespace, seed_offset: int) -> dict:
    if args.jump_sample_states <= 0:
        return {
            "sample_mean_one_bit_abs_jump": None,
            "sample_p90_one_bit_abs_jump": None,
            "sample_p99_one_bit_abs_jump": None,
            "one_bit_jump_sample_count": 0,
        }
    rng = np.random.default_rng(args.seed + seed_offset)
    count = min(args.jump_sample_states, TOTAL_STATES)
    codes = rng.integers(0, TOTAL_STATES, size=count, dtype=np.uint32)
    bits = rng.integers(0, N, size=count, dtype=np.uint32)
    jumps = np.abs(energies[codes ^ (np.uint32(1) << bits)] - energies[codes])
    return {
        "sample_mean_one_bit_abs_jump": float(np.mean(jumps)),
        "sample_p90_one_bit_abs_jump": float(np.percentile(jumps, 90)),
        "sample_p99_one_bit_abs_jump": float(np.percentile(jumps, 99)),
        "one_bit_jump_sample_count": int(count),
    }


def exact_audit_and_plots(
    design: Design,
    solution: QpSolution,
    args: argparse.Namespace,
    run_dir: Path,
    energies: np.ndarray | None = None,
) -> dict:
    if energies is None:
        energies = energies_full_cube(solution.terms, solution.theta)
    valid = design.valid_lookup
    valid_e = energies[valid]
    invalid_e = energies[~valid]
    valid_delta = valid_e - solution.reference_energy
    invalid_gap = invalid_e - solution.reference_energy
    local_codes = local_minimum_codes(energies, valid, args.local_min_tol)
    local_e = energies[local_codes] if len(local_codes) else np.empty(0, dtype=np.float64)
    local_dist = np.empty(0, dtype=np.int16)
    if len(local_codes):
        sample = local_codes[: args.local_distance_cap]
        nearest = nearest_valid_codes(sample, design.valid_codes)
        local_dist = bitcount32(np.bitwise_xor(sample, nearest)).astype(np.int16)
    dist_hist: dict[str, int] = {}
    for item in local_dist:
        dist_hist[str(int(item))] = dist_hist.get(str(int(item)), 0) + 1

    roughness = 4.0 / design.n * float(sum(len(term) * coeff * coeff for term, coeff in zip(solution.terms, solution.theta)))
    audit = {
        "run_key": solution.run_key,
        "width": design.width,
        "node_count": design.n,
        "state_count": design.total_states,
        "valid_count": int(np.sum(valid)),
        "invalid_count": int(np.sum(~valid)),
        "term_count": len(solution.terms),
        "term_count_by_order": term_count_by_order(solution.terms),
        "reference_energy": solution.reference_energy,
        "gamma": solution.gamma,
        "valid_energy_mean": float(np.mean(valid_e)),
        "valid_energy_std": float(np.std(valid_e)),
        "valid_energy_min": float(np.min(valid_e)),
        "valid_energy_max": float(np.max(valid_e)),
        "valid_max_deviation": float(np.max(np.abs(valid_delta))),
        "valid_over_soft_cap": int(np.sum(np.abs(valid_delta) > args.valid_soft_cap)),
        "min_invalid_gap": float(np.min(invalid_gap)),
        "gap_violation_count": int(np.sum(invalid_gap < solution.gamma - args.violation_tol)),
        "invalid_local_minima": int(len(local_codes)),
        "invalid_local_minimum_gap_min": float(np.min(local_e - solution.reference_energy)) if len(local_e) else None,
        "invalid_local_minimum_distance_hist_sampled": dist_hist,
        "invalid_local_minimum_distance_sample_count": int(len(local_dist)),
        "mean_one_bit_energy_jump_squared": roughness,
        "rms_one_bit_energy_jump": float(math.sqrt(max(roughness, 0.0))),
        "p01_invalid_gap": float(np.percentile(invalid_gap, 1)),
        "p10_invalid_gap": float(np.percentile(invalid_gap, 10)),
        "coeff_l2": solution.coeff_l2,
        "coeff_max_abs": solution.coeff_max_abs,
        "nonzero_terms_abs_gt_1e_9": int(np.sum(np.abs(solution.theta) > 1e-9)),
    }
    stable_offset = sum((idx + 1) * ord(ch) for idx, ch in enumerate(solution.run_key))
    audit.update(sampled_one_bit_jumps(energies, args, seed_offset=stable_offset))
    write_json(run_dir / "exhaustive_audit.json", audit)
    write_metrics_csv(run_dir / "metrics.csv", audit)
    plot_energy_hist(run_dir / "energy_histogram.png", solution, valid_e, invalid_e, args)
    plot_valid_spread(run_dir / "valid_energy_spread.png", solution, valid_delta)
    plot_local_min_hist(run_dir / "local_minimum_energy_histogram.png", solution, local_e)
    plot_low_invalid(run_dir / "low_energy_invalid_states.png", solution, invalid_gap)
    return audit


def solution_payload(design: Design, solution: QpSolution, args: argparse.Namespace) -> dict:
    terms = []
    for term, coeff in zip(solution.terms, solution.theta):
        if abs(float(coeff)) > 1e-9:
            terms.append(
                {
                    "indices": list(term),
                    "nodes": [design.node_names[idx] for idx in term],
                    "order": len(term),
                    "coefficient": float(coeff),
                }
            )
    return {
        "run_key": solution.run_key,
        "width": design.width,
        "nodes": design.node_names,
        "term_count": len(solution.terms),
        "term_count_by_order": term_count_by_order(solution.terms),
        "config": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "solution": {
            "reference_energy": solution.reference_energy,
            "gamma": solution.gamma,
            "objective": solution.objective,
            "status": solution.status,
            "valid_mean": solution.valid_mean,
            "valid_std": solution.valid_std,
            "valid_max_deviation": solution.valid_max_deviation,
            "valid_over_soft_cap": solution.valid_over_soft_cap,
            "coeff_l2": solution.coeff_l2,
            "coeff_max_abs": solution.coeff_max_abs,
            "nonzero_terms": terms,
        },
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_metrics_csv(path: Path, row: dict) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(row.keys()))
        writer.writeheader()
        writer.writerow(row)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = json.loads(json.dumps(payload, default=str))
    path.write_text(json.dumps(safe, indent=2), encoding="utf-8")


def plot_energy_hist(path: Path, solution: QpSolution, valid_e: np.ndarray, invalid_e: np.ndarray, args: argparse.Namespace) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    invalid_plot = invalid_e
    label = "invalid"
    if args.plot_invalid_sample > 0 and len(invalid_e) > args.plot_invalid_sample:
        rng = np.random.default_rng(args.seed + 911)
        idx = rng.choice(len(invalid_e), size=args.plot_invalid_sample, replace=False)
        invalid_plot = invalid_e[idx]
        label = f"invalid sample ({args.plot_invalid_sample})"
    ax.hist(invalid_plot, bins=160, color="#c44e52", alpha=0.65, label=label)
    ax.hist(valid_e, bins=40, color="#2ca02c", alpha=0.85, label="valid")
    ax.axvline(solution.reference_energy, color="black", linewidth=1.0, label="E0")
    ax.set_title(f"{solution.run_key}: full energy histogram")
    ax.set_xlabel("Hamiltonian energy")
    ax.set_ylabel("state count")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_valid_spread(path: Path, solution: QpSolution, valid_delta: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(7, 4), dpi=160)
    ax.hist(valid_delta, bins=60, color="#2ca02c", alpha=0.8)
    ax.axvline(-0.5, color="#444444", linewidth=0.8, linestyle="--")
    ax.axvline(0.5, color="#444444", linewidth=0.8, linestyle="--")
    ax.set_title(f"{solution.run_key}: valid energy deviation")
    ax.set_xlabel("H(valid)-E0")
    ax.set_ylabel("valid states")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_local_min_hist(path: Path, solution: QpSolution, local_e: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(7, 4), dpi=160)
    if len(local_e):
        ax.hist(local_e - solution.reference_energy, bins=100, color="#8172b3", alpha=0.8)
    ax.axvline(solution.gamma, color="black", linewidth=1.0, label="gamma")
    ax.set_title(f"{solution.run_key}: invalid local minima")
    ax.set_xlabel("local-minimum gap above E0")
    ax.set_ylabel("count")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_low_invalid(path: Path, solution: QpSolution, invalid_gap: np.ndarray) -> None:
    take = min(10000, len(invalid_gap))
    low = np.sort(invalid_gap)[:take]
    fig, ax = plt.subplots(figsize=(8, 4), dpi=160)
    ax.plot(np.arange(take), low, color="#c44e52", linewidth=0.8)
    ax.axhline(solution.gamma, color="black", linewidth=1.0, linestyle="--", label="gamma")
    ax.set_title(f"{solution.run_key}: lowest invalid states")
    ax.set_xlabel("sorted invalid-state rank")
    ax.set_ylabel("H(invalid)-E0")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def solve_cutting_plane(
    design: Design,
    run_key: str,
    terms: list[tuple[int, ...]],
    args: argparse.Namespace,
    seed_offset: int,
) -> tuple[QpSolution, dict]:
    run_dir = args.out / run_key
    run_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed + seed_offset)
    resume_path = run_dir / "invalid_cuts_partial.npz"
    if args.resume_cuts and resume_path.exists():
        invalid_codes = np.load(resume_path)["codes"].astype(np.uint32, copy=False)
        print(f"{run_key}: resumed {len(invalid_codes)} active cuts from {resume_path}", flush=True)
    else:
        invalid_codes = initial_invalid_codes(design, args.initial_invalid, rng)
    history = []
    solution: QpSolution | None = None
    last_energies: np.ndarray | None = None
    for round_idx in range(args.max_rounds + 1):
        solution = solve_soft_valid_qp(design, run_key, terms, invalid_codes, args, run_dir / f"gurobi_round{round_idx}.log")
        write_json(run_dir / f"solution_round{round_idx}.json", solution_payload(design, solution, args))
        np.savez_compressed(run_dir / "invalid_cuts_partial.npz", codes=invalid_codes)
        violations = find_gap_violations(design, terms, solution, args)
        last_energies = violations["energies"]
        add_codes = violations["selected_codes"]
        before = len(invalid_codes)
        if len(add_codes):
            invalid_codes = np.unique(np.concatenate([invalid_codes, add_codes.astype(np.uint32, copy=False)]))
        after_add = len(invalid_codes)
        if args.max_active_cuts > 0 and len(invalid_codes) > args.max_active_cuts:
            invalid_codes = cap_active_codes(invalid_codes, violations["energies"], solution.reference_energy, args.max_active_cuts)
        np.savez_compressed(run_dir / "invalid_cuts_partial.npz", codes=invalid_codes)
        new_cuts = max(0, after_add - before)
        active_pruned = max(0, after_add - len(invalid_codes))
        row = {
            "round": round_idx,
            "cut_count": int(len(invalid_codes)),
            "new_cuts": int(new_cuts),
            "active_pruned": int(active_pruned),
            "violation_count": int(violations["violation_count"]),
            "min_invalid_gap": float(violations["min_invalid_gap"]),
            "gamma": solution.gamma,
            "valid_std": solution.valid_std,
            "valid_max_deviation": solution.valid_max_deviation,
            "valid_over_soft_cap": solution.valid_over_soft_cap,
        }
        history.append(row)
        write_csv(run_dir / "cut_history.csv", history)
        print(
            f"{run_key} round={round_idx} violations={row['violation_count']} "
            f"new_cuts={new_cuts} cuts={len(invalid_codes)} min_gap={row['min_invalid_gap']:.6g} "
            f"gamma={solution.gamma:.6g}",
            flush=True,
        )
        if row["violation_count"] == 0:
            break
        if new_cuts == 0:
            break
    assert solution is not None
    write_json(run_dir / f"solution_{run_key}.json", solution_payload(design, solution, args))
    np.savez_compressed(run_dir / "invalid_cuts_final.npz", codes=invalid_codes)
    audit = exact_audit_and_plots(design, solution, args, run_dir, last_energies)
    return solution, audit


def low_invalid_codes(design: Design, solution: QpSolution, args: argparse.Namespace, limit: int) -> tuple[np.ndarray, np.ndarray]:
    energies = energies_full_cube(solution.terms, solution.theta)
    gaps = energies - solution.reference_energy
    invalid_codes = np.flatnonzero(~design.valid_lookup).astype(np.uint32)
    invalid_gaps = gaps[invalid_codes]
    take = min(limit, len(invalid_codes))
    idx = np.argpartition(invalid_gaps, take - 1)[:take]
    return invalid_codes[idx], energies


def binary_entropy(p: np.ndarray) -> np.ndarray:
    p = np.clip(p.astype(np.float64), 1e-12, 1.0 - 1e-12)
    return -(p * np.log2(p) + (1.0 - p) * np.log2(1.0 - p))


def pair_mutual_information(bits: np.ndarray) -> np.ndarray:
    if len(bits) == 0:
        return np.zeros((N, N), dtype=np.float64)
    p = bits.mean(axis=0)
    h = binary_entropy(p)
    mi = np.zeros((N, N), dtype=np.float64)
    for i in range(N):
        for j in range(i + 1, N):
            counts = np.zeros((2, 2), dtype=np.float64)
            np.add.at(counts, (bits[:, i], bits[:, j]), 1.0)
            probs = counts / len(bits)
            h2 = -float(np.sum(probs[probs > 0] * np.log2(probs[probs > 0])))
            value = h[i] + h[j] - h2
            mi[i, j] = value
            mi[j, i] = value
    return mi


def solution_field_terms(solution: QpSolution) -> list[list[tuple[tuple[int, ...], float]]]:
    fields: list[list[tuple[tuple[int, ...], float]]] = [[] for _ in range(N)]
    for term, coeff in zip(solution.terms, solution.theta):
        if abs(float(coeff)) <= 1e-15:
            continue
        for node in term:
            fields[node].append((tuple(idx for idx in term if idx != node), float(coeff)))
    return fields


def quick_convergence_fail_bits(
    design: Design,
    solution: QpSolution,
    args: argparse.Namespace,
    rng: np.random.Generator,
) -> np.ndarray:
    pair_count = min(args.score_convergence_cases, VALID_COUNT)
    pair_codes = rng.choice(np.arange(VALID_COUNT, dtype=np.int64), size=pair_count, replace=False)
    avals = pair_codes & ((1 << WIDTH) - 1)
    bvals = pair_codes >> WIDTH
    target_bits = np.array([valid_state(int(a), int(b)) for a, b in zip(avals, bvals)], dtype=np.int8)
    modes = ("ab", "asum", "bsum")
    sample_bits = []
    target_rows = []
    clamps = []
    for mode in modes:
        for row, (aval, bval) in enumerate(zip(avals, bvals)):
            clamp = np.full(N, -1, dtype=np.int8)
            total = int(aval + bval)
            if mode in {"ab", "asum"}:
                for bit in range(WIDTH):
                    clamp[bit] = (int(aval) >> bit) & 1
            if mode in {"ab", "bsum"}:
                for bit in range(WIDTH):
                    clamp[WIDTH + bit] = (int(bval) >> bit) & 1
            if mode in {"asum", "bsum"}:
                for bit in range(WIDTH + 1):
                    clamp[2 * WIDTH + bit] = (total >> bit) & 1
            clamps.append(clamp)
            target_rows.append(row)
    clamps_a = np.array(clamps, dtype=np.int8)
    target_idx = np.array(target_rows, dtype=np.int64)
    bits = rng.integers(0, 2, size=(len(clamps_a), N), dtype=np.int8)
    fixed = clamps_a >= 0
    bits[fixed] = clamps_a[fixed]
    spins = 2.0 * bits.astype(np.float64) - 1.0
    free_nodes = [np.flatnonzero(row < 0).astype(np.int16) for row in clamps_a]
    fields = solution_field_terms(solution)
    for _cycle in range(args.score_convergence_cycles):
        choices = np.array([rng.choice(free) if len(free) else 0 for free in free_nodes], dtype=np.int16)
        for node in np.unique(choices):
            rows = choices == node
            field = np.zeros(np.sum(rows), dtype=np.float64)
            for others, coeff in fields[int(node)]:
                prod = np.ones(np.sum(rows), dtype=np.float64)
                for other in others:
                    prod *= spins[rows, other]
                field += coeff * prod
            prob = 0.5 * (1.0 + np.tanh(args.score_beta * field))
            new_bits = (rng.random(np.sum(rows)) < prob).astype(np.int8)
            bits[rows, node] = new_bits
            spins[rows, node] = 2.0 * new_bits.astype(np.float64) - 1.0
    target = target_bits[target_idx]
    success = np.all(bits == target, axis=1)
    failed = bits[~success]
    target_failed = target[~success]
    if len(failed) == 0:
        return np.empty((0, N), dtype=np.uint8)
    return (failed != target_failed).astype(np.uint8)


def compute_node_scores(
    design: Design,
    previous: QpSolution,
    full3: QpSolution,
    args: argparse.Namespace,
    iter_dir: Path,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, dict[int, float]]:
    valid_bits = codes_to_bits(design.valid_codes)
    valid_entropy = binary_entropy(valid_bits.mean(axis=0))
    bad_codes, energies = low_invalid_codes(design, previous, args, args.score_bad_states)
    local_codes = local_minimum_codes(energies, design.valid_lookup, args.local_min_tol)
    if len(local_codes):
        bad_codes = np.unique(np.concatenate([bad_codes, local_codes[: args.score_bad_states].astype(np.uint32)]))
    bad_bits = codes_to_bits(bad_codes) if len(bad_codes) else np.empty((0, N), dtype=np.uint8)
    bad_entropy = binary_entropy(bad_bits.mean(axis=0)) if len(bad_bits) else np.zeros(N, dtype=np.float64)
    nearest = nearest_valid_codes(bad_codes[: args.score_bad_states], design.valid_codes) if len(bad_codes) else np.empty(0, dtype=np.uint32)
    if len(nearest):
        mismatch = (codes_to_bits(bad_codes[: len(nearest)]) != codes_to_bits(nearest)).mean(axis=0)
    else:
        mismatch = np.zeros(N, dtype=np.float64)
    fail_bits = quick_convergence_fail_bits(design, previous, args, rng)
    fail_rate = fail_bits.mean(axis=0) if len(fail_bits) else np.zeros(N, dtype=np.float64)
    score = 0.25 * valid_entropy + 0.25 * bad_entropy + 0.30 * mismatch + 0.20 * fail_rate
    max_score = float(np.max(score))
    if max_score > 0:
        score = score / max_score
    rows = []
    for idx, name in enumerate(design.node_names):
        rows.append(
            {
                "node": name,
                "index": idx,
                "score": float(score[idx]),
                "valid_entropy": float(valid_entropy[idx]),
                "bad_state_entropy": float(bad_entropy[idx]),
                "nearest_valid_mismatch_rate": float(mismatch[idx]),
                "convergence_failure_mismatch_rate": float(fail_rate[idx]),
            }
        )
    write_csv(iter_dir / "adaptive_node_scores.csv", rows)
    pair_mi = pair_mutual_information(bad_bits[: args.score_bad_states])
    full3_support_raw: dict[int, float] = {}
    for term, coeff in zip(full3.terms, full3.theta):
        if len(term) == 3:
            full3_support_raw[term_mask(term)] = abs(float(coeff))
    support_max = max(full3_support_raw.values(), default=0.0)
    full3_support: dict[int, float] = {}
    if support_max > 0:
        full3_support = {mask: value / support_max for mask, value in full3_support_raw.items()}
    return score, pair_mi, full3_support


def adaptive_terms(
    score: np.ndarray,
    pair_mi: np.ndarray,
    full3_support: dict[int, float],
    args: argparse.Namespace,
) -> tuple[list[tuple[int, ...]], list[dict]]:
    order = np.argsort(-score)
    order4_nodes = set(int(idx) for idx in order[: max(6, math.ceil(0.20 * N))])
    order3_nodes = set(int(idx) for idx in order[: max(12, math.ceil(0.50 * N))])
    terms = full_terms(2)
    rows = []
    triples = []
    for term in combinations(range(N), 3):
        if not any(idx in order3_nodes for idx in term):
            continue
        mask = term_mask(term)
        value = float(sum(score[list(term)]) + args.full3_support_weight * full3_support.get(mask, 0.0))
        triples.append((value, term))
    triples.sort(reverse=True, key=lambda item: item[0])
    selected_triples = [term for _value, term in triples[: args.adaptive_max_triples]]
    terms.extend(selected_triples)
    for rank, (value, term) in enumerate(triples[: args.adaptive_max_triples]):
        rows.append({"rank": rank, "order": 3, "score": float(value), "indices": list(term), "nodes": [NODE_NAMES[i] for i in term]})

    quads = []
    for term in combinations(range(N), 4):
        if not any(idx in order4_nodes for idx in term):
            continue
        mi_sum = sum(pair_mi[i, j] for i, j in combinations(term, 2))
        value = float(sum(score[list(term)]) + args.pair_mi_weight * mi_sum)
        quads.append((value, term))
    quads.sort(reverse=True, key=lambda item: item[0])
    selected_quads = [term for _value, term in quads[: args.adaptive_max_quads]]
    terms.extend(selected_quads)
    for rank, (value, term) in enumerate(quads[: args.adaptive_max_quads]):
        rows.append({"rank": rank, "order": 4, "score": float(value), "indices": list(term), "nodes": [NODE_NAMES[i] for i in term]})
    return sorted(set(terms), key=lambda item: (len(item), item)), rows


def load_solution(path: Path) -> QpSolution:
    payload = json.loads(path.read_text(encoding="utf-8"))
    terms = []
    theta = []
    for row in payload["solution"]["nonzero_terms"]:
        terms.append(tuple(row["indices"]))
        theta.append(float(row["coefficient"]))
    all_terms = []
    for order_text, count in payload["term_count_by_order"].items():
        _ = count
    # Reconstruct from nonzero plus zero terms by reading adaptive_terms if present is not reliable.
    # Instead use the stored dense coefficient rows when available.
    if "dense_terms" in payload["solution"]:
        terms = [tuple(row["indices"]) for row in payload["solution"]["dense_terms"]]
        theta = [float(row["coefficient"]) for row in payload["solution"]["dense_terms"]]
    solution = payload["solution"]
    return QpSolution(
        run_key=payload["run_key"],
        terms=terms,
        theta=np.array(theta, dtype=np.float64),
        reference_energy=float(solution["reference_energy"]),
        gamma=float(solution["gamma"]),
        objective=float(solution["objective"]),
        status=int(solution["status"]),
        valid_mean=float(solution["valid_mean"]),
        valid_std=float(solution["valid_std"]),
        valid_max_deviation=float(solution["valid_max_deviation"]),
        valid_over_soft_cap=int(solution["valid_over_soft_cap"]),
        coeff_l2=float(solution["coeff_l2"]),
        coeff_max_abs=float(solution["coeff_max_abs"]),
    )


def solution_payload_with_dense(design: Design, solution: QpSolution, args: argparse.Namespace) -> dict:
    payload = solution_payload(design, solution, args)
    payload["solution"]["dense_terms"] = [
        {"indices": list(term), "coefficient": float(coeff)} for term, coeff in zip(solution.terms, solution.theta)
    ]
    return payload


def run_baseline(args: argparse.Namespace, order: int) -> tuple[QpSolution, dict]:
    design = build_design()
    run_key = f"full{order}"
    terms = full_terms(order)
    solution, audit = solve_cutting_plane(design, run_key, terms, args, seed_offset=order)
    write_json(args.out / run_key / f"solution_{run_key}.json", solution_payload_with_dense(design, solution, args))
    return solution, audit


def run_adaptive(args: argparse.Namespace, full3: QpSolution) -> list[dict]:
    design = build_design()
    previous = full3
    summaries = []
    rng = np.random.default_rng(args.seed + 999)
    prev_metric = None
    for iteration in range(1, args.adaptive_iterations + 1):
        run_key = f"adaptive_iter{iteration}"
        iter_dir = args.out / run_key
        iter_dir.mkdir(parents=True, exist_ok=True)
        score, pair_mi, full3_support = compute_node_scores(design, previous, full3, args, iter_dir, rng)
        terms, term_rows = adaptive_terms(score, pair_mi, full3_support, args)
        write_csv(iter_dir / "adaptive_terms.csv", term_rows)
        solution, audit = solve_cutting_plane(design, run_key, terms, args, seed_offset=100 + iteration)
        write_json(iter_dir / f"solution_{run_key}.json", solution_payload_with_dense(design, solution, args))
        summaries.append({"run_key": run_key, **audit})
        metric = float(audit["gamma"]) / max(float(audit["rms_one_bit_energy_jump"]), 1e-12)
        if prev_metric is not None and audit["gap_violation_count"] == 0:
            improvement = (metric - prev_metric) / max(abs(prev_metric), 1e-12)
            if improvement < args.adaptive_stop_improvement:
                print(f"stopping adaptive loop: improvement={improvement:.4g}", flush=True)
                break
        prev_metric = metric
        previous = solution
    return summaries


def run_single_baseline(args: argparse.Namespace) -> None:
    solution, audit = run_baseline(args, args.order)
    write_csv(args.out / f"comparison_{solution.run_key}.csv", [{"run_key": solution.run_key, **audit}])


def run_adaptive_from_full3(args: argparse.Namespace) -> None:
    full3_path = args.full3_solution
    if full3_path is None:
        full3_path = args.out / "full3" / "solution_full3.json"
    full3 = load_solution(full3_path)
    rows = run_adaptive(args, full3)
    write_csv(args.out / "adaptive_comparison_summary.csv", rows)
    if rows:
        plot_comparison(rows, args.out)


def run_all(args: argparse.Namespace) -> None:
    args.out.mkdir(parents=True, exist_ok=True)
    full2, audit2 = run_baseline(args, 2)
    full3, audit3 = run_baseline(args, 3)
    rows = [{"run_key": "full2", **audit2}, {"run_key": "full3", **audit3}]
    rows.extend(run_adaptive(args, full3))
    write_csv(args.out / "comparison_summary.csv", rows)
    plot_comparison(rows, args.out)


def plot_comparison(rows: list[dict], out_dir: Path) -> None:
    labels = [row["run_key"] for row in rows]
    metrics = [
        ("gamma", "Gamma"),
        ("invalid_local_minima", "Invalid Local Minima"),
        ("rms_one_bit_energy_jump", "RMS One-Bit Jump"),
        ("term_count", "Term Count"),
    ]
    fig, axes = plt.subplots(len(metrics), 1, figsize=(10, 10), dpi=160)
    for ax, (key, title) in zip(axes, metrics):
        values = [float(row[key]) for row in rows]
        ax.bar(labels, values, color="#4c72b0")
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(out_dir / "comparison_summary.png")
    plt.close(fig)


def set_bus_clamp(clamp: np.ndarray, bus: str, values: np.ndarray) -> None:
    if bus == "a":
        start, bits = 0, WIDTH
    elif bus == "b":
        start, bits = WIDTH, WIDTH
    elif bus == "sum":
        start, bits = 2 * WIDTH, WIDTH + 1
    else:
        raise ValueError(bus)
    for bit in range(bits):
        clamp[:, start + bit] = ((values >> bit) & 1).astype(np.int8)


def convergence_case_matrix(mode: str) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    if mode in {"a", "b"}:
        values = np.arange(1 << WIDTH, dtype=np.int64)
        clamp = np.full((len(values), N), -1, dtype=np.int8)
        set_bus_clamp(clamp, mode, values)
        return clamp, {mode: values}, np.ones(len(values), dtype=bool)
    if mode == "sum":
        values = np.arange(1 << (WIDTH + 1), dtype=np.int64)
        clamp = np.full((len(values), N), -1, dtype=np.int8)
        set_bus_clamp(clamp, "sum", values)
        return clamp, {"sum": values}, values <= 2 * ((1 << WIDTH) - 1)
    pairs = [(a, b) for a in range(1 << WIDTH) for b in range(1 << WIDTH)]
    avals = np.array([item[0] for item in pairs], dtype=np.int64)
    bvals = np.array([item[1] for item in pairs], dtype=np.int64)
    sums = avals + bvals
    clamp = np.full((len(pairs), N), -1, dtype=np.int8)
    if mode in {"ab", "asum", "absum_valid"}:
        set_bus_clamp(clamp, "a", avals)
    if mode in {"ab", "bsum", "absum_valid"}:
        set_bus_clamp(clamp, "b", bvals)
    if mode in {"asum", "bsum", "absum_valid"}:
        set_bus_clamp(clamp, "sum", sums)
    return clamp, {"a": avals, "b": bvals, "sum": sums}, np.ones(len(pairs), dtype=bool)


def decode_bus(bits: np.ndarray, bus: str) -> np.ndarray:
    if bus == "a":
        start, width = 0, WIDTH
    elif bus == "b":
        start, width = WIDTH, WIDTH
    elif bus == "sum":
        start, width = 2 * WIDTH, WIDTH + 1
    else:
        raise ValueError(bus)
    weights = np.left_shift(np.int64(1), np.arange(width, dtype=np.int64))
    return bits[:, start : start + width].astype(np.int64) @ weights


def simulate_convergence(solution: QpSolution, mode: str, beta: float, cycles: int, trials: int, rng: np.random.Generator) -> dict:
    clamp, targets, feasible_cases = convergence_case_matrix(mode)
    case_count = len(clamp)
    sample_count = case_count * trials
    bits = rng.integers(0, 2, size=(sample_count, N), dtype=np.int8)
    case_ids = np.repeat(np.arange(case_count, dtype=np.int64), trials)
    sample_clamp = clamp[case_ids]
    fixed = sample_clamp >= 0
    bits[fixed] = sample_clamp[fixed]
    spins = 2.0 * bits.astype(np.float64) - 1.0
    free = [np.flatnonzero(row < 0).astype(np.int16) for row in sample_clamp]
    fields = solution_field_terms(solution)
    for _ in range(cycles):
        choices = np.array([rng.choice(row) if len(row) else 0 for row in free], dtype=np.int16)
        for node in np.unique(choices):
            rows = choices == node
            field = np.zeros(np.sum(rows), dtype=np.float64)
            for others, coeff in fields[int(node)]:
                prod = np.ones(np.sum(rows), dtype=np.float64)
                for other in others:
                    prod *= spins[rows, other]
                field += coeff * prod
            prob = 0.5 * (1.0 + np.tanh(beta * field))
            new_bits = (rng.random(np.sum(rows)) < prob).astype(np.int8)
            bits[rows, node] = new_bits
            spins[rows, node] = 2.0 * new_bits.astype(np.float64) - 1.0
    codes = bits_to_codes(bits.astype(np.uint8))
    valid_lookup = build_design().valid_lookup
    success = valid_lookup[codes] & feasible_cases[case_ids]
    for bus, values in targets.items():
        success &= decode_bus(bits, bus) == values[case_ids]
    feasible_trials = int(np.sum(feasible_cases[case_ids]))
    hits = int(np.sum(success))
    return {
        "run_key": solution.run_key,
        "mode": mode,
        "beta": beta,
        "cycles": cycles,
        "trials_per_case": trials,
        "case_count": case_count,
        "feasible_trials": feasible_trials,
        "hits": hits,
        "success_rate_feasible": hits / feasible_trials if feasible_trials else math.nan,
    }


def load_solution_from_run(run_dir: Path) -> QpSolution:
    candidates = sorted(run_dir.glob("solution_*.json"))
    candidates = [path for path in candidates if "round" not in path.name]
    if not candidates:
        raise FileNotFoundError(f"no final solution in {run_dir}")
    payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
    dense = payload["solution"]["dense_terms"]
    terms = [tuple(row["indices"]) for row in dense]
    theta = np.array([float(row["coefficient"]) for row in dense], dtype=np.float64)
    sol = payload["solution"]
    return QpSolution(
        run_key=payload["run_key"],
        terms=terms,
        theta=theta,
        reference_energy=float(sol["reference_energy"]),
        gamma=float(sol["gamma"]),
        objective=float(sol["objective"]),
        status=int(sol["status"]),
        valid_mean=float(sol["valid_mean"]),
        valid_std=float(sol["valid_std"]),
        valid_max_deviation=float(sol["valid_max_deviation"]),
        valid_over_soft_cap=int(sol["valid_over_soft_cap"]),
        coeff_l2=float(sol["coeff_l2"]),
        coeff_max_abs=float(sol["coeff_max_abs"]),
    )


def converge_test_all(args: argparse.Namespace) -> None:
    rows = []
    modes = [item.strip() for item in args.modes.split(",") if item.strip()]
    betas = [float(item.strip()) for item in args.betas.split(",") if item.strip()]
    rng = np.random.default_rng(args.seed + 202)
    for run_dir in sorted(args.out.glob("*")):
        if not run_dir.is_dir() or not (run_dir / "exhaustive_audit.json").exists():
            continue
        solution = load_solution_from_run(run_dir)
        for beta in betas:
            for mode in modes:
                row = simulate_convergence(solution, mode, beta, args.convergence_cycles, args.convergence_trials, rng)
                rows.append(row)
                write_csv(args.out / "convergence_summary.csv", rows)
                print(f"{solution.run_key} beta={beta:g} mode={mode} rate={row['success_rate_feasible']:.4f}", flush=True)


def unit_check() -> None:
    design = build_design()
    assert design.n == 25
    assert len(design.valid_codes) == 4096
    code = bits_to_codes(np.array([valid_state(63, 1)], dtype=np.uint8))[0]
    assert design.valid_lookup[code]
    bits = codes_to_bits(np.array([code]))[0]
    assert list(bits[-6:]) == carry_bits(63, 1)
    assert len(full_terms(2)) == 325
    assert len(full_terms(3)) == 2625
    # Verify Walsh evaluator against direct feature evaluation on a small sample.
    terms = full_terms(3)[:20]
    theta = np.linspace(-0.2, 0.2, len(terms))
    energies = energies_full_cube(terms, theta)
    sample = np.array([0, 1, 7, 1234, 65535], dtype=np.uint32)
    direct = feature_matrix_codes(sample, terms) @ theta
    assert np.allclose(energies[sample], direct)
    print("unit_check passed")


def add_common_args(q: argparse.ArgumentParser) -> None:
    q.add_argument("--out", type=Path, default=DEFAULT_OUT)
    q.add_argument("--coeff-max", type=float, default=2.0)
    q.add_argument("--gamma-weight", type=float, default=1.0)
    q.add_argument("--gamma-max", type=float, default=0.0)
    q.add_argument("--valid-weight", type=float, default=20000.0)
    q.add_argument("--cap-weight", type=float, default=200000.0)
    q.add_argument("--valid-soft-cap", type=float, default=0.5)
    q.add_argument("--tv-weight", type=float, default=100.0)
    q.add_argument("--coeff-weight", type=float, default=0.1)
    q.add_argument("--initial-invalid", type=int, default=12000)
    q.add_argument("--max-cuts-per-round", type=int, default=25000)
    q.add_argument("--max-active-cuts", type=int, default=0)
    q.add_argument("--constraint-chunk", type=int, default=25000)
    q.add_argument("--max-rounds", type=int, default=20)
    q.add_argument("--violation-tol", type=float, default=1e-7)
    q.add_argument("--local-min-tol", type=float, default=1e-10)
    q.add_argument("--local-distance-cap", type=int, default=5000)
    q.add_argument("--time-limit", type=float, default=0.0)
    q.add_argument("--gurobi-method", type=int, default=2)
    q.add_argument("--gurobi-crossover", type=int, default=0)
    q.add_argument("--gurobi-threads", type=int, default=0)
    q.add_argument("--bar-conv-tol", type=float, default=0.0)
    q.add_argument("--gurobi-output", action="store_true")
    q.add_argument("--resume-cuts", action="store_true")
    q.add_argument("--seed", type=int, default=2026070602)
    q.add_argument("--adaptive-iterations", type=int, default=4)
    q.add_argument("--adaptive-max-triples", type=int, default=2000)
    q.add_argument("--adaptive-max-quads", type=int, default=4000)
    q.add_argument("--adaptive-stop-improvement", type=float, default=0.01)
    q.add_argument("--score-bad-states", type=int, default=5000)
    q.add_argument("--score-convergence-cases", type=int, default=512)
    q.add_argument("--score-convergence-cycles", type=int, default=300)
    q.add_argument("--score-beta", type=float, default=5000.0)
    q.add_argument("--jump-sample-states", type=int, default=200000)
    q.add_argument("--plot-invalid-sample", type=int, default=1000000)
    q.add_argument("--full3-support-weight", type=float, default=0.5)
    q.add_argument("--pair-mi-weight", type=float, default=0.25)
    q.add_argument("--betas", type=str, default="1,100,1000,5000")
    q.add_argument("--modes", type=str, default="a,b,sum,ab,asum,bsum,absum_valid")
    q.add_argument("--convergence-cycles", type=int, default=1000)
    q.add_argument("--convergence-trials", type=int, default=5)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="6-bit least+6-shadow adaptive 2/3/4-body QP")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("run-all", "converge-test-all", "run-baseline", "run-adaptive"):
        q = sub.add_parser(name)
        add_common_args(q)
        if name == "run-baseline":
            q.add_argument("--order", type=int, choices=(2, 3), required=True)
        if name == "run-adaptive":
            q.add_argument("--full3-solution", type=Path)
    sub.add_parser("unit-check")
    return p


def main() -> None:
    args = parser().parse_args()
    if args.cmd == "unit-check":
        unit_check()
    elif args.cmd == "run-all":
        run_all(args)
    elif args.cmd == "run-baseline":
        run_single_baseline(args)
    elif args.cmd == "run-adaptive":
        run_adaptive_from_full3(args)
    elif args.cmd == "converge-test-all":
        converge_test_all(args)


if __name__ == "__main__":
    main()
