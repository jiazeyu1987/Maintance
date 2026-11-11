"""Finite publication boundaries using real files/processes from the unpolled case.

The epoch records and owner materials are explicit repository protocol fixtures;
they do not claim a business backup or restore. No owner query is invoked.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend/src/main/resources'), str(Path(__file__).resolve().parent)]
import recovery_control_smallapp_native as native_module
import recovery_control_executor as executor
from recovery_control_smallapp import Failure, Ledger, local_read
from test_automatic_incremental_plan import LocalNative
from test_automatic_incremental_async_closure import overwrite
from test_automatic_incremental_unpolled import UnpolledFixture, unpolled


def assert_originals(f):
    assert executor.pin(f.directory / 'completion.json') == f.completion_pin
    assert executor.pin(f.owner_root / 'result.json') == f.result_pin
    assert not (f.directory / 'queries').exists()


def next_epoch(f):
    path = f.root / 'epochs' / '00000000000000000000.json'
    previous = local_read(path), executor.pin(path)
    replacing = f.metadata.epoch_event(previous, kind='RESTORE_STARTED', state='REPLACING',
                                      operation='protocol-boundary')
    f.metadata.epoch_event(replacing, kind='RESTORE_FINISHED', state='READY',
                           operation='protocol-boundary')


def interrupted_publish(f, monkeypatch, suffix):
    original = native_module.persist
    def stop_after_write(path, value):
        original(path, value)
        if str(path).endswith(suffix):
            raise RuntimeError('PROTOCOL_PUBLICATION_INTERRUPTED')
    with monkeypatch.context() as patch:
        patch.setattr(native_module, 'persist', stop_after_write)
        with pytest.raises(RuntimeError, match='PROTOCOL_PUBLICATION_INTERRUPTED'):
            f.native.publish_point(f.value, f.directory, f.result_pin, f.native.configuration())
    assert not f.registration_paths[0].exists()


def test_successor_control_uses_original_owner_with_same_registry(unpolled):
    f = unpolled
    program = f.root / 'successor-owner.py'
    program.write_text('raise SystemExit(0)\n', encoding='utf-8')
    owner = f.native.document(f.owner_pin)
    owner['sources']['source-A']['captureCommand'] = [sys.executable, str(program)]
    owner_pin = f.metadata.write('successor-owner.json', owner)
    current = f.native.configuration()
    current['sourceConfigurations']['source-A'] = owner_pin
    current['programPins']['REPOSITORY'] = executor.pin(program)
    successor = LocalNative(f.metadata.write('successor-control.json', current))
    assert owner_pin != f.selection['ownerConfigurationPin']
    assert successor.config_pin != f.selection['configurationPin']
    plan = successor.incremental_plan('source-A')
    assert (plan['state'], plan['parentChainRef'], plan['chainDepth']) == ('READY', f.reference, 2), plan
    assert_originals(f)


@pytest.mark.parametrize('suffix', ['/point-epochs/unpolled-i1.json', '/point-binding.json'])
def test_partial_publication_restart_finishes_exact_original(unpolled, monkeypatch, suffix):
    f = unpolled
    interrupted_publish(f, monkeypatch, suffix)
    before = {str(path): executor.pin(path) for path in f.registration_paths if path.exists()}
    plan = LocalNative(f.native.config_pin).incremental_plan('source-A')
    assert plan['state'] == 'READY' and plan['parentChainRef'] == f.reference, plan
    assert all(executor.pin(path) == expected for path, expected in before.items())
    assert all(path.is_file() for path in f.registration_paths)
    assert_originals(f)


@pytest.mark.parametrize('partial', [False, True])
def test_unpublished_success_cannot_cross_epoch(unpolled, monkeypatch, partial):
    f = unpolled
    if partial:
        interrupted_publish(f, monkeypatch, '/point-binding.json')
    next_epoch(f)
    plan = f.native.incremental_plan('source-A')
    assert plan['state'] == 'BLOCKED' and plan['reasonCode'] == 'BACKUP_EPOCH_CHANGED_DURING_CAPTURE', plan
    assert not f.registration_paths[0].exists()
    assert_originals(f)


def test_completed_old_epoch_stays_closed_without_republishing(unpolled, monkeypatch):
    f = unpolled
    f.native.publish_point(f.value, f.directory, f.result_pin, f.native.configuration())
    previous = {str(path): executor.pin(path) for path in f.registration_paths}
    next_epoch(f)
    read = executor.pinned_read
    counts = {'original': 0}
    original_paths = {pin['path'] for pin in f.final['originalResultPins']}
    def measured(path, *args, **kwargs):
        if str(path) in original_paths:
            counts['original'] += 1
        return read(path, *args, **kwargs)
    monkeypatch.setattr(executor, 'pinned_read', measured)
    Ledger(f.root / 'ledger', LocalNative(f.native.config_pin)).require_source_idle('source-A')
    assert counts == {'original': 0}
    assert all(executor.pin(path) == expected for path, expected in previous.items())
    assert_originals(f)


@pytest.mark.parametrize('missing', [1, 2])
def test_selector_without_required_dependency_fails_closed(unpolled, missing):
    f = unpolled
    f.native.publish_point(f.value, f.directory, f.result_pin, f.native.configuration())
    f.registration_paths[missing].unlink()
    selector = executor.pin(f.registration_paths[0])
    plan = f.native.incremental_plan('source-A')
    assert plan['state'] == 'BLOCKED' and plan['reasonCode'] == 'POINT_PUBLICATION_INCOMPLETE', plan
    assert not f.registration_paths[missing].exists()
    assert executor.pin(f.registration_paths[0]) == selector
    assert_originals(f)


@pytest.mark.parametrize('kind', ['binding', 'epoch', 'material'])
def test_conflicting_or_changed_original_prevents_publication(unpolled, monkeypatch, kind):
    f = unpolled
    if kind == 'material':
        Path(f.final['data']['repositoryBindingPin']['path']).write_bytes(b'changed original')
    else:
        interrupted_publish(f, monkeypatch, '/point-binding.json')
        path = f.registration_paths[2 if kind == 'binding' else 1]
        document = local_read(path)
        document['sourceConfigRef'] = 'foreign-source'
        overwrite(path, document)
    plan = f.native.incremental_plan('source-A')
    assert plan['state'] == 'BLOCKED' and plan['parentChainRef'] is None, plan
    assert not f.registration_paths[0].exists()
    assert_originals(f)


def test_successor_cannot_redirect_original_registry(unpolled):
    f = unpolled
    config = f.native.configuration()
    registry = f.root / 'foreign-registry'
    registry.mkdir(mode=0o700)
    config['registryRoot'] = str(registry)
    successor = LocalNative(f.metadata.write('foreign-control.json', config))
    with pytest.raises(Failure, match='SOURCE_POINT_REGISTRY_CHANGED'):
        Ledger(f.root / 'ledger', successor).require_source_idle('source-A')
    assert not any(path.exists() for path in f.registration_paths)
    assert list(registry.iterdir()) == []
    assert_originals(f)


def test_failed_owner_closes_without_publishing_any_point(tmp_path):
    f = UnpolledFixture(tmp_path)
    try:
        f.final.update(state='FAILED_RETAINED', actualExitCode=None, failureCode='CAPTURE_FAILED', data={})
        overwrite(f.owner_root / 'terminal-input.json', f.final)
        f.finish()
        plan = f.native.incremental_plan('source-A')
        assert plan['state'] == 'READY' and plan['parentChainRef'] == 'full-root', plan
        assert not any(path.exists() for path in f.registration_paths)
        assert_originals(f)
    finally:
        f.close()


def test_two_planners_never_return_old_full_during_same_publication(unpolled, monkeypatch):
    f = unpolled
    barrier = threading.Barrier(2)
    method = LocalNative.publish_point
    def synchronized(self, *args, **kwargs):
        barrier.wait(timeout=10)
        return method(self, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(LocalNative, 'publish_point', synchronized)
        with ThreadPoolExecutor(max_workers=2) as pool:
            plans = list(pool.map(lambda _: LocalNative(f.native.config_pin).incremental_plan('source-A'), range(2)))
    assert any(plan['state'] == 'READY' for plan in plans), plans
    for plan in plans:
        assert (plan['state'] == 'READY' and plan['parentChainRef'] == f.reference or
                plan['state'] == 'BLOCKED' and plan['parentChainRef'] is None), plans
    final = LocalNative(f.native.config_pin).incremental_plan('source-A')
    assert final['state'] == 'READY' and final['parentChainRef'] == f.reference, final
    assert all(path.is_file() for path in f.registration_paths)
    assert_originals(f)
