#!/usr/bin/env python3
"""Public-demo candidate: scripted ACO through a fully SIMULATED stack.

Python 3.8+, standard library only:
    python3 aco_simulated_stack.py
    python3 aco_simulated_stack.py --json
    python3 aco_simulated_stack.py --self-test

DEMO-ONLY interfaces, invented here; not vendor APIs or production schemas.
MockZetaRuntime calls MockHorizonAX (assurance), MockCLEAR (decision review),
MockATLAS (disputed release request), and MockKRISHNA (execution gating).
No production source, SDKs, network, credentials, external data, or file writes.
All timing/area values are synthetic. This is not silicon signoff or an AI
agent. ACO means Agentic Change Order; its proposal is scripted in this demo.

The public lesson is the interaction: green partial checks do not authorize
release. The implementation is a fixed checklist, not proprietary reasoning.
Names identify proposed integration roles, not endorsement or availability.
The displayed history is ordinary mutable memory, NOT tamper-evident evidence.

Ouroboros Zeta educational demo.
Copyright (c) 2026 Quantum Generative Materials LLC.
SPDX-License-Identifier: MIT
See the accompanying LICENSE. No production implementation is included.
Conceptual ACO contribution: Niraj Prasad of Caminosoft; see README.md.
"""
import argparse
import json

REQUIRED = ('arithmetic', 'nominal_timing', 'slow_timing')
CLOCK_PS = 1000


def ripple_add(a, b):
    result = carry = 0
    for bit in range(8):
        x, y = (a >> bit) & 1, (b >> bit) & 1
        result |= (x ^ y ^ carry) << bit
        carry = (x & y) | (carry & (x ^ y))
    return result


def verify(design, reveal_slow):
    """Synthetic engineering checks, separate from the mock assurance layer."""
    checks = {'arithmetic': all(ripple_add(a, b) == ((a + b) & 255)
                               for a in range(256) for b in range(256))}
    slack = {'nominal': CLOCK_PS - 8 * design['stage_ps']}
    checks['nominal_timing'] = slack['nominal'] >= 0
    if reveal_slow:
        slack['slow'] = CLOCK_PS - 8 * design['stage_ps'] * 2
        checks['slow_timing'] = slack['slow'] >= 0
    return {'checks': checks, 'slack_ps': slack}


class MockHorizonAX:
    def assure(self, engineering):
        checks = engineering['checks']
        missing = [k for k in REQUIRED if k not in checks]
        failed = [k for k in REQUIRED if k in checks and checks[k] is not True]
        return {'missing': missing, 'failed': failed,
                'status': 'FAIL' if failed else 'INCOMPLETE' if missing else 'PASS'}


class MockCLEAR:
    def review(self, assurance):
        return {'recommendation': 'TOY_RELEASE' if assurance['status'] == 'PASS' else 'HOLD',
                'reason': 'Required toy checks satisfied.' if assurance['status'] == 'PASS'
                else 'Available PASS results do not satisfy the release checklist.'}


class MockATLAS:
    def resolve(self, request, review, assurance):
        # A scripted dispute rule, not a general adjudication algorithm.
        disputed = request != review['recommendation']
        return {'disputed': disputed,
                'disposition': review['recommendation'],
                'reason': ('Release request cannot waive missing or failed checks.'
                           if disputed else 'No disagreement to resolve.'),
                'outstanding': assurance['missing'] + assurance['failed']}


class MockKRISHNA:
    def execute(self, disposition, assurance, permit_local_release):
        # Defense in depth for this toy: a request or verdict alone is insufficient.
        allowed = (permit_local_release and disposition == 'TOY_RELEASE'
                   and assurance['status'] == 'PASS'
                   and not assurance['missing'] and not assurance['failed'])
        return {'action': 'TOY_RELEASE' if allowed else 'HOLD',
                'scope': 'Local simulation flag only; no physical or external action.'}


class MockZetaRuntime:
    """Toy coordinator. Every named service below is a local mock."""
    def __init__(self):
        self.horizonax = MockHorizonAX()
        self.clear = MockCLEAR()
        self.atlas = MockATLAS()
        self.krishna = MockKRISHNA()
        self.history = []

    def record(self, component, method, result):
        event = {'sequence': len(self.history), 'simulation': True,
                 'component': component, 'method': method, 'result': result}
        # Snapshot prevents accidental aliasing; provides no tamper protection.
        self.history.append(json.loads(json.dumps(event)))
        return result

    def run(self, label, design, reveal_slow=False, permit_local_release=True):
        self.record('ZETA', 'begin', {'scenario': label, 'design': design})
        engineering = self.record('VERIFIER', 'check', verify(design, reveal_slow))
        assurance = self.record('HORIZONAX', 'assure', self.horizonax.assure(engineering))
        review = self.record('CLEAR', 'review', self.clear.review(assurance))
        # Naive requester asks to release if all currently available checks are green.
        request = 'TOY_RELEASE' if all(engineering['checks'].values()) else 'HOLD'
        resolution = self.record('ATLAS', 'resolve',
                                 self.atlas.resolve(request, review, assurance))
        execution = self.record('KRISHNA', 'execute', self.krishna.execute(
            resolution['disposition'], assurance, permit_local_release))
        self.record('ZETA', 'finish', {'scenario': label, 'action': execution['action']})
        return {'scenario': label, 'requested': request, 'engineering': engineering,
                'assurance': assurance, 'review': review, 'resolution': resolution,
                'execution': execution}


def demo():
    runtime = MockZetaRuntime()
    eco = {'name': 'smaller_adder_cells', 'toy_area': 75, 'stage_ps': 70}
    original = {'name': 'original_cells', 'toy_area': 100, 'stage_ps': 50}
    first = runtime.run('ECO: slow corner withheld', eco)
    prefix = json.dumps(runtime.history, sort_keys=True)
    prefix_len = len(runtime.history)
    later = runtime.run('ECO: slow corner revealed', eco, reveal_slow=True)
    good = runtime.run('Original design: complete evidence', original, reveal_slow=True)
    unpermitted = runtime.run('Original design: no local release permission', original,
                             reveal_slow=True, permit_local_release=False)
    assert json.dumps(runtime.history[:prefix_len], sort_keys=True) == prefix
    return runtime, [first, later, good, unpermitted]


def self_test(runtime, scenarios):
    first, later, good, unpermitted = scenarios
    assert all(first['engineering']['checks'].values())
    assert first['requested'] == 'TOY_RELEASE'
    assert first['resolution']['disputed'] and first['execution']['action'] == 'HOLD'
    assert first['assurance']['missing'] == ['slow_timing']
    assert later['assurance']['failed'] == ['slow_timing']
    assert later['engineering']['slack_ps']['slow'] == -120
    assert later['execution']['action'] == 'HOLD'
    assert good['execution']['action'] == 'TOY_RELEASE'
    assert unpermitted['execution']['action'] == 'HOLD'
    # Even a directly supplied release disposition cannot bypass incomplete assurance.
    assert runtime.krishna.execute('TOY_RELEASE', first['assurance'], True)['action'] == 'HOLD'
    required_order = ['ZETA', 'VERIFIER', 'HORIZONAX', 'CLEAR', 'ATLAS', 'KRISHNA', 'ZETA']
    for offset in range(0, len(runtime.history), 7):
        assert [e['component'] for e in runtime.history[offset:offset + 7]] == required_order


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Print simulated call history')
    parser.add_argument('--self-test', action='store_true', help='Check scenarios and gate bypass')
    args = parser.parse_args()
    runtime, scenarios = demo()
    self_test(runtime, scenarios)
    if args.json:
        print(json.dumps({'simulation': True, 'scenarios': scenarios,
                          'history': runtime.history}, indent=2))
    elif args.self_test:
        print('PASS: missing evidence, revealed failure, good control, denied permission,')
        print('direct gate bypass, call order, and preservation of earlier snapshots.')
    else:
        print('ACO DEMO -- ALL NAMED SYSTEMS ARE LOCAL MOCKS\n')
        print('Toy Zeta orchestrates HorizonAX -> CLEAR -> ATLAS -> KRISHNA.')
        print('Scripted proposal: reduce modeled adder area from 100 to 75 (-25%).')
        for s in scenarios:
            print('\n' + s['scenario'])
            print('  [SIM] Checks: ' + json.dumps(s['engineering']['checks']))
            print('  [SIM] Slack (ps): ' + json.dumps(s['engineering']['slack_ps']))
            print('  [SIM] HorizonAX assurance: ' + s['assurance']['status'])
            print('  [SIM] CLEAR recommendation: ' + s['review']['recommendation'])
            print('  [SIM] ATLAS: ' + s['resolution']['reason'])
            print('  [SIM] KRISHNA action: ' + s['execution']['action'])
            print('  [SIM] Zeta recorded the local outcome.')
        print('\nNo production integration, real signoff, or tamper-proof log is demonstrated.')
        print('Use --json to inspect every simulated call. Use --self-test to verify controls.')


if __name__ == '__main__':
    main()
