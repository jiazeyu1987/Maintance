"""Locate scan matches without disclosing values or credential fingerprints."""
import json,subprocess,sys
from pathlib import Path
from common import TASK,PRIVATE,write
from verify_task_records import ROOT,secrets

known=set()
paths=[p for p in PRIVATE.glob('*.json') if p.stat().st_size<32*1024*1024]
paths += [Path('C:/SpugHandoff/release/private')/n for n in ('spug-login.private.json','loginCredentials.json')]
for path in paths:secrets(json.loads(path.read_text(encoding='utf-8-sig')),known)
name='docs/request-command-log.md';content=(ROOT/name).read_text(encoding='utf-8')
original=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT).decode('utf-8')
matches=[]
for number,line in enumerate(content.splitlines(),1):
 for value in known:
  if value not in line:continue
  matches.append(dict(line=number,valueLength=len(value),alreadyInCommittedBaseline=value in original,isRedactionPlaceholder=value in ('[REDACTED]','REDACTED','<REDACTED>','********'),isMediaType=value in ('application/json','application/octet-stream')))
write(PRIVATE/'records-scan-diagnosis.private.json',dict(file=name,matches=matches))
print(json.dumps(dict(file=name,matches=matches)))
for number in sorted({v['line'] for v in matches}):
 line=content.splitlines()[number-1]
 for value in sorted(known,key=len,reverse=True):line=line.replace(value,'[REDACTED]')
 print(json.dumps(dict(line=number,redactedContext=line),ensure_ascii=False))
if '--redact-historical-credential' in sys.argv:
 assert len(matches)==1 and matches[0]['alreadyInCommittedBaseline'] and matches[0]['valueLength']==6 and not matches[0]['isRedactionPlaceholder'] and not matches[0]['isMediaType']
 path=ROOT/name;before=path.read_bytes();lines=before.decode('utf-8').splitlines(keepends=True);number=matches[0]['line']
 old=lines[number-1];assert '用户继续提供账号' in old
 replacement=old
 for value in sorted(known,key=len,reverse=True):replacement=replacement.replace(value,'[REDACTED]')
 assert replacement!=old and before.count(old.encode('utf-8'))==1
 backup=PRIVATE/'request-command-log-before-redaction.private.md'
 with backup.open('xb') as stream:stream.write(before)
 lines[number-1]=replacement;after=''.join(lines).encode('utf-8')
 assert after==before.replace(old.encode('utf-8'),replacement.encode('utf-8'))
 path.write_bytes(after);assert path.read_bytes()==after
 write(TASK/'historical-credential-redaction.json',dict(status='PASS',file=name,line=number,existingHistoricalCredentialRedacted=True,otherBytesAndLineEndingsPreserved=True,plaintextOrCredentialFingerprintPublished=False))
 print('ONE_EXISTING_HISTORICAL_CREDENTIAL_REDACTED_OTHER_BYTES_PRESERVED')
