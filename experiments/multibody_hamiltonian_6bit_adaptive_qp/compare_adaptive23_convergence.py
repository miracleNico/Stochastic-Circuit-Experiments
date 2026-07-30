from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import numba as nb
import numpy as np

from adaptive_qp_6bit import (
    N,
    WIDTH,
    bits_to_codes,
    build_design,
    convergence_case_matrix,
    decode_bus,
    load_solution_from_run,
)


DEFAULT_ROOT = Path(__file__).resolve().parent


def parse_csv_floats(text: str) -> list[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def parse_csv_strings(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def paper_hyperparams(solution, cycles: int, noise_mode: str) -> dict:
    mu = np.zeros(N, dtype=np.float64)
    variance = np.zeros(N, dtype=np.float64)
    for term, coeff in zip(solution.terms, solution.theta):
        coeff = float(coeff)
        if len(term) == 1:
            mu[int(term[0])] += coeff
        else:
            for node in term:
                variance[int(node)] += coeff * coeff
    sigma = np.sqrt(variance)
    mean_sigma = float(np.mean(sigma))
    max_sigma = float(np.max(sigma))
    min_abs_mu = float(np.min(np.abs(mu)))
    i0min = 0.01 * max_sigma + min_abs_mu
    i0max = 2.0 * max_sigma + min_abs_mu
    if i0min <= 0.0:
        i0min = max(i0max * 1e-6, 1e-15)
    if i0max <= i0min:
        i0max = i0min * 1.001
    if noise_mode == "common":
        nrnd_by_node = np.full(N, 0.6745 * mean_sigma, dtype=np.float64)
    elif noise_mode == "unique":
        nrnd_by_node = 0.6745 * sigma
    else:
        raise ValueError(f"unknown paper noise mode: {noise_mode}")
    if cycles <= 1:
        i0_schedule = np.array([i0max], dtype=np.float64)
        beta_update = math.nan
    else:
        i0_schedule = np.geomspace(i0min, i0max, cycles).astype(np.float64)
        beta_update = float((i0min / i0max) ** (1.0 / (cycles - 1)))
    return {
        "mu": mu,
        "sigma": sigma,
        "mean_sigma": mean_sigma,
        "max_sigma": max_sigma,
        "min_abs_mu": min_abs_mu,
        "nrnd_common": 0.6745 * mean_sigma,
        "nrnd_min": float(np.min(nrnd_by_node)),
        "nrnd_max": float(np.max(nrnd_by_node)),
        "i0min": i0min,
        "i0max": i0max,
        "beta_update": beta_update,
        "nrnd_by_node": nrnd_by_node,
        "i0_schedule": i0_schedule,
    }


def noise_decay_schedule(cycles: int, mode: str, final_ratio: float) -> np.ndarray:
    if final_ratio <= 0.0:
        raise ValueError("--paper-noise-final-ratio must be positive")
    if mode == "none" or cycles <= 1:
        return np.ones(cycles, dtype=np.float64)
    if mode == "exp":
        return np.exp(np.linspace(0.0, math.log(final_ratio), cycles, dtype=np.float64))
    raise ValueError(f"unknown noise decay mode: {mode}")


def field_arrays(solution) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    per_node: list[list[tuple[int, int, int, float]]] = [[] for _ in range(N)]
    for term, coeff in zip(solution.terms, solution.theta):
        coeff = float(coeff)
        if abs(coeff) <= 1e-15:
            continue
        if len(term) > 4:
            raise ValueError("fast convergence runner currently supports terms up to order 4")
        for node in term:
            others = [idx for idx in term if idx != node]
            o1 = others[0] if len(others) >= 1 else -1
            o2 = others[1] if len(others) >= 2 else -1
            o3 = others[2] if len(others) >= 3 else -1
            per_node[node].append((o1, o2, o3, coeff))
    counts = np.array([len(items) for items in per_node], dtype=np.int32)
    starts = np.zeros(N + 1, dtype=np.int32)
    starts[1:] = np.cumsum(counts)
    total = int(starts[-1])
    other1 = np.empty(total, dtype=np.int16)
    other2 = np.empty(total, dtype=np.int16)
    other3 = np.empty(total, dtype=np.int16)
    coeffs = np.empty(total, dtype=np.float64)
    pos = 0
    for items in per_node:
        for o1, o2, o3, coeff in items:
            other1[pos] = o1
            other2[pos] = o2
            other3[pos] = o3
            coeffs[pos] = coeff
            pos += 1
    return starts, other1, other2, other3, coeffs, counts


def free_node_matrix(sample_clamp: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    free_counts = np.sum(sample_clamp < 0, axis=1).astype(np.int16)
    max_free = int(np.max(free_counts)) if len(free_counts) else 0
    free_nodes = np.zeros((len(sample_clamp), max_free), dtype=np.int16)
    for row_idx, row in enumerate(sample_clamp):
        nodes = np.flatnonzero(row < 0).astype(np.int16)
        free_nodes[row_idx, : len(nodes)] = nodes
    return free_nodes, free_counts


@nb.njit(cache=True, parallel=True, fastmath=True)
def run_updates_numba(
    bits: np.ndarray,
    starts: np.ndarray,
    other1: np.ndarray,
    other2: np.ndarray,
    other3: np.ndarray,
    coeffs: np.ndarray,
    free_nodes: np.ndarray,
    free_counts: np.ndarray,
    pick_randoms: np.ndarray,
    update_randoms: np.ndarray,
    beta: float,
    cycles: int,
) -> np.ndarray:
    sample_count = bits.shape[0]
    spins = bits.astype(np.float64) * 2.0 - 1.0
    for row in nb.prange(sample_count):
        for cycle in range(cycles):
            count = int(free_counts[row])
            if count <= 0:
                continue
            pick = int(pick_randoms[row, cycle] * count)
            if pick >= count:
                pick = count - 1
            node = int(free_nodes[row, pick])
            field = 0.0
            for pos in range(int(starts[node]), int(starts[node + 1])):
                prod = 1.0
                o1 = int(other1[pos])
                o2 = int(other2[pos])
                if o1 >= 0:
                    prod *= spins[row, o1]
                if o2 >= 0:
                    prod *= spins[row, o2]
                o3 = int(other3[pos])
                if o3 >= 0:
                    prod *= spins[row, o3]
                field += coeffs[pos] * prod
            prob = 0.5 * (1.0 + math.tanh(beta * field))
            new_bit = 1 if update_randoms[row, cycle] < prob else 0
            bits[row, node] = new_bit
            spins[row, node] = 2.0 * new_bit - 1.0
    return bits


@nb.njit(cache=True, parallel=True, fastmath=True)
def run_paper_ssa_updates_numba(
    bits: np.ndarray,
    starts: np.ndarray,
    other1: np.ndarray,
    other2: np.ndarray,
    other3: np.ndarray,
    coeffs: np.ndarray,
    free_nodes: np.ndarray,
    free_counts: np.ndarray,
    pick_randoms: np.ndarray,
    noise_randoms: np.ndarray,
    nrnd_by_node: np.ndarray,
    noise_scale: np.ndarray,
    i0_schedule: np.ndarray,
    alpha: float,
    cycles: int,
) -> np.ndarray:
    sample_count = bits.shape[0]
    spins = bits.astype(np.float64) * 2.0 - 1.0
    integrator = np.empty_like(spins)
    initial_i0 = i0_schedule[0]
    for row in nb.prange(sample_count):
        for node in range(bits.shape[1]):
            integrator[row, node] = spins[row, node] * initial_i0
        for cycle in range(cycles):
            count = int(free_counts[row])
            if count <= 0:
                continue
            pick = int(pick_randoms[row, cycle] * count)
            if pick >= count:
                pick = count - 1
            node = int(free_nodes[row, pick])
            field = 0.0
            for pos in range(int(starts[node]), int(starts[node + 1])):
                prod = 1.0
                o1 = int(other1[pos])
                o2 = int(other2[pos])
                o3 = int(other3[pos])
                if o1 >= 0:
                    prod *= spins[row, o1]
                if o2 >= 0:
                    prod *= spins[row, o2]
                if o3 >= 0:
                    prod *= spins[row, o3]
                field += coeffs[pos] * prod
            noise_sign = 1.0 if noise_randoms[row, cycle] >= 0.5 else -1.0
            total = integrator[row, node] + field + nrnd_by_node[node] * noise_scale[cycle] * noise_sign
            limit = i0_schedule[cycle]
            if total >= limit:
                total = limit - alpha
            elif total < -limit:
                total = -limit
            integrator[row, node] = total
            new_bit = 1 if total >= 0.0 else 0
            bits[row, node] = new_bit
            spins[row, node] = 2.0 * new_bit - 1.0
    return bits


def simulate_convergence_fast(
    solution,
    mode: str,
    beta: float,
    cycles: int,
    trials: int,
    initial_seed: int,
    update_seed: int,
) -> dict:
    clamp, targets, feasible_cases = convergence_case_matrix(mode)
    case_count = len(clamp)
    sample_count = case_count * trials
    rng = np.random.default_rng(initial_seed)
    bits = rng.integers(0, 2, size=(sample_count, N), dtype=np.int8)
    case_ids = np.repeat(np.arange(case_count, dtype=np.int64), trials)
    sample_clamp = clamp[case_ids]
    fixed = sample_clamp >= 0
    bits[fixed] = sample_clamp[fixed]
    free_nodes, free_counts = free_node_matrix(sample_clamp)
    starts, other1, other2, other3, coeffs, _counts = field_arrays(solution)
    update_rng = np.random.default_rng(update_seed)
    pick_randoms = update_rng.random((sample_count, cycles), dtype=np.float32)
    update_randoms = update_rng.random((sample_count, cycles), dtype=np.float32)
    final_bits = run_updates_numba(
        bits.copy(),
        starts,
        other1,
        other2,
        other3,
        coeffs,
        free_nodes,
        free_counts,
        pick_randoms,
        update_randoms,
        float(beta),
        int(cycles),
    )
    codes = bits_to_codes(final_bits.astype(np.uint8))
    valid_lookup = build_design().valid_lookup
    success = valid_lookup[codes] & feasible_cases[case_ids]
    for bus, values in targets.items():
        success &= decode_bus(final_bits, bus) == values[case_ids]
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


def simulate_convergence_paper(
    solution,
    mode: str,
    cycles: int,
    trials: int,
    initial_seed: int,
    update_seed: int,
    noise_mode: str,
    noise_decay: str,
    noise_final_ratio: float,
    alpha: float,
) -> dict:
    clamp, targets, feasible_cases = convergence_case_matrix(mode)
    case_count = len(clamp)
    sample_count = case_count * trials
    rng = np.random.default_rng(initial_seed)
    bits = rng.integers(0, 2, size=(sample_count, N), dtype=np.int8)
    case_ids = np.repeat(np.arange(case_count, dtype=np.int64), trials)
    sample_clamp = clamp[case_ids]
    fixed = sample_clamp >= 0
    bits[fixed] = sample_clamp[fixed]
    free_nodes, free_counts = free_node_matrix(sample_clamp)
    starts, other1, other2, other3, coeffs, _counts = field_arrays(solution)
    hyper = paper_hyperparams(solution, cycles, noise_mode)
    update_rng = np.random.default_rng(update_seed)
    pick_randoms = update_rng.random((sample_count, cycles), dtype=np.float32)
    noise_randoms = update_rng.random((sample_count, cycles), dtype=np.float32)
    noise_scale = noise_decay_schedule(cycles, noise_decay, noise_final_ratio)
    final_bits = run_paper_ssa_updates_numba(
        bits.copy(),
        starts,
        other1,
        other2,
        other3,
        coeffs,
        free_nodes,
        free_counts,
        pick_randoms,
        noise_randoms,
        hyper["nrnd_by_node"],
        noise_scale,
        hyper["i0_schedule"],
        float(alpha),
        int(cycles),
    )
    codes = bits_to_codes(final_bits.astype(np.uint8))
    valid_lookup = build_design().valid_lookup
    success = valid_lookup[codes] & feasible_cases[case_ids]
    for bus, values in targets.items():
        success &= decode_bus(final_bits, bus) == values[case_ids]
    feasible_trials = int(np.sum(feasible_cases[case_ids]))
    hits = int(np.sum(success))
    return {
        "run_key": solution.run_key,
        "mode": mode,
        "schedule": f"paper-ssa-{noise_mode}",
        "noise_decay": noise_decay,
        "noise_final_ratio": noise_final_ratio,
        "cycles": cycles,
        "trials_per_case": trials,
        "case_count": case_count,
        "feasible_trials": feasible_trials,
        "hits": hits,
        "success_rate_feasible": hits / feasible_trials if feasible_trials else math.nan,
        "i0min": hyper["i0min"],
        "i0max": hyper["i0max"],
        "beta_update": hyper["beta_update"],
        "nrnd_common": hyper["nrnd_common"],
        "nrnd_min": hyper["nrnd_min"],
        "nrnd_max": hyper["nrnd_max"],
        "mean_sigma": hyper["mean_sigma"],
        "max_sigma": hyper["max_sigma"],
        "min_abs_mu": hyper["min_abs_mu"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Paired convergence comparison for full3 vs adaptive 2/3")
    parser.add_argument("--full3-dir", type=Path, default=DEFAULT_ROOT / "out" / "full3")
    parser.add_argument("--adaptive23-dir", type=Path, default=DEFAULT_ROOT / "out_adaptive23" / "adaptive_iter1")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_ROOT / "out_adaptive23" / "convergence_compare")
    parser.add_argument("--schedule", choices=("paper-ssa", "fixed-tanh"), default="paper-ssa")
    parser.add_argument("--paper-noise", choices=("common", "unique"), default="common")
    parser.add_argument("--paper-noise-decay", choices=("none", "exp"), default="none")
    parser.add_argument("--paper-noise-final-ratio", type=float, default=1.0)
    parser.add_argument("--paper-alpha", type=float, default=0.0)
    parser.add_argument("--betas", type=str, default="1,100,1000,5000")
    parser.add_argument("--modes", type=str, default="a,b,sum,ab,asum,bsum,absum_valid")
    parser.add_argument("--cycles", type=int, default=1000)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026070701)
    args = parser.parse_args()

    runs = [
        ("full3", load_solution_from_run(args.full3_dir)),
        ("adaptive23", load_solution_from_run(args.adaptive23_dir)),
    ]
    betas = parse_csv_floats(args.betas)
    modes = parse_csv_strings(args.modes)

    rows: list[dict] = []
    schedule_values = betas if args.schedule == "fixed-tanh" else [math.nan]
    for schedule_idx, beta in enumerate(schedule_values):
        for mode_idx, mode in enumerate(modes):
            paired_seed = args.seed + schedule_idx * 1000 + mode_idx
            for label, solution in runs:
                if args.schedule == "fixed-tanh":
                    row = simulate_convergence_fast(
                        solution,
                        mode,
                        beta,
                        args.cycles,
                        args.trials,
                        initial_seed=paired_seed,
                        update_seed=paired_seed + 7919,
                    )
                    row["schedule"] = "fixed-tanh"
                else:
                    row = simulate_convergence_paper(
                        solution,
                        mode,
                        args.cycles,
                        args.trials,
                        initial_seed=paired_seed,
                        update_seed=paired_seed + 7919,
                        noise_mode=args.paper_noise,
                        noise_decay=args.paper_noise_decay,
                        noise_final_ratio=args.paper_noise_final_ratio,
                        alpha=args.paper_alpha,
                    )
                    row["beta"] = ""
                row["label"] = label
                rows.append(row)
                write_csv(args.out_dir / "convergence_paired.csv", rows)
                if args.schedule == "fixed-tanh":
                    prefix = f"{label} fixed-tanh beta={beta:g}"
                else:
                    prefix = (
                        f"{label} paper-ssa noise={args.paper_noise} "
                        f"decay={args.paper_noise_decay}:{args.paper_noise_final_ratio:g} "
                        f"I0=[{row['i0min']:.6g},{row['i0max']:.6g}] nrnd=[{row['nrnd_min']:.6g},{row['nrnd_max']:.6g}]"
                    )
                print(f"{prefix} mode={mode} rate={row['success_rate_feasible']:.6f} hits={row['hits']}/{row['feasible_trials']}", flush=True)

    by_key: dict[tuple[str, str, str], dict[str, dict]] = {}
    for row in rows:
        by_key.setdefault((str(row["schedule"]), str(row.get("beta", "")), str(row["mode"])), {})[str(row["label"])] = row

    comparison_rows = []
    for (schedule, beta, mode), pair in sorted(by_key.items()):
        full = pair.get("full3")
        adaptive = pair.get("adaptive23")
        if full is None or adaptive is None:
            continue
        full_rate = float(full["success_rate_feasible"])
        adaptive_rate = float(adaptive["success_rate_feasible"])
        delta = adaptive_rate - full_rate
        full_trials = int(full["feasible_trials"])
        adaptive_trials = int(adaptive["feasible_trials"])
        # Conservative two-proportion standard error, useful for small differences.
        se = math.sqrt(
            full_rate * (1.0 - full_rate) / max(full_trials, 1)
            + adaptive_rate * (1.0 - adaptive_rate) / max(adaptive_trials, 1)
        )
        comparison_rows.append(
            {
                "schedule": schedule,
                "beta": beta,
                "mode": mode,
                "full3_rate": full_rate,
                "adaptive23_rate": adaptive_rate,
                "delta_adaptive_minus_full3": delta,
                "two_se": 2.0 * se,
                "full3_hits": int(full["hits"]),
                "adaptive23_hits": int(adaptive["hits"]),
                "feasible_trials": full_trials,
                "degraded_beyond_2se": delta < -2.0 * se,
                "full3_i0min": full.get("i0min", ""),
                "full3_i0max": full.get("i0max", ""),
                "full3_nrnd_min": full.get("nrnd_min", ""),
                "full3_nrnd_max": full.get("nrnd_max", ""),
                "noise_decay": full.get("noise_decay", ""),
                "noise_final_ratio": full.get("noise_final_ratio", ""),
                "adaptive23_i0min": adaptive.get("i0min", ""),
                "adaptive23_i0max": adaptive.get("i0max", ""),
                "adaptive23_nrnd_min": adaptive.get("nrnd_min", ""),
                "adaptive23_nrnd_max": adaptive.get("nrnd_max", ""),
            }
        )

    write_csv(args.out_dir / "convergence_comparison.csv", comparison_rows)
    degraded = [row for row in comparison_rows if row["degraded_beyond_2se"]]
    print(f"wrote {args.out_dir / 'convergence_paired.csv'}", flush=True)
    print(f"wrote {args.out_dir / 'convergence_comparison.csv'}", flush=True)
    print(f"degraded_beyond_2se={len(degraded)}", flush=True)


if __name__ == "__main__":
    main()
