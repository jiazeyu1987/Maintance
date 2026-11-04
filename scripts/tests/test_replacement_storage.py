"""Storage contract units; Linux directory tests use actual disposable paths."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from recovery_replacement_storage import (parse_mountinfo, validate_storage,
    verify_storage, observe_directory, snapshot_mounts, physical_location)


def identity(**changes):
    value = dict(mountId=40, parentId=1, device='8:1', root='/', mountPoint='/',
                 filesystem='ext4', source='/dev/sda1', options=['rw', 'relatime'],
                 superOptions=['rw'])
    value.update(changes)
    return value


def contract():
    return dict(schemaVersion='RegisteredReplacementStorage/v1',
        protectedRoots=['/mnt/nas', '/archives', '/operations', '/states', '/target'], mounts=[
            dict(role=role, type='bind', source='/data/'+role,
                 destination=destination, device=2049, inode=100+index,
                 mountIdentity=identity())
            for index, (role, destination) in enumerate([
                ('mysql','/var/lib/mysql'),('minio','/data'),('redis','/data')])])


def service_rows(storage):
    return {item['role']: dict(Id='container-'+item['role'], Mounts=[dict(
        Type=item['type'], Source=item['source'], Destination=item['destination'], RW=True)])
        for item in storage['mounts']}


def native(rows, *, others=None):
    others = {} if others is None else others
    inspections = dict(others, **{row['Id']: row for row in rows.values()})
    calls=[]
    def docker(args):
        calls.append(args)
        if args[:1] == ['ps']:
            return ('\n'.join(inspections)+'\n').encode()
        if args[:2] == ['volume','inspect']:
            name=args[2]
            return json.dumps([dict(Driver='local',Options=None,
                Mountpoint='/volumes/'+name)]).encode()
        if args[:1] == ['inspect']:
            return json.dumps([inspections[i] for i in args[1:]]).encode()
        raise AssertionError(args)
    value=SimpleNamespace(docker=docker,inspect=lambda i:inspections[i],source=dict(
        archiveRoots=['/archives']),root=Path('/operations/op1'),config=dict(
        dataRoot='/target',replacement=dict(stateRoot='/states')),calls=calls)
    return value


def test_mountinfo_decodes_escaped_paths_and_ignores_optional_fields():
    rows=parse_mountinfo('40 1 8:1 / / rw,relatime shared:3 - ext4 /dev/sda1 rw\n'
        '42 40 8:1 /my\\040data /mnt/my\\040data rw - ext4 /dev/sda1 rw\n')
    assert rows == [identity(), identity(mountId=42,parentId=40,root='/my data',
        mountPoint='/mnt/my data',options=['rw'])]


def test_mountinfo_preserves_unrelated_windows_backslash_source():
    rows=parse_mountinfo('40 1 8:1 / / rw - ext4 /dev/sda1 rw\n'
        '41 40 0:100 / /host rw - 9p C:\\134Users rw\n')
    assert rows[1]['source']=='C:\\Users'


@pytest.mark.parametrize('raw',['','bad row','x 1 8:1 / / rw - ext4 /dev/a rw',
    '40 1 8:1 / / rw - ext4 /dev/a rw\n40 1 8:1 / / rw - ext4 /dev/a rw'])
def test_malformed_or_duplicate_mountinfo_is_rejected(raw):
    with pytest.raises(Exception,match='REPLACEMENT_MOUNTINFO_INVALID'):
        parse_mountinfo(raw)


def test_v2_storage_has_exact_structure_and_fixed_nas_protection():
    validate_storage(contract())
    value=contract();value['protectedRoots'].remove('/mnt/nas')
    with pytest.raises(Exception,match='REPLACEMENT_PROTECTED_ROOT_REQUIRED'):
        validate_storage(value)
    value=contract();value['unexpected']=True
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_CONFIGURATION_INVALID'):
        validate_storage(value)


@pytest.mark.parametrize('field,value', [('source','/data/../mysql'),('source','relative'),
    ('source','/'),('type','tmpfs'),('device',True),('inode',0),('role','backend')])
def test_invalid_registered_storage_cannot_be_enabled(field,value):
    data=contract();data['mounts'][0][field]=value
    with pytest.raises(Exception): validate_storage(data)


@pytest.mark.parametrize('fstype',['nfs','nfs4','cifs','overlay','tmpfs','fuse.sshfs'])
def test_nonpersistent_or_remote_filesystems_are_rejected(fstype):
    data=contract();data['mounts'][0]['mountIdentity']['filesystem']=fstype
    with pytest.raises(Exception,match='REPLACEMENT_FILESYSTEM_UNSUPPORTED'):
        validate_storage(data)


@pytest.mark.parametrize('field',['options','superOptions'])
def test_read_only_mount_or_underlying_filesystem_is_rejected(field):
    data=contract();data['mounts'][0]['mountIdentity'][field]=['ro']
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_READ_ONLY'):
        validate_storage(data)


@pytest.mark.parametrize('source',['/mnt/nas/data','/archives/app','/operations','/states/db'])
def test_protected_storage_overlap_is_rejected(source):
    data=contract();data['mounts'][0]['source']=source
    with pytest.raises(Exception,match='REPLACEMENT_PROTECTED_STORAGE_OVERLAP'):
        validate_storage(data)


def test_nested_or_duplicate_write_storage_is_rejected():
    data=contract();data['mounts'][1]['source']='/data/mysql/objects'
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_OVERLAP'):
        validate_storage(data)


def test_two_mount_aliases_map_to_the_same_physical_directory():
    mounts=[identity(), identity(mountId=41,parentId=40,root='/data',mountPoint='/alias')]
    assert physical_location('/data/minio',mounts)==physical_location('/alias/minio',mounts)


def test_v2_rejects_storage_alias_inside_protected_mount():
    data=contract()
    data['mounts'][0]['source']='/data/mysql'
    data['mounts'][0]['mountIdentity']['root']='/mnt/nas'
    with pytest.raises(Exception,match='REPLACEMENT_PROTECTED_STORAGE_OVERLAP'):
        validate_storage(data)


def test_v1_keeps_bind_rejection():
    data=contract();rows=service_rows(data)
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_INVALID'):
        verify_storage(native(rows),dict(schemaVersion='RegisteredApplicationReplacement/v1'),rows)


def test_v1_local_volume_remains_valid_and_rejects_shared_descendant():
    rows={'mysql':dict(Id='mysql-id',Mounts=[dict(Type='volume',Name='mysql',
        Source='/volumes/mysql',Destination='/var/lib/mysql',RW=True)])}
    value=dict(schemaVersion='RegisteredApplicationReplacement/v1')
    assert verify_storage(native(rows),value,rows)=={'/volumes/mysql':'mysql-id'}
    other=dict(Id='stopped-id',Mounts=[dict(Source='/volumes/mysql/nested',RW=True)])
    with pytest.raises(Exception,match='REPLACEMENT_VOLUME_SHARED'):
        verify_storage(native(rows,others={'stopped-id':other}),value,rows)


def volume_rows():
    return {'mysql':dict(Id='mysql-id',Mounts=[dict(Type='volume',Name='mysql',
        Source='/volumes/mysql',Destination='/var/lib/mysql',RW=True)])}


@pytest.mark.parametrize('other_count',[1,113,187])
def test_all_consumers_are_freshly_read_with_one_bulk_inspect_per_verification(other_count):
    rows=volume_rows();others={'stopped-'+str(i):dict(Id='stopped-'+str(i),
        State=dict(Running=False),Mounts=[]) for i in range(other_count)}
    n=native(rows,others=others);value=dict(schemaVersion='RegisteredApplicationReplacement/v1')
    for count in (1,2):
        verify_storage(n,value,rows)
        ps=[call for call in n.calls if call[:1]==['ps']]
        bulk=[call for call in n.calls if call[:1]==['inspect']]
        assert len(ps)==len(bulk)==count
        assert ps[-1]==['ps','--all','--no-trunc','--format','{{.ID}}']
        assert set(bulk[-1][1:])=={'mysql-id',*others}


@pytest.mark.parametrize('ids',['missing','duplicate','unexpected'])
def test_bulk_consumer_inspection_must_return_the_complete_unique_requested_ids(ids):
    rows=volume_rows();others={'stopped-id':dict(Id='stopped-id',Mounts=[])}
    n=native(rows,others=others);original=n.docker
    def docker(args):
        raw=original(args)
        if args[:1]!=['inspect']:
            return raw
        result=json.loads(raw)
        if ids=='missing': result=result[:1]
        elif ids=='duplicate': result=[result[0],result[0]]
        else: result[0]['Id']='unexpected-id'
        return json.dumps(result).encode()
    n.docker=docker
    with pytest.raises(Exception,match='REPLACEMENT_CONSUMER_INVENTORY_CHANGED'):
        verify_storage(n,dict(schemaVersion='RegisteredApplicationReplacement/v1'),rows)


@pytest.mark.parametrize('listing',[b'mysql-id\nmysql-id\n',b'stopped-id\n',b''])
def test_duplicate_or_incomplete_consumer_listing_is_rejected(listing):
    rows=volume_rows();n=native(rows,others={'stopped-id':dict(Id='stopped-id',Mounts=[])})
    original=n.docker
    n.docker=lambda args:listing if args[:1]==['ps'] else original(args)
    with pytest.raises(Exception,match='REPLACEMENT_CONSUMER_INVENTORY_CHANGED'):
        verify_storage(n,dict(schemaVersion='RegisteredApplicationReplacement/v1'),rows)


def test_v2_requires_actual_operation_archive_and_state_protection():
    data=contract();data['protectedRoots']=['/mnt/nas']
    rows=service_rows(data)
    with pytest.raises(Exception,match='REPLACEMENT_PROTECTED_ROOT_REQUIRED'):
        verify_storage(native(rows),dict(schemaVersion='RegisteredApplicationReplacement/v2',storage=data),rows)


def test_native_preflight_runs_before_any_replacement_prepare(monkeypatch):
    import recovery_replace
    calls=[]
    native=SimpleNamespace(replacement_preflight=lambda:calls.append('main-inputs'))
    monkeypatch.setattr(recovery_replace,'verify_services',lambda n,v:calls.append('storage'))
    native.mysql=SimpleNamespace(query=lambda sql:(_ for _ in ()).throw(RuntimeError('STOP_BEFORE_WRITES')))
    with pytest.raises(RuntimeError,match='STOP_BEFORE_WRITES'):
        recovery_replace.prepare(native,{})
    assert calls==['main-inputs','storage']


@pytest.mark.parametrize('database,valid', [('ruoyi-vue-pro',True),('small_app2',True),
    ('a`b',False),('ruoyi vue pro',False),('../ruoyi',False),('a'*65,False)])
def test_replacement_database_accepts_hyphens_without_widening_sql_identifiers(tmp_path,database,valid):
    from recovery_replace import validate
    state=tmp_path/'states';state.mkdir()
    target=dict(database=database,services=[dict(role='mysql')],redisRebuild=dict(database=0),
        replacement=dict(schemaVersion='RegisteredApplicationReplacement/v1',stateRoot=str(state),
            lockPath=str(tmp_path/'source.lock'),databaseUuid='9f7a672a-ce77-11f1-9f3a-0242ac1ca820',
            services=dict(mysql={})))
    if valid:
        assert validate(target)==target['replacement']
    else:
        with pytest.raises(Exception,match='REPLACEMENT_DATABASE_INVALID'):
            validate(target)


@pytest.mark.skipif(os.name!='posix',reason='Actual directory/mount custody requires Linux')
def test_actual_directory_observation_and_replacement_detection(tmp_path):
    # Parent integration supplies a disposable local-filesystem volume for basetemp.
    root=tmp_path/'mysql';root.mkdir()
    observed=observe_directory(str(root))
    assert observed['device']==root.stat().st_dev
    assert observed['inode']==root.stat().st_ino
    renamed=tmp_path/'old';root.rename(renamed);root.mkdir()
    assert observe_directory(str(root))['inode'] != observed['inode']


@pytest.mark.skipif(os.name!='posix',reason='Symlink and live mount custody require Linux')
def test_actual_symlink_source_is_rejected(tmp_path):
    data=tmp_path/'actual';data.mkdir();link=tmp_path/'link';link.symlink_to(data, target_is_directory=True)
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_PATH_INVALID'):
        observe_directory(str(link))


@pytest.mark.skipif(os.name!='posix',reason='Live mount snapshot requires Linux')
def test_snapshot_and_verify_real_directories_without_mutation(tmp_path):
    storage=[]
    for role,dest in [('mysql','/var/lib/mysql'),('minio','/data'),('redis','/data')]:
        path=tmp_path/role;path.mkdir()
        storage.append((role,dict(Id='id-'+role,Mounts=[dict(Type='bind',Source=str(path),Destination=dest,RW=True)])))
    rows=dict(storage)
    protected=['/mnt/nas',str(tmp_path/'archives'),str(tmp_path/'operations'),str(tmp_path/'states')]
    protected.append(str(tmp_path/'target'))
    data=snapshot_mounts(rows,protected)
    value=dict(schemaVersion='RegisteredApplicationReplacement/v2',storage=data)
    n=native(rows);n.source['archiveRoots']=[protected[1]];n.root=Path(protected[2])/'op'
    n.config['replacement']['stateRoot']=protected[3]
    n.config['dataRoot']=protected[4]
    assert verify_storage(n,value,rows)=={str(tmp_path/r):'id-'+r for r in ['mysql','minio','redis']}
    changed=copy.deepcopy(value);changed['storage']['mounts'][0]['inode']+=1
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_DIRECTORY_CHANGED'):
        verify_storage(n,changed,rows)
    changed=copy.deepcopy(value);changed['storage']['mounts'][0]['mountIdentity']['mountId']+=1
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_DIRECTORY_CHANGED'):
        verify_storage(n,changed,rows)
    other=dict(Id='stopped-id',Mounts=[dict(Source=str(tmp_path/'mysql'/'child'),RW=True)])
    n2=native(rows,others={'stopped-id':other});n2.source=n.source;n2.root=n.root;n2.config=n.config
    with pytest.raises(Exception,match='REPLACEMENT_VOLUME_SHARED'):
        verify_storage(n2,value,rows)
    rows['minio']['Mounts'][0]['Source']=str(tmp_path/'other')
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_BINDING_CHANGED'):
        verify_storage(n,value,rows)
