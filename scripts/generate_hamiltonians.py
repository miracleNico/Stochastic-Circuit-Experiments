import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Hamiltonian:
    name: str
    entity: str
    nodes: list[str]
    h: list[int]
    j: list[list[int]]
    valid_states: list[tuple[int, ...]] | None
    source: str
    energy_gap: int | float | None = None
    valid_energy: int | float | None = None
    field_frac_bits: int = 0
    weight_scale: str = "1"


def zero_matrix(n: int) -> list[list[int]]:
    return [[0 for _ in range(n)] for _ in range(n)]


def set_edge(j: list[list[int]], a: int, b: int, value: int) -> None:
    j[a][b] = value
    j[b][a] = value


def energy(h: list[int], j: list[list[int]], bits: tuple[int, ...]) -> int:
    m = [1 if bit else -1 for bit in bits]
    total = -sum(h[i] * m[i] for i in range(len(h)))
    for i in range(len(h)):
        for k in range(i + 1, len(h)):
            total -= j[i][k] * m[i] * m[k]
    return total


def annotate_gap(ham: Hamiltonian) -> Hamiltonian:
    if ham.valid_states is None:
        return ham

    valid = set(ham.valid_states)
    valid_energies = {energy(ham.h, ham.j, bits) for bits in valid}
    invalid_energies = {
        energy(ham.h, ham.j, bits)
        for bits in product([0, 1], repeat=len(ham.nodes))
        if bits not in valid
    }
    if len(valid_energies) != 1:
        raise ValueError(f"{ham.name}: valid states do not share one energy: {valid_energies}")
    valid_energy = next(iter(valid_energies))
    invalid_min = min(invalid_energies) if invalid_energies else valid_energy
    if invalid_min <= valid_energy:
        raise ValueError(f"{ham.name}: invalid minimum {invalid_min} <= valid energy {valid_energy}")

    ham.valid_energy = valid_energy
    ham.energy_gap = invalid_min - valid_energy
    return ham


def three_node_gate(name: str, entity: str, h: list[int], edges: tuple[int, int, int], fn) -> Hamiltonian:
    j = zero_matrix(3)
    set_edge(j, 0, 1, edges[0])
    set_edge(j, 0, 2, edges[1])
    set_edge(j, 1, 2, edges[2])
    valid = [(a, b, fn(a, b)) for a, b in product([0, 1], repeat=2)]
    return annotate_gap(Hamiltonian(name, entity, ["A", "B", "Y"], h, j, valid, "3-node LP block"))


def ha_block() -> Hamiltonian:
    j = zero_matrix(4)
    edges = {
        (0, 1): -1,
        (0, 2): 1,
        (0, 3): 2,
        (1, 2): 1,
        (1, 3): 2,
        (2, 3): -2,
    }
    for (a, b), value in edges.items():
        set_edge(j, a, b, value)
    valid = [(a, b, a ^ b, a & b) for a, b in product([0, 1], repeat=2)]
    return annotate_gap(Hamiltonian("HA_XOR", "gen_xor_gate", ["A", "B", "S", "C"], [1, 1, -1, -2], j, valid, "4-node LP HA/XOR block"))


def xnor_block() -> Hamiltonian:
    j = zero_matrix(4)
    edges = {
        (0, 1): -1,
        (0, 2): -1,
        (0, 3): 2,
        (1, 2): -1,
        (1, 3): 2,
        (2, 3): 2,
    }
    for (a, b), value in edges.items():
        set_edge(j, a, b, value)
    valid = [(a, b, 1 - (a ^ b), a & b) for a, b in product([0, 1], repeat=2)]
    return annotate_gap(Hamiltonian("XNOR", "gen_xnor_gate", ["A", "B", "Y", "C"], [1, 1, 1, -2], j, valid, "4-node LP XNOR block"))


def fa_block() -> Hamiltonian:
    j = zero_matrix(5)
    edges = {
        (0, 1): -1,
        (0, 2): -1,
        (0, 3): 1,
        (0, 4): 2,
        (1, 2): -1,
        (1, 3): 1,
        (1, 4): 2,
        (2, 3): 1,
        (2, 4): 2,
        (3, 4): -2,
    }
    for (a, b), value in edges.items():
        set_edge(j, a, b, value)
    valid = []
    for a, b, cin in product([0, 1], repeat=3):
        total = a + b + cin
        valid.append((a, b, cin, total & 1, (total >> 1) & 1))
    return annotate_gap(Hamiltonian("FA", "gen_fa_gate", ["A", "B", "CIN", "S", "COUT"], [0, 0, 0, 0, 0], j, valid, "5-node LP FA block"))


def add_block(global_h: list[int], global_j: list[list[int]], block: Hamiltonian, indices: list[int], scale: int) -> None:
    for local_i, global_i in enumerate(indices):
        global_h[global_i] += scale * block.h[local_i]
    for local_i, global_i in enumerate(indices):
        for local_j in range(local_i + 1, len(indices)):
            global_k = indices[local_j]
            value = scale * block.j[local_i][local_j]
            global_j[global_i][global_k] += value
            global_j[global_k][global_i] += value


def parse_fraction(text: str) -> Fraction:
    try:
        return Fraction(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid rational value: {text}") from exc


def scale_hamiltonian(ham: Hamiltonian, weight_scale: Fraction, frac_bits: int) -> Hamiltonian:
    encoded_factor = weight_scale * (1 << frac_bits)
    if encoded_factor.denominator != 1:
        raise ValueError(
            "weight_scale * 2^weight_frac_bits must be an integer so coefficients can be emitted as VHDL generics"
        )

    factor = encoded_factor.numerator
    if factor <= 0:
        raise ValueError("encoded coefficient factor must be positive")
    if factor == 1 and frac_bits == 0 and weight_scale == 1:
        ham.field_frac_bits = 0
        ham.weight_scale = "1"
        return ham

    scaled = Hamiltonian(
        ham.name,
        ham.entity,
        ham.nodes,
        [factor * value for value in ham.h],
        [[factor * value for value in row] for row in ham.j],
        ham.valid_states,
        f"{ham.source}, weight scale={weight_scale}, frac_bits={frac_bits}",
        None,
        None,
        frac_bits,
        str(weight_scale),
    )
    return annotate_gap(scaled) if scaled.valid_states is not None else scaled


def ripple_adder(
    width: int,
    entity: str,
    ha: Hamiltonian,
    fa: Hamiltonian,
    ha_scale: int = 1,
    fa_scale: int = 1,
) -> Hamiltonian:
    nodes = (
        [f"a{i}" for i in range(width)]
        + [f"b{i}" for i in range(width)]
        + [f"s{i}" for i in range(width)]
        + [f"c{i}" for i in range(1, width + 1)]
    )
    h = [0] * len(nodes)
    j = zero_matrix(len(nodes))

    def a(i: int) -> int: return i
    def b(i: int) -> int: return width + i
    def s(i: int) -> int: return 2 * width + i
    def c(i: int) -> int: return 3 * width + i - 1

    add_block(h, j, ha, [a(0), b(0), s(0), c(1)], ha_scale)
    for i in range(1, width):
        add_block(h, j, fa, [a(i), b(i), c(i), s(i), c(i + 1)], fa_scale)

    return Hamiltonian(
        f"ADDER{width}_RIPPLE",
        entity,
        nodes,
        h,
        j,
        None,
        f"Composed HA/FA {width}-bit ripple adder, HA scale={ha_scale}, FA scale={fa_scale}",
    )


def adder4(ha: Hamiltonian, fa: Hamiltonian, ha_scale: int = 1, fa_scale: int = 1) -> Hamiltonian:
    return ripple_adder(4, "gen_adder4", ha, fa, ha_scale, fa_scale)


def adder8(ha: Hamiltonian, fa: Hamiltonian, ha_scale: int = 1, fa_scale: int = 1) -> Hamiltonian:
    return ripple_adder(8, "gen_adder8", ha, fa, ha_scale, fa_scale)


def comb6_mixed(
    and_gate: Hamiltonian,
    or_gate: Hamiltonian,
    nand_gate: Hamiltonian,
    nor_gate: Hamiltonian,
    ha: Hamiltonian,
    xnor: Hamiltonian,
) -> Hamiltonian:
    nodes = [
        "x0", "x1", "x2", "x3", "x4", "x5",
        "u0_and", "u1_or", "u2_nand",
        "u3_xor", "u3_aux",
        "u4_xnor", "u4_aux",
        "v0_xor", "v0_aux",
        "v1_and", "v2_nor",
        "y1_or", "y2_xnor", "y2_aux", "y3_nand",
    ]
    idx = {name: i for i, name in enumerate(nodes)}
    h = [0] * len(nodes)
    j = zero_matrix(len(nodes))

    add_block(h, j, and_gate, [idx["x0"], idx["x1"], idx["u0_and"]], 1)
    add_block(h, j, or_gate, [idx["x2"], idx["x3"], idx["u1_or"]], 1)
    add_block(h, j, nand_gate, [idx["x4"], idx["x5"], idx["u2_nand"]], 1)
    add_block(h, j, ha, [idx["x0"], idx["x2"], idx["u3_xor"], idx["u3_aux"]], 1)
    add_block(h, j, xnor, [idx["x1"], idx["x5"], idx["u4_xnor"], idx["u4_aux"]], 1)
    add_block(h, j, ha, [idx["u0_and"], idx["u1_or"], idx["v0_xor"], idx["v0_aux"]], 1)
    add_block(h, j, and_gate, [idx["u2_nand"], idx["u3_xor"], idx["v1_and"]], 1)
    add_block(h, j, nor_gate, [idx["u1_or"], idx["u4_xnor"], idx["v2_nor"]], 1)
    add_block(h, j, or_gate, [idx["v1_and"], idx["v2_nor"], idx["y1_or"]], 1)
    add_block(h, j, xnor, [idx["u3_xor"], idx["u4_xnor"], idx["y2_xnor"], idx["y2_aux"]], 1)
    add_block(h, j, nand_gate, [idx["v0_xor"], idx["y2_xnor"], idx["y3_nand"]], 1)

    return Hamiltonian(
        "COMB6_MIXED",
        "gen_comb6_mixed",
        nodes,
        h,
        j,
        None,
        "Composed 6-input/4-output mixed combinational network from integer gate blocks",
    )


def bitcount8() -> Hamiltonian:
    nodes = [f"x{i}" for i in range(8)] + [f"y{i}" for i in range(4)]
    p = [1] * 8 + [-1, -2, -4, -8]
    # For z = sum(x_i bits) - unsigned(y), H = 2*z^2 gives integer Ising coefficients.
    offset = (sum(abs(v) for v in p if v < 0) - 8)
    h = [offset * value for value in p]
    j = zero_matrix(len(nodes))
    for i in range(len(nodes)):
        for k in range(i + 1, len(nodes)):
            set_edge(j, i, k, -(p[i] * p[k]))

    valid = []
    for xs in product([0, 1], repeat=8):
        total = sum(xs)
        ys = tuple((total >> bit) & 1 for bit in range(4))
        valid.append(xs + ys)
    return annotate_gap(Hamiltonian("BITCOUNT8", "gen_bitcount8", nodes, h, j, valid, "Exact squared bitcount constraint H=2*(sum(x)-y)^2"))


def hamiltonians(args) -> list[Hamiltonian]:
    frac_bits = getattr(args, "weight_frac_bits", 0)
    weight_scale = getattr(args, "weight_scale", Fraction(1, 1))

    and_gate = three_node_gate("AND", "gen_and_gate", [1, 1, -2], (-1, 2, 2), lambda a, b: a & b)
    or_gate = three_node_gate("OR", "gen_or_gate", [-1, -1, 2], (-1, 2, 2), lambda a, b: a | b)
    nand_gate = three_node_gate("NAND", "gen_nand_gate", [1, 1, 2], (-1, -2, -2), lambda a, b: 1 - (a & b))
    nor_gate = three_node_gate("NOR", "gen_nor_gate", [-1, -1, -2], (-1, -2, -2), lambda a, b: 1 - (a | b))
    ha = ha_block()
    xnor = xnor_block()
    fa = fa_block()
    base_hams = [
        and_gate,
        or_gate,
        nand_gate,
        nor_gate,
        ha,
        xnor,
        fa,
        adder4(ha, fa, args.ha_scale, args.fa_scale),
        adder8(ha, fa, args.ha_scale, args.fa_scale),
        comb6_mixed(and_gate, or_gate, nand_gate, nor_gate, ha, xnor),
        bitcount8(),
    ]
    return [scale_hamiltonian(ham, weight_scale, frac_bits) for ham in base_hams]


def nonzero_edges(ham: Hamiltonian) -> list[dict[str, int | str]]:
    edges = []
    for i, src in enumerate(ham.nodes):
        for k in range(i + 1, len(ham.nodes)):
            value = ham.j[i][k]
            if value:
                edges.append({"i": src, "j": ham.nodes[k], "value": value})
    return edges


def verify_ripple_adder(ham: Hamiltonian, width: int) -> None:
    expected_nodes = (
        [f"a{i}" for i in range(width)]
        + [f"b{i}" for i in range(width)]
        + [f"s{i}" for i in range(width)]
        + [f"c{i}" for i in range(1, width + 1)]
    )
    if ham.nodes != expected_nodes:
        raise ValueError(f"{ham.name}: node order changed")

    idx = {name: i for i, name in enumerate(ham.nodes)}
    energies = []
    for aval in range(1 << width):
        for bval in range(1 << width):
            bits = [0] * len(ham.nodes)
            carry_value = 0
            for bit in range(width):
                bits[idx[f"a{bit}"]] = (aval >> bit) & 1
                bits[idx[f"b{bit}"]] = (bval >> bit) & 1
                total_bit = bits[idx[f"a{bit}"]] + bits[idx[f"b{bit}"]] + carry_value
                bits[idx[f"s{bit}"]] = total_bit & 1
                carry_value = (total_bit >> 1) & 1
                bits[idx[f"c{bit + 1}"]] = carry_value
            energies.append(energy(ham.h, ham.j, tuple(bits)))
    if len(set(energies)) != 1:
        raise ValueError(f"{ham.name}: valid ripple states do not share one energy")


def verify_all(hams: list[Hamiltonian]) -> None:
    adder_widths = {
        "ADDER4_RIPPLE": 4,
        "ADDER8_RIPPLE": 8,
    }
    for ham in hams:
        if ham.name in adder_widths:
            verify_ripple_adder(ham, adder_widths[ham.name])
        elif ham.valid_states is not None:
            annotate_gap(ham)


def emit_vhdl(hams: list[Hamiltonian], path: Path) -> None:
    lines = [
        "library ieee;",
        "use ieee.std_logic_1164.all;",
        "use ieee.numeric_std.all;",
        "",
        "use work.inv_sc_pkg.all;",
        "",
    ]
    for ham in hams:
        lines.extend(emit_entity(ham))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def emit_entity(ham: Hamiltonian) -> list[str]:
    n = len(ham.nodes)
    lines = [
        "library ieee;",
        "use ieee.std_logic_1164.all;",
        "use ieee.numeric_std.all;",
        "",
        "use work.inv_sc_pkg.all;",
        "",
        f"entity {ham.entity} is",
        "    generic (",
        "        RND_WEIGHT   : natural := 0;",
        "        COUNTER_BITS : natural := 5;",
        f"        FIELD_FRAC_BITS : natural := {ham.field_frac_bits}",
        "    );",
        "    port (",
        "        clk         : in  std_logic;",
        "        rst         : in  std_logic;",
        "        enable      : in  std_logic;",
        f"        clamp_en    : in  std_logic_vector({n - 1} downto 0);",
        f"        clamp_value : in  std_logic_vector({n - 1} downto 0);",
        f"        spins       : out std_logic_vector({n - 1} downto 0)",
        "    );",
        "end entity;",
        "",
        f"architecture rtl of {ham.entity} is",
        f"    constant NODE_COUNT : natural := {n};",
        f"    signal spin_s      : std_logic_vector({n - 1} downto 0) := (others => '0');",
        f"    signal node_enable : std_logic_vector({n - 1} downto 0) := (others => '0');",
        f"    signal phase       : natural range 0 to {n - 1} := 0;",
        f"    signal sched_state : std_logic_vector(31 downto 0) := x\"{seed_for(ham.name, 0):08X}\";",
    ]
    for i in range(n):
        lines.append(f"    signal neighbors_{i} : spin_vector_t := (others => '0');")
        lines.append(f"    signal field_{i}     : field_t;")
        lines.append(f"    signal counter_{i}   : signed(COUNTER_BITS downto 0);")
    lines.extend([
        "begin",
        "    process (clk)",
        "        variable x : unsigned(31 downto 0);",
        "    begin",
        "        if rising_edge(clk) then",
        "            if rst = '1' then",
        "                phase <= 0;",
        f"                sched_state <= x\"{seed_for(ham.name, 0):08X}\";",
        "            elsif enable = '1' then",
        "                x := unsigned(sched_state);",
        "                x := x xor shift_left(x, 13);",
        "                x := x xor shift_right(x, 17);",
        "                x := x xor shift_left(x, 5);",
        "                sched_state <= std_logic_vector(x);",
        "                phase <= to_integer(unsigned(sched_state(15 downto 0))) mod NODE_COUNT;",
        "            end if;",
        "        end if;",
        "    end process;",
        "",
    ])
    lines.extend([
        "    process (all)",
        f"        variable enables_v  : std_logic_vector({n - 1} downto 0);",
        f"        variable selected_v : natural range 0 to {n - 1};",
        "        variable found_v    : boolean;",
        "    begin",
        "        enables_v := (others => '0');",
        "        if enable = '1' then",
        "            for i in 0 to NODE_COUNT - 1 loop",
        "                if clamp_en(i) = '1' then",
        "                    enables_v(i) := '1';",
        "                end if;",
        "            end loop;",
        "",
        "            found_v := false;",
        "            for offset in 0 to NODE_COUNT - 1 loop",
        "                selected_v := (phase + offset) mod NODE_COUNT;",
        "                if clamp_en(selected_v) = '0' and not found_v then",
        "                    enables_v(selected_v) := '1';",
        "                    found_v := true;",
        "                end if;",
        "            end loop;",
        "        end if;",
        "        node_enable <= enables_v;",
        "    end process;",
        "",
    ])
    for i in range(n):
        neighbors = [(k, ham.j[i][k]) for k in range(n) if ham.j[i][k] != 0]
        if neighbors:
            entries = ", ".join(f"{pos} => spin_s({idx})" for pos, (idx, _w) in enumerate(neighbors))
            lines.append(f"    neighbors_{i} <= ({entries}, others => '0');")
        else:
            lines.append(f"    neighbors_{i} <= (others => '0');")
    lines.append("")
    for i in range(n):
        neighbors = [(k, ham.j[i][k]) for k in range(n) if ham.j[i][k] != 0]
        weights = [w for _k, w in neighbors] + [0] * (32 - len(neighbors))
        lines.extend([
            f"    node_{i} : entity work.spin_node",
            "        generic map (",
            f"            NUM_INPUTS   => {len(neighbors)},",
            f"            BIAS         => {ham.h[i]},",
        ])
        for wi, value in enumerate(weights):
            suffix = "," if wi < 31 else ","
            lines.append(f"            W{wi:<2}          => {value}{suffix}")
        lines.extend([
            "            FIELD_FRAC_BITS => FIELD_FRAC_BITS,",
            "            RND_WEIGHT   => RND_WEIGHT,",
            "            COUNTER_BITS => COUNTER_BITS,",
            f"            SEED         => x\"{seed_for(ham.name, i + 1):08X}\"",
            "        )",
            "        port map (",
            "            clk         => clk,",
            "            rst         => rst,",
            f"            enable      => node_enable({i}),",
            f"            clamp_en    => clamp_en({i}),",
            f"            clamp_value => clamp_value({i}),",
            f"            neighbors   => neighbors_{i},",
            f"            spin_o      => spin_s({i}),",
            f"            field_o     => field_{i},",
            f"            counter_o   => counter_{i}",
            "        );",
            "",
        ])
    lines.extend([
        "    spins <= spin_s;",
        "end architecture;",
    ])
    return lines


def seed_for(name: str, index: int) -> int:
    value = 0x9E3779B9 ^ (index * 0x85EBCA6B)
    for ch in name.encode("utf-8"):
        value ^= ch
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value or 1


def emit_reports(hams: list[Hamiltonian], json_path: Path, md_path: Path) -> None:
    def matrix_text(matrix: list[list[int]]) -> list[str]:
        width = max(len(str(value)) for row in matrix for value in row)
        return [
            "[" + " ".join(f"{value:>{width}}" for value in row) + "]"
            for row in matrix
        ]

    data = []
    for ham in hams:
        data.append(
            {
                "name": ham.name,
                "entity": ham.entity,
                "nodes": ham.nodes,
                "node_count": len(ham.nodes),
                "h": ham.h,
                "J": ham.j,
                "edges": nonzero_edges(ham),
                "source": ham.source,
                "valid_energy": ham.valid_energy,
                "energy_gap": ham.energy_gap,
                "field_frac_bits": ham.field_frac_bits,
                "weight_scale": ham.weight_scale,
            }
        )
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    lines = [
        "# Hamiltonian coefficients",
        "",
        "All coefficients use bipolar spins with logic 0 -> -1 and logic 1 -> +1.",
        "",
        "Adder and bitcount note:",
        "",
        "The paper uses bitcount primarily to reduce multiplier node count by removing vertical internal adder connections.",
        "For adders, the direct n-bit adder row with 3n + 1 nodes is already the minimum-node direct Hamiltonian form.",
        "This project intentionally emits HA/FA-composed ripple adders for clarity and block-scaling experiments,",
        "so `ADDER4_RIPPLE` uses 16 nodes and `ADDER8_RIPPLE` uses 32 nodes.",
        "",
    ]
    for item in data:
        lines.extend([
            f"## {item['name']}",
            "",
            f"entity: {item['entity']}",
            f"source: {item['source']}",
            f"weight_scale: {item['weight_scale']}",
            f"field_frac_bits: {item['field_frac_bits']}",
            f"nodes ({item['node_count']}): {', '.join(item['nodes'])}",
            f"valid_energy: {item['valid_energy']}",
            f"energy_gap: {item['energy_gap']}",
            "",
            "h:",
            "```text",
            "[" + ", ".join(str(v) for v in item["h"]) + "]",
            "```",
            "",
            "J:",
            "```text",
            *matrix_text(item["J"]),
            "```",
            "",
        ])
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate VHDL Hamiltonian networks and coefficient reports.")
    parser.add_argument("--ha-scale", type=int, default=1)
    parser.add_argument("--fa-scale", type=int, default=1)
    parser.add_argument("--weight-frac-bits", type=int, default=0)
    parser.add_argument("--weight-scale", type=parse_fraction, default=Fraction(1, 1))
    parser.add_argument("--vhdl", type=Path, default=ROOT / "src" / "generated_networks.vhd")
    parser.add_argument("--json", type=Path, default=ROOT / "reports" / "hamiltonians.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports" / "hamiltonians.md")
    args = parser.parse_args()

    hams = hamiltonians(args)
    verify_all(hams)

    args.vhdl.parent.mkdir(parents=True, exist_ok=True)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)

    emit_vhdl(hams, args.vhdl)
    emit_reports(hams, args.json, args.markdown)
    print(f"Wrote {args.vhdl}")
    print(f"Wrote {args.json}")
    print(f"Wrote {args.markdown}")


if __name__ == "__main__":
    main()
