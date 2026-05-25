from argparse import Namespace
from itertools import product

from generate_hamiltonians import energy, hamiltonians, verify_all


def verify_block_gaps(hams) -> None:
    for ham in hams:
        if ham.valid_states is None:
            continue

        valid = set(ham.valid_states)
        valid_energy = None
        invalid_min = None

        for bits in product([0, 1], repeat=len(ham.nodes)):
            state_energy = energy(ham.h, ham.j, bits)
            if bits in valid:
                if valid_energy is None:
                    valid_energy = state_energy
                elif state_energy != valid_energy:
                    raise AssertionError(f"{ham.name}: valid energy mismatch")
            else:
                if invalid_min is None or state_energy < invalid_min:
                    invalid_min = state_energy

        if invalid_min is not None and invalid_min <= valid_energy:
            raise AssertionError(f"{ham.name}: invalid state is not above the valid manifold")

        print(
            f"{ham.name:14s} nodes={len(ham.nodes):2d} "
            f"valid_energy={valid_energy:5} gap={invalid_min - valid_energy if invalid_min is not None else 'n/a'}"
        )


def verify_ripple_adder(ham, width: int) -> None:
    expected_nodes = [f"a{i}" for i in range(width)]
    expected_nodes += [f"b{i}" for i in range(width)]
    expected_nodes += [f"s{i}" for i in range(width)]
    expected_nodes += [f"c{i}" for i in range(1, width + 1)]
    if ham.nodes != expected_nodes:
        raise AssertionError(f"{ham.name} node order changed")

    idx = {name: i for i, name in enumerate(ham.nodes)}
    energies = set()
    checked = 0

    for aval in range(1 << width):
        for bval in range(1 << width):
            bits = [0] * len(ham.nodes)
            carry = 0
            for bit in range(width):
                abit = (aval >> bit) & 1
                bbit = (bval >> bit) & 1
                total = abit + bbit + carry

                bits[idx[f"a{bit}"]] = abit
                bits[idx[f"b{bit}"]] = bbit
                bits[idx[f"s{bit}"]] = total & 1

                carry = (total >> 1) & 1
                bits[idx[f"c{bit + 1}"]] = carry

            energies.add(energy(ham.h, ham.j, tuple(bits)))
            checked += 1

    if len(energies) != 1:
        raise AssertionError(f"{ham.name} valid states have multiple energies: {sorted(energies)}")

    print(
        f"{ham.name:14s} nodes={len(ham.nodes):2d} "
        f"valid_vectors={checked} valid_energy={next(iter(energies))}"
    )


def main() -> None:
    args = Namespace(ha_scale=1, fa_scale=1)
    hams = hamiltonians(args)
    verify_all(hams)

    print("Exhaustive finite Hamiltonian checks")
    print("-------------------------------------")
    adder_widths = {
        "ADDER4_RIPPLE": 4,
        "ADDER8_RIPPLE": 8,
    }
    verify_block_gaps([ham for ham in hams if ham.name not in adder_widths])
    for name, width in adder_widths.items():
        verify_ripple_adder(next(ham for ham in hams if ham.name == name), width)
    print("\nAll Hamiltonian checks passed.")


if __name__ == "__main__":
    main()
