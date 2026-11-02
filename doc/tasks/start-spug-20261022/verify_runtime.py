"""Read-only final verification; credential values never enter tool output."""
import json
import subprocess
from pathlib import Path

PACKAGE = Path('C:/Spug/Spug-complete-20261022-151627')


def run(args, data=None):
    p = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError('Verification command failed: ' + args[0] + '; raw output withheld')
    return p.stdout


prefix = ['docker', 'compose', '-p', 'intruoyi-spug-transfer', '-f', str(PACKAGE / 'compose.transfer.json')]
db = run(prefix + ['ps', '-q', 'db']).decode().strip()
app = run(prefix + ['ps', '-q', 'spug']).decode().strip()
assert db and app, 'Missing containers'
counts = run(['docker', 'exec', '-i', db, 'sh', '-c', 'exec mariadb -u root -p"$MYSQL_ROOT_PASSWORD" -N spug'],
             b'SELECT (SELECT COUNT(*) FROM hosts),(SELECT COUNT(*) FROM tasks),(SELECT COUNT(*) FROM users),(SELECT COUNT(*) FROM task_histories);').decode().strip()
assert list(map(int, counts.split())) == [3, 14, 1, 157], 'Record counts differ from backup'
check = run(['docker', 'exec', db, 'sh', '-c', 'exec mariadb-check -u root -p"$MYSQL_ROOT_PASSWORD" spug']).decode()
assert all(line.endswith('OK') for line in check.splitlines() if line.strip()), 'MariaDB table checks not all OK'
probe = '''
import configparser,json,os,shlex
from pathlib import Path
c=configparser.RawConfigParser(); c.read('/etc/supervisord.conf')
section='program:spug-scheduler'
assert not c.getboolean(section,'autostart'), 'Scheduler autostart active'
signature=shlex.split(c.get(section,'command'))[1:]
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit() or int(p.name)==os.getpid(): continue
 try: args=(p/'cmdline').read_bytes().decode().split('\\0')
 except (FileNotFoundError,PermissionError,ProcessLookupError): continue
 if any(args[i:i+len(signature)]==signature for i in range(len(args))): active.append(p.name)
assert not active, 'Scheduler process running'
print(json.dumps({'autostart':False,'activeProcessCount':len(active)}))
'''
scheduler = json.loads(run(['docker', 'exec', app, 'python3', '-c', probe]))
plan = json.loads((PACKAGE / 'installation-plan.json').read_text('utf-8-sig'))
for image in plan['images']:
    actual = json.loads(run(['docker', 'image', 'inspect', image['reference']]))[0]['Id']
    assert actual == image['id'], 'Image mismatch'
inspection = json.loads(run(['docker', 'inspect', app]))[0]
expected_binds = {'/opt/intruoyi-spug': 'C:/Spug/runtime/ops/spug',
                  '/run/intruoyi-spug': 'C:/Spug/runtime/private',
                  '/transfer': 'C:/Spug/Spug-complete-20261022-151627'}
for mount in inspection['Mounts']:
    if mount['Destination'] in expected_binds:
        source = mount['Source'].replace('/run/desktop/mnt/host/c/', 'C:/').replace('\\', '/')
        assert source == expected_binds[mount['Destination']], 'Actual bind source differs from C: plan'
assert inspection['NetworkSettings']['Ports']['80/tcp'] == [{'HostIp': '127.0.0.1', 'HostPort': '18080'}]
assert inspection['State']['Running']
assert json.loads(run(['docker', 'inspect', db]))[0]['State']['Running']
result = {'recordCounts': dict(zip(['hosts', 'tasks', 'users', 'taskHistories'], [3, 14, 1, 157])),
          'databaseTableChecks': len(check.splitlines()), 'scheduler': scheduler,
          'imageIdentity': 'PASS', 'localPortBinding': '127.0.0.1:18080',
          'mounts': [{'type': m['Type'], 'source': m['Source'], 'destination': m['Destination']} for m in inspection['Mounts']]}
Path(__file__).with_name('runtime-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
