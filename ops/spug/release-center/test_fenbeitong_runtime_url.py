import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import intruoyi_runtime_agent as agent
from intruoyi_runtime import RuntimeBlocked


class FenbeitongRuntimeUrlTest(unittest.TestCase):
    prop = 'yudao.erp.fenbeitong-assistant.public-url'

    def profile(self, environment='test', host='172.30.30.58'):
        return dict(environment=environment, host=host, backend='backend',
                    fenbeitongAssistantHost='fenbeitong-assistant',
                    fenbeitongAssistantUrl='http://' + host + ':18734/')

    def test_actual_replacement_and_reopen_use_target_url_and_keep_internal_host(self):
        for environment, host in [('test', '172.30.30.58'), ('prod', '172.30.30.57')]:
            original = dict(Id='old', Image='old-image', State={'Running': False}, Mounts=[],
                            Config={'Env': ['JAVA_OPTS=-Xmx512m', 'UNCHANGED=yes']},
                            HostConfig={'PortBindings': {}}, NetworkSettings={'Networks': {}})
            profile = self.profile(environment, host)
            for maintenance in (True, False):
                requests = []
                def docker(method, path, body=None):
                    requests.append((path, copy.deepcopy(body)))
                    return {'Id': 'new'}
                actual = dict(Image='new-image', HostConfig={'PortBindings': {}}, Mounts=[])
                with tempfile.TemporaryDirectory() as root, \
                        patch.object(agent.remote, 'inspect', side_effect=[original, actual]), \
                        patch.object(agent, 'private_json'), patch.object(agent, 'docker', side_effect=docker):
                    agent.replace(profile, Path(root), 'backend', 'new-image', 'candidate', maintenance)
                created = next(body for path, body in requests if path.startswith('/containers/create'))
                env = dict(item.split('=', 1) for item in created['Env'])
                self.assertIn('-D' + self.prop + '=' + profile['fenbeitongAssistantUrl'], env['JAVA_OPTS'])
                self.assertIn('-Dyudao.erp.fenbeitong-assistant.assistant-host=fenbeitong-assistant', env['JAVA_OPTS'])
                self.assertIn('-Xmx512m', env['JAVA_OPTS'])
                self.assertEqual(env['UNCHANGED'], 'yes')
                original['Config'] = created

    def test_repeated_configuration_removes_old_jvm_and_cli_overrides(self):
        config = {'Env': ['JAVA_OPTS=-Xmx512m -D' + self.prop + '=http://old:18734/',
                          'INTRUOYI_EXTRA_ARGS=--other=true --' + self.prop + '=http://old:18734/',
                          'ARGS=--keep=ok --' + self.prop + '=http://old:18734/']}
        for _ in range(2):
            agent.configure_fenbeitong(config, self.profile())
        env = dict(item.split('=', 1) for item in config['Env'])
        self.assertEqual(env['JAVA_OPTS'].count(self.prop), 1)
        self.assertNotIn(self.prop, env['ARGS'])
        self.assertNotIn(self.prop, env['INTRUOYI_EXTRA_ARGS'])
        self.assertIn('--other=true', env['INTRUOYI_EXTRA_ARGS'])
        self.assertIn('--keep=ok', env['ARGS'])

    def test_invalid_or_missing_registration_fails_before_remote_preflight(self):
        values = ['', None, 'http://172.30.30.57:18734/', 'http://172.30.30.58:18733/',
                  'http://user:password@172.30.30.58:18734/', 'http://172.30.30.58:18734/?x=y',
                  'http://172.30.30.58:18734/#fragment', 'http://172.30.30.58:18734/path/',
                  'http://172.30.30.58:18734/ --bad=true']
        profiles = [dict(self.profile(), fenbeitongAssistantUrl=value) for value in values]
        missing = self.profile()
        del missing['fenbeitongAssistantUrl']
        profiles.append(missing)
        for profile in profiles:
            with self.subTest(profile=profile), patch.object(agent.remote, 'inspect') as inspect, \
                    self.assertRaisesRegex(RuntimeBlocked, 'Fenbeitong'):
                agent.preflight(profile, {})
            inspect.assert_not_called()

    def test_rehearsal_cannot_register_business_url(self):
        with self.assertRaises(RuntimeBlocked):
            agent.configure_fenbeitong({'Env': []}, self.profile('rehearsal'))


if __name__ == '__main__':
    unittest.main()
