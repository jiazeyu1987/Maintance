import copy
import unittest
import intruoyi_runtime_agent as agent


class PrestopAddressTest(unittest.TestCase):
    def setUp(self):
        self.before={'Id':'same','Image':'image','State':{'Running':True},
          'Config':{'Image':'image','Env':[]},'HostConfig':{'NetworkMode':'appnet'},
          'NetworkSettings':{'Networks':{'appnet':{'NetworkID':'network','IPAddress':'172.21.0.8','IPAMConfig':None,'Aliases':['backend']}}}}
        self.stopped=copy.deepcopy(self.before)
        self.stopped['State']['Running']=False
        self.stopped['NetworkSettings']['Networks']['appnet']['IPAddress']=''

    def test_stop_does_not_lose_dynamic_address_in_replacement(self):
        merged=agent.preserve_stopped_networks(self.stopped,self.before)
        config=agent.clone_config(merged,'new-image',True)
        self.assertEqual(config['NetworkingConfig']['EndpointsConfig']['appnet']['IPAMConfig'],{'IPv4Address':'172.21.0.8'})
        self.assertFalse(merged['State']['Running'])
        self.assertEqual(self.stopped['NetworkSettings']['Networks']['appnet']['IPAddress'],'')

    def test_replaced_container_or_network_rejected(self):
        for mismatch in ('container','network'):
            with self.subTest(mismatch=mismatch):
                stopped=copy.deepcopy(self.stopped)
                if mismatch=='container':stopped['Id']='other'
                else:stopped['NetworkSettings']['Networks']['appnet']['NetworkID']='other'
                with self.assertRaises(agent.RuntimeBlocked):agent.preserve_stopped_networks(stopped,self.before)

    def test_running_container_cannot_be_replaced(self):
        with self.assertRaises(agent.RuntimeBlocked):agent.preserve_stopped_networks(self.before,self.before)

if __name__=='__main__':unittest.main()
