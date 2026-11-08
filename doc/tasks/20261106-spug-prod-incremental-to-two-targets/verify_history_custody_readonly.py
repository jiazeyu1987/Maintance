"""Actual positive and negative audits; no file or server-state mutation."""
import argparse,json
from common import TASK,remote,write
from installation_history_custody import inputs,SCRIPT

TEST=r'''
import copy,datetime,json
positive=verify_installation_receipt_custody(CUSTODY)
cases=[]
def reject(name,mutate,expected):
 value=copy.deepcopy(CUSTODY);mutate(value)
 try:verify_installation_receipt_custody(value)
 except ValueError as error:
  assert str(error)==expected,'WRONG_RECEIPT_REJECTION';cases.append(dict(name=name,errorCode=str(error)));return
 raise AssertionError('INVALID_RECEIPT_CUSTODY_ACCEPTED')
reject('missing generation',lambda c:c['steps'].pop(),'RECEIPT_CHAIN_LENGTH_INVALID')
reject('reordered generations',lambda c:c['steps'].reverse(),'RECEIPT_GENERATION_ORDER_CHANGED')
reject('tampered activation bytes',lambda c:c['steps'][0]['currentReceiptPin'].__setitem__('sha256','0'*64),'RECEIPT_ACTIVATION_CHAIN_GAP')
reject('missing archived receipt',lambda c:c['steps'][0]['previousReceiptPin'].__setitem__('path',c['root']+'/configuration/missing-previous-target-installation.json'),'RECEIPT_PIN_UNAVAILABLE')
reject('changed owner binding',lambda c:c['steps'][0]['ownerConfigurationPin'].__setitem__('sha256','0'*64),'RECEIPT_ACTIVATION_CONTRACT_CHANGED')
assert len(cases)==5
print(json.dumps(dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=HOST,
 actualRetainedReceiptFiles=True,positive=positive,negativeRejections=cases,serverWrites=False)))
'''
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);args=parser.parse_args()
 destination=TASK/('history-receipt-custody-green-'+args.suffix+'.json');assert not destination.exists()
 immutable,custody=inputs(args.suffix)
 result=remote('172.30.30.'+args.suffix,'HOST='+repr('172.30.30.'+args.suffix)+'\nCUSTODY='+repr(custody)+'\n'+SCRIPT+'\n'+TEST,90)
 write(destination,result);print(json.dumps({k:v for k,v in result.items() if k!='positive'}))
