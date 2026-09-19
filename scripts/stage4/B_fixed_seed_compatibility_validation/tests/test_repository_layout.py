"""Guard the experiment layout and report/run separation after relocation."""
from __future__ import annotations

import sys
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'experiment_timeline.md').is_file())
sys.path.insert(0, str(ROOT))
from scripts.stage4.B_fixed_seed_compatibility_validation import run_questa_compatibility_validation as replay
from scripts.stage2 import run_rca_convergence_benchmark as benchmark


class RepositoryLayoutTests(unittest.TestCase):
    def test_shared_library_has_no_generated_hardware(self):
        self.assertEqual(
            {p.name for p in (ROOT / 'src').glob('*.vhd')},
            {'inv_sc_pkg.vhd', 'lfsr32.vhd', 'spin_node.vhd', 'inv_and_gate.vhd', 'inv_xor_gate.vhd'},
        )

    def test_each_experiment_has_a_readme(self):
        for stage in (ROOT / 'experiments').glob('stage[1-5]'):
            self.assertTrue((stage / 'README.md').is_file(), str(stage))
            for path in stage.iterdir():
                if path.is_dir() and re.match(r'^[A-Z]_', path.name):
                    self.assertTrue((path / 'README.md').is_file(), str(path))

    def test_all_do_repository_paths_exist(self):
        checked = 0
        for path in (ROOT / 'sim_scripts').rglob('*.do'):
            for relative in re.findall(r'\[sim_repo_path \{([^}]+)\}\]', path.read_text(encoding='utf-8')):
                self.assertTrue((ROOT / relative).is_file(), f'{path}: {relative}')
                checked += 1
        self.assertGreater(checked, 100)

    def test_literal_sim_input_paths_resolve_from_shared_root(self):
        for path in (ROOT / 'sim_scripts').rglob('*.do'):
            for relative in re.findall(r'\[sim_input_path \{([^}]+)\}\]', path.read_text(encoding='utf-8')):
                self.assertTrue((ROOT / 'sim_scripts' / relative).is_file(), f'{path}: {relative}')

    def test_core_plan_points_to_organized_wrappers(self):
        _, golden, _ = replay.verify_replay_inputs()
        for spec in replay.benchmark_run_specs() + replay.comb6_run_specs(golden):
            self.assertTrue(spec.wrapper.is_file(), str(spec.wrapper))
            self.assertTrue(spec.wrapper.is_relative_to(ROOT / 'sim_scripts'))
        self.assertEqual(replay.parse_args([]).build_root, ROOT / 'results_and_reports/stage4/B_fixed_seed_compatibility_validation/runs')

    def test_staging_and_publication_leave_runs_and_scratch_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reports = root / 'results_and_reports'
            owner = reports / 'stage2/rca_convergence_benchmark'
            owner.mkdir(parents=True)
            for name in replay.BENCHMARK_ARTIFACTS:
                target = owner / name
                if name.endswith('.md'):
                    target.write_text('old report', encoding='utf-8')
                else:
                    target.mkdir()
                    (target / 'old.txt').write_text('old evidence', encoding='utf-8')
            for name in ('runs', 'scratch_test'):
                (owner / name).mkdir()
                (owner / name / 'sentinel').write_bytes(b'keep me')
            comb6 = reports / 'comb6.md'
            comb6.write_text('comb6', encoding='utf-8')
            stage = root / 'stage'
            stage.mkdir()
            with mock.patch.multiple(replay, REPORTS=reports, BENCHMARK_REPORT=owner, COMB6_REPORT=comb6):
                candidate, _ = replay.prepare_candidate(stage)
                self.assertFalse((candidate / 'runs').exists())
                self.assertFalse((candidate / 'scratch_test').exists())
                (candidate / 'report.md').write_text('new report', encoding='utf-8')
                replay.publish_transaction(
                    [(candidate / name, owner / name) for name in replay.BENCHMARK_ARTIFACTS], stage,
                )
            self.assertEqual((owner / 'report.md').read_text(encoding='utf-8'), 'new report')
            for name in ('runs', 'scratch_test'):
                self.assertEqual((owner / name / 'sentinel').read_bytes(), b'keep me')

    def test_guarded_regeneration_preserves_unrelated_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            owner = root / 'results_and_reports/stage2/rca_convergence_benchmark'
            runs = owner / 'runs'
            runs.mkdir(parents=True)
            (runs / 'sentinel').write_bytes(b'keep me')
            with mock.patch.multiple(benchmark, ROOT=root, OUT=owner, DATA=owner / 'data', FIGS=owner / 'figures', TRACES=owner / 'traces'):
                benchmark.prepare_output()
            self.assertEqual((runs / 'sentinel').read_bytes(), b'keep me')


if __name__ == '__main__':
    unittest.main()
