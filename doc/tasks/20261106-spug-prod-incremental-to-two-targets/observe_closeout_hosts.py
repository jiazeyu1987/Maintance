"""Capture final host preservation snapshots without control API side effects.

Full Docker/config/process records remain in PRIVATE. This does not use the old
installation selector, /selections, Ledger, SQL or any mutation command.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

from common import TASK, PRIVATE, SOURCE, remote
from automatic_stage_deployment import load_stage_deployment
from closeout_contracts import (pinned, read, controller_generation, validate_source_spug, file_pin)
from verify_automatic_source_restoration import (
    TARGET, need, read_pinned, validate_evidence, write_exclusive)


def moment(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def i2_binding(task=TASK, observed_at=None, *, private=PRIVATE):
    deployment=load_stage_deployment(task,private,'I2')
    values, pins = {}, {}
    for key, name in dict(installation=deployment['selection']['sourceInstallationPin']['file'],
        submission='automatic-i2-ui-submission.json', audit='automatic-i2-audit.json',
        terminal='automatic-i2-ui-terminal.json', restoration='automatic-i2-source-restoration.json').items():
        values[key], pins[key] = read_pinned(task / name)
    validate_evidence('I2', **{k: v for k, v in values.items() if k != 'restoration'},deployment=deployment)
    audit, restoration = values['audit'], values['restoration']
    operation = values['submission']['request']['operationId']
    need(restoration['schemaVersion'] == 'AutomaticSourceRestoration/v1' and restoration['status'] == 'PASS' and
         restoration['kind'] == 'I2' and restoration['operationId'] == operation and
         restoration['sourceConfigRef'] == SOURCE and restoration['installationCommit'] == deployment['sourceCommit'] and
         restoration['sourceEpoch'] == audit['sourceEpoch'], 'CLOSEOUT_I2_RESTORATION_CHANGED')
    need(restoration['sourceIdle'] is True and restoration['workerCount'] == 0 and
         restoration['sourceLockVerified'] is True and restoration['sourceServicesHealthy'] is True and
         restoration['originalGlobalStateRestored'] is True and restoration['redisPongVerified'] is True and
         restoration['eventScheduler'] == 'ON' and restoration['readOnly'] == restoration['superReadOnly'] == '0',
         'CLOSEOUT_I2_SOURCE_NOT_RESTORED')
    need(restoration['failedOriginals'] == dict(inventoryCount=10044, fullShaVerified=True,
         verifiedFiles=10044, mode='FULL_SHA256'), 'CLOSEOUT_I2_ORIGINALS_NOT_VERIFIED')
    need(restoration['deploymentSelectionPin']==deployment['selectionPin'] and
         restoration['sourceCommit']==deployment['sourceCommit'] and restoration['spugCommit']==deployment['spugCommit'] and
         restoration['sourceInstallationPin']==deployment['selection']['sourceInstallationPin'] and
         restoration['controllerGenerations']==deployment['controllerGenerations'], 'CLOSEOUT_I2_STAGE_CHANGED')
    _,pins['deploymentSelection']=read_pinned(task/('automatic-i2-deployment-selection.json'))
    need(all(restoration['inputPins'][key] == pins[key] for key in ('installation', 'submission', 'audit', 'terminal')),
         'CLOSEOUT_I2_RESTORATION_INPUT_CHANGED')
    need(restoration['inputPins']['deploymentSelection']==pins['deploymentSelection'],'CLOSEOUT_I2_STAGE_INPUT_CHANGED')
    last = max(moment(audit['finishedAt']), moment(values['terminal']['observedAt']))
    need(moment(restoration['observedAt']) >= last, 'CLOSEOUT_I2_RESTORATION_STALE')
    if observed_at is not None:
        need(moment(observed_at) > moment(restoration['observedAt']), 'CLOSEOUT_HOST_SNAPSHOT_BEFORE_I2')
    return dict(backupOperationId=operation, automaticI2EvidencePins=pins,
                sourceCommit=deployment['sourceCommit'],deploymentSelectionPin=deployment['selectionPin'],
                automaticI2FinishedAt=audit['finishedAt'], sourceRestorationObservedAt=restoration['observedAt'])


def controller_selection(suffix, task=TASK, *, selection_file='automatic-current-installations.json', private=PRIVATE):
    need(suffix in ('57', '58', '59'), 'CLOSEOUT_HOST_REQUIRED')
    from main_program_installation_selection import local_name, select_main_program_installation
    local_name(selection_file)
    selected,selected_pin=read_pinned(task/selection_file)
    if selected.get('schemaVersion') == 'TaskMainProgramInstallations/v1':
        return select_main_program_installation(suffix, task, selection_file=selection_file)
    if selected.get('schemaVersion') == 'TaskMainProgramInstallations/v2':
        return select_main_program_installation(suffix, task, selection_file=selection_file,private=private)
    if selection_file != 'automatic-current-installations.json':
        raise ValueError('MAIN_INSTALLATION_SELECTION_INVALID')
    need(selected['schemaVersion']=='TaskCurrentInstallations/v2','CLOSEOUT_EXPLICIT_CURRENT_SELECTION_REQUIRED')
    source=pinned(task,selected['source57']);spug=pinned(task,selected['spug'])
    validate_source_spug(task,source,spug)
    _,source_pin=read_pinned(task/selected['source57']['file'])
    local_pins = [selected_pin,source_pin]
    if suffix == '57':
        controllers = [dict(item,**controller_generation(source,index,task)) for index,item in enumerate(source['controllers'])]
        need(len(controllers) == 2, 'CLOSEOUT_SOURCE_DUAL_ROOT_REQUIRED')
        target_ref, active_receipt = TARGET, None
    else:
        installed=pinned(task,selected['targets'][suffix])
        _,reference=read_pinned(task/selected['targets'][suffix]['file'])
        need(installed['status'] == 'PASS', 'CLOSEOUT_CURRENT_INSTALLATION_REQUIRED')
        retained=controller_generation(source,1,task)
        need(installed['host'] == '172.30.30.' + suffix and
             all(installed[key] == retained[key] for key in ('sourceCommit','packageSha256', 'fileManifestSha256', 'fileCount')),
             'CLOSEOUT_CURRENT_INSTALLATION_CHANGED')
        controllers = [dict(installed, pid=installed['controlPid'])]
        target_ref, active_receipt = installed['targetConfigRef'], installed['currentReceiptPin']
        local_pins.append(reference)
    keys = ('service', 'engine', 'pid', 'controlConfigurationPin', 'ownerConfigurationPin',
            'sourceCommit','fileManifestSha256','fileCount')
    for pin in (selected['spug'],source.get('predecessorInstallationPin'),
                controller_generation(source,1,task).get('installationPin'),
                controller_generation(source,0,task)['buildPin'],controller_generation(source,1,task)['buildPin']):
        if pin is not None:
            _,reference=read_pinned(task/pin['file'])
            if reference not in local_pins:local_pins.append(reference)
    return dict(host='172.30.30.' + suffix, suffix=suffix, sourceCommit=controllers[0]['sourceCommit'],
        currentSourceCommit=source['sourceCommit'],currentInstallationSelectionPin=file_pin(task,'automatic-current-installations.json'),
        controllers=[{key: item[key] for key in keys} for item in controllers], targetConfigRef=target_ref,
        activeReceiptPin=active_receipt,
        localInstallationPins=local_pins)


SCRIPT = r'''
import datetime,hashlib,json,os,pathlib,subprocess,sys
from types import SimpleNamespace
out=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=SPEC['host'],documents={},pins={},admissions={})
def need(condition,code):
 if not condition:raise ValueError(code)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def document(reference):
 path=pathlib.Path(reference['path']);need(path.resolve(strict=True)==path and not path.is_symlink(),'CLOSEOUT_CONFIG_ALIAS')
 raw=path.read_bytes();need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'CLOSEOUT_PIN_CHANGED')
 value=json.loads(raw);out['documents'][str(path)]=value;out['pins'][str(path)]=reference;return value
def run(arguments):
 result=subprocess.run(arguments,capture_output=True,timeout=30)
 need(result.returncode==0,'CLOSEOUT_READ_COMMAND_FAILED');return result.stdout
controls=[];owners=[];properties=[]
for controller in SPEC['controllers']:
 control=document(controller['controlConfigurationPin']);owner=document(controller['ownerConfigurationPin'])
 properties.append(run(['systemctl','show',controller['service'],'-p','ActiveState','-p','SubState','-p','MainPID','-p','LimitNOFILE']).decode())
 pid_property=run(['systemctl','show',controller['service'],'-p','MainPID']).decode().strip()
 need(pid_property.startswith('MainPID=') and pid_property[8:].isdecimal(),'CLOSEOUT_SERVICE_PID_PROPERTY_INVALID')
 need(int(pid_property[8:])==controller['pid'],'CLOSEOUT_SERVICE_PID_CHANGED')
 argv=(pathlib.Path('/proc')/str(controller['pid'])/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
 expected=[control['pythonPin']['path'],'-B',str(pathlib.Path(controller['engine'])/'control_entry.py'),'serve','--config-pin']
 need(len(argv)==6 and argv[:5]==expected and json.loads(argv[5])==controller['controlConfigurationPin'],'CLOSEOUT_SERVICE_ARGV_CHANGED')
 engine=pathlib.Path(controller['engine'])
 if SPEC['suffix']=='57' and controller is SPEC['controllers'][0]:
  need(owner['schemaVersion']=='RepositoryMinimumConfiguration/v1','CLOSEOUT_SOURCE_OWNER_SCHEMA_CHANGED')
 else:
  need(owner['schemaVersion']=='RecoveryMinimalConfiguration/v1' and pathlib.Path(owner['formalModuleDirectory']).parent==engine,'CLOSEOUT_OWNER_ENGINE_CHANGED')
 package=json.loads((engine/'package.json').read_bytes())
 need(len(package['files'])==controller['fileCount'] and package['packageSha256']==controller['fileManifestSha256'] and
  hashlib.sha256(canonical(package['files'])).hexdigest()==controller['fileManifestSha256'],'CLOSEOUT_PACKAGE_MANIFEST_CHANGED')
 need(all(hashlib.sha256((engine/name).read_bytes()).hexdigest()==sha for name,sha in package['files'].items()),'CLOSEOUT_PACKAGE_FILE_CHANGED')
 controls.append(control);owners.append(owner)
if SPEC['activeReceiptPin'] is not None:
 receipt=document(SPEC['activeReceiptPin']);selected=SPEC['controllers'][0]
 need(receipt['controlConfigurationPin']==selected['controlConfigurationPin'] and
  receipt['ownerConfigurationPin']==selected['ownerConfigurationPin'] and receipt['sourceCommit']==SPEC['sourceCommit'],
  'CLOSEOUT_ACTIVE_RECEIPT_CHANGED')
if SPEC['suffix']=='57':
 need(controls[0]['sourceConfigurations'][SOURCE]==SPEC['controllers'][0]['ownerConfigurationPin'],'CLOSEOUT_SOURCE_BINDING_CHANGED')
target_control=controls[-1];owner=owners[-1];selected=SPEC['controllers'][-1]
need(target_control['restoreConfigurations'][SOURCE][SPEC['targetConfigRef']]==selected['ownerConfigurationPin'],'CLOSEOUT_TARGET_BINDING_CHANGED')
target=owner['targets'][SPEC['targetConfigRef']];root=pathlib.Path(target_control['workingDirectory'])
out['targetConfigRef']=SPEC['targetConfigRef'];out['serviceProperties']=properties[-1]
out['packageFilesMatch']=True;out['packageFileCount']=selected['fileCount']
out['controllerGenerations']=[{key:item[key] for key in ('service','pid','sourceCommit','fileManifestSha256','fileCount')} for item in SPEC['controllers']]
out['containers']=json.loads(run(['docker','inspect',*run(['docker','ps','-aq','--no-trunc']).decode().split()]))
out['mountinfo']=pathlib.Path('/proc/self/mountinfo').read_text(encoding='utf-8')
out['fstabSha256']=hashlib.sha256(pathlib.Path('/etc/fstab').read_bytes()).hexdigest()
out['capacity']={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in (str(root),'/opt/intruoyi/runtime')}
reservation=pathlib.Path('/var/lib/spug-restore-resources/active.json')
out['activeReservation']=json.loads(reservation.read_bytes()) if reservation.exists() else None
out['processes']=[]
for path in pathlib.Path('/proc').iterdir():
 if not path.name.isdecimal():continue
 try:
  raw=(path/'cmdline').read_bytes()
  if not any(c['workingDirectory'].encode() in raw for c in controls):continue
  out['processes'].append(dict(pid=int(path.name),commandSha256=hashlib.sha256(raw).hexdigest(),
   command=raw.decode().replace('\0',' '),stat=(path/'stat').read_text()))
 except (FileNotFoundError,ProcessLookupError):continue
engine=pathlib.Path(selected['engine'])
module_paths=target_control['environment']['PYTHONPATH'].split(os.pathsep)
need(module_paths and all(p and pathlib.Path(p).is_absolute() and pathlib.Path(p).is_dir() for p in module_paths),'CLOSEOUT_DECLARED_MODULE_PATH_INVALID')
sys.path[:0]=module_paths
from recovery_main_health import preflight,endpoint,probe
rows={row['Id']:row for row in out['containers']}
native=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},
 inspect=lambda identity:rows[identity],frontend_readiness=owner.get('frontendReadiness',{}).get(SPEC['targetConfigRef']))
preflight(native)
health={role:probe(endpoint(native,role),role,12) for role in ('minio','backend','frontend')}
out['http']=dict(backend=dict(httpStatus=health['backend']['httpStatus'],status='UP' if health['backend']['ready'] else 'DOWN'),
 frontend=dict(httpStatus=health['frontend']['httpStatus']),minio=health['minio'])
out['semanticHealth']=health;out['installationCommit']=SPEC['sourceCommit']
out['currentSourceCommit']=SPEC['currentSourceCommit'];out['currentInstallationSelectionPin']=SPEC['currentInstallationSelectionPin']
out['backupOperationId']=SPEC['i2']['backupOperationId'];out['automaticI2EvidencePins']=SPEC['i2']['automaticI2EvidencePins']
out['strictReadOnlyCollection']=True;out['controlApiCalled']=False;out['localInstallationPins']=SPEC['localInstallationPins']
out['finishedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(out))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suffix', choices=['57', '58', '59'])
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--selection-file', default='automatic-current-installations.json',
                        help='Explicit task-local installation selection JSON file')
    args = parser.parse_args()
    destination = PRIVATE / ('closeout-' + args.suffix + '.private.json')
    public = TASK / ('closeout-' + args.suffix + '.json')
    if destination.exists() or public.exists():
        raise FileExistsError('CLOSEOUT_SNAPSHOT_ALREADY_EXISTS')
    spec = controller_selection(args.suffix, selection_file=args.selection_file)
    spec['i2'] = i2_binding()
    if args.selection_file == 'automatic-current-installations.json':
        need(spec['currentSourceCommit']==spec['i2']['sourceCommit'],'CLOSEOUT_CURRENT_SOURCE_NOT_I2_GENERATION')
    if args.prepare_only:
        print(json.dumps(dict(status='PREPARED', host=spec['host'], backupOperationId=spec['i2']['backupOperationId'],
                              sourceCommit=spec['sourceCommit'], remoteReadDispatched=False)))
        return
    value = remote(spec['host'], 'SOURCE=' + repr(SOURCE) + '\nSPEC=' + repr(spec) + '\n' + SCRIPT, 180)
    need(value['host'] == spec['host'] and value['backupOperationId'] == spec['i2']['backupOperationId'], 'CLOSEOUT_RESPONSE_CHANGED')
    need(i2_binding(TASK, value['observedAt']) == spec['i2'], 'CLOSEOUT_I2_CHANGED_DURING_SNAPSHOT')
    for reference in spec['localInstallationPins']:
        raw = Path(reference['path']).read_bytes()
        need(len(raw) == reference['bytes'] and hashlib.sha256(raw).hexdigest() == reference['sha256'], 'CLOSEOUT_LOCAL_INSTALLATION_CHANGED')
    write_exclusive(destination, value)
    summary = {key: value[key] for key in ('host', 'observedAt', 'finishedAt', 'targetConfigRef', 'packageFilesMatch',
        'packageFileCount', 'fstabSha256', 'http', 'installationCommit', 'currentSourceCommit','controllerGenerations',
        'currentInstallationSelectionPin','backupOperationId', 'strictReadOnlyCollection', 'controlApiCalled')}
    summary.update(status='OBSERVED', containerCount=len(value['containers']), activeReservation=bool(value['activeReservation']),
        privateBaselineSha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        processes=[{key: row[key] for key in ('pid', 'commandSha256')} for row in value['processes']])
    write_exclusive(public, summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
