"""Finite repeat-generation contracts; no server or installation is exercised."""
from copy import deepcopy
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
from types import SimpleNamespace

import pytest

from test_main_program_target_control_successor import (
    subject, activation_case as old_activation_case, canonical, digest, pin, localpin, package_build, runtime_builder, seal_successor, make_local_inputs)

B9='b9caa00b7eeed2b915c8855a8313521e57d06f72'
SCHEMA='TaskMainProgramTargetControlSuccessorSelection/v2'
PROFILE='MAIN_TARGET_CAPTURE_PREPARATION_COMPATIBILITY/v1'
PROFILE_MEMBERS=('common/recovery_capture_materials.py','common/recovery_resource_admission.py',
    'common/recovery_retained_retry.py','common/recovery_target_capture.py')


def activation_case(commit):
    """Use real member names in this independent finite baseline's fillers."""
    import test_main_program_target_control_successor as old_suite
    original=old_suite.old_inputs.__wrapped__
    def finite_inputs():
        k=original()
        for member in ('common/recovery_resource_admission.py','common/recovery_retained_retry.py'):
            filler=next(n for n in k['previous_package_files'] if n.startswith('common/unchanged_'))
            for key in ('previous_package_files','package_files'):k[key][member]=k[key].pop(filler)
        return k
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(old_suite,'old_inputs',SimpleNamespace(__wrapped__=finite_inputs))
        return old_activation_case(commit)


def payload(raw):
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        return {m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.name!='package.json'}


def delta(k):
    old=payload(k['predecessor_package_raw']);new=payload(k['package_raw'])
    return dict(schemaVersion='MainProgramTargetControlPackageDeltaReview/v1',status='REVIEWED',profileId=PROFILE,
        predecessorSelectionPin=deepcopy(k['predecessor_selection_pin']),
        predecessorCommit=k['predecessor_build']['targetCommit'],sourceCommit=k['build']['targetCommit'],
        predecessorBuildPin=deepcopy(k['predecessor']['selection']['buildPin']),buildPin=deepcopy(k['build_pin']),
        previousPackagePin=deepcopy(k['predecessor']['selection']['standardPackagePin']),
        standardPackagePin=pin('/private/next-'+k['build']['targetCommit'][:7]+'.tgz',k['package_raw']),
        changedMembers=[dict(member=n,previousSha256=digest(old[n]),sha256=digest(new[n]))
            for n in sorted(old) if old[n]!=new[n]])


def repin_review(k):
    k['package_delta_review_raw']=canonical(k['package_delta_review'])
    k['package_delta_review_pin']=localpin('review-'+k['build']['targetCommit'][:7]+'.json',k['package_delta_review'])


@pytest.fixture
def repeated_inputs():
    m=subject();first=activation_case(B9)
    predecessor=m.verify_target_successor_activations(**first)
    selection=dict(schemaVersion=m.SELECTION_SCHEMA,predecessorSelectionPin=first['predecessor']['selectionPin'],
        buildPin=first['build_pin'],standardPackagePin=pin('/private/b9.tgz',first['package_raw']),
        targetActivationEvidencePins={h:pin('/private/b9-'+h+'.json',canonical(w)) for h,w in first['activations'].items()})
    predecessor.update(selection=selection,selectionPin=localpin('b9.json',selection))
    # These are derived from the already verified v1 wrappers, then must match
    # the exact owner policy, runtime originals and full graph closure.
    graphs={}
    for host,w in first['activations'].items():
        candidate=w['result']['candidate'];owner=predecessor['targetOwners'][host];ref=candidate['targetConfigRef']
        rows={PurePosixPath(r['pin']['path']).name:deepcopy(r) for r in candidate['retainedPreservationDocuments']}
        for row in candidate['newDocuments']:
            name=PurePosixPath(row['pin']['path']).name
            if name in ('repository.json','policy.json'):rows[name]=deepcopy(row)
        graphs[host]=dict(schemaVersion='MainTargetPreservationDocuments/v1',status='BOUND_NOT_INSTALLED',
            targetConfigRef=ref,captureRef=ref+'-pre-restore',capturePin=rows['capture.json']['pin'],
            repositoryPin=rows['repository.json']['pin'],policyPin=rows['policy.json']['pin'],documents=list(rows.values()),
            originalCredentialPins=[owner['targets'][ref]['secrets']['minio'][key]
                for key in ('MINIO_ROOT_USER','MINIO_ROOT_PASSWORD')]+[pin('/original/mount.credentials',b'original-smb')])
    predecessor['currentPreservationDocumentsByHost']=graphs
    predecessor['retainedFailurePinsByHost']={h:deepcopy(w['result']['retainedFailurePins']) for h,w in first['activations'].items()}
    files=payload(first['package_raw'])
    for name in PROFILE_MEMBERS:
        files[name]+=b'\nREVIEWED_NEXT_GENERATION = True\n'
    build,raw,_=package_build(files,'e'*40)
    k=dict(predecessor=predecessor,predecessor_selection_pin=predecessor['selectionPin'],
        predecessor_selection_raw=canonical(selection),predecessor_build=first['build'],
        predecessor_build_raw=canonical(first['build']),predecessor_package_raw=first['package_raw'],
        build=build,build_pin=localpin('build-e.json',build),build_raw=canonical(build),package_raw=raw,
        host='58',preservation_documents=deepcopy(predecessor['currentPreservationDocumentsByHost']['58']),
        configuration_root='/control/configuration/main-target-eeeeeee-r1',new_engine='/control/engine-main-program-eeeeeee',
        retained_failure_pins=deepcopy(first['activations']['58']['result']['retainedFailurePins']))
    k['package_delta_review']=delta(k);repin_review(k)
    return k


def test_current_graph_binder_reads_verified_owner_policy_and_original_pins(repeated_inputs):
    k=repeated_inputs;first=activation_case(B9)
    actual=subject().bind_current_preservation_documents(k['predecessor'],first['activations'])
    assert actual==k['predecessor']['currentPreservationDocumentsByHost']


def construct(k):return subject().build_target_control_successor_candidate(**k)


def test_repeat_candidate_binds_actual_b9_and_exact_mixed_root_graph(repeated_inputs):
    k=repeated_inputs;before=deepcopy(k);candidate=construct(k)
    assert k==before and candidate['schemaVersion']=='MainProgramTargetControlSuccessorCandidate/v2'
    assert candidate['previousController']['sourceCommit']==B9
    assert candidate['packageDeltaReviewPin']==k['package_delta_review_pin']
    assert len(candidate['newDocuments'])==4 and len(candidate['retainedPreservationDocuments'])==14
    docs={PurePosixPath(r['pin']['path']).name:r for r in candidate['newDocuments']}
    owner=docs['main-recovery.json']['value'];old=k['predecessor']['targetOwners']['58']
    assert owner['targets']==old['targets'] and owner['targetProgramPolicies']==old['targetProgramPolicies']
    assert len({PurePosixPath(r['pin']['path']).parent for r in candidate['retainedPreservationDocuments']})==2


def source_projection_case(k):
    k['host']='57';k['preservation_documents']=deepcopy(k['predecessor']['currentPreservationDocumentsByHost']['57'])
    k['retained_failure_pins']=deepcopy(k['predecessor']['retainedFailurePinsByHost']['57'])
    effective=k['predecessor']['effectiveControllersByHost']['57']
    runtime=k['predecessor']['targetRuntimeSpecs']['57']['successor']['current']['controllers']
    effective[0].pop('environmentMode',None);runtime[0]['environmentMode']='CONFIG_EXACT'
    return effective,runtime


def test_known_source_config_exact_projection_is_admitted_without_rewriting_originals(repeated_inputs):
    k=repeated_inputs;source_projection_case(k);before=deepcopy(k)
    result=construct(k)
    assert k==before and result['previousController']==k['predecessor']['effectiveControllersByHost']['57'][-1]


@pytest.mark.parametrize('problem',['unknown_mode','source_pid','extra_source','reverse_mode','target_mode','target_pid'])
def test_source_projection_exception_preserves_every_other_exact_binding(repeated_inputs,problem):
    k=repeated_inputs;effective,runtime=source_projection_case(k)
    if problem=='unknown_mode':runtime[0]['environmentMode']='UNKNOWN'
    elif problem=='source_pid':runtime[0]['pid']+=1
    elif problem=='extra_source':runtime[0]['unknown']='extra'
    elif problem=='reverse_mode':effective[0]['environmentMode']=runtime[0].pop('environmentMode')
    elif problem=='target_mode':runtime[-1]['environmentMode']='UNKNOWN'
    else:runtime[-1]['pid']+=1
    with pytest.raises(ValueError,match='PREDECESSOR_RUNTIME_BINDING'):construct(k)


@pytest.mark.parametrize('problem',['unknown','missing','extra_member','missing_member','unchanged_member','foreign_member'])
def test_fixed_reviewed_profile_cannot_be_replaced_by_caller_signed_delta(repeated_inputs,problem):
    k=repeated_inputs;r=k['package_delta_review'];old=payload(k['predecessor_package_raw']);files=payload(k['package_raw'])
    if problem=='unknown':r['profileId']='UNREVIEWED/v1'
    elif problem=='missing':r.pop('profileId')
    else:
        if problem=='extra_member':files['common/recovery_backup_epoch.py']+=b'\nEXTRA=True\n'
        elif problem in ('missing_member','unchanged_member'):files[PROFILE_MEMBERS[0]]=old[PROFILE_MEMBERS[0]]
        else:
            files[PROFILE_MEMBERS[0]]=old[PROFILE_MEMBERS[0]];files['common/recovery_backup_epoch.py']+=b'\nFOREIGN=True\n'
        build,raw,_=package_build(files,k['build']['targetCommit']);k.update(build=build,build_raw=canonical(build),
            build_pin=localpin('build-e.json',build),package_raw=raw)
        k['package_delta_review']=delta(k)
        if problem=='unchanged_member':
            p=PROFILE_MEMBERS[0];k['package_delta_review']['changedMembers'].append(dict(member=p,previousSha256=digest(old[p]),sha256=digest(old[p])))
            k['package_delta_review']['changedMembers'].sort(key=lambda row:row['member'])
    repin_review(k)
    with pytest.raises(ValueError):construct(k)


@pytest.mark.parametrize('problem',['missing','unknown_field','unreviewed','missing_member','old_sha','new_sha',
    'previous_commit','commit','old_build','build','old_package','new_package','selection','review_pin','build_raw'])
def test_review_is_exact_original_not_an_arbitrary_delta_set(repeated_inputs,problem):
    k=repeated_inputs;r=k['package_delta_review']
    if problem=='missing':k['package_delta_review']=None
    elif problem=='unknown_field':r['allowedMembers']=['*']
    elif problem=='unreviewed':r['status']='PLANNED'
    elif problem=='missing_member':r['changedMembers'].pop()
    elif problem=='old_sha':r['changedMembers'][0]['previousSha256']='0'*64
    elif problem=='new_sha':r['changedMembers'][0]['sha256']='0'*64
    elif problem=='previous_commit':r['predecessorCommit']='0'*40
    elif problem=='commit':r['sourceCommit']='0'*40
    elif problem=='old_build':r['predecessorBuildPin']['sha256']='0'*64
    elif problem=='build':r['buildPin']['sha256']='0'*64
    elif problem=='old_package':r['previousPackagePin']['sha256']='0'*64
    elif problem=='new_package':r['standardPackagePin']['sha256']='0'*64
    elif problem=='selection':r['predecessorSelectionPin']['sha256']='0'*64
    elif problem=='review_pin':k['package_delta_review_pin']['sha256']='0'*64
    else:k['build_raw']+=b' '
    if problem not in ('missing','review_pin','build_raw'):repin_review(k)
    with pytest.raises(ValueError):construct(k)


@pytest.mark.parametrize('problem',['policy','old_document','foreign_graph','controller','runtime','duplicate'])
def test_graph_trust_comes_from_verified_predecessor_not_candidate(repeated_inputs,problem):
    k=repeated_inputs;graph=k['preservation_documents']
    if problem=='policy':k['predecessor']['targetOwners']['58']['targetPreservationPolicies'][graph['targetConfigRef']]['sha256']='0'*64
    elif problem=='old_document':graph['documents'][0]['value']['unreviewed']=True
    elif problem=='foreign_graph':graph['documents'][0]['pin']['path']='/foreign/preservation/capture.json'
    elif problem=='controller':k['predecessor']['effectiveControllersByHost']['58'][-1]['ownerConfigurationPin']['sha256']='0'*64
    elif problem=='runtime':k['predecessor']['targetRuntimeSpecs']['58']['successor']['retainedDocuments'].clear()
    else:graph['documents'].append(deepcopy(graph['documents'][0]))
    with pytest.raises(ValueError):construct(k)


def test_repeat_staging_keeps_158_writes_and_170_exact_originals(repeated_inputs):
    k=repeated_inputs;c=construct(k);plan=subject().build_target_successor_staging_plan(candidate=c,**k)
    assert len(plan['writes'])==158 and len(plan['retainedPins'])==170
    assert plan['schemaVersion']=='MainProgramTargetSuccessorStagingPlan/v2'
    assert {p['path'] for p in plan['retainedPins']}.isdisjoint(r['pin']['path'] for r in plan['writes'])


def test_repeat_runtime_uses_current_153_and_retains_original_147(repeated_inputs):
    k=repeated_inputs;c=construct(k);prior=k['predecessor']['targetRuntimeSpecs']['58'];before=deepcopy(prior)
    drop=pin('/etc/systemd/system/'+c['previousController']['service']+'.d/zzzz-next.conf',b'next')
    out=runtime_builder()(current_spec=prior['successor'],retained_history_spec=prior['original'],candidate=c,
        dropin_pin=drop,successor_pid=45)
    assert prior==before and out['current']['controllers'][-1]['sourceCommit']=='e'*40
    assert prior['original']['current']['controllers'][-1]['fileCount']==147
    assert out['retainedDocuments']==prior['successor']['retainedDocuments']+[r['pin'] for r in c['newDocuments']]


def test_current_target_dispatcher_is_one_versioned_entrypoint():
    import main_program_current_installation as current
    assert callable(getattr(current,'load_current_target_installation',None))


def repeat_activation(k):
    """Finite contract observations, never a remote/runtime success assertion."""
    m=subject();prior=activation_case(B9);out={}
    for host in ('57','58','59'):
        inputs=deepcopy(k);inputs['host']=host
        inputs['preservation_documents']=inputs['predecessor']['currentPreservationDocumentsByHost'][host]
        inputs['retained_failure_pins']=deepcopy(prior['activations'][host]['result']['retainedFailurePins'])
        candidate=construct(inputs);spec=k['predecessor']['targetRuntimeSpecs'][host]['successor']
        original=k['predecessor']['targetRuntimeSpecs'][host]['original'];old=candidate['previousController']
        drop=pin('/etc/systemd/system/'+old['service']+'.d/zzzz-repeat-'+k['build']['targetCommit'][:7]+'.conf',b'repeat')
        new=m.build_target_successor_runtime_spec(current_spec=spec,retained_history_spec=original,candidate=candidate,
            dropin_pin=drop,successor_pid=old['pid']+1000)
        row=new['current']['controllers'][-1]
        control=next(r['value'] for r in candidate['newDocuments'] if r['pin']==candidate['controller']['controlPin'])
        before=deepcopy(prior['activations'][host]['result']['after'])
        # Bind the finite old generation to the current spec rather than a
        # historical fixture's numeric PID or package manifest.
        unit=spec['unit']['controllers'][-1]
        def observe(r,c,drops):
            argv=[c['pythonPin']['path'],'-B',r['engine']+'/control_entry.py','serve','--config-pin',canonical(r['controlConfigurationPin']).decode()]
            dependency='spug-main-preservation-view-'+host+'-20261111-r1.service'
            return dict(service=r['service'],pid=r['pid'],argvSha256=digest(('\0'.join(argv)+'\0').encode()),
                executable=c['pythonPin']['path'],environmentVerification=dict(mode='CONFIG_EXACT',environmentSha256='e'*64),
                properties=dict(MainPID=str(r['pid']),FragmentPath=unit['unitPin']['path'],DropInPaths=' '.join(p['path'] for p in drops),
                    Requires=dependency+' original.service',After=dependency+' original.service',LimitNOFILE='65536',ActiveState='active',SubState='running'))
        drops=unit['dropinPins']+[old['dropinPin']]
        before['controllers'][-1]=observe(old,k['predecessor']['targetControls'][host],drops)
        def manifest(raw):
            with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as a:return a.extractfile('package.json').read()
        before['packagePins'][-1]=pin(old['engine']+'/package.json',manifest(k['predecessor_package_raw']))
        after=deepcopy(before);after['controllers'][-1]=observe(row,control,drops+[drop])
        after['packagePins'][-1]=pin(row['engine']+'/package.json',manifest(k['package_raw']))
        w=deepcopy(prior['activations'][host]);r=w['result'];directory='/control/control-activation-main-target-'+k['build']['targetCommit'][:7]+'-r1'
        r.update(schemaVersion='MainProgramTargetControlSuccessorActivation/v2',sourceCommit=k['build']['targetCommit'],candidate=candidate,
            beforeApiState='AVAILABLE',retainedFailureAdmission=None,
            predecessorSelectionPin=deepcopy(k['predecessor_selection_pin']),predecessorActivationReceiptPin=deepcopy(k['predecessor']['activationReceiptPins'][('57','58','59').index(host)]),
            packageDeltaReviewPin=deepcopy(k['package_delta_review_pin']),currentRuntimeSpec=deepcopy(spec),retainedHistoryRuntimeSpec=deepcopy(original),
            successorRuntimeSpec=new,currentController=row,before=before,after=after,dropinPin=drop,
            createdPaths=[directory,directory+'/before.private.json',drop['path']])
        seal_successor(w);out[host]=w
    return dict(predecessor=k['predecessor'],activations=out,build=k['build'],build_pin=k['build_pin'],build_raw=k['build_raw'],
        package_raw=k['package_raw'],previous_package_raw=k['predecessor_package_raw'],
        predecessor_selection_raw=k['predecessor_selection_raw'],predecessor_build_raw=k['predecessor_build_raw'],
        package_delta_review=k['package_delta_review'],package_delta_review_pin=k['package_delta_review_pin'],
        package_delta_review_raw=k['package_delta_review_raw'])


def test_repeat_activation_keeps_current_and_original_history(repeated_inputs):
    inputs=repeat_activation(repeated_inputs);result=subject().verify_target_successor_activations(**inputs)
    assert result['installationVerified'] is True and result['runtimeVerified'] is False
    assert result['effectiveControllersByHost']['57'][0]==inputs['predecessor']['effectiveControllersByHost']['57'][0]
    for host in ('57','58','59'):
        assert result['targetRuntimeSpecs'][host]['original']==inputs['predecessor']['targetRuntimeSpecs'][host]['original']
        assert result['effectiveControllersByHost'][host][-1]['sourceCommit']=='e'*40


@pytest.mark.parametrize('problem',['review','candidate','predecessor','retained_history','native','peer','no_workers','api','failure'])
def test_repeat_activation_rejects_incomplete_or_changed_proof(repeated_inputs,problem):
    inputs=repeat_activation(repeated_inputs);r=inputs['activations']['58']['result']
    if problem=='review':r['packageDeltaReviewPin']['sha256']='0'*64
    elif problem=='candidate':r['candidate']['newDocuments'][0]['value']['unknown']=True
    elif problem=='predecessor':r['predecessorActivationReceiptPin']['sha256']='0'*64
    elif problem=='retained_history':r['retainedHistoryRuntimeSpec']['current']['controllers'][-1]['fileCount']=153
    elif problem=='native':r['nativeAfter']['epoch']['state']='MUTATING'
    elif problem=='peer':inputs['activations']['57']['result']['after']['controllers'][0]['pid']=2
    elif problem=='no_workers':r['after']['containers']['actual-business']['unchanged']=False
    elif problem=='api':r['apiSelection']['applications'][0]['freshTargetConfigRefs']=[]
    else:r['failurePinsAfter']=[]
    for w in inputs['activations'].values():seal_successor(w)
    with pytest.raises(ValueError):subject().verify_target_successor_activations(**inputs)


def test_repeat_chain_has_cycle_and_depth_limits():
    m=subject();assert callable(getattr(m,'_repeat_selection_chain',None))
    class Records:
        def __init__(self,cycle=False):self.cycle=cycle
        def read(self,name):
            number=int(name.split('.')[0]);prior=number if self.cycle else number+1
            return dict(schemaVersion=SCHEMA,predecessorSelectionPin=dict(file=str(prior)+'.json',bytes=1,sha256='a'*64),
                buildPin={},standardPackagePin={},targetActivationEvidencePins={},packageDeltaReviewPin={})
        def pinned(self,p):return self.read(p['file'])
    with pytest.raises(ValueError,match='CYCLE'):m._repeat_selection_chain(Records(True),'0.json')
    with pytest.raises(ValueError,match='DEPTH'):m._repeat_selection_chain(Records(),'0.json')


def test_repeat_loader_is_a_formal_versioned_entrypoint():
    assert callable(getattr(subject(),'load_repeated_target_successor_installation',None))


def test_explicit_api_validation_can_record_unavailable_before_without_fake_success(repeated_inputs):
    m=subject();api=deepcopy(activation_case(B9)['activations']['58']['result']['originalApi']);target=repeated_inputs['predecessor']['effectiveControllersByHost']['58'][-1]['targetConfigRef']
    for app in api['applications']:app['freshTargetConfigRefs']=[]
    assert callable(getattr(m.activated,'_api_selection',None))
    m.activated._api_selection(api,target,available=False)
    with pytest.raises(ValueError):m.activated._api_selection(api,target,available=True)
    api['applications'][0]['historyErrorCode']='UNRELATED_HISTORY_FAILURE'
    with pytest.raises(ValueError):m.activated._api_selection(api,target,available=False)


def unavailable_api_case():
    import base64
    m=subject();old=activation_case(B9);r=deepcopy(old['activations']['58']['result'])
    owner=deepcopy(old['predecessor']['targetOwners']['58']);target=r['targetConfigRef'];core=r['candidate']['previousController']
    owner['operationsRoot']='/control/operations';owner['targets'][target]['replacement']['stateRoot']='/control/replacement'
    operation='smallapp-'+'4'*32;root='/control/operations/'+operation
    request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId=operation,action='RESTORE',sourceConfigRef=m.activated.activation.SOURCES[0],
        parentChainRef=None,recoveryPointRef='smallapp-'+'5'*32,targetConfigRef=target)
    worker=dict(schemaVersion='backup-restore-operation-result/v1',operationId=operation,requestId=operation,action='RESTORE',
        state='FAILED_RETAINED',actualExitCode=1,data=dict(mutationDispatched=False))
    originals={}
    for name,value,filename in (('request',request,'request.json'),('configuration',owner,'configuration.json'),('workerResult',worker,'worker-result.json')):
        raw=canonical(value);originals[name]=dict(pin=pin(root+'/'+filename,raw),rawBase64=base64.b64encode(raw).decode())
    packet=dict(schemaVersion='MainTargetRetainedFailureOriginals/v1',status='PASS',serverWrites=False,observedAt=r['observedAt'],
        host=r['host'],operationId=operation,operationRoot=root,targetConfigRef=target,predecessorController=deepcopy(core),originals=originals)
    r['originalApi']=deepcopy(r['originalApi'])
    for app in r['originalApi']['applications']:app['freshTargetConfigRefs']=[]
    api=dict(observedAt=r['observedAt'],host=r['host'],targetConfigRef=target,pid=core['pid'],controlConfigurationPin=core['controlConfigurationPin'],
        httpStatus=200,api=deepcopy(r['originalApi']),serverWrites=False)
    result=dict(clearancePin=pin('/control/replacement/'+operation+'/recovery-clearance.json',b'formal-clearance'),
        releasePin=pin(root+'/resource-recovery-release.json',b'formal-release'),originalState='FAILED_RETAINED',restoreDispatched=False,nextRequestMustUseSamePoint=True)
    context=dict(originalsPacket=packet,predecessorApiObservation=api,clearanceResult=result)
    r.update(beforeApiState='RETAINED_FAILURE_UNAVAILABLE',retainedFailureAdmission=dict(schemaVersion='MainTargetRetainedFailureApiAdmission/v1',
        originalsPacketPin=pin('/private/originals.json',canonical(packet)),predecessorApiObservationPin=pin('/private/api.json',canonical(api)),
        clearanceResultPin=pin('/private/clearance.json',canonical(result))))
    return r,owner,context


def test_before_unavailable_keeps_real_api_and_requires_formal_clearance_originals():
    r,owner,context=unavailable_api_case();before=deepcopy(r)
    assert callable(getattr(subject(),'_verify_repeat_api',None))
    subject()._verify_repeat_api(r,owner,owner,context)
    assert r==before and all(a['freshTargetConfigRefs']==[] for a in r['originalApi']['applications'])


def test_before_precise_old_no_mutation_error_is_retained_after_formal_clearance():
    r,owner,c=unavailable_api_case();r['originalApi']={'errorCode':'RECOVERY_NO_MUTATION_NOT_PROVEN'}
    c['predecessorApiObservation'].update(httpStatus=500,api=deepcopy(r['originalApi']))
    subject()._verify_repeat_api(r,owner,owner,c)
    assert r['originalApi']=={'errorCode':'RECOVERY_NO_MUTATION_NOT_PROVEN'}


@pytest.mark.parametrize('problem',['other_error','extra_field','wrong_status','successful_shape_500'])
def test_before_http500_is_not_a_generic_unavailable_fallback(problem):
    r,owner,c=unavailable_api_case();r['originalApi']={'errorCode':'RECOVERY_NO_MUTATION_NOT_PROVEN'}
    c['predecessorApiObservation'].update(httpStatus=500)
    if problem=='other_error':r['originalApi']['errorCode']='UNKNOWN_ERROR'
    elif problem=='extra_field':r['originalApi']['fallback']=True
    elif problem=='wrong_status':c['predecessorApiObservation']['httpStatus']=200
    else:r['originalApi']=deepcopy(c['predecessorApiObservation']['api'])
    c['predecessorApiObservation']['api']=deepcopy(r['originalApi'])
    with pytest.raises(ValueError):subject()._verify_repeat_api(r,owner,owner,c)


@pytest.mark.parametrize('problem',['context','state','controller','configuration','worker','operation','request','api','after','points','clearance','restore','unknown'])
def test_before_unavailable_does_not_bypass_other_upgrade_contracts(problem):
    import base64
    r,owner,c=unavailable_api_case()
    if problem=='context':c=None
    elif problem=='state':r['beforeApiState']='UNKNOWN'
    elif problem=='controller':c['originalsPacket']['predecessorController']['pid']+=1
    elif problem in ('configuration','worker','request'):
        name={'configuration':'configuration','worker':'workerResult','request':'request'}[problem];row=c['originalsPacket']['originals'][name]
        value=json.loads(base64.b64decode(row['rawBase64']))
        if problem=='configuration':value['operationsRoot']='/foreign'
        elif problem=='worker':value['data']['mutationDispatched']=True
        else:value['recoveryPointRef']=None
        raw=canonical(value);row.update(pin=pin(row['pin']['path'],raw),rawBase64=base64.b64encode(raw).decode())
    elif problem=='operation':c['originalsPacket']['operationId']='smallapp-'+'0'*32
    elif problem=='api':r['originalApi']['applications'][0]['historyErrorCode']='UNKNOWN_HISTORY_FAILURE'
    elif problem=='after':r['apiSelection']['applications'][0]['freshTargetConfigRefs']=[]
    elif problem=='points':r['apiSelection']['applications'][0]['recoveryPointRefs'].append('unrelated')
    elif problem=='clearance':c['clearanceResult']['clearancePin']['path']='/foreign/recovery-clearance.json'
    elif problem=='restore':c['clearanceResult']['restoreDispatched']=True
    else:r['retainedFailureAdmission']['unknown']=True
    with pytest.raises(ValueError):subject()._verify_repeat_api(r,owner,owner,c)


@pytest.fixture
def local_repeated_chain(tmp_path,monkeypatch,repeated_inputs):
    """Real finite local files; isolate only the separately tested historical root."""
    m=subject();first=activation_case(B9);old=make_local_inputs(tmp_path,first);task=old['task'];private=old['private']
    monkeypatch.setattr(m.activated,'load_activated_target_installation',lambda *a,**kw:deepcopy(old['predecessor']))
    result=m.load_activated_target_successor_installation(task,private,selection_file='successor.json')
    wrappers={h:json.loads((private/('activation-'+h+'.json')).read_text(encoding='utf-8')) for h in ('57','58','59')}
    result['currentPreservationDocumentsByHost']=m.bind_current_preservation_documents(result,wrappers)
    result['retainedFailurePinsByHost']={h:deepcopy(w['result']['retainedFailurePins']) for h,w in wrappers.items()}
    previous_build=first['build'];previous_raw=first['package_raw'];inputs=[]
    def report(name,value):
        raw=canonical(value);(task/name).write_bytes(raw);return localpin(name,value)
    for letter in ('e','f'):
        commit=letter*40;files=payload(previous_raw)
        for member in PROFILE_MEMBERS:files[member]+=('\nGEN_'+letter+'=True\n').encode()
        build,raw,_=package_build(files,commit);buildpin=report('build-'+letter+'.json',build)
        packagefile=private/('package-'+letter+'.tgz');packagefile.write_bytes(raw)
        k=deepcopy(repeated_inputs);k.update(predecessor=result,predecessor_selection_pin=result['selectionPin'],
            predecessor_selection_raw=(task/result['selectionPin']['file']).read_bytes(),predecessor_build=previous_build,
            predecessor_build_raw=canonical(previous_build),predecessor_package_raw=previous_raw,
            build=build,build_pin=buildpin,build_raw=canonical(build),package_raw=raw,
            new_engine='/control/engine-main-program-'+commit[:7],configuration_root='/control/configuration/main-target-'+commit[:7]+'-r1',
            preservation_documents=result['currentPreservationDocumentsByHost']['58'])
        k['package_delta_review']=delta(k);k['package_delta_review']['standardPackagePin']=pin(str(packagefile),raw);repin_review(k)
        report(k['package_delta_review_pin']['file'],k['package_delta_review'])
        activation=repeat_activation(k);evidence={}
        for host,w in activation['activations'].items():
            carrier=private/('carrier-'+letter+'-'+host+'.py');carrier.write_bytes(b'finite pinned local carrier')
            w['scriptPin']=pin(str(carrier),carrier.read_bytes());seal_successor(w)
            file=private/('activation-'+letter+'-'+host+'.json');file.write_bytes(canonical(w));evidence[host]=pin(str(file),file.read_bytes())
        selection=dict(schemaVersion=SCHEMA,predecessorSelectionPin=result['selectionPin'],buildPin=buildpin,
            standardPackagePin=k['package_delta_review']['standardPackagePin'],targetActivationEvidencePins=evidence,
            packageDeltaReviewPin=k['package_delta_review_pin'])
        selection_pin=report('selection-'+letter+'.json',selection)
        result=m.verify_target_successor_activations(**activation)
        result.update(selection=selection,selectionPin=selection_pin)
        result['currentPreservationDocumentsByHost']=m.bind_current_preservation_documents(result,activation['activations'])
        result['retainedFailurePinsByHost']={h:deepcopy(w['result']['retainedFailurePins']) for h,w in activation['activations'].items()}
        inputs.append(k);previous_build=build;previous_raw=raw
    return dict(task=task,private=private,expected=result,inputs=inputs,root=old)


def test_two_repeated_generations_load_every_original_without_rewriting_v1(local_repeated_chain):
    import main_program_current_installation as current
    k=local_repeated_chain
    result=current.load_current_target_installation(k['task'],k['private'],selection_file='selection-f.json')
    assert result['selectionPin']==k['expected']['selectionPin']
    assert result['currentPreservationDocumentsByHost']==k['expected']['currentPreservationDocumentsByHost']
    assert result['retainedFailurePinsByHost']==k['expected']['retainedFailurePinsByHost']
    assert result['effectiveControllersByHost']==k['expected']['effectiveControllersByHost']
    for host in ('57','58','59'):
        assert result['targetRuntimeSpecs'][host]['original']==k['root']['predecessor']['targetRuntimeSpecs'][host]['original']
    names={Path(p['path']).name for p in result['inputPins']}
    assert {'review-eeeeeee.json','review-fffffff.json','selection-e.json','selection-f.json','activation-e-58.json'}<=names


@pytest.mark.parametrize('problem',['earlier_review','earlier_carrier','earlier_wrapper','earlier_selection','latest_unknown','package','build'])
def test_repeated_loader_rejects_drift_anywhere_in_verified_chain(local_repeated_chain,problem):
    import main_program_current_installation as current
    k=local_repeated_chain
    files={'earlier_review':k['task']/'review-eeeeeee.json','earlier_carrier':k['private']/'carrier-e-58.py',
        'earlier_wrapper':k['private']/'activation-e-59.json','earlier_selection':k['task']/'selection-e.json',
        'package':k['private']/'package-e.tgz','build':k['task']/'build-e.json'}
    if problem=='latest_unknown':
        file=k['task']/'selection-f.json';v=json.loads(file.read_text(encoding='utf-8'));v['unknown']=True;file.write_bytes(canonical(v))
    else:
        file=files[problem];file.write_bytes(file.read_bytes()+b' ')
    with pytest.raises(ValueError):current.load_current_target_installation(k['task'],k['private'],selection_file='selection-f.json')
