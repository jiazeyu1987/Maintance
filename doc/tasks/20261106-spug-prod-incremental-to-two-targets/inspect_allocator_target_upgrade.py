"""Read-only exact target generation, failure custody and service bindings."""
import argparse
import json
from common import TASK, PRIVATE, now, remote, write

SCRIPT = r'''
import hashlib,json,pathlib,stat,subprocess,sys
root=pathlib.Path(ROOT)
def pin(p):
 p=pathlib.Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(ref):
 assert pin(ref['path'])==ref,'PIN_CHANGED';return json.loads(pathlib.Path(ref['path']).read_bytes())
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=45);assert p.returncode==0 and not p.stderr,'READONLY_COMMAND_FAILED';return p.stdout
receipt= json.loads((root/'target-installation.json').read_bytes())
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
target=owner['targets'][receipt['targetConfigRef']]
assert receipt['targetConfigRef']=='intruoyi-main-'+SUFFIX+'-safe-restore-20261104-v1'
engine=pathlib.Path(owner['formalModuleDirectory']).parent;version=json.loads((engine/'package.json').read_bytes())
assert version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification']
assert all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items())
rows={s['role']:json.loads(run(['docker','inspect',s['id']]))[0] for s in target['services']}
expected_running={'mysql','redis'} if SUFFIX=='58' else {'mysql','redis','minio','backend','frontend'}
assert {role for role,r in rows.items() if r['State']['Running']}==expected_running
assert all(not r['State']['Paused'] and not r['State']['Restarting'] for r in rows.values())
workers=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:cmd=(p/'cmdline').read_bytes()
 except (FileNotFoundError,ProcessLookupError):continue
 if str(root).encode() in cmd:
  assert b'control_entry.py' in cmd,'ACTIVE_TARGET_WORKER';workers.append(int(p.name))
active=pathlib.Path('/var/lib/spug-restore-resources/active.json')
active_pin=pin(active) if active.exists() else None
assert (active_pin is not None)==(SUFFIX=='58' and CLEARANCE is None)
failure_pins=[]
if SUFFIX=='58':
 if CLEARANCE is None:assert json.loads(active.read_bytes())['operationId']==FAILED_OPERATION
 operation=root/'recovery-operations'/FAILED_OPERATION
 request=json.loads((operation/'request.json').read_bytes())
 original=json.loads((operation/'configuration.json').read_bytes())
 assert request['recoveryPointRef']==POINT and original['targets']==owner['targets']
 for name in ('worker-result.json','child-exit.json','result.json','configuration.json','request.json'):
  failure_pins.append(pin(operation/name))
 assert json.loads((operation/'worker-result.json').read_bytes())['state']=='FAILED_RETAINED'
 assert json.loads((operation/'child-exit.json').read_bytes())==CHILD_EXIT
 sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
 from recovery_retained_retry import observe
 observation=observe(original,request,operation,885)
 if CLEARANCE is not None:
  from recovery_retained_retry import validate_clearance
  claim=pathlib.Path(target['replacement']['stateRoot'])/FAILED_OPERATION
  assert read(CLEARANCE['clearancePin'])==validate_clearance(target,claim)
  assert not (claim/'recovery-consumption.json').exists()
else:
 observation=None
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_control_smallapp_native import Native
Native(receipt['controlConfigurationPin']).configuration()
pid_row=run(['systemctl','show',receipt['service'],'-p','MainPID']).decode().strip()
assert pid_row.startswith('MainPID=') and pid_row.count('=')==1,'CONTROL_PID_PROPERTY_INVALID'
pid=int(pid_row.split('=',1)[1])
assert pid in workers and len(workers)==1
fdlimit=next(l for l in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if l.startswith('Max open files'))
assert fdlimit.split()[3:5]==['65536','65536']
print(json.dumps(dict(receipt=receipt,receiptPin=pin(root/'target-installation.json'),owner=owner,control=control,
 oldEngine=str(engine),oldFileCount=len(version['files']),oldManifestSha256=version['packageSha256'],
 activePointerPin=active_pin,retainedClearancePin=CLEARANCE['clearancePin'] if CLEARANCE else None,failurePins=failure_pins,retainedObservation=observation,
 unitText=run(['systemctl','cat',receipt['service']]).decode(),controlPid=pid,fdlimit=fdlimit,
 fstabPin=pin('/etc/fstab'),serviceStates={k:dict(id=r['Id'],running=r['State']['Running'],pid=r['State']['Pid']) for k,r in rows.items()})))
'''

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);parser.add_argument('--revision',choices=['r2','r3']);args=parser.parse_args()
    kind='allocator-upgrade-preflight-'+args.suffix+('-'+args.revision if args.revision else '')
    assert not (TASK/(kind+'.json')).exists()
    child=None
    if args.suffix=='58':
        failure=json.loads((PRIVATE/'restore-368-failure-documents.private.json').read_text(encoding='utf8'))
        # Read the exact child evidence through the remote observation itself;
        # explicit terminal values are independently asserted below.
    variables=dict(ROOT=('/mnt/intruoyi-data/' if args.suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',
        SUFFIX=args.suffix,FAILED_OPERATION='smallapp-c21bb7ce9f5b4668b850c37a80964786',
        POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',
        CLEARANCE=json.loads((TASK/'allocator-retained-recovery-clearance-58.json').read_text(encoding='utf8')) if args.suffix=='58' and args.revision=='r3' else None)
    # child-exit has additional protected fields; assert the actual required
    # terminal fields without synthesizing or substituting the original record.
    script=SCRIPT.replace("assert json.loads((operation/'child-exit.json').read_bytes())==CHILD_EXIT",
        "child=json.loads((operation/'child-exit.json').read_bytes());assert child['actualExitCode']==1 and child['timedOut'] is False")
    result=remote('172.30.30.'+args.suffix,'\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+script,240)
    write(PRIVATE/(kind+'.private.json'),result)
    report=dict(status='PASS',observedAt=now(),host='172.30.30.'+args.suffix,
        oldEngine=result['oldEngine'],oldFileCount=result['oldFileCount'],oldManifestSha256=result['oldManifestSha256'],
        receiptPin=result['receiptPin'],ownerConfigurationPin=result['receipt']['ownerConfigurationPin'],
        controlConfigurationPin=result['receipt']['controlConfigurationPin'],activePointerPin=result['activePointerPin'],
        failurePins=result['failurePins'],retainedClearancePin=result['retainedClearancePin'],serviceStates=result['serviceStates'],liveMaxOpenFiles=65536,
        retainedFailureObserved=args.suffix=='58',serverWrites=False)
    write(TASK/(kind+'.json'),report);print(json.dumps(report))
