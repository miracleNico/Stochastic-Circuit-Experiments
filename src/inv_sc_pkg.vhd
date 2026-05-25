library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package inv_sc_pkg is
    constant SPIN_INPUTS_MAX : natural := 32;
    constant FIELD_WIDTH     : natural := 32;

    subtype field_t is signed(FIELD_WIDTH - 1 downto 0);
    subtype spin_vector_t is std_logic_vector(SPIN_INPUTS_MAX - 1 downto 0);

    function spin_to_int(spin : std_logic) return integer;
    function sat_add(value : integer; delta : integer; limit : integer) return integer;
    function to_field(value : integer) return field_t;
end package;

package body inv_sc_pkg is
    function spin_to_int(spin : std_logic) return integer is
    begin
        if spin = '1' then
            return 1;
        else
            return -1;
        end if;
    end function;

    function sat_add(value : integer; delta : integer; limit : integer) return integer is
        variable sum : integer;
    begin
        sum := value + delta;

        if sum > limit then
            return limit;
        elsif sum < -limit then
            return -limit;
        else
            return sum;
        end if;
    end function;

    function to_field(value : integer) return field_t is
    begin
        return to_signed(value, FIELD_WIDTH);
    end function;
end package body;
