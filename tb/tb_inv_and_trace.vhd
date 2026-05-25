library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use std.textio.all;
use std.env.all;

use work.inv_sc_pkg.all;

entity tb_inv_and_trace is
end entity;

architecture sim of tb_inv_and_trace is
    constant CLK_PERIOD : time := 10 ns;
    constant SETTLE_CYC : natural := 100;
    constant SAMPLE_CYC : natural := 30000;

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

    signal scenario_id : integer range 0 to 5 := 0;
    signal measure     : std_logic := '0';
    signal log_enable  : std_logic := '0';

    file trace_file : text open write_mode is "and_trace.csv";

    function sl_to_int(value : std_logic) return integer is
    begin
        if value = '1' then
            return 1;
        else
            return 0;
        end if;
    end function;
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.inv_and_gate
        generic map (
            RND_WEIGHT   => 0,
            COUNTER_BITS => 3
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

    logger : process
        variable row : line;
    begin
        write(row, string'("time_ns,scenario,measure,clamp_a_en,clamp_a_value,"));
        write(row, string'("clamp_b_en,clamp_b_value,clamp_y_en,clamp_y_value,"));
        write(row, string'("a,b,y,field_a,field_b,field_y"));
        writeline(trace_file, row);

        loop
            wait until rising_edge(clk);

            if log_enable = '1' then
                write(row, integer'image(integer(now / 1 ns)));
                write(row, string'(","));
                write(row, integer'image(scenario_id));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(measure)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(clamp_a_en)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(clamp_a_value)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(clamp_b_en)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(clamp_b_value)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(clamp_y_en)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(clamp_y_value)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(a)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(b)));
                write(row, string'(","));
                write(row, integer'image(sl_to_int(y)));
                write(row, string'(","));
                write(row, integer'image(to_integer(field_a)));
                write(row, string'(","));
                write(row, integer'image(to_integer(field_b)));
                write(row, string'(","));
                write(row, integer'image(to_integer(field_y)));
                writeline(trace_file, row);
            end if;
        end loop;
    end process;

    stimulus : process
        procedure wait_cycles(n : natural) is
        begin
            for i in 1 to n loop
                wait until rising_edge(clk);
            end loop;
        end procedure;

        procedure reset_network is
        begin
            log_enable <= '0';
            measure    <= '0';
            rst        <= '1';
            wait_cycles(3);
            rst <= '0';
            wait_cycles(3);
        end procedure;

        procedure run_trace_case(
            constant id          : integer;
            constant a_en        : std_logic;
            constant a_value     : std_logic;
            constant b_en        : std_logic;
            constant b_value     : std_logic;
            constant y_en        : std_logic;
            constant y_value     : std_logic
        ) is
        begin
            scenario_id   <= id;
            clamp_a_en    <= a_en;
            clamp_a_value <= a_value;
            clamp_b_en    <= b_en;
            clamp_b_value <= b_value;
            clamp_y_en    <= y_en;
            clamp_y_value <= y_value;

            reset_network;

            log_enable <= '1';
            measure    <= '0';
            wait_cycles(SETTLE_CYC);

            measure <= '1';
            wait_cycles(SAMPLE_CYC);

            log_enable <= '0';
            measure    <= '0';
            wait_cycles(4);
        end procedure;
    begin
        run_trace_case(0, '1', '0', '1', '0', '0', '0');
        run_trace_case(1, '1', '0', '1', '1', '0', '0');
        run_trace_case(2, '1', '1', '1', '0', '0', '0');
        run_trace_case(3, '1', '1', '1', '1', '0', '0');
        run_trace_case(4, '0', '0', '0', '0', '1', '0');
        run_trace_case(5, '0', '0', '0', '0', '1', '1');

        report "AND trace written to and_trace.csv" severity note;
        finish;
        wait;
    end process;
end architecture;
