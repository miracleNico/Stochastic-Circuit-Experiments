# Results and reports

Each child directory uses the same experiment ID as [the experiment index](../experiments/README.md).
Curated reports, coefficient outputs, parsed data, figures and published traces
are versioned here. A file move does not imply a new simulation or change its
scientific provenance.

New simulator runs default to `stageN/<owner>/runs/<simulator>/<case>/<run-id>/`.
That ignored directory contains transcripts, metadata, raw CSV, optional WLF and
work libraries. Full compatibility validation stages under
`stage4/B_fixed_seed_compatibility_validation/runs/` and publishes verified
evidence back to its owning experiments transactionally.
Explicit `-BuildRoot` / `--build-root` overrides are still supported.

Historical ignored `.sim_build/` caches may exist locally from before the
reorganization; they are not the new default or versioned evidence. Historical
transcripts retain their original embedded paths and timestamps. Their bytes
and all frozen VHDL bytes are preserved by this reorganization.
