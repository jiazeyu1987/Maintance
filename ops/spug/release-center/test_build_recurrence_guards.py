"""Release input/real archive contracts; fixtures do not claim server acceptance."""
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

import intruoyi_build as builder
import release_precheck as checks

PREFIX = 'cn/iocoder/yudao/module/mes/service/pro/route/'
CLASSES = ('MesRouteSnapshotMigrationCli', 'MesRouteLegacySummaryIdentity', 'MesRouteLegacySummaryMigration')
SOURCE_FILES = (
    'IntRuoyiBackend/pom.xml', 'IntRuoyiFronted/package.json', 'IntRuoyiFronted/pnpm-lock.yaml',
    'IntRuoyiBackend/sql/mysql/release-sources.json',
    'IntRuoyiBackend/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/ReleaseRuntimeEndpoint.java',
    *('IntRuoyiBackend/yudao-module-mes/src/main/java/'+PREFIX+name+'.java' for name in CLASSES),
    'scripts/preflight/check-menu-migrations.py',
)


def jar_fixture(path, missing=None, duplicate=False):
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, 'w') as jar:
        for name in CLASSES:
            if name != missing:
                jar.writestr(PREFIX+name+'.class', b'unit-structural-fixture')
    monitor = io.BytesIO()
    with zipfile.ZipFile(monitor, 'w') as jar:
        jar.writestr('cn/iocoder/yudao/framework/tracer/config/ReleaseRuntimeEndpoint.class', b'fixture')
    with zipfile.ZipFile(path, 'w') as outer:
        outer.writestr('BOOT-INF/lib/yudao-module-mes-1.jar', nested.getvalue())
        if duplicate:
            outer.writestr('BOOT-INF/lib/yudao-module-mes-2.jar', nested.getvalue())
        outer.writestr('BOOT-INF/lib/yudao-spring-boot-starter-monitor-1.jar', monitor.getvalue())
        outer.writestr('org/springframework/boot/loader/launch/PropertiesLauncher.class', b'fixture')


class ArtifactGuardTest(unittest.TestCase):
    def guard(self, name, *args, **kwargs):
        function = getattr(builder, name, None)
        self.assertTrue(callable(function), 'Formal build is missing '+name)
        return function(*args, **kwargs)

    def test_nested_real_zip_requires_each_cli_support_class(self):
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory)/'app.jar'
            jar_fixture(jar)
            self.assertEqual(self.guard('verify_backend_jar', jar)['status'], 'passed')
            for name in CLASSES:
                jar_fixture(jar, missing=name)
                with self.subTest(missing=name), self.assertRaisesRegex(ValueError, name):
                    self.guard('verify_backend_jar', jar)

    def test_duplicate_module_cannot_hide_ambiguous_classpath(self):
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory)/'app.jar'
            jar_fixture(jar, duplicate=True)
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                self.guard('verify_backend_jar', jar)

    def test_offline_report_requires_bounded_error_and_every_identity(self):
        binding = dict(releaseTag='candidate', migrationId='migration', imageId='sha256:'+'a'*64,
                       operationId='offline-check', packageIdentity='b'*64)
        report = dict(binding, schemaVersion='route-snapshot-migration/v1', status='ERROR',
                      errorCode='COMMAND_FAILED', mode='READINESS')
        self.guard('validate_offline_cli_report', report, binding, 3)
        for key in report:
            changed = dict(report, **{key:'wrong'})
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.guard('validate_offline_cli_report', changed, binding, 3)
        for code in (0, 1, 2, 137):
            with self.subTest(code=code), self.assertRaises(ValueError):
                self.guard('validate_offline_cli_report', report, binding, code)
        with self.assertRaises(ValueError):
            self.guard('validate_offline_cli_report', dict(report, updatedCount=0), binding, 3)

    def test_explicit_gxp_requirement_cannot_silently_publish_formal_mode(self):
        with self.assertRaisesRegex(ValueError, 'GxP'):
            self.guard('validate_required_gxp_mode', {'requiredGxpAuditMode':'DEVELOPMENT_DISABLED'}, 'FORMAL')
        self.guard('validate_required_gxp_mode', {'requiredGxpAuditMode':'DEVELOPMENT_DISABLED'}, 'DEVELOPMENT_DISABLED')

    def test_committed_source_contract_rejects_uncommitted_repairs(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)
            git('init', '-q')
            git('config', 'user.name', 'Release contract test')
            git('config', 'user.email', 'release-test@localhost')
            for name in SOURCE_FILES:
                p = repo/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('fixture', encoding='utf-8')
            git('add', '.')
            git('commit', '-qm', 'complete-contract')
            complete = git('rev-parse', 'HEAD').decode().strip()
            missing = repo/SOURCE_FILES[-2]
            git('rm', '--', SOURCE_FILES[-2]); git('commit', '-qm', 'missing-cli-support')
            incomplete = git('rev-parse', 'HEAD').decode().strip()
            missing.write_text('uncommitted repair', encoding='utf-8')
            executor = SimpleNamespace(c={'repo':str(repo)}, run=lambda args, **kw:subprocess.check_output(args, stderr=subprocess.PIPE))
            self.assertEqual(self.guard('validate_source_contract', executor, complete)['commit'], complete)
            with self.assertRaisesRegex(ValueError, 'MesRouteLegacySummaryMigration'):
                self.guard('validate_source_contract', executor, incomplete)

    def test_image_probe_timeout_removes_its_container_and_never_exposes_output(self):
        function = getattr(builder, 'verify_backend_image', None)
        self.assertTrue(callable(function))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            jar_fixture(root/'compiled.jar')
            commands = []
            def run(command, **kwargs):
                commands.append(command)
                if command[1] == 'create': return b'a'*64
                if command[1] == 'cp':
                    Path(command[-1]).write_bytes((root/'compiled.jar').read_bytes())
                return b''
            executor = SimpleNamespace(run=run)
            with patch('build_artifact_guard.subprocess.run', side_effect=subprocess.TimeoutExpired('probe',45)), \
                    self.assertRaisesRegex(ValueError, 'timed out'):
                function(executor, {'id':'job','releaseTag':'tag'}, {'id':'sha256:'+'b'*64}, root/'compiled.jar', root/'proof')
            probes = [c for c in commands if c[1] == 'create' and '--read-only' in c]
            self.assertEqual(len(probes), 1, 'Use a named/id-bound container so timeout cannot orphan the CLI')
            self.assertIn('none', probes[0])
            self.assertIn(['docker','rm','--force','a'*64], commands)

    def test_formal_build_calls_artifact_guard_before_export_or_nas_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree_root = root/'build'; worktree_root.mkdir()
            config = dict(repo='unit-repo', gxpConfigurationSourceUrl='http://source.invalid',
                          buildWorktreeRoot=str(worktree_root), nasPath=str(root/'nas'),
                          localRuntimeImages={'backend':'base-app','frontend':'base-web'})
            from test_direct_release import POLICY
            config['releaseWorkflow'] = dict(POLICY)
            job = {'id':'build-hook','payload':{'commit':'a'*40}}
            commands = []; steps = []
            def run(command, **kwargs):
                commands.append(command)
                if 'rev-parse' in command: return ('a'*40).encode()
                if command[0] == 'git' and 'log' in command: return b'aaaaaaa Unit release change\n'
                if 'worktree' in command and 'add' in command:
                    worktree = Path(job['buildWorktree'])
                    (worktree/'scripts/preflight').mkdir(parents=True)
                    (worktree/'scripts/preflight/check-menu-migrations.py').write_text('fixture',encoding='utf-8')
                    (worktree/'IntRuoyiBackend/yudao-server/target').mkdir(parents=True)
                    jar_fixture(worktree/'IntRuoyiBackend/yudao-server/target/yudao-server-exec.jar')
                    (worktree/'IntRuoyiBackend/script/deploy/int-ruoyi-test').mkdir(parents=True)
                    (worktree/'IntRuoyiBackend/script/deploy/int-ruoyi-test/nginx.conf').write_text('fixture',encoding='utf-8')
                    (worktree/'IntRuoyiFronted/dist-intruoyi-test').mkdir(parents=True)
                if command[:3] == ['docker','image','inspect']: return ('sha256:'+'b'*64).encode()
                if command[:2] == ['docker','create']: return b'unit-container'
                if command[:2] == ['docker','cp']:
                    Path(command[-1]).write_bytes((root/'packages'/job['releaseTag']/'build-context/release-info.json').read_bytes())
                return b''
            executor = SimpleNamespace(c=config,root=root,run=run,save=lambda:None,
                step=lambda job,name:steps.append(name),state={'packages':[],
                    'environments':{e:{'baselineStatus':'registered','ledgerRecords':[]} for e in ('test','prod','backup')}})
            with patch.object(builder,'validate_source_contract',return_value={'commit':'a'*40}), \
                 patch.object(builder,'verify_login',return_value={'gxpAuditMode':'DEVELOPMENT_DISABLED'}), \
                 patch.object(builder,'check_local_space',return_value=[]), patch.object(builder,'connect_nas'), \
                 patch.object(builder,'migration_inputs',return_value=([],[],{})), \
                 patch.object(builder,'target_input_plan',return_value={}), \
                 patch.object(builder,'install_frontend'), patch.object(builder.shutil,'which',return_value='unit-tool'), \
                 patch.object(builder,'verify_backend_image',side_effect=ValueError('artifact contract rejected')) as artifact, \
                 patch.object(builder,'publish_nas') as upload:
                with self.assertRaisesRegex(ValueError,'artifact contract rejected'):
                    builder.build(executor,job)
            artifact.assert_called_once()
            upload.assert_not_called()
            self.assertIn('verify-packaged-backend-contract',steps)
            self.assertFalse(any(c[:2]==['docker','save'] for c in commands))
            self.assertNotIn('sealedPackage',job)


class DirectDiagnosticTest(unittest.TestCase):
    def test_direct_build_diagnostic_does_not_require_rehearsal_profile(self):
        # Use the exact supported policy declaration from the current executor tests.
        from test_direct_release import POLICY
        executor = SimpleNamespace(c={'releaseWorkflow':dict(POLICY)}, state={
            'jobs':[], 'environments':{e:{'baselineStatus':'registered'} for e in ('test','prod','backup')}})
        with patch.object(checks, 'rehearsal_profile', side_effect=AssertionError('cancelled rehearsal requested')):
            result = checks.workflow(executor, {'id':'check', 'payload':{'operation':'build-release'}}, None)
        self.assertEqual(result['registeredTargets'], ['test','prod','backup'])

    def test_direct_production_precheck_accepts_tested_stage_but_requires_test_proof(self):
        from test_release_precheck import PrecheckTest
        from test_direct_release import POLICY
        fixture = PrecheckTest(); fixture.setUp()
        executor = fixture.e
        executor.c['releaseWorkflow'] = dict(POLICY)
        fixture.package['stage'] = 'tested'
        executor.technical_passed = Mock(return_value=True)
        job = fixture.job('promote-prod')
        with patch.object(checks, 'passed_rehearsal', create=True, side_effect=AssertionError('cancelled rehearsal')):
            checks.workflow(executor, job, fixture.package)
        executor.technical_passed.assert_called_once_with(fixture.package, 'test')
        executor.technical_passed.return_value = False
        with self.assertRaises(ValueError):
            checks.workflow(executor, job, fixture.package)

    def test_direct_target_diagnostic_uses_same_executor_validation_basis(self):
        from test_release_precheck import PrecheckTest
        from test_direct_release import POLICY
        for operation, stage, target in [('promote-prod','tested','prod'), ('promote-backup','prod-accepted','backup')]:
            fixture = PrecheckTest(); fixture.setUp()
            executor = fixture.e; executor.c['releaseWorkflow'] = dict(POLICY)
            fixture.package['stage'] = stage
            fixture.package['outcomes'] = {'prod':{'acceptance':{'status':'passed'}}}
            executor.technical_passed = Mock(return_value=True)
            executor.check_deployment_order = Mock()
            executor.direct_validation_basis = Mock(return_value={'status':'bound'})
            job = fixture.job(operation)
            if target == 'backup':
                fixture.obs.update(releaseTag=fixture.package['releaseTag'],
                    images={r:fixture.manifest['images'][r]['id'] for r in ('backend','frontend')})
                executor.state['environments']['backup'] = dict(fixture.obs)
            fixture.run_check(job)
            self.assertEqual(job['status'], 'succeeded', job.get('error'))
            executor.direct_validation_basis.assert_called_once()
            self.assertEqual(executor.direct_validation_basis.call_args.args, (fixture.package,target))


if __name__ == '__main__':
    unittest.main()
