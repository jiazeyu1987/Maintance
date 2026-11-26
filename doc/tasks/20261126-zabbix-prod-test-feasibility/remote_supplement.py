"""Resolve precise read-only gaps from first snapshot; do not repeat broad inventory."""
import datetime
import json
import os
import subprocess
import urllib.request

os.environ['LC_ALL'] = 'C'
commands = {}
for key, args in [
    ('zabbixPackages', ['rpm', '-q', 'zabbix-agent', 'zabbix-agent2', 'zabbix-server-mysql', 'zabbix-proxy-sqlite3']),
    ('clock', ['timedatectl', 'show', '-p', 'NTPSynchronized', '-p', 'Timezone']),
    ('inputRules', ['iptables', '-S', 'INPUT']),
    ('outputRules', ['iptables', '-S', 'OUTPUT']),
    ('dockerUserRules', ['iptables', '-S', 'DOCKER-USER']),
    ('ipv6InputRules', ['ip6tables', '-S', 'INPUT']),
    ('nftTables', ['nft', 'list', 'tables']),
    ('monitorProcesses', ['ps', '-eo', 'comm='])]:
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
        text = p.stdout.decode('utf-8')
        if key == 'monitorProcesses':
            text = '\n'.join(line for line in text.splitlines() if any(x in line.lower() for x in ('zabbix', 'prometheus', 'grafana', 'exporter', 'alertmanager')))
        commands[key] = {'exitCode': p.returncode, 'stdout': text[:24000], 'stderr': p.stderr.decode('utf-8')[:700] if p.returncode else ''}
    except Exception as e:
        commands[key] = {'errorType': type(e).__name__}
http = {}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for role, path in [('frontend', ':8081/'), ('backend', ':48081/actuator/health')]:
    url = 'http://'+expected_host+path
    try:
        with opener.open(url, timeout=8) as response:
            body = response.read(16384)
            http[role] = {'url': url, 'httpStatus': response.status}
            if role == 'backend':
                http[role]['status'] = json.loads(body.decode('utf-8')).get('status')
    except Exception as e:
        http[role] = {'url': url, 'errorType': type(e).__name__}
print(json.dumps({'environment': environment, 'host': expected_host,
    'observedAtUtc': datetime.datetime.utcnow().isoformat()+'Z', 'commands': commands, 'registeredHostHttp': http}))
