"""Explicit, audited production correction using a newly tested immutable package."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3

from intruoyi_build import target_input_plan
from intruoyi_runtime import Runtime, file_sha, release_workflow, require


def prepare(state, tag, original_id, load_manifest):
    require(not any(job['status'] in ('running','interrupted') and not job.get('resolution')
                    for job in state['jobs']), 'Active or interrupted workflow prevents correction')
    original = next(job for job in state['jobs'] if job['id']==original_id)
    require(original.get('action')=='promote-prod' and original.get('target')=='prod'
            and original.get('status')=='failed' and original.get('effectsStarted')
            and not original.get('resolution')
            and original.get('error','').startswith('Route snapshot READINESS blocked:')
            and original.get('workflowPolicy',{}).get('productionRecovery')=='external',
            'Unresolved reviewed production snapshot failure required')
    package = next(item for item in state['packages'] if item['releaseTag']==tag)
    require(package.get('stage')=='tested' and tag>original['releaseTag'], 'New tested package required')
    technical = package.get('outcomes',{}).get('test',{}).get('technical',{})
    owner = next((job for job in state['jobs'] if job['id']==technical.get('jobId')), {})
    require(technical.get('status')=='passed' and technical.get('packageSha256')==package['packageSha256']
            and technical.get('releaseTag')==tag and owner.get('status')=='succeeded'
            and owner.get('target')=='test'
            and all(technical.get('checks',{}).get(key,{}).get('status')=='passed'
                    for key in ('version','upgrade','login')), 'Same-package test verification required')
    old = next(item for item in state['packages'] if item['releaseTag']==original['releaseTag'])
    load_manifest(old)
    manifest = load_manifest(package)
    operations = [item for item in original.get('remoteOperations',[])
                  if item.get('env')=='prod' and item.get('action')=='deploy']
    require(len(operations)==1, 'Unique original deployment operation required')
    incident = dict(version='stopped-origin-forward/v1',originalJobId=original_id,
        originalOperationId=operations[0]['operationId'],failedReleaseTag=original['releaseTag'],
        stagingRoot=original.get('runtimeStagingRoots',{}).get('prod'),manifestSha256=old['manifestSha256'],
        origin=original['originState'],appliedMigrations=[{key:item[key] for key in ('migrationId','sha256')}
            for item in original['migrationPlan']['items'] if item['action']=='APPLY'])
    return package,manifest,incident


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--original-job-id',required=True)
    parser.add_argument('--release-tag',required=True)
    parser.add_argument('--plan',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--confirm')
    args=parser.parse_args()
    output=Path(args.output)
    require(output.is_absolute() and not output.exists(), 'Fresh absolute private output required')
    config=json.loads(Path(args.config).read_text('utf-8-sig'))
    database=Path(config['stateDir'])/'state.sqlite3'
    with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as connection:
        state=json.loads(connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
    def load_manifest(package):
        path=Path(package['directory'])/'manifest.json'
        require(file_sha(path)==package['manifestSha256'],'Immutable manifest checksum differs')
        return json.loads(path.read_text('utf-8'))
    package,manifest,incident=prepare(state,args.release_tag,args.original_job_id,load_manifest)
    policy=release_workflow(config)
    require(policy and policy['productionRecovery']=='external','Confirmed external recovery configuration required')
    runtime=Runtime(config)
    observation=runtime.observe('prod')
    plan=target_input_plan(manifest['migrations'],observation['ledgerRecords'],'prod')
    manifest=dict(manifest,executionPlans={'prod':plan},workflowPolicy=dict(policy,targetEnvironment='prod',recoveryMode='external'))
    result=runtime.call('prod','inspect-correction-origin',manifest=manifest,incident=incident)
    record=dict(kind='authorized-maintenance-correction',taskId='20261119-update-and-release-prod',
                id='JOB-'+secrets.token_hex(5),releaseTag=args.release_tag,originalJobId=args.original_job_id,
                status='PRECHECK_PASSED',originFingerprint=result['fingerprint'])
    def save():
        output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not args.apply:
        save();print(json.dumps(dict(status=record['status'],databaseMutations=0)));return
    require(args.confirm=='PROD','Explicit PROD confirmation required')
    raw=Path(args.plan).read_bytes()
    require(len(raw)<=4*1024*1024,'Correction plan exceeds reviewed limit')
    raw.decode('utf-8')
    require(file_sha(Path(package['directory'])/'release.tar')==package['packageSha256'],'Immutable package checksum differs')
    record['status']='RUNNING';save()
    runtime.operation_context.binding=(record,save)
    try:
        runtime.stage('prod',package['directory'],load_manifest(package))
        result=runtime.call('prod','correct-imported-snapshots',manifest=manifest,incident=incident,
                            planJson=raw.decode('utf-8'),planSha256=hashlib.sha256(raw).hexdigest())
        record.update(status='CORRECTED',result=result);save()
        print(json.dumps(result))
    except Exception:
        record['status']='REQUIRES_INSPECTION';save()
        raise RuntimeError('Correction stopped; inspect the private maintenance record and original remote operation; do not replay') from None
    finally:
        runtime.operation_context.binding=None


if __name__=='__main__':
    main()
