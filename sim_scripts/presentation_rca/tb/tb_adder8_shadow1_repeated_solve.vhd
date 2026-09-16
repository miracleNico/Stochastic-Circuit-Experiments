library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder8_shadow1_repeated_solve is
    generic (
        BLOCK_RND_WEIGHT    : natural := 4;
        COPY_RND_WEIGHT     : natural := 0;
        SCRAMBLE_RND_WEIGHT : natural := 8;
        SCRAMBLE_CYCLES     : natural := 80;
        BLOCK0_CYCLES       : natural := 40;
        BLOCK1_CYCLES       : natural := 40;
        BLOCK2_CYCLES       : natural := 40;
        BLOCK3_CYCLES       : natural := 40;
        BLOCK4_CYCLES       : natural := 40;
        BLOCK5_CYCLES       : natural := 40;
        BLOCK6_CYCLES       : natural := 40;
        BLOCK7_CYCLES       : natural := 40;
        COPY_CYCLES         : natural := 2;
        TRIALS              : natural := 200
    );
end entity;

architecture sim of tb_adder8_shadow1_repeated_solve is
    constant CLK_PERIOD : time := 10 ns;
    type histogram_t is array (0 to 511) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal block_en0, block_en1, block_en2, block_en3 : std_logic := '0';
    signal block_en4, block_en5, block_en6, block_en7 : std_logic := '0';
    signal copy_en1, copy_en2, copy_en3, copy_en4 : std_logic := '0';
    signal copy_en5, copy_en6, copy_en7 : std_logic := '0';

    signal block_rnd_s : natural := BLOCK_RND_WEIGHT;
    signal copy_rnd_s  : natural := COPY_RND_WEIGHT;
    signal clamp_en, clamp_value, spins : std_logic_vector(38 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder8_shadow1_windowed
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
            block_en0   => block_en0,
            block_en1   => block_en1,
            block_en2   => block_en2,
            block_en3   => block_en3,
            block_en4   => block_en4,
            block_en5   => block_en5,
            block_en6   => block_en6,
            block_en7   => block_en7,
            copy_en1    => copy_en1,
            copy_en2    => copy_en2,
            copy_en3    => copy_en3,
            copy_en4    => copy_en4,
            copy_en5    => copy_en5,
            copy_en6    => copy_en6,
            copy_en7    => copy_en7,
            block_rnd   => block_rnd_s,
            copy_rnd    => copy_rnd_s,
            clamp_en    => clamp_en,
            clamp_value => clamp_value,
            spins       => spins
        );

    stimulus : process
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
            block_en4 <= '0';
            block_en5 <= '0';
            block_en6 <= '0';
            block_en7 <= '0';
            copy_en1 <= '0';
            copy_en2 <= '0';
            copy_en3 <= '0';
            copy_en4 <= '0';
            copy_en5 <= '0';
            copy_en6 <= '0';
            copy_en7 <= '0';
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
            copy_shadow(copy_en4);

            block_en4 <= '1';
            wait_cycles(BLOCK4_CYCLES);
            block_en4 <= '0';
            copy_shadow(copy_en5);

            block_en5 <= '1';
            wait_cycles(BLOCK5_CYCLES);
            block_en5 <= '0';
            copy_shadow(copy_en6);

            block_en6 <= '1';
            wait_cycles(BLOCK6_CYCLES);
            block_en6 <= '0';
            copy_shadow(copy_en7);

            block_en7 <= '1';
            wait_cycles(BLOCK7_CYCLES);
            block_en7 <= '0';
        end procedure;

        procedure scramble_network is
        begin
            clamp_en <= (others => '0');
            block_rnd_s <= SCRAMBLE_RND_WEIGHT;
            copy_rnd_s <= SCRAMBLE_RND_WEIGHT;
            block_en0 <= '1';
            block_en1 <= '1';
            block_en2 <= '1';
            block_en3 <= '1';
            block_en4 <= '1';
            block_en5 <= '1';
            block_en6 <= '1';
            block_en7 <= '1';
            copy_en1 <= '1';
            copy_en2 <= '1';
            copy_en3 <= '1';
            copy_en4 <= '1';
            copy_en5 <= '1';
            copy_en6 <= '1';
            copy_en7 <= '1';
            wait_cycles(SCRAMBLE_CYCLES);
            clear_enables;
            block_rnd_s <= BLOCK_RND_WEIGHT;
            copy_rnd_s <= COPY_RND_WEIGHT;
        end procedure;

        function sum_value(sp : std_logic_vector(38 downto 0)) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 7 loop
                if sp(16 + bit) = '1' then
                    value := value + (2 ** bit);
                end if;
            end loop;
            if sp(31) = '1' then
                value := value + 256;
            end if;
            return value;
        end function;

        procedure clamp_inputs(constant aval : natural; constant bval : natural) is
        begin
            clamp_en <= (others => '0');
            clamp_value <= (others => '0');
            for bit in 0 to 7 loop
                clamp_en(bit) <= '1';
                clamp_en(8 + bit) <= '1';
                if ((aval / (2 ** bit)) mod 2) = 1 then
                    clamp_value(bit) <= '1';
                end if;
                if ((bval / (2 ** bit)) mod 2) = 1 then
                    clamp_value(8 + bit) <= '1';
                end if;
            end loop;
        end procedure;

        function histogram_best_sum(hist : histogram_t) return natural is
            variable best_sum   : natural := 0;
            variable best_count : natural := 0;
        begin
            for value in 0 to 511 loop
                if hist(value) > best_count then
                    best_count := hist(value);
                    best_sum := value;
                end if;
            end loop;
            return best_sum;
        end function;

        procedure report_top_histogram(variable hist : inout histogram_t) is
            variable best_sum   : natural;
            variable best_count : natural;
        begin
            for rank in 1 to 6 loop
                best_sum := histogram_best_sum(hist);
                best_count := hist(best_sum);
                if best_count > 0 then
                    report "  top" & integer'image(rank) &
                           " sum=" & integer'image(best_sum) &
                           " count=" & integer'image(best_count)
                           severity note;
                    hist(best_sum) := 0;
                end if;
            end loop;
        end procedure;

        procedure check_repeated(constant aval : natural; constant bval : natural) is
            variable hist       : histogram_t := (others => 0);
            variable hist_copy  : histogram_t := (others => 0);
            variable expected   : natural := aval + bval;
            variable sample_sum : natural;
            variable hits       : natural := 0;
            variable distinct   : natural := 0;
        begin
            for trial in 1 to TRIALS loop
                scramble_network;
                clamp_inputs(aval, bval);
                run_shadow_schedule;
                sample_sum := sum_value(spins);
                hist(sample_sum) := hist(sample_sum) + 1;
                if sample_sum = expected then
                    hits := hits + 1;
                end if;
            end loop;

            for value in 0 to 511 loop
                hist_copy(value) := hist(value);
                if hist(value) > 0 then
                    distinct := distinct + 1;
                end if;
            end loop;

            report "repeated solve " & integer'image(aval) & "+" & integer'image(bval) &
                   " expected_sum=" & integer'image(expected) &
                   " hits=" & integer'image(hits) & "/" & integer'image(TRIALS) &
                   " distinct_sums=" & integer'image(distinct) &
                   " block_rnd=" & integer'image(BLOCK_RND_WEIGHT) &
                   " scramble_rnd=" & integer'image(SCRAMBLE_RND_WEIGHT) &
                   " scramble_cycles=" & integer'image(SCRAMBLE_CYCLES) &
                   " blocks=" & integer'image(BLOCK0_CYCLES) & "," &
                                integer'image(BLOCK1_CYCLES) & "," &
                                integer'image(BLOCK2_CYCLES) & "," &
                                integer'image(BLOCK3_CYCLES) & "," &
                                integer'image(BLOCK4_CYCLES) & "," &
                                integer'image(BLOCK5_CYCLES) & "," &
                                integer'image(BLOCK6_CYCLES) & "," &
                                integer'image(BLOCK7_CYCLES) &
                   " copy=" & integer'image(COPY_CYCLES)
                   severity note;
            report_top_histogram(hist_copy);
        end procedure;
    begin
        reset_once;
        check_repeated(37, 219);
        check_repeated(142, 73);
        check_repeated(201, 54);
        check_repeated(91, 188);
        check_repeated(6, 177);
        check_repeated(127, 1);
        report "tb_adder8_shadow1_repeated_solve completed" severity note;
        wait;
    end process;
end architecture;
