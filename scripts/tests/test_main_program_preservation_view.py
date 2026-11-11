"""Protocol units simulate mount boundaries; only O_PATH smoke is native/read-only."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import stat
import builtins
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
FILE=ROOT/'doc/tasks/20261106-spug-prod-incremental-to-two-targets/main_program_preservation_view.py'
PARENT='/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3'
SOURCE='/mnt/intruoyi-backup-nas'


def subject():
    assert FILE.exists(),'MISSING_PERSISTENT_PRESERVATION_VIEW_HELPER'
    spec=importlib.util.spec_from_file_location('preservation_view_units',FILE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path,raw):return dict(path=path,bytes=len(raw),sha256=sha(raw))


def configuration():
    helper=b'protocol-helper';directory=PARENT+'/installed-tools/main-preservation-view-'+sha(helper)[:12]
    return dict(schemaVersion='MainProgramPreservationView/v1',host='58',targetParent=PARENT,
        sourceMountPoint=SOURCE,repositoryRelativePath='Backup/BackupPackage/spug-target-preservation/main-58-20261111-r1',
        viewPath=PARENT+'/preservation-nas-view',
        source=dict(filesystem='cifs',source='//172.30.30.4/IT共享',root='/',writable=True),
        pins=dict(python=pin('/usr/bin/python3.12',b'protocol-python'),mount=pin('/usr/bin/mount',b'protocol-mount'),
        helper=pin(directory+'/main_program_preservation_view.py',helper)))


class KernelBoundary:
    """Real isolated directory/pin I/O; explicit simulated kernel mount state."""
    native=False
    def __init__(self,module,temporary,config):
        self.module=module;self.base=temporary;self.config=config;self.commands=[];self.created=[];self.changed=None
        self.view_bound=False;self.private=False;self.fail_command=None;self.bad_view=None
        for path in ('/',PARENT,SOURCE,SOURCE+'/Backup/BackupPackage/spug-target-preservation',
                config['pins']['helper']['path'].rsplit('/',1)[0]):
            self.local(path).mkdir(parents=True,exist_ok=True)
        for path in [self.base,*self.base.rglob('*')]:
            if path.is_dir():path.chmod(0o755)
        for name,raw in (('python',b'protocol-python'),('mount',b'protocol-mount'),('helper',b'protocol-helper')):
            p=self.local(config['pins'][name]['path']);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o400 if name=='helper' else 0o755)
        self.root_device=self.local('/').stat().st_dev
        device=str(os.major(self.root_device))+':'+str(os.minor(self.root_device))
        self.rows=['1 0 '+device+' / / rw - ext4 /dev/unit rw',
            '2 1 '+device+' / '+SOURCE+' rw - cifs //172.30.30.4/IT共享 rw']
    def local(self,path):return self.base/str(path).lstrip('/')
    def euid(self):return 0
    def lstat(self,path):return self.local(path).lstat()
    def exists(self,path):return os.path.lexists(self.local(path))
    def read_pin(self,reference):
        p=self.local(reference['path']);before=p.lstat();assert not p.is_symlink() and before.st_nlink==1
        raw=p.read_bytes()
        if pin(reference['path'],raw)!=reference:raise ValueError('VIEW_PIN_CHANGED')
        return raw
    def verify_runtime(self,config):
        for reference in config['pins'].values():self.read_pin(reference)
    def mkdir(self,path,mode):
        self.local(path).mkdir(mode=mode);self.created.append(str(path))
    def mountinfo(self):
        rows=list(self.rows)
        if self.view_bound:
            optional='' if self.private else ' shared:77'
            row='9 1 '+self.rows[1].split()[2]+' /'+self.config['repositoryRelativePath']+' '+self.config['viewPath']+' rw'+optional+' - cifs //172.30.30.4/IT共享 rw'
            if self.bad_view=='root':row=row.replace('/'+self.config['repositoryRelativePath'],'/wrong-root')
            rows.append(row)
            if self.bad_view=='extra':rows.append('10 1 0:99 / /unknown-extra rw - tmpfs tmpfs rw')
            if self.bad_view=='original':rows.pop(0)
        return ('\n'.join(rows)+'\n').encode('utf-8')
    def visible(self,path):
        rows=self.module.parse_mountinfo(self.mountinfo());p=str(path)
        matching=[r for r in rows if p==r['mountPoint'] or p.startswith(r['mountPoint'].rstrip('/')+'/')]
        row=max(matching,key=lambda r:len(r['mountPoint']))
        location=self.local(p)
        if p==self.config['viewPath'] and self.view_bound:
            location=self.local(SOURCE+'/'+self.config['repositoryRelativePath'])
        item=location.stat()
        return dict(row,identity=dict(device=item.st_dev,inode=item.st_ino,mode=item.st_mode,uid=item.st_uid,gid=item.st_gid))
    def run(self,argv,timeout):
        self.commands.append(list(argv))
        if len(self.commands)==self.fail_command:return dict(returncode=7,stdout=b'',stderr=b'finite-mount-error')
        if 'bind' in argv:self.view_bound=True
        if '--make-private' in argv:self.private=True
        return dict(returncode=0,stdout=b'',stderr=b'')


@pytest.fixture
def environment(tmp_path):
    module=subject();config=configuration();system=KernelBoundary(module,tmp_path/'mapped-native-files',config)
    return module,config,system


def test_install_once_creates_only_owned_leaves_and_verifies_both_mount_steps(environment):
    module,config,system=environment;before=deepcopy(config);original=system.mountinfo()
    result=module.install_once(config,system=system)
    assert config==before and result['status']=='VIEW_BOUND_KERNEL_VERIFIED' and result['nativeSystem'] is False
    backing=SOURCE+'/'+config['repositoryRelativePath']
    assert system.created==[backing,config['viewPath']]
    assert stat.S_IMODE(system.local(config['viewPath']).stat().st_mode)==0o700
    assert system.commands==[[config['pins']['mount']['path'],'-i','-n','-o','bind','--',backing,config['viewPath']],
        [config['pins']['mount']['path'],'-i','-n','--make-private','--',config['viewPath']]]
    assert all(line in system.mountinfo().splitlines() for line in original.splitlines())
    assert result['originalMountsUnchanged'] is True and result['businessActions'] is False


def test_startup_validates_existing_directories_and_never_creates(environment):
    module,config,system=environment
    backing=system.local(SOURCE+'/'+config['repositoryRelativePath']);backing.mkdir(mode=0o755)
    view=system.local(config['viewPath']);view.mkdir(mode=0o700)
    result=module.startup(config,system=system)
    assert system.created==[] and len(system.commands)==2 and result['originalMountsUnchanged'] is True


@pytest.mark.parametrize('problem',['schema','host','target-parent','relative','view','source-unc','source-root','source-rw',
    'helper-location','pin','extra-field','unsafe-path'])
def test_bad_configuration_fails_before_directory_or_mount(environment,problem):
    module,c,s=environment
    if problem=='schema':c['schemaVersion']='Unknown/v1'
    elif problem=='host':c['host']='60'
    elif problem=='target-parent':c['targetParent']='/unowned/path'
    elif problem=='relative':c['repositoryRelativePath']+='-other'
    elif problem=='view':c['viewPath']=PARENT+'/other'
    elif problem=='source-unc':c['source']['source']='//other/share'
    elif problem=='source-root':c['source']['root']='/nested'
    elif problem=='source-rw':c['source']['writable']=False
    elif problem=='helper-location':c['pins']['helper']['path']=PARENT+'/unowned/helper.py'
    elif problem=='pin':c['pins']['mount']['sha256']='BAD'
    elif problem=='extra-field':c['allowFallback']=True
    else:c['sourceMountPoint']=SOURCE+'/../unsafe'
    with pytest.raises(ValueError):module.install_once(c,system=s)
    assert s.created==s.commands==[]


@pytest.mark.parametrize('problem',['unc','ro','root','filesystem','stack','nested','missing-shared-parent',
    'existing-backing','existing-view','view-mounted','symlink','tool-pin','unsafe-mode','startup-missing'])
def test_preflight_drift_has_zero_mount_calls(environment,problem,tmp_path):
    module,c,s=environment;startup=False
    if problem=='unc':s.rows[1]=s.rows[1].replace('//172.30.30.4/IT共享','//other/share')
    elif problem=='ro':s.rows[1]=s.rows[1].replace(' rw',' ro')
    elif problem=='root':s.rows[1]=s.rows[1].replace(' / '+SOURCE,' /nested '+SOURCE)
    elif problem=='filesystem':s.rows[1]=s.rows[1].replace(' cifs ',' nfs ')
    elif problem=='stack':s.rows.append(s.rows[1].replace('2 1 ','3 1 '))
    elif problem=='nested':s.rows.append('4 2 0:77 / '+SOURCE+'/Backup rw - tmpfs tmpfs rw')
    elif problem=='missing-shared-parent':s.local(SOURCE+'/Backup/BackupPackage/spug-target-preservation').rmdir()
    elif problem=='existing-backing':s.local(SOURCE+'/'+c['repositoryRelativePath']).mkdir(mode=0o700)
    elif problem=='existing-view':s.local(c['viewPath']).mkdir(mode=0o700)
    elif problem=='view-mounted':s.rows.append('9 1 0:88 / '+c['viewPath']+' rw - tmpfs tmpfs rw')
    elif problem=='symlink':s.local(c['viewPath']).symlink_to(tmp_path/'missing')
    elif problem=='tool-pin':s.local(c['pins']['mount']['path']).write_bytes(b'changed-tool')
    elif problem=='unsafe-mode':s.local(SOURCE+'/Backup').chmod(0o777)
    else:startup=True
    with pytest.raises((ValueError,OSError)):
        (module.startup if startup else module.install_once)(c,system=s)
    assert s.commands==[] and s.created==[]


@pytest.mark.parametrize('problem',['second-command','root','extra','original'])
def test_partial_mount_failure_retains_directories_and_mount_without_rollback(environment,problem):
    module,c,s=environment
    if problem=='second-command':s.fail_command=2
    else:s.bad_view=problem
    with pytest.raises(module.ViewFailure) as caught:module.install_once(c,system=s)
    assert s.view_bound is True and len(s.created)==2 and caught.value.created_paths==tuple(s.created)
    assert caught.value.__cause__ is not None and len(s.commands) in (1,2)
    assert all('umount' not in ' '.join(argv) and 'remount' not in ' '.join(argv) for argv in s.commands)


def test_already_bound_view_is_rejected_without_retry(environment):
    module,c,s=environment;module.install_once(c,system=s);calls=deepcopy(s.commands)
    with pytest.raises(ValueError):module.startup(c,system=s)
    assert s.commands==calls


def test_service_uses_pinned_bootstrap_and_original_mount_dependency_only(environment):
    module,c,s=environment;raw=json.dumps(c,sort_keys=True,separators=(',',':')).encode()
    reference=pin(c['pins']['helper']['path'].rsplit('/',1)[0]+'/view.json',raw)
    text=module.render_service(c,configuration_pin=reference)
    assert 'Type=oneshot' in text and 'RemainAfterExit=yes' in text
    assert 'RequiresMountsFor='+SOURCE in text and 'After=network-online.target remote-fs.target' in text
    assert 'ExecStop' not in text and 'Restart=' not in text and 'daemon-reload' not in text
    argv=shlex.split(next(line.split('=',1)[1] for line in text.splitlines() if line.startswith('ExecStart=')))
    assert argv[:4]==[c['pins']['python']['path'],'-I','-B','-c']
    code=argv[4];compile(code,'unit-bootstrap','exec')
    assert 'sha256' in code and reference['sha256'] in code and c['pins']['helper']['sha256'] in code
    assert argv[-2:]==['--mode','startup']


@pytest.mark.parametrize('mode',['install_once','invalid'])
def test_first_service_invocation_uses_only_an_explicit_install_mode(environment,mode):
    module,c,s=environment;raw=json.dumps(c).encode()
    reference=pin(c['pins']['helper']['path'].rsplit('/',1)[0]+'/view.json',raw)
    if mode=='invalid':
        with pytest.raises(ValueError):module.render_service(c,configuration_pin=reference,mode=mode)
    else:
        text=module.render_service(c,configuration_pin=reference,mode=mode)
        argv=shlex.split(next(line.split('=',1)[1] for line in text.splitlines() if line.startswith('ExecStart=')))
        assert argv[-2:]==['--mode','install_once'] and 'RemainAfterExit=yes' in text


def test_real_linux_o_path_visibility_matches_one_kernel_mount_row(tmp_path):
    module=subject();system=module.NativeSystem();value=system.visible(str(tmp_path))
    rows=module.parse_mountinfo(system.mountinfo())
    assert len([r for r in rows if r['mountId']==value['mountId']])==1
    assert value['identity']['device']==tmp_path.stat().st_dev and value['identity']['inode']==tmp_path.stat().st_ino


def test_tool_drift_after_bind_stops_before_the_second_mount_command(environment):
    module,c,s=environment;original=s.run
    def changed(argv,timeout):
        result=original(argv,timeout)
        if len(s.commands)==1:s.local(c['pins']['mount']['path']).write_bytes(b'changed-between-mounts')
        return result
    s.run=changed
    with pytest.raises(module.ViewFailure):module.install_once(c,system=s)
    assert s.view_bound and len(s.commands)==1


def test_unknown_private_mount_optional_fields_are_not_accepted(environment):
    module,c,s=environment;original=s.mountinfo
    def unknown():
        raw=original()
        before=(c['viewPath']+' rw - cifs').encode()
        return raw.replace(before,(c['viewPath']+' rw future:1 - cifs').encode()) if s.private else raw
    s.mountinfo=unknown
    with pytest.raises(module.ViewFailure):module.install_once(c,system=s)
    assert s.view_bound and len(s.commands)==2


@pytest.mark.parametrize('corrupt',[False,True])
def test_bootstrap_reads_real_mapped_pin_bytes_with_atime_changes_before_helper_exec(environment,corrupt):
    """Map paths explicitly; real file reads change atime, never kernel mounts."""
    module,c,s=environment;helper=b'raise RuntimeError("PINNED_HELPER_REACHED")\n'
    c['pins']['helper']=pin(c['pins']['helper']['path'],helper)
    s.local(c['pins']['helper']['path']).chmod(0o600);s.local(c['pins']['helper']['path']).write_bytes(helper)
    s.local(c['pins']['helper']['path']).chmod(0o400)
    raw=json.dumps(c).encode();reference=pin(c['pins']['helper']['path'].rsplit('/',1)[0]+'/view.json',raw)
    s.local(reference['path']).write_bytes(raw);s.local(reference['path']).chmod(0o400)
    for value in (c['pins']['python'],c['pins']['helper'],reference):
        path=s.local(value['path']);os.utime(path,ns=(1,path.stat().st_mtime_ns))
    if corrupt:reference['sha256']='0'*64
    class MappedPath:
        def __init__(self,value):self.value=Path(value)
        @property
        def parents(self):return tuple(MappedPath(str(p)) for p in self.value.parents)
        def lstat(self):return s.local(str(self.value)).lstat()
        def __fspath__(self):return str(s.local(str(self.value)))
    mapped_os=SimpleNamespace(name='posix',geteuid=lambda:0,path=SimpleNamespace(abspath=lambda p:p),
        open=os.open,fstat=os.fstat,fdopen=os.fdopen,close=os.close,lstat=lambda p:s.local(p).lstat(),
        O_RDONLY=os.O_RDONLY,O_NOFOLLOW=os.O_NOFOLLOW,O_CLOEXEC=os.O_CLOEXEC)
    modules=dict(hashlib=hashlib,os=mapped_os,pathlib=SimpleNamespace(Path=MappedPath),stat=stat,
        sys=SimpleNamespace(executable=c['pins']['python']['path'],argv=['bootstrap']))
    def imports(name,*args,**kwargs):return modules[name]
    namespace={'__builtins__':dict(vars(builtins),__import__=imports)}
    with pytest.raises(ValueError if corrupt else RuntimeError,
            match='VIEW_BOOTSTRAP_PIN_CHANGED' if corrupt else 'PINNED_HELPER_REACHED'):
        exec(module._bootstrap(c,reference),namespace)
