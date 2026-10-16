"""R10 private-phase/restore-chain semantics; fixtures are not Linux qualification."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
import recovery_native_launcher as launcher
from recovery_environment_contract import EnvironmentFailure, Schemas, canonical
from recovery_native_process import PROCESS_FIELDS, QUALIFICATION_PROCESS_FIELDS, NativeProcessProducer


def ref(name):
    return dict(path='/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07/' + name,
                bytes=len(name), sha256=hashlib.sha256(name.encode()).hexdigest())


def stamp(delta):
    return (datetime.now(timezone.utc) + timedelta(seconds=delta)).isoformat().replace('+00:00', 'Z')


def test_private_fields_match_ratified_root_without_changing_business_fields():
    selected = json.loads((ROOT/'doc/tasks/20261010-recovery-environment-dev/native-lab-continuation-20261012/'
                           'r10-selected-contract-and-review.json').read_text(encoding='utf-8'))['contract']
    for key, fields in [('qualificationIntent', launcher.QUALIFICATION_INTENT_FIELDS),
            ('authorization', launcher.QUALIFICATION_GRANT_FIELDS), ('lease', launcher.QUALIFICATION_LEASE_FIELDS),
            ('launch', launcher.QUALIFICATION_LAUNCH_FIELDS), ('provision', launcher.QUALIFICATION_PROVISION_FIELDS)]:
        assert fields == set(selected['inputRecords'][key]['exactFields'])
    assert QUALIFICATION_PROCESS_FIELDS == set(selected['outputRecords']['qualificationProcessOriginal']['exactFields'])
    assert launcher.QUALIFICATION_RESULT_FIELDS == set(selected['outputRecords']['finiteResult']['exactFields'])
    assert {'restoreId', 'recoveryPoint', 'targetIdentityPin', 'stage'} <= PROCESS_FIELDS
    assert not {'restoreId', 'recoveryPoint', 'targetIdentityPin', 'stage'} & QUALIFICATION_PROCESS_FIELDS
    assert not {'operationRequestPin', 'serviceBindingPins', 'recordSchemasPin'} & (
        launcher.QUALIFICATION_LAUNCH_FIELDS | launcher.QUALIFICATION_PROVISION_FIELDS)


def phase_context(monkeypatch):
    """Explicit protected-record fixtures; no key/runtime or host calls occur."""
    ctx = launcher.NativeQualificationContext.__new__(launcher.NativeQualificationContext)
    ctx.authority_pin = ref('public.pem'); ctx.launch_pin = ref('launch.json'); ctx.provision_pin = ref('provision.json')
    ctx.proof_pin = ref('proof.json'); ctx.verify_runtime = False; ctx.deadline = time.monotonic()+30
    ctx.expires_at = stamp(60)
    binding = dict(rehearsalId=launcher.REHEARSAL_ID, qualificationId='q-1', operationId='op-1',
        phase='NATIVE_QUALIFICATION', hostId='host-59', targetId='brlab-20261012-native', executorId='worker-1')
    ctx.binding = {k: binding[k] for k in launcher.QUALIFICATION_BINDING_FIELDS}
    ctx.launch = dict(qualificationIntentPin=ref('intent.json'), authorizationPin=ref('grant.json'),
        leasePin=ref('lease.json'), installationPin=ref('installation.json'), allowedCallerPin=ref('caller.json'),
        producerEntryPin=ref('ops/recovery/recovery_native_launcher.py'), issuedAt=stamp(-10), expiresAt=stamp(60))
    ctx.intent = dict(binding, sourceScopePin=ref('scope.json'), issuedAt=stamp(-10), expiresAt=stamp(60))
    ctx.provision = dict(producerIdentityPin=ref('producer.json'), workingDirectory='/selected', maximumObservations=4)
    ctx.installation = dict(nativeRuntimeTrustPin=ref('trust.json'), pythonPin=ref('python'), filePins=[])
    ctx.proof = dict(hostId='host-59', bootId='boot-1', issuedAt=stamp(-10), expiresAt=stamp(60),
        **{k: k+'-actual' for k in launcher.NS_FIELDS})
    ctx.native_trust = dict(nativeFilePins=[])
    ctx.scope = dict(schemaVersion='RepositoryLabScope/v1', rehearsalId=launcher.REHEARSAL_ID,
        repositoryId='repository-1', sourceIdentityPin=ref('source-identity.json'), host='172.30.30.59',
        root=str(launcher.LAB_ROOT), resourcePrefix='brlab-20261012',
        allowedActions=sorted(launcher.BUSINESS_SCOPE_ACTIONS), expiresAt=stamp(60))
    ctx.caller = ctx.producer_identity = dict(issuedAt=stamp(-10), expiresAt=stamp(60))
    ctx.grant = dict(binding, schemaVersion='RepositoryLabNativeQualificationAuthorization/v1',
        approved=True, actions=['OWNED_PROCESS_QUALIFICATION'], notBefore=stamp(-10), expiresAt=stamp(60))
    ctx.lease = dict(binding, schemaVersion='RepositoryLabNativeQualificationLease/v1',
        leaseId='l-1', fenceToken=1, state='HELD', notBefore=stamp(-10), expiresAt=stamp(60))
    ctx.selections = [dict(action='OWNED_PROCESS_QUALIFICATION', commandId='worker', argv=['selected'],
        cwd='/selected', sourcePins=[ref('source.py')])]
    records = {p['path']: value for p, value in [(ctx.launch_pin, ctx.launch), (ctx.provision_pin, ctx.provision),
        (ctx.launch['qualificationIntentPin'], ctx.intent), (ctx.intent['sourceScopePin'], ctx.scope),
        (ctx.launch['installationPin'], ctx.installation), (ctx.proof_pin, ctx.proof),
        (ctx.installation['nativeRuntimeTrustPin'], ctx.native_trust), (ctx.launch['authorizationPin'], ctx.grant),
        (ctx.launch['leasePin'], ctx.lease)]}
    monkeypatch.setattr(launcher, 'signed_payload', lambda pin, key: records[pin['path']])
    monkeypatch.setattr(launcher, 'read_signed_caller', lambda pin, key: ctx.caller)
    monkeypatch.setattr(launcher, 'pinned_bytes', lambda pin: canonical({}))
    return ctx, records


@pytest.mark.parametrize('damage', [None, 'wrong-host', 'wrong-target', 'wrong-executor', 'wrong-operation',
    'wrong-qualification', 'business-action', 'not-approved', 'released-lease', 'zero-fence', 'bool-fence',
    'expired-grant', 'future-grant', 'extra-business-field'])
def test_phase_guard_requires_actual_matching_private_authority(monkeypatch, damage):
    ctx, records = phase_context(monkeypatch)
    fields = {'wrong-host':'hostId', 'wrong-target':'targetId', 'wrong-executor':'executorId',
              'wrong-operation':'operationId', 'wrong-qualification':'qualificationId'}
    if damage in fields: ctx.grant[fields[damage]] = 'foreign'
    if damage == 'business-action': ctx.grant['actions'] = ['VERIFY_RECOVERY']
    if damage == 'not-approved': ctx.grant['approved'] = False
    if damage == 'released-lease': ctx.lease['state'] = 'RELEASED'
    if damage == 'zero-fence': ctx.lease['fenceToken'] = 0
    if damage == 'bool-fence': ctx.lease['fenceToken'] = True
    if damage == 'expired-grant': ctx.grant['expiresAt'] = stamp(-1)
    if damage == 'future-grant': ctx.grant['notBefore'] = stamp(10)
    if damage == 'extra-business-field': ctx.grant['restoreId'] = 'fake'
    if damage:
        with pytest.raises(EnvironmentFailure): ctx.guard()
    else: ctx.guard()


@pytest.mark.parametrize('damage', [None, 'unknown-exit', 'unreaped', 'foreign-source', 'wrong-id', 'business-schema',
                                  'extra-restore-id', 'foreign-proof', 'future-time'])
def test_private_process_refuses_unknown_and_business_records(monkeypatch, damage):
    ctx, _ = phase_context(monkeypatch)
    payload = {k: None for k in QUALIFICATION_PROCESS_FIELDS}
    payload.update(ctx.binding, schemaVersion=launcher.QUALIFICATION_PROCESS_SCHEMA, rehearsalId=launcher.REHEARSAL_ID,
        **{k: ctx.selections[0][k] for k in ('commandId', 'argv', 'cwd', 'sourcePins')},
        nativeRuntimeProofPin=ctx.proof_pin, uid=0, gid=0, startedAt=stamp(-3), finishedAt=stamp(-2),
        terminationKind='EXITED', waitStatus=256, actualExitCode=1, descendantState='REAPED',
        stdoutPin=ref('stdout'), resultPin=ref('stdout'), **{k: ctx.proof[k] for k in ('hostId', 'bootId', *launcher.NS_FIELDS)})
    if damage == 'unknown-exit': payload['actualExitCode'] = None
    if damage == 'unreaped': payload['descendantState'] = 'UNKNOWN'
    if damage == 'foreign-source': payload['sourcePins'] = [ref('foreign.py')]
    if damage == 'wrong-id': payload['commandId'] = 'foreign'
    if damage == 'business-schema': payload['schemaVersion'] = 'RecoveryNativeProcessResult/v1'
    if damage == 'extra-restore-id': payload['restoreId'] = 'fake'
    if damage == 'foreign-proof': payload['nativeRuntimeProofPin'] = ref('foreign-proof')
    if damage == 'future-time': payload['finishedAt'] = stamp(10)
    if damage:
        with pytest.raises(EnvironmentFailure): ctx.admit_process(payload)
    else: ctx.admit_process(payload)


def test_process_methods_have_strict_separate_bindings():
    instance = NativeProcessProducer.__new__(NativeProcessProducer)
    with pytest.raises(EnvironmentFailure, match='NATIVE_OPERATION_BINDING_SHAPE'):
        instance.run(command_id='q', argv=[], cwd='', source_pins=[], binding=dict(
            qualificationId='q', operationId='o', phase='NATIVE_QUALIFICATION', targetId='t', executorId='e'))
    with pytest.raises(EnvironmentFailure, match='NATIVE_QUALIFICATION_BINDING_SHAPE'):
        instance.run_qualification(command_id='q', argv=[], cwd='', source_pins=[], binding=dict(
            operationId='o', restoreId='r', targetIdentityPin=ref('t'), recoveryPoint='p', stage='VERIFY_RECOVERY'))


@pytest.mark.parametrize('damage', [None, 'url', 'shell', 'extra-argv', 'extra-source', 'missing-source',
                                  'duplicate-id', 'business-action', 'wrong-cwd'])
def test_finite_literal_command_selection(monkeypatch, damage):
    ctx, _ = phase_context(monkeypatch)
    directory = 'ops/recovery/'
    files = [ref(directory+name) for name in ('recovery_native_launcher.py', 'repository_native_runtime.py',
                                            'repository_records.py', 'recovery_environment_supervisor.py')]
    ctx.installation['filePins'] = files; ctx.static_pins = files+[ctx.installation['pythonPin']]
    ctx.native_tool_pins = []
    ctx.installation_command = ['approved-installation']
    sources = launcher.installation_sources(ctx.installation, ctx.launch['producerEntryPin'])
    ctx.selections = [dict(action='OWNED_PROCESS_QUALIFICATION', commandId='worker',
        argv=[ctx.installation['pythonPin']['path'], ctx.launch['producerEntryPin']['path'], 'qualify-owned-process'],
        cwd='/selected', sourcePins=sources)]
    selection = ctx.selections[0]
    if damage == 'url': selection['argv'] = ['https://example.invalid/']
    if damage == 'shell': selection['argv'] = ['/bin/sh', '-c', 'true']
    if damage == 'extra-argv': selection['argv'].append('--fake-success')
    if damage == 'extra-source': selection['sourcePins'].append(ref('uninstalled.py'))
    if damage == 'missing-source': selection['sourcePins'].pop()
    if damage == 'duplicate-id': ctx.selections.append(deepcopy(selection))
    if damage == 'business-action': selection['action'] = 'START_APPLICATION'
    if damage == 'wrong-cwd': selection['cwd'] = '/'
    if damage:
        with pytest.raises(EnvironmentFailure): ctx._select_commands()
    else: ctx._select_commands()


@pytest.mark.parametrize('damage', ['empty-pins', 'fake-success', 'business-state', 'missing-authority', 'expired'])
def test_finite_result_cannot_be_success_without_current_signed_originals(monkeypatch, damage):
    ctx, records = phase_context(monkeypatch)
    ctx.graph_pins = []
    ctx.provision.update(signerUid=24001, signerGid=24001)
    admission = launcher.AuthorityQualificationAdmission(ctx)
    payload = dict(schemaVersion=launcher.QUALIFICATION_RESULT_SCHEMA, rehearsalId=launcher.REHEARSAL_ID,
        qualificationId='q-1', operationId='op-1', phase='NATIVE_QUALIFICATION',
        qualificationIntentPin=ctx.launch['qualificationIntentPin'], launchPin=ctx.launch_pin,
        provisionPin=ctx.provision_pin, authorityIdentityPin=ref('a.json'), invocationPins=[],
        state='SUCCEEDED', issuedAt=stamp(-1), expiresAt=stamp(30))
    peer = {k:None for k in launcher.CALLER_FIELDS}
    peer.update(schemaVersion='RepositoryLabNativeAuthority/v1', rehearsalId=launcher.REHEARSAL_ID,
        nativeRuntimeProofPin=ctx.proof_pin, pid=launcher.os.getpid(), uid=24001, gid=24001,
        issuedAt=stamp(-10), expiresAt=stamp(60))
    records[payload['authorityIdentityPin']['path']] = peer
    monkeypatch.setattr(launcher, 'match_process', lambda *args: None)
    monkeypatch.setattr(launcher.os, 'geteuid', lambda: 24001, raising=False)
    if damage == 'fake-success': payload['invocationPins'] = [ref('invented.signed.json')]
    if damage == 'business-state': payload['state'] = 'STARTED'
    if damage == 'missing-authority': peer['schemaVersion'] = 'RepositoryLabNativeCaller/v1'
    if damage == 'expired': payload['expiresAt'] = stamp(-2)
    with pytest.raises(EnvironmentFailure): admission.admit(payload)


@pytest.mark.parametrize('count', [4096, 4097])
def test_one_combined_graph_limit_counts_even_unread_private_and_binary_pins(count):
    pins = [ref(str(i)) for i in range(count)]
    if count > 4096:
        with pytest.raises(EnvironmentFailure, match='NATIVE_GRAPH_LIMIT'):
            launcher.protected_record_graph(pins, opaque_paths={p['path'] for p in pins})
    else: assert len(launcher.protected_record_graph(pins, opaque_paths={p['path'] for p in pins})) == count


def schema_fixture(rule, definitions):
    if '$ref' in rule:
        if rule['$ref'] == '#/$defs/Pin': return ref('schema-fixture.json')
        return schema_fixture(definitions[rule['$ref'].split('/')[-1]], definitions)
    if 'const' in rule: return rule['const']
    if 'enum' in rule: return rule['enum'][0]
    if rule.get('type') == 'object':
        return {k:schema_fixture(rule['properties'][k], definitions) for k in rule.get('required', [])}
    if rule.get('type') == 'array': return []
    if rule.get('type') == 'boolean': return True
    if rule.get('type') == 'integer': return 1
    if rule.get('type') == ['string','null']: return None
    if rule.get('pattern') == '^[0-9a-f]{64}$': return 'a'*64
    return 'fixture'


@pytest.mark.parametrize('damage', [None, 'operation', 'restore', 'target', 'plan-pin', 'point',
                                  'app-extra-point', 'failed-restore', 'request-plan', 'fourth-input', 'configuration'])
def test_frozen_application_reads_real_restore_plan_chain(monkeypatch, damage):
    schema = json.loads((ROOT/'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json').read_text(encoding='utf-8'))
    definitions = schema['$defs']; p = {k:ref(k+'.json') for k in ('app', 'restore', 'plan', 'target', 'point', 'identity', 'original', 'config', 'policy', 'scope')}
    app, restore, plan, target, point = [schema_fixture(definitions[k], definitions) for k in
        ('ApplicationStartResult', 'RestoreExecutionResult', 'RestorePlan', 'RecoveryTarget', 'RepositoryPoint')]
    for value in (app, restore, plan): value.update(operationId='op', restoreId='restore')
    for value in (app, restore, target): value['targetIdentityPin'] = p['identity']
    app.update(restoreResultPin=p['restore'], originalStartResultPins=[p['original']], state='SUCCEEDED')
    target['configurationPin'] = app['configurationPin']
    restore.update(planPin=p['plan'], recoveryPoint='2026-point', originalInvocationPins=[p['original']], state='SUCCEEDED')
    plan.update(mode='REHEARSAL', candidatePin=p['point'], orderedChainPins=[p['point']], targetRef=p['config'], recoveryPoint='2026-point')
    point['commonRecoveryPoint'] = '2026-point'
    config = dict(schemaVersion='RecoveryEnvironmentConfig/v1', targetIdentityPin=p['identity'], sourceScopePin=p['scope'])
    policy = dict.fromkeys(('schemaVersion maxAgeMilliseconds rtoObjectiveMilliseconds rpoObjectiveMilliseconds '
        'recoveryTargetPin verificationTargetPin dataBaselinePin dataObservationPin protectionBeforePin protectionAfterPin '
        'playwrightObservationPin timingObservationPin requiredUserPaths protectedScopes '
        'requireDeletedReferenceObjects derivedBaselinePin controlledEligibilityPin').split())
    policy.update(schemaVersion='RecoveryVerificationPolicy/v2', maxAgeMilliseconds=60000, recoveryTargetPin=p['target'])
    request = dict(action='VERIFY_RECOVERY', operationId='op', mode='REHEARSAL', selectedPointPin=p['point'],
        sourceOrTargetRef=p['config'], policyPin=p['policy'], inputPins=dict(
        applicationStartResult=p['app'], restoreExecutionResult=p['restore'], restorePlan=p['plan']))
    service = dict(applicationStartPin=p['app'], targetIdentityPin=p['identity'],
                   environmentConfigPin=p['config'], sourceScopePin=p['scope'])
    if damage == 'operation': restore['operationId'] = 'foreign'
    if damage == 'restore': plan['restoreId'] = 'foreign'
    if damage == 'target': target['targetIdentityPin'] = p['original']
    if damage == 'plan-pin': restore['planPin'] = p['original']
    if damage == 'point': point['commonRecoveryPoint'] = 'foreign'
    if damage == 'app-extra-point': app['recoveryPoint'] = 'invented'
    if damage == 'failed-restore': restore['state'] = 'FAILED_RETAINED'
    if damage == 'request-plan': request['inputPins']['restorePlan'] = p['original']
    if damage == 'fourth-input': request['inputPins']['recoveryTarget'] = p['target']
    if damage == 'configuration': plan['targetRef'] = p['target']
    records = {p[k]['path']:v for k,v in zip(('app','restore','plan','target','point','original'),
                                          (app,restore,plan,target,point,plan))}
    records.update({p['config']['path']:config, p['policy']['path']:policy})
    monkeypatch.setattr(launcher, 'pinned_bytes', lambda pin: canonical(records[pin['path']]))
    if damage:
        with pytest.raises(EnvironmentFailure): launcher.restored_application_binding(request, service, Schemas(schema))
    else:
        binding, originals = launcher.restored_application_binding(request, service, Schemas(schema))
        assert binding['recoveryPoint'] == '2026-point' and 'recoveryPoint' not in app
        assert all(p[k] in originals for k in ('app', 'restore', 'plan', 'target', 'point', 'original'))
