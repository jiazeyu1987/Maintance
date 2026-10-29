import unittest
import sys
from pathlib import Path
from unittest.mock import patch
from intruoyi_build import build_python
from intruoyi_recovery_agent import validate_database_identity
from backup_retry import test_retry_available, validate_test_retry, bind_attempt_roots
from types import SimpleNamespace
from intruoyi_runtime_agent import configure_fenbeitong
from intruoyi_runtime import RuntimeBlocked


class IntegrationConfigTests(unittest.TestCase):
    def test_legitimate_quoted_database_name_can_have_hyphens(self):
        value=['ruoyi-vue-pro','utf8mb4','utf8mb4_unicode_ci']
        self.assertEqual(validate_database_identity(value), value)

    def test_database_name_or_charset_cannot_inject_sql(self):
        for value in [['db`name','utf8mb4','utf8mb4_unicode_ci'], ['db','utf8mb4; DROP DATABASE x','x'], ['db','utf8mb4','x--y']]:
            with self.assertRaises(RuntimeBlocked): validate_database_identity(value)

    def test_capture_only_test_retry_keeps_original_files_in_separate_attempt(self):
        original={'id':'JOB-1111111111','action':'publish-test','target':'test','releaseTag':'2026-10-27-13-12-40',
                  'status':'failed','effectsStarted':True,'resolution':{'recoveryEvidence':{'recoveryKind':'capture-not-sealed','restored':True,'databaseRestored':False}}}
        package={'releaseTag':original['releaseTag'],'stage':'built','outcomes':{'test':{'deployment':{'jobId':original['id']}}}}
        state={'jobs':[original],'packages':[package]}
        e=SimpleNamespace(state=state,c={'targets':{'test':{'stagingRoot':'/test/packages'}}},save=lambda:None)
        self.assertEqual(test_retry_available(state,package),original['id'])
        validate_test_retry(e,package,original['id'])
        job={'id':'JOB-2222222222','action':'publish-test','releaseTag':package['releaseTag'],'payload':{'retryOf':original['id']}}
        bind_attempt_roots(e,job)
        self.assertEqual(job['runtimeStagingRoots']['test'],'/test/packages/attempts/JOB-2222222222')
        self.assertNotIn('runtimeStagingRoots',original)

    def test_unreconciled_effects_do_not_enable_test_retry(self):
        p={'releaseTag':'v','stage':'built'}
        state={'jobs':[{'id':'old','action':'publish-test','target':'test','releaseTag':'v','status':'failed'}]}
        self.assertIsNone(test_retry_available(state,p))

    def test_service_uses_registered_python_instead_of_host(self):
        with patch('sys.executable', 'C:/Python/pythonservice.exe'):
            actual = str(Path(sys.base_prefix) / 'python.exe')
            self.assertEqual(build_python({'executionMode': 'windows-service', 'pythonExecutable': actual}), actual)

    def test_service_without_interpreter_stops(self):
        with self.assertRaisesRegex(ValueError, 'pythonExecutable'):
            build_python({'executionMode': 'windows-service'})

    def test_service_host_is_not_a_script_interpreter(self):
        with self.assertRaisesRegex(ValueError, 'pythonservice.exe'):
            build_python({'executionMode': 'windows-service', 'pythonExecutable': str(Path(sys.base_prefix) / 'pythonservice.exe')})

    def test_deploy_replaces_only_assistant_host_and_preserves_other_flags(self):
        config = {'Env': ['UNCHANGED=one', 'JAVA_OPTS=-Xmx512m -Dyudao.erp.fenbeitong-assistant.assistant-host=old', 'INTRUOYI_EXTRA_ARGS=--existing=true --yudao.erp.fenbeitong-assistant.assistant-host=old --other=2']}
        configure_fenbeitong(config, {'environment': 'test', 'fenbeitongAssistantHost': '172.30.30.58'})
        env = dict(x.split('=', 1) for x in config['Env'])
        self.assertEqual(env['UNCHANGED'], 'one')
        self.assertIn('--existing=true', env['INTRUOYI_EXTRA_ARGS'])
        self.assertIn('--other=2', env['INTRUOYI_EXTRA_ARGS'])
        self.assertNotIn('=old', env['INTRUOYI_EXTRA_ARGS'])
        self.assertNotIn('assistant-host=', env['INTRUOYI_EXTRA_ARGS'])
        self.assertEqual(env['JAVA_OPTS'].count('assistant-host='), 1)
        self.assertIn('-Xmx512m', env['JAVA_OPTS'])
        self.assertIn('-Dyudao.erp.fenbeitong-assistant.assistant-host=172.30.30.58', env['JAVA_OPTS'])

    def test_no_integration_registered_leaves_configuration_unchanged(self):
        config = {'Env': ['INTRUOYI_EXTRA_ARGS=--existing=true']}
        configure_fenbeitong(config, {'environment': 'prod'})
        self.assertEqual(config['Env'], ['INTRUOYI_EXTRA_ARGS=--existing=true'])

    def test_isolation_cannot_be_pointed_at_real_assistant(self):
        with self.assertRaises(RuntimeBlocked):
            configure_fenbeitong({'Env': []}, {'environment': 'rehearsal', 'fenbeitongAssistantHost': '172.30.30.57'})

    def test_host_cannot_inject_shell_arguments(self):
        with self.assertRaises(RuntimeBlocked):
            configure_fenbeitong({'Env': []}, {'environment': 'prod', 'fenbeitongAssistantHost': '172.30.30.57 --bad=true'})
