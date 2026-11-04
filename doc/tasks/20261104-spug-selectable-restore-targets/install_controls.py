"""Install only the approved, task-owned controls. No restore operation is sent."""
import argparse
import base64
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess

PRIVATE=Path('C:/Spug/runtime/private/restore-targets-20261104')
COMMIT='45b4e3e'
PACKAGE=PRIVATE/('packages-'+COMMIT+'/backup-restore-standard.tgz')
ROOTS={'57':'/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',
       '58':'/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3',
       '59':'/mnt/intruoyi-data/spug-main-restore-20261104-v3'}
PROFILES=json.loads(Path('C:/Spug/runtime/private/runtime-versions.private.json').read_text(encoding='utf-8'))['profiles']

def ssh(profile,script,timeout=80):
    args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile','-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8','root@'+profile['host'],profile['python']+' -B -']
    p=subprocess.run(args,input=script.encode('utf-8'),capture_output=True,timeout=timeout)
    if p.returncode:
        (PRIVATE/(profile['host']+'-install-error.private.txt')).write_bytes(p.stderr+p.stdout)
        raise RuntimeError('CONTROL_INSTALL_FAILED '+profile['host'])
    return json.loads(p.stdout)

STAGE=r'''
import base64,hashlib,io,json,os,pathlib,tarfile
root=pathlib.Path(ROOT)
assert root.is_absolute() and not root.exists(),'INSTALL_ROOT_ALREADY_EXISTS'
assert root.parent.resolve()==root.parent and root.parent.is_dir(),'INSTALL_PARENT_INVALID'
raw=base64.b64decode(PACKAGE)
assert hashlib.sha256(raw).hexdigest()==PACKAGE_SHA,'PACKAGE_CHANGED'
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
    version=json.load(archive.extractfile('package.json'))
    assert version['variant']=='standard' and version['fileVerification'] and version['payloadContentVerification']
    assert set(archive.getnames())==set(version['files'])|{'package.json'}
    for name,checksum in version['files'].items():
        item=archive.getmember(name)
        assert item.isfile() and not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
        assert hashlib.sha256(archive.extractfile(item).read()).hexdigest()==checksum
    root.mkdir(mode=0o700)
    for sub in ['engine','configuration','private','ledger','registry','registry/applications','registry/points','operations','replacement-state','recovery-operations']:
        (root/sub).mkdir(mode=0o700)
    for item in archive.getmembers():
        path=root/'engine'/item.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(archive.extractfile(item).read())
        path.chmod(0o600)
    receipt={'schemaVersion':'SpugMainRestoreComponentInstallation/v1','root':str(root),'sourceCommit':COMMIT,
        'packageSha256':PACKAGE_SHA,'fileManifestSha256':version['packageSha256'],'files':len(version['files']),
        'controlServiceStarted':False,'restorePerformed':False}
    (root/'installation.json').write_text(json.dumps(receipt,sort_keys=True),encoding='utf-8');(root/'installation.json').chmod(0o600)
print(json.dumps(receipt))
'''

METADATA=r'''
import base64,glob,hashlib,json,pathlib
out={}
for path in glob.glob(ARCHIVES+'/*/.repository/recovery-material.json'):
    material=json.loads(pathlib.Path(path).read_bytes())
    for reference in material['versionPins']:
        p=pathlib.Path(reference['path']);raw=p.read_bytes()
        assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'ORIGINAL_VERSION_PIN_CHANGED'
        out[str(p)]={'pin':reference,'base64':base64.b64encode(raw).decode()}
print(json.dumps(out))
'''

def stage(profile):
    raw=PACKAGE.read_bytes();suffix=profile['host'].split('.')[-1]
    script='COMMIT='+repr(COMMIT)+'\nROOT='+repr(ROOTS[suffix])+'\nPACKAGE='+repr(base64.b64encode(raw).decode())+'\nPACKAGE_SHA='+repr(hashlib.sha256(raw).hexdigest())+'\n'+STAGE
    result=ssh(profile,script)
    (PRIVATE/(profile['host']+'-component-installation.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['stage','metadata']);args=parser.parse_args()
    if args.action=='metadata':
        value=ssh(next(p for p in PROFILES if p['host'].endswith('.57')),
            'ARCHIVES='+repr('/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas/Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives')+'\n'+METADATA)
        (PRIVATE/'canonical-version-files.json').write_text(json.dumps(value),encoding='utf-8')
        print(json.dumps({'metadataFiles':len(value),'pins':[v['pin'] for v in value.values()]}))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for future in concurrent.futures.as_completed([pool.submit(stage,p) for p in PROFILES]):print(json.dumps(future.result()))
