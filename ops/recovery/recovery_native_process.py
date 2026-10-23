"""Explicit lab native originals, produced by the sole parent, signed by A.

The trusted task-control caller selects the installation, command and guards.
There is no request-selected shell, signing key, transport or runtime. The A
signer is an independently provisioned Unix peer; this module has no private
key API. A missing signer/runtime is a failed prerequisite, never unsigned
success. This profile is not used by the production CommandRunner.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import selectors
import socket
import stat
import struct
import subprocess
import sys
import time

from recovery_environment_contract import (EnvironmentFailure, atomic_json, canonical,
    decode, exact, pin_file, read_bytes, require, safe_path, utc, utc_now)
from recovery_environment_supervisor import (MODEL, SUPERVISOR_SCRIPT,
    OwnedChildSupervisor, SupervisionFailure, identity, prepare_local_supervision)

LAB_ROOT = Path('/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07')
REHEARSAL_ID = 'backup-server-rehearsal-20261012-r1'
PROCESS_FIELDS = set(('schemaVersion rehearsalId operationId restoreId targetIdentityPin recoveryPoint '
    'stage commandId command argv cwd sourcePins supervisorPin pythonPin nativeRuntimeProofPin '
    'hostId bootId pidNamespace mountNamespace networkNamespace userNamespace supervisorPid '
    'supervisorStartTicks childPid childStartTicks uid gid startedAt finishedAt terminationKind '
    'waitStatus actualExitCode descendantState stdoutPin stderrPin resultPin').split())
QUALIFICATION_BINDING_FIELDS = set('qualificationId operationId phase targetId executorId'.split())
QUALIFICATION_PROCESS_SCHEMA = 'RepositoryLabNativeQualificationProcessInvocation/v1'
QUALIFICATION_PROCESS_FIELDS = (PROCESS_FIELDS - {'restoreId', 'targetIdentityPin', 'recoveryPoint', 'stage'} |
                               {'qualificationId', 'phase', 'targetId', 'executorId'})
NS_FIELDS = {'pidNamespace': 'pid', 'mountNamespace': 'mnt',
             'networkNamespace': 'net', 'userNamespace': 'user'}


def pinned_bytes(reference, *, limit=134217728):
    exact(reference, {'path', 'bytes', 'sha256'}, 'NATIVE_PIN_SHAPE')
    fd, parent = open_lab_file(reference['path'], os.O_RDONLY)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= limit,
                'NATIVE_PIN_FILE_UNSAFE')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            # Size the allocation to the observed file, with one byte to detect growth.
            raw = stream.read(before.st_size + 1)
        after = os.fstat(fd)
        require(file_metadata(before) == file_metadata(after), 'NATIVE_PIN_FILE_CHANGED')
        current, current_parent = open_lab_file(reference['path'], os.O_RDONLY)
        try:
            require(file_metadata(after) == file_metadata(os.fstat(current)), 'NATIVE_PIN_PATH_CHANGED')
        finally:
            os.close(current); os.close(current_parent)
    finally:
        os.close(fd); os.close(parent)
    require(type(reference['bytes']) is int and len(raw) == reference['bytes'] and
            hashlib.sha256(raw).hexdigest() == reference['sha256'], 'NATIVE_PIN_MISMATCH')
    return raw


def lab_path(value, *, directory=False, exists=True):
    path = safe_path(str(value), directory=directory, exists=exists)
    require(path != LAB_ROOT and LAB_ROOT in path.parents, 'NATIVE_PATH_OUTSIDE_LAB')
    return path


def file_metadata(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns,
            info.st_uid, info.st_gid, info.st_mode, info.st_nlink)


def open_lab_file(value, flags, mode=0o600):
    """Descriptor-anchor every literal LAB component; never follow an alias."""
    require(sys.platform == 'linux', 'NATIVE_LINUX_REQUIRED')
    path = lab_path(value, exists=False)
    require(str(path) == str(value), 'NATIVE_PATH_NOT_LITERAL')
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:-1]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = following
            metadata = os.fstat(parent)
            require(stat.S_ISDIR(metadata.st_mode) and metadata.st_uid in (0, os.geteuid()) and
                    not metadata.st_mode & 0o022, 'NATIVE_PATH_ANCESTOR_UNSAFE')
        fd = os.open(path.name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, mode, dir_fd=parent)
        return fd, parent
    except BaseException:
        os.close(parent)
        raise


def signed_payload(reference, authority_pin):
    lab_path(reference['path']); lab_path(authority_pin['path'])
    return authenticate_payload(decode(pinned_bytes(reference)), pinned_bytes(authority_pin), authority_pin['sha256'])


def authenticate_payload(record, public_key_bytes, authority_sha256):
    """Only the independently selected public key authenticates an envelope."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    exact(record, {'schemaVersion', 'keySha256', 'payload', 'signature'}, 'NATIVE_SIGNED_SHAPE')
    require(record['schemaVersion'] == 'RepositorySignedRecord/v1' and
            record['keySha256'] == authority_sha256, 'NATIVE_AUTHORITY_MISMATCH')
    key = load_pem_public_key(public_key_bytes)
    require(isinstance(key, Ed25519PublicKey), 'NATIVE_AUTHORITY_KEY_INVALID')
    try:
        import json
        encoded = json.dumps(record['payload'], ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')
        key.verify(base64.b64decode(record['signature'], validate=True), encoded)
    except (InvalidSignature, ValueError, TypeError):
        raise EnvironmentFailure('NATIVE_SIGNATURE_INVALID') from None
    return record['payload']


def persist_bytes(path, data):
    """One exclusive original; never overwrite a previous invocation receipt."""
    path = lab_path(path, exists=False)
    # Keep the selected repository's exact private 0600 mode. Originals are
    # persisted only after terminal wait/reap, and A verifies their actual Pins.
    fd, directory = open_lab_file(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.fsync(directory)
    finally:
        # An incomplete original remains for diagnosis. It is never signed.
        os.close(fd); os.close(directory)
    reference = {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    pinned_bytes(reference)
    return reference


def signer_socket_custody(path, expected=None):
    """Filesystem custody is root's; the connected signing peer is A's UID."""
    path = lab_path(path, exists=False)
    parent = path.parent.lstat(); current = path.lstat()
    return signer_socket_metadata(parent, current, expected)


def signer_socket_metadata(parent, current, expected=None):
    require(stat.S_ISDIR(parent.st_mode) and parent.st_uid == parent.st_gid == 0 and
            stat.S_IMODE(parent.st_mode) == 0o700 and stat.S_ISSOCK(current.st_mode) and
            current.st_uid == current.st_gid == 0 and stat.S_IMODE(current.st_mode) == 0o600,
            'NATIVE_SIGNER_SOCKET_UNSAFE')
    token = (parent.st_dev, parent.st_ino, current.st_dev, current.st_ino,
             current.st_uid, current.st_gid, current.st_mode, current.st_ctime_ns)
    require(expected is None or token == expected, 'NATIVE_SIGNER_SOCKET_REPLACED')
    return token


class IndependentAuthoritySigner:
    """A-only signing handoff with pinned originals and actual SO_PEERCRED.

    The separately installed authority service must independently admit this
    producer and read the persisted Pin itself. It is not part of the worker's
    environment, inherited descriptors or credentials. Its UID, PID/start and
    public key are provisioned by the current independent authority, not by the
    command/request. The response supplies a Pin, never caller-authored bytes.
    """
    def __init__(self, socket_path, peer_pid, peer_start_ticks, peer_uid, authority_pin, guard,
                 worker_key_guard, *, peer_gid, runtime_selector):
        require(callable(worker_key_guard), 'NATIVE_WORKER_KEY_DENIAL_GUARD_REQUIRED')
        require(callable(runtime_selector), 'NATIVE_SIGNER_RUNTIME_SELECTOR_REQUIRED')
        require(type(peer_uid) is int and peer_uid > 0 and type(peer_gid) is int and peer_gid > 0,
                'NATIVE_SIGNER_POSITIVE_IDENTITY_REQUIRED')
        self.path = socket_path
        self.pid, self.ticks, self.uid = peer_pid, peer_start_ticks, peer_uid
        self.gid = peer_gid
        self.authority_pin, self.guard = authority_pin, guard
        self.worker_key_guard = worker_key_guard
        self.runtime_selector = runtime_selector

    def check_worker(self, worker_uid, runtime_proof_pin):
        # UID alone cannot prove that a root worker cannot read A's key. The
        # independent launcher must measure denial in the selected worker root
        # and bind it to this current runtime. No key or denial claim is accepted
        # from the worker/request. This also retains private root:root programs.
        require(type(worker_uid) is int and worker_uid >= 0 and worker_uid != self.uid,
                'NATIVE_SIGNER_ROLE_NOT_SEPARATE')
        require(self.worker_key_guard(worker_uid, runtime_proof_pin) is True,
                'NATIVE_WORKER_KEY_ACCESS_NOT_DENIED')

    def sign(self, original_pin, *, deadline, worker_uid):
        require(sys.platform == 'linux' and worker_uid != self.uid,
                'NATIVE_SIGNER_ROLE_NOT_SEPARATE')
        self.guard()
        path = lab_path(self.path, exists=False)
        socket_identity = signer_socket_custody(path)
        expected = decode(pinned_bytes(original_pin))
        runtime_pin = self.runtime_selector(expected)
        require(runtime_pin is not None, 'NATIVE_SIGNER_RUNTIME_REQUIRED')
        self.check_worker(worker_uid, runtime_pin)
        remaining = deadline - time.monotonic()
        require(remaining > 0, 'NATIVE_SIGNING_DEADLINE')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.settimeout(min(5, remaining)); channel.connect(str(path))
            pid, uid, gid = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            require(pid == self.pid and uid == self.uid and gid == self.gid and identity(pid)['startTicks'] == self.ticks,
                    'NATIVE_SIGNER_PEER_CHANGED')
            # Physical mount/key separation is measured by A's independent
            # privileged parent. A is nondumpable; a capability-free producer
            # cannot inspect A's /proc root or namespace descriptors directly.
            # A serves one request at a time. A second key-guard connection
            # here would deadlock this still-empty sign request. A independently
            # measures the worker on this connection; client rechecks after close.
            signer_socket_custody(path, socket_identity)
            channel.sendall(canonical({'originalPin': original_pin}) + b'\n')
            raw = b''
            while not raw.endswith(b'\n'):
                require(time.monotonic() < deadline, 'NATIVE_SIGNING_DEADLINE')
                part = channel.recv(4096)
                require(part and len(raw) + len(part) <= 16384, 'NATIVE_SIGNER_REPLY_INVALID')
                raw += part
            response = decode(raw)
            exact(response, {'signedPin'}, 'NATIVE_SIGNER_REPLY_SHAPE')
            require(identity(pid)['startTicks'] == self.ticks, 'NATIVE_SIGNER_PEER_CHANGED')
        self.guard()
        signer_socket_custody(path, socket_identity)
        require(self.runtime_selector(expected) == runtime_pin, 'NATIVE_SIGNER_RUNTIME_CHANGED')
        self.check_worker(worker_uid, runtime_pin)
        require(signed_payload(response['signedPin'], self.authority_pin) == expected,
                'NATIVE_SIGNER_PAYLOAD_CHANGED')
        require(decode(pinned_bytes(original_pin)) == expected, 'NATIVE_ORIGINAL_CHANGED')
        return response['signedPin']


def terminal_status(terminal, supervisor_exit):
    """Only waitpid originals can establish a terminal worker status."""
    if terminal is None or supervisor_exit != 0 or terminal.get('unknown') is not False:
        return 'UNKNOWN', None, None, 'UNKNOWN'
    children = terminal.get('children', [])
    workers = [item for item in children if item['pid'] == terminal['workerPid']]
    if len(workers) != 1 or type(workers[0].get('actualWaitStatus')) is not int:
        return 'UNKNOWN', None, None, 'UNKNOWN'
    status = workers[0]['actualWaitStatus']
    # The selected profile is Linux waitpid, even when its retained original is
    # reviewed on Windows. Do not use Windows' different wait-status encoding.
    if not 0 <= status <= 65535 or status & 0x7f == 0x7f:
        return 'UNKNOWN', None, None, 'UNKNOWN'
    exited = status & 0x7f == 0
    if (exited and status & 0xff != 0) or (not exited and status >> 8 != 0):
        return 'UNKNOWN', None, None, 'UNKNOWN'
    code = (status >> 8) & 0xff if exited else -(status & 0x7f)
    if code != terminal.get('actualExitCode'):
        return 'UNKNOWN', None, None, 'UNKNOWN'
    reaped = terminal.get('treeTerminated') is True and all(item.get('reaped') is True for item in children)
    return ('EXITED' if exited else 'SIGNALED'), status, code, ('REAPED' if reaped else 'UNKNOWN')


def verify_process_source(pin, manifest, trust, *, executable_pin, deadline, qualification):
    """Dispatch exact installed membership before invoking the mandatory reader.

    A non-executable manifest original is not an ELF executable. Python source
    and catalogued native members keep their separate consumption paths. The
    shared reader performs installed-original custody, format and proof checks;
    its absence or rejection is propagated before spawning a process.
    """
    from repository_native_runtime import verify_native_file
    native = next((entry for entry in trust['nativeFilePins'] if entry['pin'] == pin), None)
    if native is not None:
        require(qualification or 'native-tool' in native['roles'], 'NATIVE_SOURCE_ROLE_NOT_ADMITTED')
        require(native['roles'] and not (pin == executable_pin and
                'native-browser-resource' in native['roles']), 'NATIVE_BROWSER_RESOURCE_NOT_EXECUTABLE')
        role = ('native-browser-resource' if native['roles'] == ['native-browser-resource']
                else native['roles'][0])
    elif pin == manifest['pythonPin']:
        role = 'installed-binary'
    elif pin in manifest['dependencyPins'] or pin == executable_pin:
        require(pin in manifest['filePins'] + manifest['dependencyPins'], 'NATIVE_SOURCE_NOT_INSTALLED')
        if Path(pin['path']).suffix == '.py':
            return pinned_bytes(pin)
        role = 'installed-binary'
    elif pin in manifest['filePins'] and LAB_ROOT in Path(pin['path']).parents:
        if Path(pin['path']).suffix == '.py':
            return pinned_bytes(pin)
        role = 'installed-original'
    else:
        raise EnvironmentFailure('NATIVE_SOURCE_NOT_INSTALLED')
    return verify_native_file(pin, manifest['nativeRuntimeTrustPin'], manifest['nativeRuntimeProofPin'],
                              role=role, deadline=deadline)


class NativeProcessProducer:
    def __init__(self, *, evidence_root, installation_pin, authority_pin, signer,
                 authority_guard, dispatch_guard, worker_uid, worker_gid, deadline):
        require(sys.platform == 'linux', 'NATIVE_LINUX_REQUIRED')
        require(type(worker_uid) is int and worker_uid >= 0 and type(worker_gid) is int and worker_gid >= 0,
                'NATIVE_WORKER_IDENTITY_REQUIRED')
        require(worker_uid != signer.uid, 'NATIVE_SIGNER_ROLE_NOT_SEPARATE')
        self.root = lab_path(evidence_root, directory=True)
        self.installation_pin, self.authority_pin = installation_pin, authority_pin
        self.signer, self.authority_guard = signer, authority_guard
        require(callable(dispatch_guard), 'NATIVE_DISPATCH_GUARD_REQUIRED')
        self.dispatch_guard = dispatch_guard
        self.uid, self.gid, self.deadline = worker_uid, worker_gid, deadline

    def guard(self):
        require(time.monotonic() < self.deadline, 'NATIVE_DEADLINE_EXCEEDED')
        self.authority_guard()

    def runtime(self):
        # Mandatory shared verified reader; absence is not a direct-path fallback.
        from repository_native_runtime import verify_native_installation, read_native_member, verify_native_file
        self.guard()
        manifest = verify_native_installation(self.installation_pin, [self.authority_pin], deadline=self.deadline)
        require(manifest['schemaVersion'] == 'RepositoryNativeInstallation/v2', 'NATIVE_EXPLICIT_V2_REQUIRED')
        proof = signed_payload(manifest['nativeRuntimeProofPin'], self.authority_pin)
        trust = signed_payload(manifest['nativeRuntimeTrustPin'], self.authority_pin)
        require(proof['schemaVersion'] == 'RepositoryLabNativeRuntimeProof/v1' and
                proof['rehearsalId'] == REHEARSAL_ID and trust['rehearsalId'] == REHEARSAL_ID and
                proof['nativeRuntimeTrustPin'] == manifest['nativeRuntimeTrustPin'], 'NATIVE_RUNTIME_BINDING')
        require(utc(proof['issuedAt']) <= datetime.now(timezone.utc) < utc(proof['expiresAt']),
                'NATIVE_RUNTIME_EXPIRED')
        require(Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip() == proof['bootId'] and
                Path('/etc/machine-id').read_text(encoding='ascii').strip() == proof['hostId'],
                'NATIVE_RUNTIME_HOST_CHANGED')
        require(all(os.readlink('/proc/self/ns/' + name) == proof[field] for field, name in NS_FIELDS.items()),
                'NATIVE_RUNTIME_NAMESPACE_CHANGED')
        root = os.stat('/proc/self/root')
        require((root.st_dev, root.st_ino) == (proof['rootDevice'], proof['rootInode']), 'NATIVE_RUNTIME_ROOT_CHANGED')
        capabilities = dict(line.split(':', 1) for line in
                            Path('/proc/self/status').read_text(encoding='ascii').splitlines())
        require(all(not int(value.strip(), 16) & (1 << 19) for name, value in capabilities.items()
                    if name.startswith('Cap')), 'NATIVE_WORKER_SIGNER_PTRACE_AUTHORITY_PRESENT')
        require(Path(sys.executable) == Path(manifest['pythonPin']['path']), 'NATIVE_PYTHON_CHANGED')
        verify_native_file(manifest['pythonPin'], manifest['nativeRuntimeTrustPin'],
                           manifest['nativeRuntimeProofPin'], role='installed-binary', deadline=self.deadline)
        return manifest, trust, proof, read_native_member

    def run(self, *, command_id, argv, cwd, source_pins, binding, result_path=None):
        """Run exact admitted inputs; returns invocation Pin even for failure.

        binding has the current operation/restore/target/recoveryPoint/stage.
        The trusted authority guard must bind these inputs before dispatch. It
        cannot be replaced by a request-provided callback. Raw output is only
        appropriate for an admitted command that never emits credentials.
        """
        exact(binding, {'operationId', 'restoreId', 'targetIdentityPin', 'recoveryPoint', 'stage'},
              'NATIVE_OPERATION_BINDING_SHAPE')
        return self._run(command_id=command_id, argv=argv, cwd=cwd, source_pins=source_pins,
                         binding=binding, result_path=result_path, qualification=False)

    def run_qualification(self, *, command_id, argv, cwd, source_pins, binding):
        """Separate finite phase; returns the signed process original, never a business invocation."""
        exact(binding, QUALIFICATION_BINDING_FIELDS, 'NATIVE_QUALIFICATION_BINDING_SHAPE')
        require(binding['phase'] == 'NATIVE_QUALIFICATION' and all(type(binding[k]) is str and
                binding[k] and binding[k].isascii() for k in QUALIFICATION_BINDING_FIELDS),
                'NATIVE_QUALIFICATION_BINDING_INVALID')
        return self._run(command_id=command_id, argv=argv, cwd=cwd, source_pins=source_pins,
                         binding=binding, result_path=None, qualification=True)

    def _run(self, *, command_id, argv, cwd, source_pins, binding, result_path, qualification):
        require(type(command_id) is str and command_id and command_id.isascii() and
                all(c.isalnum() or c in '-_' for c in command_id), 'NATIVE_COMMAND_ID_INVALID')
        require(type(argv) is list and argv and all(type(s) is str and '\x00' not in s for s in argv),
                'NATIVE_ARGV_INVALID')
        cwd = str(lab_path(cwd, directory=True))
        self.dispatch_guard(dict(binding, commandId=command_id, argv=argv, cwd=cwd, sourcePins=source_pins))
        manifest, trust, proof, native_read = self.runtime()
        self.signer.check_worker(self.uid, manifest['nativeRuntimeProofPin'])
        selected = manifest['filePins'] + manifest['dependencyPins'] + [manifest['pythonPin']]
        selected += [entry['pin'] for entry in trust['nativeFilePins']
                     if qualification or 'native-tool' in entry['roles']]
        require(source_pins and all(pin in selected for pin in source_pins), 'NATIVE_SOURCE_NOT_INSTALLED')
        supervisor_pin = next((pin for pin in selected if pin['path'] == str(SUPERVISOR_SCRIPT)), None)
        executable = next((pin for pin in source_pins if pin['path'] == argv[0]), None)
        require(supervisor_pin is not None and executable is not None, 'NATIVE_DISPATCH_SOURCE_UNBOUND')
        executable_entry = next((e for e in trust['nativeFilePins'] if e['pin'] == executable), None)
        require(executable_entry is None or 'native-browser-resource' not in executable_entry['roles'],
                'NATIVE_BROWSER_RESOURCE_NOT_EXECUTABLE')
        if qualification:
            from recovery_native_launcher import browser_resource_pins
            resources = browser_resource_pins(trust)
            require(not any(p['path'] in argv for p in resources), 'NATIVE_BROWSER_RESOURCE_NOT_PROGRAM_ARGUMENT')
        require(supervisor_pin in source_pins and manifest['pythonPin'] in source_pins,
                'NATIVE_SUPERVISOR_AND_PYTHON_SOURCE_REQUIRED')
        for pin in source_pins + [supervisor_pin]:
            verify_process_source(pin, manifest, trust, executable_pin=executable,
                                  deadline=self.deadline, qualification=qualification)
        if result_path is not None:
            result_path = lab_path(result_path, exists=False)
            require(not result_path.exists(), 'NATIVE_RESULT_ALREADY_EXISTS')
        destination = self.root / command_id
        destination.mkdir(mode=0o700)  # collision is a failure; no receipt replacement
        started = utc_now()
        stdout_limit = 134217728 if len(argv) > 2 and argv[2] == 'admit-installation' else 16 * 1024 * 1024
        process = OwnedChildSupervisor(argv, env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin',
            'LC_ALL': 'C', 'LANG': 'C', 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1',
            'INTRUOYI_NATIVE_DEADLINE_MONOTONIC': repr(self.deadline)},
            stdin=None, cwd=cwd, user=self.uid, group=self.gid, no_new_privileges=True,
            inherit_identity=True)
        output, error = bytearray(), bytearray()
        failure = None
        runtime_lost = False
        try:
            prepare_local_supervision(); self.guard()
            self.signer.check_worker(self.uid, manifest['nativeRuntimeProofPin'])
            self.dispatch_guard(dict(binding, commandId=command_id, argv=argv, cwd=cwd, sourcePins=source_pins))
            process.spawn()
            process.start(min(5, self.deadline - time.monotonic()), guard=self.guard, deadline=self.deadline)
            self._drain(process, output, error, stdout_limit=stdout_limit)
            process.members()
            try:
                self.guard(); self.runtime()
                self.signer.check_worker(self.uid, manifest['nativeRuntimeProofPin'])
            except BaseException:
                runtime_lost = True
                raise
        except BaseException as exc:
            failure = getattr(exc, 'code', 'NATIVE_EXECUTION_OR_IO_FAILED')
            if process.process is not None:
                try:
                    # Cancellation signals the sole parent; no PID/group guessing.
                    process.channel.shutdown(socket.SHUT_WR)
                    self._drain(process, output, error, stdout_limit=stdout_limit, cancelling=True)
                except BaseException:
                    failure = 'NATIVE_TREE_OR_TERMINAL_UNPROVEN'
        finally:
            process.close()
        kind, status, code, descendants = terminal_status(process.terminal,
            None if process.process is None else process.process.returncode)
        if runtime_lost or failure is not None and failure in ('NATIVE_TREE_OR_TERMINAL_UNPROVEN',
                                               'NATIVE_RUNTIME_EXPIRED', 'NATIVE_RUNTIME_NAMESPACE_CHANGED',
                                               'NATIVE_RUNTIME_ROOT_CHANGED', 'NATIVE_RUNTIME_HOST_CHANGED'):
            kind, status, code, descendants = 'UNKNOWN', None, None, 'UNKNOWN'
        if failure is not None and code == 0:
            kind, status, code, descendants = 'UNKNOWN', None, None, 'UNKNOWN'
        stdout_pin = persist_bytes(destination / 'stdout', bytes(output))
        stderr_pin = persist_bytes(destination / 'stderr', bytes(error))
        terminal_pin = persist_bytes(destination / 'supervisor-terminal.json', canonical({
            'terminal': process.terminal, 'supervisorExitCode': None if process.process is None else process.process.returncode,
            'failureCode': failure, 'stdoutPin': stdout_pin, 'stderrPin': stderr_pin}))
        result_pin = stdout_pin
        if result_path is not None:
            if result_path.exists():
                result_pin = pin_file(result_path); pinned_bytes(result_pin)
                metadata = result_path.stat()
                require(metadata.st_uid == metadata.st_gid == 0 and metadata.st_nlink == 1 and
                        stat.S_IMODE(metadata.st_mode) == 0o600, 'NATIVE_RESULT_PRIVATE_MODE_INVALID')
            else:
                failure = 'NATIVE_RESULT_MISSING'; result_pin = terminal_pin
        parent = process.supervisor_identity
        worker = next((item for item in process.observed if item['pid'] == process.pid), None)
        if (parent is None or worker is None or process.dispatch !=
                {'argv': argv, 'cwd': cwd, 'uid': self.uid, 'gid': self.gid} or
                worker.get('uid') != self.uid or worker.get('gid') != self.gid or
                parent.get('uid') != os.getuid() or parent.get('gid') != os.getgid() or
                parent.get('bootId') != proof['bootId'] or
                parent.get('namespaces') != {name: proof[field] for field, name in NS_FIELDS.items()}):
            kind, status, code, descendants = 'UNKNOWN', None, None, 'UNKNOWN'
        from recovery_native_observation import wire_canonical
        record = dict(binding, schemaVersion=QUALIFICATION_PROCESS_SCHEMA if qualification else
            'RecoveryNativeProcessResult/v1', rehearsalId=REHEARSAL_ID,
            commandId=command_id, command=wire_canonical(argv).decode('utf-8'), argv=argv, cwd=cwd,
            sourcePins=source_pins, supervisorPin=supervisor_pin, pythonPin=manifest['pythonPin'],
            nativeRuntimeProofPin=manifest['nativeRuntimeProofPin'], hostId=proof['hostId'], bootId=proof['bootId'],
            **{field: proof[field] for field in NS_FIELDS}, supervisorPid=process.supervisor_pid,
            supervisorStartTicks=None if parent is None else parent['startTicks'], childPid=process.pid,
            childStartTicks=None if worker is None else worker['startTicks'], uid=self.uid, gid=self.gid,
            startedAt=started, finishedAt=utc_now(), terminationKind=kind, waitStatus=status,
            actualExitCode=code, descendantState=descendants, stdoutPin=stdout_pin,
            stderrPin=stderr_pin, resultPin=result_pin)
        exact(record, QUALIFICATION_PROCESS_FIELDS if qualification else PROCESS_FIELDS, 'NATIVE_PROCESS_SHAPE')
        original = persist_bytes(destination / 'process-original.json', canonical(record))
        signed = self.signer.sign(original, deadline=self.deadline, worker_uid=self.uid)
        state = ('TERMINAL_UNKNOWN' if kind == 'UNKNOWN' or descendants == 'UNKNOWN' else
                 'FAILED_RETAINED' if failure or code != 0 or kind != 'EXITED' else 'SUCCEEDED')
        if qualification:
            if state != 'SUCCEEDED':
                raise EnvironmentFailure(failure or 'NATIVE_PROCESS_FAILED', unknown=state == 'TERMINAL_UNKNOWN',
                                         result=signed)
            return signed
        invocation = {key: record[key] for key in ('operationId', 'restoreId', 'targetIdentityPin', 'recoveryPoint',
            'stage', 'actualExitCode', 'startedAt', 'finishedAt', 'sourcePins', 'resultPin',
            'commandId', 'command', 'argv', 'cwd')}
        invocation.update(schemaVersion='RecoveryInvocation/v1', state=state,
                          processProfile=MODEL, processResultPin=signed)
        invocation_pin = persist_bytes(destination / 'invocation.json', canonical(invocation))
        if state != 'SUCCEEDED':
            raise EnvironmentFailure(failure or 'NATIVE_PROCESS_FAILED', unknown=state == 'TERMINAL_UNKNOWN',
                                     result=invocation_pin)
        return invocation_pin

    def _drain(self, process, output, error, *, stdout_limit, cancelling=False):
        until = time.monotonic() + 6 if cancelling else self.deadline
        with selectors.DefaultSelector() as selected:
            for stream, buffer, limit in ((process.process.stdout, output, stdout_limit),
                                          (process.process.stderr, error, 1024 * 1024)):
                os.set_blocking(stream.fileno(), False)
                selected.register(stream, selectors.EVENT_READ, (buffer, limit))
            while selected.get_map() or process.process.poll() is None:
                require(time.monotonic() < until, 'NATIVE_TREE_OR_TERMINAL_UNPROVEN' if cancelling else 'NATIVE_DEADLINE_EXCEEDED')
                if not cancelling:
                    self.guard()
                process._receive(0)
                for item, _ in selected.select(0.05):
                    chunk = os.read(item.fileobj.fileno(), 65536)
                    if not chunk:
                        selected.unregister(item.fileobj)
                    else:
                        buffer, limit = item.data
                        available = limit - len(buffer)
                        buffer.extend(chunk[:available])
                        if len(chunk) > available and not cancelling:
                            raise EnvironmentFailure('NATIVE_OUTPUT_LIMIT')
            process.process.wait(timeout=max(0.001, until - time.monotonic()))
            while not process.channel_closed:
                require(time.monotonic() < until, 'NATIVE_TREE_OR_TERMINAL_UNPROVEN')
                process._receive(0.05)
            require(process.terminal is not None and not process.buffer, 'NATIVE_TREE_OR_TERMINAL_UNPROVEN')
