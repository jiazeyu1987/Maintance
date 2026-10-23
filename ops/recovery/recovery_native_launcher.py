"""Independently selected finite A parent and installed observation producer.

The worker may invoke only producer mode. Authority mode requires root, a
separately selected signed provision and private A root; it owns its A child
and the denial probes. No provisioning, Docker mutation or private-key value
comes from an operation/control request. Deployment of this entry is gated
separately from source implementation.
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import select
import signal
import socket
import stat
import struct
import sys
import time

from recovery_environment_contract import (canonical, decode, exact, require, utc, utc_now, EnvironmentFailure)
from recovery_environment_supervisor import identity
from recovery_native_process import (LAB_ROOT, NS_FIELDS, REHEARSAL_ID, NativeProcessProducer,
    IndependentAuthoritySigner, lab_path, pinned_bytes, signed_payload, persist_bytes, file_metadata,
    signer_socket_custody, open_lab_file, PROCESS_FIELDS, QUALIFICATION_BINDING_FIELDS,
    QUALIFICATION_PROCESS_SCHEMA, QUALIFICATION_PROCESS_FIELDS)
from recovery_native_service_identity import NativeServiceIdentityProducer, expected_identity, probe_commands, SERVICE_FIELDS
from recovery_native_observation import (NativeObservationService, RESULT_FIELDS, ObservationOrder,
                                        receive_frame, send_frame, observation_originals)
from recovery_native_installation_admission import (ADMISSION_SCHEMA, ADMISSION_FIELDS,
    installation_argv, installation_sources, admit_installation_original)

LAUNCH_FIELDS = set('schemaVersion rehearsalId operationRequestPin installationPin authorityKeyPin authorizationPin leasePin producerEntryPin signerEntryPin observationSocketPath evidenceRoot allowedCallerPin issuedAt expiresAt'.split())
PROVISION_FIELDS = set('schemaVersion rehearsalId launchPin privateKeyPin signerUid signerGid signerRootPath signerSocketPath producerIdentityPin serviceBindingPins workingDirectory maximumAgeMilliseconds maximumObservations recordSchemasPin'.split())
CALLER_FIELDS = set('schemaVersion rehearsalId pid startTicks uid gid hostId bootId pidNamespace mountNamespace networkNamespace userNamespace rootDevice rootInode nativeRuntimeProofPin issuedAt expiresAt'.split())
QUALIFICATION_INTENT_FIELDS = set('schemaVersion rehearsalId qualificationId operationId phase hostId targetId executorId sourceScopePin installationPin authorityKeyPin authorizationPin leasePin commandSelections deadlineMilliseconds issuedAt expiresAt'.split())
QUALIFICATION_GRANT_FIELDS = set('schemaVersion rehearsalId qualificationId operationId phase hostId targetId executorId actions notBefore expiresAt approved'.split())
QUALIFICATION_LEASE_FIELDS = set('schemaVersion rehearsalId qualificationId operationId phase hostId targetId executorId leaseId fenceToken notBefore expiresAt state'.split())
QUALIFICATION_LAUNCH_FIELDS = LAUNCH_FIELDS - {'operationRequestPin'} | {'qualificationIntentPin'}
QUALIFICATION_PROVISION_FIELDS = PROVISION_FIELDS - {'serviceBindingPins', 'recordSchemasPin'}
QUALIFICATION_RESULT_SCHEMA = 'RepositoryLabNativeQualificationResult/v1'
QUALIFICATION_RESULT_FIELDS = set('schemaVersion rehearsalId qualificationId operationId phase qualificationIntentPin launchPin provisionPin authorityIdentityPin invocationPins state issuedAt expiresAt'.split())
QUALIFICATION_SELECTION_FIELDS = set('action commandId argv cwd sourcePins'.split())
QUALIFICATION_ACTIONS = frozenset('INSTALLATION_ADMISSION AUTHORITY_CUSTODY OWNED_PROCESS_QUALIFICATION BROWSER_ABOUT_BLANK'.split())
BUSINESS_SCOPE_ACTIONS = frozenset(('BACKUP_FULL BACKUP_INCREMENTAL LIST_POINTS POINT_DETAIL READBACK_VERIFY '
    'RESTORE_PREFLIGHT PREPARE_TARGET RESTORE_EXECUTE START_APPLICATION VERIFY_RECOVERY REHEARSAL PLAN_REHEARSAL').split())
libc = ctypes.CDLL(None, use_errno=True) if sys.platform == 'linux' else None


def native_call(name, *args):
    require(libc is not None, 'NATIVE_LINUX_REQUIRED')
    require(getattr(libc, name)(*args) == 0, 'NATIVE_LAUNCH_' + name.upper() + '_FAILED')


def status(pid):
    values = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text(encoding='ascii').splitlines())
    return {name: value.strip() for name, value in values.items()}


def measure_process(pid):
    selected = identity(pid); root = os.stat(f'/proc/{pid}/root')
    selected.update(hostId=Path('/etc/machine-id').read_text(encoding='ascii').strip(),
        bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
        rootDevice=root.st_dev, rootInode=root.st_ino,
        **{field: os.readlink(f'/proc/{pid}/ns/{name}') for field, name in NS_FIELDS.items()})
    return selected


def match_process(selected, pid, uid):
    measured = measure_process(pid)
    require(selected['pid'] == pid and selected['uid'] == uid and all(selected[name] == measured[name] for name in
        ('startTicks', 'uid', 'gid', 'hostId', 'bootId', 'rootDevice', 'rootInode', *NS_FIELDS)),
        'NATIVE_SELECTED_PEER_CHANGED')
    require(measured['state'] not in ('Z', 'X'), 'NATIVE_SELECTED_PEER_NOT_LIVE')
    return measured


def read_signed_caller(reference, authority):
    value = signed_payload(reference, authority)
    exact(value, CALLER_FIELDS, 'NATIVE_SELECTED_CALLER_SHAPE')
    require(value['schemaVersion'] == 'RepositoryLabNativeCaller/v1' and value['rehearsalId'] == REHEARSAL_ID,
            'NATIVE_SELECTED_CALLER_VERSION')
    require(utc(value['issuedAt']) <= datetime.now(timezone.utc) < utc(value['expiresAt']),
            'NATIVE_SELECTED_CALLER_EXPIRED')
    return value


class NativeLaunchContext:
    """Reread exact protected grant/lease/request/source on every admission."""
    def __init__(self, launch_pin, authority_pin, provision_pin, *, verify_runtime):
        self.launch_pin, self.authority_pin, self.provision_pin = launch_pin, authority_pin, provision_pin
        self.launch = signed_payload(launch_pin, authority_pin)
        exact(self.launch, LAUNCH_FIELDS, 'NATIVE_LAUNCH_SHAPE')
        require(self.launch['schemaVersion'] == 'RepositoryLabNativeLaunch/v1' and
                self.launch['rehearsalId'] == REHEARSAL_ID and self.launch['authorityKeyPin'] == authority_pin,
                'NATIVE_LAUNCH_SELECTION')
        self.provision = signed_payload(provision_pin, authority_pin)
        exact(self.provision, PROVISION_FIELDS, 'NATIVE_PROVISION_SHAPE')
        require(self.provision['schemaVersion'] == 'RepositoryLabNativeProvision/v1' and
                self.provision['rehearsalId'] == REHEARSAL_ID and self.provision['launchPin'] == launch_pin,
                'NATIVE_PROVISION_SELECTION')
        require(type(self.provision['signerUid']) is int and self.provision['signerUid'] > 0 and
                type(self.provision['signerGid']) is int and self.provision['signerGid'] > 0 and
                type(self.provision['maximumObservations']) is int and 2 <= self.provision['maximumObservations'] <= 64,
                'NATIVE_PROVISION_FINITE_ROLES')
        require(self.provision['serviceBindingPins'] and len(self.provision['serviceBindingPins']) <= 32,
                'NATIVE_PROVISION_SERVICE_SELECTION')
        evidence_root = lab_path(self.launch['evidenceRoot'], directory=True)
        require(evidence_root in lab_path(self.provision['signerSocketPath'], exists=False).parents and
                evidence_root in lab_path(self.launch['observationSocketPath'], exists=False).parents and
                lab_path(self.provision['signerSocketPath'], exists=False).parent !=
                lab_path(self.launch['observationSocketPath'], exists=False).parent,
                'NATIVE_A_OBSERVATION_OUTPUT_SEPARATION')
        for name in ('producerEntryPin', 'signerEntryPin'):
            require(self.launch[name]['path'].endswith('/ops/recovery/recovery_native_launcher.py'),
                    'NATIVE_INSTALLED_ENTRY_REQUIRED')
            pinned_bytes(self.launch[name])
        require(self.launch['producerEntryPin']['path'] == self.launch['signerEntryPin']['path'],
                'NATIVE_SINGLE_SELECTED_ENTRY_REQUIRED')
        self.request = decode(pinned_bytes(self.launch['operationRequestPin']))
        from recovery_environment_contract import Schemas
        self.schemas = Schemas(decode(pinned_bytes(self.provision['recordSchemasPin'])))
        self.schemas.validate(self.request, 'OperationRequest')
        require(self.request['mode'] == 'REHEARSAL' and self.request['action'] in ('VERIFY_RECOVERY', 'REHEARSAL') and
                self.request['leaseRef'] == self.launch['leasePin'] and
                self.launch['authorizationPin'] in self.request['authorizationRefs'], 'NATIVE_OPERATION_AUTHORITY_SELECTION')
        self.installation = signed_payload(self.launch['installationPin'], authority_pin)
        require(self.installation['schemaVersion'] == 'RepositoryNativeInstallation/v2', 'NATIVE_EXPLICIT_V2_REQUIRED')
        self.proof_pin = self.installation['nativeRuntimeProofPin']
        self.proof = signed_payload(self.proof_pin, authority_pin)
        self.native_trust = signed_payload(self.installation['nativeRuntimeTrustPin'], authority_pin)
        self.caller = read_signed_caller(self.launch['allowedCallerPin'], authority_pin)
        self.producer_identity = read_signed_caller(self.provision['producerIdentityPin'], authority_pin)
        require(self.producer_identity['nativeRuntimeProofPin'] == self.proof_pin and
                self.producer_identity['uid'] == self.producer_identity['gid'] == 0,
                'NATIVE_PRODUCER_CURRENT_RUNTIME_REQUIRED')
        require(all(self.producer_identity[k] == self.proof[k] for k in
                    ('rootDevice', 'rootInode', 'hostId', 'bootId', *NS_FIELDS)), 'NATIVE_PRODUCER_PROOF_IDENTITY')
        self.static_pins = self.installation['filePins'] + self.installation['dependencyPins'] + [self.installation['pythonPin']]
        self.native_tool_pins = [entry['pin'] for entry in self.native_trust['nativeFilePins'] if 'native-tool' in entry['roles']]
        require(self.launch['producerEntryPin'] in self.installation['filePins'] and
                self.launch['signerEntryPin'] in self.installation['filePins'], 'NATIVE_ENTRY_NOT_INSTALLED')
        self.deadline = time.monotonic() + min(self.request['deadlineMilliseconds'] / 1000,
            (utc(self.launch['expiresAt']) - datetime.now(timezone.utc)).total_seconds())
        self.expires_at = min(self.launch['expiresAt'], self.proof['expiresAt'],
                              self.caller['expiresAt'], self.producer_identity['expiresAt'])
        self.verify_runtime = verify_runtime
        self.reader_pins = {p['path']: p for p in [self.launch['operationRequestPin'], self.provision['recordSchemasPin'],
            *self.provision['serviceBindingPins']]}
        self.operation_binding = None
        self.protected_records = {}
        self.guard(); self._select_bindings()

    def _window(self, record, start='issuedAt'):
        require(utc(record[start]) <= datetime.now(timezone.utc) < utc(record['expiresAt']), 'NATIVE_CURRENT_AUTHORITY_EXPIRED')

    def guard(self):
        require(time.monotonic() < self.deadline, 'NATIVE_LAUNCH_DEADLINE')
        require(signed_payload(self.launch_pin, self.authority_pin) == self.launch and
                signed_payload(self.provision_pin, self.authority_pin) == self.provision and
                decode(pinned_bytes(self.launch['operationRequestPin'])) == self.request and
                signed_payload(self.launch['installationPin'], self.authority_pin) == self.installation and
                signed_payload(self.proof_pin, self.authority_pin) == self.proof and
                signed_payload(self.installation['nativeRuntimeTrustPin'], self.authority_pin) == self.native_trust,
                'NATIVE_CURRENT_PROTECTED_SELECTION_CHANGED')
        for value in (self.launch, self.proof, self.caller, self.producer_identity): self._window(value)
        require(read_signed_caller(self.launch['allowedCallerPin'], self.authority_pin) == self.caller and
                read_signed_caller(self.provision['producerIdentityPin'], self.authority_pin) == self.producer_identity,
                'NATIVE_SELECTED_PEER_RECORD_CHANGED')
        for path, (pin, value) in self.protected_records.items():
            require(decode(pinned_bytes(pin)) == value, 'NATIVE_PROTECTED_TARGET_OR_SOURCE_CHANGED')
        grant = signed_payload(self.launch['authorizationPin'], self.authority_pin)
        lease = signed_payload(self.launch['leasePin'], self.authority_pin)
        exact(grant, 'schemaVersion operationId targetId executorId mode actions notBefore expiresAt approved'.split(),
              'NATIVE_GRANT_SHAPE')
        exact(lease, 'schemaVersion operationId targetId executorId leaseId fenceToken notBefore expiresAt state'.split(),
              'NATIVE_LEASE_SHAPE')
        require(grant['schemaVersion'] == 'RecoveryEnvironmentAuthorization/v1' and
                lease['schemaVersion'] == 'RecoveryEnvironmentLease/v1' and grant['approved'] is True and
                grant['mode'] == self.request['mode'] and self.request['action'] in grant['actions'] and
                grant['operationId'] == lease['operationId'] == self.request['operationId'] and
                grant['targetId'] == lease['targetId'] and grant['executorId'] == lease['executorId'] and
                lease['state'] == 'HELD' and type(lease['fenceToken']) is int and lease['fenceToken'] > 0,
                'NATIVE_CURRENT_GRANT_OR_LEASE_INVALID')
        self._window(grant, 'notBefore'); self._window(lease, 'notBefore')
        self.grant, self.lease = grant, lease
        config = decode(pinned_bytes(self.request['sourceOrTargetRef']))
        require(config.get('schemaVersion') == 'RecoveryEnvironmentConfig/v1' and config['targetId'] == grant['targetId'],
                'NATIVE_REQUEST_TARGET_UNBOUND')
        self.expires_at = min(self.expires_at, grant['expiresAt'], lease['expiresAt'])
        if self.verify_runtime:
            from repository_native_runtime import verify_native_installation
            require(verify_native_installation(self.launch['installationPin'], [self.authority_pin],
                    deadline=self.deadline) == self.installation, 'NATIVE_CURRENT_RUNTIME_CHANGED')

    def reader(self, reference):
        require(self.reader_pins.get(reference['path']) == reference, 'NATIVE_UNSELECTED_RECORD')
        return decode(pinned_bytes(reference))

    def _select_bindings(self):
        bindings = [self.reader(p) for p in self.provision['serviceBindingPins']]
        selected = []; operations = []
        for b in bindings:
            require(b['environmentConfigPin'] == self.request['sourceOrTargetRef'], 'NATIVE_BINDING_REQUEST_TARGET')
            for name in ('targetIdentityPin', 'sourceScopePin', 'environmentConfigPin', 'resourcesProofPin', 'applicationStartPin'):
                selected.append(b[name])
            operation, chain = restored_application_binding(self.request, b, self.schemas)
            selected += chain
            operations.append(operation)
        require(all(o == operations[0] for o in operations), 'NATIVE_BINDINGS_DIFFERENT_OPERATION')
        self.operation_binding = operations[0]
        for p in selected:
            require(p['path'] not in self.reader_pins or self.reader_pins[p['path']] == p, 'NATIVE_CONFLICTING_PIN')
            self.reader_pins[p['path']] = p; pinned_bytes(p)
        self.protected_records = {p['path']: (p, decode(pinned_bytes(p))) for p in self.reader_pins.values()}
        self.commands = []
        for b in bindings:
            _, service, network, _, _ = expected_identity(b, self.reader, self.request['operationId'])
            self.commands += probe_commands(b['dockerPin'], service['id'], network['networkId'])
        self.installation_command = installation_argv(self.installation, self.launch['producerEntryPin'],
            self.launch['installationPin'], self.authority_pin)
        self.commands.append(self.installation_command)
        require(len(self.reader_pins) + len(self.static_pins) <= 4096, 'NATIVE_GRAPH_LIMIT')
        self.graph_pins = protected_record_graph([self.launch_pin, self.authority_pin, self.provision_pin,
            self.launch, self.provision, self.request, self.installation, self.proof, self.native_trust,
            self.caller, self.producer_identity, self.grant, self.lease,
            *[value for _, value in self.protected_records.values()], *self.reader_pins.values()],
            opaque_paths={self.provision['privateKeyPin']['path']},
            immutable_pins=[e['pin'] for e in self.native_trust['nativeFilePins']],
            data_pins=browser_resource_pins(self.native_trust), deadline=self.deadline)


    def check_caller(self, peer):
        require(read_signed_caller(self.launch['allowedCallerPin'], self.authority_pin) == self.caller,
                'NATIVE_ALLOWED_CALLER_CHANGED')
        pid, uid, gid = peer
        require(gid == self.caller['gid'], 'NATIVE_CALLER_GID_CHANGED')
        match_process(self.caller, pid, uid)

    def dispatch_guard(self, dispatch):
        self.guard()
        require(all(dispatch[k] == self.operation_binding[k] for k in self.operation_binding) and
                dispatch['argv'] in self.commands and dispatch['cwd'] == self.provision['workingDirectory'] and
                dispatch['sourcePins'] and all(p in self.static_pins or p in self.native_tool_pins
                    for p in dispatch['sourcePins']), 'NATIVE_LITERAL_COMMAND_NOT_ADMITTED')
        if dispatch['argv'] == self.installation_command:
            require(dispatch['sourcePins'] == installation_sources(self.installation, self.launch['producerEntryPin']),
                    'NATIVE_ADMISSION_SOURCE_SELECTION')
        else:
            require(dispatch['argv'][0] in [p['path'] for p in self.native_tool_pins] and
                    self.launch['producerEntryPin'] in dispatch['sourcePins'], 'NATIVE_COMMAND_PROVENANCE_REQUIRED')

    def signing_runtime(self, payload):
        self.guard()
        identity_record = None; binding = None
        if payload['schemaVersion'] == 'RepositoryLabNativeObserveResult/v1':
            identity_record = signed_payload(payload['identityProofPin'], self.authority_pin)
            binding = self.reader(payload['serviceBindingPin'])
            self._window(identity_record)
        return selected_signing_runtime(payload, self.launch, self.installation,
                                        self.provision, binding, identity_record)

    def admit_process(self, payload):
        self.dispatch_guard(payload)
        require(payload['nativeRuntimeProofPin'] == self.proof_pin and payload['uid'] == payload['gid'] == 0 and
                all(payload[k] == self.proof[k] for k in ('hostId', 'bootId', *NS_FIELDS)) and
                utc(self.launch['issuedAt']) <= utc(payload['startedAt']) <= utc(payload['finishedAt']) <=
                datetime.now(timezone.utc) < utc(self.expires_at), 'NATIVE_A_PROCESS_RUNTIME_SELECTION')


def restored_application_binding(request, binding, schemas):
    """Use the frozen application -> restore result -> plan -> point chain."""
    require(request['action'] == 'VERIFY_RECOVERY' and set(request['inputPins']) ==
            {'restorePlan', 'restoreExecutionResult', 'applicationStartResult'}, 'NATIVE_VERIFY_INPUT_KEYS')
    policy_pin = request['policyPin']; policy = decode(pinned_bytes(policy_pin))
    exact(policy, ('schemaVersion maxAgeMilliseconds rtoObjectiveMilliseconds rpoObjectiveMilliseconds '
        'recoveryTargetPin verificationTargetPin dataBaselinePin dataObservationPin protectionBeforePin protectionAfterPin '
        'playwrightObservationPin timingObservationPin requiredUserPaths protectedScopes '
        'requireDeletedReferenceObjects derivedBaselinePin controlledEligibilityPin').split(), 'NATIVE_VERIFICATION_POLICY_SHAPE')
    require(policy['schemaVersion'] == 'RecoveryVerificationPolicy/v2' and
            type(policy['maxAgeMilliseconds']) is int and policy['maxAgeMilliseconds'] > 0 and
            policy['controlledEligibilityPin'] is None, 'NATIVE_VERIFICATION_POLICY_INVALID')
    for key in ('rtoObjectiveMilliseconds', 'rpoObjectiveMilliseconds'):
        require(policy[key] is None or type(policy[key]) is int and policy[key] >= 0,
                'NATIVE_VERIFICATION_POLICY_INVALID')
    app_pin = binding['applicationStartPin']; app = decode(pinned_bytes(app_pin))
    schemas.validate(app, 'ApplicationStartResult')
    restore_pin = app['restoreResultPin']; restore = decode(pinned_bytes(restore_pin))
    schemas.validate(restore, 'RestoreExecutionResult')
    plan_pin = restore['planPin']; plan = decode(pinned_bytes(plan_pin))
    schemas.validate(plan, 'RestorePlan')
    config = decode(pinned_bytes(plan['targetRef']))
    require(config.get('schemaVersion') == 'RecoveryEnvironmentConfig/v1' and
            plan['targetRef'] == request['sourceOrTargetRef'] == binding['environmentConfigPin'] and
            config['sourceScopePin'] == binding['sourceScopePin'] and
            config['targetIdentityPin'] == binding['targetIdentityPin'], 'NATIVE_RESTORED_CONFIGURATION_UNBOUND')
    target_pin = policy['recoveryTargetPin']
    target = decode(pinned_bytes(target_pin)); schemas.validate(target, 'RecoveryTarget')
    point = decode(pinned_bytes(plan['candidatePin'])); schemas.validate(point, 'RepositoryPoint')
    require(app['operationId'] == restore['operationId'] == plan['operationId'] == request['operationId'] and
            app['restoreId'] == restore['restoreId'] == plan['restoreId'] and
            app['targetIdentityPin'] == restore['targetIdentityPin'] == target['targetIdentityPin'] ==
            binding['targetIdentityPin'] and plan['mode'] == request['mode'] == 'REHEARSAL' and
            app['state'] == restore['state'] == 'SUCCEEDED' and
            app['configurationPin'] == target['configurationPin'] and
            all(p in target['versionPins'] for p in app['imagePins']) and
            restore['recoveryPoint'] == plan['recoveryPoint'] == point['commonRecoveryPoint'] and
            plan['orderedChainPins'] and plan['orderedChainPins'][-1] == plan['candidatePin'] and
            request['selectedPointPin'] == plan['candidatePin'] and
            all(request['inputPins'].get(k) == p for k, p in (
                ('applicationStartResult', app_pin), ('restoreExecutionResult', restore_pin),
                ('restorePlan', plan_pin))),
            'NATIVE_RESTORED_APPLICATION_CHAIN_UNBOUND')
    originals = app['originalStartResultPins'] + restore['originalInvocationPins']
    chain = [app_pin, restore_pin, plan_pin, plan['targetRef'], policy_pin, target_pin, plan['candidatePin'],
             *plan['orderedChainPins'], *originals]
    # Keep nested evidence Pins in the same effective graph; do not replace
    # the frozen ApplicationStartResult with a private expanded record.
    return dict(operationId=request['operationId'], restoreId=app['restoreId'],
        targetIdentityPin=binding['targetIdentityPin'], recoveryPoint=restore['recoveryPoint'],
        stage='VERIFY_RECOVERY'), chain


class NativeQualificationContext:
    """Explicit private pre-business phase with its own grant, lease and records."""
    _window = NativeLaunchContext._window
    reader = NativeLaunchContext.reader
    check_caller = NativeLaunchContext.check_caller

    def __init__(self, launch_pin, authority_pin, provision_pin, *, verify_runtime):
        self.launch_pin, self.authority_pin, self.provision_pin = launch_pin, authority_pin, provision_pin
        self.launch = signed_payload(launch_pin, authority_pin)
        exact(self.launch, QUALIFICATION_LAUNCH_FIELDS, 'NATIVE_QUALIFICATION_LAUNCH_SHAPE')
        require(self.launch['schemaVersion'] == 'RepositoryLabNativeQualificationLaunch/v1' and
                self.launch['rehearsalId'] == REHEARSAL_ID and self.launch['authorityKeyPin'] == authority_pin,
                'NATIVE_QUALIFICATION_LAUNCH_SELECTION')
        self.provision = signed_payload(provision_pin, authority_pin)
        exact(self.provision, QUALIFICATION_PROVISION_FIELDS, 'NATIVE_QUALIFICATION_PROVISION_SHAPE')
        require(self.provision['schemaVersion'] == 'RepositoryLabNativeQualificationProvision/v1' and
                self.provision['rehearsalId'] == REHEARSAL_ID and self.provision['launchPin'] == launch_pin and
                type(self.provision['signerUid']) is int and self.provision['signerUid'] > 0 and
                type(self.provision['signerGid']) is int and self.provision['signerGid'] > 0 and
                type(self.provision['maximumObservations']) is int and
                1 <= self.provision['maximumObservations'] <= 64 and
                type(self.provision['maximumAgeMilliseconds']) is int and
                0 < self.provision['maximumAgeMilliseconds'] <= 300000,
                'NATIVE_QUALIFICATION_FINITE_PROVISION')
        root = lab_path(self.launch['evidenceRoot'], directory=True)
        require(root in lab_path(self.provision['signerSocketPath'], exists=False).parents and
                root in lab_path(self.launch['observationSocketPath'], exists=False).parents and
                lab_path(self.provision['signerSocketPath'], exists=False).parent !=
                lab_path(self.launch['observationSocketPath'], exists=False).parent,
                'NATIVE_A_OBSERVATION_OUTPUT_SEPARATION')
        lab_path(self.provision['workingDirectory'], directory=True)
        lab_path(self.provision['signerRootPath'], directory=True)
        lab_path(self.provision['privateKeyPin']['path'], exists=False)  # never open the A key
        self.installation = signed_payload(self.launch['installationPin'], authority_pin)
        require(self.installation['schemaVersion'] == 'RepositoryNativeInstallation/v2', 'NATIVE_EXPLICIT_V2_REQUIRED')
        self.proof_pin = self.installation['nativeRuntimeProofPin']
        self.proof = signed_payload(self.proof_pin, authority_pin)
        self.native_trust = signed_payload(self.installation['nativeRuntimeTrustPin'], authority_pin)
        require(self.proof['schemaVersion'] == 'RepositoryLabNativeRuntimeProof/v1' and
                self.proof['rehearsalId'] == self.native_trust['rehearsalId'] == REHEARSAL_ID and
                self.proof['nativeRuntimeTrustPin'] == self.installation['nativeRuntimeTrustPin'] and
                self.native_trust['runtimeRole'] == 'EXECUTOR', 'NATIVE_QUALIFICATION_RUNTIME_SELECTION')
        self.static_pins = self.installation['filePins'] + self.installation['dependencyPins'] + [self.installation['pythonPin']]
        self.native_tool_pins = [e['pin'] for e in self.native_trust['nativeFilePins'] if 'native-tool' in e['roles']]
        require(self.launch['producerEntryPin'] == self.launch['signerEntryPin'] and
                self.launch['producerEntryPin'] in self.installation['filePins'] and
                self.launch['producerEntryPin']['path'].endswith('/ops/recovery/recovery_native_launcher.py'),
                'NATIVE_ENTRY_NOT_INSTALLED')
        self.deadline = time.monotonic() + min(300, self.provision['maximumAgeMilliseconds'] / 1000)
        native_members = [e['pin'] for e in self.native_trust['nativeFilePins']]
        resources = browser_resource_pins(self.native_trust)
        stable = protected_record_graph([self.launch['installationPin'], authority_pin],
                                        immutable_pins=native_members, data_pins=resources, deadline=self.deadline)
        dynamic = [launch_pin, provision_pin, self.launch['qualificationIntentPin'],
                   self.launch['authorizationPin'], self.launch['leasePin']]
        require(not {p['path'] for p in stable} & {p['path'] for p in dynamic}, 'NATIVE_QUALIFICATION_STABLE_GRAPH_CYCLE')
        self.caller = read_signed_caller(self.launch['allowedCallerPin'], authority_pin)
        self.producer_identity = read_signed_caller(self.provision['producerIdentityPin'], authority_pin)
        require(self.producer_identity['uid'] == self.producer_identity['gid'] == 0 and
                self.producer_identity['nativeRuntimeProofPin'] == self.caller['nativeRuntimeProofPin'] == self.proof_pin and
                all(self.producer_identity[k] == self.proof[k] for k in
                    ('rootDevice', 'rootInode', 'hostId', 'bootId', *NS_FIELDS)), 'NATIVE_PRODUCER_PROOF_IDENTITY')
        self.intent = signed_payload(self.launch['qualificationIntentPin'], authority_pin)
        exact(self.intent, QUALIFICATION_INTENT_FIELDS, 'NATIVE_QUALIFICATION_INTENT_SHAPE')
        require(self.intent['schemaVersion'] == 'RepositoryLabNativeQualificationIntent/v1' and
                self.intent['rehearsalId'] == REHEARSAL_ID and self.intent['phase'] == 'NATIVE_QUALIFICATION' and
                all(type(self.intent[k]) is str and self.intent[k] and self.intent[k].isascii() and
                    '\x00' not in self.intent[k] for k in ('qualificationId', 'operationId', 'hostId', 'targetId', 'executorId')) and
                all(self.intent[k] == self.launch[k] for k in
                    ('installationPin', 'authorityKeyPin', 'authorizationPin', 'leasePin')) and
                self.intent['hostId'] == self.proof['hostId'] and
                type(self.intent['deadlineMilliseconds']) is int and 0 < self.intent['deadlineMilliseconds'] <= 300000,
                'NATIVE_QUALIFICATION_INTENT_SELECTION')
        self.scope = signed_payload(self.intent['sourceScopePin'], authority_pin)
        validate_qualification_scope(self.scope)
        pinned_bytes(self.scope['sourceIdentityPin'])
        self.binding = {k: self.intent[k] for k in QUALIFICATION_BINDING_FIELDS}
        self.selections = self.intent['commandSelections']
        self.installation_command = installation_argv(self.installation, self.launch['producerEntryPin'],
            self.launch['installationPin'], authority_pin)
        self.verify_runtime = verify_runtime
        self.deadline = min(self.deadline, time.monotonic() + self.intent['deadlineMilliseconds'] / 1000)
        self.expires_at = min(self.intent['expiresAt'], self.launch['expiresAt'], self.proof['expiresAt'],
            self.caller['expiresAt'], self.producer_identity['expiresAt'], self.scope['expiresAt'])
        self.reader_pins = {self.launch['qualificationIntentPin']['path']: self.launch['qualificationIntentPin'],
                            self.intent['sourceScopePin']['path']: self.intent['sourceScopePin']}
        self.commands = [s['argv'] for s in self.selections] if type(self.selections) is list else []
        self._select_commands()
        self.guard()
        self.graph_pins = protected_record_graph([launch_pin, provision_pin, authority_pin],
            opaque_paths={self.provision['privateKeyPin']['path']}, immutable_pins=native_members,
            data_pins=resources, deadline=self.deadline)

    def _select_commands(self):
        require(type(self.selections) is list and 0 < len(self.selections) <= self.provision['maximumObservations'],
                'NATIVE_QUALIFICATION_COMMAND_BUDGET')
        ids = set()
        for selection in self.selections:
            exact(selection, QUALIFICATION_SELECTION_FIELDS, 'NATIVE_QUALIFICATION_COMMAND_SHAPE')
            name = selection['commandId']
            require(type(name) is str and name and name.isascii() and
                    all(c.isalnum() or c in '-_' for c in name) and name not in ids,
                    'NATIVE_QUALIFICATION_COMMAND_ID')
            ids.add(name)
            require(selection['action'] in QUALIFICATION_ACTIONS and
                    selection['cwd'] == self.provision['workingDirectory'], 'NATIVE_QUALIFICATION_COMMAND_SCOPE')
            sources = selection['sourcePins']
            require(type(sources) is list and sources and all(p in self.static_pins or
                    any(e['pin'] == p for e in self.native_trust['nativeFilePins'])
                    for p in sources), 'NATIVE_QUALIFICATION_SOURCE_SELECTION')
            action = selection['action']; argv = selection['argv']
            if action == 'INSTALLATION_ADMISSION':
                require(argv == self.installation_command and
                        sources == installation_sources(self.installation, self.launch['producerEntryPin']),
                        'NATIVE_QUALIFICATION_INSTALLATION_COMMAND')
            elif action in ('AUTHORITY_CUSTODY', 'OWNED_PROCESS_QUALIFICATION'):
                require(argv == [self.installation['pythonPin']['path'], self.launch['producerEntryPin']['path'],
                                 'qualify-owned-process'] and
                        sources == installation_sources(self.installation, self.launch['producerEntryPin']),
                        'NATIVE_QUALIFICATION_OWNED_COMMAND')
            else:
                require(type(argv) is list and len(argv) == 5 and argv[1:] ==
                        ['--headless', '--disable-gpu', '--dump-dom', 'about:blank'] and
                        Path(argv[0]).name == 'chrome-headless-shell' and
                        any(p['path'] == argv[0] for p in self.native_tool_pins),
                        'NATIVE_QUALIFICATION_ABOUT_BLANK_ONLY')
                require(argv[0] == '/opt/brlab-browser/chrome-headless-shell', 'NATIVE_BROWSER_LITERAL_EXECUTABLE')
                browser_resource_pins(self.native_trust)
                browser_root = Path(argv[0]).parent
                closure = [e['pin'] for e in self.native_trust['nativeFilePins']
                           if browser_root in Path(e['pin']['path']).parents]
                expected_sources = self.static_pins + closure
                require(closure and len(sources) == len({p['path'] for p in sources}) and
                        {canonical(p) for p in sources} == {canonical(p) for p in expected_sources},
                        'NATIVE_QUALIFICATION_BROWSER_CLOSURE')
                catalog_paths = {p['path'] for p in closure}
                require(catalog_paths == {str(p) for p in browser_root.rglob('*') if p.is_file()},
                        'NATIVE_QUALIFICATION_BROWSER_RESOURCE_UNSELECTED')

    def guard(self):
        require(time.monotonic() < self.deadline, 'NATIVE_LAUNCH_DEADLINE')
        for pin, value in ((self.launch_pin, self.launch), (self.provision_pin, self.provision),
                (self.launch['qualificationIntentPin'], self.intent), (self.intent['sourceScopePin'], self.scope),
                (self.launch['installationPin'], self.installation), (self.proof_pin, self.proof),
                (self.installation['nativeRuntimeTrustPin'], self.native_trust)):
            require(signed_payload(pin, self.authority_pin) == value, 'NATIVE_CURRENT_PROTECTED_SELECTION_CHANGED')
        validate_qualification_scope(self.scope)
        pinned_bytes(self.scope['sourceIdentityPin'])
        for record in (self.launch, self.intent, self.proof, self.caller, self.producer_identity): self._window(record)
        require(datetime.now(timezone.utc) < utc(self.scope['expiresAt']) and
                read_signed_caller(self.launch['allowedCallerPin'], self.authority_pin) == self.caller and
                read_signed_caller(self.provision['producerIdentityPin'], self.authority_pin) == self.producer_identity,
                'NATIVE_SELECTED_PEER_RECORD_CHANGED')
        grant = signed_payload(self.launch['authorizationPin'], self.authority_pin)
        lease = signed_payload(self.launch['leasePin'], self.authority_pin)
        exact(grant, QUALIFICATION_GRANT_FIELDS, 'NATIVE_QUALIFICATION_GRANT_SHAPE')
        exact(lease, QUALIFICATION_LEASE_FIELDS, 'NATIVE_QUALIFICATION_LEASE_SHAPE')
        require(grant['schemaVersion'] == 'RepositoryLabNativeQualificationAuthorization/v1' and
                lease['schemaVersion'] == 'RepositoryLabNativeQualificationLease/v1' and grant['approved'] is True and
                all(grant[k] == lease[k] == self.intent[k] for k in
                    ('rehearsalId', 'qualificationId', 'operationId', 'phase', 'hostId', 'targetId', 'executorId')) and
                type(grant['actions']) is list and grant['actions'] and
                all(type(a) is str for a in grant['actions']) and
                len(set(grant['actions'])) == len(grant['actions']) and
                set(grant['actions']) <= QUALIFICATION_ACTIONS and
                all(s['action'] in grant['actions'] for s in self.selections) and
                lease['state'] == 'HELD' and type(lease['fenceToken']) is int and lease['fenceToken'] > 0 and
                type(lease['leaseId']) is str and lease['leaseId'] and lease['leaseId'].isascii(),
                'NATIVE_QUALIFICATION_CURRENT_GRANT_LEASE')
        self._window(grant, 'notBefore'); self._window(lease, 'notBefore')
        self.grant, self.lease = grant, lease
        self.expires_at = min(self.expires_at, grant['expiresAt'], lease['expiresAt'])
        if self.verify_runtime:
            from repository_native_runtime import verify_native_installation
            require(verify_native_installation(self.launch['installationPin'], [self.authority_pin],
                    deadline=self.deadline) == self.installation, 'NATIVE_CURRENT_RUNTIME_CHANGED')

    def dispatch_guard(self, dispatch):
        self.guard()
        if any(s['action'] == 'BROWSER_ABOUT_BLANK' for s in self.selections):
            self._select_commands()
        require(all(dispatch[k] == self.binding[k] for k in self.binding) and
                any(all(dispatch[k] == s[k] for k in ('commandId', 'argv', 'cwd', 'sourcePins'))
                    for s in self.selections), 'NATIVE_QUALIFICATION_DISPATCH_UNSELECTED')

    def signing_runtime(self, payload):
        self.guard()
        if payload['schemaVersion'] == QUALIFICATION_PROCESS_SCHEMA:
            exact(payload, QUALIFICATION_PROCESS_FIELDS, 'NATIVE_QUALIFICATION_PROCESS_SHAPE')
            require(payload['nativeRuntimeProofPin'] == self.proof_pin, 'NATIVE_QUALIFICATION_PROCESS_PROOF')
        else:
            require(payload['schemaVersion'] == QUALIFICATION_RESULT_SCHEMA, 'NATIVE_QUALIFICATION_SIGNER_SCHEMA')
            exact(payload, QUALIFICATION_RESULT_FIELDS, 'NATIVE_QUALIFICATION_RESULT_SHAPE')
        require(payload['rehearsalId'] == REHEARSAL_ID and all(payload[k] == self.intent[k] for k in
                ('qualificationId', 'operationId', 'phase')), 'NATIVE_QUALIFICATION_RESULT_BINDING')
        return self.proof_pin

    def admit_process(self, payload):
        self.signing_runtime(payload); self.dispatch_guard(payload)
        require(payload['uid'] == payload['gid'] == 0 and
                all(payload[k] == self.proof[k] for k in ('hostId', 'bootId', *NS_FIELDS)) and
                utc(self.launch['issuedAt']) <= utc(payload['startedAt']) <= utc(payload['finishedAt']) <=
                datetime.now(timezone.utc) < utc(self.expires_at) and
                payload['terminationKind'] in ('EXITED', 'SIGNALED') and
                type(payload['waitStatus']) is int and type(payload['actualExitCode']) is int and
                payload['descendantState'] == 'REAPED', 'NATIVE_QUALIFICATION_ACTUAL_TERMINAL_REQUIRED')
        require(payload['resultPin'] == payload['stdoutPin'], 'NATIVE_QUALIFICATION_RESULT_ORIGINAL')
        if payload['actualExitCode'] == 0:
            selection = next(s for s in self.selections if s['commandId'] == payload['commandId'])
            if selection['action'] == 'INSTALLATION_ADMISSION':
                from recovery_native_observation import wire_canonical
                require(pinned_bytes(payload['stdoutPin']) == wire_canonical(self.installation) and
                        pinned_bytes(payload['stderrPin']) == b'', 'NATIVE_QUALIFICATION_INSTALLATION_ORIGINAL')
            elif selection['action'] in ('AUTHORITY_CUSTODY', 'OWNED_PROCESS_QUALIFICATION'):
                raw = decode(pinned_bytes(payload['stdoutPin']))
                exact(raw, {'identity', 'groups', 'capabilities'}, 'NATIVE_QUALIFICATION_WORKER_ORIGINAL_SHAPE')
                measured = raw['identity']; caps = raw['capabilities']
                exact(caps, ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb', 'NoNewPrivs'),
                      'NATIVE_QUALIFICATION_WORKER_CAP_SHAPE')
                require(measured['pid'] == payload['childPid'] and measured['startTicks'] == payload['childStartTicks'] and
                        measured['uid'] == measured['gid'] == 0 and raw['groups'] == [] and
                        all(measured[k] == self.proof[k] for k in
                            ('hostId', 'bootId', 'rootDevice', 'rootInode', *NS_FIELDS)) and
                        all(int(caps[k], 16) == 0 for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb')) and
                        caps['NoNewPrivs'] == '1' and pinned_bytes(payload['stderrPin']) == b'',
                        'NATIVE_QUALIFICATION_WORKER_ORIGINAL_UNBOUND')


class AuthorityQualificationAdmission:
    """A verifies an ordered finite set of private originals independently."""
    def __init__(self, context):
        self.context = context; self.calls = {}; self.result = None
        self.graph = {p['path']: p for p in context.graph_pins}

    def admit(self, payload):
        context = self.context; context.signing_runtime(payload)
        if payload['schemaVersion'] == QUALIFICATION_PROCESS_SCHEMA:
            context.admit_process(payload)
            encoded = canonical(payload); name = payload['commandId']
            require(self.result is None, 'NATIVE_QUALIFICATION_ALREADY_FINISHED')
            if name in self.calls:
                require(self.calls[name] == encoded, 'NATIVE_QUALIFICATION_ORIGINAL_REPLACED')
            else:
                require(len(self.calls) < len(context.selections) and
                        name == context.selections[len(self.calls)]['commandId'], 'NATIVE_QUALIFICATION_ORDER')
                self.calls[name] = encoded
            from recovery_environment_contract import pin_file
            from recovery_native_signer import verify_parent_terminal
            directory = lab_path(context.launch['evidenceRoot'], directory=True) / name
            original_pin = pin_file(directory / 'process-original.json')
            parent_pin = pin_file(directory / 'supervisor-terminal.json')
            require(decode(pinned_bytes(original_pin)) == payload, 'NATIVE_QUALIFICATION_ORIGINAL_CHANGED')
            parent = decode(pinned_bytes(parent_pin)); verify_parent_terminal(payload, parent)
            records = [payload, original_pin, parent_pin, parent]
        else:
            require(payload['qualificationIntentPin'] == context.launch['qualificationIntentPin'] and
                    payload['launchPin'] == context.launch_pin and payload['provisionPin'] == context.provision_pin and
                    payload['state'] in ('SUCCEEDED', 'FAILED') and
                    utc(context.launch['issuedAt']) <= utc(payload['issuedAt']) <= datetime.now(timezone.utc) <
                    utc(payload['expiresAt']) <= utc(context.expires_at), 'NATIVE_QUALIFICATION_FINITE_SELECTION')
            peer = signed_payload(payload['authorityIdentityPin'], context.authority_pin)
            exact(peer, CALLER_FIELDS, 'NATIVE_A_IDENTITY_SHAPE')
            require(peer['schemaVersion'] == 'RepositoryLabNativeAuthority/v1' and peer['rehearsalId'] == REHEARSAL_ID and
                    peer['nativeRuntimeProofPin'] == context.proof_pin and peer['pid'] == os.getpid() and
                    peer['uid'] == context.provision['signerUid'] and peer['gid'] == context.provision['signerGid'],
                    'NATIVE_QUALIFICATION_CURRENT_A')
            context._window(peer); match_process(peer, os.getpid(), os.geteuid())
            pins = payload['invocationPins']
            require(type(pins) is list and len(pins) == len(self.calls) and pins,
                    'NATIVE_QUALIFICATION_INVOCATIONS_INCOMPLETE')
            records = [payload, peer]; success = True; previous = None
            from recovery_native_signer import verify_parent_terminal
            from recovery_environment_contract import pin_file
            for index, pin in enumerate(pins):
                process = signed_payload(pin, context.authority_pin); context.admit_process(process)
                name = context.selections[index]['commandId']
                require(process['commandId'] == name and self.calls[name] == canonical(process) and
                        (previous is None or utc(previous) <= utc(process['startedAt'])),
                        'NATIVE_QUALIFICATION_SIGNED_ORIGINAL_UNBOUND')
                original_path = lab_path(context.launch['evidenceRoot'], directory=True) / name / 'process-original.json'
                original_pin = pin_file(original_path)
                require(decode(pinned_bytes(original_pin)) == process, 'NATIVE_QUALIFICATION_ORIGINAL_CHANGED')
                parent_pin = pin_file(original_path.parent / 'supervisor-terminal.json')
                parent = decode(pinned_bytes(parent_pin)); verify_parent_terminal(process, parent)
                for k in ('stdoutPin', 'stderrPin', 'resultPin'): pinned_bytes(process[k])
                passed = process['terminationKind'] == 'EXITED' and process['waitStatus'] == process['actualExitCode'] == 0
                require(passed or index == len(pins)-1, 'NATIVE_QUALIFICATION_CONTINUED_AFTER_FAILURE')
                success = success and passed; previous = process['finishedAt']
                records += [pin, original_pin, parent_pin, process, parent]
            require(utc(previous) <= utc(payload['issuedAt']) and
                    ((payload['state'] == 'SUCCEEDED' and success and len(pins) == len(context.selections)) or
                     (payload['state'] == 'FAILED' and not success)), 'NATIVE_QUALIFICATION_STATE_UNPROVEN')
            encoded = canonical(payload)
            require(self.result is None or self.result == encoded, 'NATIVE_QUALIFICATION_RESULT_REPLACED')
            self.result = encoded
        for pin in selected_graph_pins([context.graph_pins, *self.graph.values(), *records]): self.graph[pin['path']] = pin
        # A's pending signed records and current finite original are part of
        # this same graph, even before their final signature Pins are known.
        pending_outputs = len(self.calls) if payload['schemaVersion'] == QUALIFICATION_PROCESS_SCHEMA else 2
        require(len(self.graph) + pending_outputs <= 4096, 'NATIVE_GRAPH_LIMIT')


def validate_qualification_scope(scope):
    exact(scope, 'schemaVersion rehearsalId repositoryId sourceIdentityPin host root resourcePrefix allowedActions expiresAt'.split(),
          'NATIVE_QUALIFICATION_SCOPE_SHAPE')
    actions = scope['allowedActions']
    require(scope['schemaVersion'] == 'RepositoryLabScope/v1' and scope['rehearsalId'] == REHEARSAL_ID and
            scope['host'] == '172.30.30.59' and scope['root'] == str(LAB_ROOT) and
            scope['resourcePrefix'] == 'brlab-20261012' and type(scope['repositoryId']) is str and scope['repositoryId'] and
            type(actions) is list and actions and all(type(a) is str for a in actions) and
            len(actions) == len(set(actions)) and set(actions) <= BUSINESS_SCOPE_ACTIONS and
            datetime.now(timezone.utc) < utc(scope['expiresAt']), 'NATIVE_QUALIFICATION_TASK_SCOPE')
    exact(scope['sourceIdentityPin'], ('path', 'bytes', 'sha256'), 'NATIVE_QUALIFICATION_SOURCE_PIN')
    source = scope['sourceIdentityPin']
    path = PurePosixPath(source['path'])
    require(path.is_absolute() and '..' not in path.parts and str(path) == source['path'] and
            type(source['bytes']) is int and source['bytes'] >= 0 and type(source['sha256']) is str and
            len(source['sha256']) == 64 and all(c in '0123456789abcdef' for c in source['sha256']),
            'NATIVE_QUALIFICATION_SOURCE_PIN')


def browser_resource_pins(trust):
    """Require W03's new exact inventory; it is provenance, never admission."""
    entries = [e for e in trust['nativeFilePins'] if 'native-browser-resource' in e['roles']]
    if not entries: return []
    from repository_native_browser_resources import BROWSER_RESOURCE_ORIGINALS, BROWSER_ROOT, BROWSER_VENDOR_ARCHIVE_PIN
    result = []
    for entry in entries:
        pin = entry['pin']; path = PurePosixPath(pin['path'])
        require(entry['roles'] == ['native-browser-resource'] and PurePosixPath(BROWSER_ROOT) in path.parents and
                '..' not in path.parts and str(path) == pin['path'], 'NATIVE_BROWSER_RESOURCE_ROLE_OR_PATH')
        relative = path.relative_to(BROWSER_ROOT).as_posix()
        original = BROWSER_RESOURCE_ORIGINALS.get(relative)
        require(original is not None and type(pin['bytes']) is int and 0 < pin['bytes'] <= 134217728 and
                (pin['bytes'], pin['sha256']) == (original['bytes'], original['sha256']) and
                BROWSER_VENDOR_ARCHIVE_PIN in entry['vendorArtifactPins'] and
                all(p in trust['vendorArtifactPins'] for p in entry['vendorArtifactPins']),
                'NATIVE_BROWSER_RESOURCE_VENDOR_SELECTION')
        result.append(pin)
    return result


def protected_record_graph(roots, *, opaque_paths=frozenset(), immutable_pins=(), data_pins=(), deadline=None):
    """Expand pinned JSON originals, reject cycles and count one combined graph."""
    graph = {}; active = set(); immutable = {p['path']: p for p in immutable_pins}
    data = {p['path']: p for p in data_pins}
    require(not set(data) & set(opaque_paths) and all(immutable.get(p['path']) == p for p in data_pins),
            'NATIVE_GRAPH_DATA_SELECTION')
    def original(pin):
        path = Path(pin['path'])
        if LAB_ROOT in path.parents:
            fd, parent = open_lab_file(str(path), os.O_RDONLY)
        else:
            require(immutable.get(str(path)) == pin and path.is_absolute() and '..' not in path.parts,
                    'NATIVE_GRAPH_MEMBER_UNSELECTED')
            parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                for component in path.parts[1:-1]:
                    child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent); parent = child
                fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
            except BaseException:
                os.close(parent); raise
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_uid == 0 and
                    not before.st_mode & 0o022 and type(pin['bytes']) is int and before.st_size == pin['bytes'],
                    'NATIVE_GRAPH_ORIGINAL_CUSTODY')
            if LAB_ROOT not in path.parents:
                require(os.fstatvfs(fd).f_flag & os.ST_RDONLY, 'NATIVE_GRAPH_MEMBER_NOT_READONLY')
            digest = hashlib.sha256(); prefix = b''; raw = bytearray(); count = 0; document = False
            while True:
                if deadline is not None: require(time.monotonic() < deadline, 'NATIVE_GRAPH_DEADLINE')
                chunk = os.read(fd, 1048576)
                if not chunk: break
                count += len(chunk); digest.update(chunk)
                if not prefix:
                    prefix = chunk
                    require(prefix.lstrip(), 'NATIVE_GRAPH_DOCUMENT_PREFIX_UNDETERMINED')
                    document = pin['path'] not in data and chunk.lstrip().startswith((b'{', b'['))
                if document:
                    require(count <= 134217728, 'NATIVE_GRAPH_DOCUMENT_TOO_LARGE'); raw.extend(chunk)
            require(count == pin['bytes'] and digest.hexdigest() == pin['sha256'] and
                    file_metadata(before) == file_metadata(os.fstat(fd)), 'NATIVE_GRAPH_ORIGINAL_CHANGED')
            current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            require(file_metadata(current) == file_metadata(before), 'NATIVE_GRAPH_ORIGINAL_PATH_CHANGED')
            return decode(bytes(raw)) if document else None
        finally:
            os.close(fd); os.close(parent)
    def walk(value):
        if type(value) is dict and set(value) == {'path', 'bytes', 'sha256'} and type(value['path']) is str:
            path = value['path']
            require(type(value['bytes']) is int and value['bytes'] >= 0 and type(value['sha256']) is str and
                    len(value['sha256']) == 64 and all(c in '0123456789abcdef' for c in value['sha256']),
                    'NATIVE_GRAPH_PIN_SHAPE')
            require(path not in active, 'NATIVE_GRAPH_CYCLE')
            if path in graph:
                require(graph[path] == value, 'NATIVE_GRAPH_CONFLICT'); return
            graph[path] = value; require(len(graph) <= 4096, 'NATIVE_GRAPH_LIMIT')
            if path not in opaque_paths:
                active.add(path); walk(original(value)); active.remove(path)
        elif type(value) is dict:
            for item in value.values(): walk(item)
        elif type(value) is list:
            for item in value: walk(item)
    for value in roots: walk(value)
    return list(graph.values())



def selected_signing_runtime(payload, launch, installation, provision, binding, authenticated_identity):
    """Derive observe runtime only through the authenticated identity and selection."""
    version = payload['schemaVersion']
    if version == 'RepositoryLabNativeObserveResult/v1':
        exact(payload, RESULT_FIELDS, 'NATIVE_SIGNER_OBSERVE_SHAPE')
        exact(authenticated_identity, SERVICE_FIELDS, 'NATIVE_SIGNER_IDENTITY_SHAPE')
        require(authenticated_identity['schemaVersion'] == 'RecoveryNativeServiceIdentity/v1' and
                payload['operationRequestPin'] == launch['operationRequestPin'] and
                payload['serviceBindingPin'] in provision['serviceBindingPins'] and
                all(authenticated_identity[k] == binding[k] for k in
                    ('targetIdentityPin', 'sourceScopePin', 'environmentConfigPin', 'resourcesProofPin',
                     'applicationStartPin', 'role', 'endpointUrl', 'dockerPin')),
                'NATIVE_SIGNER_OBSERVE_IDENTITY_SELECTION')
        runtime = authenticated_identity['probeRuntimeProofPin']
    elif version == 'RecoveryNativeProcessResult/v1':
        exact(payload, PROCESS_FIELDS, 'NATIVE_SIGNER_PROCESS_SHAPE'); runtime = payload['nativeRuntimeProofPin']
    elif version == 'RecoveryNativeServiceIdentity/v1':
        exact(payload, SERVICE_FIELDS, 'NATIVE_SIGNER_IDENTITY_SHAPE'); runtime = payload['probeRuntimeProofPin']
    elif version == ADMISSION_SCHEMA:
        exact(payload, ADMISSION_FIELDS, 'NATIVE_SIGNER_ADMISSION_SHAPE')
        require(payload['installationPin'] == launch['installationPin'] and payload['launchPin'] == provision['launchPin'] and
                payload['producerIdentityPin'] == provision['producerIdentityPin'] and
                payload['nativeRuntimeTrustPin'] == installation['nativeRuntimeTrustPin'],
                'NATIVE_SIGNER_ADMISSION_SELECTION')
        runtime = payload['nativeRuntimeProofPin']
    else:
        raise RuntimeError('NATIVE_SIGNER_PAYLOAD_SCHEMA_UNSELECTED')
    require(payload['rehearsalId'] == REHEARSAL_ID and runtime == installation['nativeRuntimeProofPin'],
            'NATIVE_SIGNER_CURRENT_RUNTIME_SELECTION')
    return runtime


def selected_graph_pins(records):
    """Count all Pins in selected protected records/catalogs with dynamic originals."""
    graph = {}; pending = list(records)
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if set(value) == {'path', 'bytes', 'sha256'} and type(value['path']) is str:
                require(value['path'] not in graph or graph[value['path']] == value, 'NATIVE_GRAPH_CONFLICT')
                graph[value['path']] = value
                require(len(graph) <= 4096, 'NATIVE_GRAPH_LIMIT')
            else:
                pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    return list(graph.values())


class AuthorityObservationAdmission:
    """A keeps its own finite sequence, distinct from producer bookkeeping."""
    def __init__(self, context):
        self.context = context; self.order = ObservationOrder(context.provision['maximumObservations'])
        self.admission_order = ObservationOrder(context.provision['maximumObservations'])
        self.admissions = {}
        self.pending = {}; self.graph = {p['path']: p for p in context.graph_pins}

    def admit_installation(self, payload):
        context = self.context
        originals = admit_installation_original(payload, context)
        encoded = canonical(payload); sequence = payload['sequence']
        if sequence not in self.admissions:
            self.admission_order.reserve({k: payload[k] for k in ('rehearsalId', 'collectionId', 'sequence', 'phase',
                'operationRequestPin', 'serviceBindingPin')} | {'schemaVersion': 'RepositoryLabNativeObserveRequest/v1',
                'issuedAt': payload['issuedAt'], 'deadlineMilliseconds': context.request['deadlineMilliseconds']})
            self.admissions[sequence] = encoded
        else:
            require(self.admissions[sequence] == encoded, 'NATIVE_A_ADMISSION_REPLACED')
        return originals

    def admit(self, payload):
        exact(payload, RESULT_FIELDS, 'NATIVE_A_OBSERVATION_SHAPE')
        context = self.context; context.guard()
        require(payload['operationRequestPin'] == context.launch['operationRequestPin'] and
                payload['serviceBindingPin'] in context.provision['serviceBindingPins'], 'NATIVE_A_OBSERVE_SELECTION')
        pins, start, end = observation_originals(payload['identityProofPin'], context.authority_pin,
            lab_path(context.launch['evidenceRoot'], directory=True), context.graph_pins)
        prefix = f'observe-{payload["sequence"]}-{payload["phase"].lower()}'
        from recovery_environment_contract import pin_file
        admission_original = pin_file(lab_path(context.launch['evidenceRoot'], directory=True) /
                                     (prefix + '-installation-original.json'))
        admission_pin = pin_file(lab_path(context.provision['signerSocketPath'], exists=False).parent /
                                 (admission_original['sha256'] + '.signed.json'))
        admission = signed_payload(admission_pin, context.authority_pin)
        require(decode(pinned_bytes(admission_original)) == admission and
                self.admissions.get(payload['sequence']) == canonical(admission) and
                all(admission[k] == payload[k] for k in ('collectionId', 'sequence', 'phase',
                    'operationRequestPin', 'serviceBindingPin')) and
                utc(admission['finishedAt']) <= start and utc(payload['expiresAt']) <= utc(admission['expiresAt']),
                'NATIVE_A_PHASE_ADMISSION_REQUIRED')
        pins += [admission_pin] + self.admit_installation(admission)
        require(pins == payload['originalPins'] and utc(payload['probeStartedAt']) == start and
                utc(payload['probeFinishedAt']) == end and utc(context.launch['issuedAt']) <= start < end <=
                utc(payload['issuedAt']) <= datetime.now(timezone.utc) < utc(payload['expiresAt']) <= utc(context.expires_at),
                'NATIVE_A_OBSERVATION_ORIGINALS')
        identity_record = signed_payload(payload['identityProofPin'], context.authority_pin)
        require(utc(payload['expiresAt']) <= utc(identity_record['expiresAt']) and
                identity_record['probeRuntimeProofPin'] == context.proof_pin, 'NATIVE_A_OBSERVATION_CURRENT_PROOF')
        for index, call_pin in enumerate(identity_record['invocationPins']):
            call = decode(pinned_bytes(call_pin))
            require(call['commandId'] == f'{prefix}-{index}', 'NATIVE_A_OBSERVATION_COMMAND_INTERVAL')
            context.admit_process(signed_payload(call['processResultPin'], context.authority_pin))
        encoded = canonical(payload); sequence = payload['sequence']
        if sequence not in self.pending:
            self.order.reserve({k: payload[k] for k in ('rehearsalId', 'collectionId', 'sequence', 'phase',
                'operationRequestPin', 'serviceBindingPin')} | {'schemaVersion': 'RepositoryLabNativeObserveRequest/v1',
                'issuedAt': payload['issuedAt'], 'deadlineMilliseconds': context.request['deadlineMilliseconds']})
            self.pending[sequence] = encoded
        else:
            require(self.pending[sequence] == encoded, 'NATIVE_A_OBSERVATION_REPLACED')
        for pin in pins:
            require(pin['path'] not in self.graph or self.graph[pin['path']] == pin, 'NATIVE_A_CONFLICTING_ORIGINAL')
            self.graph[pin['path']] = pin
        require(len(self.graph) + 2 * len(self.pending) <= 4096, 'NATIVE_A_OBSERVATION_GRAPH_LIMIT')


class CapHeader(ctypes.Structure):
    _fields_ = [('version', ctypes.c_uint32), ('pid', ctypes.c_int)]


class CapData(ctypes.Structure):
    _fields_ = [('effective', ctypes.c_uint32), ('permitted', ctypes.c_uint32), ('inheritable', ctypes.c_uint32)]


def drop_capabilities(uid, gid, retained):
    os.setgroups([])
    for cap in range(64):
        if retained & (1 << cap): continue
        result = libc.prctl(24, cap, 0, 0, 0)  # PR_CAPBSET_DROP
        require(result == 0 or ctypes.get_errno() == errno.EINVAL, 'NATIVE_CAP_BOUND_DROP_FAILED')
    native_call('prctl', 8, 1, 0, 0, 0)  # KEEP_CAPS for separately selected A UID
    os.setresgid(gid, gid, gid); os.setresuid(uid, uid, uid)
    header = CapHeader(0x20080522, 0); data = (CapData * 2)()
    data[0].effective = data[0].permitted = retained
    native_call('capset', ctypes.byref(header), ctypes.byref(data))
    native_call('prctl', 38, 1, 0, 0, 0)  # no_new_privileges
    native_call('prctl', 4, 0, 0, 0, 0)  # nondumpable: worker has no ptrace authority


def measure_worker_key_denial(context, signer_pid, *, until):
    """Independent sole parent enters exact current worker root, with zero caps.

    Tests only opening, never reads a key or memory byte. Any successful open,
    missing worker identity, unproven wait or timeout rejects signing.
    """
    selected = context.producer_identity
    match_process(selected, selected['pid'], selected['uid'])
    values = status(selected['pid'])
    require(all(int(values[k], 16) == 0 for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
            int(values.get('CapAmb', '0'), 16) == 0 and values['NoNewPrivs'] == '1' and not values['Groups'].split(),
            'NATIVE_WORKER_KEY_DENIAL_CAPABILITIES')
    require(os.readlink(f'/proc/{signer_pid}/ns/mnt') != selected['mountNamespace'],
            'NATIVE_A_WORKER_MOUNT_NOT_SEPARATE')
    require(os.statvfs(f'/proc/{selected["pid"]}/root').f_flag & os.ST_RDONLY,
            'NATIVE_WORKER_ROOT_NOT_READONLY')
    for path in (context.provision['signerSocketPath'],):
        exposed = Path(f'/proc/{selected["pid"]}/root') / str(Path(path).parent).lstrip('/')
        require(os.statvfs(exposed).f_flag & os.ST_RDONLY, 'NATIVE_WORKER_A_OUTPUT_NOT_READONLY')
    root_fd = os.open(f'/proc/{selected["pid"]}/root', os.O_RDONLY | os.O_DIRECTORY)
    namespace = os.open(f'/proc/{selected["pid"]}/ns/mnt', os.O_RDONLY)
    read_fd, write_fd = os.pipe(); gate_read, gate_write = os.pipe(); child = os.fork()
    if child == 0:
        try:
            os.close(read_fd); native_call('setns', namespace, 0)
            os.fchdir(root_fd); os.chroot('.'); os.chdir('/')
            # Never inherit the private A key, signing socket, or command FD.
            keep = sorted((write_fd, gate_read)); start = 3
            for fd in keep:
                os.closerange(start, fd); start = fd + 1
            os.closerange(start, os.sysconf('SC_OPEN_MAX'))
            drop_capabilities(selected['uid'], selected['gid'], 0)
            os.write(write_fd, b'R')
            require(os.read(gate_read, 1) == b'G', 'NATIVE_KEY_DENIAL_MEASUREMENT_NOT_SELECTED')
            source_pins = list(context.installation['filePins']) + list(context.installation['dependencyPins']) + [context.installation['pythonPin']]
            source_pins += [p for p in context.native_tool_pins if p['path'] in {a[0] for a in context.commands}]
            source_pins = list({p['path']: p for p in source_pins}.values())
            measured_sources = []
            for pin in source_pins:
                require(0 < pin['bytes'] <= 268435456, 'NATIVE_MEASURED_SOURCE_LIMIT')
                parent_fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    for part in Path(pin['path']).parts[1:-1]:
                        following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                        os.close(parent_fd); parent_fd = following
                    fd = os.open(Path(pin['path']).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
                    try:
                        info = os.fstat(fd)
                        require(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1 and
                                not info.st_mode & 0o022 and os.fstatvfs(fd).f_flag & os.ST_RDONLY,
                                'NATIVE_WORKER_MEASURED_SOURCE_CUSTODY')
                        sha = hashlib.sha256(); count = 0
                        while True:
                            require(time.monotonic() < until, 'NATIVE_SOURCE_MEASUREMENT_DEADLINE')
                            chunk = os.read(fd, 1048576)
                            if not chunk: break
                            count += len(chunk); require(count <= pin['bytes'], 'NATIVE_SOURCE_MEASUREMENT_SIZE'); sha.update(chunk)
                        reopened = os.open(Path(pin['path']).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
                        try: require(file_metadata(info) == file_metadata(os.fstat(fd)) == file_metadata(os.fstat(reopened)),
                                     'NATIVE_MEASURED_SOURCE_CHANGED')
                        finally: os.close(reopened)
                        require(count == pin['bytes'] and sha.hexdigest() == pin['sha256'], 'NATIVE_SOURCE_ORIGINAL_CHANGED')
                        measured_sources.append(pin)
                    finally: os.close(fd)
                finally: os.close(parent_fd)
            probes = [context.provision['privateKeyPin']['path'],
                f'/proc/{signer_pid}/root' + context.provision['privateKeyPin']['path'], f'/proc/{signer_pid}/mem']
            denied = []
            for path in probes:
                try: fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                except OSError as exc:
                    require(exc.errno in (errno.EACCES, errno.EPERM, errno.ENOENT), 'NATIVE_KEY_DENIAL_UNEXPECTED_ERROR')
                    denied.append({'path': path, 'errno': exc.errno})
                else:
                    os.close(fd); raise RuntimeError('NATIVE_WORKER_KEY_OPEN_SUCCEEDED')
            os.write(write_fd, canonical({'nativeRuntimeProofPin': context.proof_pin, 'worker': selected,
                'deniedOpens': denied, 'measuredSourcePins': measured_sources, 'measuredAt': utc_now()})); os._exit(0)
        except BaseException as error:
            print('NATIVE_KEY_DENIAL_PROBE_FAILED:' + getattr(error, 'code', type(error).__name__),
                  file=sys.stderr, flush=True)
            os._exit(1)
    os.close(write_fd); os.close(root_fd); os.close(namespace); os.close(gate_read)
    raw = bytearray(); terminal = None
    try:
        require(select.select([read_fd], [], [], max(0, until-time.monotonic()))[0] and os.read(read_fd, 1) == b'R',
                'NATIVE_KEY_DENIAL_PROBE_NOT_READY')
        actual = measure_process(child); capabilities = status(child)
        require(all(actual[k] == selected[k] for k in ('uid', 'gid', 'rootDevice', 'rootInode', 'mountNamespace')) and
                all(int(capabilities[k], 16) == 0 for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
                capabilities['NoNewPrivs'] == '1', 'NATIVE_KEY_DENIAL_WRONG_CONTEXT')
        os.write(gate_write, b'G')
        while terminal is None:
            require(time.monotonic() < until, 'NATIVE_KEY_DENIAL_DEADLINE')
            if select.select([read_fd], [], [], min(.05, until-time.monotonic()))[0]:
                part = os.read(read_fd, 65536); raw.extend(part)
                require(len(raw) <= 65536, 'NATIVE_KEY_DENIAL_FRAME_LIMIT')
            pid, wait = os.waitpid(child, os.WNOHANG)
            if pid: terminal = wait
        require(os.WIFEXITED(terminal) and os.WEXITSTATUS(terminal) == 0, 'NATIVE_WORKER_KEY_DENIAL_FAILED')
        result = decode(bytes(raw)); require(result['nativeRuntimeProofPin'] == context.proof_pin and
                len(result['deniedOpens']) == 3, 'NATIVE_KEY_DENIAL_ORIGINAL_INVALID')
        result.update(probeIdentity=actual, probeCapabilities={k: capabilities[k] for k in
            ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'NoNewPrivs')}, actualWaitStatus=terminal,
            soleParentPid=os.getpid())
        match_process(selected, selected['pid'], selected['uid'])
        return result
    finally:
        os.close(read_fd); os.close(gate_write)
        if terminal is None:
            # Sole-parent PID is held until this wait; no reuse/name/group kill.
            os.kill(child, signal.SIGKILL); os.waitpid(child, 0)


def broker_guard(channel, context):
    send_frame(channel, {'schemaVersion': 'RepositoryLabNativeGuardIntent/v1', 'nativeRuntimeProofPin': context.proof_pin}, context.deadline)
    result = receive_frame(channel, context.deadline)
    require(result['schemaVersion'] == 'RepositoryLabNativeGuardMeasured/v1' and
            result['nativeRuntimeProofPin'] == context.proof_pin and result['workerKeyDenial']['nativeRuntimeProofPin'] == context.proof_pin,
            'NATIVE_INDEPENDENT_GUARD_UNMEASURED')
    require(decode(pinned_bytes(result['measurementPin'])) == result['workerKeyDenial'],
            'NATIVE_GUARD_ORIGINAL_CHANGED')
    if type(context) is NativeQualificationContext:
        context.graph_pins = selected_graph_pins([context.graph_pins, result['measurementPin'],
                                                result['workerKeyDenial']])
    return result


def selected_producer_process(context, authority_identity_pin):
    require(os.getuid() == os.getgid() == 0, 'NATIVE_PRODUCER_ROOT_CUSTODY_REQUIRED')
    match_process(context.producer_identity, os.getpid(), os.getuid())
    peer = signed_payload(authority_identity_pin, context.authority_pin)
    exact(peer, CALLER_FIELDS, 'NATIVE_A_IDENTITY_SHAPE')
    require(peer['schemaVersion'] == 'RepositoryLabNativeAuthority/v1' and peer['rehearsalId'] == REHEARSAL_ID and
            peer['nativeRuntimeProofPin'] == context.proof_pin and utc(peer['issuedAt']) <= datetime.now(timezone.utc) <
            utc(peer['expiresAt']), 'NATIVE_A_CURRENT_IDENTITY')
    require(peer['uid'] == context.provision['signerUid'] and peer['gid'] == context.provision['signerGid'],
            'NATIVE_A_SELECTED_UID')
    def key_guard(uid, proof):
        context.guard(); require(uid == 0 and proof == context.proof_pin, 'NATIVE_WORKER_CURRENT_PROOF')
        path = lab_path(context.provision['signerSocketPath'], exists=False)
        socket_identity = signer_socket_custody(path)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.settimeout(min(5, context.deadline-time.monotonic())); channel.connect(str(path))
            actual_pid, actual_uid, actual_gid = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            require(actual_pid == peer['pid'] and actual_uid == peer['uid'] and actual_gid == peer['gid'] and
                    identity(actual_pid)['startTicks'] == peer['startTicks'], 'NATIVE_A_SOCKET_PEER_CHANGED')
            signer_socket_custody(path, socket_identity)
            channel.sendall(canonical({'guardRuntimeProofPin': proof}) + b'\n')
            raw = bytearray()
            while not raw.endswith(b'\n'):
                require(time.monotonic() < context.deadline, 'NATIVE_A_GUARD_DEADLINE')
                part = channel.recv(4096); require(part and len(raw)+len(part)<=65536, 'NATIVE_A_GUARD_REPLY_LIMIT')
                raw.extend(part)
            result = decode(bytes(raw)); exact(result, {'measurementPin', 'signer'}, 'NATIVE_A_GUARD_REPLY')
            measurement = decode(pinned_bytes(result['measurementPin']))
            require(measurement['nativeRuntimeProofPin'] == proof and measurement['worker'] == context.producer_identity and
                    len(measurement['deniedOpens']) == 3 and
                    all(result['signer'][k] == peer[k] for k in ('pid', 'startTicks', 'uid', 'gid', 'mountNamespace', 'rootDevice', 'rootInode')),
                    'NATIVE_A_PHYSICAL_DENIAL_UNBOUND')
        signer_socket_custody(path, socket_identity)
        return True
    signer = IndependentAuthoritySigner(context.provision['signerSocketPath'], peer['pid'], peer['startTicks'],
        peer['uid'], context.authority_pin, context.guard, key_guard,
        peer_gid=peer['gid'], runtime_selector=context.signing_runtime)
    process = NativeProcessProducer(evidence_root=context.launch['evidenceRoot'], installation_pin=context.launch['installationPin'],
        authority_pin=context.authority_pin, signer=signer, authority_guard=context.guard,
        dispatch_guard=context.dispatch_guard, worker_uid=0, worker_gid=0, deadline=context.deadline)
    return peer, signer, process


def producer_entry(context, authority_identity_pin):
    require(type(context) is NativeLaunchContext, "NATIVE_BUSINESS_CONTEXT_REQUIRED")
    peer, signer, process = selected_producer_process(context, authority_identity_pin)
    source = next((p for p in context.installation['filePins'] if p['path'].endswith('/recovery_native_service_identity.py')), None)
    require(source is not None, 'NATIVE_IDENTITY_SOURCE_NOT_INSTALLED')
    producer = NativeServiceIdentityProducer(process_producer=process, record_reader=context.reader,
        target_lease_guard=context.guard, probe_source_pin=source, machine_id_path='/etc/machine-id',
        maximum_age_milliseconds=context.provision['maximumAgeMilliseconds'])
    NativeObservationService(context=context, producer=producer,
        maximum_observations=context.provision['maximumObservations']).serve()
    finish_authority(context, peer)


def qualification_producer_entry(context, authority_identity_pin):
    require(type(context) is NativeQualificationContext, 'NATIVE_QUALIFICATION_CONTEXT_REQUIRED')
    peer, signer, process = selected_producer_process(context, authority_identity_pin)
    calls = []; state = 'SUCCEEDED'
    for selected in context.selections:
        try:
            reference = process.run_qualification(command_id=selected['commandId'], argv=selected['argv'],
                cwd=selected['cwd'], source_pins=selected['sourcePins'], binding=context.binding)
        except EnvironmentFailure as error:
            require(not error.unknown and error.result is not None, 'NATIVE_QUALIFICATION_TERMINAL_UNPROVEN')
            reference = error.result
            actual = signed_payload(reference, context.authority_pin)
            context.admit_process(actual)
            require(actual['terminationKind'] != 'EXITED' or actual['actualExitCode'] != 0,
                    'NATIVE_QUALIFICATION_FAILURE_ORIGINAL_REQUIRED')
            calls.append(reference); state = 'FAILED'; break
        calls.append(reference)
    context.guard()
    payload = dict(schemaVersion=QUALIFICATION_RESULT_SCHEMA, rehearsalId=REHEARSAL_ID,
        **{k: context.intent[k] for k in ('qualificationId', 'operationId', 'phase')},
        qualificationIntentPin=context.launch['qualificationIntentPin'], launchPin=context.launch_pin,
        provisionPin=context.provision_pin, authorityIdentityPin=authority_identity_pin,
        invocationPins=calls, state=state, issuedAt=utc_now(), expiresAt=context.expires_at)
    exact(payload, QUALIFICATION_RESULT_FIELDS, 'NATIVE_QUALIFICATION_RESULT_SHAPE')
    original = persist_bytes(lab_path(context.launch['evidenceRoot'], directory=True) /
                             'qualification-original.json', canonical(payload))
    signed = signer.sign(original, deadline=context.deadline, worker_uid=0)
    finish_authority(context, peer)
    print(canonical({'qualificationResultPin': signed}).decode('ascii'), flush=True)
    require(state == 'SUCCEEDED', 'NATIVE_QUALIFICATION_FAILED_RETAINED')


def finish_authority(context, peer):
    context.guard()
    socket_identity = signer_socket_custody(context.provision['signerSocketPath'])
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
        channel.settimeout(min(5, context.deadline-time.monotonic())); channel.connect(context.provision['signerSocketPath'])
        actual = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        require(actual == (peer['pid'], peer['uid'], peer['gid']) and identity(actual[0])['startTicks'] == peer['startTicks'],
                'NATIVE_A_FINISH_PEER_CHANGED')
        signer_socket_custody(context.provision['signerSocketPath'], socket_identity)
        channel.sendall(canonical({'finishLaunchPin': context.launch_pin}) + b'\n')
        raw = bytearray()
        while not raw.endswith(b'\n'):
            require(time.monotonic() < context.deadline, 'NATIVE_A_FINISH_DEADLINE')
            part=channel.recv(4096); require(part and len(raw)+len(part)<=16384, 'NATIVE_A_FINISH_REPLY_LIMIT');raw.extend(part)
        require(decode(bytes(raw)) == {'finishedLaunchPin': context.launch_pin}, 'NATIVE_A_FINISH_UNCONFIRMED')
    signer_socket_custody(context.provision['signerSocketPath'], socket_identity)


def serve_authority(context, service, child_channel):
    """Publish the unchanged parent handoff only at the server readiness barrier."""
    current_identity = service.publish_current_identity(context.proof_pin, context.expires_at)
    def on_ready():
        send_frame(child_channel, {'schemaVersion': 'RepositoryLabNativeAuthorityReady/v1',
            'authorityIdentityPin': current_identity}, context.deadline)
    service.serve(4096, on_ready=on_ready)


def authority_entry(context):
    require(type(context) is NativeLaunchContext, "NATIVE_BUSINESS_CONTEXT_REQUIRED")
    return selected_authority_entry(context)


def qualification_authority_entry(context):
    require(type(context) is NativeQualificationContext, "NATIVE_QUALIFICATION_CONTEXT_REQUIRED")
    return selected_authority_entry(context)


def selected_authority_entry(context):
    require(sys.platform == 'linux' and os.geteuid() == 0 and
            identity(os.getppid())['pid'] != context.producer_identity['pid'], 'NATIVE_INDEPENDENT_A_PARENT_REQUIRED')
    require(os.readlink('/proc/self/ns/mnt') != context.producer_identity['mountNamespace'],
            'NATIVE_INDEPENDENT_A_ROOT_REQUIRED')
    native_call('prctl', 36, 1, 0, 0, 0)  # this dedicated parent is the subreaper
    root = lab_path(context.provision['signerRootPath'], directory=True)
    require(root.stat().st_uid == 0 and not root.stat().st_mode & 0o022, 'NATIVE_A_ROOT_CUSTODY')
    readonly_pins = context.static_pins + [context.launch_pin, context.provision_pin, context.authority_pin,
        context.launch['installationPin'], context.proof_pin, context.installation['nativeRuntimeTrustPin'],
        context.launch['allowedCallerPin'], context.provision['producerIdentityPin'],
        context.launch['authorizationPin'], context.launch['leasePin'], *context.reader_pins.values()]
    if type(context) is NativeQualificationContext:
        readonly_pins = [p for p in context.graph_pins if p != context.provision['privateKeyPin']]
    for p in readonly_pins:
        if LAB_ROOT in Path(p['path']).parents:
            original = root / p['path'].lstrip('/')
            metadata = original.lstat()
            require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0 and
                    os.statvfs(original).f_flag & os.ST_RDONLY, 'NATIVE_A_INPUT_MOUNT_NOT_READONLY')
    private_key = root / context.provision['privateKeyPin']['path'].lstrip('/')
    metadata = private_key.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and metadata.st_uid == context.provision['signerUid'] and
            stat.S_IMODE(metadata.st_mode) == 0o400, 'NATIVE_A_PRIVATE_PROVISION_KEY_CUSTODY')
    parent, child_channel = socket.socketpair(); child = os.fork()
    if child == 0:
        try:
            parent.close(); native_call('unshare', 0x20000)
            native_call('mount', None, b'/', None, (1 << 18) | 16384, None)  # private recursively
            os.chroot(root); os.chdir('/')
            drop_capabilities(context.provision['signerUid'], context.provision['signerGid'], 3)
            from recovery_native_signer import AuthoritySigningService
            def guard():
                context.guard(); return broker_guard(child_channel, context)
            qualification = type(context) is NativeQualificationContext
            observation_admission = (AuthorityQualificationAdmission(context) if qualification else
                                     AuthorityObservationAdmission(context))
            def admit(payload):
                context.signing_runtime(payload)
                if qualification:
                    observation_admission.admit(payload)
                    return
                if payload['schemaVersion'] == 'RecoveryNativeProcessResult/v1':
                    context.admit_process(payload)
                elif payload['schemaVersion'] == 'RecoveryNativeServiceIdentity/v1':
                    require(payload['probeRuntimeProofPin'] == context.proof_pin and
                            any(all(payload[k] == context.reader(p)[k] for k in
                                ('targetIdentityPin', 'sourceScopePin', 'environmentConfigPin', 'resourcesProofPin',
                                 'applicationStartPin', 'role', 'endpointUrl', 'dockerPin'))
                                for p in context.provision['serviceBindingPins']), 'NATIVE_A_SERVICE_SELECTION')
                elif payload['schemaVersion'] == ADMISSION_SCHEMA:
                    observation_admission.admit_installation(payload)
                else:
                    observation_admission.admit(payload)
            service = AuthoritySigningService(socket_path=context.provision['signerSocketPath'],
                private_key_pin=context.provision['privateKeyPin'], authority_key_pin=context.authority_pin,
                original_root=context.launch['evidenceRoot'], producer_pid=context.producer_identity['pid'],
                producer_start_ticks=context.producer_identity['startTicks'], producer_uid=0,
                guard=guard, admit=admit, deadline=context.deadline)
            service.launch_pin = context.launch_pin
            serve_authority(context, service, child_channel); os._exit(0)
        except BaseException as error:
            print('NATIVE_AUTHORITY_CHILD_FAILED:' + getattr(error, 'code', type(error).__name__),
                  file=sys.stderr, flush=True)
            os._exit(1)
    child_channel.close(); waited = None; child_identity = identity(child)
    launch_started = utc_now(); failure = None
    try:
        while waited is None:
            pid, terminal = os.waitpid(child, os.WNOHANG)
            if pid:
                waited = terminal; break
            context.guard()
            if select.select([parent], [], [], .05)[0]:
                request = receive_frame(parent, context.deadline)
                if request.get('schemaVersion') == 'RepositoryLabNativeAuthorityReady/v1':
                    exact(request, {'schemaVersion', 'authorityIdentityPin'}, 'NATIVE_A_READY_SHAPE')
                    payload = signed_payload(request['authorityIdentityPin'], context.authority_pin)
                    actual = measure_process(child)
                    child_identity = actual
                    require(payload['schemaVersion'] == 'RepositoryLabNativeAuthority/v1' and
                            all(payload[k] == actual[k] for k in
                                ('pid', 'startTicks', 'uid', 'gid', 'hostId', 'bootId', 'rootDevice', 'rootInode', *NS_FIELDS)),
                            'NATIVE_A_READY_IDENTITY_UNMEASURED')
                    print(canonical(request).decode('ascii'), flush=True)
                    continue
                exact(request, {'schemaVersion', 'nativeRuntimeProofPin'}, 'NATIVE_A_GUARD_INTENT')
                require(request['schemaVersion'] == 'RepositoryLabNativeGuardIntent/v1' and
                        request['nativeRuntimeProofPin'] == context.proof_pin, 'NATIVE_A_GUARD_RUNTIME')
                measured = measure_worker_key_denial(context, child, until=min(context.deadline, time.monotonic()+5))
                reference = persist_bytes(lab_path(context.launch['evidenceRoot'], directory=True) /
                    ('key-denial-' + str(time.monotonic_ns()) + '.json'), canonical(measured))
                send_frame(parent, {'schemaVersion': 'RepositoryLabNativeGuardMeasured/v1',
                    'nativeRuntimeProofPin': context.proof_pin, 'workerKeyDenial': measured,
                    'measurementPin': reference, 'signer': measure_process(child)}, context.deadline)
            pid, terminal = os.waitpid(child, os.WNOHANG)
            if pid: waited = terminal
        require(os.WIFEXITED(waited) and os.WEXITSTATUS(waited) == 0, 'NATIVE_A_CHILD_NOT_SUCCEEDED')
    except BaseException as error:
        failure = getattr(error, 'code', 'NATIVE_AUTHORITY_PARENT_FAILED')
        raise
    finally:
        parent.close()
        if waited is None:
            os.kill(child, signal.SIGKILL); _, waited = os.waitpid(child, 0)
        persist_bytes(lab_path(context.launch['evidenceRoot'], directory=True) /
            ('authority-parent-terminal-' + str(time.monotonic_ns()) + '.json'), canonical({
                'schemaVersion': 'RepositoryLabNativeAuthorityParentTerminal/v1', 'launchPin': context.launch_pin,
                'parentIdentity': measure_process(os.getpid()), 'ownedChildIdentity': child_identity,
                'actualWaitStatus': waited, 'reaped': True, 'failureCode': failure,
                'startedAt': launch_started, 'finishedAt': utc_now()}))


def admit_installation_entry(installation_pin, authority_pin):
    """Only the actual EXECUTOR may execute W03 self-admission in this process."""
    require(sys.platform == 'linux' and os.getuid() == os.getgid() == 0 and not os.getgroups(),
            'NATIVE_ADMISSION_EXECUTOR_ROLE_REQUIRED')
    capabilities = status(os.getpid())
    require(all(int(capabilities[k], 16) == 0 for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb')) and
            capabilities['NoNewPrivs'] == '1', 'NATIVE_ADMISSION_EXECUTOR_CAPABILITIES')
    # This required absolute budget is set only by the owned native parent.
    # Its watchdog also cancels/reaps the child at the earlier current deadline.
    selected_deadline = float(os.environ['INTRUOYI_NATIVE_DEADLINE_MONOTONIC'])
    require(math.isfinite(selected_deadline) and time.monotonic() < selected_deadline,
            'NATIVE_ADMISSION_CURRENT_DEADLINE_REQUIRED')
    deadline = min(selected_deadline, time.monotonic() + 60)
    import repository_native_runtime as native
    expected = signed_payload(installation_pin, authority_pin)
    require(expected['schemaVersion'] == 'RepositoryNativeInstallation/v2' and
            expected['pythonPin']['path'] == str(Path(sys.executable)) and
            any(p['path'] == str(Path(__file__).resolve()) for p in expected['filePins']),
            'NATIVE_ADMISSION_INSTALLED_ENTRY_REQUIRED')
    helper, = [p for p in expected['filePins'] if p['path'] == str(Path(native.__file__).resolve())]
    pinned_bytes(helper)
    actual = native.verify_native_installation(installation_pin, [authority_pin], deadline=deadline)
    require(actual == expected and signed_payload(actual['nativeRuntimeTrustPin'], authority_pin)['runtimeRole'] == 'EXECUTOR' and
            time.monotonic() < deadline, 'NATIVE_ADMISSION_VERIFIED_EXECUTOR_REQUIRED')
    from recovery_native_observation import wire_canonical
    sys.stdout.buffer.write(wire_canonical(actual)); sys.stdout.buffer.flush()


def qualify_owned_process_entry():
    """Finite installed worker: emit actual identity and zero-cap measurements only."""
    require(sys.platform == 'linux' and os.getuid() == os.getgid() == 0 and not os.getgroups(),
            'NATIVE_QUALIFICATION_WORKER_IDENTITY')
    deadline = float(os.environ['INTRUOYI_NATIVE_DEADLINE_MONOTONIC'])
    require(math.isfinite(deadline) and time.monotonic() < deadline, 'NATIVE_QUALIFICATION_WORKER_DEADLINE')
    caps = status(os.getpid())
    require(all(int(caps[k], 16) == 0 for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb')) and
            caps['NoNewPrivs'] == '1', 'NATIVE_QUALIFICATION_WORKER_CAPABILITIES')
    sys.stdout.buffer.write(canonical({'identity': measure_process(os.getpid()), 'groups': os.getgroups(),
        'capabilities': {k: caps[k] for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb', 'NoNewPrivs')}}))
    sys.stdout.buffer.flush()


def main():
    parser = argparse.ArgumentParser()
    roles = parser.add_subparsers(dest='role', required=True)
    for role in ('authority', 'producer', 'qualification-authority', 'qualification-producer'):
        selected = roles.add_parser(role)
        for name in ('launch', 'authority', 'provision'): selected.add_argument('--' + name + '-pin', required=True)
        if role in ('producer', 'qualification-producer'): selected.add_argument('--authority-identity-pin', required=True)
    for role in ('browser-producer', 'browser-authority'):
        selected = roles.add_parser(role)
        for name in ('launch', 'authority', 'provision'): selected.add_argument('--' + name + '-pin', required=True)
        selected.add_argument('--deadline-monotonic', type=float, required=True)
        if role == 'browser-producer':
            selected.add_argument('--authority-identity-pin', required=True)
            selected.add_argument('--sandbox-broker-fd', type=int)
        else:
            selected.add_argument('--broker-fd', type=int, required=True)
    roles.add_parser('qualify-owned-process')
    selected = roles.add_parser('admit-installation')
    selected.add_argument('--installation-pin', required=True); selected.add_argument('--authority-pin', required=True)
    args = parser.parse_args()
    if args.role in ('browser-producer', 'browser-authority'):
        from recovery_native_browser import (BrowserQualificationContext, BrowserAuthorityService,
            BrowserSandboxObserver, qualification_entry)
        from recovery_native_observation import wire_canonical
        import math
        require(math.isfinite(args.deadline_monotonic) and 0 < args.deadline_monotonic-time.monotonic() <= 300,
                'BROWSER_EXPLICIT_FINITE_DEADLINE_REQUIRED')
        def selected_pin(value):
            decoded = decode(value.encode())
            require(wire_canonical(decoded).decode() == value, 'BROWSER_CANONICAL_PIN_REQUIRED')
            return decoded
        context = BrowserQualificationContext(selected_pin(args.launch_pin), selected_pin(args.provision_pin),
            selected_pin(args.authority_pin), deadline=args.deadline_monotonic)
        if args.role == 'browser-authority':
            require(args.broker_fd >= 3, 'BROWSER_PRIVATE_BROKER_FD_REQUIRED')
            with socket.socket(fileno=args.broker_fd) as broker:
                BrowserAuthorityService(context, broker).serve(lambda ready: print(wire_canonical(ready).decode(), flush=True))
        else:
            if args.sandbox_broker_fd is None:
                result = qualification_entry(context, selected_pin(args.authority_identity_pin))
            else:
                require(args.sandbox_broker_fd >= 3, 'BROWSER_PRIVATE_SANDBOX_BROKER_FD_REQUIRED')
                with socket.socket(fileno=args.sandbox_broker_fd) as observer_channel:
                    observer = BrowserSandboxObserver(context, observer_channel)
                    result = qualification_entry(context, selected_pin(args.authority_identity_pin), sandbox_observer=observer)
            print(wire_canonical(result).decode(), flush=True)
        return
    if args.role == 'qualify-owned-process':
        qualify_owned_process_entry(); return
    if args.role == 'admit-installation':
        from recovery_native_observation import wire_canonical
        installation_pin = decode(args.installation_pin.encode()); authority_pin = decode(args.authority_pin.encode())
        require(wire_canonical(installation_pin).decode() == args.installation_pin and
                wire_canonical(authority_pin).decode() == args.authority_pin, 'NATIVE_ADMISSION_CANONICAL_PIN_REQUIRED')
        admit_installation_entry(installation_pin, authority_pin)
        return
    context_type = NativeQualificationContext if args.role.startswith('qualification-') else NativeLaunchContext
    context = context_type(decode(args.launch_pin.encode()), decode(args.authority_pin.encode()),
        decode(args.provision_pin.encode()), verify_runtime=args.role in ('producer', 'qualification-producer'))
    if args.role == 'authority': authority_entry(context)
    elif args.role == 'qualification-authority': qualification_authority_entry(context)
    else:
        require(args.authority_identity_pin is not None, 'NATIVE_SEPARATE_A_IDENTITY_REQUIRED')
        entry = qualification_producer_entry if args.role == 'qualification-producer' else producer_entry
        entry(context, decode(args.authority_identity_pin.encode()))


if __name__ == '__main__':
    main()
