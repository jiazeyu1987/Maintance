"""Sequential real Spug actions; stop on any failed action or verification."""
from pathlib import Path
import json,os,sqlite3,subprocess,sys,time

task=Path(__file__).resolve().parent
root=Path('C:/SpugHandoff/release')
private=root/'private/backend-patch-full-release-20261102'
node='C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
selection=json.loads((task/'selected-release.json').read_text('utf-8'))
tag=selection['fullReleaseTag']
report_path=task/'full-validation-sequence.json'
assert not report_path.exists(),'Preserve previous sequence evidence'
report=dict(status='running',releaseTag=tag,commit=selection['commit'],stages=[])

def save(): report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def event(**value): print(json.dumps(value,ensure_ascii=True),flush=True)
def state():
    with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:
        return json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
def command(stage,args,phase=None,timeout=300):
    event(stage=stage,status='started')
    environment=os.environ.copy();environment['PYTHONUTF8']='1'
    if phase: environment['RELEASE_VERIFY_PHASE']=phase
    result=subprocess.run(args,cwd=task.parents[2],env=environment,capture_output=True,timeout=timeout)
    # Retain complete command output privately, emit only explicit status.
    (private/(stage+'.stdout.private.log')).write_bytes(result.stdout)
    (private/(stage+'.stderr.private.log')).write_bytes(result.stderr)
    assert result.returncode==0,stage+': command failed; inspect private evidence'
    rows=[]
    for line in result.stdout.decode('utf-8').splitlines():
        if line.startswith('{'): rows.append(json.loads(line))
    report['stages'].append(dict(stage=stage,status='PASS'));save()
    event(stage=stage,status='PASS')
    return rows
def wait_job(job_id):
    deadline=time.monotonic()+5400;previous=None
    while time.monotonic()<deadline:
        job=next(j for j in state()['jobs'] if j['id']==job_id)
        identity=(job['status'],job.get('currentStep'))
        if identity!=previous:
            event(jobId=job_id,status=identity[0],step=identity[1]);previous=identity
        if job['status']!='running':
            safe={k:job.get(k) for k in ('id','action','status','target','releaseTag','currentStep')}
            (task/('status-'+job_id+'.json')).write_text(json.dumps(safe,indent=2)+'\n',encoding='utf-8')
            assert job['status']=='succeeded',job_id+': original failure retained; sequence stopped'
            assert job['releaseTag']==tag,'Wrong package task'
            return
        time.sleep(15)
    raise TimeoutError(job_id+': waiting for existing task timed out; do not replay it')
def action(name,note=None):
    args=[node,str(task/'spug-full-ui.cjs'),name]
    if note:args.append(note)
    rows=command('spug-'+name,args,timeout=240)
    submitted=next(v for v in rows if v.get('action')==name)
    report['stages'][-1]['jobId']=submitted['jobId'];save()
    wait_job(submitted['jobId'])
def py(name,*args):
    return [sys.executable,'-X','utf8',str(task/(name+'.py')),*args]
def ui(env,acceptance=False):
    phase='full-'+env+('-acceptance' if acceptance else '-open')
    command('ui-'+phase,[node,str(task/'verify-ui-gxp.cjs'),env,tag]+(['acceptance'] if acceptance else []),phase=phase)

try:
    save()
    wait_job('JOB-b68b4b0044')
    proof=json.loads((task/'ui-gxp-full-test-test.json').read_text('utf-8'))
    assert proof['status']=='PASS' and proof['releaseTag']==tag and proof['realVersionDialog']
    command('program-full-test',py('verify-program','full','test'))
    action('mark-tested')
    action('promote-prod')
    ui('prod',True)
    action('accept-prod','PROD：真实登录、全量版本及启动日志说明、保存和运行GxP关闭已核对；本次只读验收，不称写入功能回归。')
    command('program-full-prod',py('verify-program','full','prod'))
    ui('prod')
    command('quartz-heartbeat-full',py('verify-prod-heartbeat','full'))
    action('promote-backup')
    ui('backup',True)
    action('accept-backup','真实登录、全量版本及启动日志说明、保存和运行GxP关闭已核对；只读验收通过，开放同包备份服。')
    command('program-full-backup',py('verify-program','full','backup'))
    ui('backup')
    command('database-full',py('compare-databases','full'))
    final=next(p for p in state()['packages'] if p['releaseTag']==tag)
    assert final['stage']=='completed','Same package chain is incomplete'
    report['status']='PASS';save();event(status='PASS',releaseTag=tag,sequenceComplete=True)
except BaseException as error:
    report.update(status='failed',errorType=type(error).__name__,error=str(error));save()
    event(status='failed',errorType=type(error).__name__,error=str(error))
    raise SystemExit(1)
