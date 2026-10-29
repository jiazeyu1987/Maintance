import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from intruoyi_rehearsal_agent import PREFIX,restore_entry_state


class RestoreEntryTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        (self.folder/'rehearsal-owned.json').write_text(json.dumps({'owner':PREFIX}))
        self.profile={key:PREFIX+'-'+key for key in ('frontend','backend','database','redis','minio','acceptanceFrontend','network')}
        self.profile['environment']='rehearsal'
        self.remote=Mock()
        self.remote.run.return_value=b''

    def test_no_resources_or_restore_evidence_allows_first_restore(self):
        self.assertEqual(restore_entry_state(self.profile,self.folder,self.remote),{'state':'not-started','mutations':False})

    def test_any_partial_resource_requires_existing_restore_handling(self):
        for index,value in enumerate([self.profile['backend'],self.profile['network'],self.profile['database']+'-data']):
            with self.subTest(resource=value):
                outputs=[b'',b'',b''];outputs[index]=value.encode()
                self.remote.run.side_effect=outputs
                self.assertEqual(restore_entry_state(self.profile,self.folder,self.remote)['state'],'started')

    def test_preserved_restore_evidence_prevents_reimport(self):
        (self.folder/'application.properties').write_text('isolated')
        self.assertEqual(restore_entry_state(self.profile,self.folder,self.remote)['state'],'started')

    def test_unowned_seed_rejected(self):
        (self.folder/'rehearsal-owned.json').write_text('{}')
        with self.assertRaises(ValueError):restore_entry_state(self.profile,self.folder,self.remote)

    def test_failed_inspection_not_treated_as_absent(self):
        self.remote.run.side_effect=RuntimeError('SSH failed')
        with self.assertRaises(RuntimeError):restore_entry_state(self.profile,self.folder,self.remote)

if __name__=='__main__':unittest.main()
