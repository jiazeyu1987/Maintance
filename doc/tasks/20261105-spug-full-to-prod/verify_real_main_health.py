"""Read-only real original MinIO protocol and all registered port bindings."""
import json
from install_prod_control import remote,TASK

SCRIPT=r'''
import datetime,json,pathlib,sys
from types import SimpleNamespace
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_retained_retry import ReadOnlyTarget
operation=root/'recovery-operations'/'smallapp-d7a963eb1e9a4c16826c92d5753b30c3'
config=json.loads((operation/'configuration.json').read_bytes());request=json.loads((operation/'request.json').read_bytes())
native=ReadOnlyTarget(config,request,operation)
namespace={};exec(compile(MODULE,'recovery_main_health.py','exec'),namespace)
namespace['preflight'](native)
url=namespace['endpoint'](native,'minio')
result=namespace['probe'](url,'minio',5)
assert result['ready'] and result['httpStatus']==200
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 realOriginalMinio=True,registeredPortAndConfigurationBindingsVerified=True,endpoint=url,probe=result,mutations=0)))
'''
if __name__=='__main__':
    module=(TASK.parents[2]/'ops/recovery/recovery_main_health.py').read_text(encoding='utf-8')
    report=remote('MODULE='+repr(module)+'\n'+SCRIPT,40)
    (TASK/'real-main-health-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
