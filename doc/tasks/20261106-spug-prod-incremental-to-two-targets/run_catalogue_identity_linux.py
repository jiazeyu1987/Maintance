"""Independent network-none Linux HTTP regression, exact read-only snapshot."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from common import TASK, PRIVATE, now, write

IMAGE = 'sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735'
NAME = 'spug-catalogue-identity-tests-20261108-v1'
SOURCE = TASK.parents[2] / 'ops/spug/release-center'
FILES = ['executor.py', 'state_store.py', 'release_order.py', 'application_registry.py',
         'release_http.py', 'package_catalog.py', 'package_presence.py', 'nas_connection.py',
         'test_release_identity.py', 'test_applications.py', 'test_commit_catalog.py']


def main():
    inspected = subprocess.run(['docker', 'image', 'inspect', IMAGE], capture_output=True, check=True)
    (PRIVATE/'catalogue-identity-linux-image.private.json').write_bytes(inspected.stdout)
    assert json.loads(inspected.stdout)[0]['Id'] == IMAGE
    assert subprocess.run(['docker', 'inspect', NAME], capture_output=True).returncode != 0
    snapshot = PRIVATE / 'catalogue-identity-linux-snapshot-v1'
    snapshot.mkdir(exist_ok=False)
    pins = {}
    for name in FILES:
        raw = (SOURCE/name).read_bytes()
        (snapshot/name).write_bytes(raw)
        pins[name] = hashlib.sha256(raw).hexdigest()
    write(snapshot/'input-manifest.json', pins)
    script = '''import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path('/src')
pins=json.loads((root/'input-manifest.json').read_text())
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in pins.items())
assert sys.version_info>=(3,10)
print('PREFLIGHT_PYTHON '+sys.version.split()[0],flush=True)
print('PREFLIGHT_GIT '+subprocess.check_output(['git','--version']).decode().strip(),flush=True)
result=subprocess.run([sys.executable,'-B','-m','unittest','-v','test_release_identity','test_applications','test_commit_catalog'])
assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==sha for name,sha in pins.items())
raise SystemExit(result.returncode)
'''
    command = ['docker', 'run', '--rm', '-i', '--name', NAME,
               '--label', 'codex.task=20261106-spug-prod-incremental-to-two-targets',
               '--network', 'none', '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m',
               '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
               '--memory', '512m', '--cpus', '1', '--pids-limit', '128',
               '--mount', 'type=bind,source='+str(snapshot)+',target=/src,readonly',
               '--workdir', '/src', '--env', 'PYTHONDONTWRITEBYTECODE=1', IMAGE, 'python', '-B', '-']
    result = subprocess.run(command, input=script.encode(), capture_output=True, timeout=90)
    raw = result.stdout + result.stderr
    (PRIVATE/'catalogue-identity-linux.private.log').write_bytes(raw)
    absent = subprocess.run(['docker', 'inspect', NAME], capture_output=True).returncode != 0
    report = dict(observedAt=now(), image=IMAGE, containerName=NAME, exitCode=result.returncode,
                  containerRemoved=absent, network='none', readOnlyBind=True, sourcePins=pins,
                  sourceUnchanged=all(hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()==sha for name,sha in pins.items()),
                  testSummary=[line for line in raw.decode().splitlines() if line.startswith(('PREFLIGHT_', 'Ran ', 'OK', 'FAILED'))],
                  outputSha256=hashlib.sha256(raw).hexdigest(), productionOperations=0)
    write(TASK/'catalogue-identity-linux.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if result.returncode:
        print(raw.decode())
    assert result.returncode == 0 and absent and report['sourceUnchanged']


if __name__ == '__main__':
    main()
