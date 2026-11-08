"""Real MainData methods/custody/private files/context/flock, protocol unit seams.

The native carrier is normally constructed from an actual _NativeView. External
SQL/container/readiness replies are explicit unit seams, not MinimalData/package
constructor or server recovery evidence. Runtime-input tests use real MAIN
validation, writer/config pins and archive image documents separately.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from test_recovery_program_generation import case
from test_recovery_program_protection import (protection_execution, install,
    staged, frozen_journals)
from test_recovery_program_native import context
import test_main_restore_target as main_fixtures
from recovery_engine import RecoveryError, digest, pin
import recovery_main_target as main

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='actual Linux context/flock required')

METHODS = ('replacement_preflight', 'replacement_write_fence',
    'replacement_quiescence', 'replacement_finish', 'bound')


class ProtocolNative:
    """Only the external protocol carrier; all MainData methods remain real."""
    def __init__(self, original, h, label):
        self.native_context = original.native_context
        self.config = self.native_context.configuration['targets'][h.e.request['targetConfigRef']]
        self.original, self.source = deepcopy(h.e.request), deepcopy(h.source)
        self.policy, self.budget = deepcopy(original.policy), self.native_context.budget
        self.config_services = {row['role']:row for row in self.config['services']}
        self.db_container = self.config_services['mysql']['id']
        self.db_uuid = self.config['replacement']['databaseUuid']
        self.original_pins, self.protection_custody = [], h.custody
        self.label, self.transport, self.probes = label, h.transport, h.probes
        self.material = {'versionPins': []}
        self.mysql = SimpleNamespace(query=self.quiescence_query)
        self.db_target = {'database':'app'}
        self.modules = {'formal_sql_restore':SimpleNamespace(
            database_state=lambda *args:self.probes.append((self.label,'database-state')),
            import_database_state=lambda *args:self.probes.append((self.label,'import-state')))}

    def guard(self):
        self.native_context.guard_native(self)

    def command(self, argv, **kwargs):
        return self.transport.command(self, argv, **kwargs)

    def quiescence_query(self, statement):
        self.guard()
        assert 'COUNT(*)' in statement
        self.probes.append((self.label,'quiescence-sql'))
        return '0'


MainData = main.guarded_type(ProtocolNative)


@pytest.fixture
def integrated(protection_execution, monkeypatch):
    h = protection_execution
    h.probes = []
    h.preparation = MainData(h.preparation, h, 'preparation')
    def probe(name):
        def call(native, *args, **kwargs):
            native.guard()
            h.probes.append((native.label,name))
        return call
    # These are unrelated external admission/validation seams for wiring tests.
    # The actual runtime input validation is exercised separately below.
    monkeypatch.setattr(main, 'application_inputs', probe('archive-inputs'))
    monkeypatch.setattr(main, 'application_runtime_inputs', probe('runtime-inputs'), raising=False)
    monkeypatch.setattr(main, 'database_identity', probe('database-identity'))
    monkeypatch.setattr(main, 'verify_runtime', probe('runtime'))
    monkeypatch.setattr(main, 'verify_redis_authentication', probe('redis-auth'))
    monkeypatch.setattr('recovery_main_health.preflight', probe('readiness'))
    monkeypatch.setattr('recovery_replace.verify_services', probe('services'))
    def redis(native, args, **kwargs):
        native.guard()
        h.probes.append((native.label,'redis-clients'))
        return b'addr=127.0.0.1:1234\n'
    monkeypatch.setattr(main, 'redis_command', redis)
    return h


def restore(h):
    return MainData(staged(h), h, 'restore')


def test_main_preparation_preflight_uses_original_custody_and_runtime_only(integrated):
    h = integrated
    h.preparation.replacement_preflight()
    assert ('preparation','runtime-inputs') in h.probes
    assert ('preparation','archive-inputs') not in h.probes
    assert not frozen_journals(h)
    assert not any(row[-1] for row in h.transport.calls)
    view = main.protections(h.preparation)
    assert view.scheduler.binding == h.custody.view_for(h.preparation).scheduler.binding


def test_main_write_fence_records_both_installs_in_same_custody(integrated):
    h = integrated
    h.preparation.replacement_write_fence()
    states = h.custody.snapshot()['protections']
    assert states['archive']['state'] == states['fence']['state'] == 'INSTALLED'
    assert states['scheduler']['state'] == 'NOT_INSTALLED'
    assert h.transport.scheduler == 'ON'


def test_main_quiescence_pauses_original_scheduler_after_original_fences(integrated):
    h = integrated
    view = h.custody.view_for(h.preparation)
    view.archive.install(); view.fence.install()
    h.preparation.replacement_quiescence()
    assert h.custody.snapshot()['protections']['scheduler']['state'] == 'INSTALLED'
    assert h.transport.scheduler == 'OFF'
    assert h.probes[-3:] == [('preparation','quiescence-sql'),
        ('preparation','quiescence-sql'),('preparation','redis-clients')]


@pytest.mark.parametrize('importing', [False, True])
def test_main_restore_bound_keeps_original_scheduler_digest_with_new_transport(integrated, importing):
    h = integrated
    view = install(h); before = frozen_journals(h)
    old_binding = view.scheduler.binding
    current = restore(h)
    new_binding = digest(dict(database=current.config['database'],
        databaseUuid=current.config['replacement']['databaseUuid'],
        mysql=[s for s in current.config['services'] if s['role']=='mysql'],
        mainApplication=current.config['mainApplication']))
    assert old_binding != new_binding
    start = len(h.transport.calls)
    current.bound(importing=importing)
    assert main.protections(current).scheduler.binding == old_binding
    assert h.probes[-1] == ('restore','import-state' if importing else 'database-state')
    assert ('restore','archive-inputs') in h.probes
    assert all(row[1]=='RESTORE' for row in h.transport.calls[start:])
    assert all(path.read_bytes()==raw for path,raw in before.items())


def test_main_restore_finish_releases_same_custody_and_publishes_all_original_pins(integrated):
    h = integrated
    install(h); before = frozen_journals(h); current = restore(h)
    start = len(h.transport.calls)
    result = current.replacement_finish()
    assert set(result)=={'archiveViewReleasePin','publishedWriteFenceReleasePin','mysqlSchedulerReleasePin'}
    assert h.transport.releases==['archive','fence','scheduler']
    assert h.transport.scheduler=='ON' and h.custody.snapshot()['state']=='RELEASED'
    assert all(reference in current.original_pins for reference in result.values())
    assert all(reference in current.original_pins for reference in h.preparation.original_pins)
    assert all(row[1]=='RESTORE' for row in h.transport.calls[start:])
    assert all(path.read_bytes()==raw for path,raw in before.items())


@pytest.mark.parametrize('method', METHODS)
@pytest.mark.parametrize('problem', ['missing','wrong-type','no-context','no-policy'])
def test_program_main_methods_reject_missing_or_wrong_custody_before_external_probes(integrated, method, problem):
    h = integrated; native = h.preparation
    if problem=='missing': del native.protection_custody
    elif problem=='wrong-type': native.protection_custody=SimpleNamespace(view_for=lambda _:pytest.fail('duck custody'))
    elif problem=='no-context': native.native_context=None
    else: native.native_context._configuration['targetProgramPolicies']={}
    before = list(h.transport.calls)
    with pytest.raises(RecoveryError, match='PROGRAM_PROTECTION_'):
        getattr(native,method)()
    assert h.transport.calls==before and h.probes==[]


@pytest.mark.parametrize('method', METHODS)
def test_program_main_methods_cannot_borrow_custody_from_another_real_context(integrated, method):
    h = integrated
    with context(h.e,h.ctx._binding,h.fd) as other:
        original = SimpleNamespace(native_context=other.preparation(h.e.owner),policy=h.preparation.policy)
        native = MainData(original,h,'other-context')
        before = list(h.transport.calls)
        with pytest.raises(RecoveryError,match='PROGRAM_PROTECTION_CONTEXT_CHANGED'):
            getattr(native,method)()
        assert h.transport.calls==before and h.probes==[]


@pytest.mark.parametrize('method', METHODS)
def test_old_main_preparation_never_gets_generic_permission_after_stage(integrated, method):
    h = integrated
    install(h); restore(h); before = list(h.transport.calls)
    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_PHASE_CHANGED'):
        getattr(h.preparation,method)()
    assert h.transport.calls==before and h.probes==[]


@pytest.mark.parametrize('method', ['bound','replacement_finish'])
@pytest.mark.parametrize('problem', ['credential','journal','lock'])
def test_restore_main_rejects_real_original_or_lock_drift_before_any_external_probe(integrated, method, problem):
    h = integrated
    install(h); current = restore(h)
    if problem=='credential':
        Path(current.config['secrets']['mysql']['MYSQL_ROOT_PASSWORD']['path']).write_bytes(b'changed')
    elif problem=='journal':
        (h.e.claim/'mysql-scheduler'/'active.json').write_bytes(b'{}')
    else:
        import fcntl
        fcntl.flock(h.fd,fcntl.LOCK_UN)
    before = list(h.transport.calls)
    expected = ValueError if problem=='lock' else RecoveryError
    with pytest.raises(expected,match='PROGRAM_|BACKUP_EPOCH_'):
        getattr(current,method)()
    assert h.transport.calls==before and h.probes==[]


@pytest.mark.parametrize('failure,prior', [('archive',[]),('fence',['archive']),('scheduler',['archive','fence'])])
def test_main_finish_failure_retains_prior_release_pins_without_later_release(integrated, failure, prior):
    h = integrated
    install(h); current = restore(h); h.transport.fail=failure
    with pytest.raises(RecoveryError,match='EXPECTED_.*_RELEASE_FAILURE'):
        current.replacement_finish()
    snapshot = h.custody.snapshot()
    assert snapshot['state']=='FAILED_RETAINED'
    assert h.transport.releases==prior and h.transport.scheduler=='OFF'
    assert snapshot['protections'][failure]['state']=='FAILED_RETAINED'
    assert all(snapshot['protections'][kind]['releasePin'] in current.original_pins for kind in prior)


@pytest.fixture
def runtime_contract():
    # Full original MAIN contract, real version/writer/config files. Its Docker
    # inspect reply is a unit protocol row; no context or transport grant here.
    value=main_fixtures.MainContractTests('test_registered_main_accepts_matching_archived_program')
    value.setUp()
    try: yield value
    finally: value.doCleanups()


def test_runtime_inputs_validate_current_config_without_consulting_archived_images(runtime_contract):
    c=runtime_contract
    version=Path(c.material['versionPins'][0]['path'])
    version.write_bytes(b'{"images":{"backend":"different"}}')
    main.application_runtime_inputs(c.native)
    with pytest.raises(RecoveryError,match='MAIN_PIN_CHANGED|MAIN_ARCHIVED_IMAGE_MISMATCH'):
        main.application_inputs(c.native)


@pytest.mark.parametrize('problem', ['writer','configuration','mount'])
def test_runtime_inputs_do_not_skip_current_original_configuration_evidence(runtime_contract, problem):
    c=runtime_contract
    if problem=='writer':
        Path(c.target['mainApplication']['writerAdmission']['evidencePin']['path']).write_bytes(b'{}')
    elif problem=='configuration':
        path=Path(c.temp.name)/'app.yml';path.write_bytes(b'original')
        c.target['mainApplication']['configurationPins']=[pin(path)];path.write_bytes(b'changed')
    else:
        c.rows['backend']['Mounts']=[dict(Type='bind',RW=False,Source='/unknown',Destination='/app.yml')]
    with pytest.raises(RecoveryError,match='MAIN_'):
        main.application_runtime_inputs(c.native)


def test_restore_inputs_still_reject_valid_archived_version_with_different_program(runtime_contract):
    c=runtime_contract
    version=Path(c.material['versionPins'][0]['path'])
    version.write_bytes(b'{"images":{"backend":"sha256:0000000000000000000000000000000000000000000000000000000000000000","frontend":"sha256:5555555555555555555555555555555555555555555555555555555555555555"}}')
    c.material['versionPins']=[pin(version)]
    main.application_runtime_inputs(c.native)
    with pytest.raises(RecoveryError,match='MAIN_ARCHIVED_IMAGE_MISMATCH'):
        main.application_inputs(c.native)


def test_legacy_protections_remain_lazy_and_use_original_factories(monkeypatch):
    calls=[]
    native=SimpleNamespace(config={'mainApplication':{}},native_context=None,protection_custody=None)
    for name,field in [('archive_view','archive'),('published_fence','fence'),('mysql_scheduler','scheduler')]:
        monkeypatch.setattr(main,name,lambda value,field=field:calls.append((field,value)) or field)
    view=main.protections(native)
    assert calls==[]
    assert view.archive=='archive' and calls==[('archive',native)]
    assert view.fence=='fence' and view.scheduler=='scheduler'
    assert [name for name,_ in calls]==['archive','fence','scheduler']


@pytest.mark.parametrize('method', ['replacement_write_fence','replacement_finish'])
def test_legacy_main_protection_order_and_results_are_preserved(monkeypatch, method):
    calls=[]
    native=main.guarded_type(object)();native.config={'mainApplication':{}}
    def protection(name):
        return SimpleNamespace(install=lambda:calls.append(name+'-install'),
            release=lambda:calls.append(name+'-release') or {'path':name})
    for name,factory in [('archive','archive_view'),('fence','published_fence'),('scheduler','mysql_scheduler')]:
        monkeypatch.setattr(main,factory,lambda _,name=name:protection(name))
    result=getattr(native,method)()
    if method=='replacement_write_fence':assert calls==['archive-install','fence-install']
    else:
        assert calls==['archive-release','fence-release','scheduler-release']
        assert result['mysqlSchedulerReleasePin']=={'path':'scheduler'}
