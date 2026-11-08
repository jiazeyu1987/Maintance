"""Read-only exact-container catalogue diagnosis; originals remain private."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from common import PRIVATE, TASK, now, write

CONTAINER = 'f615a60c76f46e4f6ae20ea6298f737fb9786684ce941fcc15763654461265bf'


def capture(name, args, timeout=35, data=None):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    (PRIVATE / ('catalogue-504-' + name + '.private.stdout')).write_bytes(result.stdout)
    (PRIVATE / ('catalogue-504-' + name + '.private.stderr')).write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError('READONLY_CAPTURE_FAILED_' + name + '_' + str(result.returncode))
    return result.stdout


def main():
    inspection = json.loads(capture('container', ['docker', 'inspect', CONTAINER]))[0]
    assert inspection['Id'] == CONTAINER
    assert inspection['NetworkSettings']['Ports']['80/tcp'] == [{'HostIp': '127.0.0.1', 'HostPort': '18080'}]
    nginx = capture('nginx-current', ['docker', 'exec', CONTAINER, 'nginx', '-T']).decode('utf-8')
    lines = [line for line in nginx.splitlines() if re.search(r'location|proxy_pass|proxy_.*timeout|access_log|error_log|listen |include /opt', line)]
    proc_script = '''import json, os
from pathlib import Path
rows=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=path.read_bytes().decode().split('\\0')
  if not any(x.endswith('spug_bridge.py') for x in args): continue
  env=dict(x.split('=',1) for x in (path.parent/'environ').read_bytes().decode().split('\\0') if '=' in x)
  config=json.loads(Path(env['RELEASE_BRIDGE_CONFIG']).read_text())
  rows.append(dict(pid=int(path.parent.name),argv=args,config=config,configPath=env['RELEASE_BRIDGE_CONFIG']))
 except (FileNotFoundError,PermissionError): pass
print(json.dumps(rows))
'''
    rows = json.loads(capture('bridge-process', ['docker', 'exec', '-i', CONTAINER, 'python3', '-B', '-'], data=proc_script.encode()))
    safe_procs = []
    for row in rows:
        safe_procs.append({'pid': row['pid'], 'configPath': row['configPath'], 'applications': [
            {key: app.get(key) for key in ('id', 'status', 'executorUrl')} for app in row['config']['applications']]})
    error_script = '''from pathlib import Path
p=Path('/var/log/nginx/error.log')
with p.open('rb') as f:
 f.seek(max(0,p.stat().st_size-4000000))
 data=f.read()
import sys
sys.stdout.buffer.write(data)
'''
    errors = capture('nginx-errors', ['docker', 'exec', '-i', CONTAINER, 'python3', '-B', '-'], data=error_script.encode())
    safe_errors = []
    for line in errors.decode('utf-8', errors='replace').splitlines():
        if '/package-catalog' not in line:
            continue
        match = re.search(r'^(\S+ \S+).*?(upstream timed out|connect\(\) failed|upstream prematurely closed connection).*?upstream: "([^"]+)"', line)
        if match:
            safe_errors.append({'at': match[1], 'reason': match[2], 'upstream': match[3]})
    powershell = "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'executor' } | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"
    host_processes = json.loads(capture('host-executor-process', ['powershell', '-NoProfile', '-Command', powershell]))
    if isinstance(host_processes, dict):
        host_processes = [host_processes]
    safe_host = []
    for row in host_processes or []:
        cmd = row['CommandLine']
        scripts = re.findall(r'[^\s"]*executor\.py', cmd)
        configs = re.findall(r'--config\s+(?:"([^"]+)"|(\S+))', cmd)
        safe_host.append({'pid': row['ProcessId'], 'scripts': scripts, 'configPaths': [a or b for a, b in configs]})
    report = dict(observedAt=now(), container=CONTAINER, ports=inspection['NetworkSettings']['Ports'],
                  nginxRoutes=lines, bridgeProcesses=safe_procs, hostExecutors=safe_host,
                  catalogueTimeoutCountInLast4MB=len(safe_errors), catalogueErrors=safe_errors[-20:],
                  writes=0, productOrConfigurationChanges=0)
    write(TASK / 'catalogue-504-runtime-route.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
