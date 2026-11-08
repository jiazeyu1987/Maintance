"""Read-only supplemental identity evidence; never initializes or calls a Ledger."""
import ast
import hashlib
import json
from pathlib import Path
from common import TASK,PRIVATE,remote,write
from automatic_targets_install_script import SCRIPT


def main():
    output=TASK/'automatic-target59-empty-epoch-resume-proof.json'
    assert not output.exists(),'OBSERVATION_ALREADY_RECORDED'
    candidate=json.loads((PRIVATE/'automatic-target-candidate-59-0d44578.private.json').read_text(encoding='utf-8'))
    tree=ast.parse(SCRIPT);lines=SCRIPT.splitlines(keepends=True)
    definitions='\n'.join(''.join(lines[node.lineno-1:node.end_lineno]) for node in tree.body
        if isinstance(node,ast.FunctionDef) and node.name in ('canonical','pin','snapshot','mounts','verify_retained','identity'))
    body=r'''
import datetime,hashlib,json,os,pathlib,stat,subprocess
def need(value,code):
 if not value:raise ValueError(code)
def run(argv,timeout=60):
 p=subprocess.run(argv,capture_output=True,timeout=timeout);need(p.returncode==0,'READONLY_COMMAND_FAILED');return p.stdout
def docker(args):return run([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock',*args],timeout=60)
root=pathlib.Path(CANDIDATE['previousCustody']['root'])
oldowner=json.loads(pathlib.Path(CANDIDATE['oldOwnerPin']['path']).read_bytes());target=oldowner['targets'][CANDIDATE['targetConfigRef']]
protected_paths=['/mnt/nas',*target['dataPaths'],*oldowner['sources'][SOURCE]['archiveRoots']]
pid=int(run(['systemctl','show',CANDIDATE['service'],'-p','MainPID']).decode().strip().split('=',1)[1]);need(pid==CANDIDATE['oldControlPid'],'PID_CHANGED')
argv=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().decode().rstrip('\0').split('\0')
need(json.loads(argv[argv.index('--config-pin')+1])==CANDIDATE['oldControlPin'],'ACTIVE_CONTROL_CHANGED')
for ref in (CANDIDATE['oldControlPin'],CANDIDATE['oldOwnerPin'],CANDIDATE['oldActiveReceiptPin']):need(pin(ref['path'])==ref,'OLD_PIN_CHANGED')
for engine in (pathlib.Path(oldowner['formalModuleDirectory']).parent,pathlib.Path(CANDIDATE['engine'])):
 package=json.loads((engine/'package.json').read_bytes())
 need(all(pin(engine/name)['sha256']==sha for name,sha in package['files'].items()),'PACKAGE_CHANGED')
verify_retained()
observation=epoch_stage_observation(CANDIDATE,snapshot(),pin('/etc/fstab'),mounts(),pid)
proof=dict(schemaVersion='TaskAutomatic59EmptyEpochResume/v1',observation=observation,originalInternalExceptionUnavailable=True,
 originalErrorCode='EPOCH_INITIALIZATION_FAILED',localEvidencePins=LOCAL_EVIDENCE_PINS)
verification=verify_empty_epoch_stage_resume(proof,CANDIDATE,observation)
print(json.dumps(dict(proof,observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),serverWrites=False,noControlApiCalled=True,noLedgerCalled=True,
 oldAndNewPackageMembersVerified=True,retainedOriginalPinsVerified=True)))
'''
    refs=[]
    for path in (PRIVATE/'172.30.30.59-error-988ab621597a.private.log',TASK/'automatic-target59-epoch-stage-failure.json',PRIVATE/'automatic-target59-epoch-stage-failure.private.json'):
        raw=path.read_bytes();refs.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    script='CANDIDATE='+repr(candidate)+'\nSOURCE='+repr('intruoyi-57-safe-20261024-v1')+'\nLOCAL_EVIDENCE_PINS='+repr(refs)+'\n'
    script+=(TASK/'automatic_target_epoch_resume.py').read_text(encoding='utf-8')+'\n'+definitions+'\n'+body
    value=remote('172.30.30.59',script,timeout=120)
    write(output,value)
    print(json.dumps(dict(status='PASS',host=value['observation']['host'],pid=value['observation']['pid'],
        epochRootIdentity=value['observation']['epochRootIdentity'],emptyEpochRoot=True,serverWrites=False,noLedgerCalled=True)))


if __name__=='__main__':main()
