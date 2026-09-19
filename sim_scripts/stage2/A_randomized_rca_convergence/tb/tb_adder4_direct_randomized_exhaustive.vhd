library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_direct_randomized_exhaustive is
    generic (
        ADDER_RND_WEIGHT : natural := 1;
        SCRAMBLE_CYCLES  : natural := 80;
        SETTLE_CYCLES    : natural := 500;
        TRIALS           : natural := 100
    );
end entity;

architecture sim of tb_adder4_direct_randomized_exhaustive is
    constant CLK_PERIOD : time := 10 ns;
    type hist32_t is array (0 to 31) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal clamp_en, clamp_value, spins : std_logic_vector(15 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder4
        generic map (
            RND_WEIGHT => ADDER_RND_WEIGHT
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
            clamp_en    => clamp_en,
            clamp_value => clamp_value,
            spins       => spins
        );

    stimulus : process
        variable forward_total_hits : natural := 0;
        variable forward_min_hits   : natural := TRIALS;
        variable forward_fail_cases : natural := 0;

        procedure wait_cycles(n : natural) is
        begin
            for i in 1 to n loop
                wait until rising_edge(clk);
            end loop;
        end procedure;

        procedure reset_once is
        begin
            clamp_en <= (others => '0');
            rst <= '1';
            wait_cycles(4);
            rst <= '0';
            wait_cycles(4);
        end procedure;

        procedure scramble_network is
        begin
            clamp_en <= (others => '0');
            wait_cycles(SCRAMBLE_CYCLES);
        end procedure;

        function sum_value(sp : std_logic_vector(15 downto 0)) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 3 loop
                if sp(8 + bit) = '1' then
                    value := value + (2 ** bit);
                end if;
            end loop;
            if sp(15) = '1' then
                value := value + 16;
            end if;
            return value;
        end function;

        function best_index(hist : hist32_t) return natural is
            variable best_value : natural := 0;
            variable best_count : natural := 0;
        begin
            for value in 0 to 31 loop
                if hist(value) > best_count then
                    best_count := hist(value);
                    best_value := value;
                end if;
            end loop;
            return best_value;
        end function;

        procedure clamp_forward(constant aval : natural; constant bval : natural) is
        begin
            clamp_en <= (others => '0');
            clamp_value <= (others => '0');
            for bit in 0 to 3 loop
                clamp_en(bit) <= '1';
                clamp_en(4 + bit) <= '1';
                if ((aval / (2 ** bit)) mod 2) = 1 then
                    clamp_value(bit) <= '1';
                end if;
                if ((bval / (2 ** bit)) mod 2) = 1 then
                    clamp_value(4 + bit) <= '1';
                end if;
            end loop;
        end procedure;

        procedure check_forward_case(constant aval : natural; constant bval : natural) is
            variable hist     : hist32_t := (others => 0);
            variable expected : natural := aval + bval;
            variable sample   : natural;
            variable hits     : natural;
            variable best     : natural;
        begin
            for trial in 1 to TRIALS loop
                scramble_network;
                clamp_forward(aval, bval);
                wait_cycles(SETTLE_CYCLES);
                sample := sum_value(spins);
                hist(sample) := hist(sample) + 1;
            end loop;
            hits := hist(expected);
            best := best_index(hist);
            forward_total_hits := forward_total_hits + hits;
            if hits < forward_min_hits then
                forward_min_hits := hits;
            end if;
            if hits < TRIALS then
                forward_fail_cases := forward_fail_cases + 1;
            end if;
            report "random4_direct forward case A=" & integer'image(aval) &
                   " B=" & integer'image(bval) &
                   " expected=" & integer'image(expected) &
                   " hits=" & integer'image(hits) & "/" & integer'image(TRIALS) &
                   " top=" & integer'image(best) &
                   " top_count=" & integer'image(hist(best))
                   severity note;
        end procedure;
    begin
        reset_once;
        for aval in 0 to 15 loop
            for bval in 0 to 15 loop
                check_forward_case(aval, bval);
            end loop;
        end loop;

        report "random4_direct forward summary cases=256 total_hits=" &
               integer'image(forward_total_hits) & "/" & integer'image(256 * TRIALS) &
               " min_hits=" & integer'image(forward_min_hits) &
               " fail_cases=" & integer'image(forward_fail_cases) &
               " rnd=" & integer'image(ADDER_RND_WEIGHT) &
               " scramble_cycles=" & integer'image(SCRAMBLE_CYCLES) &
               " settle_cycles=" & integer'image(SETTLE_CYCLES)
               severity note;

        report "tb_adder4_direct_randomized_exhaustive completed" severity note;
        wait;
    end process;
end architecture;
