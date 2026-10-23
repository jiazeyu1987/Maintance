"""Explicit R12 browser B admission; no root admission or decoded-record shortcut.

Broker originals are finite raw evidence formats documented in the R12 handoff.
They must be referenced by a fresh signed GuardMeasurement. Only B measures self;
the independently selected broker measures PID1/A and the protected cross views.
"""
import base64
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time

import repository_native_runtime as native
from repository_records import RepositoryError, canonical, document, exact, require, timestamp

_SCHEMA_PATH = Path(__file__).with_name('repository_native_browser_schemas.json')
_SCHEMAS = document(_SCHEMA_PATH.read_bytes())
_verified = {}
SOURCE_ROLES = native.NATIVE_ROLES | {'installed-python', 'installed-python-source', 'installed-binary', 'installed-original',
                                     'vendor-artifact', 'protected-record', 'public-authority'}
_EVIDENCE_FIELDS = ('readOnlyMountEvidencePin', 'managerIdentityEvidencePin',
                    'nativeLinkageEvidencePin', 'directoryAccessEvidencePin',
                    'completeSourceReadEvidencePin', 'workerKeyDenialEvidencePin', 'bootstrapOriginalPin')


def schema_document(name):
    """Export the exact ratified schema, including shared definitions."""
    definition = _SCHEMAS['$defs'].get(name) or _SCHEMAS['schemas'].get(name)
    require(definition is not None, 'REPOSITORY_BROWSER_SCHEMA_UNKNOWN')
    return document(canonical({'$schema': _SCHEMAS['$schema'], '$defs': _SCHEMAS['$defs'], **definition}))


def _validate(value, schema, deadline=None):
    # Interpret only the finite keyword set used by the ratified private schemas.
    native._remaining(deadline)
    if '$ref' in schema:
        return _validate(value, _SCHEMAS['$defs'][schema['$ref'].split('/')[-1]], deadline)
    for union in ('anyOf', 'oneOf'):
        if union in schema:
            matches = 0
            for option in schema[union]:
                try:
                    _validate(value, option, deadline)
                    matches += 1
                except RepositoryError as error:
                    if error.code != 'REPOSITORY_BROWSER_SCHEMA_INVALID':
                        raise
            require(matches == 1 if union == 'oneOf' else matches > 0,
                    'REPOSITORY_BROWSER_SCHEMA_INVALID')
            return
    if 'const' in schema:
        require(type(value) is type(schema['const']) and value == schema['const'],
                'REPOSITORY_BROWSER_SCHEMA_INVALID')
    if 'enum' in schema:
        require(any(type(value) is type(v) and value == v for v in schema['enum']),
                'REPOSITORY_BROWSER_SCHEMA_INVALID')
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'integer': int, 'string': str, 'boolean': bool, 'null': type(None)}
    if kind:
        require(type(value) is types[kind], 'REPOSITORY_BROWSER_SCHEMA_INVALID')
    if kind == 'object':
        require(set(schema.get('required', [])) <= set(value) and
                (schema.get('additionalProperties') is not False or set(value) <= set(schema['properties'])),
                'REPOSITORY_BROWSER_SCHEMA_INVALID')
        for key, child in value.items():
            _validate(child, schema['properties'][key], deadline)
    elif kind == 'array':
        require(schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 4096),
                'REPOSITORY_BROWSER_SCHEMA_INVALID')
        for child in value:
            _validate(child, schema['items'], deadline)
    elif kind == 'integer':
        require(schema.get('minimum', -2**63) <= value <= schema.get('maximum', 2**63-1),
                'REPOSITORY_BROWSER_SCHEMA_INVALID')
    elif kind == 'string':
        require(len(value) >= schema.get('minLength', 0) and
                ('pattern' not in schema or re.search(schema['pattern'], value)),
                'REPOSITORY_BROWSER_SCHEMA_INVALID')
        if schema.get('format') == 'date-time':
            timestamp(value)
        if schema is _SCHEMAS['$defs']['Path']:
            native._path(value)


def validate_record(value, name, deadline=None):
    _validate(value, schema_document(name), deadline)
    return value


def _window(value, *, start='issuedAt', parent=None):
    now = datetime.now(timezone.utc)
    require(timestamp(value[start]) <= now < timestamp(value['expiresAt']),
            'REPOSITORY_BROWSER_AUTHORITY_NOT_CURRENT')
    if parent is not None:
        require(timestamp(parent['issuedAt']) <= timestamp(value[start]) and
                timestamp(value['expiresAt']) <= timestamp(parent['expiresAt']),
                'REPOSITORY_BROWSER_OUTLIVES_AUTHORITY')


def _budget(deadline, proof=None):
    require(deadline is None or type(deadline) in (int, float) and math.isfinite(deadline),
            'REPOSITORY_NATIVE_DEADLINE_INVALID')
    now = time.monotonic()
    end = min(now + 300, deadline) if deadline is not None else now + 300
    if proof is not None:
        end = min(end, now + (timestamp(proof['expiresAt']) - datetime.now(timezone.utc)).total_seconds())
    native._remaining(end)
    return end


def _platform():
    require(sys.platform.startswith('linux') and sys.version_info >= (3, 12) and
            os.geteuid() > 0 and os.getegid() > 0 and hasattr(os, 'O_NOFOLLOW') and
            os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd,
            'REPOSITORY_BROWSER_NONROOT_LINUX_REQUIRED')
    require(not any(os.environ.get(k) for k in
                    ('PYTHONPATH', 'PYTHONHOME', 'LD_LIBRARY_PATH', 'LD_PRELOAD', 'LD_AUDIT')),
            'REPOSITORY_NATIVE_RUNTIME_OVERRIDE_REFUSED')
    facts = measure_security()
    require(os.getresuid() == (os.geteuid(),) * 3 and os.getresgid() == (os.getegid(),) * 3 and
            not os.getgroups() and facts['noNewPrivs'] == 1 and
            all(int(facts[k], 16) == 0 for k in ('capEff', 'capPrm', 'capInh', 'capBnd')) and
            (facts['capAmb'] is None and facts['ambientState'] == 'UNSUPPORTED_PROVEN' or
             facts['capAmb'] is not None and int(facts['capAmb'], 16) == 0),
            'REPOSITORY_BROWSER_ACTUAL_SECURITY_MISMATCH')
    current = native._status(native._kernel('/proc/self/status'))
    require(current['Uid'].split() == [str(os.geteuid())] * 4 and
            current['Gid'].split() == [str(os.getegid())] * 4,
            'REPOSITORY_BROWSER_ACTUAL_IDENTITY_MISMATCH')


def _deny(reference, private_pin):
    # Canonical identity is independent of declared bytes/hash and traversal order.
    require(type(reference) is dict and type(reference.get('path')) is str,
            'REPOSITORY_PIN_INVALID')
    value = reference['path']
    require(value.startswith('/') and '\\' not in value and '\x00' not in value,
            'REPOSITORY_NATIVE_LITERAL_PATH_REQUIRED')
    import posixpath
    require(posixpath.normpath(value) != posixpath.normpath(private_pin['path']),
            'REPOSITORY_BROWSER_PRIVATE_KEY_READ_FORBIDDEN')
    native._pin(reference, native.VENDOR_LIMIT)


def _metadata(info):
    return {'device': info.st_dev, 'inode': info.st_ino, 'bytes': info.st_size,
            'mtimeNs': info.st_mtime_ns, 'ctimeNs': info.st_ctime_ns,
            'ownerUid': info.st_uid, 'ownerGid': info.st_gid,
            'mode': format(stat.S_IMODE(info.st_mode), '04o'), 'links': info.st_nlink}


def _mount_original(path, mounts):
    left, right = native._mount_for(path, mounts)
    return {'mountId': int(left[0]), 'fields': list(left), 'filesystemFields': list(right)}


def _directory(path, selection, deadline):
    """Hold every actual B traverse; admit only selected ancestors/custody."""
    native._remaining(deadline)
    selected = {v['path']: v for v in selection['directoryAccess']}
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    current = '/'
    try:
        for part in (None, *native._path(path).parts[1:]):
            if part is not None:
                child = os.open(part, flags, dir_fd=fd)
                os.close(fd); fd = child
                current = current.rstrip('/') + '/' + part
            info = os.fstat(fd)
            access = selected.get(current)
            require(access is not None and stat.S_ISDIR(info.st_mode) and
                    (info.st_uid, info.st_gid, format(stat.S_IMODE(info.st_mode), '04o')) ==
                    (access['ownerUid'], access['ownerGid'], access['mode']),
                    'REPOSITORY_BROWSER_DIRECTORY_CUSTODY_INVALID')
            readonly = bool(os.fstatvfs(fd).f_flag & os.ST_RDONLY)
            require(readonly == access['readOnly'], 'REPOSITORY_BROWSER_DIRECTORY_MOUNT_CHANGED')
            if access['usage'] == 'SOURCE_ANCESTOR':
                require((info.st_uid, info.st_gid, access['mode'], readonly) == (0, 0, '0555', True),
                        'REPOSITORY_BROWSER_SOURCE_ANCESTOR_INVALID')
            elif access['usage'] in ('BROWSER_CWD', 'BROWSER_OUTPUT'):
                require((info.st_uid, info.st_gid, access['mode'], readonly) ==
                        (selection['browserUid'], selection['browserGid'], '0700', False),
                        'REPOSITORY_BROWSER_OUTPUT_CUSTODY_INVALID')
                mount = native._mount_for(current, native._mounts(native._kernel('/proc/self/mountinfo', deadline=deadline)))
                require({'noexec', 'nosuid', 'nodev'} <= set(mount[0][5].split(',')),
                        'REPOSITORY_BROWSER_OUTPUT_MOUNT_UNSAFE')
            elif access['usage'] in ('SIGNER_SOCKET_PARENT', 'SIGNED_PUBLICATION_PARENT'):
                require((info.st_uid, info.st_gid, access['mode']) == (0, selection['browserGid'], '0750'),
                        'REPOSITORY_BROWSER_PUBLICATION_PARENT_INVALID')
            else:
                raise RepositoryError('REPOSITORY_BROWSER_SECRET_ANCESTOR_FORBIDDEN')
            native._remaining(deadline)
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def _original(reference, selection, *, access=None, deadline=None, retain=False):
    _deny(reference, selection['privateKeyPin'])
    native._remaining(deadline)
    path = native._path(reference['path'])
    if access is None:
        access = next((a for a in selection['sourceAccess'] if a['pin'] == reference), None)
    public = str(path).startswith(selection['signedPublicationRoot'] + '/')
    worker = str(path).startswith(selection['evidenceRoot'] + '/') and not public
    require(access is not None or public or worker, 'REPOSITORY_BROWSER_ORIGINAL_NOT_SELECTED')
    parent = _directory(str(path.parent), selection, deadline)
    fd = None
    try:
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
        info = os.fstat(fd)
        require(native._meta(before) == native._meta(info) and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                'REPOSITORY_BROWSER_REGULAR_ORIGINAL_REQUIRED')
        expected = ((0, 0, access['mode']) if access is not None else
                    (0, selection['browserGid'], '0440') if public else
                    (selection['browserUid'], selection['browserGid'], '0600'))
        require((info.st_uid, info.st_gid, format(stat.S_IMODE(info.st_mode), '04o')) == expected,
                'REPOSITORY_BROWSER_ORIGINAL_CUSTODY_INVALID')
        if access is not None:
            require(os.fstatvfs(fd).f_flag & os.ST_RDONLY, 'REPOSITORY_NATIVE_WRITABLE_RUNTIME_REFUSED')
        require(info.st_size == reference['bytes'], 'REPOSITORY_PIN_CHANGED')
        count, digest, chunks = 0, hashlib.sha256(), []
        while True:
            native._remaining(deadline)
            block = os.read(fd, min(native.CHUNK, reference['bytes'] - count + 1))
            if not block:
                break
            count += len(block)
            require(count <= reference['bytes'], 'REPOSITORY_PIN_CHANGED')
            digest.update(block)
            if retain:
                require(count <= native.LIMIT, 'REPOSITORY_RECORD_TOO_LARGE')
                chunks.append(block)
        require(count == reference['bytes'] and digest.hexdigest() == reference['sha256'] and
                native._meta(os.fstat(fd)) == native._meta(info), 'REPOSITORY_PIN_CHANGED')
        yield fd, info, b''.join(chunks) if retain else None
        current = _directory(str(path.parent), selection, deadline)
        try:
            require(native._meta(os.fstat(fd)) == native._meta(info) ==
                    native._meta(os.stat(path.name, dir_fd=current, follow_symlinks=False)) and
                    _metadata(os.fstat(parent)) == _metadata(os.fstat(current)), 'REPOSITORY_INPUT_CHANGED')
        finally:
            os.close(current)
        native._remaining(deadline)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _read(reference, selection, deadline):
    _deny(reference, selection['privateKeyPin'])
    require(reference['bytes'] <= native.LIMIT, 'REPOSITORY_RECORD_TOO_LARGE')
    with _original(reference, selection, deadline=deadline, retain=True) as (_, _, raw):
        result = raw
    return result


def _signed(reference, authorities, selection, deadline):
    envelope = document(_read(reference, selection, deadline))
    exact(envelope, 'schemaVersion keySha256 payload signature', 'RepositorySignedRecord/v1')
    require(authorities == [selection['authorityKeyPin']], 'REPOSITORY_BROWSER_AUTHORITY_SELECTION_MISMATCH')
    require(envelope['keySha256'] == authorities[0]['sha256'], 'REPOSITORY_AUTHORITY_UNKNOWN')
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        key = load_pem_public_key(_read(authorities[0], selection, deadline))
        require(isinstance(key, Ed25519PublicKey), 'REPOSITORY_AUTHORITY_KEY_INVALID')
        key.verify(base64.b64decode(envelope['signature'], validate=True), canonical(envelope['payload']))
    except (ValueError, TypeError, InvalidSignature) as error:
        raise RepositoryError('REPOSITORY_SIGNATURE_INVALID') from error
    native._remaining(deadline)
    return envelope['payload']


def _bootstrap_selection(reference, authorities, private_pin, deadline):
    # Only the bootstrap selection/key use unselected protected root ancestors.
    # The embedded private Pin is metadata, never passed to this reader.
    native._pin(reference); native._lab(reference['path'])
    native._pin(private_pin); native._lab(private_pin['path'])
    def bootstrap_read(pin):
        _deny(pin, private_pin)
        native._pin(pin); native._lab(pin['path'])
        with native._original(pin, readonly=True, deadline=deadline, retain=True) as (_, info, raw):
            require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) in (0o440, 0o444),
                    'REPOSITORY_BROWSER_BOOTSTRAP_RECORD_CUSTODY_INVALID')
            return raw
    envelope = document(bootstrap_read(reference))
    exact(envelope, 'schemaVersion keySha256 payload signature', 'RepositorySignedRecord/v1')
    selection = validate_record(envelope['payload'], 'IdentitySelection', deadline)
    require(selection['privateKeyPin'] == private_pin, 'REPOSITORY_BROWSER_PRIVATE_METADATA_CONFLICT')
    _deny(reference, selection['privateKeyPin'])
    require(authorities == [selection['authorityKeyPin']], 'REPOSITORY_BROWSER_AUTHORITY_SELECTION_MISMATCH')
    _deny(authorities[0], selection['privateKeyPin'])
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        key = load_pem_public_key(bootstrap_read(authorities[0]))
        require(isinstance(key, Ed25519PublicKey) and envelope['keySha256'] == authorities[0]['sha256'],
                'REPOSITORY_AUTHORITY_KEY_INVALID')
        key.verify(base64.b64decode(envelope['signature'], validate=True), canonical(selection))
    except (ValueError, TypeError, InvalidSignature) as error:
        raise RepositoryError('REPOSITORY_SIGNATURE_INVALID') from error
    _selection_shape(selection, deadline)
    require(_signed(reference, authorities, selection, deadline) == selection,
            'REPOSITORY_BROWSER_BOOTSTRAP_RECORD_CUSTODY_INVALID')
    return selection


def _selection_shape(selection, deadline=None):
    validate_record(selection, 'IdentitySelection', deadline)
    _window(selection)
    require(selection['rehearsalId'] == native.LAB_ID and selection['browserUid'] != selection['signerUid'],
            'REPOSITORY_BROWSER_ROLE_SELECTION_INVALID')
    for name in ('browserRootPath', 'signerRootPath', 'workingDirectory', 'evidenceRoot',
                 'signerSocketPath', 'signedPublicationRoot'):
        native._lab(selection[name])
    native._lab(selection['privateKeyPin']['path'])
    require(selection['browserRootPath'] != selection['signerRootPath'] and
            selection['environment']['HOME'].startswith(selection['workingDirectory'] + '/') and
            selection['environment']['TMPDIR'].startswith(selection['workingDirectory'] + '/') and
            selection['privateKeyPin']['path'].startswith(selection['signerRootPath'] + '/'),
            'REPOSITORY_BROWSER_PRIVATE_LAYOUT_INVALID')
    sources, directories = {}, {}
    for access in selection['sourceAccess']:
        pin = access['pin']; _deny(pin, selection['privateKeyPin'])
        require(pin['path'] not in sources and len(set(access['roles'])) == len(access['roles']) and
                set(access['roles']) <= SOURCE_ROLES, 'REPOSITORY_BROWSER_SOURCE_ACCESS_INVALID')
        if set(access['roles']) & {'installed-python', 'installed-python-source', 'installed-binary', 'installed-original',
                                  'protected-record', 'vendor-artifact', 'public-authority'}:
            if pin['path'] != '/etc/machine-id':
                native._lab(pin['path'])
            require(PurePosixPath(pin['path']).suffix.lower() not in ('.key', '.p12', '.pfx') and
                    (PurePosixPath(pin['path']).suffix.lower() != '.pem' or pin == selection['authorityKeyPin']),
                    'REPOSITORY_BROWSER_SECRET_SOURCE_FORBIDDEN')
        if 'public-authority' in access['roles']:
            require(access['roles'] == ['public-authority'] and pin == selection['authorityKeyPin'],
                    'REPOSITORY_BROWSER_AUTHORITY_SELECTION_MISMATCH')
        sources[pin['path']] = access
    for access in selection['directoryAccess']:
        native._path(access['path'])
        require(access['path'] not in directories, 'REPOSITORY_BROWSER_DIRECTORY_ACCESS_INVALID')
        directories[access['path']] = access
    for access in sources.values():
        for parent in PurePosixPath(access['pin']['path']).parents:
            ancestor = directories.get(str(parent))
            require(ancestor is not None and ancestor['usage'] == 'SOURCE_ANCESTOR',
                    'REPOSITORY_BROWSER_SOURCE_ANCESTOR_MISSING')
    require(selection['browserExecutablePin']['path'] == native.BROWSER_ROOT + '/chrome-headless-shell',
            'REPOSITORY_BROWSER_EXECUTABLE_SELECTION_INVALID')
    for name in ('browserExecutablePin', 'capabilityProbeEntryPin', 'producerEntryPin', 'signerEntryPin',
                 'bootstrapLauncherPin', 'authorityKeyPin'):
        pin = selection[name]
        require(pin['path'] in sources and sources[pin['path']]['pin'] == pin,
                'REPOSITORY_BROWSER_SOURCE_NOT_SELECTED')
    require(selection['capabilityProbeArgv'] == [selection['capabilityProbeEntryPin']['path'], '--probe'],
            'REPOSITORY_BROWSER_CAPABILITY_ARGV_INVALID')
    return sources


def measure_security():
    """Native capget/bounding/ambient/NNP facts; missing proc fields are irrelevant."""
    require(sys.platform.startswith('linux'), 'REPOSITORY_BROWSER_NATIVE_SECURITY_REQUIRED')
    libc = ctypes.CDLL(None, use_errno=True)
    class Header(ctypes.Structure):
        _fields_ = [('version', ctypes.c_uint32), ('pid', ctypes.c_int)]
    class Data(ctypes.Structure):
        _fields_ = [('effective', ctypes.c_uint32), ('permitted', ctypes.c_uint32), ('inheritable', ctypes.c_uint32)]
    data, header = (Data * 2)(), Header(0x20080522, 0)
    require(libc.capget(ctypes.byref(header), data) == 0, 'REPOSITORY_BROWSER_CAPGET_UNPROVED')
    values = {name: getattr(data[0], field) | getattr(data[1], field) << 32
              for name, field in [('capEff', 'effective'), ('capPrm', 'permitted'), ('capInh', 'inheritable')]}
    bounding = 0
    ambient, unsupported, present = 0, False, False
    count = 0
    for bit in range(64):
        ctypes.set_errno(0)
        value = libc.prctl(23, bit, 0, 0, 0)  # PR_CAPBSET_READ
        error = ctypes.get_errno()
        if value == -1 and error == errno.EINVAL:
            require(bit > 0, 'REPOSITORY_BROWSER_BOUNDING_UNPROVED')
            break
        require(value in (0, 1), 'REPOSITORY_BROWSER_BOUNDING_UNPROVED')
        count += 1; bounding |= value << bit
        ctypes.set_errno(0)
        value = libc.prctl(47, 1, bit, 0, 0)  # PR_CAP_AMBIENT, IS_SET
        error = ctypes.get_errno()
        if value == -1 and error == errno.EINVAL:
            require(not present, 'REPOSITORY_BROWSER_AMBIENT_UNPROVED')
            unsupported = True
        else:
            require(value in (0, 1) and not unsupported, 'REPOSITORY_BROWSER_AMBIENT_UNPROVED')
            present = True
            ambient |= value << bit
    require(count < 64, 'REPOSITORY_BROWSER_CAPABILITY_RANGE_UNPROVED')
    ctypes.set_errno(0)
    nnp = libc.prctl(39, 0, 0, 0, 0)  # PR_GET_NO_NEW_PRIVS, never sets it
    require(nnp in (0, 1), 'REPOSITORY_BROWSER_NNP_UNPROVED')
    dumpable = libc.prctl(3, 0, 0, 0, 0)
    require(dumpable in (0, 1, 2), 'REPOSITORY_BROWSER_DUMPABLE_UNPROVED')
    return {**{k: format(v, 'x') for k, v in values.items()}, 'capBnd': format(bounding, 'x'),
            'capAmb': None if unsupported else format(ambient, 'x'),
            'ambientState': 'UNSUPPORTED_PROVEN' if unsupported else 'PRESENT',
            'noNewPrivs': nnp, 'supplementaryGroups': os.getgroups(), 'dumpable': dumpable,
            'capabilityCount': count}


def _security_shape(security, role):
    validate_record(security, 'Security')
    masks = {k: int(security[k], 16) for k in ('capEff', 'capPrm', 'capInh', 'capBnd')}
    require((security['ambientState'] == 'PRESENT' and security['capAmb'] is not None and
             int(security['capAmb'], 16) == 0) or
            (security['ambientState'] == 'UNSUPPORTED_PROVEN' and security['capAmb'] is None),
            'REPOSITORY_BROWSER_AMBIENT_UNPROVED')
    if role == 'BROWSER_PRODUCER':
        require(not any(masks.values()), 'REPOSITORY_BROWSER_CAPABILITIES_REFUSED')
    elif role == 'AUTHORITY_A':
        require(masks['capEff'] == masks['capPrm'] == 3 and masks['capInh'] == 0 and
                masks['capBnd'] & ~3 == 0, 'REPOSITORY_BROWSER_A_CUSTODY_CAPABILITIES_INVALID')
    else:
        require(not any(v & (1 << 21) for v in masks.values()),
                'REPOSITORY_NATIVE_REMOUNT_AUTHORITY_REFUSED')


def _identity_shape(identity, role, selection):
    validate_record(identity, 'MeasuredIdentity')
    uid, gid = ((selection['browserUid'], selection['browserGid']) if role == 'BROWSER_PRODUCER' else
                (selection['signerUid'], selection['signerGid']) if role == 'AUTHORITY_A' else (0, 0))
    require(all(identity[k] == uid for k in ('uid', 'realUid', 'savedUid', 'filesystemUid')) and
            all(identity[k] == gid for k in ('gid', 'realGid', 'savedGid', 'filesystemGid')) and
            identity['hostId'] == selection['hostId'], 'REPOSITORY_BROWSER_IDENTITY_ROLE_MISMATCH')
    for key, kind in [('pidNamespace', 'pid'), ('mountNamespace', 'mnt'),
                      ('networkNamespace', 'net'), ('userNamespace', 'user')]:
        require(re.fullmatch(kind + r':\[[0-9]+\]', identity[key]), 'REPOSITORY_NATIVE_NAMESPACE_INVALID')
    if role == 'MANAGER':
        require(identity['pid'] == 1, 'REPOSITORY_NATIVE_MANAGER_IDENTITY_INVALID')
    _security_shape(identity['security'], role)


def _trust_shape(trust, selection_pin, selection):
    validate_record(trust, 'BrowserTrust')
    require(trust['labRoot'] == native.LAB_ROOT and trust['rehearsalId'] == native.LAB_ID and
            trust['browserIdentitySelectionPin'] == selection_pin and
            trust['backingRootPath'] == selection['browserRootPath'], 'REPOSITORY_BROWSER_TRUST_SCOPE_INVALID')
    # Reuse the unchanged catalog validator only, never root proof/admission.
    catalog_shape = {k: v for k, v in trust.items() if k in native.TRUST_FIELDS.split()}
    catalog_shape.update(schemaVersion='RepositoryLabNativeRuntimeTrust/v1', runtimeRole='EXECUTOR')
    catalog = native._trust_shape(catalog_shape)
    installed = native._pins(trust['installedSourcePins'], 'REPOSITORY_BROWSER_SOURCE_CLOSURE_REQUIRED', native.BINARY_LIMIT)
    require(not set(catalog) & set(installed), 'REPOSITORY_BROWSER_SOURCE_ROLE_CONFLICT')
    sources = _selection_shape(selection)
    for path, entry in catalog.items():
        require(path in sources and sources[path]['pin'] == entry['pin'] and
                sources[path]['roles'] == entry['roles'], 'REPOSITORY_BROWSER_SOURCE_CLOSURE_MISMATCH')
    for path, pin in installed.items():
        require(path in sources and sources[path]['pin'] == pin, 'REPOSITORY_BROWSER_SOURCE_CLOSURE_MISMATCH')
    return catalog, installed


def _proof_shape(proof, trust, trust_pin, selection_pin, selection):
    validate_record(proof, 'BrowserProof')
    _window(proof, parent=selection)
    require(proof['runtimeId'] == trust['runtimeId'] and proof['rehearsalId'] == native.LAB_ID and
            proof['browserIdentitySelectionPin'] == selection_pin and proof['nativeRuntimeTrustPin'] == trust_pin and
            proof['immutableRuntimeArtifactDigest'] == trust['immutableRuntimeArtifactDigest'],
            'REPOSITORY_BROWSER_PROOF_SCOPE_INVALID')
    for key in ('executorInstallationPin', 'controllerIdentityPin', 'controllerRuntimeProofPin'):
        require(proof[key] == selection[key], 'REPOSITORY_BROWSER_ROOT_ANCESTRY_MISMATCH')
    for key, role in [('managerIdentity', 'MANAGER'), ('producerIdentity', 'BROWSER_PRODUCER'),
                      ('signerIdentity', 'AUTHORITY_A')]:
        _identity_shape(proof[key], role, selection)
    manager, producer, signer = (proof[k] for k in ('managerIdentity', 'producerIdentity', 'signerIdentity'))
    require(len({manager['pid'], producer['pid'], signer['pid']}) == 3,
            'REPOSITORY_BROWSER_PRINCIPALS_NOT_INDEPENDENT')
    for key in ('hostId', 'bootId', 'pidNamespace', 'networkNamespace', 'userNamespace'):
        require(manager[key] == producer[key] == signer[key], 'REPOSITORY_BROWSER_OBSERVER_NAMESPACE_MISMATCH')
    require(producer['mountNamespace'] != signer['mountNamespace'] and
            (producer['rootDevice'], producer['rootInode']) != (signer['rootDevice'], signer['rootInode']),
            'REPOSITORY_BROWSER_A_ROOT_NOT_SEPARATE')


def _stream(reference, state, role, deadline, retain=False):
    selection, catalog = state['selection'], state['catalog']
    path = reference['path']
    access = state['sources'].get(path)
    require(access is not None and access['pin'] == reference and role in access['roles'],
            'REPOSITORY_BROWSER_MEMBER_NOT_APPROVED')
    if role in native.NATIVE_ROLES:
        entry = catalog.get(path)
        require(entry is not None and entry['pin'] == reference and role in entry['roles'],
                'REPOSITORY_BROWSER_MEMBER_NOT_APPROVED')
        if role == native.BROWSER_RESOURCE_ROLE:
            native._browser_resource(entry)
    else:
        require(role in SOURCE_ROLES, 'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
        if role in ('installed-python', 'installed-binary', 'installed-python-source', 'installed-original'):
            require(state['installed'].get(path) == reference, 'REPOSITORY_BROWSER_INSTALLED_SOURCE_NOT_APPROVED')
            manifest = state['installation']
            if role == 'installed-python':
                require(reference == manifest['pythonPin'], 'REPOSITORY_BROWSER_PYTHON_NOT_APPROVED')
            elif role == 'installed-binary':
                require(reference in manifest['dependencyPins'], 'REPOSITORY_NATIVE_INSTALLED_BINARY_NOT_APPROVED')
            else:
                require(reference in manifest['filePins'] and reference != manifest['pythonPin'] and
                        reference not in manifest['dependencyPins'] and path not in catalog,
                        'REPOSITORY_NATIVE_INSTALLED_ORIGINAL_NOT_APPROVED')
        if role == 'vendor-artifact':
            require(reference in state['trust']['vendorArtifactPins'], 'REPOSITORY_NATIVE_VENDOR_PROVENANCE_INVALID')
    with _original(reference, selection, access=access, deadline=deadline, retain=retain) as (fd, info, raw):
        prefix = os.pread(fd, min(4096, info.st_size), 0)
        require(not prefix.lstrip().startswith((b'-----BEGIN PRIVATE', b'-----BEGIN RSA PRIVATE',
                                                b'-----BEGIN EC PRIVATE', b'-----BEGIN OPENSSH PRIVATE')),
                'REPOSITORY_BROWSER_SECRET_SOURCE_FORBIDDEN')
        executable = role in ('native-tool', 'native-manager', 'native-interpreter', 'installed-binary', 'installed-python')
        require(access['mode'] == ('0555' if executable or role == 'native-library' else '0444'),
                'REPOSITORY_BROWSER_SOURCE_MODE_INVALID')
        linkage = None
        if executable or role == 'native-library':
            require(prefix.startswith(b'\x7fELF'), 'REPOSITORY_NATIVE_ELF_ORIGINAL_REQUIRED')
            linkage = native._elf_ranges(lambda offset, count: os.pread(fd, count, offset), info.st_size, deadline)
        elif role == native.BROWSER_RESOURCE_ROLE:
            native._browser_data(prefix, json_raw=prefix if path == native.BROWSER_ROOT + '/vk_swiftshader_icd.json' else None)
        elif role == 'installed-original':
            require(PurePosixPath(path).suffix.lower() not in ('.py', '.pyc', '.pyo', '.sh', '.bash', '.ps1', '.bat', '.cmd', '.pem', '.key', '.p12', '.pfx') and
                    not prefix.startswith((b'\x7fELF', b'MZ', b'\x00asm')) and
                    not prefix.lstrip().startswith((b'#!', b'-----BEGIN', b'import ', b'from ',
                                                    b'<?', b'@echo', b'function ', b'const ')),
                    'REPOSITORY_NATIVE_INSTALLED_PROGRAM_OR_KEY_REFUSED')
            native._non_program_data(fd, info, deadline, reference=reference, manifest=state['installation'])
        elif role == 'installed-python-source':
            require(PurePosixPath(path).suffix == '.py' and not prefix.startswith(b'\x7fELF'),
                    'REPOSITORY_BROWSER_PYTHON_SOURCE_INVALID')
        result = info, linkage, prefix, raw
    return result


def _elf_closure(state, deadline):
    for path, access in state['sources'].items():
        role = access['roles'][0]
        if role not in native.NATIVE_ROLES | {'installed-binary', 'installed-python'}:
            continue
        _, linkage, _, _ = _stream(access['pin'], state, role, deadline)
        if linkage is None:
            continue
        require(not os.path.lexists('/etc/ld.so.cache'), 'REPOSITORY_NATIVE_LOADER_CACHE_UNMEASURED')
        if linkage['interpreter'] is not None:
            interpreter = linkage['interpreter']
            require(interpreter in state['catalog'] and
                    'native-interpreter' in state['catalog'][interpreter]['roles'],
                    'REPOSITORY_NATIVE_INTERPRETER_NOT_INSTALLED')
        directories = []
        for search in linkage['searchPaths']:
            for directory in search.split(':'):
                directory = directory.replace('${ORIGIN}', str(PurePosixPath(path).parent)).replace('$ORIGIN', str(PurePosixPath(path).parent))
                require('$' not in directory and directory.startswith('/'), 'REPOSITORY_NATIVE_LINKAGE_UNMEASURED')
                import posixpath
                directory = posixpath.normpath(directory)
                fd = _directory(directory, state['selection'], deadline)
                os.close(fd); directories.append(directory)
        for needed in linkage['needed']:
            require(needed and '/' not in needed and '\\' not in needed, 'REPOSITORY_NATIVE_NEEDED_MEMBER_NOT_INSTALLED')
            resolved = None
            for directory in dict.fromkeys([*directories, '/lib64', '/usr/lib64']):
                candidate = directory + '/' + needed
                if os.path.lexists(candidate):
                    resolved = candidate
                    break
            entry = state['sources'].get(resolved)
            require(entry is not None and set(entry['roles']) & {'native-library', 'native-interpreter', 'installed-binary'},
                    'REPOSITORY_NATIVE_NEEDED_MEMBER_NOT_INSTALLED')
            _stream(entry['pin'], state, entry['roles'][0], deadline)


def _graph(roots, state, reserved, deadline):
    seen, active = {}, set()
    private_pin = state['selection']['privateKeyPin']
    def walk(value, opaque_private=False):
        native._remaining(deadline)
        if type(value) is dict and set(value) == {'path', 'bytes', 'sha256'}:
            _deny(value, private_pin)
            path = value['path']
            require(path not in active, 'REPOSITORY_LAB_PIN_GRAPH_CYCLE')
            if path in seen:
                require(seen[path] == value, 'REPOSITORY_LAB_PIN_GRAPH_DRIFT')
                return
            require(len(seen) < 4096, 'REPOSITORY_LAB_PIN_GRAPH_TOO_LARGE')
            seen[path] = value; active.add(path)
            access = state['sources'].get(path)
            if access is not None:
                require(access['pin'] == value, 'REPOSITORY_LAB_PIN_GRAPH_DRIFT')
                _, _, prefix, _ = _stream(value, state, access['roles'][0], deadline)
                opaque = (access['roles'][0] in native.NATIVE_ROLES | {'vendor-artifact', 'installed-binary', 'installed-python'} or
                          native._browser_schema_source(value, state['installation']))
                if access['roles'] == [native.BROWSER_RESOURCE_ROLE]:
                    walk(state['catalog'][path]['vendorArtifactPins'])
                raw = b'' if opaque else _read(value, state['selection'], deadline)
            else:
                raw = _read(value, state['selection'], deadline)
            if raw.lstrip().startswith((b'{', b'[')):
                parsed = document(raw)
                if type(parsed) is dict and parsed.get('schemaVersion') == 'RepositorySignedRecord/v1':
                    parsed = _signed(value, state['authorities'], state['selection'], deadline)
                    state.setdefault('graphRecords', {})[path] = parsed
                selected = value == state['selectionPin'] and parsed == state['selection']
                provision = (type(parsed) is dict and parsed.get('schemaVersion') == 'RepositoryLabNativeQualificationProvision/v2' and
                             parsed.get('browserIdentitySelectionPin') == state['selectionPin'] and
                             parsed.get('browserRuntimeProofPin') == state['proofPin'])
                if provision:
                    validate_record(parsed, 'RepositoryLabNativeQualificationProvision/v2', deadline)
                    require(parsed['privateKeyPin'] == private_pin, 'REPOSITORY_BROWSER_PRIVATE_METADATA_CONFLICT')
                walk(parsed, selected or provision)
            active.remove(path)
        elif type(value) is dict:
            for key, child in value.items():
                if opaque_private and key == 'privateKeyPin':
                    require(child == private_pin and seen.get(child['path'], child) == child,
                            'REPOSITORY_BROWSER_PRIVATE_METADATA_CONFLICT')
                    if child['path'] not in seen:
                        require(len(seen) < 4096, 'REPOSITORY_LAB_PIN_GRAPH_TOO_LARGE')
                        seen[child['path']] = child
                else:
                    require(key not in ('privateKeyPin', 'privateKey', 'evidenceSigningKeyPin'),
                            'REPOSITORY_BROWSER_PRIVATE_METADATA_FORBIDDEN')
                    walk(child)
        elif type(value) is list:
            for child in value:
                walk(child)
    walk(roots)
    require(len(set(reserved)) == len(reserved) and len(reserved) <= 16, 'REPOSITORY_BROWSER_RESERVED_OUTPUT_CONFLICT')
    for path in reserved:
        native._lab(path)
        require(path != private_pin['path'] and path.startswith(state['selection']['evidenceRoot'] + '/') and
                path not in state.get('sources', {}),
                'REPOSITORY_BROWSER_RESERVED_OUTPUT_CONFLICT')
        if path not in seen:
            require(len(seen) < 4096, 'REPOSITORY_LAB_PIN_GRAPH_TOO_LARGE')
            seen[path] = {'reservedOutputPath': path}
    return seen


def _raw_original(pin, state, schema, deadline):
    value = document(_read(pin, state['selection'], deadline))
    require(type(value) is dict and value.get('schemaVersion') == schema,
            'REPOSITORY_BROWSER_BROKER_ORIGINAL_REQUIRED')
    require(timestamp(value['observedAt']) <= datetime.now(timezone.utc) and
            (datetime.now(timezone.utc) - timestamp(value['observedAt'])).total_seconds() * 1000 <=
            state['selection']['maximumAgeMilliseconds'], 'REPOSITORY_BROWSER_BROKER_ORIGINAL_STALE')
    return value


def _broker_identity(identity, role, state, deadline):
    selection = state['selection']
    _identity_shape(identity, role, selection)
    require(state['sources'].get(identity['exePin']['path'], {}).get('pin') == identity['exePin'],
            'REPOSITORY_BROWSER_KERNEL_EXECUTABLE_UNPROVED')
    original = _raw_original(identity['kernelIdentityOriginalPin'], state, 'RepositoryLabBrowserKernelIdentityOriginal/v1', deadline)
    expected = {k: v for k, v in identity.items() if k not in ('kernelIdentityOriginalPin', 'security')}
    require(set(original) == {'schemaVersion', 'observedAt', 'identity', 'statusPin', 'statPin', 'mapsPin',
                              'mappedFileOriginalsPin'} and
            original['identity'] == expected, 'REPOSITORY_BROWSER_KERNEL_IDENTITY_MISMATCH')
    status = native._status(_read(original['statusPin'], selection, deadline))
    require(status['Pid'] == str(identity['pid']) and status['PPid'] == str(identity['parentPid']) and
            status['Uid'].split() == [str(identity[k]) for k in ('realUid', 'uid', 'savedUid', 'filesystemUid')] and
            status['Gid'].split() == [str(identity[k]) for k in ('realGid', 'gid', 'savedGid', 'filesystemGid')],
            'REPOSITORY_BROWSER_KERNEL_STATUS_MISMATCH')
    fields = _read(original['statPin'], selection, deadline).decode('ascii').rsplit(')', 1)
    require(len(fields) == 2 and fields[0].split(' ', 1)[0] == str(identity['pid']) and
            int(fields[1].split()[1]) == identity['parentPid'] and
            int(fields[1].split()[19]) == identity['startTicks'],
            'REPOSITORY_BROWSER_START_TICKS_CHANGED')
    maps = native._maps(_read(original['mapsPin'], selection, deadline))
    require(any(path == identity['exePin']['path'] for path, _, _ in maps),
            'REPOSITORY_BROWSER_KERNEL_EXECUTABLE_UNPROVED')
    # Every role selects an explicit independently protected cross-view record.
    # This is required even when both views refer to the same inode; there is
    # no implicit copied-file or permission-based admission path.
    mapping = _raw_original(original['mappedFileOriginalsPin'], state,
                            'RepositoryLabBrowserMappedFileOriginal/v1', deadline)
    require(set(mapping) == {'schemaVersion', 'observedAt', 'browserIdentitySelectionPin', 'pid', 'startTicks',
                            'mountNamespace', 'rootDevice', 'rootInode', 'files'} and
            mapping['browserIdentitySelectionPin'] == state['selectionPin'] and
            all(mapping[k] == identity[k] for k in ('pid', 'startTicks', 'mountNamespace', 'rootDevice', 'rootInode')) and
            len(mapping['files']) == len(maps) and
            {v['pin']['path'] for v in mapping['files']} == {path for path, _, _ in maps},
            'REPOSITORY_BROWSER_CROSS_VIEW_ORIGINAL_REQUIRED')
    mapped = {v['pin']['path']: v for v in mapping['files']}
    current_mounts = native._mounts(native._kernel('/proc/self/mountinfo', deadline=deadline))
    for path, device, inode in maps:
        access = state['sources'].get(path)
        require(access is not None and set(access['roles']) & {'native-tool', 'native-manager', 'native-library', 'native-interpreter', 'installed-binary', 'installed-python'},
                'REPOSITORY_NATIVE_MAPPING_NOT_INSTALLED')
        info, _, _, _ = _stream(access['pin'], state, access['roles'][0], deadline)
        row = mapped[path]
        require(set(row) == {'pin', 'originalMetadata', 'originalReopenedMetadata', 'browserMetadata',
                            'originalMount', 'browserMount', 'openReturn', 'bytesRead', 'sha256'} and
                row['pin'] == access['pin'] and row['originalMetadata'] == row['originalReopenedMetadata'] and
                row['browserMetadata'] == _metadata(info) and row['browserMount'] == _mount_original(path, current_mounts) and
                type(row['openReturn']) is int and row['openReturn'] == 0 and
                type(row['bytesRead']) is int and row['bytesRead'] == access['pin']['bytes'] and
                row['sha256'] == access['pin']['sha256'], 'REPOSITORY_BROWSER_CROSS_VIEW_ORIGINAL_REQUIRED')
        metadata = row['originalMetadata']
        require(set(metadata) == set(_metadata(info)) and metadata['ownerUid'] == metadata['ownerGid'] == 0 and
                re.fullmatch('[0-7]{4}', metadata['mode']) and not (int(metadata['mode'], 8) & 0o022) and metadata['links'] == 1 and
                metadata['bytes'] == access['pin']['bytes'] and
                (os.major(metadata['device']), os.minor(metadata['device'])) == tuple(int(v, 16) for v in device.split(':')) and
                metadata['inode'] == inode, 'REPOSITORY_NATIVE_MAPPING_CHANGED')
        mount = row['originalMount']
        require(set(mount) == {'mountId', 'fields', 'filesystemFields'} and
                type(mount['mountId']) is int and str(mount['mountId']) == mount['fields'][0],
                'REPOSITORY_BROWSER_CROSS_VIEW_MOUNT_REQUIRED')
        native._readonly_mount((tuple(mount['fields']), tuple(mount['filesystemFields'])))
    security = identity['security']
    current = _raw_original(security['securityOriginalPin'], state, 'RepositoryLabBrowserSecurityOriginal/v1', deadline)
    require(set(current) == {'schemaVersion', 'observedAt', 'pid', 'startTicks', 'native'} and
            current['pid'] == identity['pid'] and current['startTicks'] == identity['startTicks'],
            'REPOSITORY_BROWSER_SECURITY_ORIGINAL_MISMATCH')
    native_security = current['native']
    expected_security = {k: v for k, v in security.items() if not k.endswith('Pin')}
    require(all(native_security.get(k) == v for k, v in expected_security.items()),
            'REPOSITORY_BROWSER_SECURITY_ORIGINAL_MISMATCH')
    require(security['ambientEvidencePin'] == security['getNoNewPrivsEvidencePin'] == security['securityOriginalPin'],
            'REPOSITORY_BROWSER_SECURITY_API_EVIDENCE_REQUIRED')
    if role == 'AUTHORITY_A':
        require(native_security.get('dumpable') == 0, 'REPOSITORY_BROWSER_A_DUMPABLE_REFUSED')
    for field, key in [('CapEff', 'capEff'), ('CapPrm', 'capPrm'), ('CapInh', 'capInh'), ('CapBnd', 'capBnd')]:
        require(field in status and int(status[field], 16) == int(security[key], 16),
                'REPOSITORY_BROWSER_KERNEL_SECURITY_MISMATCH')
    if 'CapAmb' in status:
        require(security['capAmb'] is not None and int(status['CapAmb'], 16) == int(security['capAmb'], 16),
                'REPOSITORY_BROWSER_KERNEL_SECURITY_MISMATCH')
    if 'NoNewPrivs' in status:
        require(status['NoNewPrivs'] == '1', 'REPOSITORY_BROWSER_KERNEL_SECURITY_MISMATCH')
    require('Groups' in status and status['Groups'].split() == [], 'REPOSITORY_BROWSER_GROUPS_REFUSED')
    return original


def _same_identity(current, prior):
    def identity_fields(value):
        return {k: ({name: item for name, item in v.items() if not name.endswith('Pin')}
                    if k == 'security' else v) for k, v in value.items() if k != 'kernelIdentityOriginalPin'}
    return identity_fields(current) == identity_fields(prior)


def _self_current(identity, state, deadline):
    selection = state['selection']
    require(os.getpid() == identity['pid'] and os.getppid() == identity['parentPid'] and
            os.getresuid() == (selection['browserUid'],) * 3 and
            os.getresgid() == (selection['browserGid'],) * 3, 'REPOSITORY_BROWSER_ACTUAL_IDENTITY_MISMATCH')
    values = native._status(native._kernel('/proc/self/status', deadline=deadline))
    require(values['Uid'].split() == [str(selection['browserUid'])] * 4 and
            values['Gid'].split() == [str(selection['browserGid'])] * 4 and 'Groups' in values and
            values['Groups'].split() == [], 'REPOSITORY_BROWSER_ACTUAL_IDENTITY_MISMATCH')
    actual = measure_security()
    require(all((int(actual[k], 16) == int(v, 16) if k.startswith('cap') and v is not None else actual.get(k) == v)
                for k, v in identity['security'].items() if not k.endswith('Pin')),
            'REPOSITORY_BROWSER_ACTUAL_SECURITY_MISMATCH')
    for key, kind in [('pidNamespace', 'pid'), ('mountNamespace', 'mnt'), ('networkNamespace', 'net'), ('userNamespace', 'user')]:
        require(os.readlink('/proc/self/ns/' + kind) == identity[key], 'REPOSITORY_BROWSER_ACTUAL_NAMESPACE_MISMATCH')
    require(os.readlink('/proc/self/exe') == identity['exePin']['path'], 'REPOSITORY_BROWSER_ACTUAL_EXECUTABLE_MISMATCH')
    exe_info, _, _, _ = _stream(identity['exePin'], state, 'installed-python', deadline)
    exe_fd = os.open('/proc/self/exe', os.O_RDONLY | os.O_CLOEXEC)
    try:
        held = os.fstat(exe_fd)
        require(native._meta(held) == native._meta(exe_info), 'REPOSITORY_BROWSER_ACTUAL_EXECUTABLE_MISMATCH')
        count, digest = 0, hashlib.sha256()
        while True:
            native._remaining(deadline)
            block = os.read(exe_fd, min(native.CHUNK, identity['exePin']['bytes'] - count + 1))
            if not block:
                break
            count += len(block)
            require(count <= identity['exePin']['bytes'], 'REPOSITORY_PIN_CHANGED')
            digest.update(block)
        require(count == identity['exePin']['bytes'] and digest.hexdigest() == identity['exePin']['sha256'] and
                native._meta(os.fstat(exe_fd)) == native._meta(held), 'REPOSITORY_BROWSER_ACTUAL_EXECUTABLE_MISMATCH')
    finally:
        os.close(exe_fd)
    require(native._kernel('/proc/sys/kernel/random/boot_id', 256, deadline).decode('ascii').strip() == identity['bootId'],
            'REPOSITORY_BROWSER_ACTUAL_BOOT_MISMATCH')
    host_source = state['sources'].get('/etc/machine-id')
    require(host_source is not None and _read(host_source['pin'], selection, deadline).decode('ascii').strip() == identity['hostId'],
            'REPOSITORY_BROWSER_ACTUAL_HOST_MISMATCH')
    fd = _directory('/', selection, deadline)
    try:
        info = os.fstat(fd)
        require((info.st_dev, info.st_ino) == (identity['rootDevice'], identity['rootInode']),
                'REPOSITORY_BROWSER_ACTUAL_ROOT_MISMATCH')
    finally:
        os.close(fd)
    # Procfs is independently verified by native._kernel before these fixed self links.
    with open('/proc/self/stat', 'rb') as stream:
        raw_stat = stream.read(65537)
    require(len(raw_stat) <= 65536, 'REPOSITORY_RECORD_TOO_LARGE')
    fields = raw_stat.decode('ascii').rsplit(')', 1)
    require(len(fields) == 2 and fields[0].split(' ', 1)[0] == str(identity['pid']) and
            int(fields[1].split()[1]) == identity['parentPid'] and
            int(fields[1].split()[19]) == identity['startTicks'],
            'REPOSITORY_BROWSER_ACTUAL_START_TICKS_MISMATCH')
    maps = native._kernel('/proc/self/maps', deadline=deadline)
    for path, device, inode in native._maps(maps):
        access = state['sources'].get(path)
        require(access is not None and set(access['roles']) & {'native-tool', 'native-manager', 'native-library', 'native-interpreter', 'installed-binary', 'installed-python'},
                'REPOSITORY_NATIVE_MAPPING_NOT_INSTALLED')
        info, _, _, _ = _stream(access['pin'], state, access['roles'][0], deadline)
        require((os.major(info.st_dev), os.minor(info.st_dev)) == tuple(int(v, 16) for v in device.split(':')) and
                info.st_ino == inode, 'REPOSITORY_NATIVE_MAPPING_CHANGED')


def _access_current(guard, state, deadline):
    selection = state['selection']
    dirs = _raw_original(guard['directoryAccessEvidencePin'], state, 'RepositoryLabBrowserDirectoryAccessOriginal/v1', deadline)
    reads = _raw_original(guard['completeSourceReadEvidencePin'], state, 'RepositoryLabBrowserSourceReadOriginal/v1', deadline)
    mounts = native._mounts(native._kernel('/proc/self/mountinfo', deadline=deadline))
    for value in (dirs, reads):
        require(value['browserIdentitySelectionPin'] == state['selectionPin'] and
            value['producerPid'] == guard['producerIdentity']['pid'] and
            value['producerStartTicks'] == guard['producerIdentity']['startTicks'],
                'REPOSITORY_BROWSER_ACCESS_IDENTITY_MISMATCH')
    required_dirs = {v['path'] for v in selection['directoryAccess'] if v['usage'] != 'A_SECRET_PARENT'}
    require(len(dirs['directories']) == len(required_dirs) and
            {v['path'] for v in dirs['directories']} == required_dirs,
            'REPOSITORY_BROWSER_DIRECTORY_GRAPH_INCOMPLETE')
    for value in dirs['directories']:
        selected_dir = next(v for v in selection['directoryAccess'] if v['path'] == value['path'])
        fd = _directory(value['path'], selection, deadline)
        try:
            actual_metadata = _metadata(os.fstat(fd))
            stable = ('device', 'inode', 'ownerUid', 'ownerGid', 'mode', 'links')
            # Publishing a later guard changes writable-directory timestamps.
            # The measured open/reopen pair must agree; current stable identity
            # and every actual read's own held/reopened checks remain mandatory.
            require(value.get('reopenedMetadata') == value['metadata'] and
                    (value['metadata'] == actual_metadata if selected_dir['readOnly'] else
                     all(value['metadata'][k] == actual_metadata[k] for k in stable)) and
                    type(value['traverseOpenReturn']) is int and value['traverseOpenReturn'] == 0 and
                    value.get('mount') == _mount_original(value['path'], mounts),
                    'REPOSITORY_BROWSER_DIRECTORY_READ_CHANGED')
        finally:
            os.close(fd)
        if selected_dir['usage'] in ('BROWSER_CWD', 'BROWSER_OUTPUT'):
            require(type(value.get('createReturn')) is int and value['createReturn'] == 0 and
                    value.get('createOriginalPin') is not None,
                    'REPOSITORY_BROWSER_ACTUAL_CREATE_UNPROVED')
            with _original(value['createOriginalPin'], selection, deadline=deadline):
                pass
    require(len(reads['sources']) == len(state['sources']) and
            {v['pin']['path'] for v in reads['sources']} == set(state['sources']),
            'REPOSITORY_BROWSER_SOURCE_READ_GRAPH_INCOMPLETE')
    for value in reads['sources']:
        access = state['sources'][value['pin']['path']]
        require(value['pin'] == access['pin'] and type(value['openReturn']) is int and value['openReturn'] == 0 and
                value.get('mount') == _mount_original(value['pin']['path'], mounts),
                'REPOSITORY_BROWSER_SOURCE_READ_CHANGED')
        info, _, _, _ = _stream(access['pin'], state, access['roles'][0], deadline)
        require(value.get('reopenedMetadata') == value['metadata'] == _metadata(info),
                'REPOSITORY_BROWSER_SOURCE_READ_CHANGED')
    denial = _raw_original(guard['workerKeyDenialEvidencePin'], state, 'RepositoryLabBrowserKeyDenialOriginal/v1', deadline)
    expected_paths = [selection['privateKeyPin']['path'], '/proc/' + str(guard['signerIdentity']['pid']) + '/root' +
                      selection['privateKeyPin']['path'], '/proc/' + str(guard['signerIdentity']['pid']) + '/mem']
    require(denial['browserIdentitySelectionPin'] == state['selectionPin'] and
            denial['producerIdentity'] == guard['producerIdentity'] and
            denial['signerIdentity'] == guard['signerIdentity'] and len(denial['attempts']) == 3 and
            [v['path'] for v in denial['attempts']] == expected_paths and
            all(type(v['returnValue']) is int and v['returnValue'] == -1 and type(v['errno']) is int and
                v['errno'] in (errno.EACCES, errno.EPERM) and type(v['bytesRead']) is int and
                v['bytesRead'] == 0 for v in denial['attempts']), 'REPOSITORY_BROWSER_KEY_DENIAL_UNPROVED')


def _qualification_authority(intent_pin, grant_pin, lease_pin, state, deadline, *, accepted_window=None):
    selection = state['selection']
    intent = _signed(intent_pin, state['authorities'], selection, deadline)
    grant = _signed(grant_pin, state['authorities'], selection, deadline)
    lease = _signed(lease_pin, state['authorities'], selection, deadline)
    scope = _signed(selection['sourceScopePin'], state['authorities'], selection, deadline)
    _authorized_intent(intent, grant, lease, scope, grant_pin, lease_pin, state, deadline,
                       accepted_window=accepted_window)
    return intent


def _authorized_intent(intent, grant, lease, scope, grant_pin, lease_pin, state, deadline, *, accepted_window=None):
    """Typed semantics after independent authentication, for either batch."""
    selection = state['selection']
    for value, schema in [(intent, 'RepositoryLabNativeQualificationIntent/v2'),
                          (grant, 'RepositoryLabNativeQualificationAuthorization/v2'),
                          (lease, 'RepositoryLabNativeQualificationLease/v2')]:
        validate_record(value, schema, deadline)
        start = 'issuedAt' if value is intent else 'notBefore'
        if accepted_window is None:
            _window(value, start=start)
        else:
            first, last = map(timestamp, accepted_window)
            require(timestamp(value[start]) <= first <= last < timestamp(value['expiresAt']) and
                    last <= datetime.now(timezone.utc), 'REPOSITORY_BROWSER_AUTHORITY_NOT_CURRENT')
        for field in ('rehearsalId', 'qualificationId', 'operationId', 'phase', 'hostId', 'targetId', 'executorId',
                      'browserIdentitySelectionPin', 'browserRuntimeProofPin', 'sourceScopePin', 'installationPin'):
            require(value[field] == intent[field], 'REPOSITORY_BROWSER_PRIVATE_AUTHORITY_MISMATCH')
    require(intent['browserIdentitySelectionPin'] == state['selectionPin'] and
            intent['browserRuntimeProofPin'] == state['proofPin'] and intent['authorityKeyPin'] == selection['authorityKeyPin'] and
            intent['installationPin'] == selection['executorInstallationPin'] and intent['sourceScopePin'] == selection['sourceScopePin'] and
            intent['authorizationPin'] == grant_pin and intent['leasePin'] == lease_pin and
            intent['rehearsalId'] == native.LAB_ID,
            'REPOSITORY_BROWSER_PRIVATE_AUTHORITY_MISMATCH')
    require(intent['hostId'] == selection['hostId'] and intent['targetId'] == selection['targetId'] and
            intent['executorId'] == selection['executorId'], 'REPOSITORY_BROWSER_PRIVATE_AUTHORITY_MISMATCH')
    require(timestamp(state['proof']['issuedAt']) <= timestamp(intent['issuedAt']) < timestamp(intent['expiresAt']) <=
            timestamp(state['proof']['expiresAt']), 'REPOSITORY_BROWSER_OUTLIVES_AUTHORITY')
    require((timestamp(intent['expiresAt']) - timestamp(intent['issuedAt'])).total_seconds() * 1000 <=
            intent['deadlineMilliseconds'], 'REPOSITORY_BROWSER_OUTLIVES_AUTHORITY')
    require(timestamp(intent['issuedAt']) >= timestamp(grant['notBefore']) and
            timestamp(intent['issuedAt']) >= timestamp(lease['notBefore']) and
            timestamp(intent['expiresAt']) <= min(timestamp(grant['expiresAt']), timestamp(lease['expiresAt'])),
            'REPOSITORY_BROWSER_OUTLIVES_AUTHORITY')
    exact(scope, 'schemaVersion rehearsalId repositoryId sourceIdentityPin host root resourcePrefix allowedActions expiresAt',
          'RepositoryLabScope/v1')
    from repository_native_lab import LAB_ACTIONS
    require(scope['rehearsalId'] == native.LAB_ID and scope['host'] == '172.30.30.59' and
            scope['root'] == native.LAB_ROOT and scope['resourcePrefix'] == 'brlab-20261012' and
            type(scope['allowedActions']) is list and len(scope['allowedActions']) == len(LAB_ACTIONS) and
            all(type(a) is str for a in scope['allowedActions']) and set(scope['allowedActions']) == LAB_ACTIONS and
            timestamp(intent['expiresAt']) <= timestamp(scope['expiresAt']), 'REPOSITORY_BROWSER_BUSINESS_SCOPE_INVALID')
    expected_action = ('BROWSER_NATIVE_CAPABILITY_PROBE' if intent['phase'] == 'NATIVE_BROWSER_CAPABILITY' else 'BROWSER_ABOUT_BLANK')
    command = intent['commandSelections'][0]
    expected_argv = selection['capabilityProbeArgv'] if expected_action == 'BROWSER_NATIVE_CAPABILITY_PROBE' else [
        native.BROWSER_ROOT + '/chrome-headless-shell', '--headless', '--disable-gpu', '--dump-dom', 'about:blank']
    require(grant['approved'] is True and grant['actions'] == [expected_action] and command['action'] == expected_action and
            lease['state'] == 'HELD' and type(lease['fenceToken']) is int and lease['fenceToken'] > 0 and
            command['argv'] == expected_argv and command['cwd'] == selection['workingDirectory'] and
            len(command['sourcePins']) == len(state['sources']) and
            {canonical(p) for p in command['sourcePins']} == {canonical(v['pin']) for v in state['sources'].values()},
            'REPOSITORY_BROWSER_FINITE_COMMAND_INVALID')
    if expected_action == 'BROWSER_NATIVE_CAPABILITY_PROBE':
        require(intent['sandboxCapabilityResultPin'] is None, 'REPOSITORY_BROWSER_CAPABILITY_PHASE_INVALID')


def _guard_authority(guard, state, deadline):
    intent = _qualification_authority(guard['qualificationIntentPin'], guard['authorizationPin'], guard['leasePin'],
                                      state, deadline)
    if intent['phase'] == 'NATIVE_BROWSER_QUALIFICATION':
        require(intent['sandboxCapabilityResultPin'] is not None, 'REPOSITORY_BROWSER_SANDBOX_CAPABILITY_REQUIRED')
        result = _signed(intent['sandboxCapabilityResultPin'], state['authorities'], state['selection'], deadline)
        validate_record(result, 'SandboxCapabilityResult', deadline); _window(result, parent=state['proof'])
        require(result['browserIdentitySelectionPin'] == state['selectionPin'] and result['browserRuntimeProofPin'] == state['proofPin'],
                'REPOSITORY_BROWSER_SANDBOX_CAPABILITY_MISMATCH')
        _capability_current(result, state, deadline)
    return intent


def _capability_process_bindings(process, result, cap_intent, state, deadline):
    selection = state['selection']
    validate_record(process, 'RepositoryLabNativeQualificationProcessInvocation/v2', deadline)
    require(process['phase'] == 'NATIVE_BROWSER_CAPABILITY' and process['command'] == 'BROWSER_NATIVE_CAPABILITY_PROBE' and
            process['argv'] == selection['capabilityProbeArgv'] and process['cwd'] == selection['workingDirectory'] and
            process['nativeRuntimeProofPin'] == process['browserRuntimeProofPin'] == state['proofPin'] and
            process['browserIdentitySelectionPin'] == state['selectionPin'] and
            process['producerIdentityPin'] == state['identityPin'] and
            process['pythonPin'] == state['installation']['pythonPin'] and
            state['sources'].get(process['supervisorPin']['path'], {}).get('pin') == process['supervisorPin'] and
            all(process[k] == state['proof']['producerIdentity'][k] for k in
                ('bootId', 'pidNamespace', 'mountNamespace', 'networkNamespace', 'userNamespace')) and
            process['uid'] == selection['browserUid'] and process['gid'] == selection['browserGid'] and
            process['terminationKind'] == 'EXITED' and process['actualExitCode'] == 0 and process['waitStatus'] == 0 and
            process['descendantState'] == 'REAPED' and process['sandboxEvidencePin'] is None and
            len(process['sourcePins']) == len(state['sources']) and
            {canonical(p) for p in process['sourcePins']} == {canonical(v['pin']) for v in state['sources'].values()},
            'REPOSITORY_BROWSER_SANDBOX_PROCESS_UNPROVED')
    require(timestamp(state['proof']['issuedAt']) <= timestamp(process['startedAt']) <= timestamp(process['finishedAt']) <=
            timestamp(result['issuedAt']), 'REPOSITORY_BROWSER_SANDBOX_PROCESS_UNPROVED')
    require(result['rehearsalId'] == cap_intent['rehearsalId'] and
            result['browserIdentitySelectionPin'] == cap_intent['browserIdentitySelectionPin'] and
            result['browserRuntimeProofPin'] == cap_intent['browserRuntimeProofPin'] and
            process['commandId'] == cap_intent['commandSelections'][0]['commandId'],
            'REPOSITORY_BROWSER_SANDBOX_PROCESS_UNPROVED')
    require(cap_intent['phase'] == 'NATIVE_BROWSER_CAPABILITY' and cap_intent['sandboxCapabilityResultPin'] is None and
            all(process[k] == cap_intent[k] for k in ('rehearsalId', 'qualificationId', 'operationId', 'phase', 'hostId',
                'targetId', 'executorId', 'browserIdentitySelectionPin', 'browserRuntimeProofPin')) and
            timestamp(cap_intent['issuedAt']) <= timestamp(process['startedAt']) and
            timestamp(process['finishedAt']) <= timestamp(cap_intent['expiresAt']),
            'REPOSITORY_BROWSER_SANDBOX_PROCESS_UNPROVED')


def _capability_current(result, state, deadline):
    selection = state['selection']
    validate_record(result, 'SandboxCapabilityResult', deadline); _window(result, parent=state['proof'])
    process = _signed(result['processResultPin'], state['authorities'], selection, deadline)
    validate_record(process, 'RepositoryLabNativeQualificationProcessInvocation/v2', deadline)
    cap_intent = _signed(result['qualificationIntentPin'], state['authorities'], selection, deadline)
    validate_record(cap_intent, 'RepositoryLabNativeQualificationIntent/v2', deadline)
    authenticated = _qualification_authority(result['qualificationIntentPin'], cap_intent['authorizationPin'],
        cap_intent['leasePin'], state, deadline, accepted_window=(process['startedAt'], result['issuedAt']))
    require(authenticated == cap_intent, 'REPOSITORY_BROWSER_SANDBOX_PROCESS_UNPROVED')
    _capability_process_bindings(process, result, cap_intent, state, deadline)
    original = document(_read(process['stdoutPin'], selection, deadline))
    require(original.get('schemaVersion') == 'RepositoryLabBrowserNativeCapabilityOriginal/v1' and
            original['uid'] == selection['browserUid'] and original['gid'] == selection['browserGid'] and
            original['kernelRelease'] == result['kernelRelease'] == os.uname().release,
            'REPOSITORY_BROWSER_SANDBOX_CAPABILITY_MISMATCH')
    require(original['pid'] == process['childPid'] and original['startTicks'] == process['childStartTicks'] and
            original['parentPid'] == process['supervisorPid'] and
            all(original[k] == process[k] for k in
                ('bootId', 'pidNamespace', 'mountNamespace', 'networkNamespace', 'userNamespace')) and
            original['security'] == {k: v for k, v in state['proof']['producerIdentity']['security'].items()
                                     if not k.endswith('Pin')},
            'REPOSITORY_BROWSER_SANDBOX_INITIAL_B_UNPROVED')
    authority = _signed(process['authorityIdentityPin'], state['authorities'], selection, deadline)
    validate_record(authority, 'ParticipantIdentity', deadline)
    require(authority['role'] == 'AUTHORITY_A' and authority['browserIdentitySelectionPin'] == state['selectionPin'] and
            authority['browserRuntimeProofPin'] == state['proofPin'] and
            _same_identity(authority['identity'], state['proof']['signerIdentity']),
            'REPOSITORY_BROWSER_SANDBOX_AUTHORITY_UNPROVED')
    for current_pin in process['currentGuardMeasurementPins']:
        measured = _signed(current_pin, state['authorities'], selection, deadline)
        validate_record(measured, 'GuardMeasurement', deadline)
        require(measured['browserIdentitySelectionPin'] == state['selectionPin'] and
                measured['browserRuntimeProofPin'] == state['proofPin'] and
                measured['qualificationIntentPin'] == result['qualificationIntentPin'] and
                measured['authorizationPin'] == cap_intent['authorizationPin'] and measured['leasePin'] == cap_intent['leasePin'] and
                _same_identity(measured['producerIdentity'], state['proof']['producerIdentity']) and
                timestamp(cap_intent['issuedAt']) <= timestamp(measured['measuredAt']) <= timestamp(process['finishedAt']),
                'REPOSITORY_BROWSER_SANDBOX_GUARDS_UNPROVED')
    probes = {p['name']: p for p in result['probes']}
    actual = {p['name']: p for p in original['probes']}
    required = {'userns-map', 'nested-userns', 'pid-network-namespace', 'seccomp-bpf'}
    require(len(probes) == len(result['probes']) and len(actual) == len(original['probes']) and
            set(probes) == set(actual) == required | {'seccomp-tsync'}, 'REPOSITORY_BROWSER_SANDBOX_CAPABILITY_UNPROVED')
    for name, probe in probes.items():
        item = actual[name]
        require(probe['originalPin'] == process['stdoutPin'] and
                all(probe[k] == item[k] for k in ('state', 'returnValue', 'errno')) and item['reaped'] is True and
                type(item['waitStatus']) is int and item['waitStatus'] == 0,
                'REPOSITORY_BROWSER_SANDBOX_CAPABILITY_UNPROVED')
        if name in required:
            require(probe['state'] == 'PASSED' and probe['returnValue'] == probe['errno'] == 0,
                    'REPOSITORY_BROWSER_SANDBOX_CAPABILITY_UNPROVED')
    for name in ('userns-map', 'nested-userns', 'pid-network-namespace'):
        for key in ('uidMap', 'gidMap'):
            fields = actual[name][key].split()
            external = selection['browserUid'] if key == 'uidMap' else selection['browserGid']
            if name == 'nested-userns':
                external = 0  # Explicit local-parent mapping; first level is separately proven B only.
            require(fields == ['0', str(external), '1'], 'REPOSITORY_BROWSER_NAMESPACE_MAPPING_UNPROVED')
    require(actual['seccomp-bpf']['auxiliaryReturn'] == -1 and actual['seccomp-bpf']['auxiliaryErrno'] == errno.EACCES,
            'REPOSITORY_BROWSER_SECCOMP_BPF_UNPROVED')
    # TSYNC availability is retained separately; the selected Chromium path's
    # requirement is decided by root using the actual sandbox transition proof.
    for key in ('kernelConfigurationEvidencePin', 'containerSecurityPolicyEvidencePin'):
        _read(result[key], selection, deadline)


def _bootstrap_current(state, deadline):
    value = _raw_original(state['proof']['bootstrapOriginalPin'], state, 'RepositoryLabBrowserBootstrapOriginal/v1', deadline)
    expected = {'schemaVersion', 'observedAt', 'browserIdentitySelectionPin', 'launcherPin', 'brokerIdentity',
                'ownedChildren', 'setupSecurityOriginalPin', 'identitySetReturn', 'groupsClearReturn',
                'namespaceSetupReturn', 'browserDropReturn', 'signerDropReturn', 'unusedDescriptorsClosed'}
    require(set(value) == expected and value['browserIdentitySelectionPin'] == state['selectionPin'] and
            value['launcherPin'] == state['selection']['bootstrapLauncherPin'] and value['unusedDescriptorsClosed'] is True and
            all(type(value[k]) is int and value[k] == 0 for k in
                ('identitySetReturn', 'groupsClearReturn', 'namespaceSetupReturn', 'browserDropReturn', 'signerDropReturn')),
            'REPOSITORY_BROWSER_PRIVILEGED_BOOTSTRAP_UNPROVED')
    broker = value['brokerIdentity']
    _broker_identity(broker, 'CONTROLLER', state, deadline)
    require(broker['exePin'] == value['launcherPin'] and
            value['ownedChildren'] == [{'pid': state['proof'][k]['pid'], 'startTicks': state['proof'][k]['startTicks']}
                                      for k in ('producerIdentity', 'signerIdentity')] and
            all(state['proof'][k]['parentPid'] == broker['pid'] for k in ('producerIdentity', 'signerIdentity')),
            'REPOSITORY_BROWSER_BOOTSTRAP_OWNERSHIP_UNPROVED')
    setup = _raw_original(value['setupSecurityOriginalPin'], state, 'RepositoryLabBrowserSetupSecurityOriginal/v1', deadline)
    require(set(setup) == {'schemaVersion', 'observedAt', 'pid', 'startTicks', 'capEff', 'capPrm', 'setupAuthority'} and
            setup['pid'] == broker['pid'] and setup['startTicks'] == broker['startTicks'] and
            type(setup['capEff']) is str and type(setup['capPrm']) is str and
            int(setup['capEff'], 16) & ((1 << 6) | (1 << 7) | (1 << 21)) == ((1 << 6) | (1 << 7) | (1 << 21)) and
            int(setup['capPrm'], 16) & int(setup['capEff'], 16) == int(setup['capEff'], 16) and
            setup['setupAuthority'] == 'EXISTING_SELECTED_PRE_DROP_AUTHORITY',
            'REPOSITORY_BROWSER_PRE_DROP_AUTHORITY_UNPROVED')


def _browser_inventory(state, deadline):
    from repository_native_browser_resources import BROWSER_RESOURCE_ORIGINALS
    selected = {p for p in state['catalog'] if p.startswith(native.BROWSER_ROOT + '/')}
    names = set(BROWSER_RESOURCE_ORIGINALS) | {'chrome-headless-shell', 'libEGL.so', 'libGLESv2.so',
                                              'libvk_swiftshader.so', 'libvulkan.so.1'}
    require(selected == {native.BROWSER_ROOT + '/' + name for name in names},
            'REPOSITORY_BROWSER_COMPLETE_VENDOR_GRAPH_REQUIRED')
    actual = set()
    def walk(path):
        fd = _directory(path, state['selection'], deadline)
        try:
            for name in os.listdir(fd):
                native._remaining(deadline)
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                child = path + '/' + name
                if stat.S_ISDIR(info.st_mode):
                    walk(child)
                else:
                    require(stat.S_ISREG(info.st_mode), 'REPOSITORY_BROWSER_VENDOR_LINK_OR_TYPE_REFUSED')
                    actual.add(child)
                    require(len(actual) <= 4096, 'REPOSITORY_LAB_PIN_GRAPH_TOO_LARGE')
        finally:
            os.close(fd)
    walk(native.BROWSER_ROOT)
    require(actual == selected, 'REPOSITORY_BROWSER_VENDOR_GRAPH_MISMATCH')


def _check_current(state, deadline):
    _platform(); native._remaining(deadline)
    selection = state['selection']
    for pin_key, value_key in [('selectionPin', 'selection'), ('trustPin', 'trust'), ('proofPin', 'proof'),
                               ('identityPin', 'identity'), ('guardPin', 'guard')]:
        require(_signed(state[pin_key], state['authorities'], selection, deadline) == state[value_key],
                'REPOSITORY_BROWSER_SIGNED_INPUT_CHANGED')
    _proof_shape(state['proof'], state['trust'], state['trustPin'], state['selectionPin'], selection)
    installation = _signed(selection['executorInstallationPin'], state['authorities'], selection, deadline)
    require(installation == state['installation'], 'REPOSITORY_NATIVE_INSTALLATION_CHANGED')
    root_trust = _signed(installation['nativeRuntimeTrustPin'], state['authorities'], selection, deadline)
    root_proof = _signed(installation['nativeRuntimeProofPin'], state['authorities'], selection, deadline)
    native._trust_shape(root_trust); native._proof_shape(root_proof, root_trust, installation['nativeRuntimeTrustPin'])
    manager = state['proof']['managerIdentity']
    require(all(manager[k] == root_proof[k] for k in ('hostId', 'bootId', 'pidNamespace', 'mountNamespace',
                'networkNamespace', 'userNamespace', 'rootDevice', 'rootInode')) and
            manager['startTicks'] == root_proof['managerStartTicks'], 'REPOSITORY_BROWSER_ROOT_ANCESTRY_MISMATCH')
    runtime_env = dict(selection['environment'])
    if 'INTRUOYI_NATIVE_DEADLINE_MONOTONIC' in os.environ:
        value = float(os.environ['INTRUOYI_NATIVE_DEADLINE_MONOTONIC'])
        require(math.isfinite(value) and time.monotonic() < value <= deadline,
                'REPOSITORY_NATIVE_DEADLINE_INVALID')
        runtime_env['INTRUOYI_NATIVE_DEADLINE_MONOTONIC'] = os.environ['INTRUOYI_NATIVE_DEADLINE_MONOTONIC']
    require(dict(os.environ) == runtime_env, 'REPOSITORY_BROWSER_ENVIRONMENT_MISMATCH')
    guard = validate_record(state['guard'], 'GuardMeasurement', deadline)
    _window(guard, start='measuredAt', parent=state['proof'])
    require((datetime.now(timezone.utc) - timestamp(guard['measuredAt'])).total_seconds()*1000 <= selection['maximumAgeMilliseconds'] and
            guard['browserIdentitySelectionPin'] == state['selectionPin'] and guard['browserRuntimeProofPin'] == state['proofPin'],
            'REPOSITORY_BROWSER_CURRENT_BROKER_MEASUREMENT_REQUIRED')
    for key, role in [('managerIdentity', 'MANAGER'), ('producerIdentity', 'BROWSER_PRODUCER'), ('signerIdentity', 'AUTHORITY_A')]:
        require(_same_identity(guard[key], state['proof'][key]), 'REPOSITORY_BROWSER_CURRENT_ROLE_CHANGED')
        _broker_identity(guard[key], role, state, deadline)
    _identity_shape(guard['controllerIdentity'], 'CONTROLLER', selection)
    _broker_identity(guard['controllerIdentity'], 'CONTROLLER', state, deadline)
    controller = _signed(selection['controllerIdentityPin'], state['authorities'], selection, deadline)
    require(controller.get('schemaVersion') == 'RepositoryLabNativeCaller/v1' and
            controller.get('nativeRuntimeProofPin') == selection['controllerRuntimeProofPin'] and
            all(controller.get(k) == guard['controllerIdentity'][k] for k in
                ('pid', 'startTicks', 'uid', 'gid', 'hostId', 'bootId', 'pidNamespace', 'mountNamespace',
                 'networkNamespace', 'userNamespace', 'rootDevice', 'rootInode')),
            'REPOSITORY_BROWSER_CONTROLLER_IDENTITY_MISMATCH')
    _window(controller)
    _self_current(guard['producerIdentity'], state, deadline)
    mounts = native._mounts(native._kernel('/proc/self/mountinfo', deadline=deadline))
    prior = native._mounts(_read(state['proof']['readOnlyMountEvidencePin'], selection, deadline))
    renewed_mounts = native._mounts(_read(guard['readOnlyMountEvidencePin'], selection, deadline))
    for path in ('/', state['trust']['backingRootPath'], *state['sources']):
        actual = native._mount_for(path, mounts)
        require(actual == native._mount_for(path, prior) == native._mount_for(path, renewed_mounts),
                'REPOSITORY_NATIVE_MOUNT_CHANGED')
        native._readonly_mount(actual)
    for snapshot in (state['proof'], guard):
        for key, role, original_field in [('managerIdentityEvidencePin', 'managerIdentity', 'statusPin'),
                                          ('nativeLinkageEvidencePin', 'producerIdentity', 'mapsPin')]:
            original = document(_read(snapshot[role]['kernelIdentityOriginalPin'], selection, deadline))
            require(_read(snapshot[key], selection, deadline) == _read(original[original_field], selection, deadline),
                    'REPOSITORY_BROWSER_KERNEL_EVIDENCE_MISMATCH')
    _access_current(guard, state, deadline)
    _guard_authority(guard, state, deadline)
    _bootstrap_current(state, deadline)
    _browser_inventory(state, deadline)
    import repository_records, repository_native_browser_resources, repository_native_lab
    for module_path in (Path(__file__), _SCHEMA_PATH, Path(native.__file__), Path(repository_records.__file__),
                        Path(repository_native_browser_resources.__file__), Path(repository_native_lab.__file__)):
        require(str(module_path.resolve()) in state['sources'], 'REPOSITORY_NATIVE_HELPER_NOT_INSTALLED')
    for pin in (state['selection']['capabilityProbeEntryPin'], state['selection']['producerEntryPin'],
                state['selection']['signerEntryPin']):
        require(state['sources'].get(pin['path'], {}).get('pin') == pin,
                'REPOSITORY_NATIVE_HELPER_NOT_INSTALLED')
    native._remaining(deadline)


def _batch_closure(state, deadline):
    records = state.get('graphRecords', {})
    guard, selection = state['guard'], state['selection']
    launches = [(path, value) for path, value in records.items()
                if value.get('schemaVersion') == 'RepositoryLabNativeQualificationLaunch/v2' and
                value.get('qualificationIntentPin') == guard['qualificationIntentPin']]
    require(len(launches) == 1, 'REPOSITORY_BROWSER_COMPLETE_GRAPH_REQUIRED')
    launch_path, launch = launches[0]
    validate_record(launch, 'RepositoryLabNativeQualificationLaunch/v2', deadline); _window(launch, parent=state['proof'])
    intent = records[guard['qualificationIntentPin']['path']]
    _window(launch, parent=intent)
    require(launch['rehearsalId'] == native.LAB_ID and
            launch['observationSocketPath'].startswith(selection['evidenceRoot'] + '/') and
            launch['observationSocketPath'] != selection['signerSocketPath'],
            'REPOSITORY_BROWSER_LAUNCH_SELECTION_MISMATCH')
    for key in ('authorityKeyPin', 'producerEntryPin', 'signerEntryPin'):
        require(launch[key] == selection[key], 'REPOSITORY_BROWSER_LAUNCH_SELECTION_MISMATCH')
    require(launch['authorizationPin'] == guard['authorizationPin'] and launch['leasePin'] == guard['leasePin'] and
            launch['allowedCallerPin'] == selection['controllerIdentityPin'] and launch['evidenceRoot'] == selection['evidenceRoot'] and
            launch['installationPin'] == selection['executorInstallationPin'] and
            launch['browserIdentitySelectionPin'] == state['selectionPin'] and launch['browserRuntimeProofPin'] == state['proofPin'],
            'REPOSITORY_BROWSER_LAUNCH_SELECTION_MISMATCH')
    provisions = [value for value in records.values()
                  if value.get('schemaVersion') == 'RepositoryLabNativeQualificationProvision/v2' and
                  value.get('launchPin') == state['graph'][launch_path]]
    require(len(provisions) == 1, 'REPOSITORY_BROWSER_COMPLETE_GRAPH_REQUIRED')
    provision = validate_record(provisions[0], 'RepositoryLabNativeQualificationProvision/v2', deadline)
    require(provision['producerIdentityPin'] == state['identityPin'] and
            provision['controllerIdentityPin'] == selection['controllerIdentityPin'] and
            provision['producerUid'] == selection['browserUid'] and provision['producerGid'] == selection['browserGid'] and
            all(provision[k] == selection[k] for k in ('privateKeyPin', 'signerUid', 'signerGid', 'signerRootPath',
                'signerSocketPath', 'workingDirectory', 'maximumAgeMilliseconds')) and
            provision['browserIdentitySelectionPin'] == state['selectionPin'] and provision['browserRuntimeProofPin'] == state['proofPin'],
            'REPOSITORY_BROWSER_PROVISION_SELECTION_MISMATCH')
    authorities = [v for v in records.values() if v.get('schemaVersion') == 'RepositoryLabBrowserParticipantIdentity/v1' and
                   v.get('role') == 'AUTHORITY_A' and v.get('browserIdentitySelectionPin') == state['selectionPin'] and
                   v.get('browserRuntimeProofPin') == state['proofPin']]
    require(len(authorities) == 1, 'REPOSITORY_BROWSER_COMPLETE_GRAPH_REQUIRED')
    authority = validate_record(authorities[0], 'ParticipantIdentity', deadline); _window(authority, parent=state['proof'])
    require(_same_identity(authority['identity'], state['proof']['signerIdentity']),
            'REPOSITORY_BROWSER_PARTICIPANT_IDENTITY_MISMATCH')


def verify_browser_runtime(browserTrustPin, browserProofPin, authorityPins, expectedIdentityPin,
                           deadline=None, *, browser_identity_selection_pin, private_key_metadata_pin, guard_pin,
                           graph_roots, reserved_output_paths):
    """Admit exact signed B originals; every current check needs a selected guard.

    All arguments are original Pins. graph_roots includes prior batch/launch/
    provision/principals and current output originals; reserved_output_paths is
    the finite literal prospective output set. Reservations are never file Pins.
    The independently selected private metadata is known before the first open.
    """
    _platform(); deadline = _budget(deadline)
    selection = _bootstrap_selection(browser_identity_selection_pin, authorityPins, private_key_metadata_pin, deadline)
    trust = _signed(browserTrustPin, authorityPins, selection, deadline)
    proof = _signed(browserProofPin, authorityPins, selection, deadline)
    identity = _signed(expectedIdentityPin, authorityPins, selection, deadline)
    guard = _signed(guard_pin, authorityPins, selection, deadline)
    deadline = _budget(deadline, proof)
    catalog, installed = _trust_shape(trust, browser_identity_selection_pin, selection)
    _proof_shape(proof, trust, browserTrustPin, browser_identity_selection_pin, selection)
    validate_record(identity, 'ParticipantIdentity', deadline); _window(identity, parent=proof)
    require(identity['role'] == 'BROWSER_PRODUCER' and identity['identity'] == proof['producerIdentity'] and
            identity['browserIdentitySelectionPin'] == browser_identity_selection_pin and identity['browserRuntimeProofPin'] == browserProofPin,
            'REPOSITORY_BROWSER_PARTICIPANT_IDENTITY_MISMATCH')
    state = {'selectionPin': browser_identity_selection_pin, 'selection': selection, 'trustPin': browserTrustPin,
             'trust': trust, 'proofPin': browserProofPin, 'proof': proof, 'identityPin': expectedIdentityPin,
             'identity': identity, 'guardPin': guard_pin, 'guard': guard, 'authorities': authorityPins,
             'catalog': catalog, 'installed': installed, 'sources': _selection_shape(selection)}
    key = canonical(browserTrustPin), canonical(browserProofPin)
    _verified.pop(key, None)
    require(type(graph_roots) is list and graph_roots and type(reserved_output_paths) is list,
            'REPOSITORY_BROWSER_COMPLETE_GRAPH_REQUIRED')
    installation = _signed(selection['executorInstallationPin'], authorityPins, selection, deadline)
    exact(installation, native.INSTALL_FIELDS, 'RepositoryNativeInstallation/v2')
    require(installation['root'] == native.LAB_ROOT and installation['nativeRuntimeProofPin'] == selection['controllerRuntimeProofPin'],
            'REPOSITORY_BROWSER_ROOT_ANCESTRY_MISMATCH')
    root_trust = _signed(installation['nativeRuntimeTrustPin'], authorityPins, selection, deadline)
    root_proof = _signed(installation['nativeRuntimeProofPin'], authorityPins, selection, deadline)
    native._trust_shape(root_trust); native._proof_shape(root_proof, root_trust, installation['nativeRuntimeTrustPin'])
    require(root_trust['nativeFilePins'] == trust['nativeFilePins'] and
            {canonical(p) for p in installation['filePins'] + installation['dependencyPins'] + [installation['pythonPin']]
             if p['path'] not in catalog} == {canonical(p) for p in installed.values()},
            'REPOSITORY_BROWSER_INSTALLATION_PROJECTION_MISMATCH')
    state['installation'] = installation
    _check_current(state, deadline)
    _elf_closure(state, deadline)
    roots = [browser_identity_selection_pin, browserTrustPin, browserProofPin, expectedIdentityPin, guard_pin,
             *authorityPins, *graph_roots]
    state['graphRoots'], state['reserved'] = roots, reserved_output_paths
    state['graph'] = _graph(roots, state, reserved_output_paths, deadline)
    _batch_closure(state, deadline)
    _check_current(state, deadline)
    _verified[key] = document(canonical(state))
    return document(canonical(proof))


def _admitted(trust, proof, deadline, guard_pin):
    native._pin(trust); native._pin(proof)
    state = _verified.get((canonical(trust), canonical(proof)))
    require(state is not None, 'REPOSITORY_BROWSER_VERIFICATION_REQUIRED')
    deadline = _budget(deadline, state['proof'])
    if guard_pin != state['guardPin']:
        _deny(guard_pin, state['selection']['privateKeyPin'])
        renewed = document(canonical(state))
        renewed['guardPin'] = guard_pin
        renewed['guard'] = _signed(guard_pin, state['authorities'], state['selection'], deadline)
        require(all(renewed['guard'].get(k) == state['guard'][k] for k in
                    ('qualificationIntentPin', 'authorizationPin', 'leasePin')),
                'REPOSITORY_BROWSER_PRIVATE_AUTHORITY_MISMATCH')
        renewed['graphRoots'].append(guard_pin)
        _check_current(renewed, deadline)
        renewed['graph'] = _graph(renewed['graphRoots'], renewed, renewed['reserved'], deadline)
        _batch_closure(renewed, deadline)
        _verified[(canonical(trust), canonical(proof))] = renewed
        state = renewed
    _check_current(state, deadline)
    require(_graph(state['graphRoots'], state, state['reserved'], deadline) == state['graph'],
            'REPOSITORY_LAB_PIN_GRAPH_DRIFT')
    _batch_closure(state, deadline)
    return state, deadline


def _deny_member_before_guard(reference, trust, proof):
    native._pin(trust); native._pin(proof)
    state = _verified.get((canonical(trust), canonical(proof)))
    require(state is not None, 'REPOSITORY_BROWSER_VERIFICATION_REQUIRED')
    _deny(reference, state['selection']['privateKeyPin'])


def read_browser_member(reference, trust, proof, *, role, limit=native.LIMIT, deadline=None, guard_pin):
    require(type(role) is str and role in native.NATIVE_ROLES, 'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
    _deny_member_before_guard(reference, trust, proof)
    native._pin(reference, native.BINARY_LIMIT)
    require(type(limit) is int and 0 <= reference['bytes'] <= limit <= native.LIMIT,
            'REPOSITORY_RECORD_TOO_LARGE')
    state, deadline = _admitted(trust, proof, deadline, guard_pin)
    raw = _stream(reference, state, role, deadline, retain=True)[3]
    _check_current(state, deadline)
    return raw


def verify_browser_file(reference, trust, proof, *, role, deadline=None, guard_pin):
    require(type(role) is str and role in SOURCE_ROLES, 'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
    _deny_member_before_guard(reference, trust, proof)
    native._pin(reference, native.VENDOR_LIMIT)
    state, deadline = _admitted(trust, proof, deadline, guard_pin)
    _stream(reference, state, role, deadline)
    _check_current(state, deadline)
    return document(canonical(reference))
