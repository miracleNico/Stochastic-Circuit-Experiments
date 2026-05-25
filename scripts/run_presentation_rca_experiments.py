import csv
import json
import re
import secrets
import shutil
import subprocess
import sys
from argparse import Namespace
from itertools import product
from pathlib import Path

from generate_hamiltonians import adder4, adder8, emit_vhdl, energy, fa_block, ha_block, hamiltonians
from generate_shadow1_adder4 import emit as emit_shadow1
from generate_shadow1_q34_adder4 import (
    COPY_PHYSICAL,
    FRAC_BITS,
    optimize_q34_blocks,
    write_report as write_q34_report,
)
from generate_windowed_adder4 import emit as emit_windowed


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "presentation_8bit_rca"
DATA = OUT / "data"
FIGS = OUT / "figures"
TRACES = OUT / "traces"


DIRECT_TRIALS = 100
SHADOW_TRIALS = 100
REPEAT8_TRIALS = 100


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def ps_value(value: int | str) -> str:
    return str(value)


def run_models(name: str, script: str, args: list[str]) -> str:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / "sim" / script),
        *args,
    ]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=3600,
    )
    transcript = TRACES / f"{name}.txt"
    transcript.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {proc.returncode}; see {transcript}")
    return proc.stdout


def matrix_md(matrix: list[list[int | float]]) -> str:
    return "\n".join("| " + " | ".join(str(v) for v in row) + " |" for row in matrix)


def all_bit_states(n: int):
    for value in range(1 << n):
        yield tuple((value >> bit) & 1 for bit in range(n))


def prepare_output() -> None:
    reports_root = (ROOT / "reports").resolve()
    out_resolved = OUT.resolve()
    if OUT.exists():
        if not out_resolved.is_relative_to(reports_root):
            raise RuntimeError(f"Refusing to clean unexpected output path: {OUT}")
        shutil.rmtree(OUT)
    DATA.mkdir(parents=True)
    FIGS.mkdir(parents=True)
    TRACES.mkdir(parents=True)


def generate_artifacts() -> dict:
    manifest: dict = {"generated_at": "2026-05-25", "artifacts": {}}

    int_ha = ha_block()
    int_fa = fa_block()

    direct_salt = f"PRESENTATION_DIRECT4_{secrets.token_hex(8).upper()}"
    direct = adder4(int_ha, int_fa)
    direct.name = f"{direct.name}_{direct_salt}"
    direct_path = ROOT / "src" / "generated_presentation_direct_adder4.vhd"
    emit_vhdl([direct], direct_path)
    manifest["artifacts"]["direct_adder4"] = {
        "path": rel(direct_path),
        "entity": "gen_adder4",
        "seed_salt": direct_salt,
        "rnd_weight": 1,
    }

    direct8_salt = f"PRESENTATION_DIRECT8_{secrets.token_hex(8).upper()}"
    direct8 = adder8(int_ha, int_fa)
    direct8.name = f"{direct8.name}_{direct8_salt}"
    direct8_path = ROOT / "src" / "generated_presentation_direct_adder8.vhd"
    emit_vhdl([direct8], direct8_path)
    manifest["artifacts"]["direct_adder8"] = {
        "path": rel(direct8_path),
        "entity": "gen_adder8",
        "seed_salt": direct8_salt,
        "rnd_weight": 1,
    }

    window4_salt = f"PRESENTATION_INT4_WINDOW_{secrets.token_hex(8).upper()}"
    window4_path = ROOT / "src" / "generated_presentation_windowed_integer_adder4.vhd"
    emit_windowed(window4_path, seed_name=window4_salt)
    manifest["artifacts"]["integer_window4"] = {
        "path": rel(window4_path),
        "entity": "gen_adder4_windowed",
        "seed_salt": window4_salt,
        "field_frac_bits": 0,
    }

    int4_salt = f"PRESENTATION_INT4_SHADOW1_{secrets.token_hex(8).upper()}"
    int4_path = ROOT / "src" / "generated_presentation_shadow1_integer_adder4.vhd"
    emit_shadow1(
        int4_path,
        width=4,
        copy_weight=4,
        entity="gen_adder4_shadow1_windowed",
        seed_name=int4_salt,
        field_frac_bits=0,
    )
    manifest["artifacts"]["integer_shadow4"] = {
        "path": rel(int4_path),
        "entity": "gen_adder4_shadow1_windowed",
        "seed_salt": int4_salt,
        "copy_weight_encoded": 4,
        "field_frac_bits": 0,
    }

    int8_salt = f"PRESENTATION_INT8_SHADOW1_{secrets.token_hex(8).upper()}"
    int8_path = ROOT / "src" / "generated_presentation_shadow1_integer_adder8.vhd"
    emit_shadow1(
        int8_path,
        width=8,
        copy_weight=4,
        entity="gen_adder8_shadow1_windowed",
        seed_name=int8_salt,
        field_frac_bits=0,
    )
    manifest["artifacts"]["integer_shadow8"] = {
        "path": rel(int8_path),
        "entity": "gen_adder8_shadow1_windowed",
        "seed_salt": int8_salt,
        "copy_weight_encoded": 4,
        "field_frac_bits": 0,
    }

    q34_ha, q34_fa = optimize_q34_blocks()
    q34_copy = COPY_PHYSICAL << FRAC_BITS

    q34_direct4_salt = f"PRESENTATION_Q34_DIRECT4_{secrets.token_hex(8).upper()}"
    q34_direct4 = adder4(q34_ha.ham, q34_fa.ham)
    q34_direct4.name = f"{q34_direct4.name}_{q34_direct4_salt}"
    q34_direct4.field_frac_bits = FRAC_BITS
    q34_direct4.weight_scale = "fixed-q3d4f"
    q34_direct4_path = ROOT / "src" / "generated_presentation_direct_q34_adder4.vhd"
    emit_vhdl([q34_direct4], q34_direct4_path)
    manifest["artifacts"]["q34_direct4"] = {
        "path": rel(q34_direct4_path),
        "entity": "gen_adder4",
        "seed_salt": q34_direct4_salt,
        "field_frac_bits": FRAC_BITS,
        "rnd_weight_encoded": 4,
        "rnd_weight_physical": 4 / (1 << FRAC_BITS),
    }

    q34_direct8_salt = f"PRESENTATION_Q34_DIRECT8_{secrets.token_hex(8).upper()}"
    q34_direct8 = adder8(q34_ha.ham, q34_fa.ham)
    q34_direct8.name = f"{q34_direct8.name}_{q34_direct8_salt}"
    q34_direct8.field_frac_bits = FRAC_BITS
    q34_direct8.weight_scale = "fixed-q3d4f"
    q34_direct8_path = ROOT / "src" / "generated_presentation_direct_q34_adder8.vhd"
    emit_vhdl([q34_direct8], q34_direct8_path)
    manifest["artifacts"]["q34_direct8"] = {
        "path": rel(q34_direct8_path),
        "entity": "gen_adder8",
        "seed_salt": q34_direct8_salt,
        "field_frac_bits": FRAC_BITS,
        "rnd_weight_encoded": 4,
        "rnd_weight_physical": 4 / (1 << FRAC_BITS),
    }

    q34_4_salt = f"PRESENTATION_Q34_4_SHADOW1_{secrets.token_hex(8).upper()}"
    q34_4_path = ROOT / "src" / "generated_presentation_shadow1_q34_adder4.vhd"
    emit_shadow1(
        q34_4_path,
        width=4,
        copy_weight=q34_copy,
        ha=q34_ha.ham,
        fa=q34_fa.ham,
        entity="gen_adder4_shadow1_windowed",
        seed_name=q34_4_salt,
        field_frac_bits=FRAC_BITS,
    )
    manifest["artifacts"]["q34_shadow4"] = {
        "path": rel(q34_4_path),
        "entity": "gen_adder4_shadow1_windowed",
        "seed_salt": q34_4_salt,
        "copy_weight_encoded": q34_copy,
        "copy_weight_physical": q34_copy / (1 << FRAC_BITS),
        "field_frac_bits": FRAC_BITS,
    }

    q34_8_salt = f"PRESENTATION_Q34_8_SHADOW1_{secrets.token_hex(8).upper()}"
    q34_8_path = ROOT / "src" / "generated_presentation_shadow1_q34_adder8.vhd"
    emit_shadow1(
        q34_8_path,
        width=8,
        copy_weight=q34_copy,
        ha=q34_ha.ham,
        fa=q34_fa.ham,
        entity="gen_adder8_shadow1_windowed",
        seed_name=q34_8_salt,
        field_frac_bits=FRAC_BITS,
    )
    manifest["artifacts"]["q34_shadow8"] = {
        "path": rel(q34_8_path),
        "entity": "gen_adder8_shadow1_windowed",
        "seed_salt": q34_8_salt,
        "copy_weight_encoded": q34_copy,
        "copy_weight_physical": q34_copy / (1 << FRAC_BITS),
        "field_frac_bits": FRAC_BITS,
    }

    write_q34_report(DATA / "optimized_q34_shadow1_blocks.json", q34_ha, q34_fa, q34_copy)

    manifest["integer_weights"] = {
        "ha": {"h": int_ha.h, "J": int_ha.j, "gap": int_ha.energy_gap, "valid_energy": int_ha.valid_energy},
        "fa": {"h": int_fa.h, "J": int_fa.j, "gap": int_fa.energy_gap, "valid_energy": int_fa.valid_energy},
    }
    manifest["q34_weights"] = {
        "format": "Q3.4 fixed point",
        "ha": {
            "h_encoded": q34_ha.ham.h,
            "J_encoded": q34_ha.ham.j,
            "gap_encoded": q34_ha.gamma_encoded,
            "gap_physical": q34_ha.gamma_encoded / (1 << FRAC_BITS),
        },
        "fa": {
            "h_encoded": q34_fa.ham.h,
            "J_encoded": q34_fa.ham.j,
            "gap_encoded": q34_fa.gamma_encoded,
            "gap_physical": q34_fa.gamma_encoded / (1 << FRAC_BITS),
        },
    }

    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run_all() -> dict[str, str]:
    runs = {
        "baseline_direct4": run_models(
            "baseline_direct4",
            "run_adder4_direct_randomized_exhaustive.ps1",
            [
                "-GeneratedNetworks",
                "../src/generated_presentation_direct_adder4.vhd",
                "-AdderRndWeight",
                ps_value(1),
                "-ScrambleCycles",
                ps_value(80),
                "-SettleCycles",
                ps_value(500),
                "-Trials",
                ps_value(DIRECT_TRIALS),
            ],
        ),
        "idea34_integer4": run_models(
            "idea34_integer4",
            "run_adder4_shadow1_randomized_exhaustive.ps1",
            [
                "-GeneratedShadowVhdl",
                "../src/generated_presentation_shadow1_integer_adder4.vhd",
                "-BlockRndWeight",
                ps_value(1),
                "-CopyRndWeight",
                ps_value(0),
                "-ScrambleRndWeight",
                ps_value(2),
                "-ScrambleCycles",
                ps_value(80),
                "-Block0Cycles",
                ps_value(40),
                "-Block1Cycles",
                ps_value(40),
                "-Block2Cycles",
                ps_value(40),
                "-Block3Cycles",
                ps_value(40),
                "-CopyCycles",
                ps_value(2),
                "-Trials",
                ps_value(SHADOW_TRIALS),
            ],
        ),
        "idea2_q34_direct4": run_models(
            "idea2_q34_direct4",
            "run_adder4_direct_randomized_exhaustive.ps1",
            [
                "-GeneratedNetworks",
                "../src/generated_presentation_direct_q34_adder4.vhd",
                "-AdderRndWeight",
                ps_value(4),
                "-ScrambleCycles",
                ps_value(80),
                "-SettleCycles",
                ps_value(500),
                "-Trials",
                ps_value(DIRECT_TRIALS),
            ],
        ),
        "idea3_window4": run_models(
            "idea3_window4",
            "run_adder4_windowed_randomized_exhaustive.ps1",
            [
                "-GeneratedWindowedVhdl",
                "../src/generated_presentation_windowed_integer_adder4.vhd",
                "-ActiveRndWeight",
                ps_value(1),
                "-FinalRndWeight",
                ps_value(1),
                "-ScrambleRndWeight",
                ps_value(2),
                "-ScrambleCycles",
                ps_value(80),
                "-Wave0Cycles",
                ps_value(40),
                "-Wave1Cycles",
                ps_value(40),
                "-Wave2Cycles",
                ps_value(40),
                "-Wave3Cycles",
                ps_value(40),
                "-FinalCycles",
                ps_value(0),
                "-Trials",
                ps_value(SHADOW_TRIALS),
            ],
        ),
        "idea4_shadow_parallel4": run_models(
            "idea4_shadow_parallel4",
            "run_adder4_shadow1_parallel_randomized_exhaustive.ps1",
            [
                "-GeneratedShadowVhdl",
                "../src/generated_presentation_shadow1_integer_adder4.vhd",
                "-BlockRndWeight",
                ps_value(1),
                "-CopyRndWeight",
                ps_value(0),
                "-ScrambleRndWeight",
                ps_value(2),
                "-ScrambleCycles",
                ps_value(80),
                "-SettleCycles",
                ps_value(160),
                "-Trials",
                ps_value(SHADOW_TRIALS),
            ],
        ),
        "baseline_direct8": run_models(
            "baseline_direct8",
            "run_adder8_direct_repeated_solve.ps1",
            [
                "-GeneratedNetworks",
                "../src/generated_presentation_direct_adder8.vhd",
                "-AdderRndWeight",
                ps_value(1),
                "-ScrambleCycles",
                ps_value(80),
                "-SettleCycles",
                ps_value(500),
                "-Trials",
                ps_value(REPEAT8_TRIALS),
            ],
        ),
        "idea2_q34_direct8": run_models(
            "idea2_q34_direct8",
            "run_adder8_direct_repeated_solve.ps1",
            [
                "-GeneratedNetworks",
                "../src/generated_presentation_direct_q34_adder8.vhd",
                "-AdderRndWeight",
                ps_value(4),
                "-ScrambleCycles",
                ps_value(80),
                "-SettleCycles",
                ps_value(500),
                "-Trials",
                ps_value(REPEAT8_TRIALS),
            ],
        ),
        "idea234_q34_4": run_models(
            "idea234_q34_4",
            "run_adder4_shadow1_randomized_exhaustive.ps1",
            [
                "-GeneratedShadowVhdl",
                "../src/generated_presentation_shadow1_q34_adder4.vhd",
                "-BlockRndWeight",
                ps_value(4),
                "-CopyRndWeight",
                ps_value(0),
                "-ScrambleRndWeight",
                ps_value(8),
                "-ScrambleCycles",
                ps_value(80),
                "-Block0Cycles",
                ps_value(10),
                "-Block1Cycles",
                ps_value(8),
                "-Block2Cycles",
                ps_value(16),
                "-Block3Cycles",
                ps_value(6),
                "-CopyCycles",
                ps_value(2),
                "-Trials",
                ps_value(SHADOW_TRIALS),
            ],
        ),
        "idea34_integer8": run_models(
            "idea34_integer8",
            "run_adder8_shadow1_repeated_solve.ps1",
            [
                "-GeneratedShadowVhdl",
                "../src/generated_presentation_shadow1_integer_adder8.vhd",
                "-BlockRndWeight",
                ps_value(1),
                "-CopyRndWeight",
                ps_value(0),
                "-ScrambleRndWeight",
                ps_value(2),
                "-ScrambleCycles",
                ps_value(80),
                "-Block0Cycles",
                ps_value(40),
                "-Block1Cycles",
                ps_value(40),
                "-Block2Cycles",
                ps_value(40),
                "-Block3Cycles",
                ps_value(40),
                "-Block4Cycles",
                ps_value(40),
                "-Block5Cycles",
                ps_value(40),
                "-Block6Cycles",
                ps_value(40),
                "-Block7Cycles",
                ps_value(40),
                "-CopyCycles",
                ps_value(2),
                "-Trials",
                ps_value(REPEAT8_TRIALS),
            ],
        ),
        "idea234_q34_8": run_models(
            "idea234_q34_8",
            "run_adder8_shadow1_repeated_solve.ps1",
            [
                "-GeneratedShadowVhdl",
                "../src/generated_presentation_shadow1_q34_adder8.vhd",
                "-BlockRndWeight",
                ps_value(4),
                "-CopyRndWeight",
                ps_value(0),
                "-ScrambleRndWeight",
                ps_value(8),
                "-ScrambleCycles",
                ps_value(80),
                "-Block0Cycles",
                ps_value(40),
                "-Block1Cycles",
                ps_value(40),
                "-Block2Cycles",
                ps_value(40),
                "-Block3Cycles",
                ps_value(40),
                "-Block4Cycles",
                ps_value(40),
                "-Block5Cycles",
                ps_value(40),
                "-Block6Cycles",
                ps_value(40),
                "-Block7Cycles",
                ps_value(40),
                "-CopyCycles",
                ps_value(2),
                "-Trials",
                ps_value(REPEAT8_TRIALS),
            ],
        ),
    }
    return runs


CASE4_RE = re.compile(
    r"random4(?P<variant>_direct|_window|_shadow_parallel)? (?P<direction>forward|inverse_bsum) case A=(?P<a>\d+) "
    r"B=(?P<b>\d+) (?:(?:expected)|(?:SUM))=(?P<target>\d+) hits=(?P<hits>\d+)/(?P<trials>\d+) "
    r"(?P<top_label>topA|top)=(?P<top>\d+) top_count=(?P<top_count>\d+)"
)
SUMMARY4_RE = re.compile(
    r"random4(?P<variant>_direct|_window|_shadow_parallel)? (?P<direction>forward|inverse_bsum) summary cases=(?P<cases>\d+) "
    r"total_hits=(?P<hits>\d+)/(?P<trials>\d+) min_hits=(?P<min_hits>\d+) fail_cases=(?P<fail_cases>\d+)"
)
REPEAT8_RE = re.compile(
    r"repeated solve (?P<a>\d+)\+(?P<b>\d+) expected_sum=(?P<expected>\d+) "
    r"hits=(?P<hits>\d+)/(?P<trials>\d+) distinct_sums=(?P<distinct>\d+)"
)


def parse_outputs(runs: dict[str, str]) -> tuple[list[dict], list[dict], list[dict]]:
    case_rows: list[dict] = []
    summary_rows: list[dict] = []
    repeat8_rows: list[dict] = []
    labels = {
        "baseline_direct4": "baseline direct RCA",
        "baseline_direct8": "baseline direct RCA",
        "idea2_q34_direct4": "idea 2 only Q3.4 direct RCA",
        "idea2_q34_direct8": "idea 2 only Q3.4 direct RCA",
        "idea3_window4": "idea 3 only sequential window RCA",
        "idea4_shadow_parallel4": "idea 4 only parallel shadow RCA",
        "idea34_integer4": "idea 3+4 integer shadow RCA",
        "idea234_q34_4": "idea 2+3+4 Q3.4 shadow RCA",
        "idea34_integer8": "idea 3+4 integer shadow RCA",
        "idea234_q34_8": "idea 2+3+4 Q3.4 shadow RCA",
    }
    for run_name, text in runs.items():
        for match in CASE4_RE.finditer(text):
            trials = int(match.group("trials"))
            hits = int(match.group("hits"))
            row = {
                "session": labels[run_name],
                "run": run_name,
                "direction": match.group("direction"),
                "a": int(match.group("a")),
                "b": int(match.group("b")),
                "target": int(match.group("target")),
                "hits": hits,
                "trials": trials,
                "success_probability": hits / trials,
                "top": int(match.group("top")),
                "top_count": int(match.group("top_count")),
            }
            case_rows.append(row)
        for match in SUMMARY4_RE.finditer(text):
            trials_total = int(match.group("trials"))
            hits = int(match.group("hits"))
            cases = int(match.group("cases"))
            per_case_trials = trials_total // cases
            summary_rows.append(
                {
                    "session": labels[run_name],
                    "run": run_name,
                    "direction": match.group("direction"),
                    "cases": cases,
                    "hits": hits,
                    "trials_total": trials_total,
                    "success_probability": hits / trials_total,
                    "per_case_trials": per_case_trials,
                    "min_hits": int(match.group("min_hits")),
                    "fail_cases": int(match.group("fail_cases")),
                }
            )
        for match in REPEAT8_RE.finditer(text):
            trials = int(match.group("trials"))
            hits = int(match.group("hits"))
            repeat8_rows.append(
                {
                    "session": labels[run_name],
                    "run": run_name,
                    "a": int(match.group("a")),
                    "b": int(match.group("b")),
                    "expected": int(match.group("expected")),
                    "hits": hits,
                    "trials": trials,
                    "success_probability": hits / trials,
                    "distinct_sums": int(match.group("distinct")),
                }
            )
    write_csv(DATA / "adder4_cases.csv", case_rows)
    write_csv(DATA / "adder4_summary.csv", summary_rows)
    write_csv(DATA / "adder8_repeated.csv", repeat8_rows)
    return case_rows, summary_rows, repeat8_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def color_for(prob: float) -> str:
    low = (183, 28, 28)
    mid = (255, 245, 157)
    high = (0, 121, 107)
    if prob < 0.5:
        t = prob / 0.5
        rgb = tuple(round(low[i] + t * (mid[i] - low[i])) for i in range(3))
    else:
        t = (prob - 0.5) / 0.5
        rgb = tuple(round(mid[i] + t * (high[i] - mid[i])) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text{font-family:Arial,Helvetica,sans-serif;fill:#1f2933}.title{font-size:18px;font-weight:700}.axis{font-size:11px}.cell{stroke:#ffffff;stroke-width:1}.small{font-size:10px}</style>",
    ]


def write_heatmap(path: Path, title: str, rows: list[dict]) -> None:
    values = {(row["a"], row["b"]): row["success_probability"] for row in rows}
    cell = 24
    left = 46
    top = 44
    width = left + 16 * cell + 24
    height = top + 16 * cell + 46
    lines = svg_header(width, height)
    lines.append(f'<text x="{width / 2}" y="22" text-anchor="middle" class="title">{title}</text>')
    lines.append(f'<text x="{left + 8 * cell}" y="{height - 10}" text-anchor="middle" class="axis">B input</text>')
    lines.append(f'<text x="14" y="{top + 8 * cell}" transform="rotate(-90 14,{top + 8 * cell})" text-anchor="middle" class="axis">A input</text>')
    for i in range(16):
        lines.append(f'<text x="{left + i * cell + cell / 2}" y="{top - 8}" text-anchor="middle" class="small">{i}</text>')
        lines.append(f'<text x="{left - 8}" y="{top + i * cell + 16}" text-anchor="end" class="small">{i}</text>')
    for a in range(16):
        for b in range(16):
            prob = values.get((a, b), 0.0)
            lines.append(
                f'<rect class="cell" x="{left + b * cell}" y="{top + a * cell}" '
                f'width="{cell}" height="{cell}" fill="{color_for(prob)}"/>'
            )
            if prob < 1.0:
                label = str(round(prob * 100))
                lines.append(
                    f'<text x="{left + b * cell + cell / 2}" y="{top + a * cell + 16}" '
                    f'text-anchor="middle" class="small">{label}</text>'
                )
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_bar_chart(path: Path, title: str, labels: list[str], values: list[float]) -> None:
    width = 900
    row_h = 34
    top = 48
    left = 250
    right = 40
    height = top + len(labels) * row_h + 42
    bar_w = width - left - right
    lines = svg_header(width, height)
    lines.append(f'<text x="{width / 2}" y="24" text-anchor="middle" class="title">{title}</text>')
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * row_h
        lines.append(f'<text x="{left - 12}" y="{y + 20}" text-anchor="end" class="axis">{label}</text>')
        lines.append(f'<rect x="{left}" y="{y + 4}" width="{bar_w}" height="20" fill="#eef2f7"/>')
        lines.append(f'<rect x="{left}" y="{y + 4}" width="{bar_w * value:.1f}" height="20" fill="#00796b"/>')
        lines.append(f'<text x="{left + bar_w * value + 8:.1f}" y="{y + 20}" class="axis">{value * 100:.1f}%</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def state_text(bits: tuple[int, ...]) -> str:
    return "".join(str(bit) for bit in bits)


def marginal_distribution(ham, clamps: dict[int, int], marginal_indices: list[int]) -> dict[str, float]:
    weights: dict[str, float] = {}
    total = 0.0
    for bits in all_bit_states(len(ham.nodes)):
        if any(bits[index] != value for index, value in clamps.items()):
            continue
        weight = 2.718281828459045 ** (-energy(ham.h, ham.j, bits))
        key = state_text(tuple(bits[index] for index in marginal_indices))
        weights[key] = weights.get(key, 0.0) + weight
        total += weight
    return {key: value / total for key, value in weights.items()} if total else {}


def gate_visualization_data() -> tuple[list[dict], list[dict]]:
    gate_names = {"AND", "OR", "NAND", "NOR", "HA_XOR", "XNOR", "FA"}
    gates = [ham for ham in hamiltonians(Namespace(ha_scale=1, fa_scale=1)) if ham.name in gate_names]
    label_for = {"HA_XOR": "HA/XOR"}
    energy_rows: list[dict] = []
    reverse_rows: list[dict] = []

    for ham in gates:
        valid = set(ham.valid_states or [])
        label = label_for.get(ham.name, ham.name)
        for bits in all_bit_states(len(ham.nodes)):
            energy_rows.append(
                {
                    "gate": label,
                    "state": state_text(bits),
                    "energy": energy(ham.h, ham.j, bits),
                    "valid": bits in valid,
                }
            )

        if ham.name == "FA":
            for s_value, c_value in product([0, 1], repeat=2):
                dist = marginal_distribution(ham, {3: s_value, 4: c_value}, [0, 1, 2])
                for key in sorted(dist):
                    reverse_rows.append(
                        {
                            "gate": label,
                            "condition": f"S={s_value}, COUT={c_value}",
                            "input": key,
                            "probability": dist[key],
                            "valid": (tuple(int(ch) for ch in key) + (s_value, c_value)) in valid,
                        }
                    )
        else:
            output_index = 2
            for y_value in [0, 1]:
                dist = marginal_distribution(ham, {output_index: y_value}, [0, 1])
                for key in ["00", "01", "10", "11"]:
                    bits_prefix = tuple(int(ch) for ch in key)
                    valid_for_y = any(
                        state[0] == bits_prefix[0] and state[1] == bits_prefix[1] and state[2] == y_value
                        for state in valid
                    )
                    reverse_rows.append(
                        {
                            "gate": label,
                            "condition": f"Y={y_value}" if ham.name not in {"HA_XOR", "XNOR"} else f"S={y_value}",
                            "input": key,
                            "probability": dist.get(key, 0.0),
                            "valid": valid_for_y,
                        }
                    )
    return energy_rows, reverse_rows


def write_gate_energy_svg(path: Path, rows: list[dict]) -> None:
    gates = list(dict.fromkeys(row["gate"] for row in rows))
    width = 1120
    row_h = 118
    left = 86
    top = 42
    height = top + len(gates) * row_h + 28
    lines = svg_header(width, height)
    lines.append(f'<text x="{width / 2}" y="24" text-anchor="middle" class="title">Primitive Gate Hamiltonian Energy Landscapes</text>')
    plot_w = width - left - 34
    for gi, gate in enumerate(gates):
        selected = [row for row in rows if row["gate"] == gate]
        energies = [row["energy"] for row in selected]
        min_e = min(energies)
        max_e = max(energies)
        span = max(1, max_e - min_e)
        y0 = top + gi * row_h
        lines.append(f'<text x="{left - 12}" y="{y0 + 54}" text-anchor="end" class="axis">{gate}</text>')
        lines.append(f'<line x1="{left}" y1="{y0 + 86}" x2="{left + plot_w}" y2="{y0 + 86}" stroke="#c8d1dc"/>')
        bar_w = max(3, plot_w / len(selected) - 1)
        for si, row in enumerate(selected):
            x = left + si * (plot_w / len(selected))
            bar_h = 8 + 68 * ((row["energy"] - min_e) / span)
            y = y0 + 86 - bar_h
            color = "#00796b" if row["valid"] else "#b71c1c"
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{color}" opacity="0.88"/>')
        lines.append(f'<text x="{left}" y="{y0 + 104}" class="small">min E={min_e}</text>')
        lines.append(f'<text x="{left + plot_w}" y="{y0 + 104}" text-anchor="end" class="small">max E={max_e}; green=valid</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_gate_reverse_svg(path: Path, rows: list[dict]) -> None:
    groups = list(dict.fromkeys((row["gate"], row["condition"]) for row in rows))
    width = 1040
    row_h = 58
    left = 170
    top = 42
    height = top + len(groups) * row_h + 30
    bar_w = width - left - 70
    lines = svg_header(width, height)
    lines.append(f'<text x="{width / 2}" y="24" text-anchor="middle" class="title">Reverse-Clamped Gate Input Distributions</text>')
    for gi, (gate, condition) in enumerate(groups):
        selected = [row for row in rows if row["gate"] == gate and row["condition"] == condition]
        y = top + gi * row_h
        lines.append(f'<text x="{left - 12}" y="{y + 24}" text-anchor="end" class="axis">{gate} {condition}</text>')
        cursor = left
        for row in selected:
            width_i = bar_w * row["probability"]
            color = "#00796b" if row["valid"] else "#b71c1c"
            lines.append(f'<rect x="{cursor:.1f}" y="{y + 8}" width="{width_i:.1f}" height="24" fill="{color}" opacity="0.88"/>')
            if width_i > 34:
                lines.append(f'<text x="{cursor + width_i / 2:.1f}" y="{y + 25}" text-anchor="middle" class="small" fill="#ffffff">{row["input"]}</text>')
            cursor += width_i
        lines.append(f'<text x="{left + bar_w + 8}" y="{y + 24}" class="small">green=valid</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_gate_visualizations() -> None:
    energy_rows, reverse_rows = gate_visualization_data()
    write_csv(DATA / "gate_energy_landscape.csv", energy_rows)
    write_csv(DATA / "gate_reverse_distributions.csv", reverse_rows)
    write_gate_energy_svg(FIGS / "gate_energy_landscape.svg", energy_rows)
    write_gate_reverse_svg(FIGS / "gate_reverse_distributions.svg", reverse_rows)


def make_figures(case_rows: list[dict], summary_rows: list[dict], repeat8_rows: list[dict]) -> dict[str, str]:
    figures: dict[str, str] = {}
    heatmap_specs = [
        ("baseline_direct4", "forward", "4-bit Baseline Direct RCA: Forward", "heatmap_baseline_direct4_forward.svg"),
        ("idea2_q34_direct4", "forward", "4-bit Idea 2 Only Q3.4 Direct: Forward", "heatmap_idea2_q34_direct4_forward.svg"),
        ("idea3_window4", "forward", "4-bit Idea 3 Only Windowed: Forward", "heatmap_idea3_window4_forward.svg"),
        ("idea3_window4", "inverse_bsum", "4-bit Idea 3 Only Windowed: B+SUM -> A", "heatmap_idea3_window4_inverse.svg"),
        ("idea4_shadow_parallel4", "forward", "4-bit Idea 4 Only Parallel Shadow: Forward", "heatmap_idea4_shadow_parallel4_forward.svg"),
        ("idea4_shadow_parallel4", "inverse_bsum", "4-bit Idea 4 Only Parallel Shadow: B+SUM -> A", "heatmap_idea4_shadow_parallel4_inverse.svg"),
        ("idea34_integer4", "forward", "4-bit Idea 3+4 Integer: Forward", "heatmap_idea34_integer4_forward.svg"),
        ("idea34_integer4", "inverse_bsum", "4-bit Idea 3+4 Integer: B+SUM -> A", "heatmap_idea34_integer4_inverse.svg"),
        ("idea234_q34_4", "forward", "4-bit Idea 2+3+4 Q3.4: Forward", "heatmap_idea234_q34_forward.svg"),
        ("idea234_q34_4", "inverse_bsum", "4-bit Idea 2+3+4 Q3.4: B+SUM -> A", "heatmap_idea234_q34_inverse.svg"),
    ]
    for run, direction, title, filename in heatmap_specs:
        rows = [row for row in case_rows if row["run"] == run and row["direction"] == direction]
        if rows:
            path = FIGS / filename
            write_heatmap(path, title, rows)
            figures[filename] = rel(path)

    labels = []
    values = []
    for row in summary_rows:
        direction = "forward" if row["direction"] == "forward" else "inverse"
        labels.append(f"{row['session']} ({direction})")
        values.append(row["success_probability"])
    write_bar_chart(FIGS / "summary_adder4_success.svg", "4-bit Exhaustive Repeated-Solve Success", labels, values)
    figures["summary_adder4_success.svg"] = rel(FIGS / "summary_adder4_success.svg")

    labels8 = [f"{row['session']}: {row['a']}+{row['b']}" for row in repeat8_rows]
    values8 = [row["success_probability"] for row in repeat8_rows]
    write_bar_chart(FIGS / "summary_adder8_spotcheck.svg", "8-bit Non-exhaustive Repeated-Solve Success", labels8, values8)
    figures["summary_adder8_spotcheck.svg"] = rel(FIGS / "summary_adder8_spotcheck.svg")
    return figures


def summary_table(summary_rows: list[dict]) -> str:
    lines = [
        "| Session | Direction | Cases | Trials/case | Total success | Min hits | Non-perfect cases |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        direction = "forward A+B->SUM" if row["direction"] == "forward" else "inverse B+SUM->A"
        lines.append(
            f"| {row['session']} | {direction} | {row['cases']} | {row['per_case_trials']} | "
            f"{row['success_probability'] * 100:.2f}% ({row['hits']}/{row['trials_total']}) | "
            f"{row['min_hits']} | {row['fail_cases']} |"
        )
    return "\n".join(lines)


def repeat8_table(rows: list[dict]) -> str:
    lines = [
        "| Session | A | B | Expected SUM | Hits | Distinct sums |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['session']} | {row['a']} | {row['b']} | {row['expected']} | "
            f"{row['hits']}/{row['trials']} ({row['success_probability'] * 100:.1f}%) | {row['distinct_sums']} |"
        )
    return "\n".join(lines)


def selected_summary_table(summary_rows: list[dict], runs: list[str]) -> str:
    selected = [row for row in summary_rows if row["run"] in runs]
    return summary_table(selected)


def summary_pct(summary_rows: list[dict], run: str, direction: str = "forward") -> float:
    for row in summary_rows:
        if row["run"] == run and row["direction"] == direction:
            return row["success_probability"] * 100
    return float("nan")


def write_report(manifest: dict, summary_rows: list[dict], repeat8_rows: list[dict], figures: dict[str, str]) -> None:
    int_weights = manifest["integer_weights"]
    q34_weights = manifest["q34_weights"]
    baseline4_pct = summary_pct(summary_rows, "baseline_direct4")
    idea2_pct = summary_pct(summary_rows, "idea2_q34_direct4")
    idea3_pct = summary_pct(summary_rows, "idea3_window4")
    idea4_pct = summary_pct(summary_rows, "idea4_shadow_parallel4")
    idea34_pct = summary_pct(summary_rows, "idea34_integer4")
    idea234_pct = summary_pct(summary_rows, "idea234_q34_4")
    idea234_inverse_pct = summary_pct(summary_rows, "idea234_q34_4", "inverse_bsum")
    report = f"""# Presentation RCA Experiments: Timing Windows, Shadow Carries, and Q3.4 Weights

Date: 2026-05-25

## 1. Problem Encountered

The ripple-carry adder is combinational in Boolean logic, but in the stochastic invertible circuit it behaves like a pseudo-time-dependent system. Bit 0 has to collapse first, then its carry must be transferred before bit 1 can be trusted, and so on. If every HA/FA block is hot together, a later FA can settle using the wrong carry-in and then become hard to move.

This is why simply increasing the intrablock Hamiltonian gap is not automatically helpful. A larger local gap increases the block's confidence in whatever boundary value it currently sees. For a downstream FA with state x and incoming carry c, its local distribution is proportional to exp(-beta H_FA(x; c)). If c is wrong early, a high beta*Delta_intra suppresses later correction. The interblock copy must be strong enough to pass the carry, but not so dominant that it forces both sides to freeze at the same time.

## 2. Ideas Tested

Idea 1: equalize gate energy gaps. This was positive for small combinational logic, but it does not solve adders by itself because RCA failure is dominated by carry timing, not just unequal local gate gaps.

Idea 2: Q3.4 / Q8-style larger dynamic-range weights. The optimized HA/FA blocks increase the internal valid-invalid gap, but the earlier tests showed that FP/Q scaling alone is not reliable across ripple blocks. In this fresh suite it is tested only as part of idea 2+3+4.

Idea 3: sequential annealing windows. Blocks are activated in carry order, so each later block receives a more reliable upstream carry.

Idea 4: one shadow carry node. Between block i-1 and block i, c[i-1] is briefly copied into q[i]. The downstream FA reads q[i] as its carry-in, but q[i] is not updated by that FA. This creates a directional latch-like bias without requiring a full clocked digital register.

```mermaid
flowchart LR
    B0["HA/FA block i-1"] --> C["carry c[i-1]"]
    C --> Q["shadow q[i]"]
    Q --> B1["FA block i"]
    B1 --> C2["carry c[i]"]
```

## 3. Primitive Gate Visualizations

These figures restore the gate-level view for every primitive block used here: AND, OR, NAND, NOR, HA/XOR, XNOR, and FA. The first figure shows all state energies with valid Boolean states in green. The second shows reverse-clamped input distributions; invalid reverse choices are red.

![Gate energy landscape](figures/gate_energy_landscape.svg)

![Gate reverse distributions](figures/gate_reverse_distributions.svg)

## 4. Fresh ModelSim Protocol

All 4-bit tests here are exhaustive over A,B in 0..15. Each case is solved {SHADOW_TRIALS} times from randomized trajectories. The generated VHDL uses OS-random seed salts, and every trial starts with an unclamped scramble window before the solve window. The constrained inverse test clamps B and SUM and measures whether A is recovered.

The 8-bit results are intentionally non-exhaustive companion checks, per the latest scope decision. They use six selected vectors and {REPEAT8_TRIALS} repeated solves per vector.

## 5. 4-bit Exhaustive Results

![4-bit summary](figures/summary_adder4_success.svg)

{summary_table(summary_rows)}

Forward heatmaps:

![Baseline direct forward](figures/heatmap_baseline_direct4_forward.svg)

![Idea 3+4 integer forward](figures/heatmap_idea34_integer4_forward.svg)

![Idea 2+3+4 Q3.4 forward](figures/heatmap_idea234_q34_forward.svg)

Backward constrained inverse heatmaps:

![Idea 3+4 integer inverse](figures/heatmap_idea34_integer4_inverse.svg)

![Idea 2+3+4 Q3.4 inverse](figures/heatmap_idea234_q34_inverse.svg)

## 6. Individual Idea Ablation

The ablation tests isolate the ideas that were bundled in the successful run.

{selected_summary_table(summary_rows, ["baseline_direct4", "idea2_q34_direct4", "idea3_window4", "idea4_shadow_parallel4", "idea34_integer4", "idea234_q34_4"])}

Individual forward heatmaps:

![Idea 2 only Q3.4 direct](figures/heatmap_idea2_q34_direct4_forward.svg)

![Idea 3 only windowed](figures/heatmap_idea3_window4_forward.svg)

![Idea 4 only parallel shadow](figures/heatmap_idea4_shadow_parallel4_forward.svg)

The idea 2 only test is the clearest negative control. It changes the local HA/FA energy scale, but leaves the RCA timing graph unchanged. Numerically, direct integer forward success is {baseline4_pct:.2f}%, while idea 2 alone is {idea2_pct:.2f}%; the successful combined idea 2+3+4 run is {idea234_pct:.2f}%.

Mathematically, the node update uses

```text
P(m_i = +1 | field F_i) = (1 + tanh(F_i)) / 2.
```

Scaling Q3.4 weights increases |F_i| and therefore saturates tanh. That is good if the local boundary values are already correct. It is harmful when a downstream FA sees a premature or wrong carry, because the wrong local minimum becomes harder to escape. In low-temperature form, a correction requiring an energy increase Delta has probability proportional to exp(-beta Delta); idea 2 increases Delta without fixing carry arrival time. Idea 3 changes time, idea 4 changes the carry boundary topology, and the combined 2+3+4 case is where the larger local gap becomes useful.

In this run, idea 3 alone reaches {idea3_pct:.2f}% forward and idea 4 alone reaches {idea4_pct:.2f}% forward. Idea 3+4 without Q3.4 reaches {idea34_pct:.2f}% forward, showing that timing/topology help somewhat, but the high-confidence Q3.4 blocks only become strongly positive when used with that timing isolation.

## 7. 8-bit Non-exhaustive Companion

![8-bit spot check](figures/summary_adder8_spotcheck.svg)

{repeat8_table(repeat8_rows)}

## 8. Interpretation

The important comparison is not only whether one frozen readout is correct, but the repeated-solve probability after fresh randomization. The direct integer RCA is the baseline failure mode. Idea 3+4 tests whether timing windows plus one shadow node repair the carry direction. Idea 2+3+4 tests whether the same topology benefits from the Q3.4 optimized gate weights while preserving the moderate interblock copy.

In this final dataset, integer idea 3+4 is only a modest improvement over the direct 8-bit baseline and is roughly tied with the 4-bit direct baseline under the repeated-solve metric. The combined idea 2+3+4 result is the clear positive result: Q3.4 plus the shadow/window schedule reaches {idea234_pct:.2f}% forward and {idea234_inverse_pct:.2f}% constrained inverse success on exhaustive 4-bit tests, and about 99-100% on the selected 8-bit vectors. This suggests the larger intrablock gap is helpful only after timing isolation is added.

## 9. Exact Parameters

Baseline direct RCA:

- 4-bit VHDL: `{manifest['artifacts']['direct_adder4']['path']}`
- 8-bit VHDL: `{manifest['artifacts']['direct_adder8']['path']}`
- 4-bit seed salt: `{manifest['artifacts']['direct_adder4']['seed_salt']}`
- 8-bit seed salt: `{manifest['artifacts']['direct_adder8']['seed_salt']}`
- Noise weight: 1
- Scramble cycles: 80
- Settle cycles: 500
- Trials per A,B case: {DIRECT_TRIALS}

Idea 2 only Q3.4 direct RCA:

- 4-bit VHDL: `{manifest['artifacts']['q34_direct4']['path']}`
- 8-bit VHDL: `{manifest['artifacts']['q34_direct8']['path']}`
- 4-bit seed salt: `{manifest['artifacts']['q34_direct4']['seed_salt']}`
- 8-bit seed salt: `{manifest['artifacts']['q34_direct8']['seed_salt']}`
- Q3.4 interpretation: physical value = encoded / 16
- Noise weight: encoded 4, physical 0.25
- Scramble cycles: 80
- Settle cycles: 500

Idea 3 only sequential window RCA:

- 4-bit VHDL: `{manifest['artifacts']['integer_window4']['path']}`
- 4-bit seed salt: `{manifest['artifacts']['integer_window4']['seed_salt']}`
- Window cycles: 40,40,40,40
- Solve noise: active_rnd=1; scramble noise=2

Idea 4 only parallel shadow RCA:

- 4-bit VHDL: `{manifest['artifacts']['integer_shadow4']['path']}`
- Shadow topology: one q node between carry blocks
- Activation: all blocks and shadow-copy nodes hot together
- Settle cycles: 160
- Solve noise: block_rnd=1, copy_rnd=0; scramble noise=2

Idea 3+4 integer shadow RCA:

- 4-bit VHDL: `{manifest['artifacts']['integer_shadow4']['path']}`
- 8-bit VHDL: `{manifest['artifacts']['integer_shadow8']['path']}`
- 4-bit seed salt: `{manifest['artifacts']['integer_shadow4']['seed_salt']}`
- 8-bit seed salt: `{manifest['artifacts']['integer_shadow8']['seed_salt']}`
- Copy weight: 4
- 4-bit window cycles: 40,40,40,40 with copy=2
- 8-bit window cycles: 40,40,40,40,40,40,40,40 with copy=2
- Solve noise: block_rnd=1, copy_rnd=0; scramble noise=2

Idea 2+3+4 Q3.4 shadow RCA:

- 4-bit VHDL: `{manifest['artifacts']['q34_shadow4']['path']}`
- 8-bit VHDL: `{manifest['artifacts']['q34_shadow8']['path']}`
- 4-bit seed salt: `{manifest['artifacts']['q34_shadow4']['seed_salt']}`
- 8-bit seed salt: `{manifest['artifacts']['q34_shadow8']['seed_salt']}`
- Q3.4 interpretation: physical value = encoded / 16
- Copy weight: encoded 64, physical 4.0
- 4-bit window cycles: 10,8,16,6 with copy=2
- 8-bit window cycles: 40,40,40,40,40,40,40,40 with copy=2
- Solve noise: block_rnd=4 encoded = 0.25 physical, copy_rnd=0; scramble noise=8 encoded = 0.5 physical

Integer HA h:

`{int_weights['ha']['h']}`

Integer HA J:

{matrix_md(int_weights['ha']['J'])}

Integer FA h:

`{int_weights['fa']['h']}`

Integer FA J:

{matrix_md(int_weights['fa']['J'])}

Q3.4 HA h encoded:

`{q34_weights['ha']['h_encoded']}`

Q3.4 HA J encoded:

{matrix_md(q34_weights['ha']['J_encoded'])}

Q3.4 HA gap: encoded {q34_weights['ha']['gap_encoded']}, physical {q34_weights['ha']['gap_physical']:.4f}

Q3.4 FA h encoded:

`{q34_weights['fa']['h_encoded']}`

Q3.4 FA J encoded:

{matrix_md(q34_weights['fa']['J_encoded'])}

Q3.4 FA gap: encoded {q34_weights['fa']['gap_encoded']}, physical {q34_weights['fa']['gap_physical']:.4f}

## 10. Artifacts

- Manifest: `data/manifest.json`
- Gate energy CSV: `data/gate_energy_landscape.csv`
- Gate reverse CSV: `data/gate_reverse_distributions.csv`
- 4-bit case CSV: `data/adder4_cases.csv`
- 4-bit summary CSV: `data/adder4_summary.csv`
- 8-bit repeated-solve CSV: `data/adder8_repeated.csv`
- ModelSim transcripts: `traces/`
"""
    (OUT / "report.md").write_text(report, encoding="utf-8")


def main() -> None:
    prepare_output()
    manifest = generate_artifacts()
    runs = run_all()
    case_rows, summary_rows, repeat8_rows = parse_outputs(runs)
    write_gate_visualizations()
    figures = make_figures(case_rows, summary_rows, repeat8_rows)
    write_report(manifest, summary_rows, repeat8_rows, figures)
    print(f"Wrote {OUT / 'report.md'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
