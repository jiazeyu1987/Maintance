"""Real temporary bytes and child processes at explicit proc/systemd boundaries.

No systemd or Docker service is run by this suite. The command adapter launches
a real Python subprocess to deliver registered protocol responses. The proc
adapter contains the real child's reported argv/environment/executable/PID.
"""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import main_program_control_activation as activation
from test_installation_history_custody_layered import receipts


def module():
    return importlib.import_module('main_program_control_runtime')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


@pytest.fixture
def runtime(tmp_path):
    engine = tmp_path / 'engine'; engine.mkdir(); work = tmp_path / 'working'; work.mkdir()
    proc_root = tmp_path / 'proc'; proc_root.mkdir()
    script = engine / 'control_entry.py'
    script.write_text("import json,os,sys\nprint(json.dumps(dict(pid=os.getpid(),argv=[sys.executable,*sys.argv],environment=dict(os.environ),executable=sys.executable)),flush=True)\nsys.stdin.buffer.read(1)\n", encoding='utf-8')
    other = engine / 'other.py'; other.write_bytes(b'VALUE = 1\n')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (script, other)}
    manifest = dict(files=hashes, packageSha256=hashlib.sha256(canonical(hashes)).hexdigest())
    (engine / 'package.json').write_bytes(canonical(manifest))
    def pin(path):
        p = Path(path); before = p.stat(); raw = p.read_bytes(); after = p.stat()
        assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
        return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    def put(name, value):
        p = tmp_path / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value if type(value) is bytes else canonical(value)); return pin(p)
    def read(ref):
        if pin(ref['path']) != ref: raise ValueError('FIXTURE_PIN_CHANGED')
        return json.loads(Path(ref['path']).read_bytes())
    configured = dict(PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=engine.as_posix(), LANG='C.UTF-8', PATH=os.environ.get('PATH',''))
    control = dict(pythonPin=dict(path=sys.executable), environment=configured, workingDirectory=str(work))
    control_pin = put('control.json', control); owner_pin = put('owner.json', dict(targets={}))
    process = subprocess.Popen([sys.executable, '-B', str(script), 'serve', '--config-pin', canonical(control_pin).decode()],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, **configured), text=True)
    try:
        report = json.loads(process.stdout.readline()); assert report['pid'] == process.pid and process.poll() is None
        process_dir = proc_root / str(process.pid); process_dir.mkdir()
        # sys.argv excludes interpreter flags; use actual Popen argv for the two
        # interpreter tokens and the child's independently reported script argv.
        args = [report['executable'], '-B', *report['argv'][1:]]
        cmdline = b'\0'.join(v.encode() for v in args) + b'\0'
        (process_dir / 'cmdline').write_bytes(cmdline)
        environ = b''.join((k+'='+v).encode()+b'\0' for k,v in report['environment'].items())
        (process_dir / 'environ').write_bytes(environ)
        (process_dir / 'limits').write_text('Max open files            65536                65536                files\n', encoding='utf-8')
        unit = put('units/control.service', b'[Service]\n'); dropin = put('units/control.service.d/old.conf', b'[Service]\nLimitNOFILE=65536\n')
        guard_pin = put('units/history.service', b'[Service]\nType=oneshot\n')
        fstab = put('fstab', b'# fixture fstab\n'); mounts = put('mountinfo', b'1 0 0:1 / / rw - tmpfs tmpfs rw\n')
        reservation = tmp_path / 'resource-active.json'
        # shlex treats Windows backslashes as escapes; the real registered
        # Environment= protocol uses forward slashes for this fixture path.
        declaration = 'Environment=PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="' + str(engine).replace('\\','/') + '"\n'
        row = dict(role='target',service='control.service',engine=str(engine),pid=process.pid,
            controlConfigurationPin=control_pin,ownerConfigurationPin=owner_pin,dropinPin=dropin,
            fileCount=2,fileManifestSha256=manifest['packageSha256'],sourceCommit='a'*40,
            argvSha256=hashlib.sha256(cmdline).hexdigest(),environmentMode='ORIGINAL_BASELINE')
        baseline = dict(**{k:row[k] for k in ('service','engine','pid','controlConfigurationPin','ownerConfigurationPin','argvSha256')},
            unitPin=unit,dropinPins=[dropin],environmentSha256=hashlib.sha256(environ).hexdigest(),
            systemdEnvironmentSha256=hashlib.sha256(declaration.encode()).hexdigest(),systemdEnvironmentRaw=declaration,
            declaredEnvironment=dict(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(engine).replace('\\','/')))
        properties = dict(MainPID=str(process.pid),FragmentPath=unit['path'],DropInPaths=dropin['path'],
            Requires='history.service',After='history.service',LimitNOFILE='65536',ActiveState='active',SubState='running')
        guard_properties = dict(MainPID='0',ActiveState='active',SubState='exited')
        container = dict(Id='c'*64,Image='sha256:'+'d'*64,RestartCount=0,
            State=dict(Running=True,Paused=False,Restarting=False,Pid=123,StartedAt='original',FinishedAt=''),
            Path='original',Args=[],HostConfig={},Config={},Mounts=[dict(Destination='/data',Source='/original')])
        transport = tmp_path / 'responses.json'; calls = []; locked = [True]
        def run(args, timeout=90, env=None):
            calls.append(list(args))
            if args[:2] == ['systemctl','show']:
                value = declaration if args[-1]=='Environment' else ''.join(k+'='+v+'\n' for k,v in
                    (guard_properties if args[2]=='history.service' else properties).items())
            elif args[:2] == ['systemctl','is-enabled']: value='enabled\n'
            elif args[:4] == ['/usr/bin/docker','--host','unix:///var/run/docker.sock','ps']: value=container['Id']+'\n'
            elif args[:4] == ['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect']: value=json.dumps([container])
            else: raise AssertionError('unregistered read-only command')
            transport.write_text(json.dumps(value),encoding='utf-8')
            result=subprocess.run([sys.executable,'-B','-c','import json,pathlib,sys;sys.stdout.buffer.write(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")).encode("utf-8"))',str(transport)],
                capture_output=True,timeout=timeout,check=True)
            return result.stdout
        def lock_guard():
            if not locked[0]: raise ValueError('FIXTURE_LOCK_LOST')
        retained = put('retained.json', dict(original=True)); history = put('history.json',dict(operation='original'))
        new_path = tmp_path / 'new.json'; new_raw = canonical(dict(candidate=True))
        new_ref = dict(path=str(new_path),bytes=len(new_raw),sha256=hashlib.sha256(new_raw).hexdigest())
        spec = dict(current=dict(controllers=[row]),unit=dict(controllers=[dict(service=row['service'],pid=row['pid'],unitPin=unit,
            dropinPins=[dropin],directory=str(Path(dropin['path']).parent),existingNames=['old.conf'])],requiredHistoryGuard='history.service',historyUnitPins=[guard_pin]),
            environmentBaseline=dict(controllers=[baseline]),targetConfigRef='fixture-target',oldReceiptPin=None,
            previousCustody=None,originalInventory=None,historyPins=[history],sourceEvidencePins=[],
            retainedDocuments=[retained],newDocuments=[new_ref])
        yield dict(spec=spec,pin=pin,read=read,run=run,lock_guard=lock_guard,locked=locked,calls=calls,
            proc_root=proc_root,process_dir=process_dir,executable=report['executable'],reservation=reservation,
            fstab=Path(fstab['path']),mounts=Path(mounts['path']),properties=properties,guard_properties=guard_properties,
            container=container,new_path=new_path,new_raw=new_raw,retained=retained,history=history,other=other)
    finally:
        if process.poll() is None: process.communicate('x', timeout=10)
        assert process.returncode == 0


def gates(case):
    subject=module()
    class ProcProtocolPaths(subject.RuntimePaths):
        def process_executable(self,pid):
            assert pid==case['spec']['current']['controllers'][0]['pid']
            return str(Path(case['executable']).resolve())
    paths=ProcProtocolPaths(proc_root=case['proc_root'],reservation_path=case['reservation'],
        fstab_path=case['fstab'],mountinfo_path=case['mounts'])
    def no_custody(value): raise AssertionError('unexpected custody for receipt-less controller')
    return subject.RuntimeGates(case['spec'],run=case['run'],pin=case['pin'],read=case['read'],paths=paths,
        verify_environment=activation.verify_environment_values,verify_custody=no_custody,lock_guard=case['lock_guard'])


def test_import_has_no_process_or_file_side_effects(tmp_path):
    before=list(tmp_path.iterdir());assert module().RuntimeGates
    assert list(tmp_path.iterdir())==before


def test_native_reader_checks_real_private_bytes_and_exact_pin(tmp_path):
    value={'message':'real temporary UTF-8 evidence'}
    path=tmp_path/'private.json';path.write_bytes(canonical(value));path.chmod(0o600)
    ref=module().pin_file(path)
    assert module().read_pinned(ref)==value
    path.write_bytes(canonical({'message':'changed'}))
    with pytest.raises(ValueError,match='REMOTE_PIN_CHANGED'):module().read_pinned(ref)


def test_native_reader_rejects_real_hardlinked_file(tmp_path):
    path=tmp_path/'original.json';path.write_bytes(b'{}')
    alias=tmp_path/'alias.json';os.link(path,alias)
    with pytest.raises(ValueError,match='REMOTE_FILE_ALIAS'):module().pin_file(alias)


def test_native_reader_rejects_duplicate_json_members(tmp_path):
    path=tmp_path/'duplicate.json';path.write_bytes(b'{"key":1,"key":2}')
    ref=module().pin_file(path)
    with pytest.raises(ValueError,match='REMOTE_JSON_DUPLICATE_KEY'):module().read_pinned(ref)


def test_native_command_runs_real_child_and_never_exposes_private_error():
    assert module().run_command([sys.executable,'-B','-c','import sys;sys.stdout.buffer.write(b"real")'])==b'real'
    with pytest.raises(ValueError,match='^RUNTIME_COMMAND_FAILED_7$'):
        module().run_command([sys.executable,'-B','-c','import sys;sys.stderr.write("private-error");sys.exit(7)'])


def test_runtime_defaults_are_real_native_boundaries_without_import_io(tmp_path):
    api=module().RuntimeGates({},verify_environment=activation.verify_environment_values,
        verify_custody=lambda value:pytest.fail('not requested'),lock_guard=lambda:None)
    path=tmp_path/'actual.json';path.write_bytes(b'{"real":true}')
    assert api.read(api.pin(path))=={'real':True}
    assert isinstance(api.paths,module().RuntimePaths)
    assert api.run([sys.executable,'-B','-c','print("actual")']).strip()==b'actual'


def test_real_process_metadata_and_command_protocol_pass_complete_before_after(runtime):
    api=gates(runtime);before=api.before()
    assert before['controllers'][0]['pid']==runtime['spec']['current']['controllers'][0]['pid']
    assert before['previousCustodyObservation'] is None
    runtime['new_path'].write_bytes(runtime['new_raw'])
    after=api.preserve(before,documents_created=True)
    assert after['containers']==before['containers']
    assert after['fstabPin']==before['fstabPin']
    assert after['mountinfoSha256']==before['mountinfoSha256']
    assert all(command[:2] not in (['systemctl','restart'],['systemctl','daemon-reload']) for command in runtime['calls'])


@pytest.mark.parametrize('change',['pid','argv','environment','executable','limits','unit','dropin','loaded-unit','loaded-dropin',
    'package-member','package-manifest','history','retained','new-exists','reservation','worker','guard','guard-unit'])
def test_before_rejects_each_original_or_runtime_drift(runtime,change):
    c=runtime
    if change=='pid':c['properties']['MainPID']='999'
    elif change=='argv':(c['process_dir']/'cmdline').write_bytes(b'changed\0')
    elif change=='environment':(c['process_dir']/'environ').write_bytes(b'PATH=changed\0')
    elif change=='executable':c['executable']=str(c['process_dir']/'other')
    elif change=='limits':(c['process_dir']/'limits').write_bytes(b'Max open files 1024 1024 files\n')
    elif change in ('unit','dropin','guard-unit'):
        ref=(c['spec']['unit']['historyUnitPins'][0] if change=='guard-unit' else
             c['spec']['unit']['controllers'][0]['unitPin'] if change=='unit' else c['spec']['unit']['controllers'][0]['dropinPins'][0])
        Path(ref['path']).write_bytes(b'changed')
    elif change=='loaded-unit':c['properties']['FragmentPath']='other'
    elif change=='loaded-dropin':c['properties']['DropInPaths']=''
    elif change=='package-member':c['other'].write_bytes(b'VALUE = 2\n')
    elif change=='package-manifest':(c['other'].parent/'package.json').write_bytes(b'{}')
    elif change in ('history','retained'):Path(c[change]['path']).write_bytes(b'changed')
    elif change=='new-exists':c['new_path'].write_bytes(c['new_raw'])
    elif change=='reservation':c['reservation'].write_bytes(b'{}')
    elif change=='worker':
        p=c['proc_root']/'999999';p.mkdir();p.joinpath('cmdline').write_bytes(c['spec']['current']['controllers'][0]['engine'].encode()+b'\0'+
            str(Path(c['other']).parent.parent/'working').encode()+b'\0worker')
    else:c['guard_properties']['ActiveState']='inactive'
    with pytest.raises((ValueError,KeyError)):gates(c).before()


@pytest.mark.parametrize('change',['container','fstab','mounts','new-missing','new-pin','old-history','old-package','lock-lost'])
def test_preserve_rejects_changes_and_lock_loss_precedes_any_command(runtime,change):
    api=gates(runtime);before=api.before();runtime['new_path'].write_bytes(runtime['new_raw'])
    if change=='container':runtime['container']['State']['StartedAt']='changed'
    elif change in ('fstab','mounts'):runtime[change].write_bytes(b'changed')
    elif change=='new-missing':runtime['new_path'].unlink()
    elif change=='new-pin':runtime['new_path'].write_bytes(b'changed')
    elif change=='old-history':Path(runtime['history']['path']).write_bytes(b'changed')
    elif change=='old-package':runtime['other'].write_bytes(b'changed')
    else:runtime['locked'][0]=False
    count=len(runtime['calls'])
    with pytest.raises((ValueError,FileNotFoundError)):api.preserve(before,documents_created=True)
    if change=='lock-lost':assert len(runtime['calls'])==count


def test_unchanged_unrelated_process_is_not_a_control_worker(runtime):
    p=runtime['proc_root']/'999999';p.mkdir();p.joinpath('cmdline').write_bytes(b'/unrelated/tool\0')
    assert gates(runtime).before()['controllers']


@pytest.mark.parametrize('phase',['before','after'])
def test_unloaded_extra_dropin_is_rejected_in_each_phase(runtime,phase):
    api=gates(runtime)
    if phase=='after':
        before=api.before();runtime['new_path'].write_bytes(runtime['new_raw'])
    directory=Path(runtime['spec']['unit']['controllers'][0]['directory'])
    (directory/'unloaded.conf').write_bytes(b'[Service]\nEnvironment=UNEXPECTED=1\n')
    with pytest.raises(ValueError,match='DROPIN_SET_CHANGED'):
        if phase=='after':api.preserve(before,documents_created=True)
        else:api.before()


def test_custody_uses_real_shared_receipts_and_complete_original_inventory(receipts):
    import installation_history_custody
    c=receipts['custody'];subject=module()
    def logical(path):return str(path).replace('\\','/')
    class Paths(subject.RuntimePaths):
        def read_bytes(self,path):return receipts['files'][logical(path)].read_bytes()
    def pin(path):
        raw=receipts['files'][logical(path)].read_bytes()
        return dict(path=logical(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    selected=dict(service=c['service'],ownerConfigurationPin=c['selectedOwnerPin'],controlConfigurationPin=c['selectedControlPin'])
    spec=dict(current=dict(controllers=[selected]),previousCustody=c,oldReceiptPin=c['selectedCurrentReceiptPin'],
        targetConfigRef=c['targetConfigRef'],originalInventory=c['originalInventory'])
    api=subject.RuntimeGates(spec,run=lambda *a,**k:pytest.fail('custody dispatch forbidden'),pin=pin,read=receipts['reader'],
        paths=Paths(),verify_environment=activation.verify_environment_values,
        verify_custody=lambda value:installation_history_custody.verify_layered_receipt_custody(value,read_pin=receipts['reader']),lock_guard=lambda:None)
    proof=api.retained_custody()
    assert proof['status']=='PASS' and len(proof['packagePins'])==3
    assert api.original_inventory(proof)['originalPathInventoryVerified'] is True
    original=c['originalInventory']['evidencePins'][1];receipts['files'][original['path']].write_bytes(b'changed')
    with pytest.raises(ValueError):api.original_inventory(proof)
