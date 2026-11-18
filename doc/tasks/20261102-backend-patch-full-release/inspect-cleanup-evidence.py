"""Inspect failed cleanup guards without deleting or reclassifying anything."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json, subprocess, sys
root=Path('C:/SpugHandoff/release');task=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime,ssh_source_bytes
runtime=Runtime(json.loads((root/'executor.private.json').read_text('utf-8')))
def read(env):
    profile=runtime.profile(env)
    code='from pathlib import Path\nimport hashlib,json,subprocess\nbase=Path('+repr(profile['stagingRoot'])+')\n'+r'''
path=base/'.cleanup/JOB-7f32aa47ab.json'
report=json.loads(path.read_text('utf-8'))
result=dict(status=report['status'],removedItems=len(report.get('removed',[])),fileBytes=report.get('bytes',0),
    retainedItems=len(report.get('retained',[])),pendingKind=report.get('pendingDeletion',{}).get('kind'))
pending=report.get('pendingDeletion',{})
if pending.get('kind')=='container':
    row=pending['resource']
    actual=subprocess.run(['docker','inspect',row['id']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    result['candidate']=dict(id=row['id'],name=row['name'],releaseTag=row['releaseTag'],exists=actual.returncode==0,
        alreadyInRemovedList=any(v.get('id')==row['id'] for v in report.get('removed',[])))
    if actual.returncode==0:
        value=json.loads(actual.stdout)[0]
        fingerprint=hashlib.sha256(json.dumps({k:value.get(k) for k in ('Id','Image','Config','HostConfig','Mounts')},sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result['candidate'].update(stopped=not any(value['State'].get(k) for k in ('Running','Paused','Restarting')),
            nameMatches=value['Name'].lstrip('/')==row['name'],imageMatches=value['Image']==row['imageId'],fingerprintMatches=fingerprint==row['fingerprint'])
if not report.get('plan') and report.get('error')=='失败目录恢复日志不完整':
    result['missingHistoricalJournals']=[]
    for record_path in base.glob('*/recovery-record.private.json'):
        record=json.loads(record_path.read_text('utf-8'))
        for folder in record_path.parent.glob('recovery-JOB-*'):
            receipt_path=folder/'receipt.private.json'
            if not receipt_path.is_file(): continue
            receipt=json.loads(receipt_path.read_text('utf-8'))
            for retained in receipt.get('retainedData',[]):
                for resource in record.get('resources',[]):
                    source=Path(resource['mount']['Source'])
                    if Path(retained)!=source.with_name(source.name+'.failed-'+receipt['jobId']):continue
                    journal=source.parent/(source.name+'.restore-'+receipt['jobId']+'.json')
                    value=json.loads(journal.read_text('utf-8')) if journal.exists() else {}
                    if value.get('phase')!='complete' or value.get('archiveSha256')!=resource['artifact']['sha256']:
                        result['missingHistoricalJournals'].append(dict(releaseTag=record.get('releaseTag'),recoveryJobId=receipt['jobId'],
                            role=resource['role'],retainedDirectoryExists=Path(retained).exists(),journalExists=journal.exists(),journalPhase=value.get('phase')))
print(json.dumps(result))
'''
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=60)
    assert result.returncode==0,env+': cleanup evidence unavailable'
    return env,json.loads(result.stdout)
with ThreadPoolExecutor(max_workers=3) as pool:result=dict(pool.map(read,('test','prod','backup')))
output=task/'cleanup-guard-evidence.json';assert not output.exists(),'Preserve original cleanup evidence'
output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
