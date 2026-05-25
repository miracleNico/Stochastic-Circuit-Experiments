from pathlib import Path

from generate_hamiltonians import fa_block, ha_block, seed_for


ROOT = Path(__file__).resolve().parents[1]


def add_directed_block(
    h: list[int],
    w: list[dict[int, int]],
    block,
    indices: list[int],
    active_mask: set[int] | None = None,
) -> None:
    active = set(indices) if active_mask is None else active_mask
    for local_i, global_i in enumerate(indices):
        if global_i in active:
            h[global_i] += block.h[local_i]
            for local_j, global_j in enumerate(indices):
                if local_i != local_j:
                    value = block.j[local_i][local_j]
                    if value:
                        w[global_i][global_j] = w[global_i].get(global_j, 0) + value


def group_for_node(name: str) -> str:
    if name.startswith("q"):
        return f"copy{name[1:]}"
    if name[0] in {"a", "b", "s", "c"}:
        return f"block{name[1]}"
    return "clamp"


def emit(
    path: Path,
    width: int = 4,
    copy_weight: int = 4,
    reverse_copy_weight: int = 0,
    ha=None,
    fa=None,
    entity: str = "gen_adder4_shadow1_windowed",
    seed_name: str | None = None,
    field_frac_bits: int = 0,
) -> None:
    if ha is None:
        ha = ha_block()
    if fa is None:
        fa = fa_block()

    nodes = [f"a{i}" for i in range(width)]
    nodes += [f"b{i}" for i in range(width)]
    nodes += [f"s{i}" for i in range(width)]
    nodes += [f"c{i}" for i in range(width)]
    nodes += [f"q{i}" for i in range(1, width)]
    idx = {name: i for i, name in enumerate(nodes)}
    n = len(nodes)

    h = [0] * n
    w = [dict() for _ in range(n)]

    add_directed_block(h, w, ha, [idx["a0"], idx["b0"], idx["s0"], idx["c0"]])
    for bit in range(1, width):
        # q{bit} is a frozen shadow carry-in during the downstream block window.
        # The FA nodes read it, but the FA is not allowed to update q{bit}.
        active_nodes = {idx[f"a{bit}"], idx[f"b{bit}"], idx[f"s{bit}"], idx[f"c{bit}"]}
        add_directed_block(
            h,
            w,
            fa,
            [idx[f"a{bit}"], idx[f"b{bit}"], idx[f"q{bit}"], idx[f"s{bit}"], idx[f"c{bit}"]],
            active_nodes,
        )

    for bit in range(1, width):
        w[idx[f"q{bit}"]][idx[f"c{bit - 1}"]] = copy_weight
        if reverse_copy_weight:
            w[idx[f"c{bit - 1}"]][idx[f"q{bit}"]] = reverse_copy_weight

    if seed_name is None:
        seed_name = f"ADDER4_SHADOW1_W{copy_weight}_R{reverse_copy_weight}"
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
        f"        FIELD_FRAC_BITS : natural := {field_frac_bits}",
        "    );",
        "    port (",
        "        clk         : in  std_logic;",
        "        rst         : in  std_logic;",
        "        enable      : in  std_logic;",
    ]
    for bit in range(width):
        lines.append(f"        block_en{bit}   : in  std_logic;")
    for bit in range(1, width):
        lines.append(f"        copy_en{bit}    : in  std_logic;")
    lines.extend(
        [
        "        block_rnd   : in  natural;",
        "        copy_rnd    : in  natural;",
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
    )
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
            "        variable selected_en_v : std_logic;",
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
            "                selected_en_v := '0';",
        ]
    )

    for i, name in enumerate(nodes):
        group = group_for_node(name)
        if group == "clamp":
            continue
        if group.startswith("block"):
            lines.append(f"                if selected_v = {i} then selected_en_v := block_en{group[5:]}; end if;")
        elif group.startswith("copy"):
            lines.append(f"                if selected_v = {i} then selected_en_v := copy_en{group[4:]}; end if;")

    lines.extend(
        [
            "                if clamp_en(selected_v) = '0' and selected_en_v = '1' and not found_v then",
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
        neighbors = sorted(w[i].items())
        if neighbors:
            entries = ", ".join(f"{pos} => spin_s({src})" for pos, (src, _value) in enumerate(neighbors))
            lines.append(f"    neighbors_{i} <= ({entries}, others => '0');")
        else:
            lines.append(f"    neighbors_{i} <= (others => '0');")
    lines.append("")

    for i, name in enumerate(nodes):
        neighbors = sorted(w[i].items())
        weights = [value for _src, value in neighbors] + [0] * (32 - len(neighbors))
        is_copy_node = name.startswith("q")
        rnd_port = "copy_rnd" if is_copy_node else "block_rnd"
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
                f"            rnd_weight_i => {rnd_port},",
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    emit(ROOT / "src" / "generated_shadow1_adder4.vhd")


if __name__ == "__main__":
    main()
