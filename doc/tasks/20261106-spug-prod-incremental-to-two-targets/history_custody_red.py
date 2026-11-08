"""Expose the exact active-receipt assumption using actual retained metadata."""
import hashlib,json,subprocess,sys
from common import TASK,PRIVATE,remote,write,now

destination=TASK/'history-receipt-custody-red.json'
assert not destination.exists()
original=TASK/'verify_protected_history_before_custody.py'
assert not original.exists()
original.write_bytes((TASK/'verify_protected_history.py').read_bytes())
command=[sys.executable,'-X','utf8',str(original),'58','--verify']
result=subprocess.run(command,capture_output=True,timeout=150)
raw=result.stdout+result.stderr
private=PRIVATE/'history-receipt-custody-red.original.log'
assert not private.exists();private.write_bytes(raw)
assert result.returncode!=0,'RED_DID_NOT_EXPOSE_UNCHANGED_PATH_ASSUMPTION'
pins=json.loads((TASK/'protected-history-58.json').read_text(encoding='utf8'))['evidencePins']
script=r'''
import hashlib,json,pathlib,datetime
changed=[]
for ref in PINS:
 p=pathlib.Path(ref['path']);raw=p.read_bytes()
 if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:changed.append(ref['path'])
assert changed==['/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/target-installation.json'],'UNEXPECTED_OTHER_ORIGINAL_HISTORY_CHANGE'
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),originalFilesRead=len(PINS),changedPaths=changed,allOtherOriginalPathsMatch=True,serverWrites=False)))
'''
observed=remote('172.30.30.58','PINS='+repr(pins)+'\n'+script,90)
report=dict(status='EXPECTED_FAIL',observedAt=now(),actualExitCode=result.returncode,
 command=command,rawOutputBytes=len(raw),rawOutputSha256=hashlib.sha256(raw).hexdigest(),
 reason='AUTHORIZED_ACTIVE_INSTALLATION_RECEIPT_REPLACED',actualOriginalHistoryAudit=observed)
write(destination,report);print(json.dumps(report))
