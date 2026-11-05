"""Read-only audit of the installed failing operation and remaining contracts."""
import json
from repair_preflight import remote,TASK
SCRIPT=r'''
import ast,copy,json,pathlib,sys
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from formal_data_evidence import validate_limits
from recovery_engine import pinned_json
request=json.loads((root/'recovery-operations/smallapp-91cc5c0b4b054cb38075681f1aca7d4a/request.json').read_bytes())
configuration=json.loads((root/'recovery-operations'/request['operationId']/'configuration.json').read_bytes())
source=configuration['sources'][request['sourceConfigRef']]
point=pinned_json(source['recoveryPoints'][request['recoveryPointRef']])
binding=pinned_json(source['repositoryBindingPinsByManifestSha256'][point['manifestPin']['sha256']])
material=pinned_json(binding['recoveryMaterialPin'])
assert point['pointType']=='FULL'
target=owner['targets'][request['targetConfigRef']]
corrected=copy.deepcopy(owner['dataLimits']);corrected['max_bytes']=16*1024**3
assert validate_limits(corrected)==corrected
expected=pinned_json(material['database']['expectedDataPin'])
shapes={}
engine=pathlib.Path(owner['formalModuleDirectory']).parent
for file,names in [('common/recovery_minimal_runtime.py',{'physical_object_chain'}),
                   ('common/recovery_minimal_derived.py',{'rebuild'}),
                   ('common/recovery_data.py',{'consistency','database_readback'})]:
 tree=ast.parse((engine/file).read_text())
 shapes[file]={n.name:ast.unparse(n) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name in names}
out={'operationId':request['operationId'],'correctedLimits':corrected,
 'maxExpandedBytes':owner['maxExpandedBytes'],'chainLength':1,
 'expectedTableCount':len(expected['tables']),'expectedRowCount':sum(t['rows'] for t in expected['tables'].values()),
 'objectMethod':material['objects']['method'],'dataPolicyKeys':sorted(target['dataPolicy']),
 'minioFileOwnership':target['dataPolicy'].get('minioFileOwnership'),
 'redisAdapter':{k:v for k,v in target['redisRebuild'].items() if k in ('kind','database')},
 'remainingImplementation':shapes,'remoteMutation':False}
print(json.dumps(out))
'''
if __name__=='__main__':
    out=remote('172.30.30.58',SCRIPT,60)
    (TASK/'readback-configuration-audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in out.items() if k!='remainingImplementation'}))
