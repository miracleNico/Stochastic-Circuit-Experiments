import argparse
import csv
import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

from generate_hamiltonians import energy, hamiltonians


GATE_LABELS = {
    "AND": "AND",
    "OR": "OR",
    "NAND": "NAND",
    "NOR": "NOR",
    "HA_XOR": "XOR",
    "XNOR": "XNOR",
}


def gate_function(name: str, a: int, b: int) -> int:
    if name == "AND":
        return a & b
    if name == "OR":
        return a | b
    if name == "NAND":
        return 1 - (a & b)
    if name == "NOR":
        return 1 - (a | b)
    if name == "HA_XOR":
        return a ^ b
    if name == "XNOR":
        return 1 - (a ^ b)
    raise ValueError(name)


def all_states(n: int):
    for value in range(1 << n):
        yield tuple((value >> bit) & 1 for bit in range(n))


def conditional_distribution(ham, clamps: dict[int, int]) -> list[tuple[tuple[int, ...], float]]:
    weighted = []
    for bits in all_states(len(ham.nodes)):
        if any(bits[index] != value for index, value in clamps.items()):
            continue
        weighted.append((bits, math.exp(-energy(ham.h, ham.j, bits))))

    norm = sum(weight for _bits, weight in weighted)
    return [(bits, weight / norm) for bits, weight in weighted]


def summarize_gate(ham) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    valid = set(ham.valid_states or [])
    summaries = []
    states_rows = []
    ab_rows = []
    scenarios: list[tuple[str, dict[int, int], str]] = []

    for a in [0, 1]:
        for b in [0, 1]:
            scenarios.append((f"forward A={a} B={b}", {0: a, 1: b}, "0"))
    for y in [0, 1]:
        scenarios.append((f"reverse Y={y}", {2: y}, "1"))

    for scenario_id, (label, clamps, y_clamped) in enumerate(scenarios):
        dist = conditional_distribution(ham, clamps)
        valid_rate = sum(prob for bits, prob in dist if bits in valid)
        y_one_rate = sum(prob for bits, prob in dist if bits[2] == 1)
        state_probs = Counter()
        ab_probs = Counter()
        for bits, prob in dist:
            state = "".join(str(bit) for bit in bits)
            ab = f"{bits[0]}{bits[1]}"
            state_probs[state] += prob
            ab_probs[ab] += prob

        for state, prob in sorted(state_probs.items()):
            states_rows.append(
                {
                    "gate": GATE_LABELS[ham.name],
                    "scenario": str(scenario_id),
                    "label": label,
                    "state": state,
                    "probability": f"{prob:.8f}",
                    "valid_state": "1" if tuple(int(ch) for ch in state) in valid else "0",
                }
            )

        for ab in ["00", "01", "10", "11"]:
            a = int(ab[0])
            b = int(ab[1])
            y_value = clamps.get(2, 0)
            ab_rows.append(
                {
                    "gate": GATE_LABELS[ham.name],
                    "scenario": str(scenario_id),
                    "label": label,
                    "y_clamped": y_clamped,
                    "y_value": str(y_value),
                    "ab": ab,
                    "probability": f"{ab_probs[ab]:.8f}",
                    "valid_for_clamped_y": "1"
                    if y_clamped == "1" and gate_function(ham.name, a, b) == y_value
                    else "0",
                }
            )

        summaries.append(
            {
                "gate": GATE_LABELS[ham.name],
                "scenario": str(scenario_id),
                "label": label,
                "valid_rate": f"{valid_rate:.8f}",
                "y_one_rate": f"{y_one_rate:.8f}",
                "state_probabilities": " ".join(
                    f"{state}:{prob:.3f}" for state, prob in state_probs.most_common()
                ),
                "ab_probabilities": " ".join(f"{ab}:{ab_probs[ab]:.3f}" for ab in ["00", "01", "10", "11"]),
            }
        )

    return summaries, states_rows, ab_rows


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_reverse_ab(rows: list[dict[str, str]], path: Path) -> None:
    reverse_rows = [row for row in rows if row["y_clamped"] == "1"]
    gates = list(dict.fromkeys(row["gate"] for row in reverse_rows))
    fig, axes = plt.subplots(len(gates), 2, figsize=(11, 2.2 * len(gates)), sharey=True)
    colors = {"00": "#4c78a8", "01": "#f58518", "10": "#54a24b", "11": "#b279a2"}

    for row_index, gate in enumerate(gates):
        for col_index, y_value in enumerate(["0", "1"]):
            ax = axes[row_index][col_index]
            selected = [
                row for row in reverse_rows
                if row["gate"] == gate and row["y_value"] == y_value
            ]
            xs = [row["ab"] for row in selected]
            ys = [float(row["probability"]) for row in selected]
            ax.bar(xs, ys, color=[colors[x] for x in xs])
            ax.set_ylim(0, 1)
            ax.grid(True, axis="y", color="#dddddd")
            ax.set_title(f"{gate} reverse Y={y_value}")
            if col_index == 0:
                ax.set_ylabel("P(A,B)")

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate exact small-gate probability CSV/PNG reports.")
    parser.add_argument("--summary", type=Path, default=Path("sim/generated_gate_probability_summary.csv"))
    parser.add_argument("--states", type=Path, default=Path("sim/generated_gate_state_probabilities.csv"))
    parser.add_argument("--ab", type=Path, default=Path("sim/generated_gate_ab_probabilities.csv"))
    parser.add_argument("--plot", type=Path, default=Path("sim/generated_gate_probabilities.png"))
    args = parser.parse_args()

    hams = [
        ham for ham in hamiltonians(argparse.Namespace(ha_scale=1, fa_scale=1))
        if ham.name in GATE_LABELS
    ]

    summaries = []
    states = []
    abs_ = []
    for ham in hams:
        gate_summaries, gate_states, gate_abs = summarize_gate(ham)
        summaries.extend(gate_summaries)
        states.extend(gate_states)
        abs_.extend(gate_abs)

    write_csv(
        args.summary,
        summaries,
        ["gate", "scenario", "label", "valid_rate", "y_one_rate", "state_probabilities", "ab_probabilities"],
    )
    write_csv(args.states, states, ["gate", "scenario", "label", "state", "probability", "valid_state"])
    write_csv(
        args.ab,
        abs_,
        ["gate", "scenario", "label", "y_clamped", "y_value", "ab", "probability", "valid_for_clamped_y"],
    )
    plot_reverse_ab(abs_, args.plot)

    print(f"Wrote summary: {args.summary}")
    print(f"Wrote states:  {args.states}")
    print(f"Wrote AB:      {args.ab}")
    print(f"Wrote plot:    {args.plot}")


if __name__ == "__main__":
    main()
