"""Actual local exporter processes; SQL/Docker semantics are protocol units.

No business database, Docker daemon or remote endpoint is contacted. The
original dump compressor and bounded drain own real Python child processes.
"""
import gzip
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from formal_snapshot_linux import PrivateDockerMySql, FormalSnapshotError
from formal_data_evidence import DataMySql
from minimal_capture_support import Budget

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='real POSIX bounded exporter required')


@pytest.fixture(autouse=True)
def strict_budget_source():
    assert Path(sys.modules[Budget.__module__].__file__).resolve()==ROOT/'ops/recovery/minimal_capture_support.py'


class Observer:
    def __init__(self,problem=None):self.problem=problem;self.events=[];self.process=None
    def before(self,argv):
        assert self.process is None
    def started(self,process,argv):
        assert type(process) is subprocess.Popen
        self.process=process;self.events.append(('started',process.pid,None))
        if self.problem=='started':raise RuntimeError('EXPECTED_STARTED_FAILURE')
    def finished(self,process):
        assert process is self.process and process.poll() is not None
        self.events.append(('finished',process.pid,process.returncode))
        if self.problem=='finished':raise RuntimeError('EXPECTED_FINISHED_FAILURE')


def command(code):return [sys.executable,'-c',code]


def test_default_dump_keeps_actual_compressed_output_without_observer(tmp_path,monkeypatch):
    mysql=PrivateDockerMySql('fixture','private-fixture',timeout=2)
    monkeypatch.setattr(mysql,'_command',lambda *a:command('import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"SQL\\n")'))
    destination=tmp_path/'database.sql.gz'
    mysql.dump_until('app',destination,guard=lambda:None,deadline=time.monotonic()+3)
    assert gzip.decompress(destination.read_bytes())==b'SQL\n'


@pytest.mark.parametrize('problem',['success','started','child','timeout','finished'])
def test_observed_dump_uses_actual_popen_and_known_reap_on_every_failure(tmp_path,monkeypatch,problem):
    observer=Observer(problem)
    mysql=PrivateDockerMySql('fixture','private-fixture',timeout=2,process_observer=observer)
    code='import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"SQL\\n")'
    if problem=='child':code='import sys;sys.stdin.buffer.read();sys.exit(7)'
    if problem=='timeout':code='import time;time.sleep(30)'
    monkeypatch.setattr(mysql,'_command',lambda *a:command(code))
    destination=tmp_path/'database.sql.gz'
    deadline=time.monotonic()+(.2 if problem=='timeout' else 3)
    if problem=='success':
        mysql.dump_until('app',destination,guard=lambda:None,deadline=deadline)
        assert gzip.decompress(destination.read_bytes())==b'SQL\n'
    else:
        expected=RuntimeError if problem in ('started','finished') else FormalSnapshotError
        with pytest.raises(expected):mysql.dump_until('app',destination,guard=lambda:None,deadline=deadline)
        assert not destination.exists()
    assert observer.process is not None and observer.process.poll() is not None
    assert [row[0] for row in observer.events]==['started','finished']
    assert observer.events[0][1]==observer.events[1][1]


def test_actual_data_stream_has_same_observer_lifecycle(tmp_path,monkeypatch):
    observer=Observer()
    mysql=DataMySql('fixture','private-fixture',timeout=2,process_observer=observer)
    monkeypatch.setattr(mysql,'_command',lambda *a:command('import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"actual-row\\n")'))
    budget=Budget(tmp_path,dict(workSeconds=3,maxWrittenBytes=65536,minimumFreeBytes=1))
    with budget.activate():
        mysql.data_query_to_file('SELECT 1;',database='app',expected_uuid='11111111-1111-1111-1111-111111111111',
            path=tmp_path/'rows',max_bytes=65536)
    assert (tmp_path/'rows').read_bytes()==b'actual-row\n'
    assert [row[0] for row in observer.events]==['started','finished']
    assert observer.events[1][2]==0


def test_unreaped_export_never_reports_finished_or_publishes(tmp_path,monkeypatch):
    import formal_capture_budget as pipes
    real_popen=subprocess.Popen;children=[]
    class Unreaped:
        def __init__(self,*args,**kwargs):
            self.child=real_popen(*args,**kwargs);children.append(self.child)
            for name in ('stdin','stdout','stderr','pid'):setattr(self,name,getattr(self.child,name))
            self.returncode=None
        def poll(self):return None
        def wait(self,timeout=None):raise subprocess.TimeoutExpired('actual-child-wait',timeout)
        def kill(self):self.child.kill()
    observer=Observer()
    # Observer validates the exact process given by the original formal helper;
    # this wrapper only injects inability to observe its otherwise real child's
    # reap. It is not a fabricated successful terminal.
    observer.started=lambda process,argv:(setattr(observer,'process',process),observer.events.append(('started',process.pid,None)))
    mysql=PrivateDockerMySql('fixture','private-fixture',timeout=2,process_observer=observer)
    monkeypatch.setattr(mysql,'_command',lambda *a:command('import time;time.sleep(30)'))
    monkeypatch.setattr(subprocess,'Popen',Unreaped)
    try:
        with pytest.raises(FormalSnapshotError) as caught:
            mysql.dump_until('app',tmp_path/'database.sql.gz',guard=lambda:None,deadline=time.monotonic()+.1)
        assert getattr(caught.value,'clientCleanupUncertain',False) is True
        assert [row[0] for row in observer.events]==['started']
        assert not (tmp_path/'database.sql.gz').exists()
    finally:
        for child in children:
            if child.poll() is None:child.kill()
            child.wait(timeout=3)
