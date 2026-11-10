"""Actual local observation children; Docker/IP/Redis replies are protocols.

These tests retain the production endpoint/Redis parsers. No real Docker,
Redis server, business data or remote machine is contacted.
"""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from formal_capture_semantics import SemanticCapture
from minimal_redis_snapshot import source_client

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual POSIX observation clients required')


@pytest.mark.parametrize('kind',['endpoint','redis'])
@pytest.mark.parametrize('mode',['default','observed','before-refused'])
def test_readonly_observations_admit_real_children_before_original_parsers(monkeypatch,kind,mode):
    events=[];children=[];real_popen=subprocess.Popen;closed=[]
    container='b'*64
    class Observer:
        def before(self,argv):
            events.append('before')
            if mode=='before-refused':raise RuntimeError('EXPECTED_OBSERVATION_REFUSAL')
        def started(self,process,argv):
            assert process is children[-1];events.append('started')
        def finished(self,process):
            assert process is children[-1] and process.poll() is not None;events.append('finished')
    endpoint_row=dict(id=container,running=True,ports={'9000/tcp':[dict(HostIp='127.0.0.1',HostPort='9000')]},networks={})
    redis_row=[dict(Id=container,State=dict(Running=True),NetworkSettings=dict(Networks={'fixture':dict(IPAddress='172.20.0.4')}))]
    def popen(argv,**kwargs):
        events.append('popen')
        if argv[0]=='ip':raw=b'1: lo    inet 127.0.0.1/8 scope host lo\n'
        else:
            assert argv[:2]==['docker','inspect']
            raw=json.dumps(endpoint_row if kind=='endpoint' else redis_row).encode()
        actual=[sys.executable,'-c','import sys;sys.stdout.buffer.write('+repr(raw)+')']
        process=real_popen(actual,**kwargs);children.append(process);return process
    monkeypatch.setattr(subprocess,'Popen',popen)
    class RedisProtocol:
        def __init__(self,**kwargs):
            assert kwargs['host']=='172.20.0.4' and kwargs['db']==0
        def info(self,section):
            assert section=='server';return {'redis_version':'7.0.1'}
        def close(self):closed.append(True)
    monkeypatch.setitem(sys.modules,'redis',SimpleNamespace(Redis=RedisProtocol))
    semantic=object.__new__(SemanticCapture)
    semantic.source=dict(endpoint='http://127.0.0.1:9000',minioContainerId=container,containerPort=9000)
    def observe():
        kwargs={} if mode=='default' else dict(process_observer=Observer())
        if kind=='endpoint':return semantic.verify_endpoint(lambda:None,**kwargs)
        with source_client(dict(containerId=container,host='172.20.0.4',database=0),lambda:None,**kwargs) as (_,row,version):
            assert row==redis_row[0] and version=='7.0.1'
    if mode=='before-refused':
        with pytest.raises(RuntimeError,match='EXPECTED_OBSERVATION_REFUSAL'):observe()
        assert events==['before'] and children==[] and closed==[]
    else:
        observe()
        count=2 if kind=='endpoint' else 1
        assert len(children)==count and all(child.poll() is not None for child in children)
        assert events==(['popen'] if mode=='default' else ['before','popen','started','finished'])*count
        assert closed==([True] if kind=='redis' else [])
