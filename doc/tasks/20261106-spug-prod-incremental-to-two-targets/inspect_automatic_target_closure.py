"""Read exact target deployment originals, keeping full configuration private."""
import json
from common import remote, write, PRIVATE

SCRIPT = r'''
import ast,datetime,hashlib,json,pathlib,subprocess
source='intruoyi-57-safe-20261024-v1';target_ref='intruoyi-main-'+SUFFIX+'-safe-restore-20261104-v1'
unit='spug-main-restore-'+SUFFIX+'-20261104-v3.service'
def pin(path):
 raw=pathlib.Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(reference):
 assert pin(reference['path'])==reference,'PIN_CHANGED';return json.loads(pathlib.Path(reference['path']).read_bytes())
def active_pid():
 raw=subprocess.check_output(['systemctl','show',unit,'-p','MainPID'],timeout=10).decode().strip()
 assert raw.startswith('MainPID=');return int(raw.split('=',1)[1])
pid=active_pid();assert pid>1
argv=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes().decode().split('\0')
control_pin=json.loads(argv[argv.index('--config-pin')+1]);control=read(control_pin)
owner_pin=control['restoreConfigurations'][source][target_ref];owner=read(owner_pin)
target=owner['targets'][target_ref];source_owner=read(control['sourceConfigurations'][source])
engine=pathlib.Path(owner['formalModuleDirectory']).parent
package=json.loads((engine/'package.json').read_bytes())
assert all(hashlib.sha256((engine/name).read_bytes()).hexdigest()==sha for name,sha in package['files'].items()),'ENGINE_CHANGED'
contracts={}
for basename in ('recovery_data.py','recovery_replace.py','recovery_minimal_runtime.py','recovery_control_smallapp_native.py'):
 names=[name for name in package['files'] if pathlib.PurePosixPath(name).name==basename]
 assert len(names)==1,'PACKAGE_MEMBER_AMBIGUOUS'
 name=names[0];text=(engine/name).read_text(encoding='utf-8');tree=ast.parse(text)
 methods=[ast.unparse(node) for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name=='incremental_captured_sql']
 contracts[name]=dict(pin=pin(engine/name),epochModuleMentioned='recovery_backup_epoch' in text,sourceEpochPolicies='sourceEpochPolicies' in text,targetBackupEpochPolicies='targetBackupEpochPolicies' in text,streamingSqlCheck='inspect_incremental_sql' in text,incrementalMethods=methods)
rows={}
for service in target['services']:
 raw=subprocess.run([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock','inspect',service['id']],capture_output=True,timeout=10)
 assert raw.returncode==0 and not raw.stderr
 actual=json.loads(raw.stdout);assert len(actual)==1 and actual[0]['Id']==service['id'];item=actual[0]
 rows[service['role']]={key:item.get(key) for key in ('Id','Image','Mounts','State')};rows[service['role']]['labels']=item['Config']['Labels']
assert active_pid()==pid,'SERVICE_CHANGED'
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host='172.30.30.'+SUFFIX,unit=unit,pid=pid,controlPin=control_pin,ownerPin=owner_pin,control=control,owner=owner,sourceOwner=source_owner,engine=str(engine),packagePin=pin(engine/'package.json'),package=package,allPackageFilesMatch=True,contracts=contracts,services=rows)))
'''

if __name__ == '__main__':
    for suffix in ('58', '59'):
        value = remote('172.30.30.' + suffix, 'SUFFIX=' + repr(suffix) + '\n' + SCRIPT, timeout=90)
        write(PRIVATE / ('automatic-target-closure-' + suffix + '.private.json'), value)
        target = value['owner']['targets']['intruoyi-main-' + suffix + '-safe-restore-20261104-v1']
        print(json.dumps(dict(host=value['host'], pid=value['pid'], unit=value['unit'],
            controlPin=value['controlPin'], ownerPin=value['ownerPin'], engine=value['engine'],
            packageFilesVerified=value['allPackageFilesMatch'], packageCount=len(value['package']['files']),
            targetKeys=list(target), ownerKeys=list(value['owner']), sourceOwnerKeys=list(value['sourceOwner']),
            sourceRefs=list(value['sourceOwner'].get('sources', {})), replacementKeys=list(target['replacement']),
            replacementLock=target['replacement']['lockPath'], databaseUuid=target['replacement']['databaseUuid'],
            targetIdentityPin=target.get('targetIdentityPin'),
            contracts={key: {k: v for k, v in row.items() if k != 'incrementalMethods'}
                       for key, row in value['contracts'].items()},
            services={role: dict(id=row['Id'], state=row['State']['Status'])
                      for role, row in value['services'].items()}), ensure_ascii=False))
