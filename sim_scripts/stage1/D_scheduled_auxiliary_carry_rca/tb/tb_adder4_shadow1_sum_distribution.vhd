library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_adder4_shadow1_sum_distribution is
    generic (
        BLOCK_RND_WEIGHT : natural := 0;
        COPY_RND_WEIGHT  : natural := 0;
        BLOCK0_CYCLES    : natural := 10;
        BLOCK1_CYCLES    : natural := 8;
        BLOCK2_CYCLES    : natural := 16;
        BLOCK3_CYCLES    : natural := 6;
        COPY_CYCLES      : natural := 2;
        TRIALS           : natural := 1000;
        REVERSE_ORDER    : boolean := false
    );
end entity;

architecture sim of tb_adder4_shadow1_sum_distribution is
    constant CLK_PERIOD : time := 10 ns;
    type pair_hist_t is array (0 to 255) of natural;

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

        procedure check_sum_distribution(constant target_sum : natural) is
            variable hist        : pair_hist_t := (others => 0);
            variable aval        : natural;
            variable bval        : natural;
            variable pair_index  : natural;
            variable valid_total : natural := 0;
            variable invalid     : natural := 0;
        begin
            clamp_sum_only(target_sum);
            reset_network;

            for trial in 1 to TRIALS loop
                run_shadow_schedule;
                wait until rising_edge(clk);
                aval := a_value(spins);
                bval := b_value(spins);
                pair_index := (aval * 16) + bval;
                hist(pair_index) := hist(pair_index) + 1;
            end loop;

            for aval_i in 0 to 15 loop
                for bval_i in 0 to 15 loop
                    pair_index := (aval_i * 16) + bval_i;
                    if aval_i + bval_i = target_sum then
                        valid_total := valid_total + hist(pair_index);
                    else
                        invalid := invalid + hist(pair_index);
                    end if;
                end loop;
            end loop;

            report "sumdist summary SUM=" & integer'image(target_sum) &
                   " valid_total=" & integer'image(valid_total) &
                   " invalid_total=" & integer'image(invalid) &
                   " trials=" & integer'image(TRIALS) &
                   " reverse=" & boolean'image(REVERSE_ORDER) &
                   " block_rnd=" & integer'image(BLOCK_RND_WEIGHT) &
                   " copy_rnd=" & integer'image(COPY_RND_WEIGHT) &
                   " blocks=" & integer'image(BLOCK0_CYCLES) & "," &
                                integer'image(BLOCK1_CYCLES) & "," &
                                integer'image(BLOCK2_CYCLES) & "," &
                                integer'image(BLOCK3_CYCLES) &
                   " copy=" & integer'image(COPY_CYCLES)
                   severity note;

            for aval_i in 0 to 15 loop
                for bval_i in 0 to 15 loop
                    if aval_i + bval_i = target_sum then
                        pair_index := (aval_i * 16) + bval_i;
                        report "sumdist valid SUM=" & integer'image(target_sum) &
                               " A=" & integer'image(aval_i) &
                               " B=" & integer'image(bval_i) &
                               " count=" & integer'image(hist(pair_index)) &
                               " trials=" & integer'image(TRIALS)
                               severity note;
                    end if;
                end loop;
            end loop;
        end procedure;
    begin
        for target_sum in 0 to 30 loop
            check_sum_distribution(target_sum);
        end loop;

        report "tb_adder4_shadow1_sum_distribution completed" severity note;
        wait;
    end process;
end architecture;
