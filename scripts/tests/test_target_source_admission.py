"""Explicit source sharing preserves the original physical target and claims."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'backend/src/main/resources')]
from recovery_engine import digest
from recovery_target_sources import admit_target_source
from recovery_control_target_availability import available
from recovery_main_target import target_configuration


class TargetSources(unittest.TestCase):
    def fixture(self, policy=True):
        target = dict(sourceConfigRef='current-source', targetId='physical-main',
            mainApplication={'schemaVersion':'RegisteredMainApplication/v2'},
            replacement=dict(schemaVersion='RegisteredApplicationReplacement/v2',
                stateRoot='/private/original-claims', lockPath='/private/original.lock'),
            resourceBudget={'original':'retained'})
        value = dict(targets={'main-target':target},
            sources={'current-source':{}, 'historical-source':{}})
        if policy:
            value['targetSourceAdmissions'] = dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',
                targets={'main-target':['current-source','historical-source']})
        return value

    def request(self, source='historical-source'):
        return dict(targetConfigRef='main-target', sourceConfigRef=source)

    def test_explicit_historical_source_returns_original_target_and_keeps_digest(self):
        value=self.fixture(); before=deepcopy(value)
        target=value['targets']['main-target']; original=digest(target)
        self.assertIs(admit_target_source(value,self.request()),target)
        self.assertEqual(value,before)
        self.assertEqual(digest(target),original)

    def test_legacy_primary_source_remains_exact_and_cross_source_requires_admission(self):
        value=self.fixture(False)
        self.assertIs(admit_target_source(value,self.request('current-source')),value['targets']['main-target'])
        with self.assertRaisesRegex(Exception,'TARGET_SOURCE_MISMATCH'):
            admit_target_source(value,self.request())

    def test_unknown_or_unlisted_source_and_target_are_refused(self):
        value=self.fixture()
        for request in (self.request('unknown'), dict(sourceConfigRef='historical-source',targetConfigRef='unknown')):
            with self.subTest(request=request), self.assertRaises(Exception):
                admit_target_source(value,request)
        value['sources']['unlisted']={}
        with self.assertRaisesRegex(Exception,'TARGET_SOURCE_MISMATCH'):
            admit_target_source(value,self.request('unlisted'))

    def test_invalid_policy_cannot_be_ignored_even_for_primary_source(self):
        invalid=(None, [], {}, dict(schemaVersion='unknown',targets={}),
            dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',targets=[]),
            dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',targets={'unknown':['current-source']}),
            dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',targets={'main-target':['historical-source']}),
            dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',targets={'main-target':['current-source','unknown']}),
            dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',targets={'main-target':['current-source']*2}),
            dict(schemaVersion='RegisteredTargetSourceAdmissions/v1',targets={'main-target':['current-source','../unsafe']}))
        for policy in invalid:
            value=self.fixture();value['targetSourceAdmissions']=policy
            with self.subTest(policy=policy), self.assertRaisesRegex(Exception,'TARGET_SOURCE_ADMISSION_INVALID'):
                admit_target_source(value,self.request('current-source'))

    def test_cross_source_policy_only_registers_safe_main_replacement_targets(self):
        for field in ('mainApplication','replacement'):
            for invalid in (None, [], {'schemaVersion':'unknown'}):
                value=self.fixture();value['targets']['main-target'][field]=invalid
                with self.subTest(field=field,invalid=invalid), self.assertRaisesRegex(Exception,'TARGET_SOURCE_ADMISSION_INVALID'):
                    admit_target_source(value,self.request())

    def test_unclaimed_selection_preserves_original_target_and_checks_retained_claims(self):
        value=self.fixture(); before=deepcopy(value)
        native=SimpleNamespace(document=lambda pin:value)
        with patch('recovery_replace.available',return_value=True) as claims:
            self.assertTrue(available(native,{'original':'owner-pin'},'main-target','historical-source',observe_main=False))
            claims.assert_called_once_with(value['targets']['main-target'])
        with patch('recovery_replace.available',return_value=False):
            self.assertFalse(available(native,{'original':'owner-pin'},'main-target','historical-source',observe_main=False))
        self.assertEqual(value,before)

    def test_selection_rejects_undeclared_source_before_claim_checks(self):
        value=self.fixture(False);native=SimpleNamespace(document=lambda pin:value)
        with patch('recovery_replace.available') as claims:
            with self.assertRaisesRegex(Exception,'TARGET_SOURCE_MISMATCH'):
                available(native,{},'main-target','historical-source',observe_main=False)
            claims.assert_not_called()

    def test_main_execution_uses_same_admission_and_original_target(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();state=root/'claims';data=state/'runtime'
            data.mkdir(parents=True)
            value=self.fixture();target=value['targets']['main-target']
            target['replacement']['stateRoot']=str(state)
            target.update(dataRoot=str(data),dataPaths=[str(data)])
            value['operationsRoot']=str(root/'operations')
            source={'archiveRoots':[str(root/'archives')]}
            before=deepcopy(value)
            with patch('recovery_main_target.validate'),patch('recovery_replace.validate'):
                self.assertIs(target_configuration(value,self.request(),source),target)
                value.pop('targetSourceAdmissions')
                with self.assertRaisesRegex(Exception,'TARGET_SOURCE_MISMATCH'):
                    target_configuration(value,self.request(),source)
            self.assertEqual(value['targets'],before['targets'])


if __name__=='__main__':unittest.main()
