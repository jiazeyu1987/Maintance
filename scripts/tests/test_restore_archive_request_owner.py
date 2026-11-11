"""Ordinary controller/A1 seam using real originals, never a business restore.

The file-backed HTTP transport is a protocol carrier, not live admission proof.
Portable nodes deliberately STOP at the Linux custody boundary.  Linux-only
nodes assert POSIX (never skip) and exercise real custody and three-file writes;
run them with a private --basetemp whose ancestors are not group/world writable.
"""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
sys.path.insert(0, str(ROOT/'backend/src/main/resources'))
sys.path.insert(0, str(ROOT/'scripts/tests'))

import recovery_control_executor as executor
import recovery_control_restore_catalogue as catalogue
import recovery_control_smallapp_native as native_module
from recovery_control_smallapp import canonical, decode
import recovery_restore_inputs as inputs
from test_recovery_restore_inputs import Originals


class CustodyBoundary(RuntimeError):
    """Successful derivation reached custody; this is NOT for_request success."""


class Case(Originals):
    def __init__(self, root):
        super().__init__(root)
        self.owner['targets'].update({'target-C':{'guard':2}, 'target-D':{'guard':3}})
        self.owner['unselectedPolicy'] = {'strict':False, 'versions':[1, {'two':2}]}
        credential = root/'transport-credential.json'
        self.write(credential, {'headers':{'Authorization':'Bearer '+'A'*43}})
        self.source['archiveCatalogue']['sourceAdmissionPin'] = self.write(root/'source-access.json',
            dict(schemaVersion='SmallAppSourceCatalogueAccess/v1',
                 selectionUrl='http://127.0.0.1:1/selections',
                 authCredentialRef=dict(path=str(credential), uid=0, gid=0, mode=0o600),
                 applicationId='app-A', engineSelectionRef='safe-engine'))
        self.configuration = dict(taskRoot=str(root), registryRoot=str(root/'registry'))
        self.native = native_module.Native(self.write(root/'control.json', self.configuration))
        self.response = root/'source-response.json'
        self.source_requests = []

    def prepare(self, increments=0, *, historical=False):
        scope = self.scope
        if historical:
            old_identity = self.write(self.root/'old/identity.json',
                json.loads(Path(self.identity['path']).read_text(encoding='utf-8')))
            scope = self.write(self.root/'old/scope.json',
                dict(schemaVersion='RecoverySourceScope/v1', sourceIdentityPin=old_identity))
            self.source['archiveCatalogue'].update(schemaVersion='RecoveryArchiveCatalogue/v2',
                sourceScopePins=[self.scope, scope])
        parents = []
        for index in range(increments):
            parents.append(self.point('ancestor-'+str(index), parents, scope=scope))
        self.selected = self.point('backup-new', parents, scope=scope)
        self.chain = parents+[self.selected]
        self.base_pin = self.write(self.root/'owner.json', self.owner)
        self.request_pin = self.write(Path(self.owner['operationsRoot'])/
            self.request['operationId']/'request.json', self.request)
        self.allow([decode(Path(pin['path']).read_bytes())['backupId'] for pin in self.chain])
        return self

    def allow(self, references, **row_changes):
        row = dict(sourceConfigRef='source-A', applicationId='app-A', engineSelectionRef='safe-engine',
            historyErrorCode=None, recoveryPointRefs=references)
        row.update(row_changes)
        self.write(self.response, dict(observedAt=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            applications=[row]))

    def transport(self, monkeypatch):
        case = self
        class Response(io.BytesIO):
            status = 200
        class FileTransport:
            def open(self, request, timeout):
                # Run source_admits itself, including credential, deadline,
                # status/size/decode/freshness/source/history checks.
                assert request.full_url == 'http://127.0.0.1:1/selections'
                assert request.get_method() == 'GET' and timeout == 10
                assert request.get_header('Authorization') == 'Bearer '+'A'*43
                case.source_requests.append(request.full_url)
                return Response(case.response.read_bytes())
        monkeypatch.setattr(catalogue.urllib.request, 'build_opener', lambda *handlers:FileTransport())

    def observe_derivation(self, monkeypatch, *, before=None, after=None):
        real = inputs.derive_archive_restore_owner
        calls = []
        def deriving(owner, request, binding, **kwargs):
            assert callable(kwargs.get('guard')) and kwargs.get('reader') is None
            call = dict(owner=deepcopy(owner), request=deepcopy(request), binding=deepcopy(binding))
            calls.append(call)
            if before is not None:
                before()
            call['result'] = real(owner, request, binding, **kwargs)
            if after is not None:
                after()
            return call['result']
        monkeypatch.setattr(inputs, 'derive_archive_restore_owner', deriving)
        return calls

    def stop_at_custody(self, monkeypatch):
        reached = []
        def stop(path, task_root):
            assert Path(task_root) == self.root
            assert Path(path) == self.request_root and Path(path).is_dir()
            reached.append(path)
            raise CustodyBoundary('LINUX_CUSTODY_NOT_EXECUTED')
        monkeypatch.setattr(native_module, 'directory', stop)
        return reached

    def run(self):
        return catalogue.for_request(self.native, self.configuration, self.request, self.base_pin)

    def snapshot(self):
        return {path:path.read_bytes() for path in self.root.rglob('*') if path.is_file()}


@pytest.fixture
def case(tmp_path_factory, monkeypatch):
    value = Case(tmp_path_factory.mktemp('ordinary-owner').resolve())
    value.transport(monkeypatch)
    return value


@pytest.mark.parametrize('increments', [0,2], ids=['full','full-two-increments'])
@pytest.mark.parametrize('target', ['target-B','target-C','target-D'])
def test_portable_request_calls_real_shared_derivation_before_custody_stop(case, monkeypatch, increments, target):
    f = case
    f.request['targetConfigRef'] = target
    f.prepare(increments)
    f.controller_originals()
    before = f.snapshot()
    calls = f.observe_derivation(monkeypatch)
    reached = f.stop_at_custody(monkeypatch)
    with pytest.raises(CustodyBoundary, match='LINUX_CUSTODY_NOT_EXECUTED'):
        f.run()
    assert len(reached) == len(calls) == len(f.source_requests) == 1
    assert calls[0]['owner'] == f.owner and calls[0]['request'] == f.request
    assert calls[0]['binding'] == f.binding and calls[0]['result'] == f.derived
    assert calls[0]['result']['sources']['source-A']['repositoryPointPins'] == f.chain
    assert calls[0]['result']['targets'] == f.owner['targets']
    assert f.snapshot() == before, 'Boundary STOP cannot rewrite historical originals'


def test_portable_historical_scope_is_derived_from_original_identity_paths(case, monkeypatch):
    f = case.prepare(2, historical=True)
    f.controller_originals()
    calls = f.observe_derivation(monkeypatch)
    f.stop_at_custody(monkeypatch)
    with pytest.raises(CustodyBoundary): f.run()
    assert len(calls) == 1 and calls[0]['result'] == f.derived
    selected_scope = calls[0]['result']['sources']['source-A']['sourceScopePin']
    assert selected_scope['path'] == (f.root/'old/scope.json').as_posix()
    identity = decode(Path(selected_scope['path']).read_bytes())['sourceIdentityPin']
    assert identity['path'] == (f.root/'old/identity.json').as_posix()


@pytest.mark.parametrize('failure', ['history-quarantined','foreign-engine','parent-not-admitted'])
def test_portable_current_source_and_all_parent_admission_precede_derivation(case, monkeypatch, failure):
    f = case.prepare(2)
    if failure == 'history-quarantined': f.allow(['backup-new'], historyErrorCode='POINT_QUARANTINED')
    elif failure == 'foreign-engine': f.allow(['backup-new'], engineSelectionRef='other-engine')
    else: f.allow(['backup-new'])
    calls = f.observe_derivation(monkeypatch)
    f.stop_at_custody(monkeypatch)
    error = 'SOURCE_PARENT_NOT_CURRENTLY_ELIGIBLE' if failure == 'parent-not-admitted' else 'SOURCE_POINT_NOT_CURRENTLY_ELIGIBLE'
    with pytest.raises(Exception, match='^'+error+'$'): f.run()
    assert calls == [] and not f.request_root.exists()


def test_portable_shared_derivation_rejects_stale_primary_identity_original(case, monkeypatch):
    f = case.prepare()
    Path(f.identity['path']).write_bytes(canonical({'sourceFingerprint':'foreign','databaseUuid':'foreign'}))
    calls = f.observe_derivation(monkeypatch)
    f.stop_at_custody(monkeypatch)
    with pytest.raises(Exception, match='RESTORE_INPUTS_PIN_CHANGED'): f.run()
    assert len(calls) == 1 and 'result' not in calls[0]
    assert not f.request_root.exists()


@pytest.mark.parametrize('mutation', ['owner-replaced','metadata-replaced','duplicate-added'])
def test_portable_guard_closes_discovery_to_shared_derivation_mutation(case, monkeypatch, mutation):
    f = case.prepare(2)
    fired = []
    def mutate():
        fired.append(mutation)
        if mutation == 'duplicate-added':
            path = f.root/'archives/late-duplicate/.repository/point.json'
            path.parent.mkdir(parents=True)
            path.write_bytes(Path(f.selected['path']).read_bytes())
        else:
            path = Path(f.base_pin['path']) if mutation == 'owner-replaced' else Path(f.selected['path']).parent/'manifest.json'
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(path.read_bytes())
            replacement.chmod(0o600)
            os.replace(replacement, path)
    calls = f.observe_derivation(monkeypatch, before=mutate)
    f.stop_at_custody(monkeypatch)
    with pytest.raises(Exception, match='ARCHIVE_(METADATA|DIRECTORY)_CHANGED'): f.run()
    assert fired == [mutation] and len(calls) == 1 and not f.request_root.exists()


def test_portable_final_sha_barrier_follows_actual_shared_derivation(case, monkeypatch):
    f = case.prepare(2)
    path = Path(f.chain[0]['path']).parent/'manifest.json'
    fired = []
    def mutate():
        stamp = path.stat()
        raw = path.read_bytes()
        path.write_bytes(b' '+raw[1:])
        os.utime(path, ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        fired.append(path)
    calls = f.observe_derivation(monkeypatch, after=mutate)
    f.stop_at_custody(monkeypatch)
    with pytest.raises(Exception, match='ARCHIVE_METADATA_CHANGED'): f.run()
    assert len(calls) == len(fired) == 1 and 'result' in calls[0]
    assert not f.request_root.exists()


def test_portable_shared_guard_failure_is_not_swallowed(case, monkeypatch):
    f = case.prepare()
    real = inputs.derive_archive_restore_owner
    called = []
    def deriving(owner, request, binding, **kwargs):
        guard = kwargs['guard']
        def fail():
            guard()
            called.append(True)
            raise RuntimeError('EXPLICIT_GUARD_FAILURE')
        return real(owner, request, binding, guard=fail)
    monkeypatch.setattr(inputs, 'derive_archive_restore_owner', deriving)
    f.stop_at_custody(monkeypatch)
    with pytest.raises(RuntimeError, match='^EXPLICIT_GUARD_FAILURE$'): f.run()
    assert called == [True] and not f.request_root.exists()


def test_portable_stat_guard_does_not_repeat_controller_full_hashes(case, monkeypatch):
    f = case.prepare(2)
    original = executor.pinned_read
    counts = {}
    def reading(path, *args, **kwargs):
        path = Path(path)
        counts[path] = counts.get(path,0)+1
        return original(path, *args, **kwargs)
    monkeypatch.setattr(executor, 'pinned_read', reading)
    f.stop_at_custody(monkeypatch)
    with pytest.raises(CustodyBoundary): f.run()
    access = Path(f.source['archiveCatalogue']['sourceAdmissionPin']['path'])
    assert counts.pop(access) == 1  # Existing source_admits reads its own access.
    assert counts and set(counts.values()) == {2}
    assert all(path.suffix == '.json' for path in counts)


def test_persistence_tail_is_exactly_the_original_three_file_contract():
    tree = ast.parse((ROOT/'backend/src/main/resources/recovery_control_restore_catalogue.py').read_text(encoding='utf-8'))
    node = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == 'for_request')
    start = next(index for index,node in enumerate(node.body) if isinstance(node,ast.ImportFrom) and
                 node.module == 'recovery_control_smallapp_native')
    tail = ast.Module(body=node.body[start:], type_ignores=[])
    assert hashlib.sha256(ast.dump(tail, include_attributes=False).encode()).hexdigest() == \
        '9e708b21626c94b89ed4adae489144174c07f6b0953a151aa4e455f028ed71ce'


@pytest.mark.parametrize('increments', [0,2], ids=['full','full-two-increments'])
@pytest.mark.parametrize('target', ['target-B','target-C','target-D'])
def test_linux_full_request_writes_and_reuses_exact_three_originals(case, increments, target):
    assert os.name == 'posix', 'Linux carrier required; this node must not be skipped'
    f = case
    f.request['targetConfigRef'] = target
    f.prepare(increments)
    before = f.snapshot()
    recovery_pin, binding_pin = f.run()  # Real Native.directory and real persist.
    directory = f.request_root/f.request['operationId']
    assert {path.name for path in directory.iterdir()} == {'restore-inputs.json','archive-point.json','recovery.json'}
    originals = dict(requestInputsPin=executor.pin(directory/'restore-inputs.json'),
        pointBindingPin=binding_pin, recoveryConfigurationPin=recovery_pin)
    verified = inputs.verify_archive_restore_inputs(f.base_pin, f.request_pin,
        request_configurations_root=str(f.request_root), originals=originals, guard=lambda:None)
    assert verified['derivedOwner'] == decode(Path(recovery_pin['path']).read_bytes())
    assert verified['derivedOwner']['sources']['source-A']['repositoryPointPins'] == f.chain
    assert all(path.read_bytes() == raw for path,raw in before.items())
    original_bytes = {path:(path.read_bytes(), path.stat().st_ino,path.stat().st_mtime_ns) for path in directory.iterdir()}
    assert f.run() == (recovery_pin,binding_pin)
    assert {path:(path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns) for path in directory.iterdir()} == original_bytes
    f.request['targetConfigRef'] = 'target-C' if target != 'target-C' else 'target-D'
    with pytest.raises(Exception, match='^ORIGINAL_RESTORE_CONFIGURATION_CHANGED$'): f.run()
    assert {path:(path.read_bytes(),path.stat().st_ino,path.stat().st_mtime_ns) for path in directory.iterdir()} == original_bytes


@pytest.mark.parametrize('name', ['restore-inputs.json','archive-point.json','recovery.json'])
def test_linux_changed_original_is_never_overwritten(case, name):
    assert os.name == 'posix', 'Linux carrier required; this node must not be skipped'
    f = case.prepare(2)
    f.run()
    path = f.request_root/f.request['operationId']/name
    path.write_bytes(canonical({'tamperedOriginal':name}))
    before = f.snapshot()
    with pytest.raises(Exception, match='^ORIGINAL_RESTORE_CONFIGURATION_CHANGED$'): f.run()
    assert f.snapshot() == before


def test_linux_failed_shared_derivation_writes_no_request_originals(case):
    assert os.name == 'posix', 'Linux carrier required; this node must not be skipped'
    f = case.prepare(2)
    Path(f.identity['path']).write_bytes(canonical({'sourceFingerprint':'foreign','databaseUuid':'foreign'}))
    before = f.snapshot()
    with pytest.raises(Exception, match='RESTORE_INPUTS_PIN_CHANGED'): f.run()
    assert not f.request_root.exists() and f.snapshot() == before


def test_linux_historical_scope_closes_exact_three_originals(case):
    assert os.name == 'posix', 'Linux carrier required; this node must not be skipped'
    f = case.prepare(2, historical=True)
    recovery_pin, binding_pin = f.run()
    owner = decode(Path(recovery_pin['path']).read_bytes())
    assert owner['sources']['source-A']['sourceScopePin']['path'] == (f.root/'old/scope.json').as_posix()
    directory = f.request_root/f.request['operationId']
    result = inputs.verify_archive_restore_inputs(f.base_pin, f.request_pin,
        request_configurations_root=str(f.request_root), guard=lambda:None,
        originals=dict(requestInputsPin=executor.pin(directory/'restore-inputs.json'),
            pointBindingPin=binding_pin, recoveryConfigurationPin=recovery_pin))
    assert result['derivedOwner'] == owner and result['clearAuthorized'] is False


def test_linux_invalid_private_directory_custody_is_not_bypassed(case):
    assert os.name == 'posix', 'Linux carrier required; this node must not be skipped'
    f = case.prepare()
    f.request_root.mkdir(mode=0o755)
    before = f.snapshot()
    with pytest.raises(Exception, match='^PRIVATE_DIRECTORY_CUSTODY_INVALID$'): f.run()
    assert not (f.request_root/f.request['operationId']).exists() and f.snapshot() == before
