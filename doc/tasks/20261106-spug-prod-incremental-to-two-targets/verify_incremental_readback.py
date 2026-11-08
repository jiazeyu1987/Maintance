"""Audit complete independent SAFE readback records without another large read."""
import ast,json
from common import TASK,PRIVATE,active_source_installation,remote,write

if __name__=='__main__':
 previous=TASK.parent/'20261105-spug-full-to-prod/verify_preservation_payload.py'
 tree=ast.parse(previous.read_text(encoding='utf-8'))
 script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCRIPT' for t in n.targets))
 script=script.replace("==116","==127").replace("=116","=127").replace("=='FULL'","=='INCREMENTAL'").replace('PreservationSafeFullReadbackAudit/v1','IncrementalSafeFullReadbackAudit/v1')
 script=script.replace("reviewed=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/engine-mainv2-db64656/common/repository_native_readback.py')","reviewed=engine/'common/repository_native_readback.py'")
 point=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf-8'));installed=active_source_installation()
 build=json.loads((TASK/'release-build-d487abf.json').read_text(encoding='utf-8'))
 assert build['status']==installed['status']=='PASS' and installed['fileManifestSha256']==build['fileManifestSha256']
 import tarfile,hashlib
 archive=PRIVATE/'package-d487abf/backup-restore-standard.tgz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==build['packageSha256']
 with tarfile.open(archive) as package:
  def ref(name):
   raw=package.extractfile(name).read();return dict(path=installed['engine']+'/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  engine=dict(status='PASS',operationId=point['operationId'],variant='standard',allInstalledFilesShaVerified=True,payloadContentVerification=True,engine=installed['engine'],fileCount=127,fileManifestSha256=installed['fileManifestSha256'],repositoryProgramPin=ref('common/repository_minimal.py'),fullReaderPin=ref('common/repository_native_readback.py'))
 payload='PRESERVATION='+repr(point)+'\nENGINE_EVIDENCE='+repr(engine)+'\n'+script
 value=remote('172.30.30.57',payload,150)
 assert value['status']=='PASS' and value['payloadFiles']==point['payloadFiles'] and value['payloadBytes']==point['payloadBytes']
 write(TASK/'new-incremental-payload-readback.json',value);print(json.dumps(value))
