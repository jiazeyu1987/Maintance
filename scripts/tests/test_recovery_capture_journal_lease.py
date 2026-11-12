"""Real Linux journal lease invariants; no server or business restore acceptance."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
import recovery_target_capture as capture
from recovery_archive_guard import ArchivePathGuard
from recovery_engine import RecoveryError,canonical,pinned_json
from recovery_program_execution import _directory
from minimal_capture_support import actual_pin
from test_recovery_program_restore import case,restore_case
from test_recovery_program_activation import locked,claim
from test_recovery_program_native import context,started
from test_recovery_target_capture_session import capture_protocol,construct,session as prepare_session

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual Linux inotify/O_PATH required')


def lease():
    constructor=getattr(capture,'_CaptureJournalLease',None)
    assert constructor is not None,'MISSING_CAPTURE_JOURNAL_CONTINUOUS_LEASE'
    return constructor()


def published(root,name='first.json'):
    path=root/name;path.write_bytes(canonical(dict(original=name)));path.chmod(0o600)
    return actual_pin(path)


def session(tmp_path):
    result=capture.MainTargetCapture.__new__(capture.MainTargetCapture)
    parent=tmp_path/'private';parent.mkdir(mode=0o700)
    result._parent=parent;result._journal=parent/'session';result._journal.mkdir(mode=0o700)
    result.root=parent/'capture';result.root.mkdir(mode=0o700)
    result._identities={p:_directory(p,'TEST_DIRECTORY') for p in (parent,result._journal,result.root)}
    result._closed=False;result._state='PREPARED';result.config={'source':{}};result.source={}
    result._raw=canonical(result.config);result._pins={};result._journal_lease=lease()
    result._context=SimpleNamespace(_target_capture_session=result)
    result._view=SimpleNamespace(_context=result._context)
    result._custody=object();result._native=SimpleNamespace(protection_custody=result._custody,original_pins=[])
    result._observer=capture._CaptureProcessObserver(result)
    return result


def test_repeated_completed_checks_do_not_hash_originals_again(tmp_path,monkeypatch):
    original=capture.actual_pin;calls=[]
    def read(path,*args,**kwargs):
        calls.append(str(path));return original(path,*args,**kwargs)
    monkeypatch.setattr(capture,'actual_pin',read)
    reference=published(tmp_path);guard=lease();pins={reference['path']:reference}
    try:
        guard.retain(reference);assert calls==[reference['path']]
        for _ in range(1000):guard.check(pins)
        assert calls==[reference['path']]
    finally:guard.close()


@pytest.mark.parametrize('mutation',['rewrite','restore','replace','chmod','hardlink','ancestor'])
def test_completed_original_changes_fail_and_remain_latched(tmp_path,mutation):
    root=tmp_path/'journal';root.mkdir(mode=0o700)
    reference=published(root);path=Path(reference['path']);raw=path.read_bytes()
    guard=lease();pins={reference['path']:reference}
    try:
        guard.retain(reference)
        if mutation=='rewrite':path.write_bytes(raw)
        elif mutation=='restore':path.write_bytes(b'changed');path.write_bytes(raw)
        elif mutation=='replace':path.unlink();path.write_bytes(raw)
        elif mutation=='chmod':path.chmod(0o400)
        elif mutation=='hardlink':os.link(path,tmp_path/'alias')
        else:root.chmod(0o755);root.chmod(0o700)
        with pytest.raises(RecoveryError):guard.check(pins)
        if mutation=='chmod':path.chmod(0o600)
        elif mutation=='hardlink':(tmp_path/'alias').unlink()
        with pytest.raises(RecoveryError):guard.check(pins)
    finally:guard.close()


def test_legitimate_append_keeps_old_and_new_originals_protected(tmp_path):
    guard=lease();first=published(tmp_path);pins={first['path']:first}
    try:
        guard.retain(first);second=published(tmp_path,'second.json')
        guard.retain(second);pins[second['path']]=second;guard.check(pins)
        Path(first['path']).write_bytes(Path(first['path']).read_bytes())
        with pytest.raises(RecoveryError):guard.check(pins)
    finally:guard.close()


def test_append_does_not_discard_preexisting_queued_mutation(tmp_path):
    guard=lease();first=published(tmp_path)
    try:
        guard.retain(first);Path(first['path']).write_bytes(Path(first['path']).read_bytes())
        second=published(tmp_path,'second.json')
        with pytest.raises(RecoveryError):guard.retain(second)
        with pytest.raises(RecoveryError):guard.check({first['path']:first,second['path']:second})
    finally:guard.close()


def test_old_lease_covers_new_watch_installation_gap(tmp_path,monkeypatch):
    guard=lease();first=published(tmp_path);second=published(tmp_path,'second.json')
    try:
        guard.retain(first);watch=ArchivePathGuard._watch;changed=[]
        def install(self,path,*args,**kwargs):
            result=watch(self,path,*args,**kwargs)
            if Path(path)==Path(second['path']) and not changed:
                changed.append(True);Path(first['path']).write_bytes(Path(first['path']).read_bytes())
            return result
        monkeypatch.setattr(ArchivePathGuard,'_watch',install)
        with pytest.raises(RecoveryError):guard.retain(second)
        assert changed
    finally:guard.close()


def test_new_original_is_hashed_after_its_watch_is_installed(tmp_path,monkeypatch):
    guard=lease();reference=published(tmp_path);original=capture.actual_pin;observed=[]
    def read(path,*args,**kwargs):
        observed.append(True);Path(path).write_bytes(Path(path).read_bytes())
        return original(path,*args,**kwargs)
    monkeypatch.setattr(capture,'actual_pin',read)
    try:
        with pytest.raises(RecoveryError):guard.retain(reference)
        assert observed
    finally:guard.close()


def test_pin_map_cannot_be_rebased_in_memory(tmp_path):
    guard=lease();reference=published(tmp_path)
    try:
        guard.retain(reference);altered=deepcopy(reference);altered['sha256']='0'*64
        with pytest.raises(RecoveryError):guard.check({altered['path']:altered})
        with pytest.raises(RecoveryError):guard.check({reference['path']:reference})
    finally:guard.close()


def test_unknown_member_is_rejected_by_session(tmp_path):
    s=session(tmp_path)
    try:
        s._record('first.json',dict(original=True));s.check()
        (s._journal/'unknown.json').write_bytes(b'{}')
        with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_JOURNAL_CHANGED'):s.check()
    finally:s.close()


def test_active_intent_still_gets_full_hash_on_each_check(tmp_path,monkeypatch):
    s=session(tmp_path);reference=published(s._journal,'stream-00001.json')
    s._observer.active=dict(path=Path(reference['path']),intent_pin=reference)
    original=capture.actual_pin;calls=[]
    def read(path,*args,**kwargs):
        calls.append(str(path));return original(path,*args,**kwargs)
    monkeypatch.setattr(capture,'actual_pin',read)
    try:
        for _ in range(3):s.check()
        assert calls==[reference['path']]*3
        Path(reference['path']).write_bytes(b'changed')
        with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_JOURNAL_CHANGED'):s.check()
    finally:s.close()


def test_fault_does_not_block_actual_child_terminal_record(tmp_path):
    s=session(tmp_path);first=s._record('first.json',dict(original=True))
    reference=published(s._journal,'stream-00001.json');finished=[]
    s._view.finish_invocation=lambda token,pin:finished.append((token,pinned_json(pin)))
    process=subprocess.Popen([sys.executable,'-c','pass']);assert process.wait(timeout=5)==0
    s._observer.active=dict(path=Path(reference['path']),value=dict(actualExitCode=None,state='TERMINAL_UNKNOWN'),
        intent_pin=reference,token=7,process=process,pid=os.getpid(),dump=False)
    try:
        Path(first['path']).write_bytes(Path(first['path']).read_bytes())
        with pytest.raises(RecoveryError):s._observer.finished(process)
        assert finished==[(7,dict(actualExitCode=0,state='SUCCEEDED',finishedAt=finished[0][1]['finishedAt']))]
        assert s._observer.active is None
        terminal=s._pins[reference['path']];assert pinned_json(terminal)['actualExitCode']==0
        s._state='FAILED_RETAINED';failure=s._record('failure.json',dict(originalFailureRetained=True))
        assert pinned_json(failure)==dict(originalFailureRetained=True)
        with pytest.raises(RecoveryError):s.check()
    finally:s.close()


def test_actual_dump_terminal_is_promoted_before_export_protection_recheck(tmp_path):
    s=session(tmp_path);reference=published(s._journal,'stream-00001.json');checked=[]
    s._view.finish_invocation=lambda token,pin:None
    def recheck(process):
        s.check();checked.append(s._pins[reference['path']])
    s._lease=SimpleNamespace(_finish_export=recheck)
    s.guard=lambda **kwargs:s.check()
    process=subprocess.Popen([sys.executable,'-c','pass']);assert process.wait(timeout=5)==0
    s._observer.active=dict(path=Path(reference['path']),value=dict(actualExitCode=None,state='TERMINAL_UNKNOWN'),
        intent_pin=reference,token=7,process=process,pid=os.getpid(),dump=True)
    try:
        s._observer.finished(process)
        assert len(checked)==1 and pinned_json(checked[0])['actualExitCode']==0
    finally:s.close()


def test_close_is_idempotent_and_releases_owned_descriptors(tmp_path):
    before=len(list(Path('/proc/self/fd').iterdir()));guard=lease()
    for i in range(4):guard.retain(published(tmp_path,str(i)+'.json'))
    assert len(list(Path('/proc/self/fd').iterdir()))>before
    guard.close();guard.close()
    assert len(list(Path('/proc/self/fd').iterdir()))==before


@pytest.mark.parametrize('failure',['object-permission','resource-after-record'])
def test_failed_actual_preparation_closes_lease_before_context_exit(capture_protocol,monkeypatch,failure):
    h=capture_protocol
    if failure=='object-permission':
        descriptor=pinned_json(h.capture_config['source']['objectSourcePin'])
        Path(descriptor['credentialReference']['path']).chmod(0o644)
    else:
        original=capture.MainTargetCapture._admit_resources
        def reject(self):
            original(self);raise RecoveryError('TEST_RESOURCE_REJECTED')
        monkeypatch.setattr(capture.MainTargetCapture,'_admit_resources',reject)
    claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd) as ctx:
            native=construct(h,ctx);before=len(list(Path('/proc/self/fd').iterdir()))
            with pytest.raises(Exception,match='MINIMAL_SECRET_MODE_REQUIRED|TEST_RESOURCE_REJECTED'):
                prepare_session(h,native)
            retained=ctx._target_capture_session
            assert retained.snapshot()['state']=='FAILED_RETAINED'
            assert any(Path(p['path']).name=='failure.json' for p in retained.snapshot()['originalResultPins'])
            assert len(list(Path('/proc/self/fd').iterdir()))==before
            retained.close();assert len(list(Path('/proc/self/fd').iterdir()))==before
