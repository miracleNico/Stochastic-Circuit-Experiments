import csv
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from generate_shadow1_adder4 import emit as emit_shadow1
from generate_shadow1_q34_adder4 import FRAC_BITS, optimize_q34_blocks


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "presentation_8bit_rca" / "scratch_shadow_j_sweep"
VHDL_DIR = OUT / "vhdl"
TRACES = OUT / "traces"
DATA = OUT / "data"

TRIALS = 200
SCRAMBLE_CYCLES = 80
SETTLE_CYCLES = 160
BLOCK_RND = 4
COPY_RND = 0
SCRAMBLE_RND = 8

PAIRS_PHYSICAL = [
    (3, 3),
    (2, 2),
    (1, 1),
    (1, 4),
    (2, 3),
    (3, 2),
    (2, 1),
]

SUMMARY_RE = re.compile(
    r"sumdist_random summary SUM=(?P<sum>\d+) valid_total=(?P<valid>\d+) "
    r"invalid_total=(?P<invalid>\d+) coverage=(?P<coverage>\d+) trials=(?P<trials>\d+) "
    r"parallel=(?P<parallel>\w+) reverse=(?P<reverse>\w+) block_rnd=(?P<block_rnd>\d+) "
    r"copy_rnd=(?P<copy_rnd>\d+) scramble_rnd=(?P<scramble_rnd>\d+) "
    r"blocks=(?P<blocks>[0-9,]+) copy=(?P<copy>\d+) settle=(?P<settle>\d+)"
)
VALID_RE = re.compile(
    r"sumdist_random valid SUM=(?P<sum>\d+) A=(?P<a>\d+) B=(?P<b>\d+) "
    r"count=(?P<count>\d+) trials=(?P<trials>\d+)"
)


def valid_pair_count(target_sum: int) -> int:
    return sum(1 for a in range(16) for b in range(16) if a + b == target_sum)


def distribution_metrics(counts: list[int], pair_count: int) -> tuple[float, float]:
    total = sum(counts)
    if total == 0:
        return 0.0, 1.0
    if pair_count <= 1:
        entropy_norm = 1.0
    else:
        entropy = 0.0
        for count in counts:
            if count:
                p = count / total
                entropy -= p * math.log(p)
        entropy_norm = entropy / math.log(pair_count)
    uniform = 1 / pair_count
    tv = 0.5 * sum(abs((count / total) - uniform) for count in counts)
    return entropy_norm, tv


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_models(name: str, vhdl_path: Path) -> str:
    sim_relative_vhdl = Path("..") / vhdl_path.relative_to(ROOT)
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / "sim" / "run_adder4_shadow1_sum_randomized_distribution.ps1"),
        "-GeneratedShadowVhdl",
        sim_relative_vhdl.as_posix(),
        "-BlockRndWeight",
        str(BLOCK_RND),
        "-CopyRndWeight",
        str(COPY_RND),
        "-ScrambleRndWeight",
        str(SCRAMBLE_RND),
        "-ScrambleCycles",
        str(SCRAMBLE_CYCLES),
        "-SettleCycles",
        str(SETTLE_CYCLES),
        "-Trials",
        str(TRIALS),
        "-ParallelMode",
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    trace_path = TRACES / f"{name}.txt"
    trace_path.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {proc.returncode}; see {trace_path}")
    return proc.stdout


def parse_run(name: str, forward_j: int, reverse_j: int, text: str) -> tuple[list[dict], list[dict]]:
    by_sum = []
    valid_counts: dict[int, list[int]] = defaultdict(list)
    for match in VALID_RE.finditer(text):
        valid_counts[int(match.group("sum"))].append(int(match.group("count")))

    for match in SUMMARY_RE.finditer(text):
        target_sum = int(match.group("sum"))
        trials = int(match.group("trials"))
        valid = int(match.group("valid"))
        pair_count = valid_pair_count(target_sum)
        counts = valid_counts[target_sum]
        coverage = sum(1 for count in counts if count > 0)
        entropy, tv = distribution_metrics(counts, pair_count)
        by_sum.append(
            {
                "run": name,
                "copy_c_to_q_physical": forward_j,
                "reverse_q_to_c_physical": reverse_j,
                "sum": target_sum,
                "valid_total": valid,
                "invalid_total": int(match.group("invalid")),
                "trials": trials,
                "valid_rate": valid / trials,
                "valid_pair_count": pair_count,
                "coverage": coverage,
                "coverage_rate": coverage / pair_count,
                "valid_entropy_norm": entropy,
                "valid_tv_from_uniform": tv,
            }
        )

    aggregate = []
    valid_total = sum(row["valid_total"] for row in by_sum)
    trials_total = sum(row["trials"] for row in by_sum)
    valid_pairs_total = sum(row["valid_pair_count"] for row in by_sum)
    valid_pairs_seen = sum(row["coverage"] for row in by_sum)
    aggregate.append(
        {
            "run": name,
            "copy_c_to_q_physical": forward_j,
            "reverse_q_to_c_physical": reverse_j,
            "copy_c_to_q_encoded": forward_j << FRAC_BITS,
            "reverse_q_to_c_encoded": reverse_j << FRAC_BITS,
            "valid_total": valid_total,
            "trials": trials_total,
            "valid_rate": valid_total / trials_total,
            "valid_pairs_seen": valid_pairs_seen,
            "valid_pairs_total": valid_pairs_total,
            "coverage_rate": valid_pairs_seen / valid_pairs_total,
            "weighted_entropy_norm": sum(row["valid_entropy_norm"] * row["valid_pair_count"] for row in by_sum)
            / valid_pairs_total,
            "weighted_tv_from_uniform": sum(row["valid_tv_from_uniform"] * row["valid_pair_count"] for row in by_sum)
            / valid_pairs_total,
            "min_sum_valid_rate": min(row["valid_rate"] for row in by_sum),
            "zero_valid_sums": sum(1 for row in by_sum if row["valid_total"] == 0),
        }
    )
    return by_sum, aggregate


def main() -> None:
    VHDL_DIR.mkdir(parents=True, exist_ok=True)
    TRACES.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    q34_ha, q34_fa = optimize_q34_blocks()
    all_by_sum = []
    all_aggregate = []

    for forward_j, reverse_j in PAIRS_PHYSICAL:
        name = f"q34_idea24_copy_{forward_j}_{reverse_j}"
        vhdl_path = VHDL_DIR / f"{name}.vhd"
        emit_shadow1(
            vhdl_path,
            width=4,
            copy_weight=forward_j << FRAC_BITS,
            reverse_copy_weight=reverse_j << FRAC_BITS,
            ha=q34_ha.ham,
            fa=q34_fa.ham,
            entity="gen_adder4_shadow1_windowed",
            seed_name=f"SWEEP_{name.upper()}",
            field_frac_bits=FRAC_BITS,
        )
        text = run_models(name, vhdl_path)
        by_sum, aggregate = parse_run(name, forward_j, reverse_j, text)
        all_by_sum.extend(by_sum)
        all_aggregate.extend(aggregate)
        row = aggregate[0]
        print(
            f"{name}: valid={row['valid_rate'] * 100:.2f}% "
            f"coverage={row['coverage_rate'] * 100:.2f}% "
            f"entropy={row['weighted_entropy_norm']:.3f} "
            f"tv={row['weighted_tv_from_uniform']:.3f} "
            f"zero={row['zero_valid_sums']}"
        )

    write_csv(DATA / "shadow_copy_j_sweep_by_sum.csv", all_by_sum)
    write_csv(DATA / "shadow_copy_j_sweep_aggregate.csv", all_aggregate)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
