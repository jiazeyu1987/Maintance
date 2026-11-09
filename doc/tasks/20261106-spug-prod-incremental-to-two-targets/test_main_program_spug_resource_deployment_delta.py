"""Actual temporary filesystem contracts, never a real Spug installation.

The existing resource fixture uses its own temporary Git repository and executes
its tiny real pytest proof. Its external transport is an explicit local boundary.
No Docker, browser, server, or production workspace Git operation is performed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import main_program_spug_resource_activation as subject
import main_program_spug_publication as publication
from test_main_program_spug_resource_activation import resource, put, digest, Transport

CHANGED=('smallapp_adapter.py','smallapp-ui/app.js','smallapp-ui/simple.js')


@pytest.fixture
def delta_case(resource):
    task,private,root,runtime,report,observed,old_inputs=resource
    for name in CHANGED[1:]:
        raw=('// previous '+name+'\n').encode('utf-8');(runtime/name).write_bytes(raw)
        next(p for p in observed['spug']['productPins'] if p['path']==subject.REMOTE+name).update(digest(raw))
    put(private/'observation.private.json',observed)
    changes=[dict(relativePath=name,beforePin=deepcopy(next(p for p in observed['spug']['productPins']
        if p['path']==subject.REMOTE+name)),afterPin=dict(path=subject.REMOTE+name,
        **report['files']['ops/spug/'+name])) for name in CHANGED]
    delta=dict(schemaVersion='MainProgramSpugResourceDeploymentDelta/v1',sourceCommit=report['sourceCommit'],
        resourceBuildPin=old_inputs['resourceBuildPin'],changes=changes)
    inputs=dict(schemaVersion='MainProgramSpugResourceActivationInputs/v2',resourceBuildPin=old_inputs['resourceBuildPin'],
        deploymentDeltaPin=put(task/'deployment-delta.json',delta),observationPin=publication.file_pin(private/'observation.private.json'))
    put(task/'inputs-v2.json',inputs)
    return dict(task=task,private=private,root=root,runtime=runtime,report=report,observed=observed,
        delta=delta,inputs=inputs,old_inputs=old_inputs)


def prepared(value):
    spec=subject.prepare(value['task'],value['private'],'inputs-v2.json')
    spec['runtime']=str(value['runtime']);return spec


def transport(value):
    result=Transport(value['observed']);original=result.reload
    def reload(expected):
        identity=original(expected)
        for name in CHANGED:
            for refs in (result.observed['spug']['productPins'],result.observed['modulePins']):
                for ref in refs:
                    if ref['path']==subject.REMOTE+name:ref.update(value['report']['files']['ops/spug/'+name])
        return identity
    result.reload=reload
    return result


def repin(value):
    value['inputs']['deploymentDeltaPin']=put(value['task']/'deployment-delta.json',value['delta'])
    value['inputs']['observationPin']=publication.file_pin(value['private']/'observation.private.json')
    put(value['task']/'inputs-v2.json',value['inputs'])


def rich(value):
    paths=list(value['private'].glob('main-program-spug-resource-activation-*.private.json'))
    assert len(paths)==1
    return json.loads(paths[0].read_bytes())


def test_explicit_three_file_prepare_never_dispatches_or_rewrites_build(delta_case):
    value=delta_case;t=transport(value)
    build=value['task']/value['inputs']['resourceBuildPin']['file'];before=build.read_bytes()
    result=subject.run_request(value['task'],value['private'],'inputs-v2.json',transport=t)
    assert result['status']=='PREPARED' and result['runtimeWrites'] is False and t.calls==[]
    assert build.read_bytes()==before and value['report']['changedFiles']==['ops/spug/smallapp_adapter.py']
    assert prepared(value)['deploymentDelta']==value['delta']


@pytest.mark.parametrize('change',['missing-pin','extra-input','unknown-schema','missing-file','duplicate','order',
    'unknown-path','path-escape','before-path','after-path','before-drift','after-build','same-before-after',
    'extra-delta','wrong-commit','wrong-build','fourth-runtime-drift'])
def test_invalid_or_unapproved_delta_refuses_before_transport(delta_case,change):
    value=delta_case;d=value['delta'];i=value['inputs'];t=transport(value)
    if change=='missing-pin':del i['deploymentDeltaPin']
    elif change=='extra-input':i['allowOtherResources']=True
    elif change=='unknown-schema':i['schemaVersion']='MainProgramSpugResourceActivationInputs/v3'
    elif change=='missing-file':d['changes'].pop()
    elif change=='duplicate':d['changes'][1]=deepcopy(d['changes'][0])
    elif change=='order':d['changes'].reverse()
    elif change=='unknown-path':d['changes'][1]['relativePath']='smallapp_entry.py'
    elif change=='path-escape':d['changes'][1]['relativePath']='../app.js'
    elif change=='before-path':d['changes'][1]['beforePin']['path']='/tmp/app.js'
    elif change=='after-path':d['changes'][1]['afterPin']['path']='/tmp/app.js'
    elif change=='before-drift':d['changes'][1]['beforePin']['sha256']='f'*64
    elif change=='after-build':d['changes'][1]['afterPin']['sha256']='f'*64
    elif change=='same-before-after':d['changes'][1]['beforePin']=deepcopy(d['changes'][1]['afterPin'])
    elif change=='extra-delta':d['allowedFallback']=True
    elif change=='wrong-commit':d['sourceCommit']='f'*40
    elif change=='wrong-build':d['resourceBuildPin']['sha256']='f'*64
    else:
        ref=next(p for p in value['observed']['spug']['productPins'] if p['path']==subject.REMOTE+'smallapp-ui/index.html')
        ref['sha256']='f'*64;put(value['private']/'observation.private.json',value['observed'])
    if change!='missing-pin':repin(value)
    else:put(value['task']/'inputs-v2.json',i)
    before={name:(value['runtime']/name).read_bytes() for name in publication.PRODUCT_FILES}
    with pytest.raises(ValueError,match='MAIN_'):
        subject.run_request(value['task'],value['private'],'inputs-v2.json',apply=True,transport=t)
    assert t.calls==[] and all((value['runtime']/n).read_bytes()==raw for n,raw in before.items())


def test_all_three_originals_exist_before_first_runtime_write_and_other_eight_stay(delta_case,monkeypatch):
    value=delta_case;spec=prepared(value);t=transport(value)
    before={n:(value['runtime']/n).read_bytes() for n in publication.PRODUCT_FILES}
    real_replace=subject.os.replace;replaced=[]
    def replace(src,dst):
        archived=list(value['private'].glob('*-originals/*-before.*'))
        assert len(archived)==3
        assert {p.read_bytes() for p in archived}=={before[n] for n in CHANGED}
        replaced.append(Path(dst).relative_to(value['runtime']).as_posix())
        return real_replace(src,dst)
    monkeypatch.setattr(subject.os,'replace',replace)
    result=subject.dispatch_prepared(value['task'],value['private'],spec,apply=True,transport=t)
    assert result['status']=='PASS' and replaced==list(CHANGED) and t.calls==['observe','reload','observe']
    assert all((value['runtime']/n).read_bytes()==(value['root']/'ops/spug'/n).read_bytes() for n in CHANGED)
    assert all((value['runtime']/n).read_bytes()==raw for n,raw in before.items() if n not in CHANGED)
    core=json.loads((value['task']/result['report']).read_bytes())
    assert core['schemaVersion']=='MainProgramSpugResourceActivation/v2'
    assert core['deploymentDeltaPin']==value['inputs']['deploymentDeltaPin']
    assert len(core['replacements'])==3
    assert rich(value)['fileStates']==[{**r,'state':'REPLACED'} for r in rich(value)['fileStates']]
    prior=list(t.calls)
    with pytest.raises(ValueError,match='ATTEMPT_EXISTS'):
        subject.dispatch_prepared(value['task'],value['private'],spec,apply=True,transport=t)
    assert t.calls==prior


@pytest.mark.parametrize('boundary',['second-replace','first-readback','second-receipt','reload'])
def test_partial_failure_reports_real_disk_state_and_preserves_all_originals(delta_case,monkeypatch,boundary):
    value=delta_case;spec=prepared(value);t=transport(value)
    before={n:(value['runtime']/n).read_bytes() for n in CHANGED};real_replace=subject.os.replace
    real_pin=subject.file_pin;real_exclusive=subject.exclusive_bytes;count=[0];fault=[False]
    def replace(src,dst):
        count[0]+=1
        if boundary=='second-replace' and count[0]==2:raise OSError('second atomic replace failed')
        result=real_replace(src,dst)
        if boundary=='first-readback' and count[0]==1:fault[0]=True
        return result
    def pin(path):
        if fault[0] and Path(path)==value['runtime']/CHANGED[0]:
            fault[0]=False;raise OSError('readback failed after real atomic replace')
        return real_pin(path)
    def exclusive(path,raw):
        if boundary=='second-receipt' and Path(path).name=='replacement-1.json':
            raise OSError('receipt write failed after second real replace')
        return real_exclusive(path,raw)
    monkeypatch.setattr(subject.os,'replace',replace);monkeypatch.setattr(subject,'file_pin',pin)
    monkeypatch.setattr(subject,'exclusive_bytes',exclusive)
    if boundary=='reload':t.failure='explicit reload failure'
    with pytest.raises(ValueError,match='CHECK_PRIVATE'):
        subject.dispatch_prepared(value['task'],value['private'],spec,apply=True,transport=t)
    actual=['REPLACED' if (value['runtime']/n).read_bytes()==(value['root']/'ops/spug'/n).read_bytes()
            else 'UNCHANGED' if (value['runtime']/n).read_bytes()==before[n] else 'UNKNOWN' for n in CHANGED]
    assert actual==({'second-replace':['REPLACED','UNCHANGED','UNCHANGED'],
        'first-readback':['REPLACED','UNCHANGED','UNCHANGED'],
        'second-receipt':['REPLACED','REPLACED','UNCHANGED'],'reload':['REPLACED']*3}[boundary])
    report=rich(value);assert report['status']=='FAILED' and [r['state'] for r in report['fileStates']]==actual
    assert len(report['originals'])==3
    assert {Path(r['archivedPin']['path']).read_bytes() for r in report['originals']}==set(before.values())
    assert not list(value['task'].glob('main-program-spug-resource-activation-*.json'))
    assert t.calls==(['observe','reload'] if boundary=='reload' else ['observe'])


@pytest.mark.parametrize('v2',[False,True])
def test_rejected_observation_keeps_raw_response_and_original_error(delta_case,v2):
    value=delta_case;inputs=deepcopy(value['inputs'] if v2 else value['old_inputs'])
    inputs['observationPin']=None;put(value['task']/'observe-inputs.json',inputs)
    t=transport(value)
    if v2:t.observed['spug']['settings']['entry']['path']='/wrong-entry.json'
    error='SETTINGS_PATH_CHANGED' if v2 else 'NON_ADAPTER_RESOURCE_CHANGED'
    with pytest.raises(ValueError,match=error):
        subject.run_request(value['task'],value['private'],'observe-inputs.json',observe=True,transport=t)
    assert t.calls==['observe']
    failed=list(value['private'].glob('*observation*.failure-*.private.json'))
    assert len(failed)==1
    raw=json.loads(failed[0].read_bytes())
    assert raw['status']=='FAILED' and raw['rawObservation']==t.observed
    assert error in raw['errorCode']
    assert list(value['private'].glob('main-program-spug-resource-observation-*.private.json'))==failed
    assert not list(value['task'].glob('main-program-spug-resource-activation-*.json'))


def test_v1_still_refuses_three_changes(delta_case):
    value=delta_case;old=deepcopy(value['old_inputs'])
    old['observationPin']=publication.file_pin(value['private']/'observation.private.json')
    put(value['task']/'old-inputs.json',old)
    with pytest.raises(ValueError,match='NON_ADAPTER_RESOURCE_CHANGED'):
        subject.prepare(value['task'],value['private'],'old-inputs.json')


def test_v2_observation_mode_uses_delta_and_never_applies(delta_case):
    value=delta_case;value['inputs']['observationPin']=None
    put(value['task']/'observe-v2.json',value['inputs']);t=transport(value)
    before={n:(value['runtime']/n).read_bytes() for n in publication.PRODUCT_FILES}
    result=subject.run_request(value['task'],value['private'],'observe-v2.json',observe=True,transport=t)
    assert result['status']=='OBSERVED' and t.calls==['observe']
    assert json.loads(Path(result['observationPin']['path']).read_bytes())==value['observed']
    assert all((value['runtime']/n).read_bytes()==raw for n,raw in before.items())


def test_fresh_drift_blocks_all_three_before_any_write(delta_case):
    value=delta_case;spec=prepared(value);t=transport(value);t.observed['historySha256']='f'*64
    before={n:(value['runtime']/n).read_bytes() for n in publication.PRODUCT_FILES}
    with pytest.raises(ValueError,match='FRESH_OBSERVATION_CHANGED'):
        subject.dispatch_prepared(value['task'],value['private'],spec,apply=True,transport=t)
    assert t.calls==['observe'] and all((value['runtime']/n).read_bytes()==raw for n,raw in before.items())


def test_third_archive_failure_prevents_any_running_file_write(delta_case,monkeypatch):
    value=delta_case;spec=prepared(value);t=transport(value)
    before={n:(value['runtime']/n).read_bytes() for n in publication.PRODUCT_FILES}
    original=subject.exclusive_bytes
    def exclusive(path,raw):
        if Path(path).name=='2-before.js':raise OSError('third original archive unavailable')
        return original(path,raw)
    monkeypatch.setattr(subject,'exclusive_bytes',exclusive)
    with pytest.raises(ValueError,match='CHECK_PRIVATE'):
        subject.dispatch_prepared(value['task'],value['private'],spec,apply=True,transport=t)
    assert t.calls==['observe'] and all((value['runtime']/n).read_bytes()==raw for n,raw in before.items())
    assert [r['state'] for r in rich(value)['fileStates']]==['UNCHANGED']*3


def test_unrecognized_current_bytes_are_unknown_not_claimed_unchanged(delta_case,monkeypatch):
    value=delta_case;spec=prepared(value);t=transport(value);original=subject.os.replace
    def replace(src,dst):
        original(src,dst);Path(dst).write_bytes(b'explicit storage corruption boundary')
        raise OSError('atomic operation then unrelated bytes')
    monkeypatch.setattr(subject.os,'replace',replace)
    with pytest.raises(ValueError,match='CHECK_PRIVATE'):
        subject.dispatch_prepared(value['task'],value['private'],spec,apply=True,transport=t)
    assert [r['state'] for r in rich(value)['fileStates']]==['UNKNOWN','UNCHANGED','UNCHANGED']
    assert (value['runtime']/CHANGED[0]).read_bytes()==b'explicit storage corruption boundary'
    assert t.calls==['observe']


def test_observer_exception_preserves_failure_without_reread(delta_case):
    value=delta_case;inputs=deepcopy(value['inputs']);inputs['observationPin']=None
    put(value['task']/'observe-error.json',inputs);t=transport(value)
    def observe():
        t.calls.append('observe');raise ValueError('MAIN_SPUG_DOCKER_COMMAND_TIMEOUT')
    t.observe=observe
    with pytest.raises(ValueError,match='^MAIN_SPUG_DOCKER_COMMAND_TIMEOUT$'):
        subject.run_request(value['task'],value['private'],'observe-error.json',observe=True,transport=t)
    failed=list(value['private'].glob('*observation*.failure-*.private.json'))
    assert len(failed)==1 and json.loads(failed[0].read_bytes())['rawObservation'] is None
    assert t.calls==['observe']
