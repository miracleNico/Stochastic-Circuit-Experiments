library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_comb6_diagnostics is
    generic (
        COMB_RND_WEIGHT : natural := 1;
        SETTLE_CYCLES   : natural := 1000;
        COUNT_CYCLES    : natural := 1000
    );
end entity;

architecture sim of tb_comb6_diagnostics is
    constant CLK_PERIOD : time := 10 ns;

    type histogram_t is array (0 to 15) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal clamp_en, clamp_value, spins : std_logic_vector(20 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_comb6_mixed
        generic map (RND_WEIGHT => COMB_RND_WEIGHT)
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

        function bit_at(value : natural; bit : natural) return natural is
        begin
            return (value / (2 ** bit)) mod 2;
        end function;

        function bool_to_nat(value : boolean) return natural is
        begin
            if value then
                return 1;
            else
                return 0;
            end if;
        end function;

        function expected_signature(input_value : natural) return natural is
            variable x0, x1, x2, x3, x4, x5 : natural;
            variable u0, u1, u2, u3, u4 : natural;
            variable v0, v1, v2 : natural;
            variable y1, y2, y3 : natural;
        begin
            x0 := bit_at(input_value, 0);
            x1 := bit_at(input_value, 1);
            x2 := bit_at(input_value, 2);
            x3 := bit_at(input_value, 3);
            x4 := bit_at(input_value, 4);
            x5 := bit_at(input_value, 5);

            u0 := bool_to_nat(x0 = 1 and x1 = 1);
            u1 := bool_to_nat(x2 = 1 or x3 = 1);
            u2 := 1 - bool_to_nat(x4 = 1 and x5 = 1);
            u3 := (x0 + x2) mod 2;
            u4 := 1 - ((x1 + x5) mod 2);

            v0 := (u0 + u1) mod 2;
            v1 := bool_to_nat(u2 = 1 and u3 = 1);
            v2 := 1 - bool_to_nat(u1 = 1 or u4 = 1);

            y1 := bool_to_nat(v1 = 1 or v2 = 1);
            y2 := 1 - ((u3 + u4) mod 2);
            y3 := 1 - bool_to_nat(v0 = 1 and y2 = 1);

            return v0 + (2 * y1) + (4 * y2) + (8 * y3);
        end function;

        function observed_signature(sp : std_logic_vector(20 downto 0)) return natural is
            variable sig : natural := 0;
        begin
            if sp(13) = '1' then
                sig := sig + 1;
            end if;
            if sp(17) = '1' then
                sig := sig + 2;
            end if;
            if sp(18) = '1' then
                sig := sig + 4;
            end if;
            if sp(20) = '1' then
                sig := sig + 8;
            end if;
            return sig;
        end function;

        procedure clamp_inputs(constant input_value : natural) is
        begin
            clamp_en <= (others => '0');
            clamp_value <= (others => '0');
            for bit in 0 to 5 loop
                clamp_en(bit) <= '1';
                if bit_at(input_value, bit) = 1 then
                    clamp_value(bit) <= '1';
                end if;
            end loop;
        end procedure;

        procedure check_forward(
            constant input_value : natural;
            variable min_hits    : inout natural;
            variable worst_input : inout natural
        ) is
            variable hist       : histogram_t := (others => 0);
            variable sample_sig : natural;
            variable expected   : natural := expected_signature(input_value);
            variable best_sig   : natural := 0;
            variable best_count : natural := 0;
        begin
            clamp_inputs(input_value);
            reset_network;
            wait_cycles(SETTLE_CYCLES);

            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                sample_sig := observed_signature(spins);
                hist(sample_sig) := hist(sample_sig) + 1;
            end loop;

            for sig in 0 to 15 loop
                if hist(sig) > best_count then
                    best_count := hist(sig);
                    best_sig := sig;
                end if;
            end loop;

            if hist(expected) < min_hits then
                min_hits := hist(expected);
                worst_input := input_value;
            end if;

            report "comb6 forward input=" & integer'image(input_value) &
                   " expected_sig=" & integer'image(expected) &
                   " hits=" & integer'image(hist(expected)) & "/" & integer'image(COUNT_CYCLES) &
                   " top_sig=" & integer'image(best_sig) &
                   " top_count=" & integer'image(best_count)
                   severity note;
        end procedure;

        variable min_hits    : natural := COUNT_CYCLES;
        variable worst_input : natural := 0;
    begin
        for input_value in 0 to 63 loop
            check_forward(input_value, min_hits, worst_input);
        end loop;

        report "comb6 summary min_hits=" & integer'image(min_hits) &
               "/" & integer'image(COUNT_CYCLES) &
               " worst_input=" & integer'image(worst_input) &
               " expected_sig=" & integer'image(expected_signature(worst_input))
               severity note;
        report "tb_comb6_diagnostics completed" severity note;
        wait;
    end process;
end architecture;
