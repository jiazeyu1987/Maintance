"""Audit this task's exact authorized active-receipt activation chains."""
import json
from common import TASK,SOURCE,allocator_installation

SEQUENCES={
 '58':[
  ('allocator-target-installation-58.json','9a65b5a6767cbb64d3f9668aa47bcc57229f0818'),
  ('allocator-target-installation-58-r2.json','701b4422426d517f00aad23e71732b54c8b19724'),
  ('allocator-target-installation-58-r3.json','7c5f0573e7e1ed7a54e42dbb614cb6e1f0a0534b'),
  ('frontend-target-installation-58.json','9c93449e99ae0790c8678a570d78a98b61d96d87'),
  ('packaged-frontend-target-installation-58.json','0c5828a63e387fe55594450bf2121cd4b31a7d8a')],
 '59':[
  ('allocator-target-installation-59.json','7c5f0573e7e1ed7a54e42dbb614cb6e1f0a0534b'),
  ('frontend-target-installation-59.json','9c93449e99ae0790c8678a570d78a98b61d96d87')]}

def inputs(suffix):
 assert suffix in SEQUENCES
 root=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3'
 inventory=json.loads((TASK/('protected-history-'+suffix+'.json')).read_text(encoding='utf8'))['evidencePins']
 active=[p for p in inventory if p['path']==root+'/target-installation.json']
 assert len(active)==1 and len({p['path'] for p in inventory})==len(inventory)
 steps=[]
 for name,commit in SEQUENCES[suffix]:
  report=json.loads((TASK/name).read_text(encoding='utf8'))
  assert report['status']=='PASS' and report['sourceCommit']==commit and report['host']=='172.30.30.'+suffix
  assert report['targetAndSourceConfigurationUnchanged'] and report['previousGenerationsRetained'] and not report['restoreDispatched']
  steps.append({k:report[k] for k in ('sourceCommit','engine','previousReceiptPin','currentReceiptPin','ownerConfigurationPin','controlConfigurationPin','dropinPin')})
 selected=allocator_installation(suffix)
 assert selected['currentReceiptPin']==steps[-1]['currentReceiptPin'] and selected['sourceCommit']==steps[-1]['sourceCommit']
 return [p for p in inventory if p!=active[0]],dict(root=root,targetConfigRef='intruoyi-main-'+suffix+'-safe-restore-20261104-v1',
  sourceConfigRef=SOURCE,service=selected['service'],originalActiveReceiptPin=active[0],
  expectedGenerationCommits=[commit for _,commit in SEQUENCES[suffix]],steps=steps,
  selectedOwnerPin=selected['ownerConfigurationPin'],selectedControlPin=selected['controlConfigurationPin'])

SCRIPT=r'''
def verify_installation_receipt_custody(custody):
 import hashlib,json,os,pathlib,stat
 def need(value,code):
  if not value:raise ValueError(code)
 def identity(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 verified=[]
 def readpin(ref,parse=True):
  need(set(ref)=={'path','bytes','sha256'} and 0<ref['bytes']<=32*1024*1024,'RECEIPT_PIN_INVALID')
  p=pathlib.Path(ref['path'])
  try:before=p.lstat()
  except OSError as error:raise ValueError('RECEIPT_PIN_UNAVAILABLE') from error
  need(p.resolve()==p and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'RECEIPT_PATH_INVALID')
  with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
   need(identity(os.fstat(stream.fileno()))==identity(before),'RECEIPT_IDENTITY_CHANGED');raw=stream.read()
   need(identity(os.fstat(stream.fileno()))==identity(before),'RECEIPT_IDENTITY_CHANGED')
  need(identity(p.lstat())==identity(before) and len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'RECEIPT_PIN_CHANGED')
  verified.append(ref)
  return json.loads(raw) if parse else raw
 def samebytes(a,b):return all(a[k]==b[k] for k in ('bytes','sha256'))
 root=pathlib.Path(custody['root']);steps=custody['steps'];original=custody['originalActiveReceiptPin']
 need(str(root) in ('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3','/mnt/intruoyi-data/spug-main-restore-20261104-v3'),'RECEIPT_ROOT_INVALID')
 need(original['path']==str(root/'target-installation.json'),'ORIGINAL_RECEIPT_PATH_INVALID')
 need(len(steps)==len(custody['expectedGenerationCommits']) and len(steps)>0,'RECEIPT_CHAIN_LENGTH_INVALID')
 need([s['sourceCommit'] for s in steps]==custody['expectedGenerationCommits'],'RECEIPT_GENERATION_ORDER_CHANGED')
 need(samebytes(original,steps[0]['previousReceiptPin']),'ORIGINAL_RECEIPT_CUSTODY_MISMATCH')
 archives=[]
 for i,step in enumerate(steps):
  ref=step['previousReceiptPin'];p=pathlib.Path(ref['path'])
  need(p.parent==root/'configuration' and p.name.endswith('-previous-target-installation.json'),'ARCHIVED_RECEIPT_PATH_INVALID')
  need(step['currentReceiptPin']['path']==str(root/'target-installation.json'),'ACTIVE_RECEIPT_PATH_INVALID')
  if i:need(samebytes(ref,steps[i-1]['currentReceiptPin']),'RECEIPT_ACTIVATION_CHAIN_GAP')
  archives.append(readpin(ref))
 active=readpin(steps[-1]['currentReceiptPin']);receipts=archives+[active]
 baseline_owner=readpin(archives[0]['ownerConfigurationPin'])
 for i,step in enumerate(steps):
  previous=receipts[i];current=receipts[i+1]
  need(previous['targetConfigRef']==current['targetConfigRef']==custody['targetConfigRef'],'RECEIPT_TARGET_CHANGED')
  need(previous['service']==current['service']==custody['service'],'RECEIPT_SERVICE_CHANGED')
  expected=dict(previous,sourceCommit=step['sourceCommit'],engine=step['engine'],
   ownerConfigurationPin=step['ownerConfigurationPin'],controlConfigurationPin=step['controlConfigurationPin'])
  need(current==expected,'RECEIPT_ACTIVATION_CONTRACT_CHANGED')
  owner=readpin(step['ownerConfigurationPin']);control=readpin(step['controlConfigurationPin'])
  need(owner['targets']==baseline_owner['targets'] and owner['sources']==baseline_owner['sources'],'HISTORICAL_SOURCE_OR_TARGET_CHANGED')
  need(owner['formalModuleDirectory']==step['engine']+'/formal','RECEIPT_ENGINE_BINDING_CHANGED')
  need(control['restoreConfigurations'][custody['sourceConfigRef']][custody['targetConfigRef']]==step['ownerConfigurationPin'],'RECEIPT_CONTROL_OWNER_BINDING_CHANGED')
  readpin(previous['ownerConfigurationPin']);readpin(previous['controlConfigurationPin']);readpin(step['dropinPin'],False)
 need(active['ownerConfigurationPin']==custody['selectedOwnerPin'] and active['controlConfigurationPin']==custody['selectedControlPin'],'SELECTED_INSTALLATION_CHANGED')
 return dict(status='PASS',authorizedActiveReceiptCount=1,originalReceiptArchived=True,
  originalActiveReceiptPin=original,originalArchivedReceiptPin=steps[0]['previousReceiptPin'],
  activatedGenerationCommits=custody['expectedGenerationCommits'],activationCount=len(steps),
  selectedCurrentReceiptPin=steps[-1]['currentReceiptPin'],allReceiptAndConfigurationPinsVerified=True,
  allHistoricalSourceAndTargetDefinitionsUnchanged=True,verifiedPins=verified,serverWrites=False)
'''
