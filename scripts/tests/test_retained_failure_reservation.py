"""Retained-failure resource lifecycle using real files and host locking."""
import copy
from pathlib import Path

import pytest

from test_recovery_resource_reservation import host
import recovery_resource_admission as admission
from recovery_engine import pin, write


def evidence(host):
    config, request, root, directory = host
    reservation = admission.reserve(config, request, root)
    child = write(root/'child-exit.json', dict(actualExitCode=1, timedOut=False))
    native = write(root/'native-001.json', dict(schemaVersion='RecoveryDataInvocation/v1',
        operationId='first', actualExitCode=0, finishedAt='finished', mutation=True))
    worker = dict(operationId='first', state='FAILED_RETAINED', actualExitCode=1,
        failureCode='FORMAL_DATA_TYPE_UNSUPPORTED', data=dict(mutationDispatched=True,
            partialTargetRetained=True, retryPermitted=False), originalResultPins=[native])
    worker_pin = write(root/'worker-result.json', worker)
    output = copy.deepcopy(worker)
    output['originalResultPins'] += [reservation, worker_pin, child]
    result_pin = write(root/'result.json', output)
    claim = write(root/'target-claim.json', dict(operationId='first'))
    proof = write(root/'stopped-proof.json', dict(claimPin=claim, stopped=True))
    return result_pin, proof, claim


def test_completed_failure_releases_only_host_and_keeps_originals(host):
    config, request, root, directory = host
    result_pin, proof, claim = evidence(host)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    calls = []
    def stopped():
        calls.append(True)
        return [proof]
    released = admission.release_retained_failure(config, request, root, result_pin, stopped)
    assert calls == [True] and proof in released
    assert not (directory/'active.json').exists()
    assert all((root/name).read_bytes() == raw for name, raw in before.items())
    assert pin(Path(claim['path'])) == claim
    assert (root/'resource-retained-failure-release.json').is_file()
    other = root.parent/'second'; other.mkdir()
    admission.reserve(config, dict(request, operationId='second'), other)
    current = (directory/'active.json').read_bytes()
    def must_not_recheck():
        raise AssertionError('Already released history must not touch new operation')
    assert admission.release_retained_failure(config, request, root, result_pin, must_not_recheck) == released
    assert (directory/'active.json').read_bytes() == current


@pytest.mark.parametrize('unsafe', ['unknown','zero_exit','timeout','missing_child','missing_worker',
    'mutation_flag','partial_flag','retry_flag','worker_mismatch','configuration','reservation',
    'proof_empty','writer_live','changed_pin','missing_native'])
def test_unproven_retained_failure_never_releases(host, unsafe):
    import json
    config, request, root, directory = host
    result_pin, proof, _ = evidence(host)
    output = json.loads((root/'result.json').read_bytes())
    if unsafe == 'unknown': output['state'] = 'TERMINAL_UNKNOWN'
    if unsafe == 'zero_exit': output['actualExitCode'] = 0
    if unsafe == 'mutation_flag': output['data']['mutationDispatched'] = False
    if unsafe == 'partial_flag': output['data']['partialTargetRetained'] = False
    if unsafe == 'retry_flag': output['data']['retryPermitted'] = True
    if unsafe == 'worker_mismatch': output['failureCode'] = 'DIFFERENT'
    if unsafe in ('missing_child','missing_worker','missing_native'):
        name = {'missing_child':'child-exit.json','missing_worker':'worker-result.json','missing_native':'native-001.json'}[unsafe]
        output['originalResultPins'] = [p for p in output['originalResultPins'] if Path(p['path']).name != name]
    if unsafe == 'timeout':
        (root/'child-exit.json').write_text(json.dumps(dict(actualExitCode=1,timedOut=True)),encoding='utf-8')
        output['originalResultPins'] = [pin(root/'child-exit.json') if Path(p['path']).name=='child-exit.json' else p for p in output['originalResultPins']]
    (root/'result.json').write_text(json.dumps(output),encoding='utf-8')
    result_pin = pin(root/'result.json')
    if unsafe == 'configuration': config = dict(config, changed=True)
    if unsafe == 'reservation': (directory/'active.json').write_text('{}',encoding='utf-8')
    if unsafe == 'changed_pin': (root/'native-001.json').write_text('{}',encoding='utf-8')
    def stopped():
        if unsafe == 'writer_live': raise RuntimeError('WRITER_STILL_ACTIVE')
        return [] if unsafe == 'proof_empty' else [proof]
    with pytest.raises(RuntimeError):
        admission.release_retained_failure(config,request,root,result_pin,stopped)
    assert (directory/'active.json').exists()
    assert not (root/'resource-retained-failure-release.json').exists()


@pytest.mark.parametrize('change', ['exit','unfinished','wrong_operation','wrong_schema'])
def test_bound_but_inconclusive_native_receipt_still_blocks(host, change):
    import json
    config, request, root, directory = host
    _, proof, _ = evidence(host)
    native = json.loads((root/'native-001.json').read_bytes())
    if change == 'exit': native['actualExitCode'] = 1
    if change == 'unfinished': native['finishedAt'] = None
    if change == 'wrong_operation': native['operationId'] = 'other'
    if change == 'wrong_schema': native['schemaVersion'] = 'Unknown/v1'
    (root/'native-001.json').write_text(json.dumps(native),encoding='utf-8')
    native_pin = pin(root/'native-001.json')
    for name in ('worker-result.json','result.json'):
        value = json.loads((root/name).read_bytes())
        value['originalResultPins'] = [native_pin if Path(p['path']).name=='native-001.json'
            else pin(root/'worker-result.json') if Path(p['path']).name=='worker-result.json'
            else p for p in value['originalResultPins']]
        (root/name).write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(admission.ResourceAdmissionError, match='RESTORE_RESOURCE_RELEASE_NOT_PROVEN'):
        admission.release_retained_failure(config,request,root,pin(root/'result.json'),lambda:[proof])
    assert (directory/'active.json').exists()
