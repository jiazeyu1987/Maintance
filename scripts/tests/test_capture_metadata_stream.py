"""Real local schema/reference clients, original parsers and finite protocols."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from formal_schema_evidence import SchemaMySql
from formal_snapshot_linux import PrivateDockerMySql
from formal_capture_semantics import bounded_reference_query

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual POSIX metadata exporter required')
UUID='11111111-1111-1111-1111-111111111111'


@pytest.mark.parametrize('kind',['schema','reference'])
@pytest.mark.parametrize('mode',['default','observed','before-refused'])
def test_actual_metadata_stream_retains_parser_and_admits_before_dispatch(tmp_path,monkeypatch,kind,mode):
    events=[];children=[];real_popen=subprocess.Popen
    class Observer:
        def before(self,argv):
            events.append('before')
            if mode=='before-refused':raise RuntimeError('EXPECTED_METADATA_REFUSAL')
        def started(self,process,argv):
            assert process is children[0];events.append('started')
        def finished(self,process):
            assert process is children[0] and process.poll() is not None;events.append('finished')
    mysql=(SchemaMySql if kind=='schema' else PrivateDockerMySql)('fixture','private-fixture',timeout=2,
        process_observer=None if mode=='default' else Observer())
    raw=(UUID+'\nactual-schema\n0\n'+UUID+'\n').encode() if kind=='schema' else b'actual-reference\n'
    def popen(argv,**kwargs):
        events.append('popen')
        process=real_popen(argv,**kwargs);children.append(process);return process
    monkeypatch.setattr(subprocess,'Popen',popen)
    monkeypatch.setattr(mysql,'_command',lambda *args:[sys.executable,'-c',
        'import sys;sys.stdin.buffer.read();sys.stdout.buffer.write('+repr(raw)+')'])
    def query():
        if kind=='schema':return mysql.schema_query('SELECT 1;',database='app',expected_uuid=UUID)
        return bounded_reference_query(mysql,'SELECT 1;',lambda:None)
    if mode=='before-refused':
        with pytest.raises(RuntimeError,match='EXPECTED_METADATA_REFUSAL'):query()
        assert events==['before'] and children==[]
    else:
        result=query()
        assert result==([['actual-schema']] if kind=='schema' else 'actual-reference\n')
        assert len(children)==1 and children[0].poll() is not None
        assert events==(['popen'] if mode=='default' else ['before','popen','started','finished'])
