"""Create concise evidence from immutable read-only snapshots; no server access."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
summary = {'scope': 'Read-only feasibility assessment; no installation or fault injection', 'hosts': {}}
for env in ('prod', 'test'):
    p = root/(env+'-readonly-evidence.json')
    r = json.loads(p.read_text(encoding='utf-8'))
    s = json.loads((root/(env+'-supplement-evidence.json')).read_text(encoding='utf-8'))
    stats = {item['Name']: item for item in (json.loads(line) for line in r['commands']['dockerStats']['stdout'].splitlines())}
    filesystems = []
    for line in r['commands']['localFilesystems']['stdout'].splitlines()[1:]:
        cols = line.split()
        if len(cols) == 7 and cols[-1] in ('/', '/var/lib/docker'):
            filesystems.append({'device': cols[0], 'type': cols[1], 'totalKiB': int(cols[2]),
                'usedKiB': int(cols[3]), 'availableKiB': int(cols[4]), 'usedPercent': cols[5], 'mount': cols[6]})
    selected = {role: next((c for c in r['containers'] if c['name'] == name), None)
                for role, name in r['registeredRoles'].items()}
    summary['hosts'][env] = {
        'observedAtUtc': r['observedAtUtc'], 'supplementObservedAtUtc': s['observedAtUtc'],
        'host': r['host'], 'os': r['os'], 'architecture': r['architecture'], 'cpuCount': r['cpuCount'],
        'virtualization': r['commands']['virtualization'], 'kernel': r['commands']['kernel'],
        'glibc': r['commands']['glibc'], 'memoryKiB': r['memoryKiB'], 'loadAverage': r['loadAverage'],
        'docker': json.loads(r['commands']['dockerInfo']['stdout']), 'filesystems': filesystems,
        'registeredContainers': selected, 'registeredStats': {role: stats.get(name) for role, name in r['registeredRoles'].items()},
        'dockerSocket': r['dockerSocket'], 'selinux': r['commands']['selinux'],
        'http': s['registeredHostHttp'], 'initialLoopbackHttp': r['http'],
        'zabbixPackages': s['commands']['zabbixPackages'], 'clock': s['commands']['clock'],
        'firewall': {key: value for key, value in s['commands'].items() if key in ('inputRules','outputRules','dockerUserRules','ipv6InputRules','nftTables')},
        'firewalld': r['commands']['firewalldState'], 'recoveryUnit': r['commands']['recoveryUnit'],
        'python': r['probePython'], 'python312OnPath': r['python312Path'],
        'rawSnapshotSha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        'notes': ['Initial rpm locale output was not valid UTF-8 and is not used; LC_ALL=C supplement is authoritative.',
                  'Initial combined timedatectl property returned empty text; separate property supplement is authoritative.',
                  'Single resource sample does not establish peak load or storage growth.',
                  'Host firewall observations do not establish upstream ACL, external reachability, or all nft/mangle effects.']}
summary['existingMonitoringOnTest'] = json.loads((root/'test-monitoring-evidence.json').read_text(encoding='utf-8'))
summary['existingMonitoringOnTest']['additionalProbe'] = {'origin': 'maintenance workstation',
    'url': 'http://172.30.30.58:19090/api/v1/status/buildinfo', 'httpStatus': 400,
    'meaning': 'Version, targets, rules and alert routing remain unverified; no bypass or configuration changes attempted.'}
target = root/'environment-summary.json'
target.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
assert '\ufffd' not in target.read_text(encoding='utf-8')
print('PASS: concise evidence saved without replacement characters')
