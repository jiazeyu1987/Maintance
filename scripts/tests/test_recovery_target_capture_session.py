"""Real FULL materials, files/flock/ctx/custody; finite external protocols.

SQL/Docker/S3/Redis replies are protocol units, not real business data or a
server acceptance. Actual Popen, gzip/schema/data/physical/object/Redis capture,
source restoration and original protection implementations remain enabled.
actualBusinessRestoreFalse. SAFE complete/packaging is a separate hard hold.
"""
from copy import deepcopy
import gzip
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'ops/recovery'),str(ROOT/'ops/backup_engine/formal')]
from test_recovery_program_restore import case, restore_case, freeze_inputs
from test_recovery_program_activation import locked, claim
from test_recovery_program_native import context, started
from test_recovery_program_protection import frozen_journals
from recovery_engine import RecoveryError, canonical, pin, pinned_json, write
import recovery_resource_admission as admission
import recovery_main_target as main
from recovery_program_protection import ProtectionCustody
from minimal_capture_support import Budget, validate_job
from formal_snapshot_linux import FormalSnapshotError
import minimal_capture_worker as worker

pytestmark=pytest.mark.skipif(not sys.platform.startswith('linux'),reason='actual Linux flock/Popen required')


CLIENT=r'''#!PYTHON
import json,re,sys,time
from pathlib import Path
state_path=Path(STATE)
s=json.loads(state_path.read_text());a=sys.argv[1:];query=sys.stdin.buffer.read().decode() if a[:1]==['exec'] else ''
def out(value):sys.stdout.write(value+'\n')
def persist():state_path.write_text(json.dumps(s))
if Path(sys.argv[0]).name=='ip':out('1: lo inet 127.0.0.1/8 scope host lo')
elif a[:2]==['image','save']:sys.stdout.buffer.write(Path(s['archive']).read_bytes())
elif a[:1]==['ps']:out('\n'.join(s['containers']))
elif a[:1]==['inspect']:
    identity=a[-1];row=s['containers'][identity]
    if '--format' in a:
        if '"ports"' in a[a.index('--format')+1]:out(json.dumps(dict(id=identity,running=row['running'],ports=row['ports'],networks=row['networks'])))
        else:out(json.dumps(dict(id=identity,running=row['running'],paused=False,image=row['image'],mounts=row['mounts'])))
    else:out(json.dumps([dict(Id=identity,State=dict(Running=row['running']),NetworkSettings=dict(Networks=row['networks']))]))
elif a[:1] in (['start'],['stop']):
    identity=a[-1];s['containers'][identity]['running']=a[0]=='start';s['actions'].append([a[0],identity]);persist()
    if s.get('restoreFailure') and a[0]=='start' and identity in s['writers']:sys.exit(7)
elif a[:1]==['exec']:
    sql=query.split('\n',1)[1] if '\n' in query else query
    # The SOURCE dependency probe mentions mysqldump but never executes it.
    probe='for program in mysql sh timeout mysqldump; do command -v "$program" >/dev/null || exit 1; done'
    dump_prefix=('test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; '
        'test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; '
        'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec timeout --signal=TERM --kill-after=5 ')
    dump=(len(a)>6 and a[:2]==['exec','-i'] and a[2] in s['containers'] and a[3:5]==['sh','-ec']
        and a[6:]==['formal-mysql','--no-defaults','--protocol=SOCKET','-uroot',
            '--single-transaction','--routines','--triggers','--events','--hex-blob',
            '--set-gtid-purged=OFF','--default-character-set=utf8mb4','app']
        and re.fullmatch(re.escape(dump_prefix)+r'[1-9][0-9]*s mysqldump "\$@"',a[5]) is not None)
    if len(a)==5 and a[1] in s['containers'] and a[2:]==['sh','-ec',probe]:pass
    elif dump:
        if s.get('dumpRelease'):
            Path(s['dumpReady']).touch();end=time.monotonic()+5
            while not Path(s['dumpRelease']).exists() and time.monotonic()<end:time.sleep(.001)
            if not Path(s['dumpRelease']).exists():sys.exit(8)
        time.sleep(.08)
        if s.get('dumpFailure'):sys.exit(9)
        out('-- finite SQL protocol; no real database')
    elif sql.strip()=='SELECT @@global.gtid_mode;':out('ON')
    elif sql.strip()=='SELECT @@server_uuid;':out(s['uuid'])
    elif sql.strip()=='SELECT @@global.read_only,@@global.super_read_only;':out('\t'.join(s['flags']))
    elif sql.strip().startswith('SET GLOBAL read_only=ON;'):s['flags']=['1','1'];persist()
    elif sql.strip().startswith('SET GLOBAL super_read_only=OFF;'):s['flags']=['0','0'];persist()
    elif sql.strip()=='SELECT @@server_uuid,@@global.read_only,@@global.super_read_only;':out(s['uuid']+'\t'+'\t'.join(s['flags']))
    elif sql.strip()=='SHOW MASTER STATUS;':out('mysql-bin.000001\t120\t\t\t'+s['uuid']+':1-2')
    elif '@@version' in sql:
        out(s['uuid']+'\t8.0.39\t1\tROW\tON'+('\t'+'\t'.join(s['flags']) if '@@global.read_only' in sql else ''))
    elif sql.strip()=='SHOW TABLES FROM `app`;':out('protocol_table')
    elif sql.strip()=='DESCRIBE `app`.`protocol_table`;':out('key\tvarbinary(255)\tYES\t\tNULL\t')
    elif sql.strip()=='SELECT HEX(CAST(`key` AS BINARY)) FROM `app`.`protocol_table`;':pass
    elif 'DESCRIBE information_schema.' in sql:out(s['uuid']+'\ndummy\n0\n'+s['uuid'])
    elif 'SHOW CREATE DATABASE' in sql:out(s['uuid']+'\napp\tCREATE DATABASE `app`\n0\n'+s['uuid'])
    elif 'SHOW FULL TABLES' in sql or 'information_schema.' in sql:out(s['uuid']+'\n0\n'+s['uuid'])
    else:raise AssertionError(('unhandled SQL protocol',sql))
else:raise AssertionError(('unhandled client protocol',a))
'''


@pytest.fixture
def capture_protocol(restore_case,monkeypatch):
    h=restore_case;base=h.case['root'];target=h.case['target'];services={s['role']:s for s in target['services']}
    # Setup an independent original owner/reservation before any ctx is made.
    # Existing restore_case originals/reservation remain untouched and unused.
    operations=base/'capture-operations';operations.mkdir(mode=0o700)
    h.root=operations/'restore-1';h.root.mkdir(mode=0o700)
    host=base/'capture-host';host.mkdir(mode=0o700);monkeypatch.setattr(admission,'HOST_ROOT',host)
    h.owner['operationsRoot']=str(operations)
    target['replacement']['storage']['protectedRoots'].append(str(operations))
    for role,service in services.items():
        service['imageId']=h.images[role];row=h.engine.rows[service['id']];row['Image']=service['imageId']
        target['replacement']['services'][role]['imageId']=service['imageId']
        target['mainApplication']['serviceConfigurationDigests'][role]=main.service_configuration_digest(row)
    for binding in target['mainApplication']['archiveImageBindings']:binding['imageId']=services[binding['role']]['imageId']
    metadata=base/'capture-inputs';metadata.mkdir(mode=0o700)
    versions=write(metadata/'versions.json',dict(images={role:s['imageId'] for role,s in services.items()}))
    identity=write(metadata/'identity.json',dict(sourceFingerprint=h.case['epoch']['sourceIdentity'],databaseUuid=h.case['epoch']['databaseUuid']))
    scope=write(metadata/'scope.json',dict(sourceIdentityPin=identity,endpointHosts=['127.0.0.1']))
    credential=write(metadata/'credential.private.json',dict(schemaVersion='backup-source-s3-credential/v1',
        endpoint='http://127.0.0.1:9000',accessKey='finite-access',secretKey='finite-secret'))
    target['secrets']['minio']={}
    for name,value in (('MINIO_ROOT_USER','finite-access'),('MINIO_ROOT_PASSWORD','finite-secret')):
        path=metadata/(name+'.private');path.write_text(value,encoding='utf-8');path.chmod(0o600)
        target['secrets']['minio'][name]=pin(path)
    recipe=write(metadata/'references.json',dict(schemaVersion='backup-capture-reference-recipe/v1',
        sourceIdentity=h.case['epoch']['sourceIdentity'],referenceQueries=[dict(table='protocol_table',columns=['key'])],
        objectBindings=[dict(table='protocol_table',bucket=dict(literal='private'),keyColumn='key',versionColumn=None,
            nullable=False,keyEncoding='RAW_KEY',urlPrefix=None)],maxRows=100,complete=True,coverageScopePin=scope))
    config_pin=target['mainApplication']['configurationPins'][0]
    derived=write(metadata/'derived.json',dict(schemaVersion='backup-capture-derived-recipe/v1',
        sourceIdentity=h.case['epoch']['sourceIdentity'],classes=dict(
            redis=dict(classification='RESTORE',requiredForBusiness=True,executorKey='REDIS_DUMP_ABSOLUTE_EXPIRY',
                rebuildFrom=None,configurationReferences=[config_pin]),
            queue=dict(classification='NOT_PRESENT',requiredForBusiness=False,executorKey=None,
                rebuildFrom=None,configurationReferences=[config_pin]))))
    descriptor=write(metadata/'objects.json',dict(schemaVersion='backup-capture-object-source/v1',
        sourceIdentity=h.case['epoch']['sourceIdentity'],endpoint='http://127.0.0.1:9000',minioContainerId=services['minio']['id'],
        containerPort=9000,credentialReference=credential,buckets=['private'],sourceScopePin=scope,
        versionPins=[versions],referenceRecipePin=recipe,derivedRecipePin=derived,parentExportIndexPin=None))
    minio=Path(target['replacement']['services']['minio']['mounts'][0]['Source'])
    (minio/'finite-object').write_bytes(b'physical bytes captured by the real tree algorithm\n')
    programs=base/'capture-programs';programs.mkdir(mode=0o700)
    h.state_path=base/'capture-protocol-state.json'
    h.protocol=dict(uuid=h.case['epoch']['databaseUuid'],flags=['0','0'],archive=h.selected.archive['path'],actions=[],
        writers=[services[r]['id'] for r in ('backend','frontend')],containers={s['id']:dict(running=True,image=s['imageId'],
            mounts=h.engine.rows[s['id']]['Mounts'],ports=h.engine.rows[s['id']]['HostConfig']['PortBindings'],
            networks=h.engine.rows[s['id']]['NetworkSettings']['Networks']) for s in services.values()})
    h.state_path.write_bytes(canonical(h.protocol));h.state_path.chmod(0o600)
    script=CLIENT.replace('#!PYTHON','#!'+sys.executable).replace('STATE',repr(str(h.state_path)))
    for name in ('docker','ip'):
        program=programs/name;program.write_text(script,encoding='utf-8');program.chmod(0o700)
    monkeypatch.setenv('PATH',str(programs)+os.pathsep+os.environ.get('PATH',''))
    monkeypatch.setenv('DOCKER_HOST','unix:///var/run/docker.sock');monkeypatch.delenv('DOCKER_CONTEXT',raising=False)
    monkeypatch.delenv('DOCKER_TLS_VERIFY',raising=False)
    target['dockerPin']=pin(programs/'docker')
    h.capture_config=dict(schemaVersion='minimal-source-capture-config/v1',sourceConfigRef='source57',
        archiveRoot=str(h.archive_root),sourceLockPath=h.case['epoch']['sourceLockPath'],parent=None,
        tools={name:str(programs/name) for name in ('docker','ip')},
        limits=dict(workSeconds=60,cleanupSeconds=10,clientWaitSeconds=0,maxWrittenBytes=8*1024*1024,
            minimumFreeBytes=1,stopSeconds=10,querySeconds=10,readySeconds=10,dataMaxRows=100,dataMaxNodes=1000,
            dataMaxBytes=1000000,dataSeconds=30),source=dict(sourceIdentity=h.case['epoch']['sourceIdentity'],
            sourceFingerprint=h.case['epoch']['sourceIdentity'],databaseUuid=h.case['epoch']['databaseUuid'],database='app',
            mysqlContainerId=services['mysql']['id'],minioContainerId=services['minio']['id'],minioDataPath=str(minio),
            minioMountDestination='/data',writerContainerIds=h.protocol['writers'],
            applicationImageIds=[s['imageId'] for s in services.values()],passwordPin=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD'],
            objectSourcePin=descriptor,configurationPins=[dict(role='application',reference=config_pin)],
            materialPins=[dict(purpose='versions',reference=versions)],redisSnapshot=dict(containerId=services['redis']['id'],
                host=services['redis']['ip'],database=0,passwordPin=target['secrets']['redis']['REDIS_PASSWORD'])))
    h.case['capture']=h.capture_config
    h.case['base_pin']=write(metadata/'capture.json',h.capture_config)
    h.case['policy']['captureConfigurationPins']=dict(source57=h.case['base_pin'])
    h.case['policy']['baselineTargetPin']=write(metadata/'target.json',target)
    h.owner['targets']['target57']=deepcopy(target);h.owner['targetProgramPolicies']['target57']=deepcopy(h.case['policy'])
    freeze_inputs(h)
    original_query=h.transport.query
    def query(native,sql,*,mutation=False):
        state=json.loads(h.state_path.read_bytes())
        from recovery_mysql_scheduler import STATE_SQL
        if sql==STATE_SQL:return ('\t'.join([state['uuid'],*state['flags'],h.transport.scheduler])+'\n').encode()
        if sql=='SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;':
            assert mutation;state['flags']=['1','1'];h.state_path.write_bytes(canonical(state));return b''
        if sql.startswith('SELECT @@GLOBAL.read_only, @@GLOBAL.super_read_only, '):return ('\t'.join([*state['flags'],'0'])+'\n').encode()
        if 'information_schema.EVENTS' in sql:return b'0\n'
        return original_query(native,sql,mutation=mutation)
    h.transport.query=query
    original_redis=main.redis_command
    def redis_command(native,arguments,*,mutation=False):
        if arguments==['--raw','CLIENT','LIST']:
            assert not mutation
            return native._invoke('redis',arguments,lambda:b'id=1 addr=127.0.0.1:50000\n',False)
        return original_redis(native,arguments,mutation=mutation)
    monkeypatch.setattr(main,'redis_command',redis_command)
    original_native=h.native_type
    class CaptureNative(original_native):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.storage_running=True;self.running_applications={'backend','frontend'};self.snapshots={}
        def docker(self,args,**kwargs):
            if args[:2]==['network','inspect']:
                rows=[r for r in h.engine.rows.values() if r['State']['Running']]
                return self._invoke('docker',args,lambda:canonical([dict(Id='f'*64,Name='task-network',Driver='bridge',
                    Internal=False,EnableIPv6=False,IPAM=dict(Driver='default',Config=[]),Options={},Labels={},
                    Containers={r['Id']:{} for r in rows})]),False)
            cleaned=[a for a in args if a!='--']
            result=super().docker(cleaned,**kwargs)
            if args[:1] in (['start'],['stop']):
                state=json.loads(h.state_path.read_bytes());identity=args[-1]
                state['containers'][identity]['running']=args[0]=='start';state['actions'].append([args[0],identity])
                h.state_path.write_bytes(canonical(state))
                role=next(s['role'] for s in self.config['services'] if s['id']==identity)
                if role=='minio':self.storage_running=args[0]=='start'
                elif role in ('backend','frontend'):
                    if args[0]=='start':self.running_applications.add(role)
                    else:self.running_applications.discard(role)
            return result
    h.native_type=CaptureNative
    class S3Protocol:
        timeout=30
        def __init__(self,*args):pass
        def versions(self,*args):return [],None
        def multipart_empty(self,bucket):return dict(bucket=bucket,state='NO_MULTIPART_UPLOAD_OBSERVED',httpStatus=200,
            rawSha256='a'*64,rawBytes=1,maxUploads=1,uploadCount=0,isTruncated=False,scope='WHOLE_BUCKET_FROM_START')
    import minimal_capture_support as support
    monkeypatch.setattr(support,'ReadOnlyS3',S3Protocol)
    class RedisProtocol:
        def __init__(self,**kwargs):assert kwargs['password']=='private-protocol-redis'
        def info(self,*args):return {'redis_version':'7.0.1'}
        def eval(self,*args):return [b'1700000000',b'0']
        def close(self):pass
    import redis
    monkeypatch.setattr(redis,'Redis',RedisProtocol)
    class HealthProtocol:
        def __init__(self,*args,**kwargs):pass
        def request(self,*args):assert args==('GET','/minio/health/ready')
        def getresponse(self):return SimpleNamespace(status=200,read=lambda maximum:b'')
        def close(self):pass
    import http.client
    monkeypatch.setattr(http.client,'HTTPConnection',HealthProtocol)
    h.preparation=None
    return h


def construct(h,ctx):
    source,policy,chain=__import__('recovery_minimal_runtime').selected_chain(h.owner,h.request)
    native=h.native_type(h.owner,h.request,source,policy,chain,h.owner['targets']['target57'],h.root,
        [h.owner_pin,h.request_pin],native_context=ctx.preparation(h.owner))
    native.protection_custody=ProtectionCustody.from_preparation(native)
    h.preparation,h.custody=native,native.protection_custody;h.e=h
    return native


def quiesce(h,native):
    from recovery_replace import quiesce as actual_quiesce
    actual_quiesce(native,native.config['replacement'])


def session(h,native):
    from recovery_target_capture import MainTargetCapture
    return MainTargetCapture.prepare(native,capture_ref='source57',reservation_pin=h.reservation)


def test_main_actual_full_materials_hold_without_releasing_original_protections(capture_protocol):
    h=capture_protocol;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd) as ctx:
            native=construct(h,ctx);budget=native.budget;capturer=session(h,native)
            assert capturer.runtime.budget.deadline<=budget.deadline and native.budget is budget
            quiesce(h,native);before=frozen_journals(h)
            materials=capturer.capture().result;value=capturer.snapshot()
            assert value['state']=='MATERIAL_COMPLETE' and value['sourceRestored'] is False
            assert value['terminalUnknown'] is False and value['writersRemainQuiesced'] is True
            assert 'sourceRestorationPin' not in materials
            for name in ('captureInputsPin','archiveEntriesPin','capturePointPin','objectContentIndexPin'):pinned_json(materials[name])
            assert gzip.decompress((Path(materials['captureRoot'])/'payload/database.sql.gz').read_bytes()).startswith(b'-- finite SQL')
            state=json.loads(h.state_path.read_bytes())
            assert state['flags']==['1','1'] and h.transport.scheduler=='OFF' and not h.transport.releases
            minio=next(s['id'] for s in native.config['services'] if s['role']=='minio')
            assert [a for a in state['actions'] if a[1]==minio]==[['stop',minio],['start',minio],['stop',minio],['start',minio],['stop',minio]]
            assert all(not state['containers'][identity]['running'] for identity in state['writers'])
            assert all(path.read_bytes()==raw for path,raw in before.items())
            assert ctx.snapshot()['terminalUnknown'] is False
            for attempt in (lambda:ctx.stage(None),lambda:native.protection_custody.release(native),lambda:capturer.handoff(None)):
                with pytest.raises(RecoveryError,match='PROGRAM_(TARGET_)?CAPTURE_'):attempt()
            actions=deepcopy(state['actions']);capturer.close()
            assert json.loads(h.state_path.read_bytes())['actions']==actions


@pytest.mark.parametrize('problem',['dump','fence','budget'])
def test_main_failed_capture_retains_barriers_and_never_restores_or_retries(capture_protocol,problem):
    h=capture_protocol;claim(h.case)
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd) as ctx:
            native=construct(h,ctx);capturer=session(h,native);quiesce(h,native)
            if problem=='dump':
                state=json.loads(h.state_path.read_bytes());state['dumpFailure']=True;h.state_path.write_bytes(canonical(state))
            elif problem=='fence':h.transport.tables['iptables']['OUTPUT'].append(['-j','UNEXPECTED'])
            else:native.budget.deadline=0
            with pytest.raises((RecoveryError,FormalSnapshotError)):capturer.capture()
            value=capturer.snapshot();assert value['state']=='FAILED_RETAINED' and value['sourceRestored'] is False
            if problem=='dump':
                assert capturer.phase=='DATABASE_CAPTURE'
                assert any(row.get('terminalObservation',{}).get('actualExitCode')==9 and
                    row['terminalObservation']['state']=='FAILED_RETAINED' for row in ctx.snapshot()['invocations'])
            before=h.state_path.read_bytes();capturer.close();assert h.state_path.read_bytes()==before
            assert h.transport.scheduler!='ON' and not h.transport.releases
            state=json.loads(h.state_path.read_bytes())
            assert not any(a[0]=='start' and a[1] in state['writers'] for a in state['actions'])
            assert not (h.root/'target-preservation'/'capture'/'source-restoration.json').exists()


@pytest.mark.parametrize('failure',[None,'dump','restore'])
def test_original_full_real_material_path_always_restores_source(capture_protocol,failure):
    h=capture_protocol;config=h.capture_config
    root=Path(config['archiveRoot'])/('full-'+str(failure));root.mkdir(mode=0o700)
    request=dict(schemaVersion='SmallAppBackupUiRequest/v1',
        operationId=root.name,action='FULL',sourceConfigRef='source57',parentChainRef=None,recoveryPointRef=None,targetConfigRef=None)
    assert validate_job(config,request)==root
    state=json.loads(h.state_path.read_bytes());state.update(dumpFailure=failure=='dump',restoreFailure=failure=='restore')
    h.state_path.write_bytes(canonical(state))
    if failure is None:
        result=worker.capture(config,request,root)
        assert pinned_json(result['sourceRestorationPin'])['restored'] is True
        assert gzip.decompress((root/'payload/database.sql.gz').read_bytes()).startswith(b'-- finite SQL')
    else:
        with pytest.raises(FormalSnapshotError):worker.capture(config,request,root)
        assert not (root/'capture-success.json').exists()
    state=json.loads(h.state_path.read_bytes())
    assert state['flags']==['0','0']
    restore=pinned_json(pin(root/'source-restoration.json'))
    assert restore['restored'] is (failure!='restore')
    assert all(state['containers'][identity]['running'] for identity in state['writers'])


def paused_dump(h):
    state=json.loads(h.state_path.read_bytes())
    ready=h.case['root']/'dump-ready';release=h.case['root']/'dump-release'
    state.update(dumpReady=str(ready),dumpRelease=str(release));h.state_path.write_bytes(canonical(state))
    return ready,release


def wait_exited_without_reap(process,deadline):
    """Bounded kernel observation, after the original drain has sent stdin."""
    assert process.stdin.closed
    end=min(deadline,time.monotonic()+5)
    while True:
        observed=os.waitid(os.P_PID,process.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
        if observed is not None:
            assert observed.si_pid==process.pid and observed.si_status==0
            return observed
        assert time.monotonic()<end,'finite dump exit was not observed'
        time.sleep(.001)


def test_actual_dump_exit_during_finite_guard_does_not_reap_before_drain(capture_protocol,monkeypatch):
    """Only external protocol responses are finite; actual child/ctx are real."""
    h=capture_protocol;claim(h.case);ready,release=paused_dump(h);triggered=[]
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd) as ctx:
            native=construct(h,ctx);capturer=session(h,native);quiesce(h,native)
            original=native.query
            def query(statement,*,mutation=False):
                row=capturer._observer.active
                if row is not None and row['dump'] and capturer._guard_depth==1 and not triggered and row['process'].stdin.closed:
                    assert row['process'] is not None and row['process'].returncode is None
                    release.touch()
                    observed=wait_exited_without_reap(row['process'],capturer.budget.deadline)
                    assert observed.si_pid==row['process'].pid and observed.si_status==0
                    assert row['process'].returncode is None
                    triggered.append(row['process'].pid)
                return original(statement,mutation=mutation)
            monkeypatch.setattr(native,'query',query)
            materials=capturer.capture()
            assert ready.is_file() and triggered and materials.result['capturePointPin']
            assert capturer.snapshot()['state']=='MATERIAL_COMPLETE' and ctx.snapshot()['terminalUnknown'] is False


@pytest.mark.parametrize('boundary',['outside-guard','reaped-tail'])
def test_actual_dump_pending_token_has_only_owned_guard_admission(capture_protocol,monkeypatch,boundary):
    h=capture_protocol;claim(h.case);ready,release=paused_dump(h);checked=[]
    with locked(h.case) as fd:
        _,binding,_=started(h,fd)
        with context(h,binding,fd) as ctx:
            native=construct(h,ctx);capturer=session(h,native);quiesce(h,native)
            original=capturer._observer.started
            def on_started(process,argv):
                original(process,argv)
                row=capturer._observer.active
                if not row['dump']:return
                assert process.returncode is None
                if boundary=='outside-guard':
                    before=len(h.transport.calls)
                    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_INVOCATION_UNSETTLED'):
                        native.query('SELECT arbitrary_external_query;')
                    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_INVOCATION_UNSETTLED'):
                        native.command(['arbitrary-write'],mutation=True)
                    with pytest.raises(RecoveryError,match='PROGRAM_CAPTURE_STREAM_ALREADY_ACTIVE'):
                        capturer._observer.before(['docker','image','save','arbitrary'])
                    assert len(h.transport.calls)==before
                    release.touch()
                    checked.append(process.pid)
            monkeypatch.setattr(capturer._observer,'started',on_started)
            if boundary=='reaped-tail':
                original_guard=capturer.guard
                def guard(*,force=False):
                    row=capturer._observer.active
                    if row is not None and row['dump'] and row['process'] is not None and row['process'].stdin.closed and not checked:
                        process=row['process'];release.touch()
                        wait_exited_without_reap(process,capturer.budget.deadline)
                        assert process.poll()==0
                        before=len(h.events);token=row['token']
                        original_guard(force=True)
                        assert len(h.events)==before and ctx._invocations[token]['terminalPin'] is None
                        checked.append(process.pid)
                        return
                    return original_guard(force=force)
                monkeypatch.setattr(capturer,'guard',guard)
                monkeypatch.setattr(capturer,'protected',guard)
            capturer.capture()
            assert ready.is_file() and checked and capturer.snapshot()['terminalUnknown'] is False
            assert all(r['terminalPin'] is not None for r in ctx.snapshot()['invocations'])
