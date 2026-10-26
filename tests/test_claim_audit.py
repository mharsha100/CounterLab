"""Claim boundaries: citations, denominators, unknowns and rehashed fabrications."""
import copy
import unittest
from unittest.mock import patch

from counterlab.claim_audit import digest, project_claim_audit, resolve, verify_saved_audit
from counterlab.records import RecordError


class ClaimAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = project_claim_audit()

    def test_every_claim_citation_resolves_to_the_bound_original_record_field(self):
        report = self.audit['report']
        for record in report['records'].values():
            self.assertEqual(record['data_sha256'], digest(record['data']))
        for claim in report['claims']:
            self.assertTrue(claim['citations'])
            for citation in claim['citations']:
                data = report['records'][citation['record']]['data']
                self.assertEqual(resolve(data, citation['pointer']), citation['value'])
        self.assertEqual(self.audit['report_sha256'], digest(report))

    def test_rehashed_fabricated_answer_or_dropped_policy_is_not_accepted(self):
        for change in ('answer', 'policies', 'citation', 'omitted_question'):
            with self.subTest(change=change):
                saved = copy.deepcopy(self.audit)
                report = saved['report']
                if change == 'answer':
                    report['claims'][3]['answer'] = 'The model is the proven winner.'
                elif change == 'policies':
                    report['records']['evaluation']['data']['policies'].pop()
                elif change == 'citation':
                    report['claims'][0]['citations'][0]['pointer'] = '/source_contracts/sources/99'
                else:
                    report['claims'].pop()
                saved['report_sha256'] = digest(report)
                with patch('counterlab.claim_audit.project_claim_audit', return_value=self.audit):
                    with self.assertRaises(RecordError):
                        verify_saved_audit(saved)

    def test_self_hash_does_not_replace_reloading_verified_evidence(self):
        with patch('counterlab.claim_audit.project_source_regime', side_effect=RecordError('changed source')):
            with self.assertRaises(RecordError):
                verify_saved_audit(self.audit)

    def test_rehashed_static_source_audit_cannot_rewrite_the_contract_comparison(self):
        from counterlab.study_records import project_study
        study = copy.deepcopy(project_study())
        study['source_contracts']['differences'][0]['support'] = 'fabricated source rule'
        # Even if a local manifest was rehashed and the numerical study still
        # passes, the independently anchored static audit must remain unchanged.
        with patch('counterlab.claim_audit.project_study', return_value=study):
            with self.assertRaises(RecordError):
                project_claim_audit()

    def test_optional_full_reference_context_cannot_change_numeric_claims(self):
        from counterlab.source_records import project_source_regime
        source = project_source_regime()
        outputs = []
        for present in (False, True):
            source['verification']['published_data_verified'] = present
            with patch('counterlab.claim_audit.project_source_regime', return_value=source):
                audit = project_claim_audit()
            self.assertEqual(audit['verification']['full_upstream_artifact_verified_here'], present)
            outputs.append(audit['report_sha256'])
        self.assertEqual(*outputs)

    def test_saved_verification_labels_are_not_trusted_as_local_verification(self):
        saved = copy.deepcopy(self.audit)
        saved['verification'] = {'full_upstream_artifact_verified_here': 'fabricated'}
        with patch('counterlab.claim_audit.project_claim_audit', return_value=self.audit):
            result = verify_saved_audit(saved)
        self.assertEqual(result['verification_context'], self.audit['verification'])

    def test_unknown_parity_and_theorem_coverage_stay_unknown(self):
        claims = {claim['id']: claim for claim in self.audit['report']['claims']}
        self.assertEqual(claims['advantage']['status'], 'open')
        self.assertEqual(claims['verdict']['status'], 'open')
        self.assertFalse(any(citation['value'] for citation in claims['verdict']['citations'][:3]))
        self.assertTrue(any(check['state'] == 'different' for check in claims['contracts']['checks']))
        self.assertTrue(any(check['state'] == 'unknown' for check in claims['contracts']['checks']))
        self.assertNotIn('incompatible', claims['contracts']['answer'].lower())

    def test_reference_and_timing_denominators_cannot_be_combined(self):
        report = self.audit['report']
        summary = report['records']['source']['data']['summary']
        claims = {claim['id']: claim for claim in report['claims']}
        self.assertEqual(len(summary['rows']), 3)
        self.assertEqual(len(summary['history_intervention']), 10)
        self.assertIn('3 of 3', claims['reference']['answer'])
        self.assertIn('10 of 10', claims['timing']['answer'])
        policies = report['records']['evaluation']['data']['policies']
        self.assertEqual({row['difference_tasks'] for row in policies}, {2})
        self.assertEqual(len(report['records']['evaluation']['data']['tasks']), 8)
        self.assertEqual({row['our_optimum'] for row in summary['rows']}, {2624})

    def test_citation_resolution_rejects_missing_or_negative_array_indices(self):
        for pointer in ('x', '/rows/-1', '/rows/01', '/rows/2', '/missing'):
            with self.subTest(pointer=pointer), self.assertRaises((ValueError, KeyError, IndexError)):
                resolve({'rows': [5, 6]}, pointer)
        self.assertEqual(resolve({'a/b': {'c~d': 7}}, '/a~1b/c~0d'), 7)


if __name__ == '__main__':
    unittest.main()
