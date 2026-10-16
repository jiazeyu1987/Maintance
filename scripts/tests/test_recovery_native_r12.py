"""R12 semantic unit fixtures only; no native admission, browser or SQL run."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path, PurePosixPath
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
sys.path.insert(0, str(ROOT/'doc/tasks/20261010-recovery-environment-dev/native-lab-continuation-20261012'))
import recovery_native_browser as browser
import recovery_native_process as process
import consume_goview as goview
import recovery_native_launcher as launcher
from recovery_environment_contract import EnvironmentFailure, canonical, decode


@pytest.fixture(autouse=True)
def linux_literal_path_semantics(monkeypatch):
    # These fixtures review a Linux wire on Windows; they never emulate a
    # Linux kernel, permission check, native reader or admitted runtime.
    root = PurePosixPath(browser.LAB_ROOT.as_posix())
    monkeypatch.setattr(browser, 'LAB_ROOT', root)
    monkeypatch.setattr(process, 'LAB_ROOT', root)
    monkeypatch.setattr(launcher, 'LAB_ROOT', root)


def stamp(delta=0):
    return (datetime.now(timezone.utc)+timedelta(seconds=delta)).isoformat().replace('+00:00', 'Z')


def pin(name, raw=b'UNIT_FIXTURE'):
    return dict(path=str(browser.LAB_ROOT)+'/'+name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def measured(uid=2101, gid=2102, authority=False):
    # All numeric identities here are semantic fixtures, never reservations.
    retained = '3' if authority else '0'
    return dict(pid=11, parentPid=1, startTicks=22, uid=uid, gid=gid, realUid=uid, savedUid=uid, filesystemUid=uid,
        realGid=gid, savedGid=gid, filesystemGid=gid, hostId='UNIT_FIXTURE', bootId='UNIT_FIXTURE',
        pidNamespace='pid:[1]', mountNamespace='mnt:[2]', networkNamespace='net:[3]', userNamespace='user:[4]',
        rootDevice=1, rootInode=2, exePin=pin('python'), kernelIdentityOriginalPin=pin('kernel.json'),
        security=dict(capEff=retained, capPrm=retained, capInh='0', capBnd=retained, capAmb='0',
            ambientState='PRESENT', ambientEvidencePin=pin('ambient.json'), noNewPrivs=1,
            getNoNewPrivsEvidencePin=pin('nnp.json'), supplementaryGroups=[], securityOriginalPin=pin('security.json')))


@pytest.mark.parametrize('damage', [None, 'eff', 'prm', 'inh', 'bnd', 'ambient', 'missing-ambient', 'groups', 'nnp',
                                   'uid', 'saved', 'filesystem', 'namespace', 'boolean-uid'])
@pytest.mark.parametrize('authority', [False, True])
def test_selected_security_boundary(damage, authority):
    value = measured(authority=authority)
    if damage in ('eff', 'prm', 'inh', 'bnd'): value['security']['cap'+damage.title()] = '4'
    if damage == 'ambient': value['security']['capAmb'] = '1'
    if damage == 'missing-ambient': value['security']['capAmb'] = None
    if damage == 'groups': value['security']['supplementaryGroups'] = [1]
    if damage == 'nnp': value['security']['noNewPrivs'] = 0
    if damage == 'uid': value['uid'] = 0
    if damage == 'saved': value['savedUid'] = 0
    if damage == 'filesystem': value['filesystemUid'] = 0
    if damage == 'namespace': value['userNamespace'] = 'mnt:[4]'
    if damage == 'boolean-uid': value['uid'] = True
    if damage:
        with pytest.raises(EnvironmentFailure): browser.security_identity(value, 2101, 2102, authority=authority)
    else: browser.security_identity(value, 2101, 2102, authority=authority)


@pytest.mark.parametrize('path', ['/a/../b', '/a/./b', '/a//b', '/a/', '/a\\b', '/a\x00b', 'relative', '//a'])
def test_literal_path_rejects_aliases(path):
    with pytest.raises(EnvironmentFailure): browser.literal_path(path)


def test_legacy_root_proof_is_never_a_browser_proof():
    with pytest.raises(EnvironmentFailure, match='EXPLICIT_VERSION'):
        browser.validate_record(dict(schemaVersion='RepositoryLabNativeRuntimeProof/v1'), 'RepositoryLabBrowserRuntimeProof/v1')


@pytest.mark.parametrize('damage', [None, 'cycle', 'conflict', 'reserved', 'limit'])
def test_protected_graph_is_combined_bounded_and_never_reads_key(damage):
    key = pin('private.key'); root = pin('selection.json'); child = pin('child.json')
    documents = {root['path']: canonical(dict(keyPin=key, childPin=child)), child['path']: b'opaque DATA'}
    calls = []
    def read(ref):
        calls.append(ref['path']); assert ref['path'] != key['path']; return documents[ref['path']]
    roots = [root]
    reserved = [str(browser.LAB_ROOT)+'/future.json']
    if damage == 'cycle': documents[child['path']] = canonical(root)
    if damage == 'conflict': roots.append(dict(child, sha256='f'*64))
    if damage == 'reserved': reserved = [root['path']]
    if damage == 'limit': reserved = [str(browser.LAB_ROOT)+'/future-'+str(i) for i in range(4096)]
    if damage:
        with pytest.raises(EnvironmentFailure): browser.graph_union(roots, read, opaque_paths={key['path']}, data_paths=set(), reserved_outputs=reserved)
    else:
        actual = browser.graph_union(roots, read, opaque_paths={key['path']}, data_paths=set(), reserved_outputs=reserved)
        assert len(actual) == 3 and key['path'] not in calls


def test_browser_resource_json_is_hashed_without_control_graph_interpretation():
    resource = pin('vendor.json'); unrelated = pin('unexpected.json')
    actual = browser.graph_union([resource], lambda p: canonical(dict(unrelatedPin=unrelated)),
                                 opaque_paths=set(), data_paths={resource['path']})
    assert actual == [resource]


@pytest.mark.parametrize('kind,role', [('json','installed-original'), ('yaml','installed-original'), ('java','installed-original'),
                                    ('py',None), ('python','installed-binary'), ('elf','installed-binary'),
                                    ('native','native-tool'), ('resource','native-browser-resource')])
def test_installed_source_dispatch_exact_role_and_proof(monkeypatch, kind, role):
    monkeypatch.setattr(process, 'Path', PurePosixPath)
    calls = []; raw_reads = []
    def verify(ref, trust, proof, **kwargs): calls.append((ref, trust, proof, kwargs))
    monkeypatch.setitem(sys.modules, 'repository_native_runtime', SimpleNamespace(verify_native_file=verify))
    monkeypatch.setattr(process, 'pinned_bytes', lambda p: raw_reads.append(p))
    python, source, elf = pin('python'), pin('source.'+kind), pin('tool')
    executable = elf if kind == 'elf' else python
    manifest = dict(filePins=[source, elf], dependencyPins=[], pythonPin=python,
                    nativeRuntimeTrustPin=pin('trust'), nativeRuntimeProofPin=pin('proof'))
    trust = dict(nativeFilePins=[])
    if kind == 'python': source = python
    if kind == 'elf': source = elf
    if kind in ('native', 'resource'):
        trust['nativeFilePins'] = [dict(pin=source, roles=[role])]
    process.verify_process_source(source, manifest, trust, executable_pin=executable, deadline=123, qualification=True)
    if role is None: assert raw_reads == [source] and not calls
    else: assert calls == [(source, manifest['nativeRuntimeTrustPin'], manifest['nativeRuntimeProofPin'], dict(role=role, deadline=123))]


@pytest.mark.parametrize('damage', ['unselected', 'hash', 'reader-rejects', 'missing-api', 'resource-executable'])
def test_source_verification_refuses_before_spawn(monkeypatch, damage):
    monkeypatch.setattr(process, 'Path', PurePosixPath)
    source, python = pin('control.json'), pin('python')
    manifest = dict(filePins=[source], dependencyPins=[], pythonPin=python,
                    nativeRuntimeTrustPin=pin('trust'), nativeRuntimeProofPin=pin('proof'))
    trust = dict(nativeFilePins=[])
    def verify(*args, **kwargs):
        if damage == 'reader-rejects': raise EnvironmentFailure('SHARED_READER_CUSTODY_REJECTED')
    monkeypatch.setitem(sys.modules, 'repository_native_runtime', SimpleNamespace(**({} if damage == 'missing-api' else {'verify_native_file':verify})))
    selected = deepcopy(source); executable = python
    if damage == 'unselected': selected = pin('unselected.json')
    if damage == 'hash': selected['sha256'] = 'f'*64
    if damage == 'resource-executable':
        executable = source; trust['nativeFilePins'] = [dict(pin=source, roles=['native-browser-resource'])]
    with pytest.raises((EnvironmentFailure, ImportError)):
        process.verify_process_source(selected, manifest, trust, executable_pin=executable, deadline=123, qualification=True)


def sandbox_fixture():
    selection_pin, proof_pin, intent_pin, capability_pin = [pin(n) for n in ('selection','proof','intent','capability')]
    measured_identity = measured(); measured_identity['userNamespace'] = 'user:[8]'
    mapping_pin, kernel_pin, filter_pin, evidence_pin = [pin(n) for n in ('mapping','renderer','filter','sandbox')]
    common = dict(browserIdentitySelectionPin=selection_pin, browserRuntimeProofPin=proof_pin, qualificationIntentPin=intent_pin)
    measured_identity['pidNamespace'] = 'pid:[8]'; measured_identity['networkNamespace'] = 'net:[9]'
    measured_identity['parentPid'] = 33
    lineage_pin = pin('lineage'); at = stamp(-.1)
    mapping = dict(schemaVersion='RepositoryLabBrowserNamespaceMapping/v2', **common, pid=11, startTicks=22,
        hostId='UNIT_FIXTURE', bootId='UNIT_FIXTURE', observedAt=at,
        userNamespace='user:[8]', parentUserNamespace='user:[4]', uidMap=[[0,2101,1]], gidMap=[[0,2102,1]], setgroups='deny')
    kernel = dict(schemaVersion='RepositoryLabBrowserDescendantKernel/v2', **common, identity=measured_identity, ownedLineageOriginalPin=lineage_pin,
        role='STABLE_RENDERER', seccomp=2, seccompFilters=1, ancestorAuthority='NONE', observedAt=at)
    filt = dict(schemaVersion='RepositoryLabBrowserSeccomp/v2', **common, pid=11, startTicks=22,
        hostId='UNIT_FIXTURE', bootId='UNIT_FIXTURE', observedAt=at,
        seccomp=2, seccompFilters=1, originalKernelPin=kernel_pin)
    evidence = dict(schemaVersion='RepositoryLabBrowserSandboxEvidence/v1', rehearsalId=browser.REHEARSAL_ID, **common,
        sandboxCapabilityResultPin=capability_pin, browserPid=33, browserStartTicks=44,
        descendantKernelOriginalPins=[kernel_pin], namespaceMappingOriginalPins=[mapping_pin], seccompFilterOriginalPins=[filter_pin],
        selectedSandbox='USER_NAMESPACE_AND_SECCOMP_BPF', setuidSandboxUsed=False, sandboxDisabled=False, observedAt=stamp())
    lineage = dict(schemaVersion='RepositoryLabBrowserOwnedLineage/v1', **common, hostId='UNIT_FIXTURE', bootId='UNIT_FIXTURE',
        browserPid=33, browserStartTicks=44, supervisorPid=55, supervisorStartTicks=66, observedAt=at, nodes=[
        dict(pid=55,startTicks=66,parentPid=11,parentStartTicks=22),
        dict(pid=33,startTicks=44,parentPid=55,parentStartTicks=66),
        dict(pid=77,startTicks=88,parentPid=33,parentStartTicks=44)])
    measured_identity['pid']=77; measured_identity['startTicks']=88; mapping['pid']=77; mapping['startTicks']=88; filt['pid']=77; filt['startTicks']=88
    security=measured_identity['security']
    security_original=dict(schemaVersion='RepositoryLabBrowserSecurity/v1',pid=77,startTicks=88,measuredAt=at,
        **{k:security[k] for k in ('capEff','capPrm','capInh','capBnd','capAmb','supplementaryGroups','noNewPrivs')})
    records = {mapping_pin['path']:mapping, kernel_pin['path']:kernel, filter_pin['path']:filt,
               lineage_pin['path']:lineage,security['securityOriginalPin']['path']:security_original}
    context = SimpleNamespace(selection_pin=selection_pin, proof_pin=proof_pin, intent_pin=intent_pin,
        selection=dict(browserUid=2101,browserGid=2102), intent=dict(sandboxCapabilityResultPin=capability_pin),
        proof=dict(producerIdentity=measured()), raw=lambda p: canonical(records[p['path']]), signed=lambda p:evidence)
    process_record = dict(childPid=33, childStartTicks=44, supervisorPid=55, supervisorStartTicks=66, startedAt=stamp(-1), finishedAt=stamp(1))
    return context, evidence_pin, process_record, mapping, kernel, filt, evidence


@pytest.mark.parametrize('damage', [None, 'root-map', 'a-map', 'range-map', 'gid-map', 'ancestor', 'eff', 'nnp', 'seccomp',
                                   'no-filter', 'wrong-child', 'wrong-batch', 'disabled', 'setuid', 'outside-time'])
def test_sandbox_evidence_rejects_root_authority_and_missing_kernel_proof(damage):
    c, p, proc, mapping, kernel, filt, evidence = sandbox_fixture()
    if damage == 'root-map': mapping['uidMap'] = [[0,0,1]]
    if damage == 'a-map': mapping['uidMap'] = [[0,3101,1]]
    if damage == 'range-map': mapping['uidMap'] = [[0,2101,2]]
    if damage == 'gid-map': mapping['gidMap'] = [[0,0,1]]
    if damage == 'ancestor': kernel['ancestorAuthority'] = 'ROOT'
    if damage == 'eff': kernel['identity']['security']['capEff'] = '1'
    if damage == 'nnp': kernel['identity']['security']['noNewPrivs'] = 0
    if damage == 'seccomp': kernel['seccomp'] = 0
    if damage == 'no-filter': evidence['seccompFilterOriginalPins'] = []
    if damage == 'wrong-child': evidence['browserStartTicks'] = 45
    if damage == 'wrong-batch': evidence['qualificationIntentPin'] = pin('foreign')
    if damage == 'disabled': evidence['sandboxDisabled'] = True
    if damage == 'setuid': evidence['setuidSandboxUsed'] = True
    if damage == 'outside-time': evidence['observedAt'] = stamp(-10)
    if damage:
        with pytest.raises(EnvironmentFailure): browser.validate_sandbox(c,p,proc)
    else: assert browser.validate_sandbox(c,p,proc) is evidence


@pytest.mark.parametrize('damage', [None,'other-connection','changed-before','changed-after','wrong-sql','text-ddl'])
def test_goview_physical_cursor_and_scope_gate(damage):
    connection = object(); calls = []; contexts = [dict(fenceGeneration=1),dict(fenceGeneration=1)]
    raw = b'UNIT_FIXTURE_SQL_BYTES'
    if damage == 'changed-before': contexts[0] = None
    if damage == 'changed-after': contexts[1] = dict(fenceGeneration=2)
    def guard():
        value = contexts.pop(0)
        if value is None: raise EnvironmentFailure('UNIT_FIXTURE_REVOKED')
        return value
    cursor = SimpleNamespace(connection=object() if damage == 'other-connection' else connection,
        execute=lambda sql,*a,**k: calls.append(sql) or 0)
    scope = SimpleNamespace(connection=connection, guard=guard, deadline=__import__('time').monotonic()+60,
        driver=SimpleNamespace(invoke=lambda target,method,*a,**k:getattr(target,method)(*a,**k)),
        selection=dict(inputPins=dict(sql=pin('sql',raw))))
    gate = goview.PhysicalCursorGate(scope,cursor)
    sql = b'WRONG' if damage == 'wrong-sql' else 'CREATE TABLE UNIT_FIXTURE' if damage == 'text-ddl' else raw
    if damage:
        with pytest.raises(EnvironmentFailure): gate.execute(sql)
        assert calls == ([raw] if damage == 'changed-after' else [])
    else: assert gate.execute(sql) == 0 and calls == [raw]


def test_goview_durable_history_reread_detects_late_mutation():
    sink = goview.DurableGoViewSink(SimpleNamespace())
    expected = dict(schemaVersion='UNIT_FIXTURE')
    sink.pins = [pin('event')]; sink.events = [expected]
    sink.read = lambda p: canonical(expected)
    sink.reread()
    sink.read = lambda p: canonical(dict(schemaVersion='MUTATED'))
    with pytest.raises(EnvironmentFailure,match='HISTORY_CHANGED'): sink.reread()


def test_goview_review_cannot_be_missing_or_a_truthy_boolean():
    s = dict(adapterReviewPin=pin('review'))
    for review in (True, dict(state='ACCEPTED'), dict(schemaVersion='LEGACY_REVIEW')):
        scope = SimpleNamespace(selection=s,signed=lambda p:review)
        with pytest.raises(EnvironmentFailure): goview.reviewed_adapter(scope)


def test_windows_cannot_be_presented_as_native_goview_scope():
    if sys.platform != 'linux':
        with pytest.raises(EnvironmentFailure,match='LINUX_REQUIRED'):
            goview.GoViewScope(pin('selection'),pin('authority'),None,deadline=123)


def test_browser_contract_export_is_exact_root_ratified_contract():
    selected = decode((ROOT/'doc/tasks/20261010-recovery-environment-dev/native-lab-continuation-20261012/r12-selected-private-contract.json').read_bytes())
    original = selected['value']['ratifiedBrowserPrivateContract']
    assert browser.CONTRACT['$defs'] == original['definitions']
    assert browser.CONTRACT['qualificationSchemas'] == original['versionedQualificationSchemas']


def goview_scope_fixture(monkeypatch):
    """Semantic signed-record contents, not issued real releases or resources."""
    s = dict(schemaVersion='W05GoViewConsumerSelection/v1', rehearsalId=browser.REHEARSAL_ID,
        operationId='UNIT_FIXTURE', batchId='UNIT_FIXTURE', executor='UNIT_FIXTURE', tenantId=122,
        schema='UNIT_FIXTURE', serverUuid='UNIT_FIXTURE', containerId='UNIT_FIXTURE', connectionId=1,
        schemaAllocationId='UNIT_FIXTURE', imageTag='UNIT_FIXTURE', imageDigest='sha256:'+'1'*64,
        evidenceRoot=str(browser.LAB_ROOT)+'/goview', issuedAt=stamp(-1), expiresAt=stamp(60))
    for field in ('sourceScopePin','executorInstallationPin','releasePin','ownershipPin','authorizationPin','leasePin','adapterReviewPin'):
        s[field] = pin(field)
    s['inputPins'] = {k:pin(k) for k in ('sql','contract','design','manifest')}
    binding = {k:s[k] for k in goview.BINDING_FIELDS}
    common = dict(binding=binding, issuedAt=stamp(-1), expiresAt=stamp(60))
    records = {}
    def put(name,version,**extra):
        records[pin(name)['path']] = dict(schemaVersion=version,**common,**extra)
    put('releasePin','W05GoViewSQLRelease/v1',action=goview.ACTION,sourceScopePin=s['sourceScopePin'],
        inputPins=s['inputPins'],evidenceRoot=s['evidenceRoot'],adapterReviewPin=s['adapterReviewPin'],
        executorInstallationPin=s['executorInstallationPin'])
    put('ownershipPin','W05GoViewResourceOwnership/v1',state='HELD',owner=s['executor'],newSchema=True,
        tenantBoundaryPin=pin('boundary'),containerIdentityPin=pin('container'))
    put('authorizationPin','W05GoViewSQLAuthorization/v1',action=goview.ACTION,approved=True,
        releasePin=s['releasePin'],ownershipPin=s['ownershipPin'],sourceScopePin=s['sourceScopePin'],inputPins=s['inputPins'])
    put('leasePin','W05GoViewSQLLease/v1',state='HELD',leaseId='UNIT_FIXTURE',fenceGeneration=1,
        exclusiveClaimPin=pin('claim'),releasePin=s['releasePin'],ownershipPin=s['ownershipPin'])
    put('claim','W05GoViewExclusiveClaim/v1',state='HELD',owner=s['executor'],leaseId='UNIT_FIXTURE',fenceGeneration=1)
    put('boundary','W05GoViewTenantBoundary/v1',tenantId=122,schemaAllocationId=s['schemaAllocationId'],isolatedFromProtectedTenants=True)
    put('container','W05GoViewContainerIdentity/v1',containerId=s['containerId'],imageTag=s['imageTag'],imageDigest=s['imageDigest'],
        state='RUNNING',containerOriginalPin=pin('inspect'),imageOriginalPin=pin('image'))
    records[s['sourceScopePin']['path']] = dict(schemaVersion='RepositoryLabScope/v1',rehearsalId=browser.REHEARSAL_ID,
        repositoryId='UNIT_FIXTURE',sourceIdentityPin=pin('source'),host='172.30.30.59',root=str(browser.LAB_ROOT),
        resourcePrefix='brlab-20261012',allowedActions=sorted(launcher.BUSINESS_SCOPE_ACTIONS),expiresAt=stamp(60))
    selection_pin = pin('selection')
    records[selection_pin['path']] = s
    raw = {pin('inspect')['path']:canonical([dict(Id=s['containerId'],Config=dict(Image=s['imageTag']),
        Image='sha256:UNIT_FIXTURE_CONFIG',State=dict(Running=True))]),
        pin('image')['path']:canonical([dict(Id='sha256:UNIT_FIXTURE_CONFIG',RepoDigests=['unit@'+s['imageDigest']])]),
        pin('source')['path']:b'UNIT_FIXTURE_SOURCE'}
    scope = object.__new__(goview.GoViewScope)
    scope.selection=s;scope.selection_pin=selection_pin;scope.binding=binding;scope.deadline=__import__('time').monotonic()+60
    scope.authority_pin=pin('authority')
    scope.initial_context=None;scope.signed=lambda p:deepcopy(records[p['path']]);scope.raw=lambda p:raw[p['path']]
    scope.connection_identity=lambda:None
    monkeypatch.setitem(sys.modules,'repository_native_runtime',SimpleNamespace(verify_native_installation=lambda *a,**k:
        dict(schemaVersion='RepositoryNativeInstallation/v2',filePins=[],dependencyPins=[])))
    return scope,records,raw


@pytest.mark.parametrize('damage',[None,'expired-grant','revoked-grant','wrong-action','released-lease','boolean-fence',
    'zero-fence','claim-fence','claim-owner','tenant','boundary','image','container','input','release-root','source-host'])
def test_goview_authentic_scope_consumption_requires_all_current_material(damage,monkeypatch):
    scope,records,raw=goview_scope_fixture(monkeypatch)
    def item(name):return records[pin(name)['path']]
    if damage=='expired-grant':item('authorizationPin')['expiresAt']=stamp(-1)
    if damage=='revoked-grant':item('authorizationPin')['approved']=False
    if damage=='wrong-action':item('releasePin')['action']='OTHER'
    if damage=='released-lease':item('leasePin')['state']='RELEASED'
    if damage=='boolean-fence':item('leasePin')['fenceGeneration']=True
    if damage=='zero-fence':item('leasePin')['fenceGeneration']=0
    if damage=='claim-fence':item('claim')['fenceGeneration']=2
    if damage=='claim-owner':item('claim')['owner']='OTHER'
    if damage=='tenant':item('boundary')['tenantId']=1
    if damage=='boundary':item('boundary')['isolatedFromProtectedTenants']=False
    if damage=='image':raw[pin('image')['path']]=canonical([dict(Id='WRONG',RepoDigests=[])])
    if damage=='container':item('container')['containerId']='OTHER'
    if damage=='input':item('releasePin')['inputPins']={}
    if damage=='release-root':item('releasePin')['evidenceRoot']='/outside'
    if damage=='source-host':item('sourceScopePin')['host']='172.30.30.57'
    if damage:
        with pytest.raises(EnvironmentFailure):scope.guard()
    else:
        result=scope.guard();assert result['connectionId']==1 and result['fenceGeneration']==1
        assert scope.guard()==result


def test_goview_signed_payload_cannot_use_unselected_authority_or_tampered_bytes():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    import base64
    from recovery_native_observation import wire_canonical
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    sha=hashlib.sha256(public).hexdigest();payload=dict(schemaVersion='UNIT_FIXTURE',fence=1)
    envelope=dict(schemaVersion='RepositorySignedRecord/v1',keySha256=sha,payload=payload,
        signature=base64.b64encode(key.sign(wire_canonical(payload))).decode())
    assert process.authenticate_payload(envelope,public,sha)==payload
    damaged=deepcopy(envelope);damaged['payload']['fence']=2
    with pytest.raises(EnvironmentFailure):process.authenticate_payload(damaged,public,sha)
    with pytest.raises(EnvironmentFailure):process.authenticate_payload(envelope,public,'f'*64)
