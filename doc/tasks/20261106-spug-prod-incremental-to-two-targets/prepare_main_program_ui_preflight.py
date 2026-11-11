"""Fresh MAIN/v4 gates for a named real UI acceptance cycle; no dispatch."""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import subprocess

from common import TASK, PRIVATE, SOURCE, now, remote
from main_program_installation_selection import local_name
from main_program_current_installation import load_current_installation, BoundDocuments
from prepare_automatic_ui_preflight import verify_stage_deployment_inputs, verify_deployment_inputs


def need(value, code):
    if not value:
        raise ValueError(code)


def validate_runtime(value, phase):
    need(value['servicesRunning'] is True and value['serviceCount'] == 5 and
         value['mainSourceMatchesTarget'] is True, 'MAIN_SOURCE_NOT_PROVEN')
    need(all(value[key] for key in ('sourceIdentity','databaseUuid','epochId')), 'SOURCE_IDENTITY_REQUIRED')
    need(set(value['health']) == {'minio','backend','frontend'} and
         all(row['ready'] is True and row['httpStatus'] == 200 for row in value['health'].values()),
         'MAIN_SERVICES_NOT_HEALTHY')
    need(value['activeReservation'] is False, 'ACTIVE_RESTORE_RESERVATION')
    if phase != 'verify':
        need(value['sourceIdle'] is True and value['workerPids'] == [], 'SOURCE_NOT_IDLE')
    need(set(value['backupCapacity']) == {'repository','operations','staging','archive'} and
         all(type(n) is int and n >= 200*1024**3 for n in value['backupCapacity'].values()),
         'BACKUP_CAPACITY_BELOW_200_GIB')


def plan_for_gate(value, kind, phase, original=None):
    plan = original if phase == 'verify' else value['plan']
    need(type(plan) is dict, 'ORIGINAL_PLAN_REQUIRED')
    result = {key:plan[key] for key in ('state','parentChainRef','baseFullRef','planDigest')}
    need(result['state'] == ('BASELINE_REQUIRED' if kind == 'FULL' else 'READY'), 'PLAN_KIND_MISMATCH')
    need(re.fullmatch('[a-f0-9]{64}', result['planDigest'] or '') is not None, 'PLAN_DIGEST_INVALID')
    need(all(type(result[key]) is str and result[key] for key in ('parentChainRef','baseFullRef'))
         if kind != 'FULL' else result['parentChainRef'] is result['baseFullRef'] is None,
         'PLAN_CHAIN_INVALID')
    return result


def write_new(path, value):
    raw=json.dumps(value,ensure_ascii=False,indent=2).encode('utf-8')
    with path.open('xb') as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    need(path.read_bytes() == raw, 'EVIDENCE_WRITE_CHANGED')
    return dict(file=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def checked(reference):
    path=Path(reference.get('path',TASK/reference.get('file','')))
    raw=path.read_bytes()
    need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'PIN_CHANGED')
    return json.loads(raw)


def pinned_context(verified, path):
    matches=[p for p in verified['inputPins'] if Path(p['path']) == Path(path)]
    need(len(matches)==1,'FORMAL_INPUT_NOT_BOUND')
    return checked(matches[0])


def _deployment_directory(value):
    need(type(value) is str and value and '\x00' not in value and
         not any(part in ('.', '..') for part in value.replace('\\', '/').split('/')),
         'MAIN_DEPLOYMENT_ROOT_INVALID')
    path = Path(value)
    need(path.is_absolute() and path.is_dir() and not path.is_symlink() and
         path.resolve(strict=True) == path, 'MAIN_DEPLOYMENT_ROOT_INVALID')
    return path


def _deployment_root_state(path, commit):
    def git(*args):
        result = subprocess.run(['git', '-C', str(path), *args], capture_output=True, timeout=30,
                                env=dict(os.environ, GIT_OPTIONAL_LOCKS='0'))
        need(result.returncode == 0, 'MAIN_DEPLOYMENT_ROOT_GIT_FAILED')
        return result.stdout.decode('utf-8').strip()
    need(_deployment_directory(str(path)) == path and
         Path(git('rev-parse', '--show-toplevel')) == path, 'MAIN_DEPLOYMENT_ROOT_NOT_GIT_ROOT')
    head = git('rev-parse', 'HEAD')
    need(head == commit, 'MAIN_DEPLOYMENT_ROOT_HEAD_CHANGED')
    need(not git('status', '--porcelain=v1', '--untracked-files=all'), 'MAIN_DEPLOYMENT_ROOT_DIRTY')
    info = path.stat()
    return dict(path=path.as_posix(), headCommit=head, identity=(info.st_dev, info.st_ino))


def installation_context(verified, *, source_activation=False):
    if source_activation:
        need(verified.get('status') == 'ACTIVATED' and
             verified.get('installationVerified') is True and verified.get('runtimeVerified') is False and
             verified.get('selection', {}).get('schemaVersion') == 'TaskMainProgramSourceControlSelection/v2',
             'SOURCE_ACTIVATION_PROTOCOL_REQUIRED')
        base = verified['baseInstallation']
        rows = verified['effectiveControllersByHost']['57']
        need(len(rows) == 2 and rows[0]['role'] == 'source' and rows[1]['role'] == 'target' and
             rows[1] == base['generation']['controllersByHost']['57'][1], 'SOURCE_ACTIVATION_ROLES_CHANGED')
        row = rows[0]
        build_pin = row['buildPin']
        build = BoundDocuments(TASK, verified['inputPins']).read(build_pin)
        need(build['targetCommit'] == row['sourceCommit'] and build['status'] == 'PASS' and
             all(build[key] == row[key] for key in ('fileCount', 'fileManifestSha256', 'packageSha256')),
             'SOURCE_ACTIVATION_BUILD_CHANGED')
        return dict(base=base, rows=rows, sourceCommit=row['sourceCommit'], buildPin=build_pin, build=build)
    need('baseInstallation' not in verified and verified.get('status') != 'ACTIVATED',
         'SOURCE_ACTIVATION_EXPLICIT_OPTION_REQUIRED')
    return dict(base=verified, rows=verified['generation'].get('controllersByHost', {}).get('57'),
        sourceCommit=verified['selection']['sourceCommit'],
        buildPin=verified['generation']['generation']['buildPin'], build=verified['generation']['build'])


def verify_main_deployment_inputs(verified, default_root, *, source_deployment_root=None,
                                  spug_deployment_root=None, source_activation=False):
    """Explicit registered component roots; the legacy shared-root gate is unchanged."""
    need((source_deployment_root is None) == (spug_deployment_root is None),
         'MAIN_DEPLOYMENT_ROOT_PAIR_REQUIRED')
    context = installation_context(verified, source_activation=source_activation)
    source_commit = context['sourceCommit']
    resource = context['base']['spugRuntime']['resourceBuild']
    files = [name.removeprefix('ops/spug/') for name in resource['files']]
    if source_deployment_root is None:
        return verify_stage_deployment_inputs(default_root, source_commit, resource['sourceCommit'], files)
    reader = BoundDocuments(TASK, verified['inputPins'])
    source_pin = context['buildPin']
    resource_pin = context['base']['spugRuntime']['resourceBuildPin']
    build = reader.read(source_pin); actual_resource = reader.read(resource_pin)
    need(build == context['build'] and actual_resource == resource,
         'MAIN_DEPLOYMENT_BUILD_CHANGED')
    need(build.get('status') == 'PASS' and build.get('targetCommit') == source_commit and
         build.get('allFilesShaAndCompileVerified') is True and
         resource.get('schemaVersion') == 'MainProgramSpugResourceBuild/v2' and resource.get('status') == 'PASS' and
         type(resource.get('fileCount')) is int and resource['fileCount'] == len(resource['files']) and
         resource['fileCount'] > 0 and all(name.startswith('ops/spug/') for name in resource['files']),
         'MAIN_DEPLOYMENT_BUILD_INVALID')
    specs = {'source': (source_deployment_root, build, source_pin, source_commit),
             'spug': (spug_deployment_root, resource, resource_pin, resource['sourceCommit'])}
    roots = {}; before = {}; bindings = {}; result = {}
    for component, (argument, original, reference, commit) in specs.items():
        root = _deployment_directory(argument)
        need(root == _deployment_directory(original['worktree']), 'MAIN_DEPLOYMENT_ROOT_NOT_REGISTERED')
        roots[component] = root; before[component] = _deployment_root_state(root, commit)
        bindings[component] = dict(schemaVersion='MainProgramDeploymentRoot/v1', mode='PINNED_BUILD_WORKTREE',
            path=root.as_posix(), buildPin=reference, targetCommit=commit, headCommit=commit,
            registeredWorktreeMatched=True, clean=True)
    for component, (_, _, _, commit) in specs.items():
        result[component] = verify_deployment_inputs(roots[component], commit, files, component=component)
    for component, (_, _, _, commit) in specs.items():
        need(_deployment_root_state(roots[component], commit) == before[component],
             'MAIN_DEPLOYMENT_ROOT_CHANGED_DURING_CHECK')
    need(reader.read(source_pin) == build and reader.read(resource_pin) == resource, 'MAIN_DEPLOYMENT_BUILD_CHANGED')
    reader.finish()
    return dict(result, deploymentRootBindings=bindings)


def validate_spug_current_entry(expected, candidates):
    need(type(candidates) is list and len(candidates) == 1, 'SPUG_CURRENT_PROCESS_NOT_UNIQUE')
    row = candidates[0]; original = expected['entryIdentity']
    need(type(row) is dict and set(row) == {'pid', 'parentPid', 'startTicks', 'argv', 'cwd',
         'executable', 'environmentSha256'} and type(row['pid']) is int and row['pid'] > 0 and
         type(row['parentPid']) is int and row['parentPid'] == original['parentPid'] and
         type(row['startTicks']) is str and row['startTicks'].isdecimal() and
         row['argv'] == original['argv'] and row['cwd'] == original['cwd'] and
         row['executable'] == original['executable'] and
         row['environmentSha256'] == expected['entryEnvironmentSha256'], 'SPUG_CURRENT_PROCESS_CHANGED')
    return row


def spug_observation(verified, selection):
    guard=verified['spugRuntime']['guard']
    build=verified['spugRuntime']['resourceBuild']
    script='EXPECTED='+repr(guard)+'\n'+inspect.getsource(validate_spug_current_entry)+'\n'+SPUG_SCRIPT
    result=subprocess.run([str(Path(os.environ['LOCALAPPDATA'])/'Programs/DockerDesktop/resources/bin/docker.exe'),
        'exec','-i','f615a60c76f46e4f6ae20ea6298f737fb9786684ce941fcc15763654461265bf',
        'python3','-B','-S','-'],input=script.encode('utf-8'),capture_output=True,timeout=50)
    if result.returncode:
        path=PRIVATE/('main-ui-spug-preflight-error-'+hashlib.sha256(result.stderr).hexdigest()[:16]+'.private.log')
        if not path.exists():path.write_bytes(result.stdout+result.stderr)
        raise RuntimeError('SPUG_CURRENT_RUNTIME_CHECK_FAILED')
    return json.loads(result.stdout),build


SPUG_SCRIPT = r'''
import hashlib,json,pathlib
def need(ok,code):
 if not ok:raise RuntimeError(code)
for pin in EXPECTED['filePins']+EXPECTED['configurationPins']:
 raw=pathlib.Path(pin['path']).read_bytes();need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'SPUG_FILE_CHANGED')
def observe(p):
 stat=(p/'stat').read_text();tail=stat[stat.rfind(')')+2:].split()
 return dict(pid=int(p.name),parentPid=int(tail[1]),startTicks=tail[19],argv=(p/'cmdline').read_bytes().decode().rstrip('\0').split('\0'),cwd=str((p/'cwd').resolve()),executable=str((p/'exe').resolve()),environmentSha256=hashlib.sha256((p/'environ').read_bytes()).hexdigest())
candidates=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:
  if (p/'cmdline').read_bytes().decode().rstrip('\0').split('\0')!=EXPECTED['entryIdentity']['argv']:continue
  candidates.append(observe(p))
 except (FileNotFoundError,ProcessLookupError):continue
identity=validate_spug_current_entry(EXPECTED,candidates)
for pin in EXPECTED['filePins']+EXPECTED['configurationPins']:
 raw=pathlib.Path(pin['path']).read_bytes();need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'SPUG_FILE_CHANGED')
need(observe(pathlib.Path('/proc')/str(identity['pid']))==identity,'SPUG_PROCESS_CHANGED_DURING_CHECK')
print(json.dumps(dict(status='PASS',entryPid=identity['pid'],entryIdentity=identity,previousEntryPid=EXPECTED['entryIdentity']['pid'],processRestarted=identity['pid']!=EXPECTED['entryIdentity']['pid'] or identity['startTicks']!=EXPECTED['entryIdentity']['startTicks'],fileCount=len(EXPECTED['filePins']),configurationCount=len(EXPECTED['configurationPins']))))
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycle',required=True)
    parser.add_argument('--kind',required=True,choices=['FULL','I1','I2'])
    parser.add_argument('--phase',required=True,choices=['preview','submit','verify'])
    parser.add_argument('--observation',required=True)
    parser.add_argument('--selection',required=True)
    parser.add_argument('--historical-source-custody')
    parser.add_argument('--source-deployment-root')
    parser.add_argument('--spug-deployment-root')
    parser.add_argument('--source-activation',action='store_true')
    args=parser.parse_args()
    need(re.fullmatch('[a-z0-9][a-z0-9-]{0,47}',args.cycle or '') and
         re.fullmatch('[a-z0-9][a-z0-9-]{0,47}',args.observation or ''),'CYCLE_OR_OBSERVATION_INVALID')
    local_name(args.selection)
    prefix='automatic-'+args.cycle+'-'+args.kind.lower()
    stem=prefix+'-'+args.phase+'-'+args.observation
    gate_path=TASK/(stem+'-preflight.json')
    need(not gate_path.exists(),'OBSERVATION_ALREADY_EXISTS')
    source_args={}
    if args.historical_source_custody:
        from main_program_spug_publication import file_pin
        source_args['historical_source_custody_pin']=file_pin(Path(args.historical_source_custody))
    if args.source_activation:
        from main_program_source_control_activated import load_activated_installation
        need(args.source_deployment_root is not None and args.spug_deployment_root is not None,
             'SOURCE_ACTIVATION_DEPLOYMENT_ROOTS_REQUIRED')
        verified=load_activated_installation(TASK,PRIVATE,selection_file=args.selection,**source_args)
    else:
        verified=load_current_installation(TASK,PRIVATE,selection_file=args.selection,**source_args)
    context=installation_context(verified,source_activation=args.source_activation)
    base=context['base'];selection=base['selection'];selection_pin=verified['selectionPin'];bundle=base['generation']
    root_args=dict(source_deployment_root=args.source_deployment_root,spug_deployment_root=args.spug_deployment_root)
    if args.source_activation:root_args['source_activation']=True
    git=verify_main_deployment_inputs(verified,TASK.parents[2],**root_args)
    spug,build=spug_observation(base,selection)
    rows=context['rows']
    values=dict(SUFFIX='57',SOURCE=SOURCE,TARGET=bundle['targets']['57'],ROWS=rows)
    actual=remote('172.30.30.57','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+SCRIPT,180)
    write_new(PRIVATE/(stem+'-native.private.json'),actual)
    validate_runtime(actual,args.phase)
    original=None;operation=None
    if args.phase=='verify':
        receipt=json.loads((TASK/(prefix+'-ui-submission.json')).read_text(encoding='utf-8'))
        need(receipt['schemaVersion']=='AutomaticIncrementalUiSubmission/v3' and receipt['cycle']==args.cycle and
             receipt['kind']==args.kind and receipt['deploymentSelectionPin']==selection_pin,
             'ORIGINAL_RECEIPT_DEPLOYMENT_CHANGED')
        original=receipt['plan'];operation=receipt['request']['operationId']
    expected=plan_for_gate(actual,args.kind,args.phase,original)
    need(verify_main_deployment_inputs(verified,TASK.parents[2],**root_args)==git,'MAIN_DEPLOYMENT_INPUTS_CHANGED_DURING_OBSERVATION')
    BoundDocuments(TASK,verified['inputPins']).finish()
    evidence=dict(schemaVersion='MainProgramAutomaticIncrementalUiRuntime/v1',status='PASS',
         observedAt=now(),source=actual,spug=spug,gitDeploymentInputs=git,
         deploymentSelectionPin=selection_pin,backupDispatched=False,restoreDispatched=False)
    runtime_pin=write_new(TASK/(stem+'-runtime.json'),evidence)
    baseline=dict(schemaVersion='MainProgramAutomaticIncrementalUiBaseline/v1',status='PASS',cycle=args.cycle,
         observedAt=now(),applicationId=SOURCE,sourceConfigRef=SOURCE,deploymentSelectionPin=selection_pin,
         expectedPlan=expected,operationId=operation)
    baseline_pin=write_new(TASK/(stem+'-baseline.json'),baseline)
    gate=dict(schemaVersion='MainProgramAutomaticIncrementalUiPreflight/v2' if args.source_deployment_root is not None else 'MainProgramAutomaticIncrementalUiPreflight/v1',status='PASS',experiencePreflight='PASS',
         cycle=args.cycle,kind=args.kind,phase=args.phase,origin='http://127.0.0.1:18080',server='172.30.30.57',mode='safe',
         applicationId=SOURCE,sourceConfigRef=SOURCE,implementationCommit=context['sourceCommit'],
         installationCommit=context['sourceCommit'],buildCommit=context['sourceCommit'],spugCommit=build['sourceCommit'],
         deploymentSelectionPin=selection_pin,controlGenerationPin=selection['controlGenerationPin'],
         spugInstallationPin=selection['spugInstallationPin'],sourceCaptureConfigurationPin=actual['captureConfigurationPin'],
         sourceOwnerConfigurationPin=rows[0]['ownerConfigurationPin'],mainDeploymentVerified=True,
         observedAt=now(),expectedUserLabel='管理员',sourceIdentityVerified=True,installationVerified=True,
         sourceServicesHealthy=True,archiveReady=True,capacityReady=True,noConcurrentMaintenance=True,
         sourceIdleVerified=actual['sourceIdle'],expectedPlan=expected,baselineEvidencePin=baseline_pin,
         runtimeEvidencePin=runtime_pin,gitDeploymentInputs=git)
    if args.source_activation:
        gate.update(schemaVersion='MainProgramAutomaticIncrementalUiPreflight/v3',
            baseSelectionPin=base['selectionPin'],controllerBuildBindings=verified['controllerBuildBindings'])
    if operation:gate['operationId']=operation
    write_new(gate_path,gate)
    print(json.dumps(dict(status='PASS',preflight=str(gate_path),expectedPlan=expected,observedAt=gate['observedAt'])))


SCRIPT = r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys,urllib.request
from types import SimpleNamespace
def need(ok,code):
 if not ok:raise RuntimeError(code)
def pincheck(pin):
 raw=pathlib.Path(pin['path']).read_bytes();need(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'PIN_CHANGED');return json.loads(raw)
def run(argv):
 p=subprocess.run(argv,capture_output=True,timeout=40);need(p.returncode==0,'READ_FAILED');return p.stdout
out=dict(host='172.30.30.'+SUFFIX,observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllers=[],businessMutationDispatched=False,sourceConfigRef=SOURCE)
controls=[];owners=[]
for row in ROWS:
 c=pincheck(row['controlConfigurationPin']);o=pincheck(row['ownerConfigurationPin']);controls.append(c);owners.append(o)
 pid=int(run(['systemctl','show',row['service'],'-p','MainPID']).decode().strip().split('=',1)[1]);need(pid==row['pid'],'CONTROL_PID_CHANGED')
 argv=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
 need(argv[:5]==[c['pythonPin']['path'],'-B',str(pathlib.Path(row['engine'])/'control_entry.py'),'serve','--config-pin'] and len(argv)==6 and json.loads(argv[5])==row['controlConfigurationPin'],'CONTROL_ARGV_CHANGED')
 v=json.loads((pathlib.Path(row['engine'])/'package.json').read_bytes());need(v['packageSha256']==row['fileManifestSha256'] and len(v['files'])==row['fileCount'],'PACKAGE_CHANGED')
 need(all(hashlib.sha256((pathlib.Path(row['engine'])/n).read_bytes()).hexdigest()==sha for n,sha in v['files'].items()),'ENGINE_FILE_CHANGED')
 out['controllers'].append(dict(service=row['service'],pid=pid,fileCount=len(v['files']),filesVerified=True))
c=controls[-1];o=owners[-1];need(c['restoreConfigurations'][SOURCE][TARGET]==ROWS[-1]['ownerConfigurationPin'],'TARGET_BINDING_CHANGED');t=o['targets'][TARGET]
rows=json.loads(run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect',*[s['id'] for s in t['services']]]));byid={r['Id']:r for r in rows}
need(len(rows)==5 and all(r['State']['Running'] and not r['State']['Paused'] and not r['State']['Restarting'] for r in rows),'MAIN_SERVICES_NOT_RUNNING')
need(all(byid[s['id']]['Image']==s['imageId'] for s in t['services']),'MAIN_IMAGE_CHANGED')
for r in rows:
 if 'Health' in r['State']:need(r['State']['Health']['Status']=='healthy','DOCKER_HEALTH_FAILED')
sys.path[:0]=c['environment']['PYTHONPATH'].split(os.pathsep)
from recovery_main_health import preflight,endpoint,probe
n=SimpleNamespace(config=t,config_services={s['role']:s for s in t['services']},inspect=lambda i:byid[i],frontend_readiness=o.get('frontendReadiness',{}).get(TARGET))
preflight(n);health={role:probe(endpoint(n,role),role,12) for role in ('minio','backend','frontend')};need(all(h['ready'] and h['httpStatus']==200 for h in health.values()),'MAIN_SEMANTIC_HEALTH_FAILED')
out.update(health=health,targetConfigRef=TARGET,servicesRunning=True,serviceCount=len(rows),activeReservation=pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),fstabSha256=hashlib.sha256(pathlib.Path('/etc/fstab').read_bytes()).hexdigest())
paths=[c['workingDirectory'],'/opt/intruoyi/runtime'];out['capacity']={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in paths}
if SUFFIX=='57':
 c=controls[0];o=owners[0];need(c['sourceConfigurations'][SOURCE]==ROWS[0]['ownerConfigurationPin'],'SOURCE_BINDING_CHANGED')
 policy=c['sourceEpochPolicies'][SOURCE]
 from recovery_backup_epoch import read_current
 epoch=read_current(policy);need(epoch['state']=='READY','EPOCH_NOT_READY')
 cap=json.loads(pathlib.Path(o['sources'][SOURCE]['configurationPath']).read_bytes());need(cap['source']['sourceIdentity']==policy['sourceIdentity'] and cap['source']['databaseUuid']==policy['databaseUuid'],'SOURCE_IDENTITY_CHANGED')
 need(o['schemaVersion']=='RepositoryMinimumConfiguration/v1','SOURCE_OWNER_CHANGED')
 main_services={r['role']:r for r in t['services']}
 out['mainSourceMatchesTarget']=(cap['source']['mysqlContainerId']==main_services['mysql']['id'] and cap['source']['minioContainerId']==main_services['minio']['id'] and set(cap['source']['writerContainerIds'])=={main_services[role]['id'] for role in ('backend','frontend')})
 need(out['mainSourceMatchesTarget'],'CAPTURE_NOT_MAIN_PROGRAM')
 capture_path=pathlib.Path(o['sources'][SOURCE]['configurationPath']);capture_raw=capture_path.read_bytes()
 out['captureConfigurationPin']=dict(path=str(capture_path),bytes=len(capture_raw),sha256=hashlib.sha256(capture_raw).hexdigest())
 paths=[o['repositoryRoot'],o['operationRoot'],o['sources'][SOURCE]['stagingRoot'],cap['archiveRoot']]
 out['backupCapacity']={role:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for role,p in zip(('repository','operations','staging','archive'),paths)};out['backupCapacityPaths']=dict(zip(('repository','operations','staging','archive'),paths));out['capacity'].update({p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in paths})
 fd=os.open(policy['sourceLockPath'],os.O_RDWR|os.O_NOFOLLOW)
 try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);idle=True;fcntl.flock(fd,fcntl.LOCK_UN)
 except BlockingIOError:idle=False
 finally:os.close(fd)
 active=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdecimal():continue
  try:cmd=(p/'cmdline').read_bytes()
  except (FileNotFoundError,ProcessLookupError):continue
  if any(x['workingDirectory'].encode() in cmd for x in controls) and b'control_entry.py' not in cmd:active.append(int(p.name))
 headers=json.loads(pathlib.Path(c['authCredentialRef']['path']).read_bytes())['headers']
 req=urllib.request.Request('http://127.0.0.1:'+str(c['listenPort'])+'/incremental-plan?sourceConfigRef='+SOURCE,headers=headers)
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=40) as response:
  need(response.status==200,'PLAN_HTTP_FAILED');plan=json.load(response)
 out.update(sourceIdentity=policy['sourceIdentity'],databaseUuid=policy['databaseUuid'],epochId=epoch['epochId'],sourceIdle=idle,workerPids=active,plan=plan,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True,captureConfigurationSha256=hashlib.sha256(pathlib.Path(o['sources'][SOURCE]['configurationPath']).read_bytes()).hexdigest())
else:out.update(controlApiQueriesPerformed=False,queryAuditWritesMayOccur=False)
out['finishedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat();print(json.dumps(out))
'''


if __name__=='__main__':main()
