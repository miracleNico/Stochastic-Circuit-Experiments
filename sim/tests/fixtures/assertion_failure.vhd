entity deliberate_assertion_failure is
end entity;

architecture sim of deliberate_assertion_failure is
begin
    process
    begin
        assert false
            report "neutral deliberate stop"
            severity failure;
        wait;
    end process;
end architecture;
