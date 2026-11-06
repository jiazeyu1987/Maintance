"""Await the existing UI observer, then run only original-operation read-only gates."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

TASK = Path(__file__).resolve().parent
PRIVATE = Path('C:/Spug/runtime/private/full-to-prod-20261105')
OPERATION = 'smallapp-7fec29a3e132463096aec915c08acab3'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(name):
    return json.loads((TASK/name).read_text(encoding='utf-8'))


if __name__ == '__main__':
    assert read('full-ui-submission.json')['request']['operationId'] == OPERATION
    assert not (TASK/'preservation-acceptance.json').exists(), 'ACCEPTANCE_ALREADY_RECORDED'
    started = now()
    print(json.dumps(dict(state='WAITING_FOR_ORIGINAL_TERMINAL',operationId=OPERATION,pid=os.getpid(),startedAt=started)),flush=True)
    deadline = time.monotonic()+10800
    terminal_path = TASK/'full-terminal-record.json'
    while not terminal_path.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError('OBSERVER_WAIT_WINDOW_ENDED_FOLLOW_ORIGINAL_OPERATION')
        time.sleep(10)
    terminal = read('full-terminal-record.json')
    assert terminal['request']['operationId'] == OPERATION, 'ORIGINAL_OPERATION_MISMATCH'
    assert terminal['result']['state'] == 'SUCCEEDED', 'ORIGINAL_BACKUP_NOT_SUCCEEDED'
    completed = []
    for helper in ('verify_preservation_point.py','verify_preservation_payload.py','verify_preservation_admission.py','verify_preserved_source_runtime.py'):
        print(json.dumps(dict(state='READ_ONLY_ACCEPTANCE',helper=helper,observedAt=now())),flush=True)
        process = subprocess.run([sys.executable,'-X','utf8',str(TASK/helper)],capture_output=True,timeout=240)
        (PRIVATE/(helper+'.acceptance.private.log')).write_bytes(process.stdout+process.stderr)
        assert process.returncode == 0, 'READ_ONLY_ACCEPTANCE_FAILED_SEE_PRIVATE_LOG: '+helper
        completed.append(helper)
    point = read('preservation-full-point-verified.json')
    payload = read('preservation-full-payload-readback.json')
    admission = read('preservation-full-admission.json')
    runtime = read('preserved-source-runtime.json')
    assert point['operationId'] == payload['operationId'] == OPERATION
    assert point['state'] == 'SUCCEEDED' and payload['status'] == runtime['status'] == 'PASS'
    assert payload['manifestPin'] == point['manifestPin'] and payload['pointPin'] == point['pointPin']
    assert admission['newRecoveryPointRef'] == OPERATION and admission['newPointAdmitted']
    report = dict(status='PASS',operationId=OPERATION,startedAt=started,finishedAt=now(),completedHelpers=completed,
                  onlyReadOnlyChecks=True,restoreDispatched=False,controlInstalled=False,businessUiAcceptanceStillRequired=True)
    with (TASK/'preservation-acceptance.json').open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
