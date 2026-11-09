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
def _verify_installation_receipt_custody(custody,*,read_pin=None,terminal_receipt_pin=None):
 import hashlib,json,os,pathlib,stat
 def need(value,code):
  if not value:raise ValueError(code)
 def identity(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
 verified=[]
 def physical(ref,parse=True):
  need(set(ref)=={'path','bytes','sha256'} and 0<ref['bytes']<=32*1024*1024,'RECEIPT_PIN_INVALID')
  p=pathlib.Path(ref['path'])
  try:before=p.lstat()
  except OSError as error:raise ValueError('RECEIPT_PIN_UNAVAILABLE') from error
  need(p.resolve()==p and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'RECEIPT_PATH_INVALID')
  with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
   need(identity(os.fstat(stream.fileno()))==identity(before),'RECEIPT_IDENTITY_CHANGED');raw=stream.read()
   need(identity(os.fstat(stream.fileno()))==identity(before),'RECEIPT_IDENTITY_CHANGED')
  need(identity(p.lstat())==identity(before) and len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'RECEIPT_PIN_CHANGED')
  return json.loads(raw) if parse else raw
 def readpin(ref,parse=True):
  actual=terminal_receipt_pin if terminal_receipt_pin is not None and ref==custody['steps'][-1]['currentReceiptPin'] else ref
  value=physical(actual,parse) if read_pin is None else read_pin(actual,parse=parse)
  verified.append(actual)
  return value
 def samebytes(a,b):return all(a[k]==b[k] for k in ('bytes','sha256'))
 root=pathlib.PurePosixPath(custody['root']);steps=custody['steps'];original=custody['originalActiveReceiptPin']
 need(str(root) in ('/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3','/mnt/intruoyi-data/spug-main-restore-20261104-v3'),'RECEIPT_ROOT_INVALID')
 need(original['path']==str(root/'target-installation.json'),'ORIGINAL_RECEIPT_PATH_INVALID')
 need(len(steps)==len(custody['expectedGenerationCommits']) and len(steps)>0,'RECEIPT_CHAIN_LENGTH_INVALID')
 need([s['sourceCommit'] for s in steps]==custody['expectedGenerationCommits'],'RECEIPT_GENERATION_ORDER_CHANGED')
 need(samebytes(original,steps[0]['previousReceiptPin']),'ORIGINAL_RECEIPT_CUSTODY_MISMATCH')
 archives=[]
 for i,step in enumerate(steps):
  ref=step['previousReceiptPin'];p=pathlib.PurePosixPath(ref['path'])
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

def verify_installation_receipt_custody(custody,*,read_pin=None):
 return _verify_installation_receipt_custody(custody,read_pin=read_pin)

def verify_installation_receipt_custody_at(custody,terminal_receipt_pin,*,read_pin=None):
 import pathlib,re
 def need(value,code):
  if not value:raise ValueError(code)
 root=pathlib.PurePosixPath(custody['root']);path=pathlib.PurePosixPath(terminal_receipt_pin['path'])
 logical=custody['steps'][-1]['currentReceiptPin']
 need(path.parent==root/'configuration' and re.fullmatch('target-installation-before-main-[0-9a-f]{7}'+r'\.json',path.name),
  'RECEIPT_TERMINAL_ARCHIVE_PATH_INVALID')
 need(set(terminal_receipt_pin)=={'path','bytes','sha256'} and all(terminal_receipt_pin[k]==logical[k] for k in ('bytes','sha256')),
  'RECEIPT_TERMINAL_ARCHIVE_MISMATCH')
 result=_verify_installation_receipt_custody(custody,read_pin=read_pin,terminal_receipt_pin=terminal_receipt_pin)
 return dict(result,logicalTerminalPin=logical,physicalTerminalPin=terminal_receipt_pin)

def verify_layered_receipt_custody(custody,*,read_pin=None):
 import hashlib,json,pathlib,re
 def need(value,code):
  if not value:raise ValueError(code)
 fields={'schemaVersion','root','targetConfigRef','sourceConfigRef','service','legacyCustody','mainSteps',
  'originalInventory','selectedOwnerPin','selectedControlPin','selectedCurrentReceiptPin'}
 need(type(custody) is dict and set(custody)==fields and custody['schemaVersion']=='MainProgramReceiptCustody/v1',
  'CUSTODY_SCHEMA_INVALID')
 legacy=custody['legacyCustody'];steps=custody['mainSteps'];root=pathlib.PurePosixPath(custody['root'])
 need(type(steps) is list and 0<len(steps)<=64 and all(custody[k]==legacy[k] for k in
  ('root','targetConfigRef','sourceConfigRef','service')),'CUSTODY_IDENTITY_CHANGED')
 expected_fields={'sourceCommit','engine','previousReceiptPin','currentReceiptPin','ownerConfigurationPin','controlConfigurationPin','dropinPin','packagePin'}
 need(all(type(s) is dict and set(s)==expected_fields for s in steps),'CUSTODY_STEP_INVALID')
 need(len({s['sourceCommit'] for s in steps})==len(steps),'CUSTODY_GENERATION_REPEATED')
 before=verify_installation_receipt_custody_at(legacy,steps[0]['previousReceiptPin'],read_pin=read_pin)
 verified=list(before['verifiedPins'])
 def pinned(ref,parse=True):
  if read_pin is None:
   # The same strict physical reader is used without granting path exceptions.
   import os,stat
   need(type(ref) is dict and set(ref)=={'path','bytes','sha256'} and type(ref['bytes']) is int and
    0<ref['bytes']<=32*1024*1024,'RECEIPT_PIN_INVALID')
   p=pathlib.Path(ref['path']);a=p.lstat();identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
   need(p.resolve()==p and stat.S_ISREG(a.st_mode) and a.st_nlink==1,'RECEIPT_PATH_INVALID')
   with os.fdopen(os.open(p,os.O_RDONLY|os.O_NOFOLLOW),'rb') as stream:
    need(identity(os.fstat(stream.fileno()))==identity(a),'RECEIPT_IDENTITY_CHANGED');raw=stream.read(32*1024*1024+1)
    need(identity(os.fstat(stream.fileno()))==identity(a),'RECEIPT_IDENTITY_CHANGED')
   need(identity(p.lstat())==identity(a) and len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'RECEIPT_PIN_CHANGED')
   value=json.loads(raw) if parse else raw
  else:value=read_pin(ref,parse=parse)
  verified.append(ref);return value
 previous_receipts=[pinned(s['previousReceiptPin']) for s in steps]
 current=pinned(steps[-1]['currentReceiptPin']);receipts=previous_receipts+[current]
 previous_owner=pinned(legacy['selectedOwnerPin'])
 for index,step in enumerate(steps):
  need(type(step['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}',step['sourceCommit']),'CUSTODY_COMMIT_INVALID')
  previous_pin=step['previousReceiptPin'];prior=legacy['steps'][-1]['currentReceiptPin'] if index==0 else steps[index-1]['currentReceiptPin']
  need(all(previous_pin[k]==prior[k] for k in ('bytes','sha256')),'RECEIPT_ACTIVATION_CHAIN_GAP')
  need(previous_pin['path']==str(root/'configuration'/('target-installation-before-main-'+step['sourceCommit'][:7]+'.json')) and
   step['currentReceiptPin']['path']==str(root/'target-installation.json'),'RECEIPT_MAIN_PATH_INVALID')
  previous,next_value=receipts[index:index+2]
  need(previous['targetConfigRef']==next_value['targetConfigRef']==custody['targetConfigRef'] and
   previous['service']==next_value['service']==custody['service'],'RECEIPT_MAIN_IDENTITY_CHANGED')
  expected=dict(previous,**{k:step[k] for k in ('sourceCommit','engine','ownerConfigurationPin','controlConfigurationPin')})
  need(next_value==expected,'RECEIPT_ACTIVATION_CONTRACT_CHANGED')
  owner=pinned(step['ownerConfigurationPin']);control=pinned(step['controlConfigurationPin']);pinned(step['dropinPin'],False)
  need(owner['targets']==previous_owner['targets'],'HISTORICAL_TARGET_CHANGED')
  if index:need({k:v for k,v in owner.items() if k!='formalModuleDirectory'}==
   {k:v for k,v in previous_owner.items() if k!='formalModuleDirectory'},'HISTORICAL_MAIN_OWNER_CHANGED')
  need(owner['formalModuleDirectory']==step['engine']+'/formal' and
   control['restoreConfigurations'][custody['sourceConfigRef']][custody['targetConfigRef']]==step['ownerConfigurationPin'],
   'RECEIPT_MAIN_CONFIGURATION_CHANGED')
  need(step['packagePin']['path']==step['engine']+'/package.json','RECEIPT_PACKAGE_PATH_CHANGED')
  package=pinned(step['packagePin']);manifest=json.dumps(package['files'],sort_keys=True,separators=(',',':')).encode()
  need(hashlib.sha256(manifest).hexdigest()==package['packageSha256'],'RECEIPT_PACKAGE_MANIFEST_CHANGED')
  previous_owner=owner
 need(custody['selectedCurrentReceiptPin']==steps[-1]['currentReceiptPin'] and
  custody['selectedOwnerPin']==steps[-1]['ownerConfigurationPin'] and custody['selectedControlPin']==steps[-1]['controlConfigurationPin'],
  'SELECTED_INSTALLATION_CHANGED')
 inventory=custody['originalInventory'];refs=inventory['evidencePins'];active=legacy['originalActiveReceiptPin']
 need(inventory['status']=='PASS' and len(refs)==inventory['protectedFiles'] and
  len({r['path'] for r in refs})==len(refs) and [r for r in refs if r['path']==active['path']]==[active],
  'ORIGINAL_INVENTORY_CHANGED')
 for ref in refs:
  if ref['path']!=active['path']:pinned(ref,False)
 return dict(status='PASS',activationCount=len(legacy['steps'])+len(steps),legacyActivationCount=len(legacy['steps']),
  legacyLogicalTerminalPin=before['logicalTerminalPin'],legacyPhysicalTerminalPin=before['physicalTerminalPin'],
  selectedCurrentReceiptPin=steps[-1]['currentReceiptPin'],originalInventoryVerified=True,
  allReceiptAndConfigurationPinsVerified=True,packageManifestsVerified=True,
  verifiedPins=list({r['path']:r for r in verified}.values()),serverWrites=False)
'''

# Definitions only. The identical source remains embeddable in read-only remote
# verification; importing the module does not read receipts or contact hosts.
exec(SCRIPT)
