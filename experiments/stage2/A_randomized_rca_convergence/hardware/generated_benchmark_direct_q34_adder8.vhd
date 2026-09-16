library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity gen_adder8 is
    generic (
        RND_WEIGHT   : natural := 0;
        COUNTER_BITS : natural := 5;
        FIELD_FRAC_BITS : natural := 4
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        enable      : in  std_logic;
        clamp_en    : in  std_logic_vector(31 downto 0);
        clamp_value : in  std_logic_vector(31 downto 0);
        spins       : out std_logic_vector(31 downto 0)
    );
end entity;

architecture rtl of gen_adder8 is
    constant NODE_COUNT : natural := 32;
    signal spin_s      : std_logic_vector(31 downto 0) := (others => '0');
    signal node_enable : std_logic_vector(31 downto 0) := (others => '0');
    signal phase       : natural range 0 to 31 := 0;
    signal sched_state : std_logic_vector(31 downto 0) := x"488E4364";
    signal neighbors_0 : spin_vector_t := (others => '0');
    signal field_0     : field_t;
    signal counter_0   : signed(COUNTER_BITS downto 0);
    signal neighbors_1 : spin_vector_t := (others => '0');
    signal field_1     : field_t;
    signal counter_1   : signed(COUNTER_BITS downto 0);
    signal neighbors_2 : spin_vector_t := (others => '0');
    signal field_2     : field_t;
    signal counter_2   : signed(COUNTER_BITS downto 0);
    signal neighbors_3 : spin_vector_t := (others => '0');
    signal field_3     : field_t;
    signal counter_3   : signed(COUNTER_BITS downto 0);
    signal neighbors_4 : spin_vector_t := (others => '0');
    signal field_4     : field_t;
    signal counter_4   : signed(COUNTER_BITS downto 0);
    signal neighbors_5 : spin_vector_t := (others => '0');
    signal field_5     : field_t;
    signal counter_5   : signed(COUNTER_BITS downto 0);
    signal neighbors_6 : spin_vector_t := (others => '0');
    signal field_6     : field_t;
    signal counter_6   : signed(COUNTER_BITS downto 0);
    signal neighbors_7 : spin_vector_t := (others => '0');
    signal field_7     : field_t;
    signal counter_7   : signed(COUNTER_BITS downto 0);
    signal neighbors_8 : spin_vector_t := (others => '0');
    signal field_8     : field_t;
    signal counter_8   : signed(COUNTER_BITS downto 0);
    signal neighbors_9 : spin_vector_t := (others => '0');
    signal field_9     : field_t;
    signal counter_9   : signed(COUNTER_BITS downto 0);
    signal neighbors_10 : spin_vector_t := (others => '0');
    signal field_10     : field_t;
    signal counter_10   : signed(COUNTER_BITS downto 0);
    signal neighbors_11 : spin_vector_t := (others => '0');
    signal field_11     : field_t;
    signal counter_11   : signed(COUNTER_BITS downto 0);
    signal neighbors_12 : spin_vector_t := (others => '0');
    signal field_12     : field_t;
    signal counter_12   : signed(COUNTER_BITS downto 0);
    signal neighbors_13 : spin_vector_t := (others => '0');
    signal field_13     : field_t;
    signal counter_13   : signed(COUNTER_BITS downto 0);
    signal neighbors_14 : spin_vector_t := (others => '0');
    signal field_14     : field_t;
    signal counter_14   : signed(COUNTER_BITS downto 0);
    signal neighbors_15 : spin_vector_t := (others => '0');
    signal field_15     : field_t;
    signal counter_15   : signed(COUNTER_BITS downto 0);
    signal neighbors_16 : spin_vector_t := (others => '0');
    signal field_16     : field_t;
    signal counter_16   : signed(COUNTER_BITS downto 0);
    signal neighbors_17 : spin_vector_t := (others => '0');
    signal field_17     : field_t;
    signal counter_17   : signed(COUNTER_BITS downto 0);
    signal neighbors_18 : spin_vector_t := (others => '0');
    signal field_18     : field_t;
    signal counter_18   : signed(COUNTER_BITS downto 0);
    signal neighbors_19 : spin_vector_t := (others => '0');
    signal field_19     : field_t;
    signal counter_19   : signed(COUNTER_BITS downto 0);
    signal neighbors_20 : spin_vector_t := (others => '0');
    signal field_20     : field_t;
    signal counter_20   : signed(COUNTER_BITS downto 0);
    signal neighbors_21 : spin_vector_t := (others => '0');
    signal field_21     : field_t;
    signal counter_21   : signed(COUNTER_BITS downto 0);
    signal neighbors_22 : spin_vector_t := (others => '0');
    signal field_22     : field_t;
    signal counter_22   : signed(COUNTER_BITS downto 0);
    signal neighbors_23 : spin_vector_t := (others => '0');
    signal field_23     : field_t;
    signal counter_23   : signed(COUNTER_BITS downto 0);
    signal neighbors_24 : spin_vector_t := (others => '0');
    signal field_24     : field_t;
    signal counter_24   : signed(COUNTER_BITS downto 0);
    signal neighbors_25 : spin_vector_t := (others => '0');
    signal field_25     : field_t;
    signal counter_25   : signed(COUNTER_BITS downto 0);
    signal neighbors_26 : spin_vector_t := (others => '0');
    signal field_26     : field_t;
    signal counter_26   : signed(COUNTER_BITS downto 0);
    signal neighbors_27 : spin_vector_t := (others => '0');
    signal field_27     : field_t;
    signal counter_27   : signed(COUNTER_BITS downto 0);
    signal neighbors_28 : spin_vector_t := (others => '0');
    signal field_28     : field_t;
    signal counter_28   : signed(COUNTER_BITS downto 0);
    signal neighbors_29 : spin_vector_t := (others => '0');
    signal field_29     : field_t;
    signal counter_29   : signed(COUNTER_BITS downto 0);
    signal neighbors_30 : spin_vector_t := (others => '0');
    signal field_30     : field_t;
    signal counter_30   : signed(COUNTER_BITS downto 0);
    signal neighbors_31 : spin_vector_t := (others => '0');
    signal field_31     : field_t;
    signal counter_31   : signed(COUNTER_BITS downto 0);
begin
    process (clk)
        variable x : unsigned(31 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '1' then
                phase <= 0;
                sched_state <= x"488E4364";
            elsif enable = '1' then
                x := unsigned(sched_state);
                x := x xor shift_left(x, 13);
                x := x xor shift_right(x, 17);
                x := x xor shift_left(x, 5);
                sched_state <= std_logic_vector(x);
                phase <= to_integer(unsigned(sched_state(15 downto 0))) mod NODE_COUNT;
            end if;
        end if;
    end process;

    process (all)
        variable enables_v  : std_logic_vector(31 downto 0);
        variable selected_v : natural range 0 to 31;
        variable found_v    : boolean;
    begin
        enables_v := (others => '0');
        if enable = '1' then
            for i in 0 to NODE_COUNT - 1 loop
                if clamp_en(i) = '1' then
                    enables_v(i) := '1';
                end if;
            end loop;

            found_v := false;
            for offset in 0 to NODE_COUNT - 1 loop
                selected_v := (phase + offset) mod NODE_COUNT;
                if clamp_en(selected_v) = '0' and not found_v then
                    enables_v(selected_v) := '1';
                    found_v := true;
                end if;
            end loop;
        end if;
        node_enable <= enables_v;
    end process;

    neighbors_0 <= (0 => spin_s(8), 1 => spin_s(16), 2 => spin_s(24), others => '0');
    neighbors_1 <= (0 => spin_s(9), 1 => spin_s(17), 2 => spin_s(24), 3 => spin_s(25), others => '0');
    neighbors_2 <= (0 => spin_s(10), 1 => spin_s(18), 2 => spin_s(25), 3 => spin_s(26), others => '0');
    neighbors_3 <= (0 => spin_s(11), 1 => spin_s(19), 2 => spin_s(26), 3 => spin_s(27), others => '0');
    neighbors_4 <= (0 => spin_s(12), 1 => spin_s(20), 2 => spin_s(27), 3 => spin_s(28), others => '0');
    neighbors_5 <= (0 => spin_s(13), 1 => spin_s(21), 2 => spin_s(28), 3 => spin_s(29), others => '0');
    neighbors_6 <= (0 => spin_s(14), 1 => spin_s(22), 2 => spin_s(29), 3 => spin_s(30), others => '0');
    neighbors_7 <= (0 => spin_s(15), 1 => spin_s(23), 2 => spin_s(30), 3 => spin_s(31), others => '0');
    neighbors_8 <= (0 => spin_s(0), 1 => spin_s(16), 2 => spin_s(24), others => '0');
    neighbors_9 <= (0 => spin_s(1), 1 => spin_s(17), 2 => spin_s(24), 3 => spin_s(25), others => '0');
    neighbors_10 <= (0 => spin_s(2), 1 => spin_s(18), 2 => spin_s(25), 3 => spin_s(26), others => '0');
    neighbors_11 <= (0 => spin_s(3), 1 => spin_s(19), 2 => spin_s(26), 3 => spin_s(27), others => '0');
    neighbors_12 <= (0 => spin_s(4), 1 => spin_s(20), 2 => spin_s(27), 3 => spin_s(28), others => '0');
    neighbors_13 <= (0 => spin_s(5), 1 => spin_s(21), 2 => spin_s(28), 3 => spin_s(29), others => '0');
    neighbors_14 <= (0 => spin_s(6), 1 => spin_s(22), 2 => spin_s(29), 3 => spin_s(30), others => '0');
    neighbors_15 <= (0 => spin_s(7), 1 => spin_s(23), 2 => spin_s(30), 3 => spin_s(31), others => '0');
    neighbors_16 <= (0 => spin_s(0), 1 => spin_s(8), 2 => spin_s(24), others => '0');
    neighbors_17 <= (0 => spin_s(1), 1 => spin_s(9), 2 => spin_s(24), 3 => spin_s(25), others => '0');
    neighbors_18 <= (0 => spin_s(2), 1 => spin_s(10), 2 => spin_s(25), 3 => spin_s(26), others => '0');
    neighbors_19 <= (0 => spin_s(3), 1 => spin_s(11), 2 => spin_s(26), 3 => spin_s(27), others => '0');
    neighbors_20 <= (0 => spin_s(4), 1 => spin_s(12), 2 => spin_s(27), 3 => spin_s(28), others => '0');
    neighbors_21 <= (0 => spin_s(5), 1 => spin_s(13), 2 => spin_s(28), 3 => spin_s(29), others => '0');
    neighbors_22 <= (0 => spin_s(6), 1 => spin_s(14), 2 => spin_s(29), 3 => spin_s(30), others => '0');
    neighbors_23 <= (0 => spin_s(7), 1 => spin_s(15), 2 => spin_s(30), 3 => spin_s(31), others => '0');
    neighbors_24 <= (0 => spin_s(0), 1 => spin_s(1), 2 => spin_s(8), 3 => spin_s(9), 4 => spin_s(16), 5 => spin_s(17), 6 => spin_s(25), others => '0');
    neighbors_25 <= (0 => spin_s(1), 1 => spin_s(2), 2 => spin_s(9), 3 => spin_s(10), 4 => spin_s(17), 5 => spin_s(18), 6 => spin_s(24), 7 => spin_s(26), others => '0');
    neighbors_26 <= (0 => spin_s(2), 1 => spin_s(3), 2 => spin_s(10), 3 => spin_s(11), 4 => spin_s(18), 5 => spin_s(19), 6 => spin_s(25), 7 => spin_s(27), others => '0');
    neighbors_27 <= (0 => spin_s(3), 1 => spin_s(4), 2 => spin_s(11), 3 => spin_s(12), 4 => spin_s(19), 5 => spin_s(20), 6 => spin_s(26), 7 => spin_s(28), others => '0');
    neighbors_28 <= (0 => spin_s(4), 1 => spin_s(5), 2 => spin_s(12), 3 => spin_s(13), 4 => spin_s(20), 5 => spin_s(21), 6 => spin_s(27), 7 => spin_s(29), others => '0');
    neighbors_29 <= (0 => spin_s(5), 1 => spin_s(6), 2 => spin_s(13), 3 => spin_s(14), 4 => spin_s(21), 5 => spin_s(22), 6 => spin_s(28), 7 => spin_s(30), others => '0');
    neighbors_30 <= (0 => spin_s(6), 1 => spin_s(7), 2 => spin_s(14), 3 => spin_s(15), 4 => spin_s(22), 5 => spin_s(23), 6 => spin_s(29), 7 => spin_s(31), others => '0');
    neighbors_31 <= (0 => spin_s(7), 1 => spin_s(15), 2 => spin_s(23), 3 => spin_s(30), others => '0');

    node_0 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 3,
            BIAS         => 56,
            W0           => -56,
            W1           => 56,
            W2           => 112,
            W3           => 0,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"FADC7215"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(0),
            clamp_en    => clamp_en(0),
            clamp_value => clamp_value(0),
            neighbors   => neighbors_0,
            spin_o      => spin_s(0),
            field_o     => field_0,
            counter_o   => counter_0
        );

    node_1 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"9DDF53BA"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(1),
            clamp_en    => clamp_en(1),
            clamp_value => clamp_value(1),
            neighbors   => neighbors_1,
            spin_o      => spin_s(1),
            field_o     => field_1,
            counter_o   => counter_1
        );

    node_2 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"8CDEC523"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(2),
            clamp_en    => clamp_en(2),
            clamp_value => clamp_value(2),
            neighbors   => neighbors_2,
            spin_o      => spin_s(2),
            field_o     => field_2,
            counter_o   => counter_2
        );

    node_3 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"436DDB10"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(3),
            clamp_en    => clamp_en(3),
            clamp_value => clamp_value(3),
            neighbors   => neighbors_3,
            spin_o      => spin_s(3),
            field_o     => field_3,
            counter_o   => counter_3
        );

    node_4 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"AD06C461"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(4),
            clamp_en    => clamp_en(4),
            clamp_value => clamp_value(4),
            neighbors   => neighbors_4,
            spin_o      => spin_s(4),
            field_o     => field_4,
            counter_o   => counter_4
        );

    node_5 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"CDCFA396"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(5),
            clamp_en    => clamp_en(5),
            clamp_value => clamp_value(5),
            neighbors   => neighbors_5,
            spin_o      => spin_s(5),
            field_o     => field_5,
            counter_o   => counter_5
        );

    node_6 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"D5CED37F"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(6),
            clamp_en    => clamp_en(6),
            clamp_value => clamp_value(6),
            neighbors   => neighbors_6,
            spin_o      => spin_s(6),
            field_o     => field_6,
            counter_o   => counter_6
        );

    node_7 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"F3D2468C"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(7),
            clamp_en    => clamp_en(7),
            clamp_value => clamp_value(7),
            neighbors   => neighbors_7,
            spin_o      => spin_s(7),
            field_o     => field_7,
            counter_o   => counter_7
        );

    node_8 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 3,
            BIAS         => 56,
            W0           => -56,
            W1           => 56,
            W2           => 112,
            W3           => 0,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"FEFE97FD"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(8),
            clamp_en    => clamp_en(8),
            clamp_value => clamp_value(8),
            neighbors   => neighbors_8,
            spin_o      => spin_s(8),
            field_o     => field_8,
            counter_o   => counter_8
        );

    node_9 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"E7F231A2"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(9),
            clamp_en    => clamp_en(9),
            clamp_value => clamp_value(9),
            neighbors   => neighbors_9,
            spin_o      => spin_s(9),
            field_o     => field_9,
            counter_o   => counter_9
        );

    node_10 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"F1BB5F2B"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(10),
            clamp_en    => clamp_en(10),
            clamp_value => clamp_value(10),
            neighbors   => neighbors_10,
            spin_o      => spin_s(10),
            field_o     => field_10,
            counter_o   => counter_10
        );

    node_11 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"66698EB8"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(11),
            clamp_en    => clamp_en(11),
            clamp_value => clamp_value(11),
            neighbors   => neighbors_11,
            spin_o      => spin_s(11),
            field_o     => field_11,
            counter_o   => counter_11
        );

    node_12 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"F885D8E9"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(12),
            clamp_en    => clamp_en(12),
            clamp_value => clamp_value(12),
            neighbors   => neighbors_12,
            spin_o      => spin_s(12),
            field_o     => field_12,
            counter_o   => counter_12
        );

    node_13 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"4ED7177E"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(13),
            clamp_en    => clamp_en(13),
            clamp_value => clamp_value(13),
            neighbors   => neighbors_13,
            spin_o      => spin_s(13),
            field_o     => field_13,
            counter_o   => counter_13
        );

    node_14 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"C24F3C67"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(14),
            clamp_en    => clamp_en(14),
            clamp_value => clamp_value(14),
            neighbors   => neighbors_14,
            spin_o      => spin_s(14),
            field_o     => field_14,
            counter_o   => counter_14
        );

    node_15 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => -56,
            W1           => 56,
            W2           => -56,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"631A5D94"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(15),
            clamp_en    => clamp_en(15),
            clamp_value => clamp_value(15),
            neighbors   => neighbors_15,
            spin_o      => spin_s(15),
            field_o     => field_15,
            counter_o   => counter_15
        );

    node_16 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 3,
            BIAS         => -56,
            W0           => 56,
            W1           => 56,
            W2           => -112,
            W3           => 0,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"561E0845"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(16),
            clamp_en    => clamp_en(16),
            clamp_value => clamp_value(16),
            neighbors   => neighbors_16,
            spin_o      => spin_s(16),
            field_o     => field_16,
            counter_o   => counter_16
        );

    node_17 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 56,
            W1           => 56,
            W2           => 56,
            W3           => -112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"A51AFC6A"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(17),
            clamp_en    => clamp_en(17),
            clamp_value => clamp_value(17),
            neighbors   => neighbors_17,
            spin_o      => spin_s(17),
            field_o     => field_17,
            counter_o   => counter_17
        );

    node_18 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 56,
            W1           => 56,
            W2           => 56,
            W3           => -112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"CD41A753"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(18),
            clamp_en    => clamp_en(18),
            clamp_value => clamp_value(18),
            neighbors   => neighbors_18,
            spin_o      => spin_s(18),
            field_o     => field_18,
            counter_o   => counter_18
        );

    node_19 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 56,
            W1           => 56,
            W2           => 56,
            W3           => -112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"771F3A00"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(19),
            clamp_en    => clamp_en(19),
            clamp_value => clamp_value(19),
            neighbors   => neighbors_19,
            spin_o      => spin_s(19),
            field_o     => field_19,
            counter_o   => counter_19
        );

    node_20 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 56,
            W1           => 56,
            W2           => 56,
            W3           => -112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"4701C791"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(20),
            clamp_en    => clamp_en(20),
            clamp_value => clamp_value(20),
            neighbors   => neighbors_20,
            spin_o      => spin_s(20),
            field_o     => field_20,
            counter_o   => counter_20
        );

    node_21 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 56,
            W1           => 56,
            W2           => 56,
            W3           => -112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"6F9B0306"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(21),
            clamp_en    => clamp_en(21),
            clamp_value => clamp_value(21),
            neighbors   => neighbors_21,
            spin_o      => spin_s(21),
            field_o     => field_21,
            counter_o   => counter_21
        );

    node_22 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 56,
            W1           => 56,
            W2           => 56,
            W3           => -112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"E196C2AF"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(22),
            clamp_en    => clamp_en(22),
            clamp_value => clamp_value(22),
            neighbors   => neighbors_22,
            spin_o      => spin_s(22),
            field_o     => field_22,
            counter_o   => counter_22
        );

    node_23 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 56,
            W1           => 56,
            W2           => 56,
            W3           => -112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"FD04CC7C"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(23),
            clamp_en    => clamp_en(23),
            clamp_value => clamp_value(23),
            neighbors   => neighbors_23,
            spin_o      => spin_s(23),
            field_o     => field_23,
            counter_o   => counter_23
        );

    node_24 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 7,
            BIAS         => -112,
            W0           => 112,
            W1           => -56,
            W2           => 112,
            W3           => -56,
            W4           => -112,
            W5           => 56,
            W6           => 112,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"FC2CB7ED"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(24),
            clamp_en    => clamp_en(24),
            clamp_value => clamp_value(24),
            neighbors   => neighbors_24,
            spin_o      => spin_s(24),
            field_o     => field_24,
            counter_o   => counter_24
        );

    node_25 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 8,
            BIAS         => 0,
            W0           => 112,
            W1           => -56,
            W2           => 112,
            W3           => -56,
            W4           => -112,
            W5           => 56,
            W6           => 112,
            W7           => 112,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"AE6A9D52"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(25),
            clamp_en    => clamp_en(25),
            clamp_value => clamp_value(25),
            neighbors   => neighbors_25,
            spin_o      => spin_s(25),
            field_o     => field_25,
            counter_o   => counter_25
        );

    node_26 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 8,
            BIAS         => 0,
            W0           => 112,
            W1           => -56,
            W2           => 112,
            W3           => -56,
            W4           => -112,
            W5           => 56,
            W6           => 112,
            W7           => 112,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"2DC0AC5B"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(26),
            clamp_en    => clamp_en(26),
            clamp_value => clamp_value(26),
            neighbors   => neighbors_26,
            spin_o      => spin_s(26),
            field_o     => field_26,
            counter_o   => counter_26
        );

    node_27 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 8,
            BIAS         => 0,
            W0           => 112,
            W1           => -56,
            W2           => 112,
            W3           => -56,
            W4           => -112,
            W5           => 56,
            W6           => 112,
            W7           => 112,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"5E450AA8"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(27),
            clamp_en    => clamp_en(27),
            clamp_value => clamp_value(27),
            neighbors   => neighbors_27,
            spin_o      => spin_s(27),
            field_o     => field_27,
            counter_o   => counter_27
        );

    node_28 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 8,
            BIAS         => 0,
            W0           => 112,
            W1           => -56,
            W2           => 112,
            W3           => -56,
            W4           => -112,
            W5           => 56,
            W6           => 112,
            W7           => 112,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"8B32B759"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(28),
            clamp_en    => clamp_en(28),
            clamp_value => clamp_value(28),
            neighbors   => neighbors_28,
            spin_o      => spin_s(28),
            field_o     => field_28,
            counter_o   => counter_28
        );

    node_29 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 8,
            BIAS         => 0,
            W0           => 112,
            W1           => -56,
            W2           => 112,
            W3           => -56,
            W4           => -112,
            W5           => 56,
            W6           => 112,
            W7           => 112,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"DAC7706E"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(29),
            clamp_en    => clamp_en(29),
            clamp_value => clamp_value(29),
            neighbors   => neighbors_29,
            spin_o      => spin_s(29),
            field_o     => field_29,
            counter_o   => counter_29
        );

    node_30 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 8,
            BIAS         => 0,
            W0           => 112,
            W1           => -56,
            W2           => 112,
            W3           => -56,
            W4           => -112,
            W5           => 56,
            W6           => 112,
            W7           => 112,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"ECC5A5D7"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(30),
            clamp_en    => clamp_en(30),
            clamp_value => clamp_value(30),
            neighbors   => neighbors_30,
            spin_o      => spin_s(30),
            field_o     => field_30,
            counter_o   => counter_30
        );

    node_31 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 4,
            BIAS         => 0,
            W0           => 112,
            W1           => 112,
            W2           => -112,
            W3           => 112,
            W4           => 0,
            W5           => 0,
            W6           => 0,
            W7           => 0,
            W8           => 0,
            W9           => 0,
            W10          => 0,
            W11          => 0,
            W12          => 0,
            W13          => 0,
            W14          => 0,
            W15          => 0,
            W16          => 0,
            W17          => 0,
            W18          => 0,
            W19          => 0,
            W20          => 0,
            W21          => 0,
            W22          => 0,
            W23          => 0,
            W24          => 0,
            W25          => 0,
            W26          => 0,
            W27          => 0,
            W28          => 0,
            W29          => 0,
            W30          => 0,
            W31          => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"48530004"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => node_enable(31),
            clamp_en    => clamp_en(31),
            clamp_value => clamp_value(31),
            neighbors   => neighbors_31,
            spin_o      => spin_s(31),
            field_o     => field_31,
            counter_o   => counter_31
        );

    spins <= spin_s;
end architecture;
