"""Read actual memory headroom for the installed native SQL validation path."""
import argparse,json
from common import TASK,remote,write
SCRIPT=r'''
import datetime,json,pathlib
memory={k:int(v.strip().split()[0])*1024 for k,v in (line.split(':',1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())}
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),host=HOST,memoryBytes={k:memory[k] for k in ('MemTotal','MemAvailable','SwapTotal','SwapFree')},serverWrites=False)))
'''
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);args=parser.parse_args()
 destination=TASK/('target-incremental-capacity-'+args.suffix+'.json');assert not destination.exists(),'CAPACITY_ALREADY_RECORDED'
 report=remote('172.30.30.'+args.suffix,'HOST='+repr('172.30.30.'+args.suffix)+'\n'+SCRIPT,30)
 write(destination,report);print(json.dumps(report))
