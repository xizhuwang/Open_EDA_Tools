"""Conservative, flattened netlist clock-crossing review. NOT CDC sign-off."""
from collections import defaultdict


def review(netlist, top):
    module = netlist['modules'][top]
    cells = module.get('cells', {})
    bits_to_name = {}
    for name, net in module.get('netnames', {}).items():
        for index, bit in enumerate(net['bits']):
            if isinstance(bit, int):
                bits_to_name.setdefault(bit, f'{name}[{index}]' if len(net['bits']) > 1 else name)
    ff = {}
    drivers = defaultdict(list)
    findings = []
    for name, cell in cells.items():
        ports = cell.get('connections', {})
        kind = cell['type'].lower()
        directions = cell.get('port_directions', {})
        if 'latch' in kind:
            findings.append({'kind': 'latch', 'cell': name, 'detail': 'Level-sensitive storage inferred; review intent and timing.'})
        if ('dff' in kind or kind in ('$ff',)) and 'D' in ports and 'Q' in ports:
            clock = tuple(ports.get('CLK', ports.get('C', [])))
            ff[name] = {'clock': clock, 'd': ports['D'], 'q': ports['Q'], 'src': cell.get('attributes', {}).get('src', '')}
        for port, bits in ports.items():
            if directions.get(port) == 'output':
                for bit in bits:
                    if isinstance(bit, int):
                        drivers[bit].append(name)
    qowner = {}
    for name, f in ff.items():
        for bit in f['q']:
            qowner[bit] = name

    def sources(bit, visited):
        if bit in qowner:
            return {qowner[bit]}
        if bit in visited:
            return set()
        visited = visited | {bit}
        result = set()
        for driver in drivers.get(bit, []):
            cell = cells[driver]
            for port, direction in cell.get('port_directions', {}).items():
                if direction == 'input':
                    for ibit in cell['connections'][port]:
                        result |= sources(ibit, visited)
        return result

    for target, t in ff.items():
        srcs = set()
        for bit in t['d']:
            srcs |= sources(bit, set())
        for source in sorted(srcs):
            s = ff[source]
            if s['clock'] == t['clock']:
                continue
            second_stages = [name for name, f in ff.items() if name != target and f['clock'] == t['clock']
                             and len(f['d']) == len(t['q']) and f['d'] == t['q']]
            direct = all(bit in s['q'] for bit in t['d'])
            width = len(t['d'])
            finding = {
                'kind': 'clock_crossing', 'source': source, 'destination': target,
                'source_clock': [bits_to_name.get(b, str(b)) for b in s['clock']],
                'destination_clock': [bits_to_name.get(b, str(b)) for b in t['clock']],
                'source_location': s['src'], 'destination_location': t['src'],
                'width': width, 'direct': direct, 'second_stage_candidates': second_stages,
                'detail': 'UNREVIEWED CDC: topology alone cannot prove pulse capture, coherency, handshake or reset safety.',
            }
            if second_stages and direct and width == 1:
                finding['detail'] = '2FF topology candidate only. Review first-stage fanout, async_reg, MTBF, pulse width, reset and physical constraints.'
            elif width > 1:
                finding['detail'] = 'Multi-bit crossing: even 2FF per bit does not establish bus coherency. Review Gray constraints / handshake / async FIFO.'
            findings.append(finding)
    return {'method': 'Yosys flattened DFF/clock/data-cone review', 'signoff': False,
            'limitations': ['Clock relationships, generated clocks, CDC protocols, reset release and MTBF are not formally proven.',
                            'Input-port crossings, memories, latches and black-box internals require manual review.',
                            'No findings is not evidence that the design is CDC-clean.'],
            'register_groups': len(ff), 'findings': findings}
