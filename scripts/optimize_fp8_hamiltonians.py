import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from generate_hamiltonians import Hamiltonian, emit_vhdl, energy, nonzero_edges, zero_matrix


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class OptimizedGate:
    ham: Hamiltonian
    gamma_encoded: int
    boundary_abs_encoded: int
    coeff_abs_encoded: int


@dataclass
class CoefficientFormat:
    name: str
    frac_bits: int
    values: list[int] | None


def set_edge(j: list[list[int]], a: int, b: int, value: int) -> None:
    j[a][b] = value
    j[b][a] = value


def parse_fraction(text: str) -> Fraction:
    try:
        return Fraction(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid rational value: {text}") from exc


def fp8_values_encoded(exp_bits: int, mant_bits: int, bias: int, coeff_max: Fraction) -> tuple[int, list[int]]:
    # Finite-only FP8 lattice. The all-ones exponent keeps finite values, with
    # the top mantissa code reserved for NaN. Values are encoded exactly as
    # fixed-point integers using the minimum binary denominator for subnormals.
    frac_bits = mant_bits + bias - 1
    values = {0}
    max_exp_code = (1 << exp_bits) - 1
    max_mant = (1 << mant_bits) - 1

    for mant in range(1, 1 << mant_bits):
        value = Fraction(mant, 1 << mant_bits) * Fraction(2) ** (1 - bias)
        if value <= coeff_max:
            encoded = int(value * (1 << frac_bits))
            values.add(encoded)
            values.add(-encoded)

    for exp in range(1, max_exp_code):
        for mant in range(0, 1 << mant_bits):
            value = (Fraction(1) + Fraction(mant, 1 << mant_bits)) * (Fraction(2) ** (exp - bias))
            if value <= coeff_max:
                encoded = int(value * (1 << frac_bits))
                values.add(encoded)
                values.add(-encoded)

    for mant in range(0, max_mant):
        value = (Fraction(1) + Fraction(mant, 1 << mant_bits)) * (Fraction(2) ** (max_exp_code - bias))
        if value <= coeff_max:
            encoded = int(value * (1 << frac_bits))
            values.add(encoded)
            values.add(-encoded)

    return frac_bits, sorted(values)


def coefficient_format(name: str, coeff_max_q8: int, fp8_bias: int | None = None) -> CoefficientFormat:
    if name == "fixed-q8":
        return CoefficientFormat(name=name, frac_bits=8, values=None)
    if name == "fp8-e4m3":
        coeff_max = Fraction(coeff_max_q8, 256)
        frac_bits, values = fp8_values_encoded(exp_bits=4, mant_bits=3, bias=7, coeff_max=coeff_max)
        return CoefficientFormat(name=name, frac_bits=frac_bits, values=values)
    if name == "fp8-e3m4":
        coeff_max = Fraction(coeff_max_q8, 256)
        bias = 1 if fp8_bias is None else fp8_bias
        frac_bits, values = fp8_values_encoded(exp_bits=3, mant_bits=4, bias=bias, coeff_max=coeff_max)
        return CoefficientFormat(name=f"{name}-b{bias}", frac_bits=frac_bits, values=values)
    if name == "fp8-e2m5":
        coeff_max = Fraction(coeff_max_q8, 256)
        bias = -2 if fp8_bias is None else fp8_bias
        frac_bits, values = fp8_values_encoded(exp_bits=2, mant_bits=5, bias=bias, coeff_max=coeff_max)
        return CoefficientFormat(name=f"{name}-b{bias}", frac_bits=frac_bits, values=values)
    raise ValueError(f"unsupported coefficient format: {name}")


def optimize_gate(
    name: str,
    entity: str,
    nodes: list[str],
    valid_states: list[tuple[int, ...]],
    boundary_nodes: set[str],
    coeff_max_q8: int,
    fmt: CoefficientFormat,
) -> OptimizedGate:
    if fmt.values is not None:
        return optimize_gate_discrete(name, entity, nodes, valid_states, boundary_nodes, fmt)

    n = len(nodes)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    coeff_count = n + len(edges)
    e0_idx = coeff_count
    gamma_idx = coeff_count + 1
    abs0_idx = coeff_count + 2
    total_vars = abs0_idx + coeff_count

    def energy_row(bits: tuple[int, ...]) -> np.ndarray:
        m = [1 if bit else -1 for bit in bits]
        row = np.zeros(total_vars)
        for i in range(n):
            row[i] = -m[i]
        for edge_idx, (i, j) in enumerate(edges):
            row[n + edge_idx] = -(m[i] * m[j])
        return row

    rows = []
    lower = []
    upper = []
    valid = set(valid_states)

    for bits in valid_states:
        row = energy_row(bits)
        row[e0_idx] = -1
        rows.append(row)
        lower.append(0)
        upper.append(0)

    for bits in product([0, 1], repeat=n):
        if bits in valid:
            continue
        row = energy_row(bits)
        row[e0_idx] = -1
        row[gamma_idx] = -1
        rows.append(row)
        lower.append(0)
        upper.append(np.inf)

    for coeff_idx in range(coeff_count):
        row = np.zeros(total_vars)
        row[abs0_idx + coeff_idx] = 1
        row[coeff_idx] = -1
        rows.append(row)
        lower.append(0)
        upper.append(np.inf)

        row = np.zeros(total_vars)
        row[abs0_idx + coeff_idx] = 1
        row[coeff_idx] = 1
        rows.append(row)
        lower.append(0)
        upper.append(np.inf)

    constraints = LinearConstraint(np.vstack(rows), np.array(lower), np.array(upper))
    bounds = Bounds(
        [-coeff_max_q8] * coeff_count + [-np.inf, 0] + [0] * coeff_count,
        [coeff_max_q8] * coeff_count + [np.inf, np.inf] + [coeff_max_q8] * coeff_count,
    )
    integrality = np.ones(total_vars)

    stage1_objective = np.zeros(total_vars)
    stage1_objective[gamma_idx] = -1
    stage1 = milp(
        c=stage1_objective,
        constraints=constraints,
        bounds=bounds,
        integrality=integrality,
        options={"mip_rel_gap": 0, "time_limit": 60},
    )
    if not stage1.success:
        raise RuntimeError(f"{name}: gate-gap MILP failed: {stage1.message}")

    gamma_q8 = int(round(stage1.x[gamma_idx]))

    boundary_indices = {nodes.index(node) for node in boundary_nodes}
    boundary_coeffs = []
    for i in boundary_indices:
        boundary_coeffs.append(i)
    for edge_idx, (i, j) in enumerate(edges):
        if i in boundary_indices or j in boundary_indices:
            boundary_coeffs.append(n + edge_idx)

    rows2 = list(rows)
    lower2 = list(lower)
    upper2 = list(upper)
    row = np.zeros(total_vars)
    row[gamma_idx] = 1
    rows2.append(row)
    lower2.append(gamma_q8)
    upper2.append(np.inf)

    stage2_objective = np.zeros(total_vars)
    for coeff_idx in boundary_coeffs:
        stage2_objective[abs0_idx + coeff_idx] += 1000
    for coeff_idx in range(coeff_count):
        stage2_objective[abs0_idx + coeff_idx] += 1

    stage2 = milp(
        c=stage2_objective,
        constraints=LinearConstraint(np.vstack(rows2), np.array(lower2), np.array(upper2)),
        bounds=bounds,
        integrality=integrality,
        options={"mip_rel_gap": 0, "time_limit": 60},
    )
    if not stage2.success:
        raise RuntimeError(f"{name}: boundary-minimization MILP failed: {stage2.message}")

    result = np.rint(stage2.x).astype(int)
    h = result[:n].tolist()
    j = zero_matrix(n)
    for edge_idx, (i, k) in enumerate(edges):
        set_edge(j, i, k, int(result[n + edge_idx]))

    ham = Hamiltonian(
        name=name,
        entity=entity,
        nodes=nodes,
        h=h,
        j=j,
        valid_states=valid_states,
        source=f"Q8 MILP: maximize valid/invalid gate gap, then minimize carry-boundary L1; |coeff|<={coeff_max_q8}/256",
        energy_gap=gamma_q8,
        valid_energy=energy(h, j, valid_states[0]),
        field_frac_bits=8,
        weight_scale="optimized",
    )

    return OptimizedGate(
        ham=ham,
        gamma_encoded=gamma_q8,
        boundary_abs_encoded=sum(abs(result[idx]) for idx in boundary_coeffs),
        coeff_abs_encoded=sum(abs(result[idx]) for idx in range(coeff_count)),
    )


def optimize_gate_discrete(
    name: str,
    entity: str,
    nodes: list[str],
    valid_states: list[tuple[int, ...]],
    boundary_nodes: set[str],
    fmt: CoefficientFormat,
) -> OptimizedGate:
    if fmt.values is None:
        raise ValueError("discrete optimizer requires an explicit coefficient value set")

    n = len(nodes)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    coeff_count = n + len(edges)
    values = fmt.values
    value_count = len(values)
    e0_idx = coeff_count * value_count
    gamma_idx = e0_idx + 1
    total_vars = gamma_idx + 1

    def coeff_var(coeff_idx: int, value_idx: int) -> int:
        return coeff_idx * value_count + value_idx

    def energy_terms(bits: tuple[int, ...]) -> list[int]:
        m = [1 if bit else -1 for bit in bits]
        terms = [-m[i] for i in range(n)]
        terms.extend([-(m[i] * m[j]) for i, j in edges])
        return terms

    rows = []
    lower = []
    upper = []

    for coeff_idx in range(coeff_count):
        row = np.zeros(total_vars)
        for value_idx in range(value_count):
            row[coeff_var(coeff_idx, value_idx)] = 1
        rows.append(row)
        lower.append(1)
        upper.append(1)

    valid = set(valid_states)
    for bits in valid_states:
        row = np.zeros(total_vars)
        for coeff_idx, term in enumerate(energy_terms(bits)):
            for value_idx, value in enumerate(values):
                row[coeff_var(coeff_idx, value_idx)] = term * value
        row[e0_idx] = -1
        rows.append(row)
        lower.append(0)
        upper.append(0)

    for bits in product([0, 1], repeat=n):
        if bits in valid:
            continue
        row = np.zeros(total_vars)
        for coeff_idx, term in enumerate(energy_terms(bits)):
            for value_idx, value in enumerate(values):
                row[coeff_var(coeff_idx, value_idx)] = term * value
        row[e0_idx] = -1
        row[gamma_idx] = -1
        rows.append(row)
        lower.append(0)
        upper.append(np.inf)

    constraints = LinearConstraint(np.vstack(rows), np.array(lower), np.array(upper))
    bounds = Bounds([0] * e0_idx + [-np.inf, 0], [1] * e0_idx + [np.inf, np.inf])
    integrality = np.ones(total_vars)

    stage1_objective = np.zeros(total_vars)
    stage1_objective[gamma_idx] = -1
    stage1 = milp(
        c=stage1_objective,
        constraints=constraints,
        bounds=bounds,
        integrality=integrality,
        options={"mip_rel_gap": 0, "time_limit": 120},
    )
    if not stage1.success:
        raise RuntimeError(f"{name}: {fmt.name} gate-gap MILP failed: {stage1.message}")

    gamma_encoded = int(round(stage1.x[gamma_idx]))

    rows2 = list(rows)
    lower2 = list(lower)
    upper2 = list(upper)
    row = np.zeros(total_vars)
    row[gamma_idx] = 1
    rows2.append(row)
    lower2.append(gamma_encoded)
    upper2.append(np.inf)

    boundary_indices = {nodes.index(node) for node in boundary_nodes}
    boundary_coeffs = []
    for i in boundary_indices:
        boundary_coeffs.append(i)
    for edge_idx, (i, j) in enumerate(edges):
        if i in boundary_indices or j in boundary_indices:
            boundary_coeffs.append(n + edge_idx)

    stage2_objective = np.zeros(total_vars)
    for coeff_idx in range(coeff_count):
        coeff_weight = 1001 if coeff_idx in boundary_coeffs else 1
        for value_idx, value in enumerate(values):
            stage2_objective[coeff_var(coeff_idx, value_idx)] = coeff_weight * abs(value)

    stage2 = milp(
        c=stage2_objective,
        constraints=LinearConstraint(np.vstack(rows2), np.array(lower2), np.array(upper2)),
        bounds=bounds,
        integrality=integrality,
        options={"mip_rel_gap": 0, "time_limit": 120},
    )
    if not stage2.success:
        raise RuntimeError(f"{name}: {fmt.name} boundary-minimization MILP failed: {stage2.message}")

    selected = []
    for coeff_idx in range(coeff_count):
        scores = stage2.x[coeff_idx * value_count:(coeff_idx + 1) * value_count]
        selected.append(values[int(np.argmax(scores))])

    h = selected[:n]
    j = zero_matrix(n)
    for edge_idx, (i, k) in enumerate(edges):
        set_edge(j, i, k, selected[n + edge_idx])

    ham = Hamiltonian(
        name=name,
        entity=entity,
        nodes=nodes,
        h=h,
        j=j,
        valid_states=valid_states,
        source=(
            f"{fmt.name} MILP: maximize valid/invalid gate gap, then minimize carry-boundary L1; "
            f"{value_count} allowed coefficient values"
        ),
        energy_gap=gamma_encoded,
        valid_energy=energy(h, j, valid_states[0]),
        field_frac_bits=fmt.frac_bits,
        weight_scale=fmt.name,
    )

    return OptimizedGate(
        ham=ham,
        gamma_encoded=gamma_encoded,
        boundary_abs_encoded=sum(abs(selected[idx]) for idx in boundary_coeffs),
        coeff_abs_encoded=sum(abs(value) for value in selected),
    )


def q8_ha(coeff_max_q8: int, fmt: CoefficientFormat) -> OptimizedGate:
    valid = [(a, b, a ^ b, a & b) for a, b in product([0, 1], repeat=2)]
    return optimize_gate(
        f"HA_XOR_{fmt.name.upper().replace('-', '_')}_OPT",
        f"gen_xor_gate_{fmt.name.replace('-', '_')}_opt",
        ["A", "B", "S", "C"],
        valid,
        {"C"},
        coeff_max_q8,
        fmt,
    )


def q8_fa(coeff_max_q8: int, fmt: CoefficientFormat) -> OptimizedGate:
    valid = []
    for a, b, cin in product([0, 1], repeat=3):
        total = a + b + cin
        valid.append((a, b, cin, total & 1, (total >> 1) & 1))
    return optimize_gate(
        f"FA_{fmt.name.upper().replace('-', '_')}_OPT",
        f"gen_fa_gate_{fmt.name.replace('-', '_')}_opt",
        ["A", "B", "CIN", "S", "COUT"],
        valid,
        {"CIN", "COUT"},
        coeff_max_q8,
        fmt,
    )


def add_block(global_h: list[int], global_j: list[list[int]], block: Hamiltonian, indices: list[int]) -> None:
    for local_i, global_i in enumerate(indices):
        global_h[global_i] += block.h[local_i]
    for local_i, global_i in enumerate(indices):
        for local_j in range(local_i + 1, len(indices)):
            global_k = indices[local_j]
            value = block.j[local_i][local_j]
            global_j[global_i][global_k] += value
            global_j[global_k][global_i] += value


def split_carry_adder(width: int, ha: Hamiltonian, fa: Hamiltonian, link_encoded: int, fmt: CoefficientFormat) -> Hamiltonian:
    nodes = [f"a{i}" for i in range(width)]
    nodes += [f"b{i}" for i in range(width)]
    nodes += [f"s{i}" for i in range(width)]
    nodes += [f"co{i}" for i in range(width)]
    nodes += [f"ci{i}" for i in range(1, width)]

    h = [0] * len(nodes)
    j = zero_matrix(len(nodes))
    idx = {name: i for i, name in enumerate(nodes)}

    add_block(h, j, ha, [idx["a0"], idx["b0"], idx["s0"], idx["co0"]])
    for bit in range(1, width):
        add_block(h, j, fa, [idx[f"a{bit}"], idx[f"b{bit}"], idx[f"ci{bit}"], idx[f"s{bit}"], idx[f"co{bit}"]])
        set_edge(j, idx[f"co{bit - 1}"], idx[f"ci{bit}"], link_encoded)

    entity = "gen_adder8_split_q8_opt" if width == 8 else f"gen_adder{width}_split_q8_opt"
    return Hamiltonian(
        name=(
            f"ADDER{width}_SPLIT_CARRY_Q8_OPT"
            if fmt.name == "fixed-q8"
            else f"ADDER{width}_SPLIT_CARRY_{fmt.name.upper().replace('-', '_')}_OPT"
        ),
        entity=entity,
        nodes=nodes,
        h=h,
        j=j,
        valid_states=None,
        source=(
            f"Composed {width}-bit adder from {fmt.name} MILP-optimized HA/FA blocks with split carry nodes; "
            f"inter-block equality link J={link_encoded}/2^{fmt.frac_bits}, link gap={2 * link_encoded}/2^{fmt.frac_bits}"
        ),
        field_frac_bits=fmt.frac_bits,
        weight_scale=fmt.name,
    )


def verify_split_adder(ham: Hamiltonian, width: int) -> tuple[int, int]:
    idx = {name: i for i, name in enumerate(ham.nodes)}
    energies = set()
    for aval in range(1 << width):
        for bval in range(1 << width):
            bits = [0] * len(ham.nodes)
            carry = 0
            for bit in range(width):
                bits[idx[f"a{bit}"]] = (aval >> bit) & 1
                bits[idx[f"b{bit}"]] = (bval >> bit) & 1
                if bit > 0:
                    bits[idx[f"ci{bit}"]] = carry
                total = bits[idx[f"a{bit}"]] + bits[idx[f"b{bit}"]] + carry
                bits[idx[f"s{bit}"]] = total & 1
                carry = (total >> 1) & 1
                bits[idx[f"co{bit}"]] = carry
            energies.add(energy(ham.h, ham.j, tuple(bits)))
    if len(energies) != 1:
        raise AssertionError(f"{ham.name}: valid states do not share one energy: {sorted(energies)[:8]}")
    return (1 << (2 * width)), next(iter(energies))


def write_report(
    path: Path,
    optimized: list[OptimizedGate],
    adder: Hamiltonian,
    width: int,
    link_encoded: int,
    fmt: CoefficientFormat,
) -> None:
    denominator = 1 << fmt.frac_bits

    def encoded_real(value: int) -> float:
        return value / float(denominator)

    def encoded_matrix(matrix: list[list[int]]) -> list[list[float]]:
        return [[encoded_real(value) for value in row] for row in matrix]

    def physical_edges(ham: Hamiltonian) -> list[dict[str, float | int | str]]:
        return [
            {
                "i": edge["i"],
                "j": edge["j"],
                "encoded": edge["value"],
                "physical": encoded_real(edge["value"]),
            }
            for edge in nonzero_edges(ham)
        ]

    def plain(value):
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, list):
            return [plain(item) for item in value]
        if isinstance(value, dict):
            return {key: plain(item) for key, item in value.items()}
        return value

    adder_vectors, adder_energy = verify_split_adder(adder, width)
    data = {
        "coefficient_format": fmt.name,
        "adder_width": width,
        "encoding": f"encoded integers; physical_value = encoded / {denominator}",
        "objective": (
            "MILP stage 1 maximizes minimum invalid-minus-valid gate energy gap. "
            "MILP stage 2 fixes that optimum and minimizes carry-boundary coefficient L1. "
            "The adder lowers block-to-block gap by splitting carry nodes and adding weak equality links."
        ),
        "link_encoded": link_encoded,
        "link_physical": encoded_real(link_encoded),
        "link_gap_encoded": 2 * link_encoded,
        "link_gap_physical": encoded_real(2 * link_encoded),
        "optimized_gates": [
            {
                "name": item.ham.name,
                "nodes": item.ham.nodes,
                "h_encoded": item.ham.h,
                "h_physical": [encoded_real(value) for value in item.ham.h],
                "J_encoded": item.ham.j,
                "J_physical": encoded_matrix(item.ham.j),
                "edges_encoded": nonzero_edges(item.ham),
                "edges_physical": physical_edges(item.ham),
                "gate_gap_encoded": item.gamma_encoded,
                "gate_gap_physical": encoded_real(item.gamma_encoded),
                "boundary_abs_encoded": item.boundary_abs_encoded,
                "boundary_abs_physical": encoded_real(item.boundary_abs_encoded),
                "coeff_abs_encoded": item.coeff_abs_encoded,
                "coeff_abs_physical": encoded_real(item.coeff_abs_encoded),
            }
            for item in optimized
        ],
        "adder": {
            "name": adder.name,
            "entity": adder.entity,
            "nodes": adder.nodes,
            "node_count": len(adder.nodes),
            "h_encoded": adder.h,
            "h_physical": [encoded_real(value) for value in adder.h],
            "J_encoded": adder.j,
            "J_physical": encoded_matrix(adder.j),
            "edges_encoded": nonzero_edges(adder),
            "edges_physical": physical_edges(adder),
            "valid_vectors": adder_vectors,
            "valid_energy_encoded": adder_energy,
            "valid_energy_physical": encoded_real(adder_energy),
        },
    }
    path.write_text(json.dumps(plain(data), indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize Hamiltonians with MILP and emit a split-carry synthesized adder.")
    parser.add_argument("--coefficient-format", choices=["fixed-q8", "fp8-e4m3", "fp8-e3m4", "fp8-e2m5"], default="fixed-q8")
    parser.add_argument("--fp8-bias", type=int, default=None)
    parser.add_argument("--coeff-max-q8", type=int, default=512)
    parser.add_argument("--coeff-max-value", type=parse_fraction, default=None)
    parser.add_argument("--adder-width", type=int, default=8)
    parser.add_argument("--link-q8", type=int, default=None, help="Deprecated: encoded Q8 link value. Prefer --link-value.")
    parser.add_argument("--link-value", type=parse_fraction, default=Fraction(1, 16))
    parser.add_argument("--vhdl", type=Path, default=ROOT / "sim" / "experiments" / "generated_networks_fp8_optimized_split.vhd")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "optimized_fp8_hamiltonians.json")
    args = parser.parse_args()

    if args.adder_width < 2:
        raise ValueError("--adder-width must be at least 2")

    coeff_max_q8 = args.coeff_max_q8
    if args.coeff_max_value is not None:
        coeff_max_q8_fraction = args.coeff_max_value * 256
        if coeff_max_q8_fraction.denominator != 1:
            raise ValueError(f"{args.coeff_max_value} cannot be encoded as a Q8 coefficient bound")
        coeff_max_q8 = coeff_max_q8_fraction.numerator

    fmt = coefficient_format(args.coefficient_format, coeff_max_q8, args.fp8_bias)
    if args.link_q8 is not None:
        link_encoded = args.link_q8 if fmt.name == "fixed-q8" else args.link_q8 * (1 << (fmt.frac_bits - 8))
    else:
        link_encoded_fraction = args.link_value * (1 << fmt.frac_bits)
        if link_encoded_fraction.denominator != 1:
            raise ValueError(f"{args.link_value} cannot be encoded exactly with {fmt.frac_bits} fractional bits")
        link_encoded = link_encoded_fraction.numerator

    if fmt.values is not None and link_encoded not in fmt.values:
        raise ValueError(f"link value {float(args.link_value)} is not representable in {fmt.name}")

    ha = q8_ha(coeff_max_q8, fmt)
    fa = q8_fa(coeff_max_q8, fmt)
    adder = split_carry_adder(args.adder_width, ha.ham, fa.ham, link_encoded, fmt)
    verify_split_adder(adder, args.adder_width)

    args.vhdl.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    emit_vhdl([ha.ham, fa.ham, adder], args.vhdl)
    write_report(args.report, [ha, fa], adder, args.adder_width, link_encoded, fmt)

    denominator = 1 << fmt.frac_bits
    print(f"Coefficient format: {fmt.name}")
    print(f"Adder width: {args.adder_width}")
    print(f"HA gate gap: {ha.gamma_encoded}/{denominator} = {ha.gamma_encoded / denominator}")
    print(f"FA gate gap: {fa.gamma_encoded}/{denominator} = {fa.gamma_encoded / denominator}")
    print(f"Inter-block link gap: {2 * link_encoded}/{denominator} = {(2 * link_encoded) / denominator}")
    print(f"Wrote {args.vhdl}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
