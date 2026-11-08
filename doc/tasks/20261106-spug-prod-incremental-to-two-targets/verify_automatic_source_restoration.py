"""Independently inspect a completed automatic backup's source, without mutations.

The original point367 verifier stays unchanged. Its reviewed SQL/exporter and
failed-original checks are reused with the actual new owner/capture/engine pins.
"""
import argparse
import ast
from datetime import datetime
import hashlib
import inspect
import json
from pathlib import Path, PurePosixPath
import re

from common import TASK, PRIVATE, SOURCE, remote
from prepare_automatic_ui_preflight import verify_submission_identity
from verify_automatic_backup_chain import prepare as prepare_package
from automatic_stage_deployment import load_stage_deployment

INSTALLED_COMMIT = '0d445782dc06995b3c84b1b45146ea4b75483f92'
TARGET = 'intruoyi-main-57-safe-restore-20261105-v2'


def need(condition, code):
    if not condition:
        raise ValueError(code)


def validate_evidence(kind, installation, submission, audit, terminal, deployment=None):
    need(kind in ('FULL', 'I1', 'I2'), 'SOURCE_KIND_INVALID')
    if deployment is None:
        need(kind == 'FULL', 'SOURCE_DEPLOYMENT_REQUIRED')
        need(installation['status'] == 'PASS' and installation['sourceCommit'] == INSTALLED_COMMIT,
             'SOURCE_INSTALLATION_CHANGED')
    else:
        need(installation == deployment['sourceInstallation'] and installation['status'] == 'PASS',
             'SOURCE_STAGE_INSTALLATION_CHANGED')
        need(audit['deploymentSelectionPin'] == deployment['selectionPin'] and
             audit['sourceCommit'] == deployment['sourceCommit'] and audit['spugCommit'] == deployment['spugCommit'] and
             audit['sourceInstallationPin'] == deployment['selection']['sourceInstallationPin'],
             'SOURCE_AUDIT_DEPLOYMENT_CHANGED')
    try:
        operation = verify_submission_identity(submission, kind, installation['sourceCommit'], deployment)
    except (AssertionError, KeyError):
        raise ValueError('SOURCE_SUBMISSION_CHANGED') from None
    need(audit['schemaVersion'] == 'AutomaticBackupChainAudit/v1' and audit['status'] == 'PASS' and
         audit['state'] == 'SUCCEEDED' and audit['actualExitCode'] == 0 and audit['sourceRestored'] is True and
         audit['operationId'] == operation and audit['sourceConfigRef'] == SOURCE and
         audit['pointType'] == submission['request']['action'], 'SOURCE_SUCCESSFUL_AUDIT_REQUIRED')
    need(audit['sourceEpoch']['state'] == 'READY', 'SOURCE_READY_EPOCH_REQUIRED')
    package = audit['package']
    need(package['engine'] == installation['controllers'][0]['engine'] and package['variant'] == 'standard' and
         package['fileCount'] == installation['fileCount'] == 130 and
         package['fileManifestSha256'] == installation['fileManifestSha256'], 'SOURCE_AUDITED_PACKAGE_CHANGED')
    need(terminal['schemaVersion'] == 'AutomaticIncrementalUiTerminal/v1' and terminal['kind'] == kind and
         terminal['applicationId'] == SOURCE and terminal['operationState'] == 'SUCCEEDED' and
         terminal['request'] == submission['request'], 'SOURCE_SUCCESSFUL_TERMINAL_REQUIRED')
    need(datetime.fromisoformat(terminal['observedAt'].replace('Z', '+00:00')) >=
         datetime.fromisoformat(audit['finishedAt'].replace('Z', '+00:00')), 'SOURCE_TERMINAL_BEFORE_NATIVE_RESULT')
    result = dict(kind=kind, operationId=operation, sourceConfigRef=SOURCE,
                  failedOriginalFullShaRequired=kind in ('FULL', 'I2'))
    if deployment is not None:
        result.update(deploymentSelectionPin=deployment['selectionPin'], sourceCommit=deployment['sourceCommit'],
            spugCommit=deployment['spugCommit'], sourceInstallationPin=deployment['selection']['sourceInstallationPin'],
            controllerGenerations=deployment['controllerGenerations'])
    return result


def validate_failed_pins(pins):
    need(len(pins) == 10044, 'SOURCE_FAILED_ORIGINAL_COUNT_CHANGED')
    paths = set()
    for pin in pins:
        need(set(pin) == {'path', 'bytes', 'sha256'} and isinstance(pin['path'], str) and
             PurePosixPath(pin['path']).is_absolute() and '..' not in PurePosixPath(pin['path']).parts and
             type(pin['bytes']) is int and pin['bytes'] >= 0 and
             re.fullmatch('[0-9a-f]{64}', pin['sha256']), 'SOURCE_FAILED_ORIGINAL_PIN_INVALID')
        need(pin['path'] not in paths, 'SOURCE_FAILED_ORIGINAL_DUPLICATE')
        paths.add(pin['path'])
    return len(paths)


def write_exclusive(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
    with Path(path).open('xb') as stream:
        stream.write(raw)
    need(Path(path).read_bytes() == raw, 'SOURCE_REPORT_WRITE_CHANGED')


def read_pinned(path):
    raw = path.read_bytes()
    return json.loads(raw), dict(path=path.resolve().as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def source_runtime_paths(control, engine):
    paths = control['environment']['PYTHONPATH'].split(':')
    expected = [(PurePosixPath(engine) / name).as_posix() for name in ('control', 'common', 'formal')]
    need(len(paths) > 3 and paths[:3] == expected and len(paths) == len(set(paths)) and
         all(PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and
             PurePosixPath(path).as_posix() == path for path in paths) and
         control['environment']['PYTHONDONTWRITEBYTECODE'] == '1', 'SOURCE_RUNTIME_PATH_INVALID')
    return paths


def bind_source_runtime(reader, control, engine, expected_files):
    """Use the pinned source controller's complete imports in the read-only carrier."""
    import importlib
    import pathlib
    import sys
    paths = source_runtime_paths(control, engine)
    python_pin = reader.local_pin(pathlib.Path(sys.executable))
    need(python_pin == control['pythonPin'] and sys.dont_write_bytecode,
         'SOURCE_RUNTIME_PYTHON_CHANGED')
    for value in paths:
        path = pathlib.Path(value)
        need(path.resolve(strict=True) == path and path.is_dir() and not path.is_symlink(),
             'SOURCE_RUNTIME_PATH_ALIAS_REJECTED')
    sys.path[:0] = paths
    modules = {}
    for name in ('recovery_backup_epoch', 'recovery_main_target', 'recovery_engine'):
        loaded = importlib.import_module(name)
        origin = pathlib.Path(loaded.__file__)
        expected = pathlib.Path(engine) / 'common' / (name + '.py')
        module_pin = reader.local_pin(origin)
        need(origin == expected and module_pin['sha256'] == expected_files['common/' + name + '.py'],
             'SOURCE_RUNTIME_MODULE_CHANGED')
        modules[name] = module_pin
    dependencies = {}
    roots = [pathlib.Path(path) for path in paths[3:]]
    for name in ('jsonschema', 'attrs', 'referencing', 'jsonschema_specifications', 'rpds'):
        loaded = importlib.import_module(name)
        origin = pathlib.Path(loaded.__file__)
        need(any(origin.is_relative_to(root) for root in roots), 'SOURCE_RUNTIME_DEPENDENCY_ORIGIN_CHANGED')
        dependencies[name] = reader.local_pin(origin)
    # Record the actual imported closure, including native dependency extensions.
    # Entrypoint __init__.py alone does not identify the code used by jsonschema.
    for name, loaded in tuple(sys.modules.items()):
        filename = getattr(loaded, '__file__', None)
        if not filename:
            continue
        origin = pathlib.Path(filename)
        if origin.is_relative_to(engine):
            relative = origin.relative_to(engine).as_posix()
            module_pin = reader.local_pin(origin)
            need(relative in expected_files and module_pin['sha256'] == expected_files[relative],
                 'SOURCE_RUNTIME_MODULE_CHANGED')
            modules[name] = module_pin
        elif any(origin.is_relative_to(root) for root in roots):
            dependencies[name] = reader.local_pin(origin)
    return dict(pythonPin=python_pin, modulePaths=paths, modulePins=modules,
        dependencyPins=dependencies, bytecodeDisabled=True, configurationModulePathVerified=True)


SOURCE_RUNTIME = inspect.getsource(source_runtime_paths) + '\n' + inspect.getsource(bind_source_runtime)


SCRIPT = SOURCE_RUNTIME + r'''
import contextlib,datetime,fcntl,hashlib,io,json,os,pathlib,stat,subprocess,sys
reader=AuditReader(seconds=180)
install=SPEC['installation'];source=SPEC['sourceConfigRef'];operation=SPEC['operationId']
controllers=install['controllers']
need(len(controllers)==len(SPEC['controllerFiles'])==2,'SOURCE_CONTROLLER_GENERATIONS_REQUIRED')
for item,manifest in zip(controllers,SPEC['controllerFiles']):
 for name,sha in manifest.items():
  reference=reader.local_pin(pathlib.Path(item['engine'])/name)
  need(reference['sha256']==sha,'SOURCE_ENGINE_CHANGED')
control=reader.document(controllers[0]['controlConfigurationPin'])
target_control=reader.document(controllers[1]['controlConfigurationPin'])
owner_pin=control['sourceConfigurations'][source]
need(owner_pin==controllers[0]['ownerConfigurationPin'],'SOURCE_OWNER_CHANGED')
owner=reader.document(owner_pin)
inputs=reader.local(pathlib.Path(control['taskRoot'])/'request-configurations'/operation/'request-inputs.json')
need(inputs['request']==SPEC['request'] and inputs['ownerConfigurationPin']==owner_pin,'SOURCE_REQUEST_INPUTS_CHANGED')
capture_pin=inputs['captureConfigurationPin']
need(capture_pin['path']==owner['sources'][source]['configurationPath'],'SOURCE_CAPTURE_PATH_CHANGED')
capture=reader.document(capture_pin)
need(capture['sourceConfigRef']==source,'SOURCE_CAPTURE_IDENTITY_CHANGED')
need(reader.local(pathlib.Path(control['ledgerRoot'])/operation/'request.json')==SPEC['request'],'SOURCE_LEDGER_REQUEST_CHANGED')
result=reader.document(SPEC['audit']['resultPin'])
need(result['state']=='SUCCEEDED' and result['actualExitCode']==0 and
 result['data']['pointPin']==SPEC['audit']['pointPin'],'SOURCE_NATIVE_RESULT_CHANGED')
target_owner=reader.document(target_control['restoreConfigurations'][source][SPEC['targetConfigRef']])
target=target_owner['targets'][SPEC['targetConfigRef']]
policy=control['sourceEpochPolicies'][source]
need(policy==install['policy']==target_owner['targetBackupEpochPolicies'][SPEC['targetConfigRef']],'SOURCE_EPOCH_POLICY_CHANGED')
need(policy['sourceIdentity']==capture['source']['sourceIdentity'] and
 policy['databaseUuid']==capture['source']['databaseUuid'] and policy['sourceLockPath']==capture['sourceLockPath'],
 'SOURCE_EPOCH_PHYSICAL_BINDING_CHANGED')
engine=pathlib.Path(controllers[0]['engine'])
source_runtime=bind_source_runtime(reader,control,engine,SPEC['files'])
from recovery_backup_epoch import read_current,validate_policy
validate_policy(policy)
lock_path=pathlib.Path(policy['sourceLockPath'])
need(lock_path.resolve(strict=True)==lock_path and not lock_path.is_symlink(),'SOURCE_LOCK_ALIAS_REJECTED')
lock=os.open(lock_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 need(stat.S_ISREG(os.fstat(lock).st_mode) and os.fstat(lock).st_nlink==1,'SOURCE_LOCK_IDENTITY_INVALID')
 need((os.fstat(lock).st_dev,os.fstat(lock).st_ino)==(lock_path.stat().st_dev,lock_path.stat().st_ino),'SOURCE_LOCK_CHANGED')
 epoch=read_current(policy);need(epoch==SPEC['audit']['sourceEpoch'] and epoch['state']=='READY','SOURCE_EPOCH_CHANGED')
 def active_workers():
  active=[]
  for path in pathlib.Path('/proc').iterdir():
   if not path.name.isdecimal():continue
   try:cmd=(path/'cmdline').read_bytes()
   except (FileNotFoundError,ProcessLookupError):continue
   if any(c['workingDirectory'].encode() in cmd for c in (control,target_control)) and b'control_entry.py' not in cmd:active.append(int(path.name))
  return active
 need(not active_workers(),'SOURCE_WORKER_ACTIVE')
 def run(args,**kwargs):
  answer=subprocess.run(args,capture_output=True,timeout=40,**kwargs)
  need(answer.returncode==0,'SOURCE_READ_COMMAND_FAILED');return answer.stdout
 for item in controllers:
  need(int(run(['systemctl','show',item['service'],'-p','MainPID','--value']))==item['pid'],'SOURCE_CONTROLLER_CHANGED')
  need(str(pathlib.Path(item['engine'])/'control_entry.py').encode() in
   (pathlib.Path('/proc')/str(item['pid'])/'cmdline').read_bytes(),'SOURCE_CONTROLLER_PROGRAM_CHANGED')
 services=json.loads(run([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','inspect',*[s['id'] for s in target['services']]]))
 need(len(services)==len(target['services'])==5,'SOURCE_FIVE_SERVICES_REQUIRED')
 rows={s['Id']:s for s in services}
 need(capture['source']['mysqlContainerId']==next(s['id'] for s in target['services'] if s['role']=='mysql'),
  'SOURCE_MYSQL_CONTAINER_CHANGED')
 target_evidence=json.loads(run([target_control['pythonPin']['path'],'-B','-c',SPEC['targetRuntimeProbe']],
  env=target_control['environment'],input=json.dumps(dict(control=target_control,engine=controllers[1]['engine'],
   files=SPEC['controllerFiles'][1],services=services)).encode()))
 target_runtime=target_evidence['runtime']
 for registered in target['services']:
  row=rows[registered['id']];state=row['State']
  need(row['Image']==registered['imageId'] and state['Running'] and not state['Paused'] and not state['Restarting'],
   'SOURCE_SERVICE_NOT_HEALTHY')
  need(target_evidence['serviceConfigurationDigests'][registered['id']]==target['mainApplication']['serviceConfigurationDigests'][registered['role']],
   'SOURCE_SERVICE_CONFIGURATION_CHANGED')
  if 'Health' in state:need(state['Health']['Status']=='healthy','SOURCE_DOCKER_HEALTH_FAILED')
 redis=capture['source']['redisSnapshot']
 need(redis['containerId']==next(s['id'] for s in target['services'] if s['role']=='redis'),'SOURCE_REDIS_CONTAINER_CHANGED')
 prefix=[target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','exec']
 arguments=[target['redisClientPath'],'--raw','-n',str(redis['database']),'PING']
 if 'passwordPin' in redis:
  password=reader.raw(redis['passwordPin']).rstrip(b'\n')+b'\n'
  pong=run([*prefix,'-i',redis['containerId'],'sh','-ec',
   'IFS= read -r REDISCLI_AUTH; export REDISCLI_AUTH; exec "$@"','source-restoration-readonly',*arguments],input=password)
 else:
  pong=run([*prefix,redis['containerId'],*arguments])
 need(pong==b'PONG\n','SOURCE_REDIS_PING_FAILED')
 # Reuse the original reviewed read-only SQL/tool/immutable-file checks with the
 # new actual capture pin, not the original point367 installation selector.
 namespace=dict(ENGINE=str(engine),CAPTURE_PIN=capture_pin,EXPORTER=SPEC['exporter'],FAILED_PINS=SPEC['failedPins'])
 captured=io.StringIO()
 with contextlib.redirect_stdout(captured):exec(SPEC['originalSourceScript'],namespace)
 original=json.loads(captured.getvalue())
 need(original['status']=='PASS' and original['databaseUuid']==policy['databaseUuid'],'SOURCE_GLOBAL_STATE_INVALID')
 health=json.loads(run([target_control['pythonPin']['path'],'-B','-c',SPEC['healthProbe'],
  json.dumps(controllers[1]['controlConfigurationPin']),source,SPEC['targetConfigRef']],
  env=dict(os.environ,**target_control['environment'])))
 need(set(health)=={'minio','backend','frontend'} and
  all(row['result']['ready'] and row['result']['httpStatus']==200 for row in health.values()),'SOURCE_SEMANTIC_HEALTH_FAILED')
 need(not active_workers() and read_current(policy)==epoch,'SOURCE_CHANGED_DURING_CHECK')
 need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'SOURCE_RESOURCE_RESERVATION_REMAINS')
 reader.finish()
 full=SPEC['failedOriginalFullShaRequired']
 need(original['failedOriginalFilesPreserved']==(10044 if full else 0),'SOURCE_FAILED_ORIGINAL_SCOPE_CHANGED')
 report=dict(original,schemaVersion='AutomaticSourceRestoration/v1',kind=SPEC['kind'],operationId=operation,
  backupOperationId=operation,sourceConfigRef=source,observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  installationCommit=install['sourceCommit'],sourceIdentity=policy['sourceIdentity'],sourceEpoch=epoch,epochId=epoch['epochId'],
  sourceIdle=True,workerCount=0,sourceLockVerified=True,sourceServicesHealthy=True,semanticHealth=health,redisPongVerified=True,
  services=[dict(role=s['role'],id=s['id'],imageId=s['imageId'],running=True) for s in target['services']],
  activeOwnerConfigurationPin=owner_pin,sourceEngine=str(engine),installedEngineFilesVerified=len(SPEC['files']),
  failedOriginals=dict(inventoryCount=10044,fullShaVerified=full,verifiedFiles=10044 if full else 0,
   mode='FULL_SHA256' if full else 'NOT_RECHECKED_THIS_OBSERVATION'),
  inputPins=SPEC['inputPins'],sourceRuntime=source_runtime,targetRuntime=target_runtime,noRemoteMutation=True,
  **SPEC.get('deployment',{}))
finally:
 os.close(lock)
print(json.dumps(report))
'''


def prepare(kind, *, task=TASK, private=PRIVATE):
    destination = task / ('automatic-' + kind.lower() + '-source-restoration.json')
    if destination.exists():
        raise FileExistsError('SOURCE_REPORT_ALREADY_EXISTS')
    deployment = None if kind == 'FULL' else load_stage_deployment(task, private, kind)
    installation_name = ('automatic-control-installation-57.json' if deployment is None else
                         deployment['selection']['sourceInstallationPin']['file'])
    names = dict(installation=installation_name,
                 submission='automatic-' + kind.lower() + '-ui-submission.json',
                 audit='automatic-' + kind.lower() + '-audit.json',
                 terminal='automatic-' + kind.lower() + '-ui-terminal.json')
    values, pins = {}, {}
    for key, name in names.items():
        values[key], pins[key] = read_pinned(task / name)
    spec = validate_evidence(kind, **values, deployment=deployment)
    package = prepare_package(task / names['submission'], task / names['installation'], task=task, private=private)
    if deployment is not None:
        _,pins['deploymentSelection'] = read_pinned(task / deployment['selectionPin']['file'])
    exporter, pins['exporter'] = read_pinned(task / 'binlog-tmpfs-tool-provisioned.json')
    failed, pins['failedOriginalBaseline'] = read_pinned(task / 'registered-binlog-tool-restored.json')
    failed_pins = list(failed['failedOriginalPins'])
    for history in ('365', '366'):
        record, pins['failedOriginal' + history] = read_pinned(private / ('failed-' + history + '-all-pins.private.json'))
        failed_pins.extend(record['pins'])
    validate_failed_pins(failed_pins)
    from verify_source_restoration import SCRIPT as ORIGINAL_SCRIPT
    from install_automatic_57 import SCRIPT as INSTALL_SCRIPT
    tree = ast.parse(INSTALL_SCRIPT)
    probe = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'health_probe' for t in n.targets))
    core = (task / 'automatic_chain_audit.py').read_text(encoding='utf-8')
    target_probe = core + '\n' + SOURCE_RUNTIME + r'''
import sys
parameters=json.load(sys.stdin)
reader=AuditReader(seconds=30)
runtime=bind_source_runtime(reader,parameters['control'],parameters['engine'],parameters['files'])
from recovery_main_target import service_configuration_digest
digests={row['Id']:service_configuration_digest(row) for row in parameters['services']}
reader.finish()
print(json.dumps(dict(runtime=runtime,serviceConfigurationDigests=digests)))
'''
    spec.update(installation=values['installation'], request=values['submission']['request'], audit=values['audit'],
        inputPins=pins, exporter=exporter, failedPins=failed_pins if spec['failedOriginalFullShaRequired'] else [],
        originalSourceScript=ORIGINAL_SCRIPT, healthProbe=probe, targetConfigRef=TARGET, files=package['files'],
        controllerFiles=package['controllerFiles'],targetRuntimeProbe=target_probe)
    if deployment is not None:
        spec['deployment'] = package['deployment']
    return destination, spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', required=True, choices=['FULL', 'I1', 'I2'])
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    destination, spec = prepare(args.kind)
    if args.prepare_only:
        print(json.dumps(dict(status='PREPARED', kind=args.kind, operationId=spec['operationId'],
                              failedOriginalFullShaRequired=spec['failedOriginalFullShaRequired'], remoteReadDispatched=False)))
        return
    core = (TASK / 'automatic_chain_audit.py').read_text(encoding='utf-8')
    report = remote('172.30.30.57', core + '\nSPEC=' + repr(spec) + '\n' + SCRIPT, timeout=240)
    need(report['status'] == 'PASS' and report['operationId'] == spec['operationId'] and
         report['sourceConfigRef'] == SOURCE, 'SOURCE_RESULT_BINDING_CHANGED')
    for pin in spec['inputPins'].values():
        raw = Path(pin['path']).read_bytes()
        need(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'], 'SOURCE_LOCAL_INPUT_CHANGED')
    write_exclusive(destination, report)
    print(json.dumps(dict(status='PASS', kind=args.kind, operationId=report['operationId'], report=destination.name,
                         failedOriginals=report['failedOriginals'])))


if __name__ == '__main__':
    main()
