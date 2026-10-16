"""Local engineering originals/signatures only; no Linux/business acceptance."""
import base64
import copy
import os
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, x25519

from test_recovery_verification_lab import fixture, admit
from test_recovery_verification_admission_v2 import reselect_admission, policy_v2
from test_recovery_verification_report import Packet, MODULE, SCHEMA
from core import Deadline, VerificationError, canonical, file_pin, json_pin, now, pin_key, read_pin
from evidence import EvidenceContext, assess_report, report_invalidations
from report_currency import assess
from bind_caller import bind
from collect_recovery import collect
from verify_recovery import run


def put(root, name, value, raw=False):
    path = root / name
    path.write_bytes(value if raw else canonical(value))
    return file_pin(str(path))


def signed(root, name, payload, role):
    key, pin = role
    return put(root, name, dict(schemaVersion='RepositorySignedRecord/v1', keySha256=pin['sha256'],
                               payload=payload, signature=base64.b64encode(key.sign(canonical(payload))).decode()))


def public(key):
    return key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


@pytest.mark.parametrize('kind,code', [('empty','LAB_PUBLIC_KEY_SIZE'), ('not-pem','LAB_PUBLIC_KEY_INVALID'),
    ('rsa','LAB_ED25519_REQUIRED'), ('x25519','LAB_ED25519_REQUIRED'), ('private','LAB_PUBLIC_KEY_INVALID'),
    ('large','LAB_PUBLIC_KEY_SIZE')])
def test_unused_second_copy_key_is_still_bounded_and_parsed(tmp_path, kind, code):
    values = fixture(tmp_path)
    raw = {'empty':b'', 'not-pem':b'not a public key', 'large':b'x'*65537}.get(kind)
    if kind == 'rsa': raw = public(rsa.generate_private_key(public_exponent=65537,key_size=2048))
    if kind == 'x25519': raw = public(x25519.X25519PrivateKey.generate())
    if kind == 'private': raw = ed25519.Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    extra = put(tmp_path, 'unused-second-key.pem', raw, True)
    values[1].append(extra)
    values = reselect_admission(values, lambda a: a['copyProtectionEvidenceKeyPins'].append(extra))
    with pytest.raises(VerificationError, match='^'+code+'$'): admit(values)


def test_two_distinct_valid_copy_keys_and_wrong_used_signer(tmp_path):
    values = fixture(tmp_path)
    second = put(tmp_path, 'second-valid-copy.pem', public(ed25519.Ed25519PrivateKey.generate()), True)
    values[1].append(second)
    values = reselect_admission(values, lambda a: a['copyProtectionEvidenceKeyPins'].append(second))
    boundary = admit(values)
    assert boundary.copy_protection(values[3],300000)['sourceDeletionDenied']
    values = reselect_admission(values, lambda a: a.update(copyProtectionEvidenceKeyPins=[second]))
    with pytest.raises(VerificationError, match='LAB_COPY_SIGNING_KEY_NOT_SELECTED'):
        admit(values).copy_protection(values[3],300000)


def test_raw_key_reader_bounds_actual_file_after_pin_and_exact_limit(tmp_path):
    key = public(ed25519.Ed25519PrivateKey.generate())
    exact = put(tmp_path,'exact-limit.pem',key+b'\n'*(65536-len(key)),True)
    assert len(read_pin(exact,max_bytes=65536)) == 65536
    Path(exact['path']).write_bytes(b'x'*65537)
    with pytest.raises(VerificationError,match='RAW_INPUT_LIMIT'): read_pin(exact,max_bytes=65536)


def currency_case(root, record):
    admission = put(root,'currency-admission.json',record)
    wrapper = put(root,'wrapper.json',{'nested':[{'actualAdmissionPin':admission},admission]})
    opaque = put(root,'opaque.bin',b'engineering current binding',True)
    stamp = now()
    current = {name:opaque for name in ('planPin','targetIdentityPin','sourceScopePin','restoreResultPin','applicationStartPin')}
    current.update(backupAndChainPins=[],toolAndVersionPins=[],targetApprovalRefs=[],operationId='op',
                   restoreId='restore',mode='REHEARSAL',reportGeneratedAt=stamp)
    report = {name:value for name,value in current.items() if name != 'reportGeneratedAt'}
    report.update(schemaVersion='RecoveryVerificationReport/v1',reportId='engineering-report',verdict='PASSED',dataEvidencePins=[wrapper,admission],
                  playwrightEvidencePins=[],invalidatedBy=[],
                  rtoObservation={'state':'UNKNOWN','observedMilliseconds':None,'objectiveMilliseconds':None,'evidencePins':[]},
                  rpoObservation={'state':'UNKNOWN','observedMilliseconds':None,'objectiveMilliseconds':None,'evidencePins':[]})
    return report,current,stamp,admission,wrapper


@pytest.mark.parametrize('version',['RecoveryLabAdmission/v1','RecoveryLabAdmission/v3','RecoveryLabAdmission/v999',
                                   'RecoveryLabAdmission/unknown','RecoveryLabAdmission'])
@pytest.mark.parametrize('first',['data','plan'])
def test_unknown_admission_in_real_graph_never_retains_passed(tmp_path,version,first):
    report,current,stamp,admission,wrapper = currency_case(tmp_path,dict(schemaVersion=version,validUntil='2099-01-01T00:00:00Z'))
    if first == 'plan': report['planPin']=current['planPin']=wrapper
    reasons = report_invalidations(report,current,300000,stamp)
    assert sum(reason.endswith('_LAB_ADMISSION_VERSION_UNSUPPORTED') for reason in reasons)==1
    assert assess_report(report,current,300000,stamp)['verdict']=='STALE'
    report_pin=put(tmp_path,'report.json',report)
    current_pin=put(tmp_path,'current.json',current)
    trust=put(tmp_path,'currency-trust.json',dict(schemaVersion='RecoveryCurrencyCallerBinding/v1',callerThreadId='caller',
        producerThreadIds=['producer'],reportPin=report_pin,currentBindingPin=current_pin,schemaPin=file_pin(str(SCHEMA)),
        maxAgeMilliseconds=300000,validUntil='2099-01-01T00:00:00Z'))
    output=tmp_path/'currency-result.json'
    assert assess(report_pin['path'],current_pin['path'],str(output),trust)==1
    assert json_pin(file_pin(str(output)))['verdict']=='STALE'


@pytest.mark.parametrize('expiry',[None,'2020-01-01T00:00:00Z','invalid'])
def test_exact_v2_missing_invalid_expired_window_is_stale(tmp_path,expiry):
    record=dict(schemaVersion='RecoveryLabAdmission/v2')
    if expiry is not None: record['validUntil']=expiry
    report,current,stamp,*_=currency_case(tmp_path,record)
    assert assess_report(report,current,300000,stamp)['verdict']=='STALE'


def test_valid_v2_and_unrelated_schema_remain_current_and_pin_drift_invalidates(tmp_path):
    values=fixture(tmp_path)
    record=json_pin(values[0])
    report,current,stamp,admission,wrapper=currency_case(tmp_path,record)
    assert assess_report(report,current,300000,stamp)['verdict']=='PASSED'
    unrelated=put(tmp_path,'unrelated.json',{'schemaVersion':'RecoveryLabAdmissionAudit/v3','validUntil':'2020-01-01T00:00:00Z'})
    report['dataEvidencePins'].append(unrelated)
    assert report_invalidations(report,current,300000,stamp)==[]
    Path(admission['path']).write_bytes(b'changed original')
    assert assess_report(report,current,300000,stamp)['verdict']=='STALE'


def test_graph_only_follows_complete_pin_objects_and_not_unreferenced_files(tmp_path):
    report,current,stamp,*_=currency_case(tmp_path,{'schemaVersion':'RecoveryLabAdmission/v2','validUntil':'2099-01-01T00:00:00Z'})
    unknown=put(tmp_path,'unreferenced.json',{'schemaVersion':'RecoveryLabAdmission/v999'})
    partial=put(tmp_path,'partial-pin.json',{'path':unknown['path'],'sha256':unknown['sha256']})
    report['dataEvidencePins'].append(partial)
    assert report_invalidations(report,current,300000,stamp)==[]
    wrapper=put(tmp_path,'linked.json',{'actualPin':unknown})
    report['dataEvidencePins'].append(wrapper)
    assert assess_report(report,current,300000,stamp)['verdict']=='STALE'


def caller_case(root, scope_signer='authority'):
    roles={}
    values=fixture(root,key_roles=roles)
    old_admission,selected,old_request,proof=values
    admission=json_pin(old_admission)
    if scope_signer != 'authority':
        scope=signed(root,'scope-e.json',json_pin(admission['labScopePin'])['payload'],roles[scope_signer])
        selected.append(scope)
        admission['labScopePin']=scope
    source=put(root,'business-scope.json',dict(schemaVersion='RecoverySourceScope/v1',machineId='engineering-host',
        sourceIdentityPin=admission['sourceIdentityPin'],containerIds=[],containerNames=[],writerContainerIds=[],
        volumeNames=[],networkNames=[],materialPaths=[],endpointHosts=[]))
    target=put(root,'recovery-target.json',dict(schemaVersion='RecoveryTarget/v1',targetId='engineering-target',
        targetIdentityPin=admission['targetIdentityPin'],resourcesProofPin=admission['sourceIdentityPin'],
        isolationProofPin=admission['sourceIdentityPin'],versionPins=[admission['sourceIdentityPin']],
        configurationPin=admission['sourceIdentityPin'],secretRefs=[],sideEffectIsolationPin=admission['sourceIdentityPin'],
        leaseRef=json_pin(old_request)['leaseRef'],modePreconditionsPin=admission['sourceIdentityPin']))
    policy=put(root,'verifier-policy.json',dict(policy_v2(admission['sourceIdentityPin']),recoveryTargetPin=target))
    request=dict(json_pin(old_request),schemaVersion='backup-restore-operation/v1',requestId='engineering-request',
        selectedPointPin=admission['sourceIdentityPin'],policyPin=policy,deadlineMilliseconds=20000,
        inputPins={name:admission['sourceIdentityPin'] for name in ('restorePlan','restoreExecutionResult','applicationStartResult')})
    request_pin=put(root,'full-current-request.json',request)
    context=json_pin(file_pin(os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_PATH']))['payload']
    context.update(operationRequestPin=request_pin,labScopePin=admission['labScopePin'])
    context_pin=signed(root,'current-full-context.json',context,roles['authority'])
    os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_PATH']=context_pin['path']
    os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_SHA256']=context_pin['sha256']
    sources=[file_pin(str(path)) for path in sorted(MODULE.glob('*.py'))]+[file_pin(sys.executable)]
    scope=put(root,'executable-scope.json',dict(schemaVersion='RecoveryExecutableScope/v1',callerThreadId='caller',
        producerThreadIds=['producer'],complete=True,sourcePins=sources))
    trace=put(root,'source-trace.json',dict(schemaVersion='RecoverySourceTrace/v1',callerThreadId='caller',
        operationId='engineering-op',sourcePinsBefore=sources,sourcePinsAfter=sources,
        startedAt=context['issuedAt'],finishedAt=now(),collectionInvocationPins=[]))
    admission_pin=put(root,'current-admission.json',admission)
    selected=[*selected,source,target,policy,request_pin,scope,trace,admission_pin,file_pin(str(SCHEMA))]
    selection=put(root,'caller-selection.json',dict(schemaVersion='RecoveryLabCallerSelection/v1',callerThreadId='caller',
        producerThreadIds=['producer'],requestPin=request_pin,schemaPin=file_pin(str(SCHEMA)),sourceScopePin=source,
        executableScopePin=scope,runTracePin=trace,independentOriginalPins=selected,
        validUntil=admission['validUntil'],labAdmissionPin=admission_pin))
    return request,request_pin,selection,roles,admission,selected,proof


def test_distinct_authority_evidence_copy_roles_full_admission_binder_and_verify_entry(tmp_path):
    request,request_pin,selection,roles,admission,selected,proof=caller_case(tmp_path)
    assert len({role[1]['sha256'] for role in roles.values()})==3
    binding=bind(request_pin['path'],str(tmp_path/'bound.json'),selection)
    context=EvidenceContext(request,request_pin,binding,Deadline(20000))
    assert context.lab.scope['schemaVersion']=='RepositoryLabScope/v1'
    evidence=signed(tmp_path,'repository-evidence.json',{'engineeringOnly':'repository evidence role'},roles['evidence'])
    context.admitted.add((os.path.normcase(evidence['path']),evidence['bytes'],evidence['sha256']))
    context.lab.selected.add((os.path.normcase(evidence['path']),evidence['bytes'],evidence['sha256']))
    assert context.lab.signed(evidence,admission['repositoryEvidenceKeyPin'])['engineeringOnly']=='repository evidence role'
    assert context.lab.copy_protection(proof,300000)['sourceDeletionDenied']
    # Execute the real verifier entry through admission. This deliberately incomplete
    # restore evidence must fail at its genuine downstream schema, never PASSED.
    output=tmp_path/'verify-result.json'
    assert run(request_pin['path'],str(output),binding)==1
    result=json_pin(file_pin(str(output)))
    assert result['failureCode']=='SCHEMA_RestorePlan' and result['state']=='FAILED_RETAINED'


@pytest.mark.parametrize('entry',['binder','verify','collector'])
def test_evidence_signed_scope_is_rejected_by_all_actual_entries(tmp_path,entry):
    request,request_pin,selection,roles,admission,selected,proof=caller_case(tmp_path,'evidence')
    output=tmp_path/'entry-result.json'
    if entry=='binder':
        with pytest.raises(VerificationError,match='LAB_SIGNING_KEY_NOT_SELECTED'):
            bind(request_pin['path'],str(output),selection)
        assert not output.exists()
    elif entry=='verify':
        trust=dict(json_pin(selection),schemaVersion='RecoveryLabCallerBinding/v1')
        trust_pin=put(tmp_path,'verify-binding.json',trust)
        assert run(request_pin['path'],str(output),trust_pin)==1
        assert json_pin(file_pin(str(output)))['failureCode']=='LAB_SIGNING_KEY_NOT_SELECTED'
    else:
        config_pin,trust_pin=collection_case(tmp_path,admission,selected)
        with pytest.raises(VerificationError,match='LAB_SIGNING_KEY_NOT_SELECTED'):
            collect(config_pin['path'],str(output),trust_pin)
        assert not output.exists()


def collection_case(root,admission,selected):
    dummy=admission['targetIdentityPin']
    config=put(root,'collection-config.json',dict(schemaVersion='RecoveryCollectionConfig/v1',kind='data',
        operationId='engineering-op',restoreId='engineering-restore',recoveryPoint='engineering-point',
        targetIdentityPin=dummy,verificationTargetPin=dummy,authorizationPin=dummy,deadlineMilliseconds=20000,settings={}))
    admission_pin=next(pin for pin in selected if Path(pin['path']).name=='current-admission.json')
    trust=put(root,'collection-trust.json',dict(schemaVersion='RecoveryLabCollectionCallerBinding/v1',callerThreadId='caller',
        producerThreadIds=['producer'],configPin=config,authorizationPin=dummy,targetIdentityPin=dummy,toolPins=[],
        independentOriginalPins=[*selected,config],labAdmissionPin=admission_pin,validUntil=admission['validUntil']))
    return config,trust


def test_collector_valid_authority_scope_reaches_real_downstream_evidence_validation(tmp_path):
    _,_,_,roles,admission,selected,_=caller_case(tmp_path)
    config,trust=collection_case(tmp_path,admission,selected)
    with pytest.raises(VerificationError,match='RECORD_FIELDS'):
        collect(config['path'],str(tmp_path/'never-collected.json'),trust)
    assert not (tmp_path/'never-collected.json').exists()


def complete_lab_packet(root):
    """Full producer-shaped engineering verifier packet, with no service calls.

    Native exits and observations are explicit engineering originals inherited
    from Packet. An engineering PASSED result is not Linux or UI acceptance.
    """
    packet = Packet(root)
    authority_root = root / 'engineering-authority'
    authority_root.mkdir()
    roles = {}
    values = fixture(authority_root, key_roles=roles)
    prior = json_pin(values[0])
    selected = list(values[1])
    def save(name, value, role=None):
        pin = signed(root, name, value, roles[role]) if role else put(root, name, value)
        selected.append(pin)
        return pin
    scope = json_pin(prior['labScopePin'])['payload']
    scope['sourceIdentityPin'] = json_pin(packet.source_scope)['sourceIdentityPin']
    scope_pin = save('packet-scope.json', scope, 'authority')
    old_proof = json_pin(values[3])['payload']
    acl = json_pin(old_proof['aclEvidencePin'])['payload']
    deletion = json_pin(acl['deletionAttemptPin'])['payload']
    access = json_pin(acl['keyAccessEvidencePin'])['payload']
    for record in (deletion, access, acl): record['labScopePin'] = scope_pin
    acl['sourceIdentityPin'] = scope['sourceIdentityPin']
    acl['deletionAttemptPin'] = save('packet-deletion.json', deletion, 'copy')
    acl['keyAccessEvidencePin'] = save('packet-key-access.json', access, 'copy')
    endpoint = json_pin(old_proof['readbackEndpointEvidencePin'])['payload']
    endpoint['labScopePin'] = scope_pin
    proof = dict(old_proof, labScopePin=scope_pin, sourceIdentityPin=scope['sourceIdentityPin'],
                 aclEvidencePin=save('packet-acl.json', acl, 'copy'),
                 readbackEndpointEvidencePin=save('packet-readback.json', endpoint, 'copy'))
    proof_pin = save('packet-copy-proof.json', proof, 'copy')
    manifest = save('packet-manifest.json', {'copyProtectionPin':proof_pin}, 'evidence')
    packet.change('point', lambda value: value.update(manifestPin=manifest))
    packet.change('material', lambda value: value.update(manifestPin=manifest))
    packet.change('target-configuration-native', lambda value: value.update(targetId='engineering-fixture'))
    packet.verification_target = packet.all_pins['verification-target']
    lease = dict(json_pin(json_pin(values[2])['leaseRef']), operationId='op1', targetId='engineering-fixture')
    grant = dict(json_pin(json_pin(values[2])['authorizationRefs'][0]), operationId='op1', targetId='engineering-fixture')
    lease_pin = save('packet-current-lease.json', lease)
    grant_pin = save('packet-current-grant.json', grant)
    packet.approval = packet.all_pins['authorization']
    packet.request.update(leaseRef=lease_pin, authorizationRefs=[grant_pin, packet.approval])
    request_pin = packet.put('request', packet.request)
    admission = dict(prior, sourceIdentityPin=scope['sourceIdentityPin'], targetIdentityPin=packet.target,
                     labScopePin=scope_pin)
    admission_pin = save('packet-admission.json', admission)
    context = json_pin(file_pin(os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_PATH']))['payload']
    context.update(sourceIdentityPin=scope['sourceIdentityPin'], labScopePin=scope_pin,
                   operationRequestPin=request_pin, authorizationPin=grant_pin, leasePin=lease_pin)
    context_pin = signed(root, 'packet-out-of-band-context.json', context, roles['authority'])
    os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_PATH'] = context_pin['path']
    os.environ['INTRUOYI_BACKUP_LAB_CONTEXT_SHA256'] = context_pin['sha256']
    data_call = packet.invocation('collect-data-call','COLLECT_DATA',packet.all_pins['data'],11,13)
    browser = packet.invocation('collect-browser-call','COLLECT_PLAYWRIGHT',packet.all_pins['browser'],14,20)
    ui = dict(schemaVersion='RecoveryUiScenarioConfig/v1',runId='engineering-only',phase='target',
        operationId='op1',restoreId='restore1',recoveryPoint='point-1',sourceOrigin='http://127.0.0.1:9998',
        targetOrigin='http://127.0.0.1:9999',baseUrl='http://127.0.0.1:9999/login',apiOrigin='http://127.0.0.1:9999',
        allowedOrigins=['http://127.0.0.1:9999'],objectOrigins=[],writeApiPaths=[],browserExecutable=sys.executable,
        passwordEnv='UNPROVIDED_ENGINEERING_SECRET',targetIdentityPin=packet.target,
        verificationTargetPin=packet.verification_target,authorizationPin=packet.approval,deadlineMilliseconds=20000,
        login={},flows=[],schemaPin=file_pin(str(SCHEMA)),prerequisites=dict(deltaObservationPin=packet.all_pins['data'],
        fullPointPin=packet.request['selectedPointPin'],fullBackupResultPin=packet.all_pins['payload'],
        incrementalPointPin=packet.request['selectedPointPin'],incrementalBackupResultPin=packet.all_pins['payload'],
        restorePlanPin=packet.request['inputPins']['restorePlan'],restoreResultPin=packet.request['inputPins']['restoreExecutionResult'],
        applicationStartPin=packet.request['inputPins']['applicationStartResult']))
    ui_pin = packet.put('packet-ui-config',ui)
    invocation = copy.deepcopy(json_pin(browser))
    entry = MODULE / 'run_ui_recovery.py'
    invocation['sourcePins'] = [file_pin(sys.executable),file_pin(str(entry))]
    invocation['argv'] = [sys.executable,str(entry),'--config',ui_pin['path'],'--output',packet.browser['path']]
    process = dict(json_pin(invocation['processResultPin']),argv=invocation['argv'])
    invocation['processResultPin'] = packet.put('packet-ui-process',process)
    ui_call = packet.put('packet-ui-call',invocation)
    sources = [file_pin(str(path)) for path in sorted(MODULE.glob('*.py'))]+[file_pin(sys.executable),packet.tool]
    executable_scope = packet.put('executable-scope',dict(schemaVersion='RecoveryExecutableScope/v1',
        callerThreadId='caller',producerThreadIds=['producer'],complete=True,sourcePins=sources))
    trace = packet.put('trace',dict(schemaVersion='RecoverySourceTrace/v1',callerThreadId='caller',operationId='op1',
        sourcePinsBefore=sources,sourcePinsAfter=sources,startedAt=packet.time(0),finishedAt=packet.time(25),
        collectionInvocationPins=[data_call,ui_call]))
    selected += list(packet.all_pins.values())+sources+[file_pin(str(SCHEMA))]
    selected = list({pin_key(pin):pin for pin in selected}.values())
    selection = put(root,'packet-selection.json',dict(schemaVersion='RecoveryLabCallerSelection/v1',callerThreadId='caller',
        producerThreadIds=['producer'],requestPin=request_pin,schemaPin=file_pin(str(SCHEMA)),sourceScopePin=packet.source_scope,
        executableScopePin=executable_scope,runTracePin=trace,independentOriginalPins=selected,
        validUntil=admission['validUntil'],labAdmissionPin=admission_pin))
    return packet,request_pin,selection,roles


def test_full_engineering_verify_uses_authority_scope_evidence_manifest_and_copy_proof(tmp_path):
    packet,request_pin,selection,roles = complete_lab_packet(tmp_path)
    assert len({role[1]['sha256'] for role in roles.values()}) == 3
    binding = bind(request_pin['path'],str(tmp_path/'packet-binding.json'),selection)
    output = tmp_path/'packet-verification.json'
    assert run(request_pin['path'],str(output),binding) == 0, json_pin(file_pin(str(output)))
    result = json_pin(file_pin(str(output)))
    assert result['state'] == 'SUCCEEDED' and result['data']['verdict'] == 'PASSED'
    assert result['message'] == 'Same-host lab REHEARSAL verified; no production, NAS or cutover acceptance'
    assert result['actualExitCode'] is None
