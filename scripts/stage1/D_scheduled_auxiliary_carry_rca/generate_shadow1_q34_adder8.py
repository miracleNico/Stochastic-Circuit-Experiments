
import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = next(p for p in _Path(__file__).resolve().parents if (p / "experiment_timeline.md").is_file())
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))

from pathlib import Path

from scripts.stage1.D_scheduled_auxiliary_carry_rca.generate_shadow1_adder4 import emit as emit_shadow1
from scripts.stage1.D_scheduled_auxiliary_carry_rca.generate_shadow1_q34_adder4 import COPY_PHYSICAL, FRAC_BITS, optimize_q34_blocks, write_report


ROOT = _REPO_ROOT
WIDTH = 8


def main() -> None:
    ha, fa = optimize_q34_blocks()
    copy_weight_encoded = COPY_PHYSICAL << FRAC_BITS
    emit_shadow1(
        ROOT / "experiments/stage1/D_scheduled_auxiliary_carry_rca/hardware/generated_shadow1_q34_adder8.vhd",
        width=WIDTH,
        copy_weight=copy_weight_encoded,
        ha=ha.ham,
        fa=fa.ham,
        entity="gen_adder8_shadow1_windowed",
        seed_name=f"ADDER8_SHADOW1_Q34_W{copy_weight_encoded}",
        field_frac_bits=FRAC_BITS,
    )
    write_report(ROOT / "results_and_reports/stage1/D_scheduled_auxiliary_carry_rca/optimized_q34_shadow1_adder8_blocks.json", ha, fa, copy_weight_encoded)


if __name__ == "__main__":
    main()
