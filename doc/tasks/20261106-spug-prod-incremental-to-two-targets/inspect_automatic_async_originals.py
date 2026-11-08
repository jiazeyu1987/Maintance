"""Read-only asynchronous owner journals; no status/reconcile calls."""
import json
from common import TASK,PRIVATE,SOURCE,remote,write

SCRIPT=r'''
import hashlib,json,pathlib,sys,time,datetime
control=INSTALL['controllers'][0]['control'];sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_control_smallapp_native import Native
from recovery_control_smallapp import local_read,public_error
import recovery_control_executor as executor
n=Native(INSTALL['controllers'][0]['controlConfigurationPin']);rows=[]
for d in sorted(pathlib.Path(control['ledgerRoot']).iterdir()):
 if not d.is_dir():continue
 value=local_read(d/'request.json')
 if value['sourceConfigRef']!=SOURCE:continue
 selection=local_read(d/'selection.json');start=time.monotonic();root=n.accepted_operation(value,selection)
 originals={name:n.document(executor.pin(root/name)) for name in ('request.json','start.json','result.json','worker-process.json','capture-terminal.json','capture-process.json') if (root/name).is_file()}
 queries=[]
 for path in (d/'queries').glob('*.json'):
  row=local_read(path)
  if row.get('result',{}).get('state') in ('SUCCEEDED','FAILED'):
   queries.append(dict(pin=executor.pin(path),value=row))
 output=originals.get('result.json',{})
 rows.append(dict(operationId=d.name,root=str(root),acceptedReadSeconds=time.monotonic()-start,originals=originals,
  terminalQueries=queries,resultPin=executor.pin(root/'result.json') if output else None,
  originalPinBytes=sum(pin['bytes'] for pin in output.get('originalResultPins',[])),
  originalPins=output.get('originalResultPins',[])))
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,serverWrites=False,noStatusOrReconcile=True)))
'''

if __name__=='__main__':
    out=PRIVATE/'automatic-async-originals.private.json';public=TASK/'automatic-async-originals.json';assert not out.exists() and not public.exists()
    install=json.loads((PRIVATE/'automatic-control-installation-57.private.json').read_text(encoding='utf-8'))
    v=remote('172.30.30.57','INSTALL='+repr(install)+'\nSOURCE='+repr(SOURCE)+'\n'+SCRIPT,timeout=60);write(out,v)
    summary=dict(v,rows=[dict(operationId=r['operationId'],acceptedReadSeconds=r['acceptedReadSeconds'],resultPin=r['resultPin'],
        state=r['originals'].get('result.json',{}).get('state'),failureCode=r['originals'].get('result.json',{}).get('failureCode'),
        originalPinBytes=r['originalPinBytes'],originalPins=r['originalPins'],terminalQueries=len(r['terminalQueries']),
        journalKeys={k:sorted(x) for k,x in r['originals'].items()}) for r in v['rows']])
    write(public,summary)
    print(json.dumps(dict(rows=[{k:r[k] for k in ('operationId','state','failureCode','originalPinBytes','terminalQueries','acceptedReadSeconds')} for r in summary['rows']],serverWrites=False)))
