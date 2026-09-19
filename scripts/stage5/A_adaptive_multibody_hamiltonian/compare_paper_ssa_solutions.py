from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import argparse
import csv
import math
from pathlib import Path

from scripts.stage5.A_adaptive_multibody_hamiltonian.adaptive_qp_6bit import load_solution_from_run
from scripts.stage5.A_adaptive_multibody_hamiltonian.compare_adaptive23_convergence import parse_csv_strings, simulate_convergence_paper


ROOT = _REPO_ROOT / "results_and_reports/stage5/A_adaptive_multibody_hamiltonian"


def parse_solution_arg(text: str) -> tuple[str, Path]:
    if "=" not in text:
        raise argparse.ArgumentTypeError("solution must be LABEL=PATH")
    label, path = text.split("=", 1)
    label = label.strip()
    if not label:
        raise argparse.ArgumentTypeError("solution label must not be empty")
    return label, Path(path)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare solution directories with paper-derived SSA schedule")
    parser.add_argument(
        "--solution",
        action="append",
        type=parse_solution_arg,
        default=[],
        help="Solution directory as LABEL=PATH. Defaults to full2 and full3.",
    )
    parser.add_argument("--baseline-label", type=str, default="full3")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "out_paper_ssa_baselines")
    parser.add_argument("--modes", type=str, default="a,b,sum,ab,asum,bsum,absum_valid")
    parser.add_argument("--cycles", type=int, default=1000)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026070701)
    parser.add_argument("--paper-noise", choices=("common", "unique"), default="common")
    parser.add_argument("--paper-noise-decay", choices=("none", "exp"), default="exp")
    parser.add_argument("--paper-noise-final-ratio", type=float, default=0.1)
    parser.add_argument("--paper-alpha", type=float, default=0.0)
    args = parser.parse_args()

    solutions = args.solution or [
        ("full2", ROOT / "out" / "full2"),
        ("full3", ROOT / "out" / "full3"),
    ]
    runs = [(label, load_solution_from_run(path)) for label, path in solutions]
    modes = parse_csv_strings(args.modes)
    rows: list[dict] = []
    for mode_idx, mode in enumerate(modes):
        paired_seed = args.seed + mode_idx
        for label, solution in runs:
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
            row["label"] = label
            rows.append(row)
            write_csv(args.out_dir / "convergence_paired.csv", rows)
            print(
                f"{label} mode={mode} rate={row['success_rate_feasible']:.6f} "
                f"hits={row['hits']}/{row['feasible_trials']} "
                f"noise={args.paper_noise} decay={args.paper_noise_decay}:{args.paper_noise_final_ratio:g}",
                flush=True,
            )

    by_mode: dict[str, dict[str, dict]] = {}
    for row in rows:
        by_mode.setdefault(str(row["mode"]), {})[str(row["label"])] = row
    comparison_rows = []
    for mode, mode_rows in sorted(by_mode.items()):
        baseline = mode_rows.get(args.baseline_label)
        if baseline is None:
            continue
        base_rate = float(baseline["success_rate_feasible"])
        base_trials = int(baseline["feasible_trials"])
        for label, row in sorted(mode_rows.items()):
            rate = float(row["success_rate_feasible"])
            trials = int(row["feasible_trials"])
            delta = rate - base_rate
            se = math.sqrt(rate * (1.0 - rate) / max(trials, 1) + base_rate * (1.0 - base_rate) / max(base_trials, 1))
            comparison_rows.append(
                {
                    "mode": mode,
                    "baseline_label": args.baseline_label,
                    "label": label,
                    "baseline_rate": base_rate,
                    "success_rate": rate,
                    "delta_vs_baseline": delta,
                    "two_se": 2.0 * se,
                    "degraded_beyond_2se": delta < -2.0 * se,
                    "hits": int(row["hits"]),
                    "baseline_hits": int(baseline["hits"]),
                    "feasible_trials": trials,
                    "schedule": row["schedule"],
                    "noise_decay": row["noise_decay"],
                    "noise_final_ratio": row["noise_final_ratio"],
                    "i0min": row["i0min"],
                    "i0max": row["i0max"],
                    "nrnd_min": row["nrnd_min"],
                    "nrnd_max": row["nrnd_max"],
                }
            )
    write_csv(args.out_dir / "convergence_vs_baseline.csv", comparison_rows)
    print(f"wrote {args.out_dir / 'convergence_paired.csv'}", flush=True)
    print(f"wrote {args.out_dir / 'convergence_vs_baseline.csv'}", flush=True)


if __name__ == "__main__":
    main()
