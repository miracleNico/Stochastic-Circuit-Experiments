"""Verify stable Questa report markers for optimizer and generated-gate evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Sequence


STATIC_MARKERS = (
    "OPTIMIZER_AUDIT HA valid_energy=-2 gap=1 invalid_local_minima=0 states=16",
    "OPTIMIZER_AUDIT FA valid_energy=-2 gap=1 invalid_local_minima=0 states=32",
    "RTL_SCALE_AUDIT HA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=16",
    "RTL_SCALE_AUDIT FA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=32",
    "tb_optimizer_energy_audit passed",
)

DYNAMIC_MARKERS = ("tb_generated_gates passed",)

_SUMMARY_PATTERN = re.compile(
    r"Errors:\s*(?P<errors>\d+)\s*,\s*Warnings:\s*(?P<warnings>\d+)",
    re.IGNORECASE,
)
_BAD_SEVERITY_PATTERN = re.compile(
    r"\*\*\s*(?:Error|Fatal|Failure|Warning)\s*:", re.IGNORECASE
)


def verify_transcript(text: str, kind: str) -> dict[str, object]:
    """Return a JSON-friendly verification result without trusting exit code alone."""

    if kind == "static":
        required = STATIC_MARKERS
        coverage = {
            "ha_states": 16,
            "fa_states": 32,
            "optimizer_and_rtl_landscapes": True,
        }
    elif kind == "generated-gates":
        required = DYNAMIC_MARKERS
        # The final testbench marker is reached only after these existing
        # tb_generated_gates loops/procedure calls have completed.
        coverage = {
            "xor_half_adder_forward_cases": 4,
            "xor_half_adder_reverse_cases": 2,
            "full_adder_forward_cases": 8,
        }
    else:
        raise ValueError(f"unsupported evidence kind: {kind}")

    missing = [marker for marker in required if marker not in text]
    bad_severities = _BAD_SEVERITY_PATTERN.findall(text)
    summaries = [
        (int(match.group("errors")), int(match.group("warnings")))
        for match in _SUMMARY_PATTERN.finditer(text)
    ]
    zero_summary = bool(summaries) and all(pair == (0, 0) for pair in summaries)
    passed = not missing and not bad_severities and zero_summary
    return {
        "schema_version": 1,
        "kind": kind,
        "passed": passed,
        "required_markers": list(required),
        "missing_markers": missing,
        "zero_errors_zero_warnings": zero_summary,
        "summary_count": len(summaries),
        "bad_severity_count": len(bad_severities),
        "coverage": coverage,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify stable markers in a Questa optimizer/gate transcript"
    )
    parser.add_argument(
        "--kind",
        choices=("static", "generated-gates"),
        required=True,
    )
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        text = args.transcript.read_text(encoding="utf-8", errors="replace")
        result = verify_transcript(text, args.kind)
        rendered = json.dumps(result, indent=2, sort_keys=True)
        if args.json_out is not None:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0 if result["passed"] else 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
