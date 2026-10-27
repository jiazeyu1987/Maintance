"""Restore only original test containers after the pre-migration capture failure."""
import json
from pathlib import Path
import shlex
import subprocess
import win32serviceutil

descriptor = Path(win32serviceutil.GetServiceCustomOption('IntRuoyiReleaseExecutor', 'Descriptor'))
c = json.loads(Path(json.loads(descriptor.read_text('utf-8'))['config']).read_text('utf-8'))
t = c['targets']['test']
root = t['stagingRoot'] + '/2026-10-27-13-12-40'
script = r'''
import json,os,subprocess
root=__TASK_ROOT__
receipt=json.load(open(root.rsplit('/',1)[0]+'/.operations/OP-2ea3e0a38441f929ed00.json'))
assert receipt['jobId']=='JOB-eb798dd338' and receipt['status']=='failed'
assert not os.path.exists('/proc/'+str(receipt['pid'])) or open('/proc/'+str(receipt['pid'])+'/stat').read().split(') ',1)[1].split()[19]!=receipt['processStart']
assert not os.path.exists(root+'/deployment-pending.json') and not os.path.exists(root+'/recovery-record.private.json')
original=json.load(open(root+'/recovery-containers.private.json'))
names=__TASK_NAMES__
def run(args):return subprocess.check_output(args,stderr=subprocess.PIPE).decode('utf-8')
current={x['Name'].lstrip('/'):x for x in json.loads(run(['docker','inspect']+list(names.values())))}
for role,name in names.items():
 assert current[name]['Id']==original[name]['Id'] and current[name]['Image']==original[name]['Image']
sql="DESCRIBE infra_release_migration; SELECT COUNT(*) FROM infra_release_migration WHERE release_tag='2026-10-27-13-12-40'; SELECT @@global.read_only,@@global.super_read_only;"
env=dict(item.split('=',1) for item in current[names['database']]['Config']['Env'])
if 'MYSQL_ROOT_PASSWORD_FILE' in env:
 auth='export MYSQL_PWD="$(cat "$MYSQL_ROOT_PASSWORD_FILE")"; '
elif env.get('MYSQL_ROOT_PASSWORD'):
 auth='export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; '
else:
 raise RuntimeError('Configured database credential source missing')
command=auth+'exec mysql -uroot -N -B "$MYSQL_DATABASE" -e '+__import__('shlex').quote(sql)
answer=run(['docker','exec',names['database'],'sh','-c',command]).splitlines()
assert answer[-2]=='0' and answer[-1]=='0\t0', 'Migration or external read-only fence present'
for role in ('redis','minio','backend','frontend'):
 run(['docker','start',names[role]])
print(json.dumps({'originalContainersStarted':True,'migrationRows':0,'databaseRestored':False,'snapshotFilesRetained':True}))
'''.replace('__TASK_ROOT__', repr(root)).replace('__TASK_NAMES__', repr({k: t[k] for k in ('backend', 'frontend', 'database', 'redis', 'minio')}))
compile(script, 'restore-unmodified-test', 'exec')
result = subprocess.run(['ssh', '-i', str(Path.home()/'.ssh/id_rsa'), '-o', 'BatchMode=yes', 'root@'+t['host'],
                         shlex.quote(t['python'])+' -c '+shlex.quote(script)], capture_output=True, text=True, timeout=120)
if result.returncode:
    raise RuntimeError('Original-container recovery check/start failed; exit '+str(result.returncode)+': '+result.stderr[-1200:])
print(result.stdout)
(Path(__file__).parent/'test-service-restoration.json').write_text(result.stdout, 'utf-8')
