import csv
import json
import math
from collections import Counter
from itertools import product
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from generate_hamiltonians import Hamiltonian, energy, fa_block, ha_block


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "presentation_8bit_rca"
FIGS = OUT / "figures"
DATA = OUT / "data"


def valid_ha_states() -> list[tuple[int, ...]]:
    return [(a, b, a ^ b, a & b) for a, b in product([0, 1], repeat=2)]


def valid_fa_states() -> list[tuple[int, ...]]:
    states = []
    for a, b, cin in product([0, 1], repeat=3):
        total = a + b + cin
        states.append((a, b, cin, total & 1, (total >> 1) & 1))
    return states


def load_q34_blocks() -> tuple[Hamiltonian, Hamiltonian, int]:
    path = DATA / "optimized_q34_shadow1_blocks.json"
    if not path.exists():
        from generate_shadow1_q34_adder4 import optimize_q34_blocks

        ha, fa = optimize_q34_blocks()
        return ha.ham, fa.ham, 4

    data = json.loads(path.read_text(encoding="utf-8"))
    gates = {gate["name"].split("_")[0]: gate for gate in data["gates"]}
    ha_gate = gates["HA"]
    fa_gate = gates["FA"]
    frac_bits = int(ha_gate["field_frac_bits"])
    ha = Hamiltonian(
        "HA_XOR_Q3D4F_OPT",
        "gen_xor_gate_q34_opt",
        ha_gate["nodes"],
        ha_gate["h_encoded"],
        ha_gate["J_encoded"],
        valid_ha_states(),
        "Loaded from optimized_q34_shadow1_blocks.json",
        field_frac_bits=frac_bits,
        weight_scale="fixed-q3d4f",
    )
    fa = Hamiltonian(
        "FA_Q3D4F_OPT",
        "gen_fa_gate_q34_opt",
        fa_gate["nodes"],
        fa_gate["h_encoded"],
        fa_gate["J_encoded"],
        valid_fa_states(),
        "Loaded from optimized_q34_shadow1_blocks.json",
        field_frac_bits=frac_bits,
        weight_scale="fixed-q3d4f",
    )
    return ha, fa, frac_bits


def convolve(left: Counter[int], right: Counter[int]) -> Counter[int]:
    result: Counter[int] = Counter()
    for e_left, n_left in left.items():
        for e_right, n_right in right.items():
            result[e_left + e_right] += n_left * n_right
    return result


def ha_transition(ha: Hamiltonian, cout: int) -> Counter[int]:
    values: Counter[int] = Counter()
    for a, b, s in product([0, 1], repeat=3):
        values[energy(ha.h, ha.j, (a, b, s, cout))] += 1
    return values


def fa_transition(fa: Hamiltonian, cin: int, cout: int) -> Counter[int]:
    values: Counter[int] = Counter()
    for a, b, s in product([0, 1], repeat=3):
        values[energy(fa.h, fa.j, (a, b, cin, s, cout))] += 1
    return values


def rca_energy_histogram(width: int, ha: Hamiltonian, fa: Hamiltonian) -> Counter[int]:
    dp = {cout: ha_transition(ha, cout) for cout in [0, 1]}
    for _bit in range(1, width):
        next_dp = {0: Counter(), 1: Counter()}
        for cin in [0, 1]:
            for cout in [0, 1]:
                combined = convolve(dp[cin], fa_transition(fa, cin, cout))
                next_dp[cout].update(combined)
        dp = next_dp

    total: Counter[int] = Counter()
    total.update(dp[0])
    total.update(dp[1])
    expected_states = 1 << (4 * width)
    observed_states = sum(total.values())
    if observed_states != expected_states:
        raise AssertionError(f"{width}-bit histogram count {observed_states} != {expected_states}")
    return total


def valid_energy(width: int, ha: Hamiltonian, fa: Hamiltonian) -> int:
    ha_e = energy(ha.h, ha.j, valid_ha_states()[0])
    fa_e = energy(fa.h, fa.j, valid_fa_states()[0])
    return ha_e + (width - 1) * fa_e


def landscape_case(label: str, width: int, ha: Hamiltonian, fa: Hamiltonian, frac_bits: int) -> dict:
    hist = rca_energy_histogram(width, ha, fa)
    e_valid = valid_energy(width, ha, fa)
    valid_count = 1 << (2 * width)
    if hist[e_valid] != valid_count:
        raise AssertionError(f"{label}: valid-energy count {hist[e_valid]} != {valid_count}")
    e_invalid = min(e for e in hist if e > e_valid)
    scale = 1 / (1 << frac_bits)
    return {
        "label": label,
        "width": width,
        "frac_bits": frac_bits,
        "scale": scale,
        "hist": hist,
        "state_count": sum(hist.values()),
        "valid_count": valid_count,
        "valid_energy_encoded": e_valid,
        "invalid_energy_encoded": e_invalid,
        "gap_encoded": e_invalid - e_valid,
        "valid_energy": e_valid * scale,
        "invalid_energy": e_invalid * scale,
        "gap": (e_invalid - e_valid) * scale,
        "min_energy": min(hist) * scale,
        "max_energy": max(hist) * scale,
        "energy_levels": len(hist),
    }


def bar_width(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.8
    diffs = [b - a for a, b in zip(xs, xs[1:]) if b > a]
    return min(diffs) * 0.82 if diffs else 0.8


def draw_full_landscape(cases: list[dict], path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 9.5), constrained_layout=True)
    for ax, case in zip(axes.flat, cases):
        hist = case["hist"]
        xs = [e * case["scale"] for e in sorted(hist)]
        ys = [math.log10(hist[e]) for e in sorted(hist)]
        ax.bar(xs, ys, width=bar_width(xs), color="#4f7cac", alpha=0.88, edgecolor="none")
        ax.axvline(case["valid_energy"], color="#00796b", linewidth=2.3, label="valid energy")
        ax.axvline(case["invalid_energy"], color="#b85c00", linewidth=2.0, linestyle="--", label="first invalid")
        ax.set_title(case["label"], fontsize=12, weight="bold")
        ax.set_xlabel("Hamiltonian energy, physical units")
        ax.set_ylabel("log10(state count)")
        ax.grid(axis="y", color="#d8dee8", linewidth=0.8)
        ax.text(
            0.02,
            0.96,
            "\n".join(
                [
                    f"states: {case['state_count']:,}",
                    f"valid states: {case['valid_count']:,}",
                    f"E_valid: {case['valid_energy']:.3g}",
                    f"gap: {case['gap']:.3g}",
                ]
            ),
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "#c8d1dc", "alpha": 0.92, "boxstyle": "round,pad=0.35"},
        )
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("RCA Hamiltonian Energy Landscape: Integer vs Q3.4 Quantized Gate Design", fontsize=15, weight="bold")
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def draw_low_energy(cases: list[dict], path: Path, levels: int = 18) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 9.5), constrained_layout=True)
    for ax, case in zip(axes.flat, cases):
        hist = case["hist"]
        selected = sorted(hist)[:levels]
        xs = list(range(len(selected)))
        colors = []
        for e in selected:
            if e == case["valid_energy_encoded"]:
                colors.append("#00796b")
            elif e == case["invalid_energy_encoded"]:
                colors.append("#b85c00")
            else:
                colors.append("#6f7f8f")
        ys = [math.log10(hist[e]) for e in selected]
        ax.bar(xs, ys, color=colors, alpha=0.9)
        labels = [f"{e * case['scale']:.3g}" for e in selected]
        ax.set_xticks(xs)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_title(case["label"], fontsize=12, weight="bold")
        ax.set_xlabel("lowest energy levels, physical units")
        ax.set_ylabel("log10(state count)")
        ax.grid(axis="y", color="#d8dee8", linewidth=0.8)
        ax.text(
            0.02,
            0.96,
            f"valid count at minimum: {case['valid_count']:,}\nfirst invalid gap: {case['gap']:.3g}",
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "#c8d1dc", "alpha": 0.92, "boxstyle": "round,pad=0.35"},
        )
    fig.suptitle("Low-Energy RCA Hamiltonian Basin", fontsize=15, weight="bold")
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_summary(cases: list[dict], path: Path) -> None:
    fields = [
        "label",
        "width",
        "state_count",
        "valid_count",
        "energy_levels",
        "min_energy",
        "valid_energy",
        "invalid_energy",
        "gap",
        "valid_energy_encoded",
        "invalid_energy_encoded",
        "gap_encoded",
        "frac_bits",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            writer.writerow({field: case[field] for field in fields})


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    int_ha = ha_block()
    int_fa = fa_block()
    q34_ha, q34_fa, q34_frac_bits = load_q34_blocks()

    cases = [
        landscape_case("4-bit RCA before quantization (integer)", 4, int_ha, int_fa, 0),
        landscape_case("4-bit RCA after Q3.4 design", 4, q34_ha, q34_fa, q34_frac_bits),
        landscape_case("8-bit RCA before quantization (integer)", 8, int_ha, int_fa, 0),
        landscape_case("8-bit RCA after Q3.4 design", 8, q34_ha, q34_fa, q34_frac_bits),
    ]

    full_path = FIGS / "rca_energy_landscape_fullcube.png"
    low_path = FIGS / "rca_energy_landscape_low_energy.png"
    summary_path = DATA / "rca_energy_landscape_summary.csv"
    draw_full_landscape(cases, full_path)
    draw_low_energy(cases, low_path)
    write_summary(cases, summary_path)
    print(full_path)
    print(low_path)
    print(summary_path)


if __name__ == "__main__":
    main()
