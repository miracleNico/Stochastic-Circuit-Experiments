library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_windowed_randomized_exhaustive is
    generic (
        ACTIVE_RND_WEIGHT   : natural := 1;
        FINAL_RND_WEIGHT    : natural := 1;
        SCRAMBLE_RND_WEIGHT : natural := 2;
        SCRAMBLE_CYCLES     : natural := 80;
        WAVE0_CYCLES        : natural := 40;
        WAVE1_CYCLES        : natural := 40;
        WAVE2_CYCLES        : natural := 40;
        WAVE3_CYCLES        : natural := 40;
        FINAL_CYCLES        : natural := 0;
        TRIALS              : natural := 100
    );
end entity;

architecture sim of tb_adder4_windowed_randomized_exhaustive is
    constant CLK_PERIOD : time := 10 ns;
    type hist32_t is array (0 to 31) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal stage_rnd0, stage_rnd1, stage_rnd2, stage_rnd3 : natural := ACTIVE_RND_WEIGHT;
    signal stage_en0, stage_en1, stage_en2, stage_en3 : std_logic := '0';

    signal clamp_en, clamp_value, spins : std_logic_vector(15 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder4_windowed
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
            stage_rnd0  => stage_rnd0,
            stage_rnd1  => stage_rnd1,
            stage_rnd2  => stage_rnd2,
            stage_rnd3  => stage_rnd3,
            stage_en0   => stage_en0,
            stage_en1   => stage_en1,
            stage_en2   => stage_en2,
            stage_en3   => stage_en3,
            clamp_en    => clamp_en,
            clamp_value => clamp_value,
            spins       => spins
        );

    stimulus : process
        variable forward_total_hits : natural := 0;
        variable forward_min_hits   : natural := TRIALS;
        variable forward_fail_cases : natural := 0;
        variable inverse_total_hits : natural := 0;
        variable inverse_min_hits   : natural := TRIALS;
        variable inverse_fail_cases : natural := 0;

        procedure wait_cycles(n : natural) is
        begin
            for i in 1 to n loop
                wait until rising_edge(clk);
            end loop;
        end procedure;

        procedure clear_enables is
        begin
            stage_en0 <= '0';
            stage_en1 <= '0';
            stage_en2 <= '0';
            stage_en3 <= '0';
        end procedure;

        procedure reset_once is
        begin
            clear_enables;
            clamp_en <= (others => '0');
            rst <= '1';
            wait_cycles(4);
            rst <= '0';
            wait_cycles(4);
        end procedure;

        procedure scramble_network is
        begin
            clamp_en <= (others => '0');
            stage_rnd0 <= SCRAMBLE_RND_WEIGHT;
            stage_rnd1 <= SCRAMBLE_RND_WEIGHT;
            stage_rnd2 <= SCRAMBLE_RND_WEIGHT;
            stage_rnd3 <= SCRAMBLE_RND_WEIGHT;
            stage_en0 <= '1';
            stage_en1 <= '1';
            stage_en2 <= '1';
            stage_en3 <= '1';
            wait_cycles(SCRAMBLE_CYCLES);
            clear_enables;
            stage_rnd0 <= ACTIVE_RND_WEIGHT;
            stage_rnd1 <= ACTIVE_RND_WEIGHT;
            stage_rnd2 <= ACTIVE_RND_WEIGHT;
            stage_rnd3 <= ACTIVE_RND_WEIGHT;
        end procedure;

        procedure run_window_schedule is
        begin
            stage_en0 <= '1';
            wait_cycles(WAVE0_CYCLES);
            stage_en0 <= '0';
            stage_en1 <= '1';
            wait_cycles(WAVE1_CYCLES);
            stage_en1 <= '0';
            stage_en2 <= '1';
            wait_cycles(WAVE2_CYCLES);
            stage_en2 <= '0';
            stage_en3 <= '1';
            wait_cycles(WAVE3_CYCLES);
            stage_en3 <= '0';

            if FINAL_CYCLES > 0 then
                stage_rnd0 <= FINAL_RND_WEIGHT;
                stage_rnd1 <= FINAL_RND_WEIGHT;
                stage_rnd2 <= FINAL_RND_WEIGHT;
                stage_rnd3 <= FINAL_RND_WEIGHT;
                stage_en0 <= '1';
                stage_en1 <= '1';
                stage_en2 <= '1';
                stage_en3 <= '1';
                wait_cycles(FINAL_CYCLES);
                clear_enables;
                stage_rnd0 <= ACTIVE_RND_WEIGHT;
                stage_rnd1 <= ACTIVE_RND_WEIGHT;
                stage_rnd2 <= ACTIVE_RND_WEIGHT;
                stage_rnd3 <= ACTIVE_RND_WEIGHT;
            end if;
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

        function a_value(sp : std_logic_vector(15 downto 0)) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 3 loop
                if sp(bit) = '1' then
                    value := value + (2 ** bit);
                end if;
            end loop;
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
                if ((aval / (2 ** bit)) mod 2) = 1 then clamp_value(bit) <= '1'; end if;
                if ((bval / (2 ** bit)) mod 2) = 1 then clamp_value(4 + bit) <= '1'; end if;
            end loop;
        end procedure;

        procedure clamp_inverse_b_sum(constant bval : natural; constant target_sum : natural) is
        begin
            clamp_en <= (others => '0');
            clamp_value <= (others => '0');
            for bit in 0 to 3 loop
                clamp_en(4 + bit) <= '1';
                if ((bval / (2 ** bit)) mod 2) = 1 then clamp_value(4 + bit) <= '1'; end if;
                clamp_en(8 + bit) <= '1';
                if ((target_sum / (2 ** bit)) mod 2) = 1 then clamp_value(8 + bit) <= '1'; end if;
            end loop;
            clamp_en(15) <= '1';
            if ((target_sum / 16) mod 2) = 1 then clamp_value(15) <= '1'; end if;
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
                run_window_schedule;
                sample := sum_value(spins);
                hist(sample) := hist(sample) + 1;
            end loop;
            hits := hist(expected);
            best := best_index(hist);
            forward_total_hits := forward_total_hits + hits;
            if hits < forward_min_hits then forward_min_hits := hits; end if;
            if hits < TRIALS then forward_fail_cases := forward_fail_cases + 1; end if;
            report "random4_window forward case A=" & integer'image(aval) &
                   " B=" & integer'image(bval) &
                   " expected=" & integer'image(expected) &
                   " hits=" & integer'image(hits) & "/" & integer'image(TRIALS) &
                   " top=" & integer'image(best) &
                   " top_count=" & integer'image(hist(best))
                   severity note;
        end procedure;

        procedure check_inverse_case(constant aval : natural; constant bval : natural) is
            variable hist       : hist32_t := (others => 0);
            variable target_sum : natural := aval + bval;
            variable sample     : natural;
            variable hits       : natural;
            variable best       : natural;
        begin
            for trial in 1 to TRIALS loop
                scramble_network;
                clamp_inverse_b_sum(bval, target_sum);
                run_window_schedule;
                sample := a_value(spins);
                hist(sample) := hist(sample) + 1;
            end loop;
            hits := hist(aval);
            best := best_index(hist);
            inverse_total_hits := inverse_total_hits + hits;
            if hits < inverse_min_hits then inverse_min_hits := hits; end if;
            if hits < TRIALS then inverse_fail_cases := inverse_fail_cases + 1; end if;
            report "random4_window inverse_bsum case A=" & integer'image(aval) &
                   " B=" & integer'image(bval) &
                   " SUM=" & integer'image(target_sum) &
                   " hits=" & integer'image(hits) & "/" & integer'image(TRIALS) &
                   " topA=" & integer'image(best) &
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

        report "random4_window forward summary cases=256 total_hits=" &
               integer'image(forward_total_hits) & "/" & integer'image(256 * TRIALS) &
               " min_hits=" & integer'image(forward_min_hits) &
               " fail_cases=" & integer'image(forward_fail_cases) &
               " active_rnd=" & integer'image(ACTIVE_RND_WEIGHT) &
               " scramble_rnd=" & integer'image(SCRAMBLE_RND_WEIGHT) &
               " waves=" & integer'image(WAVE0_CYCLES) & "," &
                           integer'image(WAVE1_CYCLES) & "," &
                           integer'image(WAVE2_CYCLES) & "," &
                           integer'image(WAVE3_CYCLES) &
               " final=" & integer'image(FINAL_CYCLES)
               severity note;

        for aval in 0 to 15 loop
            for bval in 0 to 15 loop
                check_inverse_case(aval, bval);
            end loop;
        end loop;

        report "random4_window inverse_bsum summary cases=256 total_hits=" &
               integer'image(inverse_total_hits) & "/" & integer'image(256 * TRIALS) &
               " min_hits=" & integer'image(inverse_min_hits) &
               " fail_cases=" & integer'image(inverse_fail_cases) &
               " active_rnd=" & integer'image(ACTIVE_RND_WEIGHT) &
               " scramble_rnd=" & integer'image(SCRAMBLE_RND_WEIGHT) &
               " waves=" & integer'image(WAVE0_CYCLES) & "," &
                           integer'image(WAVE1_CYCLES) & "," &
                           integer'image(WAVE2_CYCLES) & "," &
                           integer'image(WAVE3_CYCLES) &
               " final=" & integer'image(FINAL_CYCLES)
               severity note;

        report "tb_adder4_windowed_randomized_exhaustive completed" severity note;
        wait;
    end process;
end architecture;
