import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


SCENARIOS = {
    0: "forward A=0 B=0",
    1: "forward A=0 B=1",
    2: "forward A=1 B=0",
    3: "forward A=1 B=1",
    4: "reverse Y=0",
    5: "reverse Y=1",
}


INT_COLUMNS = {
    "time_ns",
    "scenario",
    "measure",
    "clamp_a_en",
    "clamp_a_value",
    "clamp_b_en",
    "clamp_b_value",
    "clamp_y_en",
    "clamp_y_value",
    "a",
    "b",
    "y",
    "aux_c",
    "field_a",
    "field_b",
    "field_y",
    "field_aux",
}


def read_trace(path: Path) -> list[dict[str, int]]:
    with path.open(newline="") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append({key: int(value) for key, value in row.items() if key in INT_COLUMNS})
    if not rows:
        raise ValueError(f"No rows found in {path}")
    return rows


def state_key(row: dict[str, int], gate: str) -> str:
    if gate == "xor":
        return f'{row["a"]}{row["b"]}{row["y"]}{row["aux_c"]}'
    return f'{row["a"]}{row["b"]}{row["y"]}'


def is_valid_state(row: dict[str, int], gate: str) -> bool:
    if gate == "xor":
        return row["y"] == (row["a"] ^ row["b"]) and row["aux_c"] == (row["a"] & row["b"])
    return row["y"] == (row["a"] & row["b"])


def valid_state_keys(gate: str) -> set[str]:
    if gate == "xor":
        return {"0000", "0110", "1010", "1101"}
    return {"000", "010", "100", "111"}


def ab_valid_for_clamp(ab: str, y_value: int, gate: str) -> bool:
    a = int(ab[0])
    b = int(ab[1])
    if gate == "xor":
        return (a ^ b) == y_value
    return (a & b) == y_value


def summarize(
    rows: list[dict[str, int]],
    gate: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[int, list[dict[str, int]]] = defaultdict(list)
    for row in rows:
        grouped[row["scenario"]].append(row)

    summaries = []
    probabilities = []
    ab_probabilities = []
    valid_keys = valid_state_keys(gate)

    for scenario in sorted(grouped):
        measured = [row for row in grouped[scenario] if row["measure"] == 1]
        if not measured:
            continue

        valid_count = sum(1 for row in measured if is_valid_state(row, gate))
        y_ones = sum(row["y"] for row in measured)
        states = Counter(state_key(row, gate) for row in measured)
        ab_states = Counter(f'{row["a"]}{row["b"]}' for row in measured)
        top_states = " ".join(f"{state}:{count}" for state, count in states.most_common())
        state_probs = " ".join(
            f"{state}:{count / len(measured):.3f}"
            for state, count in states.most_common()
        )
        ab_pairs = ["00", "01", "10", "11"]
        ab_probs = " ".join(
            f"{ab}:{ab_states.get(ab, 0) / len(measured):.3f}"
            for ab in ab_pairs
        )

        y_clamped = measured[0].get("clamp_y_en", 0) == 1
        y_value = measured[0].get("clamp_y_value", 0)

        for state, count in sorted(states.items()):
            probabilities.append(
                {
                    "gate": gate.upper(),
                    "scenario": str(scenario),
                    "label": SCENARIOS.get(scenario, f"scenario {scenario}"),
                    "state": state,
                    "count": str(count),
                    "probability": f"{count / len(measured):.6f}",
                    "valid_state": "1" if state in valid_keys else "0",
                }
            )

        for ab in ab_pairs:
            count = ab_states.get(ab, 0)
            ab_probabilities.append(
                {
                    "gate": gate.upper(),
                    "scenario": str(scenario),
                    "label": SCENARIOS.get(scenario, f"scenario {scenario}"),
                    "y_clamped": "1" if y_clamped else "0",
                    "y_value": str(y_value),
                    "ab": ab,
                    "count": str(count),
                    "probability": f"{count / len(measured):.6f}",
                    "valid_for_clamped_y": "1" if (y_clamped and ab_valid_for_clamp(ab, y_value, gate)) else "0",
                }
            )

        summaries.append(
            {
                "gate": gate.upper(),
                "scenario": str(scenario),
                "label": SCENARIOS.get(scenario, f"scenario {scenario}"),
                "samples": str(len(measured)),
                "valid_rate": f"{valid_count / len(measured):.3f}",
                "y_one_rate": f"{y_ones / len(measured):.3f}",
                "state_counts": top_states,
                "state_probabilities": state_probs,
                "ab_probabilities": ab_probs,
            }
        )
    return summaries, probabilities, ab_probabilities


def write_summary(path: Path, summaries: list[dict[str, str]]) -> None:
    fieldnames = [
        "gate",
        "scenario",
        "label",
        "samples",
        "valid_rate",
        "y_one_rate",
        "state_counts",
        "state_probabilities",
        "ab_probabilities",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summaries)


def write_probabilities(path: Path, probabilities: list[dict[str, str]]) -> None:
    fieldnames = ["gate", "scenario", "label", "state", "count", "probability", "valid_state"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(probabilities)


def write_ab_probabilities(path: Path, probabilities: list[dict[str, str]]) -> None:
    fieldnames = [
        "gate",
        "scenario",
        "label",
        "y_clamped",
        "y_value",
        "ab",
        "count",
        "probability",
        "valid_for_clamped_y",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(probabilities)


def print_summary(summaries: list[dict[str, str]], gate: str) -> None:
    print(f"\n{gate.upper()} trace summary")
    print("scenario                 samples  valid   y=1     state probabilities        AB probabilities")
    print("-" * 118)
    for item in summaries:
        print(
            f'{item["label"]:<24}'
            f'{item["samples"]:>7}  '
            f'{float(item["valid_rate"]) * 100:>5.1f}%  '
            f'{float(item["y_one_rate"]) * 100:>5.1f}%   '
            f'{item["state_probabilities"]:<26} '
            f'{item["ab_probabilities"]}'
        )


def add_scenario_background(ax, rows: list[dict[str, int]]) -> None:
    grouped: dict[int, list[dict[str, int]]] = defaultdict(list)
    for row in rows:
        grouped[row["scenario"]].append(row)

    colors = ["#f2f7ff", "#fff6e8"]
    for index, scenario in enumerate(sorted(grouped)):
        group = grouped[scenario]
        start = group[0]["time_ns"] / 1000.0
        end = group[-1]["time_ns"] / 1000.0
        ax.axvspan(start, end, color=colors[index % len(colors)], zorder=0)
        ax.text(
            (start + end) / 2,
            1.02,
            SCENARIOS.get(scenario, str(scenario)),
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=0,
        )


def plot_trace(rows: list[dict[str, int]], summaries: list[dict[str, str]], gate: str, path: Path) -> None:
    t_us = [row["time_ns"] / 1000.0 for row in rows]
    a = [row["a"] for row in rows]
    b = [row["b"] for row in rows]
    y = [row["y"] for row in rows]
    valid = [1 if is_valid_state(row, gate) else 0 for row in rows]
    measure = [row["measure"] for row in rows]
    aux = [row.get("aux_c", 0) for row in rows]

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(15, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [2.0, 1.8, 1.4, 1.4]},
    )

    for ax in axes:
        add_scenario_background(ax, rows)
        ax.grid(True, axis="y", color="#dddddd", linewidth=0.7)
        ax.set_axisbelow(True)

    axes[0].step(t_us, [2.0 + 0.65 * value for value in a], where="post", label="A", linewidth=1.6)
    axes[0].step(t_us, [1.0 + 0.65 * value for value in b], where="post", label="B", linewidth=1.6)
    axes[0].step(t_us, [0.0 + 0.65 * value for value in y], where="post", label="Y", linewidth=1.6)
    if gate == "xor":
        axes[0].step(t_us, [-1.0 + 0.65 * value for value in aux], where="post", label="aux C", linewidth=1.6)
        axes[0].set_yticks([2.325, 1.325, 0.325, -0.675])
        axes[0].set_yticklabels(["A", "B", "Y", "C"])
        axes[0].set_ylim(-1.25, 3.0)
    else:
        axes[0].set_yticks([2.325, 1.325, 0.325])
        axes[0].set_yticklabels(["A", "B", "Y"])
        axes[0].set_ylim(-0.25, 3.0)
    axes[0].set_title(f"Invertible {gate.upper()} stochastic spin samples")
    axes[0].legend(loc="upper right", ncol=4)

    axes[1].step(t_us, [row["field_a"] for row in rows], where="post", label="field A")
    axes[1].step(t_us, [row["field_b"] for row in rows], where="post", label="field B")
    axes[1].step(t_us, [row["field_y"] for row in rows], where="post", label="field Y")
    if gate == "xor":
        axes[1].step(t_us, [row["field_aux"] for row in rows], where="post", label="field C")
    axes[1].axhline(0, color="#333333", linewidth=0.8)
    axes[1].set_ylabel("local field")
    axes[1].legend(loc="upper right", ncol=4)

    valid_label = "Y == A and B" if gate == "and" else "Y == A xor B, C == A and B"
    axes[2].step(t_us, valid, where="post", color="#147a3d", label=valid_label)
    axes[2].step(t_us, [1.15 * value for value in measure], where="post", color="#555555", label="measurement window")
    axes[2].set_yticks([0, 1])
    axes[2].set_ylim(-0.15, 1.35)
    axes[2].set_ylabel("valid")
    axes[2].legend(loc="upper right", ncol=2)

    summary_text = "\n".join(
        f'{item["label"]}: valid {float(item["valid_rate"]) * 100:.0f}%, '
        f'Y=1 {float(item["y_one_rate"]) * 100:.0f}%, '
        f'P(state {item["state_probabilities"]}), P(AB {item["ab_probabilities"]})'
        for item in summaries
    )
    axes[3].axis("off")
    axes[3].text(
        0.01,
        0.95,
        summary_text,
        va="top",
        ha="left",
        family="monospace",
        fontsize=9,
        transform=axes[3].transAxes,
    )

    axes[2].set_xlabel("time (us)")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse and plot ModelSim logic-gate trace CSV.")
    parser.add_argument("--gate", choices=["and", "xor"], default="and")
    parser.add_argument("--input", type=Path, default=Path("sim/and_trace.csv"))
    parser.add_argument("--plot", type=Path, default=Path("sim/and_trace.png"))
    parser.add_argument("--summary", type=Path, default=Path("sim/and_trace_summary.csv"))
    parser.add_argument("--probabilities", type=Path, default=Path("sim/and_state_probabilities.csv"))
    parser.add_argument("--ab-probabilities", type=Path, default=Path("sim/and_ab_probabilities.csv"))
    args = parser.parse_args()

    rows = read_trace(args.input)
    summaries, probabilities, ab_probabilities = summarize(rows, args.gate)

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.plot.parent.mkdir(parents=True, exist_ok=True)
    args.probabilities.parent.mkdir(parents=True, exist_ok=True)
    args.ab_probabilities.parent.mkdir(parents=True, exist_ok=True)

    write_summary(args.summary, summaries)
    write_probabilities(args.probabilities, probabilities)
    write_ab_probabilities(args.ab_probabilities, ab_probabilities)
    plot_trace(rows, summaries, args.gate, args.plot)
    print_summary(summaries, args.gate)
    print(f"\nWrote summary: {args.summary}")
    print(f"Wrote probabilities: {args.probabilities}")
    print(f"Wrote AB probabilities: {args.ab_probabilities}")
    print(f"Wrote plot:    {args.plot}")


if __name__ == "__main__":
    main()
