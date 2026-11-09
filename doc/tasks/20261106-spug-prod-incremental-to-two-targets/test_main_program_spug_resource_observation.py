"""Real local processes/files; injected executable is not live Docker evidence."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
import main_program_spug_publication as publication
from test_main_program_spug_resource_activation import resource


@pytest.fixture
def subject():
    return importlib.import_module('main_program_spug_resource_observation')


@pytest.fixture
def local(subject,monkeypatch):
    class Commands(list):pass
    original=subprocess.Popen; children=[]; commands=Commands();commands.children=children
    def launch(argv,**kwargs):
        commands.append(argv)
        assert argv[:4]==[publication.DOCKER,'exec','-i',publication.CONTAINER]
        assert argv[4:7]==['python3','-B','-']
        child=original([sys.executable,'-B','-',argv[-1]],**kwargs);children.append(child);return child
    monkeypatch.setattr(subject,'Popen',launch)
    def inspect(container,expected,nonce,**kwargs):
        assert container==publication.CONTAINER and expected['argv'][-1]==nonce
        matches=[child for child in children if child.pid==expected['pid']]
        assert len(matches)==1 and matches[0].args[-1]==nonce
        return dict(status='ALIVE' if matches[0].poll() is None else 'EXITED',identity=None)
    monkeypatch.setattr(subject,'inspect_worker',inspect)
    yield commands
    for child in children:
        if child.poll() is None:child.kill()
        child.wait(timeout=5)


def identity():return dict(sourceCommit='a'*40,inputPins=[])


def records(tmp_path):return [json.loads(p.read_bytes()) for p in tmp_path.glob('resource-observation-*/terminal.private.json')]


def execute(subject,tmp_path,program,*,idle=.35,hard=2):
    with subject.Observation(tmp_path,identity(),idle_seconds=idle,hard_seconds=hard) as work:
        return work.run(program+"\n_observation_progress('complete')\n")


def test_completing_real_work_can_exceed_initial_idle_window(subject,local,tmp_path):
    program="import time,json\nfor i in range(1,6):\n time.sleep(.3)\n _observation_progress('ledger',i,i*3)\nprint(json.dumps({'complete':True}))\n"
    result=execute(subject,tmp_path,program,idle=1,hard=4)
    assert json.loads(result)=={'complete':True} and len(local)==1
    terminal=records(tmp_path)[0]
    assert terminal['status']=='SUCCEEDED' and terminal['actualExitCode']==0
    assert terminal['elapsedSeconds']>1 and terminal['lastProgress']['completedFiles']==5
    assert terminal['workerIdentity']['pid']>1 and terminal['workerIdentity']['argv'][-1].startswith('spug-observation-')
    assert not list(tmp_path.glob('*.gate.private.json'))


@pytest.mark.parametrize('program,code',[
    ("import time\ntime.sleep(3)\n",'STALLED'),
    ("import time\nfor i in range(40):\n _observation_progress('ledger',0,0)\n time.sleep(.04)\n",'STALLED'),
    ("import time\nfor i in range(80):\n _observation_progress('ledger',i+1,i+1)\n time.sleep(.04)\n",'HARD_DEADLINE'),
])
def test_real_process_stall_and_hard_deadline_never_restart(subject,local,tmp_path,program,code):
    with pytest.raises(ValueError,match=code):execute(subject,tmp_path,program,idle=1,hard=1.8)
    terminal=records(tmp_path)[0]
    assert terminal['status']=='FAILED' and terminal['remoteExitVerified'] is False
    assert len(local)==1 and list(tmp_path.glob('*.gate.private.json'))
    with pytest.raises(ValueError,match='UNRESOLVED'):
        execute(subject,tmp_path,"print('{}')")
    assert len(local)==1


@pytest.mark.parametrize('program,code',[
    ("import sys\nsys.stderr.write('private-token-never-public\\n');sys.stderr.flush()\nprint('{}')\n",'STDERR'),
    ("import sys\nsys.stderr.write('SPUG_OBSERVATION_PROGRESS {bad-json}\\n');sys.stderr.flush()\nprint('{}')\n",'PROTOCOL'),
    ("print('{truncated')\n",'RESULT'),
    ("raise SystemExit(7)\n",'EXIT'),
])
def test_real_failures_preserve_raw_logs_without_leaking(subject,local,tmp_path,program,code):
    with pytest.raises(ValueError,match=code) as error:execute(subject,tmp_path,program,idle=2,hard=3)
    assert 'private-token' not in str(error.value) and len(local)==1
    terminal=records(tmp_path)[0]
    raw=Path(terminal['stderrPin']['path']).read_bytes()
    if code=='STDERR':assert b'private-token-never-public' in raw
    assert Path(terminal['stdoutPin']['path']).exists()


def test_file_bytes_hash_empty_and_path_order_are_unchanged(subject,local,tmp_path):
    ledger=tmp_path/'ledger';ledger.mkdir();(ledger/'z.json').write_bytes(b'');(ledger/'a.json').write_bytes('中文'.encode())
    # Execute the actual shared pin implementation on real files, not a fake reply.
    import inspect
    program="import hashlib,os,stat,json\nfrom pathlib import Path\n"+inspect.getsource(publication.need)+inspect.getsource(publication.file_pin)
    program+="\npins=[]\nfor path in sorted(Path("+repr(str(ledger))+").glob('*.json')):\n pins.append(file_pin(path))\n _observation_progress('ledger',len(pins),sum(p['bytes'] for p in pins))\nprint(json.dumps(pins))\n"
    value=json.loads(execute(subject,tmp_path,program,idle=2,hard=4))
    assert value==[publication.file_pin(p) for p in sorted(ledger.glob('*.json'))]
    assert [Path(row['path']).name for row in value]==['a.json','z.json']
    stderr=Path(records(tmp_path)[0]['stderrPin']['path']).read_bytes()
    assert '中文'.encode() not in stderr and str(ledger).encode() not in stderr


def test_real_hardlinked_input_still_fails_original_guard(subject,local,tmp_path):
    path=tmp_path/'one.json';path.write_bytes(b'original');os.link(path,tmp_path/'two.json')
    import inspect
    program="import hashlib,os,stat,json\nfrom pathlib import Path\n"+inspect.getsource(publication.need)+inspect.getsource(publication.file_pin)
    program+="\nprint(json.dumps(file_pin("+repr(str(path))+")))\n"
    with pytest.raises(ValueError):execute(subject,tmp_path,program,idle=2,hard=4)
    assert path.read_bytes()==b'original'
    assert b'HARDLINK' in Path(records(tmp_path)[0]['stderrPin']['path']).read_bytes()


def test_short_commands_share_absolute_budget_before_dispatch(subject,local,tmp_path):
    calls=[]
    with pytest.raises(ValueError,match='HARD_DEADLINE'):
        with subject.Observation(tmp_path,identity(),idle_seconds=1,hard_seconds=1) as work:
            def command(*args,timeout):calls.append(timeout);time.sleep(1.1);return b'{}'
            work.short_command(command,'inspect')
            work.run("print('{}')")
    assert calls and calls[0]<=1 and local==[]
    assert not list(tmp_path.glob('*.gate.private.json'))


def test_same_operation_cannot_be_reused_even_after_success(subject,local,tmp_path):
    with subject.Observation(tmp_path,identity(),operation_id='1'*32,idle_seconds=2,hard_seconds=4) as work:
        work.run("print('{}')\n_observation_progress('complete')")
    with pytest.raises(ValueError,match='EXISTS'):
        with subject.Observation(tmp_path,identity(),operation_id='1'*32):pass
    assert len(local)==1


def test_query_unknown_identity_cannot_unlock_or_spawn(subject,tmp_path,monkeypatch):
    with pytest.raises(RuntimeError):
        with subject.Observation(tmp_path,identity(),operation_id='2'*32) as work:
            work.dispatched=True
            raise RuntimeError('channel lost before START')
    monkeypatch.setattr(subject,'Popen',lambda *a,**k:pytest.fail('query must not dispatch observer'))
    value=subject.query_observation(tmp_path,'2'*32,release_exited=True)
    assert value['status']=='UNKNOWN_PID' and list(tmp_path.glob('*.gate.private.json'))


def test_query_exact_identity_and_release_requires_actual_absence(subject,local,tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='STALLED'):execute(subject,tmp_path,'import time\ntime.sleep(3)',idle=1,hard=2)
    terminal=records(tmp_path)[0];operation=terminal['operationId'];seen=[]
    def inspect_worker(container,expected,nonce,**kwargs):
        seen.append((container,expected,nonce))
        assert container==publication.CONTAINER and expected['argv'][-1]==nonce
        matches=[child for child in local.children if child.pid==expected['pid']]
        assert len(matches)==1 and matches[0].poll() is not None
        return dict(status='EXITED',identity=None)
    monkeypatch.setattr(subject,'inspect_worker',inspect_worker)
    result=subject.query_observation(tmp_path,operation,release_exited=True)
    assert result['status']=='EXITED_OUTCOME_UNAVAILABLE' and result['gateReleased'] is True
    assert len(seen)==1 and len(local)==1 and not list(tmp_path.glob('*.gate.private.json'))


@pytest.mark.parametrize('status',['ALIVE','IDENTITY_CHANGED','UNKNOWN'])
def test_query_never_releases_unproved_exit(subject,tmp_path,monkeypatch,status):
    with pytest.raises(RuntimeError):
        with subject.Observation(tmp_path,identity(),operation_id='3'*32) as work:
            work.dispatched=True;work.worker_identity=dict(pid=os.getpid(),startTicks='1',argv=['python','-B','-',work.nonce])
            raise RuntimeError('lost channel')
    monkeypatch.setattr(subject,'inspect_worker',lambda *args:dict(status=status,identity=None))
    result=subject.query_observation(tmp_path,'3'*32,release_exited=True)
    assert result['gateReleased'] is False and list(tmp_path.glob('*.gate.private.json'))


def test_budget_default_is_idle_900_and_absolute_1800(subject,tmp_path):
    value=subject.Observation(tmp_path,identity())
    assert value.idle_seconds==900 and value.hard_seconds==1800


@pytest.mark.parametrize('idle,hard',[(0,1800),(901,1800),(900,1801),(2,1)])
def test_budget_cannot_expand_or_disable(subject,tmp_path,idle,hard):
    with pytest.raises(ValueError,match='BUDGET'):
        subject.Observation(tmp_path,identity(),idle_seconds=idle,hard_seconds=hard)


@pytest.mark.parametrize('program,code',[
    ("print('{}')",'INCOMPLETE'),
    ("_observation_progress('history');_observation_emit('DONE',**_observation_last);print('{}')",'INCOMPLETE'),
    ("_observation_progress('history');_observation_progress('routes');print('{}')",'REGRESSED'),
    ("_observation_progress('ledger',-1,0);print('{}')",'REGRESSED'),
    ("_observation_progress('ledger',1,-1);print('{}')",'REGRESSED'),
    ("_observation_progress('ledger',True,1);print('{}')",'PROTOCOL'),
    ("_observation_progress('ledger',1,1);_observation_progress('ledger',1,2);print('{}')",'COUNTS'),
    ("import sys;sys.stderr.write('SPUG_OBSERVATION_PROGRESS ');sys.stderr.flush();print('{}')",'PROTOCOL'),
    ("import sys;sys.stderr.write('X'*70000);sys.stderr.flush();print('{}')",'PROTOCOL'),
])
def test_real_protocol_corruption_never_completes(subject,local,tmp_path,program,code):
    with pytest.raises(ValueError,match=code):
        with subject.Observation(tmp_path,identity(),idle_seconds=2,hard_seconds=4) as work:work.run(program)
    assert len(local)==1 and records(tmp_path)[0]['status']=='FAILED'


def test_failed_spawn_without_pid_blocks_new_operation(subject,tmp_path,monkeypatch):
    calls=[]
    def fail(*args,**kwargs):calls.append(args);raise OSError('private spawn failure')
    monkeypatch.setattr(subject,'Popen',fail)
    with pytest.raises(OSError):execute(subject,tmp_path,"print('{}')",idle=2,hard=3)
    assert records(tmp_path)[0]['workerIdentity'] is None
    with pytest.raises(ValueError,match='UNRESOLVED'):execute(subject,tmp_path,"print('{}')")
    assert len(calls)==1


def test_cli_exit_zero_never_releases_gate_without_worker_exit_proof(subject,local,tmp_path,monkeypatch):
    monkeypatch.setattr(subject,'inspect_worker',lambda *args,**kwargs:dict(status='ALIVE',identity=None))
    with pytest.raises(ValueError,match='EXIT_UNPROVEN'):
        execute(subject,tmp_path,"print('{}')",idle=2,hard=4)
    terminal=records(tmp_path)[0]
    assert terminal['actualExitCode']==0 and terminal['remoteExitVerified'] is False
    assert list(tmp_path.glob('*.gate.private.json')) and len(local)==1


def test_prepare_freezes_new_transport_source_and_rechecks_bytes(subject,resource,monkeypatch,tmp_path):
    import main_program_spug_resource_activation as activation
    copy=tmp_path/'transport-source.py';copy.write_bytes(Path(subject.__file__).read_bytes())
    monkeypatch.setattr(subject,'__file__',str(copy))
    task,private,*_=resource
    spec=activation.prepare(task,private,'inputs.json')
    assert publication.file_pin(copy) in spec['inputPins']
    copy.write_bytes(copy.read_bytes()+b'\n# deliberate test drift\n')
    with pytest.raises(ValueError,match='INPUT_CHANGED'):activation.unchanged_inputs(spec)


def test_real_file_replacement_is_rejected_by_original_pin(subject,local,tmp_path):
    path=tmp_path/'target.json';path.write_bytes(b'original')
    replacement=tmp_path/'replacement.json';replacement.write_bytes(b'replaced')
    import inspect
    program="import hashlib,os,stat,json\nfrom pathlib import Path\n"+inspect.getsource(publication.need)+inspect.getsource(publication.file_pin)
    program+="\noriginal_read=Path.read_bytes\ndef replaced_read(p):\n raw=original_read(p)\n if p==Path("+repr(str(path))+"):\n  os.replace("+repr(str(replacement))+","+repr(str(path))+")\n return raw\nPath.read_bytes=replaced_read\nprint(json.dumps(file_pin("+repr(str(path))+")))\n"
    with pytest.raises(ValueError):execute(subject,tmp_path,program,idle=2,hard=4)
    assert path.read_bytes()==b'replaced'
    assert b'CHANGED' in Path(records(tmp_path)[0]['stderrPin']['path']).read_bytes()


def test_progress_does_not_reset_absolute_budget_after_worker(subject,local,tmp_path):
    with pytest.raises(ValueError,match='HARD_DEADLINE'):
        with subject.Observation(tmp_path,identity(),idle_seconds=1,hard_seconds=1.4) as work:
            value=work.run("import time\ntime.sleep(.4)\nprint('{}')\n_observation_progress('complete')")
            assert json.loads(value)=={}
            work.short_command(lambda *args,**kwargs:(time.sleep(1),b'{}')[1],'inspect-after')
    terminal=records(tmp_path)[0]
    assert terminal['remoteExitVerified'] is True and terminal['status']=='FAILED'
    assert len(local)==1 and not list(tmp_path.glob('*.gate.private.json'))


def warning_records(terminal):
    summary=terminal['warningDiagnostics']
    reference=summary['diagnosticsPin']
    assert publication.file_pin(reference['path'])==reference
    value=json.loads(Path(reference['path']).read_bytes())
    for record in value['records']:
        assert publication.file_pin(record['path'])==record
    return summary,value,[json.loads(Path(p['path']).read_bytes()) for p in value['records']]


def test_real_warning_keeps_exact_formatted_text_and_original_result(subject,local,tmp_path):
    program="import warnings,json\nwarnings.simplefilter('always',DeprecationWarning)\nwarnings.warn('private-warning-text',DeprecationWarning)\nprint(json.dumps({'original':'result'}))"
    assert json.loads(execute(subject,tmp_path,program,idle=3,hard=5))=={'original':'result'}
    terminal=records(tmp_path)[0];summary,diagnostics,rows=warning_records(terminal)
    import warnings
    assert summary['count']==1 and summary['categories']=={'builtins.DeprecationWarning':1}
    assert rows[0]['warningCategory']==dict(module='builtins',name='DeprecationWarning')
    assert rows[0]['formattedWarning']==warnings.formatwarning('private-warning-text',DeprecationWarning,'<complete-spug-observation>',3)
    assert 'private-warning-text' not in json.dumps(summary)
    assert terminal['status']=='SUCCEEDED' and terminal['remoteExitVerified'] is True and len(local)==1


def test_real_warning_storm_never_renews_idle_or_progress(subject,local,tmp_path):
    program="import warnings,time\nwarnings.simplefilter('always',UserWarning)\nfor i in range(100):\n warnings.warn('warning-'+str(i),UserWarning)\n time.sleep(.03)"
    with pytest.raises(ValueError,match='STALLED'):execute(subject,tmp_path,program,idle=1,hard=3)
    terminal=records(tmp_path)[0];summary,_,rows=warning_records(terminal)
    assert summary['count']>0 and len(rows)==summary['count']
    assert terminal['lastProgress'] is None and terminal['elapsedSeconds']<3
    assert list(tmp_path.glob('*.gate.private.json')) and len(local)==1


@pytest.mark.parametrize('tail,code',[
    ("import sys;sys.stderr.write('ordinary stderr\\n');sys.stderr.flush()",'STDERR'),
    ("raise SystemExit(9)",'EXIT'),
    ("raise RuntimeError('private exception')",'STDERR'),
    ("print('{broken')",'RESULT'),
])
def test_real_warning_does_not_hide_original_failure(subject,local,tmp_path,tail,code):
    program="import warnings\nwarnings.simplefilter('always')\nwarnings.warn('first diagnostic',UserWarning)\n"+tail
    with pytest.raises(ValueError,match=code):execute(subject,tmp_path,program,idle=3,hard=5)
    terminal=records(tmp_path)[0];summary,_,_=warning_records(terminal)
    assert terminal['status']=='FAILED' and summary['count']==1 and len(local)==1


def test_warning_as_error_remains_native_exception(subject,local,tmp_path):
    program="import warnings\nwarnings.simplefilter('error',UserWarning)\nwarnings.warn('must raise',UserWarning)\nprint('{}')"
    with pytest.raises(ValueError,match='STDERR'):execute(subject,tmp_path,program,idle=3,hard=5)
    terminal=records(tmp_path)[0]
    assert terminal['warningDiagnostics']==dict(count=0,categories={},diagnosticsPin=None)
    assert b'UserWarning: must raise' in Path(terminal['stderrPin']['path']).read_bytes()


@pytest.mark.parametrize('change',[
    "warningCategory={'module':'bad/module','name':'UserWarning'}",
    "warningCategory={'module':'builtins','name':'a'*257}",
    "warningCategory={'module':'builtins','name':'UserWarning','extra':True}",
    "formattedWarning=42",
    "formattedWarning='x'*8193",
    "formattedWarning='x'*70000",
    "phase='complete'",
    "identity={'pid':123,'startTicks':'1','argv':['python3','-B','-',NONCE]}",
])
def test_malformed_warning_protocol_is_rejected(subject,local,tmp_path,change):
    program="values=dict(warningCategory={'module':'builtins','name':'UserWarning'},formattedWarning='private')\n"
    if change.startswith('identity='):program+='_observation_'+change+'\n'
    else:program+='values.update('+change+')\n'
    program+="_observation_emit('WARNING',**values)\nprint('{}')"
    with pytest.raises(ValueError,match='WORKER_IDENTITY_CHANGED' if change.startswith('identity=') else ''):
        execute(subject,tmp_path,program,idle=3,hard=5)
    terminal=records(tmp_path)[0]
    assert terminal['status']=='FAILED' and len(local)==1
    assert terminal['warningDiagnostics']['count']==0


def test_warnings_of_distinct_real_categories_are_counted_without_filter_changes(subject,local,tmp_path):
    program="import warnings\nbefore=list(warnings.filters)\nwarnings.warn('one',UserWarning)\nwarnings.warn('two',RuntimeWarning)\nassert warnings.filters==before\nprint('{}')"
    assert json.loads(execute(subject,tmp_path,program,idle=3,hard=5))=={}
    summary,_,rows=warning_records(records(tmp_path)[0])
    assert summary['count']==2 and summary['categories']=={'builtins.UserWarning':1,'builtins.RuntimeWarning':1}
    assert len(rows)==2


def test_real_atexit_warning_after_done_is_diagnostic_only(subject,local,tmp_path):
    program="import atexit,warnings\natexit.register(lambda:warnings.warn('shutdown diagnostic',UserWarning))\nprint('{}')"
    assert json.loads(execute(subject,tmp_path,program,idle=3,hard=5))=={}
    terminal=records(tmp_path)[0];summary,_,rows=warning_records(terminal)
    assert summary['count']==1 and terminal['status']=='SUCCEEDED' and terminal['remoteExitVerified'] is True
    assert terminal['lastProgress']['event']=='DONE' and terminal['lastProgress']['phase']=='complete'
    assert rows[0]['sequence']>terminal['lastProgress']['sequence'] and terminal['lastProgress']['completedFiles']==0
    assert 'shutdown diagnostic' in rows[0]['formattedWarning'] and len(local)==1


@pytest.mark.parametrize('callback',["lambda:_observation_progress('complete')","lambda:_observation_emit('DONE',**_observation_last)"])
def test_real_atexit_progress_or_second_done_is_still_rejected(subject,local,tmp_path,callback):
    program="import atexit\natexit.register("+callback+")\nprint('{}')"
    with pytest.raises(ValueError,match='WORKER_IDENTITY_CHANGED'):
        execute(subject,tmp_path,program,idle=3,hard=5)
    terminal=records(tmp_path)[0]
    assert terminal['status']=='FAILED' and terminal['warningDiagnostics']['count']==0 and len(local)==1
