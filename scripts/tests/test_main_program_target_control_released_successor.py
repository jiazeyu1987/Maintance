"""Finite metadata contracts for the one reviewed 154-to-154 transition."""
from copy import deepcopy
import io
import json
from pathlib import Path
import tarfile
from types import SimpleNamespace

import pytest

import test_main_program_target_control_successor as old_suite
import test_main_program_target_control_partial_growth as growth
from test_main_program_target_control_partial_growth import mixed_local_selection
from test_main_program_target_control_successor import subject,canonical,localpin,package_build,pin,digest,seal_successor
from test_main_program_target_control_successor_repeat import payload,repin_review,construct

MEMBER='control/recovery_control_smallapp_native.py'
PROFILE='MAIN_TARGET_RELEASED_STATE_PROJECTION/v1'
REVIEW_SCHEMA='MainProgramTargetControlPackageDeltaReview/v3'


@pytest.fixture
def named_partial(tmp_path,monkeypatch):
    original=old_suite.old_inputs.__wrapped__
    def include_native():
        k=original()
        if MEMBER not in k['previous_package_files']:
            filler=next(n for n in k['previous_package_files'] if n.startswith('common/unchanged_'))
            for key in ('previous_package_files','package_files'):k[key][MEMBER]=k[key].pop(filler)
        return k
    monkeypatch.setattr(old_suite,'old_inputs',SimpleNamespace(__wrapped__=include_native))
    return growth.named_partial.__wrapped__(tmp_path,monkeypatch)


def released_inputs(k,host):
    m=subject();prior=m.load_mixed_target_successor_installation(k['task'],k['private'],selection_file='mixed.json')
    selected=prior['selection'];oldraw=Path(selected['standardPackagePin']['path']).read_bytes()
    oldbuild=json.loads((k['task']/selected['buildPin']['file']).read_bytes())
    old=payload(oldraw);files=deepcopy(old);files[MEMBER]+=b'\nRELEASED_STATE_PROJECTION=True\n'
    build,raw,_=package_build(files,'c'*40);build['packages'][0]['fileCount']=154
    buildpin=localpin('released154-build.json',build)
    review=dict(schemaVersion=REVIEW_SCHEMA,status='REVIEWED',profileId=PROFILE,
        predecessorSelectionPin=prior['selectionPin'],predecessorCommit=oldbuild['targetCommit'],sourceCommit=build['targetCommit'],
        predecessorBuildPin=selected['buildPin'],buildPin=buildpin,previousPackagePin=selected['standardPackagePin'],
        standardPackagePin=pin(str(k['private']/'released154.tgz'),raw),
        changedMembers=[dict(member=MEMBER,previousSha256=digest(old[MEMBER]),sha256=digest(files[MEMBER]))])
    result=dict(predecessor=prior,predecessor_selection_pin=prior['selectionPin'],
        predecessor_selection_raw=(k['task']/'mixed.json').read_bytes(),predecessor_build=oldbuild,
        predecessor_build_raw=canonical(oldbuild),predecessor_package_raw=oldraw,build=build,build_pin=buildpin,
        build_raw=canonical(build),package_raw=raw,host=host,preservation_documents=prior['currentPreservationDocumentsByHost'][host],
        configuration_root='/control/configuration/main-target-ccccccc-r1',new_engine='/control/engine-main-program-ccccccc',
        retained_failure_pins=prior['retainedFailurePinsByHost'][host],package_delta_review=review)
    repin_review(result)
    return result


@pytest.mark.parametrize('host',['57','58','59'])
def test_reviewed_same_154_member_set_builds_and_retains_all_originals(mixed_local_selection,host):
    k=released_inputs(mixed_local_selection,host);m=subject();before=deepcopy(k);candidate=construct(k)
    assert k==before
    assert candidate['schemaVersion']=='MainProgramTargetControlSuccessorCandidate/v3'
    assert candidate['package']['fileCount']==candidate['previousPackage']['fileCount']==154
    plan=m.build_target_successor_staging_plan(candidate=candidate,**k)
    assert len(plan['writes'])==159 and len(plan['retainedPins'])==171
    prior=k['predecessor'];old=candidate['previousController']
    spec=m.build_target_successor_runtime_spec(current_spec=prior['targetRuntimeSpecs'][host]['successor'],
        retained_history_spec=prior['targetRuntimeSpecs'][host]['original'],candidate=candidate,
        dropin_pin=pin('/etc/systemd/system/'+old['service']+'.d/zzzzzz-released.conf',b'released'),successor_pid=old['pid']+2000)
    assert spec['current']['controllers'][-1]['fileCount']==154
    assert prior['targetRuntimeSpecs'][host]['successor']['current']['controllers'][-1]['fileCount']==154


@pytest.mark.parametrize('problem',['unknown_profile','old_profile','growth_schema','missing_changed','extra_changed','old_sha','new_sha',
    'added_field','other_member','added','deleted','no_change','declared_count','unverified','old_controller_count','old_manifest_count'])
def test_same_154_profile_rejects_every_unreviewed_change(mixed_local_selection,problem):
    k=released_inputs(mixed_local_selection,'58');r=k['package_delta_review']
    if problem=='unknown_profile':r['profileId']='CALLER_SELECTED/v1'
    elif problem=='old_profile':r['profileId']=growth.FROM_PREPARATION
    elif problem=='growth_schema':r['schemaVersion']='MainProgramTargetControlPackageDeltaReview/v2'
    elif problem=='missing_changed':r['changedMembers']=[]
    elif problem=='extra_changed':r['changedMembers'].append(dict(member='common/unreviewed.py',previousSha256='0'*64,sha256='1'*64))
    elif problem=='old_sha':r['changedMembers'][0]['previousSha256']='0'*64
    elif problem=='new_sha':r['changedMembers'][0]['sha256']='0'*64
    elif problem=='added_field':r['addedMembers']=[]
    elif problem=='unverified':k['predecessor']['installationVerified']=False
    elif problem=='old_controller_count':k['predecessor']['effectiveControllersByHost']['58'][-1]['fileCount']=153
    elif problem=='old_manifest_count':
        k['predecessor_build']['packages'][0]['fileCount']=153
        k['predecessor_build_raw']=canonical(k['predecessor_build'])
    else:
        files=payload(k['package_raw'])
        if problem=='other_member':files[next(n for n in files if n.startswith('common/unchanged_'))]+=b'\nUNREVIEWED=True\n'
        elif problem=='added':files['common/unreviewed.py']=b'UNREVIEWED=True\n'
        elif problem=='deleted':del files[next(n for n in files if n.startswith('common/unchanged_'))]
        elif problem=='no_change':files=payload(k['predecessor_package_raw'])
        build,raw,_=package_build(files,'c'*40);build['packages'][0]['fileCount']=len(files)+(1 if problem=='declared_count' else 0)
        k.update(build=build,build_raw=canonical(build),build_pin=localpin('released154-build.json',build),package_raw=raw)
        r.update(buildPin=k['build_pin'],standardPackagePin=pin(str(mixed_local_selection['private']/'released154.tgz'),raw))
    repin_review(k)
    with pytest.raises(ValueError):construct(k)


def test_verified_mixed_root_accepts_one_complete_repeated_154_generation(mixed_local_selection):
    data=mixed_local_selection;m=subject();first=released_inputs(data,'57');prior=first['predecessor']
    task=data['task'];private=data['private'];raw=first['package_raw'];build=first['build'];buildpin=first['build_pin']
    (private/'released154.tgz').write_bytes(raw);(task/buildpin['file']).write_bytes(canonical(build))
    review=first['package_delta_review'];reviewpin=first['package_delta_review_pin'];(task/reviewpin['file']).write_bytes(canonical(review))
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:manifest=archive.extractfile('package.json').read()
    evidence={}
    for host in ('57','58','59'):
        k=first if host=='57' else released_inputs(data,host)
        k.update(package_raw=raw,build=build,build_raw=canonical(build),build_pin=buildpin,
            package_delta_review=review,package_delta_review_pin=reviewpin,package_delta_review_raw=canonical(review))
        candidate=construct(k);old=candidate['previousController'];current=prior['targetRuntimeSpecs'][host]['successor']
        wrapper=json.loads(Path(prior['selection']['targetActivationEvidencePins'][host]['path']).read_bytes())
        result=wrapper['result'];before=deepcopy(result['after'])
        drop=pin('/etc/systemd/system/'+old['service']+'.d/zzzzzz-released.conf',b'released')
        spec=m.build_target_successor_runtime_spec(current_spec=current,
            retained_history_spec=prior['targetRuntimeSpecs'][host]['original'],candidate=candidate,dropin_pin=drop,successor_pid=old['pid']+2000)
        row=spec['current']['controllers'][-1];control=m.activated._document(candidate['newDocuments'],candidate['controller']['controlPin'])
        after=deepcopy(before);observed=after['controllers'][-1]
        observed.update(pid=row['pid'],environmentVerification=dict(mode='CONFIG_EXACT',environmentSha256='e'*64),
            argvSha256=digest(('\0'.join([control['pythonPin']['path'],'-B',row['engine']+'/control_entry.py','serve','--config-pin',canonical(row['controlConfigurationPin']).decode()])+'\0').encode()))
        observed['properties'].update(MainPID=str(row['pid']),DropInPaths=observed['properties']['DropInPaths']+' '+drop['path'])
        after['packagePins'][-1]=pin(row['engine']+'/package.json',manifest)
        directory='/control/control-activation-main-target-ccccccc-r1'
        result.update(schemaVersion='MainProgramTargetControlSuccessorActivation/v3',sourceCommit=build['targetCommit'],candidate=candidate,
            beforeApiState='AVAILABLE',retainedFailureAdmission=None,predecessorSelectionPin=prior['selectionPin'],
            predecessorActivationReceiptPin=prior['activationReceiptPins'][('57','58','59').index(host)],packageDeltaReviewPin=reviewpin,
            currentRuntimeSpec=current,retainedHistoryRuntimeSpec=prior['targetRuntimeSpecs'][host]['original'],successorRuntimeSpec=spec,
            currentController=row,before=before,after=after,dropinPin=drop,
            createdPaths=[directory,directory+'/before.private.json',drop['path']])
        script=private/('released-carrier-'+host+'.py');script.write_bytes(b'# finite pure metadata proof\n')
        wrapper['scriptPin']=pin(str(script),script.read_bytes());seal_successor(wrapper)
        output=private/('released-activation-'+host+'.json');output.write_bytes(canonical(wrapper));evidence[host]=pin(str(output),output.read_bytes())
    selected=dict(schemaVersion=m.REPEAT_SELECTION_SCHEMA,predecessorSelectionPin=prior['selectionPin'],buildPin=buildpin,
        standardPackagePin=review['standardPackagePin'],packageDeltaReviewPin=reviewpin,targetActivationEvidencePins=evidence)
    (task/'released.json').write_bytes(canonical(selected))
    result=m.load_repeated_target_successor_installation(task,private,selection_file='released.json')
    assert result['status']=='ACTIVATED' and result['installationVerified'] is True
    assert result['predecessorInstallation']['selection']['schemaVersion']==m.MIXED_SELECTION_SCHEMA
    for host in ('57','58','59'):
        assert result['effectiveControllersByHost'][host][-1]['sourceCommit']=='c'*40
        assert result['effectiveControllersByHost'][host][-1]['fileCount']==154
        assert result['targetRuntimeSpecs'][host]['original']==prior['targetRuntimeSpecs'][host]['original']
