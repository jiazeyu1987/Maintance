"""Compare original definitions, unrelated runtime and protected mounted paths."""
import argparse,hashlib,json
from common import TASK,PRIVATE,now,write
from observe_closeout_hosts import i2_binding

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def definition(row):return {k:row[k] for k in ('Path','Args','HostConfig','Config','Image')}|dict(Mounts=sorted(row['Mounts'],key=lambda m:m['Destination']))
def runtime(row):return dict(state={k:row['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},restartCount=row['RestartCount'],networks=row['NetworkSettings']['Networks'])
def mount_rows(document,paths):
 rows=[]
 for line in document['mountinfo'].splitlines():
  fields=line.split();path=fields[4]
  if any(p==path or p.startswith(path.rstrip('/')+'/') or path.startswith(p.rstrip('/')+'/') for p in paths):rows.append(' '.join(fields[1:]))
 return sorted(rows)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['57','58','59']);parser.add_argument('--phase',required=True);args=parser.parse_args()
 assert args.phase.replace('-','').isalnum()
 suffix=args.suffix;before=json.loads((PRIVATE/('pre-install-'+suffix+'.private.json')).read_text(encoding='utf-8'));after=json.loads((PRIVATE/(args.phase+'-'+suffix+'.private.json')).read_text(encoding='utf-8'))
 old={r['Id']:r for r in before['containers']};new={r['Id']:r for r in after['containers']}
 assert set(old)<=set(new),'ORIGINAL_CONTAINER_REMOVED'
 added=set(new)-set(old)
 if suffix=='57' and not args.phase.startswith('after-failed-'):
  inventory=json.loads((TASK/'source-added-exporters.json').read_text(encoding='utf-8'))
  assert inventory['status']=='PASS' and inventory['originalContainerCount']==len(old)==195
  owned={r['containerId']:r for r in inventory['containers']}
  assert len(owned)==3 and added==set(owned),'UNEXPECTED_CONTAINER_ADDITION'
  for identity,expected in owned.items():
   assert digest(definition(new[identity]))==expected['definitionSha256'],'OWN_EXPORTER_DEFINITION_CHANGED'
   if expected['registered'] or new[identity]['State']['Running']:
    assert digest(runtime(new[identity]))==expected['runtimeSha256'],'OWN_EXPORTER_RUNTIME_CHANGED'
   else:
    cleanup=json.loads((TASK/'unused-exporters-stopped.json').read_text(encoding='utf-8'))
    stopped=next(r for r in cleanup['containers'] if r['containerId']==identity)
    assert cleanup['status']=='PASS' and stopped['retained'] and stopped['stopped'] and not new[identity]['State']['Paused'] and not new[identity]['State']['Restarting']
    assert digest(runtime(new[identity]))==stopped['afterRuntimeSha256'],'OWN_EXPORTER_STOPPED_STATE_CHANGED'
 else:assert not added,'UNEXPECTED_CONTAINER_ADDITION'
 owner=next(v for v in before['documents'].values() if before['targetConfigRef'] in v.get('targets',{}));target=owner['targets'][before['targetConfigRef']]
 if suffix=='57':
  capture=next(v for v in before['documents'].values() if v.get('schemaVersion')=='minimal-source-capture-config/v1')
  allowed=set(capture['source']['writerContainerIds'])|{capture['source']['minioContainerId'],'70c0487396f6954ec794230644cc5d01669c7c0ed217df7b6c4a35a722a5832a'}
 else:allowed={s['id'] for s in target['services']}
 for identity,row in old.items():
  assert digest(definition(row))==digest(definition(new[identity])),'ORIGINAL_DEFINITION_CHANGED_'+identity
  if identity not in allowed:assert digest(runtime(row))==digest(runtime(new[identity])),'OTHER_BUSINESS_RUNTIME_CHANGED_'+identity
 protected=['/mnt/nas','/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas']
 assert before['fstabSha256']==after['fstabSha256'],'FSTAB_CHANGED'
 assert mount_rows(before,protected)==mount_rows(after,protected),'PROTECTED_MOUNT_CHANGED'
 assert not after['activeReservation'] and after['http']['backend']['status']=='UP' and after['http']['frontend']['httpStatus']==200
 assert all(b'control_entry.py' in p['command'].encode() for p in after['processes']),'OWN_WORKER_REMAINS'
 report=dict(status='PASS',observedAt=now(),host='172.30.30.'+suffix,phase=args.phase,originalContainerCount=len(old),allOriginalDefinitionsAndImagesPreserved=True,otherBusinessRuntimePreserved=True,otherBusinessContainerCount=len(old)-len(allowed),allowedRuntimeChangeContainerIds=sorted(allowed),fstabPreserved=True,protectedMountsPreserved=True,backendHealth='UP',frontendHttp=200,activeReservation=False)
 if added:report.update(ownedAddedExportersVerified=True,ownedAddedExporterCount=len(added),registeredExporterContainerId=inventory['registeredContainerId'])
 if suffix=='57':
  if args.phase.startswith('after-failed-'):
   failed_attempt={'after-failed-365':'incremental-2','after-failed-366':'incremental-3'}[args.phase]
   report['failedOperationId']=json.loads((TASK/(failed_attempt+'-ui-submission.json')).read_text(encoding='utf-8'))['request']['operationId']
  elif args.phase=='closeout':
   binding=i2_binding(TASK,after['observedAt'])
   assert after['strictReadOnlyCollection'] is True and after['controlApiCalled'] is False
   assert after['backupOperationId']==binding['backupOperationId'] and after['automaticI2EvidencePins']==binding['automaticI2EvidencePins'],'CLOSEOUT_I2_SNAPSHOT_BINDING_CHANGED'
   report.update(binding)
  else:report['backupOperationId']=json.loads((TASK/'new-incremental-point-verified.json').read_text(encoding='utf-8'))['operationId']
  destination='source-after-backup-preservation.json'
  if args.phase.startswith('after-failed-'):destination='source-'+args.phase+'-preservation.json'
 else:destination='target-'+suffix+'-preservation.json'
 if args.phase=='closeout':destination=('source' if suffix=='57' else 'target-'+suffix)+'-closeout-preservation.json'
 write(TASK/destination,report);print(json.dumps(report))
