# Shared VHDL library

Only reusable primitives live here: `inv_sc_pkg.vhd`, `lfsr32.vhd`,
`spin_node.vhd`, `inv_and_gate.vhd` and `inv_xor_gate.vhd`.

Generated networks and experimental hardware belong in
`experiments/<experiment>/hardware/`. VHDL testbenches belong beside the
experiment's Questa launchers in `sim_scripts/<experiment>/tb/`.
