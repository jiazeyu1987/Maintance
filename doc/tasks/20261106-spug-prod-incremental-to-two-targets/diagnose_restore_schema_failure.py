"""Retain bounded original failure documents without changing the stopped target."""
import json

from common import PRIVATE, TASK, remote, write

SCRIPT = r'''
import datetime,hashlib,json,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
operation='smallapp-c21bb7ce9f5b4668b850c37a80964786'
op=root/'recovery-operations'/operation
paths=[op/'result.json',op/'worker-result.json',*(root/'ledger'/operation).glob('*.json'),*(op/'database-001').glob('*.json')]
documents={};pins=[]
for path in paths:
 if not path.is_file():continue
 raw=path.read_bytes();assert len(raw)<8*1024*1024
 documents[str(path)]=json.loads(raw)
 pins.append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
directories=[]
for folder in (op,op/'database-001',op/'database-001/database-readback'):
 directories.append(dict(path=str(folder),entries=[dict(name=p.name,directory=p.is_dir(),bytes=p.stat().st_size) for p in sorted(folder.iterdir())][:100]))
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,documents=documents,pins=pins,directories=directories)))
'''

if __name__ == '__main__':
    value = remote('172.30.30.58', SCRIPT, 45)
    write(PRIVATE / 'restore-368-failure-documents.private.json', value)
    documents = []
    for path, document in value['documents'].items():
        documents.append(dict(path=path, fields=sorted(document),
                              dataKeys=sorted(document.get('data') or {}),
                              **{k: v for k, v in document.items() if k in ('state', 'actualExitCode', 'failureCode', 'finishedAt')}))
    report = dict(observedAt=value['observedAt'], operationId=value['operationId'], documents=documents,
                  pins=value['pins'], directories=value['directories'], anyTargetMutation=False)
    write(TASK / 'restore-368-failure.json', report)
    print(json.dumps(dict(observedAt=report['observedAt'], documents=documents,
                         directories=report['directories'][:2])))
