"""Read-only inspection of the single failed source upgrade; no control APIs."""
import inspect
import json
from common import TASK,PRIVATE,SOURCE,remote
from install_automatic_source_successor import local_pin,rebind_document,package,exclusive_json

COMMIT='0dc7429d4758a208a5b0c098111fe9702ab63235'
SCRIPT=r'''
import datetime,hashlib,json,stat,subprocess,sys
from pathlib import Path
def checked(pin):
 assert local_pin(pin['path'])==pin,'PIN_CHANGED'
 return json.loads(Path(pin['path']).read_bytes())
def run(args):
 reply=subprocess.run(args,capture_output=True,timeout=30);assert reply.returncode==0,'READ_FAILED';return reply.stdout
old=SPEC['installation'];source_row,target_row=old['controllers']
source=checked(source_row['controlConfigurationPin']);owner=checked(source_row['ownerConfigurationPin'])
target=checked(target_row['controlConfigurationPin']);checked(target_row['ownerConfigurationPin'])
actual_pids={row['service']:int(run(['systemctl','show',row['service'],'-p','MainPID','--value'])) for row in old['controllers']}
assert all(actual_pids[row['service']]==row['pid'] for row in old['controllers']),'PID_CHANGED'
engine=Path(source['workingDirectory'])/('engine-automatic-'+SPEC['commit'][:7])
assert engine.is_dir() and engine.resolve()==engine and not engine.is_symlink(),'STAGED_ENGINE_ALIAS'
manifest=checked(dict(path=str(engine/'package.json'),**SPEC['packageJsonPin']))
assert manifest['files']==SPEC['files'] and manifest['packageSha256']==SPEC['manifest'],'STAGED_MANIFEST_CHANGED'
all_files=[]
for path in engine.rglob('*'):
 assert not path.is_symlink() and path.resolve()==path,'STAGED_CHILD_ALIAS'
 if path.is_file():all_files.append(path.relative_to(engine).as_posix())
assert set(all_files)==set(SPEC['files'])|{'package.json'},'STAGED_CONTENTS_CHANGED'
assert all(local_pin(engine/name)['sha256']==sha for name,sha in SPEC['files'].items()),'STAGED_FILE_CHANGED'
new_owner=rebind_document(owner,source_row['engine'],str(engine))
changes=[]
def compare(old,new,path):
 if isinstance(old,dict) and isinstance(new,dict):
  assert set(old)==set(new),'OWNER_KEYS_CHANGED'
  for key in old:compare(old[key],new[key],path+[key])
 elif isinstance(old,list) and isinstance(new,list):
  assert len(old)==len(new)
  for index,(left,right) in enumerate(zip(old,new)):compare(left,right,path+[str(index)])
 elif old!=new:changes.append(dict(field='.'.join(path),before=old,after=new))
compare(owner['sources'],new_owner['sources'],['sources'])
generation='automatic-'+SPEC['commit'][:7];root=Path(source['workingDirectory'])/'configuration'
pending=[root/('repository-'+generation+'.json'),root/('control-'+generation+'.json'),root/('staged-source-'+generation+'.json'),root/('installation-source-'+generation+'.json')]
assert all(not path.exists() and not path.is_symlink() for path in pending),'LATER_STAGE_ALREADY_EXISTS'
dropins=list((Path('/etc/systemd/system')/(source_row['service']+'.d')).glob('*'+SPEC['commit'][:7]+'*'))
assert not dropins,'NEW_DROPIN_ALREADY_EXISTS'
capture=Path(owner['sources'][SOURCE]['configurationPath']);capture_pin=local_pin(capture)
assert new_owner['sources'][SOURCE]['configurationPath']==str(capture),'CAPTURE_PATH_CHANGED'
sys.path.insert(0,str(Path(source_row['engine'])/'common'))
from recovery_backup_epoch import read_current
epoch=read_current(old['policy']);assert epoch==old['epoch'] and epoch['state']=='READY','EPOCH_CHANGED'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceCommit=SPEC['commit'],
 physicalCaptureConfigurationPin=capture_pin,ownerConfigurationPin=source_row['ownerConfigurationPin'],sourceFields=sorted(owner['sources'][SOURCE]),
 sourceFieldChanges=changes,sourceAndTargetPids=actual_pids,epoch=epoch,stagedEngine=str(engine),stagedFileCount=len(SPEC['files']),
 stagedPackageJsonPin=local_pin(engine/'package.json'),allStagedFilesVerified=True,newConfigurationAbsent=True,newDropinAbsent=True,
 newStageReceiptAbsent=True,controlApiCalled=False,remoteMutationDispatched=False,originalFailedApplyWroteEngine=True)))
'''

def main():
    old=json.loads((PRIVATE/'automatic-control-installation-57.private.json').read_text(encoding='utf-8'))
    build=json.loads((TASK/'release-build-0dc7429.json').read_text(encoding='utf-8'))
    raw,version=package(PRIVATE/'package-0dc7429/backup-restore-standard.tgz',build['packageSha256'])
    import io,tarfile,hashlib
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:meta=archive.extractfile('package.json').read()
    spec=dict(installation=old,commit=COMMIT,files=version['files'],manifest=version['packageSha256'],
              packageJsonPin=dict(bytes=len(meta),sha256=hashlib.sha256(meta).hexdigest()))
    code='SOURCE='+repr(SOURCE)+'\nSPEC='+repr(spec)+'\nfrom pathlib import Path\nimport hashlib\n'+inspect.getsource(local_pin)+'\n'+inspect.getsource(rebind_document)+'\n'+SCRIPT
    report=remote('172.30.30.57',code,timeout=90)
    exclusive_json(TASK/'automatic-source-successor-staged-engine-readonly.json',report)
    print(json.dumps(report))

if __name__=='__main__':main()
