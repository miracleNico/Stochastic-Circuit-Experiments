from pathlib import Path

from generate_shadow1_adder4 import emit as emit_shadow1
from generate_shadow1_q34_adder4 import COPY_PHYSICAL, FRAC_BITS, optimize_q34_blocks, write_report


ROOT = Path(__file__).resolve().parents[1]
WIDTH = 8


def main() -> None:
    ha, fa = optimize_q34_blocks()
    copy_weight_encoded = COPY_PHYSICAL << FRAC_BITS
    emit_shadow1(
        ROOT / "src" / "generated_shadow1_q34_adder8.vhd",
        width=WIDTH,
        copy_weight=copy_weight_encoded,
        ha=ha.ham,
        fa=fa.ham,
        entity="gen_adder8_shadow1_windowed",
        seed_name=f"ADDER8_SHADOW1_Q34_W{copy_weight_encoded}",
        field_frac_bits=FRAC_BITS,
    )
    write_report(ROOT / "reports" / "optimized_q34_shadow1_adder8_blocks.json", ha, fa, copy_weight_encoded)


if __name__ == "__main__":
    main()
