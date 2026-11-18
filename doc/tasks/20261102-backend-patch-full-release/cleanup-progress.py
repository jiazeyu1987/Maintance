"""Read-only bounded progress for the already submitted cleanup retry."""
from pathlib import Path
import json,subprocess,sys
root=Path('C:/SpugHandoff/release');task=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
runtime=Runtime(json.loads((root/'executor.private.json').read_text('utf-8')))
job=json.loads((task/('cleanup-retry-legacy-submission.json' if '--legacy' in sys.argv else 'cleanup-retry-submission.json')).read_text('utf-8'))['jobId']
env=sys.argv[1] if len(sys.argv)>1 else 'test';profile=runtime.profile(env)
code='from pathlib import Path\nimport json,os\nbase=Path('+repr(profile['stagingRoot'])+')\njob='+repr(job)+'\n'+r'''
output={}
path=base/'.cleanup'/(job+'.json')
if path.exists():
    report=json.loads(path.read_text('utf-8'))
    output.update(status=report['status'],removedItems=len(report.get('removed',[])),fileBytes=report.get('bytes',0),
        planned={k:len(v) for k,v in report.get('plan',{}).items() if k in ('containers','images','files','directories')},
        blockedReleaseTags=report.get('plan',{}).get('blockedReleaseTags',[]),pendingKind=report.get('pendingDeletion',{}).get('kind'))
for path in (base/'.operations').glob('OP-*.json'):
    operation=json.loads(path.read_text('utf-8'))
    if operation.get('jobId')!=job:continue
    process=Path('/proc')/str(operation['pid']);proc=process/'stat'
    raw=proc.read_text() if proc.exists() else ''
    alive=bool(raw and raw[raw.rfind(')')+2:].split()[19]==operation['processStart'])
    output.update(operationStatus=operation['status'],workerAlive=alive)
    if alive:
        output['io']={k:int(v) for k,v in (line.split(':',1) for line in (process/'io').read_text().splitlines()) if k in ('rchar','wchar','read_bytes')}
        opened=[]
        for fd in (process/'fd').iterdir():
            try:
                name=Path(os.readlink(str(fd))).name
                if name.startswith(('recovery','release.tar')):
                    details=(process/'fdinfo'/fd.name).read_text().splitlines()
                    position=int(next(line.split(':',1)[1].strip() for line in details if line.startswith('pos:')))
                    opened.append(dict(name=name,position=position,bytes=fd.stat().st_size))
            except FileNotFoundError:continue
        output['openArtifacts']=opened
print(json.dumps(output))
'''
result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=45)
assert result.returncode==0,env+': cleanup progress unavailable'
print(result.stdout.decode('utf-8'))
