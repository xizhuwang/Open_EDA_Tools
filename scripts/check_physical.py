"""A separate acceptance gate: no silent zero defaults or fake physical result."""
import json
from pathlib import Path
import sys

project = Path(sys.argv[1]).resolve()
history = project.parent / '.runs'
run = history / json.loads((history / 'latest.json').read_text())['run']
manifest = json.loads((run / 'manifest.json').read_text())
summary = json.loads((run / 'summary.json').read_text())
assert manifest['status'] == 'completed', manifest
assert summary['physical_checks'] == {'magic_drc': 0, 'lvs': 0}, summary['physical_checks']
for ext in ('.gds', '.odb', '.def', '.spef'):
    assert any(run.rglob('*' + ext)), 'Missing real artifact ' + ext
assert summary['paths'], 'No real timing paths parsed'
print('PASS: actual GDS / ODB / DEF / SPEF, STA paths, zero Magic DRC and zero LVS errors')
