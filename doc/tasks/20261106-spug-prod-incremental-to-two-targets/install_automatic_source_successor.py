"""Prepare by default; upgrade only the pinned source control service on --apply."""
import argparse
import ast
import base64
import copy
import hashlib
import inspect
import io
import json
from pathlib import Path
import re
import stat
import subprocess
import tarfile

from common import TASK, PRIVATE, SOURCE, remote, now
from closeout_contracts import (controller_generation, file_pin, pinned, read,
    validate_source_spug, validate_source_restoration, validate_native_dispatch)

ALLOWED_CHANGED_FILES = frozenset(('control/recovery_control_smallapp.py',
    'control/recovery_control_smallapp_native.py'))
FAILED_STAGE_COMMIT = '0dc7429d4758a208a5b0c098111fe9702ab63235'
FAILED_PREPARE_PIN = dict(file='automatic-source-successor-plan-0dc7429.json',bytes=679,
    sha256='5b0d78afdbef3a3543de5719a624ab9e9358589e2a30b850b60bd9a8ebc24e07')
STAGED_OBSERVATION_PIN = dict(file='automatic-source-successor-staged-engine-readonly.json',bytes=2834,
    sha256='11fc6c6d6c385bd2a3d13344d913e5016d46b37887b9d71787f1202adbb55822')
FAILED_LOG_PIN = dict(file='172.30.30.57-error-fc3fa06027c4.private.log',bytes=238,
    sha256='fc3fa06027c4a101180a553e5fecfc33fc88100c783b7c8e0dbf319d24d417e3')


def validate_package_transition(old, new):
    assert set(old) == set(new), 'SOURCE_ONLY_PACKAGE_SCOPE_CHANGED'
    changed = sorted(name for name in old if old[name] != new[name])
    assert changed and set(changed) <= ALLOWED_CHANGED_FILES, 'SOURCE_ONLY_PACKAGE_SCOPE_CHANGED'
    return changed


def local_pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def rebind_document(value, previous, engine):
    if isinstance(value, str):
        return value.replace(previous + '/', engine + '/') if value.startswith(previous + '/') else value
    if isinstance(value, list):
        return [rebind_document(item, previous, engine) for item in value]
    if isinstance(value, dict):
        result = {key: rebind_document(item, previous, engine) for key, item in value.items()}
        if {'path', 'bytes', 'sha256'} <= set(result) and result['path'] != value['path']:
            result.update(local_pin(result['path']))
        return result
    return value


def validate_source_rebinding(original, changed, previous, engine, old_files, new_files):
    """Permit only byte-identical packaged program paths in the two CLI arrays."""
    assert set(original)==set(changed), 'PHYSICAL_SOURCE_BINDING_CHANGED'
    movements=[]
    for reference,before in original.items():
        after=changed[reference]
        assert isinstance(before,dict) and isinstance(after,dict) and set(before)==set(after), 'PHYSICAL_SOURCE_BINDING_CHANGED'
        assert {'configurationPath','sourceIdentityPath','stagingRoot','captureCommand','toolPaths'}<=set(before), 'PHYSICAL_SOURCE_BINDING_CHANGED'
        for field,value in before.items():
            if field not in ('captureCommand','toolPaths'):
                assert after[field]==value, 'PHYSICAL_SOURCE_BINDING_CHANGED'
                continue
            assert isinstance(value,list) and isinstance(after[field],list) and len(value)==len(after[field]), 'PHYSICAL_SOURCE_BINDING_CHANGED'
            for index,(old,new) in enumerate(zip(value,after[field])):
                if old==new:continue
                assert isinstance(old,str) and isinstance(new,str) and old.startswith(previous+'/'), 'PHYSICAL_SOURCE_BINDING_CHANGED'
                relative=old[len(previous)+1:]
                assert relative in old_files and relative in new_files and new==engine+'/'+relative, 'PHYSICAL_SOURCE_BINDING_CHANGED'
                assert old_files[relative]==new_files[relative], 'SOURCE_CAPTURE_PROGRAM_BYTES_CHANGED'
                movements.append(dict(sourceConfigRef=reference,field=field,index=index,relativeProgram=relative,sha256=new_files[relative]))
    return movements


def verify_staged_engine(engine, files, package_pin):
    """Verify exact regular members, directories and package metadata; never write."""
    engine=Path(engine)
    assert engine.is_absolute() and engine.resolve()==engine and engine.is_dir() and not engine.is_symlink(), 'STAGED_ENGINE_ALIAS'
    expected_files=set(files)|{'package.json'}
    expected_dirs=set()
    for name in expected_files:
        relative=Path(name)
        assert not relative.is_absolute() and '..' not in relative.parts, 'STAGED_PACKAGE_PATH_INVALID'
        expected_dirs.update(parent.as_posix() for parent in relative.parents if parent!=Path('.'))
    found_files,found_dirs=set(),set()
    for path in engine.rglob('*'):
        metadata=path.lstat()
        assert path.resolve()==path and not path.is_symlink(), 'STAGED_CHILD_ALIAS'
        relative=path.relative_to(engine).as_posix()
        if stat.S_ISDIR(metadata.st_mode):found_dirs.add(relative)
        else:
            assert stat.S_ISREG(metadata.st_mode) and metadata.st_nlink==1, 'STAGED_REGULAR_FILE_REQUIRED'
            found_files.add(relative)
    assert found_files==expected_files and found_dirs==expected_dirs, 'STAGED_MEMBERS_CHANGED'
    assert local_pin(engine/'package.json')==package_pin, 'STAGED_PACKAGE_METADATA_CHANGED'
    manifest=json.loads((engine/'package.json').read_bytes())
    assert manifest['files']==files and manifest['variant']=='standard' and manifest['fileVerification'] and manifest['payloadContentVerification'], 'STAGED_MANIFEST_CHANGED'
    assert manifest['packageSha256']==hashlib.sha256(json.dumps(files,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(), 'STAGED_MANIFEST_INVALID'
    assert all(local_pin(engine/name)['sha256']==sha for name,sha in files.items()), 'STAGED_FILE_CHANGED'
    return len(files)


def validate_resume_identity(commit, predecessor):
    assert commit==FAILED_STAGE_COMMIT and predecessor=='automatic-control-installation-57.json', 'UNREVIEWED_STAGED_RESUME'


def verify_preconfiguration_stage(configuration, dropins, generation, engine):
    configuration,dropins,engine=Path(configuration),Path(dropins),Path(engine)
    assert configuration.resolve()==configuration and configuration.is_dir(), 'SOURCE_CONFIGURATION_ALIAS'
    names=('repository-','control-','staged-source-','installation-source-')
    planned=[configuration/(prefix+'automatic-'+generation+'.json') for prefix in names]
    assert all(not path.exists() and not path.is_symlink() for path in planned), 'LATER_INSTALLATION_STAGE_ALREADY_EXISTS'
    assert dropins.is_dir() and dropins.resolve()==dropins, 'SOURCE_SERVICE_DROPINS_REQUIRED'
    for path in dropins.glob('*.conf'):
        assert path.resolve()==path and path.is_file() and not path.is_symlink(), 'SOURCE_DROPIN_ALIAS'
        assert generation not in path.name and str(engine).encode() not in path.read_bytes(), 'NEW_SOURCE_DROPIN_ALREADY_EXISTS'


def exclusive_json(path, value):
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
    with Path(path).open('xb') as output:
        output.write(raw)
    assert Path(path).read_bytes() == raw


def package(path, expected_sha):
    raw = Path(path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_sha, 'PACKAGE_SHA_CHANGED'
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        version = json.load(archive.extractfile('package.json'))
        assert version['variant'] == 'standard' and version['fileVerification'] and version['payloadContentVerification']
        names = archive.getnames()
        assert len(names) == len(set(names)) and set(names) == set(version['files']) | {'package.json'}
        for member in archive.getmembers():
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            content = archive.extractfile(member).read()
            if member.name != 'package.json':
                assert hashlib.sha256(content).hexdigest() == version['files'][member.name]
                compile(content, member.name, 'exec')
    return raw, version


SCRIPT = r'''
import base64,copy,datetime,fcntl,hashlib,io,json,os,pathlib,stat,subprocess,sys,tarfile,time,urllib.request,urllib.error
def need(value,code):
 if not value:raise ValueError(code)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def checked(pin):
 path=Path(pin['path']);metadata=path.lstat()
 need(path.resolve()==path and stat.S_ISREG(metadata.st_mode) and metadata.st_nlink==1,'ORIGINAL_PIN_ALIAS')
 need(local_pin(path)==pin,'ORIGINAL_PIN_CHANGED');return json.loads(path.read_bytes())
def run(args,timeout=60,env=None):
 value=subprocess.run(args,capture_output=True,timeout=timeout,env=env)
 need(value.returncode==0,'SOURCE_UPGRADE_COMMAND_FAILED');return value.stdout
def active(unit):return int(run(['systemctl','show',unit,'-p','MainPID','--value']).strip())
def verify_controller(item,generation):
 control=checked(item['controlConfigurationPin']);owner=checked(item['ownerConfigurationPin'])
 need(active(item['service'])==item['pid'],'ORIGINAL_CONTROLLER_PID_CHANGED')
 args=Path('/proc',str(item['pid']),'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
 need((item['engine']+'/control_entry.py').encode() in args and json.loads(args[-1])==item['controlConfigurationPin'],'ORIGINAL_CONTROLLER_ARGV_CHANGED')
 need(args[0].decode()==control['pythonPin']['path'] and Path('/proc',str(item['pid']),'exe').resolve()==Path(control['pythonPin']['path']).resolve(),'ORIGINAL_CONTROLLER_EXECUTABLE_CHANGED')
 need(local_pin(item['dropinPin']['path'])==item['dropinPin'],'ORIGINAL_DROPIN_CHANGED')
 version=json.loads(Path(item['engine'],'package.json').read_bytes())
 need(version['packageSha256']==generation['fileManifestSha256'] and len(version['files'])==generation['fileCount'],'ORIGINAL_PACKAGE_MANIFEST_CHANGED')
 need(hashlib.sha256(canonical(version['files'])).hexdigest()==version['packageSha256'],'ORIGINAL_PACKAGE_MANIFEST_INVALID')
 need(all(local_pin(Path(item['engine'],name))['sha256']==sha for name,sha in version['files'].items()),'ORIGINAL_PACKAGE_CHANGED')
 return control,owner
def no_workers(controls):
 need(not Path('/var/lib/spug-restore-resources/active.json').exists(),'ACTIVE_RESTORE_RESERVATION')
 for path in Path('/proc').iterdir():
  if not path.name.isdecimal():continue
  try:args=(path/'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
  except (FileNotFoundError,ProcessLookupError):continue
  for control in controls:
   if any(control['workingDirectory'].encode() in arg for arg in args):
    need(any(arg.endswith(b'/control_entry.py') for arg in args),'ACTIVE_SOURCE_OR_TARGET_WORKER')
def snapshot():
 ids=run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','ps','-aq','--no-trunc']).decode().split()
 rows=json.loads(run(['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect',*ids]))
 return {r['Id']:dict(image=r['Image'],state={k:r['State'][k] for k in ('Running','Paused','Restarting','Pid','StartedAt','FinishedAt')},definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path','Args','HostConfig','Config')},Mounts=sorted(r['Mounts'],key=lambda m:m['Destination'])))).hexdigest()) for r in rows}
def mounts():return sorted(' '.join(line.split()[1:]) for line in Path('/proc/self/mountinfo').read_text().splitlines() if ' - cifs ' in line or 'intruoyi' in line or '/mnt/nas' in line)
def write_new(path,raw):
 need(path.is_absolute() and path.parent.resolve()==path.parent,'NEW_PATH_ALIAS')
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
 need(path.read_bytes()==raw,'NEW_WRITE_READBACK_FAILED');return local_pin(path)
def verify_pins(pins):
 need(sum(pin['bytes'] for pin in pins)<=512*1024*1024,'HISTORY_METADATA_BUDGET_EXCEEDED')
 for pin in pins:need(local_pin(pin['path'])==pin,'HISTORICAL_METADATA_CHANGED')
def http(control,path):
 ref=control['authCredentialRef'];credential=Path(ref['path']);info=credential.lstat()
 need(credential.resolve()==credential and stat.S_ISREG(info.st_mode) and info.st_nlink==1 and info.st_size<=2048 and info.st_uid==ref['uid']==0 and info.st_gid==ref['gid']==0 and stat.S_IMODE(info.st_mode)==ref['mode']==0o600,'CREDENTIAL_IDENTITY_CHANGED')
 headers=json.loads(credential.read_bytes())['headers']
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(urllib.request.Request('http://127.0.0.1:'+str(control['listenPort'])+path,headers=headers),timeout=40) as response:
  need(response.status==200,'HTTP_STATUS_CHANGED');return json.load(response)
old=SPEC['installation'];source_row,target_row=old['controllers']
source,owner=verify_controller(source_row,SPEC['generations'][0]);target,target_owner=verify_controller(target_row,SPEC['generations'][1])
need(source==source_row['control'] and target==target_row['control'],'PRIVATE_CONTROL_CHANGED')
policy=old['policy'];need(source['sourceEpochPolicies'][SOURCE]==policy,'SOURCE_POLICY_CHANGED')
capture_path=Path(owner['sources'][SOURCE]['configurationPath']);capture_pin=local_pin(capture_path);capture=json.loads(capture_path.read_bytes())
need(capture['source']['sourceIdentity']==policy['sourceIdentity'] and capture['source']['databaseUuid']==policy['databaseUuid'] and capture['sourceLockPath']==policy['sourceLockPath'],'PHYSICAL_SOURCE_CHANGED')
need(target_owner['targetBackupEpochPolicies'][TARGET]==policy,'TARGET_POLICY_CHANGED')
need(target_owner['targets'][TARGET]['replacement']['lockPath']==policy['sourceLockPath'],'PHYSICAL_TARGET_LOCK_CHANGED')
lockpath=Path(policy['sourceLockPath']);need(lockpath.resolve()==lockpath and not lockpath.is_symlink(),'LOCK_ALIAS')
lock=os.open(lockpath,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 need(stat.S_ISREG(os.fstat(lock).st_mode) and os.fstat(lock).st_nlink==1 and (os.fstat(lock).st_dev,os.fstat(lock).st_ino)==(lockpath.stat().st_dev,lockpath.stat().st_ino),'LOCK_IDENTITY_CHANGED')
 no_workers((source,target));before=snapshot();beforemounts=mounts();fstab=local_pin('/etc/fstab')
 sys.path.insert(0,str(Path(source_row['engine'])/'common'))
 from recovery_backup_epoch import read_current
 epoch=read_current(policy);need(epoch==old['epoch'] and epoch['state']=='READY','SOURCE_EPOCH_CHANGED')
 verify_pins(SPEC['historyPins']);verify_pins(SPEC['fullPins']);need(local_pin(capture_path)==capture_pin,'SOURCE_CAPTURE_CHANGED')
 raw=base64.b64decode(SPEC['package']);need(hashlib.sha256(raw).hexdigest()==SPEC['packageSha256'],'PACKAGE_CHANGED')
 engine=Path(source['workingDirectory'])/('engine-automatic-'+SPEC['commit'][:7])
 root=Path(source['workingDirectory'])/'configuration';generation='automatic-'+SPEC['commit'][:7]
 directory=Path('/etc/systemd/system')/(source_row['service']+'.d')
 verify_preconfiguration_stage(root,directory,SPEC['commit'][:7],engine)
 package_pin=dict(path=str(engine/'package.json'),**SPEC['packageJsonIdentity'])
 if SPEC['resumeStagedEngine']:
  observed=SPEC['resumeObservation']
  need(source_row['pid']==25086 and target_row['pid']==20273 and observed['stagedEngine']==str(engine),'STAGED_SOURCE_IDENTITY_CHANGED')
  need(observed['epoch']==epoch and observed['physicalCaptureConfigurationPin']==capture_pin,'STAGED_PHYSICAL_SOURCE_CHANGED')
  need(observed['stagedPackageJsonPin']==package_pin,'STAGED_PACKAGE_CHANGED')
  need(verify_staged_engine(engine,SPEC['files'],package_pin)==130,'STAGED_FILE_COUNT_CHANGED')
 else:need(not engine.exists() and not engine.is_symlink(),'NEW_ENGINE_ALREADY_EXISTS')
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  version=json.load(archive.extractfile('package.json'));names=archive.getnames()
  need(version['files']==SPEC['files'] and version['packageSha256']==SPEC['manifest'],'PACKAGE_MANIFEST_CHANGED')
  need(len(names)==len(set(names)) and set(names)==set(version['files'])|{'package.json'},'PACKAGE_MEMBERS_INVALID')
  for member in archive.getmembers():
   need(member.isfile() and not pathlib.PurePosixPath(member.name).is_absolute() and '..' not in pathlib.PurePosixPath(member.name).parts,'PACKAGE_PATH_INVALID')
   data=archive.extractfile(member).read()
   if member.name!='package.json':need(hashlib.sha256(data).hexdigest()==version['files'][member.name],'PACKAGE_MEMBER_CHANGED');compile(data,member.name,'exec')
  if not SPEC['resumeStagedEngine']:
   engine.mkdir(mode=0o700)
   for member in archive.getmembers():
    path=engine/member.name;path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);write_new(path,archive.extractfile(member).read())
 need(verify_staged_engine(engine,SPEC['files'],package_pin)==130,'NEW_ENGINE_CONTENTS_CHANGED')
 control=rebind_document(source,source_row['engine'],str(engine));new_owner=rebind_document(owner,source_row['engine'],str(engine))
 source_movements=validate_source_rebinding(owner['sources'],new_owner['sources'],source_row['engine'],str(engine),SPEC['oldFiles'],SPEC['files'])
 owner_pin=write_new(root/('repository-'+generation+'.json'),canonical(new_owner));control['sourceConfigurations'][SOURCE]=owner_pin
 control_pin=write_new(root/('control-'+generation+'.json'),canonical(control))
 for role in ('repository','recovery','control'):
  reply=json.loads(run([control['pythonPin']['path'],'-B',str(engine/(role+'_entry.py')),'--check-imports'],env=dict(os.environ,**control['environment'])))
  need(reply['role']==role,'NEW_IMPORT_FAILED')
 row=dict(service=source_row['service'],engine=str(engine),ownerConfigurationPin=owner_pin,controlConfigurationPin=control_pin,control=control,previousPid=source_row['pid'],oldControlPin=source_row['controlConfigurationPin'])
 report=dict(SPEC['receipt'],status='STAGED',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllers=[row,target_row],policy=policy,epoch=epoch,sourceProgramRebindings=source_movements,stagedEngineReused=SPEC['resumeStagedEngine'])
 write_new(root/('staged-source-'+generation+'.json'),canonical(report))
 no_workers((source,target));verify_controller(source_row,SPEC['generations'][0]);verify_controller(target_row,SPEC['generations'][1])
 directory=Path('/etc/systemd/system')/(row['service']+'.d');need(directory.is_dir(),'SOURCE_SERVICE_DROPINS_REQUIRED')
 existing=[path.name for path in directory.glob('*.conf')];leading=max([len(name)-len(name.lstrip('z')) for name in existing]+[0])+1
 dropin=directory/('z'*leading+'-source-'+generation+'.conf');need(all(dropin.name>name for name in existing),'DROPIN_PRECEDENCE_INVALID')
 command=control['pythonPin']['path']+' -B '+str(engine/'control_entry.py')+' serve --config-pin '+"'"+canonical(control_pin).decode()+"'"
 need(all('\n' not in value and '\r' not in value for value in (command,control['environment']['PYTHONPATH'])),'SERVICE_ARG_INVALID')
 write_new(dropin,('[Service]\nEnvironment=PYTHONPATH='+control['environment']['PYTHONPATH']+'\nExecStart=\nExecStart='+command+'\n').encode());dropin.chmod(0o644)
 run(['systemctl','daemon-reload']);run(['systemctl','restart',row['service']]);need(run(['systemctl','is-active',row['service']]).strip()==b'active','SOURCE_NOT_ACTIVE')
 pid=active(row['service']);need(pid>1 and pid!=source_row['pid'],'SOURCE_PID_NOT_REPLACED');row.update(pid=pid,dropinPin=local_pin(dropin))
 args=Path('/proc',str(pid),'cmdline').read_bytes().rstrip(b'\0').split(b'\0');need(str(engine/'control_entry.py').encode() in args and json.loads(args[-1])==control_pin and args[0].decode()==control['pythonPin']['path'] and Path('/proc',str(pid),'exe').resolve()==Path(control['pythonPin']['path']).resolve(),'NEW_SOURCE_ARGV_CHANGED')
 need(any(line.startswith('Max open files') and line.split()[3:5]==['65536','65536'] for line in Path('/proc',str(pid),'limits').read_text().splitlines()),'SOURCE_FD_LIMIT_CHANGED')
 for attempt in range(21):
  try:plan=http(control,'/incremental-plan?sourceConfigRef='+SOURCE);break
  except urllib.error.URLError as error:
   if not isinstance(error.reason,ConnectionRefusedError) or attempt==20:raise
   time.sleep(1)
 need(plan['state']=='READY' and plan['baseFullRef']==SPEC['fullOperation'] and plan['parentChainRef']==SPEC['fullOperation'],'SOURCE_PLAN_NOT_READY_FOR_EXISTING_FULL')
 verify_controller(target_row,SPEC['generations'][1]);need(snapshot()==before,'BUSINESS_RUNTIME_CHANGED')
 need(local_pin('/etc/fstab')==fstab and mounts()==beforemounts,'PROTECTED_STORAGE_CHANGED')
 need(read_current(policy)==epoch and local_pin(capture_path)==capture_pin,'PHYSICAL_SOURCE_CHANGED')
 verify_pins(SPEC['historyPins']);verify_pins(SPEC['fullPins']);no_workers((control,target))
 need(all(local_pin(engine/name)['sha256']==sha for name,sha in version['files'].items()),'INSTALLED_PACKAGE_CHANGED')
 need(checked(source_row['controlConfigurationPin'])==source and checked(source_row['ownerConfigurationPin'])==owner,'PREVIOUS_SOURCE_CHANGED')
 report.update(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),controllers=[row,target_row],plan=plan,liveMaxOpenFiles=65536,
  allOriginalContainersUnchanged=True,fstabAndProtectedMountsUnchanged=True,retainedTargetControlUnchanged=True,epochUnchanged=True,physicalSourceUnchanged=True,
  previousGenerationsRetained=True,historicalOperationMetadataUnchanged=True,historicalMetadataFilesVerified=len(SPEC['historyPins'])+len(SPEC['fullPins']),
  backupPerformed=False,restorePerformed=False,noBackupDispatched=True,noRestoreDispatched=True,businessMutationDispatched=False,controlApiQueriesPerformed=True,queryAuditWritesMayOccur=True)
 write_new(root/('installation-source-'+generation+'.json'),canonical(report));print(json.dumps(report))
finally:os.close(lock)
'''


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--commit', required=True)
    result.add_argument('--predecessor', default='automatic-control-installation-57.json')
    result.add_argument('--apply', action='store_true')
    result.add_argument('--resume-staged-engine', action='store_true')
    return result


def prepare(args):
    assert re.fullmatch('[0-9a-f]{40}', args.commit), 'EXACT_COMMIT_REQUIRED'
    resume_observation=None
    if args.resume_staged_engine:
        validate_resume_identity(args.commit,args.predecessor)
        original_plan=pinned(TASK,FAILED_PREPARE_PIN)
        resume_observation=pinned(TASK,STAGED_OBSERVATION_PIN)
        error=local_pin(PRIVATE/FAILED_LOG_PIN['file'])
        assert {key:error[key] for key in ('bytes','sha256')}=={key:FAILED_LOG_PIN[key] for key in ('bytes','sha256')}, 'FAILED_ATTEMPT_LOG_CHANGED'
        assert original_plan['status']=='PREPARED' and original_plan['sourceCommit']==args.commit
        assert resume_observation['status']=='PASS' and resume_observation['sourceCommit']==args.commit
    predecessor_pin = file_pin(TASK, args.predecessor)
    previous = pinned(TASK, predecessor_pin)
    private_name = args.predecessor[:-5] + '.private.json'
    privileged = json.loads((PRIVATE / private_name).read_text(encoding='utf-8'))
    reduced = copy.deepcopy(privileged)
    for row in reduced['controllers']: row.pop('control')
    assert reduced == previous, 'PRIVATE_INSTALLATION_MISMATCH'
    spug_pin = file_pin(TASK, 'automatic-spug-installation-0d44578.json')
    spug = pinned(TASK, spug_pin)
    validate_source_spug(TASK, previous, spug)
    for name, value in spug['files'].items():
        pin = local_pin(Path(spug['runtime']) / name)
        assert pin['bytes'] == value['bytes'] and pin['sha256'] == value['installedSha256'], 'SPUG_RUNTIME_CHANGED'
    build_pin = file_pin(TASK, 'release-build-' + args.commit[:7] + '.json')
    build = pinned(TASK, build_pin)
    assert build['targetCommit'] == args.commit and build['status'] == 'PASS' and build['allFilesShaAndCompileVerified']
    assert build['fileCount'] == 130 and not build['newCommits'] and not build['mergeRequired']
    expected_worktree = (PRIVATE / ('release-' + args.commit[:7])).resolve()
    assert Path(build['worktree']).resolve() == expected_worktree and expected_worktree.is_dir()
    assert subprocess.check_output(['git','-C',str(expected_worktree),'rev-parse','HEAD'],timeout=30).decode().strip()==args.commit
    assert not subprocess.check_output(['git','-C',str(expected_worktree),'status','--porcelain=v1','--untracked-files=all','--ignored'],timeout=30).strip(), 'COMMITTED_BUILD_WORKTREE_NOT_CLEAN'
    raw, version = package(PRIVATE / ('package-' + args.commit[:7]) / 'backup-restore-standard.tgz', build['packageSha256'])
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:package_json=archive.extractfile('package.json').read()
    package_json_identity=dict(bytes=len(package_json),sha256=hashlib.sha256(package_json).hexdigest())
    assert version['packageSha256'] == build['fileManifestSha256'] and len(version['files']) == build['fileCount']
    old_generation = controller_generation(previous, 0)
    _, old_version = package(PRIVATE / ('package-' + old_generation['sourceCommit'][:7]) / 'backup-restore-standard.tgz', old_generation['packageSha256'])
    changed = validate_package_transition(old_version['files'], version['files'])
    submission, terminal, audit, restored = (read(TASK, 'automatic-full-' + suffix + '.json') for suffix in
                                            ('ui-submission', 'ui-terminal', 'audit', 'source-restoration'))
    historical = read(TASK, 'automatic-control-installation-57.json')
    request = submission['request']
    assert terminal['request'] == request and terminal['operationState'] == 'SUCCEEDED'
    assert audit['status'] == 'PASS' and audit['operationId'] == request['operationId'] and audit['actualExitCode'] == 0
    validate_native_dispatch(audit)
    validate_source_restoration(TASK, 'FULL', restored, historical, request, audit)
    assert audit['sourceEpoch'] == previous['epoch'] and historical['policy'] == previous['policy']
    name = 'automatic-source-control-installation-' + args.commit[:7] + '.json'
    assert not (TASK / name).exists() and not (PRIVATE / name.replace('.json', '.private.json')).exists(), 'SUCCESSOR_ALREADY_RECORDED'
    assert not (PRIVATE / name.replace('.json', '-observed.private.json')).exists(), 'SUCCESSOR_OBSERVATION_ALREADY_RECORDED'
    target_generation = controller_generation(previous, 1)
    target_generation.setdefault('installationPin', file_pin(TASK, 'automatic-control-installation-57.json'))
    receipt = dict(schemaVersion='AutomaticSourceControlUpgrade/v1', sourceCommit=args.commit,
        packageSha256=build['packageSha256'], fileManifestSha256=build['fileManifestSha256'], fileCount=build['fileCount'],
        buildPin=build_pin, predecessorInstallationPin=predecessor_pin, retainedSpugInstallationPin=spug_pin,
        controllerGenerations=[dict(role='SOURCE',sourceCommit=args.commit,packageSha256=build['packageSha256'],
            fileManifestSha256=build['fileManifestSha256'],fileCount=build['fileCount'],buildPin=build_pin), target_generation],
        changedPackageFiles=changed, originalFullOperationId=request['operationId'], originalFullEvidencePins={
            suffix: file_pin(TASK, 'automatic-full-' + suffix + '.json') for suffix in ('ui-submission','ui-terminal','audit','source-restoration')})
    if args.resume_staged_engine:
        assert original_plan['predecessorInstallationPin']==predecessor_pin,'STAGED_PREDECESSOR_CHANGED'
        receipt['resumedStagedEngineEvidence']=dict(failedLogPin=FAILED_LOG_PIN,originalPreparedPlanPin=FAILED_PREPARE_PIN,readonlyStagedObservationPin=STAGED_OBSERVATION_PIN)
    history = read(TASK, 'protected-history-57.json')
    assert history['status'] == 'PASS' and len(history['evidencePins']) == history['protectedFiles']
    full_pins = [audit[key] for key in ('pointPin', 'resultPin', 'sourceRestorationPin', 'manifestPin', 'epochBindingPin')]
    spec = dict(installation=privileged, generations=[controller_generation(previous,i) for i in (0,1)],
        package=base64.b64encode(raw).decode(), packageSha256=build['packageSha256'], files=version['files'],
        manifest=build['fileManifestSha256'],commit=args.commit,receipt=receipt,fullOperation=request['operationId'],
        historyPins=history['evidencePins'],fullPins=full_pins,oldFiles=old_version['files'],packageJsonIdentity=package_json_identity,
        resumeStagedEngine=args.resume_staged_engine,resumeObservation=resume_observation)
    prefix = 'from pathlib import Path\n' + '\n'.join(inspect.getsource(function) for function in
        (local_pin,rebind_document,validate_source_rebinding,verify_staged_engine,verify_preconfiguration_stage))
    payload = ('SOURCE=' + repr(SOURCE) + '\nTARGET=' + repr('intruoyi-main-57-safe-restore-20261105-v2') +
               '\nSPEC=' + repr(spec) + '\nimport hashlib\n' + prefix + '\n' + SCRIPT)
    compile(payload, '<source-successor>', 'exec')
    return name, spec, payload


def main():
    args = parser().parse_args()
    name, spec, payload = prepare(args)
    if not args.apply:
        result = dict(status='PREPARED',preparedOnly=True,sourceCommit=args.commit,sourceService=spec['installation']['controllers'][0]['service'],
            predecessorInstallationPin=spec['receipt']['predecessorInstallationPin'],changedPackageFiles=spec['receipt']['changedPackageFiles'],
            originalFullOperationId=spec['fullOperation'],scriptSha256=hashlib.sha256(payload.encode()).hexdigest(),remoteWrites=False,
            resumeStagedEngine=args.resume_staged_engine,resumedStagedEngineEvidence=spec['receipt'].get('resumedStagedEngineEvidence'))
        prefix='automatic-source-successor-resume-plan-' if args.resume_staged_engine else 'automatic-source-successor-plan-'
        exclusive_json(TASK / (prefix + args.commit[:7] + '.json'), result)
        print(json.dumps(result));return
    result = remote('172.30.30.57', payload, timeout=400)
    exclusive_json(PRIVATE / name.replace('.json','-observed.private.json'), result)
    public = copy.deepcopy(result)
    for row in public['controllers']:row.pop('control')
    from closeout_contracts import validate_source_successor
    validate_source_successor(TASK, public)
    for item in spec['receipt']['originalFullEvidencePins'].values():pinned(TASK,item)
    spug = pinned(TASK,spec['receipt']['retainedSpugInstallationPin'])
    for filename,pin in spug['files'].items():
        actual=local_pin(Path(spug['runtime'])/filename)
        assert actual['bytes']==pin['bytes'] and actual['sha256']==pin['installedSha256'],'SPUG_CHANGED_DURING_UPGRADE'
    exclusive_json(PRIVATE / name.replace('.json','.private.json'), result)
    exclusive_json(TASK / name, public)
    print(json.dumps(dict(status='PASS',report=name,sourceCommit=args.commit,sourcePid=public['controllers'][0]['pid'],retainedTargetPid=public['controllers'][1]['pid'],plan=public['plan'])))


if __name__ == '__main__':main()
