"""Local state-machine tests; recording transports do not prove a deployment."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

import main_program_spug_publication as reader
import main_program_installation_selection as contract
from test_main_program_publication_v2 import v2, planning_case
from test_main_program_control_generation import case, load, physical_pin, save
from test_main_program_spug_publication import actual_r4_material


def subject():
    return importlib.import_module('main_program_spug_publication_v2')


@pytest.fixture
def protocol(v2):
    """Only a local recording transport; no host or Docker command is run."""
    value=v2;bundle=load(value);private=value['private'];task=value['task']
    responses={row['stage']:json.loads(Path(row['resultPin']['path']).read_bytes())['result']
        for row in value['rich']['stages']}
    for row in value['rich']['stages']:Path(row['resultPin']['path']).unlink()
    (private/value['rich_name']).unlink();(task/value['inputs']['outputFile']).unlink()
    records=contract.Records(task);records.read(value['input_pin']['file'])
    context=reader.v2_context(records,private,value['inputs'],value['input_pin'])
    spec=dict(inputs=value['inputs'],publicationInputsPin=value['input_pin'],
        generationPins={k:value['value'][k] for k in ('buildPin','planPin')},
        inputPins=records.path_pins()+bundle['inputPins']+context['resourcePins']+
            [value['inputs']['publicationObservationPin']],resourceSourceCommit=value['resource']['sourceCommit'],
        hostSpecs={h:dict(sourceCommit=value['inputs']['sourceCommit'],controllers=bundle['controllersByHost'][h],
            auditPath='/fixture/publication-'+h,sourceRefs=list(reader.SOURCES)) for h in contract.HOSTS},
        spugSpec=dict(sourceCommit=value['inputs']['sourceCommit'],auditPath='/fixture/publication-spug',
            observation=context['observation']['spug']),remotePublicationSupported=False)
    return dict(value,spec=spec,responses=responses)


class Recorder:
    def __init__(self, value, change=None):self.value=value;self.change=change;self.calls=[]
    def __call__(self,lane,host,phase,program):
        stage=lane+'-'+phase+('-'+host if host else '')
        self.calls.append(stage)
        prefix=self.value['inputs']['outputFile'].removesuffix('.json')+'.'+stage
        request=self.value['private']/(prefix+'.request.private.json')
        assert request.is_file(), 'request must be durable before the transport runs'
        record=json.loads(request.read_bytes())
        assert record['stage']==stage
        assert record['programPin']['sha256']==hashlib.sha256(program.encode('utf-8')).hexdigest()
        assert physical_pin(Path(record['programPin']['path']))==record['programPin']
        compile(program,'actual-generated-transport-program','exec')
        result=deepcopy(self.value['responses'][stage])
        if self.change:self.change(stage,result)
        return result


def test_default_request_performs_real_prepare_but_no_transport_or_receipt(planning_case):
    value=planning_case;before=set(value['private'].iterdir())
    result=subject().run_request(value['task'],value['private'],value['input_pin']['file'])
    assert result['status']=='PREPARED_NOT_APPLIED' and result['remoteDispatched'] is False
    assert set(value['private'].iterdir())==before


def test_twelve_recorded_phases_create_independent_proofs_before_public_core(protocol):
    value=protocol;transport=Recorder(value)
    result=subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=transport)
    assert transport.calls==reader.publication_schedule()
    assert result['status']=='PASS' and result['report']==value['inputs']['outputFile']
    result=contract.select_main_program_installation('57',value['task'],private=value['private'],
        selection_file=value['selection_pin']['file'])
    assert result['sourceCommit']==value['value']['sourceCommit']
    rich=json.loads((value['private']/value['rich_name']).read_bytes())
    assert len(rich['stages'])==12
    assert len({r['resultPin']['path'] for r in rich['stages']})==12
    assert all(physical_pin(Path(r['resultPin']['path']))==r['resultPin'] for r in rich['stages'])


@pytest.mark.parametrize('stage',reader.publication_schedule())
def test_any_actual_stage_failure_stops_without_public_core_or_retry(protocol,stage):
    value=protocol
    def change(actual,result):
        if actual==stage:result['status']='FAILED'
    recorder=Recorder(value,change)
    with pytest.raises(ValueError,match='V2_PUBLICATION_FAILED_CHECK_PRIVATE_REPORT'):
        subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=recorder)
    assert recorder.calls==reader.publication_schedule()[:reader.publication_schedule().index(stage)+1]
    assert not (value['task']/value['inputs']['outputFile']).exists()
    raw=json.loads((value['private']/value['rich_name']).read_bytes())
    assert raw['status']=='FAILED'
    assert len(raw['stages'])==len(recorder.calls)
    assert json.loads(Path(raw['stages'][-1]['resultPin']['path']).read_bytes())['result']['status']=='FAILED'


def test_transport_timeout_keeps_unknown_original_and_never_retries(protocol):
    value=protocol
    def change(stage,result):raise TimeoutError('local protocol timeout')
    recorder=Recorder(value,change)
    with pytest.raises(ValueError,match='V2_PUBLICATION_FAILED_CHECK_PRIVATE_REPORT'):
        subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=recorder)
    assert recorder.calls==['host-preflight-57']
    rich=json.loads((value['private']/value['rich_name']).read_bytes())
    original=json.loads(Path(rich['stages'][0]['resultPin']['path']).read_bytes())
    assert original['result']['status']=='UNKNOWN'
    assert original['result']['errorType']=='TimeoutError'
    assert not (value['task']/value['inputs']['outputFile']).exists()


def test_repeated_attempt_is_rejected_before_transport(protocol):
    value=protocol;recorder=Recorder(value,lambda stage,result:result.update(status='FAILED'))
    with pytest.raises(ValueError):subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=recorder)
    before={p:p.read_bytes() for p in value['private'].iterdir()}
    next_recorder=Recorder(value)
    with pytest.raises(ValueError,match='V2_ATTEMPT_EXISTS'):
        subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=next_recorder)
    assert next_recorder.calls==[] and all(p.read_bytes()==raw for p,raw in before.items())


def test_input_drift_between_phases_stops_before_next_dispatch(protocol):
    value=protocol
    def change(stage,result):
        if stage=='host-preflight-57':
            p=value['task']/value['input_pin']['file'];p.write_bytes(p.read_bytes()+b' ')
    recorder=Recorder(value,change)
    with pytest.raises(ValueError,match='V2_PUBLICATION_FAILED_CHECK_PRIVATE_REPORT'):
        subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=recorder)
    assert recorder.calls==['host-preflight-57']
    assert not (value['task']/value['inputs']['outputFile']).exists()


@pytest.mark.parametrize('lane,host',[('host','57'),('spug',None)])
def test_generated_carrier_contains_exact_original_program(lane,host):
    spec=dict(sourceCommit='d'*40,phase='verify')
    carrier=subject().program(lane,host,'verify',spec)
    compile(carrier,'carrier','exec')
    original=reader.payload(reader.HOST_PROGRAM if lane=='host' else reader.SPUG_PROGRAM,spec,'verify')
    # The outer carrier calls the exact embedded program, without replacing a
    # guard or editing its AST. Its literal is recoverable from the generated AST.
    import ast
    strings=[n.value for n in ast.walk(ast.parse(carrier)) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
    assert original in strings


def test_bad_result_generation_is_not_accepted_as_success(protocol):
    value=protocol;recorder=Recorder(value,lambda stage,result:result.update(sourceCommit='f'*40))
    with pytest.raises(ValueError,match='V2_PUBLICATION_FAILED_CHECK_PRIVATE_REPORT'):
        subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=recorder)
    assert recorder.calls==['host-preflight-57']


def test_final_reader_refusal_preserves_phase_originals_without_public_success(protocol):
    value=protocol
    def change(stage,result):
        if stage=='spug-verify':result['bridgeSelections'].pop()
    recorder=Recorder(value,change)
    with pytest.raises(ValueError,match='V2_PUBLICATION_FAILED_CHECK_PRIVATE_REPORT'):
        subject()._execute_prepared(value['task'],value['private'],value['spec'],transport=recorder)
    assert recorder.calls==reader.publication_schedule()
    assert not (value['task']/value['inputs']['outputFile']).exists()
    stages=json.loads((value['private']/value['rich_name']).read_bytes())['stages']
    assert len(stages)==12 and all(Path(r['resultPin']['path']).is_file() for r in stages)
    failure=value['private']/(value['inputs']['outputFile'].removesuffix('.json')+'.finalization-failure.private.json')
    assert json.loads(failure.read_bytes())['status']=='FAILED'


def test_cli_requires_explicit_apply():
    args=subject().parser().parse_args(['--inputs','explicit-input.json'])
    assert args.apply is False
