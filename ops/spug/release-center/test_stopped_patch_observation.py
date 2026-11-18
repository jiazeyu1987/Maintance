"""Real temporary-file checks for stopped patch provenance; no server access."""
import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import intruoyi_runtime_agent as agent
from backend_patch_contract import PATHS, PREFIX, full_release_config
from intruoyi_runtime import file_sha


class StoppedPatchObservationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name in PATHS:
            (self.root/name).write_bytes(b'actual immutable '+name.encode())
        self.digest = file_sha(self.root/'app.jar')
        self.info = dict(Id='backend-original', Image='original-image',
                         State=dict(Running=False, StartedAt='original-start'),
                         Config=dict(Labels={PREFIX+'root':self.root.as_posix(), PREFIX+'tag':'patch', PREFIX+'sha256':self.digest}),
                         HostConfig=dict(Binds=[self.root.as_posix()+'/'+n+':'+d+':ro' for n,d in PATHS.items()]),
                         Mounts=[dict(Type='bind',Source=(self.root/n).as_posix(),Destination=d,RW=False) for n,d in PATHS.items()],
                         NetworkSettings=dict(Networks={}))

    def invoke(self, after=None):
        def target_contract(config):
            # Files live on the test host; Docker's target bind grammar is Linux.
            if os.name == 'nt':
                root=config['Labels'][PREFIX+'root']
                config=copy.deepcopy(config)
                config['Labels'][PREFIX+'root']='/owned-patch'
                config['HostConfig']['Binds']=[b.replace(root,'/owned-patch') for b in config['HostConfig']['Binds']]
            return full_release_config(config)
        with patch.object(agent,'full_release_config',side_effect=target_contract), \
                patch.object(agent.remote,'inspect',return_value=after or self.info), patch.object(agent.remote,'run') as run:
            value = agent.backend_jar_sha({'backend':'backend'}, self.info)
            run.assert_not_called()
            return value

    def test_stopped_patch_reads_actual_readonly_mounted_bytes(self):
        self.assertEqual(self.invoke(), self.digest)

    def test_changed_file_wrong_source_or_writable_mount_is_rejected(self):
        for change in ('bytes','source','writable','bind'):
            with self.subTest(change=change):
                original = copy.deepcopy(self.info)
                if change=='bytes': (self.root/'app.jar').write_bytes(b'drift')
                elif change=='source': self.info['Mounts'][0]['Source'] += '.other'
                elif change=='writable': self.info['Mounts'][0]['RW'] = True
                else: self.info['HostConfig']['Binds'].append(self.root.as_posix()+':/yudao-server:ro')
                with self.assertRaises((ValueError, agent.RuntimeBlocked)): self.invoke()
                self.info = original
                (self.root/'app.jar').write_bytes(b'actual immutable app.jar')

    def test_container_identity_or_state_drift_is_rejected(self):
        for key,value in [('Id','replacement'),('Image','other-image'),('State',dict(Running=True,StartedAt='new'))]:
            after=copy.deepcopy(self.info); after[key]=value
            with self.subTest(key=key), self.assertRaisesRegex(agent.RuntimeBlocked,'changed during JAR'):
                self.invoke(after)


if __name__=='__main__':
    unittest.main()
