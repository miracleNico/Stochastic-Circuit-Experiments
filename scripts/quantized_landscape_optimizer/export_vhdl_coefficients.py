"""Export verified optimizer JSON and current RTL weights as a VHDL package.

The generated package deliberately stores coefficients as scaled integers.  The
default scale of two represents the half-integer optimizer solution exactly and
keeps the VHDL audit free of floating-point tolerances.  Before writing output,
this tool parses ``experiments/gate_baseline/hardware/generated_networks.vhd`` and proves that every HA/FA
``BIAS`` and ``W*`` value is exactly twice its optimizer counterpart.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))


import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


class ExportError(ValueError):
    """Raised when JSON or RTL cannot support the requested audit package."""


@dataclass(frozen=True)
class GateDefinition:
    label: str
    optimizer_nodes: tuple[str, ...]
    rtl_entity: str
    expected_valid_energy: float = -2.0
    expected_gap: float = 1.0
    expected_invalid_local_minima: int = 0

    @property
    def coefficient_count(self) -> int:
        node_count = len(self.optimizer_nodes)
        return node_count + node_count * (node_count - 1) // 2


GATES = (
    GateDefinition("HA", ("A", "B", "S", "C"), "gen_xor_gate"),
    GateDefinition("FA", ("A", "B", "CIN", "S", "COUT"), "gen_fa_gate"),
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ExportError(f"could not read optimizer JSON {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ExportError(f"invalid optimizer JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ExportError(f"optimizer JSON {path} must contain an object")
    return payload


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExportError(f"{label} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ExportError(f"{label} must be finite")
    return result


def load_optimizer_coefficients(
    path: Path, definition: GateDefinition, tolerance: float = 1e-9
) -> tuple[float, ...]:
    """Load and validate one successful optimizer result JSON."""

    payload = _read_json(path)
    if payload.get("status") != "success":
        raise ExportError(f"{definition.label} optimizer JSON is not successful")

    problem = payload.get("problem")
    if not isinstance(problem, dict):
        raise ExportError(f"{definition.label} optimizer JSON has no problem object")
    nodes = problem.get("nodes")
    if not isinstance(nodes, list) or tuple(nodes) != definition.optimizer_nodes:
        raise ExportError(
            f"{definition.label} optimizer nodes must be "
            f"{list(definition.optimizer_nodes)!r}, got {nodes!r}"
        )

    quantized = payload.get("quantized")
    if not isinstance(quantized, dict):
        raise ExportError(f"{definition.label} optimizer JSON has no quantized object")
    raw_coefficients = quantized.get("coefficients")
    if not isinstance(raw_coefficients, list):
        raise ExportError(f"{definition.label} quantized coefficients must be an array")
    if len(raw_coefficients) != definition.coefficient_count:
        raise ExportError(
            f"{definition.label} requires {definition.coefficient_count} coefficients, "
            f"got {len(raw_coefficients)}"
        )
    coefficients = tuple(
        _finite_number(value, f"{definition.label} coefficient[{index}]")
        for index, value in enumerate(raw_coefficients)
    )

    audit = quantized.get("audit")
    if not isinstance(audit, dict):
        raise ExportError(f"{definition.label} quantized audit is missing")
    valid_energy = _finite_number(
        audit.get("valid_energy_reference"),
        f"{definition.label} valid_energy_reference",
    )
    gap = _finite_number(
        audit.get("minimum_invalid_gap"),
        f"{definition.label} minimum_invalid_gap",
    )
    traps = audit.get("invalid_local_minima")
    if isinstance(traps, bool) or not isinstance(traps, int):
        raise ExportError(f"{definition.label} invalid_local_minima must be an integer")
    if abs(valid_energy - definition.expected_valid_energy) > tolerance:
        raise ExportError(
            f"{definition.label} valid energy is {valid_energy}, expected "
            f"{definition.expected_valid_energy}"
        )
    if abs(gap - definition.expected_gap) > tolerance:
        raise ExportError(
            f"{definition.label} gap is {gap}, expected {definition.expected_gap}"
        )
    if traps != definition.expected_invalid_local_minima:
        raise ExportError(
            f"{definition.label} has {traps} invalid local minima, expected "
            f"{definition.expected_invalid_local_minima}"
        )
    if audit.get("valid_equal") is not True or audit.get("gap_ok") is not True:
        raise ExportError(f"{definition.label} quantized audit did not pass")
    return coefficients


def _architecture_body(source: str, entity: str) -> str:
    expression = re.compile(
        rf"\barchitecture\s+\w+\s+of\s+{re.escape(entity)}\s+is\b"
        rf"(?P<body>.*?)\bend\s+architecture(?:\s+\w+)?\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    match = expression.search(source)
    if match is None:
        raise ExportError(f"could not find architecture for RTL entity {entity}")
    return match.group("body")


def parse_rtl_coefficients(
    source_path: Path, definition: GateDefinition
) -> tuple[int, ...]:
    """Extract flattened ``[h..., J01, J02, ...]`` values from generated RTL."""

    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ExportError(f"could not read RTL source {source_path}: {exc}") from exc
    body = _architecture_body(source, definition.rtl_entity)
    node_count = len(definition.optimizer_nodes)

    node_pattern = re.compile(
        r"\bnode_(?P<node>\d+)\s*:\s*entity\s+work\.spin_node\s*"
        r"generic\s+map\s*\((?P<generics>.*?)\)\s*port\s+map",
        re.IGNORECASE | re.DOTALL,
    )
    assignment_pattern = re.compile(
        r"\b(?P<name>BIAS|W\d+)\s*=>\s*(?P<value>[+-]?\d+)\b",
        re.IGNORECASE,
    )
    nodes: dict[int, dict[str, int]] = {}
    for match in node_pattern.finditer(body):
        node = int(match.group("node"))
        if node in nodes:
            raise ExportError(f"duplicate node_{node} in {definition.rtl_entity}")
        values = {
            assignment.group("name").upper(): int(assignment.group("value"))
            for assignment in assignment_pattern.finditer(match.group("generics"))
        }
        nodes[node] = values
    if set(nodes) != set(range(node_count)):
        raise ExportError(
            f"{definition.rtl_entity} nodes are {sorted(nodes)}, expected "
            f"0..{node_count - 1}"
        )

    neighbor_pattern = re.compile(
        r"\bneighbors_(?P<node>\d+)\s*<=\s*\((?P<body>.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    entry_pattern = re.compile(
        r"(?P<slot>\d+)\s*=>\s*spin_s\s*\(\s*(?P<neighbor>\d+)\s*\)",
        re.IGNORECASE,
    )
    neighbor_order: dict[int, tuple[int, ...]] = {}
    for match in neighbor_pattern.finditer(body):
        node = int(match.group("node"))
        entries = sorted(
            (
                int(entry.group("slot")),
                int(entry.group("neighbor")),
            )
            for entry in entry_pattern.finditer(match.group("body"))
        )
        if [slot for slot, _neighbor in entries] != list(range(node_count - 1)):
            raise ExportError(
                f"{definition.rtl_entity} neighbors_{node} does not define contiguous slots"
            )
        neighbor_order[node] = tuple(neighbor for _slot, neighbor in entries)
    if set(neighbor_order) != set(range(node_count)):
        raise ExportError(f"{definition.rtl_entity} neighbor maps are incomplete")

    fields: list[int] = []
    directed: dict[tuple[int, int], int] = {}
    for node in range(node_count):
        values = nodes[node]
        if "BIAS" not in values:
            raise ExportError(f"{definition.rtl_entity} node_{node} has no BIAS")
        fields.append(values["BIAS"])
        expected_neighbors = tuple(index for index in range(node_count) if index != node)
        if neighbor_order[node] != expected_neighbors:
            raise ExportError(
                f"{definition.rtl_entity} node_{node} neighbor order is "
                f"{neighbor_order[node]}, expected {expected_neighbors}"
            )
        for slot, neighbor in enumerate(neighbor_order[node]):
            key = f"W{slot}"
            if key not in values:
                raise ExportError(f"{definition.rtl_entity} node_{node} has no {key}")
            directed[(node, neighbor)] = values[key]

    pairs: list[int] = []
    for left in range(node_count):
        for right in range(left + 1, node_count):
            forward = directed[(left, right)]
            reverse = directed[(right, left)]
            if forward != reverse:
                raise ExportError(
                    f"{definition.rtl_entity} coupling {left}-{right} is asymmetric: "
                    f"{forward} vs {reverse}"
                )
            pairs.append(forward)
    return tuple(fields + pairs)


def _scaled_integers(
    coefficients: Sequence[float], scale: int, label: str, tolerance: float = 1e-9
) -> tuple[int, ...]:
    result: list[int] = []
    for index, value in enumerate(coefficients):
        scaled = float(value) * scale
        integer = round(scaled)
        if abs(scaled - integer) > tolerance:
            raise ExportError(
                f"{label} coefficient[{index}]={value} is not representable at scale {scale}"
            )
        result.append(integer)
    return tuple(result)


def _vhdl_vector(values: Sequence[int]) -> str:
    return "(" + ", ".join(str(value) for value in values) + ")"


def build_vhdl_package(
    ha_json: Path,
    fa_json: Path,
    rtl_source: Path,
    coefficient_scale: int = 2,
) -> str:
    """Return a deterministic, fully verified VHDL coefficient package."""

    if coefficient_scale < 1:
        raise ExportError("coefficient scale must be at least one")
    json_paths = {"HA": ha_json, "FA": fa_json}
    optimizer: dict[str, tuple[int, ...]] = {}
    rtl: dict[str, tuple[int, ...]] = {}
    for definition in GATES:
        optimized_values = load_optimizer_coefficients(
            json_paths[definition.label], definition
        )
        rtl_values = parse_rtl_coefficients(rtl_source, definition)
        if len(optimized_values) != len(rtl_values):
            raise ExportError(f"{definition.label} optimizer/RTL coefficient counts differ")
        for index, (optimized, current_rtl) in enumerate(
            zip(optimized_values, rtl_values)
        ):
            if abs(current_rtl - 2.0 * optimized) > 1e-9:
                raise ExportError(
                    f"{definition.label} RTL coefficient[{index}]={current_rtl} is not "
                    f"2x optimizer value {optimized}"
                )
        optimizer[definition.label] = _scaled_integers(
            optimized_values,
            coefficient_scale,
            f"{definition.label} optimizer",
        )
        rtl[definition.label] = _scaled_integers(
            rtl_values,
            coefficient_scale,
            f"{definition.label} RTL",
        )

    ha_sha = hashlib.sha256(ha_json.read_bytes()).hexdigest()
    fa_sha = hashlib.sha256(fa_json.read_bytes()).hexdigest()
    rtl_sha = hashlib.sha256(rtl_source.read_bytes()).hexdigest()
    return f"""-- Generated by export_vhdl_coefficients.py; do not edit.
-- HA optimizer JSON SHA-256: {ha_sha}
-- FA optimizer JSON SHA-256: {fa_sha}
-- RTL source SHA-256: {rtl_sha}
package optimizer_coefficients_pkg is
    type coefficient_vector_t is array (natural range <>) of integer;

    constant COEFFICIENT_SCALE : positive := {coefficient_scale};
    constant RTL_MULTIPLIER    : positive := 2;

    constant HA_NODE_COUNT : positive := 4;
    constant HA_OPT_COEFFICIENTS : coefficient_vector_t(0 to 9) :=
        {_vhdl_vector(optimizer['HA'])};
    constant HA_RTL_COEFFICIENTS : coefficient_vector_t(0 to 9) :=
        {_vhdl_vector(rtl['HA'])};

    constant FA_NODE_COUNT : positive := 5;
    constant FA_OPT_COEFFICIENTS : coefficient_vector_t(0 to 14) :=
        {_vhdl_vector(optimizer['FA'])};
    constant FA_RTL_COEFFICIENTS : coefficient_vector_t(0 to 14) :=
        {_vhdl_vector(rtl['FA'])};
end package optimizer_coefficients_pkg;
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export verified HA/FA optimizer JSON as a VHDL coefficient package"
    )
    parser.add_argument("--ha-json", type=Path, required=True)
    parser.add_argument("--fa-json", type=Path, required=True)
    parser.add_argument("--rtl-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coefficient-scale", type=int, default=2)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rendered = build_vhdl_package(
            args.ha_json,
            args.fa_json,
            args.rtl_source,
            args.coefficient_scale,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"wrote {args.output}")
        return 0
    except (ExportError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
