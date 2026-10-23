"""Pure Docker create-config regression tests; no Docker/SSH calls."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from intruoyi_runtime_agent import clone_config


class CloneNetworkConfigTest(unittest.TestCase):
    def original(self, network='release-net', ip='', ipam=None):
        return {
            'Config': {'Image': 'old-image', 'Env': ['INTRUOYI_RELEASE_MAINTENANCE=true']},
            'HostConfig': {'NetworkMode': network, 'PortBindings': {}},
            'NetworkSettings': {'Networks': {network: {
                'IPAddress': ip, 'IPAMConfig': ipam, 'Aliases': ['backend'],
            }}},
        }

    def test_stopped_backend_keeps_configured_ip_for_nginx(self):
        # Actual failure shape: docker stop cleared IPAddress, not IPAMConfig.
        original = self.original(ipam={'IPv4Address': '172.29.235.25'})
        result = clone_config(original, 'candidate-image', True)
        self.assertEqual(result['NetworkingConfig']['EndpointsConfig']['release-net'],
                         {'IPAMConfig': {'IPv4Address': '172.29.235.25'}, 'Aliases': ['backend']})
        # Normal-mode replacement must preserve the same address again.
        stopped_candidate = self.original(ipam=result['NetworkingConfig']['EndpointsConfig']['release-net']['IPAMConfig'])
        reopened = clone_config(stopped_candidate, 'candidate-image', False)
        self.assertEqual(reopened['NetworkingConfig'], result['NetworkingConfig'])
        self.assertIn('INTRUOYI_RELEASE_MAINTENANCE=false', reopened['Env'])

    def test_all_explicit_ipam_fields_are_deep_copied(self):
        ipam = {'IPv4Address': '172.29.235.25', 'IPv6Address': 'fd00::25',
                'LinkLocalIPs': ['169.254.25.1']}
        original = self.original(ip='172.29.235.25', ipam=ipam)
        baseline = copy.deepcopy(original)
        result = clone_config(original, 'candidate-image')
        cloned = result['NetworkingConfig']['EndpointsConfig']['release-net']['IPAMConfig']
        self.assertEqual(cloned, ipam)
        cloned['LinkLocalIPs'].append('169.254.25.2')
        self.assertEqual(original, baseline)

    def test_unconfigured_observed_address_retains_existing_behavior(self):
        result = clone_config(self.original(ip='172.29.235.25'), 'candidate-image')
        self.assertEqual(result['NetworkingConfig']['EndpointsConfig']['release-net']['IPAMConfig'],
                         {'IPv4Address': '172.29.235.25'})

    def test_default_bridge_and_host_do_not_gain_static_endpoint(self):
        result = clone_config(self.original(network='bridge', ipam={'IPv4Address': '172.17.0.2'}), 'candidate-image')
        self.assertEqual(result['NetworkingConfig']['EndpointsConfig'], {'bridge': {}})
        for network in ('host', 'none'):
            with self.subTest(network=network):
                result = clone_config(self.original(network=network), 'candidate-image')
                self.assertNotIn('NetworkingConfig', result)


if __name__ == '__main__':
    unittest.main()
