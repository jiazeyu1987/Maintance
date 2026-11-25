"""Task driver: private inputs stay outside Git; print only selected status fields."""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = Path('C:/SpugHandoff/release')
OUT = BASE / 'private/intruoyi-fenbeitong-test-prod-20261125'
OUT.mkdir(exist_ok=True)
CONFIG = json.loads((BASE / 'executor.private.json').read_text(encoding='utf-8-sig'))
MODE = sys.argv[1]

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

if MODE == 'processes':
    import psutil
    parent=psutil.Process(29472)
    print(json.dumps([dict(pid=p.pid,name=p.name(),status=p.status(),cpuSeconds=sum(p.cpu_times()[:2]),rssMiB=round(p.memory_info().rss/1048576)) for p in parent.children(recursive=True)],ensure_ascii=False))
elif MODE in ('local', 'progress'):
    con = sqlite3.connect('file:' + str(BASE / 'state/state.sqlite3') + '?mode=ro', uri=True)
    value = json.loads(con.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
    save('state.private.json', value)
    if MODE == 'progress':
        jobs = [j for j in value['jobs'] if len(sys.argv)>2 and j['id']==sys.argv[2]] or value['jobs'][:1]
        print(json.dumps([{**{k:j.get(k) for k in ('id','action','status','releaseTag','currentStep','error','buildWorktree','buildWorktreeCleanup','technicalVerification')},'recentSteps':[x for x in j.get('logs',[]) if x['message'].startswith('Step:')][-3:]} for j in jobs],ensure_ascii=False))
        raise SystemExit(0)
    report = {'active': [{k:j.get(k) for k in ('id','action','status','releaseTag','currentStep','error')} for j in value['jobs'] if j['status'] in ('queued','running')], 'latest':[{k:j.get(k) for k in ('id','action','status','releaseTag','currentStep','error')} for j in value['jobs'][:3]], 'config':{k:CONFIG.get(k) for k in ('applicationId','repo','stateDir','port','releaseStrategy')}, 'targets':{env:{k:CONFIG['targets'][env].get(k) for k in ('host','entryUrl','fenbeitongAssistantHost','fenbeitongAssistantUrl','runtimeEnvironmentFile','recoveryInventoryConfirmed','recoveryMode')} for env in ('test','prod')}}
    current = Path(__file__).resolve().parents[3]
    name = 'ops/spug/release-center/intruoyi_runtime_agent.py'
    report['runtimeAgent'] = {label:hashlib.sha256((root/name).read_bytes()).hexdigest() for label,root in [('main',current),('installed',BASE/'source')]}
    save('local-preflight.json', report)
    print(json.dumps(report, ensure_ascii=False))
elif MODE == 'observe':
    sys.path.insert(0, str(BASE/'source/ops/spug/release-center'))
    from intruoyi_runtime import Runtime
    env = sys.argv[2]
    value = Runtime(CONFIG).observe(env)
    save(env+'-observe.private.json', value)
    print(json.dumps({k:value.get(k) for k in ('releaseTag','backendHealth','frontendHttpStatus','maintenance','runtimeOpeningPending','schemaDigest','ledgerDigest')},ensure_ascii=False))
else:
    if MODE == 'action':
        action = sys.argv[2]
        value = json.loads((OUT/sys.argv[3]).read_text(encoding='utf-8'))
        value['applicationId'] = CONFIG['applicationId']
        endpoint = '/actions/'+action
        data = json.dumps(value, ensure_ascii=False).encode('utf-8')
    else:
        endpoint = '/state'
        data = None
    req = Request('http://127.0.0.1:'+str(CONFIG['port'])+endpoint, data=data, headers={'X-Release-Key':CONFIG['bridgeKey'],'X-Release-Actor':'codex-intruoyi-fenbeitong-release-20261125','Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=45) as resp:
            value = json.load(resp)
    except HTTPError as error:
        save('http-error.private.json', {'status':error.code,'body':error.read().decode('utf-8')})
        raise SystemExit('HTTP action rejected; private evidence saved; status='+str(error.code))
    if MODE == 'action':
        save(action+'-submission.json',value)
        print(json.dumps({k:value.get(k) for k in ('id','action','status','releaseTag','target')}, ensure_ascii=False))
    else:
        save('state.private.json',value)
        print(json.dumps({'active':[{k:j.get(k) for k in ('id','action','status','releaseTag','currentStep')} for j in value['jobs'] if j['status'] in ('queued','running')], 'latest':[{k:j.get(k) for k in ('id','action','status','releaseTag','target','currentStep','error')} for j in value['jobs'][:3]]},ensure_ascii=False))
