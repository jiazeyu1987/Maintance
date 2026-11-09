"""Storage contract units; Linux directory tests use actual disposable paths."""
import copy
import json
import os
import subprocess
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


def test_nsfs_namespace_root_is_preserved_but_not_valid_data_storage():
    rows=parse_mountinfo('40 1 8:1 / / rw - ext4 /dev/sda1 rw\n'
        '41 40 0:4 net:[4026533000] /run/docker/netns/example rw - nsfs nsfs rw\n')
    assert rows[1]['root']=='net:[4026533000]'
    assert rows[1]['mountPoint']=='/run/docker/netns/example'
    data=contract();data['mounts'][0]['mountIdentity']=rows[1]
    with pytest.raises(Exception,match='REPLACEMENT_FILESYSTEM_UNSUPPORTED'):
        validate_storage(data)


@pytest.mark.parametrize('filesystem,root',[('ext4','net:[4026533000]'),('nsfs','anything'),
    ('nsfs','net:[not-an-inode]')])
def test_only_recognized_nsfs_namespace_roots_may_be_nonabsolute(filesystem,root):
    with pytest.raises(Exception):
        parse_mountinfo(f'40 1 8:1 {root} /run/example rw - {filesystem} nsfs rw\n')


def bind_volume_contract():
    data=contract();data['schemaVersion']='RegisteredReplacementStorage/v2'
    for i,item in enumerate(data['mounts']):
        role=item['role'];source='/volumes/'+role+'/_data';backing='/disk/data/'+role
        item.update(type='volume',source=source,mountIdentity=identity(
            mountId=100+i,parentId=40,root='/data/'+role,mountPoint=source))
        item['volume']=dict(name=role,driver='local',options=dict(type='none',o='bind',device=backing),
            mountpoint=source,backing=dict(source=backing,device=item['device'],inode=item['inode'],
                mountIdentity=identity(mountPoint='/disk')))
    return data


def test_explicit_bind_backed_volume_contract_accepts_only_pinned_local_directory():
    data=bind_volume_contract()
    assert validate_storage(data)==data
    old=copy.deepcopy(data);old['schemaVersion']='RegisteredReplacementStorage/v1'
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_CONFIGURATION_INVALID'):
        validate_storage(old)


@pytest.mark.parametrize('options',[None,{}])
def test_host_managed_bind_volume_keeps_empty_options_and_explicit_backing(options):
    data=bind_volume_contract()
    for item in data['mounts']: item['volume']['options']=options
    assert validate_storage(data)==data


@pytest.mark.parametrize('change',['same-mount','different-filesystem','different-mount-source','ancestor-mount'])
def test_host_bind_requires_a_distinct_local_subdirectory_mount(change):
    data=bind_volume_contract();item=data['mounts'][0];volume=item['volume'];volume['options']=None
    if change=='same-mount': item['mountIdentity']['mountId']=volume['backing']['mountIdentity']['mountId']
    elif change=='different-filesystem': item['mountIdentity']['filesystem']='xfs'
    elif change=='different-mount-source': item['mountIdentity']['source']='/dev/sdb1'
    else:
        item['mountIdentity']['mountPoint']='/volumes/mysql'
        volume['backing']['source']='/disk/data/mysql/_data'
    with pytest.raises(Exception,match='REPLACEMENT_VOLUME_BACKING_CHANGED'):
        validate_storage(data)


@pytest.mark.parametrize('change',['filesystem-root','source-root','inode','device','physical-alias',
    'remote','rbind','read-only','duplicate-options','option-extra','device-root','protected-backing','shared-backing'])
def test_bind_backed_volume_rejects_unsafe_or_mismatched_contract(change):
    data=bind_volume_contract();item=data['mounts'][0];volume=item['volume'];backing=volume['backing']
    if change=='filesystem-root':
        backing['source']=volume['options']['device']='/disk'
    elif change=='source-root': item['mountIdentity']['root']='/'
    elif change=='inode': backing['inode']+=1
    elif change=='device': backing['device']+=1
    elif change=='physical-alias': backing['source']=volume['options']['device']='/disk/elsewhere'
    elif change=='remote': volume['options']['type']='nfs'
    elif change=='rbind': volume['options']['o']='rbind'
    elif change=='read-only': volume['options']['o']='bind,ro'
    elif change=='duplicate-options': volume['options']['o']='bind,bind'
    elif change=='option-extra': volume['options']['addr']='172.30.30.4'
    elif change=='device-root': backing['source']=volume['options']['device']='/dev'
    elif change=='protected-backing': data['protectedRoots'].append(backing['source'])
    elif change=='shared-backing': data['mounts'][1]=copy.deepcopy(item);data['mounts'][1]['role']='minio'
    with pytest.raises(Exception): validate_storage(data)


@pytest.mark.parametrize('options',['driver-bind',None,{}])
def test_snapshot_requires_explicit_inspector_for_versioned_volume_definitions(monkeypatch,options):
    import recovery_replacement_storage as module
    data=bind_volume_contract();observations={}
    rows=service_rows(data);definitions={}
    backing_paths={}
    for item in data['mounts']:
        volume=item['volume'];backing=volume['backing']
        if options!='driver-bind':
            volume['options']=options
            backing_paths[volume['name']]=backing['source']
        rows[item['role']]['Mounts'][0]['Name']=volume['name']
        observations[item['source']]={k:item[k] for k in ('device','inode','mountIdentity')}
        observations[backing['source']]={k:backing[k] for k in ('device','inode','mountIdentity')}
        definitions[volume['name']]=dict(Name=volume['name'],Driver='local',Options=volume['options'],
            Mountpoint=volume['mountpoint'])
    def observe(path,*,backing=None):
        if path in [item['source'] for item in data['mounts']]:
            assert backing is not None
        return observations[path]
    monkeypatch.setattr(module,'observe_directory',observe)
    kwargs=dict(volume_inspector=lambda name:definitions[name])
    if backing_paths: kwargs['volume_backing_paths']=backing_paths
    assert snapshot_mounts(rows,data['protectedRoots'],**kwargs)==data
    with pytest.raises(AssertionError): snapshot_mounts(rows,data['protectedRoots'])


@pytest.mark.parametrize('backings',[{'unknown':'/disk/data/unknown'},[],{'mysql':'/disk/../mysql'}])
def test_snapshot_rejects_unused_or_malformed_explicit_backing_inputs(backings):
    with pytest.raises(Exception):
        snapshot_mounts({},['/mnt/nas'],volume_inspector=lambda name:{},volume_backing_paths=backings)


def test_snapshot_requires_volume_inspector_for_explicit_host_backing():
    with pytest.raises(Exception,match='REPLACEMENT_VOLUME_BACKING_INPUT_INVALID'):
        snapshot_mounts({},['/mnt/nas'],volume_backing_paths={'mysql':'/disk/data/mysql'})


def test_legacy_contracts_continue_to_reject_local_volume_options():
    from recovery_replacement_storage import _volume
    rows=volume_rows();n=native(rows);original=n.docker
    def docker(args):
        if args[:2]==['volume','inspect']:
            return json.dumps([dict(Name='mysql',Driver='local',Mountpoint='/volumes/mysql',
                Options=dict(type='none',o='bind',device='/data/mysql'))]).encode()
        return original(args)
    n.docker=docker
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_INVALID'):
        _volume(n,rows['mysql']['Mounts'][0])


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


def historical_archive_target(tmp_path):
    rows = {}
    for role, destination in [('mysql', '/var/lib/mysql'), ('minio', '/data'), ('redis', '/data')]:
        path = tmp_path / role
        path.mkdir()
        rows[role] = dict(Id='id-' + role, Mounts=[dict(
            Type='bind', Source=str(path), Destination=destination, RW=True)])
    protected = ['/mnt/nas', *[str(tmp_path / name) for name in
                              ('archives', 'operations', 'states', 'target')]]
    value = dict(schemaVersion='RegisteredApplicationReplacement/v2',
                 storage=snapshot_mounts(rows, protected))
    n = native(rows)
    n.source['archiveRoots'] = [protected[1], str(tmp_path / 'historical-archives')]
    n.root = Path(protected[2]) / 'op'
    n.config = dict(dataRoot=protected[4], replacement=dict(stateRoot=protected[3]))
    return n, value, rows


@pytest.mark.skipif(os.name != 'posix', reason='Actual Linux archive storage custody')
def test_historical_archive_roots_extend_protection_without_changing_original_target(tmp_path):
    n, value, rows = historical_archive_target(tmp_path)
    before = copy.deepcopy((value, n.source))
    assert verify_storage(n, value, rows) == {str(tmp_path / r): 'id-' + r for r in rows}
    assert (value, n.source) == before
    assert n.calls == [['ps', '--all', '--no-trunc', '--format', '{{.ID}}'],
                       ['inspect', *[row['Id'] for row in rows.values()]]]


@pytest.mark.skipif(os.name != 'posix', reason='Actual Linux archive storage custody')
@pytest.mark.parametrize('relative', ['mysql', '.', 'mysql/nested'])
def test_new_archive_cannot_overlap_writable_data(tmp_path, relative):
    n, value, rows = historical_archive_target(tmp_path)
    n.source['archiveRoots'][-1] = str(tmp_path / relative)
    with pytest.raises(Exception, match='REPLACEMENT_PROTECTED_STORAGE_OVERLAP'):
        verify_storage(n, value, rows)


@pytest.mark.skipif(os.name != 'posix', reason='Actual Linux archive storage custody')
@pytest.mark.parametrize('roots', [[], '/archives', [None], ['relative'],
                                  ['/archives/../data'], ['/archives//data'], ['/']])
def test_new_archive_roots_require_explicit_canonical_paths(tmp_path, roots):
    n, value, rows = historical_archive_target(tmp_path)
    n.source['archiveRoots'] = roots
    with pytest.raises(Exception, match='REPLACEMENT_(ARCHIVE_ROOTS_INVALID|STORAGE_PATH_INVALID)'):
        verify_storage(n, value, rows)


@pytest.mark.skipif(os.name != 'posix', reason='Actual Linux symlink ancestry')
def test_new_archive_symlink_ancestor_cannot_hide_data_overlap(tmp_path):
    n, value, rows = historical_archive_target(tmp_path)
    link = tmp_path / 'archive-link'
    link.symlink_to(tmp_path / 'mysql', target_is_directory=True)
    n.source['archiveRoots'][-1] = str(link / 'nested')
    with pytest.raises(Exception, match='PATH_ALIAS_REJECTED'):
        verify_storage(n, value, rows)


@pytest.mark.skipif(os.name != 'posix', reason='Actual Linux bind mount aliases')
def test_new_archive_bind_alias_cannot_hide_data_overlap(tmp_path):
    n, value, rows = historical_archive_target(tmp_path)
    archive = Path(n.source['archiveRoots'][-1])
    archive.mkdir()
    subprocess.run(['mount', '--bind', str(tmp_path / 'mysql'), str(archive)], check=True, capture_output=True)
    try:
        with pytest.raises(Exception, match='REPLACEMENT_PROTECTED_STORAGE_OVERLAP'):
            verify_storage(n, value, rows)
    finally:
        subprocess.run(['umount', str(archive)], check=True, capture_output=True)


@pytest.mark.skipif(os.name != 'posix', reason='Actual Linux archive storage custody')
@pytest.mark.parametrize('root_index', [0, 2, 3, 4])
def test_new_archives_do_not_supply_missing_original_protection(tmp_path, root_index):
    n, value, rows = historical_archive_target(tmp_path)
    del value['storage']['protectedRoots'][root_index]
    with pytest.raises(Exception, match='REPLACEMENT_PROTECTED_ROOT_REQUIRED'):
        verify_storage(n, value, rows)


@pytest.mark.skipif(os.name != 'posix', reason='Actual Linux archive storage custody')
def test_new_archive_keeps_stopped_consumer_exclusion(tmp_path):
    original, value, rows = historical_archive_target(tmp_path)
    other = dict(Id='stopped-id', State=dict(Running=False), Mounts=[dict(
        Source=str(tmp_path / 'mysql' / 'child'), RW=True)])
    n = native(rows, others={'stopped-id': other})
    n.source, n.root, n.config = original.source, original.root, original.config
    with pytest.raises(Exception, match='REPLACEMENT_VOLUME_SHARED'):
        verify_storage(n, value, rows)


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


@pytest.mark.skipif(os.name!='posix',reason='Actual bind-backed directory custody requires Linux mount capability')
@pytest.mark.parametrize('options',['driver-bind',None,{}])
def test_actual_bind_backed_volume_snapshot_revalidation_and_drift(tmp_path,options):
    disk=tmp_path/'disk';backing=disk/'data'/'mysql';backing.mkdir(parents=True)
    source=tmp_path/'volumes'/'mysql'/'_data';source.mkdir(parents=True)
    subprocess.run(['mount','--bind',str(backing),str(source)],check=True,capture_output=True)
    try:
        row=dict(Id='mysql-id',Mounts=[dict(Type='volume',Name='mysql',Source=str(source),
            Destination='/var/lib/mysql',RW=True)])
        rows=dict(mysql=row)
        definition=dict(Name='mysql',Driver='local',Mountpoint=str(source),
            Options=dict(type='none',o='bind',device=str(backing)) if options=='driver-bind' else options)
        protected=['/mnt/nas',str(tmp_path/'archives'),str(tmp_path/'operations'),str(tmp_path/'states'),str(tmp_path/'target')]
        kwargs=dict(volume_inspector=lambda name:definition)
        if options!='driver-bind': kwargs['volume_backing_paths']=dict(mysql=str(backing))
        data=snapshot_mounts(rows,protected,**kwargs)
        assert data['schemaVersion']=='RegisteredReplacementStorage/v2'
        assert data['mounts'][0]['volume']['backing']['inode']==backing.stat().st_ino==source.stat().st_ino
        with pytest.raises(Exception,match='REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED'):
            snapshot_mounts(rows,protected)
        if options!='driver-bind':
            assert data['mounts'][0]['volume']['options']==options
            with pytest.raises(Exception,match='REPLACEMENT_STORAGE_MOUNT_ROOT_REFUSED'):
                snapshot_mounts(rows,protected,volume_inspector=lambda name:definition)
            with pytest.raises(Exception,match='REPLACEMENT_VOLUME_BACKING_INPUT_INVALID'):
                snapshot_mounts(rows,protected,volume_inspector=lambda name:definition,
                    volume_backing_paths=dict(mysql=str(backing),unknown=str(backing)))
        n=native(rows);n.root=Path(protected[2])/'op';n.source['archiveRoots']=[protected[1]]
        n.config.update(dataRoot=protected[4],replacement=dict(stateRoot=protected[3]))
        original=n.docker
        n.docker=lambda args:json.dumps([definition]).encode() if args[:2]==['volume','inspect'] else original(args)
        value=dict(schemaVersion='RegisteredApplicationReplacement/v2',storage=data)
        assert verify_storage(n,value,rows)=={str(source):'mysql-id'}
        # The other container's ordinary bind source aliases the same physical data.
        other=dict(Id='stopped-id',Mounts=[dict(Source=str(backing),RW=True)])
        n2=native(rows,others={'stopped-id':other});n2.root=n.root;n2.source=n.source;n2.config=n.config
        original2=n2.docker
        n2.docker=lambda args:json.dumps([definition]).encode() if args[:2]==['volume','inspect'] else original2(args)
        with pytest.raises(Exception,match='REPLACEMENT_VOLUME_SHARED'):
            verify_storage(n2,value,rows)
        saved=definition['Options'];definition['Options']={} if saved is None else None
        with pytest.raises(Exception,match='REPLACEMENT_VOLUME_CONFIGURATION_CHANGED'):
            verify_storage(n,value,rows)
        definition['Options']=saved
        data['protectedRoots'].append(str(backing))
        with pytest.raises(Exception,match='REPLACEMENT_PROTECTED_STORAGE_OVERLAP'):
            verify_storage(n,value,rows)
        data['protectedRoots'].pop()
        data['mounts'][0]['volume']['backing']['inode']+=1
        with pytest.raises(Exception,match='REPLACEMENT_VOLUME_BACKING_CHANGED'):
            verify_storage(n,value,rows)
    finally:
        subprocess.run(['umount',str(source)],check=True,capture_output=True)


@pytest.mark.skipif(os.name!='posix',reason='Actual directory observation requires Linux')
def test_nsfs_nested_or_selected_is_rejected_without_dropping_mountinfo(tmp_path):
    root=tmp_path/'data';root.mkdir();child=root/'namespace';child.mkdir()
    actual=observe_directory(str(root))['mountIdentity']
    raw=f"{actual['mountId']} 1 {actual['device']} {actual['root']} {actual['mountPoint']} rw - {actual['filesystem']} {actual['source']} rw\n"
    raw+=f"999999 {actual['mountId']} 0:4 net:[4026533000] {child} rw - nsfs nsfs rw\n"
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_NESTED_MOUNT'):
        observe_directory(str(root),raw)
    with pytest.raises(Exception,match='REPLACEMENT_FILESYSTEM_UNSUPPORTED'):
        observe_directory(str(child),raw)
