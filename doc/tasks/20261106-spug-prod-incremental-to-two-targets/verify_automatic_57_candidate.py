"""Read staged target contracts and original service readiness; no activation."""
import ast
import json
from common import TASK, PRIVATE, remote, write
from install_automatic_57 import SCRIPT

if __name__ == '__main__':
    tree = ast.parse(SCRIPT)
    probe = next(ast.literal_eval(statement.value) for statement in tree.body
                 if isinstance(statement, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'health_probe'
                         for target in statement.targets))
    variables = dict(PROBE=probe)
    script = '\n'.join(key + '=' + repr(value) for key, value in variables.items()) + r'''
import pathlib,json,subprocess,os,hashlib
p=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/configuration/control-automatic-3019c2e.json')
raw=p.read_bytes();pin=dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());c=json.loads(raw)
r=subprocess.run([c['pythonPin']['path'],'-B','-c',PROBE,json.dumps(pin),'intruoyi-57-safe-20261024-v1','intruoyi-main-57-safe-restore-20261105-v2'],capture_output=True,timeout=50,env=dict(os.environ,**c['environment']))
print(json.dumps(dict(exitCode=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode())))
'''
    result = remote('172.30.30.57', script, 60)
    write(PRIVATE / 'automatic-target-57-staged-semantic-health.private.json', result)
    if result['exitCode']:
        for line in result['stderr'].splitlines():
            if line.startswith(('Traceback', '  File', 'ValueError:', 'KeyError:', 'TypeError:', 'recovery_engine.RecoveryError:')):
                print(line)
        raise RuntimeError('CANDIDATE_HEALTH_OR_POLICY_FAILED')
    value = json.loads(result['stdout'])
    write(TASK / 'automatic-target-57-staged-semantic-health.json', value)
    print(json.dumps(value))
