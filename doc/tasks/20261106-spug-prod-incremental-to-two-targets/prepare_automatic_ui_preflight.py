"""Fresh installation/runtime gates; no backup dispatch, control query audit may write."""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import os
from common import TASK, PRIVATE, SOURCE, remote, now, write
from automatic_stage_deployment import load_stage_deployment, HISTORICAL_COMMIT


def verify_deployment_inputs(root, installed_commit, spug_files, component='combined'):
    """Allow unrelated history while binding this component to its installed commit.

    Compare HEAD, index and worktree independently: reverting a local file must
    not hide a committed or staged change. The installed allowlist defines source
    files; its builders/baseline/transforms and recovery directory are closed scopes.
    """
    if not re.fullmatch(r'[0-9a-f]{40}', installed_commit):
        raise RuntimeError('INSTALLED_COMMIT_NOT_FOUND')

    def git(*args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=30,
                                env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
        if result.returncode:
            raise RuntimeError('DEPLOYMENT_GIT_CHECK_FAILED')
        return result.stdout

    resolved = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify',
                               installed_commit + '^{commit}'], capture_output=True, timeout=30)
    if resolved.returncode or resolved.stdout.decode().strip() != installed_commit:
        raise RuntimeError('INSTALLED_COMMIT_NOT_FOUND')
    head = git('rev-parse', 'HEAD').decode().strip()
    ancestor = subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor',
                               installed_commit, head], capture_output=True, timeout=30)
    if ancestor.returncode == 1:
        raise RuntimeError('INSTALLED_COMMIT_NOT_HEAD_ANCESTOR')
    if ancestor.returncode:
        raise RuntimeError('DEPLOYMENT_GIT_CHECK_FAILED')

    def relative(name):
        if (not isinstance(name, str) or not name or '\\' in name or ':' in name or
                PurePosixPath(name).is_absolute() or
                any(part in ('', '.', '..') for part in name.split('/'))):
            raise RuntimeError('DEPLOYMENT_INPUT_PATH_INVALID')
        return name

    if component not in ('combined','source','spug'):
        raise RuntimeError('DEPLOYMENT_COMPONENT_INVALID')
    mapping = json.loads(git('show', installed_commit + ':ops/backup_engine/files.json')) if component != 'spug' else {}
    if (component != 'spug' and (not isinstance(mapping, dict) or not mapping)) or (component != 'source' and not spug_files):
        raise RuntimeError('DEPLOYMENT_INPUT_MANIFEST_INVALID')
    scopes = set()
    if component != 'spug':scopes.update({'ops/backup_engine','ops/recovery',*[relative(name) for name in mapping]})
    if component != 'source':scopes.update('ops/spug/'+relative(name) for name in spug_files)
    scopes = sorted(scopes)
    specs = [':(top,literal)' + name for name in scopes]
    comparisons = [('diff', '--name-only', '-z', '--no-renames', installed_commit, head),
                   ('diff', '--cached', '--name-only', '-z', '--no-renames', installed_commit),
                   ('diff', '--name-only', '-z', '--no-renames', installed_commit),
                   ('ls-files', '--others', '--exclude-standard', '-z')]
    for comparison in comparisons:
        if git(*comparison, '--', *specs):
            raise RuntimeError('AUTOMATIC_DEPLOYMENT_INPUTS_CHANGED')
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise RuntimeError('DEPLOYMENT_HEAD_CHANGED_DURING_CHECK')
    return dict(installedCommit=installed_commit, headCommit=head,
                installedCommitIsAncestor=True, deploymentInputsUnchanged=True,
                deploymentInputScopes=scopes)


def verify_stage_deployment_inputs(root, source_commit, spug_commit, spug_files):
    source=verify_deployment_inputs(root,source_commit,[],component='source')
    spug=verify_deployment_inputs(root,spug_commit,spug_files,component='spug')
    if source['headCommit'] != spug['headCommit']:
        raise RuntimeError('DEPLOYMENT_HEAD_CHANGED_DURING_CHECK')
    return dict(source=source,spug=spug)


def verify_submission_identity(submission, kind, commit, deployment=None):
    """Bind a post-operation health observation to the unchanged UI request."""
    schema=submission['schemaVersion']
    if schema=='AutomaticIncrementalUiSubmission/v1':
        assert kind=='FULL' and commit==HISTORICAL_COMMIT,'UNKNOWN_LEGACY_SUBMISSION_GENERATION'
    else:
        assert schema=='AutomaticIncrementalUiSubmission/v2' and deployment,'EXPLICIT_SUBMISSION_DEPLOYMENT_REQUIRED'
        assert submission['spugCommit']==deployment['spugCommit']
        assert submission['deploymentSelectionPin']==deployment['selectionPin']
    assert submission['kind'] == kind and submission['implementationCommit'] == commit
    assert submission['applicationId'] == submission['request']['sourceConfigRef'] == SOURCE
    operation = submission['request']['operationId']
    assert re.fullmatch(r'smallapp-[0-9a-f]{32}', operation)
    assert submission['intent']['operationId'] == operation
    assert submission['request']['action'] == ('FULL' if kind == 'FULL' else 'INCREMENTAL')
    return operation


SCRIPT = r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys,urllib.request
def checked(pin):
 raw=pathlib.Path(pin['path']).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'PIN_CHANGED';return json.loads(raw)
def run(args,env=None):
 r=subprocess.run(args,capture_output=True,timeout=40,env=env);assert r.returncode==0,'READ_COMMAND_FAILED';return r.stdout
for item,generation in zip(INSTALL['controllers'],INSTALL['controllerGenerations']):
 control=checked(item['controlConfigurationPin']);assert control==item['control']
 assert int(run(['systemctl','show',item['service'],'-p','MainPID','--value']))==item['pid']
 assert str(pathlib.Path(item['engine'])/'control_entry.py').encode() in (pathlib.Path('/proc')/str(item['pid'])/'cmdline').read_bytes()
 version=json.loads((pathlib.Path(item['engine'])/'package.json').read_bytes())
 assert version['packageSha256']==generation['fileManifestSha256']
 assert len(version['files'])==generation['fileCount']
 assert all(hashlib.sha256((pathlib.Path(item['engine'])/name).read_bytes()).hexdigest()==sha for name,sha in version['files'].items())
source_control=INSTALL['controllers'][0]['control'];target_control=INSTALL['controllers'][1]['control']
owner=checked(source_control['sourceConfigurations'][SOURCE]);capture=json.loads(pathlib.Path(owner['sources'][SOURCE]['configurationPath']).read_bytes())
target_owner=checked(target_control['restoreConfigurations'][SOURCE][TARGET]);target=target_owner['targets'][TARGET]
assert source_control['sourceEpochPolicies'][SOURCE]==target_owner['targetBackupEpochPolicies'][TARGET]==INSTALL['policy']
assert capture['source']['sourceIdentity']==INSTALL['policy']['sourceIdentity'] and capture['source']['databaseUuid']==INSTALL['policy']['databaseUuid']
sys.path.insert(0,str(pathlib.Path(INSTALL['controllers'][0]['engine'])/'common'))
from recovery_backup_epoch import read_current
epoch=read_current(INSTALL['policy']);assert epoch['state']=='READY'
rows=json.loads(run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect',*[s['id'] for s in target['services']]]))
assert len(rows)==5 and all(r['State']['Running'] and not r['State']['Paused'] and not r['State']['Restarting'] for r in rows),'SOURCE_SERVICES_NOT_RUNNING'
byid={r['Id']:r for r in rows}
assert all(byid[s['id']]['Image']==s['imageId'] for s in target['services']),'SERVICE_IMAGE_CHANGED'
for row in rows:
 if 'Health' in row['State']:assert row['State']['Health']['Status']=='healthy'
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESTORE_RESERVATION'
active=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:cmd=(p/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if (str(pathlib.Path(source_control['workingDirectory'])).encode() in cmd or str(pathlib.Path(target_control['workingDirectory'])).encode() in cmd) and b'control_entry.py' not in cmd:active.append(int(p.name))
if PHASE!='verify':assert not active,'SOURCE_WORKER_ACTIVE'
lock=os.open(INSTALL['policy']['sourceLockPath'],os.O_RDWR|os.O_NOFOLLOW)
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);idle=True;fcntl.flock(lock,fcntl.LOCK_UN)
except BlockingIOError:idle=False
finally:os.close(lock)
if PHASE!='verify':assert idle,'SOURCE_LOCK_BUSY'
health=json.loads(run([target_control['pythonPin']['path'],'-B','-c',HEALTH_PROBE,json.dumps(INSTALL['controllers'][1]['controlConfigurationPin']),SOURCE,TARGET],env=dict(os.environ,**target_control['environment'])))
assert all(r['result']['ready'] and r['result']['httpStatus']==200 for r in health.values())
paths=[owner['repositoryRoot'],owner['operationRoot'],owner['sources'][SOURCE]['stagingRoot'],capture['archiveRoot']]
capacity={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in paths}
# The observed old full/increment were below 31 GiB; reserve >6x that peak here.
assert all(n>=200*1024**3 for n in capacity.values()),'ACCEPTANCE_CAPACITY_BELOW_200_GIB'
headers=json.loads(pathlib.Path(source_control['authCredentialRef']['path']).read_bytes())['headers']
url='http://127.0.0.1:'+str(source_control['listenPort'])+'/incremental-plan?sourceConfigRef='+SOURCE
with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urllib.request.Request(url,headers=headers),timeout=40) as response:
 assert response.status==200;plan=json.load(response)
if PHASE!='verify':assert plan['state']==('BASELINE_REQUIRED' if KIND=='FULL' else 'READY'),'PLAN_NOT_EXECUTABLE'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceIdentity=INSTALL['policy']['sourceIdentity'],databaseUuid=INSTALL['policy']['databaseUuid'],epochId=epoch['epochId'],sourceIdle=idle,workerCount=len(active),health=health,capacity=capacity,plan=plan,businessMutationDispatched=False,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)))
'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', required=True, choices=['FULL', 'I1', 'I2'])
    parser.add_argument('--phase', required=True, choices=['preview', 'submit', 'verify'])
    parser.add_argument('--observation', required=True)
    args = parser.parse_args()
    assert args.observation.replace('-', '').isalnum()
    destination = TASK / ('automatic-' + args.kind.lower() + '-' + args.phase + '-' + args.observation + '-preflight.json')
    assert not destination.exists()
    deployment=load_stage_deployment(TASK,PRIVATE,args.kind)
    install=deployment['privateSourceInstallation'];commit=deployment['sourceCommit']
    local=deployment['spugInstallation']
    git_evidence=verify_stage_deployment_inputs(TASK.parents[2],commit,deployment['spugCommit'],local['files'])
    for name, pin in local['files'].items():
        assert hashlib.sha256((Path(local['runtime']) / name).read_bytes()).hexdigest() == pin['installedSha256']
    from install_automatic_57 import SCRIPT as INSTALL_SCRIPT
    tree = ast.parse(INSTALL_SCRIPT)
    probe = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'health_probe' for t in n.targets))
    values = dict(INSTALL=install, SOURCE=SOURCE, TARGET='intruoyi-main-57-safe-restore-20261105-v2',
                  KIND=args.kind, PHASE=args.phase, HEALTH_PROBE=probe)
    submission = None
    if args.phase == 'verify':
        submission = json.loads((TASK / ('automatic-' + args.kind.lower() + '-ui-submission.json')).read_text(encoding='utf-8'))
        operation_id = verify_submission_identity(submission, args.kind, commit, deployment)
    actual = remote('172.30.30.57', '\n'.join(k + '=' + repr(v) for k, v in values.items()) + '\n' + SCRIPT, 120)
    actual['sourceConfigRef'] = SOURCE
    actual['deploymentSelectionPin']=deployment['selectionPin']
    actual['sourceCommit']=commit;actual['spugCommit']=deployment['spugCommit']
    if submission:
        actual['operationId'] = operation_id
    evidence = destination.with_name(destination.stem + '-evidence.json')
    write(evidence, actual)
    if args.phase == 'verify':
        plan = submission['plan']
    else:
        plan = actual['plan']
    gate = dict(schemaVersion='AutomaticIncrementalUiPreflight/v2', status='PASS', experiencePreflight='PASS',
                kind=args.kind, phase=args.phase, origin='http://127.0.0.1:18080', server='172.30.30.57', mode='safe',
                applicationId=SOURCE, sourceConfigRef=SOURCE, implementationCommit=commit, installationCommit=commit,
                buildCommit=commit, spugCommit=deployment['spugCommit'],deploymentSelectionPin=deployment['selectionPin'],
                gitDeploymentInputs=git_evidence,
                observedAt=now(), expectedUserLabel='管理员', sourceIdentityVerified=True,
                installationVerified=True, sourceServicesHealthy=True, archiveReady=True, capacityReady=True,
                noConcurrentMaintenance=True, sourceIdleVerified=actual['sourceIdle'],
                expectedPlan={k: plan[k] for k in ('state', 'parentChainRef', 'baseFullRef', 'planDigest')})
    if submission:
        gate['operationId'] = operation_id
    write(destination, gate)
    print(json.dumps(dict(status='PASS', preflight=str(destination), plan=gate['expectedPlan'], observedAt=gate['observedAt'])))
