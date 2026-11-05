"""Bounded diagnosis for the approved repair; no remote mutations."""
import json
import subprocess
from pathlib import Path
from observe_current_state import PRIVATE, PROFILES, TASK

SSH = ['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=10']

def remote(host, script, timeout=45):
    profile=next(p for p in PROFILES if p['host']==host)
    python='/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12' if host.endswith('.58') else profile['python']
    p=subprocess.run(SSH+['root@'+host,python+' -B -'],input=script.encode('utf-8'),capture_output=True,timeout=timeout)
    if p.returncode:
        (PRIVATE/(host+'-repair-error.private.txt')).write_bytes(p.stdout+p.stderr)
        raise RuntimeError('REMOTE_REPAIR_DIAGNOSIS_FAILED_'+host)
    return json.loads(p.stdout)

SCRIPT=r'''
import datetime,json,pathlib,subprocess
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
ids=subprocess.check_output(['docker','ps','-aq'],timeout=10).decode().split()
rows=subprocess.check_output(['docker','inspect','--format','{{.Id}} {{json .HostConfig.PortBindings}}']+ids,timeout=20).decode().splitlines()
ids=[l.split()[0] for l in rows if '48081' in l]
out['containers']=json.loads(subprocess.check_output(['docker','inspect']+ids,timeout=15))
out['networks']=json.loads(subprocess.check_output(['docker','network','inspect','intruoyi-runtime_intruoyi_net'],timeout=10))
out['listeners']=subprocess.check_output(['ss','-lntp'],timeout=5).decode()
out['proxyProcesses']=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=(p/'cmdline').read_bytes()
  if b'docker-proxy' in cmd and b'48081' in cmd:out['proxyProcesses'].append({'pid':int(p.name),'cmdline':cmd.decode().replace('\x00',' '),'stat':(p/'stat').read_text()})
 except OSError:pass
out['credentialFiles']=[{'path':str(p),'mode':oct(p.stat().st_mode&0o777),'uid':p.stat().st_uid} for p in (pathlib.Path('/root/.smbcredentials'),pathlib.Path('/etc/samba/intruoyi-nas.credentials'),pathlib.Path('/etc/samba/nas.credentials')) if p.is_file()]
print(json.dumps(out))
'''

if __name__=='__main__':
    raw=remote('172.30.30.57',SCRIPT)
    (PRIVATE/'repair-preflight.private.json').write_text(json.dumps(raw),encoding='utf-8')
    report={'observedAt':raw['observedAt'],'credentialFiles':raw['credentialFiles'],'proxyProcesses':raw['proxyProcesses'],
        'containers':[{'id':r['Id'],'name':r['Name'],'state':r['State'],'restartPolicy':r['HostConfig']['RestartPolicy'],'networks':r['NetworkSettings']['Networks'],'sandboxId':r['NetworkSettings'].get('SandboxID'),'ports':r['HostConfig']['PortBindings']} for r in raw['containers']],
        'networkEndpoints':raw['networks'][0]['Containers']}
    (TASK/'repair-preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    path=Path('C:/Spug/runtime/private/restore-targets-20261104/172.30.30.57-install-preflight.json')
    d=json.loads(path.read_text(encoding='utf-8-sig'))
    def visit(x,key=''):
        if isinstance(x,dict):
            for k,v in x.items():visit(v,key+'.'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x):visit(v,key+'['+str(i)+']')
        elif isinstance(x,str) and (' - cifs ' in x or 'credentials=' in x):
            import re
            print(key,re.sub(r'(password|username|user)=([^,\s]+)',r'\1=<redacted>',x)[:12000])
    visit(d)
