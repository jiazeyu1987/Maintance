"""Use existing protected registered SSH identity for two fixed read-only targets."""
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

task = Path(__file__).resolve().parent
config = json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text(encoding='utf-8-sig'))
environment = sys.argv[1]
expected = {'test': '172.30.30.58', 'prod': '172.30.30.57'}
assert environment in expected
profile = config['targets'][environment]
assert profile['host'] == expected[environment]
assert re.fullmatch(r'[/A-Za-z0-9_.-]+', profile['python'])
identity, known_hosts = config['sshIdentityFile'], config['sshKnownHostsFile']
assert Path(identity).is_file() and Path(known_hosts).is_file()
roles = {key: profile.get(key) for key in ('frontend', 'backend', 'database', 'redis', 'minio')}
source = 'environment='+repr(environment)+'\nexpected_host='+repr(expected[environment])+'\nregistered_roles='+repr(roles)+'\n'
supplement = len(sys.argv) > 2 and sys.argv[2] == 'supplement'
monitoring = len(sys.argv) > 2 and sys.argv[2] == 'monitoring'
source += (task/('remote_monitoring.py' if monitoring else 'remote_supplement.py' if supplement else 'remote_probe.py')).read_text(encoding='utf-8')
encoded = base64.b64encode(source.encode('utf-8'))
stdin = b"import base64\nexec(compile(base64.b64decode('"+encoded+b"'),'<readonly-feasibility>','exec'))\n"
options = ['-F', 'NUL', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'ConnectTimeout=10', '-i', identity, '-o', 'IdentitiesOnly=yes',
           '-o', 'UserKnownHostsFile='+known_hosts]
p = subprocess.run(['ssh', *options, 'root@'+expected[environment], profile['python']+' -'],
                   input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
if p.returncode:
    print(json.dumps({'environment': environment, 'status': 'FAILED', 'exitCode': p.returncode,
                      'error': p.stderr.decode('utf-8', 'replace')[-1500:]}))
    raise SystemExit(1)
report = json.loads(p.stdout.decode('utf-8'))
assert report['host'] == expected[environment] and report['environment'] == environment
(task/(environment+('-monitoring-evidence.json' if monitoring else '-supplement-evidence.json' if supplement else '-readonly-evidence.json'))).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'environment': environment, 'observedAtUtc': report['observedAtUtc'], 'supplement': supplement,
                  'status': 'COLLECTED', 'evidenceSaved': True}, ensure_ascii=False))
