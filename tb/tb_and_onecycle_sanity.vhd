library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity tb_and_onecycle_sanity is
    generic (
        TRIALS             : natural := 1000;
        SCRAMBLE_CYCLES    : natural := 80;
        PRIME_INPUT_CYCLES : natural := 0;
        SOLVE_CYCLES       : natural := 1;
        RND_WEIGHT         : natural := 0;
        FIELD_FRAC_BITS    : natural := 0;
        BIAS_A             : integer := 1;
        BIAS_B             : integer := 1;
        BIAS_Y             : integer := -2;
        J_AB               : integer := -1;
        J_AY               : integer := 2;
        J_BY               : integer := 2
    );
end entity;

architecture sim of tb_and_onecycle_sanity is
    constant CLK_PERIOD : time := 10 ns;

    signal clk : std_logic := '0';
    signal rst : std_logic := '1';

    signal en_a : std_logic := '0';
    signal en_b : std_logic := '0';
    signal en_y : std_logic := '0';

    signal clamp_a_en    : std_logic := '0';
    signal clamp_a_value : std_logic := '0';
    signal clamp_b_en    : std_logic := '0';
    signal clamp_b_value : std_logic := '0';
    signal clamp_y_en    : std_logic := '0';
    signal clamp_y_value : std_logic := '0';

    signal a_s : std_logic := '0';
    signal b_s : std_logic := '0';
    signal y_s : std_logic := '0';

    signal n_a : spin_vector_t := (others => '0');
    signal n_b : spin_vector_t := (others => '0');
    signal n_y : spin_vector_t := (others => '0');

    signal field_a : field_t;
    signal field_b : field_t;
    signal field_y : field_t;
    signal counter_a : signed(5 downto 0);
    signal counter_b : signed(5 downto 0);
    signal counter_y : signed(5 downto 0);
begin
    clk <= not clk after CLK_PERIOD / 2;

    n_a <= (0 => b_s, 1 => y_s, others => '0');
    n_b <= (0 => a_s, 1 => y_s, others => '0');
    n_y <= (0 => a_s, 1 => b_s, others => '0');

    node_a : entity work.spin_node
        generic map (
            NUM_INPUTS      => 2,
            BIAS            => BIAS_A,
            W0              => J_AB,
            W1              => J_AY,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => RND_WEIGHT,
            COUNTER_BITS    => 5,
            SEED            => x"11223345"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => en_a,
            clamp_en    => clamp_a_en,
            clamp_value => clamp_a_value,
            neighbors   => n_a,
            spin_o      => a_s,
            field_o     => field_a,
            counter_o   => counter_a
        );

    node_b : entity work.spin_node
        generic map (
            NUM_INPUTS      => 2,
            BIAS            => BIAS_B,
            W0              => J_AB,
            W1              => J_BY,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => RND_WEIGHT,
            COUNTER_BITS    => 5,
            SEED            => x"55667789"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => en_b,
            clamp_en    => clamp_b_en,
            clamp_value => clamp_b_value,
            neighbors   => n_b,
            spin_o      => b_s,
            field_o     => field_b,
            counter_o   => counter_b
        );

    node_y : entity work.spin_node
        generic map (
            NUM_INPUTS      => 2,
            BIAS            => BIAS_Y,
            W0              => J_AY,
            W1              => J_BY,
            FIELD_FRAC_BITS => FIELD_FRAC_BITS,
            RND_WEIGHT      => RND_WEIGHT,
            COUNTER_BITS    => 5,
            SEED            => x"A1B2C3D5"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => en_y,
            clamp_en    => clamp_y_en,
            clamp_value => clamp_y_value,
            neighbors   => n_y,
            spin_o      => y_s,
            field_o     => field_y,
            counter_o   => counter_y
        );

    stimulus : process
        variable total_hits : natural := 0;
        variable min_hits   : natural := TRIALS;
        variable fail_cases : natural := 0;

        procedure wait_cycles(n : natural) is
        begin
            for i in 1 to n loop
                wait until rising_edge(clk);
            end loop;
        end procedure;

        procedure clear_enables is
        begin
            en_a <= '0';
            en_b <= '0';
            en_y <= '0';
        end procedure;

        procedure scramble_network is
        begin
            clamp_a_en <= '0';
            clamp_b_en <= '0';
            clamp_y_en <= '0';
            en_a <= '1';
            en_b <= '1';
            en_y <= '1';
            wait_cycles(SCRAMBLE_CYCLES);
            clear_enables;
        end procedure;

        function expected_and(constant aval : natural; constant bval : natural) return std_logic is
        begin
            if aval = 1 and bval = 1 then
                return '1';
            end if;
            return '0';
        end function;

        procedure clamp_inputs(constant aval : natural; constant bval : natural) is
        begin
            clamp_a_en <= '1';
            clamp_b_en <= '1';
            clamp_y_en <= '0';
            if aval = 1 then
                clamp_a_value <= '1';
            else
                clamp_a_value <= '0';
            end if;
            if bval = 1 then
                clamp_b_value <= '1';
            else
                clamp_b_value <= '0';
            end if;
        end procedure;

        procedure run_case(constant aval : natural; constant bval : natural) is
            variable hits : natural := 0;
            variable expected : std_logic;
        begin
            expected := expected_and(aval, bval);
            for trial in 1 to TRIALS loop
                scramble_network;
                clamp_inputs(aval, bval);

                if PRIME_INPUT_CYCLES > 0 then
                    en_a <= '1';
                    en_b <= '1';
                    en_y <= '0';
                    wait_cycles(PRIME_INPUT_CYCLES);
                    clear_enables;
                end if;

                en_a <= '1';
                en_b <= '1';
                en_y <= '1';
                wait_cycles(SOLVE_CYCLES);
                clear_enables;
                wait for 1 ns;

                if y_s = expected then
                    hits := hits + 1;
                end if;
            end loop;

            total_hits := total_hits + hits;
            if hits < min_hits then
                min_hits := hits;
            end if;
            if hits < TRIALS then
                fail_cases := fail_cases + 1;
            end if;

            report "and_onecycle case A=" & integer'image(aval) &
                   " B=" & integer'image(bval) &
                   " expected=" & std_logic'image(expected) &
                   " hits=" & integer'image(hits) & "/" & integer'image(TRIALS) &
                   " solve_cycles=" & integer'image(SOLVE_CYCLES) &
                   " prime_input_cycles=" & integer'image(PRIME_INPUT_CYCLES) &
                   " rnd_weight=" & integer'image(RND_WEIGHT) &
                   " frac_bits=" & integer'image(FIELD_FRAC_BITS)
                   severity note;
        end procedure;
    begin
        rst <= '1';
        wait_cycles(4);
        rst <= '0';
        wait_cycles(4);

        run_case(0, 0);
        run_case(0, 1);
        run_case(1, 0);
        run_case(1, 1);

        report "and_onecycle summary cases=4 total_hits=" &
               integer'image(total_hits) & "/" & integer'image(4 * TRIALS) &
               " success_rate_x10000=" & integer'image((total_hits * 10000) / (4 * TRIALS)) &
               " min_hits=" & integer'image(min_hits) &
               " fail_cases=" & integer'image(fail_cases) &
               " solve_cycles=" & integer'image(SOLVE_CYCLES) &
               " prime_input_cycles=" & integer'image(PRIME_INPUT_CYCLES) &
               " rnd_weight=" & integer'image(RND_WEIGHT) &
               " frac_bits=" & integer'image(FIELD_FRAC_BITS)
               severity note;

        report "tb_and_onecycle_sanity completed" severity note;
        wait;
    end process;
end architecture;
