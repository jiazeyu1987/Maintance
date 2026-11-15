"""Actual generated wait method against a real local HTTP readiness service."""
import ast
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/backup_engine'))
import build_variants as builder


@pytest.fixture(scope='module')
def standard(tmp_path_factory):
    payload = builder.safe_fixes(builder.standard_sources()[0])
    root = tmp_path_factory.mktemp('prepared-health-standard')
    for name, raw in payload.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    sys.path[:0] = [str(root/name) for name in ('common', 'formal', 'control')]
    import recovery_engine as engine
    import recovery_main_health as health
    tree = ast.parse(payload['common/recovery_minimal_runtime.py'].decode())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'MinimalData')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'wait_healthy')
    namespace = dict(require=engine.require, utc=engine.utc, write=engine.write, time=time)
    exec(compile(ast.Module(body=[method], type_ignores=[]), 'actual-standard-health', 'exec'), namespace)
    return namespace['wait_healthy'], health, engine


@pytest.fixture
def server():
    state = dict(status=200, body=b'{"status":"UP"}', paths=[])
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state['paths'].append(self.path)
            self.send_response(state['status']); self.end_headers(); self.wfile.write(state['body'])
        def log_message(self, *args): pass
    httpd = ThreadingHTTPServer(('127.0.0.1',0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    yield httpd.server_port, state
    httpd.shutdown(); thread.join(); httpd.server_close()


def target(tmp_path, role, *, seconds=2):
    service = dict(id='container',imageId='image',ip='127.0.0.1')
    row = dict(Id='container',Image='image',Config={},State=dict(Running=True,Paused=False,Restarting=False))
    deadline = time.monotonic()+seconds
    return SimpleNamespace(config=dict(preparedEmptyTarget=True),config_services={role:service},
        root=tmp_path,guard=lambda:None,bound=lambda:None,inspect=lambda identity:row,
        budget=SimpleNamespace(remaining=lambda:max(0.001,deadline-time.monotonic()))),row


@pytest.mark.parametrize('role,path',[('minio','/minio/health/ready'),('backend','/actuator/health'),('frontend','/')])
def test_prepared_without_docker_health_uses_real_service_probe(standard, server, tmp_path, monkeypatch, role, path):
    wait, health, engine = standard; port,state = server
    monkeypatch.setitem(health.ROLES,role,(port,path))
    obj,row = target(tmp_path,role)
    result = wait(obj,role)
    assert result['status']=='healthy' and state['paths']==[path]
    proof = engine.pinned_json(result['readinessPin'])
    assert proof['ready'] is True and proof['httpStatus']==200
    assert proof['dockerHealthcheckConfigured'] is False


def test_not_ready_or_unhealthy_is_not_success_and_old_contract_remains(standard, server, tmp_path, monkeypatch):
    wait,health,_ = standard; port,state = server
    monkeypatch.setitem(health.ROLES,'backend',(port,'/actuator/health'))
    for response in [(200,b'{"status":"DOWN"}'),(503,b'not ready')]:
        state['status'],state['body'] = response
        obj,row = target(tmp_path,'backend',seconds=0.06)
        with pytest.raises(Exception,match='PREPARED_SERVICE_HEALTH_TIMEOUT'): wait(obj,'backend')
    obj,row = target(tmp_path,'backend')
    row['Config']['Healthcheck'] = {'Test':['CMD','check']}
    row['State']['Health'] = {'Status':'unhealthy'}
    with pytest.raises(Exception,match='APPLICATION_OR_STORAGE_UNHEALTHY'): wait(obj,'backend')
    obj,row = target(tmp_path,'backend');obj.config.pop('preparedEmptyTarget')
    with pytest.raises(Exception,match='ACTUAL_CONTAINER_HEALTHCHECK_REQUIRED'): wait(obj,'backend')
    obj,row = target(tmp_path,'backend');row['Image']='other'
    with pytest.raises(Exception,match='PREPARED_HEALTH_SERVICE_CHANGED'): wait(obj,'backend')


def test_native_prepared_service_addresses_use_confirmed_fixed_ports(standard, tmp_path, monkeypatch):
    wait,health,_ = standard
    spec=importlib.util.spec_from_file_location('health_native_preparer',ROOT/'ops/spug/prepare_target_native.py')
    preparer=importlib.util.module_from_spec(spec);spec.loader.exec_module(preparer)
    services=[dict(role=role,id=role,imageId='image',ip=ip) for role,ip in
              [('minio','172.29.238.33'),('backend','172.29.238.35'),('frontend','172.29.238.36')]]
    prepared=preparer.fresh_target(dict(services=[]),dict(targetId='prepared',dataRoot='/prepared',
        networkId='network',services=services),{})
    # Actual native nginx uses backend :48081 and frontend listen 80; MinIO :9000 was live-probed.
    assert health.ROLES == {'minio':(9000,'/minio/health/ready'),
                            'backend':(48081,'/actuator/health'),'frontend':(80,'/')}
    endpoints=[]
    monkeypatch.setattr(health,'probe',lambda url,role,timeout:
                        endpoints.append(url) or dict(ready=True,httpStatus=200))
    for service in prepared['services']:
        obj,row=target(tmp_path,service['role']);obj.config=prepared
        obj.config_services[service['role']]=service;row['Id']=service['id']
        wait(obj,service['role'])
    assert endpoints==['http://172.29.238.33:9000/minio/health/ready',
                       'http://172.29.238.35:48081/actuator/health','http://172.29.238.36:80/']
