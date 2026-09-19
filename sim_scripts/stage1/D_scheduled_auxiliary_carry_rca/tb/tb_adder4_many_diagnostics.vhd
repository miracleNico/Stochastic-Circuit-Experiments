library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_many_diagnostics is
    generic (
        ADDER_RND_WEIGHT : natural := 1;
        SETTLE_CYCLES    : natural := 128;
        COUNT_CYCLES     : natural := 100
    );
end entity;

architecture sim of tb_adder4_many_diagnostics is
    constant CLK_PERIOD : time := 10 ns;
    type histogram_t is array (0 to 31) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal clamp_en, clamp_value, spins : std_logic_vector(15 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder4
        generic map (RND_WEIGHT => ADDER_RND_WEIGHT)
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
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

        procedure reset_network is
        begin
            rst <= '1';
            wait_cycles(4);
            rst <= '0';
            wait_cycles(4);
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
            variable hist       : histogram_t := (others => 0);
            variable sample_sum : natural;
            variable expected   : natural := aval + bval;
        begin
            clamp_inputs(aval, bval);
            reset_network;
            wait_cycles(SETTLE_CYCLES);

            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                sample_sum := sum_value(spins);
                hist(sample_sum) := hist(sample_sum) + 1;
            end loop;

            report "many4 forward " & integer'image(aval) & "+" & integer'image(bval) &
                   " expected_sum=" & integer'image(expected) &
                   " hits=" & integer'image(hist(expected)) & "/" & integer'image(COUNT_CYCLES) &
                   " rnd=" & integer'image(ADDER_RND_WEIGHT) &
                   " settle=" & integer'image(SETTLE_CYCLES)
                   severity note;
            report_histogram(hist);
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
        report "tb_adder4_many_diagnostics completed" severity note;
        wait;
    end process;
end architecture;
