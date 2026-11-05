"""Read-only measurements for a concrete repair proposal."""
import concurrent.futures
import json
import subprocess
from observe_current_state import PRIVATE, PROFILES, TASK

REMOTE=r'''
import datetime,hashlib,json,pathlib,subprocess,sys
out={'host':HOST,'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
if HOST.endswith('.57'):
 ids=subprocess.check_output(['docker','ps','-aq'],timeout=10).decode().split()
 result=subprocess.check_output(['docker','inspect','--format','{{.Id}} {{.Name}} {{json .HostConfig.PortBindings}}']+ids,timeout=15).decode()
 out['configured48081']=[line for line in result.splitlines() if '48081' in line]
 root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
 path=root/'engine/control_entry.py';out['controlEntry']={'exists':path.is_file()}
 if path.is_file():out['controlEntry'].update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 control=json.loads((root/'configuration/control.json').read_bytes())
 out['pythonExists']=pathlib.Path(control['pythonPin']['path']).is_file()
 out['installedIndependentPython']=pathlib.Path('/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12').is_file()
 out['cifsMounts']=[line.split(' - ')[0].split()[4] for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if ' - cifs ' in line]
else:
 root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3')
 receipt=json.loads((root/'target-installation.json').read_bytes());owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
 control=json.loads(pathlib.Path(receipt['controlConfigurationPin']['path']).read_bytes())
 sys.path[:0]=control['environment']['PYTHONPATH'].split(':')
 from recovery_replacement_storage import observe_directory
 target=owner['targets'][receipt['targetConfigRef']];out['storageDifferences']=[]
 for expected in target['replacement']['storage']['mounts']:
  current=observe_directory(expected['source'],backing=expected.get('volume',{}).get('backing'))
  differences={k:{'before':expected[k],'now':current[k]} for k in ('device','inode') if current[k]!=expected[k]}
  differences.update({'mountIdentity.'+k:{'before':expected['mountIdentity'][k],'now':current['mountIdentity'][k]} for k in current['mountIdentity'] if expected['mountIdentity'][k]!=current['mountIdentity'][k]})
  out['storageDifferences'].append({'role':expected['role'],'source':expected['source'],'differences':differences})
 out['ownerPin']=receipt['ownerConfigurationPin'];out['controlPin']=receipt['controlConfigurationPin']
print(json.dumps(out))
'''

def observe(profile):
 host=profile['host'];python=profile['python'] if host.endswith('.57') else '/usr/local/libexec/spug-main-restore-20261104/python/bin/python3.12'
 args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=10','root@'+host,python+' -B -']
 result=subprocess.run(args,input=('HOST='+repr(host)+'\n'+REMOTE).encode(),capture_output=True,timeout=40)
 if result.returncode:
  (PRIVATE/(host+'-boot-repair-measurement-error.private.txt')).write_bytes(result.stderr+result.stdout)
  raise RuntimeError('BOOT_REPAIR_MEASUREMENT_FAILED_'+host)
 report=json.loads(result.stdout)
 (TASK/(host+'-boot-repair-measurement.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 return report

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for report in pool.map(observe,[p for p in PROFILES if p['host'] in ('172.30.30.57','172.30.30.58')]):print(json.dumps(report,ensure_ascii=False))
