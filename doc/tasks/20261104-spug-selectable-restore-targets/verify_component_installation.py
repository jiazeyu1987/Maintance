"""Verify staged bytes and prove no task control service/restore was enabled."""
import concurrent.futures
import json
from pathlib import Path
from install_controls import PRIVATE, PROFILES, ROOTS, ssh

REMOTE=r'''
import hashlib,json,pathlib,subprocess
root=pathlib.Path(ROOT);version=json.loads((root/'engine/package.json').read_bytes())
changed=[]
for name,checksum in version['files'].items():
    p=root/'engine'/name
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=checksum:changed.append(name)
receipt=json.loads((root/'installation.json').read_bytes())
unit='spug-main-restore-'+HOST.split('.')[-1]+'-20261104-v1.service'
service=pathlib.Path('/etc/systemd/system')/unit
out={'host':HOST,'root':ROOT,'sourceCommit':receipt['sourceCommit'],'fileCount':len(version['files']),
    'changedFiles':changed,'componentBytesVerified':not changed,'serviceUnitExists':service.exists(),
    'targetConfigurationExists':(root/'configuration/main-recovery.json').exists(),
    'controlConfigurationExists':(root/'configuration/control.json').exists(),
    'registrationExists':bool(list((root/'registry/applications').iterdir())),
    'operationCount':len(list((root/'ledger').iterdir()))+len(list((root/'recovery-operations').iterdir())),
    'restorePerformed':False}
assert not changed and not out['serviceUnitExists'] and not out['targetConfigurationExists'] and not out['controlConfigurationExists'] and not out['registrationExists'] and out['operationCount']==0
print(json.dumps(out))
'''

def verify(profile):
    return ssh(profile,'ROOT='+repr(ROOTS[profile['host'].split('.')[-1]])+'\nHOST='+repr(profile['host'])+'\n'+REMOTE)

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(verify,PROFILES))
    out={'schemaVersion':'SpugMainRestoreInstallationStatus/v1','state':'BLOCKED_TARGET_ADMISSION',
        'components':results,'localSpugUpdated':False,'restorePerformed':False,
        'blockers':{'172.30.30.57':'BACKEND_IDENTITY_INSPECTION_TIMEOUT_AND_UNSTABLE_RUNTIME',
            '172.30.30.58':'MINIO_EXTERNAL_WRITER_OWNERSHIP_UNCONFIRMED',
            '172.30.30.59':'MINIO_EXTERNAL_WRITER_OWNERSHIP_UNCONFIRMED'}}
    Path(__file__).with_name('installation-status.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))
