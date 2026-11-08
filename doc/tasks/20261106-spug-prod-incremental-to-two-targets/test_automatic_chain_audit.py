"""Task-helper units use real files; they are not evidence of a live backup."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT / 'scripts/tests'),
               str(ROOT / 'backend/src/main/resources'), str(ROOT / 'ops/recovery')]
from automatic_chain_audit import AuditReader, canonical, check_reader_contract, read_chain, verify_readback, verify_request
from test_automatic_incremental_plan import MetadataFixture, ui_request


def saved(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    path.write_bytes(raw)
    return dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def readback_fixture(tmp_path):
    # The SQL file intentionally does not exist: auditing original read evidence
    # must never open it. Its declared bytes/hash are cross-bound below.
    archive = tmp_path / 'archive'
    payload = dict(path=(archive / 'payload/database.sql.gz').as_posix(), bytes=9000000000, sha256='a' * 64)
    tree = saved(archive, '.repository/tree.json', {'payload': 'directory',
        'payload/database.sql.gz': 'file|9000000000|' + 'a' * 64})
    manifest = dict(backupId='full-1', pointType='FULL', payloadRefs=[payload], payloadTreePin=tree)
    mp = saved(archive, '.repository/manifest.json', manifest)
    retained = saved(tmp_path, 'readback/copy.raw', {'immutable': 'record'})
    originals = saved(tmp_path, 'readback/originals.json', dict(schemaVersion='RepositoryReadbackOriginals/v1',
        manifestPin=mp, archivedFilePins={'payload/database.sql.gz': payload}, readbackOriginalPins={'original.json': retained}))
    native = dict(schemaVersion='RepositoryMinimumReadback/v1', operationId='full-1', manifestPin=mp,
        payloadRefs=[payload], independentConnectionId='independent-connection-1', serverDurabilityVerified=False,
        originalRecordsPin=originals)
    rp = saved(archive, '.repository/readback.json', native)
    point = dict(backupId='full-1', manifestPin=mp, payloadRefs=[payload], readbackEvidencePin=rp)
    return point, manifest, native, originals


def test_readback_audits_full_content_records_without_opening_payload(tmp_path):
    point, manifest, _, _ = readback_fixture(tmp_path)
    reader = AuditReader()
    result = verify_readback(reader, point, manifest)
    reader.finish()
    assert result['payloadContentVerified'] and result['payloadBytes'] == 9000000000
    assert result['extraFullPayloadReadDispatched'] is False
    assert not Path(manifest['payloadRefs'][0]['path']).exists()


@pytest.mark.parametrize('change', ['lightweight', 'wrong-payload', 'wrong-manifest', 'missing-copy', 'wrong-tree'])
def test_readback_rejects_incomplete_or_unbound_originals(tmp_path, change):
    point, manifest, native, originals = readback_fixture(tmp_path)
    if change == 'lightweight': native['payloadContentVerified'] = False
    elif change == 'wrong-payload': native['payloadRefs'] = []
    elif change == 'wrong-manifest': native['manifestPin'] = dict(native['manifestPin'], sha256='0' * 64)
    elif change == 'missing-copy':
        value = json.loads(Path(originals['path']).read_text())
        Path(next(iter(value['readbackOriginalPins'].values()))['path']).unlink()
    else: manifest['payloadTreePin'] = saved(tmp_path, 'wrong-tree.json', {})
    point['readbackEvidencePin'] = saved(tmp_path, 'changed-readback.json', native)
    with pytest.raises((ValueError, OSError)):
        verify_readback(AuditReader(), point, manifest)


def test_reader_rejects_changed_pins_and_rechecks_file_identity(tmp_path):
    pin = saved(tmp_path, 'record.json', {'before': True})
    reader = AuditReader(); reader.document(pin)
    Path(pin['path']).write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='AUDIT_INPUT_CHANGED'): reader.finish()
    with pytest.raises(ValueError, match='AUDIT_INPUT_CHANGED'): reader.local_pin(pin['path'])
    with pytest.raises(ValueError, match='AUDIT_PIN_CHANGED'): AuditReader().document(pin)


def test_reader_bounds_input_before_read(tmp_path):
    path = tmp_path / 'large.json'
    with path.open('wb') as stream: stream.truncate(64 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match='AUDIT_METADATA_LIMIT'):
        AuditReader().local(path)


def test_actual_standard_reader_contract_and_lightweight_refusal():
    package = Path('C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/package-0d44578/backup-restore-standard.tgz')
    with tarfile.open(package) as archive:
        caller = archive.extractfile('common/repository_minimal.py').read()
        reader = archive.extractfile('common/repository_native_readback.py').read()
    assert check_reader_contract(caller, reader)
    with pytest.raises(ValueError, match='AUDIT_FULL_SAFE_READER_REQUIRED'):
        check_reader_contract((ROOT / 'ops/recovery/repository_minimal.py').read_bytes(), reader)


def chain_fixture(tmp_path):
    f = MetadataFixture(tmp_path)
    f.enable_epoch(); f.epoch_event()
    f.point('full-1', source_restored=False); f.bind_epoch('full-1')
    for ref, parents, finished in [('inc-1', ['full-1'], '2026-11-07T01:01:00Z'),
                                   ('inc-2', ['full-1', 'inc-1'], '2026-11-07T01:02:00Z')]:
        f.point(ref, parents, finished=finished, source_restored=False)
        operation = tmp_path / 'epoch-publications' / ref
        saved(operation, 'selection.json', dict(sourceEpoch=f.native.source_epoch(f.native.configuration(), 'source-A')))
        binding = f.native.document(f.points[ref]['controlPin'])
        f.native.publish_point_epoch(ui_request(ref, parent=parents[-1]), operation,
                                    binding['resultPin'], f.native.configuration())
    return f


def test_real_metadata_full_and_two_incremental_prefixes(tmp_path):
    f = chain_fixture(tmp_path)
    for refs in (['full-1'], ['full-1', 'inc-1'], ['full-1', 'inc-1', 'inc-2']):
        reader = AuditReader()
        rows, epoch = read_chain(reader, f.native.configuration(), 'source-A', refs)
        assert list(rows) == refs and epoch['state'] == 'READY'
        reader.finish()


@pytest.mark.parametrize('change', ['wrong-prefix', 'missing-epoch', 'wrong-epoch'])
def test_real_metadata_chain_rejects_wrong_prefix_or_epoch(tmp_path, change):
    f = chain_fixture(tmp_path); refs = ['full-1', 'inc-1', 'inc-2']
    if change == 'wrong-prefix': refs = ['full-1', 'inc-2']
    else:
        path = tmp_path / 'registry/point-epochs/inc-2.json'
        if change == 'missing-epoch': path.unlink()
        else:
            value = json.loads(path.read_text()); value['epochId'] = '0' * 64
            path.write_text(json.dumps(value), encoding='utf-8')
    with pytest.raises(Exception): read_chain(AuditReader(), f.native.configuration(), 'source-A', refs)


@pytest.mark.parametrize('action', ['FULL', 'INCREMENTAL'])
def test_request_verification_uses_pure_production_binder_without_rewriting_files(tmp_path, action):
    from recovery_control_capture_config import bind_documents
    f = chain_fixture(tmp_path)
    config = f.native.configuration(); config['taskRoot'] = str(tmp_path)
    reader = AuditReader(); rows, _ = read_chain(reader, config, 'source-A', ['full-1'])
    operation = 'new-full' if action == 'FULL' else 'new-inc'
    request = ui_request(operation, parent=None if action == 'FULL' else 'full-1')
    objects_pin = saved(tmp_path, 'base-objects.json', dict(parentExportIndexPin=None))
    capture = dict(sourceConfigRef='source-A', source=dict(sourceIdentity='identity-A',
        databaseUuid=rows['full-1']['captured']['databaseEnd']['databaseUuid'], objectSourcePin=objects_pin,
        materialPins=[dict(purpose='mysqlbinlog-exporter')]))
    capture_pin = saved(tmp_path, 'base-capture.json', capture)
    owner = dict(operationRoot=str(tmp_path / 'repository-operations'), sources={'source-A': dict(configurationPath=capture_pin['path'])})
    owner_pin = saved(tmp_path, 'base-owner.json', owner)
    config['sourceConfigurations']['source-A'] = owner_pin
    config['programPins']['repository'] = saved(tmp_path, 'program.json', {'program': 'test only'})
    old = rows['full-1']; old_binding = reader.document(old['output']['data']['repositoryBindingPin'])
    parent = None
    if action == 'INCREMENTAL':
        old_binding['objectContentIndexPin'] = saved(tmp_path, 'parent-objects.json', {'parent': 'index'})
        # These fixture mutations are explicit test input setup, never live evidence.
        saved(Path(old['output']['data']['repositoryBindingPin']['path']).parent,
              'repository-binding.json', old_binding)
        old['output']['data']['repositoryBindingPin'] = AuditReader().local_pin(
            Path(old['output']['data']['repositoryBindingPin']['path']))
        parent = dict(reference='full-1', sourceConfigRef='source-A', point=old['point'], pointPin=old['pointPin'],
            capturePoint=old['captured'], binding=old_binding, material=reader.document(old_binding['recoveryMaterialPin']))
    repository, derived_capture, objects = bind_documents(request, owner, capture, {'parentExportIndexPin': None}, parent)
    root = tmp_path / 'request-configurations' / operation
    saved(root, 'request-inputs.json', dict(request=request, ownerConfigurationPin=owner_pin,
        captureConfigurationPin=capture_pin, objectSourcePin=objects_pin,
        pointBindingPin=None if parent is None else old['bindingPin']))
    derived_capture['source']['objectSourcePin'] = saved(root, 'objects.json', objects)
    cp = saved(root, 'capture.json', derived_capture)
    repository['sources']['source-A']['configurationPath'] = cp['path']
    selected = dict(ownerConfigurationPin=saved(root, 'repository.json', repository),
                    ownerProgramPin=config['programPins']['repository'],
                    pointBindingPin=None if parent is None else old['bindingPin'])
    ledger = Path(config['ledgerRoot']) / operation
    saved(ledger, 'request.json', request); saved(ledger, 'selection.json', selected)
    saved(ledger, 'intent.json', dict(operationId=operation, requestSha256=hashlib.sha256(canonical(request)).hexdigest(), selection=selected))
    before = {p: p.read_bytes() for p in tmp_path.rglob('*.json')}
    fresh = AuditReader(); verify_request(fresh, config, request, rows); fresh.finish()
    assert {p: p.read_bytes() for p in tmp_path.rglob('*.json')} == before
    bad = json.loads((root / 'capture.json').read_text()); bad['parent'] = {'untrusted': True}
    saved(root, 'capture.json', bad)
    with pytest.raises(ValueError, match='AUDIT_CAPTURE_REQUEST_CHANGED'):
        verify_request(AuditReader(), config, request, rows)
