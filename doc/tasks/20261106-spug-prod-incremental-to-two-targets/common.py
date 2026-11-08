"""Task-local UTF-8 evidence and bounded pinned SSH transport."""
import datetime
import hashlib
import json
import re
from pathlib import Path
import subprocess

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106')
SOURCE = 'intruoyi-57-safe-20261024-v1'
SSH = ['C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL', '-o', 'BatchMode=yes',
       '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-i',
       'C:/SpugHandoff/release/private/sshIdentityFile', '-o',
       'UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile',
       '-o', 'ConnectTimeout=10']


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def restore_kind(suffix):
    assert suffix in ('58', '59'), 'EXPLICIT_RESTORE_TARGET_REQUIRED'
    value = json.loads((TASK / 'restore-selected-attempts.json').read_text(encoding='utf8'))
    assert value['schemaVersion'] == 'TaskRestoreAttempts/v1' and set(value['targets']) == {'58', '59'}
    kind = value['targets'][suffix]['kind']
    assert type(kind) is str and re.fullmatch('restore-' + suffix + r'(?:-r(?:[2-9]|[1-9][0-9]+))?', kind), \
        'EXPLICIT_RESTORE_ATTEMPT_INVALID'
    return kind


def active_source_installation():
    for name in ('source-control-binlog-temp-installation.json',
                 'source-control-parent-installation.json', 'source-control-installation.json'):
        path = TASK / name
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8'))
            assert value['status'] == 'PASS', 'SOURCE_INSTALLATION_NOT_VERIFIED'
            return value
    raise FileNotFoundError('VERIFIED_SOURCE_INSTALLATION_REQUIRED')


def allocator_installation(suffix):
    assert suffix in ('58', '59')
    selected = json.loads((TASK / 'allocator-selected-installations.json').read_text(encoding='utf8'))
    assert selected['schemaVersion'] == 'TaskAllocatorInstallations/v1'
    name = selected['targets'][suffix]
    assert re.fullmatch(r'(?:allocator-target-installation-' + suffix + r'(?:-r[23])?|(?:packaged-)?frontend-target-installation-' + suffix + r')\.json', name)
    value = json.loads((TASK / name).read_text(encoding='utf8'))
    assert value['status'] == 'PASS' and value['host'] == '172.30.30.' + suffix
    return value


def allocator_contract_name(suffix):
    selected = json.loads((TASK / 'allocator-selected-installations.json').read_text(encoding='utf8'))
    assert suffix in ('58','59') and selected['schemaVersion']=='TaskAllocatorInstallations/v1'
    name=selected['contracts'][suffix]
    assert re.fullmatch(r'(?:target-allocator-contract-'+suffix+r'(?:-r3)?|target-(?:packaged-)?frontend-contract-'+suffix+r')\.json',name)
    return name


def restore_clearance(suffix):
    assert suffix=='58'
    selected=json.loads((TASK/'restore-selected-clearances.json').read_text(encoding='utf8'))
    assert selected['schemaVersion']=='TaskRestoreClearances/v1'
    name=selected['targets'][suffix]
    assert name in ('frontend-retained-recovery-clearance-58.json','packaged-frontend-retained-recovery-clearance-58.json')
    value=json.loads((TASK/name).read_text(encoding='utf8'))
    assert value['status']=='PASS' and value['writersRemainStopped']
    return value


def write(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
    path.write_bytes(raw)
    assert path.read_bytes() == raw


def remote(host, script, timeout=120):
    profiles = json.loads(Path('C:/Spug/runtime/private/runtime-versions.private.json').read_text(encoding='utf-8'))['profiles']
    python = next(p['python'] for p in profiles if p['host'] == host)
    if host.endswith('.58'):
        python = '/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12'
    elif host.endswith('.57'):
        python = '/usr/local/libexec/spug-source-control-20261105/python/bin/python3.12'
    result = subprocess.run(SSH + ['root@' + host, python + ' -B -'],
                            input=script.encode('utf-8'), capture_output=True, timeout=timeout)
    if result.returncode:
        raw = result.stdout + result.stderr
        (PRIVATE / (host + '-error-' + hashlib.sha256(raw).hexdigest()[:12] + '.private.log')).write_bytes(raw)
        raise RuntimeError('REMOTE_READ_FAILED_' + host)
    return json.loads(result.stdout)
