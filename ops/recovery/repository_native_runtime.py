"""R6 explicit laboratory native runtime admission. No production path exception.

The public API takes original Pins. read_native_member accepts only the trust and
proof Pins previously admitted by verify_native_installation in this process.
Raw evidence is Linux mountinfo, PID1 status, and PID1 maps respectively; its
security-relevant fields are compared with current kernel originals, not aliases.
"""
from datetime import datetime, timezone
import base64
import ctypes
from contextlib import contextmanager
import hashlib
import math
import os
from pathlib import PurePosixPath
import posixpath
import re
import stat
import struct
import sys
import time

from repository_records import RepositoryError, canonical, document, exact, require, timestamp
from repository_native_browser_resources import (
    BROWSER_ROOT, BROWSER_RESOURCE_ROLE, BROWSER_RESOURCE_ORIGINALS, BROWSER_VENDOR_ARCHIVE_PIN)

LAB_ROOT = '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07'
LAB_ID = 'backup-server-rehearsal-20261012-r1'
INSTALL_FIELDS = 'schemaVersion root sourceToolkitPin filePins pythonPin dependencyPins nativeRuntimeTrustPin nativeRuntimeProofPin'
TRUST_FIELDS = 'schemaVersion rehearsalId labRoot runtimeId runtimeRole backingRootPath literalRoots immutableRuntimeArtifactDigest vendorArtifactPins nativeFilePins'
PROOF_FIELDS = 'schemaVersion rehearsalId runtimeId nativeRuntimeTrustPin issuedAt expiresAt hostId bootId managerPid managerStartTicks pidNamespace mountNamespace networkNamespace userNamespace rootDevice rootInode immutableRuntimeArtifactDigest readOnlyMountEvidencePin managerIdentityEvidencePin nativeLinkageEvidencePin'
NATIVE_ROLES = frozenset({'native-tool', 'native-manager', 'native-interpreter', 'native-library', 'native-locale', BROWSER_RESOURCE_ROLE})
LIMIT = 134217728
BINARY_LIMIT = 268435456
VENDOR_LIMIT = 2147483648
CHUNK = 1048576
ELF_INSPECTION_LIMIT = 8388608
_verified = {}


def _budget(deadline=None, proof=None):
    now = time.monotonic()
    require(deadline is None or type(deadline) in (int, float) and math.isfinite(deadline),
            'REPOSITORY_NATIVE_DEADLINE_INVALID')
    end = min(now + 60, deadline) if deadline is not None else now + 60
    if proof is not None:
        remaining = (timestamp(proof['expiresAt']) - datetime.now(timezone.utc)).total_seconds()
        end = min(end, now + remaining)
    _remaining(end)
    return end


def _remaining(deadline):
    require(deadline is None or time.monotonic() < deadline, 'REPOSITORY_NATIVE_READ_DEADLINE_EXPIRED')


def _path(value):
    require(type(value) is str and value.startswith('/') and not value.startswith('//') and '\x00' not in value and
            '\\' not in value and PurePosixPath(value).as_posix() == value and
            '..' not in PurePosixPath(value).parts, 'REPOSITORY_NATIVE_LITERAL_PATH_REQUIRED')
    return PurePosixPath(value)


def _lab(value):
    path = _path(value)
    require(path == PurePosixPath(LAB_ROOT) or PurePosixPath(LAB_ROOT) in path.parents,
            'REPOSITORY_LAB_PATH_OUTSIDE_SCOPE')
    return path


def _pin(value, limit=LIMIT):
    require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'},
            'REPOSITORY_PIN_INVALID')
    _path(value['path'])
    require(type(value['bytes']) is int and 0 <= value['bytes'] <= limit and
            type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
            'REPOSITORY_PIN_INVALID')
    return value


def _platform():
    require(sys.platform.startswith('linux') and os.geteuid() == os.getegid() == 0 and
            sys.version_info >= (3, 12) and
            hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY') and
            os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd,
            'REPOSITORY_NATIVE_LINUX_RUNTIME_REQUIRED')
    require(not any(os.environ.get(key) for key in
            ('PYTHONPATH', 'PYTHONHOME', 'LD_LIBRARY_PATH', 'LD_PRELOAD', 'LD_AUDIT')),
            'REPOSITORY_NATIVE_RUNTIME_OVERRIDE_REFUSED')


def _meta(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
            value.st_ctime_ns, value.st_uid, value.st_gid, value.st_mode, value.st_nlink)


def _directory(path):
    """Return a held root-anchored directory fd, never resolve a link."""
    parts = _path(path).parts[1:]
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    try:
        for part in (None, *parts):
            if part is not None:
                child = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = child
            info = os.fstat(fd)
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0 and
                    not (info.st_mode & 0o022), 'REPOSITORY_NATIVE_UNSAFE_ANCESTOR')
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def _original(reference, *, limit=LIMIT, private=False, executable=False,
              readonly=False, deadline=None, retain=False):
    """Hash the whole held original, retaining bytes only for bounded readers."""
    _remaining(deadline)
    _pin(reference, limit)
    path = _lab(reference['path']) if private else _path(reference['path'])
    parent = _directory(str(path.parent))
    fd = None
    try:
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=parent)
        info = os.fstat(fd)
        require(_meta(before) == _meta(info) and stat.S_ISREG(info.st_mode) and
                info.st_uid == info.st_gid == 0 and info.st_nlink == 1 and
                not (info.st_mode & 0o022), 'REPOSITORY_NATIVE_REGULAR_ORIGINAL_REQUIRED')
        if private:
            require(stat.S_IMODE(info.st_mode) == 0o600,
                    'REPOSITORY_LAB_PRIVATE_ORIGINAL_REQUIRED')
        if executable:
            require(info.st_mode & 0o100, 'REPOSITORY_NATIVE_EXECUTABLE_REQUIRED')
        if readonly:
            require(os.fstatvfs(fd).f_flag & os.ST_RDONLY,
                    'REPOSITORY_NATIVE_WRITABLE_RUNTIME_REFUSED')
        require(info.st_size == reference['bytes'], 'REPOSITORY_PIN_CHANGED')
        digest, count, chunks = hashlib.sha256(), 0, []
        while True:
            _remaining(deadline)
            block = os.read(fd, min(CHUNK, limit - count + 1))
            if not block:
                break
            count += len(block)
            require(count <= limit, 'REPOSITORY_RECORD_TOO_LARGE')
            digest.update(block)
            if retain:
                chunks.append(block)
        require(count == reference['bytes'] and digest.hexdigest() == reference['sha256'],
                'REPOSITORY_PIN_CHANGED')
        _remaining(deadline)
        require(_meta(os.fstat(fd)) == _meta(info), 'REPOSITORY_INPUT_CHANGED')
        yield fd, info, b''.join(chunks) if retain else None
        _remaining(deadline)
        require(_meta(os.fstat(fd)) == _meta(info) and
                _meta(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) == _meta(info),
                'REPOSITORY_INPUT_CHANGED')
        current_parent = _directory(str(path.parent))
        try:
            held, current = os.fstat(parent), os.fstat(current_parent)
            require((held.st_dev, held.st_ino, held.st_uid, held.st_gid, held.st_mode) ==
                    (current.st_dev, current.st_ino, current.st_uid, current.st_gid, current.st_mode) and
                    _meta(os.stat(path.name, dir_fd=current_parent, follow_symlinks=False)) == _meta(info),
                    'REPOSITORY_INPUT_CHANGED')
        finally:
            os.close(current_parent)
        _remaining(deadline)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def _read_file(reference, *, limit=LIMIT, private=False, executable=False, readonly=False, deadline=None):
    require(type(limit) is int and 0 <= reference['bytes'] <= limit <= LIMIT,
            'REPOSITORY_RECORD_TOO_LARGE')
    with _original(reference, limit=limit, private=private, executable=executable,
                   readonly=readonly, deadline=deadline, retain=True) as (_, info, raw):
        result = raw, info
    return result


def _signed(reference, authority_pins, *, deadline=None):
    _remaining(deadline)
    envelope = document(_read_file(reference, private=True, deadline=deadline)[0])
    exact(envelope, 'schemaVersion keySha256 payload signature', 'RepositorySignedRecord/v1')
    require(type(authority_pins) is list and authority_pins, 'REPOSITORY_AUTHORITY_REQUIRED')
    matches = []
    for pin in authority_pins:
        _pin(pin); _lab(pin['path'])
        if pin['sha256'] == envelope['keySha256']:
            matches.append(pin)
    require(len(matches) == 1, 'REPOSITORY_AUTHORITY_UNKNOWN')
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        key = load_pem_public_key(_read_file(matches[0], limit=65536, private=True, deadline=deadline)[0])
        require(isinstance(key, Ed25519PublicKey), 'REPOSITORY_AUTHORITY_KEY_INVALID')
        key.verify(base64.b64decode(envelope['signature'], validate=True), canonical(envelope['payload']))
    except (ValueError, TypeError, InvalidSignature) as error:
        raise RepositoryError('REPOSITORY_SIGNATURE_INVALID') from error
    _remaining(deadline)
    return envelope['payload']


def _pins(values, code, limit=LIMIT):
    require(type(values) is list and values, code)
    selected = {}
    for pin in values:
        _pin(pin, limit)
        require(pin['path'] not in selected, 'REPOSITORY_NATIVE_INSTALLATION_DUPLICATE')
        selected[pin['path']] = pin
    return selected


def _trust_shape(trust):
    exact(trust, TRUST_FIELDS, 'RepositoryLabNativeRuntimeTrust/v1')
    require(trust['rehearsalId'] == LAB_ID and trust['labRoot'] == LAB_ROOT and
            type(trust['runtimeId']) is str and trust['runtimeId'] and
            trust['runtimeRole'] in ('EXECUTOR', 'VERIFIER'), 'REPOSITORY_NATIVE_TRUST_SCOPE_INVALID')
    require(_lab(trust['backingRootPath']) != PurePosixPath(LAB_ROOT),
            'REPOSITORY_NATIVE_TASK_ROOT_REQUIRED')
    require(type(trust['immutableRuntimeArtifactDigest']) is str and
            re.fullmatch('sha256:[0-9a-f]{64}', trust['immutableRuntimeArtifactDigest']),
            'REPOSITORY_NATIVE_ARTIFACT_DIGEST_INVALID')
    roots = trust['literalRoots']
    require(type(roots) is list and roots and all(type(r) is str for r in roots) and
            len(set(roots)) == len(roots),
            'REPOSITORY_NATIVE_LITERAL_ROOTS_INVALID')
    for root in roots:
        path = _path(root)
        require(path != PurePosixPath('/') and path != PurePosixPath(LAB_ROOT) and
                PurePosixPath(LAB_ROOT) not in path.parents and
                not any(path == PurePosixPath(p) or PurePosixPath(p) in path.parents
                        for p in ('/proc', '/sys', '/dev')), 'REPOSITORY_NATIVE_LITERAL_ROOTS_INVALID')
    vendors = _pins(trust['vendorArtifactPins'], 'REPOSITORY_NATIVE_VENDOR_ORIGINALS_REQUIRED', VENDOR_LIMIT)
    for pin in vendors.values():
        _lab(pin['path'])
    require(sum(pin['sha256'] == trust['immutableRuntimeArtifactDigest'][7:]
                for pin in vendors.values()) == 1, 'REPOSITORY_NATIVE_ARTIFACT_ORIGINAL_REQUIRED')
    require(type(trust['nativeFilePins']) is list and trust['nativeFilePins'],
            'REPOSITORY_NATIVE_MEMBERS_REQUIRED')
    catalog = {}
    for entry in trust['nativeFilePins']:
        require(type(entry) is dict and set(entry) == {'pin', 'roles', 'vendorArtifactPins'},
                'REPOSITORY_NATIVE_MEMBER_SCHEMA_INVALID')
        pin = _pin(entry['pin'], BINARY_LIMIT); path = _path(pin['path'])
        roles = entry['roles']
        require(type(roles) is list and roles and all(type(r) is str for r in roles) and
                len(set(roles)) == len(roles) and set(roles) <= NATIVE_ROLES,
                'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
        resource = BROWSER_RESOURCE_ROLE in roles
        require(path != PurePosixPath(LAB_ROOT) and PurePosixPath(LAB_ROOT) not in path.parents and
                any(PurePosixPath(root) in path.parents for root in roots) and
                (resource or path.suffix.lower() not in ('.py', '.pyc', '.json', '.pem', '.key', '.p12', '.pfx')),
                'REPOSITORY_NATIVE_MEMBER_PATH_INVALID')
        if resource:
            require(BROWSER_ROOT in roots, 'REPOSITORY_NATIVE_BROWSER_ROOT_REQUIRED')
            _browser_resource(entry)
        if 'native-locale' in roles:
            require(len(roles) == 1 and any(PurePosixPath(p) in path.parents
                    for p in ('/usr/lib/locale', '/usr/share/locale')), 'REPOSITORY_NATIVE_LOCALE_PATH_INVALID')
        provenance = _pins(entry['vendorArtifactPins'], 'REPOSITORY_NATIVE_VENDOR_ORIGINALS_REQUIRED', VENDOR_LIMIT)
        require(all(vendors.get(p) == v for p, v in provenance.items()),
                'REPOSITORY_NATIVE_VENDOR_PROVENANCE_INVALID')
        require(pin['path'] not in catalog, 'REPOSITORY_NATIVE_INSTALLATION_DUPLICATE')
        catalog[pin['path']] = entry
    return catalog


def _browser_resource(entry):
    """Fixed vendor member, exact installed Pin and opaque, exclusive data role."""
    require(entry['roles'] == [BROWSER_RESOURCE_ROLE],
            'REPOSITORY_NATIVE_BROWSER_ROLE_EXCLUSIVE')
    pin = _pin(entry['pin'], LIMIT)
    path = _path(pin['path'])
    require(PurePosixPath(BROWSER_ROOT) in path.parents,
            'REPOSITORY_NATIVE_BROWSER_RESOURCE_PATH_INVALID')
    relative = path.relative_to(BROWSER_ROOT).as_posix()
    original = BROWSER_RESOURCE_ORIGINALS.get(relative)
    require(original is not None and pin == dict(original, path=pin['path']),
            'REPOSITORY_NATIVE_BROWSER_VENDOR_MEMBER_MISMATCH')
    require(BROWSER_VENDOR_ARCHIVE_PIN in entry['vendorArtifactPins'],
            'REPOSITORY_NATIVE_BROWSER_VENDOR_ORIGINAL_REQUIRED')
    return original


def _browser_data(prefix, *, json_raw=None):
    # Hashing of the held descriptor precedes this classification. Never execute
    # or recursively walk vendor data, even when it contains JSON-looking bytes.
    stripped = prefix.lstrip()
    require(not prefix.startswith((b'\x7fELF', b'MZ', b'\x00asm')) and
            not stripped.startswith((b'#!', b'-----BEGIN', b'import ', b'from ',
                                     b'<?', b'@echo', b'function ', b'const ')),
            'REPOSITORY_NATIVE_BROWSER_PROGRAM_OR_KEY_REFUSED')
    if json_raw is not None:
        value = document(json_raw)
        require(type(value) is dict and set(value) == {'file_format_version', 'ICD'} and
                value['file_format_version'] == '1.0.0' and type(value['ICD']) is dict and
                set(value['ICD']) == {'library_path', 'api_version'} and
                value['ICD']['library_path'] == './libvk_swiftshader.so' and
                type(value['ICD']['api_version']) is str and
                re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', value['ICD']['api_version']),
                'REPOSITORY_NATIVE_BROWSER_CONTROL_RECORD_REFUSED')
    else:
        require(not stripped.startswith((b'{', b'[')),
                'REPOSITORY_NATIVE_BROWSER_CONTROL_RECORD_REFUSED')


def _proof_shape(proof, trust, trust_pin):
    exact(proof, PROOF_FIELDS, 'RepositoryLabNativeRuntimeProof/v1')
    require(proof['rehearsalId'] == LAB_ID and proof['runtimeId'] == trust['runtimeId'] and
            proof['nativeRuntimeTrustPin'] == trust_pin and
            proof['immutableRuntimeArtifactDigest'] == trust['immutableRuntimeArtifactDigest'],
            'REPOSITORY_NATIVE_PROOF_SCOPE_INVALID')
    require(timestamp(proof['issuedAt']) <= datetime.now(timezone.utc) < timestamp(proof['expiresAt']),
            'REPOSITORY_NATIVE_PROOF_NOT_CURRENT')
    require(type(proof['managerPid']) is int and proof['managerPid'] == 1 and
            all(type(proof[k]) is int and proof[k] > 0
                for k in ('managerStartTicks', 'rootDevice', 'rootInode')),
            'REPOSITORY_NATIVE_MANAGER_IDENTITY_INVALID')
    for key, kind in (('pidNamespace', 'pid'), ('mountNamespace', 'mnt'),
                      ('networkNamespace', 'net'), ('userNamespace', 'user')):
        require(type(proof[key]) is str and re.fullmatch(kind + r':\[[0-9]+\]', proof[key]),
                'REPOSITORY_NATIVE_NAMESPACE_INVALID')
    for key in ('hostId', 'bootId'):
        require(type(proof[key]) is str and proof[key], 'REPOSITORY_NATIVE_HOST_IDENTITY_INVALID')
    for key in ('readOnlyMountEvidencePin', 'managerIdentityEvidencePin', 'nativeLinkageEvidencePin'):
        _pin(proof[key]); _lab(proof[key]['path'])


def _kernel(path, limit=16777216, deadline=None):
    _remaining(deadline)
    require(path in ('/proc/1/stat', '/proc/1/status', '/proc/1/maps', '/proc/self/status',
            '/proc/self/maps', '/proc/self/mountinfo', '/proc/sys/kernel/random/boot_id'),
            'REPOSITORY_NATIVE_KERNEL_ORIGINAL_REQUIRED')
    proc_fd = os.open('/proc', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        # fstatfs is a kernel fact, unlike a caller-provided mountinfo document.
        fs = ctypes.create_string_buffer(256)
        libc = ctypes.CDLL(None, use_errno=True)
        require(libc.fstatfs(proc_fd, ctypes.byref(fs)) == 0 and
                ctypes.c_long.from_buffer(fs).value == 0x9fa0,
                'REPOSITORY_NATIVE_PROCFS_REQUIRED')
        fd = os.open(path[6:], os.O_RDONLY | os.O_CLOEXEC, dir_fd=proc_fd)
        with os.fdopen(fd, 'rb') as stream:
            chunks, count = [], 0
            while True:
                _remaining(deadline)
                block = stream.read(min(CHUNK, limit - count + 1))
                if not block:
                    break
                count += len(block)
                require(count <= limit, 'REPOSITORY_RECORD_TOO_LARGE')
                chunks.append(block)
            raw = b''.join(chunks)
    finally:
        os.close(proc_fd)
    _remaining(deadline)
    require(len(raw) <= limit, 'REPOSITORY_RECORD_TOO_LARGE')
    return raw


def _status(raw):
    result = {}
    for line in raw.decode('ascii').splitlines():
        key, sep, value = line.partition(':')
        require(sep and key not in result, 'REPOSITORY_NATIVE_STATUS_INVALID')
        result[key] = value.strip()
    return result


def _status_identity(values, *, manager=True):
    keys = ('Pid', 'Uid', 'Gid', 'CapInh', 'CapPrm', 'CapEff', 'CapBnd')
    require(all(k in values for k in keys), 'REPOSITORY_NATIVE_STATUS_INVALID')
    require(values['Pid'].isdigit() and int(values['Pid']) > 0 and
            (not manager or values['Pid'] == '1') and
            all(values[k].split() == ['0'] * 4 for k in ('Uid', 'Gid')),
            'REPOSITORY_NATIVE_MANAGER_IDENTITY_INVALID')
    for key in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb'):
        if key in values:
            require(re.fullmatch('[0-9a-fA-F]+', values[key]) and
                    not (int(values[key], 16) & (1 << 21)),
                    'REPOSITORY_NATIVE_REMOUNT_AUTHORITY_REFUSED')
    return tuple((k, values[k]) for k in (*keys, 'CapAmb') if k in values)


def _mounts(raw):
    result = {}
    for line in raw.decode('utf-8').splitlines():
        left, sep, right = line.partition(' - ')
        a, b = left.split(), right.split(None, 2)
        require(sep and len(a) >= 6 and len(b) == 3, 'REPOSITORY_NATIVE_MOUNTINFO_INVALID')
        require('\\' not in a[4], 'REPOSITORY_NATIVE_LITERAL_PATH_REQUIRED')
        path = str(_path(a[4]))
        # Unrelated stacked mounts do not grant native access. Ambiguity at a
        # selected root/member mount is rejected by _mount_for, never resolved
        # by selecting whichever line happens to appear last.
        result[path] = (tuple(a), tuple(b)) if path not in result else None
    require('/' in result, 'REPOSITORY_NATIVE_MOUNTINFO_INVALID')
    return result


def _mount_for(path, mounts):
    target = _path(path)
    choices = [p for p in mounts if target == PurePosixPath(p) or PurePosixPath(p) in target.parents]
    selected = mounts[max(choices, key=lambda p: len(PurePosixPath(p).parts))]
    require(selected is not None, 'REPOSITORY_NATIVE_MOUNT_ALIAS_REFUSED')
    return selected


def _readonly_mount(value):
    a, b = value
    require('ro' in a[5].split(',') and 'rw' not in a[5].split(',') and
            'ro' in b[2].split(',') and 'rw' not in b[2].split(',') and
            b[0] in ('ext4', 'xfs', 'squashfs', 'erofs', 'iso9660'),
            'REPOSITORY_NATIVE_WRITABLE_RUNTIME_REFUSED')


def _maps(raw):
    result = set()
    for line in raw.decode('utf-8').splitlines():
        fields = line.split(None, 5)
        require(len(fields) >= 5 and re.fullmatch('[0-9a-f]+:[0-9a-f]+', fields[3]) and
                fields[4].isdigit(), 'REPOSITORY_NATIVE_MAPS_INVALID')
        if int(fields[4]) == 0:
            require(len(fields) == 5 or fields[5].startswith('['), 'REPOSITORY_NATIVE_MAPS_INVALID')
            continue
        require(len(fields) == 6, 'REPOSITORY_NATIVE_MAPS_INVALID')
        path = str(_path(fields[5]))
        require(not path.endswith(' (deleted)'), 'REPOSITORY_NATIVE_MAPPING_CHANGED')
        result.add((path, fields[3], int(fields[4])))
    require(result, 'REPOSITORY_NATIVE_MAPS_INVALID')
    return result


def _read_member(reference, catalog, role, limit=LIMIT, deadline=None):
    require(type(role) is str and role in NATIVE_ROLES, 'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
    _pin(reference, BINARY_LIMIT)
    entry = catalog.get(reference['path'])
    require(entry is not None and entry['pin'] == reference and role in entry['roles'],
            'REPOSITORY_NATIVE_MEMBER_NOT_APPROVED')
    if role == BROWSER_RESOURCE_ROLE:
        _browser_resource(entry)
    raw, info = _read_file(reference, limit=limit, readonly=True,
                            executable=role in ('native-tool', 'native-manager', 'native-interpreter'), deadline=deadline)
    if role == BROWSER_RESOURCE_ROLE:
        _browser_data(raw[:4096], json_raw=raw if reference['path'] == BROWSER_ROOT + '/vk_swiftshader_icd.json' else None)
    elif role != 'native-locale':
        require(raw.startswith(b'\x7fELF'), 'REPOSITORY_NATIVE_ELF_ORIGINAL_REQUIRED')
    return raw, info


def _elf_inspect(read, length):
    """Inspect bounded ELF ranges, never materialize/map a complete binary."""
    header = read(0, 64)
    require(len(header) == 64 and header[:7] == b'\x7fELF\x02\x01\x01' and
            struct.unpack_from('<H', header, 16)[0] in (2, 3) and
            struct.unpack_from('<H', header, 18)[0] == 62, 'REPOSITORY_NATIVE_ELF_ABI_INVALID')
    offset = struct.unpack_from('<Q', header, 32)[0]
    size, count = struct.unpack_from('<HH', header, 54)
    require(size == 56 and count > 0 and offset + size * count <= length,
            'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
    table = read(offset, size * count)
    segments = [struct.unpack_from('<IIQQQQQQ', table, i * size) for i in range(count)]
    require(all(p[2] + p[5] <= length for p in segments), 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
    interpreters = [read(p[2], p[5]) for p in segments if p[0] == 3]
    require(len(interpreters) <= 1 and all(p.endswith(b'\x00') and b'\x00' not in p[:-1]
            for p in interpreters), 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
    interpreter = interpreters[0][:-1].decode('ascii') if interpreters else None
    dynamic = []
    for p in segments:
        if p[0] == 2:
            require(p[5] % 16 == 0, 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
            data = read(p[2], p[5])
            terminated = False
            for pos in range(0, len(data), 16):
                tag, value = struct.unpack_from('<qQ', data, pos)
                if tag == 0:
                    terminated = True
                    break
                dynamic.append((tag, value))
            require(terminated, 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
    strings = [v for t, v in dynamic if t == 5]
    lengths = [v for t, v in dynamic if t == 10]
    require(not dynamic or len(strings) == len(lengths) == 1, 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
    table = b''
    if dynamic:
        candidates = [p for p in segments if p[0] == 1 and
                      p[3] <= strings[0] and strings[0] + lengths[0] <= p[3] + p[5]]
        require(len(candidates) == 1, 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
        pos = candidates[0][2] + strings[0] - candidates[0][3]
        table = read(pos, lengths[0])
    def string(index):
        require(index < len(table), 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
        end = table.find(b'\x00', index)
        require(end >= index, 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
        return table[index:end].decode('ascii')
    return {'interpreter': interpreter, 'needed': [string(v) for t, v in dynamic if t == 1],
            'searchPaths': [string(v) for t, v in dynamic if t in (15, 29)]}


def _elf_ranges(read, length, deadline=None):
    used = 0
    def bounded(offset, count):
        nonlocal used
        _remaining(deadline)
        require(type(offset) is int and type(count) is int and offset >= 0 and count >= 0 and
                offset + count <= length, 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
        used += count
        require(used <= ELF_INSPECTION_LIMIT, 'REPOSITORY_NATIVE_ELF_INSPECTION_TOO_LARGE')
        chunks = []
        while count:
            _remaining(deadline)
            block = read(offset, min(count, CHUNK))
            require(block and len(block) <= count, 'REPOSITORY_NATIVE_ELF_LAYOUT_INVALID')
            chunks.append(block)
            offset += len(block); count -= len(block)
        _remaining(deadline)
        return b''.join(chunks)
    return _elf_inspect(bounded, length)


def _elf_linkage(raw):
    return _elf_ranges(lambda offset, count: raw[offset:offset + count], len(raw))


def _stream_file(reference, *, limit=LIMIT, private=False, readonly=False,
                 executable=False, elf=False, deadline=None):
    with _original(reference, limit=limit, private=private, readonly=readonly,
                   executable=executable, deadline=deadline) as (fd, info, _):
        _remaining(deadline)
        prefix = os.pread(fd, min(64, info.st_size), 0)
        is_elf = prefix.startswith(b'\x7fELF')
        require(not elf or is_elf, 'REPOSITORY_NATIVE_ELF_ORIGINAL_REQUIRED')
        linkage = None
        if is_elf:
            # Original relocatable objects remain counted; no runtime linkage.
            if len(prefix) >= 18 and struct.unpack_from('<H', prefix, 16)[0] == 1:
                require(not elf, 'REPOSITORY_NATIVE_ELF_ABI_INVALID')
            else:
                linkage = _elf_ranges(lambda offset, count: os.pread(fd, count, offset),
                                      info.st_size, deadline)
        result = info, linkage, prefix
    return result


def _member_stream(reference, catalog, role, deadline=None):
    require(type(role) is str and role in NATIVE_ROLES, 'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
    _pin(reference, LIMIT if role == 'native-locale' else BINARY_LIMIT)
    entry = catalog.get(reference['path'])
    require(entry is not None and entry['pin'] == reference and role in entry['roles'],
            'REPOSITORY_NATIVE_MEMBER_NOT_APPROVED')
    if role == BROWSER_RESOURCE_ROLE:
        _browser_resource(entry)
        with _original(reference, limit=LIMIT, readonly=True, deadline=deadline) as (fd, info, _):
            prefix = os.pread(fd, min(4096, info.st_size), 0)
            is_json = reference['path'] == BROWSER_ROOT + '/vk_swiftshader_icd.json'
            _browser_data(prefix, json_raw=prefix if is_json else None)
            result = info, None, prefix
        return result
    return _stream_file(reference, limit=LIMIT if role == 'native-locale' else BINARY_LIMIT,
                        readonly=True, executable=role in ('native-tool', 'native-manager', 'native-interpreter'),
                        elf=role != 'native-locale', deadline=deadline)


def _selected_stream(reference, state, deadline=None):
    path = reference['path']
    require(state['selected'].get(path) == reference, 'REPOSITORY_NATIVE_MEMBER_NOT_APPROVED')
    if path in state['catalog']:
        return _member_stream(reference, state['catalog'], state['catalog'][path]['roles'][0], deadline)
    _lab(path)
    binary = reference == state['manifest']['pythonPin'] or (
        state['dependencies'].get(path) == reference and
        PurePosixPath(path).suffix.lower() not in ('.py', '.pyc', '.json', '.pem', '.key', '.p12', '.pfx'))
    return _stream_file(reference, limit=BINARY_LIMIT if binary else LIMIT,
                        private=reference in state['manifest'].get('filePins', []) or not binary,
                        executable=reference == state['manifest']['pythonPin'],
                        elf=binary and reference['bytes'] > LIMIT, deadline=deadline)


def _vendor_stream(reference, state, deadline=None):
    require(state['vendors'].get(reference['path']) == reference, 'REPOSITORY_NATIVE_VENDOR_PROVENANCE_INVALID')
    _lab(reference['path'])
    # Vendor artifacts are opaque exact originals, not executable/control records.
    with _original(reference, limit=VENDOR_LIMIT, private=True, deadline=deadline) as (fd, info, _):
        if reference['bytes'] > LIMIT:
            require(PurePosixPath(reference['path']).suffix.lower() not in
                    ('.py', '.pyc', '.json', '.pem', '.key', '.p12', '.pfx') and
                    not os.pread(fd, 64, 0).lstrip().startswith((b'{', b'[')),
                    'REPOSITORY_NATIVE_LARGE_RECORD_REFUSED')
        result = info
    return result


def _origin_path(value, declaring_path):
    """Derive the vendor loader path without rewriting any original Pin."""
    origin = str(PurePosixPath(declaring_path).parent)
    value = value.replace('${ORIGIN}', origin).replace('$ORIGIN', origin)
    require('$' not in value and value.startswith('/'),
            'REPOSITORY_NATIVE_LINKAGE_UNMEASURED')
    value = posixpath.normpath(value)
    _path(value)
    return value


def _check_elf_closure(state, deadline=None):
    catalog = state['catalog']
    for path, pin in state['selected'].items():
        entry = catalog.get(path)
        if entry is not None and entry['roles'] == ['native-locale']:
            continue
        _, linkage, _ = _selected_stream(pin, state, deadline)
        if linkage is None:
            continue
        if linkage['interpreter'] is not None or linkage['needed']:
            # R6 has no role admitting an opaque generated loader cache. An
            # unmeasured cache may redirect a declared SONAME to another file.
            require(not os.path.lexists('/etc/ld.so.cache'),
                    'REPOSITORY_NATIVE_LOADER_CACHE_UNMEASURED')
        if linkage['interpreter'] is not None:
            interpreter = str(_path(linkage['interpreter']))
            require(interpreter in catalog and 'native-interpreter' in catalog[interpreter]['roles'],
                    'REPOSITORY_NATIVE_INTERPRETER_NOT_INSTALLED')
            _member_stream(catalog[interpreter]['pin'], catalog, 'native-interpreter', deadline)
        directories = []
        for search in linkage['searchPaths']:
            for directory in search.split(':'):
                # Resolve only the actual vendor ELF token, never an env/path
                # substitution. Other tokens/relative roots fail explicitly.
                # This is the vendor loader's ORIGIN/.. directory semantics,
                # not normalization/replacement of an original file Pin.
                directory = _origin_path(directory, path)
                directories.append(directory)
                fd = _directory(directory)
                try:
                    if entry is not None:
                        require(os.fstatvfs(fd).f_flag & os.ST_RDONLY,
                                'REPOSITORY_NATIVE_WRITABLE_RUNTIME_REFUSED')
                    else:
                        _lab(directory)
                finally:
                    os.close(fd)
        # These are the genuine selected CentOS x86-64 GNU loader's default
        # directories. No cache, environment override, or alternate ABI search
        # algorithm is introduced by this admission profile.
        for needed in linkage['needed']:
            require(needed and '\\' not in needed,
                    'REPOSITORY_NATIVE_NEEDED_MEMBER_NOT_INSTALLED')
            if '/' in needed:
                resolved = _origin_path(needed, path)
            else:
                resolved = None
                for directory in dict.fromkeys([*directories, '/lib64', '/usr/lib64']):
                    candidate = directory + '/' + needed
                    if os.path.lexists(candidate):
                        resolved = candidate
                        break
            require(resolved in state['selected'] and
                    ((resolved in catalog and set(catalog[resolved]['roles']) &
                      {'native-library', 'native-interpreter'}) or
                     PurePosixPath(LAB_ROOT) in PurePosixPath(resolved).parents),
                    'REPOSITORY_NATIVE_NEEDED_MEMBER_NOT_INSTALLED')
            if resolved in catalog:
                _member_stream(state['selected'][resolved], catalog, catalog[resolved]['roles'][0], deadline)
            else:
                _selected_stream(state['selected'][resolved], state, deadline)


def _check_maps(raw, state, deadline=None):
    for path, device, inode in _maps(raw):
        entry = state['catalog'].get(path)
        if entry is not None:
            role = entry['roles'][0]
            info, _, _ = _member_stream(entry['pin'], state['catalog'], role, deadline)
        else:
            _lab(path)
            require(path in state['selected'], 'REPOSITORY_NATIVE_MAPPING_NOT_INSTALLED')
            info, _, _ = _selected_stream(state['selected'][path], state, deadline)
        expected = '{:x}:{:x}'.format(os.major(info.st_dev), os.minor(info.st_dev))
        # Kernel prints zero-padded device numbers; compare numbers, not aliases.
        require(tuple(int(p, 16) for p in device.split(':')) ==
                tuple(int(p, 16) for p in expected.split(':')) and info.st_ino == inode,
                'REPOSITORY_NATIVE_MAPPING_CHANGED')


def _check_current(state, deadline=None):
    _remaining(deadline)
    _platform()
    trust, proof = state['trust'], state['proof']
    require(_signed(state['trustPin'], state['authorityPins'], deadline=deadline) == trust and
            _signed(state['proofPin'], state['authorityPins'], deadline=deadline) == proof,
            'REPOSITORY_NATIVE_TRUST_CHANGED')
    _proof_shape(proof, trust, state['trustPin'])
    for pin in state['helperPins']:
        _read_file(pin, private=True, deadline=deadline)
    for pin in trust['vendorArtifactPins']:
        _vendor_stream(pin, state, deadline)
    host_fd = _directory('/etc')
    try:
        fd = os.open('machine-id', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=host_fd)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == info.st_gid == 0 and
                    info.st_size <= 256 and not (info.st_mode & 0o022),
                    'REPOSITORY_NATIVE_HOST_IDENTITY_INVALID')
            _remaining(deadline)
            host_id = os.read(fd, 256).decode('ascii').strip()
            _remaining(deadline)
            require(_meta(os.fstat(fd)) == _meta(info), 'REPOSITORY_INPUT_CHANGED')
        finally:
            os.close(fd)
    finally:
        os.close(host_fd)
    require(proof['hostId'] == host_id and proof['bootId'] ==
            _kernel('/proc/sys/kernel/random/boot_id', 256, deadline).decode('ascii').strip(),
            'REPOSITORY_NATIVE_ACTUAL_HOST_MISMATCH')
    for key, kind in (('pidNamespace', 'pid'), ('mountNamespace', 'mnt'),
                      ('networkNamespace', 'net'), ('userNamespace', 'user')):
        require(proof[key] == os.readlink('/proc/self/ns/' + kind) ==
                os.readlink('/proc/1/ns/' + kind), 'REPOSITORY_NATIVE_NAMESPACE_MISMATCH')
    fields = _kernel('/proc/1/stat', 65536, deadline).decode('ascii').rsplit(')', 1)
    require(len(fields) == 2 and fields[0].split(' ', 1)[0] == '1' and
            len(fields[1].split()) >= 20 and int(fields[1].split()[19]) == proof['managerStartTicks'],
            'REPOSITORY_NATIVE_MANAGER_IDENTITY_INVALID')
    root_fd = _directory('/')
    backing_fd = None
    try:
        backing_fd = _directory(trust['backingRootPath'])
        root = os.fstat(root_fd)
        require((root.st_dev, root.st_ino) == (proof['rootDevice'], proof['rootInode']) ==
                (os.fstat(backing_fd).st_dev, os.fstat(backing_fd).st_ino) ==
                (os.stat('/proc/1/root').st_dev, os.stat('/proc/1/root').st_ino) ==
                (os.stat('/proc/self/root').st_dev, os.stat('/proc/self/root').st_ino),
                'REPOSITORY_NATIVE_ACTUAL_ROOT_MISMATCH')
        require(os.fstatvfs(root_fd).f_flag & os.ST_RDONLY and
                os.fstatvfs(backing_fd).f_flag & os.ST_RDONLY,
                'REPOSITORY_NATIVE_WRITABLE_RUNTIME_REFUSED')
    finally:
        if backing_fd is not None:
            os.close(backing_fd)
        os.close(root_fd)
    prior_mounts = _mounts(_read_file(proof['readOnlyMountEvidencePin'], private=True, deadline=deadline)[0])
    mounts = _mounts(_kernel('/proc/self/mountinfo', deadline=deadline))
    require(trust['backingRootPath'] in mounts, 'REPOSITORY_NATIVE_BACKING_MOUNT_UNMEASURED')
    for path in ('/', trust['backingRootPath'], *state['catalog']):
        actual = _mount_for(path, mounts)
        require(actual == _mount_for(path, prior_mounts), 'REPOSITORY_NATIVE_MOUNT_CHANGED')
        _readonly_mount(actual)
    manager = _status(_kernel('/proc/1/status', deadline=deadline))
    prior = _status(_read_file(proof['managerIdentityEvidencePin'], private=True, deadline=deadline)[0])
    require(_status_identity(manager) == _status_identity(prior), 'REPOSITORY_NATIVE_MANAGER_IDENTITY_INVALID')
    caller = _status(_kernel('/proc/self/status', deadline=deadline))
    # The caller must also lack all authority to remount the native root.
    _status_identity(caller, manager=False)
    exe = os.readlink('/proc/1/exe')
    _path(exe)
    entry = state['catalog'].get(exe)
    require(entry is not None, 'REPOSITORY_NATIVE_MANAGER_NOT_INSTALLED')
    info, _, _ = _member_stream(entry['pin'], state['catalog'], 'native-manager', deadline)
    with open('/proc/1/exe', 'rb') as stream:
        before = os.fstat(stream.fileno())
        digest, count = hashlib.sha256(), 0
        while True:
            _remaining(deadline)
            raw = stream.read(CHUNK)
            if not raw:
                break
            count += len(raw)
            require(count <= BINARY_LIMIT, 'REPOSITORY_RECORD_TOO_LARGE')
            digest.update(raw)
        require(_meta(before) == _meta(os.fstat(stream.fileno())) == _meta(info) and
                count == entry['pin']['bytes'] and digest.hexdigest() == entry['pin']['sha256'],
                'REPOSITORY_NATIVE_MANAGER_EXECUTABLE_CHANGED')
    manager_maps = _kernel('/proc/1/maps', deadline=deadline)
    prior_maps = _read_file(proof['nativeLinkageEvidencePin'], private=True, deadline=deadline)[0]
    require(_maps(manager_maps) == _maps(prior_maps), 'REPOSITORY_NATIVE_MAPPING_CHANGED')
    _check_maps(manager_maps, state, deadline)
    require(os.readlink('/proc/self/exe') == state['manifest']['pythonPin']['path'],
            'REPOSITORY_NATIVE_ACTUAL_PYTHON_MISMATCH')
    _check_maps(_kernel('/proc/self/maps', deadline=deadline), state, deadline)
    _remaining(deadline)


def _graph(roots, state, *, stable=False, deadline=None):
    seen, active = {}, set()
    forbidden = {state['manifestPin']['path'], state['proofPin']['path']} if stable else set()
    def walk(value):
        _remaining(deadline)
        if type(value) is dict and set(value) == {'path', 'bytes', 'sha256'} and type(value['path']) is str:
            pin = _pin(value, VENDOR_LIMIT); path = pin['path']
            require(path not in forbidden and path not in active, 'REPOSITORY_LAB_PIN_GRAPH_CYCLE')
            if path in seen:
                require(seen[path] == pin, 'REPOSITORY_LAB_PIN_GRAPH_DRIFT')
                return
            require(len(seen) < 4096, 'REPOSITORY_LAB_PIN_GRAPH_TOO_LARGE')
            seen[path] = pin; active.add(path)
            entry = state['catalog'].get(path)
            raw = b''
            if state.get('vendors', {}).get(path) == pin:
                _vendor_stream(pin, state, deadline)
                # The exact original data member is opaque at its vendor path too.
                if pin['bytes'] <= LIMIT and pin not in BROWSER_RESOURCE_ORIGINALS.values():
                    raw = _read_file(pin, private=True, deadline=deadline)[0]
            elif state.get('selected', {}).get(path) == pin:
                _, linkage, prefix = _selected_stream(pin, state, deadline)
                if entry is not None and entry['roles'] == [BROWSER_RESOURCE_ROLE]:
                    # The resource itself and its exact vendor originals count;
                    # its opaque bytes cannot introduce signed/control Pin edges.
                    walk(entry['vendorArtifactPins'])
                elif not prefix.startswith(b'\x7fELF'):
                    _pin(pin)
                    raw = _read_file(pin, deadline=deadline)[0]
            elif entry is not None:
                require(entry['pin'] == pin, 'REPOSITORY_NATIVE_MEMBER_NOT_APPROVED')
                _member_stream(pin, state['catalog'], entry['roles'][0], deadline)
                if entry['roles'] == [BROWSER_RESOURCE_ROLE]:
                    walk(entry['vendorArtifactPins'])
            else:
                _pin(pin); _lab(path)
                raw = _read_file(pin, deadline=deadline)[0]
            if raw.lstrip().startswith((b'{', b'[')):
                walk(document(raw))
            active.remove(path)
        elif type(value) is dict:
            if stable and type(value.get('schemaVersion')) is str:
                schema = value['schemaVersion']
                require(not any(token in schema for token in
                        ('ExecutionHost', 'ExecutionContext', 'Authorization', 'Grant', 'Lease',
                         'NativeRuntimeProof', 'NativeInstallation', 'Claim')),
                        'REPOSITORY_NATIVE_TRUST_FEEDBACK_REFUSED')
            for child in value.values():
                walk(child)
        elif type(value) is list:
            for child in value:
                walk(child)
    walk(roots)
    return seen


def verify_native_installation(reference, authority_pins, *, deadline=None):
    """Verify an explicit lab v2 manifest. v1 remains the caller's strict path."""
    _platform()
    deadline = _budget(deadline)
    manifest = _signed(reference, authority_pins, deadline=deadline)
    exact(manifest, INSTALL_FIELDS, 'RepositoryNativeInstallation/v2')
    require(manifest['root'] == LAB_ROOT, 'REPOSITORY_NATIVE_INSTALLATION_SCOPE_INVALID')
    files = _pins(manifest['filePins'], 'REPOSITORY_NATIVE_INSTALLATION_CLOSURE_REQUIRED')
    dependencies = _pins(manifest['dependencyPins'], 'REPOSITORY_NATIVE_INSTALLATION_CLOSURE_REQUIRED', BINARY_LIMIT)
    selected = _pins(manifest['filePins'] + manifest['dependencyPins'] + [manifest['pythonPin']],
                     'REPOSITORY_NATIVE_INSTALLATION_CLOSURE_REQUIRED', BINARY_LIMIT)
    _lab(manifest['pythonPin']['path']); _lab(manifest['sourceToolkitPin']['path'])
    for pin in files.values():
        _lab(pin['path'])
    trust_pin, proof_pin = manifest['nativeRuntimeTrustPin'], manifest['nativeRuntimeProofPin']
    trust = _signed(trust_pin, authority_pins, deadline=deadline)
    proof = _signed(proof_pin, authority_pins, deadline=deadline)
    deadline = _budget(deadline, proof)
    catalog = _trust_shape(trust)
    _proof_shape(proof, trust, trust_pin)
    require(all(dependencies.get(path) == entry['pin'] for path, entry in catalog.items()),
            'REPOSITORY_NATIVE_MEMBER_CLOSURE_MISMATCH')
    state = {'manifestPin': document(canonical(reference)), 'manifest': document(canonical(manifest)),
             'trustPin': document(canonical(trust_pin)), 'proofPin': document(canonical(proof_pin)),
             'trust': trust, 'proof': proof, 'catalog': catalog,
             'selected': document(canonical(selected)), 'dependencies': document(canonical(dependencies)),
             'vendors': document(canonical({p['path']: p for p in trust['vendorArtifactPins']})), 'authorityPins': document(canonical(authority_pins))}
    _verified.pop((canonical(trust_pin), canonical(proof_pin)), None)
    # The shared helper and its records implementation must themselves be exact
    # installed private programs, even when invoked by W01/W02/W04 consumers.
    import repository_records
    state['helperPins'] = []
    import repository_native_browser_resources
    for module in (sys.modules[__name__], repository_records, repository_native_browser_resources):
        path = os.path.abspath(module.__file__)
        require(path in files, 'REPOSITORY_NATIVE_HELPER_NOT_INSTALLED')
        _read_file(files[path], private=True, deadline=deadline)
        state['helperPins'].append(document(canonical(files[path])))
    _check_current(state, deadline)
    _check_elf_closure(state, deadline)
    for pin in selected.values():
        _selected_stream(pin, state, deadline)
    _read_file(manifest['sourceToolkitPin'], private=True, deadline=deadline)
    _graph([trust_pin], state, stable=True, deadline=deadline)
    _graph([reference, *authority_pins], state, deadline=deadline)
    _check_current(state, deadline)
    # Store a private verified state; returned wire dictionaries cannot mutate it.
    _verified[(canonical(trust_pin), canonical(proof_pin))] = state
    return manifest


def read_native_member(reference, trust, proof, *, role, limit=LIMIT, deadline=None):
    """Read one exact native member after current original-state revalidation.

    trust/proof are original Pin dictionaries from the verified v2 manifest.
    No caller-supplied decoded trust record can establish admission.
    """
    _pin(reference, BINARY_LIMIT); _pin(trust); _pin(proof)
    require(type(limit) is int and 0 <= reference['bytes'] <= limit <= LIMIT,
            'REPOSITORY_RECORD_TOO_LARGE')
    require(type(role) is str and role in NATIVE_ROLES, 'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
    state, deadline = _admitted(trust, proof, deadline)
    raw = _read_member(reference, state['catalog'], role, limit, deadline)[0]
    _check_current(state, deadline)
    return raw


def _admitted(trust, proof, deadline):
    _pin(trust); _pin(proof)
    state = _verified.get((canonical(trust), canonical(proof)))
    require(state is not None, 'REPOSITORY_NATIVE_VERIFICATION_REQUIRED')
    deadline = _budget(deadline, state['proof'])
    require(_signed(state['manifestPin'], state['authorityPins'], deadline=deadline) == state['manifest'],
            'REPOSITORY_NATIVE_INSTALLATION_CHANGED')
    _check_current(state, deadline)
    return state, deadline


def _browser_schema_source(reference, manifest):
    """Only the exact selected R12 schema bytes are definition source data."""
    return (reference is not None and manifest is not None and
            reference in manifest['filePins'] and
            reference['path'].endswith('/ops/recovery/repository_native_browser_schemas.json') and
            reference['bytes'] == 53347 and reference['sha256'] ==
            '2de76465c364ab86cb4528b0cf09a2c96aab828a203a8f3c90713308fb0a80ca')


def _non_program_data(fd, info, deadline, *, reference=None, manifest=None):
    # The caller still hashes every byte in the held/reopened original. This
    # finite source classification never applies to runtime control records.
    if _browser_schema_source(reference, manifest):
        _remaining(deadline)
        return
    prefix = os.pread(fd, min(4096, info.st_size), 0)
    if prefix.lstrip().startswith((b'{', b'[')):
        require(info.st_size <= LIMIT, 'REPOSITORY_RECORD_TOO_LARGE')
        chunks = []
        for offset in range(0, info.st_size, CHUNK):
            _remaining(deadline)
            chunks.append(os.pread(fd, min(CHUNK, info.st_size - offset), offset))
        def no_secret_metadata(value):
            _remaining(deadline)
            if type(value) is dict:
                require(not set(value) & {'privateKeyPin', 'privateKey', 'evidenceSigningKeyPin'},
                        'REPOSITORY_NATIVE_INSTALLED_SECRET_METADATA_REFUSED')
                for child in value.values():
                    no_secret_metadata(child)
            elif type(value) is list:
                for child in value:
                    no_secret_metadata(child)
        no_secret_metadata(document(b''.join(chunks)))
    else:
        overlap = b''
        for offset in range(0, info.st_size, CHUNK):
            _remaining(deadline)
            block = overlap + os.pread(fd, min(CHUNK, info.st_size - offset), offset)
            require(not re.search(rb'''(?m)^\s*["']?(privateKeyPin|privateKey|evidenceSigningKeyPin)["']?\s*:''', block),
                    'REPOSITORY_NATIVE_INSTALLED_SECRET_METADATA_REFUSED')
            overlap = block[-128:]


def _installed_original(reference, state, deadline):
    """An installed non-program original is a separate, finite source role."""
    path = str(_lab(reference['path']))
    require(reference in state['manifest']['filePins'] and
            reference != state['manifest']['pythonPin'] and
            path not in state['dependencies'] and path not in state['catalog'] and
            PurePosixPath(path).suffix.lower() not in
            ('.py', '.pyc', '.pyo', '.sh', '.bash', '.ps1', '.bat', '.cmd',
             '.pem', '.key', '.p12', '.pfx'),
            'REPOSITORY_NATIVE_INSTALLED_ORIGINAL_NOT_APPROVED')
    with _original(reference, private=True, readonly=True, deadline=deadline) as (fd, info, _):
        prefix = os.pread(fd, min(4096, info.st_size), 0)
        require(not prefix.startswith((b'\x7fELF', b'MZ', b'\x00asm')) and
                not prefix.lstrip().startswith((b'#!', b'-----BEGIN', b'import ', b'from ',
                                                b'<?', b'@echo', b'function ', b'const ')),
                'REPOSITORY_NATIVE_INSTALLED_PROGRAM_OR_KEY_REFUSED')
        _non_program_data(fd, info, deadline, reference=reference, manifest=state['manifest'])


def verify_native_file(reference, trust, proof, *, role, deadline=None):
    """Stream every original byte; return only its exact admitted Pin."""
    _pin(reference, VENDOR_LIMIT)
    require(type(role) is str and role in NATIVE_ROLES | {'vendor-artifact', 'installed-binary', 'installed-original'},
            'REPOSITORY_NATIVE_MEMBER_ROLE_INVALID')
    state, deadline = _admitted(trust, proof, deadline)
    if role == 'vendor-artifact':
        _vendor_stream(reference, state, deadline)
    elif role == 'installed-binary':
        path = str(_lab(reference['path']))
        require((reference == state['manifest']['pythonPin'] or
                 state['dependencies'].get(path) == reference) and
                PurePosixPath(path).suffix.lower() not in
                ('.py', '.pyc', '.json', '.pem', '.key', '.p12', '.pfx'),
                'REPOSITORY_NATIVE_INSTALLED_BINARY_NOT_APPROVED')
        _stream_file(reference, limit=BINARY_LIMIT, elf=True,
                     executable=reference == state['manifest']['pythonPin'], deadline=deadline)
    elif role == 'installed-original':
        _installed_original(reference, state, deadline)
        require(_signed(state['manifestPin'], state['authorityPins'], deadline=deadline) == state['manifest'],
                'REPOSITORY_NATIVE_INSTALLATION_CHANGED')
    else:
        _member_stream(reference, state['catalog'], role, deadline)
    _check_current(state, deadline)
    return document(canonical(reference))


def verify_browser_runtime(browserTrustPin, browserProofPin, authorityPins, expectedIdentityPin,
                           deadline=None, *, browser_identity_selection_pin, private_key_metadata_pin,
                           guard_pin, graph_roots, reserved_output_paths):
    """Explicit B profile; imported only for the separate browser API."""
    from repository_native_browser import verify_browser_runtime as verify
    return verify(browserTrustPin, browserProofPin, authorityPins, expectedIdentityPin, deadline,
                  browser_identity_selection_pin=browser_identity_selection_pin,
                  private_key_metadata_pin=private_key_metadata_pin, guard_pin=guard_pin,
                  graph_roots=graph_roots, reserved_output_paths=reserved_output_paths)


def read_browser_member(reference, trust, proof, *, role, limit=LIMIT, deadline=None, guard_pin):
    from repository_native_browser import read_browser_member as read
    return read(reference, trust, proof, role=role, limit=limit, deadline=deadline, guard_pin=guard_pin)


def verify_browser_file(reference, trust, proof, *, role, deadline=None, guard_pin):
    from repository_native_browser import verify_browser_file as verify
    return verify(reference, trust, proof, role=role, deadline=deadline, guard_pin=guard_pin)
