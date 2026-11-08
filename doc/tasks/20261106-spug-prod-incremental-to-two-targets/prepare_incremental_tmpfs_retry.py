"""Admit attempt four using the active isolated exporter and all failed originals."""
import datetime,json
from common import TASK,PRIVATE,SOURCE,active_source_installation,now,remote,write
from prepare_incremental_parent_retry import SCRIPT as PARENT_SCRIPT

SCRIPT=PARENT_SCRIPT.replace(
 "config=json.loads((root/'configuration/capture.json').read_bytes());source=config['source']",
 """capture_raw=pathlib.Path(CAPTURE_PIN['path']).read_bytes()
assert len(capture_raw)==CAPTURE_PIN['bytes'] and hashlib.sha256(capture_raw).hexdigest()==CAPTURE_PIN['sha256'],'ACTIVE_CAPTURE_CHANGED'
control_raw=pathlib.Path(CONTROL_PIN['path']).read_bytes()
assert len(control_raw)==CONTROL_PIN['bytes'] and hashlib.sha256(control_raw).hexdigest()==CONTROL_PIN['sha256'],'ACTIVE_CONTROL_CHANGED'
assert CONTROL_PIN['path'].encode() in (pathlib.Path('/proc')/str(CONTROL_PID)/'cmdline').read_bytes(),'ACTIVE_CONTROL_CHANGED'
config=json.loads(capture_raw);source=config['source']""",
).replace(
 "transport='test -z",
 """assert toolref==EXPORTER['descriptorPin'] and tool['containerId']==EXPORTER['containerId'],'REGISTERED_EXPORTER_CHANGED'
row=json.loads(subprocess.check_output(['docker','inspect',tool['containerId']],timeout=15))[0];host=row['HostConfig']
assert row['Config']['User']=='999:999' and host['Tmpfs']==EXPORTER['tmpfs'] and host['CapDrop']==['ALL'] and not host.get('CapAdd') and host['Memory']==host['MemorySwap']==EXPORTER['memoryBytes'] and host['PidsLimit']==EXPORTER['pidsLimit'],'EXPORTER_TEMPORARY_CONTRACT_CHANGED'
assert not host.get('Binds') and all(m['Type']=='tmpfs' for m in row['Mounts']),'SOURCE_DATA_VOLUME_FORBIDDEN'
transport='test -z""",
)

if __name__=='__main__':
 load=lambda name:json.loads((TASK/name).read_text(encoding='utf-8'))
 output=TASK/'incremental-4-preflight.json';assert not output.exists() and not (TASK/'incremental-4-ui-submission.json').exists(),'ATTEMPT_ALREADY_PREPARED'
 audit=load('binlog-scope-tmpfs-candidate.json');installation=active_source_installation();exporter=load('binlog-tmpfs-tool-provisioned.json');native=load('binlog-tmpfs-full-native-export.json');baseline=load('tmpfs-installed-57.json')
 assert all(v['status']=='PASS' for v in (audit,installation,exporter,native)) and not audit['diagnostics']
 assert installation['sourceCommit']=='d487abf28ae38c2e6db445d8b888bf06b32df4e5' and installation['fileCount']==127 and installation['failedOriginalFilesPreserved']==10044
 assert installation['exporterDescriptorPin']==exporter['descriptorPin']==native['descriptorPin']
 assert native['actualNativeAllSegmentsExported'] and native['allActualExitCodesZero'] and native['totalStderrBytes']==0 and native['end']==audit['end']
 for value in (audit['finishedAt'],native['observedAt'],baseline['observedAt']):assert (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(value)).total_seconds()<900,'PREFLIGHT_STALE'
 assert baseline['http']['backend']['status']=='UP' and baseline['http']['frontend']['httpStatus']==200 and not baseline['activeReservation'] and all(r['running'] for r in baseline['roles'])
 source=next(a for a in baseline['admissions']['source']['body']['applications'] if a['sourceConfigRef']==SOURCE)
 assert source['fullReady'] and not source['fullErrorCode'] and not source['historyErrorCode'] and audit['parentChainRef'] in source['parentChainRefs']
 failed=[]
 for prefix,code in [('incremental','MINIMAL_BINLOG_TOOL_CHANGED'),('incremental-2','FORMAL_CAPTURE_PIPE_DEADLINE'),('incremental-3','FORMAL_CAPTURE_STDERR_LIMIT')]:
  terminal=load(prefix+'-terminal-record.json');assert terminal['result']['state']=='FAILED' and terminal['result']['errorCode']==code
  failed.append(load(prefix+'-ui-submission.json')['request']['operationId'])
 pins=load('registered-binlog-tool-restored.json')['failedOriginalPins']
 for history in ('365','366'):pins+=json.loads((PRIVATE/('failed-'+history+'-all-pins.private.json')).read_text(encoding='utf-8'))['pins']
 assert len(pins)==10044
 variables=dict(FAILED_PINS=pins,FAILED_OPERATIONS=failed,POSITION=audit['start'],ENGINE=installation['engine'],CAPTURE_PIN=installation['captureConfigurationPin'],CONTROL_PIN=installation['controlConfigurationPin'],CONTROL_PID=installation['pid'],EXPORTER=exporter)
 payload='\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT;compile(payload,'<tmpfs-retry-preflight>','exec')
 report=remote('172.30.30.57',payload,120)
 report.update(observedAt=now(),sourceConfigRef=SOURCE,parentChainRef=audit['parentChainRef'],parentPointPin=audit['parentPointPin'],installedModulePin=audit['installedModulePin'],auditedStart=audit['start'],auditedEnd=audit['end'],binlogBytes=audit['binlogBytes'],sourceCommit=installation['sourceCommit'],originalFailedOperations=failed,strictInstalledBinlogToolVerified=True,activeCaptureConfigurationPin=installation['captureConfigurationPin'],exporterDescriptorPin=exporter['descriptorPin'],actualAllNonemptySegmentsExported=True,fullNativeSqlBytes=native['totalSqlBytes'],fullNativeAllStderrZero=True)
 write(output,report);print(json.dumps(report))
