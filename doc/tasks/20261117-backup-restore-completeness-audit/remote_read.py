"""Run this audit's read-only Python probes over the existing pinned SSH identity."""
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('host', choices=['57', '59'])
parser.add_argument('probe', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--batch', type=int)
parser.add_argument('--start', type=int)
parser.add_argument('--end', type=int)
parser.add_argument('--historical', action='store_true')
args = parser.parse_args()
python_path = {
    '57': '/usr/local/libexec/spug-source-control-20261105/python/bin/python3.12',
    '59': '/mnt/intruoyi-data/recovery-tools/python/bin/python3.12',
}[args.host]
command = [
    'C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL',
    '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
    '-o', 'IdentitiesOnly=yes', '-i', 'C:/SpugHandoff/release/private/sshIdentityFile',
    '-o', 'UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile',
    '-o', 'ConnectTimeout=8', 'root@172.30.30.' + args.host,
    python_path + ' -B -',
]
probe = args.probe.read_bytes()
if args.batch is not None:
    assert 0 <= args.batch < 5
    probe = ('AUDIT_BATCH = ' + str(args.batch) + '\n').encode() + probe
if args.start is not None:
    assert args.end is not None and 0 <= args.start < args.end <= 100000
    probe = ('AUDIT_START = ' + str(args.start) + '\nAUDIT_END = ' + str(args.end) + '\n').encode() + probe
if args.historical:
    probe = b'AUDIT_HISTORICAL = True\n' + probe
result = subprocess.run(command, input=probe, capture_output=True, timeout=65)
if result.returncode:
    raise RuntimeError('Read-only SSH probe failed, exit=' + str(result.returncode)
                       + ': ' + result.stderr.decode('utf-8', errors='replace')[-1200:])
document = json.loads(result.stdout.decode('utf-8'))
args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'host': args.host, 'output': str(args.output), 'bytes': args.output.stat().st_size,
                  'keys': list(document)}, ensure_ascii=False))
