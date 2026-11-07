"""Closed legacy MAIN history is readable; no new missing proof is accepted."""
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import pytest

from test_retained_replacement_retry import retained
from test_backup_variants import packages
from recovery_engine import RecoveryError, digest, pin, write
from recovery_retained_retry import validate_clearance, bind_clearances


def refresh(target, claim, value):
    value['targetConfigurationSha256'] = digest(target)
    reference = write(claim/'recovery-clearance.json', value)
    root = Path(value['requestPin']['path']).parent
    write(claim/'recovery-ready.json', dict(clearancePin=reference,
        releasePin=write(root/'resource-recovery-release.json', dict(
            clearancePin=reference, reason='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY'))))
    used = claim/'recovery-consumption.json'
    if used.exists():
        consumer = json.loads(used.read_bytes()); consumer['clearancePin'] = reference
        write(used, consumer)


@pytest.fixture
def closed_main(retained):
    target, claim, request, value = retained
    target['mainApplication'] = dict(schemaVersion='RegisteredMainApplication/v1')
    root = Path(value['requestPin']['path']).parent
    write(root/'configuration.json', dict(targets={'target': target}))
    successor = claim.parent/'retry-1'; successor.mkdir()
    next_root = root.parent/'retry-1'; next_root.mkdir()
    write(next_root/'configuration.json', dict(targets={'target': target}))
    write(next_root/'request.json', dict(request, operationId='retry-1'))
    write(next_root/'worker-result.json', dict(operationId='retry-1', state='SUCCEEDED', actualExitCode=0))
    write(next_root/'child-exit.json', dict(actualExitCode=0, timedOut=False))
    write(successor/'replacement-result.json', dict(operationId='retry-1', targetConfigRef='target', state='SUCCEEDED'))
    write(claim/'recovery-consumption.json', dict(schemaVersion='RetainedReplacementConsumption/v1',
        clearancePin=pin(claim/'recovery-clearance.json'), replacementOperationId='retry-1'))
    value['expiresAt'] = '2026-01-02T00:00:00Z'
    refresh(target, claim, value)
    return target, claim, request, value


def test_closed_main_history_is_read_only_and_cannot_be_consumed_again(closed_main):
    target, claim, request, value = closed_main
    before = {str(p): p.read_bytes() for p in claim.parent.parent.rglob('*') if p.is_file()}
    assert validate_clearance(target, claim) == value
    assert bind_clearances(target, dict(request, operationId='later', recoveryPointRef='new'), consume=False) == []
    assert before == {str(p): p.read_bytes() for p in claim.parent.parent.rglob('*') if p.is_file()}


@pytest.mark.parametrize('variant', ['standard', 'lightweight'])
def test_real_packaged_closed_history(variant, packages, closed_main, tmp_path):
    target, claim, _, _ = closed_main
    with tarfile.open(packages/('backup-restore-'+variant+'.tgz')) as archive:
        archive.extractall(tmp_path/'package', filter='data')
    target_file = tmp_path/'target.json'; write(target_file, target)
    program = '''import json,pathlib,sys
sys.path[:0]=[str(pathlib.Path(sys.argv[1])/p) for p in ('common','control','formal')]
from recovery_retained_retry import validate_clearance
v=validate_clearance(json.loads(pathlib.Path(sys.argv[2]).read_bytes()),pathlib.Path(sys.argv[3]))
assert v['operationId']=='failed-1'
'''
    result = subprocess.run([sys.executable, '-B', '-c', program, str(tmp_path/'package'), str(target_file), str(claim)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('case', ['unconsumed', 'v2', 'archive-config', 'published-config',
    'archive-view', 'published-fence', 'mysql-scheduler', 'protection-recovery',
    'main-protection-recovery.json', 'scheduler-proof', 'original-config', 'next-config',
    'next-point', 'next-target', 'next-source', 'next-unknown', 'next-exit', 'next-timeout',
    'next-incomplete', 'next-missing', 'cycle'])
def test_missing_proof_requires_closed_unchanged_unprotected_legacy_history(closed_main, case):
    target, claim, request, value = closed_main
    root = Path(value['requestPin']['path']).parent; next_root = root.parent/'retry-1'
    if case == 'unconsumed': (claim/'recovery-consumption.json').unlink()
    elif case == 'v2': target['mainApplication']['schemaVersion'] = 'RegisteredMainApplication/v2'
    elif case == 'archive-config': target['mainApplication']['archiveMountProtection'] = {}
    elif case == 'published-config': target['mainApplication']['publishedDataEndpoints'] = []
    elif case in ('archive-view', 'published-fence', 'mysql-scheduler', 'protection-recovery', 'main-protection-recovery.json'):
        (claim/case).mkdir()
    elif case == 'scheduler-proof': value['schedulerCustodyPin'] = {}
    elif case in ('original-config', 'next-config'):
        write((root if case == 'original-config' else next_root)/'configuration.json', dict(targets={'target': {'changed': True}}))
    elif case in ('next-point', 'next-target', 'next-source'):
        field={'next-point':'recoveryPointRef','next-target':'targetConfigRef','next-source':'sourceConfigRef'}[case]
        write(next_root/'request.json', dict(request, operationId='retry-1', **{field:'other'}))
    elif case == 'next-unknown': write(next_root/'worker-result.json', dict(operationId='retry-1', state='TERMINAL_UNKNOWN', actualExitCode=0))
    elif case == 'next-exit': write(next_root/'child-exit.json', dict(actualExitCode=1, timedOut=False))
    elif case == 'next-timeout': write(next_root/'child-exit.json', dict(actualExitCode=0, timedOut=True))
    elif case == 'next-incomplete': (next_root/'worker-result.json').unlink()
    elif case == 'next-missing': (claim.parent/'retry-1/replacement-result.json').unlink()
    elif case == 'cycle':
        write(claim/'recovery-consumption.json', dict(schemaVersion='RetainedReplacementConsumption/v1',
            clearancePin=pin(claim/'recovery-clearance.json'), replacementOperationId=claim.name))
    refresh(target, claim, value)
    with pytest.raises((RecoveryError, ValueError, KeyError, FileNotFoundError)):
        validate_clearance(target, claim)


def test_two_failed_consumptions_require_final_success(closed_main):
    target, claim, request, value = closed_main
    root = Path(value['requestPin']['path']).parent; second = claim.parent/'retry-1'; second_root=root.parent/'retry-1'
    refs=dict(value)
    refs.update(operationId='retry-1', requestPin=pin(second_root/'request.json'),
        resultPin=write(second_root/'worker-result.json', dict(operationId='retry-1', state='FAILED_RETAINED', actualExitCode=1)),
        exitPin=write(second_root/'child-exit.json', dict(actualExitCode=1, timedOut=False)),
        replacementResultPin=write(second/'replacement-result.json', dict(operationId='retry-1', targetConfigRef='target', state='FAILED_RETAINED')))
    final=claim.parent/'final';final.mkdir();final_root=root.parent/'final';final_root.mkdir()
    write(final_root/'configuration.json', dict(targets={'target':target}))
    write(final_root/'request.json',dict(request,operationId='final'))
    write(final_root/'worker-result.json',dict(operationId='final',state='SUCCEEDED',actualExitCode=0))
    write(final_root/'child-exit.json',dict(actualExitCode=0,timedOut=False))
    write(final/'replacement-result.json',dict(operationId='final',targetConfigRef='target',state='SUCCEEDED'))
    refresh(target,second,refs)
    write(second/'recovery-consumption.json',dict(schemaVersion='RetainedReplacementConsumption/v1',
        clearancePin=pin(second/'recovery-clearance.json'),replacementOperationId='final'))
    assert validate_clearance(target,claim)==value
    write(final_root/'child-exit.json',dict(actualExitCode=1,timedOut=False))
    with pytest.raises(RecoveryError):validate_clearance(target,claim)
    write(second/'recovery-consumption.json',dict(schemaVersion='RetainedReplacementConsumption/v1',
        clearancePin=pin(second/'recovery-clearance.json'),replacementOperationId=claim.name))
    with pytest.raises(RecoveryError,match='RECOVERY_LEGACY_HISTORY_CYCLE_OR_DEPTH'):
        validate_clearance(target,claim)


def test_legacy_depth_is_bounded(closed_main):
    target,claim,_,_=closed_main
    with pytest.raises(RecoveryError,match='RECOVERY_LEGACY_HISTORY_CYCLE_OR_DEPTH'):
        validate_clearance(target,claim,_legacy_ancestors=tuple('prior-'+str(i) for i in range(64)))


def test_dangling_protection_link_is_not_absence(closed_main):
    target,claim,_,_=closed_main
    (claim/'mysql-scheduler').symlink_to(claim/'missing')
    with pytest.raises(RecoveryError,match='RECOVERY_LEGACY_PROTECTION_NOT_PROVEN'):
        validate_clearance(target,claim)
