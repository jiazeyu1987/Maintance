"""Read-only public progress projection. No raw worker output or credential fields."""
import datetime
import hashlib
import json
from pathlib import Path
import re


def project(root, request):
    root = Path(root)
    operation = request['operationId']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}', operation):
        raise ValueError('PROGRESS_OPERATION_INVALID')
    restore = request['action'] == 'RESTORE'
    directory = root / ('recovery-operations' if restore else 'repository-operations') / (
        operation if restore else hashlib.sha256(operation.encode()).hexdigest())
    recorded = json.loads((directory / 'request.json').read_bytes())
    if recorded != request:
        raise ValueError('PROGRESS_REQUEST_MISMATCH')
    result_path = directory / 'result.json'
    result = json.loads(result_path.read_bytes()) if result_path.is_file() else {}
    terminal = result.get('state') in ('SUCCEEDED', 'FAILED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN')
    steps = []
    timing_paths = list(directory.glob('timing-*-start.json')) + list(directory.glob('*/timing-*-start.json'))
    for path in sorted(timing_paths):
        start = json.loads(path.read_bytes())
        end_path = path.with_name(path.name.replace('-start.json', '-end.json'))
        end = json.loads(end_path.read_bytes()) if end_path.is_file() else {}
        steps.append(dict(name=(path.parent.name + '/' if path.parent != directory else '') + start['stage'], startedAt=start['startedAt'],
                          finishedAt=end.get('finishedAt'), elapsedSeconds=end.get('elapsedSeconds'),
                          state=('SUCCEEDED' if end['completed'] else 'FAILED') if 'completed' in end else
                          ('UNCONFIRMED' if terminal else 'RUNNING')))
    # Event content is an explicit symbol whitelist; never return arbitrary diagnostic data.
    events = []
    event_paths = list(directory.glob('event-*.json'))
    if not restore:
        event_paths += list((root / 'capture-staging' / operation).glob('event-*.json'))
    for path in sorted(event_paths):
        value = json.loads(path.read_bytes())
        stage = value.get('stage')
        if isinstance(stage, str) and re.fullmatch('[A-Z0-9_:-]{1,128}', stage):
            events.append(dict(at=value.get('at'), stage=stage))
    steps.sort(key=lambda step: step['startedAt'])
    events.sort(key=lambda event: event['at'] or '')
    return dict(operationId=operation, observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                state=result.get('state', 'RUNNING'), startedAt=result.get('startedAt'),
                finishedAt=result.get('finishedAt'), steps=steps, events=events,
                percentage=None, percentageAvailable=False)


if __name__ == '__main__':
    import sys
    value = json.load(sys.stdin)
    print(json.dumps(project(value['root'], value['request'])))
