"""Approved PROD daemon repair, with separate enable and restart gates."""
import argparse
import json
from repair_preflight import remote,TASK,PRIVATE

SCRIPT=r'''
import copy,datetime,fcntl,hashlib,json,os,pathlib,stat,subprocess,time
root=pathlib.Path('/root/spug-postboot-repair-20261105/docker-management-repair')
daemon=pathlib.Path('/etc/docker/daemon.json')
def canonical(d):return json.dumps(d,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
def write_new(p,raw):
 with p.open('xb') as f:f.write(raw)
 p.chmod(0o600)
def run(args,timeout=15):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.returncode:
  if root.exists():(root/('failure-'+PHASE+'.private.json')).write_bytes(canonical({'arguments':args,'stdout':p.stdout.decode('utf-8','replace'),'stderr':p.stderr.decode('utf-8','replace'),'exitCode':p.returncode}))
  raise RuntimeError('COMMAND_FAILED_'+args[0]+'_'+str(p.returncode))
 return p.stdout.decode().strip()
def inspect(ids):return json.loads(run(['docker','inspect']+ids))
def protected():
 rows=inspect(PROTECTED)
 assert all(c['State']['Running'] and not c['State']['Restarting'] and not c['State']['Paused'] for c in rows),'PROTECTED_APP_UNSTABLE'
 return rows
def verify(before):
 now={c['Id']:c for c in protected()}
 for c in before:
  n=now[c['Id']]
  assert all(n['State'][k]==c['State'][k] for k in ('Pid','StartedAt')),'PROTECTED_APP_RESTARTED'
  assert n['Image']==c['Image'] and n['Config']==c['Config'] and n['HostConfig']==c['HostConfig'] and sorted(n['Mounts'],key=lambda x:x['Destination'])==sorted(c['Mounts'],key=lambda x:x['Destination']),'PROTECTED_APP_CONFIGURATION_CHANGED'
 return now
def properties():
 value={}
 for k in ('KillMode','ExecStop','MainPID'):
  value[k]=run(['systemctl','show','docker.service','-p',k,'--value'])
 assert value['KillMode']=='process' and not value['ExecStop'],'DOCKER_UNIT_UNSAFE'
 return value
capture=json.loads(pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/capture.json').read_bytes())
lock=pathlib.Path(capture['sourceLockPath']);fd=os.open(str(lock),os.O_RDONLY);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert os.fstat(fd).st_ino==lock.stat().st_ino,'SOURCE_LOCK_CHANGED'
assert run(['docker','info','--format','{{.Swarm.LocalNodeState}}'])=='inactive'
assert run(['docker','version','--format','{{.Server.Version}}'])=='26.1.3'
props=properties()
if PHASE=='enable':
 assert not root.exists(),'ENABLE_ALREADY_ATTEMPTED'
 before=protected();raw=daemon.read_bytes();assert hashlib.sha256(raw).hexdigest()=='ecb0765019541bf61bf120ce3c022ad38c2bdb578f768f6a3e1c1b50737dde37','DAEMON_CONFIGURATION_CHANGED'
 assert run(['docker','info','--format','{{json .LiveRestoreEnabled}}'])=='false'
 root.mkdir(mode=0o700);write_new(root/'daemon.before.private.json',raw)
 write_new(root/'applications.before.private.json',canonical(before));write_new(root/'unit.before.json',canonical(props))
 candidate=json.loads(raw);assert 'live-restore' not in candidate;candidate['live-restore']=True
 proposed=canonical(candidate)+b'\n';write_new(root/'daemon.proposed.private.json',proposed)
 run(['/usr/bin/dockerd','--validate','--config-file='+str(root/'daemon.proposed.private.json')])
 st=daemon.stat();temp=daemon.with_name('daemon.json.spug-postboot-20261105.tmp');assert not temp.exists()
 write_new(temp,proposed);os.chmod(str(temp),stat.S_IMODE(st.st_mode));os.chown(str(temp),st.st_uid,st.st_gid)
 assert daemon.read_bytes()==raw;os.replace(str(temp),str(daemon))
 run(['systemctl','reload','docker.service'])
 for _ in range(20):
  if run(['docker','info','--format','{{json .LiveRestoreEnabled}}'])=='true':break
  time.sleep(0.25)
 else:raise RuntimeError('LIVE_RESTORE_NOT_ENABLED_NO_RESTART')
 verify(before);assert properties()['MainPID']==props['MainPID'],'DAEMON_RESTARTED_DURING_RELOAD'
 out={'phase':PHASE,'status':'PASS','observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'liveRestore':True,'protectedContainers':len(before),'protectedPidAndStartedAtUnchanged':True,'daemonPid':int(props['MainPID']),'configurationSha256':hashlib.sha256(daemon.read_bytes()).hexdigest()}
 write_new(root/'enable-result.json',canonical(out))
else:
 prior=json.loads((root/'enable-result.json').read_bytes());assert prior['status']=='PASS' and prior['liveRestore']
 assert hashlib.sha256(daemon.read_bytes()).hexdigest()==prior['configurationSha256']
 assert run(['docker','info','--format','{{json .LiveRestoreEnabled}}'])=='true'
 before=json.loads((root/'applications.before.private.json').read_bytes());verify(before)
 assert int(props['MainPID'])==prior['daemonPid']
 write_new(root/'restart-started.json',canonical({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'oldDaemonPid':int(props['MainPID'])}))
 run(['systemctl','restart','docker.service'],timeout=55)
 assert run(['systemctl','is-active','docker.service'])=='active'
 assert run(['docker','info','--format','{{json .LiveRestoreEnabled}}'])=='true'
 current=properties();assert current['MainPID']!=props['MainPID'],'DAEMON_DID_NOT_RESTART'
 verify(before)
 out={'phase':PHASE,'status':'PASS','observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'liveRestore':True,'protectedContainers':len(before),'protectedPidAndStartedAtUnchanged':True,'oldDaemonPid':int(props['MainPID']),'newDaemonPid':int(current['MainPID'])}
 write_new(root/'restart-result.json',canonical(out))
print(json.dumps(out))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['enable','restart']);args=parser.parse_args()
 prior=json.loads((TASK/'other-applications-preserved.json').read_text(encoding='utf-8'))
 ids=[r['id'] for r in prior['protectedApplications']];assert len(ids)==12
 result=remote('172.30.30.57','PHASE='+repr(args.phase)+'\nPROTECTED='+repr(ids)+'\n'+SCRIPT,timeout=100)
 (TASK/('docker-'+args.phase+'-result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
