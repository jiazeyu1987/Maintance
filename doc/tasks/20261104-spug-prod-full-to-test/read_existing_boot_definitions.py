"""Read original mount definitions and exact historical backend states."""
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE=r'''
import datetime,json,pathlib,subprocess
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
out['fstabRaw']=pathlib.Path('/etc/fstab').read_text()
out['mountinfoRaw']=pathlib.Path('/proc/self/mountinfo').read_text()
for key,args in [('mountUnits',['systemctl','list-units','--all','--no-pager','--no-legend','--type=mount','--type=automount']),('portContainers',['docker','ps','-aq','--filter','publish=48081'])]:
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10);out[key]={'exitCode':p.returncode,'text':p.stdout.decode('utf-8','replace')}
ids=out['portContainers']['text'].split()
out['backendCandidates']=json.loads(subprocess.check_output(['docker','inspect']+ids,timeout=15)) if ids else []
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
out['entryRaw']=(root/'engine/control_entry.py').read_text()
out['mountTargets']={}
for path in ('/mnt/intruoyi-backup-nas','/mnt/nas/Backup/BackupPackage','/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas'):
 p=pathlib.Path(path);row={'exists':p.exists(),'isSymlink':p.is_symlink()}
 if p.is_dir():row['topEntryCount']=sum(1 for _ in p.iterdir())
 out['mountTargets'][path]=row
print(json.dumps(out))
'''
profile=next(p for p in PROFILES if p['host'].endswith('.57'))
args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=10','root@'+profile['host'],profile['python']+' -B -']
result=subprocess.run(args,input=REMOTE.encode(),capture_output=True,timeout=40)
if result.returncode:
 (PRIVATE/'boot-definitions-error.private.txt').write_bytes(result.stderr+result.stdout)
 raise RuntimeError('BOOT_DEFINITIONS_READ_FAILED')
raw=json.loads(result.stdout)
(PRIVATE/'boot-definitions.private.json').write_text(json.dumps(raw),encoding='utf-8')
report={'observedAt':raw['observedAt'],'mountUnits':raw['mountUnits'],'mountTargets':raw['mountTargets'],
 'fstabNasEntryCount':sum(1 for line in raw['fstabRaw'].splitlines() if not line.lstrip().startswith('#') and any(s in line for s in ('cifs','172.30.30.4','/mnt/nas'))),
 'autofsMounts':[line.split(' - ')[0].split()[4] for line in raw['mountinfoRaw'].splitlines() if ' - autofs ' in line],
 'backendCandidates':[{'id':c['Id'],'name':c['Name'],'state':{k:c['State'].get(k) for k in ('Status','Running','Restarting','Error','StartedAt','FinishedAt')},'restartPolicy':c['HostConfig']['RestartPolicy'],'networkSettings':c['NetworkSettings']} for c in raw['backendCandidates']]}
(TASK/'boot-definitions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({**report,'backendCandidates':[{k:v for k,v in c.items() if k!='networkSettings'} for c in report['backendCandidates']]},ensure_ascii=False))
