"""Admission protocols and actual packaged entry boundaries, never a live backup.

Metadata and payloads are real temporary files. The packaged tests run the real
configuration/catalogue/publish entry in fresh processes. Only the clock, SMB
transport (real local probe bytes), and forbidden capture boundary are replaced;
no database, remote SMB, container, browser, or successful backup is claimed.
"""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'ops/recovery'), str(ROOT/'backend/src/main/resources'),
               str(Path(__file__).resolve().parent)]
import repository_records as records
from test_automatic_incremental_plan import MetadataFixture, ui_request

NOW = datetime(2026, 11, 10, 4, 44, 59, tzinfo=timezone.utc)
POLICY = dict(maxChainPoints=16, maxChainAgeSeconds=86400)


class Clock(datetime):
    current = NOW

    @classmethod
    def now(cls, tz=None):
        return cls.current if tz is not None else cls.current.replace(tzinfo=None)


def admission(policy, created, count, *, now=NOW):
    function = getattr(records, 'incremental_chain_admission', None)
    assert callable(function), 'INCREMENTAL_CHAIN_ADMISSION_API_REQUIRED'
    return function(policy, created, count, now=now)


def stamp(value):
    return value.isoformat().replace('+00:00', 'Z')


@pytest.mark.parametrize(('age', 'count', 'expected'), [
    (86399, 1, None), (86400, 1, 'INCREMENTAL_CHAIN_AGE_EXPIRED'),
    (205907, 3, 'INCREMENTAL_CHAIN_AGE_EXPIRED'),
    (100, 15, None), (100, 16, 'INCREMENTAL_CHAIN_POINT_LIMIT_REACHED'),
])
def test_shared_age_and_point_boundaries(age, count, expected):
    assert admission(POLICY, stamp(NOW-timedelta(seconds=age)), count) == expected


INVALID_POLICIES = [
    {}, {'maxChainPoints': 16}, {'maxChainAgeSeconds': 86400},
    *[dict(POLICY, **{key: value}) for key in POLICY for value in (True, '16', 0, -1)],
    dict(POLICY, maxChainPoints=1025),
]


@pytest.mark.parametrize('policy', INVALID_POLICIES)
def test_invalid_policy_is_a_blocker_even_without_a_baseline(tmp_path, policy):
    fixture = MetadataFixture(tmp_path, policy=policy)
    value = fixture.native.incremental_plan('source-A')
    assert (value['state'], value['reasonCode']) == ('BLOCKED', 'REPOSITORY_CHAIN_POLICY_INVALID')


@pytest.mark.parametrize('created', ['not-a-time', '2026-11-10T04:44:59', None,
                                    '2026-11-11T00:00:00Z'])
def test_shared_bad_or_future_root_is_not_a_new_full_reason(created):
    with pytest.raises(records.RepositoryError):
        admission(POLICY, created, 1)


def plan_fixture(tmp_path, *, age=100, points=16, count=1, created=None):
    fixture = MetadataFixture(tmp_path, policy=dict(POLICY, maxChainPoints=points))
    fixture.point('full-root', created=stamp(NOW-timedelta(seconds=age)) if created is None else created)
    chain = ['full-root']
    for number in range(1, count):
        name = 'increment-%d' % number
        fixture.point(name, chain, finished='2026-11-07T01:%02d:00Z' % number)
        chain.append(name)
    return fixture


@pytest.mark.parametrize(('age', 'points', 'count', 'state', 'reason'), [
    (86399, 16, 1, 'READY', None),
    (86400, 16, 1, 'BASELINE_REQUIRED', 'INCREMENTAL_CHAIN_AGE_EXPIRED'),
    (205907, 16, 3, 'BASELINE_REQUIRED', 'INCREMENTAL_CHAIN_AGE_EXPIRED'),
    (100, 3, 2, 'READY', None),
    (100, 3, 3, 'BASELINE_REQUIRED', 'INCREMENTAL_CHAIN_POINT_LIMIT_REACHED'),
])
def test_real_planner_uses_root_creation_and_owner_policy(tmp_path, age, points, count, state, reason):
    fixture = plan_fixture(tmp_path, age=age, points=points, count=count)
    with patch.object(records, 'datetime', Clock):
        value = fixture.native.incremental_plan('source-A')
    assert (value['state'], value['reasonCode']) == (state, reason)
    if state == 'BASELINE_REQUIRED':
        assert value['parentChainRef'] is value['baseFullRef'] is None


@pytest.mark.parametrize('created', ['invalid', '2026-11-11T00:00:00Z'])
def test_real_planner_blocks_invalid_or_future_root(tmp_path, created):
    fixture = plan_fixture(tmp_path, created=created)
    with patch.object(records, 'datetime', Clock):
        value = fixture.native.incremental_plan('source-A')
    assert value['state'] == 'BLOCKED'
    assert value['reasonCode'] in ('REPOSITORY_CHAIN_BASELINE_TIME_INVALID', 'REPOSITORY_FUTURE_POINT_REFUSED')


def test_ready_digest_is_stable_until_expiry_and_resolve_rechecks_before_dispatch(tmp_path):
    fixture = plan_fixture(tmp_path, age=86398)
    Clock.current = NOW
    try:
        with patch.object(records, 'datetime', Clock):
            first = fixture.native.incremental_plan('source-A')
            Clock.current += timedelta(seconds=1)
            second = fixture.native.incremental_plan('source-A')
            assert first == second and first['state'] == 'READY'
            Clock.current += timedelta(seconds=1)
            value = fixture.native.incremental_plan('source-A')
            assert value['state'] == 'BASELINE_REQUIRED'
            with pytest.raises(RuntimeError, match='INCREMENTAL_CHAIN_AGE_EXPIRED'):
                fixture.native.resolve(ui_request('new-operation', parent='full-root'))
    finally:
        Clock.current = NOW


def test_plan_evidence_explicitly_binds_root_manifest_without_clock(tmp_path):
    fixture = plan_fixture(tmp_path)
    import recovery_control_incremental_plan as planner
    seen = []
    original = planner.response
    def record(*args, **kwargs):
        seen.append(kwargs['evidence'])
        return original(*args, **kwargs)
    with patch.object(records, 'datetime', Clock), patch.object(planner, 'response', side_effect=record):
        value = fixture.native.incremental_plan('source-A')
    assert value['state'] == 'READY'
    root = fixture.native.document(fixture.points['full-root']['pointPin'])
    assert root['manifestPin'] in seen[-1]
    assert NOW not in seen[-1]


def test_observation_crossing_expiry_cannot_return_stale_ready(tmp_path):
    fixture = plan_fixture(tmp_path, age=86399)
    original = fixture.native.incremental_source_observation
    def observe(*args, **kwargs):
        value = original(*args, **kwargs)
        Clock.current += timedelta(seconds=1)
        return value
    try:
        with patch.object(records, 'datetime', Clock), patch.object(
                fixture.native, 'incremental_source_observation', side_effect=observe):
            value = fixture.native.incremental_plan('source-A')
        assert (value['state'], value['reasonCode']) == ('BASELINE_REQUIRED', 'INCREMENTAL_CHAIN_AGE_EXPIRED')
    finally:
        Clock.current = NOW


def test_final_freshness_crossing_expiry_cannot_return_stale_ready(tmp_path):
    fixture = plan_fixture(tmp_path, age=86399)
    import recovery_control_incremental_plan as planner
    original = planner.PlanReader.finish
    def finish(reader):
        original(reader)
        Clock.current += timedelta(seconds=1)
    try:
        with patch.object(records, 'datetime', Clock), patch.object(planner.PlanReader, 'finish', finish):
            value = fixture.native.incremental_plan('source-A')
        assert (value['state'], value['reasonCode']) == ('BASELINE_REQUIRED', 'INCREMENTAL_CHAIN_AGE_EXPIRED')
    finally:
        Clock.current = NOW


@pytest.mark.parametrize(('age', 'points'), [(86400, 16), (100, 1)])
def test_expired_or_full_chain_never_observes_the_live_source(tmp_path, age, points):
    fixture = plan_fixture(tmp_path, age=age, points=points)
    with patch.object(records, 'datetime', Clock), patch.object(fixture.native,
            'incremental_source_observation', side_effect=AssertionError('live source must not be observed')) as observe:
        value = fixture.native.incremental_plan('source-A')
    assert value['state'] == 'BASELINE_REQUIRED'
    observe.assert_not_called()


def test_policy_and_root_manifest_changes_are_bound_in_the_plan_digest(tmp_path):
    fixture = plan_fixture(tmp_path)
    native = fixture.native
    with patch.object(records, 'datetime', Clock):
        first = native.incremental_plan('source-A')
        config = native.configuration()
        owner = native.document(config['sourceConfigurations']['source-A'])
        owner['maxChainAgeSeconds'] += 1
        config['sourceConfigurations']['source-A'] = fixture.write('owner-next.json', owner)
        native.config_pin = fixture.write('configuration-next.json', config)
        policy_changed = native.incremental_plan('source-A')
        assert first['state'] == policy_changed['state'] == 'READY'
        assert first['planDigest'] != policy_changed['planDigest']
        assert first['evidenceDigest'] != policy_changed['evidenceDigest']

        binding = native.document(fixture.points['full-root']['controlPin'])
        output = native.document(binding['resultPin'])
        point = native.document(output['data']['pointPin'])
        manifest = native.document(point['manifestPin'])
        manifest['createdAt'] = stamp(NOW-timedelta(seconds=99))
        point['manifestPin'] = fixture.write('full-root/manifest-next.json', manifest)
        point_pin = fixture.write('full-root/point-next.json', point)
        repository = native.document(output['data']['repositoryBindingPin'])
        material = native.document(repository['recoveryMaterialPin'])
        material['manifestPin'] = point['manifestPin']
        repository.update(manifestPin=point['manifestPin'], repositoryPointPin=point_pin,
            recoveryMaterialPin=fixture.write('full-root/material-next.json', material))
        output['data'].update(pointPin=point_pin,
            repositoryBindingPin=fixture.write('full-root/repository-next.json', repository))
        binding['resultPin'] = fixture.write('full-root/output-next.json', output)
        selector = fixture.write('full-root/control-next.json', binding)
        (tmp_path/'registry/points/full-root.pin.json').write_bytes(records.canonical(selector))
        root_changed = native.incremental_plan('source-A')
    assert root_changed['state'] == 'READY'
    assert root_changed['parentChainRef'] == policy_changed['parentChainRef']
    assert root_changed['evidenceDigest'] != policy_changed['evidenceDigest']
    assert root_changed['planDigest'] != policy_changed['planDigest']


@pytest.fixture(scope='module')
def actual_packages(tmp_path_factory):
    spec = importlib.util.spec_from_file_location('policy_variants', ROOT/'ops/backup_engine/build_variants.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    output = tmp_path_factory.mktemp('chain-policy-packages')/'packages'
    builder.build(output)
    return output


def test_standard_package_retains_the_original_final_age_check(actual_packages):
    import ast
    with tarfile.open(ROOT/'ops/backup_engine/baselines/backup-restore-standard-20261021.tgz') as archive:
        original = ast.parse(archive.extractfile('common/repository_minimal.py').read())
    with tarfile.open(actual_packages/'backup-restore-standard.tgz') as archive:
        shipped = ast.parse(archive.extractfile('common/repository_minimal.py').read())
    def final_check(tree):
        publish = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'publish')
        return [ast.dump(node) for node in ast.walk(publish) if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == 'require'
                and len(node.args) == 2 and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == 'REPOSITORY_NEW_FULL_REQUIRED'
                and any(isinstance(child, ast.Name) and child.id == 'created' for child in ast.walk(node.args[0]))]
    assert len(final_check(original)) == 1
    assert final_check(shipped) == final_check(original)


PACKAGED_BOUNDARY = r'''
import hashlib,json,os,pathlib,sys
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
engine,folder,variant,scenario=map(str,sys.argv[1:])
sys.path[:0]=[str(pathlib.Path(engine)/p) for p in ('common','control','formal')]
import repository_minimal as native
import repository_records as records
from repository_binding import repository_binding
root=pathlib.Path(folder)
now=datetime(2026,11,10,4,44,59,tzinfo=timezone.utc)
class Clock(datetime):
 current=now
 @classmethod
 def now(cls,tz=None):return cls.current if tz else cls.current.replace(tzinfo=None)
native.datetime=records.datetime=Clock
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(records.canonical(value));path.chmod(0o600)
 return records.pin_file(path)
nas,operations,staging=[root/n for n in ('nas','operations','staging')]
for p in (nas/'archives',operations,staging):p.mkdir(parents=True)
identity=write(root/'identity.json',dict(sourceFingerprint='source',databaseUuid='database'))
tool=write(root/'tool.json',{'protocolFixtureOnly':True})
parents=[]
count=2 if scenario in ('at-limit','next-at-limit') else 1
age=86400 if scenario=='expired' else 86399 if scenario in ('during-preflight','during-config') else 100
if scenario=='future':age=-1
for number in range(count):
 ref='baseline' if number==0 else 'increment-%d'%number
 side=nas/'archives'/ref/'.repository';side.mkdir(parents=True)
 payload=side.parent/'payload.bin';payload.write_bytes(b'real local fixture payload '+str(number).encode())
 payload_pin=records.pin_file(payload)
 created=(now-timedelta(seconds=age-number)).isoformat().replace('+00:00','Z')
 tree=write(side/'tree.json',{'payload.bin':'file|%d|%s'%(payload_pin['bytes'],payload_pin['sha256'])})
 scope=write(side/'scope.json',dict(sourceIdentityPin=identity))
 capture=write(side/'capture.json',dict(protocolFixtureOnly=True))
 manifest=dict(schemaVersion='RepositoryManifest/v1',backupId=ref,generationId='baseline',
  pointType='FULL' if not number else 'INCREMENTAL',parentPointPins=list(parents),
  commonRecoveryPoint='recovery-'+ref,payloadRefs=[payload_pin],sourceIdentityPin=identity,
  copyProtectionPin=None,createdAt=created,versionPins=[tool],toolPins=[tool],payloadTreePin=tree)
 manifest_pin=write(side/'manifest.json',manifest)
 material=write(side/'material.json',dict(manifestPin=manifest_pin,recoveryPoint=manifest['commonRecoveryPoint'],
  sourceScopePin=scope,sourceFingerprint='source',database=dict(capturePointPin=capture)))
 index=write(side/'index.json',dict(manifestPin=manifest_pin,recoveryPoint=manifest['commonRecoveryPoint'],
  backupId=ref,generationId='baseline',repositoryBound=True,sourceIdentity='source',
  contentPins={payload_pin['sha256']:payload_pin}))
 terminal=write(side/'exit.json',dict(schemaVersion='RepositoryMinimumChildTerminal/v1',actualExitCode=0,
  processTerminated=True,state='EXITED',operationId=ref))
 close=write(side/'close.json',dict(schemaVersion='RepositoryMinimumArchiveClose/v1',operationId=ref,
  archiveReaderClosed=True,closeResponse=dict(state='ARCHIVE_READER_CLOSED_NOT_NAS_PROOF')))
 readback=write(side/'readback.json',dict(schemaVersion='RepositoryMinimumReadback/v1',manifestPin=manifest_pin,
  independentConnectionId='local-protocol-fixture',payloadRefs=[payload_pin],operationId=ref,
  recoveryMaterialPin=material,objectContentIndexPin=index,sourceScopePin=scope))
 point={k:manifest[k] for k in ('backupId','generationId','pointType','parentPointPins','commonRecoveryPoint','payloadRefs')}
 point.update(schemaVersion='RepositoryPoint/v1',integrityState='COMPLETE',manifestPin=manifest_pin,
  originalExitEvidencePin=terminal,ownerCloseEvidencePin=close,readbackEvidencePin=readback)
 point_pin=write(side/'point.json',point)
 binding=repository_binding(SimpleNamespace(policy={'sourceIdentityPin':identity}),point_pin,point,material,index)
 write(side/'recovery-repository-binding.json',binding)
 parents.append(point_pin)
request=dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId='new-increment',action='INCREMENTAL',
 sourceConfigRef='source',parentChainRef='latest',recoveryPointRef=None,targetConfigRef=None)
if scenario=='full':request.update(action='FULL',parentChainRef=None)
capture=dict(schemaVersion='minimal-source-capture-config/v1',sourceConfigRef='source',archiveRoot=str(staging),
 source=dict(sourceIdentity='source',sourceFingerprint='source',databaseUuid='database'),parent=None if scenario=='full' else
 dict(parentChainRef='latest',capturePointPin=capture,repositoryPointPin=point_pin,objectContentIndexPin=index))
capture_path=root/'capture.json';write(capture_path,capture)
owner=dict(schemaVersion='RepositoryMinimumConfiguration/v1',repositoryId='protocol',repositoryRoot=str(nas),
 operationRoot=str(operations),timeoutMilliseconds=30000,responseTimeoutMilliseconds=1000,
 maxChainPoints=2 if scenario=='at-limit' else 3 if scenario=='next-at-limit' else 16,
 maxChainAgeSeconds=86400,captureBinderPath=str(root/'unused-binder.py'),
 sources={'source':dict(captureCommand=[sys.executable],configurationPath=str(capture_path),stagingRoot=str(staging),
 sourceIdentityPath=identity['path'],toolPaths=[sys.executable])},parentChains={'latest':point_pin},recoveryPoints={},
 readback={},maximumArchiveBytes=10000,minimumFreeBytes=1)
if scenario=='invalid-policy':owner['maxChainAgeSeconds']=0
owner_path=root/'owner.json';write(owner_path,owner)
operation=operations/'new';operation.mkdir();write(operation/'request.json',request)
events=[]
class LocalReadback:
 def __init__(self,configuration,deadline):self.client=os;self.kwargs={}
 def __enter__(self):events.append('preflight');return self
 def remote(self,path):return path
 def read(self,path,expected):
  assert records.pin_file(path)==expected
  return pathlib.Path(path).read_bytes()
 def __exit__(self,*args):
  if scenario=='during-preflight':Clock.current+=timedelta(seconds=1)
native.SmbReadback=LocalReadback
# An explicit local transport adapter replaces only remote credential/library setup.
native.smb_configuration=lambda config,operation,deadline:config.value['readback']
class CaptureBoundary(Exception):pass
def forbidden_capture(*args,**kwargs):events.append('capture');raise CaptureBoundary('first real capture dispatch boundary')
native.run_child=forbidden_capture
original_pin_file=native.pin_file
def advancing_pin_file(path,*args,**kwargs):
 value=original_pin_file(path,*args,**kwargs)
 if scenario=='during-config' and pathlib.Path(path)==capture_path:Clock.current+=timedelta(seconds=1)
 return value
native.pin_file=advancing_pin_file
try:
 config=native.MinimumConfiguration(str(owner_path),request)
 native.publish(config,request,operation,records.Deadline(30000))
except CaptureBoundary:result='CAPTURE_BOUNDARY'
except records.RepositoryError as error:result=error.code
else:raise AssertionError('unexpected backup completion')
print(json.dumps(dict(result=result,events=events)))
'''


@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
@pytest.mark.parametrize('scenario', ['expired', 'at-limit', 'future', 'invalid-policy',
                                     'valid', 'next-at-limit', 'during-preflight', 'during-config', 'full'])
def test_actual_packaged_constructor_and_publish_stop_before_capture(variant, scenario, actual_packages, tmp_path):
    engine = tmp_path/'engine'
    with tarfile.open(actual_packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(engine, filter='data')
        version = json.load(archive.extractfile('package.json'))
        assert len(version['files']) == (147 if variant == 'standard' else 146), 'existing package member count is preserved'
    result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', PACKAGED_BOUNDARY,
                             str(engine), str(tmp_path/'protocol'), variant, scenario],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    if scenario in ('expired', 'at-limit', 'during-config') or scenario == 'during-preflight' and variant == 'standard':
        assert value['result'] == 'REPOSITORY_NEW_FULL_REQUIRED', value
        assert 'capture' not in value['events'], value
        if scenario == 'during-preflight':
            assert value['events'] == ['preflight']
    elif scenario == 'future':
        assert value['result'] == 'REPOSITORY_FUTURE_POINT_REFUSED', value
        assert 'capture' not in value['events'], value
    elif scenario == 'invalid-policy':
        assert value['result'] in ('REPOSITORY_CHAIN_POLICY_INVALID', 'REPOSITORY_MINIMUM_BUDGET_INVALID'), value
        assert 'capture' not in value['events'], value
    else:
        assert value['result'] == 'CAPTURE_BOUNDARY', value
        assert value['events'] == (['preflight', 'capture'] if variant == 'standard' else ['capture'])
