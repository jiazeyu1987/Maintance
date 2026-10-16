"""Actual task-owned file full/delta copying, deletions and readback."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops'/'recovery'))
from recovery_engine import RecoveryError, pin
from recovery_data_files import apply_tree, inventory, relative, tree_delta, physical_chain_inputs
from recovery_engine import write


def file_entry(ref):
    return dict(kind='file', bytes=ref['bytes'], sha256=ref['sha256'])


def test_full_then_delta_preserves_content_and_applies_deletion(tmp_path):
    source = tmp_path/'source'; source.mkdir(); root = tmp_path/'target'; root.mkdir()
    (source/'one').write_bytes(b'full one'); (source/'two').write_bytes(b'full two')
    one, two = pin(source/'one'), pin(source/'two')
    full = {'assets': {'kind':'directory'}, 'assets/one':file_entry(one), 'assets/two':file_entry(two)}
    assert apply_tree(root, {}, full, {'assets/one':one,'assets/two':two}, full=True, guard=lambda:None)['completeTreeReadback']
    (source/'three').write_bytes(b'incremental content'); three = pin(source/'three')
    delta = {'assets':{'kind':'directory'}, 'assets/one':file_entry(one), 'assets/three':file_entry(three)}
    result = apply_tree(root, full, delta, {'assets/three':three}, full=False, guard=lambda:None)
    assert result['changedFileCount'] == 1 and result['deletedPathCount'] == 1
    assert inventory(root, lambda:None) == delta and (root/'assets/one').read_bytes() == b'full one'
    assert not (root/'assets/two').exists()


@pytest.mark.parametrize('path', ['../source', '/absolute', 'a/../b', 'a\\b', 'a//b', './a'])
def test_untrusted_relative_paths_cannot_escape(path):
    with pytest.raises(RecoveryError, match='FILE_RELATIVE_PATH_INVALID'): relative(path)


def test_delta_rejects_unowned_existing_file_before_writes(tmp_path):
    root = tmp_path/'target'; root.mkdir(); (root/'foreign').write_bytes(b'preserve')
    with pytest.raises(RecoveryError, match='OFFLINE_TARGET_TREE_CHANGED'):
        apply_tree(root, {}, {}, {}, full=True, guard=lambda:None)
    assert (root/'foreign').read_bytes() == b'preserve'


def test_delta_rejects_changed_payload_before_target_writes(tmp_path):
    root = tmp_path/'target'; root.mkdir(); source=tmp_path/'source'; source.write_bytes(b'approved')
    ref = pin(source); expected={'file':file_entry(ref)}; source.write_bytes(b'tampered')
    with pytest.raises(RecoveryError, match='PIN_CHANGED'):
        apply_tree(root, {}, expected, {'file':ref}, full=True, guard=lambda:None)
    assert list(root.iterdir()) == []


def test_type_replacements_remove_deep_children_before_rebuild(tmp_path):
    root=tmp_path/'target'; root.mkdir(); content=tmp_path/'content'; content.write_bytes(b'version'); ref=pin(content)
    first={'node':file_entry(ref)}
    second={'node':{'kind':'directory'}, 'node/child':{'kind':'directory'}, 'node/child/file':file_entry(ref)}
    assert tree_delta(first, second) == (['node','node/child','node/child/file'], ['node'])
    assert tree_delta(second, first) == (['node'], ['node/child/file','node/child','node'])
    apply_tree(root, {}, first, {'node':ref}, full=True, guard=lambda:None)
    apply_tree(root, first, second, {'node/child/file':ref}, full=False, guard=lambda:None)
    apply_tree(root, second, first, {'node':ref}, full=False, guard=lambda:None)
    assert inventory(root, lambda:None) == first and (root/'node').read_bytes() == b'version'


def test_chain_precheck_rejects_missing_type_tombstone_before_any_target_change(tmp_path):
    content=tmp_path/'content'; content.write_bytes(b'v'); ref=pin(content)
    first={'node':file_entry(ref)}; second={'node':{'kind':'directory'}}
    def step(number, expected, changed, deleted, payloads):
        point={'pointType':'FULL' if number == 0 else 'INCREMENTAL'}
        cap=write(tmp_path/('capture-%d.json'%number), dict(commonRecoveryPoint=str(number), pointType=point['pointType'],
                  fileInventory=expected, fileDelta=dict(changedPaths=changed, deletedPaths=deleted)))
        descriptor=dict(capturePointPin=cap,fileInventoryPin=write(tmp_path/('inventory-%d.json'%number),expected),filePayloadPins=payloads)
        return (None, point, dict(objects=descriptor,recoveryPoint=str(number),payloadPins=list(payloads.values())),None)
    chain=[step(0,first,['node'],[],{'node':ref}),step(1,second,['node'],[],{})]
    target=tmp_path/'target'; target.mkdir(); (target/'preserved').write_bytes(b'unchanged')
    with pytest.raises(RecoveryError,match='CAPTURED_FILE_DELTA_MISMATCH'): physical_chain_inputs(chain)
    assert (target/'preserved').read_bytes() == b'unchanged'
