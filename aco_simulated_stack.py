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

ACO exchange v1 / v1.1 makes the interoperability contract explicit:
    durable ACO identity + revision
        -> exact source binding
        -> participant-owned records
        -> append-oriented lifecycle history
        -> CI merge-gate projection

v1 packets remain supported. v1.1 adds revision, source_binding, ownership,
stale-after-commit semantics, optional domain policy classes, and merge_gate.
A semantic honesty patch (still schema_version 1.1) evaluates evidence and
numeric objectives, preserves OPEN disputes, requires commit bindings for
v1.1 release, and derives merge_gate reasons only from current computed state.

All timing/area/CDC/FIFO values are synthetic. This is not silicon signoff or an
AI agent. ACO means Agentic Change Order.

The public lesson is the interaction: green partial checks do not authorize
release; fixing one finding does not prove the change is acceptable; verification
PASS is not the same as meeting a stated engineering objective; and an old PASS
for commit A never authorizes commit B.

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
SCHEMA_VERSION_V11 = '1.1'
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION, SCHEMA_VERSION_V11})
HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(HERE, 'examples')
EXAMPLE_FILES = (
    'cdc_fifo_pass.json',
    'cdc_fifo_hold.json',
    'area_goal_hold.json',
)
EXAMPLE_FILES_V11 = (
    os.path.join('v1_1', 'aco2741_rev7_authorized.json'),
    os.path.join('v1_1', 'aco2741_rev8_stale.json'),
    os.path.join('v1_1', 'policy_missing_fifo.json'),
)

# Minimal stdlib checks against the documented ACO exchange contract.
# Formal JSON Schema validation would need a dependency; this is intentional.
TOP_LEVEL_REQUIRED = (
    'schema_version', 'aco_id', 'source', 'subject', 'proposed_change',
    'stated_objective', 'acceptance_criteria', 'acceptance_status', 'evidence',
    'horizonax_assurance', 'clear_review', 'atlas_dispute', 'execution_gate',
    'zeta_transition',
)
TOP_LEVEL_REQUIRED_V11 = TOP_LEVEL_REQUIRED + (
    'revision', 'source_binding', 'ownership', 'lifecycle_state',
    'transition_history', 'merge_gate',
)
CRITERION_STATUS = frozenset(
    {'SATISFIED', 'NOT_SATISFIED', 'NOT_EVALUATED', 'BLOCKED'})
ACCEPTANCE_STATUS = frozenset(
    {'SATISFIED', 'NOT_SATISFIED', 'PARTIAL', 'BLOCKED'})
CLEAR_DISPOSITION = frozenset(
    {'NOT_RUN', 'APPROVED', 'CHANGES_REQUIRED', 'REJECTED', 'CONDITIONAL'})
ATLAS_STATUS = frozenset({'NONE', 'OPEN', 'RESOLVED'})
GATE_DISPOSITION = frozenset({'PASS', 'HOLD', 'DENY', 'NOT_RUN'})
ASSURANCE_STATUS = frozenset(
    {'PASS', 'FAIL', 'INCOMPLETE', 'STALE', 'REANALYSIS_REQUIRED'})
MERGE_GATE_STATUS = frozenset({'PENDING', 'PASS', 'HOLD', 'DENY', 'STALE'})
FAIL_LIKE = frozenset({
    'FAIL', 'PROPERTY_VIOLATED', 'NOT_SATISFIED', 'REJECTED'})
INCOMPLETE_LIKE = frozenset({
    'INCOMPLETE', 'NOT_RUN', 'NOT_EVALUATED', 'BLOCKED', 'MISSING',
    'INCONCLUSIVE', 'UNSUPPORTED'})
STALE_LIKE = frozenset({'STALE', 'REANALYSIS_REQUIRED'})
# Explicit check/evidence vocabularies. Unknown required statuses never fall through to PASS.
KNOWN_CHECK_STATUSES = frozenset({
    'PASS', 'FAIL', 'PROPERTY_HOLDS', 'PROPERTY_VIOLATED', 'SYNCHRONIZED',
    'STALE', 'REANALYSIS_REQUIRED', 'NOT_RUN', 'INCOMPLETE', 'INCONCLUSIVE',
    'UNSUPPORTED', 'MISSING', 'BLOCKED', 'NOT_EVALUATED', 'NOT_SATISFIED',
})
CHECK_SUCCESS = frozenset({'PASS', 'PROPERTY_HOLDS', 'SYNCHRONIZED'})
EVIDENCE_SUCCESS_BY_KIND = {
    'cdc_structure_assessment': frozenset({'SYNCHRONIZED', 'PASS'}),
    'verification_result': frozenset({'PROPERTY_HOLDS', 'PASS'}),
    'functional_check': frozenset({'PASS'}),
    'timing_check': frozenset({'PASS'}),
    'counterexample': frozenset(),
    # Legacy v1 area fixture may use textual "toy_area=N"; handled separately.
    'objective_measurement': frozenset({'PASS'}),
}
DEFAULT_OWNERSHIP = {
    'proposed_change': 'ORIGINATOR',
    'horizonax_assurance': 'HORIZONAX',
    'clear_review': 'CLEAR',
    'atlas_dispute': 'ATLAS',
    'execution_gate': 'KRISHNA',
    'lifecycle': 'ZETA',
}
# Tiny simulated policy map. CLEAR uses this to detect missing assurance classes;
# it does NOT implement CDC/FIFO/STA algorithms.
# Declared required_assurance_classes may only ADD to a known policy, never weaken it.
DOMAIN_POLICY = {
    'ASYNC_FIFO_MODIFICATION': {
        'required': ('CDC', 'FIFO_SAFETY', 'FIFO_ORDERING', 'TIMING'),
        'conditional': {
            'RDC': 'reset behavior changes',
            'PROTOCOL': 'interface behavior changes',
        },
    },
}
# Compatibility: when evidence[] is non-empty and current, class coverage may also
# be satisfied by successful checks carrying a class label (toy aggregation only).
# Empty evidence never authorizes release via labels alone.


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


def _is_finite_number(value):
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float)):
        return value == value and value not in (float('inf'), float('-inf'))
    return False


# Criterion types with documented synthetic semantics in this demo.
SUPPORTED_CRITERION_TYPES = frozenset({
    'CDC_STRUCTURE',
    'PROPERTY_STATUS',
    'PROPERTY_SET',
    'TIMING',
    'FUNCTIONAL_CORRECTNESS',
    'OBJECTIVE_THRESHOLD',
    'MAX_FINDING_COUNT',
    'EVIDENCE_FRESHNESS',
})


def evaluate_objective_threshold(criterion):
    """Deterministic toy numeric check for OBJECTIVE_THRESHOLD. No eval()."""
    operator = criterion.get('operator')
    observed = criterion.get('observed')
    target = criterion.get('target')
    if operator != '<=':
        return {'ok': False, 'status': 'NOT_EVALUATED',
                'reason': 'UNSUPPORTED_OPERATOR'}
    if not _is_finite_number(observed) or not _is_finite_number(target):
        return {'ok': False, 'status': 'NOT_EVALUATED',
                'reason': 'NONFINITE_OR_MISSING_VALUE'}
    passed = float(observed) <= float(target)
    return {'ok': passed,
            'status': 'SATISFIED' if passed else 'NOT_SATISFIED',
            'reason': None if passed else 'REQUIRED_OBJECTIVE_NOT_MET'}


def evaluate_criteria(criteria):
    """Derive criterion statuses; preserve submitted claims for traceability."""
    evaluated = []
    for criterion in criteria or []:
        item = dict(criterion)
        item['submitted_status'] = criterion.get('status')
        ctype = criterion.get('type')
        if criterion.get('required') and ctype not in SUPPORTED_CRITERION_TYPES:
            item['status'] = 'NOT_EVALUATED'
            item['evaluation'] = {
                'ok': False,
                'status': 'NOT_EVALUATED',
                'reason': 'UNSUPPORTED_REQUIRED_CRITERION',
            }
        elif ctype == 'OBJECTIVE_THRESHOLD' and criterion.get('required'):
            result = evaluate_objective_threshold(criterion)
            item['status'] = result['status']
            item['evaluation'] = result
        evaluated.append(item)
    return evaluated


def effective_required_classes(packet):
    """Union of known DOMAIN_POLICY requirements and packet-declared classes."""
    change_class = packet.get('change_class')
    declared = list(packet.get('required_assurance_classes') or [])
    policy = []
    if change_class in DOMAIN_POLICY:
        policy = list(DOMAIN_POLICY[change_class]['required'])
    merged = list(policy)
    for cls in declared:
        if cls not in merged:
            merged.append(cls)
    return merged


def parse_legacy_objective_measurement(status):
    """v1 compatibility: objective_measurement status may be 'toy_area=75'."""
    if not isinstance(status, str) or '=' not in status:
        return None
    metric, _, raw = status.partition('=')
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not _is_finite_number(value):
        return None
    return {'metric': metric.strip(), 'observed': value}


def evidence_outcome(item, current_commit_sha=None, require_binding=False):
    """Classify one evidence record."""
    if not isinstance(item, dict):
        return 'INCOMPLETE', 'MALFORMED_EVIDENCE'
    kind = item.get('kind')
    status = item.get('status')
    freshness = item.get('freshness')
    bound = item.get('bound_commit_sha')
    if require_binding:
        if not bound:
            return 'INCOMPLETE', 'MISSING_EVIDENCE_BINDING'
        if current_commit_sha and bound != current_commit_sha:
            return 'STALE', 'EVIDENCE_BINDING_MISMATCH'
    if freshness == 'STALE':
        return 'STALE', 'STALE_EVIDENCE'
    # Release-authorizing evidence must be explicitly CURRENT.
    # UNKNOWN, missing, or null freshness is incomplete — never normalized to CURRENT.
    if freshness != 'CURRENT':
        return 'INCOMPLETE', 'UNKNOWN_FRESHNESS'
    if kind == 'objective_measurement' and status not in EVIDENCE_SUCCESS_BY_KIND.get(
            kind, frozenset()):
        legacy = parse_legacy_objective_measurement(status)
        if legacy is None:
            if status in FAIL_LIKE:
                return 'FAIL', 'FAILED_EVIDENCE'
            return 'INCOMPLETE', 'UNKNOWN_EVIDENCE_STATUS'
        return 'PASS', 'LEGACY_OBJECTIVE_MEASUREMENT'
    success = EVIDENCE_SUCCESS_BY_KIND.get(kind)
    if success is None:
        if status in FAIL_LIKE:
            return 'FAIL', 'FAILED_EVIDENCE'
        if status in CHECK_SUCCESS:
            return 'PASS', None
        if status in STALE_LIKE:
            return 'STALE', 'STALE_EVIDENCE'
        if status in INCOMPLETE_LIKE:
            return 'INCOMPLETE', 'INCOMPLETE_EVIDENCE'
        return 'INCOMPLETE', 'UNKNOWN_EVIDENCE_STATUS'
    if status in success:
        return 'PASS', None
    if status in FAIL_LIKE or status == 'PROPERTY_VIOLATED':
        return 'FAIL', 'FAILED_EVIDENCE'
    if status in STALE_LIKE:
        return 'STALE', 'STALE_EVIDENCE'
    if status in INCOMPLETE_LIKE:
        return 'INCOMPLETE', 'INCOMPLETE_EVIDENCE'
    return 'INCOMPLETE', 'UNKNOWN_EVIDENCE_STATUS'


def dedupe_codes(codes):
    out = []
    seen = set()
    for code in codes or []:
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


class MockHorizonAX:
    def assure(self, engineering, required=REQUIRED):
        checks = engineering['checks']
        missing = [k for k in required if k not in checks]
        failed = [k for k in required if k in checks and checks[k] is not True]
        return {'missing': missing, 'failed': failed,
                'status': 'FAIL' if failed else 'INCOMPLETE' if missing else 'PASS'}

    def assure_from_packet(self, packet):
        """Assess synthetic evidence/objectives; do not invent PASS from labels alone."""
        if not isinstance(packet, dict):
            raise ValueError('Invalid ACO packet: packet must be an object')
        assurance = packet.get('horizonax_assurance')
        if not isinstance(assurance, dict):
            raise ValueError('Invalid ACO packet: bad:/horizonax_assurance')
        is_v11 = packet.get('schema_version') == SCHEMA_VERSION_V11
        current_commit = None
        binding = packet.get('source_binding')
        if isinstance(binding, dict):
            current_commit = binding.get('commit_sha')
        bound = assurance.get('bound_commit_sha')
        declared = str(assurance.get('status') or '').upper()
        checks = assurance.get('checks')
        if checks is None:
            checks = []
        if not isinstance(checks, list):
            raise ValueError('Invalid ACO packet: bad:/horizonax_assurance/checks')
        for i, check in enumerate(checks):
            if not isinstance(check, dict):
                raise ValueError(
                    'Invalid ACO packet: bad:/horizonax_assurance/checks/%d' % i)
            status = check.get('status')
            if status not in KNOWN_CHECK_STATUSES:
                raise ValueError(
                    'Invalid ACO packet: bad:/horizonax_assurance/checks/%d/status '
                    'unknown status %r' % (i, status))

        evidence = packet.get('evidence')
        if evidence is None:
            evidence = []
        if not isinstance(evidence, list):
            raise ValueError('Invalid ACO packet: bad:/evidence')

        criteria = packet.get('acceptance_criteria') or []
        if not isinstance(criteria, list):
            raise ValueError('Invalid ACO packet: bad:/acceptance_criteria')
        evaluated_criteria = evaluate_criteria(criteria)

        failed = []
        missing = []
        codes = []
        required_classes = effective_required_classes(packet)
        required_criteria = [c for c in evaluated_criteria if c.get('required')]

        if not evidence and (required_criteria or required_classes or checks):
            missing.append('required_evidence')
            codes.append('MISSING_REQUIRED_EVIDENCE')
        if not required_criteria and not required_classes and not checks:
            # Empty obligations never become release authority by default.
            missing.append('required_obligations')
            codes.append('EMPTY_OBLIGATIONS')

        evidence_ids = []
        for i, item in enumerate(evidence):
            if not isinstance(item, dict):
                raise ValueError('Invalid ACO packet: bad:/evidence/%d' % i)
            eid = item.get('evidence_id')
            if eid in evidence_ids:
                raise ValueError(
                    'Invalid ACO packet: bad:/evidence/%d/evidence_id duplicate' % i)
            evidence_ids.append(eid)
            outcome, code = evidence_outcome(
                item, current_commit_sha=current_commit, require_binding=is_v11)
            label = eid or ('evidence[%d]' % i)
            if outcome == 'FAIL':
                failed.append(label)
                if code:
                    codes.append(code)
            elif outcome == 'STALE':
                missing.append(label)
                codes.append(code or 'STALE_EVIDENCE')
            elif outcome == 'INCOMPLETE':
                missing.append(label)
                if code:
                    codes.append(code)

        for i, criterion in enumerate(evaluated_criteria):
            refs = criterion.get('evidence_refs')
            if refs is None:
                continue
            if not isinstance(refs, list):
                raise ValueError(
                    'Invalid ACO packet: bad:/acceptance_criteria/%d/evidence_refs' % i)
            for ref in refs:
                if ref not in evidence_ids:
                    raise ValueError(
                        'Invalid ACO packet: dangling evidence_refs %r on '
                        '/acceptance_criteria/%d' % (ref, i))

        for check in checks:
            status = str(check.get('status', '')).upper()
            name = check.get('check') or check.get('name') or 'check'
            if status in FAIL_LIKE:
                failed.append(name)
            elif status in STALE_LIKE or status in INCOMPLETE_LIKE:
                missing.append(name)

        for criterion in evaluated_criteria:
            if not criterion.get('required'):
                continue
            status = criterion.get('status')
            cid = criterion.get('criterion_id', 'criterion')
            if status == 'NOT_SATISFIED':
                if cid not in failed:
                    failed.append(cid)
                if criterion.get('type') == 'OBJECTIVE_THRESHOLD':
                    codes.append('REQUIRED_OBJECTIVE_NOT_MET')
            elif status in ('NOT_EVALUATED', 'BLOCKED'):
                if cid not in missing:
                    missing.append(cid)
                reason = (criterion.get('evaluation') or {}).get('reason')
                if reason == 'UNSUPPORTED_REQUIRED_CRITERION':
                    codes.append('UNSUPPORTED_REQUIRED_CRITERION')
                else:
                    codes.append('UNSUPPORTED_OR_INCOMPLETE_CRITERION')

        present_classes = set()
        if evidence and 'required_evidence' not in missing:
            for check in checks:
                cls = check.get('class')
                status = check.get('status')
                if cls and status in CHECK_SUCCESS:
                    present_classes.add(cls)
            for cls in required_classes:
                if cls not in present_classes:
                    missing.append('class:%s' % cls)
                    codes.append('MISSING_REQUIRED_ASSURANCE_CLASS')

        if is_v11 and current_commit and bound and bound != current_commit:
            codes.append('SOURCE_BINDING_CHANGED')
            codes.append('ASSURANCE_STALE')

        if (declared in STALE_LIKE or 'ASSURANCE_STALE' in codes
                or (is_v11 and current_commit and bound and bound != current_commit)):
            derived = 'REANALYSIS_REQUIRED' if declared == 'REANALYSIS_REQUIRED' else 'STALE'
        elif failed:
            derived = 'FAIL'
        elif missing:
            derived = 'INCOMPLETE'
        else:
            derived = 'PASS'

        # Preserve producer-declared adverse status separately from evidence-derived status.
        # Declared FAIL/INCOMPLETE must block even when checks look green.
        # Declared PASS never overrides failed/stale/incomplete evidence (derived wins).
        status = derived
        if declared in ('FAIL', 'INCOMPLETE'):
            if derived == 'PASS':
                codes.append('ASSURANCE_STATUS_CONFLICT')
            if declared == 'FAIL':
                status = 'FAIL'
                if 'declared_assurance_status' not in failed:
                    failed.append('declared_assurance_status')
            else:
                if derived == 'FAIL':
                    status = 'FAIL'
                else:
                    status = 'INCOMPLETE'
                    if 'declared_assurance_status' not in missing:
                        missing.append('declared_assurance_status')
                if derived == 'PASS':
                    pass  # conflict already recorded
            if derived not in (declared, 'PASS') and 'ASSURANCE_STATUS_CONFLICT' not in codes:
                # Declared adverse disagrees with a different non-PASS derived result.
                if declared == 'FAIL' and derived != 'FAIL':
                    codes.append('ASSURANCE_STATUS_CONFLICT')

        return {
            'missing': missing,
            'failed': failed,
            'status': status,
            'declared_status': declared if declared in ASSURANCE_STATUS else None,
            'derived_status': derived,
            'summary': assurance.get('summary', ''),
            'checks': checks,
            'producer': 'HORIZONAX',
            'bound_commit_sha': bound,
            'assurance_classes_present': list(present_classes),
            'reason_codes': dedupe_codes(codes),
            'evaluated_criteria': evaluated_criteria,
            'require_source_binding': is_v11,
        }


class MockCLEAR:
    def missing_policy_classes(self, packet, assurance=None):
        """Detect missing required assurance classes without reimplementing checks."""
        required = effective_required_classes(packet)
        present = set()
        if assurance is not None:
            present = set(assurance.get('assurance_classes_present') or [])
        else:
            packet_assurance = packet.get('horizonax_assurance') or {}
            if isinstance(packet_assurance, dict):
                for check in packet_assurance.get('checks') or []:
                    if (isinstance(check, dict) and check.get('class')
                            and check.get('status') in CHECK_SUCCESS):
                        present.add(check['class'])
            if not (packet.get('evidence') or []):
                present = set()
        return [cls for cls in required if cls not in present]

    def review(self, assurance, reason_codes=None, packet=None):
        codes = list(reason_codes or [])
        for code in assurance.get('reason_codes') or []:
            if code not in codes:
                codes.append(code)
        if packet is not None:
            missing_classes = self.missing_policy_classes(packet, assurance)
            if missing_classes:
                if 'MISSING_REQUIRED_ASSURANCE_CLASS' not in codes:
                    codes.append('MISSING_REQUIRED_ASSURANCE_CLASS')
                if 'POLICY_CLASSES_INCOMPLETE' not in codes:
                    codes.append('POLICY_CLASSES_INCOMPLETE')
            binding = packet.get('source_binding') if isinstance(
                packet.get('source_binding'), dict) else {}
            bound = assurance.get('bound_commit_sha')
            if (binding.get('commit_sha') and bound
                    and binding['commit_sha'] != bound):
                if 'SOURCE_BINDING_CHANGED' not in codes:
                    codes.append('SOURCE_BINDING_CHANGED')
                if 'ASSURANCE_STALE' not in codes:
                    codes.append('ASSURANCE_STALE')
            dispute = packet.get('atlas_dispute') if isinstance(
                packet.get('atlas_dispute'), dict) else {}
            if dispute.get('status') == 'OPEN':
                codes.append('ATLAS_DISPUTE_OPEN')
        codes = dedupe_codes(codes)
        if assurance['status'] in STALE_LIKE:
            if 'ASSURANCE_STALE' not in codes:
                codes.append('ASSURANCE_STALE')
            if 'REANALYSIS_REQUIRED' not in codes:
                codes.append('REANALYSIS_REQUIRED')
            return {'required': True, 'decision_id': 'clear-demo-stale',
                    'disposition': 'CHANGES_REQUIRED',
                    'reason_codes': codes or ['ASSURANCE_STALE'],
                    'reason': 'Assurance is stale for the current source binding.',
                    'producer': 'CLEAR'}
        if assurance['status'] == 'PASS' and not codes:
            return {'required': True, 'decision_id': 'clear-demo-approved',
                    'disposition': 'APPROVED',
                    'reason_codes': ['REQUIRED_EVIDENCE_SATISFIED'],
                    'reason': 'Required toy checks satisfied.',
                    'producer': 'CLEAR'}
        if assurance['status'] == 'PASS' and codes:
            return {'required': True, 'decision_id': 'clear-demo-hold',
                    'disposition': 'CHANGES_REQUIRED',
                    'reason_codes': codes,
                    'reason': 'Assurance case incomplete against required policy.',
                    'producer': 'CLEAR'}
        if assurance.get('failed'):
            if ('REQUIRED_PROPERTY_VIOLATED' not in codes
                    and 'FAILED_EVIDENCE' not in codes
                    and not any(c.startswith('REQUIRED_') for c in codes)):
                codes.append('REQUIRED_CHECK_FAILED')
        if assurance.get('missing'):
            if 'MISSING_REQUIRED_EVIDENCE' not in codes:
                codes.append('MISSING_REQUIRED_EVIDENCE')
        if not codes:
            codes = ['ACCEPTANCE_CRITERIA_NOT_SATISFIED']
        return {'required': True, 'decision_id': 'clear-demo-hold',
                'disposition': 'CHANGES_REQUIRED',
                'reason_codes': dedupe_codes(codes),
                'reason': 'Available PASS results do not satisfy the release checklist.',
                'producer': 'CLEAR'}


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
                'resolution_disposition': ('UPHOLD_HOLD' if disputed else None),
                'reason': ('Release request cannot waive missing or failed checks.'
                           if disputed else 'No disagreement to resolve.'),
                'outstanding': assurance.get('missing', []) + assurance.get('failed', []),
                'producer': 'ATLAS',
                'disputed_claim': ('release_request_vs_clear'
                                  if disputed else None),
                'requester_position': request if disputed else None,
                'evidence_refs': [],
                'rationale': ('Release request cannot waive missing or failed checks.'
                              if disputed else None),
                'authority': 'ATLAS' if disputed else None,
                'conditions': None}

    def preserve_open(self, dispute):
        out = dict(dispute or {})
        out['required'] = True
        out['status'] = 'OPEN'
        out['producer'] = 'ATLAS'
        out['disputed'] = True
        return out


class MockKRISHNA:
    def execute(self, disposition, assurance, permit_local_release, reason_codes=None,
                current_commit_sha=None, dispute=None):
        # Defense in depth for this toy: a request or verdict alone is insufficient.
        # KRISHNA does not perform semiconductor analysis.
        clear_ok = disposition == 'APPROVED'
        assurance_ok = (assurance['status'] == 'PASS'
                        and not assurance.get('missing')
                        and not assurance.get('failed'))
        bound = assurance.get('bound_commit_sha')
        require_binding = bool(assurance.get('require_source_binding'))
        if require_binding:
            binding_ok = bool(current_commit_sha) and bool(bound) and (
                current_commit_sha == bound)
        else:
            # Legacy v1 / native adder path: commits are optional, but an explicit
            # mismatch still cannot authorize a different source state.
            if current_commit_sha and bound and current_commit_sha != bound:
                binding_ok = False
            else:
                binding_ok = True
        dispute = dispute or {}
        dispute_blocks = False
        if dispute.get('status') == 'OPEN':
            dispute_blocks = True
        elif dispute.get('status') == 'RESOLVED':
            res_disp = dispute.get('resolution_disposition')
            if res_disp in ('REJECT', 'UPHOLD_HOLD', 'CHANGES_REQUIRED'):
                dispute_blocks = True
        stale = assurance['status'] in STALE_LIKE or not binding_ok
        allowed = (permit_local_release and clear_ok and assurance_ok
                   and not stale and not dispute_blocks)
        codes = list(reason_codes or [])
        if allowed:
            codes = dedupe_codes(codes)
            if not codes:
                codes = ['CLEAR_APPROVED', 'REQUIRED_EVIDENCE_CURRENT',
                         'ACCEPTANCE_CRITERIA_SATISFIED', 'SOURCE_BINDING_CURRENT']
            return {'actor': 'KRISHNA', 'disposition': 'PASS',
                    'action': 'PASS', 'reason_codes': codes,
                    'authorization_id': 'krishna-auth-demo',
                    'producer': 'KRISHNA',
                    'bound_commit_sha': current_commit_sha or bound,
                    'scope': 'Local simulation flag only; no physical or external action.'}
        if dispute_blocks:
            if dispute.get('status') == 'OPEN' and 'ATLAS_DISPUTE_OPEN' not in codes:
                codes.append('ATLAS_DISPUTE_OPEN')
            if dispute.get('resolution_disposition') == 'REJECT':
                codes.append('ATLAS_RESOLVED_REJECT')
        if stale:
            if 'ASSURANCE_STALE' not in codes:
                codes.append('ASSURANCE_STALE')
            if not binding_ok and 'SOURCE_BINDING_CHANGED' not in codes:
                codes.append('SOURCE_BINDING_CHANGED')
        if assurance.get('failed'):
            failed = assurance['failed']
            if (('FAILED_EVIDENCE' in codes
                 or any('overflow' in str(x) or str(x).startswith('ac-fifo')
                        or str(x).startswith('fifo_') or str(x).startswith('ev-')
                        for x in failed))
                    and 'REQUIRED_PROPERTY_VIOLATED' not in codes
                    and 'FAILED_EVIDENCE' not in codes):
                codes.append('REQUIRED_PROPERTY_VIOLATED')
            elif (any('area' in str(x) or str(x).startswith('ac-area')
                      or 'toy_area' in str(x) for x in failed)
                  and 'REQUIRED_OBJECTIVE_NOT_MET' not in codes):
                codes.append('REQUIRED_OBJECTIVE_NOT_MET')
            elif ('REQUIRED_CHECK_FAILED' not in codes
                  and 'REQUIRED_PROPERTY_VIOLATED' not in codes
                  and 'REQUIRED_OBJECTIVE_NOT_MET' not in codes
                  and 'FAILED_EVIDENCE' not in codes):
                codes.append('REQUIRED_CHECK_FAILED')
        if assurance.get('missing') and 'MISSING_REQUIRED_EVIDENCE' not in codes:
            codes.append('MISSING_REQUIRED_EVIDENCE')
        if not clear_ok and 'ACCEPTANCE_CRITERIA_NOT_SATISFIED' not in codes:
            codes.append('ACCEPTANCE_CRITERIA_NOT_SATISFIED')
        if not permit_local_release and 'LOCAL_PERMISSION_DENIED' not in codes:
            codes.append('LOCAL_PERMISSION_DENIED')
        if not codes:
            codes = ['HOLD']
        codes = dedupe_codes(codes)
        return {'actor': 'KRISHNA', 'disposition': 'HOLD',
                'action': 'HOLD', 'reason_codes': codes,
                'authorization_id': None,
                'producer': 'KRISHNA',
                'bound_commit_sha': current_commit_sha,
                'scope': 'Local simulation flag only; no physical or external action.'}


def acceptance_status_from_criteria(criteria):
    required = [c for c in criteria if c.get('required')]
    if not required:
        # Empty required obligations do not become release authority by default.
        return 'BLOCKED'
    statuses = [c.get('status') for c in required]
    if any(s == 'NOT_SATISFIED' for s in statuses):
        return 'NOT_SATISFIED'
    if any(s in ('NOT_EVALUATED', 'BLOCKED') for s in statuses):
        return 'BLOCKED' if any(s == 'BLOCKED' for s in statuses) else 'PARTIAL'
    if all(s == 'SATISFIED' for s in statuses):
        return 'SATISFIED'
    return 'PARTIAL'


def project_merge_gate(packet, execution=None, assurance=None, review=None,
                       atlas=None, permit_local_release=True):
    """CI/PR required-check projection from *current* computed state only."""
    binding = packet.get('source_binding') if isinstance(
        packet.get('source_binding'), dict) else {}
    commit_sha = binding.get('commit_sha') or 'unknown'
    revision = packet.get('revision', 1)
    aco_id = packet.get('aco_id', 'unknown')
    assurance = assurance or {}
    review = review or {}
    atlas = atlas or {}
    execution = execution or {}
    codes = []
    gate_status = 'HOLD'

    bound = assurance.get('bound_commit_sha')
    binding_mismatch = bool(commit_sha and commit_sha != 'unknown' and bound
                            and commit_sha != bound)

    if not permit_local_release:
        gate_status = 'HOLD'
        codes.append('LOCAL_PERMISSION_DENIED')
    if atlas.get('status') == 'OPEN':
        gate_status = 'HOLD'
        codes.append('ATLAS_DISPUTE_OPEN')
    if atlas.get('status') == 'RESOLVED' and atlas.get(
            'resolution_disposition') in ('REJECT', 'UPHOLD_HOLD', 'CHANGES_REQUIRED'):
        gate_status = 'HOLD'
        codes.append('ATLAS_RESOLVED_REJECT')
    if assurance.get('status') in STALE_LIKE or binding_mismatch:
        gate_status = 'STALE'
        codes.append('ASSURANCE_STALE')
        if binding_mismatch:
            codes.append('SOURCE_BINDING_CHANGED')
        codes.append('MERGE_BLOCKED')
    elif assurance.get('status') == 'INCOMPLETE' or assurance.get('missing'):
        gate_status = 'HOLD'
        codes.append('MISSING_REQUIRED_EVIDENCE')
        codes.append('MERGE_BLOCKED')
    elif assurance.get('status') == 'FAIL' or assurance.get('failed'):
        gate_status = 'HOLD'
        codes.append('REQUIRED_CHECK_FAILED')
        codes.append('MERGE_BLOCKED')
    elif review.get('disposition') == 'CHANGES_REQUIRED':
        gate_status = 'HOLD'
        codes.append('CLEAR_CHANGES_REQUIRED')
        codes.append('MERGE_BLOCKED')
    elif execution.get('disposition') == 'DENY':
        gate_status = 'DENY'
        codes.append('KRISHNA_DENY')
        codes.append('MERGE_BLOCKED')
    elif execution.get('disposition') == 'HOLD':
        gate_status = 'HOLD'
        codes.append('KRISHNA_HOLD')
        for code in execution.get('reason_codes') or []:
            codes.append(code)
        codes.append('MERGE_BLOCKED')
    elif (permit_local_release
          and assurance.get('status') == 'PASS'
          and review.get('disposition') == 'APPROVED'
          and atlas.get('status') in (None, 'NONE')
          and execution.get('disposition') == 'PASS'
          and not binding_mismatch):
        gate_status = 'PASS'
        codes = ['MERGE_AUTHORIZED']
    elif (permit_local_release
          and assurance.get('status') == 'PASS'
          and review.get('disposition') == 'APPROVED'
          and atlas.get('status') == 'RESOLVED'
          and atlas.get('resolution_disposition') == 'ALLOW_EXECUTION'
          and execution.get('disposition') == 'PASS'
          and not binding_mismatch):
        gate_status = 'PASS'
        codes = ['MERGE_AUTHORIZED']
    else:
        gate_status = 'HOLD'
        codes.append('MERGE_BLOCKED')

    codes = dedupe_codes(codes)
    if gate_status != 'PASS':
        codes = [c for c in codes if c != 'MERGE_AUTHORIZED']
        if 'MERGE_BLOCKED' not in codes:
            codes.append('MERGE_BLOCKED')
    return {
        'aco_id': aco_id,
        'revision': revision,
        'commit_sha': commit_sha,
        'gate_status': gate_status,
        'reason_codes': codes,
    }


def mark_stale_after_source_change(authorized_packet, new_binding, new_revision):
    """Append a new revision: preserve prior PASS history; do not authorize new commit."""
    out = json.loads(json.dumps(authorized_packet))
    old_binding = authorized_packet.get('source_binding') or {}
    old_commit = old_binding.get('commit_sha')
    new_commit = new_binding['commit_sha']
    assert old_commit != new_commit
    out['schema_version'] = SCHEMA_VERSION_V11
    out['revision'] = new_revision
    out['source_binding'] = dict(new_binding)
    out['source'] = dict(authorized_packet.get('source') or {})
    out['source']['run_id'] = 'run-rev%s-%s' % (new_revision, new_commit[:7])
    history = list(authorized_packet.get('transition_history') or [])
    # Preserve historical MERGE_AUTHORIZED for the old commit.
    history.append({
        'from_state': 'MERGE_AUTHORIZED',
        'to_state': 'ANALYSIS_PENDING',
        'record_status': 'RECORDED',
        'at_revision': new_revision,
        'commit_sha': new_commit,
        'note': 'Source binding changed; prior authorization retained as history only',
        'producer': 'ZETA',
    })
    out['transition_history'] = history
    for criterion in out.get('acceptance_criteria') or []:
        if criterion.get('required'):
            criterion['status'] = 'NOT_EVALUATED'
    out['acceptance_status'] = acceptance_status_from_criteria(
        out.get('acceptance_criteria') or [])
    for item in out.get('evidence') or []:
        item['freshness'] = 'STALE'
    assurance = dict(out.get('horizonax_assurance') or {})
    assurance['status'] = 'STALE'
    assurance['producer'] = 'HORIZONAX'
    assurance['bound_commit_sha'] = old_commit
    assurance['prior_pass_revision'] = authorized_packet.get('revision')
    assurance['prior_pass_commit_sha'] = old_commit
    assurance['summary'] = (
        'Prior PASS for %s is historical evidence only; reanalysis required for %s'
        % (old_commit, new_commit))
    checks = []
    for check in assurance.get('checks') or []:
        item = dict(check)
        item['status'] = 'STALE'
        checks.append(item)
    assurance['checks'] = checks
    out['horizonax_assurance'] = assurance
    out['clear_review'] = {
        'required': True,
        'decision_id': 'clear-stale-%s' % new_revision,
        'disposition': 'CHANGES_REQUIRED',
        'reason_codes': ['SOURCE_BINDING_CHANGED', 'ASSURANCE_STALE',
                         'REANALYSIS_REQUIRED'],
        'producer': 'CLEAR',
    }
    out['atlas_dispute'] = {
        'required': False,
        'status': 'NONE',
        'resolution_id': None,
        'resolution': None,
        'producer': 'ATLAS',
        'disputed_claim': None,
        'requester_position': None,
        'evidence_refs': [],
        'rationale': None,
        'authority': None,
        'conditions': None,
    }
    out['execution_gate'] = {
        'actor': 'KRISHNA',
        'disposition': 'HOLD',
        'reason_codes': ['ASSURANCE_STALE', 'SOURCE_BINDING_CHANGED',
                         'ACCEPTANCE_CRITERIA_NOT_SATISFIED'],
        'authorization_id': None,
        'producer': 'KRISHNA',
        'bound_commit_sha': new_commit,
    }
    out['zeta_transition'] = {
        'from_state': 'MERGE_AUTHORIZED',
        'to_state': 'ANALYSIS_PENDING',
        'record_status': 'RECORDED',
        'producer': 'ZETA',
    }
    out['ownership'] = dict(DEFAULT_OWNERSHIP)
    out['lifecycle_state'] = 'ANALYSIS_PENDING'
    out['merge_gate'] = {
        'aco_id': out['aco_id'],
        'revision': new_revision,
        'commit_sha': new_commit,
        'gate_status': 'STALE',
        'reason_codes': ['SOURCE_BINDING_CHANGED', 'ASSURANCE_STALE', 'MERGE_BLOCKED'],
    }
    return out


def validate_aco_packet(packet):
    """Deterministic structural checks; not a full JSON Schema engine."""
    errors = []
    if not isinstance(packet, dict):
        return ['packet must be an object']
    version = packet.get('schema_version')
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append('schema_version must be one of %s' % sorted(SUPPORTED_SCHEMA_VERSIONS))
    required = TOP_LEVEL_REQUIRED_V11 if version == SCHEMA_VERSION_V11 else TOP_LEVEL_REQUIRED
    for key in required:
        if key not in packet:
            errors.append('missing:/' + key)
    source = packet.get('source')
    if not isinstance(source, dict):
        errors.append('bad:/source')
        source = {}
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
                errors.append('bad:/acceptance_criteria/%d' % i)
                continue
            for req in ('criterion_id', 'type', 'required', 'status'):
                if req not in criterion:
                    errors.append('missing:/acceptance_criteria/%d/%s' % (i, req))
            if criterion.get('status') not in CRITERION_STATUS:
                errors.append('bad:/acceptance_criteria/%d/status' % i)
            refs = criterion.get('evidence_refs')
            if refs is not None and not isinstance(refs, list):
                errors.append('bad:/acceptance_criteria/%d/evidence_refs' % i)
    if packet.get('acceptance_status') not in ACCEPTANCE_STATUS:
        errors.append('bad:/acceptance_status')
    evidence = packet.get('evidence')
    if not isinstance(evidence, list):
        errors.append('evidence must be an array')
    else:
        seen_ids = set()
        for i, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append('bad:/evidence/%d' % i)
                continue
            for req in ('evidence_id', 'kind', 'status',
                        'fingerprint', 'uri'):
                if req not in item:
                    errors.append('missing:/evidence/%d/%s' % (i, req))
            # freshness may be absent/null; runtime treats non-CURRENT as incomplete HOLD.
            if 'freshness' in item and item.get('freshness') not in (
                    None, 'CURRENT', 'STALE', 'UNKNOWN'):
                errors.append('bad:/evidence/%d/freshness' % i)
            eid = item.get('evidence_id')
            if eid in seen_ids:
                errors.append('bad:/evidence/%d/evidence_id duplicate' % i)
            seen_ids.add(eid)
    clear = packet.get('clear_review')
    if not isinstance(clear, dict):
        errors.append('bad:/clear_review')
        clear = {}
    if clear.get('disposition') not in CLEAR_DISPOSITION:
        errors.append('bad:/clear_review/disposition')
    atlas = packet.get('atlas_dispute')
    if not isinstance(atlas, dict):
        errors.append('bad:/atlas_dispute')
        atlas = {}
    if atlas.get('status') not in ATLAS_STATUS:
        errors.append('bad:/atlas_dispute/status')
    if atlas.get('resolution_disposition') not in (
            None, 'ALLOW_EXECUTION', 'REJECT', 'UPHOLD_HOLD', 'CHANGES_REQUIRED'):
        errors.append('bad:/atlas_dispute/resolution_disposition')
    gate = packet.get('execution_gate')
    if not isinstance(gate, dict):
        errors.append('bad:/execution_gate')
        gate = {}
    if gate.get('actor') != 'KRISHNA':
        errors.append('execution_gate.actor must be KRISHNA')
    if gate.get('disposition') not in GATE_DISPOSITION:
        errors.append('bad:/execution_gate/disposition')
    assurance = packet.get('horizonax_assurance')
    if not isinstance(assurance, dict):
        errors.append('bad:/horizonax_assurance')
        assurance = {}
    checks = assurance.get('checks')
    if checks is None:
        checks = []
    if not isinstance(checks, list):
        errors.append('bad:/horizonax_assurance/checks')
    else:
        for i, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append('bad:/horizonax_assurance/checks/%d' % i)
                continue
            status = check.get('status')
            if status not in KNOWN_CHECK_STATUSES:
                errors.append(
                    'bad:/horizonax_assurance/checks/%d/status unknown status %r'
                    % (i, status))
    if version == SCHEMA_VERSION_V11:
        if not isinstance(packet.get('revision'), int) or packet['revision'] < 1:
            errors.append('bad:/revision')
        binding = packet.get('source_binding')
        if not isinstance(binding, dict):
            errors.append('bad:/source_binding')
            binding = {}
        for field in ('repository', 'branch', 'commit_sha'):
            if not binding.get(field):
                errors.append('missing:/source_binding/' + field)
        ownership = packet.get('ownership')
        if not isinstance(ownership, dict):
            errors.append('bad:/ownership')
            ownership = {}
        for key, expected in DEFAULT_OWNERSHIP.items():
            if ownership.get(key) != expected:
                errors.append('bad:/ownership/' + key)
        if assurance.get('producer') != 'HORIZONAX':
            errors.append('horizonax_assurance.producer must be HORIZONAX')
        if assurance.get('status') not in ASSURANCE_STATUS:
            errors.append('bad:/horizonax_assurance/status')
        if not assurance.get('bound_commit_sha'):
            errors.append('missing:/horizonax_assurance/bound_commit_sha')
        if clear.get('producer') != 'CLEAR':
            errors.append('clear_review.producer must be CLEAR')
        if atlas.get('producer') != 'ATLAS':
            errors.append('atlas_dispute.producer must be ATLAS')
        if gate.get('producer') != 'KRISHNA':
            errors.append('execution_gate.producer must be KRISHNA')
        zt = packet.get('zeta_transition')
        if not isinstance(zt, dict):
            errors.append('bad:/zeta_transition')
            zt = {}
        if zt.get('producer') != 'ZETA':
            errors.append('zeta_transition.producer must be ZETA')
        if not isinstance(packet.get('transition_history'), list):
            errors.append('transition_history must be an array')
        merge = packet.get('merge_gate')
        if not isinstance(merge, dict):
            errors.append('bad:/merge_gate')
            merge = {}
        if merge.get('gate_status') not in MERGE_GATE_STATUS:
            errors.append('bad:/merge_gate/gate_status')
        for field in ('aco_id', 'revision', 'commit_sha', 'reason_codes'):
            if field not in merge:
                errors.append('missing:/merge_gate/' + field)
        # Declared classes may not weaken a known DOMAIN_POLICY (informational check).
        change_class = packet.get('change_class')
        if change_class in DOMAIN_POLICY:
            declared = packet.get('required_assurance_classes')
            if isinstance(declared, list):
                for cls in DOMAIN_POLICY[change_class]['required']:
                    if cls not in declared and declared:
                        # Allowed: runtime still unions policy; no hard error.
                        pass
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
                 'outstanding': [], 'producer': 'ATLAS'})
            atlas_invoked = False
        execution = self.record('KRISHNA', 'execute', self.krishna.execute(
            resolution['disposition'], assurance, permit_local_release, reason_codes))
        aco = self._adder_aco(label, design, engineering, assurance, review,
                              resolution, execution, reveal_slow, require_area,
                              area_target)
        transition = {'from_state': 'KRISHNA_GATE',
                      'to_state': 'AUTHORIZED' if execution['disposition'] == 'PASS'
                      else 'HOLD',
                      'record_status': 'RECORDED', 'producer': 'ZETA'}
        self.record('ZETA', 'finish', {'scenario': label,
                                       'action': execution['disposition'],
                                       'aco_id': aco['aco_id'],
                                       'zeta_transition': transition})
        return {'scenario': label, 'requested': request, 'engineering': engineering,
                'assurance': assurance, 'review': review, 'resolution': resolution,
                'atlas_invoked': atlas_invoked, 'execution': execution, 'aco': aco}

    def run_packet(self, packet, permit_local_release=True, naive_request=None):
        """Drive the same mocks from a versioned ACO exchange object."""
        # Work on a snapshot so callers' input objects are never mutated.
        packet = json.loads(json.dumps(packet))
        errors = validate_aco_packet(packet)
        if errors:
            raise ValueError('Invalid ACO packet: ' + '; '.join(errors))
        label = packet['aco_id']
        revision = packet.get('revision')
        binding = packet.get('source_binding') if isinstance(
            packet.get('source_binding'), dict) else {}
        current_commit = binding.get('commit_sha')
        self.record('ZETA', 'begin', {
            'scenario': label, 'aco_id': label, 'revision': revision,
            'commit_sha': current_commit,
        })
        assurance = self.record('HORIZONAX', 'assure',
                                self.horizonax.assure_from_packet(packet))
        evaluated = assurance.get('evaluated_criteria') or evaluate_criteria(
            packet.get('acceptance_criteria') or [])
        derived_status = acceptance_status_from_criteria(evaluated)
        reason_codes = list(assurance.get('reason_codes') or [])
        for criterion in evaluated:
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
        reason_codes = dedupe_codes(reason_codes)
        review = self.record('CLEAR', 'review',
                              self.clear.review(assurance, reason_codes, packet=packet))
        for code in review.get('reason_codes') or []:
            if code not in reason_codes:
                reason_codes.append(code)
        incoming_dispute = packet.get('atlas_dispute') if isinstance(
            packet.get('atlas_dispute'), dict) else {}
        if naive_request is None:
            request = review['disposition']
        else:
            request = naive_request
        if incoming_dispute.get('status') == 'OPEN':
            resolution = self.record(
                'ATLAS', 'preserve_open',
                self.atlas.preserve_open(incoming_dispute))
            atlas_invoked = True
        elif request != review['disposition']:
            resolution = self.record('ATLAS', 'resolve',
                                      self.atlas.resolve(request, review, assurance))
            atlas_invoked = True
        else:
            resolution = self.record(
                'ATLAS', 'skip',
                {'required': False, 'status': 'NONE', 'disputed': False,
                 'disposition': review['disposition'], 'resolution_id': None,
                 'resolution': None, 'resolution_disposition': None,
                 'reason': 'No dispute; ATLAS not invoked.',
                 'outstanding': [], 'producer': 'ATLAS'})
            atlas_invoked = False
        # Preserve structured fields from an incoming RESOLVED dispute.
        if (incoming_dispute.get('status') == 'RESOLVED'
                and resolution.get('status') != 'OPEN'):
            for key in ('resolution_disposition', 'disputed_claim', 'evidence_refs',
                        'rationale', 'authority', 'conditions', 'resolution',
                        'resolution_id'):
                if key in incoming_dispute and incoming_dispute.get(key) is not None:
                    resolution[key] = incoming_dispute.get(key)
            resolution['status'] = 'RESOLVED'
            resolution['required'] = True
            resolution['producer'] = 'ATLAS'
        execution = self.record('KRISHNA', 'execute', self.krishna.execute(
            review['disposition'], assurance, permit_local_release, reason_codes,
            current_commit_sha=current_commit, dispute=resolution))
        is_v11 = packet.get('schema_version') == SCHEMA_VERSION_V11
        if execution['disposition'] == 'PASS':
            to_state = 'MERGE_AUTHORIZED' if is_v11 else 'AUTHORIZED'
        elif assurance['status'] in STALE_LIKE:
            to_state = 'ANALYSIS_PENDING'
        elif review['disposition'] == 'CHANGES_REQUIRED' and is_v11:
            to_state = 'CHANGES_REQUIRED'
        elif resolution.get('status') == 'OPEN':
            to_state = 'DISPUTED'
        else:
            to_state = 'HOLD'
        transition = {'from_state': 'GATE_PENDING' if is_v11 else 'KRISHNA_GATE',
                      'to_state': to_state,
                      'record_status': 'RECORDED',
                      'producer': 'ZETA'}
        out = json.loads(json.dumps(packet))
        out['submitted_acceptance_criteria'] = json.loads(json.dumps(
            packet.get('acceptance_criteria') or []))
        out['acceptance_criteria'] = evaluated
        out['acceptance_status'] = derived_status
        out['horizonax_assurance'] = dict(packet.get('horizonax_assurance') or {})
        # Serialize three distinct meanings consistently with the evaluator:
        # declared_status = producer submission; derived_status = evidence assessment;
        # status = final effective status used by CLEAR/KRISHNA/merge_gate.
        submitted = (packet.get('horizonax_assurance') or {}).get('status')
        out['horizonax_assurance']['declared_status'] = assurance.get(
            'declared_status', submitted)
        out['horizonax_assurance']['derived_status'] = assurance.get(
            'derived_status', assurance['status'])
        out['horizonax_assurance']['status'] = assurance['status']
        # Compatibility alias for the producer-submitted label.
        out['horizonax_assurance']['submitted_status'] = submitted
        if is_v11:
            out['horizonax_assurance']['producer'] = 'HORIZONAX'
        out['clear_review'] = {
            'required': review['required'],
            'decision_id': review['decision_id'],
            'disposition': review['disposition'],
            'reason_codes': review['reason_codes'],
        }
        if is_v11:
            out['clear_review']['producer'] = 'CLEAR'
        out['atlas_dispute'] = {
            'required': resolution.get('required', False),
            'status': resolution.get('status', 'NONE'),
            'resolution_id': resolution.get('resolution_id'),
            'resolution': resolution.get('resolution'),
            'resolution_disposition': resolution.get('resolution_disposition'),
            'producer': 'ATLAS',
            'disputed_claim': resolution.get('disputed_claim'),
            'requester_position': resolution.get('requester_position'),
            'evidence_refs': resolution.get('evidence_refs') or [],
            'rationale': resolution.get('rationale'),
            'authority': resolution.get('authority'),
            'conditions': resolution.get('conditions'),
        }
        out['execution_gate'] = {
            'actor': 'KRISHNA',
            'disposition': execution['disposition'],
            'reason_codes': execution['reason_codes'],
            'authorization_id': execution.get('authorization_id'),
        }
        if is_v11:
            out['execution_gate']['producer'] = 'KRISHNA'
            out['execution_gate']['bound_commit_sha'] = execution.get(
                'bound_commit_sha')
        out['zeta_transition'] = transition
        merge = project_merge_gate(
            out, execution=execution, assurance=assurance,
            review=review, atlas=out['atlas_dispute'],
            permit_local_release=permit_local_release)
        if is_v11:
            out['ownership'] = dict(packet.get('ownership') or DEFAULT_OWNERSHIP)
            out['lifecycle_state'] = to_state
            history = list(packet.get('transition_history') or [])
            history.append({
                'from_state': transition['from_state'],
                'to_state': transition['to_state'],
                'record_status': 'RECORDED',
                'at_revision': packet.get('revision', 1),
                'commit_sha': current_commit,
                'note': 'Simulated governance pass',
                'producer': 'ZETA',
            })
            out['transition_history'] = history
            out['merge_gate'] = merge
        else:
            # v1 compatibility: expose projection without implying commit-bound auth.
            out['merge_gate'] = merge
        self.record('ZETA', 'finish', {'scenario': label,
                                       'action': execution['disposition'],
                                       'revision': revision,
                                       'zeta_transition': transition,
                                       'merge_gate': out.get('merge_gate')})
        return {'scenario': label, 'requested': request, 'assurance': assurance,
                'review': review, 'resolution': resolution,
                'atlas_invoked': atlas_invoked, 'execution': execution,
                'acceptance_status': derived_status, 'aco': out,
                'merge_gate': out.get('merge_gate'),
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
    examples_v11 = []
    for name in EXAMPLE_FILES_V11:
        packet = load_example(name)
        examples_v11.append(runtime.run_packet(packet))
    # Programmatic stale progression: same ACO identity, new commit, prior PASS preserved.
    rev7 = load_example(EXAMPLE_FILES_V11[0])
    rev8_derived = mark_stale_after_source_change(
        rev7,
        {
            'repository': 'demo://chip-a/rtl',
            'branch': 'feature/async-fifo-repair',
            'commit_sha': 'bbb2222cafebabe02',
            'rtl_fingerprint': 'sha256:demo-rtl-commit-b',
            'sdc_fingerprint': 'sha256:demo-sdc-commit-a',
            'requirements_fingerprint': 'sha256:demo-req-commit-a',
            'checker_config_fingerprint': 'sha256:demo-cfg-commit-a',
        },
        new_revision=8,
    )
    stale_prog = runtime.run_packet(rev8_derived)
    assert json.dumps(runtime.history[:prefix_len], sort_keys=True) == prefix
    return (runtime, [first, later, good, unpermitted, area_hold], examples,
            examples_v11, stale_prog)


def self_test(runtime, scenarios, examples, examples_v11, stale_prog):
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

    by_key = {}
    for item in examples_v11:
        aco = item['aco']
        by_key[(aco['aco_id'], aco['revision'])] = item
    rev7 = by_key[('ACO-2741', 7)]
    rev8 = by_key[('ACO-2741', 8)]
    policy = by_key[('ACO-3102', 2)]

    assert rev7['assurance']['status'] == 'PASS'
    assert rev7['review']['disposition'] == 'APPROVED'
    assert rev7['execution']['disposition'] == 'PASS'
    assert rev7['atlas_invoked'] is False
    assert rev7['merge_gate']['gate_status'] == 'PASS'
    assert rev7['merge_gate']['commit_sha'] == 'aaa1111deadbeef01'
    assert rev7['aco']['ownership']['horizonax_assurance'] == 'HORIZONAX'
    assert rev7['aco']['ownership']['execution_gate'] == 'KRISHNA'

    assert rev8['assurance']['status'] == 'STALE'
    assert rev8['review']['disposition'] == 'CHANGES_REQUIRED'
    assert rev8['execution']['disposition'] == 'HOLD'
    assert 'ASSURANCE_STALE' in rev8['execution']['reason_codes']
    assert rev8['merge_gate']['gate_status'] == 'STALE'
    assert rev8['merge_gate']['commit_sha'] == 'bbb2222cafebabe02'
    # Prior PASS history for commit A remains in append-only transition history.
    assert any(
        h.get('to_state') == 'MERGE_AUTHORIZED'
        and h.get('commit_sha') == 'aaa1111deadbeef01'
        for h in rev8['aco']['transition_history'])
    assert rev8['aco']['horizonax_assurance'].get('prior_pass_commit_sha') == (
        'aaa1111deadbeef01')

    assert policy['review']['disposition'] == 'CHANGES_REQUIRED'
    assert 'MISSING_REQUIRED_ASSURANCE_CLASS' in policy['review']['reason_codes']
    assert policy['execution']['disposition'] == 'HOLD'
    assert policy['atlas_invoked'] is False
    assert policy['merge_gate']['gate_status'] == 'HOLD'
    missing = runtime.clear.missing_policy_classes(policy['aco'])
    assert 'FIFO_SAFETY' in missing and 'FIFO_ORDERING' in missing

    # Programmatic stale transform: same aco_id, new revision/commit, old PASS preserved.
    assert stale_prog['aco']['aco_id'] == 'ACO-2741'
    assert stale_prog['aco']['revision'] == 8
    assert stale_prog['assurance']['status'] == 'STALE'
    assert stale_prog['execution']['disposition'] == 'HOLD'
    assert stale_prog['merge_gate']['gate_status'] == 'STALE'
    assert any(
        h.get('to_state') == 'MERGE_AUTHORIZED'
        and h.get('at_revision') == 7
        for h in stale_prog['aco']['transition_history'])
    # Old authorization cannot be reused for the new commit.
    assert runtime.krishna.execute(
        'APPROVED',
        {'status': 'PASS', 'missing': [], 'failed': [],
         'bound_commit_sha': 'aaa1111deadbeef01'},
        True,
        current_commit_sha='bbb2222cafebabe02',
    )['disposition'] == 'HOLD'

    for example in examples_v11 + [stale_prog]:
        errors = validate_aco_packet(example['aco'])
        assert errors == [], errors
        assert example['aco']['schema_version'] == SCHEMA_VERSION_V11

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
    if s.get('merge_gate'):
        print('  [SIM] Merge gate: ' + json.dumps(s['merge_gate']))
    if s.get('aco', {}).get('revision') is not None:
        print('  [SIM] ACO revision: %s @ %s' % (
            s['aco'].get('revision'),
            (s['aco'].get('source_binding') or {}).get('commit_sha')))
    print('  [SIM] Zeta recorded the local outcome.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Print simulated call history')
    parser.add_argument('--self-test', action='store_true', help='Check scenarios and gate bypass')
    parser.add_argument('--examples', action='store_true',
                        help='Print only ACO exchange example results')
    args = parser.parse_args()
    runtime, scenarios, examples, examples_v11, stale_prog = demo()
    self_test(runtime, scenarios, examples, examples_v11, stale_prog)
    all_examples = examples + examples_v11 + [stale_prog]
    if args.json:
        print(json.dumps({'simulation': True, 'scenarios': scenarios,
                          'examples': examples, 'examples_v11': examples_v11,
                          'stale_progression': stale_prog,
                          'history': runtime.history},
                         indent=2))
    elif args.self_test:
        print('PASS: missing evidence, revealed failure, good control, denied permission,')
        print('direct gate bypass, CDC/FIFO pass, CDC/FIFO hold, area objective hold,')
        print('ATLAS not required on happy paths, call order, earlier snapshot preservation,')
        print('ACO-2741 rev7 authorize / rev8 stale HOLD, and policy missing FIFO class HOLD.')
    elif args.examples:
        print('ACO EXCHANGE EXAMPLES -- ALL NAMED SYSTEMS ARE LOCAL MOCKS\n')
        for s in all_examples:
            print_scenario(s)
        print('\nNo production integration, real signoff, or tamper-proof log is demonstrated.')
    else:
        print('ACO DEMO -- ALL NAMED SYSTEMS ARE LOCAL MOCKS\n')
        print('Toy Zeta orchestrates HorizonAX -> CLEAR -> (ATLAS if disputed) -> KRISHNA.')
        print('Contracts: schemas/aco_exchange_v1.schema.json and aco_exchange_v1_1.schema.json')
        print('Scripted adder proposal: reduce modeled area from 100 toward a stated target.')
        for s in scenarios:
            print_scenario(s)
        print('\n--- ACO exchange examples (v1 + v1.1) ---')
        for s in all_examples:
            print_scenario(s)
        print('\nNo production integration, real signoff, or tamper-proof log is demonstrated.')
        print('Use --json to inspect every simulated call. Use --self-test to verify controls.')
        print('Use --examples to focus on exchange packets including stale-after-commit.')


if __name__ == '__main__':
    main()
