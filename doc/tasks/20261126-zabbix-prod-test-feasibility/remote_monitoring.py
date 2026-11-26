"""Inspect existing monitoring ownership and public status fields, without config contents."""
import datetime
import json
import os
import urllib.parse
import urllib.request

processes = []
for name in os.listdir('/proc'):
    if not name.isdigit():
        continue
    try:
        with open('/proc/'+name+'/comm', encoding='ascii') as stream:
            comm = stream.read().strip()
        if comm not in ('prometheus', 'node_exporter', 'alertmanager', 'zabbix_agent2', 'zabbix_agentd'):
            continue
        with open('/proc/'+name+'/cmdline', 'rb') as stream:
            args = stream.read(32768).decode('utf-8').split('\x00')
        selected = {}
        for i, arg in enumerate(args):
            for key in ('--web.listen-address', '--config.file', '--storage.tsdb.path', '--storage.tsdb.retention.time'):
                if arg.startswith(key+'='):
                    selected[key] = arg.split('=', 1)[1]
                elif arg == key and i+1 < len(args):
                    selected[key] = args[i+1]
        processes.append({'pid': int(name), 'comm': comm, 'executable': os.readlink('/proc/'+name+'/exe'), 'selectedFlags': selected})
    except (FileNotFoundError, ProcessLookupError):
        continue
api = {}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for proc in processes:
    if proc['comm'] != 'prometheus':
        continue
    address = proc['selectedFlags'].get('--web.listen-address')
    if address != expected_host+':19090':
        api['endpoint'] = {'status': 'NOT_QUERIED', 'reason': 'Explicit registered host/listener required'}
        continue
    root = 'http://'+address
    for kind, path in [('build', '/api/v1/status/buildinfo'), ('targets', '/api/v1/targets'),
                       ('alertmanagers', '/api/v1/alertmanagers'), ('rules', '/api/v1/rules')]:
        try:
            with opener.open(root+path, timeout=6) as response:
                raw = response.read(1024*1024+1)
                if len(raw) > 1024*1024:
                    raise ValueError('Status response size exceeded')
                body = json.loads(raw.decode('utf-8'))
            data = body['data']
            if kind == 'build':
                result = {k: data.get(k) for k in ('version', 'goVersion', 'buildDate')}
            elif kind == 'targets':
                result = {'activeCount': len(data.get('activeTargets', [])),
                    'targets': [{'job': t.get('labels', {}).get('job'), 'health': t.get('health'),
                                 'lastScrape': t.get('lastScrape')} for t in data.get('activeTargets', [])]}
            elif kind == 'alertmanagers':
                result = {'activeCount': len(data.get('activeAlertmanagers', [])),
                          'droppedCount': len(data.get('droppedAlertmanagers', []))}
            else:
                groups = data.get('groups', [])
                result = {'groupCount': len(groups), 'ruleCount': sum(len(g.get('rules', [])) for g in groups),
                          'alertRuleCount': sum(r.get('type') == 'alerting' for g in groups for r in g.get('rules', []))}
            api[kind] = {'status': body.get('status'), 'result': result}
        except Exception as e:
            api[kind] = {'errorType': type(e).__name__}
print(json.dumps({'environment': environment, 'host': expected_host,
    'observedAtUtc': datetime.datetime.utcnow().isoformat()+'Z', 'processes': processes, 'prometheusStatus': api}))
