library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity lfsr32 is
    generic (
        SEED : std_logic_vector(31 downto 0) := x"00000001"
    );
    port (
        clk     : in  std_logic;
        rst     : in  std_logic;
        enable  : in  std_logic;
        rnd_bit : out std_logic;
        state_o : out std_logic_vector(31 downto 0)
    );
end entity;

architecture rtl of lfsr32 is
    function nonzero_seed(seed : std_logic_vector(31 downto 0)) return std_logic_vector is
    begin
        if seed = x"00000000" then
            return x"00000001";
        else
            return seed;
        end if;
    end function;

    signal state_q : std_logic_vector(31 downto 0) := nonzero_seed(SEED);
begin
    process (clk)
        variable x : unsigned(31 downto 0);
    begin
        if rising_edge(clk) then
            if rst = '1' then
                state_q <= nonzero_seed(SEED);
            elsif enable = '1' then
                x := unsigned(state_q);
                x := x xor shift_left(x, 13);
                x := x xor shift_right(x, 17);
                x := x xor shift_left(x, 5);
                state_q <= std_logic_vector(x);
            end if;
        end if;
    end process;

    rnd_bit <= state_q(31);
    state_o <= state_q;
end architecture;
