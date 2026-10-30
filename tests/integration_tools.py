"""Run with `bash eda test` inside the actual portable tool environment."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

from edaworkbench.project import ROOT, load_project
from edaworkbench.runner import Runner, RunError, doctor


class ToolTests(unittest.TestCase):
    def project(self, directory):
        shutil.copytree(ROOT / 'examples/counter', directory, ignore=shutil.ignore_patterns('.runs'))
        return load_project(Path(directory) / 'project.json')

    def test_all_real_tools_present(self):
        d = doctor()
        self.assertTrue(d['ready'], json.dumps(d, indent=2))

    def test_self_checking_sim(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp) / 'project')
            run = Runner(p, emit=lambda _: None).run('sim')
            self.assertIn('PASS: counter', (run / 'console.log').read_text())
            self.assertTrue((run / 'dump.vcd').is_file())

    def test_lint_and_cdc(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp) / 'project')
            Runner(p, emit=lambda _: None).run('lint')
            run = Runner(p, emit=lambda _: None).run('cdc')
            self.assertFalse(json.loads((run / 'cdc.json').read_text())['signoff'])

    def test_bad_syntax_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp) / 'project')
            Path(p['base'], 'rtl/counter.v').write_text('module counter( this is not Verilog;')
            with self.assertRaises(RunError):
                Runner(p, emit=lambda _: None).run('sim')
            self.assertFalse(Path(p['base'], '.runs/.eda-lock').exists())

    def test_infinite_silent_process_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp) / 'project')
            runner = Runner(p, timeout=1, emit=lambda _: None)
            runner.run_dir = Path(tmp)
            with self.assertRaisesRegex(RunError, 'timed out'):
                runner.command(['python3', '-c', 'import time; time.sleep(30)'])
            self.assertIsNone(runner.process)

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.project(Path(tmp) / 'project')
            runner = Runner(p, timeout=20, emit=lambda _: None)
            runner.run_dir = Path(tmp)
            timer = threading.Timer(0.5, runner.cancel)
            timer.start()
            started = time.monotonic()
            try:
                with self.assertRaisesRegex(RunError, 'Cancelled'):
                    runner.command(['python3', '-c', 'import time; time.sleep(30)'])
                self.assertLess(time.monotonic() - started, 5)
            finally:
                timer.cancel()

    def test_sram_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(['iverilog', '-g2012', '-s', 'tb_sram', '-o', str(Path(tmp) / 'test.vvp'),
                                     *[str(f) for f in sorted((ROOT / 'models/sram').glob('*.v'))],
                                     str(ROOT / 'tests/tb_sram.v')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            sim = subprocess.run(['vvp', str(Path(tmp) / 'test.vvp')], capture_output=True, text=True, timeout=10)
            self.assertEqual(sim.returncode, 0, sim.stdout + sim.stderr)
            self.assertIn('PASS', sim.stdout)

    def test_tiny_tapeout_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'tt'
            shutil.copytree(ROOT / 'examples/tiny_tapeout', target, ignore=shutil.ignore_patterns('.runs'))
            p = load_project(target / 'project.json')
            sim = Runner(p, emit=lambda _: None).run('sim')
            self.assertIn('PASS: Tiny Tapeout', (sim / 'console.log').read_text())
            run = Runner(p, emit=lambda _: None).run('ttcheck')
            report = json.loads((run / 'tt-preflight.json').read_text())
            self.assertTrue(report['interface_ok'])
            self.assertFalse(report['manufacturing_accepted'])
