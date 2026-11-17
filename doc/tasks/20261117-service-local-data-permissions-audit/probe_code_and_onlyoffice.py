import json
import re
import subprocess

def run(args,timeout=15):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    assert p.returncode==0,'READ_ONLY_CODE_OR_SCHEMA_QUERY_FAILED'
    return p.stdout.decode('utf-8',errors='strict')

out={'serverWrites':False,'codeEvidence':[]}
for name in ['erp-invoice-voucher-print-assistant','fenbeitong-assistant']:
    code=run(['docker','exec',name,'cat','server.js'])
    wanted=['state.json','fenbeitong-tenants.sqlite','syncedDocuments','voucherRecords','syncBatches','fenbeitongRequesterCatalogs','.env.kingdee','runtimeDir','runtimeDirectory','writeFile','readFile','last-result','UPLOAD','RESULT','KINGDEE','operationLogs']
    evidence=[]
    for i,line in enumerate(code.splitlines(),1):
        hits=[key for key in wanted if key in line]
        if hits:
            evidence.append({'line':i,'references':hits,'functions':re.findall(r'(?:async\s+)?function\s+([A-Za-z_$][\w$]*)',line)})
    out['codeEvidence'].append({'service':name,'file':'server.js','lines':len(code.splitlines()),'evidence':evidence[:120]})
sql="BEGIN READ ONLY; SELECT 'count','doc_changes',COUNT(*) FROM doc_changes; SELECT 'count','task_result',COUNT(*) FROM task_result; COMMIT;"
out['onlyofficeDocumentTableCounts']=run(['docker','exec','--env','PGOPTIONS=-c default_transaction_read_only=on','-u','postgres','intruoyi-onlyoffice','psql','-X','-d','onlyoffice','-At','-c',sql]).splitlines()
for args,label in [(['redis-cli','INFO','keyspace'],'onlyofficeRedisKeyspace'),(['rabbitmqctl','-q','list_queues','messages_ready','messages_unacknowledged'],'onlyofficeRabbitQueueCounts')]:
    p=subprocess.run(['docker','exec','intruoyi-onlyoffice',*args],capture_output=True,timeout=20)
    out[label]={'exit':p.returncode,'rows':p.stdout.decode('utf-8').splitlines() if p.returncode==0 else [],'errorPresent':bool(p.stderr)}
print(json.dumps(out))
