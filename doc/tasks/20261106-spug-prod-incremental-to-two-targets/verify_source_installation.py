"""Read-only completion check of the already installed source generation."""
import hashlib,json
from common import PRIVATE,TASK,SOURCE,remote,write
from install_source_control import SCRIPT

commit='6319024c003ead602d59e7697673fa3c39807863'
build=json.loads((TASK/'release-build-verification.json').read_text(encoding='utf-8'))
baseline=json.loads((PRIVATE/'pre-install-57.private.json').read_text(encoding='utf-8'))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
before={r['Id']:dict(image=r['Image'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in baseline['containers']}
mounts=sorted(' '.join(line.split()[1:]) for line in baseline['mountinfo'].splitlines() if ' - cifs ' in line or 'intruoyi' in line or '/mnt/nas' in line)
oldpin=next(v for k,v in baseline['pins'].items() if k.endswith('configuration/control-postboot-20261105.json'))
variables=dict(COMMIT=commit,SOURCE=SOURCE,PACKAGE_SHA=build['packageSha256'],OLD_CONTROL_PIN=oldpin,EXPECTED=before,EXPECTED_MOUNTS=mounts,EXPECTED_FSTAB=baseline['fstabSha256'])
check=r'''
need(not pathlib.Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESERVATION')
controlpath=root/'configuration'/('control-'+generation+'.json');control=json.loads(controlpath.read_bytes())
ownerpin=control['sourceConfigurations'][SOURCE];need(pin(ownerpin['path'])==ownerpin,'OWNER_PIN_CHANGED')
version=json.loads((engine/'package.json').read_bytes());need(len(version['files'])==126,'PACKAGE_SIZE_INVALID')
need(all(pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'PACKAGE_DRIFT')
need(run(['systemctl','is-active',unit]).strip()==b'active','CONTROL_NOT_ACTIVE')
pid=int(run(['systemctl','show',unit,'-p','MainPID','--value']).strip())
command=(pathlib.Path('/proc')/str(pid)/'cmdline').read_bytes();need(str(engine/'control_entry.py').encode() in command and str(controlpath).encode() in command,'WRONG_ACTIVE_GENERATION')
limits=(pathlib.Path('/proc')/str(pid)/'limits').read_text();need(any(l.startswith('Max open files') and l.split()[3:5]==['65536','65536'] for l in limits.splitlines()),'LIVE_FD_LIMIT_INVALID')
headers=json.loads(pathlib.Path(control['authCredentialRef']['path']).read_bytes())['headers'];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(urllib.request.Request('http://127.0.0.1:'+str(control['listenPort'])+'/selections',headers=headers),timeout=90) as response:
 need(response.status==200,'SOURCE_UNAVAILABLE');selections=json.load(response)
application=next(a for a in selections['applications'] if a['sourceConfigRef']==SOURCE)
need(application['fullReady'] and not application['fullErrorCode'] and not application['historyErrorCode'],'SOURCE_NOT_ADMITTED')
need('smallapp-7fec29a3e132463096aec915c08acab3' in application['parentChainRefs'],'PARENT_NOT_ADMITTED')
need(snapshot()==EXPECTED,'ORIGINAL_DOCKER_RUNTIME_CHANGED')
need(pin('/etc/fstab')['sha256']==EXPECTED_FSTAB and mounts()==EXPECTED_MOUNTS,'PROTECTED_STORAGE_CHANGED')
need(pin(root/'configuration/control-postboot-20261105.json')==OLD_CONTROL_PIN,'OLD_CONFIGURATION_CHANGED')
out=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),sourceCommit=COMMIT,service=unit,sourceConfigRef=SOURCE,oldControlPin=OLD_CONTROL_PIN,controlConfigurationPin=pin(controlpath),ownerConfigurationPin=ownerpin,engine=str(engine),fileCount=len(version['files']),fileManifestSha256=version['packageSha256'],packageSha256=PACKAGE_SHA,dropinPin=pin(dropin),previousPid=20619,pid=pid,liveMaxOpenFiles=65536,originalContainerCount=len(EXPECTED),allOriginalContainersUnchanged=True,fstabAndProtectedMountsUnchanged=True,sourceSelectionsHttp=200,sourceSelections=selections,backupPerformed=False,restorePerformed=False,initialReadinessCheck='CONNECTION_REFUSED_BEFORE_BIND',readOnlyCompletionCheck=True)
receipt=root/'configuration'/('installation-'+generation+'.json')
need(not receipt.exists(),'REMOTE_RECEIPT_ALREADY_EXISTS')
# No remote write in this verifier: persist verified receipt only locally.
print(json.dumps(out))
'''
payload='\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+SCRIPT.split('need(root.resolve()')[0]+check
value=remote('172.30.30.57',payload,180)
write(PRIVATE/'source-control-installation.private.json',value)
public={k:v for k,v in value.items() if k!='sourceSelections'}
write(TASK/'source-control-installation.json',public);print(json.dumps(public))
