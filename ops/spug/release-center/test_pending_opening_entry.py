import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import intruoyi_runtime_agent as agent


class PendingOpeningEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.profile={'stagingRoot':self.temp.name,'backend':'backend','frontend':'frontend',
                      'entryUrl':'http://public','acceptanceUrl':'http://acceptance'}
        self.rows={'backend':{'Id':'b','Image':'bi','State':{'Running':True}},
                   'frontend':{'Id':'f','Image':'fi','State':{'Running':False}}}
        self.root=Path(self.temp.name)/'2026-11-22-21-56-28';self.root.mkdir()
        self.marker={'releaseTag':self.root.name,'backendId':'b','frontendId':'f',
                     'images':{'backend':{'id':'bi'},'frontend':{'id':'fi'}}}
        self.save_marker()
        (self.root/'deployment-pending.json').write_text(json.dumps(self.marker),encoding='utf-8')
        self.patcher=patch.object(agent.remote,'inspect',side_effect=lambda name:self.rows[name])
        self.patcher.start();self.addCleanup(self.patcher.stop)

    def save_marker(self):
        (self.root/'runtime-opening-pending.private.json').write_text(json.dumps(self.marker),encoding='utf-8')

    def test_normal_pending_backend_uses_acceptance_until_public_frontend_runs(self):
        self.assertEqual(agent.verification_entry(self.profile,False),'http://acceptance')
        self.rows['frontend']['State']['Running']=True
        self.assertEqual(agent.verification_entry(self.profile,False),'http://public')

    def test_missing_marker_does_not_switch_entry(self):
        (self.root/'runtime-opening-pending.private.json').unlink()
        self.assertEqual(agent.verification_entry(self.profile,False),'http://public')

    def test_changed_frontend_or_images_rejected(self):
        for field,value in [('frontendId','different'),('images',{'backend':{'id':'wrong'},'frontend':{'id':'fi'}})]:
            with self.subTest(field=field):
                original=self.marker[field];self.marker[field]=value;self.save_marker()
                with self.assertRaises(agent.RuntimeBlocked):agent.verification_entry(self.profile,False)
                self.marker[field]=original;self.save_marker()

    def test_other_backend_marker_cannot_authorize_entry(self):
        self.marker['backendId']='old';self.save_marker()
        self.assertEqual(agent.verification_entry(self.profile,False),'http://public')

    def test_maintenance_entry_retains_existing_behavior(self):
        self.assertEqual(agent.verification_entry(self.profile,True),'http://acceptance')


if __name__=='__main__':unittest.main()
