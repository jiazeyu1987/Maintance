"""Remote receipts for one submitted operation. Never re-execute on reconnect."""
import hashlib
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone


def require(value, message):
    if not value:
        raise ValueError(message)


def process_identity(pid):
    # Linux proc start ticks distinguish PID reuse. Missing proc means exited;
    # unreadable proc is an error, not proof that a worker stopped.
    path = Path('/proc') / str(pid) / 'stat'
    try:
        raw = path.read_text()
    except FileNotFoundError:
        return None
    return raw[raw.rfind(')') + 2:].split()[19]


def location(profile, operation_id):
    require(re.fullmatch(r'OP-[a-f0-9]{20}', operation_id or ''), 'Invalid operation identity')
    root = Path(profile['stagingRoot'])
    require(root.is_absolute() and '..' not in root.parts, 'Explicit staging root required')
    return root / '.operations' / (operation_id + '.json')


def write(path, value):
    temporary = path.with_suffix('.new')
    with temporary.open('w', encoding='utf-8') as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, ensure_ascii=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def inspect(profile, operation_id, job_id):
    path = location(profile, operation_id)
    if not path.exists():
        return dict(operationId=operation_id, jobId=job_id, status='unknown', worker='unknown')
    value = json.loads(path.read_text('utf-8'))
    require(value['operationId'] == operation_id and value['jobId'] == job_id,
            'Remote receipt identity differs')
    value['worker'] = 'running' if process_identity(value['pid']) == value['processStart'] else 'stopped'
    return value


def execute(payload, dispatch):
    import fcntl
    operation_id = payload['operationId']
    path = location(payload['profile'], operation_id)
    require(re.fullmatch(r'JOB-[a-f0-9]{10}', payload.get('workflowJobId', '')), 'Workflow task required')
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    binding = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if path.exists():
            previous = json.loads(path.read_text('utf-8'))
            require(previous['binding'] == binding, 'Operation payload identity differs')
            # A read-only inspection, not another POST, decides what to do next.
            raise ValueError('Operation already recorded; inspect original task instead of replaying it')
        value = dict(operationId=operation_id, jobId=payload['workflowJobId'], action=payload['action'],
                     binding=binding, status='running', pid=os.getpid(), processStart=process_identity(os.getpid()),
                     startedAt=datetime.now(timezone.utc).isoformat())
        require(value['processStart'], 'Cannot record worker start identity')
        write(path, value)
        try:
            result = dispatch(payload)
        except Exception as error:
            value.update(status='failed', errorType=type(error).__name__, finishedAt=datetime.now(timezone.utc).isoformat())
            write(path, value)
            raise
        value.update(status='succeeded', result=result, finishedAt=datetime.now(timezone.utc).isoformat())
        write(path, value)
        return result
