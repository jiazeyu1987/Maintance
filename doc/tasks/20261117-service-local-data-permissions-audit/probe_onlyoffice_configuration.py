import json
import re
import subprocess

def run(args):
    p=subprocess.run(args,capture_output=True,timeout=10)
    assert p.returncode==0,'READ_ONLY_CONFIGURATION_READ_FAILED'
    return p.stdout.decode('utf-8')

out={'serverWrites':False}
for name in ['local','default']:
    doc=json.loads(run(['docker','exec','intruoyi-onlyoffice','cat','/etc/onlyoffice/documentserver/'+name+'.json']))
    services=doc.get('services',{}).get('CoAuthoring',{})
    sql=services.get('sql',{})
    redis=services.get('redis',{})
    storage=doc.get('storage',{})
    out[name]={'sql':{k:v for k,v in sql.items() if k in ['type','dbHost','dbPort','dbName']},'redis':{k:v for k,v in redis.items() if k in ['host','port']},'storageFs':{k:v for k,v in storage.get('fs',{}).items() if k in ['folderPath','urlExpires']}}
code=run(['docker','exec','fenbeitong-assistant','cat','server.js'])
out['fenbeitongModules']=sorted(set(re.findall(r"(?:from\s+|import\s*)['\"](\./[^'\"]+)['\"]",code)))
p=subprocess.run(['docker','exec','intruoyi-onlyoffice','redis-cli','INFO','keyspace'],capture_output=True,timeout=10)
out['redisLocalProbeFailureClassification']=[term for term in ['Connection refused','NOAUTH','not found'] if term in p.stderr.decode('utf-8')+p.stdout.decode('utf-8')]
print(json.dumps(out))
