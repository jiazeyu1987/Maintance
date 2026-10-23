"""Persist actual step boundaries without interpreting their business result."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time


def _stamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def _write(path, value):
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def step(root, name):
    if not re.fullmatch('[a-z][a-z0-9-]{0,63}', name):
        raise ValueError('STEP_TIMING_NAME_INVALID')
    root = Path(root)
    started = time.monotonic()
    _write(root / ('timing-' + name + '-start.json'), dict(stage=name, startedAt=_stamp()))
    completed = False
    try:
        yield
        completed = True
    finally:
        _write(root / ('timing-' + name + '-end.json'), dict(
            stage=name, finishedAt=_stamp(), elapsedSeconds=round(time.monotonic() - started, 3),
            completed=completed))
