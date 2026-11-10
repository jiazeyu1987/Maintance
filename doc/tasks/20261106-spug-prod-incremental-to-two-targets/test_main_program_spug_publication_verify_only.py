"""Read real historical receipts locally; fixtures never claim a live publication."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
import ast

import pytest

import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_continuation as continuation
import spug_runtime_dependency_completion as dependency

TASK=Path(__file__).resolve().parent
PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')


def subject():return importlib.import_module('main_program_spug_publication_verify_only')


@pytest.fixture(scope='module')
def originals():
    records=contract.Records(TASK)
    c1=continuation.prepare_continuation(TASK,PRIVATE,'main-program-spug-publication-inputs-45dd7dc-r6-continuation-c1.json')
    failure=continuation.private_json(PRIVATE,publication.file_pin(PRIVATE/'main-program-spug-installation-45dd7dc-r6-continuation-c1.private.json'),[])
    custody=records.read('spug-verification-source-custody-r1.json')
    activation=records.read('main-program-spug-runtime-dependency-activation-c7728ad-r1.json')
    return records,c1,failure,custody,activation


def test_real_c1_prefix_accepts_only_its_formal_source_custody(originals):
    records,c1,failure,custody,_=originals;pins=[]
    result=dependency.validate_failed_continuation(c1,PRIVATE,failure,pins,historical_source_custody=custody)
    assert result==dict(appliedCount=7,hostVerifications=3,lastNativeError='SIMPLE_CONFIGURATION_INVALID',lastNativeExitCode=0)
    assert custody['entries'][0]['preservedPin'] in pins


@pytest.mark.parametrize('tamper',['extra','attempt','role','pin'])
def test_c1_custody_cannot_skip_other_original_inputs(originals,tamper):
    _,c1,failure,value,_=originals;value=deepcopy(value)
    if tamper=='extra':value['entries'].append(value['entries'][0])
    elif tamper=='attempt':value['continuationAttemptPin']['sha256']='0'*64
    elif tamper=='role':value['entries'][0]['originalPin']['path']=str(TASK/'observe_closeout_hosts.py')
    else:value['entries'][0]['preservedPin']['sha256']='0'*64
    with pytest.raises(ValueError):dependency.validate_failed_continuation(c1,PRIVATE,failure,[],historical_source_custody=value)


def test_actual_completed_dependency_activation_is_deeply_read(originals):
    records,c1,failure,custody,activation=originals
    actual=subject().load_completed_dependency_activation(records,PRIVATE,
        records.references['main-program-spug-runtime-dependency-activation-c7728ad-r1.json'],c1,failure,custody)
    assert actual['core']==activation and actual['core']['entryAfter']['pid']==151963
    assert len(actual['rich']['nativeReceiptPins'])==15 and len(actual['rich']['stagePins'])==7
    assert actual['core']['liveUiVerified'] is False


def test_default_cli_has_no_publish_or_activation_mode():
    args=subject().parser().parse_args(['--inputs','fixture.json']);assert args.verify is False
    for flag in ('--apply','--activate','--publish'):
        with pytest.raises(SystemExit):subject().parser().parse_args(['--inputs','fixture.json',flag])


def test_unknown_verification_inputs_fail_before_any_command():
    with pytest.raises(ValueError,match='VERIFICATION_INPUTS_INVALID'):
        subject().prepare_value(contract.Records(TASK),PRIVATE,{'schemaVersion':'wrong'},None)


def test_schedule_contains_only_six_explicit_read_phases():
    assert subject().schedule()==['spug-guard-before','host-verify-57','host-verify-58','host-verify-59','spug-verify','spug-guard-after']


def actual_inputs(records,c1,failure):
    activation_name='main-program-spug-runtime-dependency-activation-c7728ad-r1.json'
    records.read(activation_name);records.read('spug-verification-source-custody-r1.json')
    runner=records.read('spug-c1-runner-terminal-r1.json')
    return dict(schemaVersion='MainProgramSpugPublicationVerificationInputs/v1',
        **{k:c1['inputs'][k] for k in ('sourceCommit','revisionId','controlGenerationPin')},
        continuationInputsPin=c1['inputPin'],continuationAttemptPin=failure['attemptPin'],
        continuationFailurePin=publication.file_pin(PRIVATE/'main-program-spug-installation-45dd7dc-r6-continuation-c1.private.json'),
        continuationCompletionPin=runner['completionPin'],dependencyActivationPin=records.references[activation_name],
        historicalSourceCustodyPin=records.references['spug-verification-source-custody-r1.json'],verificationId='v1',
        outputFile='main-program-spug-installation-45dd7dc-r6-continuation-c1-verification-v1.json')


@pytest.fixture(scope='module')
def prepared(originals):
    records,c1,failure,_,_=originals
    return subject().prepare_value(records,PRIVATE,actual_inputs(records,c1,failure),None)


def test_actual_prepare_changes_only_verified_entry_pid(prepared):
    expected=deepcopy(prepared['c1']['originalSpec'])
    expected['spugSpec']['observation']['entryPid']=151963
    assert prepared['spec']==expected
    assert prepared['dependency']['nativeDiagnosticPins'] and prepared['prefix']['appliedCount']==7


@pytest.mark.parametrize('stage',['host-publish-57','spug-custody','spug-configuration-publish','host-verify-60','unknown'])
def test_dispatch_plan_has_no_write_lane(prepared,stage):
    with pytest.raises(ValueError,match='STAGE_NOT_ALLOWED'):subject().stage_program(prepared,stage)


def test_host_and_spug_verify_programs_reuse_original_bodies(prepared):
    module=subject()
    for host in contract.HOSTS:
        assert module.stage_program(prepared,'host-verify-'+host)==continuation.original.program('host',host,'verify',prepared['spec']['hostSpecs'][host])
    assert module.stage_program(prepared,'spug-verify')==continuation.original.program('spug',None,'verify',prepared['spec']['spugSpec'])
    assert module.stage_program(prepared,'spug-guard-before')==module.stage_program(prepared,'spug-guard-after')


def test_verify_transport_never_exposes_configuration_writers():
    value=subject().VerificationTransport
    assert not any(hasattr(value,name) for name in ('install','prepare_custody','host_publish','publish','reload'))


def test_incomplete_native_stage_cannot_be_finalized(prepared):
    with pytest.raises(ValueError,match='STAGE_SET_INCOMPLETE'):subject().aggregate(prepared,[])


@pytest.mark.parametrize('consumer',['selector','collector'])
def test_v4_dispatch_refuses_incomplete_verification_instead_of_accepting_control_only(tmp_path,consumer):
    module=subject();bad=tmp_path/'bad.json';bad.write_bytes(publication.canonical({'schemaVersion':'control-only'}))
    reference=dict(file=bad.name,bytes=bad.stat().st_size,sha256=publication.file_pin(bad)['sha256'])
    selected=dict(schemaVersion='TaskMainProgramInstallations/v4',sourceCommit='a'*40,controlGenerationPin=reference,
                  spugInstallationPin=reference,verificationInputsPin=reference)
    (tmp_path/'selection.json').write_bytes(publication.canonical(selected))
    with pytest.raises(ValueError,match='MAIN_SPUG_VERIFICATION_INPUTS_INVALID'):
        if consumer=='selector':contract.select_main_program_installation('57',tmp_path,selection_file='selection.json',private=PRIVATE)
        else:
            import observe_closeout_hosts
            observe_closeout_hosts.controller_selection('57',tmp_path,selection_file='selection.json',private=PRIVATE)


@pytest.mark.parametrize('mode',['nonzero','invalid-json','timeout'])
def test_real_local_native_failure_preserves_unique_gate_without_retry(prepared,tmp_path,mode):
    module=subject();value=deepcopy(prepared);value['inputs']['outputFile']='local-contract-verification.json'
    records=tmp_path/'task';private=tmp_path/'private';records.mkdir();private.mkdir()
    context=deepcopy(value['c1']);context['inputs']['outputFile']=value['inputs']['outputFile']
    class LocalFailedNative:
        def __init__(self):self.native=continuation.ActualContinuationTransport(private,context);self.calls=0
        @property
        def receipts(self):return self.native.receipts
        def execute(self,stage):
            self.calls+=1
            code={'nonzero':'raise SystemExit(3)','invalid-json':'print("not-json")','timeout':'import time;time.sleep(2)'}[mode]
            return self.native.command(stage,[sys.executable,'-X','utf8','-B','-c',code],timeout=.1 if mode=='timeout' else 10)
    transport=LocalFailedNative()
    with pytest.raises(ValueError,match='VERIFICATION_FAILED_CHECK_PRIVATE_EVIDENCE'):
        module.execute_prepared(records,private,value,transport=transport)
    assert transport.calls==1 and not (records/value['inputs']['outputFile']).exists()
    failed=json.loads((private/'local-contract-verification.private.json').read_bytes())
    assert failed['status']=='FAILED' and failed['stage']=='spug-guard-before'
    assert len(failed['stages'])==1 and failed['retryPermitted'] is False
    native=json.loads(Path(transport.receipts[0]['path']).read_bytes())
    assert native['actualExitCode']==({'nonzero':3,'invalid-json':0,'timeout':None}[mode])
    with pytest.raises(ValueError,match='ALREADY_ATTEMPTED'):
        module.execute_prepared(records,private,value,transport=transport)
    assert transport.calls==1


def test_after_selection_changes_default_historical_validation_still_refuses(originals):
    _,c1,failure,custody,_=originals
    current=publication.file_pin(Path(custody['entries'][0]['originalPin']['path']))
    assert current!=custody['entries'][0]['originalPin']
    with pytest.raises(ValueError):dependency.validate_failed_continuation(c1,PRIVATE,failure,[])


@pytest.mark.parametrize('tamper',['container','program','stdout','timeout'])
def test_real_native_receipt_cannot_be_reassigned(originals,tamper):
    records,_,_,_,activation=originals;module=subject();pins=[]
    rich=continuation.private_json(PRIVATE,activation['privateEvidencePin'],pins)
    native=continuation.validate_native_receipts(PRIVATE,rich['nativeReceiptPins'],pins)[1]
    receipt,request,result=native;argv=list(request['argv'])
    program=continuation.private_raw(PRIVATE,request['stdinPin'],pins).decode();timeout=request['timeoutSeconds']
    output=deepcopy(result)
    module.validate_native_command(PRIVATE,native,argv,program,output,pins,timeout=timeout)
    if tamper=='container':argv[3]='0'*64
    elif tamper=='program':program+='\n# unbound payload\n'
    elif tamper=='stdout':output['status']='unrelated'
    else:timeout+=1
    with pytest.raises(ValueError,match='NATIVE_COMMAND_CHANGED'):
        module.validate_native_command(PRIVATE,native,argv,program,output,[],timeout=timeout)


def test_a_only_approved_function_changed_from_actual_execution_custody(originals):
    records,_,_,_,activation=originals
    complete=records.pinned(activation['dependencyCompletionPin'])
    custody=continuation.private_json(PRIVATE,complete['sourceCustodyPin'],[])
    old=next(row for row in custody['entries'] if Path(row['originalPin']['path']).name==Path(dependency.__file__).name)
    before=ast.parse(continuation.private_raw(PRIVATE,old['preservedPin'],[]).decode('utf-8'))
    after=ast.parse(Path(dependency.__file__).read_text(encoding='utf-8'))
    def other(tree):return [ast.dump(node,include_attributes=False) for node in tree.body
        if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) or node.name!='validate_failed_continuation']
    assert other(before)==other(after)


def test_original_a_test_changes_only_formal_custody_argument(originals):
    records,_,_,_,activation=originals
    complete=records.pinned(activation['dependencyCompletionPin'])
    custody=continuation.private_json(PRIVATE,complete['sourceCustodyPin'],[])
    old=next(row for row in custody['entries'] if Path(row['originalPin']['path']).name=='test_spug_runtime_dependency_completion.py')
    before=continuation.private_raw(PRIVATE,old['preservedPin'],[]).decode('utf-8')
    after=Path(old['originalPin']['path']).read_text(encoding='utf-8')
    expected=before.replace('    result=subject().validate_failed_continuation(prepared,PRIVATE,failure,pins)\n',
        "    custody=json.loads((TASK/'spug-verification-source-custody-r1.json').read_text(encoding='utf-8'))\n"
        '    result=subject().validate_failed_continuation(prepared,PRIVATE,failure,pins,historical_source_custody=custody)\n')
    expected=expected.replace("    with pytest.raises(ValueError,match='DEPENDENCY_'):\n        subject().validate_failed_continuation(prepared,PRIVATE,failure,[])\n",
        "    custody=json.loads((TASK/'spug-verification-source-custody-r1.json').read_text(encoding='utf-8'))\n"
        "    with pytest.raises(ValueError,match='DEPENDENCY_'):\n        subject().validate_failed_continuation(prepared,PRIVATE,failure,[],historical_source_custody=custody)\n")
    assert after==expected.replace('\r\n','\n')
