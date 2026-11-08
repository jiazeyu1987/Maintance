"""Run the actual registry read route in a disposable diagnostic process."""
import json
from common import PRIVATE, TASK, now, write
from diagnose_catalogue_504_readonly import CONTAINER, capture


SCRIPT = r'''
import hashlib,json,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,'/opt/intruoyi-spug/release-center')
from application_registry import ApplicationRegistry
config=json.loads(Path('/var/lib/intruoyi-spug/release-center-bridge.private.json').read_text())
registry=ApplicationRegistry(config)
app,route=registry.resolve('/applications/intruoyi/package-catalog','GET')
events=[]
began=time.monotonic()
class Response:
 def __init__(self,response,event): self.response=response;self.event=event;self.status=response.status
 def __enter__(self): return self
 def __exit__(self,*args): return self.response.__exit__(*args)
 def read(self):
  t=time.monotonic();raw=self.response.read()
  self.event.update(readSeconds=round(time.monotonic()-t,3),bytes=len(raw),finishedSeconds=round(time.monotonic()-began,3),sha256=hashlib.sha256(raw).hexdigest())
  return raw
class TimedHTTP:
 def open(self,request,timeout):
  t=time.monotonic();event=dict(route=request.selector,startedSeconds=round(t-began,3),timeout=timeout);events.append(event)
  try:
   response=real.open(request,timeout=timeout)
   event.update(headerSeconds=round(time.monotonic()-t,3),httpStatus=response.status)
   return Response(response,event)
  except Exception as exc:
   event.update(errorType=type(exc).__name__,elapsedSeconds=round(time.monotonic()-t,3));raise
real=registry.http
registry.http=TimedHTTP()
try:
 status,raw=registry.request(app,route,'GET',None,'readonly-catalogue-diagnostic')
 result=dict(status=status,bodyBytes=len(raw),elapsedSeconds=round(time.monotonic()-began,3),events=events)
except Exception as exc:
 result=dict(errorType=type(exc).__name__,elapsedSeconds=round(time.monotonic()-began,3),events=events)
print(json.dumps(result))
'''


def main():
    result = json.loads(capture('bridge-measurement', ['docker', 'exec', '-i', CONTAINER, 'python3', '-B', '-'], timeout=55, data=SCRIPT.encode()))
    result.update(observedAt=now(), businessWrites=0, productChanges=0, actualRegistryCode=True)
    write(TASK / 'catalogue-504-bridge-timings.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
