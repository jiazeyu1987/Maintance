"""Explicit current source selection must preserve original history routes."""
import unittest
from unittest.mock import patch
import smallapp_adapter as adapter
import smallapp_simple as simple

class SourceRotation(unittest.TestCase):
    def fixture(self):
        old=dict(product='smallapp',server='58',mode='safe',applicationId='old',targetServers={},overwriteTargetServers={},selectable=False,progressRoot='/old',pythonPath='/python')
        new=dict(old,applicationId='new',selectable=True,progressRoot='/new')
        return dict(nas='registered',servers=['57','58','59'],bindings=[old,new])

    def test_retired_binding_is_public_and_original_progress_stays_bound(self):
        config=self.fixture()
        with patch.object(adapter,'read_json',return_value=config):
            public=simple.public_configuration()
        self.assertEqual([r['selectable'] for r in public['bindings']],[False,True])
        self.assertEqual(simple.progress_binding(dict(applicationId='old',request=dict(action='FULL')),config)['progressRoot'],'/old')

    def test_two_current_sources_for_same_simple_choices_are_rejected(self):
        config=self.fixture();config['bindings'][0]['selectable']=True
        with patch.object(adapter,'read_json',return_value=config):
            with self.assertRaisesRegex(adapter.Refused,'SIMPLE_BINDING_AMBIGUOUS'):simple.configuration()

    def test_missing_selection_state_is_not_guessed(self):
        config=self.fixture();del config['bindings'][0]['selectable']
        with patch.object(adapter,'read_json',return_value=config):
            with self.assertRaisesRegex(adapter.Refused,'SIMPLE_BINDING_SELECTION_STATE_REQUIRED'):simple.configuration()

    def test_missing_replacement_mapping_is_not_guessed(self):
        config=self.fixture();del config['bindings'][0]['overwriteTargetServers']
        with patch.object(adapter,'read_json',return_value=config):
            with self.assertRaisesRegex(adapter.Refused,'SIMPLE_REPLACEMENT_MAPPING_REQUIRED'):simple.configuration()

if __name__=='__main__':unittest.main()
