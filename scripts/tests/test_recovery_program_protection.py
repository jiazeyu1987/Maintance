"""Real Linux context/flock/files; only host and SQL transports are unit seams.

The actual three protection implementations and their journals run here. A
local in-memory mount/table/SQL protocol supplies transport replies; these are
not real kernel protections, database execution or server recovery evidence.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import importlib
import os
import shlex
import sys

import pytest

from test_recovery_program_generation import case, write
from test_recovery_program_execution import execution as make_execution, resolve
from test_recovery_program_activation import locked
from test_recovery_program_native import context, started, publish
from recovery_engine import RecoveryError, digest, pin, pinned_json, require

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='actual Linux context/flock required')


def module():
    return importlib.import_module('recovery_program_protection')


class TransportModel:
    """Explicit protocol unit seam, never a real mount/firewall/SQL result."""
    def __init__(self, original_mount, uuid):
        self.mount = deepcopy(original_mount)
        self.uuid, self.scheduler = uuid, 'ON'
        self.calls, self.releases = [], []
        self.fail = None
        self.tables = {family:{'PREROUTING':[], 'OUTPUT':[]} for family in ('iptables','ip6tables')}

    def command(self, native, argv, *, mutation=False, **kwargs):
        native.guard()
        self.calls.append(('command',native.native_context.phase,deepcopy(argv),mutation))
        if Path(argv[0]).name == 'mount':
            mode = argv[4].split(',')[-1]
            if mode == 'rw':
                if self.fail == 'archive':raise RecoveryError('EXPECTED_ARCHIVE_RELEASE_FAILURE')
                self.releases.append('archive')
            self.mount['options'] = [mode if option in ('ro','rw') else option for option in self.mount['options']]
            native.guard()
            return b''
        table = self.tables[argv[1]]
        arguments = argv[6:]; action = arguments[0]
        if action == '-S':
            names = [arguments[1]] if len(arguments)>1 else list(table)
            lines = []
            for name in names:
                if len(arguments) == 1:
                    lines.append(('-P '+name+' ACCEPT') if name in ('PREROUTING','OUTPUT') else '-N '+name)
                lines.extend(shlex.join(['-A',name,*rule]) for rule in table[name])
            result = ('\n'.join(lines)+'\n').encode('utf-8')
        elif action == '-N': table[arguments[1]]=[]; result=b''
        elif action == '-A': table[arguments[1]].append(arguments[2:]); result=b''
        elif action == '-I': table[arguments[1]].insert(0,arguments[3:]); result=b''
        elif action == '-C': assert arguments[2:] in table[arguments[1]]; result=b''
        elif action in ('-D','-X'):
            if self.fail == 'fence':raise RecoveryError('EXPECTED_FENCE_RELEASE_FAILURE')
            if action == '-D':table[arguments[1]].remove(arguments[2:])
            else:
                assert table[arguments[1]] == [];del table[arguments[1]]
                if all(set(row)=={'PREROUTING','OUTPUT'} for row in self.tables.values()):self.releases.append('fence')
            result=b''
        else:raise AssertionError(arguments)
        native.guard()
        return result

    def query(self, native, statement, *, mutation=False):
        native.guard()
        self.calls.append(('sql',native.native_context.phase,statement,mutation))
        if statement.startswith('SET GLOBAL event_scheduler='):
            state=statement.split('=')[1].rstrip(';')
            if state == 'ON':
                if self.fail == 'scheduler':raise RecoveryError('EXPECTED_SCHEDULER_RELEASE_FAILURE')
                self.releases.append('scheduler')
            self.scheduler=state;result=b''
        elif statement == 'SHOW DATABASES;':
            result=b'app\ninformation_schema\nmysql\nperformance_schema\nsys\n'
        elif '@@server_uuid' in statement:result=(self.uuid+'\t0\t0\t'+self.scheduler+'\n').encode('ascii')
        elif 'PROCESSLIST' in statement or 'innodb_trx' in statement:result=b'0\n'
        else:raise AssertionError(statement)
        native.guard()
        return result


def native_for(view, request, source, transport):
    value=SimpleNamespace(native_context=view, config=view.configuration['targets'][request['targetConfigRef']],
        original=deepcopy(request), source=deepcopy(source), budget=view.budget,
        policy={'environmentMysqlClientPath':'/usr/bin/mysql'}, original_pins=[])
    value.config_services={row['role']:row for row in value.config['services']}
    value.db_container=value.config_services['mysql']['id']
    value.guard=view.guard
    value.command=lambda argv,**kwargs:transport.command(value,argv,**kwargs)
    return value


@pytest.fixture
def protection_execution(case,monkeypatch):
    root=case['root'];target=case['target']
    archive=root/'archive-view';archive.mkdir(mode=0o700)
    (archive/'backups').mkdir(mode=0o700)
    programs=root/'programs';programs.mkdir(mode=0o700)
    for name in ('mount','xtables-multi'):
        path=programs/name;path.write_bytes(b'private protocol fixture\n');path.chmod(0o700)
    secret=root/'mysql.private';secret.write_bytes(b'private-fixture-password');secret.chmod(0o600)
    target['secrets']={'mysql':{'MYSQL_ROOT_PASSWORD':pin(secret)}}
    mount=dict(mountId=2,parentId=1,device='0:1',root='/',mountPoint=str(archive),
        filesystem='cifs',source='//fixture/share',options=['rw','relatime'],superOptions=['rw'])
    target['mainApplication'].update(schemaVersion='RegisteredMainApplication/v2',
        archiveMountProtection=dict(schemaVersion='RegisteredArchiveViewProtection/v1',
            mountIdentity=mount,mountProgramPin=pin(programs/'mount')),
        publishedDataEndpoints=[dict(role='minio',ip='127.0.0.1',port=9000,containerPort='9000/tcp',
            writeFence=dict(schemaVersion='PublishedHostWriteFence/v1',ports=[9000,9001],allowedWriterIPv4=[],
                programs={family:dict(pin=pin(programs/'xtables-multi'),applet=applet)
                    for family,applet in [('ipv4','iptables'),('ipv6','ip6tables')]}))])
    target['redisRebuild']={'database':0};target['buckets']=['private']
    e=make_execution.__wrapped__(case,monkeypatch)
    transport=TransportModel(mount,case['epoch']['databaseUuid'])
    import recovery_archive_view as archive_module
    import recovery_main_target as main
    monkeypatch.setattr(archive_module.ArchiveViewProtection,'_observed',lambda _:deepcopy(transport.mount))
    monkeypatch.setattr(main,'mysql_query',transport.query)
    source=dict(archiveRoots=[str(archive/'backups')])
    with locked(e.case) as fd:
        saved,binding,_=started(e,fd)
        with context(e,binding,fd) as ctx:
            preparation=native_for(ctx.preparation(e.owner),e.request,source,transport)
            custody=module().ProtectionCustody.from_preparation(preparation)
            yield SimpleNamespace(e=e,ctx=ctx,fd=fd,saved=saved,preparation=preparation,
                custody=custody,transport=transport,source=source)


def install(h):
    view=h.custody.view_for(h.preparation)
    for protection in (view.archive,view.fence,view.scheduler):protection.preflight()
    for protection in (view.archive,view.fence,view.scheduler):protection.install()
    return view


def staged(h):
    generation=publish(h.e,h.saved,h.fd)
    h.ctx.stage(generation)
    (h.e.claim/'runtime').mkdir(mode=0o700)
    effective,_=resolve(h.e,h.ctx._binding,h.fd,generation_pin=generation,runtime=True)
    return native_for(h.ctx.restore(effective),h.e.request,h.source,h.transport)


def frozen_journals(h):
    return {p:p.read_bytes() for name in ('archive-view','published-fence','mysql-scheduler')
            for p in (h.e.claim/name).glob('*.json')}


def test_real_context_original_protections_survive_stage_and_release_in_original_order(protection_execution):
    h=protection_execution;view=install(h);before=frozen_journals(h)
    original_binding=view.scheduler.binding
    restored=staged(h)
    assert restored.config['services'][3]['id'] != h.preparation.config['services'][3]['id']
    changed_binding=digest(dict(database=restored.config['database'],
        databaseUuid=restored.config['replacement']['databaseUuid'],
        mysql=[s for s in restored.config['services'] if s['role']=='mysql'],mainApplication=restored.config['mainApplication']))
    assert changed_binding != original_binding
    moved=h.custody.view_for(restored)
    assert moved.scheduler.binding == original_binding
    for protection in (moved.archive,moved.fence,moved.scheduler):protection.verify()
    result=h.custody.release(restored)
    assert set(result)=={'archiveViewReleasePin','publishedWriteFenceReleasePin','mysqlSchedulerReleasePin'}
    assert h.transport.releases==['archive','fence','scheduler'] and h.transport.scheduler=='ON'
    assert all(path.read_bytes()==raw for path,raw in before.items())
    assert all(reference in restored.original_pins for reference in result.values())
    assert h.custody.snapshot()['state']=='RELEASED'


def test_old_preparation_retains_no_command_or_protection_exception_after_stage(protection_execution):
    h=protection_execution;old=install(h);staged(h);count=len(h.transport.calls)
    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_PHASE_CHANGED'):
        h.preparation.command(['docker','start','old-program'],mutation=True)
    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_PHASE_CHANGED'):
        h.custody.view_for(h.preparation)
    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_PHASE_CHANGED'):
        old.scheduler.verify()
    assert len(h.transport.calls)==count


def test_protection_views_expose_no_general_command_query_or_mutable_scope(protection_execution):
    h=protection_execution;view=h.custody.view_for(h.preparation)
    for protection in (view.archive,view.fence,view.scheduler):
        assert not hasattr(protection,'execute') and not hasattr(protection,'query') and not hasattr(protection,'command')
    changed=view.archive.configuration;changed['mountIdentity']['mountPoint']='/other'
    assert view.archive.configuration==h.preparation.config['mainApplication']['archiveMountProtection']


@pytest.mark.parametrize('field',['native-config','request','source','policy','budget','mysql-id','service-cache'])
def test_changed_native_cannot_borrow_protection_transport(protection_execution,field):
    h=protection_execution;install(h);restored=staged(h);count=len(h.transport.calls)
    if field=='native-config':restored.config['secrets']={}
    elif field=='request':restored.original['operationId']='other'
    elif field=='source':restored.source['archiveRoots']=['/other']
    elif field=='policy':restored.policy['environmentMysqlClientPath']='/other'
    elif field=='budget':restored.budget=deepcopy(restored.budget)
    elif field=='mysql-id':restored.db_container='8'*64
    else:restored.config_services['mysql']=dict(restored.config_services['mysql'],id='8'*64)
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_'):
        h.custody.view_for(restored)
    assert len(h.transport.calls)==count


def test_another_real_context_cannot_borrow_the_original_custody(protection_execution):
    h=protection_execution
    with context(h.e,h.ctx._binding,h.fd) as other:
        native=native_for(other.preparation(h.e.owner),h.e.request,h.source,h.transport)
        with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_CONTEXT_CHANGED'):
            h.custody.view_for(native)
    assert not h.transport.calls


def test_duck_typed_native_view_has_no_protection_authority(protection_execution):
    h=protection_execution
    h.preparation.native_context=SimpleNamespace(_context=h.ctx,phase='PREPARATION',guard=lambda:None)
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_VIEW_INVALID'):
        h.custody.view_for(h.preparation)
    assert not h.transport.calls


@pytest.mark.parametrize('field',['intent','active','journal'])
def test_original_journal_drift_is_rejected_before_transport(protection_execution,field):
    h=protection_execution;install(h);restored=staged(h);count=len(h.transport.calls)
    journal=h.e.claim/'mysql-scheduler'
    if field=='journal':
        moved=journal.with_name('moved-scheduler');journal.rename(moved);journal.mkdir(mode=0o700)
        for path in moved.iterdir():(journal/path.name).write_bytes(path.read_bytes())
    else:
        path=journal/(field+'.json');value=pinned_json(pin(path));value['extra']='changed';write(path,value)
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_JOURNAL_CHANGED'):
        h.custody.view_for(restored)
    assert len(h.transport.calls)==count


def test_captured_protection_object_is_bound_to_same_native_and_phase_on_every_call(protection_execution):
    h=protection_execution;install(h);restored=staged(h);view=h.custody.view_for(restored)
    restored.config['mainApplication']['publishedDataEndpoints'][0]['writeFence']['ports']=[9000]
    count=len(h.transport.calls)
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_'):view.fence.verify()
    assert len(h.transport.calls)==count


@pytest.mark.parametrize('kind',['archive','fence','scheduler'])
def test_release_failure_preserves_prior_steps_and_does_not_release_later_protections(protection_execution,kind):
    h=protection_execution;install(h);restored=staged(h);before=frozen_journals(h)
    h.transport.fail=kind
    with pytest.raises(RecoveryError,match='EXPECTED_.*_RELEASE_FAILURE'):
        h.custody.release(restored)
    expected={'archive':[],'fence':['archive'],'scheduler':['archive','fence']}[kind]
    assert h.transport.releases==expected and h.transport.scheduler=='OFF'
    snapshot=h.custody.snapshot()
    assert snapshot['state']=='FAILED_RETAINED'
    for name in expected:assert snapshot['protections'][name]['state']=='RELEASED'
    assert snapshot['protections'][kind]['state']=='FAILED_RETAINED'
    for path,raw in before.items():assert path.read_bytes()==raw
    assert not (h.e.claim/'mysql-scheduler/released.json').exists()
    for name in expected:
        journal={'archive':'archive-view','fence':'published-fence'}[name]
        assert pin(h.e.claim/journal/'released.json') in restored.original_pins


def test_release_never_installs_again_or_runs_out_of_order(protection_execution):
    h=protection_execution;install(h);restored=staged(h);view=h.custody.view_for(restored)
    count=len(h.transport.calls)
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_INSTALL_PHASE'):view.archive.install()
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_RELEASE_ORDER'):view.scheduler.release()
    assert len(h.transport.calls)==count
    h.custody.release(restored);count=len(h.transport.calls)
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_ALREADY_RELEASED'):h.custody.release(restored)
    assert len(h.transport.calls)==count


def test_lock_loss_and_closed_context_cannot_release_protection(protection_execution):
    import fcntl
    h=protection_execution;install(h);restored=staged(h);count=len(h.transport.calls)
    fcntl.flock(h.fd,fcntl.LOCK_UN)
    with pytest.raises(ValueError,match='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
        h.custody.release(restored)
    h.ctx.close()
    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_CLOSED'):
        h.custody.view_for(restored)
    assert len(h.transport.calls)==count


def test_custody_cannot_be_created_from_restore_view(protection_execution):
    h=protection_execution;install(h);restored=staged(h)
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_PREPARATION_REQUIRED'):
        module().ProtectionCustody.from_preparation(restored)


@pytest.mark.parametrize('field',['credential','mount-program','fence-program'])
def test_actual_credential_and_protection_program_pin_drift_blocks_transport(protection_execution,field):
    h=protection_execution;install(h);restored=staged(h);count=len(h.transport.calls)
    target=h.preparation.config
    if field=='credential':reference=target['secrets']['mysql']['MYSQL_ROOT_PASSWORD']
    elif field=='mount-program':reference=target['mainApplication']['archiveMountProtection']['mountProgramPin']
    else:reference=target['mainApplication']['publishedDataEndpoints'][0]['writeFence']['programs']['ipv4']['pin']
    Path(reference['path']).write_bytes(b'changed')
    with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_INPUT_CHANGED'):
        h.custody.view_for(restored)
    assert len(h.transport.calls)==count
