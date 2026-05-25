import json
from pathlib import Path

import numpy as np

from generate_hamiltonians import energy, nonzero_edges
from generate_shadow1_adder4 import emit as emit_shadow1
from optimize_fp8_hamiltonians import CoefficientFormat, q8_fa, q8_ha


ROOT = Path(__file__).resolve().parents[1]
FRAC_BITS = 4
MAX_PHYSICAL = 7
COPY_PHYSICAL = 4


def optimize_q34_blocks():
    fmt = CoefficientFormat(name="fixed-q3d4f", frac_bits=FRAC_BITS, values=None)
    coeff_max_encoded = MAX_PHYSICAL << FRAC_BITS
    ha = q8_ha(coeff_max_encoded, fmt)
    fa = q8_fa(coeff_max_encoded, fmt)

    for item in (ha, fa):
        item.ham.field_frac_bits = FRAC_BITS
        item.ham.weight_scale = "fixed-q3d4f"
        item.ham.source = (
            "Fixed Q3.4 MILP: maximize valid/invalid gate gap, then minimize "
            f"carry-boundary L1; |physical coefficient|<={MAX_PHYSICAL}"
        )
    return ha, fa


def write_report(path: Path, ha, fa, copy_weight_encoded: int) -> None:
    denominator = 1 << FRAC_BITS

    def physical(value: int) -> float:
        return value / denominator

    def gate_data(item):
        ham = item.ham
        return {
            "name": ham.name,
            "nodes": ham.nodes,
            "field_frac_bits": FRAC_BITS,
            "h_encoded": ham.h,
            "h_physical": [physical(value) for value in ham.h],
            "J_encoded": ham.j,
            "J_physical": [[physical(value) for value in row] for row in ham.j],
            "edges_encoded": nonzero_edges(ham),
            "gate_gap_encoded": item.gamma_encoded,
            "gate_gap_physical": physical(item.gamma_encoded),
            "valid_energy_encoded": energy(ham.h, ham.j, ham.valid_states[0]),
            "valid_energy_physical": physical(energy(ham.h, ham.j, ham.valid_states[0])),
            "boundary_abs_encoded": item.boundary_abs_encoded,
            "boundary_abs_physical": physical(item.boundary_abs_encoded),
            "coeff_abs_encoded": item.coeff_abs_encoded,
            "coeff_abs_physical": physical(item.coeff_abs_encoded),
        }

    data = {
        "format": "fixed-q3d4f",
        "interpretation": "physical_value = encoded / 16",
        "coefficient_max_physical": MAX_PHYSICAL,
        "copy_weight_encoded": copy_weight_encoded,
        "copy_weight_physical": physical(copy_weight_encoded),
        "copy_gap_encoded": 2 * copy_weight_encoded,
        "copy_gap_physical": physical(2 * copy_weight_encoded),
        "gates": [gate_data(ha), gate_data(fa)],
    }

    def plain(value):
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, list):
            return [plain(item) for item in value]
        if isinstance(value, dict):
            return {key: plain(item) for key, item in value.items()}
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plain(data), indent=2), encoding="utf-8")


def main() -> None:
    ha, fa = optimize_q34_blocks()
    copy_weight_encoded = COPY_PHYSICAL << FRAC_BITS
    emit_shadow1(
        ROOT / "src" / "generated_shadow1_q34_adder4.vhd",
        copy_weight=copy_weight_encoded,
        ha=ha.ham,
        fa=fa.ham,
        entity="gen_adder4_shadow1_windowed",
        seed_name=f"ADDER4_SHADOW1_Q34_W{copy_weight_encoded}",
        field_frac_bits=FRAC_BITS,
    )
    write_report(ROOT / "reports" / "optimized_q34_shadow1_blocks.json", ha, fa, copy_weight_encoded)


if __name__ == "__main__":
    main()
