"""W05-shaped startup/protection originals on task-owned local files only."""
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ops'/'recovery'))
from recovery_engine import RecoveryError, canonical, digest, pin, pinned_json, utc, write
from recovery_plan_application import protected_application, SCOPES


def application_fixture(tmp_path):
    schema=pin(Path(__file__).resolve().parents[2]/'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json')
    identity=write(tmp_path/'identity.json',{'targetId':'unit-local'});configuration=write(tmp_path/'configuration.json',{'unit':True})
    script=tmp_path/'protection.py';script.write_bytes(b'# local fixture only');script_pin=pin(script);python=pin(sys.executable)
    spec=dict(schemaVersion='RecoveryApplicationWriteProtectionPolicy/v1',targetIdentityPin=identity,configurationPin=configuration,
              imagePins=[configuration],mechanismId='protocol-fixture',sourceEvidencePins=[configuration],enforceScriptPin=script_pin,
              observeScriptPin=script_pin,requiredScopes=sorted(SCOPES))
    spec_pin=write(tmp_path/'spec.json',spec)
    env_pin=write(tmp_path/'environment-policy.json',dict(applicationWriteProtectionPin=spec_pin,startupInventoryPins=[configuration]))
    config_pin=write(tmp_path/'config.json',dict(configurationPin=configuration,imagePins=[configuration],pythonPin=python))
    lease=write(tmp_path/'lease.json',{'unit':True});point=write(tmp_path/'point.json',{'unit':True})
    request=dict(operationId='op',sourceOrTargetRef=config_pin,policyPin=env_pin)
    target=dict(targetIdentityPin=identity,configurationPin=configuration)
    plan=dict(schemaVersion='RestorePlan/v1',operationId='op',restoreId='restore',mode='REHEARSAL',candidatePin=point,orderedChainPins=[point],
              recoveryPoint='point',targetRef=config_pin,supportedVersionPins=[configuration],toolPins=[python],
              plannedWrites=[dict(resource='database',action='restore',targetIdentityPin=identity)],sideEffectPolicyPin=env_pin,
              authorizationRefs=[lease],leaseRef=lease,immutableInputsSha256='a'*64)
    plan_pin=write(tmp_path/'plan.json',plan)
    execution=dict(schemaVersion='RestoreExecutionResult/v1',operationId='op',restoreId='restore',planPin=plan_pin,targetIdentityPin=identity,
                   recoveryPoint='point',dbStepEvidencePins=[configuration],objectStepEvidencePins=[configuration],consistencyEvidencePin=configuration,
                   originalInvocationPins=[configuration],state='SUCCEEDED',writeProtectionState='ENFORCED')
    execution_pin=write(tmp_path/'execution.json',execution);originals=[];phase_refs={}
    for phase in ('BEFORE_START','AFTER_START'):
        observed=utc();scopes=[];containers={'mysql':'mysql','minio':'minio','redis':'redis'}
        if phase == 'AFTER_START':containers.update(backend='backend',frontend='frontend')
        for scope in sorted(SCOPES):
            invocation=write(tmp_path/(phase+scope+'-exit.json'),dict(schemaVersion='RecoveryEnvironmentInvocation/v1',
                mutation=True,state='FAILED_RETAINED',actualExitCode=7,pid=123,startedAt=observed,finishedAt=utc()))
            refusal=write(tmp_path/(phase+scope+'.json'),dict(schemaVersion='RecoveryApplicationWriteRefusal/v1',scope=scope,phase=phase,
                denied=True,operationId='op',targetIdentityPin=identity,recoveryPoint='point',containers=containers,
                beforeFingerprint='b'*64,afterFingerprint='b'*64,originalInvocationPins=[invocation]))
            scopes.append(dict(scope=scope,enforcementPin=configuration,beforeFingerprint='b'*64,afterFingerprint='b'*64,rejectionObservationPins=[refusal]))
        raw_observation=dict(schemaVersion='RecoveryApplicationWriteProtectionObservation/v1',phase=phase,operationId='op',restoreId='restore',
              targetIdentityPin=identity,recoveryPoint='point',policyPin=spec_pin,containers=containers,state='ENFORCED',observedAt=observed,scopeObservations=scopes)
        original=write(tmp_path/(phase+'-exit.json'),dict(schemaVersion='RecoveryEnvironmentInvocation/v1',state='SUCCEEDED',actualExitCode=0,pid=123,
              mutation=True,argvSha256=digest([python['path'],'-I',script_pin['path']]),startedAt=observed,finishedAt=utc(),
              stdoutBytes=len(canonical(raw_observation)),stdoutSha256=digest(raw_observation)))
        originals.append(original)
        phase_refs[phase]=write(tmp_path/(phase+'.json'),dict(raw_observation,originalInvocationPin=original,executorPin=script_pin))
    side=write(tmp_path/'side.json',dict(schemaVersion='RecoverySideEffectIsolation/v1',operationId='op',targetIdentityPin=identity,state='ENFORCED',
        policyPin=env_pin,startupInventoryPins=[configuration],sourceWritesPerformed=False,writeProtectionState='ENFORCED',observedAt=utc(),
        applicationWriteProtectionPolicyPin=spec_pin,writeProtectionBeforePin=phase_refs['BEFORE_START'],writeProtectionAfterPin=phase_refs['AFTER_START']))
    health=write(tmp_path/'health.json',dict(schemaVersion='RecoveryApplicationHealth/v1',operationId='op',restoreId='restore',targetIdentityPin=identity,
                state='SUCCEEDED',observedAt=utc()))
    application=dict(schemaVersion='ApplicationStartResult/v1',operationId='op',restoreId='restore',targetIdentityPin=identity,restoreResultPin=execution_pin,
        imagePins=[configuration],configurationPin=configuration,sideEffectIsolationPin=side,originalStartResultPins=originals,healthEvidencePin=health,state='SUCCEEDED')
    return application,execution_pin,plan,target,request,{'recordSchemasPin':schema,'maximumProofAgeSeconds':300}


def test_frozen_application_shape_consumes_real_nested_protection_fields(tmp_path):
    args=application_fixture(tmp_path)
    assert 'writeProtectionState' not in args[0]
    assert protected_application(*args)['writeProtectionState'] == 'ENFORCED'


@pytest.mark.parametrize('field,value',[('operationId','different'),('policyPin',None),('writeProtectionState','UNKNOWN')])
def test_cross_operation_or_unprotected_side_record_cannot_pass(tmp_path,field,value):
    args=list(application_fixture(tmp_path));side=pinned_json(args[0]['sideEffectIsolationPin']);side[field]=value
    args[0]['sideEffectIsolationPin']=write(args[0]['sideEffectIsolationPin']['path'],side)
    with pytest.raises(RecoveryError,match='APPLICATION_PROTECTED_START_REQUIRED'):protected_application(*args)


def test_enforced_label_without_refusal_originals_fails(tmp_path):
    args=list(application_fixture(tmp_path));side=pinned_json(args[0]['sideEffectIsolationPin']);proof=pinned_json(side['writeProtectionAfterPin'])
    proof['scopeObservations'][0]['rejectionObservationPins']=[]
    side['writeProtectionAfterPin']=write(side['writeProtectionAfterPin']['path'],proof)
    args[0]['sideEffectIsolationPin']=write(args[0]['sideEffectIsolationPin']['path'],side)
    with pytest.raises(RecoveryError,match='APPLICATION_PROTECTION_REFUSAL_REQUIRED'):protected_application(*args)


def rewrite_phase(args, phase, change):
    side=pinned_json(args[0]['sideEffectIsolationPin']);key='writeProtection'+('Before' if phase=='BEFORE_START' else 'After')+'Pin'
    proof=pinned_json(side[key]);change(proof)
    side[key]=write(side[key]['path'],proof)
    args[0]['sideEffectIsolationPin']=write(args[0]['sideEffectIsolationPin']['path'],side)


@pytest.mark.parametrize('phase',['BEFORE_START','AFTER_START'])
def test_read_only_outer_invocation_cannot_hide_write_probe(tmp_path,phase):
    args=list(application_fixture(tmp_path))
    def change(proof):
        old=proof['originalInvocationPin'];invocation=pinned_json(old);invocation['mutation']=False
        proof['originalInvocationPin']=write(old['path'],invocation)
        args[0]['originalStartResultPins']=[proof['originalInvocationPin'] if ref==old else ref for ref in args[0]['originalStartResultPins']]
    rewrite_phase(args,phase,change)
    with pytest.raises(RecoveryError,match='APPLICATION_PROTECTION_ORIGINAL_EXIT_REQUIRED'):protected_application(*args)


@pytest.mark.parametrize('field,value',[('mutation',False),('state','TERMINAL_UNKNOWN'),('actualExitCode',None),
                                       ('pid',True),('finishedAt','2999-01-01T00:00:00Z')])
def test_nested_refusal_requires_real_terminal_fields(tmp_path,field,value):
    args=list(application_fixture(tmp_path))
    def change(proof):
        item=proof['scopeObservations'][0];ref=item['rejectionObservationPins'][0];refusal=pinned_json(ref)
        invocation_ref=refusal['originalInvocationPins'][0];invocation=pinned_json(invocation_ref);invocation[field]=value
        refusal['originalInvocationPins']=[write(invocation_ref['path'],invocation)]
        item['rejectionObservationPins']=[write(ref['path'],refusal)]
    rewrite_phase(args,'AFTER_START',change)
    with pytest.raises(RecoveryError,match='APPLICATION_PROTECTION_REFUSAL_TERMINATION_UNPROVEN'):protected_application(*args)


@pytest.mark.parametrize('field,value',[('phase','BEFORE_START'),('operationId','different'),('scope','SCHEDULERS'),
                                      ('targetIdentityPin',None),('afterFingerprint','c'*64)])
def test_refusal_binding_and_unchanged_content_gates_remain(tmp_path,field,value):
    args=list(application_fixture(tmp_path))
    def change(proof):
        item=proof['scopeObservations'][0];ref=item['rejectionObservationPins'][0];refusal=pinned_json(ref);refusal[field]=value
        item['rejectionObservationPins']=[write(ref['path'],refusal)]
    rewrite_phase(args,'AFTER_START',change)
    with pytest.raises(RecoveryError,match='APPLICATION_PROTECTION_REFUSAL_UNBOUND'):protected_application(*args)


# This executor exercises the actual W05 producer using only private local
# files. It proves protocol compatibility, not application/container protection.
LOCAL_REFUSAL_EXECUTOR = r'''
import hashlib
import json
from pathlib import Path
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, RECOVERY_MODULE_ROOT)
from recovery_environment_contract import EnvironmentFailure, atomic_json, canonical, pin_file, read_pin, require, utc_now
from recovery_environment_runtime import CommandRunner
payload = json.loads(sys.stdin.buffer.read())
root = Path(__file__).parent / ('nested-' + payload['phase'])
root.mkdir()
deadline = time.monotonic() + payload['deadlineMilliseconds'] / 1000
def guard():
    require(time.monotonic() < deadline, 'LOCAL_PROTOCOL_DEADLINE')
runner = CommandRunner(root, deadline, guard)
child = r"""import errno, os, sys
fd = os.open(sys.argv[1], os.O_RDONLY)
try:
    os.write(fd, b'attempted-write')
except OSError as error:
    if error.errno not in (errno.EBADF, errno.EACCES):
        raise
    sys.stdout.buffer.write(b'LOCAL_READ_ONLY_DESCRIPTOR_DENIED\n')
    sys.exit(7)
raise RuntimeError('READ_ONLY_WRITE_UNEXPECTEDLY_SUCCEEDED')
"""
scopes = []
for scope in REQUIRED_SCOPES:
    path = root / (scope + '.bin')
    path.write_bytes(b'private protocol content')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        runner.run([sys.executable, '-I', '-c', child, str(path)], mutation=True)
    except EnvironmentFailure as error:
        require(error.code == 'EXECUTOR_NONZERO_EXIT' and runner.last_exit == 7, 'LOCAL_REFUSAL_EXIT_REQUIRED')
    else:
        raise RuntimeError('LOCAL_REFUSAL_NOT_OBSERVED')
    original = read_pin(runner.pins[-1])
    require(original['stdoutSha256'] == hashlib.sha256(b'LOCAL_READ_ONLY_DESCRIPTOR_DENIED\n').hexdigest(),
            'LOCAL_REFUSAL_OUTPUT_REQUIRED')
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    require(before == after, 'LOCAL_PROBE_CHANGED_CONTENT')
    refusal = dict(schemaVersion='RecoveryApplicationWriteRefusal/v1', scope=scope, phase=payload['phase'],
        operationId=payload['operationId'], targetIdentityPin=payload['targetIdentityPin'], recoveryPoint=payload['recoveryPoint'],
        containers=payload['containers'], denied=True, beforeFingerprint=before, afterFingerprint=after,
        originalInvocationPins=[runner.pins[-1]])
    refusal_path = root / (scope + '-refusal.json')
    atomic_json(refusal_path, refusal)
    scopes.append(dict(scope=scope, enforcementPin=pin_file(__file__), beforeFingerprint=before,
                       afterFingerprint=after, rejectionObservationPins=[pin_file(refusal_path)]))
observation = {key: payload[key] for key in ('phase','operationId','restoreId','targetIdentityPin','recoveryPoint','policyPin','containers')}
observation.update(schemaVersion='RecoveryApplicationWriteProtectionObservation/v1', state='ENFORCED',
                   observedAt=utc_now(), scopeObservations=scopes)
sys.stdout.buffer.write(canonical(observation))
'''


def test_actual_w05_producer_records_pass_w04_for_both_phases(tmp_path):
    from recovery_application_protection import protect_application
    from recovery_environment_runtime import CommandRunner
    args=list(application_fixture(tmp_path));application,_,plan,_,request,_=args
    config=pinned_json(request['sourceOrTargetRef']);policy=pinned_json(request['policyPin'])
    spec=pinned_json(policy['applicationWriteProtectionPin'])
    script=Path(spec['enforceScriptPin']['path'])
    module_root=Path(__file__).resolve().parents[2]/'ops'/'recovery'
    script.write_text('RECOVERY_MODULE_ROOT = '+repr(str(module_root))+'\nREQUIRED_SCOPES = '+repr(sorted(SCOPES))+'\n'+LOCAL_REFUSAL_EXECUTOR,
                      encoding='utf-8')
    spec.update(enforceScriptPin=pin(script),observeScriptPin=pin(script))
    policy['applicationWriteProtectionPin']=write(policy['applicationWriteProtectionPin']['path'],spec)
    side=pinned_json(application['sideEffectIsolationPin']);side['applicationWriteProtectionPolicyPin']=policy['applicationWriteProtectionPin']
    request['policyPin']=write(request['policyPin']['path'],policy);side['policyPin']=request['policyPin']
    source=tmp_path/'source';source.mkdir()
    config.update(targetIdentityPin=spec['targetIdentityPin'],materialRoots=[str(tmp_path)],
                  sourceScopePin=write(tmp_path/'source-scope.json',dict(materialPaths=[str(source)])))
    request['sourceOrTargetRef']=write(request['sourceOrTargetRef']['path'],config)
    plan.update(targetRef=request['sourceOrTargetRef'],sideEffectPolicyPin=request['policyPin'])
    execution=pinned_json(args[1]);execution['planPin']=write(execution['planPin']['path'],plan)
    args[1]=write(args[1]['path'],execution);application['restoreResultPin']=args[1]
    deadline=time.monotonic()+30
    def guard():
        assert time.monotonic() < deadline
    application['originalStartResultPins']=[]
    for phase in ('BEFORE_START','AFTER_START'):
        evidence=tmp_path/('producer-'+phase);evidence.mkdir()
        runner=CommandRunner(evidence,deadline,guard)
        identities=dict(mysql='local-mysql',minio='local-minio',redis='local-redis')
        if phase=='AFTER_START':identities.update(backend='local-backend',frontend='local-frontend')
        proof_pin=protect_application(request,config,policy,SimpleNamespace(runner=runner,identities=identities),plan,phase)
        side['writeProtection'+('Before' if phase=='BEFORE_START' else 'After')+'Pin']=proof_pin
        application['originalStartResultPins'].extend(runner.pins)
        outer=pinned_json(runner.pins[-1])
        assert outer['mutation'] is True and outer['actualExitCode']==0 and outer['pid']>0
    application['sideEffectIsolationPin']=write(application['sideEffectIsolationPin']['path'],side)
    assert protected_application(*args)['writeProtectionState']=='ENFORCED'
