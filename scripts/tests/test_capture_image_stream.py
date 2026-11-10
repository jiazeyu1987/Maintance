"""Actual local image-export pipe; Docker replies are a finite protocol seam."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from minimal_capture_support import Budget
from formal_snapshot_linux import FormalSnapshotError

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='real POSIX owned pipe required')


@pytest.fixture(autouse=True)
def strict_budget_source():
    assert Path(sys.modules[Budget.__module__].__file__).resolve()==ROOT/'ops/recovery/minimal_capture_support.py'


@pytest.mark.parametrize('problem',['success','started','child','finished'])
def test_image_stream_observes_and_reaps_exact_local_child_before_publication(tmp_path,monkeypatch,problem):
    from recovery_capture_materials import save_application_images
    real_popen=subprocess.Popen;children=[];events=[]
    def local_protocol(argv,**kwargs):
        assert argv==['docker','image','save','sha256:'+'a'*64]
        code='import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"actual-export")'
        if problem=='child':code='import sys;sys.stdin.buffer.read();sys.exit(9)'
        child=real_popen([sys.executable,'-c',code],**kwargs);children.append(child);return child
    monkeypatch.setattr(subprocess,'Popen',local_protocol)
    class Observer:
        def before(self,argv):
            assert children==[]
        def started(self,process,argv):
            assert process is children[0];events.append(('started',process.pid))
            if problem=='started':raise RuntimeError('EXPECTED_STARTED_FAILURE')
        def finished(self,process):
            assert process is children[0] and process.poll() is not None
            events.append(('finished',process.pid))
            if problem=='finished':raise RuntimeError('EXPECTED_FINISHED_FAILURE')
    budget=Budget(tmp_path,dict(workSeconds=3,maxWrittenBytes=65536,minimumFreeBytes=1))
    path=tmp_path/'images.tar'
    if problem=='success':
        save_application_images(path,['sha256:'+'a'*64],budget,process_observer=Observer())
        assert path.read_bytes()==b'actual-export'
    else:
        error=FormalSnapshotError if problem=='child' else RuntimeError
        with pytest.raises(error):save_application_images(path,['sha256:'+'a'*64],budget,process_observer=Observer())
    assert len(children)==1 and children[0].poll() is not None
    assert [row[0] for row in events]==['started','finished'] and events[0][1]==events[1][1]
