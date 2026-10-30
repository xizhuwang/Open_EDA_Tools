"""Prepare a Tiny Tapeout handoff; never infer manufacturing acceptance."""
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from .project import ROOT, checked_file, digest


def profile():
    return json.loads((ROOT / 'profiles/tinytapeout-sky.json').read_text())


def inspect_ports(netlist, top, pdk='sky130A'):
    rules = profile()
    errors = []
    if not top.startswith('tt_um_'):
        errors.append('Top module must start with tt_um_.')
    if pdk != rules['pdk']:
        errors.append('This reviewed handoff profile targets SKY130A only.')
    ports = netlist['modules'][top]['ports']
    expected = rules['ports']
    if set(ports) != set(expected):
        errors.append(f'Port set differs. Missing: {sorted(set(expected)-set(ports))}; extra: {sorted(set(ports)-set(expected))}')
    for name, (direction, width) in expected.items():
        if name in ports and (ports[name]['direction'] != direction or len(ports[name]['bits']) != width):
            errors.append(f'{name}: expected {direction} [{width}]')
    return {'interface_ok': not errors, 'errors': errors, 'official_precheck': 'NOT RUN',
            'manufacturing_accepted': False, 'scope': rules['scope'],
            'remaining': ['Functional verification and gate-level simulation', 'Correct shuttle / tool / PDK revision',
                          'Official tile dimensions, pin placement, timing, DRC/LVS and precheck',
                          'Documentation, IP permissions, price/kit/shipping selection and provider acceptance']}


def export(project, output, author='', title='Open EDA counter'):
    """Export only the validated example/profile, not an arbitrary unwrapped ASIC."""
    rules = profile()
    settings = project.get('tapeout', {})
    if settings.get('provider') != 'tinytapeout' or project['top'] != 'tt_um_openeda_counter':
        raise ValueError('This initial exporter is for the counter example. Custom designs need their own wrapper, test and docs; do not relabel the counter tests.')
    if settings.get('tiles', '1x1') not in rules['tiles']:
        raise ValueError('Unsupported tile count for this reviewed SKY template')
    if project.get('support_files'):
        raise ValueError('This minimal exporter does not remap include/macro support files; use the official template manually.')
    names = [Path(name).name for name in project['rtl']]
    if len(set(names)) != len(names):
        raise ValueError('RTL basenames must be unique when exported into src/.')
    out = Path(output).resolve()
    if out.exists():
        raise ValueError('Output already exists. Choose a new directory; existing designs are never overwritten.')
    # git archive preserves upstream LICENSE and excludes its Git credentials/state.
    with tempfile.TemporaryDirectory(prefix='open-eda-tt-') as tmp:
        repo = Path(tmp) / 'template'
        subprocess.run(['git', 'clone', '--quiet', '--no-checkout', rules['template_url'], str(repo)], check=True, timeout=180)
        archive = Path(tmp) / 'template.tar'
        with archive.open('wb') as stream:
            subprocess.run(['git', '-C', str(repo), 'archive', rules['template_commit']], stdout=stream, check=True)
        out.mkdir(parents=True)
        with tarfile.open(archive) as tar:
            tar.extractall(out, filter='data')
    hashes = {}
    for name in project['rtl']:
        source = checked_file(project['base'], name)
        shutil.copy2(source, out / 'src' / Path(name).name)
        hashes['src/' + Path(name).name] = digest(source)
    config = json.loads((out / 'src/config.json').read_text())
    config['CLOCK_PERIOD'] = project['clock_period_ns']
    (out / 'src/config.json').write_text(json.dumps(config, indent=2))
    pins = {f'{kind}[{i}]': '' for kind in ('ui', 'uo', 'uio') for i in range(8)}
    pins.update({'ui[0]': 'count_enable', 'ui[1]': 'clear_counter'})
    pins.update({f'uo[{i}]': f'count[{i}]' for i in range(8)})
    info = {'project': {'title': title, 'author': author, 'discord': '',
                       'description': 'Counter with enable, clear and non-driving bidirectional IO',
                       'language': 'Verilog', 'clock_hz': round(1e9 / project['clock_period_ns']),
                       'tiles': settings.get('tiles', '1x1'), 'top_module': project['top'], 'source_files': names},
            'pinout': pins, 'yaml_version': 6}
    # JSON is a YAML subset; official safe_load accepts this without PyYAML here.
    (out / 'info.yaml').write_text(json.dumps(info, indent=2, ensure_ascii=False))
    tb = out / 'test/tb.v'
    tb.write_text(tb.read_text().replace('tt_um_example', project['top']))
    make = out / 'test/Makefile'
    make.write_text(make.read_text().replace('PROJECT_SOURCES = project.v', 'PROJECT_SOURCES = ' + ' '.join(names)))
    shutil.copy2(ROOT / 'profiles/tt-counter-cocotb.py', out / 'test/test.py')
    docs = ('## How it works\n\n8-bit wrapping counter; ui[0] enables counting and ui[1] synchronously clears it. '
            'ena gates updates; rst_n asynchronously clears the counter. uo[7:0] shows count. '
            'uio_oe and uio_out are zero (input-only).\n\n## How to test\n\nAssert reset, release with stable clock, '
            'enable ui[0], and observe the count at uo[7:0]. ui[1] clears; disable ui[0] to hold. '
            'Run the RTL and gate-level test before submission.\n\n## External hardware\n\nTiny Tapeout demo/breakout hardware as specified by the shuttle.\n')
    (out / 'docs/info.md').write_text(docs)
    shutil.copy2(ROOT / 'LICENSE', out / 'LICENSE-OPEN-EDA')
    manifest = {'profile': rules, 'source_sha256': hashes, 'official_precheck': 'NOT RUN',
                'status': 'PREPARATION ONLY — not a manufacturing acceptance certificate'}
    (out / 'OPEN_EDA_HANDOFF.json').write_text(json.dumps(manifest, indent=2))
    return out
