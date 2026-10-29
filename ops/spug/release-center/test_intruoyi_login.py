"""Login adapter contracts; real browser acceptance is a separate release check."""
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import intruoyi_login as login


class LoginVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('node.exe', 'cli.js'):
            (self.root / name).touch()
        self.credentials = {'username': 'private-user', 'password': 'private-password', 'tenantName': 'private-tenant'}
        (self.root / 'credentials.json').write_text(json.dumps(self.credentials), encoding='utf-8')
        self.config = {'loginVerification': {'nodePath': str(self.root / 'node.exe'),
            'cliPath': str(self.root / 'cli.js'), 'credentialsFile': str(self.root / 'credentials.json')}}
        self.binding = {'jobId': 'JOB-test', 'env': 'test', 'releaseTag': '2026-10-23-16-51-17',
                        'packageSha256': 'a' * 64}
        self.calls = []
        self.scripts = []
        self.report = {'authenticated': True, 'authenticationResponseObserved': True,
                       'authenticatedShellVisible': True, 'authenticatedUserId': 42,
                       'landedUrl': 'http://target:8081/user/profile'}

    def invoke(self):
        return login.verify_login(self.config, 'http://target:8081', self.root / 'evidence', self.binding)

    def fake_cli(self, command, **kwargs):
        self.calls.append((command, kwargs))
        operation = command[4]
        if operation == 'run-code':
            script = Path(command[-1])
            code = script.read_text(encoding='utf-8')
            self.scripts.append((script, code))
            # Unit stub for the CLI transport, not a simulated release acceptance.
            data = json.loads(code.split('const input = ', 1)[1].split(';\n', 1)[0])
            Path(data['screenshot']).write_bytes(b'unit screenshot boundary')
            return SimpleNamespace(returncode=0, stdout=json.dumps({'result': json.dumps(self.report)}))
        return SimpleNamespace(returncode=0, stdout=json.dumps({'status': 'closed' if operation == 'close' else 'open'}))

    def test_success_is_bound_sanitized_and_script_deleted(self):
        self.report['accessToken'] = 'MUST-NOT-PERSIST'
        with patch.object(login.subprocess, 'run', side_effect=self.fake_cli):
            result = self.invoke()
        self.assertEqual('passed', result['status'])
        self.assertEqual(self.binding, result['binding'])
        self.assertTrue(result['authenticated'])
        self.assertEqual(result, json.loads(Path(result['evidencePath']).read_text(encoding='utf-8')))
        self.assertEqual(['open', 'run-code', 'close'], [call[0][4] for call in self.calls])
        self.assertFalse(self.scripts[0][0].exists())
        public = json.dumps(result)
        for secret in [*self.credentials.values(), 'MUST-NOT-PERSIST']:
            self.assertNotIn(secret, public)
            self.assertNotIn(secret, repr([call[0] for call in self.calls]))
        self.assertTrue(all(call[1]['capture_output'] for call in self.calls))
        self.assertTrue(all(Path(call[1]['cwd']).parent == self.root for call in self.calls))

    def test_each_attempt_has_a_new_nonpersistent_session(self):
        with patch.object(login.subprocess, 'run', side_effect=self.fake_cli):
            first, second = self.invoke(), self.invoke()
        self.assertNotEqual(self.calls[0][0][2], self.calls[3][0][2])
        self.assertNotEqual(first['evidencePath'], second['evidencePath'])
        self.assertNotIn('--persistent', repr(self.calls))

    def test_saved_mode_capture_is_bound_to_source_commit_not_a_nonexistent_package(self):
        self.report['gxpAuditMode'] = 'DEVELOPMENT_DISABLED'
        binding = {'jobId': 'build-mode', 'gitCommit': 'a' * 40}
        with patch.object(login.subprocess, 'run', side_effect=self.fake_cli):
            result = login.verify_login(self.config, 'http://target:8081', self.root / 'source',
                                        binding, read_gxp_mode=True)
        self.assertEqual(result['gxpAuditMode'], 'DEVELOPMENT_DISABLED')
        self.assertEqual(result['binding'], binding)
        for mode in (None, 'LOCAL_POLICY', ''):
            self.report['gxpAuditMode'] = mode
            with patch.object(login.subprocess, 'run', side_effect=self.fake_cli):
                with self.assertRaises(login.LoginVerificationError):
                    login.verify_login(self.config, 'http://target:8081', self.root / 'source',
                                       binding, read_gxp_mode=True)

    def test_missing_configuration_fails_without_browser(self):
        self.config = {}
        with patch.object(login.subprocess, 'run') as run:
            with self.assertRaises(login.LoginVerificationError):
                self.invoke()
            run.assert_not_called()

    def test_all_four_binding_fields_and_exact_names_are_required(self):
        for field in tuple(self.binding):
            binding = dict(self.binding)
            del self.binding[field]
            with self.assertRaises(login.LoginVerificationError):
                self.invoke()
            self.binding = binding
        self.binding['packageSha256'] = 'bad'
        with self.assertRaises(login.LoginVerificationError):
            self.invoke()

    def test_invalid_origin_login_page_or_authentication_is_rejected(self):
        cases = [('landedUrl', 'http://other/user/profile'), ('landedUrl', 'http://target:8081/login'),
                 ('landedUrl', 'http://target:8081/user/profile?token=secret'),
                 ('authenticated', False), ('authenticationResponseObserved', False),
                 ('authenticatedShellVisible', False), ('authenticatedUserId', True)]
        original = dict(self.report)
        for field, value in cases:
            self.report = dict(original, **{field: value})
            with patch.object(login.subprocess, 'run', side_effect=self.fake_cli):
                with self.assertRaises(login.LoginVerificationError):
                    self.invoke()
            self.assertFalse(self.scripts[-1][0].exists())
        self.assertFalse(list((self.root / 'evidence').glob('*.json')))

    def test_cli_timeout_and_secret_output_do_not_escape(self):
        def fail(command, **kwargs):
            if command[4] == 'run-code':
                raise subprocess.TimeoutExpired(['private-password'], 200, output='accessToken=secret')
            return self.fake_cli(command, **kwargs)
        with patch.object(login.subprocess, 'run', side_effect=fail):
            with self.assertRaises(login.LoginVerificationError) as caught:
                self.invoke()
        self.assertNotIn('private-password', str(caught.exception))
        self.assertNotIn('accessToken', str(caught.exception))
        self.assertEqual('close', self.calls[-1][0][4])
        self.assertFalse(list(self.root.glob('release-login-*/login.private.js')))

    def test_echoed_code_without_structured_result_cannot_pass(self):
        def echo(command, **kwargs):
            result = self.fake_cli(command, **kwargs)
            if command[4] == 'run-code':
                result.stdout = '{"code":"return {authenticated:true}"}'
            return result
        with patch.object(login.subprocess, 'run', side_effect=echo):
            with self.assertRaises(login.LoginVerificationError):
                self.invoke()

    def test_close_failure_fails_and_still_deletes_script(self):
        def fail_close(command, **kwargs):
            result = self.fake_cli(command, **kwargs)
            if command[4] == 'close':
                result.returncode = 1
            return result
        with patch.object(login.subprocess, 'run', side_effect=fail_close):
            with self.assertRaisesRegex(login.LoginVerificationError, 'cleanup'):
                self.invoke()
        self.assertFalse(self.scripts[0][0].exists())

    def test_only_ui_login_and_positive_authentication_gates(self):
        code = login._SCRIPT
        self.assertIn('login.click()', code)
        self.assertIn('page.waitForResponse', code)
        self.assertIn("response.request().method() === 'POST'", code)
        self.assertIn('body.code !== 0', code)
        self.assertIn('body.data.accessToken', code)
        self.assertIn("page.locator('.v-layout')", code)
        self.assertNotIn('networkidle', code)
        self.assertNotIn('pageerror', code)
        self.assertNotIn('request.post(', code)
        self.assertNotIn('fetch(', code)


if __name__ == '__main__':
    unittest.main()
