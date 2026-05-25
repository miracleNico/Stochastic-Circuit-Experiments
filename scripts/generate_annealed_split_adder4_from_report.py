import argparse
import json
import math
import re
from fractions import Fraction
from pathlib import Path

from generate_hamiltonians import seed_for


ROOT = Path(__file__).resolve().parents[1]


def parse_fraction(text: str) -> Fraction:
    try:
        return Fraction(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid rational value: {text}") from exc


def denominator_from_report(data: dict) -> int:
    match = re.search(r"encoded\s*/\s*(\d+)", data["encoding"])
    if match is None:
        raise ValueError("could not infer encoded denominator from report")
    denominator = int(match.group(1))
    if denominator <= 0 or denominator & (denominator - 1):
        raise ValueError(f"denominator is not a power of two: {denominator}")
    return denominator


def stage_for_node(name: str) -> int:
    if name[0] in {"a", "b", "s"}:
        return int(name[1:])
    if name.startswith("co"):
        return int(name[2:])
    if name.startswith("ci"):
        return int(name[2:])
    raise ValueError(f"cannot infer stage for {name}")


def apply_link_value(nodes: list[str], j: list[list[int]], link_encoded: int) -> None:
    idx = {name: i for i, name in enumerate(nodes)}
    for bit in range(1, 4):
        a = idx[f"co{bit - 1}"]
        b = idx[f"ci{bit}"]
        j[a][b] = link_encoded
        j[b][a] = link_encoded


def emit_annealed_split_adder4(report: Path, output: Path, link_value: Fraction | None) -> None:
    data = json.loads(report.read_text(encoding="utf-8"))
    denominator = denominator_from_report(data)
    frac_bits = int(math.log2(denominator))
    adder = data["adder"]
    nodes = adder["nodes"]
    h = [int(value) for value in adder["h_encoded"]]
    j = [[int(value) for value in row] for row in adder["J_encoded"]]

    if link_value is not None:
        link_encoded_fraction = link_value * denominator
        if link_encoded_fraction.denominator != 1:
            raise ValueError(f"{link_value} cannot be encoded with denominator {denominator}")
        apply_link_value(nodes, j, link_encoded_fraction.numerator)

    n = len(nodes)
    entity = "gen_adder4_split_anneal"
    seed_name = f"{adder['name']}_ANNEAL"
    lines = [
        "library ieee;",
        "use ieee.std_logic_1164.all;",
        "use ieee.numeric_std.all;",
        "",
        "use work.inv_sc_pkg.all;",
        "",
        f"entity {entity} is",
        "    generic (",
        "        COUNTER_BITS : natural := 5;",
        f"        FIELD_FRAC_BITS : natural := {frac_bits}",
        "    );",
        "    port (",
        "        clk         : in  std_logic;",
        "        rst         : in  std_logic;",
        "        enable      : in  std_logic;",
        "        stage_rnd0  : in  natural;",
        "        stage_rnd1  : in  natural;",
        "        stage_rnd2  : in  natural;",
        "        stage_rnd3  : in  natural;",
        "        stage_en0   : in  std_logic;",
        "        stage_en1   : in  std_logic;",
        "        stage_en2   : in  std_logic;",
        "        stage_en3   : in  std_logic;",
        f"        clamp_en    : in  std_logic_vector({n - 1} downto 0);",
        f"        clamp_value : in  std_logic_vector({n - 1} downto 0);",
        f"        spins       : out std_logic_vector({n - 1} downto 0)",
        "    );",
        "end entity;",
        "",
        f"architecture rtl of {entity} is",
        f"    constant NODE_COUNT : natural := {n};",
        f"    signal spin_s      : std_logic_vector({n - 1} downto 0) := (others => '0');",
        f"    signal node_enable : std_logic_vector({n - 1} downto 0) := (others => '0');",
        f"    signal phase       : natural range 0 to {n - 1} := 0;",
        f"    signal sched_state : std_logic_vector(31 downto 0) := x\"{seed_for(seed_name, 0):08X}\";",
    ]

    for i in range(n):
        lines.append(f"    signal neighbors_{i} : spin_vector_t := (others => '0');")
        lines.append(f"    signal field_{i}     : field_t;")
        lines.append(f"    signal counter_{i}   : signed(COUNTER_BITS downto 0);")

    lines.extend(
        [
            "begin",
            "    process (clk)",
            "        variable x : unsigned(31 downto 0);",
            "    begin",
            "        if rising_edge(clk) then",
            "            if rst = '1' then",
            "                phase <= 0;",
            f"                sched_state <= x\"{seed_for(seed_name, 0):08X}\";",
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
            "    process (all)",
            f"        variable enables_v  : std_logic_vector({n - 1} downto 0);",
            f"        variable selected_v : natural range 0 to {n - 1};",
            "        variable found_v    : boolean;",
            "        variable selected_stage_en_v : std_logic;",
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
        ]
    )

    for i, name in enumerate(nodes):
        stage = stage_for_node(name)
        lines.append(f"                if selected_v = {i} then selected_stage_en_v := stage_en{stage}; end if;")

    lines.extend(
        [
            "                if clamp_en(selected_v) = '0' and selected_stage_en_v = '1' and not found_v then",
            "                    enables_v(selected_v) := '1';",
            "                    found_v := true;",
            "                end if;",
            "                selected_stage_en_v := '0';",
            "            end loop;",
            "        end if;",
            "        node_enable <= enables_v;",
            "    end process;",
            "",
        ]
    )

    for i in range(n):
        neighbors = [(k, j[i][k]) for k in range(n) if j[i][k] != 0]
        if neighbors:
            entries = ", ".join(f"{pos} => spin_s({idx})" for pos, (idx, _w) in enumerate(neighbors))
            lines.append(f"    neighbors_{i} <= ({entries}, others => '0');")
        else:
            lines.append(f"    neighbors_{i} <= (others => '0');")
    lines.append("")

    for i, name in enumerate(nodes):
        neighbors = [(k, j[i][k]) for k in range(n) if j[i][k] != 0]
        weights = [w for _k, w in neighbors] + [0] * (32 - len(neighbors))
        stage = stage_for_node(name)
        lines.extend(
            [
                f"    node_{i} : entity work.spin_node",
                "        generic map (",
                f"            NUM_INPUTS      => {len(neighbors)},",
                f"            BIAS            => {h[i]},",
            ]
        )
        for wi, value in enumerate(weights):
            lines.append(f"            W{wi:<2}             => {value},")
        lines.extend(
            [
                "            FIELD_FRAC_BITS => FIELD_FRAC_BITS,",
                "            RND_WEIGHT      => 0,",
                "            USE_DYNAMIC_RND => true,",
                "            COUNTER_BITS    => COUNTER_BITS,",
                f"            SEED            => x\"{seed_for(seed_name, i + 1):08X}\"",
                "        )",
                "        port map (",
                "            clk          => clk,",
                "            rst          => rst,",
                f"            enable       => node_enable({i}),",
                f"            rnd_weight_i => stage_rnd{stage},",
                f"            clamp_en     => clamp_en({i}),",
                f"            clamp_value  => clamp_value({i}),",
                f"            neighbors    => neighbors_{i},",
                f"            spin_o       => spin_s({i}),",
                f"            field_o      => field_{i},",
                f"            counter_o    => counter_{i}",
                "        );",
                "",
            ]
        )

    lines.extend(["    spins <= spin_s;", "end architecture;", ""])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit a dynamic-noise 4-bit split-carry adder from an optimizer report.")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "src" / "generated_annealed_split_adder4.vhd")
    parser.add_argument("--link-value", type=parse_fraction, default=None)
    args = parser.parse_args()
    emit_annealed_split_adder4(args.report, args.output, args.link_value)


if __name__ == "__main__":
    main()
