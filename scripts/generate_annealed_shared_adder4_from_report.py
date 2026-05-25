import argparse
import json
import math
import re
from pathlib import Path

from generate_hamiltonians import seed_for, zero_matrix


def denominator_from_report(data: dict) -> int:
    match = re.search(r"encoded\s*/\s*(\d+)", data["encoding"])
    if match is None:
        raise ValueError("could not infer encoded denominator from report")
    return int(match.group(1))


def add_block(h: list[int], j: list[list[int]], block: dict, indices: list[int]) -> None:
    block_h = block["h_encoded"]
    block_j = block["J_encoded"]
    for local_i, global_i in enumerate(indices):
        h[global_i] += int(block_h[local_i])
    for local_i, global_i in enumerate(indices):
        for local_j in range(local_i + 1, len(indices)):
            global_j = indices[local_j]
            value = int(block_j[local_i][local_j])
            j[global_i][global_j] += value
            j[global_j][global_i] += value


def stage_for_node(name: str) -> int:
    if name[0] in {"a", "b", "s"}:
        return int(name[1:])
    if name[0] == "c":
        return int(name[1:]) - 1
    raise ValueError(f"cannot infer stage for {name}")


def emit(report: Path, output: Path) -> None:
    data = json.loads(report.read_text(encoding="utf-8"))
    denominator = denominator_from_report(data)
    frac_bits = int(math.log2(denominator))
    gates = {gate["name"]: gate for gate in data["optimized_gates"]}
    ha = next(gate for name, gate in gates.items() if name.startswith("HA_"))
    fa = next(gate for name, gate in gates.items() if name.startswith("FA_"))

    width = 4
    nodes = [f"a{i}" for i in range(width)]
    nodes += [f"b{i}" for i in range(width)]
    nodes += [f"s{i}" for i in range(width)]
    nodes += [f"c{i}" for i in range(1, width + 1)]
    idx = {name: i for i, name in enumerate(nodes)}
    h = [0] * len(nodes)
    j = zero_matrix(len(nodes))

    add_block(h, j, ha, [idx["a0"], idx["b0"], idx["s0"], idx["c1"]])
    for bit in range(1, width):
        add_block(h, j, fa, [idx[f"a{bit}"], idx[f"b{bit}"], idx[f"c{bit}"], idx[f"s{bit}"], idx[f"c{bit + 1}"]])

    n = len(nodes)
    entity = "gen_adder4_shared_stage_anneal"
    seed_name = f"ADDER4_SHARED_{ha['name']}_{fa['name']}"
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
            "                selected_stage_en_v := '0';",
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
            entries = ", ".join(f"{pos} => spin_s({idx_})" for pos, (idx_, _w) in enumerate(neighbors))
            lines.append(f"    neighbors_{i} <= ({entries}, others => '0');")
        else:
            lines.append(f"    neighbors_{i} <= (others => '0');")
    lines.append("")

    for i, name in enumerate(nodes):
        neighbors = [(k, j[i][k]) for k in range(n) if j[i][k] != 0]
        weights = [w for _idx, w in neighbors] + [0] * (32 - len(neighbors))
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
    parser = argparse.ArgumentParser(description="Emit shared-carry staged 4-bit adder from optimized HA/FA report.")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("src/generated_annealed_shared_adder4.vhd"))
    args = parser.parse_args()
    emit(args.report, args.output)


if __name__ == "__main__":
    main()
