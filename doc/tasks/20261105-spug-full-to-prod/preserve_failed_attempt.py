"""Preserve exact local History361 files before a separately cleared UI request."""
import datetime
import hashlib
import json
from pathlib import Path
from install_prod_control import TASK, PRIVATE, POINT, TARGET, remote

OPERATION='smallapp-181aec2e16c94e259f875c0e64eb863a'
NAMES=['restore-ui-submission.json','restore-ui-result.json','restore-terminal-record.json',
       'restore-live-progress.json','restore-native-progress.json','restore-ui-confirm.png',
       'restore-ui-submitted.png','restore-ui-terminal.png']

def read(name):
    return json.loads((TASK/name).read_text(encoding='utf-8'))

def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def fixed(path,parent):
    assert path.parent.resolve()==parent.resolve() and not path.is_symlink()
    assert path.is_file(),'ORIGINAL_FILE_MISSING'
    return pin(path)

def save(path,value):
    raw=json.dumps(value,indent=2).encode('utf-8')
    with path.open('xb') as stream:
        stream.write(raw);stream.flush()
        import os
        os.fsync(stream.fileno())
    assert path.read_bytes()==raw

def archive():
    clearance=read('retained-recovery-clearance.json')
    assert clearance['status']=='PASS' and clearance['operationId']==OPERATION
    assert clearance['originalFailurePinsUnchanged']==205 and clearance['originalProtectionsPreciselyReleased']
    assert clearance['writersRemainStopped'] and not clearance['restoreDispatched']
    request=read('restore-ui-submission.json')['request']
    assert request['operationId']==OPERATION and request['recoveryPointRef']==POINT and request['targetConfigRef']==TARGET
    terminal=read('restore-terminal-record.json')
    assert terminal['result']['operationId']==OPERATION and terminal['result']['state']=='FAILED'
    assert read('restore-ui-result.json')['writes']==1
    destination=TASK/'restore-attempt-361'
    assert destination.parent.resolve()==TASK.resolve() and not destination.exists()
    originals=[fixed(TASK/name,TASK) for name in NAMES]
    private_source=PRIVATE/'restore-entry-response.private.json'
    private_pin=fixed(private_source,PRIVATE)
    private_destination=PRIVATE/'failed-restore-361-local-originals'
    assert not private_destination.exists()
    destination.mkdir();private_destination.mkdir()
    mapping=[dict(original=v,preservedPath=str(destination/Path(v['path']).name)) for v in originals]
    private_mapping=dict(original=private_pin,preservedPath=str(private_destination/private_source.name))
    intent=dict(operationId=OPERATION,originalState='FAILED',localFiles=mapping,privateFile=private_mapping)
    save(destination/'preservation-intent.json',intent)
    for item in mapping+[private_mapping]:
        source=Path(item['original']['path']);target=Path(item['preservedPath'])
        assert pin(source)==item['original'] and not target.exists()
        source.rename(target)
        after=pin(target)
        assert after['bytes']==item['original']['bytes'] and after['sha256']==item['original']['sha256']
        assert not source.exists()
    report=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        operationId=OPERATION,originalState='FAILED',originalSubmissionCount=1,
        localOriginalPinsUnchanged=len(mapping),localFiles=mapping,
        privateOriginalResponsePreserved=True,privateFile=private_mapping,
        clearancePin=clearance['clearancePin'],restoreDispatched=False)
    save(TASK/'failed-attempt-archive.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('localFiles','privateFile')}))

def verify():
    archive_report=read('failed-attempt-archive.json');assert archive_report['status']=='PASS'
    native=read('restored-native-evidence.json')
    assert native['status']=='PASS' and native['state']=='SUCCEEDED' and native['operationId']!=OPERATION
    for item in archive_report['localFiles']+[archive_report['privateFile']]:
        path=Path(item['preservedPath']);reference=item['original']
        assert not path.is_symlink()
        current=pin(path)
        assert current['bytes']==reference['bytes'] and current['sha256']==reference['sha256']
    diagnosis=read('database-state-failure-diagnosis.json')
    assert len(diagnosis['evidencePins'])==205
    script='PINS='+repr(diagnosis['evidencePins'])+'\n'+'''import datetime,hashlib,json,pathlib
for item in PINS:
 raw=pathlib.Path(item['path']).read_bytes()
 assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256'],'ORIGINAL_FAILURE_CHANGED'
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),remoteOriginalPinsUnchanged=len(PINS))))
'''
    report=remote(script,90)
    report.update(operationId=OPERATION,localOriginalPinsUnchanged=len(archive_report['localFiles']),
        privateOriginalResponsePreserved=True,successfulNewOperationId=native['operationId'],
        originalState='FAILED',archiveManifestPin=pin(TASK/'failed-attempt-archive.json'))
    (TASK/'failed-attempt-preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['archive','verify']);args=parser.parse_args()
    {'archive':archive,'verify':verify}[args.phase]()
