"""Align one installed source route with its stable owned transport."""
import json,subprocess
from pathlib import Path
from observe_current_state import PRIVATE,TASK

def docker(code,payload=None):
 p=subprocess.run(['docker','exec','-i','intruoyi-spug-transfer-spug-1','python3','-B','-c',code],input=None if payload is None else json.dumps(payload).encode('utf-8'),capture_output=True,timeout=30)
 if p.returncode:
  (PRIVATE/'route-repair-error.private.log').write_bytes(p.stdout+p.stderr);raise RuntimeError('LOCAL_ROUTE_REPAIR_FAILED')
 return json.loads(p.stdout)

if __name__=='__main__':
 route=Path('C:/Spug/runtime/private/intruoyi-57-safe-20261024-v1-bridge.private.json');raw=route.read_bytes();d=json.loads(raw)
 assert d['selectionUrl']=='http://host.docker.internal:32657/selections'
 (PRIVATE/'source-route.before.private.json').write_bytes(raw)
 for k in ('submitUrl','selectionUrl','queryUrlTemplate'):d[k]=d[k].replace('host.docker.internal:32657','host.docker.internal:42657')
 old=docker("import json,pathlib;print(pathlib.Path('/var/lib/intruoyi-spug/smallapp-simple-settings.json').read_text())")
 (PRIVATE/'simple-settings.before.private.json').write_text(json.dumps(old),encoding='utf-8')
 import copy
 new=copy.deepcopy(old);b=next(x for x in new['bindings'] if x['applicationId']=='intruoyi-57-safe-20261024-v1')
 assert b['sshTransport']=={'host':'host.docker.internal','port':18557}
 assert b['pythonPath']=='/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/python/bin/python3.12'
 b['pythonPath']='/usr/local/libexec/spug-source-control-20261105/python/bin/python3.12'
 script=Path('C:/Spug/runtime/private/restore-targets-20261104/restore_control_transport.ps1');ps=script.read_text(encoding='utf-8')
 needle="    if ($Target -ne '57') {\n        $transportArguments += @('-L',('127.0.0.1:'+$sshPort+':127.0.0.1:22'),'-R','127.0.0.1:34657:127.0.0.1:42657')\n    }"
 assert ps.count(needle)==1
 (PRIVATE/'source-transport.before.private.ps1').write_bytes(script.read_bytes())
 updated=ps.replace(needle,"    $transportArguments += @('-L',('127.0.0.1:'+$sshPort+':127.0.0.1:22'))\n    if ($Target -ne '57') {\n        $transportArguments += @('-R','127.0.0.1:34657:127.0.0.1:42657')\n    }")
 script.write_text(updated,encoding='utf-8');assert script.read_text(encoding='utf-8')==updated
 route.write_text(json.dumps(d,sort_keys=True,separators=(',',':')),encoding='utf-8')
 result=docker("""import json,pathlib,sys,os
v=json.load(sys.stdin);p=pathlib.Path('/var/lib/intruoyi-spug/smallapp-simple-settings.json');assert json.loads(p.read_bytes())==v['old'];q=p.with_name(p.name+'.source-route-20261105.tmp');q.write_text(json.dumps(v['new'],sort_keys=True,separators=(',',':')),encoding='utf-8');q.chmod(0o600);os.replace(q,p);assert json.loads(p.read_bytes())==v['new'];print(json.dumps({'sourceRouteAligned':True,'progressPythonAligned':True,'otherBindingsPreserved':True}))
""",{'old':old,'new':new})
 (TASK/'source-route-aligned.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
