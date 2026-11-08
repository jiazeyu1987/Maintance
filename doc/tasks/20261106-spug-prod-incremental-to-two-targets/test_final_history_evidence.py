"""Validate final history evidence against the actual retained generations."""
import copy
import json
from pathlib import Path

import pytest
import verify_closeout as subject


TASK = Path(__file__).parent


def inputs(suffix):
    def read(name):
        return json.loads((TASK / name).read_text(encoding='utf-8'))
    baseline = read('protected-history-' + suffix + '.json')
    current = read('stable-controls-closeout.json')['currentControls'][suffix]
    selected = (None if suffix == '57' else
                subject.contracts.current_installations(TASK)['targets'][suffix]['currentReceiptPin'])
    return baseline, current, selected


@pytest.mark.parametrize('suffix', ['57', '58', '59'])
def test_actual_current_generations_preserve_original_history(suffix):
    subject.verify_final_history_evidence(suffix, *inputs(suffix))


@pytest.mark.parametrize('field', ['originalProtectedFiles', 'immutableOriginalPathsVerified'])
def test_changed_current_counts_rejected(field):
    baseline, current, selected = copy.deepcopy(inputs('58'))
    current['currentProtectedHistory'][field] -= 1
    with pytest.raises(AssertionError):
        subject.verify_final_history_evidence('58', baseline, current, selected)


def test_baseline_bytes_rejected():
    baseline, current, selected = copy.deepcopy(inputs('57'))
    baseline['protectedBytes'] += 1
    with pytest.raises(AssertionError):
        subject.verify_final_history_evidence('57', baseline, current, selected)


def test_original_archived_receipt_bytes_rejected():
    baseline, current, selected = copy.deepcopy(inputs('58'))
    current['currentCustody']['originalArchivedReceiptPin']['sha256'] = '0' * 64
    with pytest.raises(AssertionError):
        subject.verify_final_history_evidence('58', baseline, current, selected)


def test_selected_current_receipt_rejected():
    baseline, current, selected = copy.deepcopy(inputs('59'))
    selected['sha256'] = '0' * 64
    with pytest.raises(AssertionError):
        subject.verify_final_history_evidence('59', baseline, current, selected)
