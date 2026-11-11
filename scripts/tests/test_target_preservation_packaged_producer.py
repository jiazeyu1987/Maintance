"""One actual STANDARD producer node; external service protocols are finite.

The existing MinimalData protocol subclass remains an explicit external seam.
This is not a real business restore, a CIFS test, or a deployment qualification.
"""
import base64
import gzip
import hashlib
import importlib
import io
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse

import pytest

from test_recovery_target_preservation_producer import (
    preservation_producer_case, handoff_case, publication_case, capture_protocol,
    original_capture_protocol, case, restore_case,
    test_main_producer_preserves_before_import_then_restores_and_validates_history as _original_positive)
from recovery_engine import pin, pinned_json


pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'),
    reason='actual Linux flock, exporter and SQL child processes required')

OBJECT = b'finite packaged MAIN object version; actual signed GET bytes\n'
KEY = 'packaged-main/finite-object'
VERSION = 'finite-version-1'
ETAG = '"'+hashlib.md5(OBJECT).hexdigest()+'"'
SIDECARS = {'payload-tree.json', 'manifest.json', 'recovery-material.json',
    'object-content-index.json', 'readback-original.json', 'archive-close.json',
    'capture-terminal.json', 'preservation-point.json', 'recovery-repository-binding.json'}


class _Response(io.BytesIO):
    status = 200

    def __init__(self, raw, headers=None):
        super().__init__(raw)
        self.headers = dict(headers or {})


def _raw_s3_protocol(monkeypatch, events):
    """Only the external open boundary changes; actual signed GET/parsers run."""
    from formal_s3_export import ReadOnlyS3
    import minimal_capture_support as support

    class RawByteS3(ReadOnlyS3):
        def _open(self, request):
            parsed = urllib.parse.urlsplit(request.full_url)
            assert request.get_method() == 'GET'
            assert parsed.scheme+'://'+parsed.netloc == self.endpoint
            assert parsed.path in ('/private', '/private/'+KEY)
            assert request.get_header('Authorization').startswith('AWS4-HMAC-SHA256 ')
            query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            if parsed.path == '/private' and query == {
                    'versions':[''], 'encoding-type':['url'], 'max-keys':['1000']}:
                events.append('versions')
                raw = ('<ListVersionsResult><IsTruncated>false</IsTruncated><Version>'
                    '<Key>'+urllib.parse.quote(KEY, safe='')+'</Key><VersionId>'+VERSION+'</VersionId>'
                    '<IsLatest>true</IsLatest><LastModified>2026-11-10T00:00:00Z</LastModified>'
                    '<Size>'+str(len(OBJECT))+'</Size><ETag>'+ETAG+'</ETag>'
                    '</Version></ListVersionsResult>').encode()
                return _Response(raw)
            if parsed.path == '/private' and query == {'uploads':[''], 'max-uploads':['1']}:
                events.append('multipart')
                return _Response(b'<ListMultipartUploadsResult><Bucket>private</Bucket>'
                    b'<MaxUploads>1</MaxUploads><IsTruncated>false</IsTruncated></ListMultipartUploadsResult>')
            if parsed.path == '/private/'+KEY and query == {'versionId':[VERSION]}:
                events.append('content')
                return _Response(OBJECT, {'content-length':str(len(OBJECT)), 'etag':ETAG,
                    'content-type':'application/octet-stream', 'x-amz-version-id':VERSION})
            codes = {'lifecycle':'NoSuchLifecycleConfiguration',
                'replication':'ReplicationConfigurationNotFoundError',
                'encryption':'ServerSideEncryptionConfigurationNotFoundError'}
            if parsed.path == '/private' and len(query) == 1:
                name = next(iter(query))
                assert name in codes and query[name] == [''], 'UNEXPECTED_SIGNED_S3_QUERY'
                events.append('absence:'+name)
                raw = ('<Error><Code>'+codes[name]+'</Code></Error>').encode()
                raise urllib.error.HTTPError(request.full_url, 404, 'finite expected absence',
                    {}, io.BytesIO(raw))
            raise AssertionError('UNEXPECTED_SIGNED_S3_REQUEST')

    for method in ('versions', 'content', 'multipart_empty', 'absent_configuration', '_get'):
        assert getattr(RawByteS3, method) is getattr(ReadOnlyS3, method)
    monkeypatch.setattr(support, 'ReadOnlyS3', RawByteS3)


def _metadata(reference, raw_files):
    path = Path(reference['path'])
    raw = path.read_bytes()
    assert len(raw) <= 16*1024*1024
    assert pin(path) == reference
    raw_files[str(path)] = dict(pin=reference, rawBase64=base64.b64encode(raw).decode('ascii'))
    return json.loads(raw)


def test_actual_standard_main_producer_archive_clear_and_history(preservation_producer_case,
        monkeypatch, capsys):
    h = preservation_producer_case
    events, observations, raw_files = [], [], {}
    _raw_s3_protocol(monkeypatch, events)
    preservation = importlib.import_module('recovery_target_preservation')
    replacement = importlib.import_module('recovery_replace')
    original_publish = preservation.TargetPreservation.capture_and_publish
    original_clear = replacement.clear
    archive_pin = None

    def archived(publication):
        nonlocal archive_pin
        archive_pin = original_publish(publication)
        proof = _metadata(archive_pin, raw_files)
        assert proof['state'] == 'ARCHIVED_VERIFIED' and proof['payloadContentVerified'] is True
        assert proof['serverDurabilityVerified'] is proof['independentFailureDomain'] is False
        assert publication.session._state == 'MATERIAL_COMPLETE'
        assert publication.context is h.natives[0].native_context._context
        assert publication.context.phase == 'PREPARATION'
        assert publication.context.generation_pin is None
        assert getattr(publication, '_final', None) is None
        assert not (publication.root/'preservation.json').exists()
        assert h.handoff_dispatches == 0 and not h.sql_inputs and not h.original_execute_calls
        assert not h.loaded and not any('/containers/create?' in row[1] for row in h.engine.actions)
        assert not publication.native.storage_running and not publication.native.running_applications
        state = json.loads(h.state_path.read_bytes())
        assert state['flags'] == ['1','1'] and h.transport.scheduler == 'OFF'
        assert not h.transport.releases
        assert publication.context._epoch['state'] == 'REPLACING'
        materials = _metadata(proof['materialsPin'], raw_files)
        assert materials['sourceRestored'] is False and materials['writersRemainQuiesced'] is True
        data = materials['materials']
        inputs = _metadata(data['captureInputsPin'], raw_files)
        tree = _metadata(proof['payloadTreePin'], raw_files)
        assert _metadata(data['archiveEntriesPin'], raw_files) == tree
        point = _metadata(proof['pointPin'], raw_files)
        manifest = _metadata(proof['manifestPin'], raw_files)
        assert point['role'] == 'TARGET_PRE_RESTORE' and point['pointType'] == 'FULL'
        assert point['payloadRefs'] == manifest['payloadRefs'] and point['parentPointPins'] == []
        assert _metadata(data['capturePointPin'], raw_files)['sourceRestored'] is False
        assert inputs['pointType'] == 'FULL'
        assert {Path(p['path']).relative_to(publication.archive).as_posix() for p in point['payloadRefs']} == {
            name for name, marker in tree.items() if marker != 'directory'}
        # Observe exact closed membership and existing length/hash bindings;
        # do not repeat full payload hashing while writers are stopped.
        actual = {p.relative_to(publication.archive).as_posix() for p in publication.archive.rglob('*')
            if '.repository' not in p.relative_to(publication.archive).parts}
        assert actual == set(tree)
        for reference in point['payloadRefs']:
            path = Path(reference['path']); name = path.relative_to(publication.archive).as_posix()
            assert path.stat().st_size == reference['bytes']
            assert tree[name] == 'file|'+str(reference['bytes'])+'|'+reference['sha256']
        assert {p.name for p in (publication.archive/'.repository').iterdir()} == SIDECARS
        reads = set(h.smb_protocol.reads)
        assert {Path(p['path']) for p in point['payloadRefs']} <= reads
        assert {publication.archive/'.repository'/name for name in SIDECARS} <= reads
        assert len(h.smb_protocol.registrations) >= 2
        readback = _metadata(proof['readbackPin'], raw_files)
        assert readback['payloadContentVerified'] is True
        sidecars = _metadata(proof['sidecarReadbackPin'], raw_files)
        assert sidecars['independentConnectionId'] == readback['independentConnectionId']
        terminal = _metadata(proof['captureTerminalPin'], raw_files)
        assert terminal['sourceRestored'] is False and terminal['writersRemainQuiesced'] is True
        hold = publication.configuration.root/'.repository-control'/'preservation-holds'/(h.request['operationId']+'.json')
        assert _metadata(pin(hold), raw_files)['archiveProofPin'] == archive_pin
        _metadata(proof['holdIntentPin'], raw_files)
        assert gzip.decompress((publication.archive/'payload'/'database.sql.gz').read_bytes()).startswith(b'-- finite SQL protocol')
        assert any(name.startswith('payload/minio-physical/') and marker.startswith('file|') for name, marker in tree.items())
        assert any('redis' in name.lower() and marker.startswith('file|') for name, marker in tree.items())
        images = json.loads((publication.archive/'payload'/'050-original-images.json').read_bytes())
        assert set(images['imageIds']) == set(h.images.values()) and len(images['imageIds']) == 5
        assert events.count('content') >= 2 and events.count('versions') >= 2
        assert events.count('multipart') >= 2
        observations.append(dict(stage='ARCHIVED_BEFORE_HANDOFF', archiveProofPin=archive_pin,
            payloads=len(point['payloadRefs']), sidecars=len(SIDECARS), flags=state['flags'],
            sourceRestored=False, handoffCount=h.handoff_dispatches, loadedImages=len(h.loaded)))
        return archive_pin

    def clearing(native, value):
        context = native.native_context._context
        publication = context._target_preservation
        assert len(observations) == 1 and archive_pin == publication._proof
        assert native.native_context.phase == 'RESTORE' and context.generation_pin is not None
        assert publication is h.natives[0].native_context._context._target_preservation
        assert type(publication._final) is preservation.VerifiedTargetPreservation
        assert h.original_execute_calls[-1][1]['target_preservation'] is publication._final
        assert h.handoff_dispatches == 1 and not h.sql_inputs
        assert json.loads(h.state_path.read_bytes())['flags'] == ['0','0']
        assert h.transport.scheduler == 'OFF' and not h.transport.releases
        assert not native.running_applications and not publication._repository_lock.stream.closed
        final = _metadata(publication._final.reference, raw_files)
        assert final['archiveProofPin'] == archive_pin
        observations.append(dict(stage='FIRST_CLEAR_AFTER_TYPED_HANDOFF',
            targetPreservationPin=publication._final.reference, generationPin=context.generation_pin,
            phase=native.native_context.phase, handoffCount=h.handoff_dispatches))
        return original_clear(native, value)

    monkeypatch.setattr(preservation.TargetPreservation, 'capture_and_publish', archived)
    monkeypatch.setattr(replacement, 'clear', clearing)
    returned = False
    try:
        # Includes real worker/receipt, SQL subprocess/cleanup, resource close,
        # both historical validators and intentional payload-drift rejection.
        _original_positive(h)
        returned = True
        assert [row['stage'] for row in observations] == [
            'ARCHIVED_BEFORE_HANDOFF', 'FIRST_CLEAR_AFTER_TYPED_HANDOFF']
    finally:
        raw = json.dumps(dict(schemaVersion='PackagedMainProducerWitness/v1',
            actualBusinessRestore=False, originalPositiveReturned=returned,
            observations=observations, rawS3Events=events, objectSha256=hashlib.sha256(OBJECT).hexdigest(),
            rawFiles=list(raw_files.values())), sort_keys=True, separators=(',',':')).encode()
        with capsys.disabled():
            print('\nPACKAGED_MAIN_PRODUCER_WITNESS_BASE64='+base64.b64encode(raw).decode('ascii'), flush=True)
