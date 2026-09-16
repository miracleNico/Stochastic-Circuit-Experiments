library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity gen_adder4_split_anneal is
    generic (
        COUNTER_BITS : natural := 5;
        FIELD_FRAC_BITS : natural := 8
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        enable      : in  std_logic;
        stage_rnd0  : in  natural;
        stage_rnd1  : in  natural;
        stage_rnd2  : in  natural;
        stage_rnd3  : in  natural;
        stage_en0   : in  std_logic;
        stage_en1   : in  std_logic;
        stage_en2   : in  std_logic;
        stage_en3   : in  std_logic;
        clamp_en    : in  std_logic_vector(18 downto 0);
        clamp_value : in  std_logic_vector(18 downto 0);
        spins       : out std_logic_vector(18 downto 0)
    );
end entity;

architecture rtl of gen_adder4_split_anneal is
    constant NODE_COUNT : natural := 19;
    signal spin_s      : std_logic_vector(18 downto 0) := (others => '0');
    signal node_enable : std_logic_vector(18 downto 0) := (others => '0');
    signal phase       : natural range 0 to 18 := 0;
    signal sched_state : std_logic_vector(31 downto 0) := x"ADD07D12";
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
begin
    process (clk)
        variable x : unsigned(31 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '1' then
                phase <= 0;
                sched_state <= x"ADD07D12";
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
        variable enables_v  : std_logic_vector(18 downto 0);
        variable selected_v : natural range 0 to 18;
        variable found_v    : boolean;
        variable selected_stage_en_v : std_logic;
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
                if selected_v = 0 then selected_stage_en_v := stage_en0; end if;
                if selected_v = 1 then selected_stage_en_v := stage_en1; end if;
                if selected_v = 2 then selected_stage_en_v := stage_en2; end if;
                if selected_v = 3 then selected_stage_en_v := stage_en3; end if;
                if selected_v = 4 then selected_stage_en_v := stage_en0; end if;
                if selected_v = 5 then selected_stage_en_v := stage_en1; end if;
                if selected_v = 6 then selected_stage_en_v := stage_en2; end if;
                if selected_v = 7 then selected_stage_en_v := stage_en3; end if;
                if selected_v = 8 then selected_stage_en_v := stage_en0; end if;
                if selected_v = 9 then selected_stage_en_v := stage_en1; end if;
                if selected_v = 10 then selected_stage_en_v := stage_en2; end if;
                if selected_v = 11 then selected_stage_en_v := stage_en3; end if;
                if selected_v = 12 then selected_stage_en_v := stage_en0; end if;
                if selected_v = 13 then selected_stage_en_v := stage_en1; end if;
                if selected_v = 14 then selected_stage_en_v := stage_en2; end if;
                if selected_v = 15 then selected_stage_en_v := stage_en3; end if;
                if selected_v = 16 then selected_stage_en_v := stage_en1; end if;
                if selected_v = 17 then selected_stage_en_v := stage_en2; end if;
                if selected_v = 18 then selected_stage_en_v := stage_en3; end if;
                if clamp_en(selected_v) = '0' and selected_stage_en_v = '1' and not found_v then
                    enables_v(selected_v) := '1';
                    found_v := true;
                end if;
                selected_stage_en_v := '0';
            end loop;
        end if;
        node_enable <= enables_v;
    end process;

    neighbors_0 <= (0 => spin_s(4), 1 => spin_s(8), 2 => spin_s(12), others => '0');
    neighbors_1 <= (0 => spin_s(5), 1 => spin_s(9), 2 => spin_s(13), 3 => spin_s(16), others => '0');
    neighbors_2 <= (0 => spin_s(6), 1 => spin_s(10), 2 => spin_s(14), 3 => spin_s(17), others => '0');
    neighbors_3 <= (0 => spin_s(7), 1 => spin_s(11), 2 => spin_s(15), 3 => spin_s(18), others => '0');
    neighbors_4 <= (0 => spin_s(0), 1 => spin_s(8), 2 => spin_s(12), others => '0');
    neighbors_5 <= (0 => spin_s(1), 1 => spin_s(9), 2 => spin_s(13), 3 => spin_s(16), others => '0');
    neighbors_6 <= (0 => spin_s(2), 1 => spin_s(10), 2 => spin_s(14), 3 => spin_s(17), others => '0');
    neighbors_7 <= (0 => spin_s(3), 1 => spin_s(11), 2 => spin_s(15), 3 => spin_s(18), others => '0');
    neighbors_8 <= (0 => spin_s(0), 1 => spin_s(4), 2 => spin_s(12), others => '0');
    neighbors_9 <= (0 => spin_s(1), 1 => spin_s(5), 2 => spin_s(13), 3 => spin_s(16), others => '0');
    neighbors_10 <= (0 => spin_s(2), 1 => spin_s(6), 2 => spin_s(14), 3 => spin_s(17), others => '0');
    neighbors_11 <= (0 => spin_s(3), 1 => spin_s(7), 2 => spin_s(15), 3 => spin_s(18), others => '0');
    neighbors_12 <= (0 => spin_s(0), 1 => spin_s(4), 2 => spin_s(8), 3 => spin_s(16), others => '0');
    neighbors_13 <= (0 => spin_s(1), 1 => spin_s(5), 2 => spin_s(9), 3 => spin_s(16), 4 => spin_s(17), others => '0');
    neighbors_14 <= (0 => spin_s(2), 1 => spin_s(6), 2 => spin_s(10), 3 => spin_s(17), 4 => spin_s(18), others => '0');
    neighbors_15 <= (0 => spin_s(3), 1 => spin_s(7), 2 => spin_s(11), 3 => spin_s(18), others => '0');
    neighbors_16 <= (0 => spin_s(1), 1 => spin_s(5), 2 => spin_s(9), 3 => spin_s(12), 4 => spin_s(13), others => '0');
    neighbors_17 <= (0 => spin_s(2), 1 => spin_s(6), 2 => spin_s(10), 3 => spin_s(13), 4 => spin_s(14), others => '0');
    neighbors_18 <= (0 => spin_s(3), 1 => spin_s(7), 2 => spin_s(11), 3 => spin_s(14), 4 => spin_s(15), others => '0');

    node_0 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 3,
            BIAS            => 1024,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => 0,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"AC9D0AB9"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(0),
            rnd_weight_i => stage_rnd0,
            clamp_en     => clamp_en(0),
            clamp_value  => clamp_value(0),
            neighbors    => neighbors_0,
            spin_o       => spin_s(0),
            field_o      => field_0,
            counter_o    => counter_0
        );

    node_1 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => -1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"F86CBF4C"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(1),
            rnd_weight_i => stage_rnd1,
            clamp_en     => clamp_en(1),
            clamp_value  => clamp_value(1),
            neighbors    => neighbors_1,
            spin_o       => spin_s(1),
            field_o      => field_1,
            counter_o    => counter_1
        );

    node_2 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => -1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"2D593783"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(2),
            rnd_weight_i => stage_rnd2,
            clamp_en     => clamp_en(2),
            clamp_value  => clamp_value(2),
            neighbors    => neighbors_2,
            spin_o       => spin_s(2),
            field_o      => field_2,
            counter_o    => counter_2
        );

    node_3 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => -1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"5C92B9B6"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(3),
            rnd_weight_i => stage_rnd3,
            clamp_en     => clamp_en(3),
            clamp_value  => clamp_value(3),
            neighbors    => neighbors_3,
            spin_o       => spin_s(3),
            field_o      => field_3,
            counter_o    => counter_3
        );

    node_4 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 3,
            BIAS            => 1024,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => 0,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"29CA880D"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(4),
            rnd_weight_i => stage_rnd0,
            clamp_en     => clamp_en(4),
            clamp_value  => clamp_value(4),
            neighbors    => neighbors_4,
            spin_o       => spin_s(4),
            field_o      => field_4,
            counter_o    => counter_4
        );

    node_5 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => -1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"0514C1A0"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(5),
            rnd_weight_i => stage_rnd1,
            clamp_en     => clamp_en(5),
            clamp_value  => clamp_value(5),
            neighbors    => neighbors_5,
            spin_o       => spin_s(5),
            field_o      => field_5,
            counter_o    => counter_5
        );

    node_6 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => -1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"740F79F7"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(6),
            rnd_weight_i => stage_rnd2,
            clamp_en     => clamp_en(6),
            clamp_value  => clamp_value(6),
            neighbors    => neighbors_6,
            spin_o       => spin_s(6),
            field_o      => field_6,
            counter_o    => counter_6
        );

    node_7 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => -1024,
            W1              => 1024,
            W2              => 2048,
            W3              => -1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"0802040A"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(7),
            rnd_weight_i => stage_rnd3,
            clamp_en     => clamp_en(7),
            clamp_value  => clamp_value(7),
            neighbors    => neighbors_7,
            spin_o       => spin_s(7),
            field_o      => field_7,
            counter_o    => counter_7
        );

    node_8 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 3,
            BIAS            => -1024,
            W0              => 1024,
            W1              => 1024,
            W2              => -2048,
            W3              => 0,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"454774D1"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(8),
            rnd_weight_i => stage_rnd0,
            clamp_en     => clamp_en(8),
            clamp_value  => clamp_value(8),
            neighbors    => neighbors_8,
            spin_o       => spin_s(8),
            field_o      => field_8,
            counter_o    => counter_8
        );

    node_9 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => 1024,
            W1              => 1024,
            W2              => -2048,
            W3              => 1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"4D8E2C24"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(9),
            rnd_weight_i => stage_rnd1,
            clamp_en     => clamp_en(9),
            clamp_value  => clamp_value(9),
            neighbors    => neighbors_9,
            spin_o       => spin_s(9),
            field_o      => field_9,
            counter_o    => counter_9
        );

    node_10 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => 1024,
            W1              => 1024,
            W2              => -2048,
            W3              => 1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"7AF2F77B"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(10),
            rnd_weight_i => stage_rnd2,
            clamp_en     => clamp_en(10),
            clamp_value  => clamp_value(10),
            neighbors    => neighbors_10,
            spin_o       => spin_s(10),
            field_o      => field_10,
            counter_o    => counter_10
        );

    node_11 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => 1024,
            W1              => 1024,
            W2              => -2048,
            W3              => 1024,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"7178062E"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(11),
            rnd_weight_i => stage_rnd3,
            clamp_en     => clamp_en(11),
            clamp_value  => clamp_value(11),
            neighbors    => neighbors_11,
            spin_o       => spin_s(11),
            field_o      => field_11,
            counter_o    => counter_11
        );

    node_12 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => -2048,
            W0              => 2048,
            W1              => 2048,
            W2              => -2048,
            W3              => 8192,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"86575205"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(12),
            rnd_weight_i => stage_rnd0,
            clamp_en     => clamp_en(12),
            clamp_value  => clamp_value(12),
            neighbors    => neighbors_12,
            spin_o       => spin_s(12),
            field_o      => field_12,
            counter_o    => counter_12
        );

    node_13 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 5,
            BIAS            => 0,
            W0              => 2048,
            W1              => 2048,
            W2              => -2048,
            W3              => 2048,
            W4              => 8192,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"00004A38"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(13),
            rnd_weight_i => stage_rnd1,
            clamp_en     => clamp_en(13),
            clamp_value  => clamp_value(13),
            neighbors    => neighbors_13,
            spin_o       => spin_s(13),
            field_o      => field_13,
            counter_o    => counter_13
        );

    node_14 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 5,
            BIAS            => 0,
            W0              => 2048,
            W1              => 2048,
            W2              => -2048,
            W3              => 2048,
            W4              => 8192,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"399857AF"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(14),
            rnd_weight_i => stage_rnd2,
            clamp_en     => clamp_en(14),
            clamp_value  => clamp_value(14),
            neighbors    => neighbors_14,
            spin_o       => spin_s(14),
            field_o      => field_14,
            counter_o    => counter_14
        );

    node_15 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 4,
            BIAS            => 0,
            W0              => 2048,
            W1              => 2048,
            W2              => -2048,
            W3              => 2048,
            W4              => 0,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"2A2ADF82"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(15),
            rnd_weight_i => stage_rnd3,
            clamp_en     => clamp_en(15),
            clamp_value  => clamp_value(15),
            neighbors    => neighbors_15,
            spin_o       => spin_s(15),
            field_o      => field_15,
            counter_o    => counter_15
        );

    node_16 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 5,
            BIAS            => 0,
            W0              => -1024,
            W1              => -1024,
            W2              => 1024,
            W3              => 8192,
            W4              => 2048,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"3B704EE9"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(16),
            rnd_weight_i => stage_rnd1,
            clamp_en     => clamp_en(16),
            clamp_value  => clamp_value(16),
            neighbors    => neighbors_16,
            spin_o       => spin_s(16),
            field_o      => field_16,
            counter_o    => counter_16
        );

    node_17 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 5,
            BIAS            => 0,
            W0              => -1024,
            W1              => -1024,
            W2              => 1024,
            W3              => 8192,
            W4              => 2048,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"0F8EF53C"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(17),
            rnd_weight_i => stage_rnd2,
            clamp_en     => clamp_en(17),
            clamp_value  => clamp_value(17),
            neighbors    => neighbors_17,
            spin_o       => spin_s(17),
            field_o      => field_17,
            counter_o    => counter_17
        );

    node_18 : entity work.spin_node
        generic map (
            NUM_INPUTS      => 5,
            BIAS            => 0,
            W0              => -1024,
            W1              => -1024,
            W2              => 1024,
            W3              => 8192,
            W4              => 2048,
            W5              => 0,
            W6              => 0,
            W7              => 0,
            W8              => 0,
            W9              => 0,
            W10             => 0,
            W11             => 0,
            W12             => 0,
            W13             => 0,
            W14             => 0,
            W15             => 0,
            W16             => 0,
            W17             => 0,
            W18             => 0,
            W19             => 0,
            W20             => 0,
            W21             => 0,
            W22             => 0,
            W23             => 0,
            W24             => 0,
            W25             => 0,
            W26             => 0,
            W27             => 0,
            W28             => 0,
            W29             => 0,
            W30             => 0,
            W31             => 0,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => 0,
            USE_DYNAMIC_RND => true,
            COUNTER_BITS    => COUNTER_BITS,
            SEED            => x"437802B3"
        )
        port map (
            clk          => clk,
            rst          => rst,
            enable       => node_enable(18),
            rnd_weight_i => stage_rnd3,
            clamp_en     => clamp_en(18),
            clamp_value  => clamp_value(18),
            neighbors    => neighbors_18,
            spin_o       => spin_s(18),
            field_o      => field_18,
            counter_o    => counter_18
        );

    spins <= spin_s;
end architecture;
