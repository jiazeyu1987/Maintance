import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import intruoyi_runtime_agent as agent
from intruoyi_runtime import RuntimeBlocked


class InvoicePrintRuntimeConfigTest(unittest.TestCase):
    url = 'http://172.30.30.58:18733/'
    prop = 'yudao.erp.invoice-voucher-print-assistant.public-url'

    def profile(self):
        return dict(environment='test', backend='backend', host='172.30.30.58',
                    invoiceVoucherPrintAssistantUrl=self.url)

    def test_actual_backend_replacement_and_reopen_keep_public_url(self):
        original = dict(Id='old', Image='old-image', State={'Running': False}, Mounts=[],
                        Config={'Env': ['JAVA_OPTS=-Xmx512m -Dyudao.erp.invoice-voucher-print-assistant.assistant-host=internal-assistant', 'UNCHANGED=yes']},
                        HostConfig={'PortBindings': {}}, NetworkSettings={'Networks': {}})
        for maintenance in (True, False):
            requests = []
            def docker(method, path, body=None):
                requests.append((path, copy.deepcopy(body)))
                return {'Id': 'new'}
            actual = dict(Image='new-image', HostConfig={'PortBindings': {}}, Mounts=[])
            with tempfile.TemporaryDirectory() as root, \
                    patch.object(agent.remote, 'inspect', side_effect=[original, actual]), \
                    patch.object(agent, 'private_json'), patch.object(agent, 'docker', side_effect=docker):
                agent.replace(self.profile(), Path(root), 'backend', 'new-image', 'candidate', maintenance)
            created = next(body for path, body in requests if path.startswith('/containers/create'))
            env = dict(item.split('=', 1) for item in created['Env'])
            self.assertIn('-D' + self.prop + '=' + self.url, env['JAVA_OPTS'])
            self.assertEqual(env['UNCHANGED'], 'yes')
            self.assertIn('-Xmx512m', env['JAVA_OPTS'])
            self.assertIn('-Dyudao.erp.invoice-voucher-print-assistant.assistant-host=internal-assistant', env['JAVA_OPTS'])
            original['Config'] = created

    def test_no_registration_leaves_original_unchanged(self):
        config = {'Env': ['JAVA_OPTS=-Xmx512m']}
        before = copy.deepcopy(config)
        agent.configure_invoice_print(config, {'environment': 'prod'})
        self.assertEqual(before, config)

    def test_registered_value_replaces_old_properties_once(self):
        config = {'Env': ['JAVA_OPTS=-Xmx512m -D' + self.prop + '=http://old:18733/',
                          'INTRUOYI_EXTRA_ARGS=--other=true --' + self.prop + '=http://old:18733/']}
        agent.configure_invoice_print(config, self.profile())
        agent.configure_invoice_print(config, self.profile())
        env = dict(item.split('=', 1) for item in config['Env'])
        self.assertEqual(env['JAVA_OPTS'].count(self.prop), 1)
        self.assertNotIn(self.prop, env['INTRUOYI_EXTRA_ARGS'])
        self.assertIn('--other=true', env['INTRUOYI_EXTRA_ARGS'])

    def test_invalid_registration_rejected_before_remote_preflight(self):
        for value in ('', None, 'http://user:password@172.30.30.58:18733/',
                      self.url + '?token=bad', self.url + '#frag', self.url + ' $(bad)',
                      'http://172.30.30.57:18733/', 'http://172.30.30.58:80/'):
            profile = dict(self.profile(), invoiceVoucherPrintAssistantUrl=value)
            with self.subTest(value=value), patch.object(agent.remote, 'inspect') as inspect, \
                    self.assertRaises(RuntimeBlocked):
                agent.preflight(profile, {})
            inspect.assert_not_called()

    def test_rehearsal_cannot_target_business_assistant(self):
        with self.assertRaises(RuntimeBlocked):
            agent.configure_invoice_print({'Env': []}, dict(self.profile(), environment='rehearsal'))


if __name__ == '__main__':
    unittest.main()
