"""Real historical files, no mocked publication completion or remote call."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import tempfile

import pytest

import main_program_installation_selection as contract
import main_program_spug_publication as publication

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
SELECTOR='main-program-current-installations-45dd7dc-r6-v4.json'
READERS=('main_program_spug_publication_continuation.py','spug_runtime_dependency_completion.py',
         'main_program_spug_publication_verify_only.py','main_program_spug_resource_transition.py')


def subject():return importlib.import_module('main_program_spug_historical_custody')


def make_value():
    records=contract.Records(TASK);selected=records.read(SELECTOR)
    vi=records.pinned(selected['verificationInputsPin']);base=records.pinned(vi['baseVerificationInputsPin'])
    c1=records.pinned(base['continuationInputsPin'])
    dep=records.pinned(base['dependencyActivationPin']);wrapper=records.pinned(vi['resourceTransitionPin'])
    transition=records.pinned(wrapper['transitionCorePin'])
    core=records.pinned(selected['spugInstallationPin'])
    rich_path=PRIVATE/(selected['spugInstallationPin']['file'][:-5]+'.private.json')
    rich=json.loads(rich_path.read_text(encoding='utf-8'))
    attempts=dict(publication=c1['originalAttemptPin'],continuation=base['continuationAttemptPin'],
        dependency=dep['attemptPin'],resourceTransition=transition['attemptPin'],verification=rich['attemptPin'])
    preserved=json.loads((PRIVATE/'spug-historical-read-originals-20261110-r1/preservation.json').read_text(encoding='utf-8'))
    rows=[]
    for label,reference in attempts.items():
        attempt=json.loads(publication.verify_bytes(reference))
        for row in preserved['readers']:
            if row['originalPin'] in attempt['inputPins']:
                rows.append(dict(attempt=label,**row,currentPin=publication.file_pin(row['originalPin']['path'])))
    return dict(schemaVersion='MainProgramSpugHistoricalReadCustody/v1',selectionPin=records.references[SELECTOR],
        verificationInputsPin=selected['verificationInputsPin'],verificationCorePin=selected['spugInstallationPin'],
        resourceTransitionReferencePin=vi['resourceTransitionPin'],attemptPins=attempts,
        activationSource=preserved['activationSource'],readerCustodies=rows,
        currentReaderPins=[publication.file_pin(TASK/name) for name in (*READERS,'main_program_spug_historical_custody.py')])


@pytest.fixture
def carrier():
    subject()  # Initial RED is missing the formal module, not a fake history.
    with tempfile.TemporaryDirectory(prefix='historical-custody-test-',dir=PRIVATE) as directory:
        path=Path(directory)/'custody.json'
        def write(value):
            path.write_bytes(publication.canonical(value));return publication.file_pin(path)
        yield make_value(),write,Path(directory)


def test_actual_completed_history_reads_with_explicit_custody(carrier):
    value,write,_=carrier
    before={str(p):publication.file_pin(p) for p in [TASK/SELECTOR,*[Path(p['path']) for p in value['attemptPins'].values()]]}
    result=subject().load_historical_publication(TASK,PRIVATE,write(value))
    assert set(result)=={'generation','inputPins'}
    assert result['generation']['generation']['sourceCommit']=='45dd7dc65409c87fe856584b85873ea96c0b830e'
    assert value['activationSource']['preservedPin'] in result['inputPins']
    assert before=={p:publication.file_pin(p) for p in before}


@pytest.mark.parametrize('tamper',['schema','selector','verification','core','transition','missing-attempt','extra-attempt',
    'attempt-alias','activation-sha','activation-size','activation-path','activation-missing','reader-extra','reader-duplicate',
    'reader-wrong-attempt','reader-original-sha','reader-current-sha','reader-current-missing','current-extra','current-duplicate'])
def test_explicit_scope_and_source_identity_are_required(carrier,tamper):
    value,write,directory=carrier
    if tamper=='schema':value['schemaVersion']='Unknown/v1'
    elif tamper=='selector':value['selectionPin']['sha256']='0'*64
    elif tamper=='verification':value['verificationInputsPin']['sha256']='0'*64
    elif tamper=='core':value['verificationCorePin']['sha256']='0'*64
    elif tamper=='transition':value['resourceTransitionReferencePin']['sha256']='0'*64
    elif tamper=='missing-attempt':del value['attemptPins']['verification']
    elif tamper=='extra-attempt':value['attemptPins']['other']=value['attemptPins']['publication']
    elif tamper=='attempt-alias':value['attemptPins']['verification']=value['attemptPins']['publication']
    elif tamper=='activation-sha':value['activationSource']['originalPin']['sha256']='0'*64
    elif tamper=='activation-size':value['activationSource']['originalPin']['bytes']=True
    elif tamper=='activation-path':value['activationSource']['originalPin']['path']=str(TASK/'observe_closeout_hosts.py')
    elif tamper=='activation-missing':value['activationSource']['preservedPin']['path']=str(directory/'missing.py')
    elif tamper=='reader-extra':value['readerCustodies'][0]['originalPin']['path']=str(TASK/'unknown.py')
    elif tamper=='reader-duplicate':value['readerCustodies'].append(deepcopy(value['readerCustodies'][0]))
    elif tamper=='reader-wrong-attempt':value['readerCustodies'][0]['attempt']='publication'
    elif tamper=='reader-original-sha':value['readerCustodies'][0]['originalPin']['sha256']='0'*64
    elif tamper=='reader-current-sha':value['readerCustodies'][0]['currentPin']['sha256']='0'*64
    elif tamper=='reader-current-missing':value['readerCustodies'][0]['currentPin']['path']=str(directory/'missing.py')
    elif tamper=='current-extra':value['currentReaderPins'].append(publication.file_pin(TASK/'main_program_installation_selection.py'))
    elif tamper=='current-duplicate':value['currentReaderPins'].append(value['currentReaderPins'][0])
    with pytest.raises((ValueError,OSError)):subject().load_context(TASK,PRIVATE,write(value))


def test_preserved_file_content_is_checked_not_its_self_report(carrier):
    value,write,directory=carrier
    p=directory/'changed.py';p.write_bytes(b'changed')
    value['activationSource']['preservedPin']=publication.file_pin(p)
    with pytest.raises(ValueError):subject().load_context(TASK,PRIVATE,write(value))


def test_private_preserved_hardlink_is_not_a_separate_original(carrier):
    import os
    value,write,directory=carrier
    first=directory/'one.py';first.write_bytes(Path(value['activationSource']['preservedPin']['path']).read_bytes())
    second=directory/'two.py';os.link(first,second)
    raw=first.read_bytes();value['activationSource']['preservedPin']=dict(path=str(second),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(ValueError):subject().load_context(TASK,PRIVATE,write(value))


def test_attempt_mapping_does_not_overwrite_an_existing_custody(carrier):
    value,write,_=carrier;context=subject().load_context(TASK,PRIVATE,write(value))
    attempt=json.loads(publication.verify_bytes(value['attemptPins']['publication']))
    row=value['activationSource']
    with pytest.raises(ValueError,match='CONFLICT'):
        context.verify_inputs('publication',value['attemptPins']['publication'],attempt['inputPins'],{row['originalPin']['path']:row},[])


def test_same_path_other_attempt_sha_is_not_accepted(carrier):
    value,write,_=carrier;context=subject().load_context(TASK,PRIVATE,write(value))
    attempt=json.loads(publication.verify_bytes(value['attemptPins']['dependency']))
    old=next(p for p in attempt['inputPins'] if p['path']==str(TASK/'spug_runtime_dependency_completion.py'))
    other=next(r for r in value['readerCustodies'] if r['originalPin']['path']==old['path'])
    assert old['sha256']!=other['originalPin']['sha256']
    with pytest.raises(ValueError):context.verify_reference('dependency',old,[])


def test_reader_current_bytes_are_rechecked_at_finish(carrier):
    value,write,_=carrier;context=subject().load_context(TASK,PRIVATE,write(value))
    context.finish()
    # A changed pin is a protocol-negative, not a successful loaded-module mock.
    context.current_pins[0]['sha256']='0'*64
    with pytest.raises(ValueError):context.finish()


def test_old_no_context_entry_keeps_exact_drift_failure():
    import main_program_spug_publication_continuation as continuation
    with pytest.raises(ValueError,match='ORIGINAL_BYTES_CHANGED'):
        continuation.prepare_continuation(TASK,PRIVATE,'main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json')


def test_history_context_has_no_dispatch_mode(carrier):
    value,write,_=carrier;context=subject().load_context(TASK,PRIVATE,write(value))
    assert not any(hasattr(context,name) for name in ('apply','execute','observe','transport','publish'))


def test_current_pin_must_belong_to_the_loaded_reader(carrier,monkeypatch):
    value,write,directory=carrier
    reader=importlib.import_module('main_program_spug_publication_verify_only')
    other=directory/'other-reader.py';other.write_bytes(Path(reader.__file__).read_bytes())
    # Negative imported-module identity, not a mocked successful history.
    monkeypatch.setattr(reader,'__file__',str(other))
    with pytest.raises(ValueError,match='LOADED_READER'):
        subject().load_context(TASK,PRIVATE,write(value))


def test_a_missing_attempt_specific_reader_mapping_cannot_borrow_another(carrier):
    value,write,_=carrier
    row=next(r for r in value['readerCustodies'] if r['attempt']=='verification' and
             r['originalPin']['path']==str(TASK/'main_program_spug_publication_continuation.py'))
    value['readerCustodies'].remove(row)
    assert any(r['originalPin']==row['originalPin'] for r in value['readerCustodies'])
    with pytest.raises(ValueError,match='ORIGINAL_BYTES_CHANGED'):
        subject().load_historical_publication(TASK,PRIVATE,write(value))


def test_transition_without_context_keeps_the_original_reader_call_protocol(carrier,monkeypatch):
    import main_program_spug_resource_transition as transition
    import main_program_spug_publication_verify_only as verify
    value,_,_=carrier;records=contract.Records(TASK)
    wrapper=records.pinned(value['resourceTransitionReferencePin'])
    core=records.pinned(wrapper['transitionCorePin']);inputs=records.pinned(core['transitionInputsPin'])
    class BoundaryReached(Exception):pass
    def original_reader(records,private,inputs,pin):
        raise BoundaryReached()  # Observe the protocol; never fabricate a successful history.
    monkeypatch.setattr(verify,'prepare_value',original_reader)
    with pytest.raises(BoundaryReached):
        transition._prepare(records,PRIVATE,inputs,core['transitionInputsPin'],verify_checkout=False)
