"""Actual local originals and package/prepare/validation contracts.

The remote terminal and host observations are explicit protocol fixtures, not
claims of a real stage. No command transport or server is used by this suite.
"""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

import main_program_control_activation as activation
import main_program_control_staging as staging
from test_main_program_control_staging import prepared_records
from test_main_program_control_upgrade_plan import originals


DIAGNOSTIC=b'close - IO is still pending on closed socket. read:1, write:0, io:0000020515B12EF0\r\n'


def module():return importlib.import_module('main_program_control_staging_finalize')


def local_pin(path):
    raw=path.read_bytes()
    return dict(file=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture
def recorded(prepared_records,monkeypatch):
    task,private,_,_,save=prepared_records
    previous=json.loads((task/'fixture-input-58.json').read_bytes())
    keys=('sourceCommit','revisionId','suffix','previousControlGenerationPin','buildPin','planPin',
        'coveragePin','unitObservationPin','originalEnvironmentObservationPin')
    inputs=dict(schemaVersion='MainProgramControlStagingInputs/v1',**{key:previous[key] for key in keys})
    save(task,'staging-input.json',inputs)
    prepared=staging.run_request(task,private,'staging-input.json')
    engine=json.loads((task/prepared['engineReportFile']).read_bytes())
    for name in ('engineReportFile','configurationReportFile'):(task/prepared[name]).unlink()
    envelope=staging.execution_bundle(prepared);script=staging.render_bootstrap(envelope).encode('utf-8')
    stem='main-program-control-staging-58-45dd7dc-r5'
    attempt=dict(schemaVersion='MainProgramControlStagingAttempt/v1',status='ATTEMPT_RESERVED',inputs=inputs,
        prepared=prepared,executionInputPins=envelope['prepared']['executionInputPins'],payloadBytes=len(script),
        payloadSha256=hashlib.sha256(script).hexdigest(),remoteHost='172.30.30.58',backupDispatched=False,restoreDispatched=False)
    before=dict(controllers=engine['controls'],containers={'registered-container':{'protocol':'original'}},
        fstabPin={'sha256':'a'*64},mountinfoSha256='b'*64,documentsCreated=False)
    new=prepared['filesystemSpec']['newDocuments'];retained=prepared['filesystemSpec']['retainedDocuments']
    created=[row['path'] for row in engine['engines']]+[row['pin']['path'] for row in new]
    actual=dict(before=before,after=dict(before,documentsCreated=True),
        candidate=dict(controllers=[dict(actualConfigurationReadPassed=True,directlyAdmittedSources=list(staging.SOURCES),
            archiveViewsPreflightVerified=True,epoch={'state':'READY'})]),
        files=dict(status='FILES_STAGED_RUNTIME_UNVERIFIED',activationReportEligible=False,
            sourceCommit=inputs['sourceCommit'],revisionId=inputs['revisionId'],host=attempt['remoteHost'],
            engines=engine['engines'],createdPaths=created,newDocuments=[r['pin'] for r in new],
            retainedDocuments=[r['pin'] for r in retained],requiredRuntimeGates=list(staging.RUNTIME_GATES)))
    result=dict(status='STAGED_NOT_ACTIVATED',stage='complete',reports=staging.project_stage_reports(prepared,actual),
        actual=actual,createdPaths=created,filesMayHaveBeenCreated=True,backupDispatched=False,
        restoreDispatched=False,controlServicesReloaded=False)
    request=dict(schemaVersion='MainProgramControlStagingFinalizeInputs/v1')
    def put(tail,raw):
        path=private/(stem+'-'+tail);path.write_bytes(raw);return local_pin(path)
    request['attemptPin']=put('attempt.private.json',staging.canonical(attempt))
    def terminal(value=None,stderr=DIAGNOSTIC,exit_code=0,timed_out=False,stdout=None):
        value=deepcopy(result) if value is None else value
        raw=staging.canonical(value)+b'\n' if stdout is None else stdout
        out=put('stdout.private.log',raw);err=put('stderr.private.log',stderr)
        transport=dict(schemaVersion='MainProgramControlStagingTransport/v1',actualExitCode=exit_code,timedOut=timed_out,
            filesMayHaveBeenCreated=True,automaticRetryAllowed=False,
            stdoutPin=dict(path=str(private/out['file']),bytes=out['bytes'],sha256=out['sha256']),
            stderrPin=dict(path=str(private/err['file']),bytes=err['bytes'],sha256=err['sha256']))
        request['transportPin']=put('transport.private.json',staging.canonical(transport))
        request['resultPin']=put('result.private.json',staging.canonical(value))
    terminal()
    def forbidden(*args,**kwargs):raise AssertionError('No command or remote transport is authorized')
    monkeypatch.setattr(staging,'native_transport',forbidden)
    monkeypatch.setattr(staging,'remote_stage',forbidden)
    return dict(task=task,private=private,prepared=prepared,request=request,attempt=attempt,result=result,
        terminal=terminal,stem=stem,put=put)


def snapshot(case):
    return {str(p):p.read_bytes() for root in (case['task'],case['private']) for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('stderr',[b'',DIAGNOSTIC])
def test_prepare_and_finalize_consume_original_stage_without_transport(recorded,stderr):
    c=recorded;c['terminal'](stderr=stderr);subject=module();before=snapshot(c)
    ready=subject.prepare(c['task'],c['private'],c['request'])
    assert ready['status']=='READY_TO_FINALIZE' and snapshot(c)==before
    output=subject.finalize(c['task'],c['private'],c['request'])
    assert output['status']=='STAGED_NOT_ACTIVATED' and output['remoteDispatched'] is False
    reports={key:json.loads((c['task']/output[key+'StagedPin']['file']).read_bytes()) for key in ('engine','configuration')}
    for key,report in reports.items():
        assert {k:v for k,v in report.items() if k not in ('privateSnapshotPin','transportEvidencePin')}==c['result']['reports'][key]
        assert report['transportEvidencePin']==activation.file_pin(c['private']/c['request']['transportPin']['file'])
        assert report['privateSnapshotPin']==activation.file_pin(c['private']/c['request']['resultPin']['file'])
    plan=json.loads((c['task']/c['prepared']['inputs']['planPin']['file']).read_bytes())
    activation.validate_generation_staging(c['prepared']['inputs'],plan,c['prepared']['filesystemSpec']['build'],
        reports['engine'],reports['configuration'])
    assert all(Path(path).read_bytes()==raw for path,raw in before.items())
    after=snapshot(c)
    with pytest.raises(ValueError,match='OUTPUT_EXISTS'):subject.finalize(c['task'],c['private'],c['request'])
    assert snapshot(c)==after


@pytest.mark.parametrize('kind',['missing','tampered','input-drift','payload-drift','execution-pin','coverage-missing'])
def test_changed_originals_or_full_closure_refuse_without_output(recorded,kind):
    c=recorded
    if kind=='missing':(c['private']/c['request']['resultPin']['file']).unlink()
    elif kind=='tampered':(c['private']/c['request']['transportPin']['file']).write_bytes(b'{}')
    elif kind=='input-drift':(c['task']/'staging-input.json').write_bytes(b'{}')
    elif kind=='coverage-missing':(c['task']/c['prepared']['inputs']['coveragePin']['file']).unlink()
    else:
        value=deepcopy(c['attempt'])
        if kind=='payload-drift':value['payloadSha256']='f'*64
        else:value['executionInputPins'][0]['sha256']='f'*64
        c['request']['attemptPin']=c['put']('attempt.private.json',staging.canonical(value))
    before=snapshot(c)
    with pytest.raises((ValueError,OSError)):module().finalize(c['task'],c['private'],c['request'])
    assert snapshot(c)==before


@pytest.mark.parametrize('kind',['nonzero','timeout','unknown','incomplete','backup-flag','bad-core','duplicate-json','result-diverges'])
def test_nonterminal_or_untrusted_result_is_never_published(recorded,kind):
    c=recorded;value=deepcopy(c['result']);kwargs={}
    if kind=='nonzero':kwargs['exit_code']=1
    elif kind=='timeout':kwargs['timed_out']=True
    elif kind=='unknown':value['status']='UNKNOWN'
    elif kind=='incomplete':value['stage']='candidate-final'
    elif kind=='backup-flag':value['backupDispatched']=True
    elif kind=='bad-core':value['reports']['configuration']['existingPhysicalLockAcquiredAndReleased']=False
    elif kind=='duplicate-json':kwargs['stdout']=staging.canonical(value)+b'\n'+staging.canonical(value)
    else:kwargs['stdout']=staging.canonical(dict(value,status='FAILED'))+b'\n'
    c['terminal'](value=value,**kwargs);before=snapshot(c)
    with pytest.raises(ValueError):module().finalize(c['task'],c['private'],c['request'])
    assert snapshot(c)==before


@pytest.mark.parametrize('stderr',[b'permission denied\r\n',DIAGNOSTIC+b'other warning\r\n',
    DIAGNOSTIC.replace(b'read:1',b'read:2'),DIAGNOSTIC.replace(b'0000020515B12EF0',b'not-a-pointer'),DIAGNOSTIC[:-2]])
def test_only_exact_known_ssh_diagnostic_is_allowed(recorded,stderr):
    c=recorded;c['terminal'](stderr=stderr);before=snapshot(c)
    with pytest.raises(ValueError,match='STDERR_UNRECOGNIZED'):module().finalize(c['task'],c['private'],c['request'])
    assert snapshot(c)==before


def test_existing_single_output_refuses_without_touching_other_originals(recorded):
    c=recorded;(c['task']/c['prepared']['engineReportFile']).write_bytes(b'original partial output')
    before=snapshot(c)
    with pytest.raises(ValueError,match='OUTPUT_EXISTS'):module().finalize(c['task'],c['private'],c['request'])
    assert snapshot(c)==before


def test_missing_explicit_input_fails_without_importing_transport(tmp_path):
    private=tmp_path/'private';private.mkdir();before=list(tmp_path.iterdir())
    with pytest.raises((ValueError,OSError)):module().run_request(tmp_path,private,'missing.json',finalize_output=True)
    assert list(tmp_path.iterdir())==before
