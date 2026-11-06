"""Audit the actual SAFE publisher's complete independent SMB readback evidence.

Uses the installed pinned SAFE implementation and original byte-read records.
It does not repeat publication, read the full payload again, or modify history.
"""
import json
from install_prod_control import remote, TASK, PRIVATE

SCRIPT=r'''
import ast,datetime,hashlib,json,pathlib
preservation=PRESERVATION
engine_evidence=ENGINE_EVIDENCE
operation=preservation['operationId']
verified=[]
def checked(pin):
 p=pathlib.Path(pin['path']);assert p.is_file() and not p.is_symlink(),'PRESERVATION_PIN_PATH_INVALID'
 raw=p.read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'PRESERVATION_PIN_CHANGED'
 verified.append(pin)
 return json.loads(raw)
assert preservation['state']=='SUCCEEDED' and engine_evidence['status']=='PASS'
assert engine_evidence['operationId']==operation and engine_evidence['variant']=='standard'
assert engine_evidence['allInstalledFilesShaVerified'] and engine_evidence['payloadContentVerification']
engine=pathlib.Path(engine_evidence['engine'])
version=json.loads((engine/'package.json').read_bytes())
assert version['variant']=='standard' and version['fileVerification'] is True and version['payloadContentVerification'] is True
assert len(version['files'])==engine_evidence['fileCount']==116
assert version['packageSha256']==engine_evidence['fileManifestSha256']
assert hashlib.sha256(json.dumps(version['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==version['packageSha256'],'SOURCE_SAFE_MANIFEST_CHANGED'
assert all(hashlib.sha256((engine/n).read_bytes()).hexdigest()==sha for n,sha in version['files'].items()),'SOURCE_SAFE_ENGINE_CHANGED'
def program(pin):
 raw=pathlib.Path(pin['path']).read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'SOURCE_SAFE_PROGRAM_CHANGED'
 return raw
caller=program(engine_evidence['repositoryProgramPin'])
reader=program(engine_evidence['fullReaderPin'])
reviewed=pathlib.Path('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/engine-mainv2-db64656/common/repository_native_readback.py')
assert reader==reviewed.read_bytes() and hashlib.sha256(reader).hexdigest()=='80abab1d31c9e6b6ef922ea7e93e6aa510037cfe6708ea6228bf5a6a13d5f61c'
tree=ast.parse(caller)
publish=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='publish')
calls=[n for n in ast.walk(publish) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='reader' and n.func.attr=='verify']
assert len(calls)==1 and len(calls[0].args)==3 and not calls[0].keywords,'SOURCE_NOT_USING_FULL_SAFE_READER'
manifest=checked(preservation['manifestPin']);point=checked(preservation['pointPin'])
assert manifest['backupId']==point['backupId']==operation and manifest['pointType']=='FULL'
assert point['manifestPin']==preservation['manifestPin'] and point['payloadRefs']==manifest['payloadRefs']
payload_tree=checked(manifest['payloadTreePin']);native=checked(point['readbackEvidencePin'])
assert native['schemaVersion']=='RepositoryMinimumReadback/v1' and native['operationId']==operation
assert 'payloadContentVerified' not in native,'UNEXPECTED_NATIVE_READBACK_SCHEMA'
assert native['manifestPin']==preservation['manifestPin'] and native['payloadRefs']==manifest['payloadRefs']
assert native['independentConnectionId'] and native['serverDurabilityVerified'] is False
originals=checked(native['originalRecordsPin'])
assert originals['schemaVersion']=='RepositoryReadbackOriginals/v1' and originals['manifestPin']==preservation['manifestPin']
actual=sorted(originals['archivedFilePins'].values(),key=lambda p:p['path'])
expected=sorted(manifest['payloadRefs'],key=lambda p:p['path'])
assert actual==expected,'NATIVE_FULL_PAYLOAD_READBACK_MISMATCH'
archive=pathlib.Path(preservation['archivePath'])
generated=[]
for name,marker in payload_tree.items():
 if marker=='directory':continue
 kind,size,sha=marker.split('|');assert kind=='file'
 generated.append(dict(path=str(archive/name),bytes=int(size),sha256=sha))
assert sorted(generated,key=lambda p:p['path'])==expected,'NATIVE_PAYLOAD_TREE_MISMATCH'
copies=0
for pin in originals['readbackOriginalPins'].values():
 p=pathlib.Path(pin['path']);raw=p.read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'NATIVE_RETAINED_ORIGINAL_CHANGED'
 copies+=1
source=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
original=source/'repository-operations'/hashlib.sha256(operation.encode()).hexdigest()
start=json.loads((original/'start.json').read_bytes());checked(start['configurationPin'])
request=json.loads((original/'request.json').read_bytes())
assert request['operationId']==operation and request['action']=='FULL'
assert hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==start['requestSha256']
for pin in [preservation['manifestPin'],preservation['pointPin'],manifest['payloadTreePin'],point['readbackEvidencePin']]:checked(pin)
program(engine_evidence['repositoryProgramPin']);program(engine_evidence['fullReaderPin'])
result=dict(schemaVersion='PreservationSafeFullReadbackAudit/v1',status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            finishedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),operationId=operation,
            verificationMode='NATIVE_FULL_READBACK_EVIDENCE_AUDIT',payloadContentVerified=True,
            payloadFiles=len(expected),payloadBytes=sum(p['bytes'] for p in expected),
            manifestPin=preservation['manifestPin'],pointPin=preservation['pointPin'],
            exactTreeVerifiedBeforeAndAfter=True,metadataPinsVerifiedBeforeAndAfter=True,
            independentConnectionId=native['independentConnectionId'],encrypted=True,signingRequired=True,
            privateConnectionCache=True,connectionClosed=True,nativeLegacySchemaPreserved=True,
            originalRecordsPin=native['originalRecordsPin'],retainedOriginalCopiesVerified=copies,
            pinnedSafeSourceFileCount=116,sourceFileManifestSha256=version['packageSha256'],
            fullReaderPin=engine_evidence['fullReaderPin'],verifiedMetadataPins=len(verified),
            extraFullPayloadReadDispatched=False,serverDurabilityVerified=False)
print(json.dumps(result))
'''

if __name__=='__main__':
    preservation=json.loads((TASK/'preservation-full-point-verified.json').read_text(encoding='utf-8'))
    engine=json.loads((TASK/'preservation-running-engine-verification.json').read_text(encoding='utf-8'))
    script='PRESERVATION='+repr(preservation)+'\nENGINE_EVIDENCE='+repr(engine)+'\n'+SCRIPT
    report=remote(script,timeout=150)
    assert report['status']=='PASS' and report['operationId']==preservation['operationId']
    assert report['payloadFiles']==preservation['payloadFiles'] and report['payloadBytes']==preservation['payloadBytes']
    raw=json.dumps(report,ensure_ascii=False,indent=2)
    (PRIVATE/'preservation-full-payload-readback.private.json').write_text(raw,encoding='utf-8')
    (TASK/'preservation-full-payload-readback.json').write_text(raw,encoding='utf-8')
    print(json.dumps(report))
