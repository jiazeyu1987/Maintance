"""Admit attempt three against the actual committed parent-guard installation."""
import datetime
import json

from common import PRIVATE, SOURCE, TASK, now, remote, write
from prepare_incremental_retry import SCRIPT as ORIGINAL_SCRIPT


SCRIPT = ORIGINAL_SCRIPT.replace(
    "import hashlib,json,pathlib,subprocess",
    "import hashlib,json,os,pathlib,stat,subprocess,sys,time",
).replace(
    "for reference in FAILED_PINS:\n raw=pathlib.Path(reference['path']).read_bytes();assert len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'FAILED_ORIGINAL_CHANGED'",
    """deadline=time.monotonic()+90
def identity(info):return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
for reference in FAILED_PINS:
 path=pathlib.Path(reference['path']);before=path.lstat();sha=hashlib.sha256();size=0
 assert path.resolve()==path and stat.S_ISREG(before.st_mode) and before.st_nlink==1,'FAILED_ORIGINAL_PATH_CHANGED'
 with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as stream:
  assert identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED'
  while True:
   assert time.monotonic()<deadline,'FAILED_ORIGINAL_READ_DEADLINE'
   chunk=stream.read(1024*1024)
   if not chunk:break
   sha.update(chunk);size+=len(chunk)
  assert identity(os.fstat(stream.fileno()))==identity(before),'FAILED_ORIGINAL_CHANGED'
 assert identity(path.lstat())==identity(before) and size==reference['bytes'] and sha.hexdigest()==reference['sha256'],'FAILED_ORIGINAL_CHANGED'""",
).replace(
    "transport='test -z",
    """sys.path[:0]=[str(pathlib.Path(ENGINE)/'common'),str(pathlib.Path(ENGINE)/'formal'),'/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/runtime/lib/python3.12/site-packages']
from minimal_capture_support import MinimalSeries
from types import SimpleNamespace
assert MinimalSeries.binlog_container(SimpleNamespace(binlog_tool=tool,mysql_source=mysql,guard=lambda:None),None)==tool['containerId'],'STRICT_BINLOG_TOOL_REQUIRED'
transport='test -z""",
).replace(
    "assert 'smallapp-a690233d967d4965bf5f861dc1126961' not in bindings,'FAILED_POINT_PUBLISHED'",
    "assert not set(FAILED_OPERATIONS).intersection(bindings),'FAILED_POINT_PUBLISHED'",
)


if __name__ == '__main__':
    load = lambda name: json.loads((TASK / name).read_text(encoding='utf-8'))
    output = TASK / 'incremental-3-preflight.json'
    assert not output.exists() and not (TASK / 'incremental-3-ui-submission.json').exists(), 'ATTEMPT_ALREADY_PREPARED'
    audit = load('binlog-scope-parent-installed.json')
    installation = load('source-control-parent-installation.json')
    baseline = load('parent-installed-57.json')
    assert audit['status'] == installation['status'] == 'PASS' and not audit['diagnostics']
    assert installation['sourceCommit'] == 'd487abf28ae38c2e6db445d8b888bf06b32df4e5'
    assert installation['fileCount'] == 127 and installation['failedOriginalFilesPreserved'] == 9128
    for timestamp in (audit['finishedAt'], baseline['observedAt']):
        assert (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(timestamp)).total_seconds() < 900, 'PREFLIGHT_STALE'
    assert baseline['http']['backend']['status'] == 'UP' and baseline['http']['frontend']['httpStatus'] == 200
    assert not baseline['activeReservation'] and all(row['running'] for row in baseline['roles'])
    source = baseline['admissions']['source']['body']['applications'][0]
    assert source['fullReady'] and not source['fullErrorCode'] and not source['historyErrorCode']
    assert audit['parentChainRef'] in source['parentChainRefs']
    failed = []
    for prefix, code in [('incremental', 'MINIMAL_BINLOG_TOOL_CHANGED'), ('incremental-2', 'FORMAL_CAPTURE_PIPE_DEADLINE')]:
        terminal = load(prefix + '-terminal-record.json')
        assert terminal['result']['state'] == 'FAILED' and terminal['result']['errorCode'] == code
        failed.append(load(prefix + '-ui-submission.json')['request']['operationId'])
    pins = load('registered-binlog-tool-restored.json')['failedOriginalPins']
    pins += json.loads((PRIVATE / 'failed-365-all-pins.private.json').read_text(encoding='utf-8'))['pins']
    assert len(pins) == 9128
    variables = dict(FAILED_PINS=pins, FAILED_OPERATIONS=failed, POSITION=audit['start'], ENGINE=installation['engine'])
    payload = '\n'.join(key + '=' + repr(value) for key, value in variables.items()) + '\n' + SCRIPT
    compile(payload, '<parent-retry-preflight>', 'exec')
    value = remote('172.30.30.57', payload, 120)
    value.update(observedAt=now(), sourceConfigRef=SOURCE, parentChainRef=audit['parentChainRef'],
                 parentPointPin=audit['parentPointPin'], installedModulePin=audit['installedModulePin'],
                 auditedStart=audit['start'], auditedEnd=audit['end'], binlogBytes=audit['binlogBytes'],
                 sourceCommit=installation['sourceCommit'], originalFailedOperations=failed,
                 strictInstalledBinlogToolVerified=True)
    write(output, value)
    print(json.dumps(value))
