import csv
import json
import math
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
SUM_TRIALS = 1000
SUMMARY_RUN_ORDER = [
    "baseline_direct4",
    "idea34_integer4",
    "idea2_q34_direct4",
    "idea3_window4",
    "idea4_shadow_parallel4",
    "idea234_q34_4",
]
REPEAT8_RUN_ORDER = [
    "baseline_direct8",
    "idea2_q34_direct8",
    "idea34_integer8",
    "idea234_q34_8",
]
SUM_RUN_ORDER = [
    "sum_baseline_direct4",
    "sum_idea34_integer4",
    "sum_idea234_q34_4",
    "sum_idea234_q34_reverse40_4",
    "sum_idea4_parallel4",
    "sum_idea24_q34_parallel4",
]
WINDOW_SWEEP_CONFIGS = [
    ("w1_1_2_1", 1, 1, 2, 1),
    ("w1_1_3_1", 1, 1, 3, 1),
    ("w1_2_3_1", 1, 2, 3, 1),
    ("w2_1_3_1", 2, 1, 3, 1),
    ("w2_2_3_1", 2, 2, 3, 1),
    ("w2_2_4_2", 2, 2, 4, 2),
    ("w3_3_5_2", 3, 3, 5, 2),
    ("w4_3_6_3", 4, 3, 6, 3),
    ("w4_4_4_4", 4, 4, 4, 4),
    ("w5_5_5_5", 5, 5, 5, 5),
    ("w5_4_8_3", 5, 4, 8, 3),
    ("w6_5_10_4", 6, 5, 10, 4),
    ("w8_6_12_5", 8, 6, 12, 5),
    ("w10_8_16_6", 10, 8, 16, 6),
    ("w40_40_40_40", 40, 40, 40, 40),
]


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
        "sum_baseline_direct4": run_models(
            "sum_baseline_direct4",
            "run_adder4_direct_sum_randomized_distribution.ps1",
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
                ps_value(SUM_TRIALS),
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
        "sum_idea34_integer4": run_models(
            "sum_idea34_integer4",
            "run_adder4_shadow1_sum_randomized_distribution.ps1",
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
                ps_value(SUM_TRIALS),
            ],
        ),
        "sum_idea4_parallel4": run_models(
            "sum_idea4_parallel4",
            "run_adder4_shadow1_sum_randomized_distribution.ps1",
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
                ps_value(SUM_TRIALS),
                "-ParallelMode",
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
        "sum_idea234_q34_4": run_models(
            "sum_idea234_q34_4",
            "run_adder4_shadow1_sum_randomized_distribution.ps1",
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
                ps_value(SUM_TRIALS),
            ],
        ),
        "sum_idea234_q34_reverse40_4": run_models(
            "sum_idea234_q34_reverse40_4",
            "run_adder4_shadow1_sum_randomized_distribution.ps1",
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
                ps_value(SUM_TRIALS),
                "-ReverseOrder",
            ],
        ),
        "sum_idea24_q34_parallel4": run_models(
            "sum_idea24_q34_parallel4",
            "run_adder4_shadow1_sum_randomized_distribution.ps1",
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
                "-SettleCycles",
                ps_value(160),
                "-Trials",
                ps_value(SUM_TRIALS),
                "-ParallelMode",
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
    for run_label, block0, block1, block2, block3 in WINDOW_SWEEP_CONFIGS:
        runs[f"sweep_idea234_{run_label}"] = run_models(
            f"sweep_idea234_{run_label}",
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
                ps_value(block0),
                "-Block1Cycles",
                ps_value(block1),
                "-Block2Cycles",
                ps_value(block2),
                "-Block3Cycles",
                ps_value(block3),
                "-CopyCycles",
                ps_value(2),
                "-Trials",
                ps_value(SHADOW_TRIALS),
                "-ForwardOnly",
            ],
        )
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
SUM_RANDOM_SUMMARY_RE = re.compile(
    r"sumdist_random summary SUM=(?P<sum>\d+) valid_total=(?P<valid>\d+) "
    r"invalid_total=(?P<invalid>\d+) coverage=(?P<coverage>\d+) trials=(?P<trials>\d+) "
    r"parallel=(?P<parallel>\w+) reverse=(?P<reverse>\w+) block_rnd=(?P<block_rnd>\d+) "
    r"copy_rnd=(?P<copy_rnd>\d+) scramble_rnd=(?P<scramble_rnd>\d+) "
    r"blocks=(?P<blocks>[0-9,]+) copy=(?P<copy>\d+) settle=(?P<settle>\d+)"
)
SUM_RANDOM_VALID_RE = re.compile(
    r"sumdist_random valid SUM=(?P<sum>\d+) A=(?P<a>\d+) B=(?P<b>\d+) "
    r"count=(?P<count>\d+) trials=(?P<trials>\d+)"
)


def valid_pair_count_for_sum(target_sum: int) -> int:
    return sum(1 for a in range(16) for b in range(16) if a + b == target_sum)


def valid_distribution_metrics(counts: list[int], valid_pair_count: int) -> tuple[float, float]:
    total = sum(counts)
    if total == 0:
        return 0.0, 1.0
    if valid_pair_count <= 1:
        entropy_norm = 1.0
    else:
        entropy = 0.0
        for count in counts:
            if count:
                p = count / total
                entropy -= p * math.log(p)
        entropy_norm = entropy / math.log(valid_pair_count)
    uniform = 1 / valid_pair_count
    tv = 0.5 * sum(abs((count / total) - uniform) for count in counts)
    return entropy_norm, tv


def parse_outputs(runs: dict[str, str]) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict]]:
    case_rows: list[dict] = []
    summary_rows: list[dict] = []
    repeat8_rows: list[dict] = []
    sum_summary_raw: list[dict] = []
    sum_pair_rows: list[dict] = []
    window_sweep_rows: list[dict] = []
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
        "sum_baseline_direct4": "baseline direct integer RCA",
        "sum_idea34_integer4": "idea 3+4 integer shadow/window",
        "sum_idea234_q34_4": "idea 2+3+4 Q3.4 shadow/window",
        "sum_idea234_q34_reverse40_4": "idea 2+3+4 Q3.4 reverse-order shadow/window",
        "sum_idea4_parallel4": "idea 4 only parallel shadow",
        "sum_idea24_q34_parallel4": "idea 2+4 Q3.4 parallel shadow",
    }
    for run_name, text in runs.items():
        if run_name.startswith("sweep_idea234_"):
            sweep_name = run_name.removeprefix("sweep_idea234_")
            blocks = next((cfg[1:] for cfg in WINDOW_SWEEP_CONFIGS if cfg[0] == sweep_name), None)
            if blocks is None:
                continue
            for match in SUMMARY4_RE.finditer(text):
                if match.group("direction") != "forward":
                    continue
                trials_total = int(match.group("trials"))
                hits = int(match.group("hits"))
                copy_cycles = 2
                window_sweep_rows.append(
                    {
                        "run": sweep_name,
                        "block0": blocks[0],
                        "block1": blocks[1],
                        "block2": blocks[2],
                        "block3": blocks[3],
                        "copy_cycles": copy_cycles,
                        "solve_cycles": sum(blocks) + 3 * copy_cycles,
                        "trials_total": trials_total,
                        "hits": hits,
                        "success_rate": hits / trials_total,
                        "above_baseline": False,
                        "min_hits": int(match.group("min_hits")),
                        "fail_cases": int(match.group("fail_cases")),
                    }
                )
            continue
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
        for match in SUM_RANDOM_SUMMARY_RE.finditer(text):
            trials = int(match.group("trials"))
            valid = int(match.group("valid"))
            invalid = int(match.group("invalid"))
            target_sum = int(match.group("sum"))
            sum_summary_raw.append(
                {
                    "run": run_name,
                    "pattern": labels[run_name],
                    "sum": target_sum,
                    "valid_total": valid,
                    "invalid_total": invalid,
                    "trials": trials,
                    "valid_rate": valid / trials,
                    "parallel": match.group("parallel"),
                    "reverse": match.group("reverse"),
                    "block_rnd": int(match.group("block_rnd")),
                    "copy_rnd": int(match.group("copy_rnd")),
                    "scramble_rnd": int(match.group("scramble_rnd")),
                    "blocks": match.group("blocks"),
                    "copy_cycles": int(match.group("copy")),
                    "settle_cycles": int(match.group("settle")),
                }
            )
        for match in SUM_RANDOM_VALID_RE.finditer(text):
            sum_pair_rows.append(
                {
                    "run": run_name,
                    "pattern": labels[run_name],
                    "sum": int(match.group("sum")),
                    "a": int(match.group("a")),
                    "b": int(match.group("b")),
                    "count": int(match.group("count")),
                    "trials": int(match.group("trials")),
                }
            )

    sum_pairs_by_run_sum: dict[tuple[str, int], list[dict]] = {}
    for row in sum_pair_rows:
        sum_pairs_by_run_sum.setdefault((row["run"], row["sum"]), []).append(row)

    sum_by_sum_rows: list[dict] = []
    for row in sum_summary_raw:
        key = (row["run"], row["sum"])
        pair_rows = sorted(sum_pairs_by_run_sum.get(key, []), key=lambda item: (item["a"], item["b"]))
        counts = [pair["count"] for pair in pair_rows]
        pair_count = valid_pair_count_for_sum(row["sum"])
        coverage = sum(1 for count in counts if count > 0)
        entropy_norm, tv = valid_distribution_metrics(counts, pair_count)
        sum_by_sum_rows.append(
            {
                **row,
                "valid_pair_count": pair_count,
                "coverage": coverage,
                "coverage_rate": coverage / pair_count,
                "valid_entropy_norm": entropy_norm,
                "valid_tv_from_uniform": tv,
            }
        )

    sum_aggregate_rows: list[dict] = []
    present_sum_runs = {row["run"] for row in sum_by_sum_rows}
    ordered_sum_runs = [run for run in SUM_RUN_ORDER if run in present_sum_runs]
    ordered_sum_runs.extend(sorted(present_sum_runs.difference(ordered_sum_runs)))
    for run_name in ordered_sum_runs:
        selected = [row for row in sum_by_sum_rows if row["run"] == run_name]
        if not selected:
            continue
        valid_total = sum(row["valid_total"] for row in selected)
        trials = sum(row["trials"] for row in selected)
        valid_pairs_total = sum(row["valid_pair_count"] for row in selected)
        valid_pairs_seen = sum(row["coverage"] for row in selected)
        weighted_entropy = sum(row["valid_entropy_norm"] * row["valid_pair_count"] for row in selected) / valid_pairs_total
        weighted_tv = sum(row["valid_tv_from_uniform"] * row["valid_pair_count"] for row in selected) / valid_pairs_total
        sum_aggregate_rows.append(
            {
                "run": run_name,
                "pattern": selected[0]["pattern"],
                "valid_total": valid_total,
                "trials": trials,
                "valid_rate": valid_total / trials,
                "valid_pairs_seen": valid_pairs_seen,
                "valid_pairs_total": valid_pairs_total,
                "coverage_rate": valid_pairs_seen / valid_pairs_total,
                "weighted_entropy_norm": weighted_entropy,
                "weighted_tv_from_uniform": weighted_tv,
                "min_sum_valid_rate": min(row["valid_rate"] for row in selected),
                "sums_below_90pct_valid": sum(1 for row in selected if row["valid_rate"] < 0.9),
                "zero_valid_sums": sum(1 for row in selected if row["valid_total"] == 0),
            }
        )
    write_csv(DATA / "adder4_cases.csv", ordered_case_rows(case_rows))
    write_csv(DATA / "adder4_summary.csv", ordered_summary_rows(summary_rows))
    write_csv(DATA / "adder8_repeated.csv", ordered_repeat8_rows(repeat8_rows))
    write_csv(DATA / "sum_only_by_sum.csv", sum_by_sum_rows)
    write_csv(DATA / "sum_only_valid_pairs.csv", sum_pair_rows)
    write_csv(DATA / "sum_only_aggregate.csv", sum_aggregate_rows)
    baseline_forward = next(
        (row["success_probability"] for row in summary_rows if row["run"] == "baseline_direct4" and row["direction"] == "forward"),
        None,
    )
    if baseline_forward is not None:
        for row in window_sweep_rows:
            row["above_baseline"] = row["success_rate"] > baseline_forward
    ordered_sweep = []
    for run_label, *_blocks in WINDOW_SWEEP_CONFIGS:
        ordered_sweep.extend(row for row in window_sweep_rows if row["run"] == run_label)
    write_csv(DATA / "idea234_forward_window_sweep.csv", ordered_sweep)
    return case_rows, summary_rows, repeat8_rows, sum_by_sum_rows, sum_pair_rows, sum_aggregate_rows


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


def write_sum_validity_svg(path: Path, title: str, rows: list[dict]) -> None:
    width = 900
    height = 360
    left = 58
    right = 230
    top = 42
    bottom = 44
    plot_w = width - left - right
    plot_h = height - top - bottom
    colors = ["#00796b", "#b71c1c", "#2f5597", "#7b1fa2", "#c45a00", "#455a64", "#00838f"]
    run_order = list(dict.fromkeys(row["run"] for row in rows))
    lines = svg_header(width, height)
    lines.append(f'<text x="{width / 2}" y="24" text-anchor="middle" class="title">{title}</text>')
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        y = top + plot_h * (1 - tick)
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#d8dee8"/>')
        lines.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" class="small">{tick * 100:.0f}%</text>')
    for target_sum in range(0, 31, 5):
        x = left + plot_w * (target_sum / 30)
        lines.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" stroke="#eef2f7"/>')
        lines.append(f'<text x="{x:.1f}" y="{top + plot_h + 18}" text-anchor="middle" class="small">{target_sum}</text>')
    lines.append(f'<text x="{left + plot_w / 2}" y="{height - 8}" text-anchor="middle" class="axis">clamped SUM</text>')
    lines.append(f'<text x="14" y="{top + plot_h / 2}" transform="rotate(-90 14,{top + plot_h / 2})" text-anchor="middle" class="axis">valid rate</text>')

    for index, run in enumerate(run_order):
        selected = sorted((row for row in rows if row["run"] == run), key=lambda row: row["sum"])
        if not selected:
            continue
        color = colors[index % len(colors)]
        points = []
        for row in selected:
            x = left + plot_w * (row["sum"] / 30)
            y = top + plot_h * (1 - row["valid_rate"])
            points.append(f"{x:.1f},{y:.1f}")
        lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.2"/>')
        label_y = top + 18 + index * 22
        lines.append(f'<line x1="{left + plot_w + 30}" y1="{label_y - 5}" x2="{left + plot_w + 54}" y2="{label_y - 5}" stroke="{color}" stroke-width="2.2"/>')
        lines.append(f'<text x="{left + plot_w + 62}" y="{label_y}" class="small">{selected[0]["pattern"]}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def ordered_summary_rows(rows: list[dict]) -> list[dict]:
    direction_order = {"forward": 0, "inverse_bsum": 1}
    return sorted(
        rows,
        key=lambda row: (
            SUMMARY_RUN_ORDER.index(row["run"]) if row["run"] in SUMMARY_RUN_ORDER else len(SUMMARY_RUN_ORDER),
            direction_order.get(row["direction"], 99),
        ),
    )


def ordered_case_rows(rows: list[dict]) -> list[dict]:
    direction_order = {"forward": 0, "inverse_bsum": 1}
    return sorted(
        rows,
        key=lambda row: (
            SUMMARY_RUN_ORDER.index(row["run"]) if row["run"] in SUMMARY_RUN_ORDER else len(SUMMARY_RUN_ORDER),
            direction_order.get(row["direction"], 99),
            row["a"],
            row["b"],
        ),
    )


def ordered_repeat8_rows(rows: list[dict]) -> list[dict]:
    vector_order = {(37, 219): 0, (142, 73): 1, (201, 54): 2, (91, 188): 3, (6, 177): 4, (127, 1): 5}
    return sorted(
        rows,
        key=lambda row: (
            REPEAT8_RUN_ORDER.index(row["run"]) if row["run"] in REPEAT8_RUN_ORDER else len(REPEAT8_RUN_ORDER),
            vector_order.get((row["a"], row["b"]), 99),
        ),
    )


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


def make_figures(
    case_rows: list[dict],
    summary_rows: list[dict],
    repeat8_rows: list[dict],
    sum_by_sum_rows: list[dict],
    sum_aggregate_rows: list[dict],
) -> dict[str, str]:
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
    for row in ordered_summary_rows(summary_rows):
        direction = "forward" if row["direction"] == "forward" else "inverse"
        labels.append(f"{row['session']} ({direction})")
        values.append(row["success_probability"])
    write_bar_chart(FIGS / "summary_adder4_success.svg", "4-bit Exhaustive Repeated-Solve Success", labels, values)
    figures["summary_adder4_success.svg"] = rel(FIGS / "summary_adder4_success.svg")

    ordered_repeat8 = ordered_repeat8_rows(repeat8_rows)
    labels8 = [f"{row['session']}: {row['a']}+{row['b']}" for row in ordered_repeat8]
    values8 = [row["success_probability"] for row in ordered_repeat8]
    write_bar_chart(FIGS / "summary_adder8_spotcheck.svg", "8-bit Non-exhaustive Repeated-Solve Success", labels8, values8)
    figures["summary_adder8_spotcheck.svg"] = rel(FIGS / "summary_adder8_spotcheck.svg")
    if sum_aggregate_rows:
        labels_sum = [row["pattern"] for row in sum_aggregate_rows]
        write_bar_chart(
            FIGS / "sum_only_valid_rate.svg",
            "4-bit SUM-only Inverse Valid Rate",
            labels_sum,
            [row["valid_rate"] for row in sum_aggregate_rows],
        )
        figures["sum_only_valid_rate.svg"] = rel(FIGS / "sum_only_valid_rate.svg")
        write_bar_chart(
            FIGS / "sum_only_coverage_rate.svg",
            "4-bit SUM-only Valid-Pair Coverage",
            labels_sum,
            [row["coverage_rate"] for row in sum_aggregate_rows],
        )
        figures["sum_only_coverage_rate.svg"] = rel(FIGS / "sum_only_coverage_rate.svg")
        write_sum_validity_svg(
            FIGS / "sum_only_validity_by_sum.svg",
            "SUM-only Validity by Target Sum",
            sum_by_sum_rows,
        )
        figures["sum_only_validity_by_sum.svg"] = rel(FIGS / "sum_only_validity_by_sum.svg")
    return figures


def summary_table(summary_rows: list[dict]) -> str:
    lines = [
        "| Session | Direction | Cases | Trials/case | Total success | Min hits | Non-perfect cases |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ordered_summary_rows(summary_rows):
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
    for row in ordered_repeat8_rows(rows):
        lines.append(
            f"| {row['session']} | {row['a']} | {row['b']} | {row['expected']} | "
            f"{row['hits']}/{row['trials']} ({row['success_probability'] * 100:.1f}%) | {row['distinct_sums']} |"
        )
    return "\n".join(lines)


def sum_only_table(rows: list[dict]) -> str:
    lines = [
        "| Pattern | Valid rate | Valid-pair coverage | Entropy vs uniform | TV from uniform | Zero-valid sums |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['pattern']} | {row['valid_rate'] * 100:.2f}% ({row['valid_total']}/{row['trials']}) | "
            f"{row['coverage_rate'] * 100:.2f}% ({row['valid_pairs_seen']}/{row['valid_pairs_total']}) | "
            f"{row['weighted_entropy_norm']:.3f} | {row['weighted_tv_from_uniform']:.3f} | {row['zero_valid_sums']} |"
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


def forward_window_sweep_section() -> str:
    path = DATA / "idea234_forward_window_sweep.csv"
    if not path.exists():
        return ""
    with path.open(newline="", encoding="utf-8") as fh:
        rows = {row["run"]: row for row in csv.DictReader(fh)}
    ordered = ["w40_40_40_40", "w10_8_16_6", "w2_2_4_2"]
    labels = {
        "w40_40_40_40": "40,40,40,40, copy=2",
        "w10_8_16_6": "10,8,16,6, copy=2",
        "w2_2_4_2": "2,2,4,2, copy=2",
    }
    table_lines = [
        "| Idea 2+3+4 forward schedule | Solve cycles | Total success | Min hits | Non-perfect cases |",
        "|---|---:|---:|---:|---:|",
    ]
    for run in ordered:
        row = rows.get(run)
        if row is None:
            continue
        hits = int(row["hits"])
        trials_total = int(row["trials_total"])
        success_rate = float(row["success_rate"]) * 100.0
        table_lines.append(
            f"| {labels[run]} | {row['solve_cycles']} | {success_rate:.2f}% ({hits}/{trials_total}) | "
            f"{row['min_hits']} | {row['fail_cases']} |"
        )
    if len(table_lines) == 2:
        return ""
    return "\n".join(
        [
            "### Forward Window Reduction Check",
            "",
            "Motivation: the main comparison above uses the conservative `40,40,40,40` schedule so that the forward and constrained inverse rows share the same hyperparameter setting. A separate forward-only study was then used to estimate how far the carry-window schedule can be shortened while remaining above the direct-RCA baseline.",
            "",
            "Experiment: forward-only exhaustive tests were run over all 256 A/B vectors with 100 randomized trajectories per vector, keeping the same Q3.4 HA/FA weights, shadow carry topology, copy weight, and noise settings. A primitive AND sanity check showed that a literal one-cycle clamp/readout can be misleading, because the unclamped output can still reflect the previous input state on that clock edge. The corrected protocol therefore primes clamped inputs for one clock before the solve window and samples after a post-edge readout delay.",
            "",
            *table_lines,
            "",
            "Result: the shortest physically justified forward setting tested here is `2,2,4,2` with `copy=2`. It uses 16 solve cycles and reaches 96.30%, which is 10.61 percentage points above the direct integer baseline of 85.69%. The earlier `1,1,1,1` setting is excluded because it was not supported by the gate-level sanity check. These shortened schedules are not used for the main constrained inverse comparison; they are reported only as a forward completion-time study.",
        ]
    )


def write_report(
    manifest: dict,
    summary_rows: list[dict],
    repeat8_rows: list[dict],
    sum_aggregate_rows: list[dict],
    figures: dict[str, str],
) -> None:
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

The ripple-carry adder is combinational in Boolean logic, but its stochastic invertible implementation behaves as a pseudo-time-dependent system. The least significant stage must collapse first, its carry must then be transferred, and only afterward can the next full-adder stage be interpreted reliably. When all HA/FA blocks are activated simultaneously, a downstream FA can settle under an incorrect carry-in and subsequently become difficult to correct.

This explains why simply increasing the intrablock Hamiltonian gap is not sufficient. A larger local gap increases a block's confidence in the boundary value currently presented to it. For a downstream FA with state x and incoming carry c, its local distribution is proportional to exp(-beta H_FA(x; c)). If c is initially wrong, a large beta*Delta_intra suppresses later correction. The interblock copy must therefore be strong enough to transmit the carry, but not so dominant that adjacent blocks freeze simultaneously.

## 2. Ideas Tested

Idea 1: equalize gate energy gaps. This was positive for small combinational logic, but it does not solve adders by itself because RCA failure is dominated by carry timing rather than only by unequal local gate gaps.

Idea 2: Q3.4 / Q8-style larger dynamic-range weights. The optimized HA/FA blocks increase the internal valid-invalid gap, but the tests show that FP/Q scaling alone is not reliable across ripple blocks. In this experimental suite it is therefore evaluated both as an individual negative control and as part of the combined idea 2+3+4 configuration.

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

These figures provide the gate-level reference for every primitive block used here: AND, OR, NAND, NOR, HA/XOR, XNOR, and FA. The first figure shows all state energies with valid Boolean states in green. The second shows reverse-clamped input distributions; invalid reverse choices are red.

![Gate energy landscape](figures/gate_energy_landscape.svg)

![Gate reverse distributions](figures/gate_reverse_distributions.svg)

## 4. ModelSim Protocol

All 4-bit tests are exhaustive over A,B in 0..15. Each case is solved {SHADOW_TRIALS} times from randomized trajectories. The generated VHDL uses OS-random seed salts, and every trial starts with an unclamped scramble window before the solve window. The constrained inverse test clamps B and SUM and measures whether A is recovered.

The 8-bit results are intentionally non-exhaustive companion checks. They use six selected vectors and {REPEAT8_TRIALS} repeated solves per vector.

## 5. 4-bit Exhaustive Results

![4-bit summary](figures/summary_adder4_success.svg)

For the main comparison, all shadow/window rows use the conservative 40-cycle-per-block schedule. Shorter Q3.4 schedules are evaluated separately in the forward-only window reduction check below.

{summary_table(summary_rows)}

Forward heatmaps:

![Baseline direct forward](figures/heatmap_baseline_direct4_forward.svg)

![Idea 3+4 integer forward](figures/heatmap_idea34_integer4_forward.svg)

![Idea 2+3+4 Q3.4 forward](figures/heatmap_idea234_q34_forward.svg)

Backward constrained inverse heatmaps:

![Idea 3+4 integer inverse](figures/heatmap_idea34_integer4_inverse.svg)

![Idea 2+3+4 Q3.4 inverse](figures/heatmap_idea234_q34_inverse.svg)

{forward_window_sweep_section()}

## 6. Individual Idea Ablation

The ablation tests isolate the mechanisms that are combined in the final configuration.

{selected_summary_table(summary_rows, ["baseline_direct4", "idea2_q34_direct4", "idea3_window4", "idea4_shadow_parallel4", "idea34_integer4", "idea234_q34_4"])}

Individual forward heatmaps:

![Idea 2 only Q3.4 direct](figures/heatmap_idea2_q34_direct4_forward.svg)

![Idea 3 only windowed](figures/heatmap_idea3_window4_forward.svg)

![Idea 4 only parallel shadow](figures/heatmap_idea4_shadow_parallel4_forward.svg)

The idea 2 only test is the clearest negative control. It changes the local HA/FA energy scale, but leaves the RCA timing graph unchanged. Numerically, direct integer forward success is {baseline4_pct:.2f}%, while idea 2 alone is {idea2_pct:.2f}%; the combined idea 2+3+4 run reaches {idea234_pct:.2f}% under the 40-cycle main protocol.

Mathematically, the node update uses

```text
P(m_i = +1 | field F_i) = (1 + tanh(F_i)) / 2.
```

Scaling Q3.4 weights increases |F_i| and therefore saturates tanh. This is beneficial when the local boundary values are already correct. It is harmful when a downstream FA sees a premature or wrong carry, because the wrong local minimum becomes harder to escape. In low-temperature form, a correction requiring an energy increase Delta has probability proportional to exp(-beta Delta); idea 2 increases Delta without fixing carry arrival time. Idea 3 changes time, idea 4 changes the carry boundary topology, and the combined 2+3+4 case is where the larger local gap becomes useful.

In this run, idea 3 alone reaches {idea3_pct:.2f}% forward and idea 4 alone reaches {idea4_pct:.2f}% forward. Idea 3+4 without Q3.4 reaches {idea34_pct:.2f}% forward, showing that timing and topology provide limited benefit by themselves. The high-confidence Q3.4 blocks become substantially beneficial only when combined with that timing isolation.

## 7. Clamp SUM-Only Inverse Test

This test is reported separately because it is not the same inverse task as `B+SUM->A`. Here only the five SUM bits are clamped, while both A and B are free. For each target SUM in 0..30, the solver should sample valid `(A,B)` pairs whose sum matches the clamp. A strong result needs three things at once: high valid rate, broad coverage of all valid pairs, and a distribution that is not collapsed onto only a few pairs.

The earlier main table did not include this because it measures distribution quality, not only recovery of one missing operand. That distinction is important for an invertible logic discussion: a deterministic inverse can look good under `B+SUM->A`, while a SUM-only clamp reveals whether the machine is actually sampling the full valid manifold.

All SUM-only runs below are 4-bit exhaustive over SUM=0..30 with {SUM_TRIALS} independent randomized trajectories per SUM, so each row uses {31 * SUM_TRIALS:,} total solves.

![SUM-only valid rate](figures/sum_only_valid_rate.svg)

![SUM-only valid-pair coverage](figures/sum_only_coverage_rate.svg)

![SUM-only validity by target SUM](figures/sum_only_validity_by_sum.svg)

{sum_only_table(sum_aggregate_rows)}

The direct integer baseline is useful here because it separates SUM-only inverse behavior from the shadow/window ideas. The result is mixed. The integer direct and shadow variants preserve the valid-pair manifold well: every valid `(A,B)` pair appears, and the entropy among valid samples stays close to uniform. However, the shadow variants still produce too many invalid `(A,B)` samples when only SUM is clamped.

The forward-order Q3.4 SUM-only runs improve validity relative to shadow-only cases, but they collapse the distribution. The original idea 2+3+4 SUM-only run sees only 64 of 256 valid pairs and has three target sums with zero valid samples. Reversing the block order for SUM-only and keeping `40,40,40,40` windows fixes part of that: coverage rises to 194/256 and zero-valid sums drop to zero. It still does not beat the direct baseline in valid rate, and the edge sums remain weak: `SUM=0` is 8.8% valid and `SUM=30` is 20.0% valid.

Thus, the present energy distribution is tuned for forward and constrained inverse recovery, but not yet for SUM-only inverse sampling. Future work should tune the energy distribution to balance validity against entropy on the clamped manifold. Such tuning is more likely to be practical with floating-point or fixed-point continuous weights than with integer weights, because the objective is not merely to increase the local gate gap; it is to shape relative energies among many globally valid states while keeping invalid states suppressed.

## 8. 8-bit Non-exhaustive Companion

![8-bit spot check](figures/summary_adder8_spotcheck.svg)

{repeat8_table(repeat8_rows)}

## 9. Interpretation

The important comparison is not only whether one frozen readout is correct, but the repeated-solve probability after independent randomization. The direct integer RCA is the baseline failure mode. Idea 3+4 tests whether timing windows plus one shadow node repair the carry direction. Idea 2+3+4 tests whether the same topology benefits from the Q3.4 optimized gate weights while preserving the moderate interblock copy.

In this dataset, integer idea 3+4 is only a modest improvement over the direct 8-bit baseline and is roughly tied with the 4-bit direct baseline under the repeated-solve metric. The combined idea 2+3+4 result is the strongest positive result: Q3.4 plus the shadow/window schedule reaches {idea234_pct:.2f}% forward and {idea234_inverse_pct:.2f}% constrained inverse success on exhaustive 4-bit tests under the 40-cycle main protocol, and about 99-100% on the selected 8-bit vectors. This suggests that the larger intrablock gap is helpful only after timing isolation is added.

## 10. Exact Parameters

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
- 4-bit main forward/inverse window cycles: 40,40,40,40 with copy=2
- 4-bit forward-only reduction schedules: 10,8,16,6 with copy=2 reaches 98.78%; 2,2,4,2 with copy=2 reaches 96.30% under the corrected clamp-prime/readout protocol
- 8-bit window cycles: 40,40,40,40,40,40,40,40 with copy=2
- Solve noise: block_rnd=4 encoded = 0.25 physical, copy_rnd=0; scramble noise=8 encoded = 0.5 physical

Clamp SUM-only runs:

- Direct baseline testbench: `tb/tb_adder4_direct_sum_randomized_distribution.vhd`
- Direct baseline runner: `sim/run_adder4_direct_sum_randomized_distribution.ps1`
- Shadow/window testbench: `tb/tb_adder4_shadow1_sum_randomized_distribution.vhd`
- Shadow/window runner: `sim/run_adder4_shadow1_sum_randomized_distribution.ps1`
- Scope: SUM=0..30, {SUM_TRIALS} independent randomized solves per SUM
- Baseline direct integer: adder_rnd=1, scramble=80, settle=500
- Idea 3+4 integer: block_rnd=1, copy_rnd=0, scramble_rnd=2, windows=40,40,40,40, copy=2
- Idea 2+3+4 Q3.4 forward-order SUM-only: block_rnd=4 encoded, copy_rnd=0, scramble_rnd=8 encoded, windows=10,8,16,6, copy=2
- Idea 2+3+4 Q3.4 reverse-order: block_rnd=4 encoded, copy_rnd=0, scramble_rnd=8 encoded, windows=40,40,40,40, copy=2
- Idea 4 only: block_rnd=1, copy_rnd=0, scramble_rnd=2, parallel settle=160
- Idea 2+4 Q3.4: block_rnd=4 encoded, copy_rnd=0, scramble_rnd=8 encoded, parallel settle=160

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

## 11. Artifacts

- Manifest: `data/manifest.json`
- Gate energy CSV: `data/gate_energy_landscape.csv`
- Gate reverse CSV: `data/gate_reverse_distributions.csv`
- 4-bit case CSV: `data/adder4_cases.csv`
- 4-bit summary CSV: `data/adder4_summary.csv`
- SUM-only aggregate CSV: `data/sum_only_aggregate.csv`
- SUM-only by-SUM CSV: `data/sum_only_by_sum.csv`
- SUM-only valid-pair CSV: `data/sum_only_valid_pairs.csv`
- Idea 2+3+4 forward window sweep CSV: `data/idea234_forward_window_sweep.csv`
- 8-bit repeated-solve CSV: `data/adder8_repeated.csv`
- Corrected Q3.4 40-cycle exhaustive transcript: `traces/idea234_q34_4.txt`
- Corrected Q3.4 shortened-schedule transcript: `traces/idea234_q34_4_w10_8_16_6_corrected.log`
- Other ModelSim transcripts: `traces/`
"""
    (OUT / "report.md").write_text(report, encoding="utf-8")


def main() -> None:
    prepare_output()
    manifest = generate_artifacts()
    runs = run_all()
    case_rows, summary_rows, repeat8_rows, sum_by_sum_rows, _sum_pair_rows, sum_aggregate_rows = parse_outputs(runs)
    write_gate_visualizations()
    figures = make_figures(case_rows, summary_rows, repeat8_rows, sum_by_sum_rows, sum_aggregate_rows)
    write_report(manifest, summary_rows, repeat8_rows, sum_aggregate_rows, figures)
    print(f"Wrote {OUT / 'report.md'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
