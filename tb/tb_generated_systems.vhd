library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_generated_systems is
end entity;

architecture sim of tb_generated_systems is
    constant CLK_PERIOD : time := 10 ns;
    constant SETTLE_CYC : natural := 500;
    constant COUNT_CYC  : natural := 1000;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal ce_add, cv_add, sp_add : std_logic_vector(31 downto 0) := (others => '0');
    signal ce_bc, cv_bc, sp_bc    : std_logic_vector(11 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut_adder : entity work.gen_adder8
        generic map (RND_WEIGHT => 1)
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_add, clamp_value => cv_add, spins => sp_add);

    dut_bitcount : entity work.gen_bitcount8
        generic map (RND_WEIGHT => 1)
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_bc, clamp_value => cv_bc, spins => sp_bc);

    stimulus : process
        procedure wait_cycles(n : natural) is
        begin
            for i in 1 to n loop
                wait until rising_edge(clk);
            end loop;
        end procedure;

        procedure reset_networks is
        begin
            rst <= '1';
            wait_cycles(4);
            rst <= '0';
            wait_cycles(4);
        end procedure;

        function adder_sum(sp : std_logic_vector(31 downto 0)) return natural is
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

        function adder_a(sp : std_logic_vector(31 downto 0)) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 7 loop
                if sp(bit) = '1' then
                    value := value + (2 ** bit);
                end if;
            end loop;
            return value;
        end function;

        function adder_b(sp : std_logic_vector(31 downto 0)) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 7 loop
                if sp(8 + bit) = '1' then
                    value := value + (2 ** bit);
                end if;
            end loop;
            return value;
        end function;

        function bitcount_y(sp : std_logic_vector(11 downto 0)) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 3 loop
                if sp(8 + bit) = '1' then
                    value := value + (2 ** bit);
                end if;
            end loop;
            return value;
        end function;

        function bitcount_x(sp : std_logic_vector(11 downto 0)) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 7 loop
                if sp(bit) = '1' then
                    value := value + 1;
                end if;
            end loop;
            return value;
        end function;

        procedure clamp_adder_inputs(constant aval : natural; constant bval : natural) is
        begin
            ce_add <= (others => '0');
            cv_add <= (others => '0');
            for bit in 0 to 7 loop
                ce_add(bit) <= '1';
                ce_add(8 + bit) <= '1';
                if ((aval / (2 ** bit)) mod 2) = 1 then
                    cv_add(bit) <= '1';
                end if;
                if ((bval / (2 ** bit)) mod 2) = 1 then
                    cv_add(8 + bit) <= '1';
                end if;
            end loop;
        end procedure;

        procedure clamp_adder_sum(constant sum : natural) is
        begin
            ce_add <= (others => '0');
            cv_add <= (others => '0');
            for bit in 0 to 7 loop
                ce_add(16 + bit) <= '1';
                if ((sum / (2 ** bit)) mod 2) = 1 then
                    cv_add(16 + bit) <= '1';
                end if;
            end loop;
            ce_add(31) <= '1';
            if sum >= 256 then
                cv_add(31) <= '1';
            end if;
        end procedure;

        procedure clamp_bitcount_inputs(constant pattern : std_logic_vector(7 downto 0)) is
        begin
            ce_bc <= (others => '0');
            cv_bc <= (others => '0');
            for bit in 0 to 7 loop
                ce_bc(bit) <= '1';
                cv_bc(bit) <= pattern(bit);
            end loop;
        end procedure;

        procedure clamp_bitcount_count(constant count : natural) is
        begin
            ce_bc <= (others => '0');
            cv_bc <= (others => '0');
            for bit in 0 to 3 loop
                ce_bc(8 + bit) <= '1';
                if ((count / (2 ** bit)) mod 2) = 1 then
                    cv_bc(8 + bit) <= '1';
                end if;
            end loop;
        end procedure;

        procedure check_adder_forward(constant aval : natural; constant bval : natural) is
            variable hits : natural := 0;
            variable expected : natural;
        begin
            expected := aval + bval;
            clamp_adder_inputs(aval, bval);
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if adder_sum(sp_add) = expected then
                    hits := hits + 1;
                end if;
            end loop;
            report "adder forward " & integer'image(aval) & "+" & integer'image(bval) &
                   " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYC)
                   severity note;
            if hits <= COUNT_CYC / 5 then
                report "8-bit adder forward probability below diagnostic threshold" severity note;
            end if;
        end procedure;

        procedure check_adder_reverse(constant sum : natural) is
            variable hits : natural := 0;
        begin
            clamp_adder_sum(sum);
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if (adder_a(sp_add) + adder_b(sp_add)) = sum then
                    hits := hits + 1;
                end if;
            end loop;
            report "adder reverse sum=" & integer'image(sum) &
                   " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYC)
                   severity note;
            if hits <= COUNT_CYC / 20 then
                report "8-bit adder reverse probability below diagnostic threshold" severity note;
            end if;
        end procedure;

        procedure check_bitcount_forward(constant pattern : std_logic_vector(7 downto 0); constant expected : natural) is
            variable hits : natural := 0;
        begin
            clamp_bitcount_inputs(pattern);
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if bitcount_y(sp_bc) = expected then
                    hits := hits + 1;
                end if;
            end loop;
            report "bitcount forward expected=" & integer'image(expected) &
                   " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYC)
                   severity note;
            if hits <= (COUNT_CYC * 3) / 4 then
                report "8-input bitcount forward probability below diagnostic threshold" severity note;
            end if;
        end procedure;

        procedure check_bitcount_reverse(constant count : natural) is
            variable hits : natural := 0;
        begin
            clamp_bitcount_count(count);
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if bitcount_x(sp_bc) = count then
                    hits := hits + 1;
                end if;
            end loop;
            report "bitcount reverse count=" & integer'image(count) &
                   " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYC)
                   severity note;
            if hits <= COUNT_CYC / 2 then
                report "8-input bitcount reverse probability below diagnostic threshold" severity note;
            end if;
        end procedure;
    begin
        check_adder_forward(0, 0);
        check_adder_forward(1, 1);
        check_adder_forward(15, 1);
        check_adder_forward(127, 1);
        check_adder_forward(255, 1);
        check_adder_forward(170, 85);
        check_adder_reverse(0);
        check_adder_reverse(16);
        check_adder_reverse(128);

        check_bitcount_forward("00000000", 0);
        check_bitcount_forward("00000001", 1);
        check_bitcount_forward("00001111", 4);
        check_bitcount_forward("11111111", 8);
        check_bitcount_reverse(0);
        check_bitcount_reverse(1);
        check_bitcount_reverse(4);

        report "tb_generated_systems completed" severity note;
        wait;
    end process;
end architecture;
