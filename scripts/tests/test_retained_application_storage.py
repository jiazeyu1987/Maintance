"""Preserved application binds never become replacement data or unnamed owners."""
import copy
import os
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from test_replacement_storage import native
from recovery_replacement_storage import validate_storage, verify_storage


def configuration(row):
    row.update(Path='/bin/app', Args=[], HostConfig={}, Config=dict(Env=[], Labels={}))
    return row


@pytest.fixture
def observed(tmp_path):
    from recovery_replacement_storage import snapshot_retained_storage
    runtime=tmp_path/'runtime';runtime.mkdir()
    rows={}
    for role, destination in [('mysql','/var/lib/mysql'),('minio','/data'),('redis','/data')]:
        path=runtime/'data'/role;path.mkdir(parents=True)
        rows[role]=configuration(dict(Id='id-'+role, Mounts=[dict(Type='bind',Source=str(path),
            Destination=destination,RW=True)], State=dict(Running=True)))
    tools=runtime/'tools';tools.mkdir();(tools/'tool').write_bytes(b'original tool')
    shared=tmp_path/'nas';shared.mkdir();(shared/'archive').write_bytes(b'protected archive')
    sock=socket.socket(socket.AF_UNIX);sock.bind(str(runtime/'docker.sock'))
    alias=tmp_path/'alias';alias.symlink_to(runtime, target_is_directory=True)
    mounts=[dict(Type='bind',Source=str(path),Destination=dest,RW=rw) for path,dest,rw in
        [(runtime,'/runtime',True),(shared,'/mnt/nas/Backup',True),
         (alias/'docker.sock','/var/run/docker.sock',True),(tools,'/tools',False)]]
    rows['backend']=configuration(dict(Id='id-backend',Mounts=mounts,State=dict(Running=True)))
    stopped=configuration(dict(Id='old-backend',Mounts=[copy.deepcopy(mounts[0])],
        State=dict(Running=False,Paused=False,Restarting=False,Pid=0,Status='exited'),ExecIDs=None))
    protected=['/mnt/nas',str(shared),*[str(tmp_path/p) for p in ('archives','operations','states','target')]]
    storage=snapshot_retained_storage(rows,protected,[stopped])
    n=native(rows,others={stopped['Id']:stopped});n.source['archiveRoots']=[str(tmp_path/'archives')]
    n.root=tmp_path/'operations'/'op1';n.config.update(dataRoot=str(tmp_path/'target'),
        replacement=dict(stateRoot=str(tmp_path/'states')))
    value=dict(schemaVersion='RegisteredApplicationReplacement/v2',storage=storage)
    yield rows,stopped,storage,n,value,runtime,shared
    sock.close()


def test_explicit_retained_binds_allow_only_the_three_data_directories(observed):
    rows,stopped,storage,n,value,runtime,shared=observed
    assert storage['schemaVersion']=='RegisteredReplacementStorage/v3'
    writable=verify_storage(n,value,rows)
    assert writable=={str(runtime/'data'/r):'id-'+r for r in ('mysql','minio','redis')}
    assert len(storage['preservedApplicationMounts'])==4
    assert (shared/'archive').read_bytes()==b'protected archive'
    assert (runtime/'tools'/'tool').read_bytes()==b'original tool'


@pytest.mark.parametrize('change',['running','pid','paused','restarting','exec','config','mounts','missing','unregistered'])
def test_historical_owner_requires_exact_configuration_and_actual_inactivity(observed,change):
    rows,stopped,storage,n,value,runtime,shared=observed
    if change=='running':stopped['State']['Running']=True
    elif change=='pid':stopped['State']['Pid']=42
    elif change=='paused':stopped['State']['Paused']=True
    elif change=='restarting':stopped['State']['Restarting']=True
    elif change=='exec':stopped['ExecIDs']=['active-exec']
    elif change=='config':stopped['Config']['Env']=['CHANGED=1']
    elif change=='mounts':stopped['Mounts'][0]['Destination']='/other'
    elif change=='missing':storage['inactiveConsumers'][0]['id']='absent-id'
    elif change=='unregistered':storage['inactiveConsumers']=[]
    with pytest.raises(Exception):verify_storage(n,value,rows)


@pytest.mark.parametrize('change',['readonly-bytes','type','inode','symlink-parent','extra','rw','role','source'])
def test_application_mount_bytes_identity_and_complete_bindings_are_enforced(observed,change):
    rows,stopped,storage,n,value,runtime,shared=observed
    if change=='readonly-bytes':(runtime/'tools'/'tool').write_bytes(b'changed tool')
    elif change=='type':
        (runtime/'tools'/'tool').unlink();(runtime/'tools'/'tool').mkdir()
    elif change=='inode':
        (runtime/'tools').rename(runtime/'old-tools');(runtime/'tools').mkdir()
        (runtime/'tools'/'tool').write_bytes(b'original tool')
    elif change=='symlink-parent':
        alias=runtime.parent/'alias';alias.unlink();alias.symlink_to(shared,target_is_directory=True)
    elif change=='extra':rows['backend']['Mounts'].append(dict(Type='bind',Source=str(shared),Destination='/new',RW=True))
    elif change=='rw':rows['backend']['Mounts'][-1]['RW']=True
    elif change=='role':storage['preservedApplicationMounts'][0]['role']='mysql'
    elif change=='source':storage['preservedApplicationMounts'][0]['mount']['Source']=str(shared)
    with pytest.raises(Exception):verify_storage(n,value,rows)


def test_v2_does_not_silently_accept_preserved_application_binds(observed):
    rows,stopped,storage,n,value,runtime,shared=observed
    legacy={k:v for k,v in storage.items() if k not in ('preservedApplicationMounts','inactiveConsumers')}
    legacy['schemaVersion']='RegisteredReplacementStorage/v2';value['storage']=legacy
    with pytest.raises(Exception,match='REPLACEMENT_STORAGE_INVALID'):verify_storage(n,value,rows)


@pytest.mark.parametrize('field',['preservedApplicationMounts','inactiveConsumers'])
def test_v3_contract_rejects_duplicate_ownership_entries(observed,field):
    rows,stopped,storage,n,value,runtime,shared=observed
    storage[field].append(copy.deepcopy(storage[field][0]))
    with pytest.raises(Exception):validate_storage(storage)


def test_readonly_tree_rejects_unbounded_symlink_traversal(observed):
    from recovery_replacement_storage import snapshot_retained_storage
    rows,stopped,storage,n,value,runtime,shared=observed
    (runtime/'tools'/'secret-link').symlink_to(shared,target_is_directory=True)
    with pytest.raises(Exception):snapshot_retained_storage(rows,storage['protectedRoots'],[stopped])


def test_a_new_live_parent_consumer_is_never_admitted(observed):
    rows,stopped,storage,n,value,runtime,shared=observed
    other=configuration(dict(Id='live-other',Mounts=[copy.deepcopy(rows['backend']['Mounts'][0])],
        State=dict(Running=True,Paused=False,Restarting=False,Pid=123,Status='running'),ExecIDs=None))
    n2=native(rows,others={stopped['Id']:stopped,other['Id']:other})
    n2.source=n.source;n2.root=n.root;n2.config=n.config
    with pytest.raises(Exception,match='REPLACEMENT_VOLUME_SHARED'):verify_storage(n2,value,rows)
