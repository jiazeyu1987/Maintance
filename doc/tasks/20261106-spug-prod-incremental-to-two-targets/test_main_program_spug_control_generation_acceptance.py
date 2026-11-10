"""Pinned real history/plan and native receipts; no fabricated r7 activation."""
from copy import deepcopy
import importlib
import json
import hashlib
from pathlib import Path
import tempfile

import pytest

import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_verify_only as verify
import main_program_spug_historical_custody as history

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')


def subject():return importlib.import_module('main_program_spug_control_generation_acceptance')


@pytest.fixture(scope='module')
def actual():
    custody=publication.file_pin(PRIVATE/'main-program-spug-historical-read-custody-20261110-r1.private.json')
    ctx=history.load_context(TASK,PRIVATE,custody);records=contract.Records(TASK)
    verified=verify.validate_publication_v4(records,PRIVATE,ctx.selected,historical=ctx)
    inputs=records.pinned(ctx.selected['verificationInputsPin'])
    base=verify.prepare_value(records,PRIVATE,inputs,ctx.selected['verificationInputsPin'],historical=ctx)
    public=records.read('main-program-configuration-plan-b5fa4c5-r7.json')
    secret=json.loads(publication.verify_bytes(public['privatePlanPin']))
    core=records.pinned(ctx.selected['spugInstallationPin'])
    rich=json.loads(publication.verify_bytes(publication.file_pin(PRIVATE/(ctx.selected['spugInstallationPin']['file'][:-5]+'.private.json'))))
    ctx.finish()
    return dict(base=base,public=public,secret=secret,custody=custody,core=core,rich=rich,verified=verified)


def test_actual_four_payloads_and_twenty_seven_records_are_equivalent(actual):
    before=deepcopy(actual['secret'])
    result=subject().configuration_equivalence(actual['base'],actual['secret'])
    assert set(result)=={'newToPublished','configurationCount','retainedRegistrationCount','newConnectionFilesPublished'}
    assert len(result['newToPublished'])==len(set(result['newToPublished'].values()))==4
    assert result['configurationCount']==7 and result['retainedRegistrationCount']==27
    assert result['newConnectionFilesPublished'] is False
    assert actual['secret']==before


@pytest.mark.parametrize('change',['connection-extra','connection-missing','connection-value','entry','simple','bridge-extra',
    'bridge-route','retained-pin','retained-value','retained-missing','registration','selector','metadata','original-spug'])
def test_any_non_name_configuration_difference_is_rejected(actual,change):
    secret=deepcopy(actual['secret'])
    if change=='connection-extra':secret['newConnections']['unapproved.json']={}
    elif change=='connection-missing':secret['newConnections'].pop(next(iter(secret['newConnections'])))
    elif change=='connection-value':secret['newConnections'][next(iter(secret['newConnections']))]['unapproved']='changed'
    elif change=='entry':secret['entrySettings']['unapproved']=True
    elif change=='simple':secret['simpleSettings']['unapproved']=True
    elif change=='bridge-extra':secret['bridgeSettings']['unapproved']=True
    elif change=='bridge-route':secret['bridgeSettings']['targetConnections'][next(iter(secret['bridgeSettings']['targetConnections']))]='unapproved.json'
    elif change=='retained-pin':secret['retainedDocumentsByHost']['57'][0]['pin']['sha256']='0'*64
    elif change=='retained-value':secret['retainedDocumentsByHost']['57'][0]['value']['unapproved']=True
    elif change=='retained-missing':secret['retainedDocumentsByHost']['59'].pop()
    elif change=='registration':secret['registrations']['57']=[]
    elif change=='selector':secret['sourceRegistrationSelectors'].pop()
    elif change=='metadata':secret['originalMetadata'].pop()
    elif change=='original-spug':secret['originalSpug']['unapproved']=True
    with pytest.raises(ValueError):subject().configuration_equivalence(actual['base'],secret)


def test_connection_roles_cannot_be_swapped_even_with_the_same_payload_set(actual):
    secret=deepcopy(actual['secret']);routes=secret['bridgeSettings']['targetConnections']
    keys=[k for k,v in routes.items() if v in secret['newConnections']]
    assert len(keys)>=2
    routes[keys[0]],routes[keys[1]]=routes[keys[1]],routes[keys[0]]
    with pytest.raises(ValueError):subject().configuration_equivalence(actual['base'],secret)


def test_stage_programs_reuse_exact_readonly_bodies(actual):
    module=subject();prepared=dict(programView=actual['base'])
    assert module.schedule()==verify.schedule()
    for stage in module.schedule():
        program=module.stage_program(prepared,stage)
        assert program==verify.stage_program(actual['base'],stage)
        assert module.command_arguments(prepared,stage)==verify.command_arguments(actual['base'],stage)
        compile(program,stage,'exec')
        assert 'incremental_plan(' not in program and '/incremental-plan' not in program


@pytest.mark.parametrize('stage',['host-publish-57','spug-configuration-publish','reload','unknown'])
def test_no_write_stage_is_accepted(actual,stage):
    with pytest.raises(ValueError):subject().stage_program(dict(programView=actual['base']),stage)


def original_stage(actual,name):
    row=next(r for r in actual['rich']['stages'] if r['stage']==name)
    return json.loads(publication.verify_bytes(row['resultPin']))


def test_original_native_receipts_are_read_without_claiming_a_new_activation(actual):
    row=original_stage(actual,'host-verify-59')
    # Original r6 program/receipt only; this is not an r7 success fixture.
    subject().validate_stage_native(dict(programView=actual['base']),PRIVATE,row['stage'],row['nativeReceiptPins'],row['result'],[])


@pytest.mark.parametrize('change',['controller-pid','source-commit','argv'])
def test_an_original_native_success_cannot_be_reused_for_a_changed_program(actual,change):
    view=deepcopy(actual['base']);row=original_stage(actual,'host-verify-59')
    if change=='controller-pid':view['spec']['hostSpecs']['59']['controllers'][0]['pid']+=1
    elif change=='source-commit':view['spec']['hostSpecs']['59']['sourceCommit']='0'*40
    elif change=='argv':view['c1']['hostCommands']['59'].append('unapproved')
    with pytest.raises(ValueError):
        subject().validate_stage_native(dict(programView=view),PRIVATE,row['stage'],row['nativeReceiptPins'],row['result'],[])


def test_default_parser_does_not_request_remote_execution():
    args=subject().parser().parse_args(['--inputs','explicit.json'])
    assert args.verify is False


def test_missing_inputs_fail_before_a_transport_is_constructed(tmp_path,monkeypatch):
    module=subject()
    def forbidden(*args,**kwargs):raise AssertionError('transport must not be constructed')
    monkeypatch.setattr(module,'AcceptanceTransport',forbidden)
    with pytest.raises((ValueError,OSError)):
        module.run_request(tmp_path,tmp_path,'missing.json')


def projected_observation(actual):
    # Exact already-proven r6 publication values; protocol projection only.
    base=actual['base'];obs=deepcopy(base['verificationContext']['observation'])
    def pin(path,value):
        raw=publication.canonical(value)
        return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    obs['spug']['entryPid']=base['resourceTransition']['entryAfter']['pid']
    for row in base['spec']['spugSpec']['writes']:
        reference=pin(row['path'],row['value'])
        if row['path'] in publication.SETTINGS.values():
            name=next(k for k,v in publication.SETTINGS.items() if v==row['path'])
            obs['spug']['settings'][name]=reference
        else:obs['spug']['connections'][Path(row['path']).name]=reference
    obs['selectorsByHost']={host:[dict(path=row['path'],pin=pin(row['path'],row['value']))
        for row in spec['selectors']] for host,spec in base['spec']['hostSpecs'].items()}
    return obs


def test_pure_projection_keeps_original_expected_and_audit_paths(actual):
    # A real old completed bundle is used only at this pure protocol boundary.
    # The public prepare separately requires the actual completed r7 successor.
    base=actual['base'];candidate=actual['verified']['generation'];obs=projected_observation(actual)
    view=subject().project_published_configuration(base,candidate,obs)
    for host in contract.HOSTS:
        assert view['spec']['hostSpecs'][host]['selectors']==base['spec']['hostSpecs'][host]['selectors']
        assert view['spec']['hostSpecs'][host]['auditPath']==base['spec']['hostSpecs'][host]['auditPath']
    assert view['spec']['spugSpec']['writes']==base['spec']['spugSpec']['writes']
    assert view['spec']['spugSpec']['auditPath']==base['spec']['spugSpec']['auditPath']
    assert len(view['resourceTransition']['afterFiles'])==14


@pytest.mark.parametrize('change',['selector','settings','connection','product','entry','host-set'])
def test_projection_refuses_observation_drift(actual,change):
    obs=projected_observation(actual)
    if change=='selector':obs['selectorsByHost']['59'][0]['pin']['sha256']='0'*64
    elif change=='settings':obs['spug']['settings']['simple']['sha256']='0'*64
    elif change=='connection':obs['spug']['connections'][next(iter(obs['spug']['connections']))]['sha256']='0'*64
    elif change=='product':obs['spug']['productPins'][0]['sha256']='0'*64
    elif change=='entry':obs['spug']['entryPid']+=1
    elif change=='host-set':del obs['hostPreservationByHost']['59']
    with pytest.raises(ValueError):
        subject().project_published_configuration(actual['base'],actual['verified']['generation'],obs)


def test_actual_staged_record_is_never_a_completed_generation(actual,monkeypatch):
    module=subject();records=contract.Records(TASK)
    records.read('main-program-control-staging-59-b5fa4c5-r7-inputs.json')
    stage=records.read('chain-policy-control-staging-59-b5fa4c5-r7.json')
    assert stage['status']=='STAGED_NOT_ACTIVATED'
    inputs=dict(schemaVersion='MainProgramSpugControlGenerationAcceptanceInputs/v1',historicalReadCustodyPin=actual['custody'],
        controlGenerationPin=records.references['chain-policy-control-staging-59-b5fa4c5-r7.json'],
        observationPin=actual['public']['privatePlanPin'],verificationId='unit',
        outputFile='main-program-spug-control-acceptance-b5fa4c5-r7-unit.json')
    def forbidden(*args,**kwargs):raise AssertionError('transport must not be constructed')
    monkeypatch.setattr(module,'AcceptanceTransport',forbidden)
    with tempfile.NamedTemporaryFile(prefix='acceptance-contract-',suffix='.json',dir=TASK,delete=False) as stream:
        path=Path(stream.name);stream.write(publication.canonical(inputs))
    try:
        with pytest.raises(ValueError,match='MAIN_GENERATION_'):
            module.run_request(TASK,PRIVATE,path.name)
    finally:path.unlink()


@pytest.mark.parametrize('mode,exit_code',[('nonzero',7),('invalid-json',0),('timeout',None)])
def test_real_local_native_failure_retains_stage_and_original_exit(actual,tmp_path,mode,exit_code):
    import sys
    import main_program_spug_publication_continuation as continuation
    module=subject();base=actual['base'];prepared=dict(programView=base,inputs=dict(outputFile='local-native-'+mode+'.json'))
    recorder=continuation.ActualContinuationTransport(tmp_path,dict(inputs=prepared['inputs']))
    code={'nonzero':'print("native-error");raise SystemExit(7)',
          'invalid-json':'print("not-json")','timeout':'import time;time.sleep(3)'}[mode]
    class LocalBoundary:
        @property
        def receipts(self):return recorder.receipts
        def execute(self,stage):
            return recorder.command(stage,[sys.executable,'-B','-c',code],program=module.stage_program(prepared,stage),
                                    timeout=0.05 if mode=='timeout' else 5)
    rows=[]
    with pytest.raises(Exception):
        module._record_stage(prepared,tmp_path,'spug-guard-before',{},LocalBoundary(),rows)
    assert len(rows)==1
    stage=json.loads(publication.verify_bytes(rows[0]['resultPin']))
    assert stage['result']['status']=='UNKNOWN' and len(stage['nativeReceiptPins'])==1
    native=json.loads(publication.verify_bytes(stage['nativeReceiptPins'][0]))
    assert native['actualExitCode']==exit_code
    request=json.loads(publication.verify_bytes(native['requestPin']))
    assert request['argv']==[sys.executable,'-B','-c',code]
    assert request['automaticRetryPermitted'] is False
    assert not (tmp_path/prepared['inputs']['outputFile']).exists()


def test_real_returned_failure_is_preserved_when_local_validation_rejects(actual,tmp_path):
    import sys
    import main_program_spug_publication_continuation as continuation
    module=subject();stage='host-verify-59'
    prepared=dict(programView=actual['base'],inputs=dict(outputFile='local-returned-failure.json'))
    observed=dict(status='FAILED',errorCode='LOCAL_PROTOCOL_REFUSAL',detail={'reason':'preserve exact returned object'})
    code='import json;print(json.dumps('+repr(observed)+'))'
    recorder=continuation.ActualContinuationTransport(tmp_path,dict(inputs=prepared['inputs']))
    class LocalRecorderBoundary:
        @property
        def receipts(self):return recorder.receipts
        def command(self,label,argv,program,timeout):
            assert (argv,timeout)==module.command_arguments(prepared,stage)
            # Explicit external protocol boundary: actual local failure, never SSH.
            return recorder.command(label,[sys.executable,'-B','-c',code],program=program,timeout=5)
    transport=module.AcceptanceTransport(tmp_path,prepared);transport._recorder=LocalRecorderBoundary()
    rows=[]
    with pytest.raises(ValueError):module._record_stage(prepared,tmp_path,stage,{},transport,rows)
    result=json.loads(publication.verify_bytes(rows[0]['resultPin']))
    assert result['result']==observed
    assert result['validationError']['errorType']=='ValueError'
    native=json.loads(publication.verify_bytes(result['nativeReceiptPins'][0]))
    assert native['actualExitCode']==0
    assert json.loads(publication.verify_bytes(native['stdoutPin']))==observed
