"""Read the exact submitted target operation; never dispatch or read payloads."""
import argparse,ast,hashlib,json
from common import TASK,PRIVATE,remote,write,restore_kind


def stage_states(timings):
 stages={}
 for row in timings:
  value=row['value'];scope=row['path'].rpartition('/')[0] or 'operation'
  stage=scope+'/'+value['stage']
  if 'completed' in value:stages[stage]='DONE' if value['completed'] else 'FAILED'
  else:stages.setdefault(stage,'RUNNING')
 return stages


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('suffix',choices=['58','59']);args=parser.parse_args();suffix=args.suffix
 tree=ast.parse((TASK.parent/'20261105-spug-prod-full-to-review/observe_restore.py').read_text(encoding='utf-8'))
 script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCRIPT' for t in n.targets))
 script=script.replace("root=pathlib.Path('/mnt/intruoyi-data/spug-main-restore-20261104-v3')","root=pathlib.Path(ROOT)")
 script=script.replace('print(json.dumps(out))',"out['databaseReadbackSteps']={p.name:dict(tableDirectories=sum(q.is_dir() for q in (p/'database-readback').iterdir()),tokenFiles=sum((q/'tokens.tsv').is_file() for q in (p/'database-readback').iterdir() if q.is_dir())) for p in op.glob('database-*') if (p/'database-readback').is_dir()}\nprint(json.dumps(out))")
 kind=restore_kind(suffix)
 operation=json.loads((TASK/(kind+'-ui-submission.json')).read_text(encoding='utf-8'))['request']['operationId']
 script='ROOT='+repr(('/mnt/intruoyi-data/' if suffix=='59' else '/var/lib/docker/intruoyi-data/')+'spug-main-restore-20261104-v3')+'\n'+script.replace('OPERATION_LITERAL',repr(operation))
 result=remote('172.30.30.'+suffix,script,65)
 digest=hashlib.sha256(result['observedAt'].encode()).hexdigest()[:12]
 write(PRIVATE/(kind+'-progress-'+digest+'.private.json'),result)
 write(TASK/(kind+'-native-progress.json'),result)
 stages=stage_states(result['nativeTimings'])
 print(json.dumps(dict(observedAt=result['observedAt'],operationId=operation,stages=stages,workers=[dict(pid=p['pid'],readGiB=round(p['rchar']/1024**3,2),writeGiB=round(p['wchar']/1024**3,2),wchan=p['wchan'],openFileLimits=p['openFileLimits']) for p in result['processes'] if 'recovery_minimal_worker.py' in p['program']],databaseReadbackSteps=result['databaseReadbackSteps'],runningServiceCount=sum(s['running'] for s in result['services']),evidenceFileCount=len(result['evidenceFiles']))))
