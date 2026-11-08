"""Real local evidence files; no installation, service action, or backup."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import importlib

import closeout_contracts as contracts

TASK = Path(__file__).resolve().parent


class MixedGenerationTests(unittest.TestCase):
    def read(self, name):
        return json.loads((TASK / name).read_text(encoding='utf-8'))

    def fixture(self, task):
        for name in ('automatic-control-installation-57.json', 'release-build-0d44578.json',
                     'automatic-spug-installation-0d44578.json', 'release-build-b5c8817.json'):
            (task / name).write_bytes((TASK / name).read_bytes())
        previous = self.read('automatic-control-installation-57.json')
        build = self.read('release-build-b5c8817.json')
        # Local contract data only: this is never presented as a real installation.
        successor = copy.deepcopy(previous)
        successor.update(schemaVersion='AutomaticSourceControlUpgrade/v1', sourceCommit=build['targetCommit'],
            packageSha256=build['packageSha256'], fileManifestSha256=build['fileManifestSha256'],
            fileCount=build['fileCount'], predecessorInstallationPin=contracts.file_pin(task, 'automatic-control-installation-57.json'),
            buildPin=contracts.file_pin(task, 'release-build-b5c8817.json'),
            retainedTargetControlUnchanged=True, epochUnchanged=True, physicalSourceUnchanged=True,
            previousGenerationsRetained=True, backupPerformed=False, restorePerformed=False)
        successor['controllers'][0].update(pid=999999, previousPid=previous['controllers'][0]['pid'],
            engine=previous['controllers'][0]['engine'].replace('0d44578', 'b5c8817'))
        first = contracts.controller_generation(previous, 0)
        successor['controllerGenerations'] = [dict(first, sourceCommit=build['targetCommit'],
            packageSha256=build['packageSha256'], buildPin=successor['buildPin']),
            dict(contracts.controller_generation(previous, 1), installationPin=successor['predecessorInstallationPin'])]
        successor['retainedSpugInstallationPin'] = contracts.file_pin(task, 'automatic-spug-installation-0d44578.json')
        return previous, successor

    def test_original_pair_exposes_each_actual_package_generation(self):
        original = self.read('automatic-control-installation-57.json')
        first = contracts.controller_generation(original, 0)
        second = contracts.controller_generation(original, 1)
        self.assertEqual(first['role'], 'SOURCE')
        self.assertEqual(second['role'], 'MAIN_TARGET')
        self.assertEqual(first['fileManifestSha256'], original['fileManifestSha256'])

    def test_successor_retains_original_target_and_physical_epoch(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            previous, successor = self.fixture(task)
            contracts.validate_source_successor(task, successor)
            self.assertEqual(contracts.controller_generation(successor, 1)['sourceCommit'], previous['sourceCommit'])
            self.assertNotEqual(contracts.controller_generation(successor, 0)['sourceCommit'], previous['sourceCommit'])

    def test_changed_predecessor_original_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            _, successor = self.fixture(task)
            with (task / 'automatic-control-installation-57.json').open('ab') as output:
                output.write(b' ')
            with self.assertRaisesRegex(AssertionError, 'ORIGINAL_EVIDENCE_CHANGED'):
                contracts.validate_source_successor(task, successor)

    def test_retained_target_or_epoch_or_claimed_build_cannot_drift(self):
        for mode in ('target', 'epoch', 'policy', 'build', 'generation', 'spug'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                task = Path(directory)
                _, value = self.fixture(task)
                if mode == 'target': value['controllers'][1]['pid'] += 1
                elif mode == 'epoch': value['epoch']['epochId'] = 'f' * 64
                elif mode == 'policy': value['policy']['databaseUuid'] = 'different'
                elif mode == 'build': value['packageSha256'] = 'f' * 64
                elif mode == 'generation': value['controllerGenerations'][1]['sourceCommit'] = value['sourceCommit']
                else: value['retainedSpugInstallationPin']['sha256'] = 'f' * 64
                with self.assertRaises(AssertionError):
                    contracts.validate_source_successor(task, value)

    def test_actual_async_launcher_two_requires_owner_success_bound_original(self):
        record = dict(nativeLauncherExitCode=2, nativeDispatch=dict(launcherActualExitCode=2,
            launcherState='TERMINAL_UNKNOWN', ownerActualExitCode=0, ownerState='SUCCEEDED',
            resolution='ORIGINAL_OWNER_TERMINAL_AFTER_ASYNC_REPLY',
            originalReplyPin=dict(path='/actual/reply.json', bytes=100, sha256='f' * 64)))
        contracts.validate_native_dispatch(record)
        for key, value in (('launcherActualExitCode', 3), ('ownerActualExitCode', 2),
                           ('launcherState', 'SUCCEEDED'), ('originalReplyPin', None)):
            changed = copy.deepcopy(record)
            changed['nativeDispatch'][key] = value
            with self.assertRaises(AssertionError): contracts.validate_native_dispatch(changed)


class SuccessorInstallerTests(unittest.TestCase):
    def test_capture_program_paths_can_move_only_with_identical_packaged_bytes(self):
        module=importlib.import_module('install_automatic_source_successor')
        old={'source':dict(configurationPath='/physical/capture.json',sourceIdentityPath='/physical/id.json',stagingRoot='/physical/stage',
            captureCommand=['/python','-B','/old/formal/capture.py'],toolPaths=['/mysqlbinlog','/old/formal/tool.py'])}
        new=copy.deepcopy(old);new['source']['captureCommand'][2]='/new/formal/capture.py';new['source']['toolPaths'][1]='/new/formal/tool.py'
        files={'formal/capture.py':'a'*64,'formal/tool.py':'b'*64}
        self.assertEqual(len(module.validate_source_rebinding(old,new,'/old','/new',files,files)),2)
        for mode in ('capture','identity','stage','argument','program','unknown'):
            changed=copy.deepcopy(new)
            if mode=='capture':changed['source']['configurationPath']='/other/capture.json'
            elif mode=='identity':changed['source']['sourceIdentityPath']='/other/id.json'
            elif mode=='stage':changed['source']['stagingRoot']='/other/stage'
            elif mode=='argument':changed['source']['captureCommand'][0]='/other/python'
            elif mode=='program':changed['source']['toolPaths'][1]='/new/unknown.py'
            else:changed['source']['unreviewed']='value'
            with self.assertRaisesRegex(AssertionError,'PHYSICAL_SOURCE_BINDING_CHANGED'):
                module.validate_source_rebinding(old,changed,'/old','/new',files,files)
        with self.assertRaisesRegex(AssertionError,'SOURCE_CAPTURE_PROGRAM_BYTES_CHANGED'):
            module.validate_source_rebinding(old,new,'/old','/new',files,dict(files,**{'formal/tool.py':'c'*64}))

    def test_staged_engine_reuse_requires_exact_real_members_and_bytes(self):
        module=importlib.import_module('install_automatic_source_successor')
        import hashlib
        for mode in ('valid','missing','changed','extra','extra-directory','manifest','hardlink'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                engine=Path(directory)/'engine';(engine/'formal').mkdir(parents=True)
                (engine/'formal/tool.py').write_bytes(b'print(1)\n')
                files={'formal/tool.py':hashlib.sha256((engine/'formal/tool.py').read_bytes()).hexdigest()}
                manifest=dict(variant='standard',fileVerification=True,payloadContentVerification=True,files=files,
                    packageSha256=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest())
                (engine/'package.json').write_text(json.dumps(manifest),encoding='utf-8')
                meta=module.local_pin(engine/'package.json')
                if mode=='missing':(engine/'formal/tool.py').unlink()
                elif mode=='changed':(engine/'formal/tool.py').write_bytes(b'changed')
                elif mode=='extra':(engine/'unexpected.py').write_bytes(b'extra')
                elif mode=='extra-directory':(engine/'unexpected').mkdir()
                elif mode=='manifest':(engine/'package.json').write_bytes(b'{}')
                elif mode=='hardlink':
                    import os
                    os.link(engine/'formal/tool.py',Path(directory)/'second-link.py')
                if mode=='valid':self.assertEqual(module.verify_staged_engine(engine,files,meta),1)
                else:
                    with self.assertRaises(AssertionError):module.verify_staged_engine(engine,files,meta)

    def test_resume_requires_explicit_flag_and_fixed_failed_commit(self):
        module=importlib.import_module('install_automatic_source_successor')
        parsed=module.parser().parse_args(['--commit','f'*40])
        self.assertFalse(parsed.resume_staged_engine)
        with self.assertRaisesRegex(AssertionError,'UNREVIEWED_STAGED_RESUME'):
            module.validate_resume_identity('f'*40,'automatic-control-installation-57.json')

    def test_any_following_configuration_or_dropin_refuses_preconfiguration_resume(self):
        module=importlib.import_module('install_automatic_source_successor')
        for mode in ('valid','owner','control','stage','receipt','dropin','argv'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);configuration=root/'configuration';dropins=root/'service.d'
                configuration.mkdir();dropins.mkdir();engine=root/'engine-automatic-0dc7429'
                generation='automatic-0dc7429'
                if mode in ('owner','control','stage','receipt'):
                    prefix={'owner':'repository-','control':'control-','stage':'staged-source-','receipt':'installation-source-'}[mode]
                    (configuration/(prefix+generation+'.json')).write_bytes(b'{}')
                elif mode=='dropin':(dropins/'z-source-automatic-0dc7429.conf').write_bytes(b'existing')
                elif mode=='argv':(dropins/'z-other.conf').write_bytes(str(engine).encode())
                if mode=='valid':module.verify_preconfiguration_stage(configuration,dropins,'0dc7429',engine)
                else:
                    with self.assertRaises(AssertionError):module.verify_preconfiguration_stage(configuration,dropins,'0dc7429',engine)

    def test_only_source_planning_modules_may_change(self):
        module = importlib.import_module('install_automatic_source_successor')
        old = {'control/recovery_control_smallapp.py': 'a' * 64,
               'control/recovery_control_smallapp_native.py': 'b' * 64,
               'common/repository_minimal.py': 'c' * 64}
        new = dict(old, **{'control/recovery_control_smallapp.py': 'd' * 64})
        self.assertEqual(module.validate_package_transition(old, new), ['control/recovery_control_smallapp.py'])
        for changed in (dict(new, **{'common/repository_minimal.py': 'e' * 64}),
                        {key:value for key,value in new.items() if key != 'common/repository_minimal.py'}):
            with self.assertRaisesRegex(AssertionError, 'SOURCE_ONLY_PACKAGE_SCOPE_CHANGED'):
                module.validate_package_transition(old, changed)

    def test_default_cli_does_not_apply(self):
        module = importlib.import_module('install_automatic_source_successor')
        parsed = module.parser().parse_args(['--commit', 'f' * 40])
        self.assertFalse(parsed.apply)

    def test_embedded_installer_compiles_with_reviewed_pure_helpers(self):
        module = importlib.import_module('install_automatic_source_successor')
        import inspect
        compiled = 'from pathlib import Path\nimport hashlib\n' + inspect.getsource(module.local_pin) + '\n' + inspect.getsource(module.rebind_document) + '\n' + module.SCRIPT
        compile(compiled, '<source-successor-check>', 'exec')

    def test_exclusive_output_preserves_first_real_file(self):
        module = importlib.import_module('install_automatic_source_successor')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'observation.json'
            module.exclusive_json(path, dict(status='FAIL', error='actual-first-result'))
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):module.exclusive_json(path, dict(status='PASS'))
            self.assertEqual(path.read_bytes(), before)

    def test_rebind_repins_new_real_file_and_preserves_unrelated_source_identity(self):
        module = importlib.import_module('install_automatic_source_successor')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, new = root / 'old', root / 'new'
            old.mkdir(); new.mkdir()
            (old / 'control.py').write_bytes(b'old bytes')
            (new / 'control.py').write_bytes(b'new actual bytes')
            original = dict(program=module.local_pin(old / 'control.py'),
                            sourceIdentity='physical-source', capturePath='/unchanged/capture.json',
                            PYTHONPATH=old.as_posix()+'/control:'+old.as_posix()+'/common:/retained/deps')
            updated = module.rebind_document(original, old.as_posix(), new.as_posix())
            self.assertEqual(updated['program'], module.local_pin(new / 'control.py'))
            self.assertEqual(updated['sourceIdentity'], original['sourceIdentity'])
            self.assertEqual(updated['capturePath'], original['capturePath'])
            self.assertEqual(updated['PYTHONPATH'],new.as_posix()+'/control:'+new.as_posix()+'/common:/retained/deps')
            self.assertEqual((old / 'control.py').read_bytes(), b'old bytes')


if __name__ == '__main__':
    unittest.main()
