import unittest

from prepare_target_ingress import render


class PublicIngressTest(unittest.TestCase):
    def config(self):
        return dict(host='172.30.30.59', subnet='172.29.238.0/24',
                    services=[dict(role=r) for r in ('mysql', 'minio', 'redis', 'backend', 'frontend')])

    def test_public_page_uses_only_declared_host_and_frontend(self):
        result = render(self.config(), 8081)
        self.assertIn('ListenStream=172.30.30.59:8081', result['socket'])
        self.assertIn('systemd-socket-proxyd 172.29.238.36:80', result['service'])
        self.assertIn('WantedBy=sockets.target', result['socket'])
        self.assertIn('destination address="172.30.30.59/32"', result['firewallRule'])
        self.assertIn('port="8081"', result['firewallRule'])
        self.assertNotIn('48081', result['service'])

    def test_upstream_follows_preparation_subnet_and_role_order(self):
        config = self.config()
        config['subnet'] = '172.29.237.0/24'
        config['services'] = list(reversed(config['services']))
        self.assertIn('172.29.237.32:80', render(config, 8081)['service'])

    def test_invalid_host_or_missing_frontend_is_visible_failure(self):
        config = self.config()
        config['host'] = '172.30.30.59\nExecStart=bad'
        with self.assertRaises(ValueError):
            render(config, 8081)
        config = self.config()
        config['services'].pop()
        with self.assertRaises(ValueError):
            render(config, 8081)


if __name__ == '__main__':
    unittest.main()
