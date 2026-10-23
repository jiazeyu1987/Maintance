"""Bound observations from an inherited, independently approved native author.

This is a private author channel, separate from the frozen consumer control
stream. It accepts observations only; it never transports executable commands,
selects another peer, reconnects or retries a request.
"""
import base64
import hashlib
import os
from pathlib import Path
import secrets
import socket
import stat
import struct
import threading
import time

from formal_normal_owner import canonical, integer, pin, require, strict_document

OBSERVATIONS = frozenset({
    'allocation-local', 'allocation-nas', 'allocation-staging', 'admission-nas',
    'admission-staging', 'control-budget', 'repository-parent', 'writer-protection',
})
MAX_FRAME = 96 * 1024 * 1024


def validate_channel(value):
    fields = {'schemaVersion', 'fd', 'peerPid', 'peerUid', 'peerGid',
              'peerStartTicks', 'hostBootId', 'pidNamespace', 'mountNamespace',
              'programPin', 'bindingSha256'}
    require(type(value) is dict and set(value) == fields and
            value['schemaVersion'] == 'backup-native-observation-channel/v1',
            'BACKUP_INTERFACE_SCHEMA_INVALID')
    for name in ('fd', 'peerPid', 'peerStartTicks'):
        integer(value[name], 3 if name == 'fd' else 1)
    require(type(value['peerUid']) is int and value['peerUid'] == 0 and
            type(value['peerGid']) is int and value['peerGid'] == 0,
            'BACKUP_INTERFACE_AUTHORITY_INVALID')
    for name in ('hostBootId', 'pidNamespace', 'mountNamespace'):
        require(type(value[name]) is str and value[name], 'BACKUP_INTERFACE_SCHEMA_INVALID')
    pin(value['programPin'])
    require(type(value['bindingSha256']) is str and len(value['bindingSha256']) == 64 and
            all(c in '0123456789abcdef' for c in value['bindingSha256']),
            'BACKUP_INTERFACE_SCHEMA_INVALID')
    return value


def validate_reply(raw, *, nonce, sequence, binding_sha256, expected_reference):
    value = strict_document(raw, MAX_FRAME)
    require(type(value) is dict and set(value) == {'schemaVersion', 'nonce', 'sequence',
            'bindingSha256', 'reference', 'payloadBase64'} and
            value['schemaVersion'] == 'backup-native-observation-reply/v1' and
            value['nonce'] == nonce and type(value['sequence']) is int and
            value['sequence'] == sequence and value['bindingSha256'] == binding_sha256,
            'BACKUP_INTERFACE_BINDING_INVALID')
    reference = pin(value['reference'])
    if expected_reference is not None:
        require(reference == pin(expected_reference), 'BACKUP_INTERFACE_SOURCE_CHANGED')
    require(type(value['payloadBase64']) is str, 'BACKUP_INTERFACE_SCHEMA_INVALID')
    try:
        payload = base64.b64decode(value['payloadBase64'], validate=True)
    except (ValueError, TypeError) as error:
        from formal_snapshot_linux import FormalSnapshotError
        raise FormalSnapshotError('BACKUP_INTERFACE_SCHEMA_INVALID') from error
    require(len(payload) == reference['bytes'] and
            hashlib.sha256(payload).hexdigest() == reference['sha256'],
            'BACKUP_INTERFACE_SOURCE_CHANGED')
    return payload, reference


class NativeObservationChannel:
    """Keep the exact acquiring process, inherited FD and native peer epoch."""
    def __init__(self, configuration, *, original_guard, deadline, control_device):
        from formal_filesystem_watchdog import require_native_runtime
        import formal_boot_state as boot
        require_native_runtime()
        require(os.geteuid() == 0 and callable(original_guard),
                'BACKUP_INTERFACE_NATIVE_PREREQUISITE_REQUIRED')
        self.configuration = strict_document(canonical(validate_channel(configuration)))
        self.configuration_raw = canonical(self.configuration)
        self.guard = original_guard
        self.deadline = deadline
        self.pid = os.getpid()
        self.thread = threading.get_ident()
        self.fd = self.configuration['fd']
        self.fd_identity = boot._signature(os.fstat(self.fd))
        require(stat.S_ISSOCK(self.fd_identity[4]), 'BACKUP_INTERFACE_AUTHOR_LOST')
        self.program_path = boot._absolute(self.configuration['programPin']['path'])
        self.program = boot._read_secure(self.program_path, 0o600, 1048576, no_atime=True)
        require(self.program[1][0] == control_device and
                len(self.program[0]) == self.configuration['programPin']['bytes'] and
                hashlib.sha256(self.program[0]).hexdigest() == self.configuration['programPin']['sha256'],
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        with boot._directory(self.program_path.parent, no_atime=True) as (_, chain):
            self.program_directory = chain
        self.sequence = 0
        self.busy = False
        self.socket = socket.socket(fileno=self.fd)
        # The inherited descriptor remains owned by its launcher. Detach it
        # from this wrapper during teardown rather than closing an unrelated FD.
        try:
            require(self.socket.family == socket.AF_UNIX and
                    self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) == socket.SOCK_STREAM,
                    'BACKUP_INTERFACE_AUTHOR_LOST')
            self.check()
        except BaseException:
            self.socket.detach()
            raise

    def check(self):
        import formal_boot_state as boot
        self.guard()
        require(os.getpid() == self.pid and threading.get_ident() == self.thread and
                time.monotonic() < self.deadline and self.socket.fileno() == self.fd and
                boot._signature(os.fstat(self.fd)) == self.fd_identity and
                canonical(self.configuration) == self.configuration_raw,
                'BACKUP_INTERFACE_AUTHOR_LOST')
        expected = self.configuration
        actual = struct.unpack('3i', self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require(actual == (expected['peerPid'], expected['peerUid'], expected['peerGid']),
                'BACKUP_INTERFACE_AUTHOR_LOST')
        process = Path('/proc') / str(expected['peerPid'])
        with (process/'stat').open('rb') as stream:
            raw_stat = stream.read(4097)
        require(0 < len(raw_stat) <= 4096, 'BACKUP_INTERFACE_AUTHOR_LOST')
        fields = raw_stat[raw_stat.rfind(b')')+2:].split()
        require(len(fields) > 19 and int(fields[19]) == expected['peerStartTicks'] and
                fields[0] not in (b'Z', b'X') and
                Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip() == expected['hostBootId'] and
                os.readlink(process/'ns/pid') == expected['pidNamespace'] and
                os.readlink(process/'ns/mnt') == expected['mountNamespace'],
                'BACKUP_INTERFACE_AUTHOR_LOST')
        with (process/'status').open('rb') as stream:
            status = stream.read(65537)
        require(0 < len(status) <= 65536, 'BACKUP_INTERFACE_AUTHOR_LOST')
        credentials = {line.split(b':', 1)[0]: line.split(b':', 1)[1].split()
                       for line in status.splitlines() if line.startswith((b'Uid:', b'Gid:'))}
        require(credentials == {b'Uid': [b'0']*4, b'Gid': [b'0']*4},
                'BACKUP_INTERFACE_AUTHOR_LOST')
        with (process/'cmdline').open('rb') as stream:
            command = stream.read(65537)
        require(0 < len(command) <= 65536 and os.fsencode(self.program_path) in command.split(b'\0'),
                'BACKUP_INTERFACE_AUTHOR_LOST')
        boot._directory_unchanged(self.program_path.parent, self.program_directory)
        require(boot._read_secure(self.program_path, 0o600, 1048576, no_atime=True) == self.program,
                'BACKUP_INTERFACE_SOURCE_CHANGED')
        self.guard()
        require(boot._signature(os.fstat(self.fd)) == self.fd_identity and
                boot._signature(self.program_path.lstat()) == self.program[1],
                'BACKUP_INTERFACE_AUTHOR_LOST')

    def exchange(self, action, payload, *, expected_reference, deadline):
        require(action in OBSERVATIONS and type(payload) is dict and not self.busy,
                'BACKUP_INTERFACE_SEQUENCE_INVALID')
        self.deadline = min(self.deadline, deadline)
        self.check()
        self.sequence += 1
        nonce = secrets.token_hex(32)
        request = canonical(dict(schemaVersion='backup-native-observation-request/v1', action=action,
            nonce=nonce, sequence=self.sequence, bindingSha256=self.configuration['bindingSha256'],
            input=payload, expectedReference=expected_reference))
        require(len(request) <= 1048576, 'BACKUP_INTERFACE_SCHEMA_INVALID')
        self.busy = True
        sent = time.monotonic()
        try:
            def within():
                remaining = self.deadline-time.monotonic()
                require(remaining > 0, 'BACKUP_INTERFACE_BUDGET_EXPIRED')
                self.socket.settimeout(remaining)

            within()
            self.socket.sendall(struct.pack('!I', len(request))+request)

            def take(count):
                parts = bytearray()
                while len(parts) < count:
                    within()
                    part = self.socket.recv(min(count-len(parts), 1048576))
                    require(bool(part), 'BACKUP_INTERFACE_COMPONENT_FAILED')
                    parts.extend(part)
                return bytes(parts)

            length = struct.unpack('!I', take(4))[0]
            require(0 < length <= MAX_FRAME, 'BACKUP_INTERFACE_SCHEMA_INVALID')
            response = take(length)
            received = time.monotonic()
            raw, reference = validate_reply(response, nonce=nonce, sequence=self.sequence,
                binding_sha256=self.configuration['bindingSha256'], expected_reference=expected_reference)
            self.check()
            return raw, reference, self.sequence, sent, received, self.check
        except (OSError, TimeoutError) as error:
            # Delivery uncertainty is terminal. A subsequent operation cannot
            # replay this request on the same channel or a replacement peer.
            self.deadline = 0
            from formal_snapshot_linux import FormalSnapshotError
            raise FormalSnapshotError('BACKUP_INTERFACE_TERMINAL_UNKNOWN') from error
        except BaseException:
            self.deadline = 0
            raise
        finally:
            self.busy = False

    def close(self):
        if self.socket.fileno() != -1:
            self.socket.detach()
