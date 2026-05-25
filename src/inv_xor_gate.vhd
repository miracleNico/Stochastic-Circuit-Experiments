library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity inv_xor_gate is
    generic (
        RND_WEIGHT   : natural := 0;
        COUNTER_BITS : natural := 5
    );
    port (
        clk             : in  std_logic;
        rst             : in  std_logic;
        enable          : in  std_logic;
        clamp_a_en      : in  std_logic;
        clamp_a_value   : in  std_logic;
        clamp_b_en      : in  std_logic;
        clamp_b_value   : in  std_logic;
        clamp_y_en      : in  std_logic;
        clamp_y_value   : in  std_logic;
        clamp_aux_en    : in  std_logic;
        clamp_aux_value : in  std_logic;
        a               : out std_logic;
        b               : out std_logic;
        y               : out std_logic;
        aux_c           : out std_logic;
        field_a         : out field_t;
        field_b         : out field_t;
        field_y         : out field_t;
        field_aux       : out field_t
    );
end entity;

architecture rtl of inv_xor_gate is
    signal a_s : std_logic := '0';
    signal b_s : std_logic := '0';
    signal y_s : std_logic := '0';
    signal c_s : std_logic := '0';

    signal n_a : spin_vector_t := (others => '0');
    signal n_b : spin_vector_t := (others => '0');
    signal n_y : spin_vector_t := (others => '0');
    signal n_c : spin_vector_t := (others => '0');

    signal phase       : natural range 0 to 3 := 0;
    signal sched_state : std_logic_vector(31 downto 0) := x"3C3CC3C3";
    signal en_a       : std_logic;
    signal en_b       : std_logic;
    signal en_y       : std_logic;
    signal en_c       : std_logic;

    signal unused_counter_a : signed(COUNTER_BITS downto 0);
    signal unused_counter_b : signed(COUNTER_BITS downto 0);
    signal unused_counter_y : signed(COUNTER_BITS downto 0);
    signal unused_counter_c : signed(COUNTER_BITS downto 0);
begin
    -- XOR is implemented as the sum output of an invertible half-adder.
    -- Order is A, B, Y(sum), aux_c(carry):
    -- h = [1, 1, -1, -2]
    -- J_AB=-1, J_AY=1, J_AC=2, J_BY=1, J_BC=2, J_YC=-2.
    n_a <= (0 => b_s, 1 => y_s, 2 => c_s, others => '0');
    n_b <= (0 => a_s, 1 => y_s, 2 => c_s, others => '0');
    n_y <= (0 => a_s, 1 => b_s, 2 => c_s, others => '0');
    n_c <= (0 => a_s, 1 => b_s, 2 => y_s, others => '0');

    process (clk)
        variable x : unsigned(31 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '1' then
                phase       <= 0;
                sched_state <= x"3C3CC3C3";
            elsif enable = '1' then
                x := unsigned(sched_state);
                x := x xor shift_left(x, 13);
                x := x xor shift_right(x, 17);
                x := x xor shift_left(x, 5);
                sched_state <= std_logic_vector(x);

                case sched_state(31 downto 30) is
                    when "00" =>
                        phase <= 0;
                    when "01" =>
                        phase <= 1;
                    when "10" =>
                        phase <= 2;
                    when others =>
                        phase <= 3;
                end case;
            end if;
        end if;
    end process;

    en_a <= enable when (clamp_a_en = '1' or phase = 0) else '0';
    en_b <= enable when (clamp_b_en = '1' or phase = 1) else '0';
    en_y <= enable when (clamp_y_en = '1' or phase = 2) else '0';
    en_c <= enable when (clamp_aux_en = '1' or phase = 3) else '0';

    node_a : entity work.spin_node
        generic map (
            NUM_INPUTS   => 3,
            BIAS         => 1,
            W0           => -1,
            W1           => 1,
            W2           => 2,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"10203041"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => en_a,
            clamp_en    => clamp_a_en,
            clamp_value => clamp_a_value,
            neighbors   => n_a,
            spin_o      => a_s,
            field_o     => field_a,
            counter_o   => unused_counter_a
        );

    node_b : entity work.spin_node
        generic map (
            NUM_INPUTS   => 3,
            BIAS         => 1,
            W0           => -1,
            W1           => 1,
            W2           => 2,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"55667788"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => en_b,
            clamp_en    => clamp_b_en,
            clamp_value => clamp_b_value,
            neighbors   => n_b,
            spin_o      => b_s,
            field_o     => field_b,
            counter_o   => unused_counter_b
        );

    node_y : entity work.spin_node
        generic map (
            NUM_INPUTS   => 3,
            BIAS         => -1,
            W0           => 1,
            W1           => 1,
            W2           => -2,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"89ABCDEF"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => en_y,
            clamp_en    => clamp_y_en,
            clamp_value => clamp_y_value,
            neighbors   => n_y,
            spin_o      => y_s,
            field_o     => field_y,
            counter_o   => unused_counter_y
        );

    node_c : entity work.spin_node
        generic map (
            NUM_INPUTS   => 3,
            BIAS         => -2,
            W0           => 2,
            W1           => 2,
            W2           => -2,
            RND_WEIGHT   => RND_WEIGHT,
            COUNTER_BITS => COUNTER_BITS,
            SEED         => x"C001D00D"
        )
        port map (
            clk         => clk,
            rst         => rst,
            enable      => en_c,
            clamp_en    => clamp_aux_en,
            clamp_value => clamp_aux_value,
            neighbors   => n_c,
            spin_o      => c_s,
            field_o     => field_aux,
            counter_o   => unused_counter_c
        );

    a     <= a_s;
    b     <= b_s;
    y     <= y_s;
    aux_c <= c_s;
end architecture;
