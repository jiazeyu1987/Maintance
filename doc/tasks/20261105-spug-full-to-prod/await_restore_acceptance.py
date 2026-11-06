"""Wait for the existing real UI observer, then run read-only acceptance once.

Never dispatch, retry, repair, stop services, or remove any resource.
"""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

from install_prod_control import TASK, PRIVATE
from verify_task_records import NODE


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


if __name__=='__main__':
    request=json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']
    start=now()
    terminal=TASK/'restore-terminal-record.json'
    for cycle in range(1440):
        if terminal.exists():
            result=json.loads(terminal.read_text(encoding='utf-8'))
            assert result['request']==request,'ORIGINAL_OPERATION_MISMATCH'
            assert result['result']['state']=='SUCCEEDED','ORIGINAL_OPERATION_NOT_SUCCEEDED'
            break
        if cycle%4==0:print(json.dumps(dict(observedAt=now(),operationId=request['operationId'],state='WAITING_FOR_ORIGINAL_TERMINAL')),flush=True)
        time.sleep(15)
    else:raise SystemExit('OBSERVATION_WINDOW_EXCEEDED_KEEP_ORIGINAL_ID')
    checks=[]
    for name,args in [
        ('verify_restore_evidence.py',[]),
        ('verify_restored_runtime.py',[]),
        ('verify_protection_runtime.py',[]),
        ('verify_business_ui.cjs',['production-after-restore']),
        ('verify_other_business.py',['--phase','after-restore']),
        ('verify_local_control.py',['closeout']),
    ]:
        command=[NODE,str(TASK/name),*args] if name.endswith('.cjs') else [sys.executable,'-X','utf8','-B',str(TASK/name),*args]
        completed=subprocess.run(command,capture_output=True)
        (PRIVATE/('restore-acceptance-'+name+'.private.log')).write_bytes(completed.stdout+completed.stderr)
        checks.append(dict(check=name,actualExitCode=completed.returncode,finishedAt=now()))
        print(json.dumps(checks[-1]),flush=True)
        if completed.returncode:
            raise SystemExit('RESTORE_ACCEPTANCE_FAILED_SEE_PRIVATE_LOG: '+name)
    report=dict(status='PASS',startedAt=start,observedAt=now(),operationId=request['operationId'],checks=checks,
                restoreDispatched=False,resourcesCleaned=False,recordsCommitted=False)
    (TASK/'restore-acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)
