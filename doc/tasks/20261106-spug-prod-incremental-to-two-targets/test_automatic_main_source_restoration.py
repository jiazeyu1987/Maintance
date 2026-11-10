"""Local evidence protocol tests; synthetic terminals never claim real success."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

TASK=Path(__file__).resolve().parent
sys.path.insert(0,str(TASK))
import verify_automatic_source_restoration as source
from verify_automatic_backup_chain import prepare as formal_package

PRIVATE=Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
CYCLE='main-20261110-r6'
SELECTION='main-program-current-installations-45dd7dc-r6-v4.json'
SUBMISSION='automatic-main-20261110-r6-i1-ui-submission.json'
BINDINGS=('deploymentSelectionPin','controlGenerationPin','spugInstallationPin',
          'sourceCaptureConfigurationPin','sourceOwnerConfigurationPin')


def put(root,name,value):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode('utf-8');path.write_bytes(raw)
    return dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


@pytest.fixture(scope='module')
def package():
    # Actual local installed-deployment records, with the formal v4 reader.
    # Does not observe services, dispatch a backup or create an audit/terminal.
    return formal_package(TASK/SUBMISSION,parent_path=TASK/'automatic-i2-audit.json',selection_path=TASK/SELECTION)


def protocol(package):
    submission=json.loads((TASK/SUBMISSION).read_bytes())
    audit=deepcopy(package['parent']);operation=submission['request']['operationId']
    point=dict(path='/protocol/'+operation+'/point.json',bytes=1,sha256='0'*64)
    audit.update(operationId=operation,pointType='INCREMENTAL',finishedAt='2026-11-10T04:00:00Z',pointPin=point,
        chain=[*deepcopy(package['parent']['chain']),dict(operationId=operation,pointPin=point,
            pointType='INCREMENTAL',epochBindingPin=point)],**deepcopy(package['deployment']))
    audit['package']=dict(engine=package['engine'],variant='standard',fileCount=147,
        fileManifestSha256=package['fileManifestSha256'],allInstalledFilesShaVerified=True,
        repositoryProgramPin=dict(path=package['engine']+'/common/repository_minimal.py',bytes=1,
            sha256=package['files']['common/repository_minimal.py']),
        fullReaderPin=dict(path=package['engine']+'/common/repository_native_readback.py',bytes=1,
            sha256=package['files']['common/repository_native_readback.py']))
    terminal=dict(schemaVersion='AutomaticIncrementalUiTerminal/v3',kind='I1',applicationId=submission['applicationId'],
        observedAt='2026-11-10T04:00:01Z',request=deepcopy(submission['request']),plan=deepcopy(submission['plan']),
        operationState='SUCCEEDED',spugHistoryId=999,observation='protocol',preflightSha256='0'*64,
        implementationCommit=submission['implementationCommit'],spugCommit=submission['spugCommit'],cycle=CYCLE,
        **{k:deepcopy(submission[k]) for k in BINDINGS})
    return submission,audit,terminal


def test_actual_closed_private_plan_provides_original_source_and_target_policy(package):
    installation=source.main_installation(package)
    assert installation['schemaVersion']=='MainProgramAutomaticSourceInstallation/v1'
    assert installation['controllers']==package['deployment']['controllerGenerations']
    assert installation['fileCount']==147
    assert installation['policy']['schemaVersion']=='SourceBackupEpochPolicy/v1'
    from automatic_chain_audit import canonical
    assert hashlib.sha256(canonical(installation['policy'])).hexdigest()==package['parent']['sourceEpoch']['policySha256']


@pytest.mark.parametrize('kind,full_sha',[('I1',False),('I2',True),('FULL',True)])
def test_main_protocol_kind_reports_original_full_sha_scope(package,kind,full_sha):
    package=deepcopy(package);submission,audit,terminal=protocol(package)
    submission['kind']=terminal['kind']=kind
    if kind=='FULL':
        submission['request']['action']=terminal['request']['action']=audit['pointType']='FULL'
        submission['request']['parentChainRef']=terminal['request']['parentChainRef']=None
        package['request']=deepcopy(submission['request']);package['parent']=None
        audit['chain']=audit['chain'][-1:];audit['chain'][0]['pointType']='FULL'
    result=source.validate_main_evidence(kind,source.main_installation(package),submission,audit,terminal,package,CYCLE)
    assert result['failedOriginalFullShaRequired'] is full_sha
    assert result['operationId']==submission['request']['operationId']
    assert result['schemaVersion']=='MainProgramAutomaticSourceRestorationSpec/v1'


@pytest.mark.parametrize('change',['schema','cycle','operation','state','count','manifest','deployment','owner',
    'terminal-schema','terminal-cycle','terminal-state','terminal-request','terminal-plan','terminal-time','parent','readback'])
def test_main_rejects_cross_cycle_package_or_unsuccessful_proofs(package,change):
    submission,audit,terminal=protocol(package)
    if change=='schema':submission['schemaVersion']='AutomaticIncrementalUiSubmission/v2'
    elif change=='cycle':submission['cycle']='another'
    elif change=='operation':audit['operationId']='smallapp-'+'0'*32
    elif change=='state':audit['state']='RUNNING'
    elif change=='count':audit['package']['fileCount']=130
    elif change=='manifest':audit['package']['fileManifestSha256']='0'*64
    elif change=='deployment':audit['spugInstallationPin']['sha256']='0'*64
    elif change=='owner':audit['sourceOwnerConfigurationPin']['sha256']='0'*64
    elif change=='terminal-schema':terminal['schemaVersion']='AutomaticIncrementalUiTerminal/v1'
    elif change=='terminal-cycle':terminal['cycle']='another'
    elif change=='terminal-state':terminal['operationState']='RUNNING'
    elif change=='terminal-request':terminal['request']['parentChainRef']='other'
    elif change=='terminal-plan':terminal['plan']['planDigest']='0'*64
    elif change=='terminal-time':terminal['observedAt']='2026-11-09T00:00:00Z'
    elif change=='parent':audit['chain'][0]['operationId']='other'
    elif change=='readback':audit['readback']['payloadContentVerified']=False
    with pytest.raises(ValueError,match='SOURCE_MAIN_'):
        source.validate_main_evidence('I1',source.main_installation(package),submission,audit,terminal,package,CYCLE)


def write_protocol(tmp_path,package):
    submission,audit,terminal=protocol(package)
    for name in (SUBMISSION,SELECTION,'automatic-i2-audit.json','binlog-tmpfs-tool-provisioned.json',
                 'registered-binlog-tool-restored.json','automatic_chain_audit.py'):
        (tmp_path/name).write_bytes((TASK/name).read_bytes())
    put(tmp_path,'protocol-audit.json',audit)
    baseline=json.loads((TASK/submission['baselineEvidencePin']['file']).read_bytes())
    baseline['operationId']=submission['request']['operationId']
    terminal['baselineEvidencePin']=put(tmp_path,'protocol-verify-baseline.json',baseline)
    put(tmp_path,'automatic-'+CYCLE+'-i1-ui-terminal.json',terminal)
    observation=dict(schemaVersion='AutomaticIncrementalUiObservation/v1',kind='I1',phase='verify',
        observation='protocol',status='SUCCEEDED_VERIFIED',realBrowser=True,identityVerified=True,permissionVerified=True,
        businessPosts=0,blockedRequests=[],pageErrorCount=0,request=deepcopy(submission['request']),
        operationState='SUCCEEDED',implementationCommit=submission['implementationCommit'],spugCommit=submission['spugCommit'],
        cycle=CYCLE,preflightSha256=terminal['preflightSha256'],baselineEvidencePin=terminal['baselineEvidencePin'],
        **{k:deepcopy(submission[k]) for k in BINDINGS})
    put(tmp_path,'automatic-'+CYCLE+'-i1-verify-protocol-result.json',observation)
    return submission,audit,terminal,observation


def test_prepare_uses_one_actual_formal_reader_and_keeps_protocol_success_only_in_tmp(tmp_path,package,monkeypatch):
    write_protocol(tmp_path,package);calls=[]
    def actual_reader(path,*args,**kwargs):
        # File-root protocol seam only: both submission/selection/parent raw
        # bytes must be the real originals before redirecting the closure root.
        assert path.read_bytes()==(TASK/SUBMISSION).read_bytes()
        assert kwargs['selection_path'].read_bytes()==(TASK/SELECTION).read_bytes()
        assert kwargs['parent_path'].read_bytes()==(TASK/'automatic-i2-audit.json').read_bytes()
        calls.append(path)
        return formal_package(TASK/SUBMISSION,parent_path=TASK/'automatic-i2-audit.json',selection_path=TASK/SELECTION)
    monkeypatch.setattr(source,'prepare_package',actual_reader)
    monkeypatch.setattr(source,'remote',lambda *a,**k:pytest.fail('remote read is forbidden'))
    destination,spec=source.prepare('I1',cycle=CYCLE,selection_path=tmp_path/SELECTION,
        audit_path=tmp_path/'protocol-audit.json',parent_path=tmp_path/'automatic-i2-audit.json',task=tmp_path,private=PRIVATE)
    assert len(calls)==1
    assert destination==tmp_path/('automatic-'+CYCLE+'-i1-source-restoration.json') and not destination.exists()
    assert spec['installation']['schemaVersion']=='MainProgramAutomaticSourceInstallation/v1'
    assert spec['installation']['fileCount']==len(spec['files'])==147 and spec['failedPins']==[]
    assert spec['failedOriginalFullShaRequired'] is False
    assert spec['deployment']==package['deployment'] and len(spec['inputPins'])>1000
    assert len(spec['controllerFiles'])==2


@pytest.mark.parametrize('mode',['selection-only','cycle-only','audit-outside','parent-outside','exists','missing-terminal'])
def test_main_paths_and_original_output_fail_before_remote(tmp_path,mode):
    args=dict(cycle=CYCLE,selection_path=tmp_path/SELECTION,task=tmp_path,private=PRIVATE)
    if mode=='selection-only':args['cycle']=None
    elif mode=='cycle-only':args['selection_path']=None
    elif mode=='audit-outside':args['audit_path']=TASK/'automatic-i2-audit.json'
    elif mode=='parent-outside':args['parent_path']=TASK/'automatic-i2-audit.json'
    elif mode=='exists':put(tmp_path,'automatic-'+CYCLE+'-i1-source-restoration.json',{'original':True})
    with pytest.raises((ValueError,FileExistsError,FileNotFoundError)):
        source.prepare('I1',**args)


@pytest.mark.parametrize('mode',['observation-state','observation-post','observation-binding','baseline-operation','baseline-plan'])
def test_verify_observation_and_baseline_are_original_terminal_proofs(tmp_path,package,mode):
    submission,audit,terminal,observation=write_protocol(tmp_path,package)
    if mode.startswith('observation'):
        if mode=='observation-state':observation['status']='ORIGINAL_OBSERVED_AFTER_UNKNOWN'
        elif mode=='observation-post':observation['businessPosts']=1
        else:observation['controlGenerationPin']['sha256']='0'*64
        put(tmp_path,'automatic-'+CYCLE+'-i1-verify-protocol-result.json',observation)
    else:
        baseline=json.loads((tmp_path/'protocol-verify-baseline.json').read_bytes())
        if mode=='baseline-operation':baseline['operationId']='other'
        else:baseline['expectedPlan']['planDigest']='0'*64
        terminal['baselineEvidencePin']=put(tmp_path,'protocol-verify-baseline.json',baseline)
    with pytest.raises(ValueError,match='SOURCE_MAIN_'):
        source.verify_main_terminal_files('I1',CYCLE,submission,terminal,tmp_path)


def test_readonly_carrier_keeps_original_source_health_and_full_sha_contract():
    for fragment in ('SOURCE_GLOBAL_STATE_INVALID','SOURCE_FIVE_SERVICES_REQUIRED','SOURCE_REDIS_PING_FAILED',
        'SOURCE_SEMANTIC_HEALTH_FAILED','SOURCE_WORKER_ACTIVE','SOURCE_LOCK_CHANGED','SOURCE_EPOCH_CHANGED',
        'SOURCE_FAILED_ORIGINAL_SCOPE_CHANGED',"10044 if full else 0"):
        assert fragment in source.SCRIPT
