"""Bind the fresh source audit to the single genuine UI dispatch."""
import json,hashlib,datetime
from common import TASK,SOURCE,write,now
load=lambda name:json.loads((TASK/name).read_text(encoding='utf-8'))
audit=load('binlog-scope-installed.json');installed=load('source-control-installation.json');build=load('release-build-verification.json')
assert audit['status']==installed['status']==build['status']=='PASS'
assert not audit['diagnostics'] and audit['parentChainRef']=='smallapp-7fec29a3e132463096aec915c08acab3'
assert audit['installedModulePin']['path'].startswith(installed['engine']+'/')
assert installed['sourceCommit']==build['targetCommit']=='6319024c003ead602d59e7697673fa3c39807863'
assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(audit['finishedAt'])).total_seconds()<900,'AUDIT_STALE'
assert not (TASK/'incremental-ui-submission.json').exists(),'ALREADY_SUBMITTED'
for suffix in ('57','58','59'):
 baseline=load('pre-install-'+suffix+'.json')
 assert not baseline['activeReservation'] and baseline['http']['backend']['status']=='UP' and baseline['http']['frontend']['httpStatus']==200
 assert baseline['packageFilesMatch'] and all(r['running'] for r in baseline['roles'])
 assert baseline['admissions']['target']['httpStatus']==200
value=dict(status='PASS',observedAt=now(),sourceConfigRef=SOURCE,parentChainRef=audit['parentChainRef'],parentPointPin=audit['parentPointPin'],installedModulePin=audit['installedModulePin'],auditedStart=audit['start'],auditedEnd=audit['end'],binlogBytes=audit['binlogBytes'],scopeProofSha256=hashlib.sha256(json.dumps(audit['proof'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),sourceCommit=installed['sourceCommit'],finalSubmitCount=0)
write(TASK/'incremental-preflight.json',value);print(json.dumps(value))
