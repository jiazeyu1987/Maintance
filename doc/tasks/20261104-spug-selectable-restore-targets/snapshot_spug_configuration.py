"""Snapshot private local settings without printing credentials or modifying Spug."""
import hashlib,json,subprocess
from pathlib import Path
from install_controls import PRIVATE
CONTAINER='intruoyi-spug-transfer-spug-1'
code="""import json,pathlib
root=pathlib.Path('/var/lib/intruoyi-spug')
print(json.dumps({name:json.loads((root/name).read_text()) for name in ('smallapp-simple-settings.json','smallapp-entry-settings.json')}))
"""
p=subprocess.run(['docker','exec',CONTAINER,'python3','-B','-c',code],capture_output=True,check=True)
settings=json.loads(p.stdout)
private=Path('C:/Spug/runtime/private')
bridge=json.loads((private/'smallapp-bridge.private.json').read_text(encoding='utf-8'))
settings['smallapp-bridge.private.json']=bridge
for name in set(bridge.get('sourceConnections',{}).values())|set(bridge.get('targetConnections',{}).values()):
 settings[name]=json.loads((private/name).read_text(encoding='utf-8'))
settings['runtimeAdapterSha256']=hashlib.sha256(Path('C:/Spug/runtime/ops/spug/smallapp_adapter.py').read_bytes()).hexdigest()
destination=PRIVATE/'spug-before.private.json'
if destination.exists():raise SystemExit('SPUG_SNAPSHOT_ALREADY_EXISTS')
destination.write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8')
binding=next(b for b in settings['smallapp-simple-settings.json']['bindings'] if b['applicationId']=='intruoyi-57-safe-20261024-v1')
print(json.dumps({'applicationId':binding['applicationId'],'binding':binding,'servers':settings['smallapp-simple-settings.json']['servers'],'bridgeFiles':sorted(set(bridge.get('sourceConnections',{}).values())|set(bridge.get('targetConnections',{}).values()))},ensure_ascii=False))
