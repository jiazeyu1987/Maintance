"""Real local query clients; SQL replies are a finite external protocol unit."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from formal_snapshot_linux import PrivateDockerMySql

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual POSIX query client required')


@pytest.mark.parametrize('mode',['default','observed','before-refused'])
def test_query_admits_actual_client_and_retains_original_decoding(monkeypatch,mode):
    events=[];children=[];real_popen=subprocess.Popen
    class Observer:
        def before(self,argv):
            events.append('before')
            if mode=='before-refused':raise RuntimeError('EXPECTED_QUERY_REFUSAL')
        def started(self,process,argv):
            assert process is children[0];events.append('started')
        def finished(self,process):
            assert process is children[0] and process.poll() is not None;events.append('finished')
    mysql=PrivateDockerMySql('fixture','private-fixture',timeout=2,
        process_observer=None if mode=='default' else Observer())
    monkeypatch.setattr(mysql,'_command',lambda *args:[sys.executable,'-c',
        'import sys;sys.stdin.buffer.read();sys.stdout.buffer.write(b"actual-query\\n")'])
    def popen(argv,**kwargs):
        events.append('popen')
        process=real_popen(argv,**kwargs);children.append(process);return process
    monkeypatch.setattr(subprocess,'Popen',popen)
    if mode=='before-refused':
        with pytest.raises(RuntimeError,match='EXPECTED_QUERY_REFUSAL'):mysql.query('SELECT 1;')
        assert events==['before'] and children==[]
    else:
        assert mysql.query('SELECT 1;')=='actual-query\n'
        assert len(children)==1 and children[0].poll() is not None
        assert events==(['popen'] if mode=='default' else ['before','popen','started','finished'])
