"""Verify this task's new terminal pins and NAS publication, read-only.

Payload readback is asserted from the original publisher evidence; this helper
does not claim to rehash every large payload or prove NAS server durability.
"""
import json
from repair_preflight import remote, TASK

SCRIPT = r'''
import datetime,hashlib,json,pathlib
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
operation=OPERATION_LITERAL
verified=[]
def read(pin):
 p=pathlib.Path(pin['path']);raw=p.read_bytes()
 assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'PIN_CHANGED'
 verified.append(pin)
 return json.loads(raw)
matches=[]
for p in (root/'registry/points').glob('*.json'):
 value=read(json.loads(p.read_bytes()))
 if value['reference']==operation:matches.append(value)
assert len(matches)==1,'NEW_POINT_NOT_PUBLISHED'
binding=matches[0]
assert binding['sourceConfigRef']=='intruoyi-57-safe-20261024-v1'
result=read(binding['resultPin'])
assert result['operationId']==operation and result['state']=='SUCCEEDED' and result['actualExitCode']==0 and result['failureCode'] is None
data=result['data'];manifest=read(data['manifestPin']);point=read(data['pointPin']);readback=read(data['readbackPin'])
assert manifest['pointType']=='FULL' and not manifest['parentPointPins']
assert point['integrityState']=='COMPLETE' and point['rehearsalEligible'] is True
assert point['controlledRestoreEligible'] is False and point['blockedReason']=='REPOSITORY_RECOVERY_NOT_RUN'
assert point['manifestPin']==data['manifestPin']==readback['manifestPin']
assert point['payloadRefs']==manifest['payloadRefs']==readback['payloadRefs']
assert readback['independentConnectionId'] and readback['serverDurabilityVerified'] is False
capture=read(data['captureResultPin'])
assert capture['operationId']==operation and capture['state']=='SUCCEEDED' and capture['actualExitCode']==0
restoration=read(capture['data']['sourceRestorationPin'])
assert restoration['schemaVersion']=='minimal-capture-source-restoration/v1' and restoration['restored'] is True and not restoration['errors']
assert point['readbackEvidencePin']==data['readbackPin']
close=read(point['ownerCloseEvidencePin']);terminal=read(point['originalExitEvidencePin'])
assert close['schemaVersion']=='RepositoryMinimumArchiveClose/v1' and close['operationId']==operation and close['archiveReaderClosed'] is True
assert close['closeResponse']['state']=='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF'
assert terminal['state']=='EXITED' and terminal['actualExitCode']==0 and terminal['processTerminated'] is True
evidence={'readback':{'schemaVersion':readback['schemaVersion'],'independentConnectionId':readback['independentConnectionId'],'serverDurabilityVerified':False},'close':{'archiveReaderClosed':True},'terminal':{'actualExitCode':0,'processTerminated':True}}
archive=pathlib.Path(data['manifestPin']['path']).parent.parent
assert archive.is_dir() and '/nas/Backup/BackupPackage/' in str(archive)
report={'observedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'operationId':operation,'state':result['state'],'finishedAt':result['finishedAt'],'pointType':manifest['pointType'],'backupId':manifest['backupId'],'commonRecoveryPoint':manifest['commonRecoveryPoint'],'integrityState':point['integrityState'],'rehearsalEligible':point['rehearsalEligible'],'controlledRestoreEligible':point['controlledRestoreEligible'],'controlledRestoreBlockedReason':point['blockedReason'],'registeredTargetAdmissionRequired':True,'manifestPin':data['manifestPin'],'pointPin':data['pointPin'],'archivePath':str(archive),'payloadFiles':len(manifest['payloadRefs']),'payloadBytes':sum(p['bytes'] for p in manifest['payloadRefs']),'verifiedSmallDocumentPins':len(verified),'sourceStartCommandsCompleted':restoration['restored'],'sourceIndependentHealthCheckRequired':True,'evidence':evidence,'serverDurabilityVerified':False}
print(json.dumps(report))
'''
if __name__ == '__main__':
    operation=json.loads((TASK/'full-ui-submission.json').read_text(encoding='utf-8'))['request']['operationId']
    report=remote('172.30.30.57',SCRIPT.replace('OPERATION_LITERAL',repr(operation)),timeout=55)
    (TASK/'new-full-point-verified.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report))
