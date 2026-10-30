import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_project(filename):
    filename = Path(filename).resolve()
    data = json.loads(filename.read_text(encoding='utf-8'))
    base = filename.parent
    for key in ('top', 'testbench_top', 'clock'):
        if not IDENT.fullmatch(data.get(key, '')):
            raise ValueError(f'{key} must be a simple Verilog identifier')
    period = data.get('clock_period_ns')
    if isinstance(period, bool) or not isinstance(period, (int, float)) or not 0.01 <= period <= 100000:
        raise ValueError('clock_period_ns must be between 0.01 and 100000')
    for key in ('rtl', 'testbench', 'support_files'):
        files = data.get(key, [])
        if not isinstance(files, list) or any(not isinstance(f, str) for f in files):
            raise ValueError(f'{key} must be a list of filenames')
        if key != 'support_files' and not files:
            raise ValueError(f'{key} cannot be empty')
        for name in files:
            checked_file(base, name)
    checked_file(base, data['sdc'])
    data['file'] = str(filename)
    data['base'] = str(base)
    return data


def checked_file(base, name):
    if not isinstance(name, str) or Path(name).is_absolute():
        raise ValueError('Project filenames must be relative')
    path = (Path(base) / name).resolve()
    if not path.is_relative_to(Path(base).resolve()) or not path.is_file():
        raise ValueError(f'Missing file, symlink escape or path outside project: {name}')
    if any(c in name for c in ('\n', '\r', '"', '\\')):
        raise ValueError('Unsupported filename character')
    return path


def snapshot(project, run):
    dest = run / 'input'
    dest.mkdir()
    names = set(project['rtl'] + project['testbench'] + project.get('support_files', []) + [project['sdc']])
    hashes = {}
    for name in sorted(names):
        source = checked_file(project['base'], name)
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        hashes[name] = digest(target)
    public = {k: v for k, v in project.items() if k not in ('base', 'file')}
    (dest / 'project.json').write_text(json.dumps(public, indent=2, ensure_ascii=False), encoding='utf-8')
    return dest, hashes


def flow_config(project, source):
    config = {
        'DESIGN_NAME': project['top'],
        'VERILOG_FILES': [str(source / f) for f in project['rtl']],
        'VERILOG_INCLUDE_DIRS': [str(source)],
        'CLOCK_PORT': project['clock'],
        'CLOCK_PERIOD': project['clock_period_ns'],
        'PNR_SDC_FILE': str(source / project['sdc']),
        'SIGNOFF_SDC_FILE': str(source / project['sdc']),
        'FP_SIZING': 'absolute',
        'DIE_AREA': [0, 0, 120, 120],
        'FP_CORE_UTIL': 35,
        'PL_TARGET_DENSITY_PCT': 45,
        'PDN_VPITCH': 30,
        'PDN_HPITCH': 30,
        'PDN_VOFFSET': 5,
        'PDN_HOFFSET': 5,
        'RUN_MAGIC_DRC': True,
        'RUN_LVS': True,
        # KLayout DRC availability depends on the PDK. Magic DRC is required.
        'RUN_KLAYOUT_DRC': False,
    }
    extra = project.get('physical', {})
    if not isinstance(extra, dict):
        raise ValueError('physical must be a LibreLane configuration object')
    protected = {'DESIGN_NAME', 'VERILOG_FILES', 'CLOCK_PORT', 'CLOCK_PERIOD', 'PNR_SDC_FILE', 'SIGNOFF_SDC_FILE', 'RUN_MAGIC_DRC', 'RUN_LVS'}
    if protected & extra.keys():
        raise ValueError(f'Protected flow keys: {sorted(protected & extra.keys())}')
    config.update(extra)
    return config
