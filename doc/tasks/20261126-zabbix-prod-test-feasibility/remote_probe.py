"""Read-only metadata probe, executed via stdin; no remote files are written."""
import datetime
import grp
import json
import os
import platform
import pwd
import shutil
import socket
import stat
import subprocess
import urllib.request

results = {}
os.environ['LC_ALL'] = 'C'

def query(key, args, timeout=12):
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        item = {'exitCode': p.returncode, 'stdout': p.stdout.decode('utf-8').strip()}
        if p.returncode:
            item['stderr'] = p.stderr.decode('utf-8', 'replace')[:700]
    except Exception as e:
        item = {'errorType': type(e).__name__}
    results[key] = item
    return item

os_info = {}
with open('/etc/os-release', encoding='utf-8') as stream:
    for line in stream:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            if k in ('ID', 'ID_LIKE', 'VERSION_ID', 'PRETTY_NAME', 'NAME', 'VERSION'):
                os_info[k] = v.strip('"')
with open('/proc/meminfo', encoding='ascii') as stream:
    memory = {k: int(v.split()[0]) for k, v in (line.split(':', 1) for line in stream)
              if k in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree')}
query('kernel', ['uname', '-r'])
query('glibc', ['getconf', 'GNU_LIBC_VERSION'])
query('virtualization', ['systemd-detect-virt'])
query('localFilesystems', ['df', '-PT', '-l'])
query('localInodes', ['df', '-Pi', '-l'])
query('listeners', ['ss', '-lnt'])
query('routes', ['ip', '-4', 'route', 'show'])
query('selinux', ['getenforce'])
query('firewalldState', ['firewall-cmd', '--state'])
query('firewalldActiveZones', ['firewall-cmd', '--get-active-zones'])
query('firewalldDefault', ['firewall-cmd', '--list-all'])
query('zabbixPackages', ['rpm', '-q', 'zabbix-agent', 'zabbix-agent2', 'zabbix-server-mysql', 'zabbix-proxy-sqlite3'])
query('units', ['systemctl', 'list-unit-files', '--no-pager', '--no-legend', 'zabbix*', 'intruoyi-service-recovery*'])
query('recoveryUnit', ['systemctl', 'show', 'intruoyi-service-recovery@'+environment+'.service',
                      '--property=LoadState,ActiveState,SubState,UnitFileState,MainPID'])
query('clock', ['timedatectl', 'show', '--property=NTPSynchronized,Timezone'])
query('dockerVersion', ['docker', 'version', '--format', '{{json .Server}}'])
query('dockerInfo', ['docker', 'info', '--format',
      '{"serverVersion":"{{.ServerVersion}}","root":"{{.DockerRootDir}}","driver":"{{.Driver}}","cgroupDriver":"{{.CgroupDriver}}","running":{{.ContainersRunning}},"stopped":{{.ContainersStopped}},"images":{{.Images}}}'])
ids = query('containerIds', ['docker', 'ps', '-aq'])
containers = []
if ids.get('exitCode') == 0 and ids.get('stdout'):
    p = subprocess.run(['docker', 'inspect']+ids['stdout'].split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    results['containerInspect'] = {'exitCode': p.returncode}
    if p.returncode == 0:
        for c in json.loads(p.stdout.decode('utf-8')):
            s, h = c['State'], c['HostConfig']
            containers.append({'name': c['Name'].lstrip('/'), 'image': c['Config']['Image'],
                'running': s['Running'], 'status': s['Status'], 'health': (s.get('Health') or {}).get('Status'),
                'healthcheckConfigured': bool(c['Config'].get('Healthcheck')),
                'restartPolicy': h['RestartPolicy']['Name'], 'restartCount': c['RestartCount'],
                'oomKilled': s['OOMKilled'], 'memoryLimitBytes': h.get('Memory'),
                'networkMode': h.get('NetworkMode'), 'ports': c['NetworkSettings'].get('Ports'),
                'dataMounts': [{'type': m['Type'], 'destination': m['Destination'], 'readWrite': m.get('RW')}
                               for m in c.get('Mounts', []) if m['Destination'] in ('/var/lib/mysql', '/data', '/var/run/docker.sock')]})
results.pop('containerIds', None)
query('dockerStats', ['docker', 'stats', '--no-stream', '--format', '{{json .}}'], timeout=20)
socket_info = {'exists': os.path.exists('/var/run/docker.sock')}
if socket_info['exists']:
    s = os.stat('/var/run/docker.sock')
    socket_info.update(mode=oct(stat.S_IMODE(s.st_mode)), owner=pwd.getpwuid(s.st_uid).pw_name,
                       group=grp.getgrgid(s.st_gid).gr_name)
http = {}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for role, url in [('frontend', 'http://127.0.0.1:8081/'), ('backend', 'http://127.0.0.1:48081/actuator/health')]:
    try:
        with opener.open(url, timeout=8) as response:
            data = response.read(16384)
            http[role] = {'httpStatus': response.status}
            if role == 'backend':
                http[role]['status'] = json.loads(data.decode('utf-8')).get('status')
    except Exception as e:
        http[role] = {'errorType': type(e).__name__}
report = {'schemaVersion': 'ZabbixFeasibilityReadOnly/v1', 'environment': environment,
    'host': expected_host, 'observedAtUtc': datetime.datetime.utcnow().isoformat()+'Z',
    'os': os_info, 'architecture': platform.machine(), 'cpuCount': os.cpu_count(),
    'loadAverage': os.getloadavg(), 'memoryKiB': memory,
    'probePython': platform.python_version(), 'python312Path': shutil.which('python3.12'),
    'registeredRoles': registered_roles, 'containers': containers,
    'dockerSocket': socket_info, 'http': http,
    'recoveryEntryExists': os.path.isfile('/opt/intruoyi-maintenance/ops/spug/release-center/service_recovery.py'),
    'recoveryConfigDirectoryExists': os.path.isdir('/etc/intruoyi-service-recovery'), 'commands': results}
print(json.dumps(report, ensure_ascii=True))
