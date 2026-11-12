import json,subprocess
from install_controls import PRIVATE
session=json.loads((PRIVATE/'spug-browser-session.private.json').read_text(encoding='utf-8'))
origin=next(o for o in session['origins'] if o['origin']=='http://127.0.0.1:18080')
token=next(i['value'] for i in origin['localStorage'] if i['name']=='token')
code=r'''
import json,sys,time,urllib.request,urllib.error
token=json.load(sys.stdin)['token'];out=[]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for path in ('/simple-settings','/settings','/selections?applicationId=intruoyi-57-safe-20261024-v1'):
 start=time.monotonic()
 try:
  with opener.open(urllib.request.Request('http://127.0.0.1:18081'+path,headers={'X-Token':token}),timeout=45) as r:
   raw=r.read();status=r.status
 except urllib.error.HTTPError as e:raw=e.read();status=e.code
 out.append({'path':path,'status':status,'seconds':time.monotonic()-start,'bytes':len(raw),'result':json.loads(raw) if status!=200 else 'OK'})
print(json.dumps(out))
'''
p=subprocess.run(['docker','exec','-i','intruoyi-spug-transfer-spug-1','python3','-B','-c',code],input=json.dumps({'token':token}).encode(),capture_output=True,timeout=150)
if p.returncode:
 (PRIVATE/'local-entry-error.private.log').write_bytes(p.stderr+p.stdout);raise RuntimeError('LOCAL_ENTRY_READ_FAILED')
print(p.stdout.decode())
