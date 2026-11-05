"""Preserve the terminated third UI attempt before a new genuine UI request."""
import hashlib
import json
from preflight import TASK

if __name__ == '__main__':
    operation='smallapp-a732505e94bc4863b568e2b2a8c17d57'
    assert json.loads((TASK/'restore-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']==operation
    names=('restore-ui-submission.json','restore-ui-result.json','restore-ui-confirm.png',
           'restore-ui-submitted.png','restore-terminal-record.json','restore-live-progress.json',
           'restore-native-progress.json','restore-ui-terminal.png')
    destination=(TASK/'restore-attempt-3').resolve()
    assert destination.parent==TASK.resolve() and not destination.exists()
    records=[]
    for name in names:
        source=(TASK/name).resolve()
        assert source.parent==TASK.resolve() and source.is_file()
        raw=source.read_bytes()
        records.append(dict(path='restore-attempt-3/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    destination.mkdir()
    for name,record in zip(names,records):
        (TASK/name).rename(destination/name)
        raw=(destination/name).read_bytes()
        assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256']
    report=dict(operationId=operation,state='FAILED',pins=records,remoteHistoryUnchanged=True)
    (TASK/'third-failed-attempt-preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='PASS',operationId=operation,preservedFileCount=len(records))))
