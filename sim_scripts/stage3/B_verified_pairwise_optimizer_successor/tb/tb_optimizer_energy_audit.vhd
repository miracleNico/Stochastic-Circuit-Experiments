library ieee;
use ieee.std_logic_1164.all;

use work.optimizer_coefficients_pkg.all;

entity tb_optimizer_energy_audit is
end entity tb_optimizer_energy_audit;

architecture sim of tb_optimizer_energy_audit is
    function state_bit(
        constant state_code : natural;
        constant node_count : positive;
        constant node_index : natural
    ) return integer is
        variable weight : positive;
    begin
        weight := 2 ** (node_count - 1 - node_index);
        return (state_code / weight) mod 2;
    end function;

    function spin_value(
        constant state_code : natural;
        constant node_count : positive;
        constant node_index : natural
    ) return integer is
    begin
        return 2 * state_bit(state_code, node_count, node_index) - 1;
    end function;

    function state_energy_scaled(
        constant state_code : natural;
        constant node_count : positive;
        constant coefficients : coefficient_vector_t
    ) return integer is
        variable result_value : integer := 0;
        variable coefficient_index : natural := node_count;
    begin
        assert coefficients'length = node_count + node_count * (node_count - 1) / 2
            report "coefficient vector length does not match node count"
            severity failure;
        for left in 0 to node_count - 1 loop
            result_value := result_value
                - coefficients(coefficients'low + left)
                * spin_value(state_code, node_count, left);
        end loop;
        for left in 0 to node_count - 2 loop
            for right in left + 1 to node_count - 1 loop
                result_value := result_value
                    - coefficients(coefficients'low + coefficient_index)
                    * spin_value(state_code, node_count, left)
                    * spin_value(state_code, node_count, right);
                coefficient_index := coefficient_index + 1;
            end loop;
        end loop;
        return result_value;
    end function;

    function is_local_minimum(
        constant state_code : natural;
        constant node_count : positive;
        constant coefficients : coefficient_vector_t
    ) return boolean is
        variable current_energy : integer;
        variable neighbor_code : natural;
        variable bit_weight : positive;
    begin
        current_energy := state_energy_scaled(state_code, node_count, coefficients);
        for node_index in 0 to node_count - 1 loop
            bit_weight := 2 ** (node_count - 1 - node_index);
            if state_bit(state_code, node_count, node_index) = 0 then
                neighbor_code := state_code + bit_weight;
            else
                neighbor_code := state_code - bit_weight;
            end if;
            if current_energy
                > state_energy_scaled(neighbor_code, node_count, coefficients)
            then
                return false;
            end if;
        end loop;
        return true;
    end function;

    function is_valid_ha(constant state_code : natural) return boolean is
        variable a_value : integer;
        variable b_value : integer;
        variable total : integer;
    begin
        a_value := state_bit(state_code, HA_NODE_COUNT, 0);
        b_value := state_bit(state_code, HA_NODE_COUNT, 1);
        total := a_value + b_value;
        return state_bit(state_code, HA_NODE_COUNT, 2) = total mod 2
            and state_bit(state_code, HA_NODE_COUNT, 3) = total / 2;
    end function;

    function is_valid_fa(constant state_code : natural) return boolean is
        variable total : integer;
    begin
        total := state_bit(state_code, FA_NODE_COUNT, 0)
            + state_bit(state_code, FA_NODE_COUNT, 1)
            + state_bit(state_code, FA_NODE_COUNT, 2);
        return state_bit(state_code, FA_NODE_COUNT, 3) = total mod 2
            and state_bit(state_code, FA_NODE_COUNT, 4) = total / 2;
    end function;

    procedure audit_ha(
        constant coefficients : in coefficient_vector_t;
        constant expected_valid_energy : in integer;
        constant expected_gap : in integer
    ) is
        variable valid_minimum : integer := integer'high;
        variable valid_maximum : integer := integer'low;
        variable invalid_minimum : integer := integer'high;
        variable invalid_local_minima : natural := 0;
        variable energy_value : integer;
    begin
        for state_code in 0 to 2 ** HA_NODE_COUNT - 1 loop
            energy_value := state_energy_scaled(
                state_code,
                HA_NODE_COUNT,
                coefficients
            );
            if is_valid_ha(state_code) then
                if energy_value < valid_minimum then
                    valid_minimum := energy_value;
                end if;
                if energy_value > valid_maximum then
                    valid_maximum := energy_value;
                end if;
            else
                if energy_value < invalid_minimum then
                    invalid_minimum := energy_value;
                end if;
                if is_local_minimum(state_code, HA_NODE_COUNT, coefficients) then
                    invalid_local_minima := invalid_local_minima + 1;
                end if;
            end if;
        end loop;
        assert valid_minimum = expected_valid_energy * COEFFICIENT_SCALE
            and valid_maximum = expected_valid_energy * COEFFICIENT_SCALE
            report "HA valid energy mismatch"
            severity failure;
        assert invalid_minimum - valid_maximum = expected_gap * COEFFICIENT_SCALE
            report "HA gap mismatch"
            severity failure;
        assert invalid_local_minima = 0
            report "HA has an invalid local minimum"
            severity failure;
    end procedure;

    procedure audit_fa(
        constant coefficients : in coefficient_vector_t;
        constant expected_valid_energy : in integer;
        constant expected_gap : in integer
    ) is
        variable valid_minimum : integer := integer'high;
        variable valid_maximum : integer := integer'low;
        variable invalid_minimum : integer := integer'high;
        variable invalid_local_minima : natural := 0;
        variable energy_value : integer;
    begin
        for state_code in 0 to 2 ** FA_NODE_COUNT - 1 loop
            energy_value := state_energy_scaled(
                state_code,
                FA_NODE_COUNT,
                coefficients
            );
            if is_valid_fa(state_code) then
                if energy_value < valid_minimum then
                    valid_minimum := energy_value;
                end if;
                if energy_value > valid_maximum then
                    valid_maximum := energy_value;
                end if;
            else
                if energy_value < invalid_minimum then
                    invalid_minimum := energy_value;
                end if;
                if is_local_minimum(state_code, FA_NODE_COUNT, coefficients) then
                    invalid_local_minima := invalid_local_minima + 1;
                end if;
            end if;
        end loop;
        assert valid_minimum = expected_valid_energy * COEFFICIENT_SCALE
            and valid_maximum = expected_valid_energy * COEFFICIENT_SCALE
            report "FA valid energy mismatch"
            severity failure;
        assert invalid_minimum - valid_maximum = expected_gap * COEFFICIENT_SCALE
            report "FA gap mismatch"
            severity failure;
        assert invalid_local_minima = 0
            report "FA has an invalid local minimum"
            severity failure;
    end procedure;

    procedure assert_scaled_copy(
        constant optimized : in coefficient_vector_t;
        constant rtl : in coefficient_vector_t
    ) is
    begin
        assert optimized'length = rtl'length
            report "optimizer and RTL coefficient lengths differ"
            severity failure;
        for index in optimized'range loop
            assert rtl(rtl'low + index - optimized'low)
                = optimized(index) * RTL_MULTIPLIER
                report "RTL coefficient is not optimizer coefficient x2"
                severity failure;
        end loop;
    end procedure;
begin
    stimulus : process
    begin
        audit_ha(HA_OPT_COEFFICIENTS, -2, 1);
        report "OPTIMIZER_AUDIT HA valid_energy=-2 gap=1 invalid_local_minima=0 states=16"
            severity note;
        audit_fa(FA_OPT_COEFFICIENTS, -2, 1);
        report "OPTIMIZER_AUDIT FA valid_energy=-2 gap=1 invalid_local_minima=0 states=32"
            severity note;

        assert_scaled_copy(HA_OPT_COEFFICIENTS, HA_RTL_COEFFICIENTS);
        for state_code in 0 to 2 ** HA_NODE_COUNT - 1 loop
            assert state_energy_scaled(
                state_code,
                HA_NODE_COUNT,
                HA_RTL_COEFFICIENTS
            ) = RTL_MULTIPLIER * state_energy_scaled(
                state_code,
                HA_NODE_COUNT,
                HA_OPT_COEFFICIENTS
            )
                report "HA RTL energy is not optimizer energy x2"
                severity failure;
            assert is_local_minimum(
                state_code,
                HA_NODE_COUNT,
                HA_RTL_COEFFICIENTS
            ) = is_local_minimum(
                state_code,
                HA_NODE_COUNT,
                HA_OPT_COEFFICIENTS
            )
                report "HA RTL changed the local-minimum structure"
                severity failure;
        end loop;
        audit_ha(HA_RTL_COEFFICIENTS, -4, 2);
        report "RTL_SCALE_AUDIT HA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=16"
            severity note;

        assert_scaled_copy(FA_OPT_COEFFICIENTS, FA_RTL_COEFFICIENTS);
        for state_code in 0 to 2 ** FA_NODE_COUNT - 1 loop
            assert state_energy_scaled(
                state_code,
                FA_NODE_COUNT,
                FA_RTL_COEFFICIENTS
            ) = RTL_MULTIPLIER * state_energy_scaled(
                state_code,
                FA_NODE_COUNT,
                FA_OPT_COEFFICIENTS
            )
                report "FA RTL energy is not optimizer energy x2"
                severity failure;
            assert is_local_minimum(
                state_code,
                FA_NODE_COUNT,
                FA_RTL_COEFFICIENTS
            ) = is_local_minimum(
                state_code,
                FA_NODE_COUNT,
                FA_OPT_COEFFICIENTS
            )
                report "FA RTL changed the local-minimum structure"
                severity failure;
        end loop;
        audit_fa(FA_RTL_COEFFICIENTS, -4, 2);
        report "RTL_SCALE_AUDIT FA valid_energy=-4 gap=2 invalid_local_minima=0 proportional_scale=2 states=32"
            severity note;

        report "tb_optimizer_energy_audit passed" severity note;
        wait;
    end process;
end architecture sim;
