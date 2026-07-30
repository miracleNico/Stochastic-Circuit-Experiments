from __future__ import annotations

import argparse
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
    full_terms,
    load_solution,
    pair_mutual_information,
    solution_payload_with_dense,
    solve_cutting_plane,
    term_count_by_order,
    term_mask,
    write_csv,
    write_json,
)
from edge_hypercut_experiment import (
    build_edge_cut,
    load_failure_rates,
    parse_pair_list,
    select_quads_with_hypercut,
)
from tiny4_experiment import classify_critical_nodes


ROOT = Path(__file__).resolve().parent


def sum_sum_pairs() -> set[tuple[int, int]]:
    sum_indices = [idx for idx, name in enumerate(NODE_NAMES) if name.startswith("s")]
    return {tuple(pair) for pair in combinations(sum_indices, 2)}


def output_sibling_pairs() -> set[tuple[int, int]]:
    pairs = set()
    for bit in range(6):
        pairs.add(tuple(sorted((NODE_NAMES.index(f"s{bit}"), NODE_NAMES.index(f"c{bit + 1}")))))
    return pairs


def nonlocal_sum_carry_pairs() -> set[tuple[int, int]]:
    pairs = set()
    for s_bit in range(7):
        s_idx = NODE_NAMES.index(f"s{s_bit}")
        allowed = set()
        if 1 <= s_bit <= 5:
            allowed.add(f"c{s_bit}")  # input carry of the same sum bit
        if s_bit == 6:
            allowed.add("c6")  # final sum is the final carry
        for c_bit in range(1, 7):
            cname = f"c{c_bit}"
            if cname not in allowed:
                pairs.add(tuple(sorted((s_idx, NODE_NAMES.index(cname)))))
    return pairs


def nonadjacent_carry_pairs() -> set[tuple[int, int]]:
    pairs = set()
    for left in range(1, 7):
        for right in range(left + 1, 7):
            if right - left > 1:
                pairs.add(tuple(sorted((NODE_NAMES.index(f"c{left}"), NODE_NAMES.index(f"c{right}")))))
    return pairs


def augment_pairs(base: set[tuple[int, int]], args: argparse.Namespace, prefix: str) -> set[tuple[int, int]]:
    pairs = set(base)
    if getattr(args, f"{prefix}_cut_sum_sum"):
        pairs.update(sum_sum_pairs())
    if getattr(args, f"{prefix}_cut_output_siblings"):
        pairs.update(output_sibling_pairs())
    if getattr(args, f"{prefix}_cut_nonlocal_sum_carry"):
        pairs.update(nonlocal_sum_carry_pairs())
    if getattr(args, f"{prefix}_cut_nonadjacent_carry"):
        pairs.update(nonadjacent_carry_pairs())
    return pairs


def pair_names(pairs: set[tuple[int, int]]) -> list[list[str]]:
    return [[NODE_NAMES[i], NODE_NAMES[j]] for i, j in sorted(pairs)]


def has_cut_pair(term: tuple[int, ...], pairs: set[tuple[int, int]]) -> bool:
    return any(tuple(sorted(pair)) in pairs for pair in combinations(term, 2))


def filter_terms(terms: list[tuple[int, ...]], pairs: set[tuple[int, int]]) -> tuple[list[tuple[int, ...]], list[dict]]:
    kept = []
    removed = []
    for term in terms:
        term = tuple(term)
        cut_pairs = [tuple(sorted(pair)) for pair in combinations(term, 2) if tuple(sorted(pair)) in pairs]
        if cut_pairs:
            removed.append(
                {
                    "order": len(term),
                    "indices": list(term),
                    "nodes": [NODE_NAMES[idx] for idx in term],
                    "cut_pairs": ["-".join(NODE_NAMES[idx] for idx in pair) for pair in cut_pairs],
                }
            )
        else:
            kept.append(term)
    return kept, removed


def select_triples_with_edgecut(
    score: np.ndarray,
    bad_mi: np.ndarray,
    valid_mi: np.ndarray,
    full3_support: dict[int, float],
    candidate_cut_pairs: set[tuple[int, int]],
    max_count: int,
    args: argparse.Namespace,
) -> tuple[list[tuple[int, ...]], list[dict], dict]:
    ranked = []
    rejected_by_cut = 0
    rejected_by_critical_max = 0
    for term in combinations(range(N), 3):
        term = tuple(int(idx) for idx in term)
        if has_cut_pair(term, candidate_cut_pairs):
            rejected_by_cut += 1
            continue
        critical_count = int(sum(bool(args._stage3_critical[idx]) for idx in term))
        if args.triple_max_critical_count >= 0 and critical_count > args.triple_max_critical_count:
            rejected_by_critical_max += 1
            continue
        bad_mi_sum = float(sum(bad_mi[i, j] for i, j in combinations(term, 2)))
        valid_mi_sum = float(sum(valid_mi[i, j] for i, j in combinations(term, 2)))
        value = float(
            args.triple_score_weight * np.sum(score[list(term)])
            + args.triple_full3_support_weight * full3_support.get(term_mask(term), 0.0)
            + args.triple_valid_mi_weight * valid_mi_sum
            - args.triple_bad_mi_penalty * bad_mi_sum
        )
        ranked.append((value, bad_mi_sum, valid_mi_sum, critical_count, term))
    ranked.sort(reverse=True, key=lambda item: item[0])
    usage = np.zeros(N, dtype=np.int32)
    selected_ranked = []
    rejected_by_usage = 0
    for item in ranked:
        _value, _bad_mi, _valid_mi, _cc, term = item
        if args.triple_node_usage_cap > 0 and any(usage[idx] >= args.triple_node_usage_cap for idx in term):
            rejected_by_usage += 1
            continue
        selected_ranked.append(item)
        for idx in term:
            usage[idx] += 1
        if len(selected_ranked) >= max_count:
            break
    rows = []
    for rank, (value, bad_mi_sum, valid_mi_sum, critical_count, term) in enumerate(selected_ranked):
        rows.append(
            {
                "rank": rank,
                "score": float(value),
                "bad_mi_sum": float(bad_mi_sum),
                "valid_mi_sum": float(valid_mi_sum),
                "critical_node_count": critical_count,
                "indices": list(term),
                "nodes": [NODE_NAMES[idx] for idx in term],
            }
        )
    summary = {
        "ranked_candidates": len(ranked),
        "selected": len(selected_ranked),
        "rejected_by_edge_cut": rejected_by_cut,
        "rejected_by_max_critical_count": rejected_by_critical_max,
        "rejected_by_node_usage_cap": rejected_by_usage,
        "node_usage_cap": args.triple_node_usage_cap,
    }
    return [term for *_prefix, term in selected_ranked], rows, summary


def copy_seed(seed_path: Path, run_dir: Path, args: argparse.Namespace) -> None:
    if seed_path.exists():
        shutil.copy2(seed_path, run_dir / "invalid_cuts_partial.npz")
        args.resume_cuts = True


def run_stage3(args: argparse.Namespace):
    design = build_design()
    full2 = load_solution(args.full2_solution)
    full3 = load_solution(args.full3_solution)
    stage3_dir = args.out / "stage3_from_full2"
    scoring_dir = stage3_dir / "_scoring"
    scoring_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed + 6103)

    score, bad_mi, full3_support = compute_node_scores(design, full2, full3, args, scoring_dir, rng)
    valid_mi = pair_mutual_information(codes_to_bits(design.valid_codes))
    failure_rates = load_failure_rates(args.failure_bit_csv)
    edge_pairs = parse_pair_list(args.stage3_cut_pairs)
    edge_pairs = augment_pairs(edge_pairs, args, "stage3")
    cut_pairs, edge_rows = build_edge_cut(valid_mi, bad_mi, failure_rates, edge_pairs, args)
    candidate_cut_pairs = set(cut_pairs)
    candidate_cut_pairs.update(parse_pair_list(args.stage3_candidate_cut_pairs))
    candidate_cut_pairs = augment_pairs(candidate_cut_pairs, args, "stage3")
    write_csv(scoring_dir / "edge_cut.csv", edge_rows)
    write_json(
        scoring_dir / "edge_cut_summary.json",
        {
            "cut_pairs": pair_names(cut_pairs),
            "candidate_cut_pairs": pair_names(candidate_cut_pairs),
            "cut_sum_sum": args.stage3_cut_sum_sum,
            "cut_output_siblings": args.stage3_cut_output_siblings,
            "cut_nonlocal_sum_carry": args.stage3_cut_nonlocal_sum_carry,
            "cut_nonadjacent_carry": args.stage3_cut_nonadjacent_carry,
        },
    )
    critical, critical_rows, critical_summary = classify_critical_nodes(score, bad_mi, full3, args)
    args._stage3_critical = critical
    write_csv(scoring_dir / "critical_nodes.csv", critical_rows)
    write_json(scoring_dir / "critical_summary.json", critical_summary)
    triples, triple_rows, triple_summary = select_triples_with_edgecut(
        score,
        bad_mi,
        valid_mi,
        full3_support,
        candidate_cut_pairs,
        args.stage3_triples,
        args,
    )
    write_csv(scoring_dir / "selected_triples.csv", triple_rows)
    write_json(scoring_dir / "triple_selection_summary.json", triple_summary)
    base_terms, removed_base = filter_terms(full_terms(2), candidate_cut_pairs)
    write_csv(scoring_dir / "removed_base_terms.csv", removed_base)
    terms = sorted(set(base_terms).union(triples), key=lambda item: (len(item), item))
    run_key = "stage3_from_full2"
    row = {
        "run_key": run_key,
        "term_count": len(terms),
        "term_count_by_order": term_count_by_order(terms),
        "removed_base_terms": len(removed_base),
        "selected_triples": len(triples),
        "critical_nodes": " ".join(critical_summary["critical_nodes"]),
        **triple_summary,
    }
    write_csv(args.out / "staged_summary.csv", [row])
    print(
        f"stage3 select: terms={len(terms)} triples={len(triples)} "
        f"cut_pairs={pair_names(candidate_cut_pairs)}",
        flush=True,
    )
    if args.select_only:
        return None, row

    copy_seed(args.stage3_seed_cuts_from, stage3_dir, args)
    solution, audit = solve_cutting_plane(design, run_key, terms, args, seed_offset=8103)
    write_json(stage3_dir / f"solution_{run_key}.json", solution_payload_with_dense(design, solution, args))
    row.update(audit)
    write_csv(args.out / "staged_summary.csv", [row])
    return solution, row


def run_stage4(args: argparse.Namespace, stage3_solution):
    design = build_design()
    full3 = load_solution(args.full3_solution)
    if stage3_solution is None:
        stage3_solution = load_solution(args.stage3_solution)
    run_key = f"stage4_from_stage3_q{args.stage4_quads}"
    stage4_dir = args.out / run_key
    scoring_dir = stage4_dir / "_scoring"
    scoring_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed + 7104)

    score, bad_mi, _full3_support = compute_node_scores(design, stage3_solution, full3, args, scoring_dir, rng)
    valid_mi = pair_mutual_information(codes_to_bits(design.valid_codes))
    failure_rates = load_failure_rates(args.failure_bit_csv)
    edge_pairs = parse_pair_list(args.stage4_cut_pairs)
    edge_pairs = augment_pairs(edge_pairs, args, "stage4")
    cut_pairs, edge_rows = build_edge_cut(valid_mi, bad_mi, failure_rates, edge_pairs, args)
    candidate_cut_pairs = set(cut_pairs)
    candidate_cut_pairs.update(parse_pair_list(args.stage4_candidate_cut_pairs))
    candidate_cut_pairs = augment_pairs(candidate_cut_pairs, args, "stage4")
    write_csv(scoring_dir / "edge_cut.csv", edge_rows)
    write_json(
        scoring_dir / "edge_cut_summary.json",
        {
            "cut_pairs": pair_names(cut_pairs),
            "candidate_cut_pairs": pair_names(candidate_cut_pairs),
            "cut_sum_sum": args.stage4_cut_sum_sum,
            "cut_output_siblings": args.stage4_cut_output_siblings,
            "cut_nonlocal_sum_carry": args.stage4_cut_nonlocal_sum_carry,
            "cut_nonadjacent_carry": args.stage4_cut_nonadjacent_carry,
        },
    )
    critical, critical_rows, critical_summary = classify_critical_nodes(score, bad_mi, full3, args)
    write_csv(scoring_dir / "critical_nodes.csv", critical_rows)
    write_json(scoring_dir / "critical_summary.json", critical_summary)
    quads, quad_rows, quad_summary = select_quads_with_hypercut(
        stage3_solution.terms,
        critical_rows,
        critical,
        bad_mi,
        valid_mi,
        candidate_cut_pairs,
        args.stage4_quads,
        args,
    )
    write_csv(scoring_dir / "selected_quads.csv", quad_rows)
    write_json(scoring_dir / "quad_selection_summary.json", quad_summary)
    terms = sorted(set(stage3_solution.terms).union(quads), key=lambda item: (len(item), item))
    row = {
        "run_key": run_key,
        "term_count": len(terms),
        "term_count_by_order": term_count_by_order(terms),
        "selected_quads": len(quads),
        "critical_nodes": " ".join(critical_summary["critical_nodes"]),
        **quad_summary,
    }
    summary_path = args.out / "staged_summary.csv"
    existing = []
    if summary_path.exists():
        import csv

        with summary_path.open(newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    write_csv(summary_path, existing + [row])
    print(
        f"stage4 select: terms={len(terms)} quads={len(quads)} "
        f"cut_pairs={pair_names(candidate_cut_pairs)}",
        flush=True,
    )
    if args.select_only:
        return None, row

    seed_path = args.stage4_seed_cuts_from
    if seed_path is None:
        seed_path = args.out / "stage3_from_full2" / "invalid_cuts_final.npz"
    copy_seed(seed_path, stage4_dir, args)
    solution, audit = solve_cutting_plane(design, run_key, terms, args, seed_offset=9104)
    write_json(stage4_dir / f"solution_{run_key}.json", solution_payload_with_dense(design, solution, args))
    row.update(audit)
    if summary_path.exists():
        import csv

        with summary_path.open(newline="", encoding="utf-8") as handle:
            existing = [item for item in csv.DictReader(handle) if item.get("run_key") != run_key]
    write_csv(summary_path, existing + [row])
    return solution, row


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify staged edge/hyperedge cuts: 2-body -> 3-body -> 4-body")
    add_common_args(parser)
    parser.set_defaults(out=ROOT / "out_staged_cut_verifier")
    parser.add_argument("--full2-solution", type=Path, default=ROOT / "out" / "full2" / "solution_full2.json")
    parser.add_argument("--full3-solution", type=Path, default=ROOT / "out" / "full3" / "solution_full3.json")
    parser.add_argument("--stage3-solution", type=Path, default=ROOT / "out_staged_cut_verifier" / "stage3_from_full2" / "solution_stage3_from_full2.json")
    parser.add_argument("--stage3-seed-cuts-from", type=Path, default=ROOT / "out" / "full2" / "invalid_cuts_final.npz")
    parser.add_argument("--stage4-seed-cuts-from", type=Path, default=None)
    parser.add_argument(
        "--failure-bit-csv",
        type=Path,
        default=ROOT / "out_tiny4_q64" / "ab_failure_analysis_t20" / "tiny4_q64" / "ab_failed_bit_mismatch.csv",
    )
    parser.add_argument("--stage", choices=("stage3", "stage4", "all"), default="all")
    parser.add_argument("--select-only", action="store_true")
    parser.add_argument("--stage3-triples", type=int, default=2080)
    parser.add_argument("--stage3-cut-sum-sum", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stage3-cut-output-siblings", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--stage3-cut-nonlocal-sum-carry", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--stage3-cut-nonadjacent-carry", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--stage3-cut-pairs", type=str, default="s5:s6,s5:c6")
    parser.add_argument("--stage3-candidate-cut-pairs", type=str, default="")
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
    parser.add_argument("--triple-max-critical-count", type=int, default=-1)
    parser.add_argument("--triple-node-usage-cap", type=int, default=0)
    parser.add_argument("--triple-score-weight", type=float, default=1.0)
    parser.add_argument("--triple-full3-support-weight", type=float, default=0.5)
    parser.add_argument("--triple-valid-mi-weight", type=float, default=0.25)
    parser.add_argument("--triple-bad-mi-penalty", type=float, default=0.25)
    parser.add_argument("--stage4-quads", type=int, default=48)
    parser.add_argument("--stage4-cut-pairs", type=str, default="s5:s6,s5:c6")
    parser.add_argument("--stage4-candidate-cut-pairs", type=str, default="s6:c6")
    parser.add_argument("--stage4-cut-sum-sum", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stage4-cut-output-siblings", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--stage4-cut-nonlocal-sum-carry", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--stage4-cut-nonadjacent-carry", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--candidate-cut-min-order", type=int, default=4)
    parser.add_argument("--quad-require-critical-count", type=int, default=1)
    parser.add_argument("--quad-max-critical-count", type=int, default=1)
    parser.add_argument("--quad-node-usage-cap", type=int, default=8)
    parser.add_argument("--quad-linear-weight", type=float, default=1.0)
    parser.add_argument("--quad-bad-mi-penalty", type=float, default=1.0)
    parser.add_argument("--quad-valid-mi-weight", type=float, default=1.0)
    parser.add_argument("--quad-critical-bonus", type=float, default=0.25)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    stage3_solution = None
    if args.stage in ("stage3", "all"):
        stage3_solution, _row = run_stage3(args)
    if args.stage in ("stage4", "all") and not args.select_only:
        run_stage4(args, stage3_solution)
    elif args.stage in ("stage4", "all") and args.select_only:
        run_stage4(args, stage3_solution)


if __name__ == "__main__":
    main()
