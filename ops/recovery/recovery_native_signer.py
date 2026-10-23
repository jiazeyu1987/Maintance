"""Separate authority-A role for the W05 native producer's persisted originals.

This is an explicit finite task authority service, not a general signing API.
The independent A launcher supplies current guards, original root, exact live
producer PID/start/UID and its pinned command/source selection. No request may
select the peer, private key, authority, runtime or admission callback. Workers
do not receive this socket descriptor or the key. Provisioning is a required
prerequisite; the producer never starts this service itself.
"""
from __future__ import annotations

import base64
import os
import select
from pathlib import Path
import socket
import stat
import struct
import time

from recovery_environment_contract import canonical, decode, exact, require, pin_file
from recovery_environment_supervisor import identity
from recovery_native_process import (PROCESS_FIELDS, REHEARSAL_ID, lab_path,
    open_lab_file, persist_bytes, pinned_bytes, signed_payload, terminal_status, signer_socket_custody,
    QUALIFICATION_PROCESS_SCHEMA, QUALIFICATION_PROCESS_FIELDS)
from recovery_native_service_identity import SERVICE_FIELDS, probe_commands
from recovery_native_observation import RESULT_FIELDS
from recovery_native_installation_admission import ADMISSION_SCHEMA, ADMISSION_FIELDS


def verify_parent_terminal(payload, raw):
    """Check sole-parent originals before A signs a process attestation."""
    exact(raw, {'terminal', 'supervisorExitCode', 'failureCode', 'stdoutPin', 'stderrPin'},
          'NATIVE_SIGNER_PARENT_ORIGINAL_SHAPE')
    terminal = raw['terminal']
    require(terminal is not None and terminal['model'] == 'linux-owned-child-subreaper-v1' and
            terminal['supervisorPid'] == payload['supervisorPid'] and
            terminal['workerPid'] == payload['childPid'] and raw['stdoutPin'] == payload['stdoutPin'] and
            raw['stderrPin'] == payload['stderrPin'], 'NATIVE_SIGNER_PARENT_BINDING')
    parent = terminal['supervisorIdentity']
    require(parent['startTicks'] == payload['supervisorStartTicks'] and parent['bootId'] == payload['bootId'] and
            parent['namespaces'] == {name: payload[field] for field, name in (
                ('pidNamespace', 'pid'), ('mountNamespace', 'mnt'), ('networkNamespace', 'net'), ('userNamespace', 'user'))},
            'NATIVE_SIGNER_PARENT_IDENTITY')
    require(terminal['dispatch'] == {'argv': payload['argv'], 'cwd': payload['cwd'],
                                    'uid': payload['uid'], 'gid': payload['gid']}, 'NATIVE_SIGNER_ACTUAL_DISPATCH')
    workers = [item for item in terminal['children'] if item['pid'] == payload['childPid']]
    require(len(workers) == 1 and workers[0]['startTicks'] == payload['childStartTicks'] and
            workers[0]['uid'] == payload['uid'] and workers[0]['gid'] == payload['gid'],
            'NATIVE_SIGNER_CHILD_IDENTITY')
    actual = terminal_status(terminal, raw['supervisorExitCode'])
    claimed = tuple(payload[name] for name in ('terminationKind', 'waitStatus', 'actualExitCode', 'descendantState'))
    # Unknown runtime/authority can make known native wait unusable. It must
    # never strengthen an unknown original into a successful terminal status.
    require(claimed == actual or claimed == ('UNKNOWN', None, None, 'UNKNOWN'),
            'NATIVE_SIGNER_WAIT_MISMATCH')
    if claimed[0] == 'EXITED' and claimed[2] == 0:
        require(raw['failureCode'] is None, 'NATIVE_SIGNER_FAILED_COMMAND_ZERO_EXIT')


class AuthoritySigningService:
    def __init__(self, *, socket_path, private_key_pin, authority_key_pin, original_root,
                 producer_pid, producer_start_ticks, producer_uid, guard, admit, deadline,
                 launch_pin=None):
        require(os.name == 'posix' and os.geteuid() > 0 and producer_uid != os.geteuid(),
                'NATIVE_A_ROLE_REQUIRED')
        require(callable(guard) and callable(admit), 'NATIVE_A_ADMISSION_REQUIRED')
        self.path = lab_path(socket_path, exists=False)
        require(not self.path.exists(), 'NATIVE_A_SOCKET_ALREADY_EXISTS')
        self.root = lab_path(original_root, directory=True)
        self.pid, self.ticks, self.peer_uid = producer_pid, producer_start_ticks, producer_uid
        self.guard, self.admit, self.deadline = guard, admit, deadline
        self.authority_key_pin = authority_key_pin
        self.launch_pin = launch_pin
        guard()
        output_directory = self.path.parent.stat()
        require(output_directory.st_uid == output_directory.st_gid == 0 and
                stat.S_IMODE(output_directory.st_mode) == 0o700, 'NATIVE_A_ROOT_CUSTODY_DIRECTORY_REQUIRED')
        status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text(encoding='ascii').splitlines())
        # The independently provisioned A role needs only CHOWN and DAC_OVERRIDE:
        # read root-private originals, then publish the same signed inode under
        # existing root:root custody. This service never grants capabilities.
        require(int(status['CapEff'].strip(), 16) == int(status['CapPrm'].strip(), 16) == 3 and
                all(not int(value.strip(), 16) & ~3 for name, value in status.items() if name.startswith('Cap')) and
                status['NoNewPrivs'].strip() == '1', 'NATIVE_A_FINITE_CUSTODY_CAPABILITIES_REQUIRED')
        key_path = lab_path(private_key_pin['path'])
        info = key_path.stat()
        require(info.st_uid == os.geteuid() and info.st_nlink == 1 and
                stat.S_IMODE(info.st_mode) == 0o400, 'NATIVE_A_PRIVATE_KEY_MODE')
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        self.key = serialization.load_pem_private_key(pinned_bytes(private_key_pin), password=None)
        require(isinstance(self.key, Ed25519PrivateKey), 'NATIVE_A_PRIVATE_KEY_TYPE')
        public = serialization.load_pem_public_key(pinned_bytes(authority_key_pin))
        require(self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) ==
                public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw), 'NATIVE_A_KEY_MISMATCH')

    def _live_peer(self, channel):
        measured = self.guard()
        require(time.monotonic() < self.deadline, 'NATIVE_A_DEADLINE')
        pid, uid, gid = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require(pid == self.pid and uid == self.peer_uid == 0 and gid == 0 and identity(pid)['startTicks'] == self.ticks,
                'NATIVE_A_PRODUCER_PEER_CHANGED')
        require(measured['workerKeyDenial']['worker']['pid'] == pid and
                measured['workerKeyDenial']['worker']['startTicks'] == self.ticks and
                measured['workerKeyDenial']['worker']['mountNamespace'] != measured['signer']['mountNamespace'],
                'NATIVE_A_SECRET_MOUNT_NOT_SEPARATE')

    def _sign(self, reference):
        path = lab_path(reference['path'])
        require(self.root in path.parents and path.name in ('process-original.json',) or
                self.root == path.parent and path.name.endswith(('-identity-original.json', '-observe-original.json',
                                                                '-installation-original.json', 'qualification-original.json')),
                'NATIVE_A_ORIGINAL_NOT_PRODUCER_OWNED')
        metadata = path.stat()
        require(metadata.st_uid == self.peer_uid and metadata.st_nlink == 1 and
                stat.S_IMODE(metadata.st_mode) == 0o600 and os.statvfs(path).f_flag & os.ST_RDONLY,
                'NATIVE_A_ORIGINAL_PRIVATE_MODE_INVALID')
        original = pinned_bytes(reference)
        payload = decode(original)
        version = payload.get('schemaVersion')
        from recovery_native_launcher import QUALIFICATION_RESULT_SCHEMA, QUALIFICATION_RESULT_FIELDS
        fields = PROCESS_FIELDS if version == 'RecoveryNativeProcessResult/v1' else (
            QUALIFICATION_PROCESS_FIELDS if version == QUALIFICATION_PROCESS_SCHEMA else
            QUALIFICATION_RESULT_FIELDS if version == QUALIFICATION_RESULT_SCHEMA else
            SERVICE_FIELDS if version == 'RecoveryNativeServiceIdentity/v1' else
            RESULT_FIELDS if version == 'RepositoryLabNativeObserveResult/v1' else
            ADMISSION_FIELDS if version == ADMISSION_SCHEMA else None)
        require(fields is not None, 'NATIVE_A_PAYLOAD_VERSION')
        exact(payload, fields, 'NATIVE_A_PAYLOAD_SHAPE')
        require(payload['rehearsalId'] == REHEARSAL_ID, 'NATIVE_A_REHEARSAL')
        # The independently provisioned admission includes current actual
        # worker-key access denial as well as request/lease/runtime/source.
        self.guard(); self.admit(payload)
        if version in ('RecoveryNativeProcessResult/v1', QUALIFICATION_PROCESS_SCHEMA):
            require(payload['uid'] >= 0 and payload['uid'] != os.geteuid(), 'NATIVE_A_WORKER_KEY_SEPARATION')
            parent_path = lab_path(path.parent / 'supervisor-terminal.json')
            parent_meta = parent_path.stat()
            require(parent_meta.st_uid == self.peer_uid and stat.S_IMODE(parent_meta.st_mode) == 0o600,
                    'NATIVE_A_PARENT_ORIGINAL_PRIVATE_MODE_INVALID')
            parent = decode(pinned_bytes(pin_file(parent_path)))
            verify_parent_terminal(payload, parent)
            for name in ('stdoutPin', 'stderrPin', 'resultPin'):
                pinned_bytes(payload[name])
        elif version == 'RecoveryNativeServiceIdentity/v1':
            references = [payload[name] for name in ('infoResultPin', 'inspectResultPin', 'networkResultPin')]
            require(len(payload['invocationPins']) == 3, 'NATIVE_A_SERVICE_INVOCATIONS_INCOMPLETE')
            commands = probe_commands(payload['dockerPin'], payload['containerId'], payload['networkId'])
            for pin, raw_pin, argv in zip(payload['invocationPins'], references, commands):
                call = decode(pinned_bytes(pin))
                process = signed_payload(call['processResultPin'], self.authority_key_pin)
                require(call['schemaVersion'] == 'RecoveryInvocation/v1' and call['state'] == 'SUCCEEDED' and
                        call['processProfile'] == 'linux-owned-child-subreaper-v1' and
                        all(call[name] == process[name] == payload[name] for name in
                            ('operationId', 'restoreId', 'targetIdentityPin')) and
                        process['argv'] == call['argv'] == argv and
                        process['resultPin'] == call['resultPin'] == raw_pin and
                        process['terminationKind'] == 'EXITED' and process['actualExitCode'] == 0 and
                        process['waitStatus'] == 0 and process['descendantState'] == 'REAPED' and
                        process['nativeRuntimeProofPin'] == payload['probeRuntimeProofPin'] and
                        payload['probeSourcePin'] in process['sourcePins'], 'NATIVE_A_SERVICE_INVOCATION_UNBOUND')
                pinned_bytes(raw_pin)
        self.guard(); self.admit(payload)
        require(pinned_bytes(reference) == original, 'NATIVE_A_ORIGINAL_CHANGED')
        return self._publish(payload, reference['sha256'] + '.signed.json')

    def _publish(self, payload, name):
        from recovery_native_observation import wire_canonical
        envelope = {'schemaVersion': 'RepositorySignedRecord/v1', 'keySha256': self.authority_key_pin['sha256'],
                    'payload': payload, 'signature': base64.b64encode(self.key.sign(wire_canonical(payload))).decode('ascii')}
        # Output lives in A's own socket directory, inaccessible for worker writes.
        signed = persist_bytes(self.path.parent / name, canonical(envelope))
        fd, parent = open_lab_file(signed['path'], os.O_RDONLY)
        try:
            require(os.fstat(fd).st_uid == os.geteuid(), 'NATIVE_A_SIGNED_ORIGINAL_OWNER_CHANGED')
            os.fchown(fd, 0, 0); os.fsync(fd); os.fsync(parent)
            metadata = os.fstat(fd)
            require(metadata.st_uid == metadata.st_gid == 0 and stat.S_IMODE(metadata.st_mode) == 0o600,
                    'NATIVE_A_SIGNED_ORIGINAL_ROOT_CUSTODY_FAILED')
        finally:
            os.close(fd); os.close(parent)
        pinned_bytes(signed)
        return signed

    def publish_current_identity(self, runtime_proof_pin, expires_at):
        measured = self.guard()
        signer = measured['signer']
        from recovery_native_launcher import CALLER_FIELDS
        from recovery_environment_contract import utc_now
        fields = CALLER_FIELDS - {'schemaVersion', 'rehearsalId', 'nativeRuntimeProofPin', 'issuedAt', 'expiresAt'}
        payload = {name: signer[name] for name in fields}
        payload.update(schemaVersion='RepositoryLabNativeAuthority/v1', rehearsalId=REHEARSAL_ID,
            nativeRuntimeProofPin=runtime_proof_pin, issuedAt=utc_now(), expiresAt=expires_at)
        require(signer['pid'] == os.getpid() and signer['uid'] == os.geteuid() and
                measured['nativeRuntimeProofPin'] == runtime_proof_pin, 'NATIVE_A_CURRENT_IDENTITY_UNMEASURED')
        return self._publish(payload, 'authority-identity.signed.json')

    def serve(self, maximum_records, *, on_ready):
        require(type(maximum_records) is int and 1 <= maximum_records <= 4096, 'NATIVE_A_FINITE_BUDGET')
        require(callable(on_ready), 'NATIVE_A_READY_CALLBACK_REQUIRED')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            parent = self.path.parent.stat()
            require(parent.st_uid == parent.st_gid == 0 and stat.S_IMODE(parent.st_mode) == 0o700,
                    'NATIVE_A_ROOT_CUSTODY_DIRECTORY_REQUIRED')
            server.bind(str(self.path)); os.chmod(self.path, 0o600)
            os.chown(self.path, 0, 0, follow_symlinks=False)
            socket_identity = signer_socket_custody(self.path)
            server.listen(1)
            self.guard()
            signer_socket_custody(self.path, socket_identity)
            require(time.monotonic() < self.deadline, 'NATIVE_A_DEADLINE')
            on_ready()
            handled = 0
            while handled < maximum_records:
                self.guard()
                remaining = self.deadline - time.monotonic()
                require(remaining > 0, 'NATIVE_A_DEADLINE')
                if not select.select([server], [], [], min(.25, remaining))[0]:
                    continue
                signer_socket_custody(self.path, socket_identity)
                with server.accept()[0] as channel:
                    handled += 1
                    channel.settimeout(min(5, remaining)); self._live_peer(channel)
                    raw = b''
                    while not raw.endswith(b'\n'):
                        part = channel.recv(4096)
                        require(part and len(raw) + len(part) <= 16384, 'NATIVE_A_REQUEST_LIMIT')
                        raw += part
                    request = decode(raw)
                    finished = False
                    if set(request) == {'finishLaunchPin'}:
                        require(self.launch_pin is not None and request['finishLaunchPin'] == self.launch_pin,
                                'NATIVE_A_FINISH_LAUNCH_UNSELECTED')
                        self.guard(); reply = {'finishedLaunchPin': self.launch_pin}; finished = True
                    elif set(request) == {'guardRuntimeProofPin'}:
                        measured = self.guard()
                        require(request['guardRuntimeProofPin'] == measured['nativeRuntimeProofPin'],
                                'NATIVE_A_GUARD_PROOF_MISMATCH')
                        reply = {'measurementPin': measured['measurementPin'], 'signer': measured['signer']}
                    else:
                        exact(request, {'originalPin'}, 'NATIVE_A_REQUEST_SHAPE')
                        reply = {'signedPin': self._sign(request['originalPin'])}
                    self._live_peer(channel)
                    signer_socket_custody(self.path, socket_identity)
                    channel.sendall(canonical(reply) + b'\n')
                    if finished:
                        return
            raise RuntimeError('NATIVE_A_FINITE_MESSAGE_BUDGET_EXHAUSTED')
