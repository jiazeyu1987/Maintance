"""Native filesystem contracts in isolated temporary trees, never live paths."""
from copy import deepcopy
import errno
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tarfile

import pytest
import test_main_program_target_control_candidate as units

TASK=Path(__file__).resolve().parents[2]/'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
sys.path.insert(0,str(TASK))
FILE=TASK/'main_program_target_control_staging.py'


def subject():
    assert FILE.exists(),'MISSING_TARGET_ONLY_FILESYSTEM_STAGING'
    spec=importlib.util.spec_from_file_location('target_control_staging_units',FILE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def archive(files,change=None,extra=None):
    hashes={name:units.digest(raw) for name,raw in files.items()}
    metadata=dict(variant='standard',fileVerification=True,payloadContentVerification=True,
        files=hashes,packageSha256=units.digest(units.canonical(hashes)))
    contents=dict(files,**{'package.json':units.canonical(metadata)})
    if change:change(contents)
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as output:
        for name,raw in contents.items():
            row=tarfile.TarInfo(name);row.size=len(raw);output.addfile(row,io.BytesIO(raw))
        if extra:output.addfile(extra[0],io.BytesIO(extra[1]))
    return buffer.getvalue(),contents


@pytest.fixture
def material(tmp_path):
    k=units.inputs.__wrapped__();parent=tmp_path/'control'
    def relocate(value):
        if type(value) is str:
            if value.startswith('/control'):
                return ':'.join(str(parent)+part[len('/control'):] if part.startswith('/control') else part
                    for part in value.split(':'))
            return value
        if type(value) is dict:return {a:relocate(b) for a,b in value.items()}
        if type(value) is list:return [relocate(v) for v in value]
        return value
    k=relocate(k);units.graph_repin(k);units.repin(k)
    for targets in k['control']['restoreConfigurations'].values():targets['target-58']=deepcopy(k['current_controller']['ownerConfigurationPin'])
    units.repin(k)
    old_raw,old_files=archive(k['previous_package_files']);raw,files=archive(k['package_files'])
    k['old_build']['packageSha256']=k['current_controller']['packageSha256']=units.digest(old_raw)
    k['new_build']['packages'][0].update(sha256=units.digest(raw),bytes=len(raw))
    for name,content in old_files.items():
        p=Path(k['current_controller']['engine'])/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content);p.chmod(0o400)
    for value,key in ((k['owner'],'ownerConfigurationPin'),(k['control'],'controlConfigurationPin')):
        p=Path(k['current_controller'][key]['path']);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(units.canonical(value));p.chmod(0o400)
    candidate=units.build(k)
    args={name:value for name,value in k.items() if name not in ('package_files','previous_package_files')}
    args.update(candidate=candidate,package_raw=raw,previous_package_raw=old_raw)
    return dict(args=args,oldFiles=old_files,files=files,parent=parent)


def snapshot(root):
    result={}
    for path in [root,*sorted(root.rglob('*'))]:
        value=path.lstat()
        result[str(path)]=(value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns,
            units.digest(path.read_bytes()) if path.is_file() and not path.is_symlink() else None,
            os.readlink(path) if path.is_symlink() else None)
    return result


def test_preflight_rebuilds_and_reads_all_originals_before_any_write(material):
    module=subject();args=material['args'];before=snapshot(material['parent']);inputs=deepcopy(args)
    result=module.preflight_target_filesystem(**args)
    assert result['status']=='PREFLIGHT_ONLY_NOT_STAGED' and result['payloadFileCount']==153
    assert result['packageFileCount']==154 and result['documentCount']==16
    assert len(result['retainedPins'])==150
    assert snapshot(material['parent'])==before and args==inputs


def test_stage_creates_exact_immutable_package_and_documents_and_keeps_originals(material):
    module=subject();args=material['args'];before=snapshot(material['parent']);inputs=deepcopy(args)
    result=module.stage_target_filesystem(**args)
    assert args==inputs and result['status']=='FILES_STAGED_RUNTIME_UNVERIFIED'
    assert result['activationReportEligible'] is False and result['payloadFileCount']==153
    assert result['packageFileCount']==154 and result['documentCount']==16
    assert result['controlServicesReloaded'] is result['restoreDispatched'] is result['installationPerformed'] is False
    engine=Path(args['new_engine']);configuration=Path(args['configuration_root'])
    expected={engine/name:raw for name,raw in material['files'].items()}
    expected.update({Path(row['pin']['path']):units.canonical(row['value']) for row in args['candidate']['newDocuments']})
    actual={p for root in (engine,configuration) for p in root.rglob('*') if p.is_file()}
    assert actual==set(expected) and len(actual)==170
    for path,raw in expected.items():
        assert path.read_bytes()==raw and stat.S_IMODE(path.stat().st_mode)==0o400 and path.stat().st_nlink==1
    current=snapshot(material['parent'])
    for name,value in before.items():
        if name==str(material['parent']) or name==str(material['parent']/'configuration'):continue
        assert current[name]==value
    assert set(result['createdPaths'])==set(current)-set(before)


@pytest.mark.parametrize('problem',['candidate','candidate-doc-pin','package-sha','old-package-sha','original-owner',
    'original-control','original-payload','original-metadata','missing-original','old-hardlink','old-symlink',
    'existing-engine','existing-config','engine-symlink','config-symlink','ancestor-symlink','dangling-engine',
    'bad-root','foreign-engine','build-manifest'])
def test_invalid_preflight_has_zero_new_writes(material,problem,tmp_path):
    module=subject();args=material['args'];engine=Path(args['new_engine']);config=Path(args['configuration_root'])
    core=args['current_controller']
    def rewrite(path,raw):path.chmod(0o600);path.write_bytes(raw)
    if problem=='candidate':args['candidate']['retainedSourceConfigurationUnchanged']=False
    elif problem=='candidate-doc-pin':args['candidate']['newDocuments'][0]['pin']['sha256']='0'*64
    elif problem=='package-sha':args['package_raw']+=b'changed'
    elif problem=='old-package-sha':args['previous_package_raw']+=b'changed'
    elif problem=='original-owner':rewrite(Path(core['ownerConfigurationPin']['path']),b'changed-owner')
    elif problem=='original-control':rewrite(Path(core['controlConfigurationPin']['path']),b'changed-control')
    elif problem=='original-payload':rewrite(Path(core['engine'])/'recovery_entry.py',b'changed-payload')
    elif problem=='original-metadata':rewrite(Path(core['engine'])/'package.json',b'changed-metadata')
    elif problem=='missing-original':(Path(core['engine'])/'recovery_entry.py').unlink()
    elif problem=='old-hardlink':os.link(Path(core['engine'])/'recovery_entry.py',tmp_path/'hardlink')
    elif problem=='old-symlink':
        p=Path(core['engine'])/'recovery_entry.py';raw=p.read_bytes();p.unlink();target=tmp_path/'link-target';target.write_bytes(raw);p.symlink_to(target)
    elif problem=='existing-engine':engine.mkdir()
    elif problem=='existing-config':config.mkdir()
    elif problem=='engine-symlink':engine.symlink_to(Path(core['engine']),target_is_directory=True)
    elif problem=='config-symlink':config.symlink_to(Path(core['ownerConfigurationPin']['path']).parent,target_is_directory=True)
    elif problem=='dangling-engine':engine.symlink_to(tmp_path/'missing')
    elif problem=='ancestor-symlink':
        old=material['parent']/'configuration';moved=material['parent']/'real-configuration';old.rename(moved);old.symlink_to(moved,target_is_directory=True)
    elif problem=='bad-root':args['configuration_root']=str(config.parent/'../escape')
    elif problem=='foreign-engine':args['new_engine']=str(tmp_path/'engine-main-program-ccccccc')
    else:args['new_build']['packages'][0]['fileManifestSha256']='0'*64
    before=snapshot(material['parent'])
    with pytest.raises((ValueError,OSError)):module.stage_target_filesystem(**args)
    assert snapshot(material['parent'])==before


@pytest.mark.parametrize('problem',['duplicate','traversal','symlink','metadata','compile','extra'])
def test_rehashed_bad_official_package_is_rejected_before_first_write(material,problem):
    module=subject();args=material['args'];payload={n:r for n,r in material['files'].items() if n!='package.json'}
    extra=None;mutate=None
    if problem in ('duplicate','traversal','symlink'):
        payload.pop(next(iter(payload)))
        row=tarfile.TarInfo(next(iter(payload)) if problem=='duplicate' else '../escape.py' if problem=='traversal' else 'alias.py')
        content=b'VALUE=1\n';row.size=len(content)
        if problem=='symlink':row.type=tarfile.SYMTYPE;row.linkname='recovery_entry.py';content=b'';row.size=0
        extra=(row,content)
    elif problem=='metadata':mutate=lambda f:f.update({'package.json':b'{}'})
    elif problem=='compile':payload['recovery_entry.py']=b'return 1\n'
    else:payload['extra.py']=b'EXTRA=True\n'
    raw,_=archive(payload,mutate,extra);args['package_raw']=raw
    args['new_build']['packages'][0].update(sha256=units.digest(raw),bytes=len(raw))
    before=snapshot(material['parent'])
    with pytest.raises((ValueError,SyntaxError)):module.stage_target_filesystem(**args)
    assert snapshot(material['parent'])==before


def test_partial_write_failure_retains_created_files_and_exact_cause(material,monkeypatch):
    module=subject();args=material['args'];before=snapshot(material['parent']);write=module.legacy._write_exclusive;calls=[]
    def fail_second(path,raw,created):
        calls.append(str(path))
        if len(calls)==2:raise OSError(errno.ENOSPC,'finite-test-no-space')
        return write(path,raw,created)
    monkeypatch.setattr(module.legacy,'_write_exclusive',fail_second)
    with pytest.raises(module.TargetStagingFailure) as caught:module.stage_target_filesystem(**args)
    error=caught.value
    assert isinstance(error.__cause__,OSError) and error.__cause__.errno==errno.ENOSPC
    assert error.failed_path==calls[1] and calls[0] in error.created_paths and Path(calls[0]).exists()
    assert not Path(calls[1]).exists() and not Path(args['configuration_root']).exists()
    current=snapshot(material['parent'])
    assert set(error.created_paths)==set(current)-set(before)
    for name,value in before.items():
        if name==str(material['parent']):continue
        assert current[name]==value


def test_no_automatic_retry_after_partial_failure(material,monkeypatch):
    module=subject();args=material['args'];write=module.legacy._write_exclusive
    def fail_after_real_file(path,raw,created):
        write(path,raw,created);raise OSError(errno.EIO,'finite-test-after-write')
    monkeypatch.setattr(module.legacy,'_write_exclusive',fail_after_real_file)
    with pytest.raises(module.TargetStagingFailure):module.stage_target_filesystem(**args)
    before=snapshot(material['parent'])
    with pytest.raises(ValueError,match='ENGINE_EXISTS'):module.stage_target_filesystem(**args)
    assert snapshot(material['parent'])==before


def test_final_mode_drift_is_rejected_and_files_are_retained(material,monkeypatch):
    module=subject();args=material['args'];write=module.legacy._write_exclusive;written=[]
    def change_prior_mode(path,raw,created):
        result=write(path,raw,created);written.append(path)
        if len(written)==2:written[0].chmod(0o600)
        return result
    monkeypatch.setattr(module.legacy,'_write_exclusive',change_prior_mode)
    with pytest.raises(module.TargetStagingFailure,match='PARTIAL_FILES_RETAINED') as caught:
        module.stage_target_filesystem(**args)
    assert str(written[0]) in caught.value.created_paths and written[0].exists()
    assert 'STAGED_IDENTITY_CHANGED' in str(caught.value.__cause__)


def test_original_change_during_writes_is_rejected_and_new_files_are_retained(material,monkeypatch):
    module=subject();args=material['args'];write=module.legacy._write_exclusive;changed=[]
    def change_original(path,raw,created):
        result=write(path,raw,created)
        if not changed:
            original=Path(args['current_controller']['engine'])/'recovery_entry.py'
            original.chmod(0o600);original.write_bytes(b'changed-during-write');changed.append(original)
        return result
    monkeypatch.setattr(module.legacy,'_write_exclusive',change_original)
    with pytest.raises(module.TargetStagingFailure) as caught:module.stage_target_filesystem(**args)
    assert caught.value.failed_path==str(changed[0]) and len(caught.value.created_paths)>=170
    assert 'FILE_PIN_CHANGED' in str(caught.value.__cause__) and Path(args['new_engine']).exists()


def test_document_phase_failure_keeps_engine_and_partial_configuration(material,monkeypatch):
    module=subject();args=material['args'];write=module.legacy._write_exclusive
    def fail_policy(path,raw,created):
        if str(path)==args['configuration_root']+'/preservation/policy.json':
            raise OSError(errno.EIO,'finite-policy-write-failure')
        return write(path,raw,created)
    monkeypatch.setattr(module.legacy,'_write_exclusive',fail_policy)
    with pytest.raises(module.TargetStagingFailure) as caught:module.stage_target_filesystem(**args)
    engine=Path(args['new_engine']);configuration=Path(args['configuration_root'])
    assert len([p for p in engine.rglob('*') if p.is_file()])==154
    assert len([p for p in configuration.rglob('*') if p.is_file()])==13
    assert caught.value.failed_path.endswith('/preservation/policy.json') and caught.value.__cause__.errno==errno.EIO
