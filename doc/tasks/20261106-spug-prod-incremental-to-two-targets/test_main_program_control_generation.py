"""Pinned local protocol documents, never evidence of a server installation.

The final audit reads the existing actual 899 originals without copying secrets,
creating a generation record, contacting a host, or dispatching a command.
"""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys

import pytest

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
sys.path.insert(0, str(TASK))
import main_program_installation_selection as contract

COMMIT = 'a' * 40


def subject():
    return importlib.import_module('main_program_control_generation')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def save(root, name, value):
    path = root / name
    path.write_bytes(canonical(value))
    return dict(file=name, bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def physical_pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def remote(path, value):
    raw = canonical(value)
    return dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def case(tmp_path):
    task = tmp_path / 'task'; task.mkdir()
    private = tmp_path / 'private'; private.mkdir()
    old = json.loads((TASK / contract.OLD_FILE).read_bytes())
    names = [contract.OLD_FILE, 'automatic-i2-audit.json', 'protected-history-58.json', 'protected-history-59.json']
    names += [ref['file'] for key, ref in old.items() if isinstance(ref, dict) and 'file' in ref]
    names += [ref['file'] for ref in old['targets'].values()]
    for name in set(names):
        (task / name).write_bytes((TASK / name).read_bytes())
    records = contract.Records(task)
    previous = contract._previous(records, records.references.get(contract.OLD_FILE) or save(task, contract.OLD_FILE, old))
    build = json.loads((TASK / 'release-build-899730d.json').read_bytes())
    build['targetCommit'] = COMMIT
    build_pin = save(task, 'release-build-'+COMMIT[:7]+'.json', build)
    plan = json.loads((TASK / 'main-program-configuration-plan-r4.json').read_bytes())
    plan['sourceCommit'] = COMMIT
    docs = {}; current = {}; controllers = {}
    for suffix, rows in plan['controllers'].items():
        docs[suffix] = []; controllers[suffix] = []
        for row in rows:
            engine = '/fixture/'+suffix+'/'+row['role']+'/engine-main-program-'+COMMIT[:7]
            owner = dict(schemaVersion=('RepositoryMinimumConfiguration/v1' if row['role']=='source' else
                'RecoveryMinimalConfiguration/v1'), sources={'fixture-source': {'archiveRoots':['/retained']}},
                targets={'fixture-target': {'data':'/unchanged'}}, formalModuleDirectory=engine+'/formal')
            control = dict(schemaVersion='SmallAppExecutionServiceConfig/v2', fixtureProtocolOnly=True)
            row['engine'] = engine
            for key, value, name in [('ownerPin',owner,'owner.json'),('controlPin',control,'control.json')]:
                row[key] = remote('/fixture/'+suffix+'/'+row['role']+'/'+COMMIT[:7]+'/'+name, value)
                docs[suffix].append(dict(pin=row[key],value=value))
        while len(docs[suffix]) < plan['documents'][suffix]:
            value = dict(schemaVersion='FixtureRetainedMaterial/v1', index=len(docs[suffix]))
            docs[suffix].append(dict(pin=remote('/fixture/'+suffix+'/retained-'+str(len(docs[suffix]))+'.json',value),value=value))
        current[suffix] = dict(currentInstallationSelectionPin=save(task, contract.OLD_FILE, old))
    private_plan = dict(schemaVersion='MainProgramConfigurationInstallationPlan/v1',status=plan['status'],
        sourceCommit=COMMIT, build=build, controllers=deepcopy(plan['controllers']), documentsByHost=docs,
        currentSelections=current, sourceArchiveProtections={s:{} for s in contract.HOSTS})
    save(private, 'main-program-configuration-plan-r4.private.json', private_plan)
    plan['privatePlanPin'] = physical_pin(private / 'main-program-configuration-plan-r4.private.json')
    plan_pin = save(task, 'main-program-configuration-plan-r4.json', plan)
    rich_refs = {}
    for suffix, rows in plan['controllers'].items():
        rich_refs[suffix] = []
        for index, row in enumerate(rows):
            core = dict(schemaVersion='MainProgramControlActivation/v1',status='PASS',role=row['role'],
                host='172.30.30.'+suffix, sourceCommit=COMMIT, buildPin=build_pin,planPin=plan_pin,
                service=row['service'],engine=row['engine'],pid=7000+int(suffix)*2+index,
                controlConfigurationPin=row['controlPin'],ownerConfigurationPin=row['ownerPin'],
                dropinPin=remote('/etc/systemd/system/'+row['service']+'.d/new.conf', {'fixture':True}),
                fileCount=147,fileManifestSha256=build['fileManifestSha256'],packageSha256=build['packageSha256'],
                targetConfigRef=None if row['role']=='source' else plan['programTargets'][int(suffix)-57],
                **{k:True for k in contract.TRUE_FLAGS},**{k:False for k in contract.FALSE_FLAGS})
            if suffix=='57': core['activeReceiptPin']=None
            else:
                core['previousReceiptPin']=dict(previous[suffix]['currentReceiptPin'],
                    path=str(Path(previous[suffix]['engine']).as_posix()).rsplit('/',1)[0]+'/configuration/target-installation-before-main-'+COMMIT[:7]+'.json')
                core['currentReceiptPin']=dict(previous[suffix]['currentReceiptPin'],bytes=2020,sha256='e'*64)
            stem='main-program-control-activation-'+suffix+'-'+row['role']+'-'+COMMIT[:7]
            controllers[suffix].append(save(task,stem+'.json',core))
            rich=dict(status='PASS',activationCompleted=True,host=core['host'],service=core['service'],
                pid=core['pid'],sourceCommit=COMMIT,dropinPin=core['dropinPin'],controllersAfter=[dict(core)],
                packageJsonPin=remote(core['engine']+'/package.json',{'fixturePackageOnly':True}),
                registrySelectorsPublished=False,**{k:True for k in ('actualImportsVerified','originalUnitPinsVerified',
                'physicalLockVerified','epochVerified','historyGuardVerified','apiVerified','argvVerified',
                'environmentVerified','limitVerified','noWorkersVerified',*contract.TRUE_FLAGS)},
                **{k:False for k in contract.FALSE_FLAGS})
            if row['role']=='source':rich.update(sourceCaptureVerified=True,sourceBaselineVerified=True)
            else:rich.update(directlyAdmittedSources=plan['sourceRefs'],archiveViewsPreflightVerified=True)
            if suffix!='57':
                legacy=previous[suffix]['extendedCustody']
                rich.update(receiptRotated=True,completePreviousCustodyVerified=True,originalPathInventoryVerified=True,
                    previousReceiptPin=core['previousReceiptPin'],currentReceiptPin=core['currentReceiptPin'],
                    previousCustodyObservation=dict(status='PASS',activationCount=len(legacy['steps']),
                        activatedGenerationCommits=legacy['expectedGenerationCommits'],
                        selectedCurrentReceiptPin=legacy['steps'][-1]['currentReceiptPin'],
                        originalActiveReceiptPin=legacy['originalActiveReceiptPin'],
                        allReceiptAndConfigurationPinsVerified=True,allHistoricalSourceAndTargetDefinitionsUnchanged=True))
            save(private,stem+'.private.json',rich)
            rich_refs[suffix].append(physical_pin(private/(stem+'.private.json')))
    value=dict(schemaVersion='MainProgramControlGeneration/v1',status='PASS',sourceCommit=COMMIT,
        buildPin=build_pin,planPin=plan_pin,predecessor=dict(kind='AUTOMATIC_INSTALLATION',
        selectionPin=save(task,contract.OLD_FILE,old)),controllersByHost=controllers,activationEvidenceByHost=rich_refs,
        sourceBaselinePin=dict(file='automatic-i2-audit.json',bytes=(task/'automatic-i2-audit.json').stat().st_size,
            sha256=hashlib.sha256((task/'automatic-i2-audit.json').read_bytes()).hexdigest()),
        selectorsPublished=False,spugResourceInstalled=False,backupDispatched=False,restoreDispatched=False)
    reference=save(task,'control-generation-'+COMMIT[:7]+'.json',value)
    return dict(task=task,private=private,value=value,reference=reference)


def load(case):
    return subject().load_control_generation(case['task'],case['private'],case['reference'])


def repin(case):
    case['reference']=save(case['task'],case['reference']['file'],case['value'])


@pytest.mark.parametrize('suffix',['57','58','59'])
def test_local_files_bind_all_four_controls_without_full_spug_selection(case,suffix):
    before={str(p):p.read_bytes() for base in (case['task'],case['private']) for p in base.iterdir()}
    bundle=load(case)
    result=subject().select_control_generation(suffix,case['task'],case['private'],generation_pin=case['reference'])
    assert set(bundle)=={'generationPin','generation','build','plan','privatePlan','controllersByHost',
        'selections','inputPins','targets','sourceBaseline','custodyByHost'}
    assert result==bundle['selections'][suffix]
    assert result['currentControlGenerationPin']==case['reference']
    assert [r['role'] for r in result['controllers']]==list(contract.ROLES[suffix])
    assert 'currentInstallationSelectionPin' not in result
    assert result['activeReceiptPin']==(None if suffix=='57' else bundle['controllersByHost'][suffix][0]['currentReceiptPin'])
    assert bundle['generation']['selectorsPublished'] is bundle['generation']['spugResourceInstalled'] is False
    assert set(bundle['custodyByHost'])=={'58','59'}
    assert all(p.read_bytes()==raw for path,raw in before.items() for p in [Path(path)])
    assert all(physical_pin(Path(p['path']))==p for p in bundle['inputPins'])


@pytest.mark.parametrize('field',['selectorsPublished','spugResourceInstalled','backupDispatched','restoreDispatched'])
def test_no_publication_or_business_operation_may_be_inferred(case,field):
    case['value'][field]=True;repin(case)
    with pytest.raises(ValueError,match='GENERATION_'):load(case)


@pytest.mark.parametrize('change',['schema','unknown-field','missing-host','reorder','duplicate','typed-predecessor','cycle','depth'])
def test_exact_schema_roles_and_typed_acyclic_predecessor(case,change):
    v=case['value']
    if change=='schema':v['schemaVersion']='TaskMainProgramInstallations/v1'
    elif change=='unknown-field':v['spugInstallationPin']=v['planPin']
    elif change=='missing-host':del v['controllersByHost']['58']
    elif change=='reorder':v['controllersByHost']['57'].reverse()
    elif change=='duplicate':v['controllersByHost']['59']=v['controllersByHost']['58']
    elif change=='typed-predecessor':v['predecessor']['kind']='LATEST'
    elif change=='cycle':v['predecessor']=dict(kind='CONTROL_GENERATION',generationPin=case['reference'])
    else:
        # Depth is checked before a reader follows a repeated file; no recursion
        # or fabricated successful predecessor is required to exercise it.
        module=subject()
        with pytest.raises(ValueError,match='GENERATION_'):
            module._load(contract.Records(case['task']),case['private'],case['reference'],
                trail=tuple('old-'+str(n)+'.json' for n in range(module.MAX_GENERATIONS)))
        return
    repin(case)
    with pytest.raises(ValueError,match='GENERATION_|MAIN_INSTALLATION_'):load(case)


@pytest.mark.parametrize('field',['pid','sourceCommit','controlConfigurationPin','previousReceiptPin'])
def test_even_a_different_host_core_is_fully_bound(case,field):
    ref=case['value']['controllersByHost']['58'][0]
    d=json.loads((case['task']/ref['file']).read_bytes())
    d[field]=False if field=='pid' else ('f'*40 if field=='sourceCommit' else dict(path='/wrong',bytes=1,sha256='f'*64))
    case['value']['controllersByHost']['58'][0]=save(case['task'],ref['file'],d);repin(case)
    with pytest.raises(ValueError,match='GENERATION_|MAIN_INSTALLATION_|ACTUAL_'):load(case)


@pytest.mark.parametrize('component',['buildPin','planPin','sourceBaselinePin','rich','private-plan'])
def test_any_original_pin_drift_fails_before_return(case,component):
    if component=='rich':p=Path(case['value']['activationEvidenceByHost']['59'][0]['path'])
    elif component=='private-plan':p=case['private']/'main-program-configuration-plan-r4.private.json'
    else:p=case['task']/case['value'][component]['file']
    p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='GENERATION_|MAIN_INSTALLATION_|PIN_CHANGED'):load(case)


def test_rich_with_a_rebound_pin_still_requires_real_proof_fields(case):
    r=case['value']['activationEvidenceByHost']['59'][0];p=Path(r['path']);d=json.loads(p.read_bytes())
    d['completePreviousCustodyVerified']=False
    save(p.parent,p.name,d);case['value']['activationEvidenceByHost']['59'][0]=physical_pin(p);repin(case)
    with pytest.raises(ValueError,match='ACTUAL_RECEIPT_CUSTODY_REQUIRED'):load(case)


def test_generation_duplicate_keys_are_rejected(case):
    p=case['task']/case['reference']['file'];raw=p.read_bytes()
    p.write_bytes(raw[:-1]+b',"status":"PASS"}')
    case['reference']=dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    with pytest.raises(ValueError,match='DUPLICATE'):load(case)


def successor(case,monkeypatch):
    """Metadata seam for separately tested coverage/pure-plan material checks.

    All four core/rich/activation-input and configuration pins are actual local
    files. The material seam is explicitly not evidence of package installation.
    """
    previous=load(case);commit='d'*40;revision='r5';old=case['value']
    build=deepcopy(previous['build']);build.pop('packages');build['targetCommit']=commit
    build_pin=save(case['task'],'release-build-'+commit[:7]+'.json',build)
    secret=deepcopy(previous['privatePlan']);plan=deepcopy(previous['plan'])
    secret.update(schemaVersion='MainProgramConfigurationInstallationPlan/v2',sourceCommit=commit,build=build,
        revisionId=revision,predecessorGenerationPin=case['reference'],previousPlanPin=old['planPin'],
        buildPin=build_pin,currentSelections=deepcopy(previous['selections']))
    plan.update(schemaVersion='MainProgramConfigurationPlan/v2',sourceCommit=commit,revisionId=revision,
        predecessorGenerationPin=case['reference'],previousPlanPin=old['planPin'],buildPin=build_pin)
    new_groups={};retained_groups={};new_cores={};rich_refs={}
    for host,rows in secret['controllers'].items():
        old_paths={p[key]['path'] for p in rows for key in ('ownerPin','controlPin')}
        new_groups[host]=[];retained_groups[host]=[];new_cores[host]=[];rich_refs[host]=[]
        docs={d['pin']['path']:d for d in secret['documentsByHost'][host]}
        for index,row in enumerate(rows):
            old_core=previous['controllersByHost'][host][index]
            row.update(engine=row['engine'].replace(COMMIT[:7],commit[:7]),
                previousControlPin=old_core['controlConfigurationPin'],previousOwnerPin=old_core['ownerConfigurationPin'])
            for key in ('ownerPin','controlPin'):
                doc=deepcopy(docs[row[key]['path']]);value=doc['value']
                if 'formalModuleDirectory' in value:value['formalModuleDirectory']=row['engine']+'/formal'
                doc['pin']=remote(doc['pin']['path'].replace(COMMIT[:7],commit[:7]),value)
                row[key]=doc['pin'];new_groups[host].append(doc)
        retained_groups[host]=[deepcopy(d) for path,d in docs.items() if path not in old_paths]
        secret['documentsByHost'][host]=new_groups[host]+retained_groups[host]
    coverage_pin=save(case['task'],'fixture-coverage.json',{'schemaVersion':'FixtureCoverageProtocol/v1'})
    for d in (secret,plan):
        d['packageDeltaPin']=save(case['task'],'fixture-delta.json',{'schemaVersion':'FixtureDeltaProtocol/v1'})
    secret['newDocumentsByHost']=new_groups;secret['retainedDocumentsByHost']=retained_groups
    plan['newDocumentsByHost']={h:[r['pin'] for r in rows] for h,rows in new_groups.items()}
    plan['retainedDocumentsByHost']={h:[r['pin'] for r in rows] for h,rows in retained_groups.items()}
    plan['controllers']={h:[{k:r[k] for k in ('role','service','engine','controlPin','ownerPin')} for r in rows]
        for h,rows in secret['controllers'].items()}
    stem='main-program-configuration-plan-'+commit[:7]+'-'+revision
    save(case['private'],stem+'.private.json',secret)
    plan['privatePlanPin']=physical_pin(case['private']/(stem+'.private.json'))
    plan_pin=save(case['task'],stem+'.json',plan)
    for host,rows in secret['controllers'].items():
        for index,row in enumerate(rows):
            prior=previous['controllersByHost'][host][index];core=deepcopy(prior)
            core.update(sourceCommit=commit,buildPin=build_pin,planPin=plan_pin,engine=row['engine'],pid=prior['pid']+100,
                ownerConfigurationPin=row['ownerPin'],controlConfigurationPin=row['controlPin'])
            if host!='57':
                recipe=previous['custodyByHost'][host]
                core['previousReceiptPin']=dict(prior['currentReceiptPin'],path=recipe['root']+
                    '/configuration/target-installation-before-main-'+commit[:7]+'.json')
                core['currentReceiptPin']=dict(prior['currentReceiptPin'],sha256='f'*64)
            name='main-program-control-activation-'+host+'-'+row['role']+'-'+commit[:7]+'-'+revision
            new_cores[host].append(save(case['task'],name+'.json',core))
            old_rich=json.loads(Path(old['activationEvidenceByHost'][host][index]['path']).read_bytes())
            old_rich.update(sourceCommit=commit,pid=core['pid'],controllersAfter=[core],
                packageJsonPin=remote(core['engine']+'/package.json',{'fixtureOnly':True}))
            if host!='57':old_rich.update(previousReceiptPin=core['previousReceiptPin'],currentReceiptPin=core['currentReceiptPin'],
                previousCustodyObservation=dict(status='PASS',activationCount=len(recipe['legacyCustody']['steps'])+len(recipe['mainSteps']),
                    legacyActivationCount=len(recipe['legacyCustody']['steps']),
                    selectedCurrentReceiptPin=prior['currentReceiptPin'],originalInventoryVerified=True,
                    allReceiptAndConfigurationPinsVerified=True,packageManifestsVerified=True,serverWrites=False))
            if host!='57':
                old_rich['currentLayeredCustodyObservation']=dict(old_rich['previousCustodyObservation'],
                    activationCount=old_rich['previousCustodyObservation']['activationCount']+1,
                    selectedCurrentReceiptPin=core['currentReceiptPin'])
            save(case['private'],name+'.private.json',old_rich)
            rich_refs[host].append(physical_pin(case['private']/(name+'.private.json')))
    import main_program_control_activation as activation
    for host,roles in contract.ROLES.items():
        for index,role in enumerate(roles):
            ref=new_cores[host][index]
            inputs=dict(schemaVersion='MainProgramControlActivationInputs/v4',sourceCommit=commit,suffix=host,role=role,
                revisionId=revision,buildPin=build_pin,planPin=plan_pin,previousControlGenerationPin=case['reference'],
                coveragePin=coverage_pin,sourceBaselinePin=old['sourceBaselinePin'],outputFile=ref['file'],
                precedingActivationPins=[new_cores[s][list(contract.ROLES[s]).index(r)]
                    for s,r in activation.predecessors(host,role)])
            for field,stem in [('engineStagedPin','main-program-engine-staged'),
                ('configurationStagedPin','main-program-configuration-staged'),('unitObservationPin','main-program-control-units'),
                ('originalEnvironmentObservationPin','main-program-control-environment-baseline')]:
                inputs[field]=save(case['task'],stem+'-'+host+'-'+commit[:7]+'-'+revision+'.json',
                    dict(schemaVersion='FixtureReadOnlyProtocol/v1',host=host))
            inputs_pin=save(case['task'],'fixture-activation-inputs-'+host+'-'+role+'.json',inputs)
            rich_path=Path(rich_refs[host][index]['path']);rich=json.loads(rich_path.read_bytes())
            rich.update(activationInputsPin=inputs_pin,coveragePin=coverage_pin,
                previousControlGenerationPin=case['reference'],revisionId=revision)
            save(rich_path.parent,rich_path.name,rich);rich_refs[host][index]=physical_pin(rich_path)
    value=deepcopy(old);value.update(sourceCommit=commit,buildPin=build_pin,planPin=plan_pin,
        predecessor=dict(kind='CONTROL_GENERATION',generationPin=case['reference']),controllersByHost=new_cores,
        activationEvidenceByHost=rich_refs)
    result=dict(case,value=value,reference=save(case['task'],'control-generation-'+commit[:7]+'-'+revision+'.json',value))
    def materials_protocol(records,private,inputs,build,prior,public,private_plan):
        assert records.pinned(inputs['coveragePin'])=={'schemaVersion':'FixtureCoverageProtocol/v1'}
        assert records.pinned(public['packageDeltaPin'])=={'schemaVersion':'FixtureDeltaProtocol/v1'}
        assert build['targetCommit']==commit and 'packages' not in build
        assert prior['generationPin']==previous['generationPin']
        return []
    monkeypatch.setattr(subject(),'_validate_upgrade_materials',materials_protocol,raising=False)
    return result,previous


def test_successor_generic_build_and_revision_preserve_typed_predecessor(case,monkeypatch):
    updated,previous=successor(case,monkeypatch)
    bundle=load(updated)
    assert bundle['generation']['predecessor']['generationPin']==previous['generationPin']
    assert bundle['selections']['58']['baseAutomaticSelectionPin']==previous['selections']['58']['baseAutomaticSelectionPin']
    for host in ('58','59'):
        assert bundle['custodyByHost'][host]['legacyCustody']==previous['custodyByHost'][host]['legacyCustody']
        assert bundle['custodyByHost'][host]['mainSteps'][:-1]==previous['custodyByHost'][host]['mainSteps']


@pytest.mark.parametrize('change',['retained','group-overlap','predecessor','previous-owner','layered-proof'])
def test_successor_rejects_mixed_graph_or_unproved_custody(case,monkeypatch,change):
    updated,_=successor(case,monkeypatch)
    p=updated['task']/updated['value']['planPin']['file'];plan=json.loads(p.read_bytes())
    private_path=Path(plan['privatePlanPin']['path']);secret=json.loads(private_path.read_bytes())
    if change=='retained':secret['retainedDocumentsByHost']['58'][0]['value']['changed']=True
    elif change=='group-overlap':secret['retainedDocumentsByHost']['58'].append(secret['newDocumentsByHost']['58'][0])
    elif change=='predecessor':secret['predecessorGenerationPin']=updated['value']['buildPin']
    elif change=='previous-owner':secret['controllers']['58'][0]['previousOwnerPin']=dict(path='/wrong',bytes=1,sha256='e'*64)
    else:
        rich_path=Path(updated['value']['activationEvidenceByHost']['58'][0]['path'])
        rich=json.loads(rich_path.read_bytes());rich['previousCustodyObservation']['originalInventoryVerified']=False
        save(rich_path.parent,rich_path.name,rich);updated['value']['activationEvidenceByHost']['58'][0]=physical_pin(rich_path)
    save(private_path.parent,private_path.name,secret);plan['privatePlanPin']=physical_pin(private_path)
    updated['value']['planPin']=save(updated['task'],p.name,plan)
    # Keep the core's own plan binding precise to reach the mutated inner graph.
    for refs in updated['value']['controllersByHost'].values():
        for index,ref in enumerate(refs):
            core=json.loads((updated['task']/ref['file']).read_bytes());core['planPin']=updated['value']['planPin']
            refs[index]=save(updated['task'],ref['file'],core)
    repin(updated)
    with pytest.raises(ValueError,match='GENERATION_'):load(updated)


@pytest.mark.parametrize('change',['missing','count','receipt'])
def test_successor_requires_completed_custody_observation(case,monkeypatch,change):
    updated,_=successor(case,monkeypatch)
    ref=updated['value']['activationEvidenceByHost']['58'][0];path=Path(ref['path']);rich=json.loads(path.read_bytes())
    if change=='missing':del rich['currentLayeredCustodyObservation']
    elif change=='count':rich['currentLayeredCustodyObservation']['activationCount']-=1
    else:rich['currentLayeredCustodyObservation']['selectedCurrentReceiptPin']=rich['previousReceiptPin']
    save(path.parent,path.name,rich)
    updated['value']['activationEvidenceByHost']['58'][0]=physical_pin(path);repin(updated)
    with pytest.raises(ValueError,match='GENERATION_'):load(updated)


def test_actual_899_originals_including_two_r2_failure_chains_are_read_only():
    milestone=json.loads((TASK/'main-program-four-controls-activation-milestone-r1.json').read_bytes())
    # Select explicit names, rather than trust a summary as proof of activation.
    records=contract.Records(TASK)
    def local(name):records.read(name);return records.references[name]
    commit='899730de38c0e883245c11f2ad7986424ecbaf80'
    controls={};rich={}
    for suffix,roles in contract.ROLES.items():
        controls[suffix]=[];rich[suffix]=[]
        for role in roles:
            stem='main-program-control-activation-'+suffix+'-'+role+'-899730d'
            controls[suffix].append(local(stem+'.json'))
            path=PRIVATE/(stem+('-r2' if suffix in ('58','59') else '')+'.private.json')
            rich[suffix].append(physical_pin(path))
    value=dict(schemaVersion='MainProgramControlGeneration/v1',status='PASS',sourceCommit=commit,
        buildPin=local('release-build-899730d.json'),planPin=local('main-program-configuration-plan-r4.json'),
        predecessor=dict(kind='AUTOMATIC_INSTALLATION',selectionPin=local(contract.OLD_FILE)),
        controllersByHost=controls,activationEvidenceByHost=rich,sourceBaselinePin=local('automatic-i2-audit.json'),
        selectorsPublished=False,spugResourceInstalled=False,backupDispatched=False,restoreDispatched=False)
    before={p['path']:p for rows in rich.values() for p in rows}
    result=subject().inspect_control_generation(value,TASK,PRIVATE)
    assert result['generationPin'] is None
    assert [result['selections'][s]['controllers'][-1]['pid'] for s in contract.HOSTS]==[9785,18785,6329]
    names={Path(p['path']).name for p in result['inputPins']}
    assert 'main-program-control-initial-continuation-59-target-899730d-r2.json' in names
    assert 'main-program-control-preswitch-continuation-58-target-899730d-r2.json' in names
    assert all(physical_pin(Path(path))==pin for path,pin in before.items())
