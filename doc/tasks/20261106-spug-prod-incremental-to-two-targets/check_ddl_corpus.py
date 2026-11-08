"""Validate private real DDL observations against the local candidate parser."""
import collections
import hashlib
import json
import re
import sys
from common import PRIVATE,TASK,write
sys.path.insert(0,str(TASK.parents[2]/'ops/backup_engine/formal'))
from formal_binlog_scope import RowEventScope

scan=json.loads((PRIVATE/'binlog-scope-scan.private.json').read_text(encoding='utf-8'))
assert scan['status']=='DIAGNOSTIC_ONLY'
unique={re.sub(r' /\* xid=[0-9]+ \*/$','',v['info']):v for v in scan['diagnostics']}
fail=[];passed=[]
for sql,item in unique.items():
    scope=RowEventScope('ruoyi-vue-pro','FILE_POSITION')
    try:
        scope.observe('Anonymous_Gtid','SET @@SESSION.GTID_NEXT= ANONYMOUS')
        scope.observe('Query',sql);scope.complete();passed.append(item['infoSha256'])
    except Exception as error:
        fail.append(dict(sql=sql,sha256=hashlib.sha256(sql.encode()).hexdigest(),error=str(error)))
write(PRIVATE/'candidate-ddl-failures.private.json',fail)
summary=dict(originalRejectedEventCount=len(scan['diagnostics']),uniqueStatements=len(unique),candidatePassCount=len(passed),candidateFailCount=len(fail),originalEventCount=sum(s['eventCount'] for s in scan['proof']['segments']),originalReadOnlyScanFinishedAt=scan['finishedAt'])
write(TASK/'ddl-corpus-candidate.json',summary)
print(json.dumps(summary))
for item in fail[:8]:print(item['sql'][:110]+' ... '+item['sql'][-400:])
