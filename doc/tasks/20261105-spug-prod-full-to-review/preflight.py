"""Read-only original MAIN and archive admission; keep raw Docker data private."""
import hashlib
import json
from pathlib import Path
import sys

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-full-to-review-20261105')
PREVIOUS = TASK.parent / '20261104-spug-selectable-restore-targets'
sys.path.insert(0, str(PREVIOUS))
from resume_readonly import SCRIPT as SNAPSHOT, remote
from install_review_control import SCRIPT as COMMON

ROOT = '/mnt/intruoyi-data/spug-main-restore-20261104-v3'
SOURCE = 'intruoyi-57-safe-20261024-v1'
POINT = 'smallapp-73cd541a95d84d6a86f9d693e4053c75'
TARGET = 'intruoyi-main-59-safe-restore-20261104-v1'

CHECK = r'''
import urllib.request
from types import SimpleNamespace
receipt=json.loads((root/'target-installation.json').read_bytes())
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_main_target import verify_runtime
from recovery_replacement_storage import verify_storage
from recovery_control_smallapp_native import Native
from recovery_control_restore_catalogue import bind_archive_chain,source_admits
from formal_data_evidence import validate_limits
need(receipt['targetConfigRef']==TARGET,'WRONG_TARGET')
native_control=Native(receipt['controlConfigurationPin'])
need(native_control.configuration()==control,'CONTROL_INVALID')
validate_limits(owner['dataLimits'])
target=owner['targets'][TARGET]
rows={s['role']:json.loads(run(['docker','inspect',s['id']]))[0] for s in target['services']}
need(all(r['State']['Running'] for r in rows.values()),'ORIGINAL_SERVICE_NOT_RUNNING')
native=SimpleNamespace(config=target,config_services={s['role']:s for s in target['services']},snapshots={},source=owner['sources'][SOURCE],root=root/'recovery-operations',inspect=lambda identity:next(r for r in rows.values() if r['Id']==identity),docker=lambda args:run(['docker',*args]))
verify_runtime(native,states=False);verify_storage(native,target['replacement'],rows)
engine=pathlib.Path(owner['formalModuleDirectory']).parent
version=json.loads((engine/'package.json').read_bytes())
need(all(pin(engine/n)['sha256']==h for n,h in version['files'].items()),'INSTALLED_PACKAGE_CHANGED')
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
need(not [p for n in ('ledger','operations','recovery-operations','replacement-state') for p in (root/n).rglob('*') if p.is_file() and p.name!='service.lock'],'EXISTING_OPERATION_RECORDS')
need(not [p for p in root.rglob('*claim*') if p.is_file()],'EXISTING_CLAIM')
request={'sourceConfigRef':SOURCE,'recoveryPointRef':POINT}
admitted=source_admits(native_control,owner['sources'][SOURCE],request)
resolved,binding=bind_archive_chain(owner['sources'][SOURCE],request)
need(POINT in admitted,'SOURCE_POINT_NOT_ADMITTED')
need(binding['pointPin']['sha256']=='af95ffa94e9478bd32935c6e0c662aa5590854a0cda7597b84a25abd81a8f128','WRONG_FULL_POINT')
need(len(resolved['repositoryPointPins'])==1,'WRONG_CHAIN')
archive=pathlib.Path('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
mount=[line for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(archive)]
need(len(mount)==1 and 'ro' in mount[0].split()[5].split(',') and ' - cifs //172.30.30.4/IT共享 ' in mount[0],'CANONICAL_ARCHIVE_NOT_RO')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://'+next(s['ip'] for s in target['services'] if s['role']=='backend')+':48081/actuator/health',timeout=10) as response:need(json.load(response)['status']=='UP','BACKEND_NOT_UP')
with opener.open('http://172.30.30.59:38081',timeout=10) as response:need(response.status==200,'FRONTEND_NOT_READY')
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
with opener.open(urllib.request.Request('http://127.0.0.1:33659/selections?targetConfigRef='+TARGET,headers=headers),timeout=35) as response:
 document=json.load(response);need(response.status==200,'TARGET_ADMISSION_HTTP')
need(TARGET in document['applications'][0]['freshTargetConfigRefs'],'TARGET_NOT_ADMITTED')
capacity=os.statvfs('/mnt/intruoyi-data');free=capacity.f_bavail*capacity.f_frsize
need(free>80*1024**3,'TARGET_CAPACITY_BELOW_80GIB')
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','sourceConfigRef':SOURCE,'recoveryPointRef':POINT,'targetConfigRef':TARGET,'ownerConfigurationPin':receipt['ownerConfigurationPin'],'controlConfigurationPin':receipt['controlConfigurationPin'],'dataLimits':owner['dataLimits'],'maxExpandedBytes':owner['maxExpandedBytes'],'pointPin':binding['pointPin'],'archiveEvidencePinsChecked':len(binding['evidencePins']),'archiveReadOnly':True,'packageFileCount':len(version['files']),'packageFilesMatch':True,'runtimeAndStorageVerified':True,'backendHealth':'UP','frontendHTTP':200,'targetFreeBytes':free,'targetAdmission':'PASS','activeReservation':False,'existingRestoreCount':0,'business':business()}))
'''

if __name__ == '__main__':
    PRIVATE.mkdir(parents=True, exist_ok=True)
    raw = remote('172.30.30.59', 'HOST="172.30.30.59"\nROOT='+repr(ROOT)+'\n'+SNAPSHOT, 100)
    (PRIVATE/'original-runtime-baseline.private.json').write_text(json.dumps(raw), encoding='utf-8')
    script = COMMON.split('receiptpath=root/')[0]
    script += '\n'.join(k+'='+repr(v) for k,v in {'SOURCE':SOURCE,'POINT':POINT,'TARGET':TARGET}.items())+'\n'+CHECK
    report = remote('172.30.30.59', script, 100)
    (TASK/'restore-preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='business'},ensure_ascii=False))
