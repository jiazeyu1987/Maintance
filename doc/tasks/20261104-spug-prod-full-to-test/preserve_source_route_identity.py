"""Restore immutable URL identity; provide its original port on owned SSH."""
import json
from pathlib import Path
from observe_current_state import PRIVATE,TASK
if __name__=='__main__':
 route=Path('C:/Spug/runtime/private/intruoyi-57-safe-20261024-v1-bridge.private.json')
 old=(PRIVATE/'source-route.before.private.json').read_bytes();before=json.loads(old);current=json.loads(route.read_bytes())
 expected=dict(before)
 for k in ('submitUrl','queryUrlTemplate','selectionUrl'):expected[k]=expected[k].replace('host.docker.internal:32657','host.docker.internal:42657')
 assert current==expected
 script=Path('C:/Spug/runtime/private/restore-targets-20261104/restore_control_transport.ps1');text=script.read_text(encoding='utf-8')
 needle="    $transportArguments += @('-L',('127.0.0.1:'+$sshPort+':127.0.0.1:22'))"
 assert text.count(needle)==1
 (PRIVATE/'source-transport-before-alias.private.ps1').write_bytes(script.read_bytes())
 text=text.replace(needle,needle+"\n    if ($Target -eq '57') { $transportArguments += @('-L','127.0.0.1:32657:127.0.0.1:32657') }")
 script.write_text(text,encoding='utf-8');assert script.read_text(encoding='utf-8')==text
 route.write_bytes(old);assert route.read_bytes()==old
 previous=TASK/'full-ui-result.json';r=json.loads(previous.read_text(encoding='utf-8'));assert r['httpStatus']==409;r['status']='FAIL';r['error']='ORIGINAL_BRIDGE_BINDING_CHANGED';previous.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'originalSourceRouteBytesRestored':True,'aliasInstalled':True,'historyModified':False}))
