"""Read retained native failure metadata; expose no configuration or raw SQL."""
import argparse,hashlib,json
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import datetime,hashlib,json,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
capture=root/'capture-staging'/OPERATION
repository=root/'repository-operations'/hashlib.sha256(OPERATION.encode()).hexdigest()
out=dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=OPERATION,documents={},events=[],pins=[])
for path in [repository/'result.json',capture/'terminal-result.json',capture/'worker-failure.json',capture/'job-configuration.json',capture/'source-restoration.json',*sorted(capture.glob('event-*.json'))]:
 if not path.is_file():continue
 raw=path.read_bytes();assert len(raw)<=16*1024*1024
 out['documents'][str(path)]=json.loads(raw)
 out['pins'].append(dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
print(json.dumps(out))
'''
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=['incremental-2','incremental-3'],default='incremental-2');args=parser.parse_args()
 history='365' if args.attempt=='incremental-2' else '366'
 assert not (TASK/('incremental-'+history+'-failure.json')).exists(),'FAILURE_EVIDENCE_ALREADY_EXISTS'
 operation=json.loads((TASK/(args.attempt+'-ui-submission.json')).read_text(encoding='utf-8'))['request']['operationId']
 value=remote('172.30.30.57','OPERATION='+repr(operation)+'\n'+SCRIPT,45)
 write(PRIVATE/('incremental-'+history+'-failure.private.json'),value)
 report=dict(observedAt=value['observedAt'],operationId=operation,terminalDocuments=[],events=[],pins=value['pins'])
 for path,document in value['documents'].items():
  if pathlib_name:=path.rsplit('/',1)[-1]:
   if pathlib_name.startswith('event-'):
    report['events'].append({k:v for k,v in document.items() if k in ('at','stage','captureStage','failureCode','restorationFailureCode','captureFailureCode')})
   elif pathlib_name!='job-configuration.json':
    report['terminalDocuments'].append(dict(path=path,fields=sorted(document),**{k:v for k,v in document.items() if k in ('state','actualExitCode','failureCode','restored','finishedAt')},dataKeys=sorted(document.get('data') or {})))
 write(TASK/('incremental-'+history+'-failure.json'),report)
 print(json.dumps(report))
