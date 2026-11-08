"""Local contract tests only; no remote health or backup success is simulated."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_automatic_source_restoration import validate_evidence, write_exclusive, validate_failed_pins


@pytest.fixture
def evidence():
    task = Path(__file__).resolve().parent
    submission = json.loads((task / 'automatic-full-ui-submission.json').read_text(encoding='utf-8'))
    installation = json.loads((task / 'automatic-control-installation-57.json').read_text(encoding='utf-8'))
    # Structural unit fixture; it is never sent to a host or saved as acceptance.
    audit = dict(schemaVersion='AutomaticBackupChainAudit/v1', status='PASS', state='SUCCEEDED',
        actualExitCode=0, operationId=submission['request']['operationId'], sourceConfigRef=submission['applicationId'],
        pointType='FULL', sourceRestored=True, sourceEpoch=installation['epoch'],
        package=dict(engine=installation['controllers'][0]['engine'], variant='standard', fileCount=130,
                     fileManifestSha256=installation['fileManifestSha256']),
        finishedAt='2026-11-08T00:00:00+00:00')
    terminal = dict(schemaVersion='AutomaticIncrementalUiTerminal/v1', kind='FULL', applicationId=submission['applicationId'],
        request=deepcopy(submission['request']), operationState='SUCCEEDED', observedAt='2026-11-08T00:00:01+00:00')
    return installation, submission, audit, terminal


@pytest.mark.parametrize('kind,full_sha', [('FULL', True)])
def test_kind_reports_exact_failed_original_scope(evidence, kind, full_sha):
    installation, submission, audit, terminal = deepcopy(evidence)
    submission['kind'] = terminal['kind'] = kind
    if kind != 'FULL':
        submission['request']['action'] = terminal['request']['action'] = audit['pointType'] = 'INCREMENTAL'
    result = validate_evidence(kind, installation, submission, audit, terminal)
    assert result['operationId'] == submission['request']['operationId']
    assert result['failedOriginalFullShaRequired'] is full_sha


@pytest.mark.parametrize('kind', ['I1', 'I2'])
def test_legacy_full_submission_cannot_be_relabelled_as_new_incremental(evidence, kind):
    installation, submission, audit, terminal = deepcopy(evidence)
    submission['kind'] = terminal['kind'] = kind
    submission['request']['action'] = terminal['request']['action'] = audit['pointType'] = 'INCREMENTAL'
    with pytest.raises(ValueError, match='SOURCE_DEPLOYMENT_REQUIRED'):
        validate_evidence(kind, installation, submission, audit, terminal)


@pytest.mark.parametrize('document,key,value', [
    (2, 'status', 'FAILED'), (2, 'state', 'RUNNING'), (2, 'actualExitCode', 3),
    (2, 'operationId', 'other'), (2, 'sourceConfigRef', 'other'), (2, 'sourceRestored', False),
    (3, 'operationState', 'RUNNING'), (3, 'observedAt', '2026-11-07T00:00:00+00:00'),
    (0, 'sourceCommit', 'f' * 40),
])
def test_incomplete_or_mismatched_evidence_is_rejected_before_remote(evidence, document, key, value):
    evidence[document][key] = value
    with pytest.raises(ValueError):
        validate_evidence('FULL', *evidence)


def test_terminal_exact_original_request_required(evidence):
    evidence[3]['request']['parentChainRef'] = 'other'
    with pytest.raises(ValueError):
        validate_evidence('FULL', *evidence)


def test_epoch_ready_required(evidence):
    evidence[2]['sourceEpoch']['state'] = 'REPLACING'
    with pytest.raises(ValueError):
        validate_evidence('FULL', *evidence)


def test_full_sha_inventory_requires_all_unique_10044_pins():
    pins = [dict(path='/original/' + str(i), bytes=0, sha256='0' * 64) for i in range(10044)]
    assert validate_failed_pins(pins) == 10044
    with pytest.raises(ValueError):
        validate_failed_pins(pins[:-1])
    pins[-1] = pins[0]
    with pytest.raises(ValueError):
        validate_failed_pins(pins)


def test_write_is_exclusive_and_preserves_original_bytes(tmp_path):
    output = tmp_path / 'result.json'
    write_exclusive(output, dict(status='LOCAL_UNIT_FIXTURE'))
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        write_exclusive(output, dict(status='CHANGED'))
    assert output.read_bytes() == before
