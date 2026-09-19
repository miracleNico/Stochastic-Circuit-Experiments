library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_shadow1_inverse is
    generic (
        BLOCK_RND_WEIGHT : natural := 0;
        COPY_RND_WEIGHT  : natural := 0;
        BLOCK0_CYCLES    : natural := 10;
        BLOCK1_CYCLES    : natural := 8;
        BLOCK2_CYCLES    : natural := 16;
        BLOCK3_CYCLES    : natural := 6;
        COPY_CYCLES      : natural := 2;
        COUNT_CYCLES     : natural := 1000;
        REVERSE_ORDER    : boolean := false
    );
end entity;

architecture sim of tb_adder4_shadow1_inverse is
    constant CLK_PERIOD : time := 10 ns;
    type shadow_counts_t is array (1 to 3) of natural;

    signal clk    : std_logic := '0';
    signal rst    : std_logic := '1';
    signal enable : std_logic := '1';

    signal block_en0, block_en1, block_en2, block_en3 : std_logic := '0';
    signal copy_en1, copy_en2, copy_en3 : std_logic := '0';

    signal clamp_en, clamp_value, spins : std_logic_vector(18 downto 0) := (others => '0');
begin
    clk <= not clk after CLK_PERIOD / 2;

    dut : entity work.gen_adder4_shadow1_windowed
        port map (
            clk         => clk,
            rst         => rst,
            enable      => enable,
            block_en0   => block_en0,
            block_en1   => block_en1,
            block_en2   => block_en2,
            block_en3   => block_en3,
            copy_en1    => copy_en1,
            copy_en2    => copy_en2,
            copy_en3    => copy_en3,
            block_rnd   => BLOCK_RND_WEIGHT,
            copy_rnd    => COPY_RND_WEIGHT,
            clamp_en    => clamp_en,
            clamp_value => clamp_value,
            spins       => spins
        );

    stimulus : process
        variable inv_total_hits      : natural := 0;
        variable inv_min_hits        : natural := COUNT_CYCLES;
        variable inv_perfect_cases   : natural := 0;
        variable inv_failed_cases    : natural := 0;
        variable out_total_hits      : natural := 0;
        variable out_min_hits        : natural := COUNT_CYCLES;
        variable out_perfect_cases   : natural := 0;
        variable out_failed_cases    : natural := 0;
        variable shadow_min_hits     : shadow_counts_t := (others => COUNT_CYCLES);

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
            copy_en1 <= '0';
            copy_en2 <= '0';
            copy_en3 <= '0';
        end procedure;

        procedure reset_network is
        begin
            clear_enables;
            rst <= '1';
            wait_cycles(4);
            rst <= '0';
            wait_cycles(4);
        end procedure;

        procedure copy_shadow(signal copy_en : out std_logic) is
        begin
            copy_en <= '1';
            wait_cycles(COPY_CYCLES);
            copy_en <= '0';
        end procedure;

        procedure run_shadow_schedule is
        begin
            if not REVERSE_ORDER then
                block_en0 <= '1';
                wait_cycles(BLOCK0_CYCLES);
                block_en0 <= '0';
                copy_shadow(copy_en1);

                block_en1 <= '1';
                wait_cycles(BLOCK1_CYCLES);
                block_en1 <= '0';
                copy_shadow(copy_en2);

                block_en2 <= '1';
                wait_cycles(BLOCK2_CYCLES);
                block_en2 <= '0';
                copy_shadow(copy_en3);

                block_en3 <= '1';
                wait_cycles(BLOCK3_CYCLES);
                block_en3 <= '0';
            else
                block_en3 <= '1';
                wait_cycles(BLOCK3_CYCLES);
                block_en3 <= '0';
                copy_shadow(copy_en3);

                block_en2 <= '1';
                wait_cycles(BLOCK2_CYCLES);
                block_en2 <= '0';
                copy_shadow(copy_en2);

                block_en1 <= '1';
                wait_cycles(BLOCK1_CYCLES);
                block_en1 <= '0';
                copy_shadow(copy_en1);

                block_en0 <= '1';
                wait_cycles(BLOCK0_CYCLES);
                block_en0 <= '0';
            end if;
        end procedure;

        function nibble_value(sp : std_logic_vector(18 downto 0); constant base : natural) return natural is
            variable value : natural := 0;
        begin
            for bit in 0 to 3 loop
                if sp(base + bit) = '1' then
                    value := value + (2 ** bit);
                end if;
            end loop;
            return value;
        end function;

        function a_value(sp : std_logic_vector(18 downto 0)) return natural is
        begin
            return nibble_value(sp, 0);
        end function;

        function b_value(sp : std_logic_vector(18 downto 0)) return natural is
        begin
            return nibble_value(sp, 4);
        end function;

        function sum_value(sp : std_logic_vector(18 downto 0)) return natural is
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

        procedure clamp_b_and_sum(constant bval : natural; constant target_sum : natural) is
        begin
            clamp_en <= (others => '0');
            clamp_value <= (others => '0');
            for bit in 0 to 3 loop
                clamp_en(4 + bit) <= '1';
                if ((bval / (2 ** bit)) mod 2) = 1 then
                    clamp_value(4 + bit) <= '1';
                end if;

                clamp_en(8 + bit) <= '1';
                if ((target_sum / (2 ** bit)) mod 2) = 1 then
                    clamp_value(8 + bit) <= '1';
                end if;
            end loop;

            clamp_en(15) <= '1';
            if ((target_sum / 16) mod 2) = 1 then
                clamp_value(15) <= '1';
            end if;
        end procedure;

        procedure clamp_sum_only(constant target_sum : natural) is
        begin
            clamp_en <= (others => '0');
            clamp_value <= (others => '0');
            for bit in 0 to 3 loop
                clamp_en(8 + bit) <= '1';
                if ((target_sum / (2 ** bit)) mod 2) = 1 then
                    clamp_value(8 + bit) <= '1';
                end if;
            end loop;

            clamp_en(15) <= '1';
            if ((target_sum / 16) mod 2) = 1 then
                clamp_value(15) <= '1';
            end if;
        end procedure;

        procedure update_shadow_min(variable shadow_hits : in shadow_counts_t) is
        begin
            for bit in 1 to 3 loop
                if shadow_hits(bit) < shadow_min_hits(bit) then
                    shadow_min_hits(bit) := shadow_hits(bit);
                end if;
            end loop;
        end procedure;

        procedure check_inverse_b_sum(constant expected_a : natural; constant bval : natural) is
            variable hits        : natural := 0;
            variable sample_a    : natural;
            variable target_sum  : natural := expected_a + bval;
            variable shadow_hits : shadow_counts_t := (others => 0);
        begin
            clamp_b_and_sum(bval, target_sum);
            reset_network;
            run_shadow_schedule;

            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                sample_a := a_value(spins);
                if sample_a = expected_a then
                    hits := hits + 1;
                end if;
                if spins(16) = spins(12) then shadow_hits(1) := shadow_hits(1) + 1; end if;
                if spins(17) = spins(13) then shadow_hits(2) := shadow_hits(2) + 1; end if;
                if spins(18) = spins(14) then shadow_hits(3) := shadow_hits(3) + 1; end if;
            end loop;

            inv_total_hits := inv_total_hits + hits;
            if hits < inv_min_hits then
                inv_min_hits := hits;
            end if;
            if hits = COUNT_CYCLES then
                inv_perfect_cases := inv_perfect_cases + 1;
            else
                if inv_failed_cases < 8 then
                    report "shadow1 inverse B+SUM fail A=" & integer'image(expected_a) &
                           " B=" & integer'image(bval) &
                           " SUM=" & integer'image(target_sum) &
                           " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYCLES) &
                           " last_A=" & integer'image(sample_a) &
                           " last_sum=" & integer'image(sum_value(spins))
                           severity note;
                end if;
                inv_failed_cases := inv_failed_cases + 1;
            end if;
            update_shadow_min(shadow_hits);
        end procedure;

        procedure check_inverse_sum_only(constant target_sum : natural) is
            variable hits        : natural := 0;
            variable sample_a    : natural;
            variable sample_b    : natural;
            variable sample_sum  : natural;
            variable shadow_hits : shadow_counts_t := (others => 0);
        begin
            clamp_sum_only(target_sum);
            reset_network;
            run_shadow_schedule;

            for i in 1 to COUNT_CYCLES loop
                wait until rising_edge(clk);
                sample_a := a_value(spins);
                sample_b := b_value(spins);
                sample_sum := sample_a + sample_b;
                if sample_sum = target_sum then
                    hits := hits + 1;
                end if;
                if spins(16) = spins(12) then shadow_hits(1) := shadow_hits(1) + 1; end if;
                if spins(17) = spins(13) then shadow_hits(2) := shadow_hits(2) + 1; end if;
                if spins(18) = spins(14) then shadow_hits(3) := shadow_hits(3) + 1; end if;
            end loop;

            out_total_hits := out_total_hits + hits;
            if hits < out_min_hits then
                out_min_hits := hits;
            end if;
            if hits = COUNT_CYCLES then
                out_perfect_cases := out_perfect_cases + 1;
            else
                if out_failed_cases < 8 then
                    report "shadow1 inverse SUM-only fail SUM=" & integer'image(target_sum) &
                           " hits=" & integer'image(hits) & "/" & integer'image(COUNT_CYCLES) &
                           " last_A=" & integer'image(sample_a) &
                           " last_B=" & integer'image(sample_b) &
                           " last_AplusB=" & integer'image(sample_sum)
                           severity note;
                end if;
                out_failed_cases := out_failed_cases + 1;
            end if;
            update_shadow_min(shadow_hits);
        end procedure;
    begin
        for aval in 0 to 15 loop
            for bval in 0 to 15 loop
                check_inverse_b_sum(aval, bval);
            end loop;
        end loop;

        report "shadow1 inverse B+SUM completed cases=256 perfect=" & integer'image(inv_perfect_cases) &
               " failed=" & integer'image(inv_failed_cases) &
               " total_hits=" & integer'image(inv_total_hits) & "/" & integer'image(256 * COUNT_CYCLES) &
               " min_hits=" & integer'image(inv_min_hits) &
               " reverse=" & boolean'image(REVERSE_ORDER) &
               " block_rnd=" & integer'image(BLOCK_RND_WEIGHT) &
               " copy_rnd=" & integer'image(COPY_RND_WEIGHT) &
               " blocks=" & integer'image(BLOCK0_CYCLES) & "," &
                            integer'image(BLOCK1_CYCLES) & "," &
                            integer'image(BLOCK2_CYCLES) & "," &
                            integer'image(BLOCK3_CYCLES) &
               " copy=" & integer'image(COPY_CYCLES)
               severity note;

        for target_sum in 0 to 30 loop
            check_inverse_sum_only(target_sum);
        end loop;

        report "shadow1 inverse SUM-only completed cases=31 perfect=" & integer'image(out_perfect_cases) &
               " failed=" & integer'image(out_failed_cases) &
               " total_hits=" & integer'image(out_total_hits) & "/" & integer'image(31 * COUNT_CYCLES) &
               " min_hits=" & integer'image(out_min_hits) &
               " reverse=" & boolean'image(REVERSE_ORDER) &
               " block_rnd=" & integer'image(BLOCK_RND_WEIGHT) &
               " copy_rnd=" & integer'image(COPY_RND_WEIGHT) &
               " blocks=" & integer'image(BLOCK0_CYCLES) & "," &
                            integer'image(BLOCK1_CYCLES) & "," &
                            integer'image(BLOCK2_CYCLES) & "," &
                            integer'image(BLOCK3_CYCLES) &
               " copy=" & integer'image(COPY_CYCLES)
               severity note;

        report "shadow1 inverse shadow_min q1=" & integer'image(shadow_min_hits(1)) &
               " q2=" & integer'image(shadow_min_hits(2)) &
               " q3=" & integer'image(shadow_min_hits(3)) &
               "/" & integer'image(COUNT_CYCLES)
               severity note;
        wait;
    end process;
end architecture;
