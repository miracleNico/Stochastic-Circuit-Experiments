library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity gen_comb6_mixed is
    generic (
        RND_WEIGHT   : natural := 0;
        COUNTER_BITS : natural := 5;
        FIELD_FRAC_BITS : natural := 4
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        enable      : in  std_logic;
        clamp_en    : in  std_logic_vector(20 downto 0);
        clamp_value : in  std_logic_vector(20 downto 0);
        spins       : out std_logic_vector(20 downto 0)
    );
end entity;

architecture rtl of gen_comb6_mixed is
    constant NODE_COUNT : natural := 21;
    signal spin_s      : std_logic_vector(20 downto 0) := (others => '0');
    signal node_enable : std_logic_vector(20 downto 0) := (others => '0');
    signal phase       : natural range 0 to 20 := 0;
    signal sched_state : std_logic_vector(31 downto 0) := x"89EE4ED7";
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
begin
    process (clk)
        variable x : unsigned(31 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '1' then
                phase <= 0;
                sched_state <= x"89EE4ED7";
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
        variable enables_v  : std_logic_vector(20 downto 0);
        variable selected_v : natural range 0 to 20;
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

    neighbors_0 <= (0 => spin_s(1), 1 => spin_s(2), 2 => spin_s(6), 3 => spin_s(9), 4 => spin_s(10), others => '0');
    neighbors_1 <= (0 => spin_s(0), 1 => spin_s(5), 2 => spin_s(6), 3 => spin_s(11), 4 => spin_s(12), others => '0');
    neighbors_2 <= (0 => spin_s(0), 1 => spin_s(3), 2 => spin_s(7), 3 => spin_s(9), 4 => spin_s(10), others => '0');
    neighbors_3 <= (0 => spin_s(2), 1 => spin_s(7), others => '0');
    neighbors_4 <= (0 => spin_s(5), 1 => spin_s(8), others => '0');
    neighbors_5 <= (0 => spin_s(1), 1 => spin_s(4), 2 => spin_s(8), 3 => spin_s(11), 4 => spin_s(12), others => '0');
    neighbors_6 <= (0 => spin_s(0), 1 => spin_s(1), 2 => spin_s(7), 3 => spin_s(13), 4 => spin_s(14), others => '0');
    neighbors_7 <= (0 => spin_s(2), 1 => spin_s(3), 2 => spin_s(6), 3 => spin_s(11), 4 => spin_s(13), 5 => spin_s(14), 6 => spin_s(16), others => '0');
    neighbors_8 <= (0 => spin_s(4), 1 => spin_s(5), 2 => spin_s(9), 3 => spin_s(15), others => '0');
    neighbors_9 <= (0 => spin_s(0), 1 => spin_s(2), 2 => spin_s(8), 3 => spin_s(10), 4 => spin_s(11), 5 => spin_s(15), 6 => spin_s(18), 7 => spin_s(19), others => '0');
    neighbors_10 <= (0 => spin_s(0), 1 => spin_s(2), 2 => spin_s(9), others => '0');
    neighbors_11 <= (0 => spin_s(1), 1 => spin_s(5), 2 => spin_s(7), 3 => spin_s(9), 4 => spin_s(12), 5 => spin_s(16), 6 => spin_s(18), 7 => spin_s(19), others => '0');
    neighbors_12 <= (0 => spin_s(1), 1 => spin_s(5), 2 => spin_s(11), others => '0');
    neighbors_13 <= (0 => spin_s(6), 1 => spin_s(7), 2 => spin_s(14), 3 => spin_s(18), 4 => spin_s(20), others => '0');
    neighbors_14 <= (0 => spin_s(6), 1 => spin_s(7), 2 => spin_s(13), others => '0');
    neighbors_15 <= (0 => spin_s(8), 1 => spin_s(9), 2 => spin_s(16), 3 => spin_s(17), others => '0');
    neighbors_16 <= (0 => spin_s(7), 1 => spin_s(11), 2 => spin_s(15), 3 => spin_s(17), others => '0');
    neighbors_17 <= (0 => spin_s(15), 1 => spin_s(16), others => '0');
    neighbors_18 <= (0 => spin_s(9), 1 => spin_s(11), 2 => spin_s(13), 3 => spin_s(19), 4 => spin_s(20), others => '0');
    neighbors_19 <= (0 => spin_s(9), 1 => spin_s(11), 2 => spin_s(18), others => '0');
    neighbors_20 <= (0 => spin_s(13), 1 => spin_s(18), others => '0');

    node_0 : entity work.spin_node
        generic map (
            NUM_INPUTS   => 5,
            BIAS         => 48,
            W0           => -16,
            W1           => -32,
            W2           => 32,
            W3           => 32,
            W4           => 64,
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
            SEED         => x"38C4171C"
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
            NUM_INPUTS   => 5,
            BIAS         => 48,
            W0           => -16,
            W1           => -32,
            W2           => 32,
            W3           => -32,
            W4           => 64,
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
            SEED         => x"13E4FE59"
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
            NUM_INPUTS   => 5,
            BIAS         => 16,
            W0           => -32,
            W1           => -16,
            W2           => 32,
            W3           => 32,
            W4           => 64,
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
            SEED         => x"341E2E0E"
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
            NUM_INPUTS   => 2,
            BIAS         => -16,
            W0           => -16,
            W1           => 32,
            W2           => 0,
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
            SEED         => x"845406F3"
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
            NUM_INPUTS   => 2,
            BIAS         => 16,
            W0           => -16,
            W1           => -32,
            W2           => 0,
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
            SEED         => x"042903A8"
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
            NUM_INPUTS   => 5,
            BIAS         => 48,
            W0           => -32,
            W1           => -16,
            W2           => -32,
            W3           => -32,
            W4           => 64,
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
            SEED         => x"F9868385"
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
            NUM_INPUTS   => 5,
            BIAS         => 0,
            W0           => 32,
            W1           => 32,
            W2           => -32,
            W3           => 32,
            W4           => 64,
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
            SEED         => x"BB0E7DDA"
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
            NUM_INPUTS   => 7,
            BIAS         => 48,
            W0           => 32,
            W1           => 32,
            W2           => -32,
            W3           => -16,
            W4           => 32,
            W5           => 64,
            W6           => -32,
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
            SEED         => x"26C6230F"
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
            NUM_INPUTS   => 4,
            BIAS         => 48,
            W0           => -32,
            W1           => -32,
            W2           => -16,
            W3           => 32,
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
            SEED         => x"FD500054"
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
            NUM_INPUTS   => 8,
            BIAS         => 16,
            W0           => 32,
            W1           => 32,
            W2           => -16,
            W3           => -64,
            W4           => -32,
            W5           => 32,
            W6           => -32,
            W7           => 64,
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
            SEED         => x"8AF13011"
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
            NUM_INPUTS   => 3,
            BIAS         => -64,
            W0           => 64,
            W1           => 64,
            W2           => -64,
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
            SEED         => x"66D07C86"
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
            NUM_INPUTS   => 8,
            BIAS         => 48,
            W0           => -32,
            W1           => -32,
            W2           => -16,
            W3           => -32,
            W4           => 64,
            W5           => -32,
            W6           => -32,
            W7           => 64,
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
            SEED         => x"4ADF0B0B"
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
            NUM_INPUTS   => 3,
            BIAS         => -64,
            W0           => 64,
            W1           => 64,
            W2           => 64,
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
            SEED         => x"25BBBCC0"
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
            NUM_INPUTS   => 5,
            BIAS         => -16,
            W0           => 32,
            W1           => 32,
            W2           => -64,
            W3           => -16,
            W4           => -32,
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
            SEED         => x"273C231D"
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
            NUM_INPUTS   => 3,
            BIAS         => -64,
            W0           => 64,
            W1           => 64,
            W2           => -64,
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
            SEED         => x"57B023D2"
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
            BIAS         => -48,
            W0           => 32,
            W1           => 32,
            W2           => -16,
            W3           => 32,
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
            SEED         => x"24C360C7"
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
            NUM_INPUTS   => 4,
            BIAS         => -48,
            W0           => -32,
            W1           => -32,
            W2           => -16,
            W3           => 32,
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
            SEED         => x"020516CC"
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
            NUM_INPUTS   => 2,
            BIAS         => 32,
            W0           => 32,
            W1           => 32,
            W2           => 0,
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
            SEED         => x"337FBB49"
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
            NUM_INPUTS   => 5,
            BIAS         => 48,
            W0           => -32,
            W1           => -32,
            W2           => -16,
            W3           => 64,
            W4           => -32,
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
            SEED         => x"1618187E"
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
            NUM_INPUTS   => 3,
            BIAS         => -64,
            W0           => 64,
            W1           => 64,
            W2           => 64,
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
            SEED         => x"29E8CB23"
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
            NUM_INPUTS   => 2,
            BIAS         => 32,
            W0           => -32,
            W1           => -32,
            W2           => 0,
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
            SEED         => x"AB8CCCD8"
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

    spins <= spin_s;
end architecture;
