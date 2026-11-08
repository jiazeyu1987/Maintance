"""Operation-private MAIN execution views and retained native evidence.

This module neither dispatches commands nor installs/releases write protection.
An execution view is usable only while the original physical lock, immutable
metadata lease, shared budget and this operation's REPLACING epoch remain valid.
Terminal evidence recording is intentionally independent of execution admission:
a timeout or lost lock must never discard an already dispatched command's exit.
"""
from copy import deepcopy
import os
from pathlib import Path
import re

from recovery_archive_guard import ArchivePathGuard
from recovery_backup_epoch import _assert_lock, _read_file
from recovery_engine import Budget, RecoveryError, absolute, require
from recovery_program_execution import _directory, resolve_execution_configuration
from recovery_program_generation import document


class _NativeView:
    def __init__(self, context, phase, configuration, evidence):
        self._context = context
        self._phase = phase
        self._configuration = deepcopy(configuration)
        self._evidence = deepcopy(evidence)

    @property
    def phase(self):
        return self._phase

    @property
    def budget(self):
        return self._context.budget

    @property
    def configuration(self):
        return deepcopy(self._configuration)

    @property
    def evidence(self):
        return deepcopy(self._evidence)

    def guard(self):
        self._context._view_guard(self)

    def validate_inputs(self, configuration, request, target):
        """Bind the complete constructor inputs before any target access."""
        self.guard()
        require(configuration == self._configuration, 'PROGRAM_NATIVE_CONFIGURATION_CHANGED')
        require(request == self._context._request, 'PROGRAM_NATIVE_REQUEST_CHANGED')
        require(target == self._configuration['targets'][self._context._request['targetConfigRef']],
                'PROGRAM_NATIVE_TARGET_CHANGED')

    def guard_native(self, native):
        """Check the executing object's fields, not only this view's snapshot."""
        self.guard()
        require(native.original == self._context._request, 'PROGRAM_NATIVE_REQUEST_CHANGED')
        require(native.config == self._configuration['targets'][self._context._request['targetConfigRef']],
                'PROGRAM_NATIVE_TARGET_CHANGED')
        require(native.budget is self.budget, 'PROGRAM_NATIVE_BUDGET_CHANGED')


class MainNativeExecutionContext:
    def __init__(self, owner, request, operation_root, *, binding_pin, lock_fd,
                 budget, guard=None):
        require(isinstance(budget, Budget), 'PROGRAM_NATIVE_SHARED_BUDGET_REQUIRED')
        require(guard is None or callable(guard), 'PROGRAM_NATIVE_GUARD_INVALID')
        self._owner, self._request = deepcopy(owner), deepcopy(request)
        self._root = absolute(str(operation_root))
        self._binding = deepcopy(binding_pin)
        self._lock_fd, self._budget, self._outer_guard = lock_fd, budget, guard
        self._leases, self._references, self._directories = [], {}, {}
        self._closed = False
        self._phase, self._generation = 'PREPARATION', None
        self._views, self._invocations, self._invocation_paths = [], [], set()
        self._policy = None
        try:
            self._check()
            # The resolver proves all original inputs, reservation and the
            # actual READY prefix. No native target access occurs here.
            effective, evidence = self._resolve()
            require(evidence['epoch']['state'] == 'REPLACING' and
                    evidence['epoch']['operationId'] == self._request['operationId'],
                    'PROGRAM_NATIVE_REPLACING_REQUIRED')
            self._policy = deepcopy(self._owner['targetProgramPolicies'][self._request['targetConfigRef']])
            self._claim = Path(self._binding['path']).parent
            self._epoch = deepcopy(evidence['epoch'])
            self._directories = {path: _directory(path, 'PROGRAM_NATIVE_DIRECTORY_CHANGED')
                                 for path in (self._root, self._claim)}
            self._configuration, self._evidence = self._lease_and_resolve(effective, evidence)
        except BaseException:
            self.close()
            raise

    @property
    def budget(self):
        return self._budget

    @property
    def phase(self):
        return self._phase

    @property
    def generation_pin(self):
        return deepcopy(self._generation)

    def _check(self):
        require(not self._closed, 'PROGRAM_NATIVE_CLOSED')
        self._budget.remaining()
        if self._outer_guard is not None:
            self._outer_guard()
        for lease in self._leases:
            lease.check()
        if self._policy is not None:
            _assert_lock(self._policy['backupEpochPolicy'], self._lock_fd)
        for path, identity in self._directories.items():
            require(_directory(path, 'PROGRAM_NATIVE_DIRECTORY_CHANGED') == identity,
                    'PROGRAM_NATIVE_DIRECTORY_CHANGED')
        for lease in self._leases:
            lease.check()
        self._budget.remaining()

    def _resolve(self, generation=None, runtime=False):
        return resolve_execution_configuration(self._owner, self._request, self._root,
            binding_pin=self._binding, generation_pin=generation, lock_fd=self._lock_fd,
            guard=self._check, runtime=runtime)

    def _lease_and_resolve(self, expected, evidence, *, generation=None, runtime=False):
        """Watch new evidence before the authoritative second full validation.

        Existing leases stay alive across stage; only newly proven paths gain
        another watch set. This avoids hashing history on every SQL stream chunk
        without treating an old successful resolution as perpetual authority.
        """
        import recovery_resource_admission as admission
        self._check()
        _, active = _read_file(admission.HOST_ROOT/'active.json', 4*1024*1024)
        references = [*evidence['evidencePins'], active]
        additions = {}
        for reference in references:
            key = reference['path']
            require(key not in self._references or self._references[key] == reference,
                    'PROGRAM_NATIVE_METADATA_CHANGED')
            require(key not in additions or additions[key] == reference,
                    'PROGRAM_NATIVE_METADATA_CHANGED')
            if key not in self._references:
                additions[key] = deepcopy(reference)
        lease = None
        try:
            if additions:
                closed = (self._policy['backupEpochPolicy']['root'],) if not self._leases else ()
                lease = ArchivePathGuard.capture(additions, closed_directories=closed)
                self._leases.append(lease)
            actual, proof = self._resolve(generation, runtime)
            require(actual == expected and proof == evidence and proof['epoch'] == self._epoch,
                    'PROGRAM_NATIVE_METADATA_CHANGED')
            # Include the host's durable reservation, not just the operation's
            # local reservation copy. The resolver independently verifies both.
            for reference in additions.values():
                document(reference)
                self._check()
            self._references.update(additions)
            return actual, proof
        except BaseException:
            if lease is not None:
                self._leases.remove(lease)
                lease.close()
            raise

    def _view_guard(self, view):
        require(type(view) is _NativeView and view in self._views and view._context is self,
                'PROGRAM_NATIVE_VIEW_INVALID')
        self._check()
        require(view.phase == self._phase, 'PROGRAM_NATIVE_PHASE_CHANGED')
        if self._phase == 'PREPARATION':
            require(not os.path.lexists(self._claim/'generation.json'), 'PROGRAM_NATIVE_STAGE_REQUIRED')
        else:
            require(view._evidence['generationPin'] == self._generation,
                    'PROGRAM_NATIVE_GENERATION_CHANGED')

    def preparation(self, configuration):
        self._check()
        require(self._phase == 'PREPARATION', 'PROGRAM_NATIVE_PHASE_CHANGED')
        require(not os.path.lexists(self._claim/'generation.json'), 'PROGRAM_NATIVE_STAGE_REQUIRED')
        require(configuration == self._configuration, 'PROGRAM_NATIVE_CONFIGURATION_CHANGED')
        view = _NativeView(self, 'PREPARATION', self._configuration, self._evidence)
        self._views.append(view)
        view.guard()
        return view

    def stage(self, generation_pin):
        self._check()
        require(self._phase == 'PREPARATION', 'PROGRAM_NATIVE_STAGE_ALREADY_BOUND')
        require(all(row['terminalPin'] is not None for row in self._invocations),
                'PROGRAM_NATIVE_INVOCATION_PENDING')
        require(all(row['terminalObservation']['state'] == 'SUCCEEDED' for row in self._invocations),
                'PROGRAM_NATIVE_INVOCATION_NOT_SUCCEEDED')
        require(generation_pin is not None, 'PROGRAM_NATIVE_STAGE_REQUIRED')
        generation = deepcopy(generation_pin)
        effective, evidence = self._resolve(generation)
        effective, evidence = self._lease_and_resolve(effective, evidence, generation=generation)
        # Publish the in-process transition only after all new evidence is
        # watched and independently revalidated under the old continuous lease.
        self._generation = generation
        self._configuration, self._evidence = effective, evidence
        self._phase = 'RESTORE'

    def restore(self, configuration):
        self._check()
        require(self._phase == 'RESTORE', 'PROGRAM_NATIVE_STAGE_REQUIRED')
        effective, evidence = self._resolve(self._generation, runtime=True)
        require(configuration == effective, 'PROGRAM_NATIVE_CONFIGURATION_CHANGED')
        effective, evidence = self._lease_and_resolve(effective, evidence,
            generation=self._generation, runtime=True)
        runtime = self._claim/'runtime'
        identity = _directory(runtime, 'PROGRAM_NATIVE_DIRECTORY_CHANGED')
        require(runtime not in self._directories or self._directories[runtime] == identity,
                'PROGRAM_NATIVE_DIRECTORY_CHANGED')
        self._directories[runtime] = identity
        view = _NativeView(self, 'RESTORE', effective, evidence)
        self._views.append(view)
        view.guard()
        return view

    def _evidence_path(self, reference):
        path = absolute(reference['path'])
        require((path != self._root and self._root in path.parents) or
                (path != self._claim and self._claim in path.parents),
                'PROGRAM_NATIVE_EVIDENCE_PATH_INVALID')
        return path

    def begin_invocation(self, view, intent_pin):
        self._view_guard(view)
        require(all(row['terminalPin'] is not None and
                    row['terminalObservation']['state'] != 'TERMINAL_UNKNOWN' for row in self._invocations),
                'PROGRAM_NATIVE_INVOCATION_UNSETTLED')
        path = self._evidence_path(intent_pin)
        require(path not in self._invocation_paths, 'PROGRAM_NATIVE_EVIDENCE_DUPLICATE')
        value = document(intent_pin)
        require(type(value) is dict and value.get('schemaVersion') == 'RecoveryDataInvocation/v1' and
                value.get('operationId') == self._request['operationId'] and
                value.get('action') == self._request['action'] and
                type(value.get('argvSha256')) is str and re.fullmatch('[0-9a-f]{64}', value['argvSha256']) and
                type(value.get('mutation')) is bool and type(value.get('startedAt')) is str and value['startedAt'] and
                value.get('finishedAt') is None and value.get('actualExitCode') is None and
                value.get('state') == 'TERMINAL_UNKNOWN', 'PROGRAM_NATIVE_EVIDENCE_INTENT_INVALID')
        self._view_guard(view)
        token = len(self._invocations)
        self._invocations.append(dict(sequence=token, phase=view.phase,
            intentObservation=deepcopy(value), intentPinAtDispatch=deepcopy(intent_pin), terminalPin=None))
        self._invocation_paths.add(path)
        return token

    def finish_invocation(self, token, terminal_pin):
        """Record only: no execution guard, mutation, release, or retry authority."""
        require(type(token) is int and 0 <= token < len(self._invocations),
                'PROGRAM_NATIVE_EVIDENCE_TOKEN_INVALID')
        row = self._invocations[token]
        require(row['terminalPin'] is None, 'PROGRAM_NATIVE_EVIDENCE_ALREADY_FINISHED')
        self._evidence_path(terminal_pin)
        require(terminal_pin['path'] == row['intentPinAtDispatch']['path'],
                'PROGRAM_NATIVE_EVIDENCE_PATH_INVALID')
        value = document(terminal_pin)
        identity = ('schemaVersion', 'operationId', 'action', 'argvSha256', 'mutation', 'startedAt')
        require(type(value) is dict and all(type(value.get(key)) is type(row['intentObservation'][key]) and
                value.get(key) == row['intentObservation'][key] for key in identity),
                'PROGRAM_NATIVE_EVIDENCE_IDENTITY_INVALID')
        code, state = value.get('actualExitCode'), value.get('state')
        require(type(value.get('finishedAt')) is str and value['finishedAt'] and
                (code is None or type(code) is int) and
                state in ('SUCCEEDED', 'FAILED_RETAINED', 'TERMINAL_UNKNOWN') and
                (state != 'SUCCEEDED' or code == 0) and
                (state != 'FAILED_RETAINED' or type(code) is int), 'PROGRAM_NATIVE_EVIDENCE_TERMINAL_INVALID')
        row['terminalPin'] = deepcopy(terminal_pin)
        row['terminalObservation'] = deepcopy(value)

    def snapshot(self):
        """Read evidence even after timeout/close; never authorize another command."""
        pins = []
        for row in self._invocations:
            if row['terminalPin'] is not None:
                require(document(row['terminalPin']) == row['terminalObservation'],
                        'PROGRAM_NATIVE_EVIDENCE_CHANGED')
                pins.append(deepcopy(row['terminalPin']))
        last = self._invocations[-1].get('terminalObservation', {}) if self._invocations else {}
        return dict(schemaVersion='MainNativeExecutionEvidence/v1', operationId=self._request['operationId'],
            bindingPin=deepcopy(self._binding), generationPin=deepcopy(self._generation), phase=self._phase,
            originalResultPins=pins, invocations=deepcopy(self._invocations),
            mutationDispatched=any(row['intentObservation']['mutation'] for row in self._invocations),
            terminalUnknown=any(row['terminalPin'] is None or
                row['terminalObservation']['state'] == 'TERMINAL_UNKNOWN' for row in self._invocations),
            lastExitCode=last.get('actualExitCode'))

    def close(self):
        self._closed = True
        leases, self._leases = self._leases, []
        failure = None
        for lease in reversed(leases):
            try:
                lease.close()
            except OSError as error:
                if failure is None:
                    failure = error
        if failure is not None:
            raise failure

    def __enter__(self):
        try:
            self._check()
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *_):
        self.close()
