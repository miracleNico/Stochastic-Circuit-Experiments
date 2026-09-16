from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from scripts.multibody_hamiltonian_6bit_adaptive_qp.adaptive_qp_6bit import N, WIDTH, build_design, load_solution_from_run, valid_state
from scripts.multibody_hamiltonian_6bit_adaptive_qp.compare_adaptive23_convergence import (
    field_arrays,
    free_node_matrix,
    noise_decay_schedule,
    paper_hyperparams,
    run_paper_ssa_updates_numba,
)


ROOT = _REPO_ROOT / "results_and_reports/multibody_hamiltonian_6bit_adaptive_qp"
NODE_NAMES = [f"a{i}" for i in range(WIDTH)] + [f"b{i}" for i in range(WIDTH)] + [f"s{i}" for i in range(WIDTH + 1)] + [f"c{i}" for i in range(1, WIDTH + 1)]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def decode(bits: np.ndarray, start: int, width: int) -> np.ndarray:
    weights = np.left_shift(np.int64(1), np.arange(width, dtype=np.int64))
    return bits[:, start : start + width].astype(np.int64) @ weights


def simulate_ab(solution, trials: int, cycles: int, seed: int, noise_mode: str, noise_decay: str, noise_final_ratio: float):
    pairs = [(a, b) for a in range(1 << WIDTH) for b in range(1 << WIDTH)]
    avals = np.array([a for a, _b in pairs], dtype=np.int64)
    bvals = np.array([b for _a, b in pairs], dtype=np.int64)
    sums = avals + bvals
    case_count = len(pairs)
    sample_count = case_count * trials
    clamp = np.full((case_count, N), -1, dtype=np.int8)
    for bit in range(WIDTH):
        clamp[:, bit] = ((avals >> bit) & 1).astype(np.int8)
        clamp[:, WIDTH + bit] = ((bvals >> bit) & 1).astype(np.int8)
    rng = np.random.default_rng(seed)
    bits = rng.integers(0, 2, size=(sample_count, N), dtype=np.int8)
    case_ids = np.repeat(np.arange(case_count, dtype=np.int64), trials)
    sample_clamp = clamp[case_ids]
    fixed = sample_clamp >= 0
    bits[fixed] = sample_clamp[fixed]
    free_nodes, free_counts = free_node_matrix(sample_clamp)
    starts, other1, other2, other3, coeffs, _counts = field_arrays(solution)
    hyper = paper_hyperparams(solution, cycles, noise_mode)
    update_rng = np.random.default_rng(seed + 7919)
    pick_randoms = update_rng.random((sample_count, cycles), dtype=np.float32)
    noise_randoms = update_rng.random((sample_count, cycles), dtype=np.float32)
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
        noise_decay_schedule(cycles, noise_decay, noise_final_ratio),
        hyper["i0_schedule"],
        0.0,
        cycles,
    )
    design = build_design()
    codes = np.zeros(sample_count, dtype=np.uint32)
    for node in range(N):
        codes |= final_bits[:, node].astype(np.uint32) << np.uint32(node)
    decoded_sum = decode(final_bits, 2 * WIDTH, WIDTH + 1)
    target_bits = np.array([valid_state(int(a), int(b)) for a, b in pairs], dtype=np.int8)
    target_samples = target_bits[case_ids]
    success = design.valid_lookup[codes] & (decoded_sum == sums[case_ids])
    bit_mismatch = final_bits != target_samples
    return pairs, avals, bvals, sums, case_ids, final_bits, decoded_sum, success, bit_mismatch


def carry_features(a: int, b: int) -> tuple[int, int, int]:
    carry = 0
    true_carries = 0
    longest_chain = 0
    current_chain = 0
    for bit in range(WIDTH):
        abit = (a >> bit) & 1
        bbit = (b >> bit) & 1
        next_carry = 1 if abit + bbit + carry >= 2 else 0
        if next_carry:
            true_carries += 1
        if carry or (abit & bbit):
            current_chain += 1
        else:
            current_chain = 0
        longest_chain = max(longest_chain, current_chain)
        carry = next_carry
    return true_carries, longest_chain, carry


def plot_heatmap(path: Path, grid: np.ndarray, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6), dpi=160)
    im = ax.imshow(grid, origin="lower", vmin=0.0, vmax=1.0, cmap="magma")
    ax.set_title(title)
    ax.set_xlabel("B")
    ax.set_ylabel("A")
    fig.colorbar(im, ax=ax, label="failure rate")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def analyze_solution(label: str, run_dir: Path, args: argparse.Namespace) -> dict:
    solution = load_solution_from_run(run_dir)
    pairs, avals, bvals, sums, case_ids, final_bits, decoded_sum, success, bit_mismatch = simulate_ab(
        solution,
        args.trials,
        args.cycles,
        args.seed,
        args.paper_noise,
        args.paper_noise_decay,
        args.paper_noise_final_ratio,
    )
    out_dir = args.out_dir / label
    out_dir.mkdir(parents=True, exist_ok=True)
    case_rows = []
    sum_groups = defaultdict(lambda: [0, 0])
    carry_groups = defaultdict(lambda: [0, 0])
    final_carry_groups = defaultdict(lambda: [0, 0])
    grid = np.zeros((1 << WIDTH, 1 << WIDTH), dtype=np.float64)
    for idx, (a, b) in enumerate(pairs):
        rows = np.flatnonzero(case_ids == idx)
        hits = int(np.sum(success[rows]))
        fail = len(rows) - hits
        fail_rate = fail / len(rows)
        grid[a, b] = fail_rate
        target_sum = int(a + b)
        true_carries, longest_chain, final_carry = carry_features(a, b)
        sum_groups[target_sum][0] += fail
        sum_groups[target_sum][1] += len(rows)
        carry_groups[true_carries][0] += fail
        carry_groups[true_carries][1] += len(rows)
        final_carry_groups[final_carry][0] += fail
        final_carry_groups[final_carry][1] += len(rows)
        fail_rows = rows[~success[rows]]
        common_error = ""
        mean_sum_error = 0.0
        if len(fail_rows):
            errors = (decoded_sum[fail_rows] - target_sum).astype(int)
            common_error = Counter(errors.tolist()).most_common(1)[0][0]
            mean_sum_error = float(np.mean(errors))
        case_rows.append(
            {
                "A": a,
                "B": b,
                "SUM": target_sum,
                "true_carries": true_carries,
                "longest_carry_chain": longest_chain,
                "final_carry": final_carry,
                "hits": hits,
                "trials": len(rows),
                "failure_rate": fail_rate,
                "common_sum_error": common_error,
                "mean_sum_error": mean_sum_error,
            }
        )
    write_csv(out_dir / "ab_case_failures.csv", case_rows)
    plot_heatmap(out_dir / "ab_failure_heatmap.png", grid, f"{label}: AB clamp failure rate")

    fail_rows = np.flatnonzero(~success)
    bit_rows = []
    for node, name in enumerate(NODE_NAMES):
        bit_rows.append(
            {
                "node": name,
                "index": node,
                "failed_trial_mismatch_rate": float(np.mean(bit_mismatch[fail_rows, node])) if len(fail_rows) else 0.0,
                "all_trial_mismatch_rate": float(np.mean(bit_mismatch[:, node])),
            }
        )
    write_csv(out_dir / "ab_failed_bit_mismatch.csv", bit_rows)

    sum_rows = [{"SUM": key, "failures": value[0], "trials": value[1], "failure_rate": value[0] / value[1]} for key, value in sorted(sum_groups.items())]
    carry_rows = [{"true_carries": key, "failures": value[0], "trials": value[1], "failure_rate": value[0] / value[1]} for key, value in sorted(carry_groups.items())]
    final_carry_rows = [{"final_carry": key, "failures": value[0], "trials": value[1], "failure_rate": value[0] / value[1]} for key, value in sorted(final_carry_groups.items())]
    write_csv(out_dir / "ab_failures_by_sum.csv", sum_rows)
    write_csv(out_dir / "ab_failures_by_carry_count.csv", carry_rows)
    write_csv(out_dir / "ab_failures_by_final_carry.csv", final_carry_rows)
    return {
        "label": label,
        "success_rate": float(np.mean(success)),
        "failures": int(np.sum(~success)),
        "trials": int(len(success)),
        "worst_case_failure_rate": float(max(row["failure_rate"] for row in case_rows)),
        "perfect_cases": int(sum(1 for row in case_rows if row["failure_rate"] == 0.0)),
        "zero_hit_cases": int(sum(1 for row in case_rows if row["hits"] == 0)),
    }


def parse_solution_arg(text: str) -> tuple[str, Path]:
    label, path = text.split("=", 1)
    return label, Path(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="AB clamp failure diagnostics")
    parser.add_argument("--solution", action="append", type=parse_solution_arg, default=[])
    parser.add_argument("--out-dir", type=Path, default=ROOT / "out_tiny4_q64" / "ab_failure_analysis")
    parser.add_argument("--cycles", type=int, default=1000)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=2026070901)
    parser.add_argument("--paper-noise", choices=("common", "unique"), default="common")
    parser.add_argument("--paper-noise-decay", choices=("none", "exp"), default="exp")
    parser.add_argument("--paper-noise-final-ratio", type=float, default=0.1)
    args = parser.parse_args()
    solutions = args.solution or [
        ("full3", ROOT / "out" / "full3"),
        ("adaptive23", ROOT / "out_adaptive23" / "adaptive_iter1"),
        ("tiny4_q64", ROOT / "out_tiny4_q64" / "tiny4_q64"),
    ]
    rows = [analyze_solution(label, path, args) for label, path in solutions]
    write_csv(args.out_dir / "ab_failure_summary.csv", rows)
    for row in rows:
        print(f"{row['label']} success={row['success_rate']:.6f} failures={row['failures']}/{row['trials']}", flush=True)


if __name__ == "__main__":
    main()
