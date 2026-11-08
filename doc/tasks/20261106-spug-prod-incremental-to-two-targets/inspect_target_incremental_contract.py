"""Read installed target protocol support before the new incremental is admitted."""
import argparse,json
from common import TASK,remote,write,allocator_installation,allocator_contract_name

SCRIPT=r'''
import datetime,hashlib,json,pathlib
root=pathlib.Path(ROOT);receipt=json.loads((root/'target-installation.json').read_bytes())
def read(pin):
 raw=pathlib.Path(pin['path']).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'CONFIGURATION_CHANGED'
 return json.loads(raw)
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
engine=pathlib.Path(owner['formalModuleDirectory']).parent;version=json.loads((engine/'package.json').read_bytes())
assert all(hashlib.sha256((engine/name).read_bytes()).hexdigest()==sha for name,sha in version['files'].items()),'INSTALLED_ENGINE_CHANGED'
checks={}
for name in ('common/recovery_data.py','formal/formal_data_evidence.py','common/recovery_plan.py'):
 raw=(engine/name).read_bytes();text=raw.decode()
 checks[name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),databaseDdlScopeV3Recognized='backup-binlog-event-scope/v3' in text,scopedDatabaseDdlPolicyRecognized='MYSQL80_ROW_AND_SCOPED_DATABASE_DDL' in text)
compatible=all(checks[n]['databaseDdlScopeV3Recognized'] and checks[n]['scopedDatabaseDdlPolicyRecognized'] for n in ('common/recovery_data.py','formal/formal_data_evidence.py'))
allocator=False;health=False;constructor=False;endpoints={}
if ALLOCATOR_INSTALL is not None:
 assert receipt['sourceCommit']==ALLOCATOR_INSTALL['sourceCommit'] and str(engine)==ALLOCATOR_INSTALL['engine']
 assert version['packageSha256']==ALLOCATOR_INSTALL['fileManifestSha256']
 import ast
 data=ast.parse((engine/'common/recovery_data.py').read_text())
 native=next(n for n in data.body if isinstance(n,ast.ClassDef) and n.name=='NativeData')
 assert any(isinstance(n,ast.FunctionDef) and n.name=='restore_allocator_state' for n in native.body)
 incremental=next(n for n in native.body if isinstance(n,ast.FunctionDef) and n.name=='incremental_captured_sql')
 assert 'sql-allocator-state' in ast.unparse(incremental) and 'restore_allocator_state' in ast.unparse(incremental)
 schema=ast.parse((engine/'formal/formal_schema_evidence.py').read_text())
 assert {'restore_frozen_auto_increment','frozen_auto_increment_plan'} <= {n.name for n in schema.body if isinstance(n,ast.FunctionDef)}
 import sys
 sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
 from recovery_minimal_runtime import modules_from
 modules=modules_from(str(engine/'formal'))
 assert callable(modules['formal_schema_evidence'].restore_frozen_auto_increment)
 assert pathlib.Path(modules['formal_schema_evidence'].__file__).resolve()==engine/'formal/formal_schema_evidence.py'
 allocator=True
 if ALLOCATOR_INSTALL.get('actualHealthContractVerified'):
  import subprocess
  from types import SimpleNamespace
  from recovery_main_health import endpoint,preflight
  from recovery_control_smallapp_native import Native
  assert receipt['ownerConfigurationPin']==ALLOCATOR_INSTALL['ownerConfigurationPin'] and receipt['controlConfigurationPin']==ALLOCATOR_INSTALL['controlConfigurationPin']
  reference='intruoyi-main-'+HOST.rsplit('.',1)[1]+'-safe-restore-20261104-v1'
  target=owner['targets'][reference]
  def docker(args):
   process=subprocess.run(['docker',*args],capture_output=True,timeout=20);assert process.returncode==0 and not process.stderr;return process.stdout
  rows={s['role']:json.loads(docker(['inspect',s['id']]))[0] for s in target['services']}
  view=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},
   frontend_readiness=owner.get('frontendReadiness',{}).get(reference),docker=docker,
   inspect=lambda identity:next(r for r in rows.values() if r['Id']==identity))
  preflight(view);endpoints={role:endpoint(view,role) for role in ('minio','backend','frontend')}
  selection=Native(receipt['controlConfigurationPin']).selections(selected_target=reference)
  assert reference in next(a for a in selection['applications'] if a['sourceConfigRef']=='intruoyi-57-safe-20261024-v1')['freshTargetConfigRefs']
  health=True
  if ALLOCATOR_INSTALL.get('actualPackagedConstructorVerified'):
   boundary=read(ALLOCATOR_INSTALL['constructorEvidencePin'])
   assert boundary['schemaVersion']=='TaskPackagedConstructorBoundary/v1' and boundary['ownerConfigurationPin']==receipt['ownerConfigurationPin']
   assert pathlib.Path(boundary['constructorModulePath'])==engine/'common/recovery_minimal_runtime.py'
   assert boundary['exactProfileFromActualOwner'] and boundary['noDatabaseIO'] and not boundary['restoreDispatched']
   assert boundary['healthEndpoints']==endpoints and len(boundary['nativeInvocationPins'])>=3
   assert all(read(p)['mutation'] is False and read(p)['actualExitCode']==0 for p in boundary['nativeInvocationPins'])
   constructor=True
print(json.dumps(dict(status='PASS' if compatible else 'BLOCKER',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=HOST,engine=str(engine),fileCount=len(version['files']),packageFilesMatch=True,incrementalDatabaseDdlScopeV3Supported=compatible,frozenAllocatorRestoreSupported=allocator,actualHealthContractVerified=health,actualPackagedConstructorVerified=constructor,healthEndpoints=endpoints,moduleContracts=checks,serverWrites=False)))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);parser.add_argument('--allocator',action='store_true');args=parser.parse_args()
 destination=TASK/(allocator_contract_name(args.suffix) if args.allocator else 'target-incremental-contract-'+args.suffix+'.json');assert not destination.exists(),'CONTRACT_OBSERVATION_ALREADY_RECORDED'
 variables=dict(ROOT=('/mnt/intruoyi-data/' if args.suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',HOST='172.30.30.'+args.suffix)
 variables['ALLOCATOR_INSTALL']=allocator_installation(args.suffix) if args.allocator else None
 if args.allocator:assert variables['ALLOCATOR_INSTALL']['status']=='PASS'
 report=remote(variables['HOST'],'\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT,60)
 write(destination,report);print(json.dumps(report))
