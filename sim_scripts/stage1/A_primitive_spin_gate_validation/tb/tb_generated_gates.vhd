library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_generated_gates is
end entity;

architecture sim of tb_generated_gates is
    constant CLK_PERIOD : time := 10 ns;
    constant SETTLE_CYC : natural := 200;
    constant COUNT_CYC  : natural := 2000;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal ce_and, cv_and, sp_and       : std_logic_vector(2 downto 0) := (others => '0');
    signal ce_or, cv_or, sp_or          : std_logic_vector(2 downto 0) := (others => '0');
    signal ce_nand, cv_nand, sp_nand    : std_logic_vector(2 downto 0) := (others => '0');
    signal ce_nor, cv_nor, sp_nor       : std_logic_vector(2 downto 0) := (others => '0');
    signal ce_xor, cv_xor, sp_xor       : std_logic_vector(3 downto 0) := (others => '0');
    signal ce_xnor, cv_xnor, sp_xnor    : std_logic_vector(3 downto 0) := (others => '0');
    signal ce_fa, cv_fa, sp_fa          : std_logic_vector(4 downto 0) := (others => '0');

    function f3(gate_id : natural; a : std_logic; b : std_logic) return std_logic is
    begin
        case gate_id is
            when 0 => return a and b;
            when 1 => return a or b;
            when 2 => return not (a and b);
            when others => return not (a or b);
        end case;
    end function;

    function f4(gate_id : natural; a : std_logic; b : std_logic) return std_logic is
    begin
        if gate_id = 0 then
            return a xor b;
        else
            return not (a xor b);
        end if;
    end function;
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut_and : entity work.gen_and_gate
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_and, clamp_value => cv_and, spins => sp_and);
    dut_or : entity work.gen_or_gate
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_or, clamp_value => cv_or, spins => sp_or);
    dut_nand : entity work.gen_nand_gate
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_nand, clamp_value => cv_nand, spins => sp_nand);
    dut_nor : entity work.gen_nor_gate
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_nor, clamp_value => cv_nor, spins => sp_nor);
    dut_xor : entity work.gen_xor_gate
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_xor, clamp_value => cv_xor, spins => sp_xor);
    dut_xnor : entity work.gen_xnor_gate
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_xnor, clamp_value => cv_xnor, spins => sp_xnor);
    dut_fa : entity work.gen_fa_gate
        port map (clk => clk, rst => rst, enable => enable, clamp_en => ce_fa, clamp_value => cv_fa, spins => sp_fa);

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

        procedure check3_forward(
            constant name    : string;
            constant gate_id : natural;
            signal ce        : out std_logic_vector(2 downto 0);
            signal cv        : out std_logic_vector(2 downto 0);
            signal sp        : in  std_logic_vector(2 downto 0);
            constant a_in    : std_logic;
            constant b_in    : std_logic
        ) is
            variable hits : natural := 0;
            variable y_exp : std_logic;
        begin
            y_exp := f3(gate_id, a_in, b_in);
            ce <= "011";
            cv <= (0 => a_in, 1 => b_in, others => '0');
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if sp(2) = y_exp then
                    hits := hits + 1;
                end if;
            end loop;
            assert hits > (COUNT_CYC * 3) / 4
                report name & " forward probability too low"
                severity failure;
        end procedure;

        procedure check3_reverse(
            constant name    : string;
            constant gate_id : natural;
            signal ce        : out std_logic_vector(2 downto 0);
            signal cv        : out std_logic_vector(2 downto 0);
            signal sp        : in  std_logic_vector(2 downto 0);
            constant y_in    : std_logic
        ) is
            variable hits : natural := 0;
        begin
            ce <= "100";
            cv <= (2 => y_in, others => '0');
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if f3(gate_id, sp(0), sp(1)) = y_in then
                    hits := hits + 1;
                end if;
            end loop;
            assert hits > (COUNT_CYC * 3) / 4
                report name & " reverse probability too low"
                severity failure;
        end procedure;

        procedure check4_forward(
            constant name    : string;
            constant gate_id : natural;
            signal ce        : out std_logic_vector(3 downto 0);
            signal cv        : out std_logic_vector(3 downto 0);
            signal sp        : in  std_logic_vector(3 downto 0);
            constant a_in    : std_logic;
            constant b_in    : std_logic
        ) is
            variable hits : natural := 0;
            variable y_exp : std_logic;
        begin
            y_exp := f4(gate_id, a_in, b_in);
            ce <= "0011";
            cv <= (0 => a_in, 1 => b_in, others => '0');
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if sp(2) = y_exp and sp(3) = (a_in and b_in) then
                    hits := hits + 1;
                end if;
            end loop;
            assert hits > COUNT_CYC / 2
                report name & " forward probability too low"
                severity failure;
        end procedure;

        procedure check4_reverse(
            constant name    : string;
            constant gate_id : natural;
            signal ce        : out std_logic_vector(3 downto 0);
            signal cv        : out std_logic_vector(3 downto 0);
            signal sp        : in  std_logic_vector(3 downto 0);
            constant y_in    : std_logic
        ) is
            variable hits : natural := 0;
        begin
            ce <= "0100";
            cv <= (2 => y_in, others => '0');
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if f4(gate_id, sp(0), sp(1)) = y_in then
                    hits := hits + 1;
                end if;
            end loop;
            assert hits > (COUNT_CYC * 3) / 5
                report name & " reverse probability too low"
                severity failure;
        end procedure;

        procedure check_fa_forward(
            constant a_in  : std_logic;
            constant b_in  : std_logic;
            constant ci_in : std_logic
        ) is
            variable hits : natural := 0;
            variable total : natural;
            variable s_exp : std_logic;
            variable co_exp : std_logic;
        begin
            total := 0;
            if a_in = '1' then total := total + 1; end if;
            if b_in = '1' then total := total + 1; end if;
            if ci_in = '1' then total := total + 1; end if;
            if (total mod 2) = 1 then s_exp := '1'; else s_exp := '0'; end if;
            if total >= 2 then co_exp := '1'; else co_exp := '0'; end if;

            ce_fa <= "00111";
            cv_fa <= (0 => a_in, 1 => b_in, 2 => ci_in, others => '0');
            reset_networks;
            wait_cycles(SETTLE_CYC);
            hits := 0;
            for i in 1 to COUNT_CYC loop
                wait until rising_edge(clk);
                if sp_fa(3) = s_exp and sp_fa(4) = co_exp then
                    hits := hits + 1;
                end if;
            end loop;
            assert hits > COUNT_CYC / 2
                report "FA forward probability too low"
                severity failure;
        end procedure;
    begin
        for a in 0 to 1 loop
            for b in 0 to 1 loop
                check3_forward("AND", 0, ce_and, cv_and, sp_and, std_logic'val(a + 2), std_logic'val(b + 2));
                check3_forward("OR", 1, ce_or, cv_or, sp_or, std_logic'val(a + 2), std_logic'val(b + 2));
                check3_forward("NAND", 2, ce_nand, cv_nand, sp_nand, std_logic'val(a + 2), std_logic'val(b + 2));
                check3_forward("NOR", 3, ce_nor, cv_nor, sp_nor, std_logic'val(a + 2), std_logic'val(b + 2));
                check4_forward("XOR", 0, ce_xor, cv_xor, sp_xor, std_logic'val(a + 2), std_logic'val(b + 2));
                check4_forward("XNOR", 1, ce_xnor, cv_xnor, sp_xnor, std_logic'val(a + 2), std_logic'val(b + 2));
            end loop;
        end loop;

        check3_reverse("AND", 0, ce_and, cv_and, sp_and, '0');
        check3_reverse("AND", 0, ce_and, cv_and, sp_and, '1');
        check3_reverse("OR", 1, ce_or, cv_or, sp_or, '0');
        check3_reverse("OR", 1, ce_or, cv_or, sp_or, '1');
        check3_reverse("NAND", 2, ce_nand, cv_nand, sp_nand, '0');
        check3_reverse("NAND", 2, ce_nand, cv_nand, sp_nand, '1');
        check3_reverse("NOR", 3, ce_nor, cv_nor, sp_nor, '0');
        check3_reverse("NOR", 3, ce_nor, cv_nor, sp_nor, '1');
        check4_reverse("XOR", 0, ce_xor, cv_xor, sp_xor, '0');
        check4_reverse("XOR", 0, ce_xor, cv_xor, sp_xor, '1');
        check4_reverse("XNOR", 1, ce_xnor, cv_xnor, sp_xnor, '0');
        check4_reverse("XNOR", 1, ce_xnor, cv_xnor, sp_xnor, '1');

        for a in 0 to 1 loop
            for b in 0 to 1 loop
                for ci in 0 to 1 loop
                    check_fa_forward(std_logic'val(a + 2), std_logic'val(b + 2), std_logic'val(ci + 2));
                end loop;
            end loop;
        end loop;

        report "tb_generated_gates passed" severity note;
        wait;
    end process;
end architecture;
