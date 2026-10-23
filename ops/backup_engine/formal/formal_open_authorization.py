"""Independent original-OPEN approval verification; no consume or OPEN author.

Only the executor's explicit, independently trusted SPKI key/SHA select trust.
Ed25519 via the approved native OpenSSL is mandatory. All returned identities
are signed; a valid signature alone never authorizes a service start or replay.
"""
import base64
import binascii
import fcntl
import hashlib
import json
import os
import re
import subprocess
import time

from formal_boot_state import ROLES, _read_secure
from formal_filesystem_watchdog import require_native_runtime
from formal_snapshot_linux import FormalSnapshotError, observation_timeout, require

OPENSSL = '/usr/bin/openssl'
SPKI_PREFIX = bytes.fromhex('302a300506032b6570032100')
BINDING_KEYS = {'operationId', 'role', 'hostBootId', 'containerId', 'launchSha256',
                'artifactSha256', 'originalOpenSha256', 'closedSha256'}
PAYLOAD_KEYS = BINDING_KEYS | {'purpose', 'grantId', 'actorId', 'tenantId', 'issuedAt', 'expiresAt'}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _hex(value, length=64):
    return type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}', value) is not None


def _json(raw, code):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, code)
            result[key] = value
        return result
    def constant(_):
        raise FormalSnapshotError(code)
    try:
        # ASCII is a strict subset of UTF-8 and excludes escaped non-ASCII values
        # through the field validation below as well.
        return json.loads(raw.decode('ascii'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError):
        raise FormalSnapshotError(code) from None


def _binding(value, code):
    require(type(value) is dict and set(value) == BINDING_KEYS, code)
    require(type(value['operationId']) is str and
            re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value['operationId']) and
            type(value['role']) is str and value['role'] in ROLES and
            type(value['hostBootId']) is str and
            re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['hostBootId']) and
            all(_hex(value[key]) for key in BINDING_KEYS - {'operationId','role','hostBootId'}), code)


def _decode(value, limit):
    require(type(value) is str and len(value) <= 4*((limit+2)//3), 'FORMAL_OPEN_ENVELOPE_INVALID')
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise FormalSnapshotError('FORMAL_OPEN_ENVELOPE_INVALID') from None
    require(0 < len(raw) <= limit and base64.b64encode(raw).decode('ascii') == value,
            'FORMAL_OPEN_ENVELOPE_INVALID')
    return raw


def _sealed_fd(raw):
    # Seekable, anonymous, sealed files support OpenSSL's Ed25519 one-shot input
    # without a filesystem path, temporary key file or pipe/seek workaround.
    fd = os.memfd_create('formal-original-open', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            require(written > 0, 'FORMAL_OPEN_VERIFIER_IO_FAILED')
            offset += written
        os.lseek(fd, 0, os.SEEK_SET)
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS,
                    fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _run(arguments, *, pass_fds=()):
    try:
        result = subprocess.run([OPENSSL, *arguments], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, pass_fds=pass_fds,
            timeout=min(10, observation_timeout(10)), check=False)
    except subprocess.TimeoutExpired:
        raise FormalSnapshotError('FORMAL_OPEN_VERIFIER_TIMEOUT') from None
    except OSError:
        raise FormalSnapshotError('FORMAL_OPEN_VERIFIER_UNAVAILABLE') from None
    return result


def verify_original_open_approval(approval_path, trusted_key_path, trusted_key_sha256,
                                  expected_binding, *, now_seconds, guard):
    """Read-only authenticity/binding gate, explicitly not persistent consumption."""
    require_native_runtime()
    require(os.geteuid() == 0, 'FORMAL_OPEN_ROOT_REQUIRED')
    require(_hex(trusted_key_sha256) and type(now_seconds) is int and now_seconds > 0 and callable(guard),
            'FORMAL_OPEN_VERIFIER_INPUT_INVALID')
    _binding(expected_binding, 'FORMAL_OPEN_VERIFIER_INPUT_INVALID')
    require(callable(getattr(os, 'memfd_create', None)) and
            all(type(getattr(fcntl, name, None)) is int for name in
                ('F_ADD_SEALS','F_SEAL_WRITE','F_SEAL_GROW','F_SEAL_SHRINK','F_SEAL_SEAL')),
            'FORMAL_OPEN_VERIFIER_UNAVAILABLE')
    started = time.monotonic()
    try:
        guard(); observation_timeout(1)
        approval_raw, approval_identity = _read_secure(approval_path, 0o600, 8192, no_atime=True)
        key_raw, key_identity = _read_secure(trusted_key_path, 0o644, 4096, no_atime=True)
        require(_sha(key_raw) == trusted_key_sha256 and len(key_raw) == len(SPKI_PREFIX)+32 and
                key_raw.startswith(SPKI_PREFIX), 'FORMAL_OPEN_TRUSTED_KEY_INVALID')
        envelope = _json(approval_raw, 'FORMAL_OPEN_ENVELOPE_INVALID')
        require(type(envelope) is dict and set(envelope) ==
                {'schemaVersion','keySha256','payloadBase64','signatureBase64'} and
                envelope['schemaVersion'] == 'formal-original-open-approval/v1' and
                envelope['keySha256'] == trusted_key_sha256, 'FORMAL_OPEN_ENVELOPE_INVALID')
        payload_raw = _decode(envelope['payloadBase64'], 4096)
        signature = _decode(envelope['signatureBase64'], 64)
        require(len(signature) == 64, 'FORMAL_OPEN_ENVELOPE_INVALID')
        payload = _json(payload_raw, 'FORMAL_OPEN_PAYLOAD_INVALID')
        require(type(payload) is dict and set(payload) == PAYLOAD_KEYS, 'FORMAL_OPEN_PAYLOAD_INVALID')
        binding = {key:payload[key] for key in BINDING_KEYS}
        _binding(binding, 'FORMAL_OPEN_PAYLOAD_INVALID')
        require(binding == expected_binding and payload['purpose'] == 'RESTORE_SAVED_ORIGINAL_OPEN' and
                _hex(payload['grantId'], 32) and
                all(type(payload[k]) is int and payload[k] > 0 for k in ('actorId','tenantId','issuedAt','expiresAt')) and
                1 <= payload['expiresAt'] - payload['issuedAt'] <= 3600 and
                payload['issuedAt'] <= now_seconds < payload['expiresAt'], 'FORMAL_OPEN_PAYLOAD_INVALID')
        version = _run(['version'])
        require(version.returncode == 0 and version.stdout.startswith(b'OpenSSL 3.0.13 '),
                'FORMAL_OPEN_VERIFIER_UNAVAILABLE')
        descriptors = []
        try:
            for raw in (key_raw, payload_raw, signature):descriptors.append(_sealed_fd(raw))
            key_fd, message_fd, signature_fd = descriptors
            checked = _run(['pkeyutl','-verify','-pubin','-keyform','DER','-rawin',
                '-inkey',f'/proc/self/fd/{key_fd}','-in',f'/proc/self/fd/{message_fd}',
                '-sigfile',f'/proc/self/fd/{signature_fd}'], pass_fds=tuple(descriptors))
            require(checked.returncode == 0, 'FORMAL_OPEN_SIGNATURE_INVALID')
        finally:
            for fd in reversed(descriptors):os.close(fd)
        guard(); observation_timeout(1)
        require(_read_secure(approval_path, 0o600, 8192, no_atime=True) == (approval_raw, approval_identity),
                'FORMAL_OPEN_APPROVAL_CHANGED')
        require(_read_secure(trusted_key_path, 0o644, 4096, no_atime=True) == (key_raw, key_identity),
                'FORMAL_OPEN_TRUSTED_KEY_CHANGED')
        elapsed = time.monotonic() - started
        # The trusted caller supplies floor(epoch seconds). Refuse its entire
        # unknown fractional second rather than accept up to one second late.
        require(elapsed >= 0 and now_seconds + 1 + elapsed < payload['expiresAt'],
                'FORMAL_OPEN_PAYLOAD_INVALID')
        return dict(binding, state='ORIGINAL_OPEN_APPROVAL_VERIFIED_PENDING_CONSUMPTION',
            **{key:payload[key] for key in ('grantId','actorId','tenantId','issuedAt','expiresAt')},
            approvalSha256=_sha(approval_raw), keySha256=trusted_key_sha256,
            approvalConsumed=False, serviceActionsPerformed=False, productionEvidence=False, releaseReady=False)
    except OSError:
        raise FormalSnapshotError('FORMAL_OPEN_VERIFIER_IO_FAILED') from None


PRODUCTION_A_CODE = 'FORMAL_PRODUCTION_A_RESUME_APPROVAL_INVALID'
PRODUCTION_A_BINDINGS = {'environment', 'operationId', 'releaseTag', 'attemptId', 'leaseTokenDigest',
    'packageDigest', 'manifestDigest', 'planDigest', 'approvedSourceTargetSha256', 'sourceBindingSha256', 'hostBootId'}
PRODUCTION_A_PURPOSE = 'RESTORE_PRODUCTION_SAVED_ORIGINAL_STATE'
PRODUCTION_A_POLICY = {'originalStateOnly': True, 'preserveStoppedAndAbsent': True,
                       'preserveUnfinishedRecords': True, 'noBootStateWrites': True}


def _production_a_binding(value):
    require(type(value) is dict and set(value) == PRODUCTION_A_BINDINGS, PRODUCTION_A_CODE)
    require(type(value['environment']) is str and value['environment'] == 'prod' and type(value['releaseTag']) is str and
        re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,122}', value['releaseTag']) and
        type(value['operationId']) is str and value['operationId'] == 'prod-'+value['releaseTag'] and type(value['hostBootId']) is str and
        re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['hostBootId']) and
        all(_hex(value[key]) for key in PRODUCTION_A_BINDINGS -
            {'environment', 'operationId', 'releaseTag', 'hostBootId'}), PRODUCTION_A_CODE)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def _production_a_terminal_files(pins, directories):
    """After all content/guard reads, check only native directory/file identities."""
    import formal_boot_state as boot
    try:
        for path, identity in directories.items(): boot._directory_unchanged(path, identity)
        for path, _, _, pair in pins:
            require(boot._signature(os.stat(path, follow_symlinks=False)) == pair[1], PRODUCTION_A_CODE)
    except OSError:
        raise FormalSnapshotError(PRODUCTION_A_CODE) from None


def verify_production_a_resume_approval(approval_path, trusted_key_path, trusted_key_sha256,
                                      expected_binding, *, now_seconds, guard):
    """Distinct PROD A approval, without OPEN writes, grant consumption or service actions.

    The owner derives sourceBindingSha256 from the complete pinned original source
    inventory, not a caller summary or the four-file legacy maintenance scope.
    This finite verifier checks that supplied binding; it cannot prove its origin.
    """
    require_native_runtime()
    require(os.geteuid() == 0 and _hex(trusted_key_sha256) and type(now_seconds) is int and
        now_seconds > 0 and callable(guard), PRODUCTION_A_CODE)
    expected_raw = _production_a_binding(expected_binding)
    started = time.monotonic()
    guard(); observation_timeout(1)
    import formal_boot_state as boot
    directories = {}
    for path in (approval_path, trusted_key_path):
        parent = boot._absolute(path).parent
        with boot._directory(parent, no_atime=True) as (_, identity): directories[parent] = identity
    try:
        approval_raw, approval_identity = _read_secure(approval_path, 0o600, 8192, no_atime=True)
        key_raw, key_identity = _read_secure(trusted_key_path, 0o644, 4096, no_atime=True)
        require(_sha(key_raw) == trusted_key_sha256 and len(key_raw) == len(SPKI_PREFIX)+32 and
            key_raw.startswith(SPKI_PREFIX), PRODUCTION_A_CODE)
        envelope = _json(approval_raw, PRODUCTION_A_CODE)
        require(type(envelope) is dict and set(envelope) ==
            {'schemaVersion', 'keySha256', 'payloadBase64', 'signatureBase64'} and
            envelope['schemaVersion'] == 'formal-production-a-resume-approval/v1' and
            envelope['keySha256'] == trusted_key_sha256, PRODUCTION_A_CODE)
        payload_raw = _decode(envelope['payloadBase64'], 4096)
        signature = _decode(envelope['signatureBase64'], 64)
        require(len(signature) == 64, PRODUCTION_A_CODE)
        payload = _json(payload_raw, PRODUCTION_A_CODE)
        require(type(payload) is dict and set(payload) == PRODUCTION_A_BINDINGS |
            {'purpose', 'policy', 'grantId', 'actorId', 'tenantId', 'issuedAt', 'expiresAt'}, PRODUCTION_A_CODE)
        require(type(payload['policy']) is dict and set(payload['policy']) == set(PRODUCTION_A_POLICY) and
            all(type(flag) is bool and flag is True for flag in payload['policy'].values()), PRODUCTION_A_CODE)
        require(_production_a_binding({k: payload[k] for k in PRODUCTION_A_BINDINGS}) == expected_raw and
            payload['purpose'] == PRODUCTION_A_PURPOSE and _hex(payload['grantId'], 32) and
            all(type(payload[k]) is int and payload[k] > 0 for k in ('actorId', 'tenantId', 'issuedAt', 'expiresAt')) and
            1 <= payload['expiresAt']-payload['issuedAt'] <= 3600 and
            payload['issuedAt'] <= now_seconds < payload['expiresAt'], PRODUCTION_A_CODE)
        version = _run(['version'])
        require(version.returncode == 0 and version.stdout.startswith(b'OpenSSL 3.0.13 '), PRODUCTION_A_CODE)
        descriptors = []
        try:
            for raw in (key_raw, payload_raw, signature): descriptors.append(_sealed_fd(raw))
            key_fd, message_fd, signature_fd = descriptors
            checked = _run(['pkeyutl', '-verify', '-pubin', '-keyform', 'DER', '-rawin',
                '-inkey', f'/proc/self/fd/{key_fd}', '-in', f'/proc/self/fd/{message_fd}',
                '-sigfile', f'/proc/self/fd/{signature_fd}'], pass_fds=tuple(descriptors))
            require(checked.returncode == 0, PRODUCTION_A_CODE)
        finally:
            for fd in reversed(descriptors): os.close(fd)
    except (OSError, FormalSnapshotError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise FormalSnapshotError(PRODUCTION_A_CODE) from None
    guard(); observation_timeout(1)
    require(_production_a_binding(expected_binding) == expected_raw and
        _read_secure(approval_path, 0o600, 8192, no_atime=True) == (approval_raw, approval_identity) and
        _read_secure(trusted_key_path, 0o644, 4096, no_atime=True) == (key_raw, key_identity), PRODUCTION_A_CODE)
    _production_a_terminal_files([(approval_path, 0o600, 8192, (approval_raw, approval_identity)),
                                 (trusted_key_path, 0o644, 4096, (key_raw, key_identity))], directories)
    require(_production_a_binding(expected_binding) == expected_raw, PRODUCTION_A_CODE)
    elapsed = time.monotonic()-started
    require(elapsed >= 0 and now_seconds+1+elapsed < payload['expiresAt'], PRODUCTION_A_CODE)
    observation_timeout(1)
    return dict(payload, state='PRODUCTION_A_RESUME_VERIFIED_PENDING_CONSUMPTION',
        approvalSha256=_sha(approval_raw), keySha256=trusted_key_sha256, approvalConsumed=False,
        serviceActionsPerformed=False, productionEvidence=False, releaseReady=False)


def consume_production_a_resume_approval(claim, registry_path, approval_path, trusted_key_path,
                                       trusted_key_sha256, expected_binding, *, guard):
    """Exclusive durable one-attempt grant, never a service-restoration operation.

    The normal owner must independently pin registry_path outside per-claim roots,
    supply source/lease/thaw guards, and retain this marker through task cleanup.
    An interrupted consume is not replayable, even in a second claim directory.
    """
    import stat
    from pathlib import Path
    import formal_boot_state as boot
    import formal_snapshot_linux as snapshot
    require_native_runtime()
    require(os.geteuid() == 0 and type(claim) is snapshot.FormalMaintenanceClaim and callable(guard), PRODUCTION_A_CODE)
    expected_raw = _production_a_binding(expected_binding)
    expected = json.loads(expected_raw)
    claim.assert_owned()
    baseline = json.loads(snapshot._canonical_bytes(claim.events))
    require(json.loads(claim._plan)['operationId'] == expected['operationId'] and
        not any(e['step'].startswith('production-a-resume-') or '-restore-' in e['step'] or
            'recovery' in e['step'] for e in claim.events), 'FORMAL_PRODUCTION_A_RESUME_ALREADY_ATTEMPTED')
    verified = verify_production_a_resume_approval(approval_path, trusted_key_path, trusted_key_sha256,
        expected, now_seconds=int(time.time()), guard=guard)
    pins = [(path, mode, limit, boot._read_secure(path, mode, limit, no_atime=True))
        for path, mode, limit in ((approval_path, 0o600, 8192), (trusted_key_path, 0o644, 4096))]
    require(_sha(pins[0][3][0]) == verified['approvalSha256'] and
        _sha(pins[1][3][0]) == verified['keySha256'], PRODUCTION_A_CODE)
    registry = boot._absolute(registry_path)
    require(registry != claim.root and registry not in claim.root.parents and claim.root not in registry.parents,
        PRODUCTION_A_CODE)
    marker = 'production-a-resume-grant-'+verified['grantId']+'.json'
    details = dict(binding=expected, **{k: verified[k] for k in
        ('purpose', 'grantId', 'actorId', 'tenantId', 'issuedAt', 'expiresAt', 'approvalSha256', 'keySha256')})
    raw = snapshot._canonical_bytes(dict(schemaVersion='formal-production-a-resume-consumption/v1', **details))
    approved_wall, approved_monotonic = time.time(), time.monotonic()
    with boot._directory(registry, no_atime=True) as (directory, identity):
        require(stat.S_IMODE(os.fstat(directory).st_mode) == 0o700, PRODUCTION_A_CODE)
        directories = {registry: identity}
        for path in (approval_path, trusted_key_path, str(claim.root/'binding.json')):
            parent = boot._absolute(path).parent
            with boot._directory(parent, no_atime=True) as (_, parent_identity): directories[parent] = parent_identity
        lock_identity = boot._signature(os.fstat(claim._fd))
        consumed_details = dict(details, markerSha256=_sha(raw))
        def stage(*, complete=False):
            require(snapshot._canonical_bytes(claim.events[:len(baseline)]) == snapshot._canonical_bytes(baseline), PRODUCTION_A_CODE)
            suffix = claim.events[len(baseline):]
            expected_suffix = [('production-a-resume-intent', details), ('production-a-resume-consumed', consumed_details)]
            require((len(suffix) == 2 if complete else len(suffix) <= 2) and all(e['step'] == expected_suffix[i][0] and
                snapshot._canonical_bytes(e['details']) == snapshot._canonical_bytes(expected_suffix[i][1])
                for i, e in enumerate(suffix)), PRODUCTION_A_CODE)
        def current():
            guard(); observation_timeout(1); claim.assert_owned(); stage()
            require(_production_a_binding(expected_binding) == expected_raw and
                Path('/proc/sys/kernel/random/boot_id').read_text().strip() == expected['hostBootId'], PRODUCTION_A_CODE)
            boot._directory_unchanged(registry, identity)
            for path, mode, limit, pair in pins:
                require(boot._read_secure(path, mode, limit, no_atime=True) == pair, PRODUCTION_A_CODE)
            elapsed = time.monotonic()-approved_monotonic
            require(elapsed >= 0 and verified['issuedAt'] <= time.time() < verified['expiresAt'] and
                approved_wall+elapsed < verified['expiresAt'], PRODUCTION_A_CODE)
        current()
        require(not os.path.lexists(registry/marker), 'FORMAL_PRODUCTION_A_RESUME_ALREADY_ATTEMPTED')
        # Reserve globally before any claim intent. An intent-write failure or
        # process exit must not let a cloned claim consume this grant again.
        try:
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=directory)
            try:
                offset = 0
                while offset < len(raw):
                    count = os.write(fd, raw[offset:]); require(count > 0, PRODUCTION_A_CODE); offset += count
                os.fsync(fd)
            finally: os.close(fd)
            os.fsync(directory)
        except OSError:
            raise FormalSnapshotError('FORMAL_PRODUCTION_A_RESUME_CONSUMPTION_FAILED_RETAINED') from None
        marker_pair = boot._read_at(directory, marker, 0o600, 8192, no_atime=True)
        require(marker_pair[0] == raw, PRODUCTION_A_CODE)
        current()
        claim.record('production-a-resume-intent', details)
        current()
        claim.record('production-a-resume-consumed', consumed_details)
        current()
        stage(complete=True)
        final_events = json.loads(snapshot._canonical_bytes(claim.events))
        require(boot._read_at(directory, marker, 0o600, 8192, no_atime=True) == marker_pair, PRODUCTION_A_CODE)
        claim.assert_owned()
        journal_pins = []
        for path, expected_content in ([(claim.root/'binding.json', claim._plan)] +
                [(claim.root/('event-%06d.json'%e['sequence']), snapshot._canonical_bytes(e)) for e in final_events]):
            pair = boot._read_secure(path, 0o600, 16384, no_atime=True)
            require(pair[0] == expected_content, PRODUCTION_A_CODE)
            journal_pins.append((path, 0o600, 16384, pair))
        _production_a_terminal_files(pins + [(registry/marker, 0o600, 8192, marker_pair)] + journal_pins, directories)
        require(boot._signature(os.fstat(claim._fd)) == lock_identity and
            boot._signature(os.stat(claim._lock, follow_symlinks=False)) == lock_identity and
            (os.stat(claim.root, follow_symlinks=False).st_dev, os.stat(claim.root, follow_symlinks=False).st_ino) == claim._root_identity,
            PRODUCTION_A_CODE)
        stage(complete=True)
        require({name for name in os.listdir(claim.root) if name.startswith('event-')} ==
            {'event-%06d.json'%e['sequence'] for e in final_events}, PRODUCTION_A_CODE)
        require(_production_a_binding(expected_binding) == expected_raw, PRODUCTION_A_CODE)
        elapsed = time.monotonic()-approved_monotonic
        require(elapsed >= 0 and verified['issuedAt'] <= time.time() < verified['expiresAt'] and
            approved_wall+elapsed < verified['expiresAt'], PRODUCTION_A_CODE)
        observation_timeout(1)
    return dict(verified, state='PRODUCTION_A_RESUME_CONSUMED_PENDING_SERVICE_ACTIONS',
        approvalConsumed=True, markerSha256=_sha(raw), serviceActionsPerformed=False, releaseReady=False)


SELECTED_CODE = 'RELEASE_SELECTED_SERVICE_APPROVAL_INVALID'
SELECTED_FIELDS = {'schemaVersion', 'role', 'purpose', 'dispatchBinding', 'sourceBinding',
                   'grantId', 'actorId', 'tenantId', 'issuedAt', 'expiresAt', 'policy'}
SELECTED_BINDING_FIELDS = {'schemaVersion', 'role', 'purpose', 'dispatchBinding', 'sourceBinding', 'policy'}
SELECTED_ACTIONS = ['quiesce-selected-writers', 'set-selected-mysql-read-only',
                    'stop-selected-mysql', 'stop-selected-minio', 'freeze-approved-selected-source']


def _selected_json(raw):
    """Selected bindings are UTF-8; original OPEN's ASCII contract stays separate."""
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, SELECTED_CODE)
            result[key] = value
        return result
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: require(False, SELECTED_CODE))
    except (ValueError, UnicodeError, RecursionError):
        raise FormalSnapshotError(SELECTED_CODE) from None


def _selected_canonical(value):
    # JSON bytes distinguish bool/int as well as int/float in current identities.
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False,
                          ensure_ascii=True).encode('ascii')
    except (ValueError, TypeError, RecursionError):
        raise FormalSnapshotError(SELECTED_CODE) from None


def _selected_fields(value, fields):
    require(type(value) is dict and set(value) == set(fields), SELECTED_CODE)


def _selected_binding(value):
    """Independent current range/policy; issuer metadata is never expected input."""
    _selected_fields(value, SELECTED_BINDING_FIELDS)
    role = value['role']
    require(value['schemaVersion'] == 'release-selected-test-service-authority/v1' and
            type(role) is str and role in ('stopAuthority', 'restoreAuthority'), SELECTED_CODE)
    require(value['purpose'] == ('CLOSE_SELECTED_SOURCE_FOR_CAPTURE' if role == 'stopAuthority'
                                else 'RESTORE_SELECTED_SAVED_SOURCE_STATE'), SELECTED_CODE)
    dispatch = value['dispatchBinding']
    _selected_fields(dispatch, ('workflowId', 'operationId', 'releaseTag', 'packageDigest',
                               'manifestDigest', 'targetDigest', 'deploymentBindingDigest'))
    require(all(type(dispatch[key]) is str and re.fullmatch('[A-Za-z0-9_-]{1,128}', dispatch[key])
                for key in ('workflowId', 'operationId')) and
            type(dispatch['releaseTag']) is str and
            re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', dispatch['releaseTag']) and
            all(_hex(dispatch[key]) for key in ('packageDigest', 'manifestDigest', 'targetDigest',
                                                'deploymentBindingDigest')), SELECTED_CODE)
    source = value['sourceBinding']
    _selected_fields(source, ('scope', 'instanceIdentity', 'configSha256', 'envSha256',
                              'originalsSha256', 'containers', 'applicationsSha256'))
    scope = source['scope']
    _selected_fields(scope, ('environment', 'host', 'machineId', 'database', 'serverUuid'))
    require(scope['environment'] == 'test' and scope['host'] == '172.30.30.58' and
            _hex(scope['machineId'], 32) and type(scope['database']) is str and
            re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}', scope['database']) and
            type(scope['serverUuid']) is str and
            re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', scope['serverUuid']) and
            type(source['instanceIdentity']) is dict and
            all(_hex(source[key]) for key in ('configSha256', 'envSha256', 'applicationsSha256')), SELECTED_CODE)
    original_roles = ('application-config', 'application-env', 'data-env', 'application-compose', 'data-compose')
    _selected_fields(source['originalsSha256'], original_roles)
    require(all(_hex(digest) for digest in source['originalsSha256'].values()), SELECTED_CODE)
    _selected_fields(source['containers'], ('mysql', 'minio'))
    for container in source['containers'].values():
        _selected_fields(container, ('id', 'imageId', 'volume'))
        require(_hex(container['id']) and type(container['imageId']) is str and
                re.fullmatch('sha256:[0-9a-f]{64}', container['imageId']) and
                type(container['volume']) is dict, SELECTED_CODE)
    if role == 'stopAuthority':
        _selected_fields(value['policy'], ('actions',))
        require(value['policy']['actions'] == SELECTED_ACTIONS, SELECTED_CODE)
    else:
        _selected_fields(value['policy'], ('originalStateOnly', 'preserveAbsent',
                                         'retainOnUnknownNewWrites', 'requireIndependentOriginalOpen'))
        require(all(type(flag) is bool and flag is True for flag in value['policy'].values()), SELECTED_CODE)
    return _selected_canonical(value)


def _selected_authority(value, now):
    """Validate signed issuer metadata, without accepting it before authenticity."""
    _selected_fields(value, SELECTED_FIELDS)
    _selected_binding({key: value[key] for key in SELECTED_BINDING_FIELDS})
    require(_hex(value['grantId'], 32) and
            all(type(value[key]) is int and value[key] > 0 for key in ('actorId', 'tenantId', 'issuedAt', 'expiresAt')) and
            1 <= value['expiresAt'] - value['issuedAt'] <= 3600 and
            value['issuedAt'] <= now < value['expiresAt'], SELECTED_CODE)
    return _selected_canonical(value)


def _selected_read(path, mode, limit):
    try:
        return _read_secure(path, mode, limit, no_atime=True)
    except (OSError, FormalSnapshotError):
        raise FormalSnapshotError(SELECTED_CODE) from None


def verify_selected_service_approval(approval_path, trusted_key_path, trusted_key_sha256,
                                     expected_binding, *, now_seconds, guard):
    """Actual native authenticity/current binding, never grant consumption or effects.

    Trust comes only from independently configured executor key inputs. The author
    must derive expected_binding from complete fresh source observations and
    fixed purpose/policy, enforcing resource/recovery admission separately. Grant,
    approval actor/tenant and validity are issuer metadata, accepted only after
    strict validation and real signature verification. They cannot be caller
    expected fields or derived from the dispatch actor. Caller time is trusted
    code, never a field of the approval request or envelope.
    """
    try:
        require_native_runtime()
        require(os.geteuid() == 0 and _hex(trusted_key_sha256) and type(now_seconds) is int and
                now_seconds > 0 and callable(guard), SELECTED_CODE)
        expected_bytes = _selected_binding(expected_binding)
        require(callable(getattr(os, 'memfd_create', None)) and
                all(type(getattr(fcntl, name, None)) is int for name in
                    ('F_ADD_SEALS', 'F_SEAL_WRITE', 'F_SEAL_GROW', 'F_SEAL_SHRINK', 'F_SEAL_SEAL')), SELECTED_CODE)
    except (OSError, FormalSnapshotError, KeyError, TypeError, AttributeError, RecursionError):
        raise FormalSnapshotError(SELECTED_CODE) from None
    started = time.monotonic()
    guard(); observation_timeout(1)
    approval_raw, approval_identity = _selected_read(approval_path, 0o600, 32768)
    key_raw, key_identity = _selected_read(trusted_key_path, 0o644, 4096)
    try:
        require(_sha(key_raw) == trusted_key_sha256 and len(key_raw) == len(SPKI_PREFIX)+32 and
                key_raw.startswith(SPKI_PREFIX), SELECTED_CODE)
        envelope = _selected_json(approval_raw)
        _selected_fields(envelope, ('schemaVersion', 'keySha256', 'payloadBase64', 'signatureBase64'))
        require(envelope['schemaVersion'] == 'release-selected-test-service-approval/v1' and
                envelope['keySha256'] == trusted_key_sha256, SELECTED_CODE)
        # The request is capped at 16384 bytes before server-owned metadata is
        # appended. Keep a bounded 1024-byte allowance for that issuer metadata.
        payload_raw = _decode(envelope['payloadBase64'], 17408)
        signature = _decode(envelope['signatureBase64'], 64)
        require(len(signature) == 64, SELECTED_CODE)
        payload = _selected_json(payload_raw)
        _selected_authority(payload, now_seconds)
        require(_selected_binding({key: payload[key] for key in SELECTED_BINDING_FIELDS}) == expected_bytes,
                SELECTED_CODE)
        version = _run(['version'])
        require(version.returncode == 0 and version.stdout.startswith(b'OpenSSL 3.0.13 '), SELECTED_CODE)
        descriptors = []
        try:
            for raw in (key_raw, payload_raw, signature): descriptors.append(_sealed_fd(raw))
            key_fd, message_fd, signature_fd = descriptors
            checked = _run(['pkeyutl', '-verify', '-pubin', '-keyform', 'DER', '-rawin',
                            '-inkey', f'/proc/self/fd/{key_fd}', '-in', f'/proc/self/fd/{message_fd}',
                            '-sigfile', f'/proc/self/fd/{signature_fd}'], pass_fds=tuple(descriptors))
            require(checked.returncode == 0, SELECTED_CODE)
        finally:
            for fd in reversed(descriptors): os.close(fd)
    except (OSError, FormalSnapshotError, KeyError, TypeError, AttributeError, RecursionError):
        raise FormalSnapshotError(SELECTED_CODE) from None
    # External ownership failures remain their exact fixed guard errors.
    guard(); observation_timeout(1)
    require(_selected_read(approval_path, 0o600, 32768) == (approval_raw, approval_identity) and
            _selected_read(trusted_key_path, 0o644, 4096) == (key_raw, key_identity), SELECTED_CODE)
    try:
        require(_selected_binding(expected_binding) == expected_bytes, SELECTED_CODE)
        elapsed = time.monotonic() - started
        require(elapsed >= 0 and now_seconds + 1 + elapsed < payload['expiresAt'], SELECTED_CODE)
    except (KeyError, TypeError, AttributeError, RecursionError):
        raise FormalSnapshotError(SELECTED_CODE) from None
    return dict(state='SELECTED_SERVICE_APPROVAL_VERIFIED_PENDING_CONSUMPTION', authority=payload,
                approvalSha256=_sha(approval_raw), keySha256=trusted_key_sha256,
                approvalConsumed=False, serviceActionsPerformed=False, releaseReady=False)
