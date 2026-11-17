import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,'C:/Spug/runtime/private/spug-backup59-mvp-20261116')
import collect59
root=Path(__file__).parent
private=collect59.ROOT
docker='C:/Users/D01021/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe'
container='intruoyi-spug-transfer-spug-1'
target='/var/lib/intruoyi-spug/prepare-target.private.json'
apply='--apply' in sys.argv[1:]
repair='--repair-storage' in sys.argv[1:]
assert set(sys.argv[1:]) <= {'--apply','--repair-storage'}
receipt=json.loads((private/'bootstrap59-receipt.private.json').read_text(encoding='utf-8'))
collect59.PY=receipt['pythonPath']
before=root/'prepare-wrapper-before.private.json'
subprocess.run([docker,'cp',container+':'+target,str(before)],check=True,capture_output=True)
wrapper=json.loads(before.read_text(encoding='utf-8'))
assert wrapper['nativeConfigurationPin']==receipt['nativeConfigurationPin']
resolved=json.loads((root/'prepare-point-resolved.private.json').read_text(encoding='utf-8'))
baseline=json.loads((root/'acceptance/selected-chain-acceptance-baseline.private.json').read_text(encoding='utf-8'))
assert baseline['chainBindingVerified'] and baseline['backupFinalSuccessVerified']
expected=receipt['nativeConfigurationPin']
old=collect59.remote("import json,hashlib; from pathlib import Path; p="+repr(expected)+"; raw=Path(p['path']).read_bytes(); assert len(raw)==p['bytes'] and hashlib.sha256(raw).hexdigest()==p['sha256']; print(raw.decode('utf-8'))")
entry=dict(old['points'][baseline['parentBackupId']])
entry['imageArchivePin']=resolved['archivePin']
entry['roleImages']=dict(entry['roleImages'])
entry['roleImages']['backend']='sha256:38b553011ea540830fc9302167b2bf9eb76d3f18e4d6e2ddd38eab749172626d'
entry['roleImages']['frontend']='sha256:e0648d3c40d5984ca484ca1c518d8d982321429b275c88978b802d6df65356bc'
assert set(entry['roleImages'].values())=={'sha256:'+Path(m['Config']).name for m in resolved['manifest']}
if repair:
 policy=entry['fileStorage']
 entry=dict(old['points'][resolved['pointId']])
 assert not entry.get('fileStorage'), 'STORAGE_POLICY_ALREADY_PRESENT'
 entry['fileStorage']=policy
payload=dict(expected=receipt['nativeConfigurationPin'],entry=entry,point=resolved['pointId'],apply=apply,repair=repair)
code='''import json,hashlib,importlib.util
from pathlib import Path
p=PAYLOAD
path=Path(p['expected']['path']);raw=path.read_bytes()
assert len(raw)==p['expected']['bytes'] and hashlib.sha256(raw).hexdigest()==p['expected']['sha256'], 'CONFIG_CHANGED'
c=json.loads(raw)
assert (p['point'] in c['points']) == p['repair'], 'POINT_REGISTRATION_MODE_MISMATCH'
c['points'][p['point']]=p['entry']
spec=importlib.util.spec_from_file_location('native','/mnt/intruoyi-data/recovery-tools/prepare_target_native.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
n=m.NativePreparation(c)
with n.host_lock():
 assert not (Path(c['hostReservationRoot'])/'active.json').exists(), 'RESTORE_ACTIVE'
 n.plan({'applicationId':p['entry']['applicationId'],'recoveryPointRef':p['point']})
 updated=json.dumps(c,indent=2).encode('utf-8')
 if p['apply']:
  path.write_bytes(updated)
  assert path.read_bytes()==updated
print(json.dumps({'applied':p['apply'],'plan':'PASS','point':p['point'],'nativeConfigurationPin':{'path':str(path),'bytes':len(updated),'sha256':hashlib.sha256(updated).hexdigest()}}))
'''.replace('PAYLOAD',repr(payload))
result=collect59.remote(code)
if apply:
 wrapper['nativeConfigurationPin']=result['nativeConfigurationPin']
 staged=root/'prepare-wrapper-updated.private.json'
 staged.write_text(json.dumps(wrapper,indent=2),encoding='utf-8')
 subprocess.run([docker,'cp',str(staged),container+':'+target],check=True,capture_output=True)
 subprocess.run([docker,'exec',container,'chmod','600',target],check=True,capture_output=True)
 after=root/'prepare-wrapper-after.private.json'
 subprocess.run([docker,'cp',container+':'+target,str(after)],check=True,capture_output=True)
 assert json.loads(after.read_text(encoding='utf-8'))==wrapper
 receipt['nativeConfigurationPin']=result['nativeConfigurationPin']
 old['points'][resolved['pointId']]=entry
 for name,value in [('bootstrap59-receipt.private.json',receipt),('prepare-target59.private.json',old),('prepare-target.private.json',wrapper)]:
  (private/name).write_text(json.dumps(value,indent=2),encoding='utf-8')
 (root/'prepare-point-registration.private.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
