"""Authenticated HTTP routing contracts, not remote execution or browser E2E."""
import json
import unittest
from unittest.mock import patch
import prepare_target
import test_automatic_incremental_http as existing_http


class PreparationHttp(unittest.TestCase):
    def setUp(self):
        self.fixture = existing_http.AutomaticIncrementalHttp()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def call(self, method, path, value=None, token=True):
        import http.client
        connection=http.client.HTTPConnection('127.0.0.1',self.fixture.server.server_port)
        headers={'Origin':'http://127.0.0.1:18080','Content-Type':'application/json'}
        if token:headers['X-Token']='a'*32
        connection.request(method,path,None if value is None else json.dumps(value),headers)
        response=connection.getresponse();body=json.loads(response.read());connection.close()
        return response.status,body

    def test_config_requires_real_entry_authentication(self):
        with patch.object(prepare_target,'public_configuration',return_value={'configured':False}):
            self.assertEqual(self.call('GET','/prepare-target/config'),(200,{'configured':False}))
            self.assertEqual(self.call('GET','/prepare-target/config',token=False)[0],401)

    def test_submit_uses_edit_permission_and_fixed_route(self):
        with patch.object(prepare_target,'submit',return_value={'state':'PENDING'}) as submit:
            self.assertEqual(self.call('POST','/prepare-target/operations',{'operationId':'http-operation'}),
                             (202,{'state':'PENDING'}))
            self.assertEqual(submit.call_args.args[0],{'operationId':'http-operation'})
            self.assertIn(('schedule.schedule.edit',),self.fixture.permission_checks)

    def test_failed_preview_is_not_success(self):
        with patch.object(prepare_target,'preview',side_effect=prepare_target.Refused('PREPARATION_NOT_CONFIGURED')):
            self.assertEqual(self.call('POST','/prepare-target/preview',{}),
                             (409,{'errorCode':'PREPARATION_NOT_CONFIGURED'}))

if __name__=='__main__':unittest.main()
