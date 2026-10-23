"""Own local Spug entry routing/bootstrap only. No container/shared-service restart."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

STATE = Path('/var/lib/intruoyi-spug')
INCLUDE = '        include /opt/intruoyi-spug/smallapp-entry.locations.conf;\n'
PROGRAM = '''
[program:intruoyi-spug-backup-entry]
command = python3 -B /opt/intruoyi-spug/smallapp_entry.py
directory = /data/spug/spug_api
autostart = true
autorestart = unexpected
startsecs = 2
stdout_logfile = /var/lib/intruoyi-spug/smallapp-entry.log
redirect_stderr = true
'''


def install(bootstrap=False):
    STATE.mkdir(parents=True, exist_ok=True)
    nginx = Path('/etc/nginx/nginx.conf')
    raw = nginx.read_text(encoding='utf-8')
    backup = STATE / 'smallapp-entry.original-nginx.conf'
    if INCLUDE not in raw:
        marker = '        location ^~ /api/ {'
        if raw.count(marker) != 1 or (backup.exists() and backup.read_text(encoding='utf-8') != raw):
            raise SystemExit('OWN_NGINX_ROUTING_BASELINE_CONFLICT')
        if not backup.exists():
            backup.write_text(raw, encoding='utf-8')
        nginx.write_text(raw.replace(marker, INCLUDE + '\n' + marker), encoding='utf-8')
        checked = subprocess.run(['nginx', '-t'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if checked.returncode:
            nginx.write_text(raw, encoding='utf-8')
            raise SystemExit('OWN_NGINX_ROUTING_CONFIG_REJECTED')
        if not bootstrap:
            subprocess.run(['nginx', '-s', 'reload'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    supervisor = Path('/etc/supervisord.conf')
    current = supervisor.read_text(encoding='utf-8')
    if '[program:intruoyi-spug-backup-entry]' not in current:
        (STATE / 'smallapp-entry.original-supervisord.conf').write_text(current, encoding='utf-8')
        supervisor.write_text(current + PROGRAM, encoding='utf-8')
    elif PROGRAM not in current:
        raise SystemExit('OWN_ENTRY_BOOTSTRAP_CONFLICT')
    print(json.dumps(dict(nginxRoutingInstalled=True, nginxReloadedOnly=not bootstrap, sharedServiceRestarted=False,
            ownEntryNextNormalBootConfigured=True, ownEntryCurrentStartRequired=True,
            originalNginxSha256=hashlib.sha256(backup.read_bytes()).hexdigest())))


if __name__ == '__main__':
    if sys.argv[1:] not in ([], ['--bootstrap']):
        raise SystemExit('OWN_INSTALL_ARGUMENTS_INVALID')
    install(bootstrap=sys.argv[1:] == ['--bootstrap'])
