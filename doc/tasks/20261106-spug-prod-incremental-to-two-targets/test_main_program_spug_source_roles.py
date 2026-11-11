"""Exact local originals and real Git provenance; no fabricated publication."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import tempfile

import pytest
import main_program_spug_publication as publication

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
PRESERVATION=PRIVATE/'spug-historical-source-roles-originals-20261111-r1/preservation.json'
READERS=('main_program_spug_historical_custody.py','main_program_spug_control_generation_acceptance.py',
         'main_program_current_installation.py')


def subject():return importlib.import_module('main_program_spug_historical_custody')


def value():
    result=json.loads(PRESERVATION.read_bytes())
    result['schemaVersion']='MainProgramSpugHistoricalSourceRoles/v1'
    result['currentReaderPins']=[publication.file_pin(TASK/name) for name in READERS]
    return result


@pytest.fixture
def carrier():
    with tempfile.TemporaryDirectory(prefix='source-roles-test-',dir=PRIVATE) as directory:
        root=Path(directory);counter=0
        def write(data):
            nonlocal counter
            counter+=1;p=root/('input-'+str(counter)+'.json')
            with p.open('xb') as stream:stream.write(publication.canonical(data))
            return publication.file_pin(p)
        yield value(),write,root


def load(data,write):return subject().load_source_roles(TASK,PRIVATE,write(data))


def test_two_exact_roles_bind_real_originals_and_git_provenance(carrier):
    data,write,_=carrier;before=deepcopy(data)
    roles=load(data,write)
    assert set(roles.source_roles)=={'catalogue','acceptanceActivation'}
    assert roles.value['attemptPins']==data['attemptPins']
    for row in data['sourceRoles'].values():assert row['preservedPin'] in roles.finish()
    assert roles.git_evidence['actualExitCode']==0 and roles.git_evidence['timedOut'] is False
    assert roles.git_evidence['stdoutSha256']==data['sourceRoles']['acceptanceActivation']['originalPin']['sha256']
    assert data==before


@pytest.mark.parametrize('mutation',['schema','extra-role','missing-role','catalogue-original-sha','catalogue-original-path',
    'catalogue-commit','catalogue-registered-build','activation-original-sha','activation-other-attempt',
    'attempt-missing','attempt-alias','selection','acceptance-input','base-custody','reader-extra','reader-current-sha'])
def test_unknown_or_unbound_role_is_rejected(carrier,mutation):
    data,write,_=carrier
    if mutation=='schema':data['schemaVersion']='Unknown/v1'
    elif mutation=='extra-role':data['sourceRoles']['other']=deepcopy(data['sourceRoles']['catalogue'])
    elif mutation=='missing-role':del data['sourceRoles']['catalogue']
    elif mutation=='catalogue-original-sha':data['sourceRoles']['catalogue']['originalPin']['sha256']='0'*64
    elif mutation=='catalogue-original-path':data['sourceRoles']['catalogue']['originalPin']['path']=str(TASK/'unknown.py')
    elif mutation=='catalogue-commit':data['sourceRoles']['catalogue']['provenance']['sourceCommit']='0'*40
    elif mutation=='catalogue-registered-build':data['sourceRoles']['catalogue']['provenance']['registeredBuildPin']['sha256']='0'*64
    elif mutation=='activation-original-sha':data['sourceRoles']['acceptanceActivation']['originalPin']['sha256']='0'*64
    elif mutation=='activation-other-attempt':data['acceptanceAttemptPin']=deepcopy(data['attemptPins']['publication'])
    elif mutation=='attempt-missing':del data['attemptPins']['verification']
    elif mutation=='attempt-alias':data['attemptPins']['verification']=deepcopy(data['attemptPins']['publication'])
    elif mutation=='selection':data['selectionPin']['sha256']='0'*64
    elif mutation=='acceptance-input':data['acceptanceInputsPin']['sha256']='0'*64
    elif mutation=='base-custody':data['baseHistoricalCustodyPin']['sha256']='0'*64
    elif mutation=='reader-extra':data['readerCustodies'].append(deepcopy(data['readerCustodies'][0]))
    elif mutation=='reader-current-sha':data['currentReaderPins'][0]['sha256']='0'*64
    with pytest.raises((ValueError,OSError)):load(data,write)


@pytest.mark.parametrize('mutation',['bytes','missing','hardlink'])
def test_preserved_activation_requires_actual_separate_original(carrier,mutation):
    import os
    data,write,root=carrier;row=data['sourceRoles']['acceptanceActivation']
    if mutation=='missing':row['preservedPin']['path']=str(root/'missing')
    else:
        path=root/'original';path.write_bytes(Path(row['preservedPin']['path']).read_bytes())
        if mutation=='bytes':path.write_bytes(b'changed')
        else:os.link(path,root/'alias')
        row['preservedPin']=dict(row['preservedPin'],path=str(path))
    with pytest.raises((ValueError,OSError)):load(data,write)


@pytest.mark.parametrize('mutation',['commit','exit','argv','stdout'])
def test_native_self_report_cannot_authorize_another_blob(carrier,mutation):
    data,write,root=carrier;row=data['sourceRoles']['acceptanceActivation']
    native=json.loads(Path(row['provenance']['gitNativePin']['path']).read_bytes())
    if mutation=='commit':native['sourceCommit']='0'*40
    elif mutation=='exit':native['actualExitCode']=1
    elif mutation=='argv':native['argv'][-1]='HEAD:other.py'
    elif mutation=='stdout':native['stdoutPin']['sha256']='0'*64
    row['provenance']['gitNativePin']=write(native)
    with pytest.raises((ValueError,OSError)):load(data,write)


def test_finish_rechecks_actual_preserved_bytes(carrier):
    data,write,root=carrier
    # Preserve a separate actual reader file, then mutate it after admission.
    row=data['readerCustodies'][0];path=root/'reader.original';path.write_bytes(Path(row['preservedPin']['path']).read_bytes())
    row['preservedPin']=publication.file_pin(path)
    roles=load(data,write);path.write_bytes(b'changed after admission')
    with pytest.raises(ValueError):roles.finish()


def reconstructed(roles):
    result=[];source=roles.source_roles
    mappings={r['originalPin']['path']:r for r in roles.value['readerCustodies']}
    for old in roles.acceptance_attempt['inputPins']:
        if old==source['catalogue']['originalPin']:continue
        if old==source['acceptanceActivation']['originalPin'] or old['path'] in mappings:
            result.append(publication.file_pin(old['path']))
        else:result.append(old)
    indexed={p['path']:p for p in result}
    for pin in roles.finish():indexed[pin['path']]=pin
    return list(indexed.values())


def test_logical_collection_remains_exact_and_physical_additions_are_separate(carrier):
    data,write,_=carrier;roles=load(data,write);original=deepcopy(roles.acceptance_attempt['inputPins'])
    roles.verify_acceptance_inputs(original,reconstructed(roles))
    assert roles.acceptance_attempt['inputPins']==original


@pytest.mark.parametrize('mutation',['missing-unmapped','extra','changed-unmapped'])
def test_unrelated_logical_differences_are_rejected(carrier,mutation):
    data,write,root=carrier;roles=load(data,write);derived=reconstructed(roles)
    old=next(p for p in roles.acceptance_attempt['inputPins'] if p['path'].endswith('common.py'))
    if mutation=='missing-unmapped':derived=[p for p in derived if p!=old]
    elif mutation=='changed-unmapped':derived=[dict(p,sha256='0'*64) if p==old else p for p in derived]
    else:
        path=root/'extra';path.write_bytes(b'extra');derived.append(publication.file_pin(path))
    with pytest.raises(ValueError):roles.verify_acceptance_inputs(roles.acceptance_attempt['inputPins'],derived)


def test_no_argument_still_refuses_original_development_drift():
    with pytest.raises(ValueError,match='ORIGINAL_BYTES_CHANGED'):
        subject().load_historical_publication(TASK,PRIVATE,publication.file_pin(
            PRIVATE/'main-program-spug-historical-read-custody-20261110-r1.private.json'))


def test_legacy_existing_custody_mapping_cannot_be_overridden(carrier):
    data,write,_=carrier;roles=load(data,write)
    context=subject().load_context(TASK,PRIVATE,data['baseHistoricalCustodyPin'],source_roles=roles)
    old={k:data['sourceRoles']['catalogue'][k] for k in ('originalPin','preservedPin')}
    with pytest.raises(ValueError,match='CONFLICT'):
        context.verify_inputs('publication',data['attemptPins']['publication'],
            context.attempts['publication']['inputPins'],{old['originalPin']['path']:old},[])


def logical_case():
    import main_program_installation_selection as contract
    records=contract.Records(TASK)
    plan=records.read('main-program-configuration-plan-b5fa4c5-r7.json')
    secret=json.loads(publication.verify_bytes(plan['privatePlanPin']))
    build=records.read('release-build-45dd7dc.json')
    coverage_name='main-program-control-coverage-45dd7dc-r1.json';records.read(coverage_name)
    inputs=dict(sourceCommit=build['targetCommit'],coveragePin=records.references[coverage_name])
    originals=secret['currentSelections']
    old=value()['sourceRoles']['catalogue']['originalPin']
    checkout=publication.file_pin(Path(build['worktree'])/'backend/src/main/resources/recovery_control_restore_catalogue.py')
    physical=[checkout if p==old else p for p in originals['57']['localInstallationPins']]
    return records,inputs,build,originals,physical,checkout


def test_frozen_selection_recovers_only_the_proven_catalogue_logical_identity():
    generation=importlib.import_module('main_program_control_generation')
    records,inputs,build,originals,physical,_=logical_case();before=deepcopy(physical)
    logical=generation._catalogue_logical_materials(records,inputs,build,physical)
    for host in ('57','58','59'):assert logical==originals[host]['localInstallationPins']
    assert physical==before
    diagnostic=json.loads((PRIVATE/'spug-source-roles-generation-diagnostic-r1.private.json').read_bytes())
    assert {p['path']:p for p in physical}=={p['path']:p for p in diagnostic['actualPhysicalPins']}


@pytest.mark.parametrize('mutation',['commit','missing-checkout','changed-checkout','missing-linux-copy'])
def test_logical_projection_cannot_mask_unproven_physical_inputs(mutation):
    generation=importlib.import_module('main_program_control_generation')
    records,inputs,build,_,physical,checkout=logical_case()
    if mutation=='commit':inputs['sourceCommit']='0'*40
    elif mutation=='missing-checkout':physical=[p for p in physical if p!=checkout]
    elif mutation=='changed-checkout':physical=[dict(p,sha256='0'*64) if p==checkout else p for p in physical]
    else:physical.remove(checkout)
    with pytest.raises(ValueError):generation._catalogue_logical_materials(records,inputs,build,physical)
