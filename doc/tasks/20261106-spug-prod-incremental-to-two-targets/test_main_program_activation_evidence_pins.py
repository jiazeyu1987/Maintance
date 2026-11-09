"""Real temporary evidence bytes; transport fixtures are not host success proof."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import main_program_control_activation as subject
import test_main_program_control_activation as original_tests
from test_main_program_control_generation_activation import prepared_protocol, coverage_documents, originals


@pytest.mark.parametrize('raw', [b'original command --fixed-argument\n', b'import sys\nprint(sys.version)\n',
    b'\x00\xff\xfe\x80binary\r\n', b'{"original":true}'])
def test_generic_pin_verification_preserves_arbitrary_original_bytes(tmp_path, raw):
    path=tmp_path/'evidence.original';path.write_bytes(raw);ref=subject.file_pin(path)
    assert subject.verify_local_pin(path,ref)==ref
    assert path.read_bytes()==raw


@pytest.mark.parametrize('change',['same-length','size','expected-sha'])
def test_generic_pin_verification_rejects_changed_identity_bytes_or_sha(tmp_path,change):
    path=tmp_path/'evidence.log';path.write_bytes(b'original command\n');ref=subject.file_pin(path)
    if change=='same-length':path.write_bytes(b'changed! command\n')
    elif change=='size':path.write_bytes(b'changed')
    else:ref['sha256']='0'*64
    with pytest.raises(ValueError,match='PIN_CHANGED'):subject.verify_local_pin(path,ref)


def test_generic_pin_verification_keeps_original_non_file_rejection(tmp_path):
    with pytest.raises(ValueError,match='FILE_ALIAS'):
        subject.verify_local_pin(tmp_path,dict(bytes=0,sha256='0'*64))


def test_explicit_json_consumers_keep_their_existing_return_value(tmp_path):
    path=tmp_path/'private.json';value={'original':{'nested':[1,2]}}
    path.write_bytes(subject.canonical(value));ref=subject.file_pin(path)
    assert subject.checked_local(path,ref)==value
    assert subject.private_document(tmp_path,ref,path.name)==value


def test_explicit_json_consumers_reject_raw_logs_before_receipt_writes(tmp_path):
    path=tmp_path/'private.log';path.write_bytes(b'original raw command\n');ref=subject.file_pin(path)
    with pytest.raises(json.JSONDecodeError):subject.checked_local(path,ref)
    with pytest.raises(json.JSONDecodeError):subject.private_document(tmp_path,ref,path.name)
    archive=tmp_path/'archived.json'
    with pytest.raises(json.JSONDecodeError):subject.rotate_receipt(path,archive,ref,{})
    assert not archive.exists() and path.read_bytes()==b'original raw command\n'


def test_complete_v4_prepare_accepts_real_non_json_historical_inputs(prepared_protocol,originals):
    """Reuse existing explicit generation/host protocol seam, real planner/tars."""
    import main_program_control_upgrade_plan
    task,private,bundle,old_plan_ref,save=prepared_protocol
    refs=[]
    for name,raw in [('original-command.log',b'fixed original command\n'),('original-code.py',b'VALUE = 1\n'),
                     ('original-binary.bin',b'\x00\xff\xfeoriginal')]:
        path=task/name;path.write_bytes(raw);refs.append(subject.file_pin(path))
    bundle['selections']['59']['localInstallationPins']=refs
    bundle['inputPins'].extend(refs)
    old_plan=json.loads((task/old_plan_ref['file']).read_bytes())
    kwargs=deepcopy(originals.kwargs)
    kwargs.update(predecessor=bundle,private_plan_path=old_plan['privatePlanPin']['path'],observed_at=old_plan['observedAt'])
    planned=main_program_control_upgrade_plan.plan_control_upgrade(**kwargs)
    save(private,Path(old_plan['privatePlanPin']['path']).name,planned['privatePlan'])
    plan_ref=save(task,old_plan_ref['file'],planned['plan'])
    name='fixture-input-59.json';value=json.loads((task/name).read_bytes())
    value.update(planPin=plan_ref,role='target',precedingActivationPins=[],
        outputFile='main-program-control-activation-59-target-45dd7dc-r5.json')
    for field in ('engineStagedPin','configurationStagedPin'):
        stage=json.loads((task/value[field]['file']).read_bytes());stage['planPin']=plan_ref
        value[field]=save(task,value[field]['file'],stage)
    save(task,name,value)
    before={path:path.read_bytes() for path in task.rglob('*') if path.is_file()}
    spec,payload=subject.prepare(task,private,name)
    assert all(ref in spec['immutablePrivatePins'] for ref in refs)
    assert subject.dispatch_prepared(task,private,spec,payload)['remoteDispatched'] is False
    assert {path:path.read_bytes() for path in task.rglob('*') if path.is_file()}==before


@pytest.mark.parametrize('changed_during_transport',[False,True])
def test_post_dispatch_closure_verifies_raw_evidence_without_json_assumption(tmp_path,changed_during_transport):
    """Only the existing remote-observation protocol is isolated; no SSH occurs."""
    fixture=original_tests.CoreProjectionTests();fixture.setUp();spec=fixture.spec
    task=tmp_path/'task';private=tmp_path/'private';task.mkdir();private.mkdir()
    raw=private/'original.log';raw.write_bytes(b'original command\n');ref=subject.file_pin(raw)
    spec.update(current={'host':'172.30.30.59'},inputPins=[ref],helperPins=[])
    spec['inputs']['outputFile']='protocol-result.json'
    for key in ('privatePlanPin','privateUnitPin'):
        path=private/(key+'.json');path.write_bytes(b'{"protocol":true}');spec[key]=subject.file_pin(path)
    calls=[]
    def transport(host,payload,timeout):
        calls.append((host,payload,timeout))
        if changed_during_transport:raw.write_bytes(b'changed! command\n')
        return deepcopy(fixture.observed)
    if changed_during_transport:
        with pytest.raises(ValueError,match='PIN_CHANGED'):
            subject.dispatch_prepared(task,private,spec,'local protocol only',activate=True,transport=transport)
        assert not (task/spec['inputs']['outputFile']).exists()
    else:
        result=subject.dispatch_prepared(task,private,spec,'local protocol only',activate=True,transport=transport)
        assert result['status']=='PASS' and raw.read_bytes()==b'original command\n'
    assert len(calls)==1
