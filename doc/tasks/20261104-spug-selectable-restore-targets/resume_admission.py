"""Authenticated read-only selections and current production installation gates."""
import concurrent.futures,json
from resume_readonly import TASK,PRIVATE,remote

SCRIPT=r'''
import datetime,hashlib,json,pathlib,urllib.request,urllib.error
root=pathlib.Path(ROOT);receipt=json.loads((root/'target-installation.json').read_bytes())
reference=receipt['controlConfigurationPin'];raw=pathlib.Path(reference['path']).read_bytes()
assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256']
control=json.loads(raw);headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers']
url='http://127.0.0.1:'+str(control['listenPort'])+'/selections?targetConfigRef='+receipt['targetConfigRef']
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with opener.open(urllib.request.Request(url,headers=headers),timeout=60) as response:
  out={'status':response.status,'body':json.load(response)}
except urllib.error.HTTPError as error:out={'status':error.code,'body':json.loads(error.read())}
out.update(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),targetConfigRef=receipt['targetConfigRef'])
print(json.dumps(out))
'''
def get(suffix):
    root=('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3'
    out=remote('172.30.30.'+suffix,'ROOT='+repr(root)+'\n'+SCRIPT,timeout=80)
    (PRIVATE/('resume-admission-'+suffix+'.private.json')).write_text(json.dumps(out),encoding='utf-8')
    (TASK/('resume-admission-'+suffix+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'host':'172.30.30.'+suffix,**out}

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for out in pool.map(get,('58','59')):print(json.dumps(out,ensure_ascii=False))
