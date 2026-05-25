library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_integer_block_timing is
    generic (
        RND_WEIGHT    : natural := 1;
        SETTLE_CYCLES : natural := 20;
        COUNT_CYCLES  : natural := 100
    );
end entity;

architecture sim of tb_integer_block_timing is
    constant CLK_PERIOD : time := 10 ns;

    signal clk    : std_logic := '0';
    signal rst_ha : std_logic := '1';
    signal rst_fa : std_logic := '1';
    signal enable : std_logic := '1';

    signal ha_clamp_en, ha_clamp_value, ha_spins : std_logic_vector(3 downto 0) := (others => '0');
    signal fa_clamp_en, fa_clamp_value, fa_spins : std_logic_vector(4 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    ha_dut : entity work.gen_xor_gate
        generic map (RND_WEIGHT => RND_WEIGHT)
        port map (
            clk         => clk,
            rst         => rst_ha,
            enable      => enable,
            clamp_en    => ha_clamp_en,
            clamp_value => ha_clamp_value,
            spins       => ha_spins
        );

    fa_dut : entity work.gen_fa_gate
        generic map (RND_WEIGHT => RND_WEIGHT)
        port map (
            clk         => clk,
            rst         => rst_fa,
            enable      => enable,
            clamp_en    => fa_clamp_en,
            clamp_value => fa_clamp_value,
            spins       => fa_spins
        );

    stimulus : process
        procedure wait_cycles(n : natural) is
        begin
            for i in 1 to n loop
                wait until rising_edge(clk);
            end loop;
        end procedure;

        procedure reset_ha is
        begin
            rst_ha <= '1';
            wait_cycles(4);
            rst_ha <= '0';
            wait_cycles(4);
        end procedure;

        procedure reset_fa is
        begin
            rst_fa <= '1';
            wait_cycles(4);
            rst_fa <= '0';
            wait_cycles(4);
        end procedure;

        procedure check_ha(constant aval : natural; constant bval : natural) is
            variable hits : natural := 0;
            variable s_expected : std_logic := '0';
            variable c_expected : std_logic := '0';
        begin
            ha_clamp_en <= (others => '0');
            ha_clamp_value <= (others => '0');
            ha_clamp_en(0) <= '1';
            ha_clamp_en(1) <= '1';
            if aval = 1 then
                ha_clamp_value(0) <= '1';
            end if;
            if bval = 1 then
                ha_clamp_value(1) <= '1';
            end if;
            if (aval + bval) = 1 then
                s_expected := '1';
            else
                s_expected := '0';
            end if;
            if (aval + bval) = 2 then
                c_expected := '1';
            else
                c_expected := '0';
            end if;

            reset_ha;
            wait_cycles(SETTLE_CYCLES);
            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                if ha_spins(2) = s_expected and ha_spins(3) = c_expected then
                    hits := hits + 1;
                end if;
            end loop;

            report "integer_block HA " & integer'image(aval) & "+" & integer'image(bval) &
                   " settle=" & integer'image(SETTLE_CYCLES) &
                   " rnd=" & integer'image(RND_WEIGHT) &
                   " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYCLES)
                   severity note;
        end procedure;

        procedure check_fa(constant aval : natural; constant bval : natural; constant cinval : natural) is
            variable hits : natural := 0;
            variable total : natural := aval + bval + cinval;
            variable s_expected : std_logic := '0';
            variable c_expected : std_logic := '0';
        begin
            fa_clamp_en <= (others => '0');
            fa_clamp_value <= (others => '0');
            fa_clamp_en(0) <= '1';
            fa_clamp_en(1) <= '1';
            fa_clamp_en(2) <= '1';
            if aval = 1 then
                fa_clamp_value(0) <= '1';
            end if;
            if bval = 1 then
                fa_clamp_value(1) <= '1';
            end if;
            if cinval = 1 then
                fa_clamp_value(2) <= '1';
            end if;
            if (total mod 2) = 1 then
                s_expected := '1';
            else
                s_expected := '0';
            end if;
            if total >= 2 then
                c_expected := '1';
            else
                c_expected := '0';
            end if;

            reset_fa;
            wait_cycles(SETTLE_CYCLES);
            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                if fa_spins(3) = s_expected and fa_spins(4) = c_expected then
                    hits := hits + 1;
                end if;
            end loop;

            report "integer_block FA " & integer'image(aval) & "+" & integer'image(bval) &
                   "+cin" & integer'image(cinval) &
                   " settle=" & integer'image(SETTLE_CYCLES) &
                   " rnd=" & integer'image(RND_WEIGHT) &
                   " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYCLES)
                   severity note;
        end procedure;
    begin
        check_ha(0, 0);
        check_ha(0, 1);
        check_ha(1, 0);
        check_ha(1, 1);

        check_fa(0, 0, 0);
        check_fa(0, 0, 1);
        check_fa(0, 1, 0);
        check_fa(0, 1, 1);
        check_fa(1, 0, 0);
        check_fa(1, 0, 1);
        check_fa(1, 1, 0);
        check_fa(1, 1, 1);

        report "tb_integer_block_timing completed" severity note;
        wait;
    end process;
end architecture;
