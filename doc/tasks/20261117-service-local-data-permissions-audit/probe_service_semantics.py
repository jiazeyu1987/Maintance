"""Read shapes and code references only, without business or secret values."""
import collections
import json
import re
import subprocess
from pathlib import Path

def command(args,timeout=15):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    assert p.returncode==0,'READ_ONLY_COMMAND_FAILED'
    return p.stdout.decode('utf-8',errors='strict')

def shape(value,depth=0):
    if isinstance(value,dict):
        return {'type':'object','keyCount':len(value),'fields':{k:shape(v,depth+1) for k,v in list(value.items())[:55]}} if depth<3 else {'type':'object','fieldNames':list(value)[:55]}
    if isinstance(value,list):
        return {'type':'list','count':len(value),'elementShape':shape(value[0],depth+1) if value and depth<3 else None}
    return {'type':type(value).__name__}

out={'serverWrites':False}
state=Path('/var/lib/docker/fenbeitong-release/data/state.json')
state_value=json.loads(state.read_bytes())
out['fenbeitongStateShape']={}
for key,value in state_value.items():
    if key in ['syncedDocuments','voucherRecords','syncBatches','fenbeitongRequesterCatalogs']:
        first=next(iter(value.values()),None) if isinstance(value,dict) else None
        out['fenbeitongStateShape'][key]={'type':'keyedRecords','count':len(value),'recordFields':{k:type(v).__name__ for k,v in first.items()} if isinstance(first,dict) else type(first).__name__}
    else:
        out['fenbeitongStateShape'][key]=shape(value)
runtime=Path('/opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/runtime')
out['invoiceConnectionFiles']=[]
for path in runtime.iterdir():
    if not path.is_file():continue
    raw=path.read_bytes()
    entry={'extension':'.env.kingdee','bytes':len(raw)}
    try:entry['jsonShape']=shape(json.loads(raw))
    except (ValueError,UnicodeError):
        entry['format']='ENV'
        entry['variableNames']=[line.partition('=')[0].strip() for line in raw.decode('utf-8').splitlines() if re.fullmatch(r'[A-Z_][A-Z0-9_]*',line.partition('=')[0].strip())]
    out['invoiceConnectionFiles'].append(entry)
for name in ['erp-invoice-voucher-print-assistant','fenbeitong-assistant']:
    listing=command(['docker','exec',name,'sh','-c',"find . -maxdepth 2 -type f \\( -name '*.js' -o -name '*.mjs' -o -name '*.cjs' -o -name '*.json' \\) -not -path './node_modules/*' | head -70"])
    out[name+'SourceFiles']=listing.splitlines()
    package=command(['docker','exec',name,'cat','package.json'])
    doc=json.loads(package)
    out[name+'EntryPoints']={k:v for k,v in doc.get('scripts',{}).items() if k in ['start','server']}
oo=json.loads(command(['docker','inspect','intruoyi-onlyoffice']))[0]
data=Path(next(m['Source'] for m in oo['Mounts'] if m['Destination']=='/var/www/onlyoffice/Data'))
out['onlyofficeDataFileNames']=[p.relative_to(data).as_posix() for p in data.rglob('*') if p.is_file()]
sql="SELECT 'table',tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename; SELECT 'column',table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position;"
p=subprocess.run(['docker','exec','--env','PGOPTIONS=-c default_transaction_read_only=on','-u','postgres','intruoyi-onlyoffice','psql','-X','-d','onlyoffice','-At','-c',sql],capture_output=True,timeout=15)
out['onlyofficeDatabaseProbe']={'exit':p.returncode,'schemaRows':p.stdout.decode('utf-8').splitlines() if p.returncode==0 else [],'errorPresent':bool(p.stderr)}
print(json.dumps(out))
