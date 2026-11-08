"""Read exact idle installation before the frontend contract generation."""
import argparse,json
from common import TASK,PRIVATE,remote,write,now
from inspect_allocator_target_upgrade import SCRIPT

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);args=parser.parse_args()
 suffix=args.suffix;stem='packaged-frontend-upgrade-preflight-'+suffix
 assert not (TASK/(stem+'.json')).exists()
 script=SCRIPT.replace("assert (active_pin is not None)==(SUFFIX=='58' and CLEARANCE is None)","assert active_pin is None")
 script=script.replace("if CLEARANCE is None:assert json.loads(active.read_bytes())['operationId']==FAILED_OPERATION","assert not active.exists()")
 script=script.replace("assert json.loads((operation/'child-exit.json').read_bytes())==CHILD_EXIT", "child=json.loads((operation/'child-exit.json').read_bytes());assert child['actualExitCode']==1 and child['timedOut'] is False")
 values=dict(ROOT=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3',SUFFIX=suffix,
  FAILED_OPERATION='smallapp-e61ca1c4b93f4aa3ab5a70eca399c36d',POINT='smallapp-ae9f83a19bb84ec28f27b5ca666bf62c',CLEARANCE=None)
 result=remote('172.30.30.'+suffix,'\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+script,180)
 write(PRIVATE/(stem+'.private.json'),result)
 report=dict(status='PASS',observedAt=now(),host='172.30.30.'+suffix,receiptPin=result['receiptPin'],
  ownerConfigurationPin=result['receipt']['ownerConfigurationPin'],controlConfigurationPin=result['receipt']['controlConfigurationPin'],
  oldEngine=result['oldEngine'],oldFileCount=result['oldFileCount'],activePointerPin=None,retainedClearancePin=None,
  failurePins=result['failurePins'],serviceStates=result['serviceStates'],liveMaxOpenFiles=65536,serverWrites=False)
 write(TASK/(stem+'.json'),report);print(json.dumps(report))
