"""Read-only bounded status for the final acceptance cleanup tail."""
from pathlib import Path
import json, re, sqlite3, sys
root = Path('C:/SpugHandoff/release')
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro', uri=True) as db:
    state = json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
identity='JOB-7f32aa47ab'
if '--retry' in sys.argv:
    identity=json.loads(Path(__file__).with_name('cleanup-retry-submission.json').read_text('utf-8'))['jobId']
if '--legacy' in sys.argv:
    identity=json.loads(Path(__file__).with_name('cleanup-retry-legacy-submission.json').read_text('utf-8'))['jobId']
job = next(j for j in state['jobs'] if j['id']==identity)
cleanup = job.get('postReleaseCleanup', {})
print(json.dumps(dict(jobId=job['id'], status=job['status'], step=job.get('currentStep'), cleanupStatus=cleanup.get('status'),
    environments={e:dict(status=v.get('status'), removedItems=len(v.get('removed',[])), fileBytes=v.get('bytes',0),
        retainedItems=len(v.get('retained',[])), blockedReleaseTags=v.get('plan',{}).get('blockedReleaseTags',[]),
        errorPresent=bool(v.get('error'))) for e,v in cleanup.get('environments',{}).items()})))
if '--errors' in sys.argv:
    config = json.loads((root/'executor.private.json').read_text('utf-8'))
    private_values = []
    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if re.search(r'password|passwd|secret|token', key, re.I) and isinstance(item, str):
                    private_values.append(item)
                collect(item)
        elif isinstance(value, list):
            for item in value: collect(item)
    collect(config)
    for env, value in cleanup.get('environments',{}).items():
        message = value.get('error','')
        for secret in private_values:
            if secret: message = message.replace(secret,'[REDACTED]')
        message = re.sub(r'(?i)(password|token|secret)\s*[=:]\s*[^\s,;]+',r'\1=[REDACTED]',message)
        if message: print(json.dumps(dict(environment=env,error=message[:900])))
