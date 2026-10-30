import argparse
import json
import sys
import subprocess
from pathlib import Path

from .project import ROOT, load_project
from .runner import Runner, RunError, STAGES, doctor, latest_run, open_view


def main(argv=None):
    parser = argparse.ArgumentParser(description='Open EDA Tools — native WSL desktop and local ASIC flow')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor', help='Check actual tools and desktop support')
    gui = sub.add_parser('gui', help='Native desktop workbench (no HTTP server)')
    run = sub.add_parser('run', help='Run an actual EDA stage')
    run.add_argument('stage', choices=STAGES)
    run.add_argument('--jobs', type=int, default=2)
    run.add_argument('--timeout', type=int, default=3600, help='Per-tool timeout in seconds')
    view = sub.add_parser('view')
    view.add_argument('kind', choices=('wave', 'layout', 'openroad'))
    sub.add_parser('test', help='Self-check simulation, SRAM models, lint and CDC')
    summary = sub.add_parser('report')
    tapeout = sub.add_parser('tapeout', help='Export the TT counter preparation project into the reviewed official SKY template')
    tapeout.add_argument('--out', required=True)
    tapeout.add_argument('--author', default='', help='Public author field; blank means fill it before submission')
    tapeout.add_argument('--title', default='Open EDA counter')
    for command in (gui, run, view, summary, tapeout):
        command.add_argument('--project', default=str(ROOT / 'examples/counter/project.json'))
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            data = doctor()
            print(json.dumps(data, indent=2))
            return 0 if data['ready'] else 2
        if args.command == 'test':
            import unittest
            suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='integration_*.py')
            return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
        project = load_project(args.project)
        if args.command == 'gui':
            from .gui import Workbench
            Workbench(project).mainloop()
        elif args.command == 'run':
            run_dir = Runner(project, timeout=args.timeout, jobs=args.jobs).run(args.stage)
            print(f'Completed: {run_dir}\nReports: {run_dir / "summary.json"}')
        elif args.command == 'view':
            process = open_view(project, args.kind)
            return process.wait()
        elif args.command == 'report':
            print((latest_run(project) / 'summary.json').read_text())
        elif args.command == 'tapeout':
            from .tapeout import export
            Runner(project).run('ttcheck')
            out = export(project, args.out, args.author, args.title)
            print(f'Prepared: {out}\nOfficial GDS / precheck / gate-level test and provider acceptance are still required. Nothing was submitted or purchased.')
        return 0
    except (ValueError, OSError, RunError, ImportError, subprocess.SubprocessError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
