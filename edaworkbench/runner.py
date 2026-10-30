import datetime
import json
import os
from pathlib import Path
import selectors
import shlex
import shutil
import signal
import subprocess
import threading
import time
import uuid

from . import __version__
from .project import ROOT, flow_config, snapshot
from .reports import collect
from .cdc import review

TOOLS = ('iverilog', 'vvp', 'verilator', 'yosys', 'openroad', 'sta', 'magic', 'netgen', 'klayout', 'gtkwave', 'librelane')
STAGES = ('sim', 'lint', 'cdc', 'synth', 'sta', 'apr', 'verify', 'ttcheck', 'full')


def doctor():
    tools = {name: shutil.which(name) for name in TOOLS}
    try:
        import tkinter
        tk = tkinter.TkVersion
    except ImportError:
        tk = None
    return {'workbench': __version__, 'tools': tools, 'tk': tk,
            'display': os.environ.get('DISPLAY'), 'pdk_root': os.environ.get('PDK_ROOT', str(ROOT / '.pdks')),
            'toolchain': json.loads((ROOT / 'toolchain.lock.json').read_text()),
            'ready': all(tools.values()) and tk is not None}


class RunError(RuntimeError):
    pass


class Runner:
    def __init__(self, project, emit=print, timeout=3600, jobs=2):
        self.project = project
        self.emit = emit
        self.timeout = timeout
        self.jobs = max(1, min(16, jobs))
        self.cancelled = threading.Event()
        self.process = None
        self.run_dir = None
        self.commands = []

    def cancel(self):
        self.cancelled.set()

    def _kill(self, process):
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
        except ProcessLookupError:
            pass

    def command(self, argv, cwd=None):
        if self.cancelled.is_set():
            raise RunError('Cancelled')
        executable = shutil.which(argv[0])
        if not executable:
            raise RunError(f'{argv[0]} is missing. Run bash eda setup, then use bash eda ...')
        self.emit('$ ' + shlex.join(argv))
        record = {'argv': argv, 'started': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        self.commands.append(record)
        began = time.monotonic()
        env = dict(os.environ, NO_COLOR='1', PYTHONUNBUFFERED='1', OMP_NUM_THREADS=str(self.jobs))
        self.process = subprocess.Popen(argv, cwd=cwd or self.run_dir, env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
        process = self.process
        # Poll a pipe, not readline(): a silent hung tool must still be cancellable.
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        pending = b''
        size = 0
        with (self.run_dir / 'console.log').open('ab') as log:
            try:
                while selector.get_map():
                    if self.cancelled.is_set() or time.monotonic() - began > self.timeout:
                        self._kill(process)
                        raise RunError('Cancelled' if self.cancelled.is_set() else f'Tool timed out after {self.timeout}s')
                    for key, _ in selector.select(timeout=0.1):
                        block = os.read(key.fd, 65536)
                        if not block:
                            selector.unregister(key.fileobj)
                            continue
                        size += len(block)
                        if size > 100_000_000:
                            self._kill(process)
                            raise RunError('100 MB console limit exceeded; stopped runaway output')
                        log.write(block)
                        log.flush()
                        pending += block
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            self.emit(line.decode('utf-8', errors='replace'))
                if pending:
                    self.emit(pending.decode('utf-8', errors='replace'))
                code = process.wait()
                record['exit_code'] = code
                if code:
                    raise RunError(f'{argv[0]} exited with code {code}; inspect console.log')
            finally:
                selector.close()
                if process.poll() is None:
                    self._kill(process)
                self.process = None
                record['seconds'] = round(time.monotonic() - began, 3)

    def run(self, stage):
        if stage not in STAGES:
            raise ValueError(stage)
        base = Path(self.project['base'])
        history = base / '.runs'
        history.mkdir(exist_ok=True)
        lock = history / '.eda-lock'
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise RunError(f'Another job may be running. Inspect {lock}; remove only if its process is gone.')
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        tag = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
        run = history / tag
        run.mkdir()
        self.run_dir = run
        self.emit(f'RUN DIRECTORY: {run}')
        manifest = {'stage': stage, 'status': 'running', 'run': tag,
                    'clock_period_ns': self.project['clock_period_ns'], 'commands': self.commands,
                    'environment': doctor()}
        (history / 'latest.json').write_text(json.dumps({'run': tag}))
        try:
            src, hashes = snapshot(self.project, run)
            manifest['input_sha256'] = hashes
            (run / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            if stage == 'full':
                for action in ('sim', 'lint', 'cdc', 'verify'):
                    self._stage(action, src)
            else:
                self._stage(stage, src)
            manifest['status'] = 'completed'
        except (Exception, KeyboardInterrupt) as e:
            manifest['status'] = 'cancelled' if self.cancelled.is_set() or isinstance(e, KeyboardInterrupt) else 'failed'
            manifest['error'] = str(e)
            self.emit(f'{manifest["status"].upper()}: {e}')
            if isinstance(e, KeyboardInterrupt):
                self.cancel()
            raise
        finally:
            try:
                collect(run)
                (run / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
            finally:
                lock.unlink(missing_ok=True)
        return run

    def _stage(self, stage, src):
        p = self.project
        rtl = [str(src / f) for f in p['rtl']]
        if stage == 'sim':
            self.command(['iverilog', '-g2012', '-Wall', '-I', str(src), '-s', p['testbench_top'], '-o', 'simulation.vvp',
                          *rtl, *[str(src / f) for f in p['testbench']]])
            self.command(['vvp', 'simulation.vvp'])
        elif stage == 'lint':
            # Warnings remain visible but do not suppress structural synthesis checks.
            self.command(['verilator', '--lint-only', '--Wall', '-Wno-fatal', '--top-module', p['top'], '-I' + str(src), *rtl])
            self._netlist(src)
        elif stage == 'ttcheck':
            from .tapeout import inspect_ports
            self._netlist(src)
            data = json.loads((self.run_dir / 'netlist.json').read_text())
            result = inspect_ports(data, p['top'], p.get('pdk', 'sky130A'))
            (self.run_dir / 'tt-preflight.json').write_text(json.dumps(result, indent=2))
            self.emit(json.dumps(result, indent=2))
            if not result['interface_ok']:
                raise RunError('Tiny Tapeout interface mismatch. See tt-preflight.json.')
        elif stage == 'cdc':
            self._netlist(src)
            data = json.loads((self.run_dir / 'netlist.json').read_text())
            report = review(data, p['top'])
            (self.run_dir / 'cdc.json').write_text(json.dumps(report, indent=2))
            self.emit(f'CDC REVIEW: {len(report["findings"])} findings (manual review required; not sign-off).')
        else:
            config = flow_config(p, src)
            path = src / 'flow.json'
            path.write_text(json.dumps(config, indent=2))
            argv = ['librelane', '--pdk-root', os.environ.get('PDK_ROOT', str(ROOT / '.pdks')),
                    '--pdk', p.get('pdk', 'sky130A'), '--scl', p.get('scl', 'sky130_fd_sc_hd'),
                    '--run-tag', 'physical', '--jobs', str(self.jobs)]
            targets = {'synth': 'Yosys.Synthesis', 'sta': 'OpenROAD.STAPrePNR', 'apr': 'OpenROAD.STAPostPNR'}
            if stage in targets:
                argv += ['--to', targets[stage]]
            self.command([*argv, str(path)])
            if stage == 'verify':
                result = collect(self.run_dir)
                checks = result['physical_checks']
                if checks['magic_drc'] != 0 or checks['lvs'] != 0:
                    raise RunError(f'DRC/LVS not clean or not reported: {checks}')

    def _netlist(self, src):
        # Script content uses validated paths quoted for Yosys, not shell escaping.
        files = ' '.join('"' + str(src / f) + '"' for f in self.project['rtl'])
        script = '\n'.join([
            f'read_verilog -noautowire -I"{src}" {files}',
            f'hierarchy -check -top {self.project["top"]}',
            'proc', 'flatten', 'opt_clean', 'check -assert',
            'scc -expect 0', 'write_json netlist.json',
        ])
        script_path = self.run_dir / 'review.ys'
        script_path.write_text(script)
        self.command(['yosys', '-T', '-s', str(script_path)])


def latest_run(project):
    history = Path(project['base']) / '.runs'
    try:
        tag = json.loads((history / 'latest.json').read_text())['run']
        path = (history / tag).resolve()
        if path.parent != history.resolve() or not path.is_dir():
            raise ValueError('Invalid latest run')
        return path
    except FileNotFoundError:
        raise RunError('No run yet. Run simulation or the physical flow first.')


def open_view(project, kind, run=None):
    run = run or latest_run(project)
    if kind == 'wave':
        waves = sorted(run.rglob('*.vcd')) + sorted(run.rglob('*.fst'))
        if not waves:
            raise RunError('No VCD/FST. Add $dumpfile("dump.vcd"); $dumpvars(0, tb); to your testbench and run sim.')
        argv = ['gtkwave', str(waves[0])]
    elif kind == 'layout' and list(run.rglob('*.gds')):
        gds = sorted(run.rglob('*.gds'))
        argv = ['klayout', str(gds[-1])]
    elif kind in ('layout', 'openroad'):
        resolved = sorted(run.rglob('resolved.json'))
        if not resolved:
            raise RunError('No resolved physical flow. Run APR/verify first.')
        flow = 'OpenInKLayout' if kind == 'layout' else 'OpenInOpenROAD'
        argv = ['librelane', '--pdk-root', os.environ.get('PDK_ROOT', str(ROOT / '.pdks')), '--last-run', '--flow', flow, str(resolved[-1])]
    else:
        raise ValueError(kind)
    if not shutil.which(argv[0]):
        raise RunError(f'Missing tool: {argv[0]}')
    # Viewer lifetimes are separate from computational jobs; do not block the UI.
    log = (run / f'{kind}-viewer.log').open('ab')
    try:
        return subprocess.Popen(argv, cwd=run, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        log.close()
