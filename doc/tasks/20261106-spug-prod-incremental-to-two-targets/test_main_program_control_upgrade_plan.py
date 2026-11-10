"""Pure planning contracts using actual local originals; no new deployment proof."""
import copy
import hashlib
import json
from pathlib import Path
import tarfile

import pytest

import main_program_control_upgrade_plan as subject


TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
COMMIT = '45dd7dc65409c87fe856584b85873ea96c0b830e'
OLD_COMMIT = '899730de38c0e883245c11f2ad7986424ecbaf80'


def pinned_document(path):
    raw = path.read_bytes()
    return dict(pin=dict(file=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),raw=raw)


def members(path):
    with tarfile.open(path,'r:gz') as archive:
        return {row.name:archive.extractfile(row).read() for row in archive.getmembers()
                if row.isfile() and row.name != 'package.json'}


class Materials:
    """Do not render actual private planning values in pytest failure repr."""
    def __init__(self,kwargs): self.kwargs = kwargs
    def __repr__(self): return '<actual-control-upgrade-materials-redacted>'


@pytest.fixture(scope='module')
def originals():
    private_path = PRIVATE/'main-program-configuration-plan-r4.private.json'
    public_path = TASK/'main-program-configuration-plan-r4.json'
    delta_path = TASK/'archive-catalogue-package-delta-r3.json'
    paths = [private_path,public_path,delta_path,TASK/'release-build-45dd7dc.json',TASK/'release-build-899730d.json']
    before = [p.read_bytes() for p in paths]
    old = json.loads(before[0]);public = json.loads(before[1]);delta = json.loads(before[2])
    assert hashlib.sha256(before[0]).hexdigest() == '0547063b1c8b235af78bfc15871a539911ae9c5ffc3be84ebb621f3f63548e69'
    assert hashlib.sha256(before[2]).hexdigest() == 'a5f17a8f2c9c1ba25746a36eb0a67bfbfb2b85563614696e865ad4ed3fa1a39f'
    standard = next(row for row in delta['packages'] if row['variant'] == 'standard')
    controllers = {}
    core_paths = []
    for host in subject.HOSTS:
        controllers[host] = []
        for row in old['controllers'][host]:
            path = TASK/('main-program-control-activation-'+host+'-'+row['role']+'-899730d.json')
            core_paths.append(path);controllers[host].append(json.loads(path.read_bytes()))
    before_cores = [p.read_bytes() for p in core_paths]
    generation_pin = dict(file='fixture-control-generation-899730d.json',bytes=3,sha256='a'*64)
    selections = {}
    for host in subject.HOSTS:
        rows = controllers[host]
        selections[host] = dict(host='172.30.30.'+host,suffix=host,sourceCommit=OLD_COMMIT,currentSourceCommit=OLD_COMMIT,
            currentControlGenerationPin=generation_pin,controllers=[{
            k:row[k] for k in ('role','service','engine','pid','controlConfigurationPin','ownerConfigurationPin','dropinPin')}
            for row in rows],targetConfigRef=public['programTargets'][subject.HOSTS.index(host)],
            activeReceiptPin=None if host == '57' else rows[0]['currentReceiptPin'])
    # Explicit validated-bundle protocol seam; actual core/config/package bytes
    # are reused, but this in-memory index is never claimed as a real installation.
    bundle = dict(generationPin=generation_pin,generation=dict(sourceCommit=OLD_COMMIT,
        buildPin=pinned_document(paths[4])['pin'],planPin=pinned_document(public_path)['pin']),
        build=json.loads(before[4]),plan=public,privatePlan=old,controllersByHost=controllers,selections=selections,
        inputPins=[],targets={s:selections[s]['targetConfigRef'] for s in subject.HOSTS},
        sourceBaseline={},custodyByHost={})
    kwargs = dict(source_commit=COMMIT,revision_id='r5',build_document=pinned_document(paths[3]),
        package_delta_document=pinned_document(delta_path),package_files=members(Path(standard['path'])),
        previous_package_files=members(Path(standard['predecessor']['path'])),predecessor=bundle,
        private_plan_path=str(PRIVATE/'main-program-configuration-plan-45dd7dc-r5.private.json'),
        observed_at='2026-11-09T15:00:00+00:00')
    yield Materials(kwargs)
    assert [p.read_bytes() for p in paths] == before
    assert [p.read_bytes() for p in core_paths] == before_cores


@pytest.fixture
def inputs(originals):
    return Materials(copy.deepcopy(originals.kwargs))


def planned(value):
    return subject.plan_control_upgrade(**value.kwargs)


def output_identity(path):
    """Observe immutability without putting private contents in assertion output."""
    if not path.exists():
        return None
    info = path.stat()
    return ((info.st_dev, info.st_ino, info.st_mode, info.st_size,
             info.st_mtime_ns, info.st_ctime_ns),
            hashlib.sha256(path.read_bytes()).hexdigest())


def test_actual_plan_is_pure_v2_and_groups_are_exact_8_new_27_retained(inputs):
    before = copy.deepcopy(inputs.kwargs)
    result = planned(inputs);private,public = result['privatePlan'],result['plan']
    assert inputs.kwargs == before
    assert private['schemaVersion'] == 'MainProgramConfigurationInstallationPlan/v2'
    assert public['schemaVersion'] == 'MainProgramConfigurationPlan/v2'
    assert private['status'] == public['status'] == 'PLAN_ONLY_NOT_ACTIVATED'
    assert private['revisionId'] == public['revisionId'] == 'r5'
    assert public['predecessorGenerationPin'] == inputs.kwargs['predecessor']['generationPin']
    assert public['previousPlanPin'] == inputs.kwargs['predecessor']['generation']['planPin']
    assert public['buildPin'] == inputs.kwargs['build_document']['pin']
    assert public['packageDeltaPin'] == inputs.kwargs['package_delta_document']['pin']
    assert sum(map(len,private['newDocumentsByHost'].values())) == 8
    assert sum(map(len,private['retainedDocumentsByHost'].values())) == 27
    assert sum(map(len,private['documentsByHost'].values())) == 35
    for host in subject.HOSTS:
        new = private['newDocumentsByHost'][host];retained = private['retainedDocumentsByHost'][host]
        assert not ({r['pin']['path'] for r in new} & {r['pin']['path'] for r in retained})
        assert private['documentsByHost'][host] == [*new,*retained]
        assert public['newDocumentsByHost'][host] == [r['pin'] for r in new]
        assert public['retainedDocumentsByHost'][host] == [r['pin'] for r in retained]
        assert all(row in inputs.kwargs['predecessor']['privatePlan']['documentsByHost'][host] for row in retained)
    assert public['privatePlanPin']['sha256'] == hashlib.sha256(subject.canonical(private)).hexdigest()
    assert public['privatePlanPin']['bytes'] == len(subject.canonical(private))
    assert public['registrationCount'] == 12 and public['applicationCount'] == 33 and public['originalTaskCount'] == 3
    assert public['restoreDispatched'] is False and public['installationPerformed'] is False


def test_actual_only_approved_configuration_fields_change(inputs):
    old = inputs.kwargs['predecessor']['privatePlan'];new = planned(inputs)['privatePlan']
    assert new['currentSelections'] == inputs.kwargs['predecessor']['selections']
    for key in ('registrations','sourceRegistrationSelectors','originalSpug','sourceProgramArchivePolicies',
                'sourceArchiveProtections','archiveViewDependencies','originalMetadata','requiredBeforeActivation'):
        assert new[key] == old[key]
    for host in subject.HOSTS:
        previous_docs = {r['pin']['path']:r for r in old['documentsByHost'][host]}
        new_docs = {r['pin']['path']:r for r in new['documentsByHost'][host]}
        for index,row in enumerate(new['controllers'][host]):
            previous = old['controllers'][host][index];core=inputs.kwargs['predecessor']['controllersByHost'][host][index]
            assert row['previousControlPin'] == core['controlConfigurationPin']
            assert row['previousOwnerPin'] == core['ownerConfigurationPin']
            owner=new_docs[row['ownerPin']['path']]['value'];old_owner=previous_docs[previous['ownerPin']['path']]['value']
            if row['role']=='target':
                assert owner == dict(old_owner,formalModuleDirectory=row['engine']+'/formal')
            control=new_docs[row['controlPin']['path']]['value'];old_control=previous_docs[previous['controlPin']['path']]['value']
            assert {k:v for k,v in control.items() if k not in ('programPins','environment','sourceConfigurations','restoreConfigurations')} == {
                k:v for k,v in old_control.items() if k not in ('programPins','environment','sourceConfigurations','restoreConfigurations')}
            assert {k:v for k,v in control['environment'].items() if k!='PYTHONPATH'} == {
                k:v for k,v in old_control['environment'].items() if k!='PYTHONPATH'}
            for name,pin in control['programPins'].items():
                raw=inputs.kwargs['package_files'][name+'_entry.py']
                assert pin == dict(path=row['engine']+'/'+name+'_entry.py',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def test_actual_routes_settings_and_four_connection_values_stay_compatible(inputs):
    output = Path(inputs.kwargs['private_plan_path'])
    before = output_identity(output)
    old=inputs.kwargs['predecessor']['privatePlan'];new=planned(inputs)['privatePlan']
    assert new['simpleSettings'] == old['simpleSettings'] and new['entrySettings'] == old['entrySettings']
    assert new['bridgeSettings']['sourceConnections'] == old['bridgeSettings']['sourceConnections']
    assert len(new['bridgeSettings']['sourceConnections']) == 31
    assert len(new['newConnections']) == 4 and sorted(new['newConnections'].values(),key=subject.canonical) == sorted(old['newConnections'].values(),key=subject.canonical)
    assert not set(new['newConnections']) & (set(old['newConnections']) | set(old['originalSpug']['connections']))
    assert all('45dd7dc-r5' in name for name in new['newConnections'])
    routes=new['bridgeSettings']['selectionConnections'];assert len(routes)==3 and len(set(routes.values()))==1
    for key,value in old['bridgeSettings'].items():
        if key not in ('selectionConnections','targetConnections'):assert new['bridgeSettings'][key] == value
    assert output_identity(output) == before


@pytest.mark.parametrize('existing', [False, True])
def test_planning_does_not_create_or_replace_output(inputs, tmp_path, existing):
    output = tmp_path/'main-program-configuration-plan-45dd7dc-r5.private.json'
    if existing:
        output.write_bytes(b'original planning output must remain unchanged\n')
    inputs.kwargs['private_plan_path'] = str(output)
    before = output_identity(output)
    planned(inputs)
    assert output_identity(output) == before


@pytest.mark.parametrize('change',['same-commit','invalid-commit','invalid-revision','build-pin','build-commit',
    'new-file-set','old-file-set','new-byte-change','old-byte-change','unreviewed-semantic-change',
    'delta-pin','delta-commit','delta-changed','external-engine-program','old-program-pin','duplicate-document',
    'owner-module','selection-owner','relative-output','wrong-output-name'])
def test_invalid_or_unreviewed_upgrade_inputs_fail_without_outputs(inputs,change):
    k=inputs.kwargs;old=k['predecessor']['privatePlan']
    def repin_document(key,mutate):
        material=k[key];value=json.loads(material['raw']);mutate(value);raw=subject.canonical(value)
        material['raw']=raw;material['pin'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    if change=='same-commit':k['source_commit']=OLD_COMMIT
    if change=='invalid-commit':k['source_commit']='A'*40
    if change=='invalid-revision':k['revision_id']='r0'
    if change=='build-pin':k['build_document']['pin']['sha256']='f'*64
    if change=='build-commit':repin_document('build_document',lambda x:x.update(targetCommit='f'*40))
    if change=='new-file-set':k['package_files'].pop(next(iter(k['package_files'])))
    if change=='old-file-set':k['previous_package_files'].pop(next(iter(k['previous_package_files'])))
    if change=='new-byte-change':k['package_files']['recovery_entry.py']+=b'\n'
    if change=='old-byte-change':k['previous_package_files']['recovery_entry.py']+=b'\n'
    if change=='unreviewed-semantic-change':k['package_files']['recovery_entry.py']+=b'\nUNREVIEWED=True\n'
    if change=='delta-pin':k['package_delta_document']['pin']['sha256']='f'*64
    if change=='delta-commit':repin_document('package_delta_document',lambda x:x.update(sourceCommit='f'*40))
    if change=='delta-changed':repin_document('package_delta_document',lambda x:x['packages'][0]['changedFiles'].pop())
    if change=='external-engine-program':old['documentsByHost']['57'][0]['value']['captureBinderPath']='/unknown/engine-main-program-other/formal/tool.py'
    if change=='old-program-pin':
        control=old['controllers']['58'][0]['controlPin'];doc=next(x for x in old['documentsByHost']['58'] if x['pin']==control)
        doc['value']['programPins']['recovery']['sha256']='f'*64
    if change=='duplicate-document':old['documentsByHost']['59'].append(copy.deepcopy(old['documentsByHost']['59'][0]))
    if change=='owner-module':
        owner=old['controllers']['59'][0]['ownerPin'];doc=next(x for x in old['documentsByHost']['59'] if x['pin']==owner)
        doc['value']['formalModuleDirectory']='/unapproved/formal'
    if change=='selection-owner':k['predecessor']['selections']['58']['controllers'][0]['ownerConfigurationPin']['sha256']='f'*64
    if change=='relative-output':k['private_plan_path']='main-program-configuration-plan-45dd7dc-r5.private.json'
    if change=='wrong-output-name':k['private_plan_path']=str(PRIVATE/'main-program-configuration-plan-r4.private.json')
    with pytest.raises(ValueError,match='MAIN_UPGRADE_'):planned(inputs)


def test_old_planner_preservation_contracts_still_accept_original_r4(inputs):
    # Reuse established validators directly; never import/exec the r4 template.
    import main_program_spug_publication as publication
    value=copy.deepcopy(inputs.kwargs['predecessor']['privatePlan'])
    value['programTargets']=[inputs.kwargs['predecessor']['targets'][s] for s in subject.HOSTS]
    assert publication.validate_history_routes(value)['sourceRouteCount']==31
    publication.validate_settings(value,historical_registration_plan=PRIVATE/'historical-registration-plan-r1.private.json')
    publication.validate_selection_routes(value)


def test_validator_rebuilds_exact_public_and_private_from_identical_materials(inputs):
    result=planned(inputs)
    assert subject.validate_control_upgrade_plan(result['plan'],result['privatePlan'],**inputs.kwargs) == result


def test_validator_rejects_changed_public_group_and_private_data(inputs):
    original=planned(inputs)
    for side in ('plan','privatePlan'):
        result=copy.deepcopy(original)
        if side=='plan':result[side]['retainedDocumentsByHost']['58'].pop()
        else:result[side]['documentsByHost']['58'][0]['value']['maxExpandedBytes']+=1
        with pytest.raises(ValueError,match='MAIN_UPGRADE_CANDIDATE_'):
            subject.validate_control_upgrade_plan(result['plan'],result['privatePlan'],**inputs.kwargs)
