library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity tb_inv_xor_gate is
end entity;

architecture sim of tb_inv_xor_gate is
    constant CLK_PERIOD : time := 10 ns;
    constant SETTLE_CYC : natural := 100;
    constant COUNT_CYC  : natural := 1000;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal clamp_a_en      : std_logic := '0';
    signal clamp_a_value   : std_logic := '0';
    signal clamp_b_en      : std_logic := '0';
    signal clamp_b_value   : std_logic := '0';
    signal clamp_y_en      : std_logic := '0';
    signal clamp_y_value   : std_logic := '0';
    signal clamp_aux_en    : std_logic := '0';
    signal clamp_aux_value : std_logic := '0';

    signal a     : std_logic;
    signal b     : std_logic;
    signal y     : std_logic;
    signal aux_c : std_logic;

    signal field_a   : field_t;
    signal field_b   : field_t;
    signal field_y   : field_t;
    signal field_aux : field_t;
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.inv_xor_gate
        generic map (
            RND_WEIGHT   => 0,
            COUNTER_BITS => 5
        )
        port map (
            clk             => clk,
            rst             => rst,
            enable          => enable,
            clamp_a_en      => clamp_a_en,
            clamp_a_value   => clamp_a_value,
            clamp_b_en      => clamp_b_en,
            clamp_b_value   => clamp_b_value,
            clamp_y_en      => clamp_y_en,
            clamp_y_value   => clamp_y_value,
            clamp_aux_en    => clamp_aux_en,
            clamp_aux_value => clamp_aux_value,
            a               => a,
            b               => b,
            y               => y,
            aux_c           => aux_c,
            field_a         => field_a,
            field_b         => field_b,
            field_y         => field_y,
            field_aux       => field_aux
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
            constant y_exp : std_logic;
            constant c_exp : std_logic
        ) is
            variable y_ones : natural := 0;
            variable c_ones : natural := 0;
        begin
            clamp_a_en      <= '1';
            clamp_a_value   <= a_in;
            clamp_b_en      <= '1';
            clamp_b_value   <= b_in;
            clamp_y_en      <= '0';
            clamp_aux_en    <= '0';
            reset_network;
            wait_cycles(SETTLE_CYC);

            y_ones := 0;
            c_ones := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if y = '1' then
                    y_ones := y_ones + 1;
                end if;
                if aux_c = '1' then
                    c_ones := c_ones + 1;
                end if;
            end loop;

            if y_exp = '1' then
                assert y_ones > (COUNT_CYC * 13) / 20
                    report "XOR forward failed: Y should be 1"
                    severity failure;
            else
                assert y_ones < (COUNT_CYC * 7) / 20
                    report "XOR forward failed: Y should be 0"
                    severity failure;
            end if;

            if c_exp = '1' then
                assert c_ones > (COUNT_CYC * 13) / 20
                    report "XOR auxiliary carry failed: C should be 1"
                    severity failure;
            else
                assert c_ones < (COUNT_CYC * 7) / 20
                    report "XOR auxiliary carry failed: C should be 0"
                    severity failure;
            end if;
        end procedure;

        procedure check_reverse(
            constant y_in       : std_logic;
            constant parity_exp : std_logic
        ) is
            variable valid : natural := 0;
        begin
            clamp_a_en   <= '0';
            clamp_b_en   <= '0';
            clamp_y_en      <= '1';
            clamp_y_value   <= y_in;
            clamp_aux_en    <= '0';
            reset_network;
            wait_cycles(SETTLE_CYC);

            valid := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if (a xor b) = parity_exp then
                    valid := valid + 1;
                end if;
            end loop;

            report "XOR reverse Y=" & std_logic'image(y_in) &
                   " valid parity samples=" & integer'image(valid) &
                   "/" & integer'image(COUNT_CYC)
                   severity note;

            assert valid > (COUNT_CYC * 7) / 10
                report "XOR reverse failed: A xor B did not match clamped Y"
                severity failure;
        end procedure;
    begin
        check_forward('0', '0', '0', '0');
        check_forward('0', '1', '1', '0');
        check_forward('1', '0', '1', '0');
        check_forward('1', '1', '0', '1');
        check_reverse('0', '0');
        check_reverse('1', '1');

        report "tb_inv_xor_gate passed" severity note;
        wait;
    end process;
end architecture;
