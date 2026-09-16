
import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

from scripts.gate_baseline.generate_hamiltonians import energy, hamiltonians


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


def _load_matplotlib_pyplot():
    """Load matplotlib on demand so the bundled Pillow-only runtime works."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as pyplot
    except ImportError:
        return None
    return pyplot


def _plot_reverse_ab_matplotlib(rows: list[dict[str, str]], path: Path, plt) -> None:
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


def _pillow_font(size: int, bold: bool = False):
    from PIL import ImageFont

    family = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(family, size)
    except OSError:
        return ImageFont.load_default()


def _plot_reverse_ab_pillow(rows: list[dict[str, str]], path: Path) -> None:
    from PIL import Image, ImageDraw

    reverse_rows = [row for row in rows if row["y_clamped"] == "1"]
    gates = list(dict.fromkeys(row["gate"] for row in reverse_rows))
    if not gates:
        raise ValueError("No reverse-clamp probability rows were provided")

    width = 1100
    header_height = 54
    row_height = 235
    height = header_height + row_height * len(gates) + 24
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _pillow_font(20, bold=True)
    heading_font = _pillow_font(14, bold=True)
    label_font = _pillow_font(11)
    small_font = _pillow_font(9)
    colors = {"00": "#4c78a8", "01": "#f58518", "10": "#54a24b", "11": "#b279a2"}

    draw.text((28, 16), "Exact reverse-clamp P(A,B) distributions", fill="#111111", font=title_font)
    panel_width = (width - 74) // 2
    for row_index, gate in enumerate(gates):
        panel_top = header_height + row_index * row_height + 28
        panel_bottom = panel_top + 170
        for col_index, y_value in enumerate(["0", "1"]):
            panel_left = 52 + col_index * (panel_width + 18)
            panel_right = panel_left + panel_width
            draw.rectangle((panel_left, panel_top, panel_right, panel_bottom), outline="#777777", width=1)
            for tick in range(5):
                probability = tick / 4
                y = round(panel_bottom - probability * (panel_bottom - panel_top))
                draw.line((panel_left, y, panel_right, y), fill="#e0e0e0", width=1)
                if col_index == 0:
                    draw.text((panel_left - 7, y), f"{probability:.2f}", fill="#444444", font=small_font, anchor="rm")

            selected = [
                row
                for row in reverse_rows
                if row["gate"] == gate and row["y_value"] == y_value
            ]
            by_ab = {row["ab"]: row for row in selected}
            bar_area = panel_right - panel_left
            slot_width = bar_area / 4
            for index, ab in enumerate(["00", "01", "10", "11"]):
                row = by_ab.get(ab)
                probability = float(row["probability"]) if row is not None else 0.0
                center = panel_left + (index + 0.5) * slot_width
                bar_width = slot_width * 0.58
                bar_top = panel_bottom - probability * (panel_bottom - panel_top)
                draw.rectangle(
                    (round(center - bar_width / 2), round(bar_top), round(center + bar_width / 2), panel_bottom),
                    fill=colors[ab],
                    outline="#333333" if row is not None and row["valid_for_clamped_y"] == "1" else colors[ab],
                    width=2,
                )
                draw.text((round(center), panel_bottom + 7), ab, fill="#222222", font=label_font, anchor="ma")
                draw.text(
                    (round(center), max(panel_top + 4, round(bar_top) - 15)),
                    f"{probability:.3f}",
                    fill="#222222",
                    font=small_font,
                    anchor="ma",
                )

            draw.text(
                ((panel_left + panel_right) // 2, panel_top - 22),
                f"{gate} reverse Y={y_value}",
                fill="#111111",
                font=heading_font,
                anchor="ma",
            )
            if col_index == 0:
                draw.text((18, (panel_top + panel_bottom) // 2), "P(A,B)", fill="#222222", font=label_font, anchor="mm")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def plot_reverse_ab(rows: list[dict[str, str]], path: Path) -> None:
    plt = _load_matplotlib_pyplot()
    if plt is None:
        _plot_reverse_ab_pillow(rows, path)
    else:
        _plot_reverse_ab_matplotlib(rows, path, plt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate exact small-gate probability CSV/PNG reports.")
    results = _REPO_ROOT / "results_and_reports/gate_baseline"
    parser.add_argument("--summary", type=Path, default=results / "generated_gate_probability_summary.csv")
    parser.add_argument("--states", type=Path, default=results / "generated_gate_state_probabilities.csv")
    parser.add_argument("--ab", type=Path, default=results / "generated_gate_ab_probabilities.csv")
    parser.add_argument("--plot", type=Path, default=results / "generated_gate_probabilities.png")
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
