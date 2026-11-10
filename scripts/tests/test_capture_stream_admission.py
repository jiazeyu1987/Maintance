"""A stream intent must be admitted before the actual Popen dispatch."""
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from formal_snapshot_linux import PrivateDockerMySql
from formal_data_evidence import DataMySql
from minimal_capture_support import Budget

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual POSIX stream admission required')


@pytest.mark.parametrize('kind',['dump','data'])
def test_before_refusal_leaves_no_exporter_and_no_success_terminal(tmp_path,monkeypatch,kind):
    assert Path(sys.modules[Budget.__module__].__file__).resolve()==ROOT/'ops/recovery/minimal_capture_support.py'
    events=[]
    class Observer:
        def before(self,argv):
            events.append('before')
            raise RuntimeError('EXPECTED_BEFORE_REFUSAL')
        def started(self,*args):events.append('started')
        def finished(self,*args):events.append('finished')
    def forbidden(*args,**kwargs):
        events.append('popen')
        raise AssertionError('EXPORTER_DISPATCHED_BEFORE_ADMISSION')
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    mysql=(PrivateDockerMySql if kind=='dump' else DataMySql)('fixture','private-fixture',timeout=2,process_observer=Observer())
    budget=Budget(tmp_path,dict(workSeconds=3,maxWrittenBytes=65536,minimumFreeBytes=1))
    with budget.activate(),pytest.raises(RuntimeError,match='EXPECTED_BEFORE_REFUSAL'):
        if kind=='dump':mysql.dump_until('app',tmp_path/'database.sql.gz',guard=lambda:None,deadline=time.monotonic()+3)
        else:mysql.data_query_to_file('SELECT 1;',database='app',expected_uuid='11111111-1111-1111-1111-111111111111',
            path=tmp_path/'rows',max_bytes=65536)
    assert events==['before']
    assert not (tmp_path/'database.sql.gz').exists()
