#!/usr/bin/env python3
"""Public-demo candidate: scripted ACO through a fully SIMULATED stack.

Python 3.8+, standard library only:
    python3 aco_simulated_stack.py
    python3 aco_simulated_stack.py --json
    python3 aco_simulated_stack.py --self-test
    python3 aco_simulated_stack.py --examples

DEMO-ONLY interfaces, invented here; not vendor APIs or production schemas.
MockZetaRuntime calls MockHorizonAX (assurance), MockCLEAR (decision review),
MockATLAS (dispute only when one exists), and MockKRISHNA (execution gating).
No production source, SDKs, network, credentials, external data, or file writes
during normal demo execution (example JSON is read-only input).

ACO exchange v1 makes the interoperability contract explicit:
    versioned ACO object -> same mock workflow -> versioned disposition

All timing/area/CDC/FIFO values are synthetic. This is not silicon signoff or an
AI agent. ACO means Agentic Change Order.

The public lesson is the interaction: green partial checks do not authorize
release; fixing one finding does not prove the change is acceptable; verification
PASS is not the same as meeting a stated engineering objective.

Ouroboros Zeta educational demo.
Copyright (c) 2026 Quantum Generative Materials LLC.
SPDX-License-Identifier: MIT
See the accompanying LICENSE. No production implementation is included.
Conceptual ACO contribution: Niraj Prasad of Caminosoft; see README.md.
"""
import argparse
import json
import os

REQUIRED = ('arithmetic', 'nominal_timing', 'slow_timing')
CLOCK_PS = 1000
SCHEMA_VERSION = '1.0'
HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(HERE, 'examples')
EXAMPLE_FILES = (
    'cdc_fifo_pass.json',
    'cdc_fifo_hold.json',
    'area_goal_hold.json',
)

# Minimal stdlib checks against the documented ACO exchange v1 contract.
# Formal JSON Schema validation would need a dependency; this is intentional.
TOP_LEVEL_REQUIRED = (
    'schema_version', 'aco_id', 'source', 'subject', 'proposed_change',
    'stated_objective', 'acceptance_criteria', 'acceptance_status', 'evidence',
    'horizonax_assurance', 'clear_review', 'atlas_dispute', 'execution_gate',
    'zeta_transition',
)
CRITERION_STATUS = frozenset(
    {'SATISFIED', 'NOT_SATISFIED', 'NOT_EVALUATED', 'BLOCKED'})
ACCEPTANCE_STATUS = frozenset(
    {'SATISFIED', 'NOT_SATISFIED', 'PARTIAL', 'BLOCKED'})
CLEAR_DISPOSITION = frozenset(
    {'NOT_RUN', 'APPROVED', 'CHANGES_REQUIRED', 'REJECTED', 'CONDITIONAL'})
ATLAS_STATUS = frozenset({'NONE', 'OPEN', 'RESOLVED'})
GATE_DISPOSITION = frozenset({'PASS', 'HOLD', 'DENY', 'NOT_RUN'})
FAIL_LIKE = frozenset({
    'FAIL', 'PROPERTY_VIOLATED', 'NOT_SATISFIED', 'REJECTED'})
INCOMPLETE_LIKE = frozenset({
    'INCOMPLETE', 'NOT_RUN', 'NOT_EVALUATED', 'BLOCKED', 'MISSING',
    'INCONCLUSIVE', 'UNSUPPORTED', 'STALE'})


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


def area_objective_met(design, target=70):
    """Stated area objective is separate from arithmetic/timing verification."""
    return design.get('toy_area', 10 ** 9) <= target


class MockHorizonAX:
    def assure(self, engineering, required=REQUIRED):
        checks = engineering['checks']
        missing = [k for k in required if k not in checks]
        failed = [k for k in required if k in checks and checks[k] is not True]
        return {'missing': missing, 'failed': failed,
                'status': 'FAIL' if failed else 'INCOMPLETE' if missing else 'PASS'}

    def assure_from_packet(self, packet):
        """Read HorizonAX posture from the exchange packet; do not invent PASS."""
        checks = list(packet.get('horizonax_assurance', {}).get('checks') or [])
        criteria = packet.get('acceptance_criteria') or []
        failed = []
        missing = []
        for check in checks:
            status = str(check.get('status', '')).upper()
            name = check.get('check') or check.get('name') or 'check'
            if status in FAIL_LIKE:
                failed.append(name)
            elif status in INCOMPLETE_LIKE:
                missing.append(name)
        for criterion in criteria:
            if not criterion.get('required'):
                continue
            status = criterion.get('status')
            cid = criterion.get('criterion_id', 'criterion')
            if status == 'NOT_SATISFIED':
                if cid not in failed:
                    failed.append(cid)
            elif status in ('NOT_EVALUATED', 'BLOCKED'):
                if cid not in missing:
                    missing.append(cid)
        if failed:
            status = 'FAIL'
        elif missing:
            status = 'INCOMPLETE'
        else:
            status = 'PASS'
        return {
            'missing': missing,
            'failed': failed,
            'status': status,
            'summary': packet.get('horizonax_assurance', {}).get('summary', ''),
            'checks': checks,
        }


class MockCLEAR:
    def review(self, assurance, reason_codes=None):
        if assurance['status'] == 'PASS':
            return {'required': True, 'decision_id': 'clear-demo-approved',
                    'disposition': 'APPROVED',
                    'reason_codes': reason_codes or ['REQUIRED_EVIDENCE_SATISFIED'],
                    'reason': 'Required toy checks satisfied.'}
        codes = list(reason_codes or [])
        if assurance.get('failed'):
            if 'REQUIRED_PROPERTY_VIOLATED' not in codes and not codes:
                codes.append('REQUIRED_CHECK_FAILED')
        if assurance.get('missing'):
            if 'MISSING_REQUIRED_EVIDENCE' not in codes:
                codes.append('MISSING_REQUIRED_EVIDENCE')
        if not codes:
            codes = ['ACCEPTANCE_CRITERIA_NOT_SATISFIED']
        return {'required': True, 'decision_id': 'clear-demo-hold',
                'disposition': 'CHANGES_REQUIRED',
                'reason_codes': codes,
                'reason': 'Available PASS results do not satisfy the release checklist.'}


class MockATLAS:
    def resolve(self, request, review, assurance):
        # Invoked only when a dispute exists; not a mandatory happy-path step.
        disputed = request != review['disposition']
        disposition = review['disposition']
        return {'required': disputed, 'status': 'RESOLVED' if disputed else 'NONE',
                'disputed': disputed,
                'disposition': disposition,
                'resolution_id': 'atlas-demo-001' if disputed else None,
                'resolution': ('Release request cannot waive missing or failed checks.'
                              if disputed else None),
                'reason': ('Release request cannot waive missing or failed checks.'
                           if disputed else 'No disagreement to resolve.'),
                'outstanding': assurance['missing'] + assurance['failed']}


class MockKRISHNA:
    def execute(self, disposition, assurance, permit_local_release, reason_codes=None):
        # Defense in depth for this toy: a request or verdict alone is insufficient.
        clear_ok = disposition == 'APPROVED'
        assurance_ok = (assurance['status'] == 'PASS'
                        and not assurance['missing'] and not assurance['failed'])
        allowed = permit_local_release and clear_ok and assurance_ok
        codes = list(reason_codes or [])
        if allowed:
            if not codes:
                codes = ['CLEAR_APPROVED', 'REQUIRED_EVIDENCE_CURRENT',
                         'ACCEPTANCE_CRITERIA_SATISFIED']
            return {'actor': 'KRISHNA', 'disposition': 'PASS',
                    'action': 'PASS', 'reason_codes': codes,
                    'authorization_id': 'krishna-auth-demo',
                    'scope': 'Local simulation flag only; no physical or external action.'}
        if assurance.get('failed'):
            failed = assurance['failed']
            if (any('overflow' in str(x) or str(x).startswith('ac-fifo')
                    or str(x).startswith('fifo_') for x in failed)
                    and 'REQUIRED_PROPERTY_VIOLATED' not in codes):
                codes.append('REQUIRED_PROPERTY_VIOLATED')
            elif (any('area' in str(x) or str(x).startswith('ac-area')
                      or 'toy_area' in str(x) for x in failed)
                  and 'REQUIRED_OBJECTIVE_NOT_MET' not in codes):
                codes.append('REQUIRED_OBJECTIVE_NOT_MET')
            elif ('REQUIRED_CHECK_FAILED' not in codes
                  and 'REQUIRED_PROPERTY_VIOLATED' not in codes
                  and 'REQUIRED_OBJECTIVE_NOT_MET' not in codes):
                codes.append('REQUIRED_CHECK_FAILED')
        if assurance.get('missing') and 'MISSING_REQUIRED_EVIDENCE' not in codes:
            codes.append('MISSING_REQUIRED_EVIDENCE')
        if not clear_ok and 'ACCEPTANCE_CRITERIA_NOT_SATISFIED' not in codes:
            codes.append('ACCEPTANCE_CRITERIA_NOT_SATISFIED')
        if not permit_local_release and 'LOCAL_PERMISSION_DENIED' not in codes:
            codes.append('LOCAL_PERMISSION_DENIED')
        if not codes:
            codes = ['HOLD']
        # Preserve order while dropping accidental duplicates.
        deduped = []
        seen = set()
        for code in codes:
            if code not in seen:
                seen.add(code)
                deduped.append(code)
        codes = deduped
        return {'actor': 'KRISHNA', 'disposition': 'HOLD',
                'action': 'HOLD', 'reason_codes': codes,
                'authorization_id': None,
                'scope': 'Local simulation flag only; no physical or external action.'}


def acceptance_status_from_criteria(criteria):
    required = [c for c in criteria if c.get('required')]
    if not required:
        return 'SATISFIED'
    statuses = [c.get('status') for c in required]
    if any(s == 'NOT_SATISFIED' for s in statuses):
        return 'NOT_SATISFIED'
    if any(s in ('NOT_EVALUATED', 'BLOCKED') for s in statuses):
        return 'BLOCKED' if any(s == 'BLOCKED' for s in statuses) else 'PARTIAL'
    if all(s == 'SATISFIED' for s in statuses):
        return 'SATISFIED'
    return 'PARTIAL'


def validate_aco_packet(packet):
    """Deterministic structural checks; not a full JSON Schema engine."""
    errors = []
    if not isinstance(packet, dict):
        return ['packet must be an object']
    for key in TOP_LEVEL_REQUIRED:
        if key not in packet:
            errors.append('missing:/' + key)
    if packet.get('schema_version') != SCHEMA_VERSION:
        errors.append('schema_version must be %s' % SCHEMA_VERSION)
    source = packet.get('source') or {}
    if source.get('system') != 'HorizonAX':
        errors.append('source.system must be HorizonAX')
    for field in ('project_id', 'case_id', 'run_id'):
        if not source.get(field):
            errors.append('missing:/source/' + field)
    criteria = packet.get('acceptance_criteria')
    if not isinstance(criteria, list):
        errors.append('acceptance_criteria must be an array')
    else:
        for i, criterion in enumerate(criteria):
            if not isinstance(criterion, dict):
                errors.append('acceptance_criteria/%d must be an object' % i)
                continue
            for req in ('criterion_id', 'type', 'required', 'status'):
                if req not in criterion:
                    errors.append('missing:/acceptance_criteria/%d/%s' % (i, req))
            if criterion.get('status') not in CRITERION_STATUS:
                errors.append('bad:/acceptance_criteria/%d/status' % i)
    if packet.get('acceptance_status') not in ACCEPTANCE_STATUS:
        errors.append('bad:/acceptance_status')
    evidence = packet.get('evidence')
    if not isinstance(evidence, list):
        errors.append('evidence must be an array')
    else:
        for i, item in enumerate(evidence):
            for req in ('evidence_id', 'kind', 'status', 'freshness',
                        'fingerprint', 'uri'):
                if not isinstance(item, dict) or req not in item:
                    errors.append('missing:/evidence/%d/%s' % (i, req))
    clear = packet.get('clear_review') or {}
    if clear.get('disposition') not in CLEAR_DISPOSITION:
        errors.append('bad:/clear_review/disposition')
    atlas = packet.get('atlas_dispute') or {}
    if atlas.get('status') not in ATLAS_STATUS:
        errors.append('bad:/atlas_dispute/status')
    gate = packet.get('execution_gate') or {}
    if gate.get('actor') != 'KRISHNA':
        errors.append('execution_gate.actor must be KRISHNA')
    if gate.get('disposition') not in GATE_DISPOSITION:
        errors.append('bad:/execution_gate/disposition')
    return errors


def load_example(name):
    path = os.path.join(EXAMPLES_DIR, name)
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


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

    def run(self, label, design, reveal_slow=False, permit_local_release=True,
            require_area=False, area_target=70):
        """Existing adder demonstration path, now emitting ACO v1 dispositions."""
        self.record('ZETA', 'begin', {'scenario': label, 'design': design})
        engineering = self.record('VERIFIER', 'check', verify(design, reveal_slow))
        required = list(REQUIRED)
        if require_area:
            engineering['checks']['area_objective'] = area_objective_met(
                design, area_target)
            required = list(REQUIRED) + ['area_objective']
        assurance = self.record('HORIZONAX', 'assure',
                                self.horizonax.assure(engineering, required))
        reason_codes = []
        if 'area_objective' in assurance['failed']:
            reason_codes.append('REQUIRED_OBJECTIVE_NOT_MET')
        if 'slow_timing' in assurance['missing']:
            reason_codes.append('MISSING_REQUIRED_EVIDENCE')
        if 'slow_timing' in assurance['failed']:
            reason_codes.append('REQUIRED_CHECK_FAILED')
        review = self.record('CLEAR', 'review',
                              self.clear.review(assurance, reason_codes))
        # Naive requester asks to approve if all currently available checks are green.
        request = 'APPROVED' if all(engineering['checks'].values()) else 'CHANGES_REQUIRED'
        if request != review['disposition']:
            resolution = self.record('ATLAS', 'resolve',
                                      self.atlas.resolve(request, review, assurance))
            atlas_invoked = True
        else:
            resolution = self.record(
                'ATLAS', 'skip',
                {'required': False, 'status': 'NONE', 'disputed': False,
                 'disposition': review['disposition'], 'resolution_id': None,
                 'resolution': None, 'reason': 'No dispute; ATLAS not invoked.',
                 'outstanding': []})
            atlas_invoked = False
        execution = self.record('KRISHNA', 'execute', self.krishna.execute(
            resolution['disposition'], assurance, permit_local_release, reason_codes))
        aco = self._adder_aco(label, design, engineering, assurance, review,
                              resolution, execution, reveal_slow, require_area,
                              area_target)
        transition = {'from_state': 'KRISHNA_GATE',
                      'to_state': 'AUTHORIZED' if execution['disposition'] == 'PASS'
                      else 'HOLD',
                      'record_status': 'RECORDED'}
        self.record('ZETA', 'finish', {'scenario': label,
                                       'action': execution['disposition'],
                                       'aco_id': aco['aco_id'],
                                       'zeta_transition': transition})
        return {'scenario': label, 'requested': request, 'engineering': engineering,
                'assurance': assurance, 'review': review, 'resolution': resolution,
                'atlas_invoked': atlas_invoked, 'execution': execution, 'aco': aco}

    def run_packet(self, packet, permit_local_release=True, naive_request=None):
        """Drive the same mocks from a versioned ACO exchange v1 object."""
        errors = validate_aco_packet(packet)
        if errors:
            raise ValueError('Invalid ACO packet: ' + '; '.join(errors))
        label = packet['aco_id']
        self.record('ZETA', 'begin', {'scenario': label, 'aco_id': label})
        derived_status = acceptance_status_from_criteria(packet['acceptance_criteria'])
        assurance = self.record('HORIZONAX', 'assure',
                                self.horizonax.assure_from_packet(packet))
        reason_codes = []
        for criterion in packet['acceptance_criteria']:
            if not criterion.get('required'):
                continue
            if criterion.get('status') == 'NOT_SATISFIED':
                ctype = criterion.get('type', '')
                if ctype in ('PROPERTY_STATUS', 'PROPERTY_SET'):
                    reason_codes.append('REQUIRED_PROPERTY_VIOLATED')
                elif ctype == 'OBJECTIVE_THRESHOLD':
                    reason_codes.append('REQUIRED_OBJECTIVE_NOT_MET')
                else:
                    reason_codes.append('REQUIRED_CHECK_FAILED')
            elif criterion.get('status') in ('NOT_EVALUATED', 'BLOCKED'):
                reason_codes.append('MISSING_REQUIRED_EVIDENCE')
        # Deduplicate while preserving order.
        seen = set()
        reason_codes = [c for c in reason_codes
                        if not (c in seen or seen.add(c))]
        review = self.record('CLEAR', 'review',
                              self.clear.review(assurance, reason_codes))
        if naive_request is None:
            # Happy-path packets do not invent a conflicting release request.
            request = review['disposition']
        else:
            request = naive_request
        if request != review['disposition']:
            resolution = self.record('ATLAS', 'resolve',
                                      self.atlas.resolve(request, review, assurance))
            atlas_invoked = True
        else:
            resolution = self.record(
                'ATLAS', 'skip',
                {'required': False, 'status': 'NONE', 'disputed': False,
                 'disposition': review['disposition'], 'resolution_id': None,
                 'resolution': None, 'reason': 'No dispute; ATLAS not invoked.',
                 'outstanding': []})
            atlas_invoked = False
        execution = self.record('KRISHNA', 'execute', self.krishna.execute(
            resolution['disposition'], assurance, permit_local_release, reason_codes))
        transition = {'from_state': 'KRISHNA_GATE',
                      'to_state': 'AUTHORIZED' if execution['disposition'] == 'PASS'
                      else 'HOLD',
                      'record_status': 'RECORDED'}
        out = json.loads(json.dumps(packet))
        out['acceptance_status'] = derived_status
        out['horizonax_assurance'] = dict(packet.get('horizonax_assurance') or {})
        out['horizonax_assurance']['derived_status'] = assurance['status']
        out['clear_review'] = {
            'required': review['required'],
            'decision_id': review['decision_id'],
            'disposition': review['disposition'],
            'reason_codes': review['reason_codes'],
        }
        out['atlas_dispute'] = {
            'required': resolution.get('required', False),
            'status': resolution.get('status', 'NONE'),
            'resolution_id': resolution.get('resolution_id'),
            'resolution': resolution.get('resolution'),
        }
        out['execution_gate'] = {
            'actor': 'KRISHNA',
            'disposition': execution['disposition'],
            'reason_codes': execution['reason_codes'],
            'authorization_id': execution.get('authorization_id'),
        }
        out['zeta_transition'] = transition
        self.record('ZETA', 'finish', {'scenario': label,
                                       'action': execution['disposition'],
                                       'zeta_transition': transition})
        return {'scenario': label, 'requested': request, 'assurance': assurance,
                'review': review, 'resolution': resolution,
                'atlas_invoked': atlas_invoked, 'execution': execution,
                'acceptance_status': derived_status, 'aco': out,
                'validation_errors': errors}

    def _adder_aco(self, label, design, engineering, assurance, review,
                   resolution, execution, reveal_slow, require_area, area_target):
        checks = engineering['checks']
        criteria = []
        for name in ('arithmetic', 'nominal_timing', 'slow_timing'):
            if name not in checks:
                status = 'NOT_EVALUATED'
            elif checks[name] is True:
                status = 'SATISFIED'
            else:
                status = 'NOT_SATISFIED'
            criteria.append({
                'criterion_id': 'ac-%s' % name.replace('_', '-'),
                'type': 'TIMING' if 'timing' in name else 'FUNCTIONAL_CORRECTNESS',
                'required': True,
                'expected': 'PASS',
                'status': status,
            })
        if require_area:
            criteria.append({
                'criterion_id': 'ac-area-01',
                'type': 'OBJECTIVE_THRESHOLD',
                'required': True,
                'metric': 'toy_area',
                'operator': '<=',
                'target': area_target,
                'observed': design['toy_area'],
                'status': 'SATISFIED' if checks.get('area_objective') else 'NOT_SATISFIED',
            })
        evidence = []
        for name, ok in checks.items():
            evidence.append({
                'evidence_id': 'ev-%s' % name,
                'kind': 'synthetic_check',
                'status': 'PASS' if ok else 'FAIL',
                'freshness': 'CURRENT',
                'fingerprint': 'sha256:demo-%s-%s' % (name, ok),
                'uri': 'demo://adder/%s/%s' % (design['name'], name),
            })
        if 'slow_timing' not in checks:
            evidence.append({
                'evidence_id': 'ev-slow-timing',
                'kind': 'synthetic_check',
                'status': 'MISSING',
                'freshness': 'UNKNOWN',
                'fingerprint': 'sha256:demo-slow-missing',
                'uri': 'demo://adder/%s/slow_timing' % design['name'],
            })
        return {
            'schema_version': SCHEMA_VERSION,
            'aco_id': 'aco-demo-%s' % label.replace(' ', '-').lower()[:48],
            'source': {'system': 'HorizonAX', 'project_id': 'demo-adder',
                       'case_id': 'adder-eco-demo', 'run_id': label},
            'subject': {'object_id': 'rtl::toy_adder_8b', 'object_kind': 'rtl_block',
                        'display_name': design['name']},
            'proposed_change': {
                'change_type': 'AREA_OPTIMIZATION',
                'summary': label,
                'files': ['rtl/toy_adder_8b.sv'],
                'change_fingerprint': 'sha256:demo-%s' % design['name'],
            },
            'stated_objective': {
                'objective_id': 'obj-adder-demo',
                'summary': ('Reduce modeled area while preserving arithmetic and '
                            'required timing evidence'),
                'metrics': ([{'metric': 'toy_area', 'operator': '<=',
                              'target': area_target, 'observed': design['toy_area']}]
                            if require_area else []),
            },
            'acceptance_criteria': criteria,
            'acceptance_status': acceptance_status_from_criteria(criteria),
            'evidence': evidence,
            'horizonax_assurance': {
                'summary': 'Synthetic adder assurance for educational demo',
                'checks': [{'check': k, 'status': 'PASS' if v else 'FAIL'}
                           for k, v in checks.items()]
                + ([{'check': 'slow_timing', 'status': 'NOT_RUN'}]
                   if 'slow_timing' not in checks else []),
                'derived_status': assurance['status'],
            },
            'clear_review': {
                'required': True,
                'decision_id': review.get('decision_id'),
                'disposition': review['disposition'],
                'reason_codes': review.get('reason_codes', []),
            },
            'atlas_dispute': {
                'required': resolution.get('required', False),
                'status': resolution.get('status', 'NONE'),
                'resolution_id': resolution.get('resolution_id'),
                'resolution': resolution.get('resolution'),
            },
            'execution_gate': {
                'actor': 'KRISHNA',
                'disposition': execution['disposition'],
                'reason_codes': execution.get('reason_codes', []),
                'authorization_id': execution.get('authorization_id'),
            },
            'zeta_transition': {
                'from_state': 'KRISHNA_GATE',
                'to_state': 'AUTHORIZED' if execution['disposition'] == 'PASS'
                else 'HOLD',
                'record_status': 'RECORDED',
            },
        }


def demo():
    runtime = MockZetaRuntime()
    eco = {'name': 'smaller_adder_cells', 'toy_area': 75, 'stage_ps': 70}
    original = {'name': 'original_cells', 'toy_area': 100, 'stage_ps': 50}
    # Same timing as original, smaller modeled area that still misses target <= 70.
    area_candidate = {'name': 'smaller_area_same_timing', 'toy_area': 75, 'stage_ps': 50}
    first = runtime.run('ECO: slow corner withheld', eco)
    prefix = json.dumps(runtime.history, sort_keys=True)
    prefix_len = len(runtime.history)
    later = runtime.run('ECO: slow corner revealed', eco, reveal_slow=True)
    good = runtime.run('Original design: complete evidence', original, reveal_slow=True)
    unpermitted = runtime.run('Original design: no local release permission', original,
                              reveal_slow=True, permit_local_release=False)
    area_hold = runtime.run('ECO: arithmetic+timing pass, area objective fails',
                            area_candidate, reveal_slow=True, require_area=True,
                            area_target=70)
    examples = []
    for name in EXAMPLE_FILES:
        packet = load_example(name)
        examples.append(runtime.run_packet(packet))
    assert json.dumps(runtime.history[:prefix_len], sort_keys=True) == prefix
    return runtime, [first, later, good, unpermitted, area_hold], examples


def self_test(runtime, scenarios, examples):
    first, later, good, unpermitted, area_hold = scenarios
    assert all(first['engineering']['checks'].values())
    assert first['requested'] == 'APPROVED'
    assert first['resolution']['disputed'] and first['execution']['disposition'] == 'HOLD'
    assert first['assurance']['missing'] == ['slow_timing']
    assert first['assurance']['status'] == 'INCOMPLETE'
    assert first['review']['disposition'] == 'CHANGES_REQUIRED'
    assert first['atlas_invoked'] is True
    assert later['assurance']['failed'] == ['slow_timing']
    assert later['engineering']['slack_ps']['slow'] == -120
    assert later['execution']['disposition'] == 'HOLD'
    assert later['assurance']['status'] == 'FAIL'
    assert good['execution']['disposition'] == 'PASS'
    assert good['atlas_invoked'] is False
    assert good['aco']['atlas_dispute']['status'] == 'NONE'
    assert unpermitted['execution']['disposition'] == 'HOLD'
    assert 'LOCAL_PERMISSION_DENIED' in unpermitted['execution']['reason_codes']
    # Even a directly supplied APPROVED disposition cannot bypass incomplete assurance.
    assert runtime.krishna.execute(
        'APPROVED', first['assurance'], True)['disposition'] == 'HOLD'
    assert area_hold['engineering']['checks']['arithmetic'] is True
    assert area_hold['engineering']['checks']['nominal_timing'] is True
    assert area_hold['engineering']['checks']['slow_timing'] is True
    assert area_hold['engineering']['checks']['area_objective'] is False
    assert area_hold['assurance']['status'] == 'FAIL'
    assert area_hold['execution']['disposition'] == 'HOLD'
    assert 'REQUIRED_OBJECTIVE_NOT_MET' in area_hold['execution']['reason_codes']
    assert area_hold['aco']['acceptance_status'] == 'NOT_SATISFIED'

    by_id = {e['aco']['aco_id']: e for e in examples}
    cdc_pass = by_id['aco-cdc-fifo-pass-001']
    cdc_hold = by_id['aco-cdc-fifo-hold-001']
    area_ex = by_id['aco-area-hold-001']

    assert cdc_pass['acceptance_status'] == 'SATISFIED'
    assert cdc_pass['review']['disposition'] == 'APPROVED'
    assert cdc_pass['execution']['disposition'] == 'PASS'
    assert cdc_pass['atlas_invoked'] is False
    assert cdc_pass['aco']['atlas_dispute']['status'] == 'NONE'
    assert cdc_pass['aco']['zeta_transition']['to_state'] == 'AUTHORIZED'

    assert any(c['criterion_id'] == 'ac-cdc-01' and c['status'] == 'SATISFIED'
               for c in cdc_hold['aco']['acceptance_criteria'])
    assert any(c['criterion_id'] == 'ac-fifo-01' and c['status'] == 'NOT_SATISFIED'
               for c in cdc_hold['aco']['acceptance_criteria'])
    assert cdc_hold['acceptance_status'] == 'NOT_SATISFIED'
    assert cdc_hold['review']['disposition'] == 'CHANGES_REQUIRED'
    assert cdc_hold['execution']['disposition'] == 'HOLD'
    assert 'REQUIRED_PROPERTY_VIOLATED' in cdc_hold['execution']['reason_codes']
    assert cdc_hold['atlas_invoked'] is False

    assert area_ex['acceptance_status'] == 'NOT_SATISFIED'
    assert area_ex['execution']['disposition'] == 'HOLD'
    assert 'REQUIRED_OBJECTIVE_NOT_MET' in area_ex['execution']['reason_codes']
    assert area_ex['atlas_invoked'] is False

    for example in examples:
        assert validate_aco_packet(example['aco']) == []
        assert example['aco']['schema_version'] == SCHEMA_VERSION

    # Each scenario records ZETA begin...finish with HorizonAX, CLEAR, ATLAS, KRISHNA.
    index = 0
    while index < len(runtime.history):
        assert runtime.history[index]['component'] == 'ZETA'
        assert runtime.history[index]['method'] == 'begin'
        end = index + 1
        while end < len(runtime.history) and not (
                runtime.history[end]['component'] == 'ZETA'
                and runtime.history[end]['method'] == 'finish'):
            end += 1
        assert end < len(runtime.history)
        components = [e['component'] for e in runtime.history[index:end + 1]]
        assert components[0] == 'ZETA' and components[-1] == 'ZETA'
        assert 'HORIZONAX' in components
        assert 'CLEAR' in components
        assert 'ATLAS' in components
        assert 'KRISHNA' in components
        index = end + 1


def print_scenario(s):
    print('\n' + s['scenario'])
    if 'engineering' in s:
        print('  [SIM] Checks: ' + json.dumps(s['engineering']['checks']))
        if 'slack_ps' in s['engineering']:
            print('  [SIM] Slack (ps): ' + json.dumps(s['engineering']['slack_ps']))
    if 'acceptance_status' in s:
        print('  [SIM] Acceptance: ' + s['acceptance_status'])
    elif 'aco' in s:
        print('  [SIM] Acceptance: ' + s['aco']['acceptance_status'])
    print('  [SIM] HorizonAX assurance: ' + s['assurance']['status'])
    print('  [SIM] CLEAR disposition: ' + s['review']['disposition'])
    atlas = 'invoked' if s.get('atlas_invoked') else 'not invoked'
    print('  [SIM] ATLAS: %s (%s)' % (atlas, s['resolution'].get('reason', '')))
    print('  [SIM] KRISHNA disposition: ' + s['execution']['disposition'])
    print('  [SIM] KRISHNA reasons: ' + json.dumps(s['execution'].get('reason_codes')))
    print('  [SIM] Zeta recorded the local outcome.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Print simulated call history')
    parser.add_argument('--self-test', action='store_true', help='Check scenarios and gate bypass')
    parser.add_argument('--examples', action='store_true',
                        help='Print only ACO exchange example results')
    args = parser.parse_args()
    runtime, scenarios, examples = demo()
    self_test(runtime, scenarios, examples)
    if args.json:
        print(json.dumps({'simulation': True, 'scenarios': scenarios,
                          'examples': examples, 'history': runtime.history},
                         indent=2))
    elif args.self_test:
        print('PASS: missing evidence, revealed failure, good control, denied permission,')
        print('direct gate bypass, CDC/FIFO pass, CDC/FIFO hold, area objective hold,')
        print('ATLAS not required on happy paths, call order, and earlier snapshot preservation.')
    elif args.examples:
        print('ACO EXCHANGE V1 EXAMPLES -- ALL NAMED SYSTEMS ARE LOCAL MOCKS\n')
        for s in examples:
            print_scenario(s)
        print('\nNo production integration, real signoff, or tamper-proof log is demonstrated.')
    else:
        print('ACO DEMO -- ALL NAMED SYSTEMS ARE LOCAL MOCKS\n')
        print('Toy Zeta orchestrates HorizonAX -> CLEAR -> (ATLAS if disputed) -> KRISHNA.')
        print('Contract: schemas/aco_exchange_v1.schema.json (demo interoperability only).')
        print('Scripted adder proposal: reduce modeled area from 100 toward a stated target.')
        for s in scenarios:
            print_scenario(s)
        print('\n--- ACO exchange examples ---')
        for s in examples:
            print_scenario(s)
        print('\nNo production integration, real signoff, or tamper-proof log is demonstrated.')
        print('Use --json to inspect every simulated call. Use --self-test to verify controls.')
        print('Use --examples to focus on CDC/FIFO and area-objective exchange packets.')


if __name__ == '__main__':
    main()
