from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import argparse
import math
import shutil
from itertools import combinations
from pathlib import Path

import numpy as np

from scripts.multibody_hamiltonian_6bit_adaptive_qp.adaptive_qp_6bit import (
    N,
    NODE_NAMES,
    add_common_args,
    build_design,
    compute_node_scores,
    load_solution,
    solution_payload_with_dense,
    solve_cutting_plane,
    write_csv,
    write_json,
)


ROOT = _REPO_ROOT / "results_and_reports/multibody_hamiltonian_6bit_adaptive_qp"


def parse_int_list(text: str) -> list[int]:
    return [int(item.strip()) for item in text.split(",") if item.strip()]


def normalize(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float64)
    lo = float(np.min(values))
    hi = float(np.max(values))
    if hi - lo <= 1e-15:
        return np.zeros_like(values)
    return (values - lo) / (hi - lo)


def node_mi_score(pair_mi: np.ndarray, topk: int) -> np.ndarray:
    scores = np.zeros(N, dtype=np.float64)
    take = max(1, min(topk, N - 1))
    for node in range(N):
        row = np.delete(pair_mi[node].astype(np.float64), node)
        if len(row) == 0:
            continue
        top = np.sort(row)[-take:]
        scores[node] = float(np.mean(top))
    return scores


def full3_node_support(full3) -> np.ndarray:
    support = np.zeros(N, dtype=np.float64)
    for term, coeff in zip(full3.terms, full3.theta):
        if len(term) != 3:
            continue
        for node in term:
            support[int(node)] += abs(float(coeff))
    return support


def classify_critical_nodes(score: np.ndarray, pair_mi: np.ndarray, full3, args: argparse.Namespace) -> tuple[np.ndarray, list[dict], dict]:
    mi_score = node_mi_score(pair_mi, args.critical_mi_topk)
    support = full3_node_support(full3)
    linear_raw = (
        args.critical_score_weight * normalize(score)
        + args.critical_mi_weight * normalize(mi_score)
        + args.critical_support_weight * normalize(support)
    )
    linear = normalize(linear_raw)
    order = np.argsort(-linear)
    ordered = linear[order]
    min_nodes = max(1, min(args.critical_min_nodes, N - 1))
    max_nodes = max(min_nodes, min(args.critical_max_nodes, N - 1))
    best_k = min_nodes
    best_gap = -math.inf
    for k in range(min_nodes, max_nodes + 1):
        gap = float(ordered[k - 1] - ordered[k])
        if gap > best_gap:
            best_gap = gap
            best_k = k
    threshold = float(0.5 * (ordered[best_k - 1] + ordered[best_k]))
    critical = linear >= threshold
    # If no visible score gap exists, still keep the minimum top nodes but report
    # that the split was forced by the min-node setting.
    forced = False
    if best_gap < args.critical_min_gap:
        forced = True
        critical = np.zeros(N, dtype=bool)
        critical[order[:min_nodes]] = True
        threshold = float(ordered[min_nodes - 1])
        best_k = min_nodes

    rows = []
    for rank, idx in enumerate(order):
        rows.append(
            {
                "rank": rank,
                "node": NODE_NAMES[int(idx)],
                "index": int(idx),
                "critical": bool(critical[int(idx)]),
                "linear_score": float(linear[int(idx)]),
                "base_score": float(score[int(idx)]),
                "node_mi_score": float(mi_score[int(idx)]),
                "full3_node_support": float(support[int(idx)]),
            }
        )
    summary = {
        "critical_count": int(np.sum(critical)),
        "critical_nodes": [NODE_NAMES[int(idx)] for idx in np.flatnonzero(critical)],
        "threshold": threshold,
        "largest_gap": float(best_gap),
        "gap_after_rank": int(best_k),
        "forced_min_split": forced,
        "critical_score_weight": args.critical_score_weight,
        "critical_mi_weight": args.critical_mi_weight,
        "critical_support_weight": args.critical_support_weight,
        "critical_mi_topk": args.critical_mi_topk,
    }
    return critical, rows, summary


def select_quads(
    base_terms: list[tuple[int, ...]],
    linear_rows: list[dict],
    critical: np.ndarray,
    pair_mi: np.ndarray,
    max_count: int,
    args: argparse.Namespace,
) -> tuple[list[tuple[int, ...]], list[dict]]:
    linear_score = np.zeros(N, dtype=np.float64)
    for row in linear_rows:
        linear_score[int(row["index"])] = float(row["linear_score"])
    existing = {tuple(term) for term in base_terms}
    ranked = []
    for term in combinations(range(N), 4):
        term = tuple(int(idx) for idx in term)
        if term in existing:
            continue
        critical_count = int(sum(bool(critical[idx]) for idx in term))
        if critical_count < args.quad_require_critical_count:
            continue
        mi_sum = float(sum(pair_mi[i, j] for i, j in combinations(term, 2)))
        value = float(
            args.quad_linear_weight * np.sum(linear_score[list(term)])
            + args.quad_mi_weight * mi_sum
            + args.quad_critical_bonus * critical_count
        )
        ranked.append((value, mi_sum, critical_count, term))
    ranked.sort(reverse=True, key=lambda item: item[0])
    selected = [term for _value, _mi, _cc, term in ranked[:max_count]]
    rows = []
    for rank, (value, mi_sum, critical_count, term) in enumerate(ranked[:max_count]):
        rows.append(
            {
                "rank": rank,
                "score": float(value),
                "mi_sum": float(mi_sum),
                "critical_node_count": int(critical_count),
                "indices": list(term),
                "nodes": [NODE_NAMES[idx] for idx in term],
            }
        )
    return selected, rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Tiny selected 4-body experiment for 6-bit adaptive QP")
    add_common_args(parser)
    parser.set_defaults(out=ROOT / "out_tiny4")
    parser.add_argument("--full3-solution", type=Path, default=ROOT / "out" / "full3" / "solution_full3.json")
    parser.add_argument(
        "--base-solution",
        type=Path,
        default=ROOT / "out_adaptive23" / "adaptive_iter1" / "solution_adaptive_iter1.json",
    )
    parser.add_argument(
        "--seed-cuts-from",
        type=Path,
        default=ROOT / "out_adaptive23" / "adaptive_iter1" / "invalid_cuts_final.npz",
    )
    parser.add_argument("--quad-counts", type=str, default="64")
    parser.add_argument("--critical-min-nodes", type=int, default=1)
    parser.add_argument("--critical-max-nodes", type=int, default=8)
    parser.add_argument("--critical-min-gap", type=float, default=0.02)
    parser.add_argument("--critical-mi-topk", type=int, default=4)
    parser.add_argument("--critical-score-weight", type=float, default=1.0)
    parser.add_argument("--critical-mi-weight", type=float, default=1.5)
    parser.add_argument("--critical-support-weight", type=float, default=0.25)
    parser.add_argument("--quad-require-critical-count", type=int, default=1)
    parser.add_argument("--quad-linear-weight", type=float, default=1.0)
    parser.add_argument("--quad-mi-weight", type=float, default=1.0)
    parser.add_argument("--quad-critical-bonus", type=float, default=0.25)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    design = build_design()
    full3 = load_solution(args.full3_solution)
    base = load_solution(args.base_solution)
    scoring_dir = args.out / "_critical_scoring"
    scoring_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed + 4242)
    score, pair_mi, full3_support = compute_node_scores(design, base, full3, args, scoring_dir, rng)
    _ = full3_support

    critical, critical_rows, critical_summary = classify_critical_nodes(score, pair_mi, full3, args)
    write_csv(scoring_dir / "critical_nodes.csv", critical_rows)
    write_json(scoring_dir / "critical_summary.json", critical_summary)
    print(
        "critical nodes: "
        f"count={critical_summary['critical_count']} "
        f"gap={critical_summary['largest_gap']:.6g} "
        f"nodes={critical_summary['critical_nodes']}",
        flush=True,
    )

    summary_rows = []
    max_count = max(parse_int_list(args.quad_counts), default=0)
    all_quads, all_quad_rows = select_quads(base.terms, critical_rows, critical, pair_mi, max_count, args)
    write_csv(scoring_dir / "selected_quads_ranked.csv", all_quad_rows)
    for quad_count in parse_int_list(args.quad_counts):
        run_key = f"tiny4_q{quad_count}"
        run_dir = args.out / run_key
        run_dir.mkdir(parents=True, exist_ok=True)
        selected_quads = all_quads[:quad_count]
        write_csv(run_dir / "selected_quads.csv", all_quad_rows[:quad_count])
        write_json(run_dir / "critical_summary.json", critical_summary)
        terms = sorted(set(tuple(term) for term in base.terms).union(selected_quads), key=lambda item: (len(item), item))
        if args.seed_cuts_from.exists():
            shutil.copy2(args.seed_cuts_from, run_dir / "invalid_cuts_partial.npz")
            args.resume_cuts = True
        solution, audit = solve_cutting_plane(design, run_key, terms, args, seed_offset=400 + quad_count)
        write_json(run_dir / f"solution_{run_key}.json", solution_payload_with_dense(design, solution, args))
        row = {
            "run_key": run_key,
            "quad_count": quad_count,
            "critical_count": critical_summary["critical_count"],
            "critical_nodes": " ".join(critical_summary["critical_nodes"]),
            "critical_largest_gap": critical_summary["largest_gap"],
            "term_count": len(terms),
            **audit,
        }
        summary_rows.append(row)
        write_csv(args.out / "tiny4_summary.csv", summary_rows)


if __name__ == "__main__":
    main()
