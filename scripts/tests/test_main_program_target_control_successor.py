"""Finite pure successor contracts; synthetic bundles grant no installation."""
from copy import deepcopy
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

TASK=Path(__file__).resolve().parents[2]/'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
sys.path.insert(0,str(TASK))
FILE=TASK/'main_program_target_control_successor.py'
from test_main_program_target_control_candidate import inputs as old_inputs, graph_repin, repin
import main_program_target_control_candidate as old_binding

A312='a3121c64d46fcdc2c1a3195a2cbbf8ca1c05742e'
EPOCH='common/recovery_backup_epoch.py'


def subject():
    assert FILE.exists(),'MISSING_TARGET_153_READER_SUCCESSOR_HELPER'
    return importlib.import_module('main_program_target_control_successor')


def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def pin(path,raw):return dict(path=path,bytes=len(raw),sha256=digest(raw))
def docpin(path,value):return pin(path,canonical(value))
def localpin(name,value):return dict(file=name,bytes=len(canonical(value)),sha256=digest(canonical(value)))


def archive(files):
    hashes={name:digest(raw) for name,raw in files.items()}
    manifest=canonical(dict(variant='standard',fileVerification=True,payloadContentVerification=True,
        files=hashes,packageSha256=digest(canonical(hashes))))
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w:gz') as tar:
        for name,raw in sorted(dict(files,**{'package.json':manifest}).items()):
            item=tarfile.TarInfo(name);item.size=len(raw);tar.addfile(item,io.BytesIO(raw))
    return output.getvalue(),manifest,digest(canonical(hashes))


def package_build(files,commit):
    raw,manifest,sha=archive(files)
    value=dict(status='PASS',targetCommit=commit,allFilesShaAndCompileVerified=True,exactCommittedInput=True,
        newCommits=False,mergeRequired=False,packages=[dict(variant='standard',fileCount=153,bytes=len(raw),
            sha256=digest(raw),fileManifestSha256=sha),dict(variant='lightweight',fileCount=152,bytes=1,
            sha256='e'*64,fileManifestSha256='f'*64)])
    return value,raw,manifest


def successor_case(host='58'):
    k=old_inputs.__wrapped__()
    def scope(value):
        if type(value) is dict:return {scope(a):scope(b) for a,b in value.items()}
        if type(value) is list:return [scope(a) for a in value]
        if type(value) is str and (value=='58' or 'target-58' in value or '.58' in value or '/58' in value):
            return value.replace('58',host)
        return value
    k=scope(k)
    # Include the reader in both true member sets; fixture construction is pure
    # and does not change the older candidate's reviewed 147->153 delta.
    removed=next(name for name in k['previous_package_files'] if name.startswith('common/unchanged_'))
    for key in ('previous_package_files','package_files'):
        k[key][EPOCH]=k[key].pop(removed)
    _,_,sha=archive(k['previous_package_files']);k['old_build']['fileManifestSha256']=sha
    k['current_controller']['fileManifestSha256']=sha
    k['new_build'],current_raw,current_manifest=package_build(k['package_files'],A312)
    def relocate(value):
        if type(value) is str:return value.replace('ccccccc','a3121c6')
        if type(value) is list:return [relocate(x) for x in value]
        if type(value) is dict:return {a:relocate(b) for a,b in value.items()}
        return value
    k['new_engine']=relocate(k['new_engine']);k['configuration_root']=relocate(k['configuration_root'])
    k['preservation']=relocate(k['preservation']);graph_repin(k)
    k['preservation']['originalCredentialPins'][-1]=pin('/original/mount.credentials',b'original-smb')
    core=k['current_controller'];core.update(pid=42,dropinPin=pin('/etc/systemd/system/spug-target-'+host+'.service.d/old.conf',b'old'),
        buildPin={'historical':'old147'})
    k['control']['pythonPin']=pin('/usr/bin/python3',b'python')
    repin(k)
    for targets in k['control']['restoreConfigurations'].values():targets[core['targetConfigRef']]=deepcopy(core['ownerConfigurationPin'])
    repin(k)
    candidate=old_binding.build_target_control_candidate(**k)
    docs=candidate['newDocuments'];c=candidate['controller']
    owner=next(r['value'] for r in docs if r['pin']==c['ownerPin'])
    control=next(r['value'] for r in docs if r['pin']==c['controlPin'])
    row=deepcopy(core);row.update(engine=c['engine'],pid=43,sourceCommit=A312,fileCount=153,
        fileManifestSha256=candidate['package']['fileManifestSha256'],ownerConfigurationPin=c['ownerPin'],
        controlConfigurationPin=c['controlPin'],dropinPin=pin('/etc/systemd/system/spug-target-'+host+'.service.d/zz-a3121c6.conf',b'current'),
        environmentMode='CONFIG_EXACT')
    # Raw runtime row deliberately retains old buildPin/packageSha256 historical
    # fields. The current artifact is the formally bound per-role build instead.
    current_build=k['new_build'];buildpin=localpin('release-build-main-a3121c6-r1.json',current_build)
    selection=dict(schemaVersion='TaskMainProgramTargetControlSelection/v1',baseSourceSelectionPin={
        'file':'retained-source.json','bytes':10,'sha256':'1'*64},buildPin=buildpin,
        standardPackagePin=pin('/private/current.tgz',current_raw),targetActivationEvidencePins={
            host:pin('/private/activation-'+host+'.json',b'original') for host in ('57','58','59')})
    predecessor=dict(status='ACTIVATED',installationVerified=True,runtimeVerified=False,selection=selection,
        selectionPin=localpin('main-program-targets-activated-a3121c6-r2-v1.json',selection),
        effectiveControllersByHost={host:[row]},controllerBuildBindings={host:{'target':dict(buildPin=buildpin,sourceCommit=A312)}},
        targetOwners={host:owner},targetControls={host:control},sourceInstallation={'keep':'source6968b58'},
        baseInstallation={'keep':'Spug5651efc-and-original147'},activationReceiptPins=[pin(
            '/control/control-activation-main-target-a3121c6-r1/result-activate.private.json',b'original-activation')],inputPins=[])
    files=deepcopy(k['package_files']);files[EPOCH]=b'READER_VERSION = 2\n'
    newbuild,newraw,_=package_build(files,'d'*40)
    return dict(predecessor=predecessor,predecessor_selection_pin=predecessor['selectionPin'],
        predecessor_selection_raw=canonical(selection),predecessor_build_raw=canonical(current_build),
        predecessor_build=current_build,build=newbuild,predecessor_package_raw=current_raw,package_raw=newraw,
        host=host,preservation_documents=k['preservation'],configuration_root='/control/configuration/main-target-ddddddd-r1',
        new_engine='/control/engine-main-program-ddddddd',retained_failure_pins=[pin('/control/failed-operation.json',b'original-failure')])


@pytest.fixture
def successor_inputs():return successor_case()


def construct(values):return subject().build_target_control_successor_candidate(**values)


def documents(candidate):return {Path(r['pin']['path']).name:r for r in candidate['newDocuments']}


def test_single_reader_upgrade_builds_only_four_exact_documents_from_activated_153(successor_inputs):
    k=successor_inputs;before=deepcopy(k);result=construct(k);docs=documents(result)
    assert k==before and result['schemaVersion']=='MainProgramTargetControlSuccessorCandidate/v1'
    assert result['status']=='BOUND_NOT_INSTALLED' and result['previousController']==k['predecessor']['effectiveControllersByHost']['58'][-1]
    assert result['predecessorSelectionPin']==k['predecessor_selection_pin'] and len(result['newDocuments'])==4
    assert set(docs)=={'repository.json','policy.json','main-recovery.json','control-target.json'}
    olddocs={Path(r['pin']['path']).name:r for r in k['preservation_documents']['documents']}
    repository=deepcopy(olddocs['repository.json']['value'])
    repository['captureBinderPin']=dict(olddocs['repository.json']['value']['captureBinderPin'],
        path=k['new_engine']+'/formal/formal_capture_recovery_inputs.py')
    assert docs['repository.json']['value']==repository
    policy=deepcopy(olddocs['policy.json']['value']);policy['repositoryConfigurationPin']=docs['repository.json']['pin']
    assert docs['policy.json']['value']==policy
    ref=result['targetConfigRef'];oldowner=k['predecessor']['targetOwners']['58'];owner=deepcopy(oldowner)
    owner['formalModuleDirectory']=k['new_engine']+'/formal';owner['targetPreservationPolicies'][ref]=docs['policy.json']['pin']
    assert docs['main-recovery.json']['value']==owner
    assert owner['targetProgramPolicies'][ref]['captureConfigurationPins']==oldowner['targetProgramPolicies'][ref]['captureConfigurationPins']
    assert result['retainedPreservationDocuments']==k['preservation_documents']['documents']
    assert result['retainedFailurePins']==k['retained_failure_pins']
    assert result['installationPerformed'] is result['restoreDispatched'] is False
    for row in result['newDocuments']:assert row['pin']==docpin(row['pin']['path'],row['value'])


@pytest.mark.parametrize('problem',['not-activated','runtime-true','wrong-selection','predecessor147','wrong-current-commit',
    'wrong-role-build','wrong-role-commit','wrong-source-commit','old-package-pin','old-package-bytes','new-package-bytes',
    'not-committed','same-commit','compile-unverified','wrong-engine-parent','wrong-root','root-r0','source-owner',
    'control-owner','graph-missing','graph-extra','graph-pin','graph-old-binder','graph-old-policy','graph-old-capture',
    'failure-pin','failure-duplicate'])
def test_each_unproven_predecessor_or_graph_input_fails_closed_without_mutation(successor_inputs,problem):
    k=successor_inputs;p=k['predecessor'];r=p['effectiveControllersByHost']['58'][-1]
    if problem=='not-activated':p['installationVerified']=False
    elif problem=='runtime-true':p['runtimeVerified']=True
    elif problem=='wrong-selection':k['predecessor_selection_pin']['sha256']='0'*64
    elif problem=='predecessor147':r['fileCount']=147
    elif problem=='wrong-current-commit':r['sourceCommit']='b'*40
    elif problem=='wrong-role-build':p['controllerBuildBindings']['58']['target']['buildPin']={'file':'wrong.json','bytes':1,'sha256':'0'*64}
    elif problem=='wrong-role-commit':p['controllerBuildBindings']['58']['target']['sourceCommit']='b'*40
    elif problem=='wrong-source-commit':k['predecessor_build']['targetCommit']='b'*40
    elif problem=='old-package-pin':p['selection']['standardPackagePin']['sha256']='0'*64
    elif problem=='old-package-bytes':k['predecessor_package_raw']+=b'unknown'
    elif problem=='new-package-bytes':k['package_raw']+=b'unknown'
    elif problem=='not-committed':k['build']['exactCommittedInput']=False
    elif problem=='same-commit':k['build']['targetCommit']=A312
    elif problem=='compile-unverified':k['build']['allFilesShaAndCompileVerified']=False
    elif problem=='wrong-engine-parent':k['new_engine']='/other/engine-main-program-ddddddd'
    elif problem=='wrong-root':k['configuration_root']='/other/configuration/main-target-ddddddd-r1'
    elif problem=='root-r0':k['configuration_root']='/control/configuration/main-target-ddddddd-r0'
    elif problem=='source-owner':p['targetOwners']['58']['sources']['existing-source']['identity']='changed'
    elif problem=='control-owner':p['targetControls']['58']['restoreConfigurations']['existing-source']['target-58']['sha256']='0'*64
    elif problem=='graph-missing':k['preservation_documents']['documents'].pop()
    elif problem=='graph-extra':k['preservation_documents']['documents'].append(deepcopy(k['preservation_documents']['documents'][0]))
    elif problem=='graph-pin':k['preservation_documents']['documents'][0]['pin']['sha256']='0'*64
    elif problem=='graph-old-binder':
        row=next(x for x in k['preservation_documents']['documents'] if Path(x['pin']['path']).name=='repository.json')
        row['value']['captureBinderPin']['path']='/wrong/formal/formal_capture_recovery_inputs.py'
    elif problem=='graph-old-policy':p['targetOwners']['58']['targetPreservationPolicies']['target-58']['sha256']='0'*64
    elif problem=='graph-old-capture':p['targetOwners']['58']['targetProgramPolicies']['target-58']['captureConfigurationPins'].clear()
    elif problem=='failure-pin':k['retained_failure_pins'][0]['sha256']='unknown'
    else:k['retained_failure_pins'].append(deepcopy(k['retained_failure_pins'][0]))
    original=deepcopy(k)
    with pytest.raises(ValueError):construct(k)
    assert k==original


@pytest.mark.parametrize('problem',['second-member','added','deleted','unchanged-reader','syntax'])
def test_official_rehashed_tar_still_requires_exactly_one_reader_change(successor_inputs,problem):
    k=successor_inputs
    with tarfile.open(fileobj=io.BytesIO(k['package_raw']),mode='r:gz') as tar:
        files={m.name:tar.extractfile(m).read() for m in tar if m.name!='package.json'}
    if problem=='second-member':files['recovery_entry.py']+=b'EXTRA=True\n'
    elif problem=='added':files['common/unreviewed.py']=b'EXTRA=True\n'
    elif problem=='deleted':files.pop('recovery_entry.py')
    elif problem=='unchanged-reader':
        with tarfile.open(fileobj=io.BytesIO(k['predecessor_package_raw']),mode='r:gz') as tar:files[EPOCH]=tar.extractfile(EPOCH).read()
    else:files[EPOCH]=b'return 1\n'
    k['build'],k['package_raw'],_=package_build(files,'d'*40)
    with pytest.raises((ValueError,SyntaxError)):construct(k)


def test_raw_historical_artifact_fields_are_preserved_but_never_used_as_current_build(successor_inputs):
    k=successor_inputs;row=k['predecessor']['effectiveControllersByHost']['58'][-1]
    assert row['buildPin']=={'historical':'old147'} and row['packageSha256']!=digest(k['predecessor_package_raw'])
    result=construct(k)
    assert result['previousController']==row and result['previousPackage']['packageSha256']==digest(k['predecessor_package_raw'])


def test_staging_plan_contains_158_exclusive_writes_and_170_unchanged_originals(successor_inputs):
    k=successor_inputs;candidate=construct(k);original=deepcopy(k)
    result=subject().build_target_successor_staging_plan(candidate=candidate,**k)
    assert result['status']=='PLANNED_NOT_STAGED' and result['payloadFileCount']==153 and result['packageFileCount']==154
    assert result['documentCount']==4 and len(result['writes'])==158 and len(result['retainedPins'])==170
    assert len({row['pin']['path'] for row in result['writes']})==158
    assert not {row['pin']['path'] for row in result['writes']} & {p['path'] for p in result['retainedPins']}
    assert all(row['mode']==0o400 and row['exclusive'] is True and row['pin']==pin(row['pin']['path'],row['raw']) for row in result['writes'])
    assert result['installationPerformed'] is result['restoreDispatched'] is result['serverWrites'] is False
    assert k==original


def test_staging_plan_rebuilds_candidate_and_rejects_a_changed_document(successor_inputs):
    k=successor_inputs;candidate=construct(k);candidate['newDocuments'][0]['value']['unknown']='change'
    with pytest.raises(ValueError):subject().build_target_successor_staging_plan(candidate=candidate,**k)


def test_original_pretty_json_pins_are_not_reinterpreted_as_canonical(successor_inputs):
    k=successor_inputs;p=k['predecessor']
    raw=json.dumps(k['predecessor_build'],ensure_ascii=False,indent=2).encode('utf-8')
    k['predecessor_build_raw']=raw
    bp=dict(file=p['selection']['buildPin']['file'],bytes=len(raw),sha256=digest(raw))
    p['selection']['buildPin']=bp;p['controllerBuildBindings']['58']['target']['buildPin']=deepcopy(bp)
    raw=json.dumps(p['selection'],ensure_ascii=False,indent=2).encode('utf-8')
    k['predecessor_selection_raw']=raw
    reference=dict(file=p['selectionPin']['file'],bytes=len(raw),sha256=digest(raw))
    p['selectionPin']=reference;k['predecessor_selection_pin']=reference
    assert construct(k)['status']=='BOUND_NOT_INSTALLED'


def test_local_private_package_and_evidence_pins_keep_native_windows_paths(successor_inputs):
    k=successor_inputs;p=k['predecessor'];selection=p['selection']
    selection['standardPackagePin']['path']='C:\\private\\current.tgz'
    for host,reference in selection['targetActivationEvidencePins'].items():reference['path']='C:\\private\\activation-'+host+'.json'
    raw=canonical(selection);p['selectionPin']=dict(file=p['selectionPin']['file'],bytes=len(raw),sha256=digest(raw))
    k['predecessor_selection_pin']=deepcopy(p['selectionPin']);k['predecessor_selection_raw']=raw
    assert construct(k)['status']=='BOUND_NOT_INSTALLED'


def runtime_inputs(k):
    candidate=construct(k);old=deepcopy(candidate['previousController']);ref=candidate['targetConfigRef']
    unit=dict(service=old['service'],directory='/etc/systemd/system/'+old['service']+'.d',
        existingNames=['old.conf'],dropinPins=[pin('/etc/systemd/system/'+old['service']+'.d/old.conf',b'old')],
        unitPin=pin('/etc/systemd/system/'+old['service'],b'unit'),opaque={'keep':'unit'})
    spec=dict(current=dict(host=old['host'],suffix=old['host'].rsplit('.',1)[1],controllers=[old]),
        unit=dict(controllers=[unit]),targetConfigRef=ref,environmentBaseline=None,previousCustody={'keep':'legacy147'},
        oldReceiptPin=pin('/control/legacy147-receipt.json',b'legacy147'),originalInventory={'keep':'original'},
        historyPins=[],sourceEvidencePins=[],newDocuments=[],retainedDocuments=[
            *[deepcopy(row['pin']) for row in candidate['retainedPreservationDocuments']],
            old['ownerConfigurationPin'],old['controlConfigurationPin'],pin('/original/mount.credentials',b'original-smb')])
    if old['host'].endswith('.57'):
        spec['current']['controllers'].insert(0,dict(role='source',pid=1,engine='/source6968b58',service='source.service',
            retained={'keep':'source'}))
    historical=deepcopy(spec);historical['current']['controllers'][-1]['pid']=42
    historical['current']['controllers'][-1]['fileCount']=147
    dropin=pin(unit['directory']+'/zzz-reader.conf',b'new reader dropin')
    return dict(current_spec=spec,retained_history_spec=historical,candidate=candidate,dropin_pin=dropin,successor_pid=44)


def runtime_builder():
    module=subject();assert hasattr(module,'build_target_successor_runtime_spec'),'MISSING_SUCCESSOR_RUNTIME_SPEC_BUILDER'
    return module.build_target_successor_runtime_spec


def test_runtime_spec_separates_current_153_and_original_147_without_rebinding_history(successor_inputs):
    args=runtime_inputs(successor_inputs);before=deepcopy(args);result=runtime_builder()(**args)
    assert args==before
    old=args['candidate']['previousController'];row=result['current']['controllers'][-1]
    expected=deepcopy(old);expected.update(pid=44,engine=args['candidate']['controller']['engine'],
        controlConfigurationPin=args['candidate']['controller']['controlPin'],ownerConfigurationPin=args['candidate']['controller']['ownerPin'],
        sourceCommit=args['candidate']['sourceCommit'],fileManifestSha256=args['candidate']['package']['fileManifestSha256'],
        dropinPin=args['dropin_pin'],environmentMode='CONFIG_EXACT')
    assert row==expected
    for key in ('oldReceiptPin','previousCustody','originalInventory','historyPins','sourceEvidencePins','environmentBaseline'):
        assert result[key]==args['current_spec'][key]
    assert result['retainedDocuments']==args['current_spec']['retainedDocuments']+[r['pin'] for r in args['candidate']['newDocuments']]
    assert result['unit']['controllers'][-1]['dropinPins'][-1]==old['dropinPin']
    assert args['retained_history_spec']['current']['controllers'][-1]['fileCount']==147


@pytest.mark.parametrize('problem',['current147','current-row','history153','same-pid','dropin-existing','dropin-order','foreign-service'])
def test_runtime_spec_rejects_unknown_transition_scope(successor_inputs,problem):
    args=runtime_inputs(successor_inputs)
    if problem=='current147':args['current_spec']['current']['controllers'][-1]['fileCount']=147
    elif problem=='current-row':args['current_spec']['current']['controllers'][-1]['ownerConfigurationPin']['sha256']='0'*64
    elif problem=='history153':args['retained_history_spec']['current']['controllers'][-1]['fileCount']=153
    elif problem=='same-pid':args['successor_pid']=args['candidate']['previousController']['pid']
    elif problem=='dropin-existing':args['dropin_pin']=args['candidate']['previousController']['dropinPin']
    elif problem=='dropin-order':args['dropin_pin']['path']=args['dropin_pin']['path'].replace('zzz-reader','aaa-reader')
    else:args['current_spec']['unit']['controllers'][-1]['service']='foreign.service'
    with pytest.raises(ValueError):runtime_builder()(**args)


def seal_successor(wrapper):
    result=wrapper['result'];result.pop('activationReceiptPin',None)
    result['activationReceiptPin']=docpin(result['createdPaths'][0]+'/result-activate.private.json',result)


@pytest.fixture
def activation_inputs():
    from test_main_program_target_control_activated import proofs as initial_proofs
    initial=initial_proofs.__wrapped__();cases={host:successor_case(host) for host in ('57','58','59')}
    first=cases['58'];predecessor=deepcopy(first['predecessor']);predecessor['targetRuntimeSpecs']={}
    predecessor['activationReceiptPins']=[];activations={}
    for host,k in cases.items():
        for key in ('predecessor_build','build','predecessor_package_raw','package_raw','predecessor_selection_raw','predecessor_build_raw'):
            k[key]=deepcopy(first[key])
        k['predecessor']['selection']=deepcopy(predecessor['selection'])
        k['predecessor']['selectionPin']=deepcopy(predecessor['selectionPin'])
        k['predecessor']['controllerBuildBindings'][host]['target']['buildPin']=deepcopy(predecessor['selection']['buildPin'])
        k['predecessor_selection_pin']=deepcopy(predecessor['selectionPin'])
        if host!='58':k['retained_failure_pins']=[]
        args=runtime_inputs(k);spec=args['current_spec'];candidate=args['candidate'];old=candidate['previousController']
        predecessor['effectiveControllersByHost'][host]=deepcopy(spec['current']['controllers'])
        for key in ('targetOwners','targetControls','controllerBuildBindings'):
            predecessor[key][host]=deepcopy(k['predecessor'][key][host])
        predecessor['targetRuntimeSpecs'][host]=dict(original=deepcopy(args['retained_history_spec']),successor=deepcopy(spec))
        oldreceipt=pin('/control/activation-a3121c6-'+host+'/result-activate.private.json',b'old-activation-'+host.encode())
        predecessor['activationReceiptPins'].append(oldreceipt)
        newspec=runtime_builder()(**args);row=newspec['current']['controllers'][-1]
        oldcontrol=k['predecessor']['targetControls'][host]
        newcontrol=next(r['value'] for r in candidate['newDocuments'] if r['pin']==candidate['controller']['controlPin'])
        unit=spec['unit']['controllers'][-1]
        drops=unit['dropinPins']+[old['dropinPin']]
        def observed(r,control):
            argv=[control['pythonPin']['path'],'-B',r['engine']+'/control_entry.py','serve','--config-pin',canonical(r['controlConfigurationPin']).decode()]
            dependency='spug-main-preservation-view-'+host+'-20261111-r1.service'
            return dict(service=r['service'],pid=r['pid'],argvSha256=digest(('\0'.join(argv)+'\0').encode()),
                executable=control['pythonPin']['path'],environmentVerification=dict(mode='CONFIG_EXACT',environmentSha256='e'*64),
                properties=dict(MainPID=str(r['pid']),FragmentPath=unit['unitPin']['path'],DropInPaths=' '.join(p['path'] for p in drops),
                    Requires=dependency+' original.service',After=dependency+' original.service',
                    LimitNOFILE='65536',ActiveState='active',SubState='running'))
        with tarfile.open(fileobj=io.BytesIO(k['predecessor_package_raw']),mode='r:gz') as tar:oldmanifest=tar.extractfile('package.json').read()
        with tarfile.open(fileobj=io.BytesIO(k['package_raw']),mode='r:gz') as tar:newmanifest=tar.extractfile('package.json').read()
        before=dict(controllers=[observed(old,oldcontrol)],packagePins=[pin(old['engine']+'/package.json',oldmanifest)],
            containers={'actual-business':{'unchanged':True}},fstabPin=pin('/etc/fstab',b'original'),mountinfoSha256='f'*64,
            historyGuard={'After':'history-original.service'},previousCustodyObservation={'legacy':'original147'},
            originalInventoryObservation={'original':'preserved'},documentsCreated=True)
        after=deepcopy(before);after['controllers']=[observed(row,newcontrol)]
        after['controllers'][-1]['properties']['DropInPaths']+=' '+args['dropin_pin']['path']
        after['packagePins']=[pin(row['engine']+'/package.json',newmanifest)]
        if host=='57':
            peer={'source':'unchanged','pid':1}
            for observation in (before,after):
                observation['controllers'].insert(0,deepcopy(peer));observation['packagePins'].insert(0,pin('/source6968b58/package.json',b'source'))
        prior=initial['activations'][host]['result']
        directory='/control/control-activation-main-target-ddddddd-r1'
        result=dict(schemaVersion='MainProgramTargetControlSuccessorActivation/v1',status='PASS',stage='complete',
            host=old['host'],role='target',targetConfigRef=candidate['targetConfigRef'],sourceCommit=k['build']['targetCommit'],
            observedAt='2026-11-12T00:00:00+00:00',candidate=candidate,predecessorSelectionPin=deepcopy(predecessor['selectionPin']),
            predecessorActivationReceiptPin=deepcopy(oldreceipt),retainedFailurePins=deepcopy(k['retained_failure_pins']),
            failurePinsBefore=deepcopy(k['retained_failure_pins']),failurePinsAfter=deepcopy(k['retained_failure_pins']),
            currentRuntimeSpec=spec,retainedHistoryRuntimeSpec=args['retained_history_spec'],successorRuntimeSpec=newspec,
            before=before,after=after,currentController=row,nativeBefore=deepcopy(prior['nativeBefore']),
            nativeAfter=deepcopy(prior['nativeAfter']),originalApi=deepcopy(prior['originalApi']),apiSelection=deepcopy(prior['apiSelection']),
            dropinPin=args['dropin_pin'],createdPaths=[directory,directory+'/before.private.json',args['dropin_pin']['path']])
        for key in ('activationCompleted','apiVerified','controlServiceRestarted','oldReceiptPreserved','businessContainersUnchanged',
            'fstabAndMountsUnchanged','physicalLockVerified','actualImportsVerified'):result[key]=True
        for key in ('backupDispatched','restoreDispatched','businessMutationDispatched','oldReceiptRotated'):result[key]=False
        wrapper=dict(status='PASS',host=host,mode='ACTIVATE',observedAt=result['observedAt'],elapsedSeconds=1,
            scriptPin=pin('/private/successor-'+host+'.py',b'actual-pinned-carrier'),result=result)
        seal_successor(wrapper);activations[host]=wrapper
    return dict(predecessor=predecessor,activations=activations,build=first['build'],build_pin=localpin('new-build.json',first['build']),
        predecessor_selection_raw=first['predecessor_selection_raw'],predecessor_build_raw=first['predecessor_build_raw'],
        package_raw=first['package_raw'],previous_package_raw=first['predecessor_package_raw'])


def projector():
    module=subject();assert hasattr(module,'verify_target_successor_activations'),'MISSING_SUCCESSOR_ACTIVATION_PROJECTION'
    return module.verify_target_successor_activations


def test_complete_successor_proofs_preserve_source_spug_and_both_historical_generations(activation_inputs):
    k=activation_inputs;before=deepcopy(k);result=projector()(**k)
    assert k==before and result['status']=='ACTIVATED' and result['installationVerified'] is True and result['runtimeVerified'] is False
    assert result['predecessorInstallation']==k['predecessor']
    assert result['sourceInstallation']==k['predecessor']['sourceInstallation'] and result['baseInstallation']==k['predecessor']['baseInstallation']
    assert result['effectiveControllersByHost']['57'][0]==k['predecessor']['effectiveControllersByHost']['57'][0]
    assert len(result['activationReceiptPins'])==3
    for host,w in k['activations'].items():
        assert result['effectiveControllersByHost'][host][-1]==w['result']['currentController']
        assert result['controllerBuildBindings'][host]['target']==dict(buildPin=k['build_pin'],sourceCommit=k['build']['targetCommit'])
        assert result['targetRuntimeSpecs'][host]['original']==k['predecessor']['targetRuntimeSpecs'][host]['original']
        assert result['targetRuntimeSpecs'][host]['successor']==w['result']['successorRuntimeSpec']


def test_successor_original_receipt_publication_may_append_only_its_own_tail(activation_inputs):
    k=activation_inputs;r=k['activations']['58']['result'];r['createdPaths'].append(r['activationReceiptPin']['path'])
    assert projector()(**k)['installationVerified'] is True


def test_successor_before_duplicate_dependency_is_not_accepted_as_a_set(activation_inputs):
    k=activation_inputs;r=k['activations']['58']['result'];r['before']['controllers'][-1]['properties']['After']+=' original.service'
    seal_successor(k['activations']['58'])
    with pytest.raises(ValueError):projector()(**k)


@pytest.mark.parametrize('problem',['missing-host','extra-host','prepare-only','bound','wrong-receipt','unknown-field',
    'wrong-predecessor','old-current-spec','old-history-spec','new-spec','candidate','receipt-bytes','containers','mounts',
    'custody','source-peer','new-pid','new-argv','dropin','dependency','package-before','package-after',
    'native','api','failed-before','failed-after','failed-retained','backup','history-spec-target'])
def test_successor_activation_rejects_each_missing_or_changed_proof(activation_inputs,problem):
    k=activation_inputs;w=k['activations']['58'];r=w['result']
    if problem=='missing-host':k['activations'].pop('59')
    elif problem=='extra-host':k['activations']['60']=deepcopy(w)
    elif problem=='prepare-only':w['mode']='PREPARE'
    elif problem=='bound':r['status']='BOUND_NOT_INSTALLED'
    elif problem=='wrong-receipt':r['predecessorActivationReceiptPin']['sha256']='0'*64
    elif problem=='unknown-field':r['unknown']='unapproved'
    elif problem=='wrong-predecessor':r['predecessorSelectionPin']['sha256']='0'*64
    elif problem=='old-current-spec':r['currentRuntimeSpec']['oldReceiptPin']['sha256']='0'*64
    elif problem=='old-history-spec':r['retainedHistoryRuntimeSpec']['oldReceiptPin']['sha256']='0'*64
    elif problem=='new-spec':r['successorRuntimeSpec']['historyPins'].append(pin('/unknown.json',b'unknown'))
    elif problem=='candidate':r['candidate']['newDocuments'][0]['value']['unknown']='changed'
    elif problem=='receipt-bytes':r['activationReceiptPin']['sha256']='0'*64
    elif problem=='containers':r['after']['containers']['actual-business']['unchanged']=False
    elif problem=='mounts':r['after']['mountinfoSha256']='0'*64
    elif problem=='custody':r['after']['previousCustodyObservation']={}
    elif problem=='source-peer':k['activations']['57']['result']['after']['controllers'][0]['pid']=2
    elif problem=='new-pid':r['currentController']['pid']=r['candidate']['previousController']['pid']
    elif problem=='new-argv':r['after']['controllers'][-1]['argvSha256']='0'*64
    elif problem=='dropin':r['after']['controllers'][-1]['properties']['DropInPaths']='/unknown.conf'
    elif problem=='dependency':r['after']['controllers'][-1]['properties']['After']+=' unknown.service'
    elif problem=='package-before':r['before']['packagePins'][-1]['sha256']='0'*64
    elif problem=='package-after':r['after']['packagePins'][-1]['sha256']='0'*64
    elif problem=='native':r['nativeAfter']['epoch']['state']='MUTATING'
    elif problem=='api':r['apiSelection']['applications'][0]['freshTargetConfigRefs']=[]
    elif problem=='failed-before':r['failurePinsBefore']=[]
    elif problem=='failed-after':r['failurePinsAfter']=[]
    elif problem=='failed-retained':r['retainedFailurePins']=[]
    elif problem=='backup':r['backupDispatched']=True
    else:r['retainedHistoryRuntimeSpec']['current']['controllers'][-1]['fileCount']=153
    if problem!='receipt-bytes':
        for wrapper in k['activations'].values():seal_successor(wrapper)
    with pytest.raises(ValueError):projector()(**k)


def loader():
    module=subject();assert hasattr(module,'load_activated_target_successor_installation'),'MISSING_SUCCESSOR_LOCAL_LOADER'
    return module.load_activated_target_successor_installation


@pytest.fixture
def local_inputs(tmp_path,activation_inputs):
    k=deepcopy(activation_inputs);task=tmp_path/'task';private=tmp_path/'private';task.mkdir();private.mkdir()
    def write(path,raw):path.write_bytes(raw);return pin(str(path),raw)
    def report(name,raw):write(task/name,raw);return dict(file=name,bytes=len(raw),sha256=digest(raw))
    predecessor=k['predecessor'];oldbuild=json.loads(k['predecessor_build_raw'])
    predecessor['selection']['standardPackagePin']=write(private/'previous.tgz',k['previous_package_raw'])
    original_selection=canonical(predecessor['selection']);predecessor['selectionPin']=report('predecessor.json',original_selection)
    report(predecessor['selection']['buildPin']['file'],k['predecessor_build_raw'])
    k['predecessor_selection_raw']=original_selection
    evidence={}
    for host,w in k['activations'].items():
        w['scriptPin']=write(private/('carrier-'+host+'.py'),b'actual-carrier')
        w['result']['predecessorSelectionPin']=deepcopy(predecessor['selectionPin'])
        w['result']['candidate']['predecessorSelectionPin']=deepcopy(predecessor['selectionPin'])
        seal_successor(w);evidence[host]=write(private/('activation-'+host+'.json'),canonical(w))
    buildpin=report('successor-build.json',canonical(k['build']))
    selection=dict(schemaVersion='TaskMainProgramTargetControlSuccessorSelection/v1',
        predecessorSelectionPin=predecessor['selectionPin'],buildPin=buildpin,
        standardPackagePin=write(private/'successor.tgz',k['package_raw']),targetActivationEvidencePins=evidence)
    report('successor.json',canonical(selection))
    predecessor['inputPins']=[pin(str(task/'predecessor.json'),original_selection)]
    return dict(task=task,private=private,selection=selection,predecessor=predecessor)


def test_loader_reads_exact_files_and_formal_predecessor_then_rechecks_all_pins(local_inputs,monkeypatch):
    call=loader();module=subject();observed=[];k=local_inputs
    def formal(task,private,*,selection_file,historical_source_custody_pin=None):
        observed.append((task,private,selection_file,historical_source_custody_pin));return deepcopy(k['predecessor'])
    monkeypatch.setattr(module.activated,'load_activated_target_installation',formal)
    result=call(k['task'],k['private'],selection_file='successor.json',historical_source_custody_pin={'retained':'actual'})
    assert observed==[(k['task'],k['private'],'predecessor.json',{'retained':'actual'})]
    assert result['selection']==k['selection'] and result['installationVerified'] is True and result['runtimeVerified'] is False
    paths={p['path'] for p in result['inputPins']}
    assert str(k['task']/'successor.json') in paths and str(k['private']/'activation-58.json') in paths
    assert str(Path(module.__file__).resolve()) in paths
    assert str(Path(module.transition.RuntimeGates.__module__.replace('.','/'))) not in paths
    assert any(p.endswith('main_program_control_runtime.py') for p in paths)


@pytest.mark.parametrize('problem',['selection-unknown','missing-host','pin-changed','outside-private','carrier-changed',
    'predecessor-not-formal','predecessor-pin','during-projection'])
def test_loader_rejects_incomplete_local_chain_or_input_drift(local_inputs,monkeypatch,problem):
    call=loader();module=subject();k=local_inputs;selection=k['selection']
    def formal(*args,**kwargs):
        result=deepcopy(k['predecessor'])
        if problem=='predecessor-not-formal':result['installationVerified']=False
        elif problem=='predecessor-pin':result['selectionPin']['sha256']='0'*64
        return result
    monkeypatch.setattr(module.activated,'load_activated_target_installation',formal)
    if problem=='selection-unknown':selection['unknown']=True
    elif problem=='missing-host':selection['targetActivationEvidencePins'].pop('59')
    elif problem=='pin-changed':selection['standardPackagePin']['sha256']='0'*64
    elif problem=='outside-private':selection['standardPackagePin']['path']=str(k['task']/'predecessor.json')
    elif problem=='carrier-changed':(k['private']/'carrier-58.py').write_bytes(b'changed')
    elif problem=='during-projection':
        original=module.verify_target_successor_activations
        def drifting(**kwargs):
            result=original(**kwargs);(k['private']/'carrier-58.py').write_bytes(b'drift');return result
        monkeypatch.setattr(module,'verify_target_successor_activations',drifting)
    (k['task']/'successor.json').write_bytes(canonical(selection))
    with pytest.raises(ValueError):call(k['task'],k['private'],selection_file='successor.json')
