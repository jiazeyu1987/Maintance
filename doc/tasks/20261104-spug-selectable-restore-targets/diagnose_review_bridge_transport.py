"""Read-only native transport facts; never emit URLs with auth or header values."""
import json,subprocess
from resume_readonly import TASK,PRIVATE

SCRIPT=r'''
import concurrent.futures,datetime,json,sys,time,urllib.request,urllib.parse
sys.path.insert(0,'/opt/intruoyi-spug')
from smallapp_adapter import HttpBridge
source='intruoyi-57-safe-20261024-v1'
def query(target):
 bridge=HttpBridge(source_ref=source,target_ref=target)
 endpoint=bridge.selection_url
 if target and bridge.selected_target_preflight:endpoint+='?targetConfigRef='+target
 start=time.monotonic();parsed=urllib.parse.urlsplit(endpoint)
 out={'targetConfigRef':target,'host':parsed.hostname,'port':parsed.port,'scheme':parsed.scheme}
 try:
  with bridge.opener.open(urllib.request.Request(endpoint,headers=bridge.headers),timeout=15) as response:
   data=json.load(response);out.update(status=response.status,applicationCount=len(data.get('applications',[])),errorCode=data.get('errorCode'))
 except Exception as error:
  cause=getattr(error,'reason',error)
  out.update(errorClass=type(error).__name__,causeClass=type(cause).__name__,errno=getattr(cause,'errno',None),winerror=getattr(cause,'winerror',None))
  # Fixed classifications retain useful facts without arbitrary exception text.
  text=str(cause).lower()
  out['proxyTunnelFailed']='tunnel connection failed' in text
  out['httpCode']=getattr(error,'code',None)
 out['seconds']=round(time.monotonic()-start,3)
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 rows=list(pool.map(query,[None,'intruoyi-main-58-safe-restore-20261104-v1','intruoyi-main-59-safe-restore-20261104-v1']))
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':rows,'proxyVariableNames':sorted(urllib.request.getproxies()),'remoteMutation':False}))
'''
if __name__=='__main__':
 p=subprocess.run(['docker','exec','intruoyi-spug-transfer-spug-1','python3','-B','-c',SCRIPT],capture_output=True,timeout=45)
 if p.returncode:
  (PRIVATE/'review-bridge-transport-error.private.log').write_bytes(p.stdout+p.stderr)
  raise RuntimeError('READONLY_BRIDGE_TRANSPORT_DIAGNOSIS_FAILED')
 result=json.loads(p.stdout)
 (TASK/'review-bridge-transport-diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
