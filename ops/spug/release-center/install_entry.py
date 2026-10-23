"""Add own nginx include and validate; never restart shared Spug."""
from pathlib import Path
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--bridge-config', required=True)
args = parser.parse_args()
if not Path(args.bridge_config).is_file() or any(c in args.bridge_config for c in '\n\r"%'):
    raise SystemExit('Private bridge config missing or path invalid')
path = Path('/etc/nginx/nginx.conf')
raw = path.read_text('utf-8')
include = '        include /opt/intruoyi-spug/release-center/locations.conf;\n'
if include not in raw:
    marker = '        location ^~ /api/ {'
    if raw.count(marker) != 1:
        raise SystemExit('Nginx route baseline conflict')
    backup = Path('/var/lib/intruoyi-spug/release-center-original-nginx.conf')
    if backup.exists():
        raise SystemExit('Prior install backup exists without own include; inspect conflict')
    backup.write_text(raw, 'utf-8')
    path.write_text(raw.replace(marker, include + marker), 'utf-8')
    checked = subprocess.run(['nginx', '-t'], capture_output=True)
    if checked.returncode:
        path.write_text(raw, 'utf-8')
        raise SystemExit('Nginx validation rejected; original config restored')
    subprocess.run(['nginx', '-s', 'reload'], check=True)
supervisor = Path('/etc/supervisord.conf')
current = supervisor.read_text('utf-8')
program = '''
[program:release-center-bridge]
command = python3 -B /opt/intruoyi-spug/release-center/spug_bridge.py
directory = /data/spug/spug_api
environment = RELEASE_BRIDGE_CONFIG="''' + args.bridge_config + '''"
autostart = true
autorestart = unexpected
startsecs = 2
stdout_logfile = /var/lib/intruoyi-spug/release-center-bridge.log
redirect_stderr = true
'''
if '[program:release-center-bridge]' not in current:
    supervisor.write_text(current + program, 'utf-8')
elif program not in current:
    raise SystemExit('Existing own supervisor program differs; inspect before changing')
print('Additive routing and own supervisor program installed; run supervisorctl reread and update release-center-bridge. Shared services not restarted.')
