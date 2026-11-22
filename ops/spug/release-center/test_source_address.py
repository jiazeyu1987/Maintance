import copy
import unittest
import release_backup_source as source


class SourceAddressTests(unittest.TestCase):
    def setUp(self):
        self.service={'role':'backend','ip':'172.21.0.11'}
        self.target={'mainApplication':{'networkAttachments':{'backend':{'appnet':{'networkId':'network-1'}}},
            'publishedDataEndpoints':[{'writeFence':{'allowedWriterIPv4':['172.21.0.11','172.21.0.20']}}]}}
        self.row={'NetworkSettings':{'Networks':{'appnet':{'NetworkID':'network-1','IPAddress':'172.21.0.8'}}}}

    def test_new_application_address_updates_exact_writer_binding(self):
        source.refresh_application_address(self.target,self.service,self.row)
        self.assertEqual(self.service['ip'],'172.21.0.8')
        self.assertEqual(self.target['mainApplication']['publishedDataEndpoints'][0]['writeFence']['allowedWriterIPv4'],['172.21.0.8','172.21.0.20'])

    def test_changed_network_rejected_without_mutation(self):
        original=copy.deepcopy(self.target)
        self.row['NetworkSettings']['Networks']['appnet']['NetworkID']='different'
        with self.assertRaisesRegex(ValueError,'SOURCE_APPLICATION_NETWORK_CHANGED'):
            source.refresh_application_address(self.target,self.service,self.row)
        self.assertEqual(self.target,original)
        self.assertEqual(self.service['ip'],'172.21.0.11')

    def test_multiple_addresses_rejected(self):
        self.row['NetworkSettings']['Networks']['extra']={'NetworkID':'extra','IPAddress':'172.22.0.8'}
        with self.assertRaises(ValueError):source.refresh_application_address(self.target,self.service,self.row)

    def test_data_services_cannot_use_application_rebinding(self):
        self.service['role']='mysql'
        with self.assertRaisesRegex(ValueError,'SOURCE_APPLICATION_ROLE_REQUIRED'):
            source.refresh_application_address(self.target,self.service,self.row)

    def test_unchanged_address_keeps_writer_policy(self):
        self.row['NetworkSettings']['Networks']['appnet']['IPAddress']='172.21.0.11'
        original=copy.deepcopy(self.target)
        source.refresh_application_address(self.target,self.service,self.row)
        self.assertEqual(self.target,original)

if __name__=='__main__':unittest.main()
