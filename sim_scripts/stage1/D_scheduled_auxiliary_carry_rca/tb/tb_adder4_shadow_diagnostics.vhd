library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_shadow_diagnostics is
    generic (
        BLOCK_RND_WEIGHT : natural := 1;
        COPY_RND_WEIGHT  : natural := 0;
        BLOCK0_CYCLES    : natural := 12;
        BLOCK1_CYCLES    : natural := 32;
        BLOCK2_CYCLES    : natural := 32;
        BLOCK3_CYCLES    : natural := 8;
        COPY_CYCLES      : natural := 8;
        COUNT_CYCLES     : natural := 100
    );
end entity;

architecture sim of tb_adder4_shadow_diagnostics is
    constant CLK_PERIOD : time := 10 ns;
    type histogram_t is array (0 to 31) of natural;
    type shadow_counts_t is array (1 to 3) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal block_en0, block_en1, block_en2, block_en3 : std_logic := '0';
    signal write_en1, write_en2, write_en3 : std_logic := '0';
    signal xfer_en1, xfer_en2, xfer_en3 : std_logic := '0';

    signal clamp_en, clamp_value, spins : std_logic_vector(21 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder4_shadow_windowed
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
            block_en0   => block_en0,
            block_en1   => block_en1,
            block_en2   => block_en2,
            block_en3   => block_en3,
            write_en1   => write_en1,
            write_en2   => write_en2,
            write_en3   => write_en3,
            xfer_en1    => xfer_en1,
            xfer_en2    => xfer_en2,
            xfer_en3    => xfer_en3,
            block_rnd   => BLOCK_RND_WEIGHT,
            copy_rnd    => COPY_RND_WEIGHT,
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
            write_en1 <= '0';
            write_en2 <= '0';
            write_en3 <= '0';
            xfer_en1 <= '0';
            xfer_en2 <= '0';
            xfer_en3 <= '0';
        end procedure;

        procedure reset_network is
        begin
            clear_enables;
            rst <= '1';
            wait_cycles(4);
            rst <= '0';
            wait_cycles(4);
        end procedure;

        procedure write_shadow(signal write_en : out std_logic; signal xfer_en : out std_logic) is
        begin
            write_en <= '1';
            wait_cycles(COPY_CYCLES);
            write_en <= '0';
            xfer_en <= '1';
            wait_cycles(COPY_CYCLES);
            xfer_en <= '0';
        end procedure;

        procedure run_shadow_schedule is
        begin
            block_en0 <= '1';
            wait_cycles(BLOCK0_CYCLES);
            block_en0 <= '0';
            write_shadow(write_en1, xfer_en1);

            block_en1 <= '1';
            wait_cycles(BLOCK1_CYCLES);
            block_en1 <= '0';
            write_shadow(write_en2, xfer_en2);

            block_en2 <= '1';
            wait_cycles(BLOCK2_CYCLES);
            block_en2 <= '0';
            write_shadow(write_en3, xfer_en3);

            block_en3 <= '1';
            wait_cycles(BLOCK3_CYCLES);
            block_en3 <= '0';
        end procedure;

        function sum_value(sp : std_logic_vector(21 downto 0)) return natural is
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

        procedure report_histogram(variable hist : inout histogram_t) is
            variable best_sum   : natural := 0;
            variable best_count : natural := 0;
        begin
            for rank in 1 to 4 loop
                best_sum := 0;
                best_count := 0;
                for value in 0 to 31 loop
                    if hist(value) > best_count then
                        best_count := hist(value);
                        best_sum := value;
                    end if;
                end loop;
                if best_count > 0 then
                    report "  top" & integer'image(rank) &
                           " sum=" & integer'image(best_sum) &
                           " count=" & integer'image(best_count)
                           severity note;
                    hist(best_sum) := 0;
                end if;
            end loop;
        end procedure;

        procedure check_forward(constant aval : natural; constant bval : natural) is
            variable hist        : histogram_t := (others => 0);
            variable shadow_hits : shadow_counts_t := (others => 0);
            variable sample_sum  : natural;
            variable expected    : natural := aval + bval;
        begin
            clamp_inputs(aval, bval);
            reset_network;
            run_shadow_schedule;

            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                sample_sum := sum_value(spins);
                hist(sample_sum) := hist(sample_sum) + 1;
                if spins(16) = spins(19) then shadow_hits(1) := shadow_hits(1) + 1; end if;
                if spins(17) = spins(20) then shadow_hits(2) := shadow_hits(2) + 1; end if;
                if spins(18) = spins(21) then shadow_hits(3) := shadow_hits(3) + 1; end if;
            end loop;

            report "shadow4 forward " & integer'image(aval) & "+" & integer'image(bval) &
                   " expected_sum=" & integer'image(expected) &
                   " hits=" & integer'image(hist(expected)) & "/" & integer'image(COUNT_CYCLES) &
                   " block_rnd=" & integer'image(BLOCK_RND_WEIGHT) &
                   " copy_rnd=" & integer'image(COPY_RND_WEIGHT) &
                   " blocks=" & integer'image(BLOCK0_CYCLES) & "," &
                                integer'image(BLOCK1_CYCLES) & "," &
                                integer'image(BLOCK2_CYCLES) & "," &
                                integer'image(BLOCK3_CYCLES) &
                   " copy=" & integer'image(COPY_CYCLES)
                   severity note;
            report_histogram(hist);
            for bit in 1 to 3 loop
                report "  w" & integer'image(bit) & "_r" & integer'image(bit) &
                       "_match=" & integer'image(shadow_hits(bit)) &
                       "/" & integer'image(COUNT_CYCLES)
                       severity note;
            end loop;
        end procedure;
    begin
        check_forward(0, 0);
        check_forward(1, 1);
        check_forward(2, 3);
        check_forward(3, 1);
        check_forward(4, 4);
        check_forward(5, 2);
        check_forward(6, 9);
        check_forward(7, 1);
        check_forward(7, 8);
        check_forward(8, 7);
        check_forward(9, 6);
        check_forward(10, 5);
        check_forward(11, 4);
        check_forward(12, 3);
        check_forward(14, 1);
        check_forward(15, 1);
        report "tb_adder4_shadow_diagnostics completed" severity note;
        wait;
    end process;
end architecture;
