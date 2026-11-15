"""Execute actual standard-package mount methods with explicit Docker protocol boundaries."""
import ast
from copy import deepcopy
import importlib.util
import ipaddress
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/backup_engine'))
import build_variants as builder


@pytest.fixture(scope='module')
def standard(tmp_path_factory):
    payload, _ = builder.standard_sources()
    payload = builder.safe_fixes(payload)
    root = tmp_path_factory.mktemp('prepared-standard')
    for name, raw in payload.items():
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    sys.path[:0] = [str(root/name) for name in ('common', 'formal', 'control')]
    import recovery_engine
    from recovery_minimal_plan import disjoint
    tree = ast.parse(payload['common/recovery_minimal_runtime.py'].decode())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'MinimalData')
    namespace = dict(absolute=recovery_engine.absolute, require=recovery_engine.require,
        disjoint=disjoint, json=json, ipaddress=ipaddress)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'prepared_data_bind']
    nodes += [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in
              ('bound', 'fresh_target', 'physical_object_chain', 'application_inputs')]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'actual-standard-runtime', 'exec'), namespace)
    initialize = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_initialize')
    index = next(i for i,n in enumerate(initialize.body) if isinstance(n,ast.Assign)
                 and any(isinstance(t,ast.Name) and t.id == 'executables' for t in n.targets))
    namespace['executor_nodes'] = initialize.body[index:index+2]
    return namespace


def target(tmp_path):
    root=tmp_path/'target'; root.mkdir()
    mounts={}
    for role,destination in [('mysql','/var/lib/mysql'),('minio','/data'),('redis','/data')]:
        path=root/role;path.mkdir()
        mounts[role]=dict(Type='bind',Source=str(path),Destination=destination,RW=True)
    config=dict(preparedEmptyTarget=True,dataRoot=str(root),dataPaths=[m['Source'] for m in mounts.values()],
                dataPolicy={'minioDataMount':'/data'},redisClientPath='/usr/bin/redis-cli',targetId='prepared')
    source=dict(sourcePaths=[str(tmp_path/'source')],archiveRoots=[str(tmp_path/'nas')],sourceVolumeNames=[])
    return config,source,mounts


def test_prepared_bind_allowlist_and_source_nas_boundaries(standard,tmp_path):
    config,source,mounts=target(tmp_path)
    allow=standard['prepared_data_bind']
    for role,mount in mounts.items(): assert allow(config,source,role,mount)
    for problem in ('unmarked','outside','not-listed','broad-parent','private','destination','wrong-role','source','nas'):
        c,s,m=deepcopy(config),deepcopy(source),deepcopy(mounts['mysql'])
        if problem=='unmarked':c.pop('preparedEmptyTarget')
        elif problem=='outside':m['Source']=str(tmp_path/'outside')
        elif problem=='not-listed':c['dataPaths'].remove(m['Source'])
        elif problem=='broad-parent':c['dataPaths']=[c['dataRoot']]
        elif problem=='private':m['Source']=str(Path(c['dataRoot'])/'private');c['dataPaths'].append(m['Source'])
        elif problem=='destination':m['Destination']='/etc'
        elif problem=='source':s['sourcePaths']=[c['dataRoot']]
        elif problem=='nas':s['archiveRoots']=[m['Source']]
        assert not allow(c,s,'backend' if problem=='wrong-role' else 'mysql',m),problem
    assert not allow(config,source,'mysql',dict(mounts['mysql'],RW=False))


def test_bound_admits_only_prepared_data_bind_and_keeps_identity(standard,tmp_path,monkeypatch):
    config,source,mounts=target(tmp_path)
    machine=tmp_path/'machine-id';machine.write_text('measured-machine')
    original_absolute=standard['absolute']
    monkeypatch.setitem(standard,'absolute',lambda path:machine if path=='/etc/machine-id' else original_absolute(path))
    config.update(machineId='measured-machine',dockerEngineId='engine',networkId='network')
    row=dict(Id='mysql-id',Image='image',Config={'Labels':{'intruoyi.recovery.target':'prepared'}},
        State=dict(Running=True,Paused=False,Restarting=False),RestartCount=0,
        HostConfig=dict(Privileged=False,Devices=[],CapAdd=[],PidMode='',IpcMode='',NetworkMode='network',
                        RestartPolicy={'Name':'no'},PortBindings={}),NetworkSettings={'Networks':{'prepared':{}}},
        Mounts=[mounts['mysql']],Path='mysql',Args=[])
    network=dict(Id='network',Name='prepared',Internal=True,Driver='bridge',EnableIPv6=False,
                 IPAM={'Config':[{'Subnet':'172.29.238.0/24'}]},Containers={'mysql-id':{}})
    def docker(args):return json.dumps({'ID':'engine'} if args[0]=='info' else [network]).encode()
    def command(args):raise AssertionError('prepared target must not execute legacy iptables')
    obj=SimpleNamespace(config=config,source=source,config_services={'mysql':{'id':'mysql-id','imageId':'image'}},
        storage_running=False,running_applications=set(),snapshots={},guard=lambda:None,inspect=lambda identity:row,
        docker=docker,command=command,mysql=None,db_target=None,
        modules={'formal_sql_restore':SimpleNamespace(database_state=lambda *a:None)})
    standard['bound'](obj)
    assert 'mysql' in obj.snapshots
    row['Image']='wrong'
    with pytest.raises(Exception,match='TARGET_CHANGED_OR_EXPOSED'):standard['bound'](obj)


def fresh_object(config,source,mounts,shared=False):
    services={role:{'id':role+'-id'} for role in mounts}
    snapshots={role:{'Id':role+'-id','Mounts':[mount]} for role,mount in mounts.items()}
    def docker(args,**kwargs):
        if args[0]=='ps':return ('\n'.join(s['id'] for s in services.values())+ ('\nother' if shared else '')).encode()
        if args[0]=='exec':return b'0'
        raise AssertionError('data bind must not invoke volume inspect')
    def inspect(identity):
        if identity=='other':return {'Mounts':[mounts['minio']]}
        return snapshots[identity.removesuffix('-id')]
    return SimpleNamespace(config=config,source=source,config_services=services,snapshots=snapshots,
        storage_running=False,bound=lambda:None,application_inputs=lambda:None,
        modules={'formal_sql_restore':SimpleNamespace(empty_database=lambda *a:None)},mysql=None,db_target=None,
        policy={'minioDataMount':'/data'},guard=lambda:None,docker=docker,inspect=inspect,secret=lambda *a:'private')


def test_fresh_target_accepts_bind_but_rejects_shared_data(standard,tmp_path):
    config,source,mounts=target(tmp_path)
    standard['fresh_target'](fresh_object(config,source,mounts))
    with pytest.raises(Exception,match='TARGET_VOLUME_SHARED'):
        standard['fresh_target'](fresh_object(config,source,mounts,shared=True))


def test_physical_bind_reaches_copy_and_rejects_shared_source(standard,tmp_path,monkeypatch):
    config,source,mounts=target(tmp_path)
    import recovery_data_files
    def reached(chain, *, verify_content):
        assert verify_content is False
        raise RuntimeError('PHYSICAL_COPY_REACHED')
    monkeypatch.setattr(recovery_data_files,'physical_chain_inputs',reached)
    obj=fresh_object(config,source,mounts);obj.policy['bucketMapping']={};obj.chain=[]
    with pytest.raises(RuntimeError,match='PHYSICAL_COPY_REACHED'):standard['physical_object_chain'](obj)
    obj=fresh_object(config,source,mounts,shared=True);obj.policy['bucketMapping']={};obj.chain=[]
    with pytest.raises(Exception,match='PHYSICAL_VOLUME_SHARED'):standard['physical_object_chain'](obj)


def test_only_prepared_targets_omit_legacy_firewall_executable(standard):
    for prepared in (True,False):
        ns=dict(target={'dockerPin':'docker','iptablesPin':'iptables','preparedEmptyTarget':prepared},
                registered_main=lambda target:False)
        exec(compile(ast.Module(body=standard['executor_nodes'],type_ignores=[]),'actual-executables','exec'),ns)
        assert ns['executables']==(['docker'] if prepared else ['docker','iptables'])


def test_prepared_inputs_use_provisioned_services_and_keep_start_order(standard):
    app=dict(imageBindings=[],configurationBindings=[],artifactBindings=[],startOrder=['backend','frontend'])
    obj=SimpleNamespace(config=dict(preparedEmptyTarget=True,application=app),
        config_services={role:{'imageId':'selected-'+role} for role in ('mysql','minio','redis','backend','frontend')},
        material=dict(payloadPins=[],versionPins=[]))
    standard['application_inputs'](obj)
    app['startOrder']=['backend']
    with pytest.raises(Exception,match='APPLICATION_START_ORDER_INVALID'):
        standard['application_inputs'](obj)
    app['startOrder']=['backend','frontend']
    obj.config.pop('preparedEmptyTarget')
    with pytest.raises(Exception,match='ARCHIVED_IMAGE_VERSIONS_INCOMPLETE'):
        standard['application_inputs'](obj)
