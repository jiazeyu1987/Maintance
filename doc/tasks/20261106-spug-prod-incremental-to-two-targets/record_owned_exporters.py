"""Record exactly the three task-created tools from preserved actual snapshots."""
import json
from common import TASK,PRIVATE,now,write
from verify_host_preservation import definition,digest,runtime

if __name__=='__main__':
 destination=TASK/'source-added-exporters.json';private=PRIVATE/'source-added-exporters.private.json'
 assert not destination.exists() and not private.exists(),'EXPORTER_INVENTORY_ALREADY_RECORDED'
 old=json.loads((PRIVATE/'pre-install-57.private.json').read_text(encoding='utf-8'))
 current=json.loads((PRIVATE/'tmpfs-installed-57.private.json').read_text(encoding='utf-8'))
 original={r['Id'] for r in old['containers']};added=[r for r in current['containers'] if r['Id'] not in original]
 assert len(original)==195 and len(added)==3,'UNEXPECTED_CONTAINER_ADDITION'
 registered=json.loads((TASK/'binlog-tmpfs-tool-provisioned.json').read_text(encoding='utf-8'))
 mysql=registered['sourceMysqlContainerId'];prefix='/spug-intruoyi57-binlog-tmpfs-20261107-v'
 assert {r['Name'] for r in added}=={prefix+str(i) for i in (1,2,3)}
 assert next(r for r in added if r['Name']==prefix+'3')['Id']==registered['containerId']
 assert next(r for r in added if r['Name']==prefix+'1')['Id']=='a7aa973f623ad07adb82c25f9b5f352db74a00ea2abf22a8fbd0b4db4cdfeb2f'
 public=[]
 for r in sorted(added,key=lambda r:r['Name']):
  host=r['HostConfig'];generation=int(r['Name'][-1])
  assert r['Image']==registered['imageId'] and r['Path']=='sleep' and r['Args']==['infinity'] and r['State']['Running']
  assert host['ReadonlyRootfs'] and host['NetworkMode']==host['PidMode']=='container:'+mysql
  assert host['Tmpfs']==registered['tmpfs'] and not host.get('Binds') and all(m['Type']=='tmpfs' for m in r['Mounts'])
  assert host['Memory']==host['MemorySwap']==registered['memoryBytes'] and host['PidsLimit']==registered['pidsLimit']
  assert host['CapDrop']==['ALL'] and (host.get('CapAdd') or [])==(['DAC_OVERRIDE'] if generation==2 else [])
  assert r['Config']['User']==('999:999' if generation==3 else '')
  public.append(dict(containerId=r['Id'],name=r['Name'][1:],generation=generation,registered=generation==3,definitionSha256=digest(definition(r)),runtimeSha256=digest(runtime(r)),retainedForFailureEvidence=generation!=3))
 write(private,dict(observedAt=current['observedAt'],containers=added))
 report=dict(status='PASS',observedAt=now(),snapshotObservedAt=current['observedAt'],originalContainerCount=len(original),addedContainerCount=len(added),registeredContainerId=registered['containerId'],containers=public,noServerActionPerformed=True)
 write(destination,report);print(json.dumps(report))
