library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity tb_inv_and_gate is
end entity;

architecture sim of tb_inv_and_gate is
    constant CLK_PERIOD : time := 10 ns;
    constant SETTLE_CYC : natural := 80;
    constant COUNT_CYC  : natural := 120;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal clamp_a_en    : std_logic := '0';
    signal clamp_a_value : std_logic := '0';
    signal clamp_b_en    : std_logic := '0';
    signal clamp_b_value : std_logic := '0';
    signal clamp_y_en    : std_logic := '0';
    signal clamp_y_value : std_logic := '0';

    signal a : std_logic;
    signal b : std_logic;
    signal y : std_logic;

    signal field_a : field_t;
    signal field_b : field_t;
    signal field_y : field_t;
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.inv_and_gate
        generic map (
            RND_WEIGHT   => 0,
            COUNTER_BITS => 5
        )
        port map (
            clk           => clk,
            rst           => rst,
            enable        => enable,
            clamp_a_en    => clamp_a_en,
            clamp_a_value => clamp_a_value,
            clamp_b_en    => clamp_b_en,
            clamp_b_value => clamp_b_value,
            clamp_y_en    => clamp_y_en,
            clamp_y_value => clamp_y_value,
            a             => a,
            b             => b,
            y             => y,
            field_a       => field_a,
            field_b       => field_b,
            field_y       => field_y
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
            wait_cycles(3);
            rst <= '0';
            wait_cycles(3);
        end procedure;

        procedure check_forward(
            constant a_in  : std_logic;
            constant b_in  : std_logic;
            constant y_exp : std_logic
        ) is
            variable ones : natural := 0;
        begin
            clamp_a_en    <= '1';
            clamp_a_value <= a_in;
            clamp_b_en    <= '1';
            clamp_b_value <= b_in;
            clamp_y_en    <= '0';
            reset_network;
            wait_cycles(SETTLE_CYC);

            ones := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if y = '1' then
                    ones := ones + 1;
                end if;
            end loop;

            if y_exp = '1' then
                assert ones > (COUNT_CYC * 9) / 10
                    report "AND forward failed: Y should be 1"
                    severity failure;
            else
                assert ones < COUNT_CYC / 10
                    report "AND forward failed: Y should be 0"
                    severity failure;
            end if;
        end procedure;

        procedure check_reverse_y_one is
            variable both_one : natural := 0;
        begin
            clamp_a_en <= '0';
            clamp_b_en <= '0';
            clamp_y_en    <= '1';
            clamp_y_value <= '1';
            reset_network;
            wait_cycles(SETTLE_CYC);

            both_one := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if a = '1' and b = '1' then
                    both_one := both_one + 1;
                end if;
            end loop;

            assert both_one > (COUNT_CYC * 9) / 10
                report "AND reverse failed: Y=1 should force A=B=1"
                severity failure;
        end procedure;

        procedure check_reverse_y_zero is
            variable invalid : natural := 0;
        begin
            clamp_a_en <= '0';
            clamp_b_en <= '0';
            clamp_y_en    <= '1';
            clamp_y_value <= '0';
            reset_network;
            wait_cycles(SETTLE_CYC);

            invalid := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if a = '1' and b = '1' then
                    invalid := invalid + 1;
                end if;
            end loop;

            assert invalid < COUNT_CYC / 10
                report "AND reverse failed: Y=0 should reject A=B=1"
                severity failure;
        end procedure;
    begin
        check_forward('0', '0', '0');
        check_forward('0', '1', '0');
        check_forward('1', '0', '0');
        check_forward('1', '1', '1');
        check_reverse_y_one;
        check_reverse_y_zero;

        report "tb_inv_and_gate passed" severity note;
        wait;
    end process;
end architecture;
