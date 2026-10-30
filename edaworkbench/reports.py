"""Parse real LibreLane/OpenSTA output without manufacturing absent metrics."""
import json
import math
import re
from pathlib import Path

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')


def timing_paths(text, source='', limit=40):
    paths = []
    # OpenSTA uses both Startpoint:/Endpoint: and slack (MET/VIOLATED) lines.
    for block in re.split(r'(?=Startpoint:)', ANSI.sub('', text)):
        if not block.startswith('Startpoint:'):
            continue
        start = re.search(r'^Startpoint:\s*(.+)', block, re.M)
        end = re.search(r'^Endpoint:\s*(.+)', block, re.M)
        slack = re.search(r'^\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s+slack\s*\(([^)]+)\)', block, re.M)
        # Some OpenSTA releases print the label before the numeric value.
        if not slack:
            reverse = re.search(r'^\s*slack\s*\(([^)]+)\)\s+([-+]?\d+(?:\.\d+)?)', block, re.M)
            if reverse:
                value, status = float(reverse[2]), reverse[1]
            else:
                continue
        else:
            value, status = float(slack[1]), slack[2]
        kind = re.search(r'^Path Type:\s*(.+)', block, re.M)
        paths.append({'startpoint': start[1] if start else '?', 'endpoint': end[1] if end else '?',
                      'slack': value, 'status': status, 'type': kind[1] if kind else 'unknown',
                      'report': source, 'detail': block.strip()})
        if len(paths) >= limit:
            break
    return paths


def collect(run):
    run = Path(run)
    summary = {'metrics': {}, 'paths': [], 'states': [], 'artifacts': [],
               'physical_checks': {'magic_drc': 'not run', 'lvs': 'not run'},
               'notes': ['Missing metrics mean not reported, never zero.',
                         'Power is the tool activity/model estimate, not measured silicon power.',
                         'Timing units/corner are those in each original report and resolved configuration.']}
    def step_order(filename):
        match = re.match(r'(\d+)', filename.parent.name)
        return (int(match[1]) if match else -1, str(filename))
    candidates = sorted(run.rglob('state_out.json'), key=step_order)
    latest = None
    for filename in candidates:
        try:
            state = json.loads(filename.read_text())
        except (OSError, ValueError):
            continue
        summary['states'].append(str(filename.relative_to(run)))
        latest = state
    if latest:
        # Sequential steps carry forward prior metrics; use the final one only.
        summary['metrics'] = latest.get('metrics', {})
    nonfinite = [k for k, v in summary['metrics'].items() if isinstance(v, float) and not math.isfinite(v)]
    for key in nonfinite:
        summary['metrics'][key] = None
    summary['nonfinite_metrics'] = nonfinite
    if nonfinite:
        summary['notes'].append('Non-finite upstream metrics are null here; inspect original reports for unconstrained / absent paths.')
    m = summary['metrics']
    if 'magic__drc_error__count' in m:
        summary['physical_checks']['magic_drc'] = m['magic__drc_error__count']
    if 'design__lvs_error__count' in m:
        summary['physical_checks']['lvs'] = m['design__lvs_error__count']
    # Prefer most recent step reports; retain raw reports for all corners.
    reports = sorted(run.rglob('*.rpt'), key=lambda f: (f.stat().st_mtime_ns, str(f)), reverse=True)
    seen = set()
    for filename in reports:
        if len(summary['paths']) >= 80 or filename.stat().st_size > 20_000_000:
            continue
        text = filename.read_text(errors='replace')
        for path in timing_paths(text, str(filename.relative_to(run))):
            key = (path['startpoint'], path['endpoint'], path['type'], path['slack'])
            if key not in seen:
                summary['paths'].append(path)
                seen.add(key)
    summary['paths'].sort(key=lambda p: p['slack'])
    for f in sorted(run.rglob('*')):
        if f.is_file() and f.suffix.lower() in ('.vcd', '.fst', '.gds', '.def', '.odb', '.lef', '.spef', '.spice', '.rpt', '.lyrdb', '.png', '.sdc', '.lib'):
            summary['artifacts'].append(str(f.relative_to(run)))
    (run / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return summary
