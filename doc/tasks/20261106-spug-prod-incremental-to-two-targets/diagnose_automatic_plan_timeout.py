"""Read closure originals and timing only; never reconciles or dispatches."""
import json
from common import TASK,PRIVATE,SOURCE,remote,write

SCRIPT=r'''
import json,pathlib,sys,time,hashlib,datetime
control_pin=INSTALL['controllers'][0]['controlConfigurationPin'];control=INSTALL['controllers'][0]['control']
raw=pathlib.Path(control_pin['path']).read_bytes();assert len(raw)==control_pin['bytes'] and hashlib.sha256(raw).hexdigest()==control_pin['sha256']
sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
from recovery_control_smallapp_native import Native
from recovery_control_smallapp import Ledger,local_read,public_error
import recovery_control_executor as executor
native=Native(control_pin);ledger=Ledger(control['ledgerRoot'],native)
reads=[];actual_read=executor.pinned_read
def measured(path,*args,**kwargs):
 start=time.monotonic()
 try:return actual_read(path,*args,**kwargs)
 finally:reads.append(dict(path=str(path),seconds=time.monotonic()-start))
executor.pinned_read=measured
rows=[]
for directory in sorted(pathlib.Path(control['ledgerRoot']).iterdir()):
 if not directory.is_dir():continue
 request=local_read(directory/'request.json')
 if request['sourceConfigRef']!=SOURCE:continue
 originals={name:local_read(directory/name) for name in ('request.json','selection.json','intent.json','completion.json','execute/native-intent.json','execute/native-process.json','execute/native-original-exit.json') if (directory/name).is_file()}
 start=time.monotonic()
 try:closed=ledger.successfully_closed(directory,request);error=None
 except Exception as exc:closed=False;error=public_error(exc)
 rows.append(dict(operationId=directory.name,action=request['action'],closed=closed,error=error,seconds=time.monotonic()-start,
  originalKeys={key:sorted(value) for key,value in originals.items()},originals=originals))
print(json.dumps(dict(status='OBSERVED',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),rows=rows,reads=reads,
 controlPin=control_pin,serverWrites=False,noReconcile=True,noLedgerStatus=True)))
'''

if __name__=='__main__':
    private_path=PRIVATE/'automatic-plan-timeout-closure.private.json';public_path=TASK/'automatic-plan-timeout-closure.json'
    assert not private_path.exists() and not public_path.exists()
    install=json.loads((PRIVATE/'automatic-control-installation-57.private.json').read_text(encoding='utf-8'))
    value=remote('172.30.30.57','INSTALL='+repr(install)+'\nSOURCE='+repr(SOURCE)+'\n'+SCRIPT,timeout=90)
    write(private_path,value)
    public=dict(value,rows=[{key:item for key,item in row.items() if key!='originals'} for row in value['rows']])
    write(public_path,public)
    print(json.dumps(dict(status=public['status'],rows=[{k:r[k] for k in ('operationId','action','closed','error','seconds')} for r in public['rows']],serverWrites=False)))
