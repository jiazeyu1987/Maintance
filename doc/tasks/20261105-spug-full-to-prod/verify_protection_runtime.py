"""Check actual protection release and stable controller paths after restore."""
import inspect
import json

from install_prod_control import PRIVATE, TASK, TARGET, remote


def verify_company_nas_mounts(before, after):
    """Require all original NAS submounts and covering filesystems unchanged."""
    protected = '/mnt/nas'

    def relevant(mount):
        point = mount['mountPoint']
        return (point == '/' or point == protected or
                protected.startswith(point + '/') or point.startswith(protected + '/'))

    original = sorted((m for m in before if relevant(m)), key=lambda m: m['mountPoint'])
    current = sorted((m for m in after if relevant(m)), key=lambda m: m['mountPoint'])
    assert any(m['mountPoint'] == protected or m['mountPoint'].startswith(protected + '/')
               for m in original), 'ORIGINAL_COMPANY_NAS_MOUNT_MISSING'
    assert current == original, 'COMPANY_NAS_MOUNT_CHANGED'
    return original


SCRIPT = r'''
import datetime,fcntl,hashlib,json,os,pathlib,subprocess,sys

def read(pin):
 raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'RUNTIME_PIN_CHANGED'
 return json.loads(raw)

def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
 assert p.returncode==0,'RUNTIME_CHECK_COMMAND_FAILED'
 return p.stdout

root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes())
assert receipt['targetConfigRef']==TARGET and receipt['sourceCommit']==COMMIT,'INSTALLED_GENERATION_CHANGED'
owner=read(receipt['ownerConfigurationPin']);control=read(receipt['controlConfigurationPin'])
target=owner['targets'][TARGET]
engine=root/('engine-mainv2-'+COMMIT[:7])
assert pathlib.Path(owner['formalModuleDirectory'])==engine/'formal','FORMAL_PATH_CHANGED'
assert pathlib.Path(control['workingDirectory'])==root,'CONTROL_ROOT_CHANGED'
version=json.loads((engine/'package.json').read_bytes())
assert len(version['files'])==126,'PACKAGE_FILE_COUNT_CHANGED'
for name,sha in version['files'].items():
 assert hashlib.sha256((engine/name).read_bytes()).hexdigest()==sha,'INSTALLED_PROGRAM_CHANGED'
paths=control['environment']['PYTHONPATH'].split(':')+[control['pythonPin']['path']]+[p['path'] for p in control['programPins'].values()]
assert all(pathlib.Path(p).is_absolute() and pathlib.Path(p).exists() for p in paths),'RUNTIME_PATH_MISSING'
assert all(not any(name in p for name in ('release-bdd8aab','release-db64656','release-9b3a298','release-1595d0f','release-9dce318')) for p in paths),'UNSTABLE_BUILD_DEPENDENCY'
assert all(pathlib.Path(p['path']).is_relative_to(engine) for p in control['programPins'].values()),'UNSTABLE_ENTRY_PATH'
assert run(['systemctl','is-active',receipt['service']]).strip()==b'active','CONTROL_INACTIVE'
assert run(['systemctl','is-enabled',receipt['service']]).strip()==b'enabled','CONTROL_NOT_ENABLED'
pid=int(run(['systemctl','show',receipt['service'],'-p','MainPID','--value']).strip())
arguments=pathlib.Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')
assert str(engine/'control_entry.py').encode() in arguments,'WRONG_LIVE_PROGRAM'
line=next(v for v in pathlib.Path('/proc',str(pid),'limits').read_text().splitlines() if v.startswith('Max open files'))
assert line.split()[3:5]==['65536','65536'],'LIVE_FD_BUDGET_CHANGED'
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_replacement_storage import parse_mountinfo
from recovery_published_fence import _table
from recovery_engine import check_pin
mounts=parse_mountinfo(pathlib.Path('/proc/self/mountinfo').read_text(encoding='utf-8'))
COMPANY_MOUNT=verify_company_nas_mounts(parse_mountinfo(ORIGINAL_MOUNTINFO),mounts)
expected=target['mainApplication']['archiveMountProtection']['mountIdentity']
assert [m for m in mounts if m['mountPoint']==expected['mountPoint']]==[expected],'ARCHIVE_VIEW_NOT_RESTORED'
claim=pathlib.Path(target['replacement']['stateRoot'])/OPERATION
archive=json.loads((claim/'archive-view/released.json').read_bytes())
assert archive['operationId']==OPERATION and archive['originalMountRestored'] is True
fence=json.loads((claim/'published-fence/released.json').read_bytes())
intent=json.loads((claim/'published-fence/intent.json').read_bytes())
assert fence['operationId']==intent['operationId']==OPERATION and fence['originalRulesPreserved'] is True
scheduler=json.loads((claim/'mysql-scheduler/released.json').read_bytes())
assert scheduler['schemaVersion']=='MainMysqlSchedulerRelease/v1' and scheduler['operationId']==OPERATION
assert scheduler['originalStateRestored'] is True and scheduler['originalState']=='ON'
for reference in [scheduler['intentPin'],scheduler['activePin']]:check_pin(reference)
from recovery_main_target import mysql_query
from types import SimpleNamespace
services={s['role']:s for s in target['services']}
def mysql_docker(args,**kwargs):
 response=subprocess.run([target['dockerPin']['path'],'--host','unix:///var/run/docker.sock',*args],input=kwargs.get('input_bytes'),capture_output=True,timeout=15)
 assert response.returncode==0 and not response.stderr,'MYSQL_STATE_QUERY_FAILED'
 return response.stdout
native=SimpleNamespace(config=target,config_services=services,db_container=services['mysql']['id'],docker=mysql_docker,
 policy=dict(target['dataPolicy'],environmentMysqlClientPath=owner['environmentMysqlClientPath']),
 secret=lambda role,key:check_pin(target['secrets'][role][key]).decode('utf-8'))
assert mysql_query(native,'SELECT @@server_uuid, @@GLOBAL.event_scheduler;').decode().strip()==target['replacement']['databaseUuid']+'\tON','MYSQL_SCHEDULER_ORIGINAL_STATE_NOT_RESTORED'
entry=next(v for v in target['mainApplication']['publishedDataEndpoints'] if v['role']=='minio')
for family,program in entry['writeFence']['programs'].items():
 check_pin(program['pin'])
 observed=_table(run([program['pin']['path'],program['applet'],'-w','5','-t','mangle','-S']))
 assert observed==intent['originalTables'][family],'ORIGINAL_RULES_CHANGED_AFTER_RELEASE'
assert not os.path.lexists('/var/lib/spug-restore-resources/active.json'),'ACTIVE_RESERVATION_REMAINS'
fd=os.open('/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/source-locks/source.lock',os.O_RDWR|os.O_NOFOLLOW)
try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
finally:os.close(fd)
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,controlActiveEnabled=True,stableRuntimePaths=True,installedFileCount=126,liveFdLimit=65536,archiveOriginalMountRestored=True,companyNasMountPreserved=True,publishedOriginalRulesPreserved=True,mysqlSchedulerOriginalStateRestored=True,mysqlSchedulerState='ON',sourceLockAvailable=True,reservationReleased=True)))
'''

if __name__ == '__main__':
    native=json.loads((TASK/'restored-native-evidence.json').read_text(encoding='utf-8'))
    assert native['status']=='PASS' and native['state']=='SUCCEEDED' and native['actualExitCode']==0
    custody=json.loads((PRIVATE/'custody-production.private.json').read_text(encoding='utf-8'))
    # Use the exact original line, parsed by the already verified installed module.
    installation=json.loads((TASK/'health-control-installation.json').read_text(encoding='utf-8'))
    assert installation['status']=='PASS'
    prelude='TARGET='+repr(TARGET)+'\nCOMMIT='+repr(installation['sourceCommit'])+'\nOPERATION='+repr(native['operationId'])+'\n'
    prelude+='ORIGINAL_MOUNTINFO='+repr(custody['mountinfo'])+'\n'
    prelude+=inspect.getsource(verify_company_nas_mounts)+'\n'
    report=remote(prelude+SCRIPT,65)
    (TASK/'protection-runtime-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
