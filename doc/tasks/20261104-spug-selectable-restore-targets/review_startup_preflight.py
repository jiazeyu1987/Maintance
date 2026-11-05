"""Read-only preparation for a separately authorized original-service start."""
import json
from resume_readonly import TASK,remote
SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cifsMounts':[],'fstabCifs':[],'canonicalRoot':{},'remoteMutation':False}
base=pathlib.Path('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas')
out['canonicalRoot']={'path':str(base),'exists':base.exists(),'isDirectory':base.is_dir(),'isSymlink':base.is_symlink()}
if base.is_dir():out['canonicalRoot']['entryCount']=sum(1 for _ in base.iterdir())
relative=pathlib.Path('Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives/prod-standard-197d8fd4ced92df64f0c152e9c6d470596ec343532e3b2dd82ebbef680114bcb/.repository/point.json')
for line in pathlib.Path('/proc/self/mountinfo').read_text().splitlines():
 a,b=line.split(' - ',1);left=a.split();right=b.split()
 if right[0]!='cifs':continue
 mount=pathlib.Path(left[4].replace('\\040',' '));point=mount/relative
 row={'path':str(mount),'root':left[3],'source':right[1],'readonly':'ro' in left[5].split(','),'pointExists':point.is_file()}
 if point.is_file():row['pointSha256']=hashlib.sha256(point.read_bytes()).hexdigest()
 out['cifsMounts'].append(row)
for line in pathlib.Path('/etc/fstab').read_text().splitlines():
 if not line.strip() or line.lstrip().startswith('#'):continue
 fields=line.split()
 if len(fields)>2 and fields[2]=='cifs':out['fstabCifs'].append({'source':fields[0],'target':fields[1],'type':fields[2]})
root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')
receipt=json.loads((root/'target-installation.json').read_bytes());owner=json.loads(pathlib.Path(receipt['ownerConfigurationPin']['path']).read_bytes())
ids=[s['id'] for s in owner['targets'][receipt['targetConfigRef']]['services']]
rows=json.loads(subprocess.check_output(['docker','inspect',*ids],timeout=15))
out['services']=[{'id':r['Id'],'name':r['Name'],'running':r['State']['Running'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],'restartPolicy':r['HostConfig']['RestartPolicy'],'ports':r['HostConfig']['PortBindings']} for r in rows]
out['listeners']=[line for line in subprocess.check_output(['ss','-lnt'],timeout=5).decode().splitlines() if any(':'+str(p) in line.split()[3] for p in (38081,48081,18081))]
print(json.dumps(out))
'''
if __name__=='__main__':
    out=remote('172.30.30.59',SCRIPT,timeout=75)
    (TASK/'review-startup-preflight.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))
