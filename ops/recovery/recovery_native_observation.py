"""Finite R7 control intent transport; only protected native identity probes."""
from __future__ import annotations

from datetime import datetime, timezone
import re
import json
import select
import socket
import stat
import struct
import time

from recovery_environment_contract import canonical, decode, exact, require, utc, utc_now
from recovery_environment_supervisor import identity
from recovery_native_process import (REHEARSAL_ID, lab_path, persist_bytes, pinned_bytes, signed_payload)
from recovery_native_installation_admission import (invocation_originals, produce_installation_admission,
                                                   unique_originals)

MAX_FRAME = 1048576
REQUEST_FIELDS = set('schemaVersion rehearsalId collectionId sequence phase operationRequestPin serviceBindingPin issuedAt deadlineMilliseconds'.split())
RESULT_FIELDS = set('schemaVersion rehearsalId collectionId sequence phase operationRequestPin serviceBindingPin identityProofPin originalPins probeStartedAt probeFinishedAt issuedAt expiresAt'.split())


def wire_canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def receive_frame(channel, deadline):
    def read(count):
        data = bytearray()
        while len(data) < count:
            remaining = deadline - time.monotonic()
            require(remaining > 0, 'NATIVE_OBSERVE_DEADLINE')
            channel.settimeout(min(5, remaining))
            part = channel.recv(count - len(data))
            require(part, 'NATIVE_OBSERVE_TRUNCATED_FRAME')
            data.extend(part)
        return bytes(data)
    size, = struct.unpack('!I', read(4))
    require(0 < size <= MAX_FRAME, 'NATIVE_OBSERVE_FRAME_LIMIT')
    raw = read(size); value = decode(raw)
    require(wire_canonical(value) == raw, 'NATIVE_OBSERVE_NONCANONICAL_FRAME')
    return value


def send_frame(channel, value, deadline):
    raw = wire_canonical(value)
    require(0 < len(raw) <= MAX_FRAME and time.monotonic() < deadline, 'NATIVE_OBSERVE_FRAME_LIMIT')
    channel.settimeout(min(5, deadline - time.monotonic()))
    channel.sendall(struct.pack('!I', len(raw)) + raw)


class ObservationOrder:
    """A failed intent consumes its sequence; it cannot be retried as success."""
    def __init__(self, maximum):
        require(type(maximum) is int and 2 <= maximum <= 64, 'NATIVE_OBSERVE_FINITE_BUDGET')
        self.maximum, self.sequence, self.collections = maximum, 0, {}

    def reserve(self, request):
        exact(request, REQUEST_FIELDS, 'NATIVE_OBSERVE_REQUEST_SHAPE')
        require(request['schemaVersion'] == 'RepositoryLabNativeObserveRequest/v1' and
                request['rehearsalId'] == REHEARSAL_ID, 'NATIVE_OBSERVE_REQUEST_VERSION')
        collection = request['collectionId']; sequence = request['sequence']; phase = request['phase']
        require(type(collection) is str and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', collection) and
                type(sequence) is int and sequence == self.sequence + 1 and sequence <= self.maximum,
                'NATIVE_OBSERVE_REPLAY_OR_SEQUENCE')
        require(phase in ('BEFORE', 'AFTER') and
                (phase == 'BEFORE' and collection not in self.collections or
                 phase == 'AFTER' and self.collections.get(collection) == ('BEFORE', request['serviceBindingPin'])),
                'NATIVE_OBSERVE_PHASE_OR_BINDING')
        self.sequence = sequence; self.collections[collection] = (phase, request['serviceBindingPin'])


def observation_originals(identity_pin, authority_pin, root, static_pins):
    """Admit only exact newly produced finite originals, never directory scans."""
    identity_record = signed_payload(identity_pin, authority_pin)
    require(identity_record['schemaVersion'] == 'RecoveryNativeServiceIdentity/v1', 'NATIVE_OBSERVE_IDENTITY_SCHEMA')
    closure = [identity_pin]; intervals = []
    for invocation_pin in identity_record['invocationPins']:
        originals, call, process = invocation_originals(invocation_pin, authority_pin, root)
        intervals.append((utc(process['startedAt']), utc(process['finishedAt'])))
        closure += originals
    require(len(intervals) == 3 and all(a <= b for a, b in intervals), 'NATIVE_OBSERVE_INTERVAL_INVALID')
    unique = unique_originals(closure, root)
    require(len(unique) + len(static_pins) <= 4096, 'NATIVE_OBSERVE_GRAPH_LIMIT')
    return unique, min(a for a, _ in intervals), max(b for _, b in intervals)


class NativeObservationService:
    def __init__(self, *, context, producer, maximum_observations):
        self.context, self.producer = context, producer
        self.order = ObservationOrder(maximum_observations)
        self.originals = {p['path']: p for p in context.graph_pins}

    def handle(self, request, peer):
        self.context.guard(); self.context.check_caller(peer)
        self.order.reserve(request)
        require(request['operationRequestPin'] == self.context.launch['operationRequestPin'] and
                request['serviceBindingPin'] in self.context.provision['serviceBindingPins'], 'NATIVE_OBSERVE_SCOPE')
        milliseconds = request['deadlineMilliseconds']
        require(type(milliseconds) is int and 0 < milliseconds <= self.context.request['deadlineMilliseconds'],
                'NATIVE_OBSERVE_REQUEST_DEADLINE')
        issued = utc(request['issuedAt']); now = datetime.now(timezone.utc)
        require(utc(self.context.launch['issuedAt']) <= issued <= now and
                (now - issued).total_seconds() * 1000 <= self.context.provision['maximumAgeMilliseconds'],
                'NATIVE_OBSERVE_STALE_INTENT')
        deadline = min(self.context.deadline, time.monotonic() + milliseconds / 1000 - (now - issued).total_seconds())
        require(time.monotonic() < deadline, 'NATIVE_OBSERVE_REQUEST_DEADLINE')
        prior = self.producer.process.deadline; self.producer.process.deadline = deadline
        prior_context = self.context.deadline; self.context.deadline = deadline
        try:
            stable = self.context.reader(request['serviceBindingPin'])
            # Internal copy only. The binding original is reread unchanged,
            # and its historical proof is never rewritten or reused as fresh.
            binding = dict(stable, nativeIdentityProofPin=None)
            prefix = f'observe-{request["sequence"]}-{request["phase"].lower()}'
            admission_pin, admission, admission_originals = produce_installation_admission(
                request, self.context, self.producer.process)
            identity_pin = self.producer.produce(binding, operation_binding=self.context.operation_binding,
                command_prefix=prefix, cwd=self.context.provision['workingDirectory'])
            require(self.context.reader(request['serviceBindingPin']) == stable, 'NATIVE_OBSERVE_BINDING_CHANGED')
            originals, started, finished = observation_originals(identity_pin, self.context.authority_pin,
                self.producer.process.root, self.context.graph_pins)
            originals += admission_originals
            for p in originals:
                require(p['path'] not in self.originals or self.originals[p['path']] == p, 'NATIVE_OBSERVE_CONFLICTING_PIN')
                self.originals[p['path']] = p
            require(len(self.originals) + 2 <= 4096, 'NATIVE_OBSERVE_GRAPH_LIMIT')
            require(issued <= utc(admission['startedAt']) < utc(admission['finishedAt']) <= started <= finished <=
                    datetime.now(timezone.utc) and time.monotonic() < deadline and
                    (datetime.now(timezone.utc) - utc(admission['startedAt'])).total_seconds() * 1000 <=
                    self.context.provision['maximumAgeMilliseconds'],
                    'NATIVE_OBSERVE_ACTUAL_INTERVAL')
            self.context.guard(); self.context.check_caller(peer)
            result = {k: request[k] for k in ('rehearsalId', 'collectionId', 'sequence', 'phase',
                                            'operationRequestPin', 'serviceBindingPin')}
            result.update(schemaVersion='RepositoryLabNativeObserveResult/v1', identityProofPin=identity_pin,
                originalPins=originals, probeStartedAt=started.isoformat().replace('+00:00', 'Z'),
                probeFinishedAt=finished.isoformat().replace('+00:00', 'Z'), issuedAt=utc_now(),
                expiresAt=min(self.context.expires_at, admission['expiresAt'], signed_payload(identity_pin,
                                      self.context.authority_pin)['expiresAt']))
            exact(result, RESULT_FIELDS, 'NATIVE_OBSERVE_RESULT_SHAPE')
            original = persist_bytes(self.producer.process.root / (prefix + '-observe-original.json'), canonical(result))
            signed = self.producer.process.signer.sign(original, deadline=deadline, worker_uid=self.producer.process.uid)
            self.originals[original['path']] = original; self.originals[signed['path']] = signed
            return decode(pinned_bytes(signed))
        finally:
            self.producer.process.deadline = prior
            self.context.deadline = prior_context

    def serve(self):
        path = lab_path(self.context.launch['observationSocketPath'], exists=False)
        metadata = path.parent.stat()
        require(metadata.st_uid == metadata.st_gid == 0 and stat.S_IMODE(metadata.st_mode) == 0o700 and
                not path.exists(), 'NATIVE_OBSERVE_SOCKET_CUSTODY')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(str(path))
            import os
            os.chmod(path, 0o600); server.listen(1)
            while self.order.sequence < self.order.maximum:
                self.context.guard(); remaining = self.context.deadline - time.monotonic()
                if not select.select([server], [], [], min(.25, remaining))[0]:
                    continue
                with server.accept()[0] as channel:
                    peer = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    request = receive_frame(channel, self.context.deadline)
                    response = self.handle(request, peer)
                    send_frame(channel, response, self.context.deadline)
