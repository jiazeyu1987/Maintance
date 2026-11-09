"""Real temporary receipt bytes through an explicit local path-reader seam.

The seam maps registered Linux paths onto a temporary filesystem. It does not
simulate a remote installation or return a successful custody observation.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

TASK=Path(__file__).resolve().parent
sys.path.insert(0,str(TASK))
import installation_history_custody as subject

ROOT='/mnt/intruoyi-data/spug-main-restore-20261104-v3'
SOURCE='intruoyi-57-safe-20261024-v1'
TARGET='intruoyi-main-59-safe-restore-20261104-v1'


def raw(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


@pytest.fixture
def receipts(tmp_path):
    files={}
    def put(path,value):
        payload=value if isinstance(value,bytes) else raw(value)
        actual=tmp_path/str(len(files));actual.write_bytes(payload);files[path]=actual
        return dict(path=path,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    def reader(ref,parse=True):
        path=files[ref['path']];before=path.stat();payload=path.read_bytes();after=path.stat()
        assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
        if len(payload)!=ref['bytes'] or hashlib.sha256(payload).hexdigest()!=ref['sha256']:
            raise ValueError('RECEIPT_PIN_CHANGED')
        return json.loads(payload) if parse else payload
    service='spug-main-59.service'; owners=[];controls=[];drops=[];packages=[]
    for index in range(4):
        engine=ROOT+'/engine-'+str(index)
        owner=dict(targets={TARGET:{'same':'target'}},sources={SOURCE:{'same':'source'}},formalModuleDirectory=engine+'/formal')
        if index>=2:owner['sources']['historical-source']={'approved':'expanded-in-main-plan'}
        op=put(ROOT+'/configuration/owner-'+str(index)+'.json',owner);owners.append(op)
        controls.append(put(ROOT+'/configuration/control-'+str(index)+'.json',
            {'restoreConfigurations':{SOURCE:{TARGET:op}}}))
        drops.append(put('/etc/systemd/system/'+service+'.d/'+str(index)+'.conf',b'fixture-unit'))
        packages.append(put(engine+'/package.json',{'files':{},'packageSha256':hashlib.sha256(raw({})).hexdigest()}))
    values=[]
    for index in range(4):
        values.append(dict(targetConfigRef=TARGET,service=service,sourceCommit=str(index)*40,
            engine=ROOT+'/engine-'+str(index),ownerConfigurationPin=owners[index],controlConfigurationPin=controls[index],
            immutableFact={'keep':'every-other-receipt-field'}))
    previous0=put(ROOT+'/configuration/allocator-1111111-previous-target-installation.json',values[0])
    previous1=put(ROOT+'/configuration/target-installation-before-main-2222222.json',values[1])
    previous2=put(ROOT+'/configuration/target-installation-before-main-3333333.json',values[2])
    active=put(ROOT+'/target-installation.json',values[3])
    logical0=dict(previous0,path=ROOT+'/target-installation.json')
    logical1=dict(previous1,path=ROOT+'/target-installation.json')
    logical2=dict(previous2,path=ROOT+'/target-installation.json')
    def step(index,prev,cur):return dict(sourceCommit=str(index)*40,engine=ROOT+'/engine-'+str(index),
        previousReceiptPin=prev,currentReceiptPin=cur,ownerConfigurationPin=owners[index],
        controlConfigurationPin=controls[index],dropinPin=drops[index])
    legacy=dict(root=ROOT,targetConfigRef=TARGET,sourceConfigRef=SOURCE,service=service,
        originalActiveReceiptPin=logical0,expectedGenerationCommits=['1'*40],steps=[step(1,previous0,logical1)],
        selectedOwnerPin=owners[1],selectedControlPin=controls[1])
    main=[dict(step(2,previous1,logical2),packagePin=packages[2]),dict(step(3,previous2,active),packagePin=packages[3])]
    historical=put(ROOT+'/unrelated-old-operation.json',{'keep':'original-history'})
    inventory=dict(status='PASS',host='172.30.30.59',protectedFiles=2,evidencePins=[logical0,historical])
    custody=dict(schemaVersion='MainProgramReceiptCustody/v1',root=ROOT,targetConfigRef=TARGET,
        sourceConfigRef=SOURCE,service=service,legacyCustody=legacy,mainSteps=main,originalInventory=inventory,
        selectedOwnerPin=owners[3],selectedControlPin=controls[3],selectedCurrentReceiptPin=active)
    return dict(custody=custody,reader=reader,files=files,put=put,values=values)


def verify(case):
    return subject.verify_layered_receipt_custody(case['custody'],read_pin=case['reader'])


def test_real_receipt_files_allow_only_byte_identical_terminal_relocation(receipts):
    before=deepcopy(receipts['custody'])
    result=verify(receipts)
    assert result['status']=='PASS' and result['serverWrites'] is False
    assert result['activationCount']==3 and result['legacyActivationCount']==1
    assert result['selectedCurrentReceiptPin']==before['selectedCurrentReceiptPin']
    assert result['legacyLogicalTerminalPin']==before['legacyCustody']['steps'][-1]['currentReceiptPin']
    assert result['legacyPhysicalTerminalPin']==before['mainSteps'][0]['previousReceiptPin']
    assert result['originalInventoryVerified'] is True
    assert receipts['custody']==before


@pytest.mark.parametrize('change',['gap','reorder','missing-step','terminal','target','service','unknown-field',
    'old-owner-drift','main-owner-drift','main-dropin-drift','package-drift','inventory-drift','extra-receipt-field'])
def test_any_missing_or_changed_layer_or_original_fails(receipts,change):
    c=receipts['custody']; files=receipts['files']
    if change=='gap':c['mainSteps'][0]['previousReceiptPin']['sha256']='f'*64
    elif change=='reorder':c['mainSteps'].reverse()
    elif change=='missing-step':c['mainSteps'].pop(0)
    elif change=='terminal':c['selectedCurrentReceiptPin']=c['mainSteps'][0]['currentReceiptPin']
    elif change=='target':c['targetConfigRef']='other'
    elif change=='service':c['service']='other.service'
    elif change=='unknown-field':c['terminalOverrides']={ROOT+'/any':'/unrelated'}
    elif change=='extra-receipt-field':
        value=deepcopy(receipts['values'][3]);value['immutableFact']={'changed':True}
        new=receipts['put'](ROOT+'/target-installation.json',value)
        c['mainSteps'][-1]['currentReceiptPin']=new;c['selectedCurrentReceiptPin']=new
    else:
        ref=(c['legacyCustody']['steps'][0]['ownerConfigurationPin'] if change=='old-owner-drift' else
            c['mainSteps'][0]['ownerConfigurationPin'] if change=='main-owner-drift' else
            c['mainSteps'][0]['dropinPin'] if change=='main-dropin-drift' else
            c['mainSteps'][0]['packagePin'] if change=='package-drift' else c['originalInventory']['evidencePins'][1])
        p=files[ref['path']];p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError,match='RECEIPT_|CUSTODY_|HISTORICAL_|ORIGINAL_|SELECTED_|PIN_'):verify(receipts)


def test_legacy_default_still_rejects_the_now_changed_active_path(receipts):
    scope={};exec(subject.SCRIPT,scope)
    with pytest.raises(ValueError,match='RECEIPT_PIN_CHANGED'):
        scope['verify_installation_receipt_custody'](receipts['custody']['legacyCustody'],read_pin=receipts['reader'])


def test_original_legacy_contract_accepts_actual_files_when_terminal_still_current(receipts):
    legacy=deepcopy(receipts['custody']['legacyCustody'])
    terminal=receipts['custody']['mainSteps'][0]['previousReceiptPin']
    receipts['files'][legacy['steps'][-1]['currentReceiptPin']['path']]=receipts['files'][terminal['path']]
    scope={};exec(subject.SCRIPT,scope)
    result=scope['verify_installation_receipt_custody'](legacy,read_pin=receipts['reader'])
    assert result['status']=='PASS' and result['activationCount']==1
    assert result['allHistoricalSourceAndTargetDefinitionsUnchanged'] is True
