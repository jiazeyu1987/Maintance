"""Read-only final evidence, including persisted remote operation receipts."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,sqlite3,subprocess,sys

task=Path(__file__).resolve().parent;root=Path('C:/SpugHandoff/release')
live=root/'source/ops/spug/release-center';sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime,ssh_source_bytes
output=task/'final-verification.json';assert not output.exists(),'Preserve earlier final evidence'
selection=json.loads((task/'selected-release.json').read_text('utf-8'))
tag=selection['fullReleaseTag'];sequence=json.loads((task/'full-validation-sequence.json').read_text('utf-8'))
assert sequence['status']=='PASS' and sequence['releaseTag']==tag
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as connection:
    state=json.loads(connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
jobs={j['id']:j for j in state['jobs']}
assert not any(j['status'] in ('running','queued') for j in jobs.values())
package=next(p for p in state['packages'] if p['releaseTag']==tag)
assert package['stage']=='completed' and package['gitCommit']==selection['commit']
patch=next(p for p in state['backendPatches'] if p['releaseTag']==selection['backendPatchTag'])
assert patch['stage']=='completed' and patch['gitCommit']==selection['commit']
manifest=json.loads((Path(package['directory'])/'manifest.json').read_text('utf-8'))
assert hashlib.sha256((Path(package['directory'])/'manifest.json').read_bytes()).hexdigest()==package['manifestSha256']
sealed=json.loads((task/'sealed-full-verification.json').read_text('utf-8'))
assert sealed['status']=='PASS' and sealed['packageSha256']==package['packageSha256'] and sealed['manifestSha256']==package['manifestSha256']
assert jobs['JOB-bd1f8db63f']['status']=='failed' and jobs['JOB-eeaf3711eb']['status']=='succeeded'
assert jobs['JOB-0a72553fa4']['status']=='failed' and jobs['JOB-0a72553fa4']['resolution']['jobId']=='JOB-b68b4b0044'
previous_cleanup_retry=json.loads((task/'cleanup-retry-submission.json').read_text('utf-8'))
assert jobs[previous_cleanup_retry['jobId']]['postReleaseCleanup']['status']=='failed'
cleanup_retry=json.loads((task/'cleanup-retry-legacy-submission.json').read_text('utf-8'))
assert cleanup_retry['realPlaywrightLogin'] and cleanup_retry['cleanupOf']=='JOB-7f32aa47ab'
retry=jobs[cleanup_retry['jobId']]
assert retry['action']=='retry-release-cleanup' and retry['cleanupOf']==cleanup_retry['cleanupOf']
selected=[jobs['JOB-b68b4b0044']]+[jobs[v['jobId']] for v in sequence['stages'] if v.get('jobId')]+[jobs[previous_cleanup_retry['jobId']],retry]
assert all(j['status']=='succeeded' and j['releaseTag']==tag for j in selected)
accept=next(j for j in selected if j['action']=='accept-backup')
assert accept.get('postReleaseCleanup',{}).get('status')=='failed','Preserve original cleanup failure'
cleanup=retry.get('postReleaseCleanup',{})
assert cleanup.get('status')=='succeeded','Wait for cleanup or inspect its independent failure'
runtime=Runtime(json.loads((root/'executor.private.json').read_text('utf-8')))

def remote_receipts(env):
    base=runtime.profile(env);entries=[]
    for job in selected:
        for operation in job.get('remoteOperations',[]):
            if operation['env']==env:
                entries.append(dict(operationId=operation['operationId'],action=operation['action'],jobId=job['id'],
                    stagingRoot=base['stagingRoot'] if operation['action']=='artifact-auto-clean' else job.get('runtimeStagingRoots',{}).get(env,base['stagingRoot'])))
    assert entries,env+': missing operation identities'
    code='from pathlib import Path\nimport json\nentries='+repr(entries)+r'''
result=[]
for item in entries:
    path=Path(item['stagingRoot'])/'.operations'/(item['operationId']+'.json')
    value=json.loads(path.read_text('utf-8'))
    assert value['operationId']==item['operationId'] and value['jobId']==item['jobId'] and value['action']==item['action']
    assert value['status']=='succeeded'
    worker_alive=False
    if value.get('pid') and value.get('processStart'):
        process=Path('/proc')/str(value['pid'])/'stat'
        if process.exists():
            raw=process.read_text()
            worker_alive=raw[raw.rfind(')')+2:].split()[19]==value['processStart']
    assert not worker_alive,'Terminal receipt still has a live worker'
    result.append(dict(operationId=value['operationId'],jobId=value['jobId'],action=value['action'],status=value['status'],workerAlive=False))
print(json.dumps(result))
'''
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+base['host'],base['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=60)
    if result.returncode:
        private=root/'private/backend-patch-full-release-20261102'
        (private/('final-receipt-'+env+'-error.private.log')).write_bytes(result.stderr)
    assert result.returncode==0,env+': persisted remote operation proof failed'
    return env,json.loads(result.stdout)

with ThreadPoolExecutor(max_workers=3) as pool: operations=dict(pool.map(remote_receipts,('test','prod','backup')))
databases=json.loads((task/'database-full.json').read_text('utf-8'))
before=json.loads((task/'database-patch.json').read_text('utf-8'))
assert all(v['schemaEqual'] for v in databases['comparisons'])
targets={}
for env,phase in [('test','full-test'),('prod','full-prod-open'),('backup','full-backup-open')]:
    proof=json.loads((task/('program-full-'+env+'.json')).read_text('utf-8'))[env]
    page=json.loads((task/('ui-gxp-'+phase+'-'+env+'.json')).read_text('utf-8'))
    assert proof['status']=='PASS' and proof['tag']==tag and proof['programMounts']==[]
    assert page['status']=='PASS' and page['realPlaywrightLogin'] and page['realVersionDialog'] and page['releaseTag']==tag
    assert page['savedMode']==page['runtimeMode']=='DEVELOPMENT_DISABLED' and page['auditEnabled'] is False and page['pendingRestart'] is False
    current=state['environments'][env]
    assert current['releaseTag']==tag and current['images']=={r:manifest['images'][r]['id'] for r in ('backend','frontend')}
    assert current['backendHealth']['status']=='UP' and current['frontendHttpStatus']==200 and current['maintenance'] is False
    assert databases['targets'][env]['schema']['sha256']==before['targets'][env]['schema']['sha256']
    assert databases['targets'][env]['migrations']==before['targets'][env]['migrations'],env+': own migration history changed'
    outcome=package['outcomes'][env]
    assert outcome['deployment']['status']=='succeeded' and outcome['technical']['status']=='passed'
    targets[env]=dict(url=runtime.profile(env)['entryUrl'],releaseTag=tag,jarSha256=proof['observation']['backendJarSha256'],
        images=current['images'],health='UP',frontendHttpStatus=200,programMounts=[],gxp='DEVELOPMENT_DISABLED',
        startupLogCount=proof['startupLogCount'],schemaCounts=databases['targets'][env]['schema']['counts'],ownMigrationHistoryPreserved=True,
        persistedOperations=len(operations[env]),cleanupStatus=cleanup['environments'][env]['status'])
assert len({v['jarSha256'] for v in targets.values()})==1
report=dict(status='PASS',backendPatchTag=selection['backendPatchTag'],fullReleaseTag=tag,sourceCommit=selection['commit'],
    sameSource=True,originalPackagePreserved=True,originalFailuresPreserved=True,temporaryBuildWorktreeRemoved=sealed['buildWorktreeRemoved'],
    businessWriteRegressionPerformed=False,targets=targets,operations=operations,cleanupRetryJobId=retry['id'],originalCleanupFailurePreserved=True,
    previousCleanupRetryFailurePreserved=True,
    totalCleanupFileBytes=sum(v.get('bytes',0) for j in (accept,jobs[previous_cleanup_retry['jobId']],retry) for v in j['postReleaseCleanup']['environments'].values()),
    cleanup={e:dict(status=v['status'],removedItems=len(v.get('removed',[])),fileBytes=v.get('bytes',0),retainedItems=len(v.get('retained',[])),
        blockedReleaseTags=v.get('plan',{}).get('blockedReleaseTags',[])) for e,v in cleanup['environments'].items()})
output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='PASS',fullReleaseTag=tag,targets=targets,cleanup=report['cleanup'])))
