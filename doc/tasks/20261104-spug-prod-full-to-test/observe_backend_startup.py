"""Read exact source backend startup and preserve raw logs privately."""
import json
import re
from repair_preflight import remote, TASK, PRIVATE

SCRIPT=r'''
import datetime,json,subprocess
cid='c4385604eb83b44f2836755bad709581c7e7edd0078b148f3b0f74e0b567304c'
row=json.loads(subprocess.check_output(['docker','inspect',cid],timeout=8))[0]
logs=subprocess.run(['docker','logs','--since',row['State']['StartedAt'],'--tail','2000',cid],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
probe=subprocess.run(['docker','exec',cid,'curl','-fsS','--max-time','3','http://127.0.0.1:48081/actuator/health'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=6)
print(json.dumps({'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':row['State'],'networks':{k:{'ip':v['IPAddress'],'networkId':v['NetworkID']} for k,v in row['NetworkSettings']['Networks'].items()},'insideHealthExitCode':probe.returncode,'insideHealth':probe.stdout.decode('utf-8','replace'),'logs':(logs.stdout+logs.stderr).decode('utf-8','replace')}))
'''
if __name__=='__main__':
    raw=remote('172.30.30.57',SCRIPT,timeout=35)
    (PRIVATE/'source-backend-startup.private.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
    text=raw.pop('logs')
    raw['startupMarkers']={pattern:bool(re.search(pattern,text,re.I)) for pattern in ['Started .*Application','Tomcat started','Application run failed','OutOfMemoryError','BindException','Connection refused','CommunicationsException']}
    raw['errorClasses']=sorted(set(re.findall(r'(?m)(?:Caused by: )?([A-Za-z_][A-Za-z0-9_.$]*(?:Exception|Error))\b',text)))[:30]
    raw['logLines']=len(text.splitlines())
    (TASK/'source-backend-startup.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(raw))
