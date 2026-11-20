import ast
from pathlib import Path
import unittest
import json
import tempfile
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

class EntryContract(unittest.TestCase):
    def test_finish_opening_calls_binding_before_removing_acceptance(self):
        source=Path(__file__).with_name('intruoyi_runtime_agent.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='finish_reopen')
        body=ast.get_source_segment(source,node)
        self.assertIn('synchronize_backup_source',body)
        self.assertLess(body.index('synchronize_backup_source'),body.index("['docker', 'rm'"))

    def test_remote_transport_includes_binding_module(self):
        source=Path(__file__).with_name('intruoyi_runtime.py').read_text(encoding='utf-8')
        self.assertIn('release_backup_source.py',source)

    def test_completed_acceptance_consumes_binding_retry_marker(self):
        source=Path(__file__).with_name('intruoyi_runtime_agent.py').read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='finish_reopen')
        body=ast.get_source_segment(source,node)
        self.assertIn('binding_pending.unlink()',body)
        self.assertLess(body.index("['docker', 'rm'"),body.index('binding_pending.unlink()'))

    def test_binding_failure_is_not_reported_as_success_or_cleaned_up(self):
        source=Path(__file__).with_name('intruoyi_runtime_agent.py').read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='finish_reopen')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            run=Mock()
            observe=Mock()
            binding=Mock(side_effect=RuntimeError('binding failed'))
            def require(ok,message):
                if not ok:raise ValueError(message)
            ns={'directory':lambda *a:root,'json':json,'require':require,'datetime':datetime,'timezone':timezone,
                'private_json':lambda p,v:p.write_text(json.dumps(v),encoding='utf-8'),
                'remote':SimpleNamespace(inspect=lambda n:{'Id':'backend-new','State':{'Running':True}},run=run),
                'docker':Mock(),'quote':lambda x:x,'health':Mock(),'gxp_release_mode':Mock(),'observe':observe,
                'BACKUP_SOURCE_PROGRAM':'registered-stage-program'}
            exec(compile(ast.Module(body=[node],type_ignores=[]),'<finish_reopen>','exec'),ns)
            profile={'backend':'backend','frontend':'frontend','acceptanceFrontend':'acceptance','writers':[],
                     'backupSourceBinding':{'configured':True}}
            candidate={'releaseTag':'r1','images':{}}
            with patch.dict(sys.modules,{'release_backup_source':SimpleNamespace(synchronize=binding)}), \
                    patch('release_runtime_metadata.align',return_value={'status':'ALIGNED'}):
                with self.assertRaisesRegex(RuntimeError,'binding failed'):ns['finish_reopen'](profile,candidate)
            self.assertEqual(json.loads((root/'backup-source-binding-pending.private.json').read_text())['backendId'],'backend-new')
            observe.assert_not_called()
            ns['docker'].assert_not_called()
            self.assertEqual(binding.call_args.kwargs['stage_program'], 'registered-stage-program')
            self.assertFalse(any(c.args[0][:2]==['docker','rm'] for c in run.call_args_list))

    def test_normal_backend_retry_requires_exact_persisted_identity(self):
        source=Path(__file__).with_name('intruoyi_runtime_agent.py').read_text(encoding='utf-8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='reopen')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'release';root.mkdir()
            candidate={'releaseTag':'release','images':{'backend':{'id':'b'},'frontend':{'id':'f'}}}
            (root/'deployment-pending.json').write_text(json.dumps(candidate))
            backend={'Id':'actual','Image':'b','Config':{'Env':['INTRUOYI_RELEASE_MAINTENANCE=false']}}
            def require(ok,message):
                if not ok:raise ValueError(message)
            finish=Mock(return_value={'done':True})
            ns={'check_fence':Mock(),'remote':SimpleNamespace(inspect=lambda name:backend if name=='b' else {'Image':'f'}),
                'Path':Path,'json':json,'require':require,'health':Mock(),'gxp_release_mode':Mock(), 'finish_reopen':finish}
            exec(compile(ast.Module(body=[node],type_ignores=[]),'<reopen>','exec'),ns)
            profile={'backend':'b','frontend':'f','stagingRoot':temp,'backupSourceBinding':{'registered':True}}
            with self.assertRaisesRegex(ValueError,'not in maintenance'):ns['reopen'](profile)
            marker=root/'backup-source-binding-pending.private.json'
            marker.write_text(json.dumps(dict(releaseTag='release',backendId='old',images=candidate['images'])))
            with self.assertRaisesRegex(ValueError,'target changed'):ns['reopen'](profile)
            marker.write_text(json.dumps(dict(releaseTag='release',backendId='actual',images=candidate['images'])))
            self.assertEqual(ns['reopen'](profile),{'done':True})
            finish.assert_called_once()

if __name__=='__main__':unittest.main()
