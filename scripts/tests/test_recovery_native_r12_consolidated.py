"""Offline typed-chain fixtures only; never native/B permission or SQL proof."""
from copy import deepcopy
from pathlib import Path, PurePosixPath
import os
import stat
import sys
import time
from types import SimpleNamespace

import pytest
from test_recovery_native_r12 import pin, stamp, measured, sandbox_fixture, goview_scope_fixture
import recovery_native_browser as browser
import recovery_native_browser_measurement as measurement
import recovery_native_goview_deadline as deadlines
import consume_goview as goview
import recovery_native_launcher as launcher
from recovery_environment_contract import EnvironmentFailure, canonical, decode


@pytest.fixture(autouse=True)
def literal_linux_wire(monkeypatch):
    monkeypatch.setattr(browser, 'LAB_ROOT', PurePosixPath(browser.LAB_ROOT.as_posix()))
    monkeypatch.setattr(launcher, 'LAB_ROOT', PurePosixPath(launcher.LAB_ROOT.as_posix()))


def full_browser_chain(monkeypatch):
    """Use the actual context constructor and whole predecessor validator.

    Files, signatures and W03 native reader calls are explicit unit adapters.
    No fixture is issued, installed or admitted as a native measurement.
    """
    monkeypatch.setattr(browser.sys, 'platform', 'linux')
    root = str(browser.LAB_ROOT); documents = {}; bodies = {}
    def put(name, value):
        p = pin(name); documents[p['path']] = value; return p
    def role(name, pid, uid, gid, authority=False):
        value = measured(uid, gid, authority); value.update(pid=pid, startTicks=pid*2)
        value['kernelIdentityOriginalPin'] = pin(name+'-kernel')
        s = value['security']; s['securityOriginalPin'] = put(name+'-security', dict(schemaVersion='RepositoryLabBrowserSecurity/v1',
            pid=pid,startTicks=pid*2,measuredAt=stamp(-11),**{k:s[k] for k in
                ('capEff','capPrm','capInh','capBnd','capAmb','supplementaryGroups','noNewPrivs')}))
        s['getNoNewPrivsEvidencePin'] = put(name+'-nnp', dict(schemaVersion='RepositoryLabBrowserNoNewPrivileges/v1',
            pid=pid,startTicks=pid*2,prctl=39,returnValue=1,errno=0))
        s['ambientEvidencePin'] = put(name+'-ambient', dict(schemaVersion='RepositoryLabBrowserAmbientCapability/v1',
            pid=pid,startTicks=pid*2,state='PRESENT',returnValue=0,errno=0,kernelRelease='UNIT_FIXTURE'))
        return value
    b = role('b',11,2101,2102); a = role('a',12,3101,3102,True); a['mountNamespace']='mnt:[5]'
    manager = role('manager',1,0,0); controller_pin=put('controller', manager)
    authority_pin=pin('authority'); install_pin=pin('installation'); selection_pin=pin('selection'); proof_pin=pin('proof')
    sources = [pin(name) for name in ('python','recovery_environment_supervisor.py','producer.py','signer.py','bootstrap.py','helper.py','chrome')]
    sources[-1] = dict(sources[-1],path=browser.ABOUT_BLANK[0])
    scope_pin=put('source-scope',dict(schemaVersion='RepositoryLabScope/v1',rehearsalId=browser.REHEARSAL_ID,
        repositoryId='UNIT_FIXTURE',sourceIdentityPin=pin('source-identity'),host='172.30.30.59',root=root,
        resourcePrefix='brlab-20261012',allowedActions=sorted(launcher.BUSINESS_SCOPE_ACTIONS),expiresAt=stamp(60)))
    selected = dict(schemaVersion='RepositoryLabBrowserIdentitySelection/v1',rehearsalId=browser.REHEARSAL_ID,
        selectionId='UNIT_FIXTURE',hostId='UNIT_FIXTURE',targetId='UNIT_FIXTURE',executorId='UNIT_FIXTURE',sourceScopePin=scope_pin,
        executorInstallationPin=install_pin,controllerIdentityPin=controller_pin,controllerRuntimeProofPin=pin('root-proof'),authorityKeyPin=authority_pin,
        browserUid=2101,browserGid=2102,signerUid=3101,signerGid=3102,bootstrapMode='INDEPENDENT_PRIVILEGED_LAUNCHER_BEFORE_IDENTITY_DROP',
        bootstrapLauncherPin=sources[4],pidNamespaceMode='SHARED_WITH_SELECTED_ROOT_PID1_AND_A',browserRootPath=root+'/b-root',
        signerRootPath=root+'/a-root',workingDirectory=root+'/work',evidenceRoot=root+'/outputs',signerSocketPath=root+'/control/a.sock',
        signedPublicationRoot=root+'/publications',privateKeyPin=pin('private-key'),environment=dict(PATH='/usr/sbin:/usr/bin:/sbin:/bin',LC_ALL='C',
        LANG='C',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',HOME=root+'/work',TMPDIR=root+'/work'),
        sourceAccess=[dict(pin=p,ownerUid=0,ownerGid=0,mode='0555',roles=['installed-binary']) for p in sources],
        directoryAccess=[dict(path=root+'/work',ownerUid=2101,ownerGid=2102,mode='0700',readOnly=False,usage='BROWSER_CWD')],
        browserExecutablePin=sources[-1],capabilityProbeEntryPin=sources[5],capabilityProbeArgv=[sources[0]['path'],sources[5]['path']],
        producerEntryPin=sources[2],signerEntryPin=sources[3],maximumAgeMilliseconds=300000,maximumRecords=16,issuedAt=stamp(-20),expiresAt=stamp(60))
    put('selection',selected)
    trust = dict(schemaVersion='RepositoryLabBrowserRuntimeTrust/v1',rehearsalId=browser.REHEARSAL_ID,runtimeId='UNIT_FIXTURE',runtimeRole='BROWSER_PRODUCER',
        labRoot=root,backingRootPath=root+'/backing',literalRoots=[root],browserIdentitySelectionPin=selection_pin,
        immutableRuntimeArtifactDigest='sha256:'+'1'*64,vendorArtifactPins=[pin('vendor')],installedSourcePins=sources[:-1],
        nativeFilePins=[dict(pin=sources[-1],roles=['native-browser'],vendorArtifactPins=[pin('vendor')])])
    trust_pin=put('trust',trust)
    proof=dict(schemaVersion='RepositoryLabBrowserRuntimeProof/v1',rehearsalId=browser.REHEARSAL_ID,runtimeId='UNIT_FIXTURE',runtimeRole='BROWSER_PRODUCER',
        browserIdentitySelectionPin=selection_pin,nativeRuntimeTrustPin=trust_pin,executorInstallationPin=install_pin,controllerIdentityPin=controller_pin,
        controllerRuntimeProofPin=selected['controllerRuntimeProofPin'],managerIdentity=manager,producerIdentity=b,signerIdentity=a,
        immutableRuntimeArtifactDigest=trust['immutableRuntimeArtifactDigest'],issuedAt=stamp(-20),expiresAt=stamp(60),
        **{k:pin(k) for k in ('readOnlyMountEvidencePin','managerIdentityEvidencePin','nativeLinkageEvidencePin','directoryAccessEvidencePin',
            'completeSourceReadEvidencePin','workerKeyDenialEvidencePin','bootstrapOriginalPin')})
    put('proof',proof)
    common=dict(rehearsalId=browser.REHEARSAL_ID,qualificationId='CAPABILITY_FIXTURE',operationId='CAPABILITY_FIXTURE',phase='NATIVE_BROWSER_CAPABILITY',
        hostId='UNIT_FIXTURE',targetId='UNIT_FIXTURE',executorId='UNIT_FIXTURE',sourceScopePin=scope_pin,installationPin=install_pin,
        browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin)
    grant_pin=put('grant',dict(schemaVersion='RepositoryLabNativeQualificationAuthorization/v2',**common,actions=['BROWSER_NATIVE_CAPABILITY_PROBE'],
        approved=True,notBefore=stamp(-15),expiresAt=stamp(60)))
    lease_pin=put('lease',dict(schemaVersion='RepositoryLabNativeQualificationLease/v2',**common,leaseId='UNIT_FIXTURE',state='HELD',fenceToken=1,
        notBefore=stamp(-15),expiresAt=stamp(60)))
    command=dict(action='BROWSER_NATIVE_CAPABILITY_PROBE',commandId='capability-fixture',argv=selected['capabilityProbeArgv'],cwd=selected['workingDirectory'],sourcePins=sources)
    intent=dict(schemaVersion='RepositoryLabNativeQualificationIntent/v2',**common,authorityKeyPin=authority_pin,authorizationPin=grant_pin,leasePin=lease_pin,
        commandSelections=[command],deadlineMilliseconds=300000,issuedAt=stamp(-15),expiresAt=stamp(60),sandboxCapabilityResultPin=None)
    intent_pin=put('intent',intent)
    participant=put('producer-identity',dict(schemaVersion='RepositoryLabBrowserParticipantIdentity/v1',rehearsalId=browser.REHEARSAL_ID,
        role='BROWSER_PRODUCER',browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin,identity=b,issuedAt=stamp(-20),expiresAt=stamp(60)))
    launch=put('launch',dict(schemaVersion='RepositoryLabNativeQualificationLaunch/v2',rehearsalId=browser.REHEARSAL_ID,allowedCallerPin=controller_pin,
        authorityKeyPin=authority_pin,authorizationPin=grant_pin,leasePin=lease_pin,evidenceRoot=selected['evidenceRoot'],installationPin=install_pin,
        observationSocketPath=root+'/observer.sock',producerEntryPin=sources[2],signerEntryPin=sources[3],qualificationIntentPin=intent_pin,
        browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin,issuedAt=stamp(-15),expiresAt=stamp(60)))
    provision=put('provision',dict(schemaVersion='RepositoryLabNativeQualificationProvision/v2',rehearsalId=browser.REHEARSAL_ID,launchPin=launch,
        maximumAgeMilliseconds=300000,maximumObservations=1,privateKeyPin=selected['privateKeyPin'],producerIdentityPin=participant,
        producerUid=2101,producerGid=2102,browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin,
        **{k:selected[k] for k in ('signerUid','signerGid','signerRootPath','signerSocketPath','workingDirectory','controllerIdentityPin')}))
    manifest=dict(schemaVersion='RepositoryNativeInstallation/v2',nativeRuntimeProofPin=selected['controllerRuntimeProofPin'],pythonPin=sources[0])
    monkeypatch.setitem(sys.modules,'repository_native_runtime',SimpleNamespace(verify_native_installation=lambda *a,**k:manifest,
        verify_browser_runtime=lambda *a,**k:deepcopy(proof)))
    monkeypatch.setattr(launcher,'browser_resource_pins',lambda trust: [])
    class UnitContext(browser.BrowserQualificationContext):
        def signed(self,p):return deepcopy(documents[p['path']])
        def raw(self,p):return canonical(documents[p['path']]) if p['path'] in documents else bodies.get(p['path'],b'UNIT_FIXTURE')
    c=UnitContext(launch,provision,authority_pin,deadline=time.monotonic()+60)
    # A complete accepted capability predecessor, including actual-shaped sole
    # parent wait and all signed guard/source/denial/security original links.
    ac=put('a-identity',dict(schemaVersion='RepositoryLabBrowserParticipantIdentity/v1',rehearsalId=browser.REHEARSAL_ID,
        role='AUTHORITY_A',browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin,identity=a,issuedAt=stamp(-20),expiresAt=stamp(60)))
    bindings=dict(browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin,measuredAt=stamp(-11))
    sr=put('fresh-source',dict(schemaVersion='RepositoryLabBrowserCompleteSourceRead/v1',**bindings,producerIdentity=b,measuredSourcePins=sources))
    dr=put('fresh-directory',dict(schemaVersion='RepositoryLabBrowserDirectoryAccess/v1',**bindings,producerIdentity=b,directoryAccess=selected['directoryAccess']))
    denial=put('fresh-denial',dict(schemaVersion='RepositoryLabBrowserKeyDenial/v1',**bindings,producerIdentity=b,signerIdentity=a,
        probeIdentity=deepcopy(b),actualWaitStatus=0,soleParentPid=1,deniedOpens=[dict(path=p,errno=13) for p in
            (selected['privateKeyPin']['path'],'/proc/12/root'+selected['privateKeyPin']['path'],'/proc/12/mem')]))
    guard=put('fresh-guard',dict(schemaVersion='RepositoryLabBrowserGuardMeasurement/v1',rehearsalId=browser.REHEARSAL_ID,**bindings,
        qualificationIntentPin=intent_pin,authorizationPin=grant_pin,leasePin=lease_pin,controllerIdentity=manager,managerIdentity=manager,
        producerIdentity=b,signerIdentity=a,completeSourceReadEvidencePin=sr,directoryAccessEvidencePin=dr,workerKeyDenialEvidencePin=denial,expiresAt=stamp(60)))
    process=dict(schemaVersion=browser.PROCESS_VERSION,**{k:intent[k] for k in ('rehearsalId','qualificationId','operationId','phase','targetId','executorId')},
        **{k:command[k] for k in ('commandId','argv','cwd','sourcePins')},command=canonical(command['argv']).decode().strip(),
        bootId=b['bootId'],hostId=b['hostId'],**{k:b[k] for k in browser.NS_FIELDS},nativeRuntimeProofPin=proof_pin,
        browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin,producerIdentityPin=participant,authorityIdentityPin=ac,
        supervisorPin=sources[1],pythonPin=sources[0],supervisorPid=55,supervisorStartTicks=66,childPid=77,childStartTicks=88,uid=2101,gid=2102,
        startedAt=stamp(-10),finishedAt=stamp(-5),terminationKind='EXITED',actualExitCode=0,waitStatus=0,descendantState='REAPED',
        stdoutPin=pin('outputs/capability-fixture/stdout'),stderrPin=pin('outputs/capability-fixture/stderr'),resultPin=pin('outputs/capability-fixture/stdout'),
        currentGuardMeasurementPins=[guard],sandboxEvidencePin=None)
    process_pin=put('process-signed',process)
    terminal=put('outputs/capability-fixture/supervisor-terminal.json',dict(supervisorExitCode=0,failureCode=None,stdoutPin=process['stdoutPin'],
        stderrPin=process['stderrPin'],terminal=dict(model='linux-owned-child-subreaper-v1',supervisorPid=55,workerPid=77,unknown=False,
        supervisorIdentity=dict(startTicks=66,bootId=b['bootId'],namespaces={name:b[field] for field,name in browser.NS_FIELDS.items()}),
        dispatch=dict(argv=command['argv'],cwd=command['cwd'],uid=2101,gid=2102),children=[dict(pid=77,startTicks=88,uid=2101,gid=2102,
        actualWaitStatus=0,reaped=True)],actualExitCode=0,treeTerminated=True)))
    probes=[]
    for name in ('user-namespace','uid-map','gid-map','pid-namespace','network-namespace','seccomp-bpf','no-new-privileges'):
        item=dict(name=name,state='PASSED',returnValue=0,errno=0)
        item['originalPin']=put('probe-'+name,dict(**item,browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin));probes.append(item)
    cap=put('cap-result',dict(schemaVersion='RepositoryLabBrowserSandboxCapabilityResult/v1',rehearsalId=browser.REHEARSAL_ID,
        browserIdentitySelectionPin=selection_pin,browserRuntimeProofPin=proof_pin,qualificationIntentPin=intent_pin,processResultPin=process_pin,
        kernelRelease='UNIT_FIXTURE',kernelConfigurationEvidencePin=pin('kernel-config'),containerSecurityPolicyEvidencePin=pin('security-policy'),
        probes=probes,issuedAt=stamp(-1),expiresAt=stamp(60)))
    monkeypatch.setattr(browser,'read_producer_original',lambda context,p:context.raw(p))
    monkeypatch.setattr(browser,'producer_original_pin',lambda context,path: terminal if path==terminal['path'] else pytest.fail('wrong terminal path'))
    return c,documents,cap,process


@pytest.mark.parametrize('damage',[None,'revoked','released','fence','host','target','executor','scope','source','argv','stream','terminal',
                                   'a-role','guard-batch','guard-time','missing-guard','wait','authority-drift'])
def test_complete_typed_capability_predecessor(monkeypatch,damage):
    c,docs,cap,p=full_browser_chain(monkeypatch)
    def rec(name):return docs[pin(name)['path']]
    if damage=='revoked':rec('grant')['approved']=False
    if damage=='released':rec('lease')['state']='RELEASED'
    if damage=='fence':rec('lease')['fenceToken']=True
    if damage in ('host','target','executor'):rec('intent')[damage+'Id']='OTHER'
    if damage=='scope':rec('intent')['sourceScopePin']=pin('foreign')
    if damage=='source':p['sourcePins']=p['sourcePins'][:-1]
    if damage=='argv':p['argv']=['wrong']
    if damage=='stream':p['stdoutPin']=pin('foreign')
    if damage=='terminal':rec('outputs/capability-fixture/supervisor-terminal.json')['terminal']['children'][0]['actualWaitStatus']=256
    if damage=='a-role':rec('a-identity')['role']='BROWSER_PRODUCER'
    if damage=='guard-batch':rec('fresh-guard')['qualificationIntentPin']=pin('foreign')
    if damage=='guard-time':rec('fresh-source')['measuredAt']=stamp(-100)
    if damage=='missing-guard':p['currentGuardMeasurementPins']=[]
    if damage=='wait':p['waitStatus']=256
    if damage=='authority-drift':
        raw=c.raw
        def mutate(ref):
            if ref==rec('cap-result')['containerSecurityPolicyEvidencePin']:rec('grant')['approved']=False
            return raw(ref)
        c.raw=mutate
    if damage:
        with pytest.raises(EnvironmentFailure):browser.validate_capability(c,cap)
    else:
        assert browser.validate_capability(c,cap)['processResultPin']==pin('process-signed')
        assert 'issuedAt' not in c.provision
        first=c.reserved_paths();c.command=dict(c.command,commandId='about-fixture');second=c.reserved_paths()
        assert set(first).isdisjoint(second)


def test_full_about_constructor_accepts_distinct_prior_complete_capability(monkeypatch):
    c,docs,cap,process=full_browser_chain(monkeypatch)
    def put(name,value):docs[pin(name)['path']]=value;return pin(name)
    intent=deepcopy(c.intent);intent.update(phase='NATIVE_BROWSER_QUALIFICATION',qualificationId='ABOUT_FIXTURE',operationId='ABOUT_FIXTURE',
        issuedAt=stamp(-.5),sandboxCapabilityResultPin=cap)
    for name,source,version in (('about-grant','grant','RepositoryLabNativeQualificationAuthorization/v2'),
                                ('about-lease','lease','RepositoryLabNativeQualificationLease/v2')):
        record=deepcopy(docs[pin(source)['path']]);record.update(phase=intent['phase'],qualificationId=intent['qualificationId'],
            operationId=intent['operationId'],notBefore=intent['issuedAt'])
        if source=='grant':record['actions']=['BROWSER_ABOUT_BLANK']
        intent['authorizationPin' if source=='grant' else 'leasePin']=put(name,record)
    intent['commandSelections']=[dict(c.command,action='BROWSER_ABOUT_BLANK',commandId='about-fixture',argv=browser.ABOUT_BLANK)]
    intent_pin=put('about-intent',intent)
    launch=dict(c.launch,qualificationIntentPin=intent_pin,authorizationPin=intent['authorizationPin'],leasePin=intent['leasePin'],issuedAt=intent['issuedAt'])
    launch_pin=put('about-launch',launch);provision_pin=put('about-provision',dict(c.provision,launchPin=launch_pin))
    about=type(c)(launch_pin,provision_pin,c.authority_pin,deadline=time.monotonic()+60)
    assert about.phase=='NATIVE_BROWSER_QUALIFICATION'
    assert set(about.reserved_paths()).isdisjoint(c.reserved_paths())


@pytest.mark.parametrize('damage',['host','boot','pid-ns','net-ns','stale-kernel','stale-map','stale-filter','foreign-lineage',
                                   'foreign-link','legacy-map','legacy-kernel','legacy-filter'])
def test_renderer_every_raw_original_is_bound(damage):
    c,ref,p,m,k,f,e=sandbox_fixture()
    if damage=='host':k['identity']['hostId']='OTHER'
    if damage=='boot':m['bootId']='OTHER'
    if damage=='pid-ns':k['identity']['pidNamespace']=c.proof['producerIdentity']['pidNamespace']
    if damage=='net-ns':k['identity']['networkNamespace']=c.proof['producerIdentity']['networkNamespace']
    if damage=='stale-kernel':k['observedAt']=stamp(-100)
    if damage=='stale-map':m['observedAt']=stamp(-100)
    if damage=='stale-filter':f['observedAt']=stamp(-100)
    if damage=='foreign-lineage':
        raw=c.raw
        def change(p):
            obj=decode(raw(p))
            if obj.get('schemaVersion')=='RepositoryLabBrowserOwnedLineage/v1':obj['nodes'][-1]['parentPid']=999
            return canonical(obj)
        c.raw=change
    if damage=='foreign-link':f['originalKernelPin']=pin('foreign-kernel')
    if damage=='legacy-map':m['schemaVersion']='RepositoryLabBrowserNamespaceMapping/v1'
    if damage=='legacy-kernel':k['schemaVersion']='RepositoryLabBrowserDescendantKernel/v1'
    if damage=='legacy-filter':f['schemaVersion']='RepositoryLabBrowserSeccomp/v1'
    with pytest.raises(EnvironmentFailure):browser.validate_sandbox(c,ref,p)


@pytest.mark.parametrize('stage',['identity','source'])
@pytest.mark.parametrize('damage',['revoke','release','fence','expire','deadline'])
def test_goview_callback_changes_are_read_after_callbacks(monkeypatch,stage,damage):
    scope,docs,raw=goview_scope_fixture(monkeypatch)
    def drift():
        if damage=='revoke':docs[pin('authorizationPin')['path']]['approved']=False
        if damage=='release':docs[pin('leasePin')['path']]['state']='RELEASED'
        if damage=='fence':docs[pin('leasePin')['path']]['fenceGeneration']=2
        if damage=='expire':docs[pin('authorizationPin')['path']]['expiresAt']=stamp(-1)
        if damage=='deadline':scope.deadline=time.monotonic()-1
    if stage=='identity':scope.connection_identity=drift
    else:
        old=scope.raw
        def read(p):
            result=old(p)
            if p==pin('source'):drift()
            return result
        scope.raw=read
    with pytest.raises(EnvironmentFailure):scope.guard()


def test_goview_expiry_in_guard_prevents_native_execute():
    calls=[];scope=SimpleNamespace(connection=object(),deadline=time.monotonic()+60,
        selection=dict(inputPins=dict(sql=pin('sql',b'UNIT_FIXTURE'))),driver=SimpleNamespace(invoke=lambda *a:calls.append('dispatch')))
    def guard():scope.deadline=time.monotonic()-1;return {'fence':1}
    scope.guard=guard; cursor=SimpleNamespace(connection=scope.connection)
    with pytest.raises(EnvironmentFailure,match='DEADLINE'):goview.PhysicalCursorGate(scope,cursor).execute(b'UNIT_FIXTURE')
    assert calls==[]


def test_driver_requires_real_owned_boundary_before_any_sql():
    scope=SimpleNamespace(selection=dict(driverClass=deadlines.DRIVER_CLASS,cursorClass=deadlines.CURSOR_CLASS),connection=object(),deadline=time.monotonic()+60)
    with pytest.raises(EnvironmentFailure,match='OWNED_TOTAL'):deadlines.SelectedPyMySQLDeadline(scope)


@pytest.mark.parametrize('mode,gid',[(0o444,2102),(0o440,0),(0o600,2102),(0o440,2102)])
def test_publication_uses_dedicated_reader_only(monkeypatch,mode,gid):
    c=SimpleNamespace(selection=dict(signedPublicationRoot=str(browser.LAB_ROOT)+'/publications',browserGid=2102,signerUid=3101),deadline=time.monotonic()+60)
    monkeypatch.setattr(browser.os,'open',lambda *a,**k:5);monkeypatch.setattr(browser.os,'close',lambda fd:None)
    monkeypatch.setattr(browser.os,'fstat',lambda fd:SimpleNamespace(st_uid=0,st_gid=2102,st_mode=stat.S_IFDIR|0o750))
    monkeypatch.setattr(browser.os,'geteuid',lambda:2101,raising=False)
    monkeypatch.setattr(browser.os,'O_DIRECTORY',0,raising=False);monkeypatch.setattr(browser.os,'O_NOFOLLOW',0,raising=False)
    def read(p,**kw):
        assert kw['modes']==(0o440,) and kw['owner_gid']==2102 and kw['readonly'] is True
        if mode not in kw['modes'] or gid!=kw['owner_gid']:raise EnvironmentFailure('UNIT_CUSTODY')
        return b'UNIT_FIXTURE'
    monkeypatch.setattr(browser,'descriptor_read',read)
    p=pin('publications/a.signed.json')
    if (mode,gid)==(0o440,2102):assert browser.read_signed_publication(c,p)==b'UNIT_FIXTURE'
    else:
        with pytest.raises(EnvironmentFailure):browser.read_signed_publication(c,p)


def test_native_providers_refuse_windows_before_observation_or_probe():
    if sys.platform=='linux':pytest.skip('Windows refusal check')
    with pytest.raises(EnvironmentFailure,match='NATIVE_OBSERVER'):measurement.Measurements(pin('s'),pin('p'),pin('i'),pin('a'),time.monotonic()+60)
