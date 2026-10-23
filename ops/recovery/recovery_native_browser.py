"""Finite R12 browser-B profile. Never promotes the root executor's proof.

The independently installed privileged launcher provisions identities and A's
broker. B only consumes the explicit selected v2 records and inherits its
already capability-free identity. No sandbox/capability/OS policy is changed.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import select
import socket
import stat
import struct
import sys
import time

from recovery_environment_contract import EnvironmentFailure, canonical, decode, exact, require, utc, utc_now
from recovery_environment_supervisor import OwnedChildSupervisor, identity, prepare_local_supervision
from recovery_native_process import (LAB_ROOT, REHEARSAL_ID, NS_FIELDS, file_metadata,
    authenticate_payload, terminal_status, NativeProcessProducer)
from recovery_native_signer import verify_parent_terminal

CONTRACT_PATH = Path(__file__).with_name('recovery_native_browser_contract.json')
CONTRACT = decode(CONTRACT_PATH.read_bytes())
DEFINITIONS = CONTRACT['$defs']
SCHEMAS = {item['properties']['schemaVersion']['const']: item for item in
           [*CONTRACT['qualificationSchemas'].values(),
            *[v for v in DEFINITIONS.values() if 'schemaVersion' in v.get('properties', {})]]}
PROCESS_VERSION = 'RepositoryLabNativeQualificationProcessInvocation/v2'
RESULT_VERSION = 'RepositoryLabNativeQualificationResult/v2'
PHASE_ACTION = {'NATIVE_BROWSER_CAPABILITY': 'BROWSER_NATIVE_CAPABILITY_PROBE',
                'NATIVE_BROWSER_QUALIFICATION': 'BROWSER_ABOUT_BLANK'}
ABOUT_BLANK = ['/opt/brlab-browser/chrome-headless-shell', '--headless', '--disable-gpu', '--dump-dom', 'about:blank']


def literal_path(value, *, lab=False):
    require(type(value) is str and value.startswith('/') and '\\' not in value and '\x00' not in value and
            not any(p in ('', '.', '..') for p in value.split('/')[1:]), 'BROWSER_LITERAL_PATH_REQUIRED')
    if lab:
        require(str(LAB_ROOT) + '/' == value[:len(str(LAB_ROOT)) + 1], 'BROWSER_PATH_OUTSIDE_LAB')
    return value


def _shape(value, spec):
    """Validate only the ratified task schema vocabulary; unknown rules fail."""
    require(set(spec) <= {'$ref', 'const', 'enum', 'type', 'properties', 'required', 'additionalProperties',
            'items', 'minItems', 'maxItems', 'minimum', 'maximum', 'minLength', 'pattern', 'format', 'anyOf', 'oneOf'},
            'BROWSER_SCHEMA_RULE_UNSUPPORTED')
    if '$ref' in spec:
        return _shape(value, DEFINITIONS[spec['$ref'].removeprefix('#/$defs/')])
    for union in ('anyOf', 'oneOf'):
        if union in spec:
            accepted = 0
            for variant in spec[union]:
                try: _shape(value, variant)
                except EnvironmentFailure: continue
                accepted += 1
            require(accepted == 1 if union == 'oneOf' else accepted > 0, 'BROWSER_SCHEMA_UNION')
            return
    if 'const' in spec:
        require(type(value) is type(spec['const']) and value == spec['const'], 'BROWSER_SCHEMA_CONSTANT')
    if 'enum' in spec:
        require(any(type(value) is type(v) and value == v for v in spec['enum']), 'BROWSER_SCHEMA_ENUM')
    kind = spec.get('type')
    if kind:
        types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool, 'null': type(None)}
        require(kind in types and type(value) is types[kind], 'BROWSER_SCHEMA_TYPE')
    if kind == 'object':
        require(spec['additionalProperties'] is False, 'BROWSER_SCHEMA_OPEN_OBJECT_REJECTED')
        exact(value, spec['required'], 'BROWSER_SCHEMA_FIELDS')
        for field, item in value.items(): _shape(item, spec['properties'][field])
    elif kind == 'array':
        require(spec.get('minItems', 0) <= len(value) <= spec.get('maxItems', 4096), 'BROWSER_SCHEMA_ARRAY_SIZE')
        for item in value: _shape(item, spec['items'])
    elif kind == 'integer':
        require(spec.get('minimum', -2**64) <= value <= spec.get('maximum', 2**64), 'BROWSER_SCHEMA_INTEGER_RANGE')
    elif kind == 'string':
        require(len(value) >= spec.get('minLength', 0) and
                ('pattern' not in spec or re.search(spec['pattern'], value) is not None), 'BROWSER_SCHEMA_STRING')
        if spec.get('format') == 'date-time': utc(value)


def validate_record(value, expected):
    require(expected in SCHEMAS and type(value) is dict and value.get('schemaVersion') == expected,
            'BROWSER_EXPLICIT_VERSION_REQUIRED')
    _shape(value, SCHEMAS[expected])
    def paths(item):
        if type(item) is str and item.startswith('/'): literal_path(item)
        elif type(item) is dict:
            for child in item.values(): paths(child)
        elif type(item) is list:
            for child in item: paths(child)
    paths(value)
    return value


def current_window(value, start='issuedAt'):
    now = datetime.now(timezone.utc)
    require(utc(value[start]) <= now < utc(value['expiresAt']) and
            0 < (utc(value['expiresAt']) - utc(value[start])).total_seconds() <= 300,
            'BROWSER_CURRENT_WINDOW_REQUIRED')


def security_identity(measured, uid, gid, *, authority=False):
    _shape(measured, DEFINITIONS['MeasuredIdentity'])
    require(all(measured[k] == uid for k in ('uid', 'realUid', 'savedUid', 'filesystemUid')) and
            all(measured[k] == gid for k in ('gid', 'realGid', 'savedGid', 'filesystemGid')),
            'BROWSER_SELECTED_IDENTITY_CHANGED')
    for field, kind in NS_FIELDS.items():
        require(re.fullmatch(kind + r':\[[1-9][0-9]*\]', measured[field]) is not None,
                'BROWSER_NAMESPACE_IDENTITY_INVALID')
    security = measured['security']
    require(security['supplementaryGroups'] == [] and security['noNewPrivs'] == 1,
            'BROWSER_SECURITY_BOUNDARY')
    retained = 3 if authority else 0
    require(int(security['capEff'], 16) == int(security['capPrm'], 16) == retained and
            int(security['capInh'], 16) == 0 and int(security['capBnd'], 16) == retained,
            'BROWSER_CAPABILITIES_NOT_SELECTED')
    require((security['ambientState'] == 'PRESENT' and security['capAmb'] is not None and
             int(security['capAmb'], 16) == 0) or
            (security['ambientState'] == 'UNSUPPORTED_PROVEN' and security['capAmb'] is None),
            'BROWSER_AMBIENT_EVIDENCE_REQUIRED')


def descriptor_read(pin, *, owners, deadline, readonly=True, modes=(0o444, 0o555, 0o600),
                    limit=268435456, owner_gid=None):
    """Held and reopened literal inode; explicit custody and no key-path use."""
    _shape(pin, DEFINITIONS['Pin']); literal_path(pin['path'])
    require(sys.platform == 'linux' and time.monotonic() < deadline, 'BROWSER_NATIVE_PREREQUISITE')
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in PurePosixPath(pin['path']).parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = child
            meta = os.fstat(parent)
            require(meta.st_uid in owners and not meta.st_mode & 0o022, 'BROWSER_ANCESTOR_CUSTODY')
        fd = os.open(PurePosixPath(pin['path']).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid in owners and
                    stat.S_IMODE(before.st_mode) in modes and before.st_size == pin['bytes'] <= limit,
                    'BROWSER_ORIGINAL_CUSTODY')
            require(owner_gid is None or before.st_gid == owner_gid, 'BROWSER_ORIGINAL_GROUP_CUSTODY')
            require(not readonly or os.fstatvfs(fd).f_flag & os.ST_RDONLY, 'BROWSER_ORIGINAL_NOT_READONLY')
            raw = bytearray()
            while True:
                require(time.monotonic() < deadline, 'BROWSER_READ_DEADLINE')
                part = os.read(fd, 1048576)
                if not part: break
                raw.extend(part); require(len(raw) <= pin['bytes'], 'BROWSER_ORIGINAL_SIZE')
            reopened = os.open(PurePosixPath(pin['path']).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                require(file_metadata(before) == file_metadata(os.fstat(fd)) == file_metadata(os.fstat(reopened)),
                        'BROWSER_HELD_ORIGINAL_CHANGED')
            finally: os.close(reopened)
            require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'],
                    'BROWSER_ORIGINAL_HASH')
            return bytes(raw)
        finally: os.close(fd)
    finally: os.close(parent)


def read_signed_publication(context, pin):
    """Only the selected root:B-group 0440 lane admits signed publications."""
    s = context.selection; root = literal_path(s['signedPublicationRoot'], lab=True)
    literal_path(pin['path'], lab=True)
    require(PurePosixPath(pin['path']).parent == PurePosixPath(root), 'BROWSER_PUBLICATION_PATH')
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        meta = os.fstat(directory)
        require(meta.st_uid == 0 and meta.st_gid == s['browserGid'] and stat.S_IMODE(meta.st_mode) == 0o750,
                'BROWSER_PUBLICATION_DIRECTORY_CUSTODY')
        return descriptor_read(pin, owners={0}, deadline=context.deadline, modes=(0o440,),
            owner_gid=s['browserGid'], readonly=os.geteuid() not in (0, s['signerUid']))
    finally: os.close(directory)


def graph_union(roots, reader, *, opaque_paths, data_paths, reserved_outputs=()):
    """Single acyclic budget includes opaque keys and reserved future outputs."""
    graph, active = {}, set()
    for path in reserved_outputs: literal_path(path, lab=True)
    require(len(set(reserved_outputs)) == len(reserved_outputs), 'BROWSER_OUTPUT_COLLISION')
    def walk(item):
        if type(item) is dict and set(item) == {'path', 'bytes', 'sha256'}:
            _shape(item, DEFINITIONS['Pin']); path = literal_path(item['path'])
            require(path not in reserved_outputs and path not in active, 'BROWSER_GRAPH_CYCLE_OR_OUTPUT_COLLISION')
            if path in graph:
                require(graph[path] == item, 'BROWSER_GRAPH_PIN_CONFLICT'); return
            graph[path] = item
            require(len(graph) + len(reserved_outputs) <= 4096, 'BROWSER_GRAPH_LIMIT')
            if path in opaque_paths: return  # never open a private key
            raw = reader(item)
            if path not in data_paths and raw.lstrip().startswith((b'{', b'[')):
                active.add(path); walk(decode(raw)); active.remove(path)
        elif type(item) is dict:
            for child in item.values(): walk(child)
        elif type(item) is list:
            for child in item: walk(child)
    for root in roots: walk(root)
    return list(graph.values())


def browser_socket_custody(path, selection, expected=None):
    literal_path(path, lab=True)
    require(path == selection['signerSocketPath'], 'BROWSER_SOCKET_UNSELECTED')
    parent, current = Path(path).parent.lstat(), Path(path).lstat()
    require(stat.S_ISDIR(parent.st_mode) and parent.st_uid == 0 and parent.st_gid == selection['browserGid'] and
            stat.S_IMODE(parent.st_mode) == 0o750 and stat.S_ISSOCK(current.st_mode) and
            current.st_uid == 0 and current.st_gid == selection['browserGid'] and
            stat.S_IMODE(current.st_mode) == 0o660, 'BROWSER_SOCKET_CUSTODY')
    token = (file_metadata(parent), file_metadata(current))
    require(expected is None or expected == token, 'BROWSER_SOCKET_REPLACED')
    return token


class BrowserQualificationContext:
    """Authentic selected browser proof, finite command and current grant/lease."""
    def __init__(self, launch_pin, provision_pin, authority_pin, *, deadline):
        require(sys.platform == 'linux', 'BROWSER_LINUX_REQUIRED')
        self.deadline, self.authority_pin = deadline, authority_pin
        self.launch_pin, self.provision_pin = launch_pin, provision_pin
        self._records = []
        self.launch = self.record(launch_pin, 'RepositoryLabNativeQualificationLaunch/v2')
        self.provision = self.record(provision_pin, 'RepositoryLabNativeQualificationProvision/v2')
        self.selection_pin = self.launch['browserIdentitySelectionPin']
        self.proof_pin = self.launch['browserRuntimeProofPin']
        self.selection = self.record(self.selection_pin, 'RepositoryLabBrowserIdentitySelection/v1')
        s = self.selection
        require(s['authorityKeyPin'] == authority_pin and s['browserUid'] != s['signerUid'] and
                s['browserGid'] != s['signerGid'], 'BROWSER_SELECTED_ROLES_REQUIRED')
        self.proof = self.record(self.proof_pin, 'RepositoryLabBrowserRuntimeProof/v1')
        self.trust_pin = self.proof['nativeRuntimeTrustPin']
        self.trust = self.record(self.trust_pin, 'RepositoryLabBrowserRuntimeTrust/v1')
        self.intent_pin = self.launch['qualificationIntentPin']
        self.intent = self.record(self.intent_pin, 'RepositoryLabNativeQualificationIntent/v2')
        self.phase = self.intent['phase']
        self.command = self.intent['commandSelections'][0]
        require(self.launch['installationPin'] == self.intent['installationPin'] == self.proof['executorInstallationPin'] ==
                s['executorInstallationPin'] and self.provision['launchPin'] == launch_pin and
                self.launch['authorityKeyPin'] == self.intent['authorityKeyPin'] == authority_pin and
                self.launch['producerEntryPin'] == s['producerEntryPin'] and
                self.launch['signerEntryPin'] == s['signerEntryPin'] and
                self.launch['authorizationPin'] == self.intent['authorizationPin'] and
                self.launch['leasePin'] == self.intent['leasePin'], 'BROWSER_CONTROL_BINDING')
        require(self.provision['privateKeyPin'] == s['privateKeyPin'] and
                all(self.provision[k] == s[k] for k in ('signerUid', 'signerGid', 'signerRootPath',
                    'signerSocketPath', 'workingDirectory', 'maximumAgeMilliseconds', 'controllerIdentityPin')) and
                self.provision['producerUid'] == s['browserUid'] and self.provision['producerGid'] == s['browserGid'] and
                self.launch['evidenceRoot'] == s['evidenceRoot'],
                'BROWSER_PROVISION_BINDING')
        require(self.proof['controllerIdentityPin'] == s['controllerIdentityPin'] and
                self.proof['controllerRuntimeProofPin'] == s['controllerRuntimeProofPin'] and
                self.trust['browserIdentitySelectionPin'] == self.selection_pin and
                self.trust['runtimeId'] == self.proof['runtimeId'] and
                self.trust['immutableRuntimeArtifactDigest'] == self.proof['immutableRuntimeArtifactDigest'] and
                self.proof_pin != s['controllerRuntimeProofPin'], 'BROWSER_ROOT_PROOF_REUSE_REJECTED')
        for role, uid, gid in (('producer', s['browserUid'], s['browserGid']),
                               ('signer', s['signerUid'], s['signerGid'])):
            security_identity(self.proof[role + 'Identity'], uid, gid, authority=role == 'signer')
        require(self.proof['managerIdentity']['pid'] == 1 and self.proof['managerIdentity']['uid'] == 0 and
                self.proof['producerIdentity']['pidNamespace'] == self.proof['managerIdentity']['pidNamespace'] ==
                self.proof['signerIdentity']['pidNamespace'] and
                self.proof['producerIdentity']['mountNamespace'] != self.proof['signerIdentity']['mountNamespace'],
                'BROWSER_MANAGER_OR_SECRET_NAMESPACE')
        require(self.command['action'] == PHASE_ACTION[self.phase] and self.command['cwd'] == s['workingDirectory'] and
                self.command['argv'] == (s['capabilityProbeArgv'] if self.phase == 'NATIVE_BROWSER_CAPABILITY' else ABOUT_BLANK),
                'BROWSER_EXACT_COMMAND_REQUIRED')
        if self.phase == 'NATIVE_BROWSER_CAPABILITY':
            require(self.intent['sandboxCapabilityResultPin'] is None and
                    s['capabilityProbeEntryPin']['path'] in self.command['argv'], 'BROWSER_PROBE_ENTRY_REQUIRED')
        else:
            require(self.intent['sandboxCapabilityResultPin'] is not None and
                    s['browserExecutablePin']['path'] == ABOUT_BLANK[0], 'BROWSER_CAPABILITY_PREREQUISITE')
        self.producer = self.record(self.provision['producerIdentityPin'], 'RepositoryLabBrowserParticipantIdentity/v1')
        require(self.producer['role'] == 'BROWSER_PRODUCER' and self.producer['identity'] == self.proof['producerIdentity'],
                'BROWSER_PRODUCER_IDENTITY_BINDING')
        source_pins = [a['pin'] for a in s['sourceAccess']]
        require(len(source_pins) == len({p['path'] for p in source_pins}) and
                set(map(canonical, source_pins)) == set(map(canonical, self.command['sourcePins'])) and
                s['producerEntryPin'] in source_pins and s['signerEntryPin'] in source_pins and
                s['bootstrapLauncherPin'] in source_pins and s['capabilityProbeEntryPin'] in source_pins and
                s['privateKeyPin'] not in source_pins, 'BROWSER_COMPLETE_SOURCE_SELECTION')
        self.guards = []
        self.outputs = []
        self.guard()

    def raw(self, pin):
        require(not hasattr(self, 'selection') or pin['path'] != self.selection['privateKeyPin']['path'],
                'BROWSER_PRIVATE_KEY_READ_REJECTED')
        if hasattr(self, 'selection') and pin['path'].startswith(self.selection['signedPublicationRoot'] + '/'):
            return read_signed_publication(self, pin)
        return descriptor_read(pin, owners={0}, deadline=self.deadline)

    def signed(self, pin):
        literal_path(pin['path'], lab=True)
        return authenticate_payload(decode(self.raw(pin)), self.raw(self.authority_pin), self.authority_pin['sha256'])

    def record(self, pin, version):
        value = validate_record(self.signed(pin), version)
        if 'expiresAt' in value: current_window(value, 'notBefore' if 'notBefore' in value else 'issuedAt')
        require(value.get('rehearsalId', REHEARSAL_ID) == REHEARSAL_ID, 'BROWSER_REHEARSAL')
        self._records.append((pin, value))
        return value

    def guard(self):
        require(time.monotonic() < self.deadline, 'BROWSER_DEADLINE')
        for pin, value in self._records:
            require(self.signed(pin) == value, 'BROWSER_SELECTED_RECORD_CHANGED')
            if 'expiresAt' in value: current_window(value, 'notBefore' if 'notBefore' in value else 'issuedAt')
        for item in (self.provision, self.proof, self.intent, self.producer):
            require(item['browserIdentitySelectionPin'] == self.selection_pin and
                    item.get('browserRuntimeProofPin', self.proof_pin) == self.proof_pin, 'BROWSER_SELECTION_PROOF_BINDING')
        require(0 < self.deadline - time.monotonic() <= self.intent['deadlineMilliseconds'] / 1000 and
                self.intent['deadlineMilliseconds'] <= self.selection['maximumAgeMilliseconds'], 'BROWSER_FINITE_DEADLINE')
        grant = validate_record(self.signed(self.intent['authorizationPin']), 'RepositoryLabNativeQualificationAuthorization/v2')
        lease = validate_record(self.signed(self.intent['leasePin']), 'RepositoryLabNativeQualificationLease/v2')
        for field in ('rehearsalId', 'qualificationId', 'operationId', 'phase', 'hostId', 'targetId', 'executorId',
                      'sourceScopePin', 'installationPin', 'browserIdentitySelectionPin', 'browserRuntimeProofPin'):
            require(grant[field] == lease[field] == self.intent[field], 'BROWSER_GRANT_LEASE_BINDING')
        require(grant['approved'] is True and grant['actions'] == [self.command['action']] and lease['state'] == 'HELD' and
                type(lease['fenceToken']) is int and lease['fenceToken'] > 0, 'BROWSER_CURRENT_GRANT_LEASE')
        current_window(grant, 'notBefore'); current_window(lease, 'notBefore')
        require(all(self.intent[k] == self.selection[k] for k in ('hostId', 'targetId', 'executorId', 'sourceScopePin')),
                'BROWSER_SCOPE_IDENTITY_BINDING')
        from repository_native_runtime import verify_native_installation, verify_browser_runtime
        manifest = verify_native_installation(self.intent['installationPin'], [self.authority_pin], deadline=self.deadline)
        require(manifest['schemaVersion'] == 'RepositoryNativeInstallation/v2' and
                manifest['nativeRuntimeProofPin'] == self.selection['controllerRuntimeProofPin'],
                'BROWSER_SEPARATE_EXECUTOR_INSTALLATION')
        verified = verify_browser_runtime(self.trust_pin, self.proof_pin, [self.authority_pin],
            self.provision['producerIdentityPin'], deadline=self.deadline)
        require(verified == self.proof, 'BROWSER_SHARED_READER_PROOF_CHANGED')
        require(self.signed(self.selection['controllerIdentityPin']) == self.signed(self.launch['allowedCallerPin']),
                'BROWSER_CONTROLLER_NOT_SELECTED')
        from recovery_native_launcher import validate_qualification_scope
        scope = self.signed(self.intent['sourceScopePin']); validate_qualification_scope(scope)
        require(datetime.now(timezone.utc) < utc(scope['expiresAt']), 'BROWSER_SOURCE_SCOPE_EXPIRED')
        self.grant, self.lease, self.manifest = grant, lease, manifest
        expected_sources = self.trust['installedSourcePins'] + [e['pin'] for e in self.trust['nativeFilePins']]
        require(set(map(canonical, expected_sources)) == set(map(canonical, self.command['sourcePins'])) and
                manifest['pythonPin'] in self.command['sourcePins'] and
                any(p['path'].endswith('/recovery_environment_supervisor.py') for p in self.command['sourcePins']),
                'BROWSER_ALL_INSTALLED_AND_NATIVE_SOURCES_REQUIRED')
        from recovery_native_launcher import browser_resource_pins
        browser_resource_pins(self.trust)
        self.graph = graph_union([*[p for p, _ in self._records], self.authority_pin,
                self.intent['authorizationPin'], self.intent['leasePin'], *self.guards], self.raw,
            opaque_paths={self.selection['privateKeyPin']['path']},
            data_paths={a['pin']['path'] for a in self.selection['sourceAccess']},
            reserved_outputs=self.reserved_paths())
        if self.phase == 'NATIVE_BROWSER_QUALIFICATION':
            validate_capability(self, self.intent['sandboxCapabilityResultPin'])

    def reserved_paths(self):
        root = literal_path(self.selection['evidenceRoot'], lab=True)
        command = self.command['commandId']
        return [root + '/' + command + '/' + n for n in
                ('stdout', 'stderr', 'supervisor-terminal.json', 'process-original.json', 'qualification-original.json')]

    def source_guard(self):
        from repository_native_runtime import read_browser_member, verify_browser_file
        native = self.trust['nativeFilePins']
        for access in self.selection['sourceAccess']:
            pin = access['pin']; entry = next((e for e in native if e['pin'] == pin), None)
            if entry:
                require(access['roles'] == entry['roles'], 'BROWSER_SOURCE_ROLE_CHANGED')
                for role in entry['roles']:
                    verify_browser_file(pin, self.trust_pin, self.proof_pin, role=role, deadline=self.deadline)
            else:
                require(pin in self.trust['installedSourcePins'] and len(access['roles']) == 1,
                        'BROWSER_INSTALLED_SOURCE_UNSELECTED')
                read_browser_member(pin, self.trust_pin, self.proof_pin, role=access['roles'][0], deadline=self.deadline)
            descriptor_read(pin, owners={0}, deadline=self.deadline, modes=(int(access['mode'], 8),))

    def admit_output_graph(self, pin):
        """Include all actual stream/terminal/result Pins in the original budget."""
        self.outputs.append(pin)
        def read(reference):
            if reference['path'].startswith(self.selection['evidenceRoot'] + '/'):
                return read_producer_original(self, reference)
            return self.raw(reference)
        records = graph_union([*self.graph, *self.outputs], read,
            opaque_paths={self.selection['privateKeyPin']['path']},
            data_paths={*[a['pin']['path'] for a in self.selection['sourceAccess']],
                        *[p for p in self.reserved_paths() if p.endswith(('/stdout', '/stderr'))]})
        remaining = set(self.reserved_paths()) - {p['path'] for p in records}
        require(len(records) + len(remaining) <= 4096, 'BROWSER_GRAPH_OUTPUT_BUDGET')

    def admit_guard(self, pin):
        value = validate_record(self.signed(pin), 'RepositoryLabBrowserGuardMeasurement/v1')
        current_window(value, 'measuredAt')
        for field, expected in (('browserIdentitySelectionPin', self.selection_pin), ('browserRuntimeProofPin', self.proof_pin),
                ('qualificationIntentPin', self.intent_pin), ('authorizationPin', self.intent['authorizationPin']),
                ('leasePin', self.intent['leasePin'])):
            require(value[field] == expected, 'BROWSER_GUARD_BATCH_CHANGED')
        for role, expected in (('producer', self.proof['producerIdentity']), ('signer', self.proof['signerIdentity']),
                               ('manager', self.proof['managerIdentity'])):
            require(stable_measured_identity(value[role + 'Identity']) == stable_measured_identity(expected),
                    'BROWSER_GUARD_LIVE_IDENTITY_CHANGED')
        controller = self.signed(self.selection['controllerIdentityPin'])
        require(all(value['controllerIdentity'][k] == controller[k] for k in
                    ('pid', 'startTicks', 'uid', 'gid', 'hostId', 'bootId', 'rootDevice', 'rootInode', *NS_FIELDS)),
                'BROWSER_GUARD_CONTROLLER_CHANGED')
        security_identity(value['producerIdentity'], self.selection['browserUid'], self.selection['browserGid'])
        security_identity(value['signerIdentity'], self.selection['signerUid'], self.selection['signerGid'], authority=True)
        validate_guard_originals(self, value)
        self.guards.append(pin)
        require(len(self.guards) <= self.selection['maximumRecords'], 'BROWSER_FINITE_GUARD_BUDGET')
        self.guard()
        return value


def stable_measured_identity(value):
    _shape(value, DEFINITIONS['MeasuredIdentity'])
    return {k: ({s: v for s, v in item.items() if not s.endswith('EvidencePin') and s != 'securityOriginalPin'}
                if k == 'security' else item) for k, item in value.items() if k != 'kernelIdentityOriginalPin'}


def measurement_time(context, value, stamp='measuredAt', *, end=None):
    instant = utc(value[stamp]); now = datetime.now(timezone.utc)
    require(utc(context.intent['issuedAt']) <= instant <= (utc(end) if end is not None else now) and
            instant < utc(context.intent['expiresAt']) and
            (now - instant).total_seconds() * 1000 <= context.selection['maximumAgeMilliseconds'],
            'BROWSER_MEASUREMENT_WINDOW')


def validate_guard_originals(context, guard):
    """The independent broker must supply complete original measurements."""
    sources = decode(context.raw(guard['completeSourceReadEvidencePin']))
    exact(sources, {'schemaVersion', 'browserIdentitySelectionPin', 'browserRuntimeProofPin', 'measuredSourcePins',
                    'producerIdentity', 'measuredAt'}, 'BROWSER_SOURCE_MEASUREMENT_SHAPE')
    require(sources['schemaVersion'] == 'RepositoryLabBrowserCompleteSourceRead/v1' and
            sources['browserIdentitySelectionPin'] == context.selection_pin and sources['browserRuntimeProofPin'] == context.proof_pin and
            sources['producerIdentity'] == guard['producerIdentity'] and
            sources['measuredSourcePins'] == [a['pin'] for a in context.selection['sourceAccess']],
            'BROWSER_COMPLETE_SOURCE_READ_UNPROVEN')
    directories = decode(context.raw(guard['directoryAccessEvidencePin']))
    exact(directories, {'schemaVersion', 'browserIdentitySelectionPin', 'browserRuntimeProofPin', 'directoryAccess',
                       'producerIdentity', 'measuredAt'}, 'BROWSER_DIRECTORY_MEASUREMENT_SHAPE')
    require(directories['schemaVersion'] == 'RepositoryLabBrowserDirectoryAccess/v1' and
            directories['browserIdentitySelectionPin'] == context.selection_pin and directories['browserRuntimeProofPin'] == context.proof_pin and
            directories['producerIdentity'] == guard['producerIdentity'] and
            directories['directoryAccess'] == context.selection['directoryAccess'], 'BROWSER_DIRECTORY_ACCESS_UNPROVEN')
    denial = decode(context.raw(guard['workerKeyDenialEvidencePin']))
    exact(denial, {'schemaVersion', 'browserIdentitySelectionPin', 'browserRuntimeProofPin', 'producerIdentity',
                  'signerIdentity', 'deniedOpens', 'probeIdentity', 'actualWaitStatus', 'soleParentPid', 'measuredAt'},
          'BROWSER_KEY_DENIAL_MEASUREMENT_SHAPE')
    require(denial['schemaVersion'] == 'RepositoryLabBrowserKeyDenial/v1' and
            denial['browserIdentitySelectionPin'] == context.selection_pin and denial['browserRuntimeProofPin'] == context.proof_pin and
            denial['producerIdentity'] == guard['producerIdentity'] and denial['signerIdentity'] == guard['signerIdentity'] and
            type(denial['actualWaitStatus']) is int and denial['actualWaitStatus'] == 0 and
            type(denial['soleParentPid']) is int and denial['soleParentPid'] > 0,
            'BROWSER_KEY_DENIAL_UNPROVEN')
    security_identity(denial['probeIdentity'], context.selection['browserUid'], context.selection['browserGid'])
    for field in ('mountNamespace', 'rootDevice', 'rootInode'):
        require(denial['probeIdentity'][field] == guard['producerIdentity'][field], 'BROWSER_KEY_DENIAL_WRONG_ROOT')
    paths = [context.selection['privateKeyPin']['path'], '/proc/' + str(guard['signerIdentity']['pid']) + '/root' +
             context.selection['privateKeyPin']['path'], '/proc/' + str(guard['signerIdentity']['pid']) + '/mem']
    require(type(denial['deniedOpens']) is list and len(denial['deniedOpens']) == 3, 'BROWSER_KEY_DENIAL_INCOMPLETE')
    for item in (sources, directories, denial): measurement_time(context, item, end=guard['measuredAt'])
    for item, path in zip(denial['deniedOpens'], paths):
        exact(item, {'path', 'errno'}, 'BROWSER_KEY_DENIAL_PROBE_SHAPE')
        require(item['path'] == path and type(item['errno']) is int and item['errno'] in (1, 2, 13),
                'BROWSER_KEY_OPEN_NOT_DENIED')
    for role in ('producerIdentity', 'signerIdentity'):
        security = guard[role]['security']
        original = decode(context.raw(security['securityOriginalPin']))
        measurement_time(context, original, end=guard['measuredAt'])
        exact(original, {'schemaVersion', 'pid', 'startTicks', 'capEff', 'capPrm', 'capInh', 'capBnd', 'capAmb',
                         'supplementaryGroups', 'noNewPrivs', 'measuredAt'}, 'BROWSER_SECURITY_ORIGINAL_SHAPE')
        require(original['schemaVersion'] == 'RepositoryLabBrowserSecurity/v1' and
                original['pid'] == guard[role]['pid'] and original['startTicks'] == guard[role]['startTicks'] and
                all(original[k] == security[k] for k in ('capEff', 'capPrm', 'capInh', 'capBnd', 'capAmb',
                                                         'supplementaryGroups', 'noNewPrivs')),
                'BROWSER_SECURITY_ORIGINAL_CHANGED')
        nnp = decode(context.raw(security['getNoNewPrivsEvidencePin']))
        exact(nnp, {'schemaVersion', 'pid', 'startTicks', 'prctl', 'returnValue', 'errno'}, 'BROWSER_NNP_ORIGINAL_SHAPE')
        require(nnp['schemaVersion'] == 'RepositoryLabBrowserNoNewPrivileges/v1' and nnp['prctl'] == 39 and
                type(nnp['returnValue']) is int and nnp['returnValue'] == 1 and type(nnp['errno']) is int and nnp['errno'] == 0 and
                nnp['pid'] == guard[role]['pid'] and nnp['startTicks'] == guard[role]['startTicks'], 'BROWSER_NNP_ORIGINAL_UNPROVEN')
        raw = decode(context.raw(security['ambientEvidencePin']))
        exact(raw, {'schemaVersion', 'pid', 'startTicks', 'state', 'returnValue', 'errno', 'kernelRelease'},
              'BROWSER_AMBIENT_ORIGINAL_SHAPE')
        require(raw['schemaVersion'] == 'RepositoryLabBrowserAmbientCapability/v1' and
                raw['pid'] == guard[role]['pid'] and raw['startTicks'] == guard[role]['startTicks'] and
                raw['state'] == security['ambientState'] and type(raw['errno']) is int and
                ((raw['state'] == 'PRESENT' and raw['returnValue'] == 0 and raw['errno'] == 0) or
                 (raw['state'] == 'UNSUPPORTED_PROVEN' and raw['returnValue'] == -1 and raw['errno'] == 22)),
                'BROWSER_AMBIENT_UNSUPPORTED_NOT_PROVEN')


def validate_capability(context, pin):
    value = validate_record(context.signed(pin), 'RepositoryLabBrowserSandboxCapabilityResult/v1')
    current_window(value)
    require(value['browserIdentitySelectionPin'] == context.selection_pin and value['browserRuntimeProofPin'] == context.proof_pin,
            'BROWSER_CAPABILITY_IDENTITY_CHANGED')
    process = validate_record(context.signed(value['processResultPin']), PROCESS_VERSION)
    prior_intent = validate_record(context.signed(value['qualificationIntentPin']), 'RepositoryLabNativeQualificationIntent/v2')
    current_window(prior_intent)
    prior = object.__new__(BrowserQualificationContext)
    prior.__dict__ = dict(context.__dict__, intent=prior_intent, intent_pin=value['qualificationIntentPin'],
                          phase='NATIVE_BROWSER_CAPABILITY', command=prior_intent['commandSelections'][0])
    prior.raw, prior.signed = context.raw, context.signed
    grant = validate_record(context.signed(prior_intent['authorizationPin']), 'RepositoryLabNativeQualificationAuthorization/v2')
    lease = validate_record(context.signed(prior_intent['leasePin']), 'RepositoryLabNativeQualificationLease/v2')
    for material in (grant, lease): current_window(material, 'notBefore')
    fields = ('rehearsalId', 'qualificationId', 'operationId', 'phase', 'hostId', 'targetId', 'executorId',
              'sourceScopePin', 'installationPin', 'browserIdentitySelectionPin', 'browserRuntimeProofPin')
    require(all(grant[k] == lease[k] == prior_intent[k] for k in fields) and grant['approved'] is True and
            grant['actions'] == [PHASE_ACTION['NATIVE_BROWSER_CAPABILITY']] and lease['state'] == 'HELD' and
            type(lease['fenceToken']) is int and lease['fenceToken'] > 0, 'BROWSER_CAPABILITY_CURRENT_GRANT_LEASE')
    require(all(prior_intent[k] == context.intent[k] for k in
                ('rehearsalId', 'hostId', 'targetId', 'executorId', 'sourceScopePin', 'installationPin',
                 'browserIdentitySelectionPin', 'browserRuntimeProofPin', 'authorityKeyPin')) and
            prior_intent['sandboxCapabilityResultPin'] is None and
            (context.phase == 'NATIVE_BROWSER_CAPABILITY' or
             all(prior_intent[k] != context.intent[k] for k in ('qualificationId', 'operationId')) and
             prior_intent['authorizationPin'] != context.intent['authorizationPin'] and
             prior_intent['leasePin'] != context.intent['leasePin'] and
             prior.command['commandId'] != context.command['commandId']), 'BROWSER_CAPABILITY_PREDECESSOR_SCOPE')
    require(prior.command['action'] == PHASE_ACTION['NATIVE_BROWSER_CAPABILITY'] and
            prior.command['cwd'] == context.selection['workingDirectory'] and
            prior.command['argv'] == context.selection['capabilityProbeArgv'] and
            set(map(canonical, prior.command['sourcePins'])) == set(map(canonical, context.command['sourcePins'])),
            'BROWSER_CAPABILITY_FULL_SOURCE_COMMAND')
    require(prior_intent['phase'] == process['phase'] == 'NATIVE_BROWSER_CAPABILITY' and
            process['qualificationId'] == prior_intent['qualificationId'] and process['operationId'] == prior_intent['operationId'] and
            process['nativeRuntimeProofPin'] == process['browserRuntimeProofPin'] == context.proof_pin and
            process['browserIdentitySelectionPin'] == context.selection_pin and process['actualExitCode'] == 0 and
            process['terminationKind'] == 'EXITED' and process['waitStatus'] == 0 and process['descendantState'] == 'REAPED' and
            process['argv'] == context.selection['capabilityProbeArgv'] and
            process['command'] == __import__('recovery_native_observation').wire_canonical(prior.command['argv']).decode() and
            all(process[k] == prior_intent[k] for k in ('rehearsalId', 'targetId', 'executorId')) and
            all(process[k] == prior.command[k] for k in ('commandId', 'argv', 'cwd', 'sourcePins')) and
            process['pythonPin'] == context.manifest['pythonPin'] and
            process['supervisorPin'] in prior.command['sourcePins'] and
            process['supervisorPin']['path'].endswith('/recovery_environment_supervisor.py') and
            process['producerIdentityPin'] == context.provision['producerIdentityPin'] and
            process['uid'] == context.selection['browserUid'] and process['gid'] == context.selection['browserGid'] and
            all(process[k] == context.proof['producerIdentity'][k] for k in ('hostId', 'bootId', *NS_FIELDS)) and
            process['sandboxEvidencePin'] is None and
            utc(prior_intent['issuedAt']) <= utc(process['startedAt']) <= utc(process['finishedAt']) <= utc(value['issuedAt']) and
            utc(process['finishedAt']) < utc(prior_intent['expiresAt']), 'BROWSER_CAPABILITY_PROCESS_UNPROVEN')
    participant = validate_record(context.signed(process['authorityIdentityPin']), 'RepositoryLabBrowserParticipantIdentity/v1')
    current_window(participant)
    require(participant['role'] == 'AUTHORITY_A' and participant['browserIdentitySelectionPin'] == context.selection_pin and
            participant['browserRuntimeProofPin'] == context.proof_pin and
            stable_measured_identity(participant['identity']) == stable_measured_identity(context.proof['signerIdentity']),
            'BROWSER_CAPABILITY_AUTHORITY')
    require(process['currentGuardMeasurementPins'], 'BROWSER_CAPABILITY_GUARDS_REQUIRED')
    for ref in process['currentGuardMeasurementPins']:
        measured = validate_record(context.signed(ref), 'RepositoryLabBrowserGuardMeasurement/v1')
        current_window(measured, 'measuredAt')
        require(measured['browserIdentitySelectionPin'] == context.selection_pin and measured['browserRuntimeProofPin'] == context.proof_pin and
                measured['qualificationIntentPin'] == value['qualificationIntentPin'] and
                measured['authorizationPin'] == prior_intent['authorizationPin'] and measured['leasePin'] == prior_intent['leasePin'] and
                all(stable_measured_identity(measured[r+'Identity']) == stable_measured_identity(context.proof[r+'Identity'])
                    for r in ('producer', 'signer', 'manager')), 'BROWSER_CAPABILITY_GUARD_BINDING')
        validate_guard_originals(prior, measured)
        controller = context.signed(context.selection['controllerIdentityPin'])
        require(all(measured['controllerIdentity'][k] == controller[k] for k in
                    ('pid', 'startTicks', 'uid', 'gid', 'hostId', 'bootId', 'rootDevice', 'rootInode', *NS_FIELDS)),
                'BROWSER_CAPABILITY_GUARD_CONTROLLER')
    require(process['stdoutPin']['path'] == prior.reserved_paths()[0] and
            process['stderrPin']['path'] == prior.reserved_paths()[1] and process['resultPin'] == process['stdoutPin'],
            'BROWSER_CAPABILITY_STREAM_PATHS')
    for name in ('stdoutPin', 'stderrPin', 'resultPin'): read_producer_original(prior, process[name])
    terminal_pin = producer_original_pin(prior, prior.reserved_paths()[2])
    verify_parent_terminal(process, decode(read_producer_original(prior, terminal_pin)))
    names = [p['name'] for p in value['probes']]
    required = {'user-namespace', 'uid-map', 'gid-map', 'pid-namespace', 'network-namespace', 'seccomp-bpf', 'no-new-privileges'}
    require(len(names) == len(set(names)) and required <= set(names), 'BROWSER_CAPABILITY_PROBES_INCOMPLETE')
    for probe in value['probes']:
        original = decode(context.raw(probe['originalPin']))
        require(all(original.get(k) == probe[k] for k in ('name', 'state', 'returnValue', 'errno')) and
                original.get('browserIdentitySelectionPin') == context.selection_pin and
                original.get('browserRuntimeProofPin') == context.proof_pin, 'BROWSER_CAPABILITY_ORIGINAL_CHANGED')
        if probe['name'] in required:
            require(probe['state'] == 'PASSED' and probe['returnValue'] == 0 and probe['errno'] == 0,
                    'BROWSER_REQUIRED_CAPABILITY_UNAVAILABLE')
    context.raw(value['kernelConfigurationEvidencePin']); context.raw(value['containerSecurityPolicyEvidencePin'])
    require(context.signed(prior_intent['authorizationPin']) == grant and context.signed(prior_intent['leasePin']) == lease,
            'BROWSER_CAPABILITY_FINAL_AUTHORITY_CHANGED')
    current_window(grant, 'notBefore'); current_window(lease, 'notBefore'); current_window(prior_intent); current_window(value)
    require(time.monotonic() < context.deadline, 'BROWSER_CAPABILITY_DEADLINE')
    return value


def validate_sandbox(context, pin, process):
    evidence = validate_record(context.signed(pin), 'RepositoryLabBrowserSandboxEvidence/v1')
    require(evidence['browserIdentitySelectionPin'] == context.selection_pin and evidence['browserRuntimeProofPin'] == context.proof_pin and
            evidence['qualificationIntentPin'] == context.intent_pin and
            evidence['sandboxCapabilityResultPin'] == context.intent['sandboxCapabilityResultPin'] and
            evidence['browserPid'] == process['childPid'] and evidence['browserStartTicks'] == process['childStartTicks'],
            'BROWSER_SANDBOX_BATCH_CHANGED')
    producer = context.proof['producerIdentity']; host = {k: producer[k] for k in ('hostId', 'bootId')}
    def bound(raw, stamp='observedAt'):
        require(raw['browserIdentitySelectionPin'] == context.selection_pin and raw['browserRuntimeProofPin'] == context.proof_pin and
                raw['qualificationIntentPin'] == context.intent_pin, 'BROWSER_SANDBOX_ORIGINAL_BATCH')
        require(utc(process['startedAt']) <= utc(raw[stamp]) <= utc(evidence['observedAt']) <= utc(process['finishedAt']) and
                utc(raw[stamp]) <= datetime.now(timezone.utc), 'BROWSER_SANDBOX_ORIGINAL_TIME')
    common = {'schemaVersion', 'browserIdentitySelectionPin', 'browserRuntimeProofPin', 'qualificationIntentPin', 'observedAt'}
    mapped = {}
    for ref in evidence['namespaceMappingOriginalPins']:
        mapping = decode(context.raw(ref))
        exact(mapping, common | {'hostId', 'bootId', 'pid', 'startTicks', 'userNamespace', 'parentUserNamespace',
                                'uidMap', 'gidMap', 'setgroups'}, 'BROWSER_NAMESPACE_MAP_SHAPE')
        bound(mapping)
        require(mapping['schemaVersion'] == 'RepositoryLabBrowserNamespaceMapping/v2' and
                all(mapping[k] == v for k, v in host.items()) and type(mapping['pid']) is int and mapping['pid'] > 0 and
                type(mapping['startTicks']) is int and mapping['startTicks'] > 0 and
                mapping['uidMap'] == [[0, context.selection['browserUid'], 1]] and
                mapping['gidMap'] == [[0, context.selection['browserGid'], 1]] and mapping['setgroups'] == 'deny' and
                mapping['parentUserNamespace'] == producer['userNamespace'] and
                mapping['userNamespace'] != mapping['parentUserNamespace'], 'BROWSER_NAMESPACE_MAP_ESCAPES_SELECTED_B')
        key = (mapping['pid'], mapping['startTicks'])
        require(key not in mapped, 'BROWSER_DUPLICATE_NAMESPACE_MAPPING'); mapped[key] = mapping
    kernels = {}; kernel_refs = {}
    for ref in evidence['descendantKernelOriginalPins']:
        original = decode(context.raw(ref))
        exact(original, common | {'identity', 'role', 'seccomp', 'seccompFilters', 'ancestorAuthority',
                                  'ownedLineageOriginalPin'}, 'BROWSER_RENDERER_ORIGINAL_SHAPE')
        bound(original)
        measured = original['identity']; security_identity(measured, context.selection['browserUid'], context.selection['browserGid'])
        key = (measured['pid'], measured['startTicks'])
        require(original['schemaVersion'] == 'RepositoryLabBrowserDescendantKernel/v2' and original['role'] == 'STABLE_RENDERER' and
                all(measured[k] == v for k, v in host.items()) and measured['pidNamespace'] != producer['pidNamespace'] and
                measured['networkNamespace'] != producer['networkNamespace'] and key in mapped and
                measured['userNamespace'] == mapped[key]['userNamespace'] and original['ancestorAuthority'] == 'NONE' and
                type(original['seccomp']) is int and original['seccomp'] == 2 and
                type(original['seccompFilters']) is int and original['seccompFilters'] > 0, 'BROWSER_RENDERER_SECURITY_UNPROVEN')
        lineage = decode(context.raw(original['ownedLineageOriginalPin']))
        exact(lineage, common | {'hostId', 'bootId', 'browserPid', 'browserStartTicks', 'supervisorPid',
                                 'supervisorStartTicks', 'nodes'}, 'BROWSER_OWNED_LINEAGE_SHAPE')
        bound(lineage)
        require(lineage['schemaVersion'] == 'RepositoryLabBrowserOwnedLineage/v1' and
                all(lineage[k] == v for k, v in host.items()) and
                all(lineage[k] == process[k] for k in ('supervisorPid', 'supervisorStartTicks')) and
                lineage['browserPid'] == process['childPid'] and lineage['browserStartTicks'] == process['childStartTicks'] and
                type(lineage['nodes']) is list and 3 <= len(lineage['nodes']) <= 4096, 'BROWSER_OWNED_LINEAGE_BINDING')
        nodes = {}
        for node in lineage['nodes']:
            exact(node, {'pid', 'startTicks', 'parentPid', 'parentStartTicks'}, 'BROWSER_LINEAGE_NODE_SHAPE')
            require(all(type(v) is int and v > 0 for v in node.values()), 'BROWSER_LINEAGE_NODE_IDENTITY')
            node_key = (node['pid'], node['startTicks'])
            require(node_key not in nodes, 'BROWSER_LINEAGE_DUPLICATE'); nodes[node_key] = node
        browser_key = (process['childPid'], process['childStartTicks'])
        supervisor_key = (process['supervisorPid'], process['supervisorStartTicks'])
        producer_key = (producer['pid'], producer['startTicks'])
        require(browser_key in nodes and supervisor_key in nodes and key in nodes and
                (nodes[browser_key]['parentPid'], nodes[browser_key]['parentStartTicks']) == supervisor_key and
                (nodes[supervisor_key]['parentPid'], nodes[supervisor_key]['parentStartTicks']) == producer_key and
                measured['parentPid'] == nodes[key]['parentPid'], 'BROWSER_LINEAGE_SELECTED_ANCESTRY')
        for node_key in nodes:
            if node_key in (producer_key, supervisor_key): continue
            seen = set(); cursor = node_key
            while cursor != browser_key:
                require(cursor in nodes and cursor not in seen, 'BROWSER_LINEAGE_FOREIGN_OR_CYCLE')
                seen.add(cursor); node = nodes[cursor]; cursor = (node['parentPid'], node['parentStartTicks'])
        security = measured['security']; raw_security = decode(context.raw(security['securityOriginalPin']))
        exact(raw_security, {'schemaVersion', 'pid', 'startTicks', 'capEff', 'capPrm', 'capInh', 'capBnd', 'capAmb',
                             'supplementaryGroups', 'noNewPrivs', 'measuredAt'}, 'BROWSER_RENDERER_SECURITY_SHAPE')
        require(raw_security['schemaVersion'] == 'RepositoryLabBrowserSecurity/v1' and
                (raw_security['pid'], raw_security['startTicks']) == key and
                all(raw_security[k] == security[k] for k in ('capEff', 'capPrm', 'capInh', 'capBnd', 'capAmb',
                                                            'supplementaryGroups', 'noNewPrivs')) and
                utc(process['startedAt']) <= utc(raw_security['measuredAt']) <= utc(evidence['observedAt']),
                'BROWSER_RENDERER_SECURITY_ORIGINAL')
        require(key not in kernels, 'BROWSER_DUPLICATE_RENDERER'); kernels[key] = original; kernel_refs[key] = ref
    filters = {}
    for ref in evidence['seccompFilterOriginalPins']:
        original = decode(context.raw(ref))
        exact(original, common | {'hostId', 'bootId', 'pid', 'startTicks', 'seccomp', 'seccompFilters',
                                  'originalKernelPin'}, 'BROWSER_SECCOMP_ORIGINAL_SHAPE')
        bound(original); key = (original['pid'], original['startTicks'])
        require(original['schemaVersion'] == 'RepositoryLabBrowserSeccomp/v2' and key in kernels and
                all(original[k] == v for k, v in host.items()) and type(original['seccomp']) is int and original['seccomp'] == 2 and
                type(original['seccompFilters']) is int and original['seccompFilters'] == kernels[key]['seccompFilters'] and
                original['originalKernelPin'] == kernel_refs[key] and key not in filters, 'BROWSER_SECCOMP_FILTER_UNPROVEN')
        filters[key] = original
    require(kernels and set(kernels) == set(mapped) == set(filters), 'BROWSER_SANDBOX_PROOF_INCOMPLETE')
    return evidence


class BrowserAuthorityClient:
    def __init__(self, context, authority_identity_pin):
        self.context, self.authority_identity_pin = context, authority_identity_pin
        self.authority = validate_record(context.signed(authority_identity_pin), 'RepositoryLabBrowserParticipantIdentity/v1')
        current_window(self.authority)
        require(self.authority['role'] == 'AUTHORITY_A' and self.authority['browserIdentitySelectionPin'] == context.selection_pin and
                self.authority['browserRuntimeProofPin'] == context.proof_pin and
                self.authority['identity'] == context.proof['signerIdentity'], 'BROWSER_AUTHORITY_IDENTITY_UNBOUND')
        self.uid = context.selection['signerUid']

    def exchange(self, request):
        c = self.context; c.guard()
        _shape(request, DEFINITIONS['SignerRequest'])
        require(request['browserIdentitySelectionPin'] == c.selection_pin and
                request.get('browserRuntimeProofPin', request.get('guardRuntimeProofPin')) == c.proof_pin,
                'BROWSER_SIGNER_REQUEST_PROOF')
        path = c.selection['signerSocketPath']; token = browser_socket_custody(path, c.selection)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.settimeout(min(5, c.deadline - time.monotonic())); channel.connect(path)
            pid, uid, gid = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            peer = self.authority['identity']
            require((pid, uid, gid) == (peer['pid'], peer['uid'], peer['gid']) and identity(pid)['startTicks'] == peer['startTicks'],
                    'BROWSER_SIGNER_PEER_CHANGED')
            channel.sendall(canonical(request) + b'\n'); raw = bytearray()
            while not raw.endswith(b'\n'):
                require(time.monotonic() < c.deadline, 'BROWSER_SIGNER_DEADLINE')
                part = channel.recv(4096)
                require(part and len(raw) + len(part) <= 16384, 'BROWSER_SIGNER_RESPONSE_LIMIT'); raw.extend(part)
            response = decode(bytes(raw)); _shape(response, DEFINITIONS['SignerResponse'])
            require(identity(pid)['startTicks'] == peer['startTicks'], 'BROWSER_SIGNER_PEER_CHANGED')
        browser_socket_custody(path, c.selection, token); c.guard()
        return response

    def renew(self):
        c = self.context
        response = self.exchange({'guardRuntimeProofPin': c.proof_pin, 'browserIdentitySelectionPin': c.selection_pin})
        exact(response, {'measurementPin', 'authorityIdentityPin'}, 'BROWSER_GUARD_REPLY_REQUIRED')
        require(response['authorityIdentityPin'] == self.authority_identity_pin, 'BROWSER_AUTHORITY_READY_CHANGED')
        c.admit_guard(response['measurementPin'])

    def sign(self, original_pin, *, deadline, worker_uid):
        c = self.context
        require(deadline == c.deadline and worker_uid == c.selection['browserUid'], 'BROWSER_SIGNER_WORKER_CHANGED')
        self.renew(); expected = decode(read_producer_original(c, original_pin))
        response = self.exchange({'originalPin': original_pin, 'browserIdentitySelectionPin': c.selection_pin,
                                  'browserRuntimeProofPin': c.proof_pin})
        exact(response, {'signedPin'}, 'BROWSER_SIGNED_REPLY_REQUIRED')
        require(c.signed(response['signedPin']) == expected and decode(read_producer_original(c, original_pin)) == expected,
                'BROWSER_SIGNED_ORIGINAL_CHANGED')
        c.admit_output_graph(original_pin); c.admit_output_graph(response['signedPin'])
        self.renew(); return response['signedPin']

    def finish(self):
        c = self.context
        response = self.exchange({'finishLaunchPin': c.launch_pin, 'browserIdentitySelectionPin': c.selection_pin,
                                  'browserRuntimeProofPin': c.proof_pin})
        require(response == {'finishedLaunchPin': c.launch_pin}, 'BROWSER_FINISH_REPLY_CHANGED')


def read_producer_original(context, pin):
    root = context.selection['evidenceRoot']; literal_path(pin['path'], lab=True)
    require(pin['path'].startswith(root + '/') and pin['path'] != context.selection['privateKeyPin']['path'],
            'BROWSER_PRODUCER_ORIGINAL_UNSELECTED')
    return descriptor_read(pin, owners={0, context.selection['browserUid']}, deadline=context.deadline,
                           readonly=os.geteuid() != context.selection['browserUid'], modes=(0o600,))


def producer_original_pin(context, path):
    """Acquire a selected named terminal original without any symlink read."""
    literal_path(path, lab=True)
    require(path in context.reserved_paths(), 'BROWSER_NAMED_ORIGINAL_UNSELECTED')
    owners = {0, context.selection['browserUid']}
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in Path(path).parts[1:-1]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = following
            info = os.fstat(parent)
            require(info.st_uid in owners and not info.st_mode & 0o022, 'BROWSER_NAMED_ANCESTOR_CUSTODY')
        fd = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == context.selection['browserUid'] and
                    info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= 1048576 and
                    (os.geteuid() == context.selection['browserUid'] or os.fstatvfs(fd).f_flag & os.ST_RDONLY),
                    'BROWSER_NAMED_ORIGINAL_CUSTODY')
            raw = bytearray()
            while True:
                require(time.monotonic() < context.deadline, 'BROWSER_NAMED_ORIGINAL_DEADLINE')
                chunk = os.read(fd, 65536)
                if not chunk: break
                raw.extend(chunk); require(len(raw) <= info.st_size, 'BROWSER_NAMED_ORIGINAL_SIZE')
            require(file_metadata(info) == file_metadata(os.fstat(fd)), 'BROWSER_NAMED_ORIGINAL_CHANGED')
            pin = dict(path=path, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            require(read_producer_original(context, pin) == bytes(raw), 'BROWSER_NAMED_ORIGINAL_REOPEN_CHANGED')
            return pin
        finally: os.close(fd)
    finally: os.close(parent)


def persist_original(context, path, raw):
    literal_path(path, lab=True)
    require(path.startswith(context.selection['evidenceRoot'] + '/') and
            os.getresuid() == (context.selection['browserUid'],) * 3 and
            os.getresgid() == (context.selection['browserGid'],) * 3, 'BROWSER_OUTPUT_IDENTITY_REQUIRED')
    directory = producer_directory(context, str(Path(path).parent))
    try:
        meta = os.fstat(directory)
        require(meta.st_uid == context.selection['browserUid'] and meta.st_gid == context.selection['browserGid'] and
                stat.S_IMODE(meta.st_mode) == 0o700, 'BROWSER_OUTPUT_DIRECTORY_CUSTODY')
        fd = os.open(Path(path).name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw); stream.flush(); os.fsync(fd)
            os.fsync(directory)
        finally: os.close(fd)
    finally: os.close(directory)
    pin = {'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    read_producer_original(context, pin)
    return pin


def producer_directory(context, path):
    literal_path(path, lab=True)
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in Path(path).parts[1:]:
            following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = following
            meta = os.fstat(directory)
            require(meta.st_uid in (0, context.selection['browserUid']) and not meta.st_mode & 0o022,
                    'BROWSER_WRITE_ANCESTOR_CUSTODY')
        meta = os.fstat(directory)
        require(meta.st_uid == context.selection['browserUid'] and meta.st_gid == context.selection['browserGid'] and
                stat.S_IMODE(meta.st_mode) == 0o700, 'BROWSER_WRITABLE_DIRECTORY_CUSTODY')
        return directory
    except BaseException:
        os.close(directory); raise


def assert_current_b(context):
    s = context.selection
    require(sys.platform == 'linux' and os.getresuid() == (s['browserUid'],) * 3 and
            os.getresgid() == (s['browserGid'],) * 3 and os.getgroups() == [], 'BROWSER_PRE_DROPPED_B_REQUIRED')
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text(encoding='ascii').splitlines())
    require(all(int(status[name].strip(), 16) == 0 for name in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
            status['NoNewPrivs'].strip() == '1', 'BROWSER_CURRENT_CAPABILITY_AUTHORITY')
    # Missing CapAmb does not imply zero. The external broker's selected native
    # API measurement must prove UNSUPPORTED_PROVEN in that case.
    security = context.proof['producerIdentity']['security']
    require(('CapAmb' in status and int(status['CapAmb'].strip(), 16) == 0 and security['ambientState'] == 'PRESENT') or
            ('CapAmb' not in status and security['ambientState'] == 'UNSUPPORTED_PROVEN'), 'BROWSER_CURRENT_AMBIENT_UNPROVEN')
    selected = context.proof['producerIdentity']; actual = identity(os.getpid())
    require(actual['pid'] == selected['pid'] and actual['startTicks'] == selected['startTicks'] and
            all(os.readlink('/proc/self/ns/' + name) == selected[field] for field, name in NS_FIELDS.items()) and
            (os.stat('/proc/self/root').st_dev, os.stat('/proc/self/root').st_ino) ==
            (selected['rootDevice'], selected['rootInode']), 'BROWSER_CURRENT_ROOT_OR_PID_CHANGED')
    import ctypes
    require(ctypes.CDLL(None, use_errno=True).prctl(39, 0, 0, 0, 0) == 1, 'BROWSER_NATIVE_NNP_NOT_PROVEN')


def enter_selected_browser_identity(selection_pin, authority_pin, bootstrap_original_pin, *, role, deadline):
    """Called only by the existing selected privileged launcher, before drop.

    Reservation originals and an actual collision scan in this new task PID
    namespace are required. This helper never creates an account, recovers a
    capability, or executes a wrapper. Installation/root assembly stays W01's.
    """
    require(sys.platform == 'linux' and os.getresuid() == (0, 0, 0) and os.getresgid() == (0, 0, 0) and
            role in ('BROWSER_PRODUCER', 'AUTHORITY_A'), 'BROWSER_PRIVILEGED_PRE_DROP_REQUIRED')
    def raw(pin): return descriptor_read(pin, owners={0}, deadline=deadline)
    def signed(pin): return authenticate_payload(decode(raw(pin)), raw(authority_pin), authority_pin['sha256'])
    selection = validate_record(signed(selection_pin), 'RepositoryLabBrowserIdentitySelection/v1'); current_window(selection)
    require(selection['authorityKeyPin'] == authority_pin and selection['browserUid'] != selection['signerUid'] and
            selection['browserGid'] != selection['signerGid'], 'BROWSER_BOOTSTRAP_SEPARATE_ROLES')
    controller = signed(selection['controllerIdentityPin'])
    # Only that controller or its actual unreaped direct child may invoke the
    # already installed bootstrap source. Parent PID/start is never guessed.
    current = identity(os.getpid())
    require(controller['uid'] == controller['gid'] == 0 and
            identity(controller['pid'])['startTicks'] == controller['startTicks'] and
            current['parent'] == controller['pid'], 'BROWSER_EXISTING_SELECTED_PRIVILEGED_PARENT_REQUIRED')
    raw(selection['bootstrapLauncherPin'])
    original = signed(bootstrap_original_pin)
    exact(original, {'schemaVersion', 'browserIdentitySelectionPin', 'controllerIdentityPin', 'bootstrapLauncherPin',
                     'pidNamespace', 'reservationOriginalPin', 'roleRootPaths', 'issuedAt', 'expiresAt'},
          'BROWSER_BOOTSTRAP_ORIGINAL_SHAPE')
    require(original['schemaVersion'] == 'RepositoryLabBrowserBootstrapOriginal/v1' and
            original['browserIdentitySelectionPin'] == selection_pin and
            original['controllerIdentityPin'] == selection['controllerIdentityPin'] and
            original['bootstrapLauncherPin'] == selection['bootstrapLauncherPin'] and
            original['pidNamespace'] == controller['pidNamespace'] == os.readlink('/proc/self/ns/pid') and
            original['roleRootPaths'] == {'BROWSER_PRODUCER':selection['browserRootPath'], 'AUTHORITY_A':selection['signerRootPath']},
            'BROWSER_BOOTSTRAP_ORIGINAL_BINDING')
    current_window(original)
    reservation = signed(original['reservationOriginalPin'])
    exact(reservation, {'schemaVersion', 'browserIdentitySelectionPin', 'pidNamespace', 'unusedUidGidPairs',
                       'collisionObservationPins', 'issuedAt', 'expiresAt'}, 'BROWSER_RESERVATION_ORIGINAL_SHAPE')
    require(reservation['schemaVersion'] == 'RepositoryLabBrowserIdentityReservation/v1' and
            reservation['browserIdentitySelectionPin'] == selection_pin and reservation['pidNamespace'] == original['pidNamespace'] and
            reservation['unusedUidGidPairs'] == [[selection['browserUid'],selection['browserGid']],
                                               [selection['signerUid'],selection['signerGid']]] and
            reservation['collisionObservationPins'], 'BROWSER_ACTUAL_RESERVATION_REQUIRED')
    current_window(reservation)
    for pin in reservation['collisionObservationPins']: raw(pin)
    uid, gid, retained = ((selection['browserUid'], selection['browserGid'], 0) if role == 'BROWSER_PRODUCER'
                          else (selection['signerUid'], selection['signerGid'], 3))
    forbidden_uids, forbidden_gids = {uid}, {gid}
    # Both IDs were reserved before either role started. At this role's drop,
    # its selected identity must still be unused; the other role may be live.
    # Disappeared/unreadable processes fail rather than hiding a collision.
    for path in Path('/proc').iterdir():
        if not path.name.isdigit(): continue
        require(time.monotonic() < deadline, 'BROWSER_COLLISION_SCAN_DEADLINE')
        status = dict(line.split(':', 1) for line in (path/'status').read_text(encoding='ascii').splitlines())
        require(not forbidden_uids.intersection(map(int,status['Uid'].split())) and
                not forbidden_gids.intersection(map(int,status['Gid'].split())) and
                not forbidden_gids.intersection(map(int,status['Groups'].split())), 'BROWSER_RESERVED_IDENTITY_COLLISION')
    from recovery_native_launcher import drop_capabilities
    root = selection['browserRootPath'] if role == 'BROWSER_PRODUCER' else selection['signerRootPath']
    literal_path(root, lab=True)
    metadata = Path(root).lstat()
    require(stat.S_ISDIR(metadata.st_mode) and metadata.st_uid == 0 and not metadata.st_mode & 0o022,
            'BROWSER_SELECTED_BOOTSTRAP_ROOT_CUSTODY')
    require(os.readlink('/proc/self/ns/mnt') != controller['mountNamespace'],
            'BROWSER_SELECTED_PRIVATE_MOUNT_BEFORE_DROP_REQUIRED')
    os.chroot(root); os.chdir('/')
    drop_capabilities(uid, gid, retained)
    require(os.getresuid() == (uid, uid, uid) and os.getresgid() == (gid, gid, gid) and os.getgroups() == [],
            'BROWSER_BOOTSTRAP_IDENTITY_DROP_FAILED')


class BrowserSandboxObserver:
    """Separate finite root-parent observation channel, not a signer request.

    The actual renderer evidence is produced during this process, so its Pin
    cannot be precomputed in a launch record. W01 must provision this private
    channel and pin its observer before a browser batch can be released.
    """
    def __init__(self, context, channel):
        self.context, self.channel, self.started = context, channel, False
        controller = context.signed(context.selection['controllerIdentityPin'])
        pid, uid, gid = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require((pid,uid,gid) == (controller['pid'],0,0) and identity(pid)['startTicks'] == controller['startTicks'],
                'BROWSER_SANDBOX_OBSERVER_NOT_INDEPENDENT')
        self.controller = controller

    def start(self, process):
        c = self.context; c.guard()
        require(not self.started and process.pid is not None and process.worker_dispatched is not None,
                'BROWSER_SANDBOX_OBSERVATION_DISPATCH_REQUIRED')
        worker = next((v for v in process.observed if v['pid'] == process.pid), None)
        require(worker is not None and worker['uid'] == c.selection['browserUid'] and worker['gid'] == c.selection['browserGid'],
                'BROWSER_SANDBOX_OBSERVATION_WORKER_UNPROVEN')
        self.channel.settimeout(min(5,c.deadline-time.monotonic()))
        request = dict(schemaVersion='RepositoryLabBrowserSandboxObservationRequest/v1',
            browserIdentitySelectionPin=c.selection_pin, browserRuntimeProofPin=c.proof_pin,
            qualificationIntentPin=c.intent_pin, sandboxCapabilityResultPin=c.intent['sandboxCapabilityResultPin'],
            browserPid=process.pid, browserStartTicks=worker['startTicks'],
            supervisorPid=process.supervisor_pid, supervisorStartTicks=process.supervisor_identity['startTicks'])
        self.channel.sendall(canonical(request)+b'\n'); self.started = True

    def result(self):
        c = self.context; require(self.started, 'BROWSER_SANDBOX_OBSERVATION_NOT_STARTED')
        raw = bytearray()
        while not raw.endswith(b'\n'):
            require(time.monotonic() < c.deadline, 'BROWSER_SANDBOX_OBSERVATION_DEADLINE')
            self.channel.settimeout(min(5,c.deadline-time.monotonic()))
            part = self.channel.recv(4096)
            require(part and len(raw)+len(part) <= 16384, 'BROWSER_SANDBOX_OBSERVATION_RESPONSE'); raw.extend(part)
        response = decode(bytes(raw)); exact(response, {'sandboxEvidencePin'}, 'BROWSER_SANDBOX_OBSERVATION_PIN_REQUIRED')
        require(identity(self.controller['pid'])['startTicks'] == self.controller['startTicks'], 'BROWSER_SANDBOX_OBSERVER_CHANGED')
        c.guard(); return response['sandboxEvidencePin']


def run_selected_browser(context, signer, *, sandbox_observer=None):
    """One owned process. Failed or missing sandbox evidence cannot yield success."""
    c = context; c.guard(); assert_current_b(c); c.source_guard(); signer.renew()
    require(c.phase == 'NATIVE_BROWSER_CAPABILITY' and sandbox_observer is None or
            c.phase == 'NATIVE_BROWSER_QUALIFICATION' and isinstance(sandbox_observer, BrowserSandboxObserver) and
            sandbox_observer.context is c, 'BROWSER_SELECTED_LIVE_SANDBOX_OBSERVER_REQUIRED')
    command = c.command; root = Path(c.selection['evidenceRoot']) / command['commandId']
    # Parent is a selected B-private directory. Existing result paths fail.
    directory = producer_directory(c, str(root.parent))
    try:
        os.mkdir(root.name, mode=0o700, dir_fd=directory); os.fsync(directory)
    finally: os.close(directory)
    environment = dict(c.selection['environment'], INTRUOYI_NATIVE_DEADLINE_MONOTONIC=repr(c.deadline))
    process = OwnedChildSupervisor(command['argv'], env=environment, stdin=None, cwd=command['cwd'],
        user=c.selection['browserUid'], group=c.selection['browserGid'], no_new_privileges=True, inherit_identity=True)
    output, error = bytearray(), bytearray(); failure = None; started = utc_now()
    drain = NativeProcessProducer._drain
    try:
        prepare_local_supervision(); c.guard(); signer.renew(); assert_current_b(c)
        process.spawn(); process.start(min(5, c.deadline-time.monotonic()), guard=c.guard, deadline=c.deadline)
        if sandbox_observer is not None: sandbox_observer.start(process)
        drain(c, process, output, error, stdout_limit=16 * 1024 * 1024)
        c.guard(); signer.renew(); assert_current_b(c)
    except BaseException as exc:
        failure = getattr(exc, 'code', 'BROWSER_EXECUTION_OR_IO_FAILED')
        if process.process is not None:
            try:
                process.channel.shutdown(socket.SHUT_WR)
                drain(c, process, output, error, stdout_limit=16 * 1024 * 1024, cancelling=True)
            except BaseException as terminal_error:
                failure = 'BROWSER_TERMINAL_UNPROVEN:' + getattr(terminal_error, 'code', type(terminal_error).__name__)
    finally: process.close()
    kind, wait, code, descendants = terminal_status(process.terminal, None if process.process is None else process.process.returncode)
    if failure is not None: kind, wait, code, descendants = 'UNKNOWN', None, None, 'UNKNOWN'
    stdout = persist_original(c, str(root/'stdout'), bytes(output)); stderr = persist_original(c, str(root/'stderr'), bytes(error))
    parent_pin = persist_original(c, str(root/'supervisor-terminal.json'), canonical({'terminal': process.terminal,
        'supervisorExitCode': None if process.process is None else process.process.returncode,
        'failureCode': failure, 'stdoutPin': stdout, 'stderrPin': stderr}))
    parent = process.supervisor_identity
    worker = next((v for v in process.observed if v['pid'] == process.pid), None)
    if (parent is None or worker is None or parent['uid'] != c.selection['browserUid'] or parent['gid'] != c.selection['browserGid'] or
            worker['uid'] != c.selection['browserUid'] or worker['gid'] != c.selection['browserGid']):
        kind, wait, code, descendants = 'UNKNOWN', None, None, 'UNKNOWN'
    producer = c.proof['producerIdentity']
    from recovery_native_observation import wire_canonical
    sandbox_evidence_pin = None
    if sandbox_observer is not None and failure is None:
        try: sandbox_evidence_pin = sandbox_observer.result()
        except (EnvironmentFailure, OSError) as exc:
            failure = getattr(exc, 'code', 'BROWSER_SANDBOX_OBSERVATION_IO_FAILED')
            kind, wait, code, descendants = 'UNKNOWN', None, None, 'UNKNOWN'
    payload = {k: c.intent[k] for k in ('rehearsalId', 'qualificationId', 'operationId', 'phase', 'targetId', 'executorId')}
    payload.update(schemaVersion=PROCESS_VERSION, commandId=command['commandId'], command=wire_canonical(command['argv']).decode(),
        argv=command['argv'], cwd=command['cwd'], sourcePins=command['sourcePins'],
        supervisorPin=next(p for p in command['sourcePins'] if p['path'].endswith('/recovery_environment_supervisor.py')),
        pythonPin=c.manifest['pythonPin'], nativeRuntimeProofPin=c.proof_pin, hostId=producer['hostId'], bootId=producer['bootId'],
        **{k: producer[k] for k in NS_FIELDS}, supervisorPid=process.supervisor_pid,
        supervisorStartTicks=None if parent is None else parent['startTicks'], childPid=process.pid,
        childStartTicks=None if worker is None else worker['startTicks'], uid=c.selection['browserUid'], gid=c.selection['browserGid'],
        startedAt=started, finishedAt=utc_now(), terminationKind=kind, waitStatus=wait, actualExitCode=code,
        descendantState=descendants, stdoutPin=stdout, stderrPin=stderr, resultPin=stdout,
        browserIdentitySelectionPin=c.selection_pin, browserRuntimeProofPin=c.proof_pin,
        producerIdentityPin=c.provision['producerIdentityPin'], authorityIdentityPin=signer.authority_identity_pin,
        currentGuardMeasurementPins=list(c.guards), sandboxEvidencePin=sandbox_evidence_pin)
    if c.phase == 'NATIVE_BROWSER_QUALIFICATION':
        try:
            require(sandbox_evidence_pin is not None, 'BROWSER_REAL_SANDBOX_EVIDENCE_MISSING')
            validate_sandbox(c, sandbox_evidence_pin, payload)
        except EnvironmentFailure as exc:
            payload.update(terminationKind='UNKNOWN', waitStatus=None, actualExitCode=None, descendantState='UNKNOWN')
            failure = exc.code
    validate_record(payload, PROCESS_VERSION)
    original = persist_original(c, str(root/'process-original.json'), canonical(payload))
    signed = signer.sign(original, deadline=c.deadline, worker_uid=c.selection['browserUid'])
    if failure or payload['terminationKind'] == 'UNKNOWN' or payload['descendantState'] != 'REAPED':
        raise EnvironmentFailure(failure or 'BROWSER_PROCESS_UNKNOWN', unknown=True, result=signed)
    if payload['actualExitCode'] != 0 or payload['terminationKind'] != 'EXITED':
        raise EnvironmentFailure('BROWSER_PROCESS_FAILED', result=signed)
    return signed


class BrowserAuthorityService:
    """A's finite v2 service, using its independently provisioned root broker.

    The private socketpair is inherited from the selected privileged parent.
    Its original measurement is read by A, then signed by A; B can neither
    replace the peer nor submit a purported key-denial/renderer measurement.
    """
    def __init__(self, context, broker_channel):
        self.context, self.channel = context, broker_channel
        s = context.selection
        require(sys.platform == 'linux' and os.getresuid() == (s['signerUid'],) * 3 and
                os.getresgid() == (s['signerGid'],) * 3 and os.getgroups() == [], 'BROWSER_A_SELECTED_IDENTITY_REQUIRED')
        actual = identity(os.getpid()); selected = context.proof['signerIdentity']
        require(actual['pid'] == selected['pid'] and actual['startTicks'] == selected['startTicks'], 'BROWSER_A_SELECTED_PID_REQUIRED')
        status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text(encoding='ascii').splitlines())
        require(int(status['CapEff'].strip(), 16) == int(status['CapPrm'].strip(), 16) == int(status['CapBnd'].strip(), 16) == 3 and
                int(status['CapInh'].strip(), 16) == 0 and status['NoNewPrivs'].strip() == '1' and
                ('CapAmb' in status and int(status['CapAmb'].strip(), 16) == 0 or
                 'CapAmb' not in status and selected['security']['ambientState'] == 'UNSUPPORTED_PROVEN'),
                'BROWSER_A_EXISTING_CUSTODY_ONLY')
        parent = context.signed(s['controllerIdentityPin'])
        pid, uid, gid = struct.unpack('3i', broker_channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require((pid, uid, gid) == (parent['pid'], 0, 0) and identity(pid)['startTicks'] == parent['startTicks'],
                'BROWSER_INDEPENDENT_BROKER_PEER_REQUIRED')
        self.broker_identity = parent; self.broker_count = 0; self.signed_invocations = []
        key_pin = s['privateKeyPin']; key_path = Path(key_pin['path'])
        meta, directory = key_path.lstat(), key_path.parent.lstat()
        require(meta.st_uid == s['signerUid'] and meta.st_gid == s['signerGid'] and meta.st_nlink == 1 and
                stat.S_IMODE(meta.st_mode) == 0o400 and directory.st_uid == s['signerUid'] and
                stat.S_IMODE(directory.st_mode) == 0o700, 'BROWSER_A_KEY_CUSTODY_REQUIRED')
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        self.key = serialization.load_pem_private_key(descriptor_read(key_pin, owners={0, s['signerUid']},
            deadline=context.deadline, modes=(0o400,), readonly=True), password=None)
        require(isinstance(self.key, Ed25519PrivateKey), 'BROWSER_A_ED25519_REQUIRED')
        public = serialization.load_pem_public_key(context.raw(context.authority_pin))
        require(self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw) ==
                public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw), 'BROWSER_A_KEY_MISMATCH')
        self.sequence = 0; self.result_pin = None

    def publish(self, value):
        c = self.context; self.sequence += 1
        require(self.sequence <= c.selection['maximumRecords'] * 4, 'BROWSER_A_PUBLICATION_BUDGET')
        from recovery_native_observation import wire_canonical
        envelope = dict(schemaVersion='RepositorySignedRecord/v1', keySha256=c.authority_pin['sha256'], payload=value,
                        signature=base64.b64encode(self.key.sign(wire_canonical(value))).decode('ascii'))
        raw = canonical(envelope); root = c.selection['signedPublicationRoot']; literal_path(root, lab=True)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            meta = os.fstat(directory)
            require(meta.st_uid == 0 and meta.st_gid == c.selection['browserGid'] and stat.S_IMODE(meta.st_mode) == 0o750,
                    'BROWSER_A_PUBLICATION_CUSTODY')
            name = str(self.sequence) + '-' + hashlib.sha256(raw).hexdigest() + '.signed.json'
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            try:
                with os.fdopen(fd, 'wb', closefd=False) as stream:
                    stream.write(raw); stream.flush(); os.fsync(fd)
                os.fchown(fd, 0, c.selection['browserGid']); os.fchmod(fd, 0o440); os.fsync(fd); os.fsync(directory)
            finally: os.close(fd)
        finally: os.close(directory)
        pin = dict(path=root + '/' + name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        require(c.signed(pin) == value, 'BROWSER_A_PUBLICATION_READBACK_FAILED')
        return pin

    def sign_provider_original(self, pin, *, controller_channel):
        """Private W01 selected-controller lane; never a B socket request."""
        c = self.context
        pid, uid, gid = struct.unpack('3i', controller_channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require((pid, uid, gid) == (self.broker_identity['pid'], 0, 0) and
                identity(pid)['startTicks'] == self.broker_identity['startTicks'], 'BROWSER_PROVIDER_ACTUAL_CONTROLLER_PEER')
        raw = read_signed_publication(c, pin); value = decode(raw)
        require(value['schemaVersion'] in ('RepositoryLabBrowserSandboxCapabilityResult/v1', 'RepositoryLabBrowserSandboxEvidence/v1'),
                'BROWSER_PROVIDER_EXPLICIT_PAYLOAD')
        validate_record(value, value['schemaVersion'])
        # This proxy validates an unsigned original; it never authenticates it
        # as a signed record. The protected actual root peer is its producer.
        proxy = object.__new__(BrowserQualificationContext); proxy.__dict__ = dict(c.__dict__)
        proxy.signed = lambda reference: value if reference == pin else c.signed(reference)
        if value['schemaVersion'] == 'RepositoryLabBrowserSandboxCapabilityResult/v1':
            require(c.phase == 'NATIVE_BROWSER_CAPABILITY' and value['qualificationIntentPin'] == c.intent_pin,
                    'BROWSER_PROVIDER_CAPABILITY_BATCH')
            validate_capability(proxy, pin)
        else:
            require(c.phase == 'NATIVE_BROWSER_QUALIFICATION', 'BROWSER_PROVIDER_SANDBOX_BATCH')
            lineage = decode(c.raw(decode(c.raw(value['descendantKernelOriginalPins'][0]))['ownedLineageOriginalPin']))
            for selected_pid, ticks in ((value['browserPid'], value['browserStartTicks']),
                                       (lineage['supervisorPid'], lineage['supervisorStartTicks'])):
                require(identity(selected_pid)['startTicks'] == ticks, 'BROWSER_PROVIDER_LIVE_CHILD_CHANGED')
            process = dict(childPid=value['browserPid'], childStartTicks=value['browserStartTicks'],
                supervisorPid=lineage['supervisorPid'], supervisorStartTicks=lineage['supervisorStartTicks'],
                startedAt=c.intent['issuedAt'], finishedAt=utc_now())
            validate_sandbox(proxy, pin, process)
        self.measured_guard(); require(read_signed_publication(c, pin) == raw, 'BROWSER_PROVIDER_ORIGINAL_CHANGED')
        return self.publish(value)

    def measured_guard(self):
        c = self.context; c.guard(); self.broker_count += 1
        require(self.broker_count <= c.selection['maximumRecords'], 'BROWSER_BROKER_BUDGET')
        require(identity(self.broker_identity['pid'])['startTicks'] == self.broker_identity['startTicks'],
                'BROWSER_BROKER_CHANGED')
        self.channel.settimeout(min(5, c.deadline - time.monotonic()))
        request = dict(schemaVersion='RepositoryLabBrowserBrokerGuardRequest/v1', browserIdentitySelectionPin=c.selection_pin,
            browserRuntimeProofPin=c.proof_pin, qualificationIntentPin=c.intent_pin,
            authorizationPin=c.intent['authorizationPin'], leasePin=c.intent['leasePin'])
        self.channel.sendall(canonical(request) + b'\n'); raw = bytearray()
        while not raw.endswith(b'\n'):
            require(time.monotonic() < c.deadline, 'BROWSER_BROKER_DEADLINE')
            part = self.channel.recv(4096)
            require(part and len(raw) + len(part) <= 16384, 'BROWSER_BROKER_RESPONSE_INVALID'); raw.extend(part)
        response = decode(bytes(raw)); exact(response, {'guardOriginalPin'}, 'BROWSER_BROKER_EXPLICIT_RESPONSE_REQUIRED')
        measured = validate_record(decode(c.raw(response['guardOriginalPin'])), 'RepositoryLabBrowserGuardMeasurement/v1')
        validate_guard_originals(c, measured)
        pin = self.publish(measured); c.admit_guard(pin)
        return pin

    def peer(self, channel):
        c = self.context; self.current_measurement_pin = self.measured_guard()
        pid, uid, gid = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        peer = c.proof['producerIdentity']
        require((pid, uid, gid) == (peer['pid'], c.selection['browserUid'], c.selection['browserGid']) and
                identity(pid)['startTicks'] == peer['startTicks'], 'BROWSER_A_PEER_NOT_SELECTED_B')

    def sign_original(self, pin):
        c = self.context; raw = read_producer_original(c, pin); payload = decode(raw)
        version = payload.get('schemaVersion'); require(version in (PROCESS_VERSION, RESULT_VERSION), 'BROWSER_A_ONLY_V2_PAYLOAD')
        validate_record(payload, version)
        for field in ('rehearsalId', 'qualificationId', 'operationId', 'phase'):
            require(payload[field] == c.intent[field], 'BROWSER_A_RESULT_BATCH_CHANGED')
        require(payload['browserIdentitySelectionPin'] == c.selection_pin and payload['browserRuntimeProofPin'] == c.proof_pin and
                payload['authorityIdentityPin'] == self.authority_identity_pin, 'BROWSER_A_RESULT_PROOF_CHANGED')
        if version == PROCESS_VERSION:
            command = c.command
            require(not self.signed_invocations and pin['path'] == c.reserved_paths()[3] and
                    payload['nativeRuntimeProofPin'] == c.proof_pin and payload['producerIdentityPin'] == c.provision['producerIdentityPin'] and
                    payload['uid'] == c.selection['browserUid'] and payload['gid'] == c.selection['browserGid'] and
                    all(payload[k] == command[k] for k in ('commandId', 'argv', 'cwd', 'sourcePins')) and
                    payload['currentGuardMeasurementPins'] and all(p in c.guards for p in payload['currentGuardMeasurementPins']),
                    'BROWSER_A_INVOCATION_UNSELECTED')
            parent_path = str(Path(pin['path']).parent/'supervisor-terminal.json')
            # Metadata and raw bytes are verified through the same B-owned RO
            # view, including its exact held/reopened stream originals.
            parent_pin = producer_original_pin(c, parent_path)
            verify_parent_terminal(payload, decode(read_producer_original(c, parent_pin)))
            c.admit_output_graph(parent_pin)
            for name in ('stdoutPin', 'stderrPin', 'resultPin'): read_producer_original(c, payload[name])
            if c.phase == 'NATIVE_BROWSER_QUALIFICATION' and payload['terminationKind'] != 'UNKNOWN':
                require(payload['sandboxEvidencePin'] is not None, 'BROWSER_A_SANDBOX_EVIDENCE_MISSING')
                validate_sandbox(c, payload['sandboxEvidencePin'], payload)
        else:
            require(pin['path'] == c.reserved_paths()[-1] and payload['qualificationIntentPin'] == c.intent_pin and
                    payload['launchPin'] == c.launch_pin and payload['provisionPin'] == c.provision_pin and
                    payload['invocationPins'] == self.signed_invocations, 'BROWSER_A_RESULT_INVOCATION_CHAIN')
            processes = [validate_record(c.signed(p), PROCESS_VERSION) for p in self.signed_invocations]
            expected = ('UNKNOWN' if not processes or any(p['terminationKind'] == 'UNKNOWN' or p['descendantState'] == 'UNKNOWN' for p in processes)
                        else 'SUCCEEDED' if all(p['terminationKind'] == 'EXITED' and p['actualExitCode'] == 0 for p in processes) else 'FAILED')
            require(payload['state'] == expected, 'BROWSER_A_RESULT_STATE_UNPROVEN')
        self.measured_guard(); require(read_producer_original(c, pin) == raw, 'BROWSER_A_ORIGINAL_CHANGED')
        signed = self.publish(payload)
        c.admit_output_graph(pin); c.admit_output_graph(signed)
        if version == PROCESS_VERSION: self.signed_invocations.append(signed)
        else: self.result_pin = signed
        return signed

    def serve(self, on_ready):
        c = self.context; path = c.selection['signerSocketPath']
        require(not Path(path).exists(), 'BROWSER_A_SOCKET_COLLISION')
        self.measured_guard()
        payload = dict(schemaVersion='RepositoryLabBrowserParticipantIdentity/v1', rehearsalId=REHEARSAL_ID, role='AUTHORITY_A',
            browserIdentitySelectionPin=c.selection_pin, browserRuntimeProofPin=c.proof_pin, identity=c.proof['signerIdentity'],
            issuedAt=utc_now(), expiresAt=min(c.proof['expiresAt'], c.intent['expiresAt']))
        self.authority_identity_pin = self.publish(validate_record(payload, payload['schemaVersion']))
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(path); os.chmod(path, 0o660); os.chown(path, 0, c.selection['browserGid'], follow_symlinks=False)
            token = browser_socket_custody(path, c.selection); server.listen(1)
            on_ready(dict(schemaVersion='RepositoryLabNativeAuthorityReady/v2', browserIdentitySelectionPin=c.selection_pin,
                browserRuntimeProofPin=c.proof_pin, authorityIdentityPin=self.authority_identity_pin))
            return self._serve_pending(server, token)

    def _serve_pending(self, server, token):
        c = self.context; handled = 0
        while handled < c.selection['maximumRecords']:
            c.guard(); require(time.monotonic() < c.deadline, 'BROWSER_A_DEADLINE')
            if not select.select([server], [], [], min(.25, c.deadline-time.monotonic()))[0]: continue
            handled += 1
            if self._request(server, token): return
        raise EnvironmentFailure('BROWSER_A_REQUEST_BUDGET_EXHAUSTED')

    def _request(self, server, token):
        c = self.context; browser_socket_custody(c.selection['signerSocketPath'], c.selection, token)
        with server.accept()[0] as channel:
            channel.settimeout(min(5, c.deadline-time.monotonic())); self.peer(channel); raw = bytearray()
            while not raw.endswith(b'\n'):
                part = channel.recv(4096)
                require(part and len(raw)+len(part) <= 16384, 'BROWSER_A_REQUEST_SIZE'); raw.extend(part)
            request = decode(bytes(raw)); _shape(request, DEFINITIONS['SignerRequest'])
            require(request['browserIdentitySelectionPin'] == c.selection_pin and
                    request.get('browserRuntimeProofPin', request.get('guardRuntimeProofPin')) == c.proof_pin,
                    'BROWSER_A_REQUEST_SELECTION_CHANGED')
            finished = False
            if 'originalPin' in request: response = {'signedPin': self.sign_original(request['originalPin'])}
            elif 'guardRuntimeProofPin' in request:
                response = {'measurementPin': self.current_measurement_pin, 'authorityIdentityPin': self.authority_identity_pin}
            else:
                require(request['finishLaunchPin'] == c.launch_pin and self.result_pin is not None, 'BROWSER_A_FINISH_UNSELECTED')
                self.measured_guard(); response = {'finishedLaunchPin': c.launch_pin}; finished = True
            channel.sendall(canonical(response) + b'\n')
            return finished


def qualification_entry(context, authority_identity_pin, *, sandbox_observer=None):
    c = context; signer = BrowserAuthorityClient(c, authority_identity_pin); invocations = []; state = 'UNKNOWN'; failure = None
    try:
        invocations.append(run_selected_browser(c, signer, sandbox_observer=sandbox_observer)); state = 'SUCCEEDED'
    except EnvironmentFailure as exc:
        failure = exc
        if exc.result is not None: invocations.append(exc.result)
        state = 'UNKNOWN' if exc.unknown or not invocations else 'FAILED'
    payload = dict(schemaVersion=RESULT_VERSION, rehearsalId=REHEARSAL_ID,
        **{k: c.intent[k] for k in ('qualificationId', 'operationId', 'phase')},
        qualificationIntentPin=c.intent_pin, launchPin=c.launch_pin, provisionPin=c.provision_pin,
        authorityIdentityPin=authority_identity_pin, invocationPins=invocations, state=state,
        browserIdentitySelectionPin=c.selection_pin, browserRuntimeProofPin=c.proof_pin,
        issuedAt=utc_now(), expiresAt=min(c.intent['expiresAt'], c.proof['expiresAt']))
    validate_record(payload, RESULT_VERSION)
    original = persist_original(c, c.reserved_paths()[-1], canonical(payload))
    result = signer.sign(original, deadline=c.deadline, worker_uid=c.selection['browserUid']); signer.finish()
    if failure is not None: raise EnvironmentFailure(failure.code, unknown=state == 'UNKNOWN', result=result)
    return result


# W01 owns controller servers/FDs. Selected A alone signs provider originals.
def measure_browser_guard_originals(*args, **kwargs):
    from recovery_native_browser_measurement import measure_browser_guard_originals as provider
    return provider(*args, **kwargs)


def measure_browser_sandbox_originals(*args, **kwargs):
    from recovery_native_browser_measurement import measure_browser_sandbox_originals as provider
    return provider(*args, **kwargs)


def assemble_browser_capability_result(*args, **kwargs):
    from recovery_native_browser_measurement import assemble_browser_capability_result as provider
    return provider(*args, **kwargs)
