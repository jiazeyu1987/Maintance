"""Local signed authority/stable digest checks; no Linux or restore acceptance."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from test_recovery_plan_lab import originals, current_case
from test_recovery_plan_objects import archived_chain, rewrite_final_index
from recovery_engine import RecoveryError, digest, pinned_json, require, validate_record, write
from recovery_plan import immutable_inputs
from recovery_plan_lab import context_record, current_authority, immutable_binding


@pytest.fixture
def requests(tmp_path):
    c = originals(tmp_path)
    preflight = current_case(c, 'RESTORE_PREFLIGHT')
    point = write(tmp_path/'engineering-point.json', {'engineeringOnly': 'not-a-live-repository-point'})
    grant = write(tmp_path/'two-action-grant.json', preflight['grant'])
    preflight['request'].update(authorizationRefs=[grant], selectedPointPin=point,
                                inputPins={'repositoryPoint': point})
    preflight['trust']['authorizationSha256s'] = [grant['sha256']]
    preflight['context'].update(authorizationPin=grant,
        operationRequestPin=write(tmp_path/'preflight-original-request.json', preflight['request']))
    preflight_context = c['seal']('preflight-authority-context', preflight['context'])
    source_scope = write(tmp_path/'engineering-source-scope.json', {'sourceIdentityPin': c['identity']})
    stable_policy = dict(c['policy'], sourceScopePin=source_scope,
                         dataTargetPin=preflight['identity'], repositoryBindingPinsByManifestSha256={})
    policy_c1 = dict(stable_policy, selectedLabContextPin=preflight_context)
    plan = dict(schemaVersion='RestorePlan/v1', operationId=preflight['request']['operationId'],
        restoreId='engineering-digest-only-plan', mode='REHEARSAL', candidatePin=point, orderedChainPins=[],
        recoveryPoint='engineering-only', targetRef=preflight['request']['sourceOrTargetRef'],
        supportedVersionPins=[], toolPins=[], plannedWrites=[], sideEffectPolicyPin=preflight['request']['policyPin'],
        authorizationRefs=preflight['request']['authorizationRefs'], leaseRef=preflight['request']['leaseRef'],
        immutableInputsSha256=digest(immutable_inputs(preflight['request'], policy_c1, [])))
    plan_pin = write(tmp_path/'engineering-restore-plan.json', plan)
    restored = dict(preflight['request'], action='RESTORE_EXECUTE', requestId='execute-request',
                    inputPins={'restorePlan': plan_pin, 'recoveryTarget': preflight['identity']})
    execution_context = dict(preflight['context'],
        operationRequestPin=write(tmp_path/'execute-original-request.json', restored))
    restored_context = c['seal']('execute-authority-context', execution_context)
    policy_c2 = dict(stable_policy, selectedLabContextPin=restored_context)
    # Empty chain intentionally limits these checks to plan digest/authority.
    # It never claims native admission, a complete recovery chain or execution.
    return dict(c=c, preflight=preflight, restored=restored, c1=preflight_context, c2=restored_context,
                policy_c1=policy_c1, policy_c2=policy_c2, stable_policy=stable_policy, plan=plan, plan_pin=plan_pin)


def test_two_complete_requests_have_distinct_signed_current_authority_and_one_stable_digest(requests):
    f = requests; c = f['c']; first = f['preflight']
    schemas = __import__('recovery_engine').pin(Path(__file__).resolve().parents[2]/
        'doc/tasks/20261010-backup-restore-modular-development/record-schemas.json')
    for request, context_pin in ((first['request'], f['c1']), (f['restored'], f['c2'])):
        validate_record(request, 'OperationRequest', schemas)
        selected = context_record(context_pin, c['profile'], c['scope'])
        current_authority(request, selected, c['scope'], first['identity'], first['trust'])
    assert f['c1'] != f['c2']
    one = immutable_inputs(first['request'], f['policy_c1'], [])
    two = immutable_inputs(f['restored'], f['policy_c2'], [])
    assert one == two and digest(one) == digest(two)
    validate_record(pinned_json(f['plan_pin']), 'RestorePlan', schemas)
    require(f['plan']['immutableInputsSha256'] == digest(two), 'RESTORE_PLAN_IMMUTABLE_INPUT_MISMATCH')
    assert one['dataPolicySha256'] == digest(f['stable_policy'])
    assert 'selectedLabContextPin' not in one['labBinding']
    assert 'selectedLabContextPin' in f['policy_c1']  # Admission's in-memory authority stays intact.
    assert one['authorizations'] == first['request']['authorizationRefs']
    assert one['lease'] == first['request']['leaseRef']
    for name in ('labProfilePin', 'executionHostPin', 'installedClosurePin', 'labScopePin'):
        expected = f['policy_c1'][name] if name == 'labProfilePin' else c['profile'][name]
        assert one['labBinding'][name] == expected


def test_current_context_does_not_enter_either_policy_digest_or_lab_binding(requests):
    f = requests
    assert digest(f['policy_c1']) != digest(f['policy_c2'])
    assert immutable_binding(f['policy_c1'], []) == immutable_binding(f['policy_c2'], [])
    assert immutable_inputs(f['preflight']['request'], f['policy_c1'], []) == \
        immutable_inputs(f['preflight']['request'], f['policy_c2'], [])


@pytest.mark.parametrize('field', ['sourceScopePin', 'dataTargetPin', 'maximumProofAgeSeconds', 'pythonPin',
    'moduleSourcePins', 'dataWorkerPin', 'repositoryBindingPinsByManifestSha256', 'futureStablePolicyField'])
def test_every_other_lab_policy_input_remains_in_plan_digest(requests, tmp_path, field):
    f = requests; before = digest(immutable_inputs(f['preflight']['request'], f['policy_c1'], []))
    changed = dict(f['policy_c2'])
    changed[field] = write(tmp_path/('changed-'+field), {'engineeringOnly': field})
    after = digest(immutable_inputs(f['restored'], changed, []))
    assert before != after
    with pytest.raises(RecoveryError, match='RESTORE_PLAN_IMMUTABLE_INPUT_MISMATCH'):
        require(before == after, 'RESTORE_PLAN_IMMUTABLE_INPUT_MISMATCH')


@pytest.mark.parametrize('field', ['executionHostPin', 'installedClosurePin', 'labScopePin',
                                  'copyProtectionPinsByManifestSha256', 'authorityKeyPin'])
def test_stable_profile_installation_and_copy_protection_changes_reject_prior_digest(requests, tmp_path, field):
    f = requests; c = f['c']
    before = digest(immutable_inputs(f['preflight']['request'], f['policy_c1'], []))
    profile = dict(c['profile']); original = write(tmp_path/('new-'+field), {'engineeringOnly': field})
    profile[field] = {'b'*64: original} if field == 'copyProtectionPinsByManifestSha256' else original
    changed = dict(f['policy_c2'], labProfilePin=write(tmp_path/'changed-stable-profile.json', profile))
    after = digest(immutable_inputs(f['restored'], changed, []))
    assert before != after


@pytest.mark.parametrize('field', ['selectedPointPin', 'sourceOrTargetRef', 'policyPin', 'authorizationRefs', 'leaseRef'])
def test_request_stable_pins_and_original_authority_bindings_remain_immutable(requests, tmp_path, field):
    f = requests; before = digest(immutable_inputs(f['preflight']['request'], f['policy_c1'], []))
    request = dict(f['restored']); changed = write(tmp_path/('changed-request-'+field), {'engineeringOnly': field})
    request[field] = [changed] if field == 'authorizationRefs' else changed
    assert before != digest(immutable_inputs(request, f['policy_c2'], []))


@pytest.mark.parametrize('change', ['old_preflight_context', 'expired_current_context', 'wrong_complete_request',
                                  'expired_grant', 'wrong_lease', 'untrusted_grant'])
def test_stable_digest_never_replaces_current_request_authority(requests, tmp_path, change):
    f = requests; c = f['c']; first = f['preflight']
    request = copy.deepcopy(f['restored']); trust = copy.deepcopy(first['trust'])
    ref = f['c1'] if change == 'old_preflight_context' else f['c2']
    context = context_record(ref, c['profile'], c['scope'])
    if change == 'wrong_complete_request': request['deadlineMilliseconds'] += 1
    if change == 'expired_current_context':
        now = datetime.now(timezone.utc)
        context.update(issuedAt=(now-timedelta(hours=1)).isoformat().replace('+00:00','Z'),
                       expiresAt=(now-timedelta(minutes=1)).isoformat().replace('+00:00','Z'))
        ref = c['seal']('expired-current-context', context)
    if change == 'expired_grant':
        grant = pinned_json(context['authorizationPin']); grant['expiresAt'] = '2000-01-01T00:00:00Z'
        context['authorizationPin'] = write(tmp_path/'expired-selected-grant.json', grant)
        request['authorizationRefs'] = [context['authorizationPin']]
        context['operationRequestPin'] = write(tmp_path/'expired-grant-request.json', request)
        trust['authorizationSha256s'] = [context['authorizationPin']['sha256']]
        ref = c['seal']('expired-grant-context', context)
    if change == 'wrong_lease':
        lease = pinned_json(context['leasePin']); lease['operationId'] = 'other'
        context['leasePin'] = write(tmp_path/'wrong-held-lease.json', lease); request['leaseRef'] = context['leasePin']
        context['operationRequestPin'] = write(tmp_path/'wrong-lease-request.json', request)
        trust['leaseSha256s'] = [context['leasePin']['sha256']]
        ref = c['seal']('wrong-lease-context', context)
    if change == 'untrusted_grant': trust['authorizationSha256s'] = []
    with pytest.raises(RecoveryError):
        selected = context_record(ref, c['profile'], c['scope'])
        current_authority(request, selected, c['scope'], first['identity'], trust)


def test_production_digest_and_complete_local_chain_bindings_are_unchanged(tmp_path):
    chain, policy = archived_chain(tmp_path)
    policy['schemaVersion'] = 'RecoveryDataPolicy/v1'
    request = dict(selectedPointPin=chain[-1][0], sourceOrTargetRef=chain[-1][3], policyPin=chain[0][3],
                   authorizationRefs=[chain[0][0]], leaseRef=chain[0][3])
    before = immutable_inputs(request, policy, chain)
    assert before['dataPolicySha256'] == digest(policy) and 'labBinding' not in before
    assert before['chain'] == [step[0] for step in chain]
    assert before['materials'] == [step[3] for step in chain]
    assert len(before['repositoryBindings']) == len(before['objectContentIndexes']) == 2
    # Even this key stays hashed under production; exclusion is lab-only.
    with_context = dict(policy, selectedLabContextPin=chain[0][0])
    assert immutable_inputs(request, with_context, chain)['dataPolicySha256'] == digest(with_context)
    assert digest(before) != digest(immutable_inputs(request, with_context, chain))
    assert digest(before) != digest(immutable_inputs(request, policy, chain[:1]))
    rewrite_final_index(chain, policy, lambda index: index.update(changedContentSha256=[]))
    after = immutable_inputs(request, policy, chain)
    assert before['objectContentIndexes'] != after['objectContentIndexes'] and digest(before) != digest(after)
