library ieee;
use ieee.std_logic_1164.all;

entity deliberate_compile_error is
end entity;

architecture invalid_syntax of deliberate_compile_error is
begin
    this is deliberately not valid VHDL;
end architecture;
