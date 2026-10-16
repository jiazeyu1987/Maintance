"""Stage checks remain fail-closed; file/row loops use the lightweight guard."""
from pathlib import Path
import json
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops/recovery'))
from recovery_engine import Budget, RecoveryError, pin, write
from recovery_minimal_runtime import MinimalData
import recovery_data_files as files
import recovery_data_objects as objects


@pytest.mark.parametrize('count', [1, 40])
@pytest.mark.parametrize('fail_at', [None, 2, 3])
def test_physical_loop_checks_stages_not_each_file(tmp_path, monkeypatch, count, fail_at):
    root = tmp_path/'target'; root.mkdir()
    evidence = tmp_path/'evidence'; evidence.mkdir()
    payload = tmp_path/'payload'; payload.write_bytes(b'checked bytes')
    ref = pin(payload)
    after = {f'file-{i}': dict(kind='file', bytes=ref['bytes'], sha256=ref['sha256']) for i in range(count)}
    n = MinimalData.__new__(MinimalData)
    n.root = evidence; n.chain = []; n.original_pins = []; n.mutation_dispatched = False
    n.policy = dict(bucketMapping={'bucket':'bucket'}, minioDataMount='/data', minioFileOwnership=None)
    n.config_services = {'minio': {'id':'storage'}}; n.config = {'buckets':['bucket']}
    n.budget = Budget(10000); n.plan = {'recoveryPoint':'point'}
    versions = tmp_path/'versions'; versions.write_bytes(b'')
    n.material = {'objects': {'inventoryPin': pin(versions)}}
    checks = []; light = []; starts = []
    def bound(**kwargs):
        checks.append(kwargs)
        if len(checks) == fail_at:
            raise RecoveryError('TARGET_FIREWALL_CHANGED')
    n.bound = bound
    n.guard = lambda: light.append(n.budget.remaining())
    n.inspect = lambda identity: {'Id':identity, 'Mounts':[dict(Destination='/data', Type='volume', RW=True, Name='owned', Source=str(root))]}
    def docker(argv, **kwargs):
        if argv[0] == 'volume':
            return json.dumps([dict(Driver='local', Options=None, Mountpoint=str(root))]).encode()
        if argv[0] == 'ps': return b'storage\n'
        assert argv == ['start', 'storage']; starts.append(True); return b''
    n.docker = docker; n.wait_healthy = lambda role: None; n.object_client = lambda: None
    n.check_bucket_permissions = lambda: write(evidence/'permissions.json', {})
    def export(*args, guard, **kwargs):
        for _ in range(count): guard()
        return {}
    n.modules = {'formal_s3_export':SimpleNamespace(export_s3_versions=export), 'formal_physical_restore_readback':object()}
    monkeypatch.setattr(files, 'physical_chain_inputs', lambda chain: [(ref, {}, after, {key:ref for key in after}, list(after), [])])
    def compare(chain, policy, root, export, module, guard):
        for _ in range(count): guard()
        return {'matched':True}
    monkeypatch.setattr(objects, 'compare_indexed_restore', compare)
    if fail_at:
        with pytest.raises(RecoveryError, match='TARGET_FIREWALL_CHANGED'): n.physical_object_chain()
        assert not starts
        assert len(list(root.iterdir())) == (0 if fail_at == 2 else count)
        assert not (evidence/'physical-step-000-readback.json').exists()
    else:
        result = n.physical_object_chain()
        assert len(checks) == 7 and len(light) > count
        assert len(list(root.iterdir())) == count and starts == [True]
        assert result['originalVersionIdsPreserved'] is True


@pytest.mark.parametrize('fail_after', [False, True])
def test_database_observation_rows_keep_light_guard(tmp_path, fail_after):
    n = MinimalData.__new__(MinimalData); n.root = tmp_path; n.mysql = object(); n.db_uuid = 'uuid'
    n.config = {'database':'db'}; n.policy = {'dataLimits':{'seconds':10}}; n.budget = Budget(10000)
    n.material = {'recoveryPoint':'point', 'database':{'expectedDataPin':write(tmp_path/'expected.json', {}), 'endPosition':{}}}
    checks = []; light = []
    def bound():
        checks.append(True)
        if fail_after and len(checks) == 2: raise RecoveryError('TARGET_CHANGED_OR_EXPOSED')
    def observe(*args, guard, **kwargs):
        for _ in range(100): guard()
        return {}
    n.bound = bound; n.guard = lambda: light.append(n.budget.remaining())
    n.modules = {'formal_data_evidence':SimpleNamespace(validate_limits=dict, observe_data=observe, compare_data=lambda a,b:{})}
    if fail_after:
        with pytest.raises(RecoveryError, match='TARGET_CHANGED_OR_EXPOSED'): n.database_readback()
    else:
        assert n.database_readback()['fullSchemaDataEquivalenceVerified'] is True
    assert len(checks) == 2 and len(light) == 100
