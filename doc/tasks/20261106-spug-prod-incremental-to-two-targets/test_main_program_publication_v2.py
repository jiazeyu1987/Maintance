"""Local protocol fixtures; never evidence of an actual publication.

Generation fixtures exercise the real file/pin reader. Their separately tested
coverage/material seam is inherited explicitly from the generation suite. The
resource build and validation log are existing, read-only actual local evidence.
No transport, browser, server, package build, or Git write is performed here.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import main_program_installation_selection as contract
import main_program_spug_publication as subject
import observe_closeout_hosts as closeout
from test_main_program_control_generation import case, successor, load, save, physical_pin, remote, TASK, PRIVATE
from test_main_program_spug_publication import actual_r4_material


def schedule():
    return [lane+'-'+phase+('-'+host if host else '')
        for phase in ('preflight','publish','verify')
        for lane,host in [('host','57'),('host','58'),('host','59'),('spug',None)]]


@pytest.fixture
def v2(case, monkeypatch):
    updated,_ = successor(case,monkeypatch)
    return publication_case(updated)


def publication_case(updated):
    task,private=updated['task'],updated['private']
    resource=json.loads((TASK/'spug-resource-build-c7728ad.json').read_bytes())
    validation=json.loads((TASK/resource['testEvidencePin']['file']).read_bytes())
    log=Path(validation['logPin']['path'])
    (private/log.name).write_bytes(log.read_bytes())
    validation['logPin']=physical_pin(private/log.name)
    resource['testEvidencePin']=save(task,resource['testEvidencePin']['file'],validation)
    resource_pin=save(task,'spug-resource-build-c7728ad.json',resource)
    commit=updated['value']['sourceCommit'];revision='r5'
    observation=dict(schemaVersion='MainProgramSpugPublicationObservation/v2',sourceCommit=commit,
        revisionId=revision,controlGenerationPin=updated['reference'],spugResourceBuildPin=resource_pin,
        selectorsByHost={},hostPreservationByHost={},spug=dict(productPins=[
            dict(path='/opt/intruoyi-spug/'+name,**resource['files']['ops/spug/'+name]) for name in subject.PRODUCT_FILES]))
    obs_name='fixture-publication-observation.private.json'
    save(private,obs_name,observation)
    inputs=dict(schemaVersion='MainProgramSpugPublicationInputs/v2',sourceCommit=commit,revisionId=revision,
        controlGenerationPin=updated['reference'],spugResourceBuildPin=resource_pin,
        publicationObservationPin=physical_pin(private/obs_name),
        outputFile='main-program-spug-installation-'+commit[:7]+'-'+revision+'.json')
    input_pin=save(task,'fixture-publication-inputs.json',inputs)
    binding={k:inputs[k] for k in ('sourceCommit','revisionId','controlGenerationPin',
        'spugResourceBuildPin','publicationObservationPin')}
    binding['publicationInputsPin']=input_pin
    stages=[];bundle=load(updated)
    for stage in schedule():
        lane,phase,*hosts=stage.split('-')
        result=dict(status='PASS',sourceCommit=commit,phase=phase,backupDispatched=False,restoreDispatched=False)
        if lane=='host':
            host=hosts[0]
            result.update(host='172.30.30.'+host,selectorCount=6 if host=='57' else 3,
                controllers=deepcopy(bundle['controllersByHost'][host]),
                **{k:True for k in ('selectorsReadBack','actualNativeSelectionsVerified','oldFilesPreserved',
                'businessContainersUnchanged','fstabAndMountsUnchanged','controlIdentityVerified')})
            result['nativeSelections']=[dict(service=c['service'],selections=dict(applications=[
                dict(sourceConfigRef=s,historyErrorCode=None,recoveryPointRefs=['fixture-point'],
                     freshTargetConfigRefs=[bundle['targets'][host]]) for s in subject.SOURCES]))
                for c in bundle['controllersByHost'][host]]
        else:
            result.update(applicationCount=33,taskCount=3,**{k:True for k in ('productSettingsReadBack',
                'historicalFingerprintsUnchanged','oldFilesPreserved','protectedSpugUnchanged','oldTasksUnchanged',
                'productFilesUnchanged')})
            result['productPins']=deepcopy(observation['spug']['productPins'])
            result['bridgeSelections']=[dict(sourceConfigRef=s,targetConfigRef=bundle['targets'][h])
                for h in contract.HOSTS for s in subject.SOURCES]
        raw=dict(schemaVersion='MainProgramSpugPublicationStage/v2',stage=stage,**binding,result=result)
        name='fixture-'+stage+'.private.json';save(private,name,raw)
        stages.append(dict(stage=stage,resultPin=physical_pin(private/name)))
    rich=dict(schemaVersion='MainProgramSpugPublicationEvidence/v2',status='PASS',stage='complete',**binding,
        resourceSourceCommit=resource['sourceCommit'],stages=stages,selectorCount=12,applicationCount=33,taskCount=3,
        backupDispatched=False,restoreDispatched=False,**{k:True for k in subject.TRUE_CHECKS})
    rich_name=inputs['outputFile'].replace('.json','.private.json');save(private,rich_name,rich)
    core=dict(schemaVersion='MainProgramSpugInstallation/v1',status='PASS',sourceCommit=commit,
        buildPin=updated['value']['buildPin'],planPin=updated['value']['planPin'],
        applicationCount=33,taskCount=3,restoreSelectorCount=12,protectedSpugUnchanged=True)
    selection=dict(schemaVersion='TaskMainProgramInstallations/v2',sourceCommit=commit,
        controlGenerationPin=updated['reference'],spugInstallationPin=save(task,inputs['outputFile'],core))
    selection_pin=save(task,'fixture-main-selection.json',selection)
    return dict(updated,inputs=inputs,input_pin=input_pin,rich=rich,rich_name=rich_name,
        core=core,selection=selection,selection_pin=selection_pin,resource=resource)


@pytest.fixture
def planning_case(case,monkeypatch,actual_r4_material):
    """Real historical settings, with protocol-only controls in temporary files."""
    secret=deepcopy(actual_r4_material.value);task,private=case['task'],case['private']
    (private/actual_r4_material.approved.name).write_bytes(actual_r4_material.approved.read_bytes())
    plan=json.loads((task/case['value']['planPin']['file']).read_bytes())
    old_secret=json.loads((private/'main-program-configuration-plan-r4.private.json').read_bytes())
    secret.update(sourceCommit=case['value']['sourceCommit'],build=old_secret['build'],
        currentSelections=old_secret['currentSelections'])
    for host,rows in secret['controllers'].items():
        docs={r['pin']['path']:r for r in secret['documentsByHost'][host]}
        for row in rows:
            row['engine']=row['engine'].replace('899730d','aaaaaaa')
            for key in ('ownerPin','controlPin'):
                doc=docs[row[key]['path']]
                if 'formalModuleDirectory' in doc['value']:
                    doc['value']['formalModuleDirectory']=row['engine']+'/formal'
                doc['pin']=remote(row[key]['path'].replace('899730d','aaaaaaa'),doc['value'])
                row[key]=doc['pin']
        plan['controllers'][host]=[{k:r[k] for k in ('role','service','engine','controlPin','ownerPin')} for r in rows]
        assert len(secret['documentsByHost'][host])==plan['documents'][host]
    save(private,'main-program-configuration-plan-r4.private.json',secret)
    plan['privatePlanPin']=physical_pin(private/'main-program-configuration-plan-r4.private.json')
    case['value']['planPin']=save(task,case['value']['planPin']['file'],plan)
    for host,rows in secret['controllers'].items():
        for index,row in enumerate(rows):
            ref=case['value']['controllersByHost'][host][index];core=json.loads((task/ref['file']).read_bytes())
            core.update(planPin=case['value']['planPin'],engine=row['engine'],
                ownerConfigurationPin=row['ownerPin'],controlConfigurationPin=row['controlPin'])
            case['value']['controllersByHost'][host][index]=save(task,ref['file'],core)
            rich_path=Path(case['value']['activationEvidenceByHost'][host][index]['path'])
            rich=json.loads(rich_path.read_bytes());rich['controllersAfter']=[core]
            rich['packageJsonPin']=remote(core['engine']+'/package.json',{'fixtureProtocolOnly':True})
            save(private,rich_path.name,rich)
            case['value']['activationEvidenceByHost'][host][index]=physical_pin(rich_path)
    case['reference']=save(task,case['reference']['file'],case['value'])
    updated,_=successor(case,monkeypatch)
    value=publication_case(updated);bundle=load(updated)
    secret=dict(bundle['privatePlan'],programTargets=bundle['plan']['programTargets'])
    selectors=subject.selector_rows(secret,bundle['controllersByHost'])
    obs_path=Path(value['inputs']['publicationObservationPin']['path']);obs=json.loads(obs_path.read_bytes())
    obs['selectorsByHost']={h:[dict(path=r['path'],pin=None) for r in rows] for h,rows in selectors.items()}
    obs['hostPreservationByHost']={h:dict(containers={'protocol-fixture':{}},
        fstabPin=remote('/etc/fstab',{'fixture':True}),mountinfoSha256='e'*64) for h in contract.HOSTS}
    obs['spug'].update(containerId=subject.CONTAINER,containerSnapshot={},protectedContainerId='a'*64,
        protectedContainerSnapshot={},entryPid=7123,taskSnapshotSha256='b'*64,
        settings={k:{n:secret['originalSpug'][k][n] for n in ('path','bytes','sha256')} for k in subject.SETTINGS},
        connections={k:{n:r[n] for n in ('path','bytes','sha256')} for k,r in secret['originalSpug']['connections'].items()})
    save(private,obs_path.name,obs);value['inputs']['publicationObservationPin']=physical_pin(obs_path)
    value['input_pin']=save(task,value['input_pin']['file'],value['inputs'])
    return value


def selected(v2,host='57'):
    return contract.select_main_program_installation(host,v2['task'],private=v2['private'],
        selection_file=v2['selection_pin']['file'])


@pytest.mark.parametrize('host',['57','58','59'])
def test_complete_selection_requires_exact_generation_and_twelve_stage_originals(v2,host):
    before={str(p):p.read_bytes() for base in (v2['task'],v2['private']) for p in base.iterdir()}
    result=selected(v2,host)
    assert result['currentInstallationSelectionPin']==v2['selection_pin']
    assert result['sourceCommit']==v2['value']['sourceCommit']
    assert result['controllers']==[{k:c[k] for k in contract.CONTROLLER_KEYS}
        for c in load(v2)['controllersByHost'][host]]
    paths={p['path'] for p in result['localInstallationPins']}
    assert str(v2['private']/v2['rich_name']) in paths
    assert all(r['resultPin']['path'] in paths for r in v2['rich']['stages'])
    assert all(Path(path).read_bytes()==raw for path,raw in before.items())


@pytest.mark.parametrize('change',['missing-rich','failed-rich','control-only-core','wrong-core-plan',
    'wrong-commit','wrong-revision','missing-stage','duplicate-stage','stage-order','unknown-field',
    'stage-failed','stage-business-write','stage-cross-generation','stage-rebound-pid',
    'stage-selectors','stage-applications','resource-runtime-drift','observation-drift','input-drift'])
def test_full_selection_rejects_missing_cross_generation_or_rebound_proof(v2,change):
    task,private=v2['task'],v2['private'];rich=v2['rich'];path=private/v2['rich_name']
    if change=='missing-rich':path.unlink()
    elif change=='control-only-core':
        ref=v2['value']['controllersByHost']['57'][0]
        v2['selection']['spugInstallationPin']=ref
        save(task,v2['selection_pin']['file'],v2['selection'])
    elif change=='wrong-core-plan':
        v2['core']['planPin']=v2['value']['buildPin']
        v2['selection']['spugInstallationPin']=save(task,v2['inputs']['outputFile'],v2['core'])
        save(task,v2['selection_pin']['file'],v2['selection'])
    elif change=='resource-runtime-drift':rich['resourceSourceCommit']='f'*40
    elif change=='observation-drift':
        p=Path(v2['inputs']['publicationObservationPin']['path']);p.write_bytes(p.read_bytes()+b' ')
    elif change=='input-drift':
        p=task/v2['input_pin']['file'];p.write_bytes(p.read_bytes()+b' ')
    elif change.startswith('stage-'):
        row=rich['stages'][8 if change!='stage-applications' else 11]
        p=Path(row['resultPin']['path']);raw=json.loads(p.read_bytes())
        if change=='stage-order':rich['stages'][0],rich['stages'][1]=rich['stages'][1],rich['stages'][0]
        elif change=='stage-failed':raw['result']['status']='FAILED'
        elif change=='stage-business-write':raw['result']['backupDispatched']=True
        elif change=='stage-cross-generation':raw['controlGenerationPin']=v2['value']['buildPin']
        elif change=='stage-rebound-pid':raw['result']['controllers'][0]['pid']+=1
        elif change=='stage-selectors':raw['result']['selectorCount']=3
        elif change=='stage-applications':raw['result']['applicationCount']=32
        if change!='stage-order':save(private,p.name,raw);row['resultPin']=physical_pin(p)
    elif change=='failed-rich':rich['status']='FAILED'
    elif change=='wrong-commit':rich['sourceCommit']='f'*40
    elif change=='wrong-revision':rich['revisionId']='r6'
    elif change=='missing-stage':rich['stages'].pop()
    elif change=='duplicate-stage':rich['stages'][1]=deepcopy(rich['stages'][0])
    elif change=='unknown-field':rich['fullInstallationInferred']=True
    if change!='missing-rich':save(private,path.name,rich)
    with pytest.raises(ValueError,match='MAIN_'):selected(v2)


@pytest.mark.parametrize('field',list(subject.TRUE_CHECKS))
def test_every_rich_safety_result_is_required(v2,field):
    v2['rich'][field]=False;save(v2['private'],v2['rich_name'],v2['rich'])
    with pytest.raises(ValueError,match='MAIN_'):selected(v2)


def test_closeout_dispatches_explicit_v2_and_does_not_accept_control_only(v2):
    result=closeout.controller_selection('59',v2['task'],private=v2['private'],
        selection_file=v2['selection_pin']['file'])
    assert result==selected(v2,'59')
    with pytest.raises(ValueError,match='MAIN_INSTALLATION_SELECTION_INVALID'):
        closeout.controller_selection('59',v2['task'],private=v2['private'],selection_file=v2['reference']['file'])


@pytest.mark.parametrize('change',['schema','extra','commit','revision','output','missing-observation'])
def test_prepare_v2_refuses_invalid_inputs_before_any_transport(v2,change):
    value=v2['inputs']
    if change=='schema':value['schemaVersion']='MainProgramSpugPublicationInputs/v3'
    elif change=='extra':value['controllersByHost']=v2['value']['controllersByHost']
    elif change=='commit':value['sourceCommit']='f'*40
    elif change=='revision':value['revisionId']='r6'
    elif change=='output':value['outputFile']='main-program-spug-installation-ddddddd.json'
    else:Path(value['publicationObservationPin']['path']).unlink()
    save(v2['task'],v2['input_pin']['file'],value)
    with pytest.raises(ValueError,match='MAIN_'):
        subject.prepare(v2['task'],v2['private'],v2['input_pin']['file'])


def test_v2_apply_is_blocked_before_attempt_or_transport(v2):
    calls=[];before=set(v2['private'].iterdir())
    spec=dict(inputs=v2['inputs'],remotePublicationSupported=False)
    with pytest.raises(ValueError,match='V2_REMOTE_PUBLICATION_NOT_IMPLEMENTED'):
        subject.dispatch_prepared(v2['task'],v2['private'],spec,apply=True,transport=lambda *args:calls.append(args))
    assert calls==[] and set(v2['private'].iterdir())==before


def test_prepare_real_historical_graph_keeps_31_routes_33_apps_and_12_selectors(planning_case):
    value=planning_case
    spec=subject.prepare(value['task'],value['private'],value['input_pin']['file'])
    assert spec['remotePublicationSupported'] is False
    assert spec['spugSpec']['history']['sourceRouteCount']==31
    assert len(spec['spugSpec']['settings']['applications'])==33
    assert len(spec['spugSpec']['settings']['tasks'])==3
    assert [len(spec['hostSpecs'][h]['selectors']) for h in contract.HOSTS]==[6,3,3]
    assert spec['generationPins']=={k:value['value'][k] for k in ('buildPin','planPin')}
    assert all(physical_pin(Path(pin['path']))==pin for pin in spec['inputPins'])
    before=set(value['private'].iterdir())
    result=subject.dispatch_prepared(value['task'],value['private'],spec)
    assert result['status']=='PREPARED_NOT_APPLIED' and result['remoteDispatched'] is False
    assert set(value['private'].iterdir())==before


@pytest.mark.parametrize('change',['native-missing','native-service','native-source','native-target',
    'native-error','native-empty-points','bridge-missing','bridge-duplicate','product-sha'])
def test_stage_original_content_is_checked_beyond_boolean_claims(v2,change):
    rich=v2['rich'];row=rich['stages'][11 if change.startswith(('bridge','product')) else 8]
    path=Path(row['resultPin']['path']);raw=json.loads(path.read_bytes());result=raw['result']
    if change=='native-missing':result['nativeSelections']=[]
    elif change=='native-service':result['nativeSelections'][0]['service']='unregistered.service'
    elif change=='native-source':result['nativeSelections'][0]['selections']['applications'][0]['sourceConfigRef']='other-source'
    elif change=='native-target':result['nativeSelections'][0]['selections']['applications'][0]['freshTargetConfigRefs']=[]
    elif change=='native-error':result['nativeSelections'][0]['selections']['applications'][0]['historyErrorCode']='FAILED'
    elif change=='native-empty-points':result['nativeSelections'][0]['selections']['applications'][0]['recoveryPointRefs']=[]
    elif change=='bridge-missing':result['bridgeSelections'].pop()
    elif change=='bridge-duplicate':result['bridgeSelections'][0]=deepcopy(result['bridgeSelections'][1])
    else:result['productPins'][0]['sha256']='f'*64
    save(v2['private'],path.name,raw);row['resultPin']=physical_pin(path)
    save(v2['private'],v2['rich_name'],rich)
    with pytest.raises(ValueError,match='MAIN_'):selected(v2)
