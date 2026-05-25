library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_anneal_diagnostics is
    generic (
        HOT_RND_WEIGHT  : natural := 2;
        COLD_RND_WEIGHT : natural := 1;
        WAVE_CYCLES     : natural := 1000;
        FINAL_CYCLES    : natural := 1000;
        COUNT_CYCLES    : natural := 1000;
        REVERSE_COOL    : boolean := false
    );
end entity;

architecture sim of tb_adder4_anneal_diagnostics is
    constant CLK_PERIOD : time := 10 ns;

    type histogram_t is array (0 to 31) of natural;
    type bit_counts_t is array (0 to 7) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal stage_rnd0 : natural := 0;
    signal stage_rnd1 : natural := 0;
    signal stage_rnd2 : natural := 0;
    signal stage_rnd3 : natural := 0;

    signal clamp_en, clamp_value, spins : std_logic_vector(15 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder4_anneal
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
            stage_rnd0  => stage_rnd0,
            stage_rnd1  => stage_rnd1,
            stage_rnd2  => stage_rnd2,
            stage_rnd3  => stage_rnd3,
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

        procedure run_fixed_wave_anneal is
        begin
            stage_rnd0 <= HOT_RND_WEIGHT;
            stage_rnd1 <= HOT_RND_WEIGHT;
            stage_rnd2 <= HOT_RND_WEIGHT;
            stage_rnd3 <= HOT_RND_WEIGHT;
            wait_cycles(WAVE_CYCLES);

            if REVERSE_COOL then
                stage_rnd3 <= COLD_RND_WEIGHT;
                wait_cycles(WAVE_CYCLES);

                stage_rnd2 <= COLD_RND_WEIGHT;
                wait_cycles(WAVE_CYCLES);

                stage_rnd1 <= COLD_RND_WEIGHT;
                wait_cycles(WAVE_CYCLES);

                stage_rnd0 <= COLD_RND_WEIGHT;
            else
                stage_rnd0 <= COLD_RND_WEIGHT;
                wait_cycles(WAVE_CYCLES);

                stage_rnd1 <= COLD_RND_WEIGHT;
                wait_cycles(WAVE_CYCLES);

                stage_rnd2 <= COLD_RND_WEIGHT;
                wait_cycles(WAVE_CYCLES);

                stage_rnd3 <= COLD_RND_WEIGHT;
            end if;
            wait_cycles(FINAL_CYCLES);
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

        procedure expected_bits(
            constant aval   : natural;
            constant bval   : natural;
            variable expect : out std_logic_vector(7 downto 0)
        ) is
            variable carry : natural := 0;
            variable total : natural;
            variable abit  : natural;
            variable bbit  : natural;
        begin
            expect := (others => '0');
            for bit in 0 to 3 loop
                abit := (aval / (2 ** bit)) mod 2;
                bbit := (bval / (2 ** bit)) mod 2;
                total := abit + bbit + carry;
                if (total mod 2) = 1 then
                    expect(bit) := '1';
                end if;
                carry := total / 2;
                if carry = 1 then
                    expect(4 + bit) := '1';
                end if;
            end loop;
        end procedure;

        procedure report_histogram(variable hist : inout histogram_t) is
            variable best_sum   : natural := 0;
            variable best_count : natural := 0;
        begin
            for rank in 1 to 8 loop
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
            variable bit_hits   : bit_counts_t := (others => 0);
            variable expect     : std_logic_vector(7 downto 0);
            variable sample_sum : natural;
            variable expected   : natural := aval + bval;
        begin
            expected_bits(aval, bval, expect);
            clamp_inputs(aval, bval);
            reset_network;
            run_fixed_wave_anneal;

            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                sample_sum := sum_value(spins);
                hist(sample_sum) := hist(sample_sum) + 1;

                for bit in 0 to 3 loop
                    if spins(8 + bit) = expect(bit) then
                        bit_hits(bit) := bit_hits(bit) + 1;
                    end if;
                    if spins(12 + bit) = expect(4 + bit) then
                        bit_hits(4 + bit) := bit_hits(4 + bit) + 1;
                    end if;
                end loop;
            end loop;

            report "anneal4 forward " & integer'image(aval) & "+" & integer'image(bval) &
                   " expected_sum=" & integer'image(expected) &
                   " hits=" & integer'image(hist(expected)) & "/" & integer'image(COUNT_CYCLES) &
                   " hot=" & integer'image(HOT_RND_WEIGHT) &
                   " cold=" & integer'image(COLD_RND_WEIGHT) &
                   " wave=" & integer'image(WAVE_CYCLES) &
                   " final=" & integer'image(FINAL_CYCLES) &
                   " reverse=" & boolean'image(REVERSE_COOL)
                   severity note;
            report_histogram(hist);
            for bit in 0 to 3 loop
                report "  s" & integer'image(bit) & "_hits=" & integer'image(bit_hits(bit)) &
                       " c" & integer'image(bit + 1) & "_hits=" & integer'image(bit_hits(4 + bit))
                       severity note;
            end loop;
        end procedure;
    begin
        check_forward(0, 0);
        check_forward(1, 1);
        check_forward(3, 1);
        check_forward(7, 1);
        check_forward(10, 5);
        check_forward(15, 1);
        report "tb_adder4_anneal_diagnostics completed" severity note;
        wait;
    end process;
end architecture;
