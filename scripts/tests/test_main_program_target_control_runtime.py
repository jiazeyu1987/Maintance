"""Real local files/PIDs with explicit read-only systemd/Docker protocols.

These units do not switch a real service or prove a remote installation.
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

TASK=Path(__file__).resolve().parents[2]/'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
sys.path.insert(0,str(TASK))
FILE=TASK/'main_program_target_control_runtime.py'
import main_program_control_runtime as legacy
from main_program_control_activation import verify_environment_values
from test_installation_history_custody_layered import receipts


def subject():
    assert FILE.exists(),'MISSING_TARGET_RUNTIME_TRANSITION_GATE'
    return importlib.import_module('main_program_target_control_runtime')


def canonical(value):return legacy.canonical(value)
def digest(raw):return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def transition(tmp_path):
    module=subject();parent=tmp_path/'target-control';parent.mkdir();processes=[];calls=[];locked=[True]
    old_commit='a'*40;new_commit='b'*40;target='target-57';host='172.30.30.57'
    script=("import json,os,resource,sys\nresource.setrlimit(resource.RLIMIT_NOFILE,(65536,65536))\n"
        "print(json.dumps({'pid':os.getpid()}),flush=True)\nsys.stdin.buffer.read(1)\n").encode()
    def put(path,value):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(value if type(value) is bytes else canonical(value));return legacy.pin_file(path)
    def package(root,count):
        root.mkdir();files={'control_entry.py':script}
        files.update({'member-'+str(i)+'.py':b'VALUE=True\n' for i in range(1,count)})
        for name,raw in files.items():(root/name).write_bytes(raw)
        hashes={name:digest(raw) for name,raw in files.items()};sha=digest(canonical(hashes))
        pin=put(root/'package.json',dict(files=hashes,packageSha256=sha));return sha,pin
    def start(engine,control_pin,control):
        child=subprocess.Popen([sys.executable,'-B',str(engine/'control_entry.py'),'serve','--config-pin',
            canonical(control_pin).decode()],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            env=dict(os.environ,**control['environment']))
        processes.append(child);value=json.loads(child.stdout.readline());assert value['pid']==child.pid
        assert child.poll() is None;return child
    def stop(child):
        if child.poll() is None:child.communicate(b'x',timeout=10)
        assert child.returncode==0
    units=[];rows=[];baselines=[];properties={};controls={}
    for role,commit,count in [('source','c'*40,2),('target',old_commit,147)]:
        engine=parent/(('source-engine-' if role=='source' else 'engine-main-program-')+commit[:7])
        sha,package_pin=package(engine,count)
        control=dict(pythonPin=dict(path=sys.executable),workingDirectory=str(parent),
            environment=dict(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(engine),LANG='C.UTF-8'))
        cp=put(parent/'configuration'/role/'control.json',control)
        op=put(parent/'configuration'/role/'owner.json',dict(targets={target:{'physical':'unchanged'}}))
        service='control-'+role+'.service';unit=put(tmp_path/'units'/service,b'[Service]\n')
        drop=put(tmp_path/'units'/(service+'.d')/'old.conf',b'[Service]\nLimitNOFILE=65536\n')
        child=start(engine,cp,control);pid=child.pid
        argv=Path('/proc')/str(pid)/'cmdline';env=Path('/proc')/str(pid)/'environ'
        declaration='Environment=PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="'+str(engine)+'"\n'
        row=dict(role=role,service=service,engine=str(engine),pid=pid,controlConfigurationPin=cp,
            ownerConfigurationPin=op,sourceCommit=commit,fileCount=count,fileManifestSha256=sha,
            dropinPin=drop,argvSha256=digest(argv.read_bytes()),environmentMode='ORIGINAL_BASELINE',
            opaqueOriginal={'keep':'every-unknown-field'})
        baseline=dict(**{k:row[k] for k in ('service','engine','pid','controlConfigurationPin','ownerConfigurationPin','argvSha256')},
            unitPin=unit,dropinPins=[drop],environmentSha256=digest(env.read_bytes()),
            systemdEnvironmentRaw=declaration,systemdEnvironmentSha256=digest(declaration.encode()),
            declaredEnvironment=dict(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(engine)))
        row.update({key:deepcopy(baseline[key]) for key in ('environmentSha256','systemdEnvironmentSha256',
            'systemdEnvironmentRaw','declaredEnvironment')})
        properties[service]=dict(MainPID=str(pid),FragmentPath=unit['path'],DropInPaths=drop['path'],
            Requires='history.service',After='history.service',LimitNOFILE='65536',ActiveState='active',SubState='running')
        units.append(dict(service=service,pid=pid,unitPin=unit,dropinPins=[drop],
            directory=str(Path(drop['path']).parent),existingNames=['old.conf']))
        rows.append(row);baselines.append(baseline);controls[role]=control
    target_process=processes[-1]
    new_engine=parent/('engine-main-program-'+new_commit[:7]);new_sha,new_package=package(new_engine,153)
    new_control=deepcopy(controls['target']);new_control['environment']['PYTHONPATH']=str(new_engine)
    cp=put(parent/'configuration'/'new'/'control.json',new_control)
    op=put(parent/'configuration'/'new'/'owner.json',dict(targets={target:{'physical':'unchanged'}}))
    docs=[dict(pin=cp,value=new_control),dict(pin=op,value=legacy.read_pinned(op))]
    docs += [dict(pin=put(parent/'configuration'/'new'/('preservation-'+str(i)+'.json'),{'bound':i}),value={'bound':i}) for i in range(14)]
    core=dict(schemaVersion='MainProgramControlActivation/v1',status='PASS',host=host,targetConfigRef=target,
        **{key:value for key,value in rows[-1].items() if key not in ('environmentMode','argvSha256','opaqueOriginal')})
    candidate=dict(schemaVersion='MainProgramTargetControlCandidate/v1',status='BOUND_NOT_INSTALLED',host=host,
        targetConfigRef=target,sourceCommit=new_commit,previousController=core,
        controller=dict(role='target',service=rows[-1]['service'],engine=str(new_engine),
            previousControlPin=rows[-1]['controlConfigurationPin'],previousOwnerPin=rows[-1]['ownerConfigurationPin'],
            controlPin=cp,ownerPin=op),newDocuments=docs,
        package=dict(fileCount=153,fileManifestSha256=new_sha,packageSha256='d'*64),
        retainedSourceConfigurationUnchanged=True,installationPerformed=False,restoreDispatched=False)
    raw_drop=b'[Unit]\nRequires=spug-main-preservation-view-57-20261111-r1.service\n'
    path=Path(units[-1]['directory'])/'zz-new.conf';new_drop=dict(path=str(path),bytes=len(raw_drop),sha256=digest(raw_drop))
    history=put(tmp_path/'history.json',{'original':'history'})
    guard_pin=put(tmp_path/'units'/'history.service',b'[Service]\nType=oneshot\n')
    fstab=put(tmp_path/'fstab',b'# original\n');mounts=put(tmp_path/'mountinfo',b'original-preservation-view-and-source-mounts\n')
    spec=dict(current=dict(host=host,suffix='57',controllers=rows),unit=dict(controllers=units,
        requiredHistoryGuard='history.service',historyUnitPins=[guard_pin]),environmentBaseline=dict(controllers=baselines),
        targetConfigRef=target,previousCustody=None,oldReceiptPin=None,originalInventory=None,
        retainedDocuments=[history],newDocuments=[r['pin'] for r in docs],historyPins=[history],sourceEvidencePins=[])
    container=dict(Id='e'*64,Image='sha256:'+'f'*64,RestartCount=0,
        State=dict(Running=True,Paused=False,Restarting=False,Pid=123,StartedAt='original',FinishedAt=''),
        Path='original',Args=[],HostConfig={},Config={},Mounts=[])
    guard_props=dict(MainPID='0',ActiveState='active',SubState='exited')
    def run(argv,timeout=90,env=None):
        calls.append(list(argv))
        if argv[:2]==['systemctl','show']:
            if argv[-1]=='Environment':
                value=next(r['systemdEnvironmentRaw'] for r in baselines if r['service']==argv[2]);return value.encode()
            value=guard_props if argv[2]=='history.service' else properties[argv[2]]
            return ''.join(k+'='+v+'\n' for k,v in value.items()).encode()
        if argv[:2]==['systemctl','is-enabled']:return b'enabled\n'
        if argv[:4]==['/usr/bin/docker','--host','unix:///var/run/docker.sock','ps']:return (container['Id']+'\n').encode()
        if argv[:4]==['/usr/bin/docker','--host','unix:///var/run/docker.sock','inspect']:return canonical([container])
        raise AssertionError('unregistered command '+str(argv))
    def lock():
        if not locked[0]:raise ValueError('TEST_LOCK_LOST')
    paths=legacy.RuntimePaths(reservation_path=str(tmp_path/'reservation.json'),fstab_path=fstab['path'],mountinfo_path=mounts['path'])
    def unexpected_custody(value):raise AssertionError('receiptless host must not create custody')
    args=dict(candidate=candidate,dropin_pin=new_drop,verify_environment=verify_environment_values,
        verify_custody=unexpected_custody,lock_guard=lock,run=run,paths=paths)
    def switch(keep_old=False):
        if not keep_old:stop(target_process)
        Path(new_drop['path']).write_bytes(raw_drop)
        child=start(new_engine,cp,new_control)
        prop=properties[rows[-1]['service']];prop['MainPID']=str(child.pid)
        prop['DropInPaths']+=' '+new_drop['path'];return child.pid
    try:
        yield dict(module=module,spec=spec,args=args,rows=rows,candidate=candidate,properties=properties,
            paths=paths,calls=calls,locked=locked,container=container,guard=guard_props,new_engine=new_engine,
            new_control=cp,new_owner=op,new_drop=new_drop,raw_drop=raw_drop,switch=switch,stop=stop,
            target_process=target_process,processes=processes,history=history,fstab=fstab,mounts=mounts)
    finally:
        for child in processes:stop(child)


def api(case):return case['module'].TargetControlRuntimeTransition(case['spec'],**case['args'])


def test_real_old_and_successor_processes_pass_full_transition_without_changing_inputs(transition):
    c=transition;original=deepcopy(c['spec']);candidate=deepcopy(c['candidate']);gate=api(c)
    before=gate.before();pid=c['switch']();result=gate.after(before,successor_pid=pid)
    assert result['status']=='TARGET_SUCCESSOR_RUNTIME_VERIFIED' and result['serverWrites'] is False
    assert result['installationReceiptCreated'] is result['restoreDispatched'] is False
    assert result['before']==before and result['after']['controllers'][0]==before['controllers'][0]
    assert result['after']['packagePins'][0]==before['packagePins'][0]
    assert result['after']['controllers'][-1]['pid']==pid
    assert result['successorController']['opaqueOriginal']==c['rows'][-1]['opaqueOriginal']
    assert result['retainedRowEnvironment']=={key:c['rows'][-1][key] for key in (
        'environmentSha256','systemdEnvironmentSha256','systemdEnvironmentRaw','declaredEnvironment')}
    assert not set(result['retainedRowEnvironment']) & set(result['successorController'])
    assert c['spec']==original and c['candidate']==candidate
    assert all(argv[:2] not in (['systemctl','restart'],['systemctl','daemon-reload']) for argv in c['calls'])


@pytest.mark.parametrize('problem',['role','host','service','previous-owner','previous-control','previous-engine',
    'previous-manifest','file-count','new-engine','new-dropin-location','new-dropin-old','candidate-doc-pin',
    'source-flag','bad-dependency','schema'])
def test_invalid_transition_input_is_rejected_without_any_command(transition,problem):
    c=transition;p=c['candidate'];a=c['args']
    if problem=='role':p['controller']['role']='source'
    elif problem=='host':p['host']='172.30.30.59'
    elif problem=='service':p['controller']['service']='other.service'
    elif problem=='previous-owner':p['controller']['previousOwnerPin']=p['controller']['ownerPin']
    elif problem=='previous-control':p['controller']['previousControlPin']=p['controller']['controlPin']
    elif problem=='previous-engine':p['previousController']['engine']+='/wrong'
    elif problem=='previous-manifest':p['previousController']['fileManifestSha256']='0'*64
    elif problem=='file-count':p['package']['fileCount']=147
    elif problem=='new-engine':p['controller']['engine']=str(Path(c['rows'][-1]['engine']).parent/'wrong')
    elif problem=='new-dropin-location':a['dropin_pin']=dict(c['new_drop'],path='/unrelated/new.conf')
    elif problem=='new-dropin-old':a['dropin_pin']=deepcopy(c['rows'][-1]['dropinPin'])
    elif problem=='candidate-doc-pin':p['newDocuments'][0]['pin']['sha256']='0'*64
    elif problem=='source-flag':p['retainedSourceConfigurationUnchanged']=False
    elif problem=='schema':p['schemaVersion']='Unknown/v1'
    else:a['added_dependencies']={'Requires':['network-online.target'],'After':[]}
    with pytest.raises(ValueError):api(c)
    assert c['calls']==[]


@pytest.mark.parametrize('problem',['new-dropin-exists','missing-new-document','new-package-byte','old-config-byte','old-package-byte'])
def test_before_requires_complete_staged_new_files_and_unchanged_old_files(transition,problem):
    c=transition;gate=api(c)
    if problem=='new-dropin-exists':Path(c['new_drop']['path']).write_bytes(c['raw_drop'])
    elif problem=='missing-new-document':Path(c['new_control']['path']).unlink()
    elif problem=='new-package-byte':(c['new_engine']/'member-1.py').write_bytes(b'changed')
    elif problem=='old-config-byte':Path(c['rows'][-1]['ownerConfigurationPin']['path']).write_bytes(b'changed')
    else:(Path(c['rows'][-1]['engine'])/'member-1.py').write_bytes(b'changed')
    with pytest.raises((ValueError,OSError)):gate.before()


@pytest.mark.parametrize('problem',['old-still-running','old-pid','peer-pid','wrong-pid','extra-dropin','dropin-byte',
    'container','fstab','mounts','history','old-owner','old-package','source-config','source-package','new-package',
    'new-argv','new-environment','dependency','limit','lock-lost','forged-before'])
def test_after_rejects_each_unknown_or_retained_change(transition,problem):
    c=transition;gate=api(c);before=gate.before();pid=c['switch'](keep_old=problem=='old-still-running')
    if problem=='old-pid':pid=c['rows'][-1]['pid']
    elif problem=='peer-pid':pid=c['rows'][0]['pid']
    elif problem=='wrong-pid':pid=999999
    elif problem=='extra-dropin':Path(c['new_drop']['path']).with_name('unexpected.conf').write_bytes(b'[Service]\n')
    elif problem=='dropin-byte':Path(c['new_drop']['path']).write_bytes(b'changed')
    elif problem=='container':c['container']['State']['StartedAt']='changed'
    elif problem in ('fstab','mounts','history'):Path(c[problem]['path']).write_bytes(b'changed')
    elif problem=='old-owner':Path(c['rows'][-1]['ownerConfigurationPin']['path']).write_bytes(b'changed')
    elif problem=='old-package':(Path(c['rows'][-1]['engine'])/'member-1.py').write_bytes(b'changed')
    elif problem=='source-config':Path(c['rows'][0]['controlConfigurationPin']['path']).write_bytes(b'changed')
    elif problem=='source-package':(Path(c['rows'][0]['engine'])/'member-1.py').write_bytes(b'changed')
    elif problem=='new-package':(c['new_engine']/'member-1.py').write_bytes(b'changed')
    elif problem=='new-argv':c['properties'][c['rows'][-1]['service']]['MainPID']=str(c['rows'][0]['pid'])
    elif problem=='new-environment':
        control=json.loads(Path(c['new_control']['path']).read_bytes());control['environment']['LANG']='changed'
        Path(c['new_control']['path']).write_bytes(canonical(control))
    elif problem=='dependency':c['properties'][c['rows'][-1]['service']]['Requires']+=' unexpected.service'
    elif problem=='limit':c['properties'][c['rows'][-1]['service']]['LimitNOFILE']='1024'
    elif problem=='lock-lost':c['locked'][0]=False
    elif problem=='forged-before':before=deepcopy(before);before['mountinfoSha256']='0'*64
    with pytest.raises((ValueError,OSError)):gate.after(before,successor_pid=pid)


@pytest.mark.parametrize('already_declared',[False,True])
def test_exact_preservation_dependency_union_is_deduplicated(transition,already_declared):
    c=transition;dep='spug-main-preservation-view-57-20261111-r1.service'
    c['args']['added_dependencies']={'Requires':[dep],'After':[dep]}
    props=c['properties'][c['rows'][-1]['service']]
    if already_declared:
        props['Requires']+=' '+dep;props['After']+=' '+dep
    gate=api(c);before=gate.before();pid=c['switch']()
    if not already_declared:props['Requires']+=' '+dep;props['After']+=' '+dep
    result=gate.after(before,successor_pid=pid)
    assert result['after']['controllers'][-1]['properties']['Requires'].split().count(dep)==1


def test_old_current_dropin_outside_original_unit_set_is_explicitly_retained(transition):
    c=transition;row=c['rows'][-1];unit=c['spec']['unit']['controllers'][-1]
    old_current=Path(unit['directory'])/'z-current.conf';old_current.write_bytes(b'[Service]\n# original current\n')
    row['dropinPin']=legacy.pin_file(old_current)
    c['candidate']['previousController']['dropinPin']=deepcopy(row['dropinPin'])
    c['properties'][row['service']]['DropInPaths']+=' '+str(old_current)
    gate=api(c);before=gate.before();pid=c['switch']();result=gate.after(before,successor_pid=pid)
    assert result['after']['controllers'][-1]['properties']['DropInPaths'].split()==[
        unit['dropinPins'][0]['path'],str(old_current),c['new_drop']['path']]


def test_real_layered_custody_stays_bound_to_original_spec_under_a_successor_view(receipts):
    import installation_history_custody
    module=subject();custody=receipts['custody'];original=deepcopy(custody)
    def logical(path):return str(path).replace('\\','/')
    def pin(path):
        raw=receipts['files'][logical(path)].read_bytes()
        return dict(path=logical(path),bytes=len(raw),sha256=digest(raw))
    row=dict(service=custody['service'],ownerConfigurationPin=custody['selectedOwnerPin'],
        controlConfigurationPin=custody['selectedControlPin'])
    spec=dict(current=dict(controllers=[row]),previousCustody=custody,oldReceiptPin=custody['selectedCurrentReceiptPin'],
        targetConfigRef=custody['targetConfigRef'],originalInventory=custody['originalInventory'])
    kwargs=dict(pin=pin,read=receipts['reader'],run=lambda *a,**k:pytest.fail('no runtime dispatch in custody unit'),
        verify_environment=verify_environment_values,
        verify_custody=lambda value:installation_history_custody.verify_layered_receipt_custody(value,read_pin=receipts['reader']),
        lock_guard=lambda:None)
    retained=legacy.RuntimeGates(spec,**kwargs);successor=deepcopy(spec)
    successor['current']['controllers'][0]['ownerConfigurationPin']={'new':'runtime-only'}
    successor['current']['controllers'][0]['controlConfigurationPin']={'new':'runtime-only'}
    gate=module.RetainedHistoryRuntimeGates(successor,retained_gates=retained,**kwargs)
    proof=gate.retained_custody();assert proof['status']=='PASS' and len(proof['packagePins'])==3
    assert gate.original_inventory(proof)['originalPathInventoryVerified'] is True
    assert custody==original and retained.spec==spec and gate.spec==successor
    reference=custody['mainSteps'][0]['ownerConfigurationPin'];receipts['files'][reference['path']].write_bytes(b'changed')
    with pytest.raises(ValueError):gate.retained_custody()


def test_unknown_target_observation_field_is_preserved_instead_of_implicitly_allowed(transition,monkeypatch):
    c=transition;original=legacy.RuntimeGates.verify_process;changed=[False]
    def observe(self,row):
        result=original(self,row)
        if row['role']=='target':result['opaqueGateField']='changed' if changed[0] else 'original'
        return result
    monkeypatch.setattr(legacy.RuntimeGates,'verify_process',observe)
    gate=api(c);before=gate.before();pid=c['switch']();changed[0]=True
    with pytest.raises(ValueError):gate.after(before,successor_pid=pid)
