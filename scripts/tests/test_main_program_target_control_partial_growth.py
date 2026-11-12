"""Two reviewed mixed predecessors admit one fixed added retry module."""
from copy import deepcopy
from types import SimpleNamespace
import json
from pathlib import Path
import pytest
from test_main_program_target_control_successor import subject,canonical,localpin,package_build,pin,digest,seal_successor
from test_main_program_target_control_successor_repeat import repeated_inputs,local_repeated_chain,payload,PROFILE_MEMBERS,repin_review,construct
from test_main_program_target_control_partial_predecessor import local_partial

CHANGED=('common/recovery_main_target.py','common/recovery_program_activation.py','common/recovery_program_execution.py',
    'common/recovery_program_evidence.py','common/recovery_program_restore.py','common/recovery_program_targets.py','common/recovery_program_native.py',
    'control/recovery_control_target_availability.py')
ADDED='common/recovery_program_retry.py'
FROM_PREPARATION='MAIN_TARGET_RETAINED_RETRY_FROM_PREPARATION/v1'
FROM_READER='MAIN_TARGET_RETAINED_RETRY_FROM_READER/v1'


@pytest.fixture
def named_partial(tmp_path,monkeypatch):
    import test_main_program_target_control_successor as old_suite
    original=old_suite.old_inputs.__wrapped__
    def finite_named_inputs():
        k=original()
        for member in CHANGED:
            if member not in k['previous_package_files']:
                filler=next(n for n in k['previous_package_files'] if n.startswith('common/unchanged_'))
                for key in ('previous_package_files','package_files'):k[key][member]=k[key].pop(filler)
        return k
    monkeypatch.setattr(old_suite,'old_inputs',SimpleNamespace(__wrapped__=finite_named_inputs))
    k=repeated_inputs.__wrapped__()
    return local_partial.__wrapped__(local_repeated_chain.__wrapped__(tmp_path,monkeypatch,k))


def growth_inputs(k,host):
    m=subject();prior=m.load_partial_target_predecessor(k['task'],k['private'],selection_file='partial.json')
    artifact=prior['targetPredecessorArtifactsByHost'][host]
    oldraw=Path(artifact['standardPackagePin']['path']).read_bytes()
    oldbuild=json.loads((k['task']/artifact['buildPin']['file']).read_bytes())
    # One new payload from the actual activated host's predecessor. Its four
    # earlier changes already exist on57 and are new changes for58/59.
    files=payload(Path(prior['targetPredecessorArtifactsByHost']['57']['standardPackagePin']['path']).read_bytes())
    for member in CHANGED:files[member]+=b'\nRETAINED_RETRY=True\n'
    files[ADDED]=b'RETAINED_RETRY_AUTHORITY=True\n'
    build,raw,_=package_build(files,'9'*40);build['packages'][0]['fileCount']=154
    buildpin=localpin('mixed154-build.json',build)
    inputs=dict(predecessor=prior,predecessor_selection_pin=prior['selectionPin'],
        predecessor_selection_raw=(k['task']/'partial.json').read_bytes(),predecessor_build=oldbuild,
        predecessor_build_raw=canonical(oldbuild),predecessor_package_raw=oldraw,build=build,build_pin=buildpin,
        build_raw=canonical(build),package_raw=raw,host=host,preservation_documents=prior['currentPreservationDocumentsByHost'][host],
        configuration_root='/control/configuration/main-target-9999999-r1',new_engine='/control/engine-main-program-9999999',
        retained_failure_pins=prior['retainedFailurePinsByHost'][host])
    old=payload(oldraw)
    review=dict(schemaVersion='MainProgramTargetControlPackageDeltaReview/v2',status='REVIEWED',
        profileId=FROM_PREPARATION if host=='57' else FROM_READER,
        predecessorSelectionPin=prior['selectionPin'],predecessorCommit=oldbuild['targetCommit'],sourceCommit=build['targetCommit'],
        predecessorBuildPin=artifact['buildPin'],buildPin=buildpin,previousPackagePin=artifact['standardPackagePin'],
        standardPackagePin=pin('/private/mixed154.tgz',raw),
        changedMembers=[dict(member=n,previousSha256=digest(old[n]),sha256=digest(files[n])) for n in sorted(old) if old[n]!=files[n]],
        addedMembers=[dict(member=ADDED,sha256=digest(files[ADDED]))])
    inputs['package_delta_review']=review;repin_review(inputs)
    return inputs


@pytest.mark.parametrize('host',['57','58','59'])
def test_fixed_v3_profile_builds_154_candidate_and_159_exclusive_writes(named_partial,host):
    k=growth_inputs(named_partial,host);m=subject();candidate=construct(k)
    assert candidate['schemaVersion']=='MainProgramTargetControlSuccessorCandidate/v3'
    assert candidate['package']['fileCount']==154 and candidate['previousPackage']['fileCount']==153
    plan=m.build_target_successor_staging_plan(candidate=candidate,**k)
    assert plan['schemaVersion']=='MainProgramTargetSuccessorStagingPlan/v3' and plan['payloadFileCount']==154
    assert len(plan['writes'])==159 and len(plan['retainedPins'])==170
    prior=k['predecessor'];old=candidate['previousController']
    spec=m.build_target_successor_runtime_spec(current_spec=prior['targetRuntimeSpecs'][host]['successor'],
        retained_history_spec=prior['targetRuntimeSpecs'][host]['original'],candidate=candidate,
        dropin_pin=pin('/etc/systemd/system/'+old['service']+'.d/zzzzzz-growth.conf',b'growth'),successor_pid=old['pid']+2000)
    assert spec['current']['controllers'][-1]['fileCount']==154
    assert prior['targetRuntimeSpecs'][host]['successor']['current']['controllers'][-1]['fileCount']==153


@pytest.mark.parametrize('problem',['unknown_profile','wrong_profile','missing_added','extra_added','added_sha','missing_changed','extra_changed','changed_sha','deleted','extra_new','arbitrary_count'])
def test_v3_profile_is_a_fixed_review_not_a_caller_selected_whitelist(named_partial,problem):
    k=growth_inputs(named_partial,'57');r=k['package_delta_review']
    if problem=='unknown_profile':r['profileId']='SELF_SIGNED/v1'
    elif problem=='wrong_profile':r['profileId']=FROM_READER
    elif problem=='missing_added':r['addedMembers']=[]
    elif problem=='extra_added':r['addedMembers'].append(dict(member='common/unreviewed.py',sha256='0'*64))
    elif problem=='added_sha':r['addedMembers'][0]['sha256']='0'*64
    elif problem=='missing_changed':r['changedMembers'].pop()
    elif problem=='extra_changed':r['changedMembers'].append(dict(member='common/unreviewed.py',previousSha256='0'*64,sha256='1'*64))
    elif problem=='changed_sha':r['changedMembers'][0]['previousSha256']='0'*64
    else:
        files=payload(k['package_raw'])
        if problem=='deleted':del files[next(n for n in files if n.startswith('common/unchanged_'))]
        elif problem=='extra_new':files['common/unreviewed.py']=b'UNREVIEWED=True\n'
        build,raw,_=package_build(files,'9'*40);build['packages'][0]['fileCount']=len(files)+(1 if problem=='arbitrary_count' else 0)
        k.update(build=build,build_raw=canonical(build),build_pin=localpin('mixed154-build.json',build),package_raw=raw)
        r.update(buildPin=k['build_pin'],standardPackagePin=pin('/private/mixed154.tgz',raw))
    repin_review(k)
    with pytest.raises(ValueError):construct(k)


@pytest.fixture
def mixed_local_selection(named_partial):
    k=named_partial;m=subject();first=growth_inputs(k,'57');prior=first['predecessor']
    task=k['task'];private=k['private'];raw=first['package_raw'];build=first['build'];buildpin=first['build_pin']
    packagefile=private/'mixed154.tgz';packagefile.write_bytes(raw);packagepin=pin(str(packagefile),raw)
    (task/buildpin['file']).write_bytes(canonical(build));reviews={};evidence={}
    def manifest(raw):
        import io,tarfile
        with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:return archive.extractfile('package.json').read()
    for host in ('57','58','59'):
        inputs=first if host=='57' else growth_inputs(k,host)
        inputs.update(package_raw=raw,build=build,build_raw=canonical(build),build_pin=buildpin)
        inputs['package_delta_review'].update(buildPin=buildpin,standardPackagePin=packagepin)
        review=inputs['package_delta_review'];reviewpin=localpin('mixed-review-'+host+'.json',review)
        inputs.update(package_delta_review_pin=reviewpin,package_delta_review_raw=canonical(review))
        (task/reviewpin['file']).write_bytes(canonical(review));reviews[host]=reviewpin
        candidate=construct(inputs);spec=prior['targetRuntimeSpecs'][host]['successor'];old=candidate['previousController']
        originalfile=private/('activation-e-57.json' if host=='57' else 'activation-'+host+'.json')
        wrapper=json.loads(originalfile.read_bytes());r=wrapper['result'];before=deepcopy(r['after'])
        drop=pin('/etc/systemd/system/'+old['service']+'.d/zzzzzz-growth.conf',b'growth')
        newspec=m.build_target_successor_runtime_spec(current_spec=spec,retained_history_spec=prior['targetRuntimeSpecs'][host]['original'],
            candidate=candidate,dropin_pin=drop,successor_pid=old['pid']+2000)
        row=newspec['current']['controllers'][-1];control=m.activated._document(candidate['newDocuments'],candidate['controller']['controlPin'])
        after=deepcopy(before);observed=after['controllers'][-1]
        observed.update(pid=row['pid'],environmentVerification=dict(mode='CONFIG_EXACT',environmentSha256='e'*64),
            argvSha256=digest(('\0'.join([control['pythonPin']['path'],'-B',row['engine']+'/control_entry.py','serve','--config-pin',canonical(row['controlConfigurationPin']).decode()])+'\0').encode()))
        observed['properties'].update(MainPID=str(row['pid']),DropInPaths=observed['properties']['DropInPaths']+' '+drop['path'])
        after['packagePins'][-1]=pin(row['engine']+'/package.json',manifest(raw))
        directory='/control/control-activation-main-target-9999999-r1'
        r.update(schemaVersion='MainProgramTargetControlSuccessorActivation/v3',sourceCommit=build['targetCommit'],candidate=candidate,
            beforeApiState='AVAILABLE',retainedFailureAdmission=None,predecessorSelectionPin=prior['selectionPin'],
            predecessorActivationReceiptPin=prior['activationReceiptPins'][('57','58','59').index(host)],packageDeltaReviewPin=reviewpin,
            currentRuntimeSpec=spec,retainedHistoryRuntimeSpec=prior['targetRuntimeSpecs'][host]['original'],successorRuntimeSpec=newspec,
            currentController=row,before=before,after=after,dropinPin=drop,
            createdPaths=[directory,directory+'/before.private.json',drop['path']])
        script=private/('mixed-carrier-'+host+'.py');script.write_bytes(b'# finite pure proof carrier\n')
        wrapper['scriptPin']=pin(str(script),script.read_bytes());seal_successor(wrapper)
        output=private/('mixed-activation-'+host+'.json');output.write_bytes(canonical(wrapper));evidence[host]=pin(str(output),output.read_bytes())
    selection=dict(schemaVersion=m.MIXED_SELECTION_SCHEMA,predecessorSelectionPin=prior['selectionPin'],buildPin=buildpin,
        standardPackagePin=packagepin,packageDeltaReviewPinsByHost=reviews,targetActivationEvidencePins=evidence)
    (task/'mixed.json').write_bytes(canonical(selection))
    return dict(**k,mixed=selection)


def test_complete_v3_local_loader_verifies_all_hosts_over_their_actual_predecessors(mixed_local_selection):
    k=mixed_local_selection
    import main_program_current_installation as current
    result=current.load_current_target_installation(k['task'],k['private'],selection_file='mixed.json')
    assert result['status']=='ACTIVATED' and result['installationVerified'] is True and result['runtimeVerified'] is False
    prior=result['predecessorInstallation'];assert prior['status']=='PARTIALLY_ACTIVATED' and prior['installationVerified'] is False
    for host in ('57','58','59'):
        assert result['effectiveControllersByHost'][host][-1]['sourceCommit']=='9'*40
        assert result['effectiveControllersByHost'][host][-1]['fileCount']==154
        assert result['targetRuntimeSpecs'][host]['original']==prior['targetRuntimeSpecs'][host]['original']
    assert prior['controllerBuildBindings']['57']['target']['sourceCommit']=='e'*40
    assert prior['controllerBuildBindings']['58']['target']['sourceCommit'].startswith('b9caa00')


@pytest.mark.parametrize('problem',['missing_host','review_swap','failed_stage','changed_receipt','cycle','no_growth'])
def test_complete_v3_loader_rejects_unproven_or_mixed_artifacts(mixed_local_selection,problem):
    k=mixed_local_selection;selected=deepcopy(k['mixed']);task=k['task'];private=k['private']
    if problem=='missing_host':selected['targetActivationEvidencePins'].pop('59')
    elif problem=='review_swap':selected['packageDeltaReviewPinsByHost']['57']=selected['packageDeltaReviewPinsByHost']['58']
    elif problem in ('failed_stage','changed_receipt'):
        file=Path(selected['targetActivationEvidencePins']['58']['path']);w=json.loads(file.read_bytes())
        if problem=='failed_stage':w['mode']='PREPARE'
        else:w['result']['currentController']['pid']+=1
        seal_successor(w);file.write_bytes(canonical(w));selected['targetActivationEvidencePins']['58']=pin(str(file),file.read_bytes())
    elif problem=='cycle':selected['predecessorSelectionPin']=localpin('mixed.json',selected)
    else:
        selected['packageDeltaReviewPinsByHost']['57']=k['partial']['packageDeltaReviewPin']
    (task/'mixed.json').write_bytes(canonical(selected))
    with pytest.raises(ValueError):subject().load_mixed_target_successor_installation(task,private,selection_file='mixed.json')
