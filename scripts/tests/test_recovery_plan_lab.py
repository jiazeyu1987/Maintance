"""Real local signature/byte checks; no fabricated runtime or restore acceptance."""
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
from recovery_engine import RecoveryError, canonical, pin, write
from recovery_plan_lab import (ACL_FIELDS, COPY_FIELDS, PROFILE_FIELDS, READBACK_FIELDS,
    REHEARSAL_ID, LAB_HOST, LAB_ROOT, LAB_PREFIX, admit, copy_protection, context_record,
    chain_binding, scope_record, host_record, host_contract, selected_context, acyclic_inputs,
    LAB_ACTIONS, current_authority, required_actions, capture_scope_binding)


def originals(tmp_path):
    key = Ed25519PrivateKey.generate()
    public = tmp_path/'public.pem'
    public.write_bytes(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    key_ref = pin(public)
    def seal(name, payload):
        return write(tmp_path/(name+'.json'), dict(schemaVersion='RepositorySignedRecord/v1',
            keySha256=key_ref['sha256'], payload=payload,
            signature=base64.b64encode(key.sign(canonical(payload))).decode()))
    now = datetime.now(timezone.utc)
    start = (now-timedelta(seconds=10)).isoformat().replace('+00:00', 'Z')
    end = (now+timedelta(minutes=10)).isoformat().replace('+00:00', 'Z')
    identity = write(tmp_path/'identity.json', dict(sourceFingerprint='a'*64, databaseUuid='source-db'))
    source_raw = tmp_path/'raw-observation'; source_raw.write_bytes(b'original local protocol evidence')
    raw_ref = pin(source_raw)
    scope = dict(schemaVersion='RepositoryLabScope/v1', rehearsalId=REHEARSAL_ID, repositoryId='repo',
        sourceIdentityPin=identity, host=LAB_HOST, root=LAB_ROOT, resourcePrefix=LAB_PREFIX,
        allowedActions=sorted(LAB_ACTIONS), expiresAt=end)
    scope_pin = seal('scope', scope)
    bound = dict(repositoryId='repo', sourceIdentityPin=identity, labScopePin=scope_pin)
    account_pins=[]
    for account in ('source','writer','reader'):
        path=tmp_path/(account+'.account');path.write_bytes(('local account original: '+account).encode())
        account_pins.append(pin(path))
    archive_root=LAB_ROOT+'/repository/archives'
    deletion=dict(schemaVersion='RepositoryLabDeletionProbe/v1',labScopePin=scope_pin,
        accountPin=account_pins[0],archiveRoot=archive_root,deleteDenied=True,probeOriginalPin=raw_ref)
    key_access=dict(schemaVersion='RepositoryLabKeyAccess/v1',labScopePin=scope_pin,
        recoveryKeysAvailable=True,probeOriginalPin=raw_ref)
    acl = dict(schemaVersion='RepositoryLabAclEvidence/v1',labScopePin=scope_pin,sourceIdentityPin=identity,
        archiveRoot=archive_root,sourceAccountPin=account_pins[0],writerAccountPin=account_pins[1],
        readerAccountPin=account_pins[2],deletionAttemptPin=seal('deletion',deletion),
        keyAccessEvidencePin=seal('key-access',key_access))
    readback = dict(schemaVersion='RepositoryLabReadbackEndpoint/v1',labScopePin=scope_pin,
        archiveRoot=archive_root,uncRoot='\\\\'+LAB_HOST+'\\'+LAB_PREFIX+'-archive',encrypted=True,
        signingRequired=True,independentConnectionId='local independent reader connection',
        readerAccountPin=account_pins[2],readbackOriginalPin=raw_ref,observedAt=start)
    proof = dict(schemaVersion='RepositoryLabCopyProtection/v1', **bound, sourceDeletionDenied=True,
        independentFailureDomain=False, recoveryKeysAvailable=True, aclEvidencePin=seal('acl',acl),
        readbackEndpointEvidencePin=seal('readback',readback), validUntil=end)
    proof_pin = seal('copy', proof)
    profile = dict(schemaVersion='RecoveryDataLabProfile/v2', authorityKeyPin=key_ref,
        executionHostPin=raw_ref, installedClosurePin=raw_ref, labScopePin=scope_pin,
        repositoryAuthorityKeyPins=[key_ref], copyProtectionEvidenceKeyPins=[key_ref],
        copyProtectionPinsByManifestSha256={'b'*64:proof_pin})
    assert set(profile) == PROFILE_FIELDS and set(proof) == COPY_FIELDS
    assert set(acl) == ACL_FIELDS and set(readback) == READBACK_FIELDS
    policy = dict(schemaVersion='RecoveryDataLabPolicy/v1', repositoryId='repo',
                  labProfilePin=write(tmp_path/'profile.json',profile), maximumProofAgeSeconds=300)
    manifest = dict(copyProtectionPin=proof_pin, sourceIdentityPin=identity)
    return locals()


def revise(case, name, record):
    ref = case['seal'](name, record)
    profile = case['profile']
    if name == 'copy':
        profile['copyProtectionPinsByManifestSha256']={'b'*64:ref}; case['manifest']['copyProtectionPin']=ref
    elif name in {'deletion','key_access'}:
        case['acl']['deletionAttemptPin' if name=='deletion' else 'keyAccessEvidencePin']=ref
        return revise(case,'acl',case['acl'])
    else:
        proof = case['proof']; proof['aclEvidencePin' if name=='acl' else 'readbackEndpointEvidencePin']=ref
        return revise(case,'copy',proof)
    case['policy']['labProfilePin']=write(case['tmp_path']/'profile.json',profile)


def test_signed_lab_copy_protection_accepts_only_truthful_same_host_protocol(tmp_path):
    c=originals(tmp_path)
    pins=copy_protection(c['manifest'],c['policy'],archive_root=c['archive_root'])
    assert len(pins) == 11 and c['acl']['deletionAttemptPin'] in pins and c['raw_ref'] in pins


@pytest.mark.parametrize('field,value', [('independentFailureDomain',True), ('independentFailureDomain',0),
    ('sourceDeletionDenied',False), ('recoveryKeysAvailable',False), ('repositoryId','other'),
    ('validUntil','2000-01-01T00:00:00Z')])
def test_wrong_or_expired_copy_protection_is_rejected(tmp_path,field,value):
    c=originals(tmp_path); c['proof'][field]=value; revise(c,'copy',c['proof'])
    with pytest.raises(RecoveryError): copy_protection(c['manifest'],c['policy'])


@pytest.mark.parametrize('kind,field,value', [('acl','sourceIdentityPin',None),
    ('acl','archiveRoot','/other/archives'), ('acl','readerAccountPin',None),
    ('acl','deletionAttemptPin',None), ('readback','independentConnectionId',''),
    ('readback','signingRequired',False), ('readback','encrypted',False),
    ('readback','readerAccountPin',None), ('readback','observedAt','2000-01-01T00:00:00Z'),
    ('deletion','deleteDenied',False),('deletion','accountPin',None),('deletion','labScopePin',None),
    ('key_access','recoveryKeysAvailable',False),('key_access','probeOriginalPin',None)])
def test_acl_and_actual_reader_proofs_are_not_optional(tmp_path,kind,field,value):
    c=originals(tmp_path); c[kind][field]=value; revise(c,kind,c[kind])
    with pytest.raises(RecoveryError): copy_protection(c['manifest'],c['policy'])


def test_original_acl_bytes_are_rehashed(tmp_path):
    c=originals(tmp_path); copy_protection(c['manifest'],c['policy'])
    c['source_raw'].write_bytes(b'tampered protocol bytes')
    with pytest.raises(RecoveryError,match='PIN_CHANGED'): copy_protection(c['manifest'],c['policy'])


def test_signature_changes_never_select_a_different_authority(tmp_path):
    c=originals(tmp_path)
    from recovery_engine import pinned_json
    envelope=pinned_json(c['manifest']['copyProtectionPin']); envelope['payload']['sourceDeletionDenied']=False
    ref=write(tmp_path/'tampered.json',envelope); c['manifest']['copyProtectionPin']=ref
    c['profile']['copyProtectionPinsByManifestSha256']={'b'*64:ref}
    c['policy']['labProfilePin']=write(tmp_path/'profile.json',c['profile'])
    with pytest.raises(InvalidSignature): copy_protection(c['manifest'],c['policy'])


@pytest.mark.parametrize('field,value',[('host','172.30.30.58'), ('root','/other'),
    ('resourcePrefix','other'), ('rehearsalId','other')])
def test_exact_rehearsal_host_root_and_actions_are_required(tmp_path,field,value):
    c=originals(tmp_path);c['scope'][field]=value;c['profile']['labScopePin']=c['seal']('scope2',c['scope'])
    with pytest.raises(RecoveryError,match='LAB_SCOPE_NOT_AUTHORIZED'):scope_record(c['profile'],c['policy'])


@pytest.mark.parametrize('allowed',[['FULL'],['INCREMENTAL'],['READBACK'],['CONTROLLED_CUTOVER'],[],
                                  ['RESTORE_EXECUTE','RESTORE_EXECUTE'],[None]])
def test_scope_has_no_action_alias_or_implicit_all_actions(tmp_path,allowed):
    c=originals(tmp_path);c['scope']['allowedActions']=allowed
    c['profile']['labScopePin']=c['seal']('scope-actions',c['scope'])
    with pytest.raises(RecoveryError,match='LAB_ACTIONS_INVALID'):scope_record(c['profile'],c['policy'])


def test_scope_accepts_selected_subset_and_requires_only_needed_actions(tmp_path):
    c=originals(tmp_path);c['scope']['allowedActions']=['READBACK_VERIFY']
    c['profile']['labScopePin']=c['seal']('scope-subset',c['scope'])
    assert scope_record(c['profile'],c['policy'],{'READBACK_VERIFY'}) == c['scope']
    with pytest.raises(RecoveryError,match='LAB_SCOPE_NOT_AUTHORIZED'):
        scope_record(c['profile'],c['policy'],{'RESTORE_EXECUTE'})


@pytest.mark.parametrize('mode,action',[('CONTROLLED_RESTORE','RESTORE_PREFLIGHT'),
    ('CONTROLLED_RESTORE','RESTORE_EXECUTE'),('REHEARSAL','CONTROLLED_CUTOVER')])
def test_lab_selection_cannot_enter_controlled_or_cutover(mode,action):
    with pytest.raises(RecoveryError,match='LAB_REHEARSAL_ONLY'):
        admit(dict(mode=mode,action=action),{}, {}, {})


def test_windows_local_machine_never_counts_as_native_lab_host(tmp_path):
    c=originals(tmp_path)
    host={name:None for name in __import__('recovery_plan_lab').HOST_FIELDS}
    host['schemaVersion']='RepositoryNativeExecutionHost/v1'
    c['profile']['executionHostPin']=write(tmp_path/'host.json',host)
    with pytest.raises(RecoveryError,match='LAB_NATIVE_HOST_REQUIRED'):host_record(c['profile'])


def host_contract_case(c):
    host={name:None for name in __import__('recovery_plan_lab').HOST_FIELDS}
    host.update(schemaVersion='RepositoryNativeExecutionHost/v1',hostOs='Linux',uid=0,gid=0,
                environment={'PATH':'/usr/bin'},installationManifestPin=c['profile']['installedClosurePin'])
    return host


def test_explicit_linux_case_and_static_environment_contract(tmp_path):
    c=originals(tmp_path);host=host_contract_case(c)
    assert host_contract(host,c['profile']) == host


@pytest.mark.parametrize('field,value',[('hostOs','linux'),('uid',False),('gid',1),
    ('environment','backup-lab'),('environment',{'INTRUOYI_BACKUP_LAB_CONTEXT_PATH':'/current'}),
    ('environment',{'INTRUOYI_REPOSITORY_LAB_CONTEXT_SHA256':'a'*64}),('environment',{'PYTHONPATH':'/other'}),
    ('environment',{'NAME=BAD':'value'}),('environment',{'NAME':None}),
    ('environment',{'INTRUOYI_REPOSITORY_HOST_VIEW_PATH':'/other'})])
def test_host_contract_rejects_aliases_and_dynamic_selection(tmp_path,field,value):
    c=originals(tmp_path);host=host_contract_case(c);host[field]=value
    with pytest.raises(RecoveryError):host_contract(host,c['profile'])


def current_case(c, action='REHEARSAL'):
    identity=write(c['tmp_path']/'target-identity.json',{'targetId':'target'})
    grant=dict(schemaVersion='RecoveryEnvironmentAuthorization/v1',operationId='op',targetId='target',
        executorId='executor',mode='REHEARSAL',actions=sorted(required_actions({'mode':'REHEARSAL','action':action})),
        notBefore=c['start'],expiresAt=c['end'],approved=True)
    lease=dict(schemaVersion='RecoveryEnvironmentLease/v1',operationId='op',targetId='target',executorId='executor',
        leaseId='lease',fenceToken=1,notBefore=c['start'],expiresAt=c['end'],state='HELD')
    grant_pin=write(c['tmp_path']/'current-grant.json',grant);lease_pin=write(c['tmp_path']/'current-lease.json',lease)
    request=dict(schemaVersion='backup-restore-operation/v1',operationId='op',requestId='req',action=action,
        mode='REHEARSAL',selectedPointPin=None,sourceOrTargetRef=identity,policyPin=c['policy']['labProfilePin'],
        authorizationRefs=[grant_pin],leaseRef=lease_pin,inputPins={},deadlineMilliseconds=1000)
    context=dict(schemaVersion='BackupRehearsalAuthorityContext/v1',rehearsalId=REHEARSAL_ID,
        environment='backup-lab',sourceIdentityPin=c['identity'],executionHostPin=c['raw_ref'],
        labScopePin=c['scope_pin'],operationRequestPin=write(c['tmp_path']/'current-request.json',request),
        installedClosurePin=c['raw_ref'],authorizationPin=grant_pin,leasePin=lease_pin,authorityKeyPin=c['key_ref'],
        issuedAt=c['start'],expiresAt=c['end'])
    context=context_record(c['seal']('current-context',context),c['profile'],c['scope'])
    trust=dict(executorId='executor',authorizationSha256s=[grant_pin['sha256']],leaseSha256s=[lease_pin['sha256']])
    return dict(request=request,context=context,grant=grant,lease=lease,identity=identity,trust=trust)


@pytest.mark.parametrize('action',['RESTORE_PREFLIGHT','REHEARSAL','RESTORE_EXECUTE'])
def test_exact_current_request_and_needed_actions_are_required(tmp_path,action):
    c=originals(tmp_path);r=current_case(c,action)
    scope=dict(c['scope'],allowedActions=r['grant']['actions'])
    current_authority(r['request'],r['context'],scope,r['identity'],r['trust'])


@pytest.mark.parametrize('mutation',['scope_missing','selected_grant_missing','other_grant_covers_gap',
    'wrong_request','wrong_operation','untrusted_grant','lease_not_held','fence_zero','unknown_grant',
    'expired_grant','context_outlives_lease'])
def test_current_authority_never_uses_another_request_or_grant(tmp_path,mutation):
    c=originals(tmp_path);r=current_case(c);scope=dict(c['scope'])
    if mutation=='scope_missing':scope['allowedActions']=['RESTORE_EXECUTE']
    if mutation in {'selected_grant_missing','other_grant_covers_gap'}:
        r['grant']['actions']=['RESTORE_EXECUTE']
    if mutation=='other_grant_covers_gap':
        other=write(tmp_path/'other-grant.json',dict(r['grant'],actions=sorted(LAB_ACTIONS)))
        r['request']['authorizationRefs'].append(other);r['trust']['authorizationSha256s'].append(other['sha256'])
    if mutation=='wrong_request':r['request']['requestId']='other'
    if mutation=='wrong_operation':r['grant']['operationId']='other'
    if mutation=='lease_not_held':r['lease']['state']='EXPIRED'
    if mutation=='fence_zero':r['lease']['fenceToken']=0
    if mutation=='unknown_grant':r['grant']['schemaVersion']='RepositoryAuthorization/v1'
    if mutation=='expired_grant':r['grant']['expiresAt']='2000-01-01T00:00:00Z'
    if mutation=='context_outlives_lease':r['context']['expiresAt']='2100-01-01T00:00:00Z'
    if mutation not in {'scope_missing','wrong_request','context_outlives_lease'}:
        grant=write(tmp_path/'changed-grant.json',r['grant']);lease=write(tmp_path/'changed-lease.json',r['lease'])
        r['context'].update(authorizationPin=grant,leasePin=lease)
        r['request'].update(authorizationRefs=[grant]+r['request']['authorizationRefs'][1:],leaseRef=lease)
        r['trust'].update(authorizationSha256s=[grant['sha256']]+r['trust']['authorizationSha256s'][1:],
                          leaseSha256s=[lease['sha256']])
        r['context']['operationRequestPin']=write(tmp_path/'changed-request.json',r['request'])
    if mutation=='untrusted_grant':r['trust']['authorizationSha256s']=[]
    with pytest.raises(RecoveryError):current_authority(r['request'],r['context'],scope,r['identity'],r['trust'])


def historical_case(c):
    template_scope=dict(schemaVersion='backup-lab-source-scope-template/v1',environment='backup-lab',
        targetRawSha256='c'*64,targetFingerprint='a'*64,database='database',databaseUuid='source-db')
    template=write(c['tmp_path']/'capture-template.json',dict(schemaVersion='backup-lab-capture-request-template/v1',
        sourceScope=template_scope))
    source=write(c['tmp_path']/'capture-source.json',dict(schemaVersion='RepositoryNativeBackupSource/v1',
        sourceIdentityPin=c['identity'],executionHostPin=c['raw_ref'],captureRequestPin=template))
    lease=c['seal']('capture-lease',dict(schemaVersion='RepositoryLease/v1',repositoryId='repo',operationId='capture',
        ownerIdentityPin=c['identity'],expiresAt=c['end']))
    grant=c['seal']('capture-grant',dict(schemaVersion='RepositoryAuthorization/v1',repositoryId='repo',
        operationId='capture',actions=['BACKUP_FULL'],sourceOrTargetRef=source,resourcePin=source,
        policyPin=c['policy']['labProfilePin'],leaseRef=lease,notBefore=c['start'],expiresAt=c['end']))
    request=dict(schemaVersion='backup-restore-operation/v1',operationId='capture',requestId='capture-req',
        action='BACKUP_FULL',mode='REHEARSAL',selectedPointPin=None,sourceOrTargetRef=source,
        policyPin=c['policy']['labProfilePin'],authorizationRefs=[grant],leaseRef=lease,inputPins={},deadlineMilliseconds=1000)
    context=dict(schemaVersion='BackupRehearsalAuthorityContext/v1',rehearsalId=REHEARSAL_ID,
        environment='backup-lab',sourceIdentityPin=c['identity'],executionHostPin=c['raw_ref'],labScopePin=c['scope_pin'],
        operationRequestPin=write(c['tmp_path']/'capture-request.json',request),installedClosurePin=c['raw_ref'],
        authorizationPin=grant,leasePin=lease,authorityKeyPin=c['key_ref'],issuedAt=c['start'],expiresAt=c['end'])
    return request,context


def test_signed_capture_provenance_is_bound_to_original_backup_request(tmp_path):
    c=originals(tmp_path);request,context=historical_case(c)
    assert context_record(c['seal']('historical-capture',context),c['profile'],c['scope'],historical=True)==context


@pytest.mark.parametrize('mutation',[None,'different_raw_target','different_database','other_context',
                                    'wrong_template_schema','embedded_current_context'])
def test_retained_capture_scope_matches_its_original_context_free_template(tmp_path,mutation):
    from recovery_engine import pinned_json
    c=originals(tmp_path);request,context=historical_case(c)
    context_ref=c['seal']('scope-capture-context',context)
    source=pinned_json(request['sourceOrTargetRef']);template=pinned_json(source['captureRequestPin'])
    capture=dict(template['sourceScope'],schemaVersion='backup-lab-source-scope/v1',labContextPin=context_ref)
    if mutation=='different_raw_target':capture['targetRawSha256']='d'*64
    if mutation=='different_database':capture['database']='different'
    if mutation=='other_context':capture['labContextPin']=c['raw_ref']
    if mutation=='wrong_template_schema':template['schemaVersion']='backup-lab-capture-request/v1'
    if mutation=='embedded_current_context':template['labContextPin']=context_ref
    if mutation in {'wrong_template_schema','embedded_current_context'}:
        source['captureRequestPin']=write(tmp_path/'wrong-template',template)
        request['sourceOrTargetRef']=write(tmp_path/'wrong-template-source',source)
        context['operationRequestPin']=write(tmp_path/'wrong-template-request',request)
    consumer={'captureContextPin':context_ref}
    if mutation is None:
        capture_scope_binding(consumer,context,capture,pinned_json(c['identity']))
    else:
        with pytest.raises(RecoveryError):capture_scope_binding(consumer,context,capture,pinned_json(c['identity']))


def test_expired_signed_capture_provenance_is_not_current_authority(tmp_path):
    c=originals(tmp_path);now=datetime.now(timezone.utc)
    c['start']=(now-timedelta(hours=1)).isoformat().replace('+00:00','Z')
    c['end']=(now-timedelta(minutes=30)).isoformat().replace('+00:00','Z')
    _,context=historical_case(c);ref=c['seal']('expired-capture',context)
    assert context_record(ref,c['profile'],c['scope'],historical=True)==context
    with pytest.raises(RecoveryError,match='AUTHORIZATION_OR_PROOF_EXPIRED'):
        context_record(ref,c['profile'],c['scope'])


@pytest.mark.parametrize('kind,schema',[('acl','RepositoryLabAclEvidence/unknown'),
                                      ('readback','RepositoryLabReadbackEndpoint/unknown')])
def test_unknown_child_schemas_are_rejected_with_original_signatures(tmp_path,kind,schema):
    c=originals(tmp_path);c[kind]['schemaVersion']=schema;revise(c,kind,c[kind])
    with pytest.raises(RecoveryError,match='LAB_RECORD_INVALID_'):copy_protection(c['manifest'],c['policy'])


def test_lab_action_words_and_request_fields_match_frozen_wire_exactly():
    import json
    path=Path(__file__).resolve().parents[2]/'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json'
    schema=json.loads(path.read_text(encoding='utf-8'))['$defs']['OperationRequest']
    assert LAB_ACTIONS == set(schema['properties']['action']['enum'])-{
        'CONTROLLED_CUTOVER','RETENTION_PLAN','RETENTION_EXECUTE','OBSERVE_OPERATION','DIAGNOSE_EXECUTION'}
    assert __import__('recovery_plan_lab').OPERATION_FIELDS == set(schema['required'])


@pytest.mark.parametrize('mutation',['restore_action','wrong_operation','wrong_source','wrong_grant','wrong_lease'])
def test_historical_capture_cannot_be_another_request_current_context(tmp_path,mutation):
    c=originals(tmp_path);request,context=historical_case(c)
    if mutation=='restore_action':request['action']='REHEARSAL'
    if mutation=='wrong_operation':request['operationId']='other'
    if mutation=='wrong_source':request['sourceOrTargetRef']=write(tmp_path/'other-source',
        dict(schemaVersion='RepositoryNativeBackupSource/v1',sourceIdentityPin=c['raw_ref'],executionHostPin=c['raw_ref']))
    if mutation=='wrong_grant':request['authorizationRefs']=[]
    if mutation=='wrong_lease':request['leaseRef']=c['raw_ref']
    context['operationRequestPin']=write(tmp_path/'wrong-capture-request',request)
    with pytest.raises(RecoveryError):
        context_record(c['seal']('wrong-historical-context',context),c['profile'],c['scope'],historical=True)


@pytest.mark.parametrize('original',['sourceAccountPin','writerAccountPin','readerAccountPin','readbackOriginalPin'])
def test_actual_account_and_readback_original_bytes_are_rehashed(tmp_path,original):
    c=originals(tmp_path);copy_protection(c['manifest'],c['policy'])
    ref=c['readback'][original] if original=='readbackOriginalPin' else c['acl'][original]
    Path(ref['path']).write_bytes(b'changed retained original')
    with pytest.raises(RecoveryError,match='PIN_CHANGED'):copy_protection(c['manifest'],c['policy'])


def test_copy_evidence_is_bound_to_selected_archive_and_distinct_account_pins(tmp_path):
    c=originals(tmp_path)
    with pytest.raises(RecoveryError,match='LAB_ARCHIVE_ROOT_MISMATCH'):
        copy_protection(c['manifest'],c['policy'],archive_root=LAB_ROOT+'/different/archives')
    c['acl']['writerAccountPin']=c['acl']['sourceAccountPin'];revise(c,'acl',c['acl'])
    with pytest.raises(RecoveryError,match='LAB_INDEPENDENT_READER_REQUIRED'):copy_protection(c['manifest'],c['policy'])


def test_private_profile_v1_flat_mappings_are_rejected_not_aliased(tmp_path):
    c=originals(tmp_path);c['profile']['schemaVersion']='RecoveryDataLabProfile/v1'
    c['profile']['copyProtectionEvidenceRules']={'acl':{},'readback':{}}
    c['policy']['labProfilePin']=write(tmp_path/'old-profile.json',c['profile'])
    with pytest.raises(RecoveryError,match='LAB_RECORD_INVALID_RECOVERYDATALABPROFILE'):
        copy_protection(c['manifest'],c['policy'])


def test_actual_w03_nested_proofs_are_acyclic_byte_graph(tmp_path):
    c=originals(tmp_path);selected=c['seal']('current',{'unitOnly':True})
    c['profile']['executionHostPin']=write(tmp_path/'host-graph-node',{'unitOnly':'not-an-actual-host'})
    c['profile']['installedClosurePin']=write(tmp_path/'install-graph-node',{'unitOnly':'not-an-installed-runtime'})
    acyclic_inputs([c['profile']],selected)


def test_public_output_protects_actual_nested_account_and_probe_originals(tmp_path):
    from recovery_cli import PublicOutput
    from recovery_engine import Budget
    c=originals(tmp_path);publisher=PublicOutput(c['raw_ref']['path']);publisher.budget=Budget(30000)
    publisher.collect({'copyProtectionPin':c['manifest']['copyProtectionPin']})
    for ref in c['account_pins']+[c['raw_ref']]:
        assert Path(ref['path']) in publisher.protected and Path(ref['path']) not in publisher.documents
    assert Path(c['acl']['deletionAttemptPin']['path']) in publisher.documents
    publisher.context=({}, {'evidenceRoot':str(tmp_path)});publisher.complete=True
    with pytest.raises(RecoveryError,match='PUBLIC_OUTPUT_PROTECTED_PATH'):publisher.check()


def test_public_output_keeps_signed_installation_programs_as_protected_byte_leaves(tmp_path):
    from recovery_cli import PublicOutput
    from recovery_engine import Budget
    c=originals(tmp_path)
    installed=c['seal']('installation',dict(schemaVersion='RepositoryNativeInstallation/v1',root=LAB_ROOT,
        sourceToolkitPin=c['account_pins'][2],filePins=[c['raw_ref']],dependencyPins=[c['account_pins'][0]],
        pythonPin=c['account_pins'][1]))
    publisher=PublicOutput(tmp_path/'unused');publisher.budget=Budget(30000)
    publisher.collect({'installedClosurePin':installed})
    assert Path(installed['path']) in publisher.documents
    for ref in c['account_pins']+[c['raw_ref']]:
        assert Path(ref['path']) in publisher.protected and Path(ref['path']) not in publisher.documents


def test_lab_material_and_signed_copy_record_are_rejected_under_production_policy(tmp_path):
    c=originals(tmp_path); policy={'schemaVersion':'RecoveryDataPolicy/v1'}
    with pytest.raises(RecoveryError,match='LAB_MATERIAL_IN_PRODUCTION_POLICY'):
        chain_binding({},c['manifest'],{'environment':'backup-lab'},policy)
    with pytest.raises(RecoveryError,match='LAB_COPY_PROTECTION_IN_PRODUCTION_POLICY'):
        chain_binding({},c['manifest'],{'environment':'prod'},policy)


@pytest.mark.parametrize('change',[{'environment':'prod'}, {'rehearsalId':'other'},
    {'expiresAt':'2000-01-01T00:00:00Z'}, {'unknown':True}])
def test_context_is_signed_exact_current_and_source_bound(tmp_path,change):
    c=originals(tmp_path)
    context=dict(schemaVersion='BackupRehearsalAuthorityContext/v1',rehearsalId=REHEARSAL_ID,
        environment='backup-lab',sourceIdentityPin=c['identity'],
        executionHostPin=c['raw_ref'],labScopePin=c['scope_pin'],operationRequestPin=c['raw_ref'],
        installedClosurePin=c['raw_ref'],authorizationPin=c['raw_ref'],leasePin=c['raw_ref'],
        authorityKeyPin=c['key_ref'],issuedAt=c['start'],expiresAt=c['end'])
    context.update(change);ref=c['seal']('context',context)
    with pytest.raises(RecoveryError):context_record(ref,c['profile'],c['scope'])


def test_valid_context_and_wrong_source_are_checked_from_signed_originals(tmp_path):
    c=originals(tmp_path)
    context=dict(schemaVersion='BackupRehearsalAuthorityContext/v1',rehearsalId=REHEARSAL_ID,
        environment='backup-lab',sourceIdentityPin=c['identity'],executionHostPin=c['raw_ref'],
        labScopePin=c['scope_pin'],operationRequestPin=c['raw_ref'],installedClosurePin=c['raw_ref'],
        authorizationPin=c['raw_ref'],leasePin=c['raw_ref'],authorityKeyPin=c['key_ref'],
        issuedAt=c['start'],expiresAt=c['end'])
    assert context_record(c['seal']('valid-context',context),c['profile'],c['scope']) == context
    context['sourceIdentityPin']=write(tmp_path/'other-source.json',{'different':'source'})
    with pytest.raises(RecoveryError,match='LAB_CONTEXT_BINDING_INVALID'):
        context_record(c['seal']('wrong-source-context',context),c['profile'],c['scope'])


def test_lab_unknown_profile_and_untrusted_selection_fail_before_runtime(tmp_path):
    c=originals(tmp_path)
    with pytest.raises(RecoveryError,match='LAB_PROFILE_NOT_INDEPENDENTLY_TRUSTED'):
        admit({'mode':'REHEARSAL','action':'REHEARSAL'},c['policy'],{'schemaVersion':'RecoveryDataTrust/v1'}, {})
    c['profile']['schemaVersion']='RecoveryDataLabProfile/unknown'
    c['policy']['labProfilePin']=write(tmp_path/'profile.json',c['profile'])
    with pytest.raises(RecoveryError,match='LAB_RECORD_INVALID_RECOVERYDATALABPROFILE'):
        copy_protection(c['manifest'],c['policy'])


def test_explicit_launch_context_has_no_default_and_rehashes(monkeypatch,tmp_path):
    monkeypatch.delenv('INTRUOYI_BACKUP_LAB_CONTEXT_PATH',raising=False)
    monkeypatch.delenv('INTRUOYI_BACKUP_LAB_CONTEXT_SHA256',raising=False)
    with pytest.raises(RecoveryError,match='LAB_CURRENT_CONTEXT_SELECTION_REQUIRED'):selected_context()
    ref=write(tmp_path/'launch-context.json',{'localProtocolOnly':True})
    monkeypatch.setenv('INTRUOYI_BACKUP_LAB_CONTEXT_PATH',ref['path'])
    monkeypatch.setenv('INTRUOYI_BACKUP_LAB_CONTEXT_SHA256',ref['sha256'])
    assert selected_context()==ref
    write(ref['path'],{'changed':True})
    with pytest.raises(RecoveryError,match='LAB_CURRENT_CONTEXT_SELECTION_CHANGED'):selected_context()


def test_original_request_dependencies_cannot_embed_selected_context_even_without_json_extension(tmp_path):
    context=write(tmp_path/'selected',{'localProtocolOnly':True})
    template=write(tmp_path/'template.config',{'embeddedContextPin':context})
    with pytest.raises(RecoveryError,match='LAB_CURRENT_CONTEXT_PIN_CYCLE'):
        acyclic_inputs([{'policyPin':template}],context)
    original=write(tmp_path/'stable.config',{'source':'local-protocol'})
    acyclic_inputs([{'policyPin':original}],context)


def test_byte_payload_jsonlines_do_not_become_configuration_graph(tmp_path):
    context=write(tmp_path/'context',{'localProtocolOnly':True})
    payload=tmp_path/'objects.jsonl';payload.write_bytes(b'{"key":"one"}\n{"key":"two"}\n')
    acyclic_inputs([{'payloadRefs':[pin(payload)]}],context)
    with pytest.raises(RecoveryError,match='LAB_CURRENT_CONTEXT_PIN_CYCLE'):
        acyclic_inputs([{'payloadRefs':[context]}],context)


def test_saved_frozen_request_then_signed_context_is_an_acyclic_non_runtime_example(tmp_path):
    c=originals(tmp_path)
    c['profile']['executionHostPin']=write(tmp_path/'local-host-node.json',
        {'schemaVersion':'W04LocalPinGraphNode/v1','kind':'not-an-actual-host'})
    c['profile']['installedClosurePin']=write(tmp_path/'local-install-node.json',
        {'schemaVersion':'W04LocalPinGraphNode/v1','kind':'not-an-installed-runtime'})
    c['policy']['labProfilePin']=write(tmp_path/'profile.json',c['profile'])
    source=write(tmp_path/'stable-source.json',{'schemaVersion':'W04LocalPinGraphNode/v1','kind':'source-template'})
    policy=write(tmp_path/'stable-policy.json',{'schemaVersion':'W04LocalPinGraphNode/v1','kind':'policy-template'})
    grant=write(tmp_path/'local-grant.json',{'schemaVersion':'W04LocalPinGraphNode/v1','kind':'unit-grant','sourcePin':source})
    lease=write(tmp_path/'local-lease.json',{'schemaVersion':'W04LocalPinGraphNode/v1','kind':'unit-lease'})
    request=dict(schemaVersion='backup-restore-operation/v1',operationId='local-pin-graph-only',
        requestId='local-pin-graph-only-request',action='PLAN_REHEARSAL',mode='REHEARSAL',
        selectedPointPin=None,sourceOrTargetRef=source,policyPin=policy,
        authorizationRefs=[grant],leaseRef=lease,inputPins={},deadlineMilliseconds=1000)
    from recovery_engine import validate_record, pinned_json
    schema=pin(Path(__file__).resolve().parents[2]/'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json')
    validate_record(request,'OperationRequest',schema)
    request_pin=write(tmp_path/'original-operation-request.json',request)
    context=dict(schemaVersion='BackupRehearsalAuthorityContext/v1',rehearsalId=REHEARSAL_ID,
        environment='backup-lab',sourceIdentityPin=c['identity'],executionHostPin=c['profile']['executionHostPin'],
        labScopePin=c['scope_pin'],operationRequestPin=request_pin,installedClosurePin=c['profile']['installedClosurePin'],
        authorizationPin=grant,leasePin=lease,authorityKeyPin=c['key_ref'],issuedAt=c['start'],expiresAt=c['end'])
    selected=c['seal']('original-signed-context',context)
    assert context_record(selected,c['profile'],c['scope']) == context
    assert pinned_json(context['operationRequestPin']) == request
    acyclic_inputs([request,c['profile']],selected)
    index=write(tmp_path/'acyclic-example-index.json',dict(schemaVersion='W04LocalPinGraphExample/v1',
        originalRequestPin=request_pin,selectedContextPin=selected,stableSourcePin=source,stablePolicyPin=policy,
        profilePin=c['policy']['labProfilePin'],grantPin=grant,leasePin=lease,
        selectionVariables=['INTRUOYI_BACKUP_LAB_CONTEXT_PATH','INTRUOYI_BACKUP_LAB_CONTEXT_SHA256'],
        executableRuntimeInput=False,repositoryPointCreated=False,actualLabHostProven=False,
        meaning='Local signed byte graph only; PLAN_REHEARSAL/no selected point, not runtime authorization or restore materials.'))
    assert pinned_json(index)['repositoryPointCreated'] is False
