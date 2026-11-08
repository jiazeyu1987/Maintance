"""Fault injection for the switch transaction; real Engine coverage is separate."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops/recovery'))
import recovery_backup_epoch as epochs
from recovery_engine import RecoveryError
from recovery_program_containers import switch_stopped_programs
from test_recovery_program_containers import original, image


class Engine:
    def __init__(self, originals):
        self.rows = {row['Id']: deepcopy(row) for row in originals.values()}
        self.actions = []
        self.fail_on = None
        self.bad_created = False
        self.counter = 0

    def inspect(self, identity):
        return deepcopy(self.rows[identity])

    def image(self, identity):
        return image()

    def metadata(self):
        return {'OperatingSystem': 'Linux'}

    def network(self, identity):
        return dict(Id=identity, Name='task-network')

    def request(self, method, path, body=None):
        self.actions.append((method, path, body))
        if self.fail_on == len(self.actions): raise TimeoutError('unobserved daemon outcome')
        if '/rename?' in path:
            self.rows[path.split('/')[2]]['Name'] = '/'+path.split('name=')[1]
        elif path.endswith('/disconnect'):
            self.rows[body['Container']]['NetworkSettings']['Networks'] = {}
        elif path.startswith('/containers/create?'):
            self.counter += 1
            identity = ('c' if self.counter == 1 else 'd')*64
            row = original()
            row.update(Id=identity, Name='/'+path.split('name=')[1], Image=image()['Id'],
                Config={k: deepcopy(v) for k, v in body.items() if k not in ('HostConfig','NetworkingConfig')},
                HostConfig=deepcopy(body['HostConfig']))
            row['NetworkSettings']['Networks']['task-network'].update(
                body['NetworkingConfig']['EndpointsConfig']['task-network'])
            if self.bad_created: row['Image'] = 'sha256:'+'0'*64
            self.rows[identity] = row
            return dict(Id=identity, Warnings=[])


@pytest.fixture
def case(tmp_path, monkeypatch):
    originals = {role: original() for role in ('backend', 'frontend')}
    originals['frontend'].update(Id='b'*64, Name='/program-frontend')
    originals['frontend']['NetworkSettings']['Networks']['task-network']['Aliases'] = ['program-frontend', 'b'*12]
    engine = Engine(originals)
    program = dict(schemaVersion='ArchivedProgramImages/v1', archivePin=None,
        images=[dict(role=r,imageId=image()['Id'],os='linux',architecture='amd64',diffIds=[]) for r in originals])
    monkeypatch.setattr(epochs, '_assert_lock', lambda *args: None)
    monkeypatch.setattr(epochs, 'read_current', lambda _: dict(state='REPLACING',operationId='test-program-switch'))
    return dict(originals=originals,program=program,engine=engine,guard=lambda:None,
        journal=tmp_path,operation_id='test-program-switch',epoch_policy={},lock_fd=42)


def test_switch_returns_only_after_two_new_and_two_retained_proved(case):
    result = switch_stopped_programs(**case)
    assert len(result['replacements']) == 2
    assert len(case['engine'].rows) == 4
    assert all(not row['State']['Running'] for row in case['engine'].rows.values())
    assert json.loads((case['journal']/'result.json').read_text(encoding='utf-8'))['state'] == 'CREATED_STOPPED'
    assert all(method == 'POST' and '/start' not in path for method,path,_ in case['engine'].actions)


@pytest.mark.parametrize('stage', range(1,7))
def test_each_partial_mutation_retains_failure_without_cleanup_or_retry(case,stage):
    case['engine'].fail_on = stage
    with pytest.raises(TimeoutError): switch_stopped_programs(**case)
    assert (case['journal']/'intent.json').is_file()
    failure = json.loads((case['journal']/'failure.json').read_text(encoding='utf-8'))
    assert failure['attemptedMutations'] == stage
    assert not (case['journal']/'result.json').exists()
    assert len(case['engine'].actions) == stage
    with pytest.raises(RecoveryError,match='PROGRAM_SWITCH_ALREADY_CLAIMED'):
        switch_stopped_programs(**case)
    assert len(case['engine'].actions) == stage


def test_loaded_image_mismatch_refused_before_any_mutation(case):
    case['program']['images'][0]['diffIds'] = ['sha256:'+'3'*64]
    with pytest.raises(RecoveryError,match='PROGRAM_LOADED_IMAGE_CHANGED'):
        switch_stopped_programs(**case)
    assert not case['engine'].actions
    assert not list(case['journal'].iterdir())


def test_changed_original_refused_before_any_mutation(case):
    case['engine'].rows['b'*64]['Config']['Env'] = ['APP=changed']
    with pytest.raises(RecoveryError,match='PROGRAM_ORIGINAL_CHANGED'):
        switch_stopped_programs(**case)
    assert not case['engine'].actions


def test_wrong_epoch_operation_is_refused(case,monkeypatch):
    monkeypatch.setattr(epochs,'read_current',lambda _:dict(state='REPLACING',operationId='another-operation'))
    with pytest.raises(RecoveryError,match='PROGRAM_REPLACEMENT_EPOCH_REQUIRED'):
        switch_stopped_programs(**case)
    assert not case['engine'].actions


def test_lock_loss_stops_before_next_mutation(case,monkeypatch):
    def lock(*args):
        if case['engine'].actions: raise ValueError('BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED')
    monkeypatch.setattr(epochs,'_assert_lock',lock)
    with pytest.raises(ValueError,match='BACKUP_EPOCH_EXCLUSIVE_LOCK_REQUIRED'):
        switch_stopped_programs(**case)
    assert len(case['engine'].actions) == 1
    assert not (case['journal']/'result.json').exists()


def test_unexpected_created_image_retains_resources_and_failure(case):
    case['engine'].bad_created = True
    with pytest.raises(RecoveryError,match='PROGRAM_CREATED_IDENTITY_CHANGED'):
        switch_stopped_programs(**case)
    assert len(case['engine'].rows) == 3
    assert (case['journal']/'failure.json').exists()
    observed = json.loads((case['journal']/'frontend-created-observation.json').read_text(encoding='utf-8'))
    assert observed['Image'] == 'sha256:'+'0'*64
    assert not (case['journal']/'result.json').exists()


def test_writer_resuming_after_preflight_blocks_first_mutation(case):
    def guard():
        if (case['journal']/'intent.json').exists():
            case['engine'].rows['a'*64]['State']['Running'] = True
    case['guard'] = guard
    with pytest.raises(RecoveryError,match='PROGRAM_ORIGINAL_NOT_STOPPED'):
        switch_stopped_programs(**case)
    assert case['engine'].actions == []
