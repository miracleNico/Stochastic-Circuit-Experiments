library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.inv_sc_pkg.all;

entity spin_node is
    generic (
        NUM_INPUTS   : natural := 2;
        BIAS         : integer := 0;
        W0           : integer := 0;
        W1           : integer := 0;
        W2           : integer := 0;
        W3           : integer := 0;
        W4           : integer := 0;
        W5           : integer := 0;
        W6           : integer := 0;
        W7           : integer := 0;
        W8           : integer := 0;
        W9           : integer := 0;
        W10          : integer := 0;
        W11          : integer := 0;
        W12          : integer := 0;
        W13          : integer := 0;
        W14          : integer := 0;
        W15          : integer := 0;
        W16          : integer := 0;
        W17          : integer := 0;
        W18          : integer := 0;
        W19          : integer := 0;
        W20          : integer := 0;
        W21          : integer := 0;
        W22          : integer := 0;
        W23          : integer := 0;
        W24          : integer := 0;
        W25          : integer := 0;
        W26          : integer := 0;
        W27          : integer := 0;
        W28          : integer := 0;
        W29          : integer := 0;
        W30          : integer := 0;
        W31          : integer := 0;
        FIELD_FRAC_BITS : natural := 0;
        RND_WEIGHT      : natural := 0;
        USE_DYNAMIC_RND : boolean := false;
        COUNTER_BITS    : natural := 5;
        SEED         : std_logic_vector(31 downto 0) := x"00000001"
    );
    port (
        clk         : in  std_logic;
        rst         : in  std_logic;
        enable      : in  std_logic;
        rnd_weight_i : in natural := 0;
        clamp_en    : in  std_logic;
        clamp_value : in  std_logic;
        neighbors   : in  spin_vector_t;
        spin_o      : out std_logic;
        field_o     : out field_t;
        counter_o   : out signed(COUNTER_BITS downto 0)
    );
end entity;

architecture rtl of spin_node is
    constant COUNTER_LIMIT : integer := (2 ** COUNTER_BITS) - 1;

    signal rnd_bit     : std_logic;
    signal lfsr_state  : std_logic_vector(31 downto 0);
    signal spin_q      : std_logic := '0';
    signal counter_q   : integer range -COUNTER_LIMIT to COUNTER_LIMIT := 0;
    signal field_q     : integer := 0;

    function weight_at(index : natural) return integer is
    begin
        case index is
            when 0 => return W0;
            when 1 => return W1;
            when 2 => return W2;
            when 3 => return W3;
            when 4 => return W4;
            when 5 => return W5;
            when 6 => return W6;
            when 7 => return W7;
            when 8 => return W8;
            when 9 => return W9;
            when 10 => return W10;
            when 11 => return W11;
            when 12 => return W12;
            when 13 => return W13;
            when 14 => return W14;
            when 15 => return W15;
            when 16 => return W16;
            when 17 => return W17;
            when 18 => return W18;
            when 19 => return W19;
            when 20 => return W20;
            when 21 => return W21;
            when 22 => return W22;
            when 23 => return W23;
            when 24 => return W24;
            when 25 => return W25;
            when 26 => return W26;
            when 27 => return W27;
            when 28 => return W28;
            when 29 => return W29;
            when 30 => return W30;
            when 31 => return W31;
            when others => return 0;
        end case;
    end function;

    type tanh_table_t is array (0 to 128) of integer range 0 to 65536;
    constant TANH_Q4_TABLE : tanh_table_t := (
           22,    25,    28,    32,    36,    41,    47,    53,
           60,    68,    77,    87,    98,   111,   126,   143,
          162,   184,   208,   236,   267,   302,   342,   387,
          439,   497,   562,   636,   720,   815,   922,  1042,
         1179,  1333,  1506,  1701,  1921,  2168,  2446,  2758,
         3108,  3500,  3938,  4427,  4971,  5577,  6249,  6992,
         7812,  8714,  9702, 10782, 11955, 13226, 14595, 16062,
        17625, 19282, 21025, 22849, 24743, 26695, 28693, 30723,
        32768, 34813, 36843, 38841, 40793, 42687, 44511, 46254,
        47911, 49474, 50941, 52310, 53581, 54754, 55834, 56822,
        57724, 58544, 59287, 59959, 60565, 61109, 61598, 62036,
        62428, 62778, 63090, 63368, 63615, 63835, 64030, 64203,
        64357, 64494, 64614, 64721, 64816, 64900, 64974, 65039,
        65097, 65149, 65194, 65234, 65269, 65300, 65328, 65352,
        65374, 65393, 65410, 65425, 65438, 65449, 65459, 65468,
        65476, 65483, 65489, 65495, 65500, 65504, 65508, 65511,
        65514
    );

    function field_to_q8(field : integer) return integer is
        variable scaled : integer := field;
    begin
        if FIELD_FRAC_BITS < 8 then
            for i in FIELD_FRAC_BITS to 7 loop
                scaled := scaled * 2;
            end loop;
        elsif FIELD_FRAC_BITS > 8 then
            for i in 9 to FIELD_FRAC_BITS loop
                scaled := scaled / 2;
            end loop;
        end if;

        return scaled;
    end function;

    function tanh_probability_threshold(field : integer) return integer is
        variable q8_field : integer;
        variable offset   : integer;
        variable index    : integer;
        variable frac     : integer;
        variable low_v    : integer;
        variable high_v   : integer;
    begin
        -- 16-bit thresholds for P(m=+1) = (1 + tanh(field)) / 2, beta = 1.
        -- FIELD_FRAC_BITS lets generated networks encode fractional coefficients.
        q8_field := field_to_q8(field);

        if q8_field <= -1024 then
            return 0;
        elsif q8_field >= 1024 then
            return 65536;
        else
            offset := q8_field + 1024;
            index := offset / 16;
            frac := offset mod 16;

            if index >= 128 then
                return TANH_Q4_TABLE(128);
            else
                low_v := TANH_Q4_TABLE(index);
                high_v := TANH_Q4_TABLE(index + 1);
                return low_v + (((high_v - low_v) * frac + 8) / 16);
            end if;
        end if;
    end function;

    function weighted_sum(
        spins : spin_vector_t;
        noise : std_logic;
        rnd_weight : natural
    ) return integer is
        variable sum : integer;
    begin
        sum := BIAS;

        for i in 0 to SPIN_INPUTS_MAX - 1 loop
            if i < NUM_INPUTS then
                sum := sum + (weight_at(i) * spin_to_int(spins(i)));
            end if;
        end loop;

        if noise = '1' then
            sum := sum + integer(rnd_weight);
        else
            sum := sum - integer(rnd_weight);
        end if;

        return sum;
    end function;
begin
    prng : entity work.lfsr32
        generic map (
            SEED => SEED
        )
        port map (
            clk     => clk,
            rst     => rst,
            enable  => enable,
            rnd_bit => rnd_bit,
            state_o => lfsr_state
        );

    process (clk)
        variable field_v     : integer;
        variable counter_v   : integer;
        variable threshold_v : integer;
        variable uniform_v   : integer;
        variable rnd_weight_v : natural;
    begin
        if rising_edge(clk) then
            if rst = '1' then
                field_q <= 0;
                if SEED(0) = '1' then
                    spin_q <= '1';
                else
                    spin_q <= '0';
                end if;
                counter_q <= 0;
            elsif enable = '1' then
                if clamp_en = '1' then
                    spin_q  <= clamp_value;
                    field_q <= 0;
                    if clamp_value = '1' then
                        counter_q <= COUNTER_LIMIT;
                    else
                        counter_q <= -COUNTER_LIMIT;
                    end if;
                else
                    if USE_DYNAMIC_RND then
                        rnd_weight_v := rnd_weight_i;
                    else
                        rnd_weight_v := RND_WEIGHT;
                    end if;
                    field_v   := weighted_sum(neighbors, rnd_bit, rnd_weight_v);
                    counter_v := sat_add(counter_q, field_v, COUNTER_LIMIT);
                    threshold_v := tanh_probability_threshold(field_v);
                    uniform_v := to_integer(unsigned(lfsr_state(31 downto 16)));

                    field_q   <= field_v;
                    counter_q <= counter_v;

                    if uniform_v < threshold_v then
                        spin_q <= '1';
                    else
                        spin_q <= '0';
                    end if;
                end if;
            end if;
        end if;
    end process;

    spin_o    <= spin_q;
    field_o   <= to_field(field_q);
    counter_o <= to_signed(counter_q, COUNTER_BITS + 1);
end architecture;
