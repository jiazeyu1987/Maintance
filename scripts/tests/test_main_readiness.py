"""Registered original services require semantic readiness, without reconfiguration."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
from recovery_engine import RecoveryError, load
import recovery_main_target as main
import recovery_main_health as health


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.status, self.body, self.headers = 200, b'', {}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.seen = self.path
                self.send_response(owner.status)
                for key, value in owner.headers.items():self.send_header(key, value)
                self.end_headers(); self.wfile.write(owner.body)
            def log_message(self, *args):pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%s/' % self.server.server_port
        self.addCleanup(self.finish)

    def finish(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def test_minio_ready_and_frontend_require_actual_200(self):
        for role in ('minio', 'frontend'):
            result = health.probe(self.url, role, 2)
            self.assertTrue(result['ready']); self.assertEqual(200, result['httpStatus'])

    def test_backend_requires_explicit_up_not_http_alone(self):
        self.body = b'{"status":"DOWN"}'
        self.assertFalse(health.probe(self.url, 'backend', 2)['ready'])
        self.body = b'{"status":"UP"}'
        self.assertTrue(health.probe(self.url, 'backend', 2)['ready'])

    def test_readiness_waits_for_explicit_startup_status(self):
        self.status = 503
        self.assertFalse(health.probe(self.url, 'minio', 2)['ready'])

    def test_redirect_is_rejected_without_following(self):
        self.status, self.headers = 302, {'Location':'/other'}
        with self.assertRaisesRegex(RecoveryError, 'MAIN_HEALTH_HTTP_STATUS_INVALID'):
            health.probe(self.url, 'frontend', 2)
        self.assertEqual('/', self.seen)

    def test_missing_endpoint_is_not_startup(self):
        self.status = 404
        with self.assertRaisesRegex(RecoveryError, 'MAIN_HEALTH_HTTP_STATUS_INVALID'):
            health.probe(self.url, 'backend', 2)

    def test_invalid_backend_json_fails_explicitly(self):
        for raw in (b'not-json', b'{}', b'{"status":"UP","status":"DOWN"}', b'[]'):
            self.body = raw
            with self.assertRaisesRegex(RecoveryError, 'MAIN_HEALTH_BACKEND_RESPONSE_INVALID'):
                health.probe(self.url, 'backend', 2)

    def test_response_limit(self):
        self.body = b'x' * 65537
        with self.assertRaisesRegex(RecoveryError, 'MAIN_HEALTH_RESPONSE_LIMIT'):
            health.probe(self.url, 'frontend', 2)

    def test_proxy_environment_cannot_redirect_probe(self):
        with patch.dict('os.environ', {'http_proxy':'http://127.0.0.1:1','HTTP_PROXY':'http://127.0.0.1:1','no_proxy':'','NO_PROXY':''}):
            self.assertTrue(health.probe(self.url, 'minio', 2)['ready'])


class BoundReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.row = dict(Id='a'*64,Image='sha256:'+'b'*64,Path='/entrypoint',Args=[],
            Config={'ExposedPorts':{'48081/tcp':{}}},HostConfig={'PortBindings':{}},
            State={'Running':True,'Paused':False,'Restarting':False})
        self.native = SimpleNamespace(config={'mainApplication':{'serviceConfigurationDigests':{'backend':main.service_configuration_digest(self.row)}}},
            config_services={'backend':dict(id=self.row['Id'],imageId=self.row['Image'],ip='172.21.0.11')},
            inspect=lambda identity:deepcopy(self.row), bound=lambda:None, guard=lambda:None,
            budget=SimpleNamespace(remaining=lambda:20),root=Path(self.temp.name),original_pins=[])

    def test_registered_endpoint_and_port_are_explicit(self):
        self.assertEqual('http://172.21.0.11:48081/actuator/health',health.endpoint(self.native,'backend'))
        self.row['Config']['ExposedPorts']={}
        self.native.config['mainApplication']['serviceConfigurationDigests']['backend']=main.service_configuration_digest(self.row)
        with self.assertRaisesRegex(RecoveryError,'MAIN_HEALTH_PORT_NOT_DECLARED'):
            health.endpoint(self.native,'backend')

    def test_config_image_and_identity_changes_rejected(self):
        for key,value in (('Id','c'*64),('Image','sha256:'+'d'*64),('Args',['changed'])):
            with self.subTest(key=key):
                previous=self.row[key];self.row[key]=value
                with self.assertRaisesRegex(RecoveryError,'MAIN_HEALTH_SERVICE_CHANGED'):
                    health.endpoint(self.native,'backend')
                self.row[key]=previous

    def test_dns_and_loopback_application_endpoint_rejected(self):
        for ip in ('localhost','127.0.0.1','0.0.0.0','169.254.1.1','::1','172.21.0.11/path'):
            self.native.config_services['backend']['ip']=ip
            with self.assertRaisesRegex(RecoveryError,'MAIN_HEALTH_ENDPOINT_INVALID'):
                health.endpoint(self.native,'backend')

    def test_semantic_success_writes_bound_proof(self):
        with patch.object(health,'probe',return_value=dict(ready=True,httpStatus=200,bodySha256='0'*64)):
            result=health.wait_healthy(self.native,'backend')
        self.assertEqual('healthy',result['status'])
        proof=load(result['readinessPin']['path'])
        self.assertEqual('RegisteredMainSemanticReadiness/v1',proof['schemaVersion'])
        self.assertEqual(self.row['Id'],proof['containerId'])
        self.assertEqual('UP',proof['semanticStatus'])
        self.assertIn(result['readinessPin'],self.native.original_pins)

    def test_existing_unhealthy_docker_check_cannot_be_overruled_by_http(self):
        self.row['Config']['Healthcheck']={'Test':['CMD','check']}
        self.native.config['mainApplication']['serviceConfigurationDigests']['backend']=main.service_configuration_digest(self.row)
        for state in (None, {'Status':'unhealthy'}):
            if state is None:self.row['State'].pop('Health',None)
            else:self.row['State']['Health']=state
            with patch.object(health,'probe',return_value=dict(ready=True,httpStatus=200,bodySha256='0'*64)):
                with self.assertRaisesRegex(RecoveryError,'MAIN_DOCKER_HEALTH_INVALID'):
                    health.wait_healthy(self.native,'backend')
        self.assertEqual([],self.native.original_pins)

    def test_starting_and_down_have_bounded_timeout_and_no_success_receipt(self):
        with patch.object(health,'probe',return_value=dict(ready=False,httpStatus=503,bodySha256='0'*64)), \
             patch.object(health,'STARTUP_SECONDS',0.001),patch.object(health.time,'sleep'):
            with self.assertRaisesRegex(RecoveryError,'MAIN_SEMANTIC_HEALTH_TIMEOUT'):
                health.wait_healthy(self.native,'backend')
        self.assertEqual([],self.native.original_pins)

    def test_stopped_paused_or_restarting_is_not_readiness(self):
        for name,value in (('Running',False),('Paused',True),('Restarting',True)):
            previous=self.row['State'][name];self.row['State'][name]=value
            with self.assertRaisesRegex(RecoveryError,'MAIN_HEALTH_SERVICE_NOT_RUNNING'):
                health.wait_healthy(self.native,'backend')
            self.row['State'][name]=previous

    def test_main_only_routes_known_roles_to_semantic_health(self):
        class Original:
            def wait_healthy(self,role):return 'original-'+role
        obj=main.guarded_type(Original)();obj.config={}
        self.assertEqual('original-backend',obj.wait_healthy('backend'))
        obj.config={'mainApplication':{'schemaVersion':'RegisteredMainApplication/v2'}}
        with patch.object(health,'wait_healthy',return_value='semantic') as called:
            self.assertEqual('semantic',obj.wait_healthy('backend'))
            called.assert_called_once_with(obj,'backend')
        self.assertEqual('original-mysql',obj.wait_healthy('mysql'))

    def test_both_actual_bundles_ship_semantic_health(self):
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location('backup_engine',ROOT/'ops/backup_engine/build_variants.py')
        module=module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            import tarfile
            output=Path(directory)/'packages'
            module.build(output)
            for variant in module.VARIANTS:
                with tarfile.open(output/('backup-restore-'+variant+'.tgz')) as package:
                    self.assertEqual((ROOT/'ops/recovery/recovery_main_health.py').read_bytes(),package.extractfile('common/recovery_main_health.py').read())
                    self.assertIn(b'def wait_healthy(self, role)',package.extractfile('common/recovery_main_target.py').read())

