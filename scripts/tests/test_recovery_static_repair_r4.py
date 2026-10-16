"""R4 offline protocol/fault fixtures; no NAS, S3 service or recovery acceptance."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import urllib.error

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops'/'recovery'))
import recovery_engine as engine
from recovery_engine import Budget, InvocationRunner, RecoveryError, canonical, pin, write, check_pin
from recovery_engine_read_guard import RepositoryReadGuard, repository_root
from recovery_data_objects import prepare_buckets, protection


def local_executor(root, state=None):
    script = root/'executor.py'
    source = 'import time;time.sleep(5)' if state is None else (
        "import argparse,json,sys\np=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--output');a=p.parse_args()\n"
        "r=json.load(open(a.request));r.update(state="+repr(state)+",data={'protocolOnly':True});json.dump(r,open(a.output,'w'));sys.exit("+
        str({'SUCCEEDED':0,'FAILED_RETAINED':1,'TERMINAL_UNKNOWN':2}[state])+")")
    script.write_text(source, encoding='utf-8')
    return pin(Path(sys.executable)), pin(script)


@pytest.mark.parametrize('stage,state', [(stage,state) for stage in ('streams.json','exit.json','stdout-pin','result-pin')
                                      for state in (None,'TERMINAL_UNKNOWN') if not (stage == 'result-pin' and state is None)])
def test_runner_recording_or_pin_failure_preserves_unknown(tmp_path, monkeypatch, stage, state):
    python, script = local_executor(tmp_path, state)
    runner = InvocationRunner(tmp_path, Budget(150 if state is None else 5000))
    original_write, original_pin = engine.write, engine.pin
    def broken_write(path, value):
        if Path(path).name == stage: raise OSError('protocol recording fault')
        return original_write(path, value)
    def broken_pin(path):
        if (stage == 'stdout-pin' and Path(path).name == 'stdout') or (stage == 'result-pin' and Path(path).name == 'result.json'):
            raise OSError('protocol Pin fault')
        return original_pin(path)
    monkeypatch.setattr(engine, 'write', broken_write); monkeypatch.setattr(engine, 'pin', broken_pin)
    with pytest.raises(Exception) as failure:
        runner.run(python, script, dict(operationId='op', requestId='req', action='PROTOCOL'), guard=lambda: None)
    assert failure.value.unknown and failure.value.exit_code == runner.actual_exit_code
    assert runner.actual_exit_code is not None and not runner.readers_terminal
    assert any(Path(ref['path']).name == 'intent.json' for ref in failure.value.original_pins)
    if stage != 'exit.json':
        original_exit = json.loads((tmp_path/'invocation-001'/'exit.json').read_text())
        assert original_exit['nativePid'] > 0 and original_exit['actualExitCode'] == runner.actual_exit_code


def test_original_unknown_survives_terminal_and_fault_receipt_failure(tmp_path, monkeypatch):
    def fail(*args): raise OSError('protocol full evidence failure')
    monkeypatch.setattr(engine, 'write', fail)
    with pytest.raises(RecoveryError) as failure:
        try: raise RecoveryError('ORIGINAL_REMOTE_UNKNOWN', unknown=True, exit_code=0)
        finally: engine.persist_evidence(tmp_path/'exit.json', {'state':'TERMINAL_UNKNOWN'})
    assert failure.value.unknown and failure.value.original_code == 'ORIGINAL_REMOTE_UNKNOWN'
    assert failure.value.exit_code == 0 and failure.value.fault_recording_error == 'OSError'


def repository_fixture(root):
    metadata = root/'repo'/'archives'/'first'/'.repository'; metadata.mkdir(parents=True)
    point = write(metadata/'point.json', {'protocolOnly': True})
    request = dict(operationId='op', requestId='req', selectedPointPin=point)
    request_pin = write(root/'request.json', request)
    policy = dict(repositoryId='approved-protocol-repository', repositoryPointPins=[point])
    return request, request_pin, policy


def test_guard_exact_marker_same_process_refusal_and_known_release(tmp_path):
    request, request_pin, policy = repository_fixture(tmp_path)
    with RepositoryReadGuard(request, request_pin, policy, Budget(5000)) as guard:
        value = json.loads(guard.path.read_text())
        assert set(value) == {'schemaVersion','repositoryId','operationId','requestId','requestPin','candidatePin','state','createdAt'}
        assert value['requestPin'] == request_pin and value['candidatePin'] == request['selectedPointPin']
        with pytest.raises(RecoveryError, match='REPOSITORY_ALREADY_EXECUTING'):
            with RepositoryReadGuard(request, request_pin, policy, Budget(5000)): pass
        guard.finish(terminal_known=True)
    assert not guard.path.exists()


def test_guard_byte_range_conflicts_with_independent_native_process(tmp_path):
    request, request_pin, policy = repository_fixture(tmp_path)
    source = "import os,sys\nf=open(sys.argv[1],'a+b')\ntry:\n"
    if os.name == 'nt': source += " import msvcrt;f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)\n"
    else: source += " import fcntl;fcntl.lockf(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB,1,0,os.SEEK_SET)\n"
    source += 'except OSError: sys.exit(7)\nsys.exit(0)'
    with RepositoryReadGuard(request, request_pin, policy, Budget(5000)) as guard:
        actual = subprocess.run([sys.executable, '-B', '-c', source, str(guard.lock_path)], timeout=5, capture_output=True)
        assert actual.returncode == 7
        guard.finish(terminal_known=True)
    actual = subprocess.run([sys.executable, '-B', '-c', source, str(guard.lock_path)], timeout=5, capture_output=True)
    assert actual.returncode == 0


@pytest.mark.parametrize('previous', ['ACTIVE', 'TERMINAL_UNKNOWN', 'malformed', 'write-unknown'])
def test_prior_guard_or_write_unknown_blocks_without_reconciliation(tmp_path, previous):
    request, request_pin, policy = repository_fixture(tmp_path)
    control = tmp_path/'repo'/'.repository-control'; control.mkdir()
    path = control/('write-unknown.json' if previous == 'write-unknown' else 'recovery-read-guard.json')
    path.write_text('not-json' if previous == 'malformed' else json.dumps({'state':previous}), encoding='utf-8')
    before = path.read_bytes()
    with pytest.raises(RecoveryError, match='RECONCILIATION_REQUIRED'):
        with RepositoryReadGuard(request, request_pin, policy, Budget(5000)): pass
    assert path.read_bytes() == before


def test_unknown_and_marker_change_are_retained(tmp_path):
    request, request_pin, policy = repository_fixture(tmp_path)
    with pytest.raises(RecoveryError) as failure:
        with RepositoryReadGuard(request, request_pin, policy, Budget(5000)) as guard:
            raise RecoveryError('PROTOCOL_READER_UNKNOWN', unknown=True)
    assert failure.value.unknown and json.loads(guard.path.read_text())['state'] == 'TERMINAL_UNKNOWN'


def test_reader_evidence_failure_retains_marker_even_with_zero_exit(tmp_path, monkeypatch):
    request, request_pin, policy = repository_fixture(tmp_path)
    python, script = local_executor(tmp_path, 'SUCCEEDED')
    original = engine.write
    def fail(path, value):
        if Path(path).name == 'exit.json': raise OSError('protocol terminal recording fault')
        return original(path, value)
    monkeypatch.setattr(engine, 'write', fail)
    with pytest.raises(RecoveryError) as failure:
        with RepositoryReadGuard(request, request_pin, policy, Budget(5000)) as guard:
            # Windows protocol workers do not use Linux fd inheritance here.
            monkeypatch.setattr(guard, 'child_options', lambda env, fds=(): {'env':env})
            InvocationRunner(tmp_path, Budget(5000)).run(python, script,
                dict(operationId='op', requestId='req', action='PROTOCOL'), guard=guard.check)
    assert failure.value.unknown and json.loads(guard.path.read_text())['state'] == 'TERMINAL_UNKNOWN'


@pytest.mark.parametrize('stage', ['request.json','intent.json'])
def test_admitted_pre_dispatch_evidence_failure_retains_guard(tmp_path, monkeypatch, stage):
    request, request_pin, policy = repository_fixture(tmp_path)
    python, script = local_executor(tmp_path,'SUCCEEDED')
    original = engine._write
    def fail(path,value):
        if Path(path).name == stage: raise OSError('protocol pre-dispatch evidence fault')
        return original(path,value)
    monkeypatch.setattr(engine,'_write',fail)
    runner = InvocationRunner(tmp_path,Budget(5000))
    with pytest.raises(OSError) as failure:
        with RepositoryReadGuard(request,request_pin,policy,Budget(5000)) as guard:
            runner.run(python,script,dict(operationId='op',requestId='req',action='PROTOCOL'),guard=lambda:None)
    assert failure.value.unknown and runner.actual_exit_code is None
    assert json.loads(guard.path.read_text())['state'] == 'TERMINAL_UNKNOWN'


def test_canonical_root_and_cross_repository_originals_rejected(tmp_path):
    request, request_pin, policy = repository_fixture(tmp_path)
    sibling = tmp_path/'other'/'archives'/'ancestor'/'.repository'; sibling.mkdir(parents=True)
    other = write(sibling/'point.json', {'protocolOnly':'other'})
    policy['repositoryPointPins'].append(other)
    with RepositoryReadGuard(request, request_pin, policy, Budget(5000)) as guard:
        with pytest.raises(RecoveryError, match='CROSS_REPOSITORY'): guard.point(other)
        with pytest.raises(RecoveryError, match='ARCHIVE_BINDING'): guard.archive_pins(request['selectedPointPin'], [other])
        with pytest.raises(RecoveryError, match='CROSS_REPOSITORY'): guard.original_pins([other])
        with pytest.raises(RecoveryError, match='CROSS_REPOSITORY'): check_pin(other)
        guard.finish(terminal_known=True)
    bad = dict(request['selectedPointPin'], path=str(tmp_path/'arbitrary-point.json'))
    policy['repositoryPointPins'].append(bad)
    with pytest.raises(RecoveryError, match='POINT_PATH_INVALID'): repository_root(bad, policy)


def test_crash_keeps_active_marker(tmp_path):
    request, request_pin, policy = repository_fixture(tmp_path)
    config = tmp_path/'protocol-config.json'; config.write_text(json.dumps([request, request_pin, policy]))
    source = ("import sys,json,os\nsys.path.insert(0,sys.argv[1])\nfrom recovery_engine import Budget\n"
              "from recovery_engine_read_guard import RepositoryReadGuard\na,b,c=json.load(open(sys.argv[2]))\n"
              "guard=RepositoryReadGuard(a,b,c,Budget(5000));guard.__enter__();os._exit(0)")
    actual = subprocess.run([sys.executable,'-B','-c',source,str(Path(engine.__file__).parent),str(config)], capture_output=True, timeout=5)
    assert actual.returncode == 0
    marker = tmp_path/'repo'/'.repository-control'/'recovery-read-guard.json'
    assert json.loads(marker.read_text())['state'] == 'ACTIVE'
    with pytest.raises(RecoveryError, match='RECONCILIATION_REQUIRED'):
        with RepositoryReadGuard(request, request_pin, policy, Budget(5000)): pass


class Response(io.BytesIO):
    status = 200


class BucketProtocolFixture:
    """Only a request/response fixture; never used by the native product."""
    endpoint = 'http://protocol.invalid:9000'; host = 'protocol.invalid:9000'
    _access = 'protocol-access'; _secret = 'protocol-secret'
    def __init__(self):
        self.puts = []; self.existing = False; self.fail_put = False; self.deny_acl = False
        self.acl = b'<AccessControlPolicy><Owner><ID>protocol-owner</ID></Owner><AccessControlList/></AccessControlPolicy>'
    def _get(self, bucket, params=(), expected_absence=None):
        configuration = params[0][0] if params else None
        if configuration is None:
            return Response(b'<ListAllMyBucketsResult><Buckets>'+ (b'<Bucket><Name>bucket</Name></Bucket>' if self.existing else b'')+ b'</Buckets></ListAllMyBucketsResult>')
        if configuration == 'acl':
            if self.deny_acl: raise RecoveryError('PROTOCOL_HTTP_403')
            return Response(self.acl)
        if configuration == 'policy':
            assert expected_absence == 'NoSuchBucketPolicy'
            return dict(httpStatus=404,errorCode=expected_absence,rawSha256='a'*64,rawBytes=5)
        raise AssertionError('unplanned protocol GET')
    def _open(self, request):
        self.puts.append(request)
        if self.fail_put: raise OSError('protocol dispatched response lost')
        return Response(b'')
    def replica_configuration(self, bucket, configuration):
        if configuration == 'versioning': return dict(status='Enabled',httpStatus=200,rawSha256='a'*64)
        if configuration == 'object-lock': return dict(enabled=False,httpStatus=404,rawSha256='b'*64)
        if configuration == 'notification': return dict(externalNotificationEntries=0,httpStatus=200,rawSha256='c'*64)
        raise AssertionError('unexpected configuration')
    def absent_configuration(self, bucket, configuration, code): return dict(httpStatus=404,errorCode=code)
    def multipart_empty(self, bucket): return dict(uploadCount=0,isTruncated=False)
    def empty_versioned(self, bucket): return True


def approved_protection(client):
    return dict(schemaVersion='RecoveryBucketProtection/v1', buckets={'bucket':dict(versioning='Enabled',objectLockEnabled=False,
        objectLockSha256=None,aclSha256=hashlib.sha256(client.acl).hexdigest(),policySha256=None)})


def test_bucket_preparation_native_request_contract_and_readback():
    client = BucketProtocolFixture(); evidence = []; guarded = []
    result = prepare_buckets(client, ['bucket'], {'bucket':dict(versioning='Enabled',objectLockEnabled=False)},
        guard=lambda:guarded.append(True), intent=lambda name,value:evidence.append((name,value)))
    assert result['state'] == 'CONFIGURATION_MATCHED' and len(client.puts) == 2 and len(guarded) > 8
    assert [r.full_url for r in client.puts] == [client.endpoint+'/bucket',client.endpoint+'/bucket?versioning=']
    assert all(r.method == 'PUT' and r.get_header('Authorization').startswith('AWS4-HMAC-SHA256 ') for r in client.puts)
    assert b'<Status>Enabled</Status>' in client.puts[1].data and len(evidence) == 5


@pytest.mark.parametrize('kind', ['missing-settings','bad-settings','existing'])
def test_bucket_prerequisite_failure_has_no_put(kind):
    client = BucketProtocolFixture(); settings = {'bucket':dict(versioning='Enabled',objectLockEnabled=False)}
    if kind == 'missing-settings': settings = {}
    if kind == 'bad-settings': settings['bucket']['versioning'] = 'Suspended'
    if kind == 'existing': client.existing = True
    with pytest.raises(RecoveryError):
        prepare_buckets(client,['bucket'],settings,guard=lambda:None,intent=lambda *args:None)
    assert not client.puts


def test_lost_bucket_response_and_failed_receipt_remain_unknown():
    client = BucketProtocolFixture(); client.fail_put = True
    def receipt(name,value):
        if name.endswith('-exit.json'): raise OSError('protocol recording fault')
    with pytest.raises(RecoveryError) as failure:
        prepare_buckets(client,['bucket'],{'bucket':dict(versioning='Enabled',objectLockEnabled=False)},guard=lambda:None,intent=receipt)
    assert failure.value.unknown and len(client.puts) == 1


def test_bucket_protection_requires_explicit_actual_acl_policy_and_settings():
    client = BucketProtocolFixture(); expected = approved_protection(client)
    result = protection(client,['bucket'],expected,guard=lambda:None)
    assert result['state'] == 'CONFIGURATION_MATCHED' and result['applicationWriteProtectionVerified'] is False
    expected['buckets']['bucket']['aclSha256'] = '0'*64
    with pytest.raises(RecoveryError,match='ACL_MISMATCH'): protection(client,['bucket'],expected,guard=lambda:None)
    client.deny_acl = True
    with pytest.raises(RecoveryError,match='HTTP_403'): protection(client,['bucket'],approved_protection(client),guard=lambda:None)
    with pytest.raises(RecoveryError,match='SCOPE_INVALID'): protection(client,['bucket'],{},guard=lambda:None)


def test_bucket_object_lock_is_explicit_and_readback_digest_matches():
    class Locked(BucketProtocolFixture):
        def replica_configuration(self,bucket,configuration):
            if configuration == 'object-lock': return dict(enabled=True,httpStatus=200,rawSha256='d'*64)
            return super().replica_configuration(bucket,configuration)
    client = Locked()
    prepare_buckets(client,['bucket'],{'bucket':dict(versioning='Enabled',objectLockEnabled=True)},
                    guard=lambda:None,intent=lambda *args:None)
    assert client.puts[0].get_header('X-amz-bucket-object-lock-enabled') == 'true'
    expected = approved_protection(client)
    expected['buckets']['bucket'].update(objectLockEnabled=True,objectLockSha256='d'*64)
    assert protection(client,['bucket'],expected,guard=lambda:None)['state'] == 'CONFIGURATION_MATCHED'
    expected['buckets']['bucket']['objectLockSha256'] = '0'*64
    with pytest.raises(RecoveryError,match='CONFIGURATION_MISMATCH'):
        protection(client,['bucket'],expected,guard=lambda:None)


def test_native_permission_helper_binds_expected_pin_and_target(tmp_path):
    from recovery_data import NativeData
    native = NativeData.__new__(NativeData); client = BucketProtocolFixture()
    expected = write(tmp_path/'approved-protection.json',approved_protection(client))
    native.policy = {'bucketProtectionPin':expected}; native.config = {'buckets':['bucket']}
    native.target = {'targetIdentityPin':write(tmp_path/'target.json',{'protocolOnly':True})}
    native.original = {'operationId':'op'}; native.plan = {'recoveryPoint':'point'}; native.root = tmp_path
    guarded = []; native.bound = lambda:guarded.append(True); native.object_client = lambda:client
    ref = native.check_bucket_permissions(); result = json.loads(check_pin(ref))
    assert result['expectedProtectionPin'] == expected and result['targetIdentityPin'] == native.target['targetIdentityPin']
    assert result['operationId'] == 'op' and result['recoveryPoint'] == 'point' and len(guarded) > 5


def test_native_mutation_zero_exit_recording_fault_is_unknown(tmp_path, monkeypatch):
    from recovery_data import NativeData
    native = NativeData.__new__(NativeData)
    native.original = {'operationId':'protocol'}; native.request = {'action':'PROTOCOL'}
    native.root = tmp_path; native.budget = Budget(5000); native.original_pins = []
    native.mutation_dispatched = False; native.last_exit = None; native.guard = lambda:None
    original = engine.write
    def fail(path, value):
        if Path(path).name.startswith('native-') and value.get('finishedAt'): raise OSError('protocol recording fault')
        return original(path,value)
    monkeypatch.setattr(engine,'write',fail)
    with pytest.raises(RecoveryError) as failure: native.command([sys.executable,'-B','-c','raise SystemExit(0)'],mutation=True)
    assert failure.value.unknown and failure.value.exit_code == 0 and native.last_exit == 0


@pytest.mark.parametrize('fail_stage', ['public-output','journal','failure-protection'])
def test_cli_final_evidence_failure_keeps_guard_journal_and_no_replay(tmp_path_factory, monkeypatch, fail_stage):
    tmp_path = tmp_path_factory.mktemp('cli')
    import recovery_cli as cli
    request, _, policy = repository_fixture(tmp_path)
    evidence = tmp_path/'evidence'; evidence.mkdir(mode=0o700)
    identity = write(tmp_path/'identity.json', {'protocolOnly':'target'})
    policy.update(evidenceRoot=str(evidence), dataTargetPin=write(tmp_path/'target.json', {'targetIdentityPin':identity}),
                  recordSchemasPin=write(tmp_path/'schema.json', {}))
    input_ref = write(tmp_path/'input.json', {'protocolOnly':True})
    request.update(action='RESTORE_EXECUTE', deadlineMilliseconds=5000,
                   inputPins={'restorePlan':input_ref,'recoveryTarget':input_ref})
    request_pin = write(tmp_path/'request.json',request)
    output = tmp_path/'public-result.json'
    monkeypatch.setattr(cli,'trusted_configuration',lambda request:({},policy,{}))
    monkeypatch.setattr(cli,'authorities',lambda *args:None)
    monkeypatch.setattr(cli,'validate_record',lambda value,*args:value)
    monkeypatch.setattr(RepositoryReadGuard,'child_options',lambda self,env,fds=():dict(env=env))
    python, script = local_executor(tmp_path,'TERMINAL_UNKNOWN' if fail_stage == 'failure-protection' else 'SUCCEEDED')
    def protocol_operation(operation):
        operation.runner.run(python,script,dict(operationId='op',requestId='req',action='PROTOCOL'),guard=lambda:None)
        return {'protocolOnly':True}
    monkeypatch.setattr(cli.RecoveryOperation,'run',protocol_operation)
    original_engine_write = engine.write
    def fault(path,value):
        name = Path(path).name
        if ((fail_stage == 'public-output' and Path(path) == output) or
            (fail_stage == 'failure-protection' and name == 'failure-protection.json')):
            raise OSError('protocol evidence fault')
        return original_engine_write(path,value)
    monkeypatch.setattr(engine,'write',fault)
    if fail_stage == 'journal':
        def finish(*args): raise OSError('protocol journal fault')
        monkeypatch.setattr(cli.Journal,'finish',finish)
    with pytest.raises(Exception) as failure: cli.execute(request,request_pin,str(output))
    assert failure.value.unknown and failure.value.exit_code is not None
    marker = tmp_path/'repo'/'.repository-control'/'recovery-read-guard.json'
    if fail_stage == 'journal':
        assert failure.value.code == 'RECOVERY_TERMINAL_STATE_PERSISTENCE_FAILED'
        assert failure.value.original_code == 'OSError' and failure.value.original_pins
        # Confirmed terminal readers released the repository before cache
        # publication failed. The durable RUNNING journal still blocks replay.
        assert not marker.exists()
        assert json.loads(output.read_text())['state'] == 'TERMINAL_UNKNOWN'
        assert json.loads(next(evidence.glob('target-*.state.json')).read_text())['state'] == 'TERMINAL_UNKNOWN'
    else:
        assert json.loads(marker.read_text())['state'] == 'TERMINAL_UNKNOWN'
    journal = next(evidence.glob('request-*.json'))
    assert json.loads(journal.read_text())['state'] == ('RUNNING' if fail_stage == 'failure-protection' else 'TERMINAL_UNKNOWN')
    with pytest.raises(RecoveryError) as replay: cli.execute(request,request_pin,str(output))
    assert replay.value.unknown


@pytest.mark.skipif(os.name != 'posix', reason='Native Linux supervisor record-lock inheritance requires Linux')
def test_linux_worker_inherits_exact_marker_and_supervisor_lock(tmp_path):
    request, request_pin, policy = repository_fixture(tmp_path)
    config = tmp_path/'worker-config.json'; config.write_text(json.dumps([request,request_pin,policy]))
    source = ("import sys,json\nsys.path.insert(0,sys.argv[1])\nfrom recovery_engine import Budget,check_pin\n"
              "from recovery_engine_read_guard import inherit_read_guard\na,b,c=json.load(open(sys.argv[2]))\n"
              "guard=inherit_read_guard(a,b,c,Budget(5000));check_pin(a['selectedPointPin']);guard.check()")
    with RepositoryReadGuard(request,request_pin,policy,Budget(5000)) as guard:
        options = guard.child_options(dict(os.environ))
        actual = subprocess.run([sys.executable,'-B','-c',source,str(Path(engine.__file__).parent),str(config)],
                                capture_output=True,timeout=5,**options)
        assert actual.returncode == 0, actual.stderr
        guard.finish(terminal_known=True)


def test_remote_cutover_original_unknown_survives_intent_write_failure(tmp_path, monkeypatch):
    """Real local client + fixture-only prerequisites; remote proof is deliberately absent."""
    import recovery_cutover_worker as worker
    script = tmp_path/'cutover-protocol-tool.py'
    script.write_text("import sys,json\nr=json.load(sys.stdin);r.update(schemaVersion='RecoveryCutoverObservation/v1',state='OBSERVED',"
        "validFrom='2000-01-01T00:00:00Z',validUntil='2099-01-01T00:00:00Z',remoteTerminalProofPin={'protocol':'missing'},observations={'fenced':True});print(json.dumps(r))",encoding='utf-8')
    identity = {'protocol':'target'}; scope = {'protocol':'source'}; candidate = {'protocol':'point'}; tool = pin(Path(sys.executable))
    host_pin = {'protocol':'host'}; material_pin = {'protocol':'material'}; recipe_pin = {'sha256':'a'*64}
    original = dict(operationId='op',action='CONTROLLED_CUTOVER',mode='CONTROLLED_RESTORE',selectedPointPin=candidate,
                    sourceOrTargetRef={'protocol':'config'},inputPins={'repositoryPoint':candidate,'recoveryVerificationReport':{'protocol':'report'}},
                    authorizationRefs=[],leaseRef={'protocol':'lease'})
    request = dict(operationId='op',requestId='req',action='STOP_SOURCE_WRITES',mode='CONTROLLED_RESTORE',phase='SOURCE_FENCE',
        originalRequestPin={'protocol':'original'},planPin={'protocol':'plan'},deadlineMilliseconds=5000,recoveryTargetPin=None,
        targetIdentityPin=identity,sourceScopePin=scope,reportPin=original['inputPins']['recoveryVerificationReport'],
        authorizationRefs=[],leaseRef=original['leaseRef'],inputPins={},postVerificationApprovalPin=None)
    plan = dict(operationId='op',recoveryPoint='point',plannedWrites=[{'targetIdentityPin':identity}],candidatePin=candidate,
                orderedChainPins=[candidate],immutableInputsSha256=worker.digest({}),targetRef=original['sourceOrTargetRef'])
    command = dict(toolPin=tool,argv=['-B',str(script)],mutation=True,executionKind='REMOTE',executionHostIdentityPin=host_pin,
                   configurationPin={'protocol':'command-config'},requiredObservations={'fenced':True})
    recipe = dict(schemaVersion='RecoveryCutoverRecipe/v1',action=request['action'],targetIdentityPin=identity,
        sourceScopePin=scope,recoveryPoint='point',commands=[command],validFrom='2000-01-01T00:00:00Z',validUntil='2099-01-01T00:00:00Z',resultFields=['fenced'])
    policy = dict(dataTargetPin={'protocol':'data-target'},sourceScopePin=scope,cutoverRecipePins={request['action']:recipe_pin})
    trust = dict(cutoverRecipeSha256s=[recipe_pin['sha256']],cutoverToolSha256s=[tool['sha256']])
    def fixture_json(ref):
        if ref == request['originalRequestPin']: return original
        if ref == request['planPin']: return plan
        if ref == policy['dataTargetPin']: return {'targetIdentityPin':identity}
        if ref == recipe_pin: return recipe
        if ref in (host_pin,identity,scope): return {'machineId':'protocol-machine'}
        raise AssertionError('unplanned fixture Pin')
    monkeypatch.setattr(worker,'pinned_json',fixture_json)
    monkeypatch.setattr(worker,'trusted_configuration',lambda request:(trust,policy,{}))
    monkeypatch.setattr(worker,'authorities',lambda *args:None)
    monkeypatch.setattr(worker,'inherit_read_guard',lambda *args:None)
    monkeypatch.setattr(worker,'inherited_target_lock',lambda *args:123)
    monkeypatch.setattr(worker,'resolve_chain',lambda *args:[(candidate,{}, {},material_pin)])
    monkeypatch.setattr(worker,'immutable_inputs',lambda *args:{})
    monkeypatch.setattr(worker,'check_pin',lambda *args,**kwargs:None)
    monkeypatch.setattr(worker,'verify_report',lambda *args,**kwargs:None)
    monkeypatch.setattr(worker,'os',SimpleNamespace(name='posix',killpg=None))
    guard = SimpleNamespace(check=lambda:None,child_options=lambda env,fds=():{'env':dict(os.environ)})
    monkeypatch.setattr(worker,'repository_guard',lambda:guard)
    def remote_unknown(*args): raise RecoveryError('ORIGINAL_REMOTE_PROCESS_UNPROVEN',unknown=True,exit_code=0)
    monkeypatch.setattr(worker,'remote_terminal',remote_unknown)
    original_write = engine.write
    def fault(path,value):
        if Path(path).name == 'command-000.json': raise OSError('protocol terminal receipt failure')
        return original_write(path,value)
    monkeypatch.setattr(engine,'write',fault)
    pins = []
    with pytest.raises(RecoveryError) as failure: worker.run(request,tmp_path,pins)
    assert failure.value.unknown and failure.value.exit_code == 0
    assert failure.value.original_code == 'ORIGINAL_REMOTE_PROCESS_UNPROVEN'
    receipt = next(tmp_path.glob('*.recording-failure.json'))
    value = json.loads(receipt.read_text())
    assert value['failedEvidence']['nativePid'] > 0 and value['failedEvidence']['actualExitCode'] == 0
    assert value['state'] == 'TERMINAL_UNKNOWN' and pins


def test_guard_marker_pin_failure_after_replace_blocks_next_admission(tmp_path, monkeypatch):
    import recovery_engine_read_guard as module
    request, request_pin, policy = repository_fixture(tmp_path)
    original = module.write
    def fail_after_replace(path,value):
        original(path,value)
        raise OSError('protocol post-replace Pin failure')
    monkeypatch.setattr(module,'write',fail_after_replace)
    with pytest.raises(OSError) as failure:
        with RepositoryReadGuard(request,request_pin,policy,Budget(5000)): pass
    assert failure.value.unknown
    marker = tmp_path/'repo'/'.repository-control'/'recovery-read-guard.json'
    assert json.loads(marker.read_text())['state'] == 'ACTIVE'
    with pytest.raises(RecoveryError,match='RECONCILIATION_REQUIRED'):
        with RepositoryReadGuard(request,request_pin,policy,Budget(5000)): pass


def test_changed_marker_is_not_removed_or_overwritten(tmp_path):
    request, request_pin, policy = repository_fixture(tmp_path)
    with pytest.raises(RecoveryError) as failure:
        with RepositoryReadGuard(request,request_pin,policy,Budget(5000)) as guard:
            replacement = dict(guard.value,operationId='different-owner')
            write(guard.path,replacement)
            guard.finish(terminal_known=True)
    assert failure.value.unknown and json.loads(guard.path.read_text()) == replacement




def test_preflight_has_no_guard_and_restore_revalidates_under_guard(tmp_path_factory, monkeypatch):
    import recovery_cli as cli
    tmp_path = tmp_path_factory.mktemp('pre')
    request, _, policy = repository_fixture(tmp_path)
    evidence = tmp_path/'evidence'; evidence.mkdir(mode=0o700)
    identity = write(tmp_path/'identity.json',{'protocolOnly':'target'})
    policy.update(evidenceRoot=str(evidence),dataTargetPin=write(tmp_path/'target.json',{'targetIdentityPin':identity}),
                  recordSchemasPin=write(tmp_path/'schema.json',{}))
    monkeypatch.setattr(cli,'trusted_configuration',lambda request:({},policy,{}))
    monkeypatch.setattr(cli,'authorities',lambda *args:None)
    monkeypatch.setattr(cli,'validate_record',lambda value,*args:value)
    observed = []
    def read_originals(operation):
        active = engine.repository_guard(); observed.append(active is not None)
        if active is not None: active.check()
        check_pin(operation.request['selectedPointPin'])
        return {'protocolOnly':True}
    monkeypatch.setattr(cli.RecoveryOperation,'run',read_originals)
    request.update(action='RESTORE_PREFLIGHT',deadlineMilliseconds=5000,inputPins={'repositoryPoint':request['selectedPointPin']})
    first_pin = write(tmp_path/'preflight.json',request)
    assert cli.execute(request,first_pin)['state'] == 'SUCCEEDED'
    request = dict(request,requestId='restore-request',action='RESTORE_EXECUTE',
                   inputPins={'restorePlan':first_pin,'recoveryTarget':first_pin})
    next_pin = write(tmp_path/'restore.json',request)
    assert cli.execute(request,next_pin)['state'] == 'SUCCEEDED' and observed == [False,True]
    assert not (tmp_path/'repo'/'.repository-control'/'recovery-read-guard.json').exists()
