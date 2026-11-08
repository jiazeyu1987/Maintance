"""Read-only reproduction of the retained failing segment; raw stderr is private."""
import argparse,json,re
from common import TASK,PRIVATE,remote,write

SCRIPT=r'''
import datetime,hashlib,json,os,pathlib,selectors,subprocess,sys,time
from types import SimpleNamespace
root=pathlib.Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
source=json.loads((root/'configuration/capture.json').read_bytes())['source']
assert not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION'
reference=source['passwordPin'];secret=pathlib.Path(reference['path']).read_bytes()
assert len(secret)==reference['bytes'] and hashlib.sha256(secret).hexdigest()==reference['sha256'],'SECRET_CHANGED'
engine=pathlib.Path(ENGINE);sys.path[:0]=[str(engine/'formal'),str(engine/'common')]
from minimal_capture_support import MinimalSeries
toolpin=next(r['reference'] for r in source['materialPins'] if r['purpose']=='mysqlbinlog-exporter')
toolraw=pathlib.Path(toolpin['path']).read_bytes();assert hashlib.sha256(toolraw).hexdigest()==toolpin['sha256']
tool=json.loads(toolraw);series=SimpleNamespace(binlog_tool=tool,mysql_source=source['mysqlContainerId'],guard=lambda:None)
if NEW_TOOL:
 row=json.loads(subprocess.check_output(['docker','inspect','spug-intruoyi57-binlog-tmpfs-20261107-v1'],timeout=15))[0]
 tool=dict(tool,containerId=row['Id']);series.binlog_tool=tool
container=MinimalSeries.binlog_container(series,None)
shell='test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec timeout --signal=TERM --kill-after=5s 60s mysqlbinlog "$@"'
args=['docker','exec','-i',container,'sh','-ec',shell,'readonly-binlog-stderr-diagnostic','--no-defaults','--read-from-remote-server',*MinimalSeries.binlog_connection(series),'--user=root','--verify-binlog-checksum','--disable-log-bin','--start-position='+str(SEGMENT['startPosition']),'--stop-position='+str(SEGMENT['stopPosition']),SEGMENT['file']]
started=time.monotonic();stderr=bytearray();output=0;limit_reached=False;deadline=started+70;p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
selector=selectors.DefaultSelector()
try:
 p.stdin.write(secret.rstrip(b'\n')+b'\n');p.stdin.close()
 for stream,kind in ((p.stdout,'out'),(p.stderr,'err')):
  os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,kind)
 while selector.get_map() and not limit_reached:
  assert time.monotonic()<deadline,'DIAGNOSTIC_DEADLINE'
  for key,_ in selector.select(.1):
   raw=os.read(key.fileobj.fileno(),65536)
   if not raw:selector.unregister(key.fileobj);key.fileobj.close();continue
   if key.data=='out':output+=len(raw)
   else:
    stderr.extend(raw[:65536-len(stderr)])
    if len(stderr)>=65536:
     limit_reached=True;p.kill();break
 exitcode=p.wait(timeout=2)
finally:
 selector.close()
 if p.poll() is None:p.kill();p.wait(timeout=2)
 for stream in (p.stdout,p.stderr):
  if not stream.closed:stream.close()
text=stderr.decode('utf-8',errors='strict').replace(secret.rstrip(b'\n').decode(),'[REDACTED]')
print(json.dumps(dict(observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),readOnly=True,segment=SEGMENT,containerId=container,actualExitCode=exitcode,elapsedSeconds=round(time.monotonic()-started,3),stdoutBytes=output,stderrBytes=len(stderr),diagnosticLimitReached=limit_reached,stderr=text,strictToolVerified=True)))
'''

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['diagnostic','bdd-red','tmpfs-diagnostic'],default='diagnostic');args=parser.parse_args()
 suffix='' if args.phase=='diagnostic' else '-'+args.phase
 destination=PRIVATE/('incremental-366-export-stderr'+suffix+'.private.json');assert not destination.exists(),'DIAGNOSTIC_ALREADY_EXISTS'
 installed=json.loads((TASK/'source-control-parent-installation.json').read_text(encoding='utf-8'))
 segment=json.loads((TASK/'binlog-scope-parent-installed.json').read_text(encoding='utf-8'))['segments'][0]
 value=remote('172.30.30.57','NEW_TOOL='+repr(args.phase=='tmpfs-diagnostic')+'\nENGINE='+repr(installed['engine'])+'\nSEGMENT='+repr(segment)+'\n'+SCRIPT,90)
 write(destination,value)
 public={k:v for k,v in value.items() if k!='stderr'}
 public['readOnlyTemporaryFilesystemError']=('OS errno 30 - Read-only file system' in value['stderr'] and '/tmp/tmp.' in value['stderr'])
 public['permissionDenied']=('Permission denied' in value['stderr'])
 public['stderrFirstLine']=re.sub(r"'[^']*'",'[LITERAL]',value['stderr'].splitlines()[0])[:500] if value['stderr'] else ''
 public['diagnosticPhase']=args.phase
 write(TASK/('incremental-366-export-stderr-'+args.phase+'.json'),public);print(json.dumps(public))
