"""Read-only comparison when the installation preflight detects drift."""
import hashlib,json
from install_review_control import SCRIPT
from resume_readonly import PRIVATE,TASK,remote

if __name__=='__main__':
    before=json.loads((PRIVATE/'resume-59.private.json').read_text(encoding='utf-8'))
    def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    expected={r['Id']:{'name':r['Name'],'pid':r['State']['Pid'],'startedAt':r['State']['StartedAt'],
      'running':r['State']['Running'],'image':r['Image'],
      'configurationSha256':hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','Config','HostConfig')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()}
      for r in before['containers']}
    current=remote('172.30.30.59',SCRIPT.split('receiptpath=root/')[0]+'\nprint(json.dumps(business()))',timeout=60)
    report={'removedIds':sorted(set(expected)-set(current)),'addedIds':sorted(set(current)-set(expected)),
      'changes':[{'id':k,'name':current[k]['name'],'fields':{f:{'before':expected[k][f],'after':current[k][f]} for f in current[k] if current[k][f]!=expected[k][f]}}
                 for k in set(expected)&set(current) if current[k]!=expected[k]],'remoteMutation':False}
    (TASK/'review-business-drift.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
