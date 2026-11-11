"""MAIN publication units: real files/flock/ctx/capture/binder, finite SMB only.

The SMB client below transports local bytes over an explicit protocol seam. It
does not contact NAS or prove actualBusinessRestore; no successful publication
or native custody is mocked. Ordinary FULL regression lives in its original file.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path, PureWindowsPath
import sys
import time
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'ops/backup_engine/formal')]
from recovery_engine import RecoveryError, pin, pinned_json, write
from repository_records import Deadline, RepositoryError
from test_recovery_target_capture_session import (
    capture_protocol, case, restore_case, construct, quiesce, freeze_inputs,
    claim, locked, started, context, frozen_journals)

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual Linux files/flock required')


class LocalSmb:
    """Finite external SMB protocol; real stat/read bytes and explicit session."""
    def __init__(self, root, monkeypatch, metadata):
        self.root = root
        self.after_read = None
        self.authentication = True
        self.reads = []
        self.registrations = []
        client, protocol = ModuleType('smbclient'), ModuleType('smbprotocol')
        for module in (client, protocol):
            path = metadata/(module.__name__+'.py')
            path.write_bytes(b'# finite local SMB protocol fixture\n')
            module.__file__ = str(path)
            monkeypatch.setitem(sys.modules, module.__name__, module)
        self.modules = (client, protocol)
        client.register_session = self.register_session
        client.stat = lambda path, **kw: self.local(path).lstat()
        client.open_file = self.open_file
        client.scandir = lambda path, **kw: os.scandir(self.local(path))
        client.reset_connection_cache = lambda **kw: kw['connection_cache'].clear()

    def local(self, remote):
        parts = PureWindowsPath(remote).parts
        assert parts[0] == '\\\\finite\\share\\' and parts[1] == 'repository'
        return self.root.joinpath(*parts[2:])

    def register_session(self, server, **kw):
        assert server == 'finite' and kw['encrypt'] is True and kw['require_signing'] is True
        assert not kw['connection_cache']
        self.registrations.append(kw['connection_cache'])
        value = SimpleNamespace(connection=SimpleNamespace(transport=SimpleNamespace(connected=True),
            require_signing=True, client_guid='finite-independent'), encrypt_data=self.authentication,
            session_id=len(self.registrations))
        kw['connection_cache']['finite'] = value
        return value

    @contextmanager
    def open_file(self, remote, **kw):
        assert kw['mode'] == 'rb' and kw['share_access'] == 'r'
        path = self.local(remote)
        self.reads.append(path)
        with path.open('rb') as stream:
            yield stream
        if self.after_read is not None:
            self.after_read(path)


def readback_configuration(tmp_path, monkeypatch):
    repository = tmp_path/'preservation-repository'; repository.mkdir(mode=0o700)
    metadata = tmp_path/'preservation-protocol-inputs'; metadata.mkdir(mode=0o700)
    records = tmp_path/'preservation-readback-records'; records.mkdir(mode=0o700)
    protocol = LocalSmb(repository, monkeypatch, metadata)
    credential = write(metadata/'credential.json', dict(schemaVersion='RepositorySmbCredential/v1',
        server='finite', share='share', username='finite-user', password='finite-password'))
    value = dict(schemaVersion='RepositorySmbReadbackConfig/v1', uncRoot='\\\\finite\\share',
        repositoryRelativePath='repository', repositoryRoot=str(repository), credentialPin=credential,
        port=445, authProtocol='ntlm', recordRoot=str(records), maximumRecordBytes=1024*1024,
        maximumTotalRecordBytes=4*1024*1024, libraryPins=[pin(m.__file__) for m in protocol.modules])
    return repository, protocol, value


@pytest.mark.parametrize('problem', ['expected', 'inode', 'size', 'link', 'authentication'])
def test_verified_smb_reader_rejects_actual_protocol_drift(tmp_path, monkeypatch, problem):
    repository, protocol, config = readback_configuration(tmp_path, monkeypatch)
    path = repository/'payload'; path.write_bytes(b'actual original bytes\n'); expected = pin(path)
    if problem == 'expected': expected['sha256'] = 'f'*64
    elif problem == 'inode':
        def replace(actual):
            raw = actual.read_bytes(); actual.unlink(); actual.write_bytes(raw)
        protocol.after_read = replace
    elif problem == 'size': protocol.after_read = lambda actual: actual.write_bytes(b'changed')
    elif problem == 'link':
        other = repository/'other'; path.rename(other); path.symlink_to(other)
    elif problem == 'authentication': protocol.authentication = False
    module = importlib.import_module('repository_native_readback')
    codes = {'expected':'REPOSITORY_INDEPENDENT_READBACK_MISMATCH',
        'inode':'REPOSITORY_SMB_INPUT_CHANGED', 'size':'REPOSITORY_SMB_INPUT_CHANGED',
        'link':'REPOSITORY_SMB_FILE_REQUIRED', 'authentication':'REPOSITORY_SMB_AUTHENTICATION_UNPROVEN'}
    with pytest.raises(RepositoryError, match=codes[problem]):
        with module.PreservationReadback(config, Deadline(30000)) as reader:
            reader.read(str(path), expected, retain=True)
    if problem == 'authentication':
        assert protocol.registrations and protocol.registrations[-1] == {}, 'OWN_SMB_CACHE_RETAINED_AFTER_REJECTION'


def test_verified_smb_reader_retains_actual_original_and_default_light_contract(tmp_path, monkeypatch):
    repository, protocol, config = readback_configuration(tmp_path, monkeypatch)
    path = repository/'payload'; path.write_bytes(b'actual original bytes\n'); expected = pin(path)
    module = importlib.import_module('repository_native_readback')
    with module.PreservationReadback(config, Deadline(30000)) as reader:
        actual, copy = reader.read(str(path), expected, retain=True)
        assert actual == expected and Path(copy['path']).read_bytes() == path.read_bytes()
        assert reader.verify_environment is True and len(protocol.registrations) == 1
    assert module.SmbReadback.read is not module.PreservationReadback.read


@pytest.fixture
def publication_case(capture_protocol, monkeypatch, capsys, request):
    h = capture_protocol
    # This is a source MAIN candidate plus the authentic SAFE semantic
    # component, not an assertion that STANDARD packaging is already wired.
    # The isolated carrier preloads the unchanged safe_fixes output before
    # importing support; refusing LIGHT here keeps the binder's complete gate.
    import importlib.util
    builder_spec = importlib.util.spec_from_file_location('preservation_safe_builder',
        ROOT/'ops/backup_engine/build_variants.py')
    builder = importlib.util.module_from_spec(builder_spec)
    builder_spec.loader.exec_module(builder)
    frozen, _ = builder.standard_sources()
    expected = builder.safe_fixes(frozen)['formal/formal_capture_semantics.py']
    # Candidate's only pending packaging seam is the exact, already tested
    # observer method. All SAFE capture/finalize bytes stay unchanged.
    import ast
    def method(raw):
        classes=[n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='SemanticCapture']
        assert len(classes)==1
        nodes=[n for n in classes[0].body if isinstance(n,ast.FunctionDef) and n.name=='verify_endpoint']
        assert len(nodes)==1
        n=nodes[0];return ''.join(raw.splitlines(keepends=True)[n.lineno-1:n.end_lineno])
    original=expected.decode('utf-8')
    old_method=method(original)
    new_method=method((ROOT/'ops/backup_engine/formal/formal_capture_semantics.py').read_text(encoding='utf-8'))
    assert original.count(old_method)==1
    expected=original.replace(old_method,new_method).encode('utf-8')
    import formal_capture_semantics as semantic
    import minimal_capture_support as support
    actual = Path(semantic.__file__).resolve()
    assert actual != (ROOT/'ops/backup_engine/formal/formal_capture_semantics.py').resolve()
    assert actual.read_bytes() == expected
    assert support.MinimalSemantic.__mro__[1] is semantic.SemanticCapture
    assert Path(semantic.SemanticCapture.finalize.__code__.co_filename).resolve() == actual
    with capsys.disabled():
        print('ACTUAL_SAFE_SEMANTIC='+str(actual)+' SHA256='+hashlib.sha256(expected).hexdigest(),flush=True)
    original_s3 = support.ReadOnlyS3
    class PreservationS3(original_s3):
        def absent_configuration(self,bucket,configuration,error_code):
            codes={'lifecycle':'NoSuchLifecycleConfiguration',
                'replication':'ReplicationConfigurationNotFoundError',
                'encryption':'ServerSideEncryptionConfigurationNotFoundError'}
            assert bucket == 'private' and codes[configuration] == error_code
            raw=('<Error><Code>'+error_code+'</Code></Error>').encode()
            return dict(bucket=bucket,configuration=configuration,httpStatus=404,errorCode=error_code,
                rawSha256=hashlib.sha256(raw).hexdigest(),rawBytes=len(raw))
    monkeypatch.setattr(support,'ReadOnlyS3',PreservationS3)
    # This fixture adds owner policy, so reserve a separate owner/root before
    # binding. The upstream capture fixture's original reservation stays intact.
    operations = h.case['root']/'preservation-operations'; operations.mkdir(mode=0o700)
    h.root = operations/'restore-1'; h.root.mkdir(mode=0o700)
    host = h.case['root']/'preservation-host'; host.mkdir(mode=0o700)
    import recovery_resource_admission as admission
    monkeypatch.setattr(admission, 'HOST_ROOT', host)
    h.owner['operationsRoot'] = str(operations)
    h.owner['targets']['target57']['replacement']['storage']['protectedRoots'].append(str(operations))
    h.case['policy']['baselineTargetPin'] = write(h.case['root']/'preservation-target.json',h.owner['targets']['target57'])
    h.capture_config['limits']['workSeconds'] = 180
    h.case['base_pin'] = write(h.case['root']/'preservation-capture.json',h.capture_config)
    h.case['policy']['captureConfigurationPins'] = {'source57':h.case['base_pin']}
    h.owner['targetProgramPolicies']['target57'] = deepcopy(h.case['policy'])
    repository, protocol, readback = readback_configuration(h.case['root'], monkeypatch)
    (repository/'archives').mkdir(mode=0o700)
    readback['recordRoot'] = str(h.root/'target-preservation'/'publication')
    problem = getattr(request,'param',None)
    if problem == 'schema':readback['port']='invalid'
    elif problem == 'credential':
        credential=pinned_json(readback['credentialPin']);credential['share']='other-share'
        readback['credentialPin']=write(h.case['root']/'bad-preservation-credential.json',credential)
    elif problem == 'library':Path(protocol.modules[0].__file__).write_bytes(b'# drifted client bytes\n')
    elif problem == 'authentication':protocol.authentication=False
    elif problem == 'capacity':
        module=importlib.import_module('recovery_target_preservation')
        original_usage=module.shutil.disk_usage
        monkeypatch.setattr(module.shutil,'disk_usage',lambda path:
            SimpleNamespace(total=1024**3,used=1024**3-1,free=1) if Path(path)==repository else original_usage(path))
    metadata = h.case['root']/'preservation-protocol-inputs'
    scope = pinned_json(pinned_json(h.capture_config['source']['objectSourcePin'])['sourceScopePin'])
    repository_pin = write(metadata/'preservation-repository.json', dict(
        schemaVersion='MainTargetPreservationRepository/v1', repositoryId='finite-target-preservation',
        repositoryRoot=str(repository), sourceIdentityPin=scope['sourceIdentityPin'],
        captureBinderPin=pin(importlib.import_module('formal_capture_recovery_inputs').__file__),
        readbackConfigPin=write(metadata/'readback.json', readback)))
    policy = dict(schemaVersion='MainTargetPreservationPolicy/v1', targetConfigRef='target57',
        captureRef='source57', captureConfigurationPin=h.case['base_pin'], repositoryConfigurationPin=repository_pin,
        backupEpochPolicy=deepcopy(h.case['epoch']), maxArchiveBytes=8*1024*1024,
        maxReadbackRecordBytes=4*1024*1024, maxPreservationSeconds=180, minimumFreeBytes=1)
    h.preservation_policy = write(metadata/'preservation-policy.json', policy)
    h.owner['targetPreservationPolicies'] = {'target57': h.preservation_policy}
    freeze_inputs(h)
    h.repository, h.smb_protocol, h.repository_pin = repository, protocol, repository_pin
    from recovery_target_capture import MainTargetCapture
    from repository_minimal import CapturedPublisher
    from repository_native_readback import PreservationReadback
    for cls, method, phase in ((MainTargetCapture,'capture','capture'),
            (CapturedPublisher,'stream','copy'),(PreservationReadback,'verify','full-readback')):
        original = getattr(cls,method)
        def timed(*args,_original=original,_phase=phase,**kwargs):
            start = time.monotonic()
            try:return _original(*args,**kwargs)
            finally:
                with capsys.disabled():
                    print('PRESERVATION_TIMING '+json.dumps(dict(phase=_phase,
                        elapsedSeconds=round(time.monotonic()-start,3))),flush=True)
        monkeypatch.setattr(cls,method,timed)
    return h


@pytest.mark.parametrize('publication_case',
    ['schema','credential','library','authentication','capacity'],indirect=True)
def test_publication_admits_repository_before_capture_or_quiescence(publication_case):
    h=publication_case;claim(h.case)
    module=importlib.import_module('recovery_target_preservation')
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=__import__('recovery_engine').Budget(240000)) as ctx:
            native=construct(h,ctx)
            codes='REPOSITORY_SMB_CONFIGURATION_INVALID|REPOSITORY_SMB_CREDENTIAL_TARGET_MISMATCH|REPOSITORY_SMB_INPUT_PIN_CHANGED|REPOSITORY_SMB_AUTHENTICATION_UNPROVEN|PRESERVATION_ARCHIVE_CAPACITY_INSUFFICIENT'
            before=list(h.engine.actions)
            with pytest.raises(RepositoryError,match=codes):
                module.TargetPreservation.prepare(native,policy_pin=h.preservation_policy,
                    reservation_pin=h.reservation)
            assert h.engine.actions==before
            assert native.running_applications=={'backend','frontend'} and native.storage_running
            assert not (h.root/'target-preservation'/'publication'/'archive-proof.json').exists()


@pytest.mark.parametrize('problem',['held','read-guard','write-unknown'])
def test_publication_requires_original_repository_byte_lock(publication_case,problem):
    import select
    import subprocess
    h=publication_case;claim(h.case)
    module=importlib.import_module('recovery_target_preservation')
    control=h.repository/'.repository-control';control.mkdir(mode=0o700)
    process=None
    if problem=='held':
        code="import fcntl,sys; f=open(sys.argv[1],'a+b'); f.write(b'\\0'); f.flush(); fcntl.lockf(f,fcntl.LOCK_EX|fcntl.LOCK_NB,1,0); print('READY',flush=True); sys.stdin.buffer.read(1)"
        process=subprocess.Popen([sys.executable,'-B','-c',code,str(control/'write.lock')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        assert select.select([process.stdout],[],[],5)[0] and process.stdout.readline()==b'READY\n'
    else:(control/('recovery-read-guard.json' if problem=='read-guard' else 'write-unknown.json')).write_bytes(b'{')
    try:
        with locked(h.case) as fd:
            _,binding,_=started(h,fd)
            with context(h,binding,fd,budget=__import__('recovery_engine').Budget(240000)) as ctx:
                native=construct(h,ctx);before=list(h.engine.actions)
                expected=BlockingIOError if problem=='held' else RepositoryError
                with pytest.raises(expected):
                    module.TargetPreservation.prepare(native,policy_pin=h.preservation_policy,
                        reservation_pin=h.reservation)
                assert h.engine.actions==before and native.running_applications=={'backend','frontend'}
                assert not list(control.glob('preservation-holds/*'))
    finally:
        if process is not None:
            process.communicate(b'X',timeout=5)
            assert process.returncode==0


def test_publication_rechecks_original_repository_lock_identity(publication_case):
    h=publication_case;claim(h.case)
    module=importlib.import_module('recovery_target_preservation')
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=__import__('recovery_engine').Budget(240000)) as ctx:
            native=construct(h,ctx)
            publication=module.TargetPreservation.prepare(native,policy_pin=h.preservation_policy,
                reservation_pin=h.reservation)
            path=h.repository/'.repository-control'/'write.lock'
            assert path.exists(), 'ORIGINAL_REPOSITORY_BYTE_LOCK_REQUIRED'
            path.rename(path.with_name('retained-original-write.lock'));path.write_bytes(b'\0')
            with pytest.raises(RepositoryError,match='REPOSITORY_OWNER_LOST'):publication.check()
            with pytest.raises(RepositoryError,match='REPOSITORY_OWNER_LOST'):publication.close()


@pytest.mark.parametrize('drift',['inode','directory'])
def test_same_process_main_materials_publish_readback_and_durable_hold(publication_case,drift):
    h = publication_case; claim(h.case)
    module = importlib.import_module('recovery_target_preservation')
    with locked(h.case) as fd:
        _, binding, _ = started(h, fd)
        with context(h, binding, fd, budget=__import__('recovery_engine').Budget(240000)) as ctx:
            native = construct(h, ctx)
            publication = module.TargetPreservation.prepare(native, policy_pin=h.preservation_policy,
                reservation_pin=h.reservation)
            quiesce(h, native); before = frozen_journals(h)
            proof_pin = publication.capture_and_publish(); proof = pinned_json(proof_pin)
            verified = module.validate_archive(native, proof_pin)
            assert verified.archive_pin == proof_pin
            assert proof['state'] == 'ARCHIVED_VERIFIED' and proof['payloadContentVerified'] is True
            assert proof['serverDurabilityVerified'] is proof['independentFailureDomain'] is False
            point = pinned_json(proof['pointPin']); assert point['pointType'] == 'FULL' and point['parentPointPins'] == []
            for reference in point['payloadRefs']: assert pin(reference['path']) == reference
            assert set(module.preservation_holds(publication.configuration, guard=publication.check)) == {proof['pointPin']['path']}
            hold = h.repository/'.repository-control'/'preservation-holds'/(h.request['operationId']+'.json')
            assert pinned_json(pin(hold))['archiveProofPin'] == proof_pin
            assert len(h.smb_protocol.registrations) >= 1 and h.smb_protocol.reads
            assert all(p.read_bytes() == raw for p, raw in before.items())
            assert h.transport.scheduler == 'OFF' and not h.transport.releases
            with pytest.raises(RecoveryError, match='PROGRAM_TARGET_CAPTURE_PENDING'): ctx.stage(None)
            with pytest.raises(RecoveryError, match='PROGRAM_CAPTURE_PRESERVATION_REQUIRED'):
                publication.session.handoff(verified)
            with pytest.raises((RecoveryError, RepositoryError), match='PRESERVATION_ALREADY_USED'):
                publication.capture_and_publish()
            if drift == 'inode':
                payload=Path(point['payloadRefs'][0]['path'])
                raw=payload.read_bytes()
                payload.rename(publication.root/'retained-original-payload')
                payload.write_bytes(raw)
            else:(publication.archive/'unregistered-payload').write_bytes(b'extra archive bytes')
            with pytest.raises(RecoveryError,match='ARCHIVED_PAYLOAD_CHANGED|ARCHIVE_WATCH_CHANGED|PATH_ALIAS_REJECTED'):
                publication.check()
            publication.close()
            assert hold.exists() and Path(proof_pin['path']).exists()


def test_publication_failure_preserves_actual_session_uncertainty(publication_case,monkeypatch):
    """Fault injection at capture boundary; no fake successful material/child."""
    from formal_snapshot_linux import FormalSnapshotError
    h=publication_case;claim(h.case)
    module=importlib.import_module('recovery_target_preservation')
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd,budget=__import__('recovery_engine').Budget(240000)) as ctx:
            native=construct(h,ctx)
            publication=module.TargetPreservation.prepare(native,policy_pin=h.preservation_policy,
                reservation_pin=h.reservation)
            quiesce(h,native)
            error=FormalSnapshotError('FINITE_CAPTURE_CLIENT_REAP_UNKNOWN')
            error.clientCleanupUncertain=True
            def failed_capture():
                publication.session._fail(error)
                raise error
            monkeypatch.setattr(publication.session,'capture',failed_capture)
            with pytest.raises(FormalSnapshotError,match='FINITE_CAPTURE_CLIENT_REAP_UNKNOWN'):
                publication.capture_and_publish()
            assert publication.session.snapshot()['terminalUnknown'] is True
            failure=pinned_json(pin(publication.root/'failure.json'))
            assert failure['terminalUnknown'] is True
            assert h.transport.scheduler=='OFF' and not h.transport.releases
            assert not (publication.root/'archive-proof.json').exists()
            publication.close()


@pytest.mark.parametrize('problem', ['missing', 'extra', 'link', 'malformed'])
def test_pending_or_invalid_durable_hold_is_never_absent(tmp_path, problem):
    module = importlib.import_module('recovery_target_preservation')
    repository = tmp_path/'repository'; repository.mkdir(mode=0o700)
    holds = repository/'.repository-control'/'preservation-holds'; holds.mkdir(mode=0o700, parents=True)
    path = holds/'restore-1-intent.json'
    path.write_bytes(b'{}' if problem != 'malformed' else b'{')
    if problem == 'extra': (holds/'unrecognized').write_bytes(b'x')
    elif problem == 'link':
        outside = tmp_path/'outside'; path.rename(outside); path.symlink_to(outside)
    configuration = SimpleNamespace(root=repository, value={'repositoryId':'finite-target-preservation'})
    with pytest.raises((RecoveryError, RepositoryError), match='PRESERVATION_'):
        module.preservation_holds(configuration, guard=lambda:None)
