library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_shadow1_exhaustive is
    generic (
        BLOCK_RND_WEIGHT : natural := 1;
        COPY_RND_WEIGHT  : natural := 0;
        BLOCK0_CYCLES    : natural := 10;
        BLOCK1_CYCLES    : natural := 16;
        BLOCK2_CYCLES    : natural := 16;
        BLOCK3_CYCLES    : natural := 8;
        COPY_CYCLES      : natural := 1;
        COUNT_CYCLES     : natural := 1000
    );
end entity;

architecture sim of tb_adder4_shadow1_exhaustive is
    constant CLK_PERIOD : time := 10 ns;
    type histogram_t is array (0 to 31) of natural;
    type shadow_counts_t is array (1 to 3) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal block_en0, block_en1, block_en2, block_en3 : std_logic := '0';
    signal copy_en1, copy_en2, copy_en3 : std_logic := '0';

    signal clamp_en, clamp_value, spins : std_logic_vector(18 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder4_shadow1_windowed
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
            block_en0   => block_en0,
            block_en1   => block_en1,
            block_en2   => block_en2,
            block_en3   => block_en3,
            copy_en1    => copy_en1,
            copy_en2    => copy_en2,
            copy_en3    => copy_en3,
            block_rnd   => BLOCK_RND_WEIGHT,
            copy_rnd    => COPY_RND_WEIGHT,
            clamp_en    => clamp_en,
            clamp_value => clamp_value,
            spins       => spins
        );

    stimulus : process
        variable total_hits      : natural := 0;
        variable min_hits        : natural := COUNT_CYCLES;
        variable perfect_cases   : natural := 0;
        variable failed_cases    : natural := 0;
        variable shadow_min_hits : shadow_counts_t := (others => COUNT_CYCLES);

        procedure wait_cycles(n : natural) is
        begin
            for i in 1 to n loop
                wait until rising_edge(clk);
            end loop;
        end procedure;

        procedure clear_enables is
        begin
            block_en0 <= '0';
            block_en1 <= '0';
            block_en2 <= '0';
            block_en3 <= '0';
            copy_en1 <= '0';
            copy_en2 <= '0';
            copy_en3 <= '0';
        end procedure;

        procedure reset_network is
        begin
            clear_enables;
            rst <= '1';
            wait_cycles(4);
            rst <= '0';
            wait_cycles(4);
        end procedure;

        procedure copy_shadow(signal copy_en : out std_logic) is
        begin
            copy_en <= '1';
            wait_cycles(COPY_CYCLES);
            copy_en <= '0';
        end procedure;

        procedure run_shadow_schedule is
        begin
            block_en0 <= '1';
            wait_cycles(BLOCK0_CYCLES);
            block_en0 <= '0';
            copy_shadow(copy_en1);

            block_en1 <= '1';
            wait_cycles(BLOCK1_CYCLES);
            block_en1 <= '0';
            copy_shadow(copy_en2);

            block_en2 <= '1';
            wait_cycles(BLOCK2_CYCLES);
            block_en2 <= '0';
            copy_shadow(copy_en3);

            block_en3 <= '1';
            wait_cycles(BLOCK3_CYCLES);
            block_en3 <= '0';
        end procedure;

        function sum_value(sp : std_logic_vector(18 downto 0)) return natural is
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

        procedure clamp_inputs(constant aval : natural; constant bval : natural) is
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

        function histogram_best_sum(hist : histogram_t) return natural is
            variable best_sum   : natural := 0;
            variable best_count : natural := 0;
        begin
            for value in 0 to 31 loop
                if hist(value) > best_count then
                    best_count := hist(value);
                    best_sum := value;
                end if;
            end loop;
            return best_sum;
        end function;

        procedure check_case(constant aval : natural; constant bval : natural) is
            variable hist        : histogram_t := (others => 0);
            variable shadow_hits : shadow_counts_t := (others => 0);
            variable sample_sum  : natural;
            variable expected    : natural := aval + bval;
            variable hits        : natural;
            variable best_sum    : natural;
        begin
            clamp_inputs(aval, bval);
            reset_network;
            run_shadow_schedule;

            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                sample_sum := sum_value(spins);
                hist(sample_sum) := hist(sample_sum) + 1;
                if spins(16) = spins(12) then shadow_hits(1) := shadow_hits(1) + 1; end if;
                if spins(17) = spins(13) then shadow_hits(2) := shadow_hits(2) + 1; end if;
                if spins(18) = spins(14) then shadow_hits(3) := shadow_hits(3) + 1; end if;
            end loop;

            hits := hist(expected);
            total_hits := total_hits + hits;
            if hits < min_hits then
                min_hits := hits;
            end if;
            if hits = COUNT_CYCLES then
                perfect_cases := perfect_cases + 1;
            else
                failed_cases := failed_cases + 1;
                best_sum := histogram_best_sum(hist);
                report "shadow1 exhaustive fail " & integer'image(aval) & "+" & integer'image(bval) &
                       " expected_sum=" & integer'image(expected) &
                       " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYCLES) &
                       " top_sum=" & integer'image(best_sum) &
                       " top_count=" & integer'image(hist(best_sum))
                       severity note;
            end if;

            for bit in 1 to 3 loop
                if shadow_hits(bit) < shadow_min_hits(bit) then
                    shadow_min_hits(bit) := shadow_hits(bit);
                end if;
            end loop;
        end procedure;
    begin
        for aval in 0 to 15 loop
            for bval in 0 to 15 loop
                check_case(aval, bval);
            end loop;
        end loop;

        report "shadow1 exhaustive completed cases=256 perfect=" & integer'image(perfect_cases) &
               " failed=" & integer'image(failed_cases) &
               " total_hits=" & integer'image(total_hits) & "/" & integer'image(256 * COUNT_CYCLES) &
               " min_hits=" & integer'image(min_hits) &
               " block_rnd=" & integer'image(BLOCK_RND_WEIGHT) &
               " copy_rnd=" & integer'image(COPY_RND_WEIGHT) &
               " blocks=" & integer'image(BLOCK0_CYCLES) & "," &
                            integer'image(BLOCK1_CYCLES) & "," &
                            integer'image(BLOCK2_CYCLES) & "," &
                            integer'image(BLOCK3_CYCLES) &
               " copy=" & integer'image(COPY_CYCLES)
               severity note;
        report "shadow1 exhaustive shadow_min q1=" & integer'image(shadow_min_hits(1)) &
               " q2=" & integer'image(shadow_min_hits(2)) &
               " q3=" & integer'image(shadow_min_hits(3)) &
               "/" & integer'image(COUNT_CYCLES)
               severity note;
        wait;
    end process;
end architecture;
