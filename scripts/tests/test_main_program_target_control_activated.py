"""Pure activation proof contracts; synthetic records do not prove installation."""
from copy import deepcopy
import hashlib
import importlib
import io
import inspect
import json
from pathlib import Path
import sys
import tarfile

import pytest

TASK=Path(__file__).resolve().parents[2]/'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
sys.path.insert(0,str(TASK))
FILE=TASK/'main_program_target_control_activated.py'
from test_main_program_target_control_candidate import inputs as candidate_inputs, repin, graph_repin
import main_program_target_control_candidate as binding
import main_program_control_runtime as runtime


def subject():
    assert FILE.exists(),'MISSING_ACTIVATED_TARGET_OVERLAY_LOADER'
    return importlib.import_module('main_program_target_control_activated')


def canonical(value):return runtime.canonical(value)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def pin(path,raw):return dict(path=path,bytes=len(raw),sha256=digest(raw))
def docpin(path,value):return pin(path,canonical(value))


def package(files):
    hashes={name:digest(raw) for name,raw in files.items()}
    manifest=canonical(dict(variant='standard',fileVerification=True,payloadContentVerification=True,
        files=hashes,packageSha256=digest(canonical(hashes))))
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w:gz') as tar:
        for name,raw in sorted(dict(files,**{'package.json':manifest}).items()):
            item=tarfile.TarInfo(name);item.size=len(raw);tar.addfile(item,io.BytesIO(raw))
    return stream.getvalue(),manifest


def seal(wrapper,*,self_path=False):
    result=wrapper['result'];result.pop('activationReceiptPin',None)
    path=result['createdPaths'][0]+'/result-activate.private.json'
    result['activationReceiptPin']=docpin(path,result)
    if self_path:result['createdPaths'].append(path)
    return wrapper


@pytest.fixture
def proofs():
    original=candidate_inputs.__wrapped__();oldraw,oldmanifest=package(original['previous_package_files'])
    newraw,newmanifest=package(original['package_files']);oldbuild=deepcopy(original['old_build'])
    oldbuild['packageSha256']=digest(oldraw);newbuild=deepcopy(original['new_build'])
    newbuild['packages'][0].update(bytes=len(newraw),sha256=digest(newraw))
    buildpin=dict(file='target-build.json',bytes=100,sha256='1'*64)
    source=dict(status='ACTIVATED',installationVerified=True,runtimeVerified=False,
        selectionPin=dict(file='source-selection.json',bytes=10,sha256='2'*64),inputPins=[],
        effectiveControllersByHost={},controllerBuildBindings={},sourceControl={'retained':'source-control'},
        sourceOwner={'retained':'source-owner'},sourceEpoch={'retained':'source-epoch'},activationReceiptPins=[])
    generation=dict(build=oldbuild,controllersByHost={},selections={},custodyByHost={},targets={},
        privatePlan=dict(documentsByHost={}),sourceBaseline={})
    source['baseInstallation']=dict(generation=generation,spugRuntime={'retained':'spug5651efc'},inputPins=[])
    activations={}
    for suffix in ('57','58','59'):
        def host_values(value):
            if type(value) is dict:return {host_values(a):host_values(b) for a,b in value.items()}
            if type(value) is list:return [host_values(a) for a in value]
            if type(value) is str and (value=='58' or 'target-58' in value or '.58' in value or '/58' in value):
                return value.replace('58',suffix)
            return deepcopy(value)
        k=host_values(original);graph_repin(k)
        k['preservation']['originalCredentialPins'][-1]=pin('/original/mount.credentials',b'original-smb')
        k.update(old_build=deepcopy(oldbuild),new_build=deepcopy(newbuild))
        old=k['current_controller'];old.update(pid=int(suffix)*10,dropinPin=pin(
            '/etc/systemd/system/'+old['service']+'.d/old.conf',b'old dropin'),buildPin={'retained':'old-build'})
        old['packageSha256']=digest(oldraw)
        k['control']['pythonPin']=pin('/usr/bin/python3',b'python')
        repin(k)
        for value in k['control']['restoreConfigurations'].values():value[k['current_controller']['targetConfigRef']]=old['ownerConfigurationPin']
        repin(k)
        candidate=binding.build_target_control_candidate(**k)
        target=candidate['targetConfigRef'];oldrow=dict(deepcopy(old),environmentMode='CONFIG_EXACT')
        rows=[oldrow]
        if suffix=='57':rows.insert(0,dict(role='source',service='source.service',pid=1,engine='/source6968b58',
            sourceCommit='d'*40,buildPin={'retained':'source-build'},environmentMode='CONFIG_EXACT'))
        unit=dict(directory='/etc/systemd/system/'+old['service']+'.d',service=old['service'],
            dropinPins=[old['dropinPin']],existingNames=['old.conf'],unitPin=pin('/etc/systemd/system/'+old['service'],b'unit'))
        basecurrent=dict(host=old['host'],suffix=suffix,targetConfigRef=target,controllers=[])
        spec=dict(current=dict(basecurrent,controllers=deepcopy(rows)),unit=dict(controllers=[unit]),
            environmentBaseline=None,targetConfigRef=target,previousCustody=None,oldReceiptPin=None,
            originalInventory=None,historyPins=[],sourceEvidencePins=[],newDocuments=[],
            retainedDocuments=[old['ownerConfigurationPin'],old['controlConfigurationPin'],
                k['preservation']['originalCredentialPins'][-1],*[r['pin'] for r in candidate['newDocuments']]])
        generation['controllersByHost'][suffix]=[deepcopy(old)] if suffix!='57' else [deepcopy(rows[0]),deepcopy(old)]
        generation['selections'][suffix]=basecurrent;generation['targets'][suffix]=target
        generation['privatePlan']['documentsByHost'][suffix]=[
            dict(pin=old['ownerConfigurationPin'],value=k['owner']),dict(pin=old['controlConfigurationPin'],value=k['control'])]
        source['effectiveControllersByHost'][suffix]=[deepcopy(row) for row in generation['controllersByHost'][suffix]]
        source['controllerBuildBindings'][suffix]={row['role']:dict(buildPin=row['buildPin'],sourceCommit=row['sourceCommit']) for row in rows}
        newrow=deepcopy(oldrow);newrow.update(pid=old['pid']+1,engine=candidate['controller']['engine'],
            controlConfigurationPin=candidate['controller']['controlPin'],ownerConfigurationPin=candidate['controller']['ownerPin'],
            sourceCommit=newbuild['targetCommit'],fileCount=153,fileManifestSha256=candidate['package']['fileManifestSha256'])
        dropin=pin(unit['directory']+'/zz-new.conf',b'new dropin');newrow['dropinPin']=dropin
        dependency='spug-main-preservation-view-'+suffix+'-20261111-r1.service'
        def observed(row,control):
            args=[control['pythonPin']['path'],'-B',row['engine']+'/control_entry.py','serve','--config-pin',canonical(row['controlConfigurationPin']).decode()]
            return dict(service=row['service'],pid=row['pid'],argvSha256=digest(('\0'.join(args)+'\0').encode()),
                executable=control['pythonPin']['path'],environmentVerification=dict(mode='CONFIG_EXACT',environmentSha256='e'*64),
                properties=dict(MainPID=str(row['pid']),FragmentPath=unit['unitPin']['path'],DropInPaths=old['dropinPin']['path'],
                    Requires='original.service',After='original.service',LimitNOFILE='65536',ActiveState='active',SubState='running'))
        control=next(r['value'] for r in candidate['newDocuments'] if r['pin']==candidate['controller']['controlPin'])
        a=observed(oldrow,k['control']);b=observed(newrow,control)
        b['properties']['DropInPaths']+=' '+dropin['path']
        for key in ('Requires','After'):b['properties'][key]+=' '+dependency
        oldpackage=pin(old['engine']+'/package.json',oldmanifest);newpackage=pin(newrow['engine']+'/package.json',newmanifest)
        before=dict(controllers=[a],packagePins=[oldpackage],containers={'retained-container':{'state':'running'}},
            fstabPin=pin('/etc/fstab',b'original'),mountinfoSha256='f'*64,historyGuard={'ActiveState':'active','SubState':'exited'},
            previousCustodyObservation=None,originalInventoryObservation=None,documentsCreated=True)
        after=deepcopy(before);after['controllers']=[b];after['packagePins']=[newpackage]
        if suffix=='57':
            peer=dict(service='source.service',pid=1,retained='source-runtime')
            before['controllers'].insert(0,deepcopy(peer));after['controllers'].insert(0,deepcopy(peer))
            before['packagePins'].insert(0,pin('/source6968b58/package.json',b'source'))
            after['packagePins'].insert(0,pin('/source6968b58/package.json',b'source'))
        transition=dict(schemaVersion='MainProgramTargetRuntimeTransition/v1',status='TARGET_SUCCESSOR_RUNTIME_VERIFIED',
            host=old['host'],targetConfigRef=target,service=old['service'],successorController=newrow,before=before,after=after,
            retainedEnvironmentBaseline=None,retainedRowEnvironment={},retainedHistoryUsesOriginalSpec=True,
            serverWrites=False,installationReceiptCreated=False,restoreDispatched=False)
        epochpolicy=k['owner']['targetProgramPolicies'][target]['backupEpochPolicy']
        native=dict(actualConfigurationReadPassed=True,archiveViewsPreflightVerified=True,
            directlyAdmittedSources=['intruoyi-57-safe-20261024-v1','intruoyi-59-safe-20261024-v1','intruoyi-PROD57-20261019'],
            epochPolicy=epochpolicy,epoch=dict(schemaVersion='SourceBackupEpoch/v1',state='READY',operationId=None,
                epochId='a'*64,policySha256=digest(canonical(epochpolicy)),eventPin=pin(epochpolicy['root']+'/00000000000000000000.json',b'event')))
        api=dict(observedAt='2026-11-11T00:00:00+00:00',applications=[dict(applicationId=s,sourceConfigRef=s,
            engineSelectionRef='retained-engine',freshTargetConfigRefs=[target],fullReady=i==0,
            fullErrorCode=None if i==0 else 'SOURCE_RESTORE_ONLY',historyErrorCode=None,parentChainRefs=[],recoveryPointRefs=['point'])
            for i,s in enumerate(native['directlyAdmittedSources'])])
        result=dict(schemaVersion='MainProgramTargetControlActivation/v1',status='PASS',host=old['host'],role='target',
            stage='complete',targetConfigRef=target,sourceCommit=newbuild['targetCommit'],observedAt='2026-11-11T00:00:00+00:00',
            transition=transition,originalRuntimeSpec=spec,candidate=candidate,currentController=newrow,
            addedDependencies={'Requires':[dependency],'After':[dependency]},nativeBefore=native,nativeAfter=deepcopy(native),
            apiSelection=api,originalApi=deepcopy(api),dropinPin=dropin,createdPaths=[
                '/control/control-activation-main-target-ccccccc-r1',
                '/control/control-activation-main-target-ccccccc-r1/before.private.json',dropin['path']])
        for key in ('activationCompleted','apiVerified','controlServiceRestarted','oldReceiptPreserved','businessContainersUnchanged',
                    'fstabAndMountsUnchanged','physicalLockVerified','actualImportsVerified'):result[key]=True
        for key in ('backupDispatched','restoreDispatched','businessMutationDispatched','oldReceiptRotated'):result[key]=False
        wrapper=dict(status='PASS',host=suffix,mode='ACTIVATE',observedAt='2026-11-11T00:00:00+00:00',elapsedSeconds=1,
            scriptPin=pin('/private/activation-'+suffix+'.py',b'actual-script'),result=result)
        activations[suffix]=seal(wrapper)
    return dict(source=source,activations=activations,build=newbuild,build_pin=buildpin,
        package_raw=newraw,previous_package_raw=oldraw)


def project(c):
    return subject().verify_target_activations(c['source'],c['activations'],build=c['build'],build_pin=c['build_pin'],
        package_raw=c['package_raw'],previous_package_raw=c['previous_package_raw'])


def test_complete_three_target_proofs_overlay_only_targets_and_preserve_originals(proofs):
    original=deepcopy(proofs);result=project(proofs)
    assert result['status']=='ACTIVATED' and result['installationVerified'] is True and result['runtimeVerified'] is False
    assert result['sourceInstallation']==proofs['source'] and proofs==original
    assert result['effectiveControllersByHost']['57'][0]==proofs['source']['effectiveControllersByHost']['57'][0]
    assert result['baseInstallation']==proofs['source']['baseInstallation']
    assert len(result['activationReceiptPins'])==3
    for host,wrapper in proofs['activations'].items():
        assert result['effectiveControllersByHost'][host][-1]==wrapper['result']['currentController']
        assert result['controllerBuildBindings'][host]['target']['buildPin']==proofs['build_pin']


@pytest.mark.parametrize('self_path',[False,True])
def test_both_explicit_original_receipt_publication_phases_close(proofs,self_path):
    w=proofs['activations']['58'];seal(w,self_path=self_path)
    assert project(proofs)['installationVerified'] is True


@pytest.mark.parametrize('problem',['wrong-tail','middle','two-items','other-field'])
def test_receipt_publication_never_ignores_unknown_differences(proofs,problem):
    w=proofs['activations']['58'];seal(w,self_path=True);r=w['result']
    if problem=='wrong-tail':r['createdPaths'][-1]+='-wrong'
    elif problem=='middle':r['createdPaths'].append('/unknown')
    elif problem=='two-items':r['createdPaths'].append(r['createdPaths'][-1])
    else:r['physicalLockVerified']=False
    with pytest.raises(ValueError):project(proofs)


@pytest.mark.parametrize('problem',['missing-host','extra-host','not-activated','wrapper-failed','prepare-only','host','role','stage',
    'old-receipt-rotated','imports','lock','business','new-commit','candidate-old-owner','candidate-source-trust','candidate-doc-pin',
    'new-package','old-package','native-mismatch','native-not-ready','native-source','native-policy','api-source','api-target','api-history',
    'new-pid','new-controller','new-argv','new-dropin','old-binding','source-controller','containers','mounts','custody','unknown-field'])
def test_any_incomplete_or_changed_binding_fails_closed(proofs,problem):
    c=proofs;w=c['activations']['58'];r=w['result'];t=r['transition']
    if problem=='missing-host':c['activations'].pop('59')
    elif problem=='extra-host':c['activations']['60']=deepcopy(w)
    elif problem=='not-activated':c['source']['installationVerified']=False
    elif problem=='wrapper-failed':w['status']='FAILED'
    elif problem=='prepare-only':w['mode']='PREPARE'
    elif problem=='host':r['host']='172.30.30.59'
    elif problem=='role':r['role']='source'
    elif problem=='stage':r['stage']='restart-selected-control'
    elif problem=='old-receipt-rotated':r['oldReceiptRotated']=True
    elif problem=='imports':r['actualImportsVerified']=False
    elif problem=='lock':r['physicalLockVerified']=False
    elif problem=='business':r['businessMutationDispatched']=True
    elif problem=='new-commit':r['sourceCommit']='a'*40
    elif problem=='candidate-old-owner':r['candidate']['controller']['previousOwnerPin']['sha256']='0'*64
    elif problem=='candidate-source-trust':r['candidate']['newDocuments'][-2]['value']['sources']['existing-source']['identity']='changed'
    elif problem=='candidate-doc-pin':r['candidate']['newDocuments'][0]['pin']['sha256']='0'*64
    elif problem=='new-package':c['package_raw']+=b'changed'
    elif problem=='old-package':c['previous_package_raw']+=b'changed'
    elif problem=='native-mismatch':r['nativeAfter']['epoch']['epochId']='0'*64
    elif problem=='native-not-ready':r['nativeBefore']['epoch']['state']='INVALID';r['nativeAfter']=deepcopy(r['nativeBefore'])
    elif problem=='native-source':r['nativeBefore']['directlyAdmittedSources'].pop();r['nativeAfter']=deepcopy(r['nativeBefore'])
    elif problem=='native-policy':r['nativeBefore']['epochPolicy']['databaseUuid']='wrong';r['nativeAfter']=deepcopy(r['nativeBefore'])
    elif problem=='api-source':r['apiSelection']['applications'].pop()
    elif problem=='api-target':r['apiSelection']['applications'][1]['freshTargetConfigRefs']=[]
    elif problem=='api-history':r['apiSelection']['applications'][1]['historyErrorCode']='FAILED'
    elif problem=='new-pid':r['currentController']['pid']=r['originalRuntimeSpec']['current']['controllers'][-1]['pid']
    elif problem=='new-controller':r['currentController']['engine']+='/wrong'
    elif problem=='new-argv':t['after']['controllers'][-1]['argvSha256']='0'*64
    elif problem=='new-dropin':t['after']['controllers'][-1]['properties']['DropInPaths']+=' /unknown.conf'
    elif problem=='old-binding':r['originalRuntimeSpec']['current']['controllers'][-1]['ownerConfigurationPin']['sha256']='0'*64
    elif problem=='source-controller':c['activations']['57']['result']['transition']['after']['controllers'][0]['pid']=8;seal(c['activations']['57'])
    elif problem=='containers':t['after']['containers']['retained-container']['state']='changed'
    elif problem=='mounts':t['after']['mountinfoSha256']='0'*64
    elif problem=='custody':r['originalRuntimeSpec']['oldReceiptPin']=pin('/other',b'wrong')
    else:r['unknownUnapproved']=True
    seal(w)
    with pytest.raises(ValueError):project(c)


def test_unknown_retained_source_and_spug_fields_survive_projection(proofs):
    proofs['source']['futureSourceContract']={'keep':'all'}
    proofs['source']['baseInstallation']['spugRuntime']['future']=['keep']
    result=project(proofs)
    assert result['sourceInstallation']['futureSourceContract']=={'keep':'all'}
    assert result['baseInstallation']['spugRuntime']['future']==['keep']


def continuation(c):
    w=c['activations']['59'];r=w['result'];before=deepcopy(r['transition']['before']);priorroot=r['createdPaths'][0]
    failed={k:deepcopy(r[k]) for k in ('schemaVersion','host','targetConfigRef','sourceCommit','role','observedAt',
        'backupDispatched','restoreDispatched','businessMutationDispatched','oldReceiptRotated')}
    failed.update(status='FAILED',stage='restart-selected-control',errorType='CalledProcessError',
        errorCode='SYSTEMCTL_MAINPID_FAILED',createdPaths=deepcopy(r['createdPaths']))
    failure=deepcopy(w);failure.update(status='FAIL',result=failed);seal(failure,self_path=True)
    prepared={k:deepcopy(failed[k]) for k in ('schemaVersion','host','targetConfigRef','sourceCommit','role','observedAt',
        'backupDispatched','restoreDispatched','businessMutationDispatched','oldReceiptRotated')}
    prepared.update(status='TARGET_ACTIVATION_PREPARED',stage='prepared',before=before,nativeGate=deepcopy(r['nativeBefore']),
        originalApi=deepcopy(r['originalApi']),proposedDropinPin=deepcopy(r['dropinPin']),serverWrites=False,
        controlServiceRestarted=False,createdPaths=[])
    prepare=deepcopy(w);prepare.update(mode='PREPARE',result=prepared)
    w['continuationLocalFailurePin']=docpin('/private/failure.json',failure)
    w['continuationLocalPreparePin']=docpin('/private/prepare.json',prepare)
    r.update(continuationFailurePin=failed['activationReceiptPin'],continuationBeforePin=docpin(priorroot+'/before.private.json',before),
        controlServiceRestartedInPriorAttempt=True,createdPaths=[priorroot[:-1]+'2'])
    seal(w)
    return dict(failure=failure,prepare=prepare)


def test_explicit_continuation_preserves_actual_failed_attempt_and_prepared_before(proofs):
    context=continuation(proofs)
    result=subject().verify_target_activations(proofs['source'],proofs['activations'],build=proofs['build'],build_pin=proofs['build_pin'],
        package_raw=proofs['package_raw'],previous_package_raw=proofs['previous_package_raw'],continuations={'59':context})
    assert result['installationVerified'] is True and context['failure']['result']['status']=='FAILED'


@pytest.mark.parametrize('problem',['missing-context','failed-pass','failed-receipt','before-pin','before-value',
    'original-api','native','dropin','scope','prior-restart','prepare-writes','local-pin-missing'])
def test_continuation_requires_each_original_failure_and_before_binding(proofs,problem):
    context=continuation(proofs);w=proofs['activations']['59'];r=w['result']
    if problem=='missing-context':context=None
    elif problem=='failed-pass':context['failure']['result']['status']='PASS';seal(context['failure'])
    elif problem=='failed-receipt':context['failure']['result']['activationReceiptPin']['sha256']='0'*64
    elif problem=='before-pin':r['continuationBeforePin']['sha256']='0'*64
    elif problem=='before-value':context['prepare']['result']['before']['mountinfoSha256']='0'*64
    elif problem=='original-api':context['prepare']['result']['originalApi']['applications'][0]['freshTargetConfigRefs']=[]
    elif problem=='native':context['prepare']['result']['nativeGate']['epoch']['epochId']='0'*64
    elif problem=='dropin':context['prepare']['result']['proposedDropinPin']['sha256']='0'*64
    elif problem=='scope':context['prepare']['result']['host']='172.30.30.58'
    elif problem=='prior-restart':r['controlServiceRestartedInPriorAttempt']=False
    elif problem=='prepare-writes':context['prepare']['result']['serverWrites']=True
    else:w.pop('continuationLocalFailurePin')
    seal(w)
    with pytest.raises(ValueError):
        subject().verify_target_activations(proofs['source'],proofs['activations'],build=proofs['build'],build_pin=proofs['build_pin'],
            package_raw=proofs['package_raw'],previous_package_raw=proofs['previous_package_raw'],
            continuations={} if context is None else {'59':context})


@pytest.mark.parametrize('problem',['old-dropin','missing-created-before','missing-created-dropin','dependency'])
def test_original_process_and_created_path_scope_are_exact(proofs,problem):
    r=proofs['activations']['58']['result']
    if problem=='old-dropin':
        for phase in ('before','after'):r['transition'][phase]['controllers'][-1]['properties']['DropInPaths']='/unknown.conf'
        r['transition']['after']['controllers'][-1]['properties']['DropInPaths']+=' '+r['dropinPin']['path']
    elif problem=='missing-created-before':r['createdPaths'].pop(1)
    elif problem=='missing-created-dropin':r['createdPaths'].pop(2)
    else:r['addedDependencies']={'Requires':[],'After':[]}
    seal(proofs['activations']['58'])
    with pytest.raises(ValueError):project(proofs)


def test_shared_runtime_implementation_is_pinned_before_any_selection_read(tmp_path,monkeypatch):
    module=subject();actual=module.publication.file_pin;observed=[]
    def read_pin(path):
        value=actual(path);observed.append(value);return value
    monkeypatch.setattr(module.publication,'file_pin',read_pin)
    with pytest.raises(FileNotFoundError):
        module.load_activated_target_installation(tmp_path,tmp_path,selection_file='absent.json')
    defining_file=Path(inspect.getfile(module.transition.RuntimeGates)).resolve(strict=True)
    assert actual(defining_file) in observed,'SHARED_RUNTIME_IMPLEMENTATION_NOT_PINNED'
