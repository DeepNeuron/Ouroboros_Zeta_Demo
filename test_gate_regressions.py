"""Run beside aco_simulated_stack.py: python3 -m unittest -v test_gate_regressions."""
import copy
import unittest
import aco_simulated_stack as demo


class GateRegressions(unittest.TestCase):
    def packet(self):
        return demo.load_example('v1_1/aco2741_rev7_authorized.json')

    def run_packet(self, packet, **kwargs):
        return demo.MockZetaRuntime().run_packet(copy.deepcopy(packet), **kwargs)

    def assert_blocked(self, packet, validation_rejection=False):
        try:
            result = self.run_packet(packet)
        except ValueError:
            if validation_rejection:
                return
            raise
        self.assertIn(result['execution']['disposition'], ('HOLD', 'DENY'))
        self.assertIn(result['merge_gate']['gate_status'], ('HOLD', 'DENY', 'STALE'))
        self.assertNotIn('MERGE_AUTHORIZED', result['merge_gate']['reason_codes'])
        self.assertTrue(result['merge_gate']['reason_codes'])
        return result

    def test_01_good_control(self):
        result = self.run_packet(self.packet())
        self.assertEqual(result['execution']['disposition'], 'PASS')
        self.assertEqual(result['merge_gate']['gate_status'], 'PASS')

    def test_02_denied_permission(self):
        result = self.run_packet(self.packet(), permit_local_release=False)
        self.assertEqual(result['execution']['disposition'], 'HOLD')
        self.assertEqual(result['merge_gate']['gate_status'], 'HOLD')
        self.assertNotIn('MERGE_AUTHORIZED', result['merge_gate']['reason_codes'])
        self.assertIn('LOCAL_PERMISSION_DENIED', result['merge_gate']['reason_codes'])

    def test_03_removed_evidence(self):
        p = self.packet(); p['evidence'] = []
        self.assert_blocked(p)

    def test_04_stale_evidence(self):
        p = self.packet()
        for e in p['evidence']: e['freshness'] = 'STALE'
        self.assert_blocked(p)

    def test_05_failed_evidence(self):
        p = self.packet()
        for e in p['evidence']: e['status'] = 'PROPERTY_VIOLATED'
        self.assert_blocked(p)

    def test_06_open_dispute_preserved(self):
        p = self.packet()
        p['atlas_dispute'].update(required=True, status='OPEN',
                                  disputed_claim='required FIFO safety evidence')
        result = self.assert_blocked(p)
        self.assertEqual(result['aco']['atlas_dispute']['status'], 'OPEN')
        self.assertEqual(result['aco']['atlas_dispute']['disputed_claim'],
                         p['atlas_dispute']['disputed_claim'])

    def test_07_missing_assurance_binding(self):
        p = self.packet(); del p['horizonax_assurance']['bound_commit_sha']
        self.assert_blocked(p, validation_rejection=True)

    def test_08_wrong_evidence_binding(self):
        p = self.packet()
        for e in p['evidence']: e['bound_commit_sha'] = 'bbb2222cafebabe02'
        self.assert_blocked(p)

    def test_09_unknown_check_status(self):
        p = self.packet()
        for c in p['horizonax_assurance']['checks']: c['status'] = 'BANANA'
        self.assert_blocked(p, validation_rejection=True)

    def test_10_changed_commit_consistent_reasons(self):
        p = self.packet(); p['source_binding']['commit_sha'] = 'bbb2222cafebabe02'
        self.assert_blocked(p)

    def test_11_area_labels_cannot_override_values(self):
        p = demo.load_example('area_goal_hold.json')
        for c in p['acceptance_criteria']: c['status'] = 'SATISFIED'
        for c in p['horizonax_assurance']['checks']: c['status'] = 'PASS'
        p['acceptance_status'] = 'SATISFIED'
        result = self.run_packet(p)
        self.assertIn(result['execution']['disposition'], ('HOLD', 'DENY'))

    def test_12_history_and_input_preserved(self):
        p = demo.load_example('v1_1/aco2741_rev8_stale.json')
        before = copy.deepcopy(p)
        result = self.assert_blocked(p)
        self.assertEqual(p, before)
        history = before['transition_history']
        self.assertEqual(result['aco']['transition_history'][:len(history)], history)

    def test_13_missing_evidence_binding(self):
        p = self.packet()
        for e in p['evidence']:
            del e['bound_commit_sha']
        self.assert_blocked(p)

    def test_14_unknown_evidence_status(self):
        p = self.packet()
        for e in p['evidence']:
            e['status'] = 'BANANA'
        self.assert_blocked(p)

    def test_15_dangling_evidence_ref(self):
        p = self.packet()
        p['acceptance_criteria'][0]['evidence_refs'] = ['missing-ev-id']
        with self.assertRaises(ValueError):
            self.run_packet(p)

    def test_16_empty_obligations_do_not_authorize(self):
        p = self.packet()
        p['acceptance_criteria'] = []
        p['required_assurance_classes'] = []
        p['change_class'] = 'UNKNOWN_CLASS'
        p['horizonax_assurance']['checks'] = []
        p['horizonax_assurance']['assurance_classes_present'] = []
        p['evidence'] = []
        p['acceptance_status'] = 'SATISFIED'
        self.assert_blocked(p)

    def test_17_cannot_weaken_domain_policy(self):
        p = self.packet()
        # Attempt to declare a weaker class set than DOMAIN_POLICY requires.
        p['required_assurance_classes'] = ['CDC', 'TIMING']
        p['horizonax_assurance']['assurance_classes_present'] = ['CDC', 'TIMING']
        p['horizonax_assurance']['checks'] = [
            c for c in p['horizonax_assurance']['checks']
            if c.get('class') in ('CDC', 'TIMING')
        ]
        result = self.assert_blocked(p)
        self.assertIn('MISSING_REQUIRED_ASSURANCE_CLASS',
                      result['review']['reason_codes'])

    def test_18_numeric_objective_boundary(self):
        p = demo.load_example('area_goal_hold.json')
        for c in p['acceptance_criteria']:
            if c['type'] == 'OBJECTIVE_THRESHOLD':
                c['observed'] = 70
                c['target'] = 70
                c['status'] = 'NOT_SATISFIED'
            else:
                c['status'] = 'SATISFIED'
        for c in p['horizonax_assurance']['checks']:
            c['status'] = 'PASS'
        p['acceptance_status'] = 'SATISFIED'
        result = self.run_packet(p)
        self.assertEqual(result['execution']['disposition'], 'PASS')

        p2 = demo.load_example('area_goal_hold.json')
        for c in p2['acceptance_criteria']:
            c['status'] = 'SATISFIED'
        for c in p2['horizonax_assurance']['checks']:
            c['status'] = 'PASS'
        p2['acceptance_status'] = 'SATISFIED'
        result2 = self.run_packet(p2)
        self.assertIn(result2['execution']['disposition'], ('HOLD', 'DENY'))
        area = [c for c in result2['aco']['acceptance_criteria']
                if c['type'] == 'OBJECTIVE_THRESHOLD'][0]
        self.assertEqual(area['submitted_status'], 'SATISFIED')
        self.assertEqual(area['status'], 'NOT_SATISFIED')

    def test_19_resolved_reject_does_not_authorize(self):
        p = self.packet()
        p['atlas_dispute'].update(
            required=True, status='RESOLVED',
            resolution_disposition='REJECT',
            disputed_claim='FIFO overflow exception denied',
            resolution='reject waiver',
            rationale='adverse evidence stands')
        self.assert_blocked(p)

    def test_20_merge_projection_open_dispute_prefills(self):
        p = self.packet()
        p['atlas_dispute'].update(required=True, status='OPEN',
                                  disputed_claim='open claim')
        # Prefill green labels that must not override an OPEN dispute.
        p['clear_review']['disposition'] = 'APPROVED'
        p['execution_gate']['disposition'] = 'PASS'
        p['merge_gate'] = {
            'aco_id': p['aco_id'], 'revision': p['revision'],
            'commit_sha': p['source_binding']['commit_sha'],
            'gate_status': 'PASS',
            'reason_codes': ['MERGE_AUTHORIZED'],
        }
        result = self.assert_blocked(p)
        self.assertEqual(result['aco']['atlas_dispute']['status'], 'OPEN')
        direct = demo.project_merge_gate(
            p,
            execution={'disposition': 'PASS', 'reason_codes': ['CLEAR_APPROVED']},
            assurance={'status': 'PASS', 'missing': [], 'failed': [],
                       'bound_commit_sha': p['source_binding']['commit_sha']},
            review={'disposition': 'APPROVED'},
            atlas={'status': 'OPEN'},
            permit_local_release=True,
        )
        self.assertIn(direct['gate_status'], ('HOLD', 'DENY', 'STALE'))
        self.assertNotIn('MERGE_AUTHORIZED', direct['reason_codes'])

    def test_21_unknown_freshness_blocks(self):
        p = self.packet()
        for e in p['evidence']:
            e['freshness'] = 'UNKNOWN'
        self.assert_blocked(p)

    def test_22_missing_freshness_blocks(self):
        p = self.packet()
        for e in p['evidence']:
            del e['freshness']
        self.assert_blocked(p)

    def test_23_null_freshness_blocks(self):
        p = self.packet()
        for e in p['evidence']:
            e['freshness'] = None
        self.assert_blocked(p)

    def test_24_unsupported_required_criterion_blocks(self):
        p = self.packet()
        p['acceptance_criteria'].append({
            'criterion_id': 'new-unsupported',
            'type': 'UNSUPPORTED_PHYSICS_CHECK',
            'required': True,
            'status': 'SATISFIED',
        })
        result = self.assert_blocked(p)
        unsupported = [c for c in result['aco']['acceptance_criteria']
                       if c['criterion_id'] == 'new-unsupported'][0]
        self.assertEqual(unsupported['submitted_status'], 'SATISFIED')
        self.assertEqual(unsupported['status'], 'NOT_EVALUATED')
        self.assertIn('UNSUPPORTED_REQUIRED_CRITERION',
                      result['execution']['reason_codes']
                      + result['review']['reason_codes']
                      + result['assurance'].get('reason_codes', []))

    def test_25_declared_fail_blocks_despite_green_checks(self):
        p = self.packet()
        p['horizonax_assurance']['status'] = 'FAIL'
        result = self.assert_blocked(p)
        self.assertEqual(result['assurance']['status'], 'FAIL')
        self.assertIn('ASSURANCE_STATUS_CONFLICT',
                      result['assurance'].get('reason_codes', [])
                      + result['execution']['reason_codes']
                      + result['review']['reason_codes'])

    def test_26_declared_incomplete_blocks_despite_green_checks(self):
        p = self.packet()
        p['horizonax_assurance']['status'] = 'INCOMPLETE'
        result = self.assert_blocked(p)
        self.assertEqual(result['assurance']['status'], 'INCOMPLETE')
        self.assertIn('ASSURANCE_STATUS_CONFLICT',
                      result['assurance'].get('reason_codes', [])
                      + result['execution']['reason_codes']
                      + result['review']['reason_codes'])

    def _assert_assurance_status_serialization(self, declared):
        p = self.packet()
        before = copy.deepcopy(p)
        p['horizonax_assurance']['status'] = declared
        result = self.assert_blocked(p)
        internal = result['assurance']
        serialized = result['aco']['horizonax_assurance']
        self.assertEqual(internal.get('declared_status'), declared)
        self.assertEqual(internal.get('derived_status'), 'PASS')
        self.assertEqual(internal.get('status'), declared)
        self.assertEqual(serialized.get('declared_status'), declared)
        self.assertEqual(serialized.get('derived_status'), 'PASS')
        self.assertEqual(serialized.get('status'), declared)
        self.assertEqual(serialized.get('submitted_status'), declared)
        self.assertIn('ASSURANCE_STATUS_CONFLICT',
                      internal.get('reason_codes', [])
                      + result['execution']['reason_codes']
                      + result['review']['reason_codes'])
        self.assertNotIn('MERGE_AUTHORIZED', result['merge_gate']['reason_codes'])
        self.assertEqual(before['transition_history'],
                         result['aco']['transition_history'][
                             :len(before['transition_history'])])
        # Input object passed to run_packet is deep-copied inside the helper;
        # the caller's packet mutation for the test fixture is local only.
        return result

    def test_27_declared_fail_serialization_preserves_derived_pass(self):
        self._assert_assurance_status_serialization('FAIL')

    def test_28_declared_incomplete_serialization_preserves_derived_pass(self):
        self._assert_assurance_status_serialization('INCOMPLETE')


if __name__ == '__main__':
    unittest.main(verbosity=2)
