"""Restore only the three approved, original NAS mounts with persistent units."""
import json
from repair_preflight import remote, PRIVATE, TASK

SCRIPT=r'''
import datetime,hashlib,json,pathlib,subprocess
def run(args,timeout=35):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if p.returncode:raise RuntimeError('COMMAND_FAILED '+repr(args[:3])+' '+p.stderr.decode('utf-8','replace')[:1000])
 return p.stdout.decode('utf-8','replace').strip()
def mounts():return [l for l in pathlib.Path('/proc/self/mountinfo').read_text().splitlines() if ' - cifs ' in l]
credential=pathlib.Path('/root/.smbcredentials')
assert credential.is_file() and credential.stat().st_uid==0 and credential.stat().st_mode&0o077==0
targets=[('/mnt/intruoyi-backup-nas','//172.30.30.4/IT共享','cifs','ro,credentials=/root/.smbcredentials,vers=3.0,seal,soft,uid=0,gid=0,file_mode=0600,dir_mode=0700',''),
('/mnt/nas/Backup/BackupPackage','/mnt/intruoyi-backup-nas/Backup/BackupPackage','none','bind,ro','/mnt/intruoyi-backup-nas'),
('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas','//172.30.30.4/IT共享','cifs','rw,credentials=/root/.smbcredentials,vers=3.0,sec=ntlmssp,seal,soft,serverino,uid=0,gid=0,file_mode=0600,dir_mode=0700','')]
assert not mounts(),'NAS_MOUNT_STATE_CHANGED'
for target,*_ in targets:
 p=pathlib.Path(target);assert p.is_dir() and not p.is_symlink() and str(p.resolve())==target and not any(p.iterdir()),'LOCAL_TARGET_NOT_EMPTY'
units=[]
for target,source,kind,options,dependency in targets:
 unit=run(['systemd-escape','--path','--suffix=mount',target]);path=pathlib.Path('/etc/systemd/system')/unit
 assert not path.exists(),'UNIT_ALREADY_EXISTS'
 extra='RequiresMountsFor='+dependency+'\n' if dependency else ''
 text='[Unit]\nDescription=Original IntRuoyi NAS mount restored 20261105\nWants=network-online.target\nAfter=network-online.target\n'+extra+'\n[Mount]\nWhat='+source+'\nWhere='+target+'\nType='+kind+'\nOptions='+options+'\nTimeoutSec=25\n\n[Install]\nWantedBy=multi-user.target\n'
 path.write_text(text,encoding='utf-8');path.chmod(0o644);units.append(unit)
run(['systemctl','daemon-reload'])
results=[]
for unit,(target,source,kind,options,dependency) in zip(units,targets):
 if dependency:assert pathlib.Path(source).is_dir(),'ORIGINAL_SHARE_SUBDIRECTORY_MISSING'
 run(['systemctl','enable','--now',unit])
 rows=[l for l in mounts() if l.split(' - ')[0].split()[4]==target];assert len(rows)==1,'EXPECTED_CIFS_MOUNT_MISSING'
 assert rows[0].split(' - ')[1].split()[1]=='//172.30.30.4/IT共享'
 actualMode=rows[0].split(' - ')[0].split()[5].split(',')[0];assert actualMode==options.split(',')[0] or (kind=='none' and actualMode=='ro')
 results.append({'target':target,'unit':unit,'active':run(['systemctl','is-active',unit]),'mode':actualMode,'mountRoot':rows[0].split()[3]})
archive=pathlib.Path(targets[2][0])/'Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives'
assert archive.is_dir(),'ORIGINAL_ARCHIVE_ROOT_MISSING'
stat=archive.stat();space=run(['df','-B1','--output=avail',str(archive)],timeout=8).splitlines()[-1]
out={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mounts':results,'archiveRoot':str(archive),'archiveRootDevice':stat.st_dev,'freeBytes':int(space)}
print(json.dumps(out))
'''
if __name__=='__main__':
    result=remote('172.30.30.57',SCRIPT,timeout=110)
    (TASK/'nas-restored.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
