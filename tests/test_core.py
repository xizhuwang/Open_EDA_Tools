import copy
import json
from pathlib import Path
import tempfile
import unittest

from edaworkbench.project import ROOT, checked_file, flow_config, load_project, snapshot
from edaworkbench.reports import timing_paths, collect
from edaworkbench.cdc import review
from edaworkbench.tapeout import inspect_ports, profile


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.project = load_project(ROOT / 'examples/counter/project.json')

    def test_example(self):
        self.assertEqual(self.project['top'], 'counter')
        self.assertEqual(self.project['clock_period_ns'], 20)

    def test_snapshot_hash_and_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, hashes = snapshot(self.project, Path(tmp))
            self.assertIn('rtl/counter.v', hashes)
            self.assertEqual(len(hashes['rtl/counter.v']), 64)
            self.assertTrue((source / 'tb/tb.v').is_file())

    def test_outside_path_rejected(self):
        with self.assertRaises(ValueError):
            checked_file(self.project['base'], '../../eda.py')

    def test_config_checks_enabled(self):
        config = flow_config(self.project, Path('/example/input'))
        self.assertTrue(config['RUN_MAGIC_DRC'])
        self.assertTrue(config['RUN_LVS'])
        self.assertEqual(config['CLOCK_PERIOD'], 20)

    def test_checks_cannot_be_silently_disabled(self):
        p = copy.deepcopy(self.project)
        p['physical'] = {'RUN_LVS': False}
        with self.assertRaises(ValueError):
            flow_config(p, Path('/input'))


class ReportTests(unittest.TestCase):
    TEXT = '''Startpoint: count[0] (rising edge-triggered flip-flop clocked by clk)
Endpoint: count[7] (rising edge-triggered flip-flop clocked by clk)
Path Type: max
  3.5 data arrival time
  -0.42 slack (VIOLATED)
Startpoint: enable (input port)
Endpoint: count[1] (rising edge-triggered flip-flop clocked by clk)
Path Type: min
   0.35 slack (MET)
'''

    def test_multiple_real_paths(self):
        paths = timing_paths(self.TEXT, 'timing.rpt')
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0]['slack'], -0.42)
        self.assertEqual(paths[1]['type'], 'min')

    def test_no_fake_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = collect(tmp)
            self.assertEqual(result['metrics'], {})
            self.assertEqual(result['physical_checks']['lvs'], 'not run')
            self.assertEqual(result['paths'], [])

    def test_physical_checks_read_from_real_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'state_out.json'
            p.write_text(json.dumps({'metrics': {'magic__drc_error__count': 0, 'design__lvs_error__count': 1}}))
            result = collect(tmp)
            self.assertEqual(result['physical_checks'], {'magic_drc': 0, 'lvs': 1})


def ff(clock, d, q):
    return {'type': '$dff', 'connections': {'CLK': [clock], 'D': d, 'Q': q},
            'port_directions': {'CLK': 'input', 'D': 'input', 'Q': 'output'}}


class CDCTests(unittest.TestCase):
    def net(self, cells):
        return {'modules': {'top': {'cells': cells, 'netnames': {}}}}

    def test_unsafe_single_bit(self):
        report = review(self.net({'a': ff(2, [1], [3]), 'b': ff(5, [3], [6])}), 'top')
        crossings = [f for f in report['findings'] if f['kind'] == 'clock_crossing']
        self.assertEqual(len(crossings), 1)
        self.assertEqual(crossings[0]['second_stage_candidates'], [])

    def test_two_ff_is_candidate_not_signoff(self):
        report = review(self.net({'a': ff(2, [1], [3]), 'b': ff(5, [3], [6]), 'c': ff(5, [6], [7])}), 'top')
        self.assertFalse(report['signoff'])
        self.assertEqual(report['findings'][0]['second_stage_candidates'], ['c'])
        self.assertIn('candidate', report['findings'][0]['detail'])

    def test_multibit_not_marked_safe(self):
        report = review(self.net({'a': ff(2, [1, 8], [3, 9]), 'b': ff(5, [3, 9], [6, 10]), 'c': ff(5, [6, 10], [7, 11])}), 'top')
        self.assertIn('coherency', report['findings'][0]['detail'])

    def test_same_clock(self):
        report = review(self.net({'a': ff(2, [1], [3]), 'b': ff(2, [3], [6])}), 'top')
        self.assertEqual(report['findings'], [])


class TapeoutTests(unittest.TestCase):
    def test_exact_interface_not_acceptance(self):
        ports = {k: {'direction': d, 'bits': list(range(w))} for k, (d, w) in profile()['ports'].items()}
        data = {'modules': {'tt_um_example': {'ports': ports}}}
        report = inspect_ports(data, 'tt_um_example')
        self.assertTrue(report['interface_ok'])
        self.assertFalse(report['manufacturing_accepted'])
        self.assertEqual(report['official_precheck'], 'NOT RUN')

    def test_missing_and_wrong_ports(self):
        data = {'modules': {'counter': {'ports': {'ui_in': {'direction': 'output', 'bits': [1]}}}}}
        report = inspect_ports(data, 'counter')
        self.assertFalse(report['interface_ok'])
        self.assertGreater(len(report['errors']), 1)

    def test_wrong_process(self):
        ports = {k: {'direction': d, 'bits': list(range(w))} for k, (d, w) in profile()['ports'].items()}
        self.assertFalse(inspect_ports({'modules': {'tt_um_test': {'ports': ports}}}, 'tt_um_test', 'gf180mcuD')['interface_ok'])


if __name__ == '__main__':
    unittest.main()
