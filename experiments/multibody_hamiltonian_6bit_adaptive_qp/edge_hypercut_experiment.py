from __future__ import annotations

import argparse
import csv
import shutil
from itertools import combinations
from pathlib import Path

import numpy as np

from adaptive_qp_6bit import (
    N,
    NODE_NAMES,
    add_common_args,
    build_design,
    codes_to_bits,
    compute_node_scores,
    load_solution,
    pair_mutual_information,
    solution_payload_with_dense,
    solve_cutting_plane,
    term_count_by_order,
    write_csv,
    write_json,
)
from tiny4_experiment import classify_critical_nodes, normalize, parse_int_list


ROOT = Path(__file__).resolve().parent


def node_index(name: str) -> int:
    try:
        return NODE_NAMES.index(name)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"unknown node name: {name}") from exc


def parse_pair_list(text: str) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    if not text.strip():
        return pairs
    for raw in text.split(","):
        item = raw.strip()
        if not item:
            continue
        if ":" in item:
            left, right = item.split(":", 1)
        elif "-" in item:
            left, right = item.split("-", 1)
        else:
            raise argparse.ArgumentTypeError(f"pair must use ':' or '-': {item}")
        i = node_index(left.strip())
        j = node_index(right.strip())
        if i == j:
            raise argparse.ArgumentTypeError(f"self-pair is invalid: {item}")
        pairs.add(tuple(sorted((i, j))))
    return pairs


def node_stage(idx: int) -> int:
    name = NODE_NAMES[idx]
    if name[0] in ("a", "b", "s"):
        return int(name[1:])
    if name[0] == "c":
        return int(name[1:])
    raise ValueError(name)


def same_stage_parent_output(i: int, j: int) -> bool:
    left, right = NODE_NAMES[i], NODE_NAMES[j]
    names = {left, right}
    if names == {"c6", "s6"}:
        return True
    for bit in range(6):
        parents = {f"a{bit}", f"b{bit}"}
        if bit > 0:
            parents.add(f"c{bit}")
        outputs = {f"s{bit}", f"c{bit + 1}"}
        if len(names & parents) == 1 and len(names & outputs) == 1:
            return True
    return False


def semantic_sibling_pair(i: int, j: int) -> bool:
    names = {NODE_NAMES[i], NODE_NAMES[j]}
    for bit in range(6):
        if names == {f"s{bit}", f"c{bit + 1}"}:
            return True
    return names == {"s5", "s6"}


def load_failure_rates(path: Path) -> np.ndarray:
    rates = np.zeros(N, dtype=np.float64)
    if not path.exists():
        return rates
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            idx = int(row["index"])
            rates[idx] = float(row["failed_trial_mismatch_rate"])
    return rates


def cut_pairs_in_term(term: tuple[int, ...], cut_pairs: set[tuple[int, int]]) -> list[tuple[int, int]]:
    return [tuple(sorted(pair)) for pair in combinations(term, 2) if tuple(sorted(pair)) in cut_pairs]


def any_cut_pair(term: tuple[int, ...], cut_pairs: set[tuple[int, int]], min_order: int = 2) -> bool:
    return len(term) >= min_order and bool(cut_pairs_in_term(term, cut_pairs))


def build_edge_cut(
    valid_mi: np.ndarray,
    bad_mi: np.ndarray,
    failure_rates: np.ndarray,
    explicit_pairs: set[tuple[int, int]],
    args: argparse.Namespace,
) -> tuple[set[tuple[int, int]], list[dict]]:
    valid_norm = normalize(valid_mi.reshape(-1)).reshape(valid_mi.shape)
    bad_norm = normalize(bad_mi.reshape(-1)).reshape(bad_mi.shape)
    cut_pairs = set(explicit_pairs)
    scored: list[tuple[float, tuple[int, int]]] = []
    rows: list[dict] = []
    for i, j in combinations(range(N), 2):
        pair = (i, j)
        fail_geom = float(np.sqrt(max(failure_rates[i], 0.0) * max(failure_rates[j], 0.0)))
        sibling = semantic_sibling_pair(i, j)
        protected = same_stage_parent_output(i, j)
        stage_distance = abs(node_stage(i) - node_stage(j))
        hazard = float(
            args.auto_cut_bad_mi_weight * bad_norm[i, j]
            + args.auto_cut_failure_weight * fail_geom
            + (args.auto_cut_sibling_bonus if sibling else 0.0)
            + args.auto_cut_stage_weight * stage_distance / 6.0
            - args.auto_cut_valid_mi_credit * valid_norm[i, j]
        )
        eligible = (
            not protected
            and fail_geom >= args.auto_cut_min_failure
            and hazard >= args.auto_cut_min_score
        )
        if eligible and pair not in cut_pairs:
            scored.append((hazard, pair))
        rows.append(
            {
                "node_i": NODE_NAMES[i],
                "node_j": NODE_NAMES[j],
                "i": i,
                "j": j,
                "valid_mi": float(valid_mi[i, j]),
                "bad_mi": float(bad_mi[i, j]),
                "failure_geom": fail_geom,
                "stage_distance": stage_distance,
                "semantic_sibling": sibling,
                "protected_parent_output": protected,
                "explicit_cut": pair in explicit_pairs,
                "auto_cut_candidate": eligible,
                "hazard_score": hazard,
                "cut": False,
            }
        )
    scored.sort(reverse=True, key=lambda item: item[0])
    for _score, pair in scored[: max(args.auto_cut_edges, 0)]:
        cut_pairs.add(pair)
    for row in rows:
        row["cut"] = tuple(sorted((int(row["i"]), int(row["j"])))) in cut_pairs
    return cut_pairs, sorted(rows, key=lambda row: (-int(row["cut"]), -float(row["hazard_score"])))


def filter_terms_by_cut(
    terms: list[tuple[int, ...]],
    cut_pairs: set[tuple[int, int]],
    min_order: int,
) -> tuple[list[tuple[int, ...]], list[dict]]:
    kept: list[tuple[int, ...]] = []
    removed_rows: list[dict] = []
    for term in terms:
        term = tuple(term)
        cut_inside = cut_pairs_in_term(term, cut_pairs) if len(term) >= min_order else []
        if cut_inside:
            removed_rows.append(
                {
                    "order": len(term),
                    "indices": list(term),
                    "nodes": [NODE_NAMES[idx] for idx in term],
                    "cut_pairs": ["-".join(NODE_NAMES[idx] for idx in pair) for pair in cut_inside],
                }
            )
        else:
            kept.append(term)
    return kept, removed_rows


def select_quads_with_hypercut(
    base_terms: list[tuple[int, ...]],
    linear_rows: list[dict],
    critical: np.ndarray,
    bad_mi: np.ndarray,
    valid_mi: np.ndarray,
    cut_pairs: set[tuple[int, int]],
    max_count: int,
    args: argparse.Namespace,
) -> tuple[list[tuple[int, ...]], list[dict], dict]:
    linear_score = np.zeros(N, dtype=np.float64)
    for row in linear_rows:
        linear_score[int(row["index"])] = float(row["linear_score"])
    existing = {tuple(term) for term in base_terms}
    ranked = []
    rejected_by_cut = 0
    rejected_by_critical = 0
    rejected_by_critical_max = 0
    for term in combinations(range(N), 4):
        term = tuple(int(idx) for idx in term)
        if term in existing:
            continue
        if any_cut_pair(term, cut_pairs, args.candidate_cut_min_order):
            rejected_by_cut += 1
            continue
        critical_count = int(sum(bool(critical[idx]) for idx in term))
        if critical_count < args.quad_require_critical_count:
            rejected_by_critical += 1
            continue
        if args.quad_max_critical_count >= 0 and critical_count > args.quad_max_critical_count:
            rejected_by_critical_max += 1
            continue
        bad_mi_sum = float(sum(bad_mi[i, j] for i, j in combinations(term, 2)))
        valid_mi_sum = float(sum(valid_mi[i, j] for i, j in combinations(term, 2)))
        value = float(
            args.quad_linear_weight * np.sum(linear_score[list(term)])
            - args.quad_bad_mi_penalty * bad_mi_sum
            + args.quad_valid_mi_weight * valid_mi_sum
            + args.quad_critical_bonus * critical_count
        )
        ranked.append((value, bad_mi_sum, valid_mi_sum, critical_count, term))
    ranked.sort(reverse=True, key=lambda item: item[0])
    usage = np.zeros(N, dtype=np.int32)
    selected_ranked = []
    rejected_by_usage = 0
    for item in ranked:
        _value, _bad_mi, _valid_mi, _cc, term = item
        if args.quad_node_usage_cap > 0 and any(usage[idx] >= args.quad_node_usage_cap for idx in term):
            rejected_by_usage += 1
            continue
        selected_ranked.append(item)
        for idx in term:
            usage[idx] += 1
        if len(selected_ranked) >= max_count:
            break
    selected = [term for _value, _bad_mi, _valid_mi, _cc, term in selected_ranked]
    rows = []
    for rank, (value, bad_mi_sum, valid_mi_sum, critical_count, term) in enumerate(selected_ranked):
        rows.append(
            {
                "rank": rank,
                "score": float(value),
                "bad_mi_sum": float(bad_mi_sum),
                "valid_mi_sum": float(valid_mi_sum),
                "critical_node_count": int(critical_count),
                "indices": list(term),
                "nodes": [NODE_NAMES[idx] for idx in term],
            }
        )
    summary = {
        "ranked_candidates": len(ranked),
        "selected": len(selected),
        "rejected_by_hyperedge_cut": rejected_by_cut,
        "rejected_by_min_critical_count": rejected_by_critical,
        "rejected_by_max_critical_count": rejected_by_critical_max,
        "rejected_by_node_usage_cap": rejected_by_usage,
        "node_usage_cap": args.quad_node_usage_cap,
    }
    return selected, rows, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge/hyperedge-cut 4-body experiment for the 6-bit adaptive QP adder")
    add_common_args(parser)
    parser.set_defaults(out=ROOT / "out_edge_hypercut")
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
    parser.add_argument(
        "--failure-bit-csv",
        type=Path,
        default=ROOT / "out_tiny4_q64" / "ab_failure_analysis_t20" / "tiny4_q64" / "ab_failed_bit_mismatch.csv",
    )
    parser.add_argument("--quad-counts", type=str, default="16")
    parser.add_argument("--cut-pairs", type=str, default="s5:s6,s5:c6")
    parser.add_argument("--candidate-cut-pairs", type=str, default="")
    parser.add_argument("--base-cut-min-order", type=int, default=2)
    parser.add_argument("--candidate-cut-min-order", type=int, default=4)
    parser.add_argument("--auto-cut-edges", type=int, default=0)
    parser.add_argument("--auto-cut-min-failure", type=float, default=0.35)
    parser.add_argument("--auto-cut-min-score", type=float, default=0.0)
    parser.add_argument("--auto-cut-bad-mi-weight", type=float, default=0.5)
    parser.add_argument("--auto-cut-failure-weight", type=float, default=1.0)
    parser.add_argument("--auto-cut-sibling-bonus", type=float, default=1.0)
    parser.add_argument("--auto-cut-stage-weight", type=float, default=0.0)
    parser.add_argument("--auto-cut-valid-mi-credit", type=float, default=0.0)
    parser.add_argument("--critical-min-nodes", type=int, default=1)
    parser.add_argument("--critical-max-nodes", type=int, default=8)
    parser.add_argument("--critical-min-gap", type=float, default=0.02)
    parser.add_argument("--critical-mi-topk", type=int, default=4)
    parser.add_argument("--critical-score-weight", type=float, default=1.0)
    parser.add_argument("--critical-mi-weight", type=float, default=1.5)
    parser.add_argument("--critical-support-weight", type=float, default=0.25)
    parser.add_argument("--quad-require-critical-count", type=int, default=1)
    parser.add_argument("--quad-max-critical-count", type=int, default=-1)
    parser.add_argument("--quad-node-usage-cap", type=int, default=0)
    parser.add_argument("--quad-linear-weight", type=float, default=1.0)
    parser.add_argument("--quad-bad-mi-penalty", type=float, default=0.0)
    parser.add_argument("--quad-valid-mi-weight", type=float, default=0.0)
    parser.add_argument("--quad-critical-bonus", type=float, default=0.25)
    parser.add_argument("--select-only", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    design = build_design()
    full3 = load_solution(args.full3_solution)
    base = load_solution(args.base_solution)
    scoring_dir = args.out / "_edge_hypercut_scoring"
    scoring_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed + 5252)
    score, bad_mi, full3_support = compute_node_scores(design, base, full3, args, scoring_dir, rng)
    _ = full3_support
    valid_mi = pair_mutual_information(codes_to_bits(design.valid_codes))
    failure_rates = load_failure_rates(args.failure_bit_csv)
    explicit_pairs = parse_pair_list(args.cut_pairs)
    candidate_explicit_pairs = set(explicit_pairs)
    candidate_explicit_pairs.update(parse_pair_list(args.candidate_cut_pairs))
    cut_pairs, edge_rows = build_edge_cut(valid_mi, bad_mi, failure_rates, explicit_pairs, args)
    candidate_cut_pairs = set(cut_pairs)
    candidate_cut_pairs.update(candidate_explicit_pairs)
    write_csv(scoring_dir / "edge_cut.csv", edge_rows)
    write_json(
        scoring_dir / "edge_cut_summary.json",
        {
            "cut_pairs": [[NODE_NAMES[i], NODE_NAMES[j]] for i, j in sorted(cut_pairs)],
            "candidate_cut_pairs": [[NODE_NAMES[i], NODE_NAMES[j]] for i, j in sorted(candidate_cut_pairs)],
            "explicit_cut_pairs": [[NODE_NAMES[i], NODE_NAMES[j]] for i, j in sorted(explicit_pairs)],
            "candidate_explicit_cut_pairs": [[NODE_NAMES[i], NODE_NAMES[j]] for i, j in sorted(candidate_explicit_pairs)],
            "auto_cut_edges": args.auto_cut_edges,
            "failure_bit_csv": str(args.failure_bit_csv),
            "base_cut_min_order": args.base_cut_min_order,
            "candidate_cut_min_order": args.candidate_cut_min_order,
        },
    )

    filtered_base_terms, removed_rows = filter_terms_by_cut(base.terms, cut_pairs, args.base_cut_min_order)
    write_csv(scoring_dir / "removed_base_terms_by_cut.csv", removed_rows)
    critical, critical_rows, critical_summary = classify_critical_nodes(score, bad_mi, full3, args)
    write_csv(scoring_dir / "critical_nodes.csv", critical_rows)
    write_json(scoring_dir / "critical_summary.json", critical_summary)

    max_count = max(parse_int_list(args.quad_counts), default=0)
    all_quads, all_quad_rows, hyper_summary = select_quads_with_hypercut(
        filtered_base_terms,
        critical_rows,
        critical,
        bad_mi,
        valid_mi,
        candidate_cut_pairs,
        max_count,
        args,
    )
    write_csv(scoring_dir / "selected_quads_ranked.csv", all_quad_rows)
    write_json(scoring_dir / "hyperedge_cut_summary.json", hyper_summary)
    print(
        "edge/hyperedge cut: "
        f"cut_pairs={[[NODE_NAMES[i], NODE_NAMES[j]] for i, j in sorted(cut_pairs)]} "
        f"candidate_cut_pairs={[[NODE_NAMES[i], NODE_NAMES[j]] for i, j in sorted(candidate_cut_pairs)]} "
        f"removed_base_terms={len(removed_rows)} "
        f"ranked_quads={hyper_summary['ranked_candidates']}",
        flush=True,
    )
    print(
        "critical nodes: "
        f"count={critical_summary['critical_count']} "
        f"nodes={critical_summary['critical_nodes']}",
        flush=True,
    )

    summary_rows: list[dict] = []
    for quad_count in parse_int_list(args.quad_counts):
        run_key = f"hypercut_q{quad_count}"
        run_dir = args.out / run_key
        run_dir.mkdir(parents=True, exist_ok=True)
        selected_quads = all_quads[:quad_count]
        write_csv(run_dir / "selected_quads.csv", all_quad_rows[:quad_count])
        write_json(run_dir / "critical_summary.json", critical_summary)
        terms = sorted(set(tuple(term) for term in filtered_base_terms).union(selected_quads), key=lambda item: (len(item), item))
        row = {
            "run_key": run_key,
            "quad_count": quad_count,
            "cut_pair_count": len(cut_pairs),
            "removed_base_terms": len(removed_rows),
            "term_count": len(terms),
            "term_count_by_order": term_count_by_order(terms),
            "selected_quad_count": len(selected_quads),
            "critical_count": critical_summary["critical_count"],
            "critical_nodes": " ".join(critical_summary["critical_nodes"]),
        }
        if args.select_only:
            summary_rows.append(row)
            write_csv(args.out / "edge_hypercut_summary.csv", summary_rows)
            continue
        if args.seed_cuts_from.exists():
            shutil.copy2(args.seed_cuts_from, run_dir / "invalid_cuts_partial.npz")
            args.resume_cuts = True
        solution, audit = solve_cutting_plane(design, run_key, terms, args, seed_offset=700 + quad_count)
        write_json(run_dir / f"solution_{run_key}.json", solution_payload_with_dense(design, solution, args))
        row.update(audit)
        summary_rows.append(row)
        write_csv(args.out / "edge_hypercut_summary.csv", summary_rows)


if __name__ == "__main__":
    main()
