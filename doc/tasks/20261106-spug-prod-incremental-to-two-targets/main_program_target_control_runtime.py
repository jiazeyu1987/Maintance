"""Read-only transition from one retained target controller to its successor.

Candidate construction/staging and the service change belong to the caller.
No historical receipt is converted into evidence for the successor. Both old
and new observations use the original RuntimeGates implementation.
"""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re

from main_program_control_runtime import RuntimeGates, canonical, need


_BINDING = ('role', 'service', 'engine', 'controlConfigurationPin',
            'ownerConfigurationPin', 'sourceCommit', 'fileCount',
            'fileManifestSha256', 'dropinPin')
_BASELINE_ONLY = ('environmentSha256', 'systemdEnvironmentSha256',
                  'systemdEnvironmentRaw', 'declaredEnvironment')


def _pin(value):
    need(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'} and
         type(value['bytes']) is int and value['bytes'] > 0 and
         type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
         'TARGET_RUNTIME_PIN_INVALID')
    name = value['path']
    need(type(name) is str and PurePosixPath(name).is_absolute() and
         str(PurePosixPath(name)) == name and '..' not in PurePosixPath(name).parts and
         not any(ord(char) < 32 or char == '\\' for char in name), 'TARGET_RUNTIME_PATH_INVALID')
    return value


class RetainedHistoryRuntimeGates(RuntimeGates):
    """A successor runtime whose history is read under the explicit old spec."""
    def __init__(self, spec, *, retained_gates, **boundaries):
        need(isinstance(retained_gates, RuntimeGates), 'TARGET_RUNTIME_RETAINED_GATE_REQUIRED')
        super().__init__(spec, **boundaries)
        self.retained_gates = retained_gates

    def retained_custody(self):
        return self.retained_gates.retained_custody()

    def original_inventory(self, custody_observation):
        return self.retained_gates.original_inventory(custody_observation)


class TargetControlRuntimeTransition:
    """Keep an actual before observation, then check a caller-observed new PID."""
    def __init__(self, original_spec, *, candidate, dropin_pin, added_dependencies=None,
                 verify_environment, verify_custody, lock_guard,
                 run=None, pin=None, read=None, paths=None):
        self.original = RuntimeGates(original_spec, verify_environment=verify_environment,
            verify_custody=verify_custody, lock_guard=lock_guard, run=run, pin=pin, read=read, paths=paths)
        self.candidate = deepcopy(candidate)
        self.dropin = deepcopy(_pin(dropin_pin))
        self._before = None
        self._new_package_pin = None
        self._boundaries = dict(verify_environment=verify_environment, verify_custody=verify_custody,
            lock_guard=lock_guard, run=self.original.run, pin=self.original.pin,
            read=self.original.read, paths=self.original.paths)
        self._validate(added_dependencies)

    def _validate(self, added):
        spec, candidate = self.original.spec, self.candidate
        need(type(candidate) is dict and candidate.get('schemaVersion') == 'MainProgramTargetControlCandidate/v1'
             and candidate.get('status') == 'BOUND_NOT_INSTALLED' and
             candidate.get('retainedSourceConfigurationUnchanged') is True and
             candidate.get('installationPerformed') is False and candidate.get('restoreDispatched') is False,
             'TARGET_RUNTIME_CANDIDATE_INVALID')
        host = candidate.get('host')
        need(host in ('172.30.30.57', '172.30.30.58', '172.30.30.59') and
             spec['current']['host'] == host and spec['current']['suffix'] == host.rsplit('.', 1)[1] and
             candidate.get('targetConfigRef') == spec['targetConfigRef'], 'TARGET_RUNTIME_SCOPE_CHANGED')
        rows = spec['current']['controllers']
        expected = ['source', 'target'] if host.endswith('.57') else ['target']
        need(type(rows) is list and [row['role'] for row in rows] == expected and
             len({row['service'] for row in rows}) == len(rows) and
             len({row['pid'] for row in rows}) == len(rows), 'TARGET_RUNTIME_CONTROLLER_SET')
        self.index = len(rows) - 1
        self.old = deepcopy(rows[self.index])
        previous, new = candidate['previousController'], candidate['controller']
        need(previous.get('schemaVersion') == 'MainProgramControlActivation/v1' and
             previous.get('status') == 'PASS' and previous.get('host') == host and
             previous.get('targetConfigRef') == spec['targetConfigRef'] and
             all(previous[key] == self.old[key] for key in _BINDING), 'TARGET_RUNTIME_PREVIOUS_BINDING_CHANGED')
        need(type(new) is dict and set(new) == {'role', 'service', 'engine', 'previousControlPin',
             'previousOwnerPin', 'controlPin', 'ownerPin'} and new['role'] == 'target' and
             new['service'] == self.old['service'] and new['previousControlPin'] == self.old['controlConfigurationPin'] and
             new['previousOwnerPin'] == self.old['ownerConfigurationPin'], 'TARGET_RUNTIME_SUCCESSOR_BINDING_CHANGED')
        commit = candidate.get('sourceCommit')
        need(type(commit) is str and re.fullmatch('[0-9a-f]{40}', commit) and
             new['engine'] == str(PurePosixPath(self.old['engine']).parent / ('engine-main-program-' + commit[:7])) and
             new['engine'] != self.old['engine'], 'TARGET_RUNTIME_ENGINE_CHANGED')
        for key in ('controlPin', 'ownerPin'):
            _pin(new[key])
        package = candidate['package']
        need(self.old['fileCount'] == 147 and package.get('fileCount') == 153 and
             type(package.get('fileManifestSha256')) is str and
             re.fullmatch('[0-9a-f]{64}', package['fileManifestSha256']), 'TARGET_RUNTIME_PACKAGE_SCOPE')
        docs = candidate['newDocuments']
        need(type(docs) is list and len(docs) == 16, 'TARGET_RUNTIME_DOCUMENT_SET')
        seen = set()
        for row in docs:
            need(type(row) is dict and set(row) == {'pin', 'value'}, 'TARGET_RUNTIME_DOCUMENT_INVALID')
            reference = _pin(row['pin']); raw = canonical(row['value'])
            need(reference['path'] not in seen and len(raw) == reference['bytes'] and
                 hashlib.sha256(raw).hexdigest() == reference['sha256'], 'TARGET_RUNTIME_DOCUMENT_PIN')
            seen.add(reference['path'])
        need(sum(row['pin'] == new['controlPin'] for row in docs) == 1 and
             sum(row['pin'] == new['ownerPin'] for row in docs) == 1 and
             not {self.old['controlConfigurationPin']['path'], self.old['ownerConfigurationPin']['path']} & seen,
             'TARGET_RUNTIME_CONFIGURATION_COLLISION')
        units = [row for row in spec['unit']['controllers'] if row['service'] == self.old['service']]
        need(len(units) == 1, 'TARGET_RUNTIME_UNIT_BINDING')
        self.old_unit = deepcopy(units[0])
        original_names = list(self.old_unit['existingNames'])
        original_refs = list(self.old_unit['dropinPins'])
        if self.old['dropinPin'] not in original_refs:
            need(all(ref['path'] != self.old['dropinPin']['path'] for ref in original_refs),
                 'TARGET_RUNTIME_ORIGINAL_DROPIN_CONFLICT')
            original_refs.append(deepcopy(self.old['dropinPin']))
            name = PurePosixPath(self.old['dropinPin']['path']).name
            need(name not in original_names, 'TARGET_RUNTIME_ORIGINAL_DROPIN_CONFLICT')
            original_names.append(name)
        self.retained_dropins, self.retained_names = original_refs, original_names
        location = PurePosixPath(self.dropin['path'])
        need(str(location.parent) == self.old_unit['directory'] and location.name.endswith('.conf') and
             location.name not in original_names and all(location.name > name for name in original_names) and
             self.dropin['path'] not in {ref['path'] for ref in original_refs}, 'TARGET_RUNTIME_NEW_DROPIN_INVALID')
        dependency = 'spug-main-preservation-view-' + host.rsplit('.', 1)[1] + '-20261111-r1.service'
        if added is None:
            added = dict(Requires=[], After=[])
        need(type(added) is dict and set(added) == {'Requires', 'After'} and
             all(type(values) is list and (values == [] or values == [dependency]) for values in added.values()) and
             added['Requires'] == added['After'], 'TARGET_RUNTIME_DEPENDENCY_INVALID')
        self.dependencies = deepcopy(added)
        baseline = spec.get('environmentBaseline')
        if baseline is not None:
            matches = [row for row in baseline['controllers'] if row['service'] == self.old['service']]
            need(len(matches) == 1, 'TARGET_RUNTIME_ENVIRONMENT_BASELINE_MISSING')
            self.retained_environment = deepcopy(matches[0])
        else:
            self.retained_environment = None
        self.retained_row_environment = {key:deepcopy(self.old[key]) for key in _BASELINE_ONLY if key in self.old}

    def _documents(self):
        for row in self.candidate['newDocuments']:
            need(self.original.read(row['pin']) == row['value'], 'TARGET_RUNTIME_CANDIDATE_DOCUMENT_CHANGED')
        old_control = self.original.read(self.old['controlConfigurationPin'])
        self.original.read(self.old['ownerConfigurationPin'])
        new_control = self.original.read(self.candidate['controller']['controlPin'])
        need(old_control['pythonPin'] == new_control['pythonPin'] and
             old_control['workingDirectory'] == new_control['workingDirectory'],
             'TARGET_RUNTIME_EXECUTION_SCOPE_CHANGED')

    def _row(self, pid):
        need(type(pid) is int and pid > 0 and pid not in
             {row['pid'] for row in self.original.spec['current']['controllers']}, 'TARGET_RUNTIME_PID_INVALID')
        row = deepcopy(self.old); new = self.candidate['controller']
        row.update(engine=new['engine'], pid=pid, controlConfigurationPin=deepcopy(new['controlPin']),
            ownerConfigurationPin=deepcopy(new['ownerPin']), sourceCommit=self.candidate['sourceCommit'],
            fileCount=153, fileManifestSha256=self.candidate['package']['fileManifestSha256'],
            dropinPin=deepcopy(self.dropin), environmentMode='CONFIG_EXACT')
        row.pop('argvSha256', None)
        # These known fields described the old captured process, not a fresh
        # successor. Their exact original values remain in the retained spec and
        # explicit result context. Unknown row fields are never dropped.
        for key in _BASELINE_ONLY:
            row.pop(key, None)
        return row

    def _successor(self, pid):
        spec = deepcopy(self.original.spec)
        spec['current']['controllers'][self.index] = self._row(pid)
        unit = next(row for row in spec['unit']['controllers'] if row['service'] == self.old['service'])
        unit['dropinPins'] = deepcopy(self.retained_dropins)
        unit['existingNames'] = deepcopy(self.retained_names)
        return RetainedHistoryRuntimeGates(spec, retained_gates=self.original, **self._boundaries)

    def before(self):
        self.original.lock_guard()
        need(self._before is None, 'TARGET_RUNTIME_BASELINE_ALREADY_CAPTURED')
        need(not self.original.paths.exists(self.dropin['path']), 'TARGET_RUNTIME_NEW_DROPIN_ALREADY_EXISTS')
        before = self.original._observe(documents_created=True)
        self._documents()
        package_row = dict(engine=self.candidate['controller']['engine'], fileCount=153,
                           fileManifestSha256=self.candidate['package']['fileManifestSha256'])
        self._new_package_pin = self.original.verify_package(package_row)
        need(not self.original.paths.exists(self.dropin['path']), 'TARGET_RUNTIME_NEW_DROPIN_ALREADY_EXISTS')
        self.original.lock_guard()
        self._before = deepcopy(before)
        return before

    def _no_retired_workers(self, rows):
        allowed = {row['pid'] for row in rows}
        roots = {self.original.read(row['controlConfigurationPin'])['workingDirectory']
                 for row in self.original.spec['current']['controllers']}
        retired_entry = str(Path(self.old['engine']) / 'control_entry.py').encode()
        for pid in self.original.paths.process_ids():
            try:
                args = self.original.paths.process_bytes(pid, 'cmdline').rstrip(b'\0').split(b'\0')
            except (FileNotFoundError, ProcessLookupError):
                continue
            if retired_entry in args or any(root.encode() in arg for root in roots for arg in args):
                need(pid in allowed and retired_entry not in args and
                     any(arg.replace(b'\\', b'/').endswith(b'/control_entry.py') for arg in args),
                     'TARGET_RUNTIME_RETIRED_PROCESS_OR_WORKER')

    def _compare(self, before, after, pid):
        need(set(before) == set(after), 'TARGET_RUNTIME_OBSERVATION_SHAPE_CHANGED')
        need({k:v for k,v in before.items() if k not in ('controllers', 'packagePins')} ==
             {k:v for k,v in after.items() if k not in ('controllers', 'packagePins')},
             'TARGET_RUNTIME_PROTECTED_OBSERVATION_CHANGED')
        need(len(before['controllers']) == len(after['controllers']) ==
             len(before['packagePins']) == len(after['packagePins']) == len(self.original.spec['current']['controllers']),
             'TARGET_RUNTIME_OBSERVATION_COUNT_CHANGED')
        for index, (old, new) in enumerate(zip(before['controllers'], after['controllers'])):
            if index != self.index:
                need(old == new and before['packagePins'][index] == after['packagePins'][index],
                     'TARGET_RUNTIME_PEER_CHANGED')
                continue
            need(set(old) == set(new) and old['service'] == new['service'] == self.old['service'] and
                 new['pid'] == pid and old['executable'] == new['executable'] and
                 new['environmentVerification']['mode'] == 'CONFIG_EXACT', 'TARGET_RUNTIME_SUCCESSOR_OBSERVATION_CHANGED')
            changing = {'pid', 'argvSha256', 'environmentVerification', 'properties'}
            need({k:v for k,v in old.items() if k not in changing} ==
                 {k:v for k,v in new.items() if k not in changing}, 'TARGET_RUNTIME_UNKNOWN_OBSERVATION_CHANGED')
            props, current = old['properties'], new['properties']
            need(set(props) == set(current), 'TARGET_RUNTIME_PROPERTY_SET_CHANGED')
            need({k:v for k,v in props.items() if k not in ('MainPID', 'DropInPaths', 'Requires', 'After')} ==
                 {k:v for k,v in current.items() if k not in ('MainPID', 'DropInPaths', 'Requires', 'After')},
                 'TARGET_RUNTIME_PROPERTY_CHANGED')
            need(current['MainPID'] == str(pid) and current['DropInPaths'].split() ==
                 [*props['DropInPaths'].split(), self.dropin['path']], 'TARGET_RUNTIME_DROPIN_TRANSITION_CHANGED')
            for key in ('Requires', 'After'):
                tokens = current[key].split()
                need(len(tokens) == len(set(tokens)) and set(tokens) ==
                     set(props[key].split()) | set(self.dependencies[key]), 'TARGET_RUNTIME_DEPENDENCY_CHANGED')
            need(after['packagePins'][index] == self._new_package_pin, 'TARGET_RUNTIME_NEW_PACKAGE_CHANGED')

    def after(self, before, *, successor_pid):
        self.original.lock_guard()
        need(self._before is not None and before == self._before, 'TARGET_RUNTIME_ACTUAL_BASELINE_REQUIRED')
        successor = self._successor(successor_pid)
        need(self.original.pin(self.dropin['path']) == self.dropin, 'TARGET_RUNTIME_NEW_DROPIN_CHANGED')
        self._documents()
        need(self.original.verify_package(self.old) == before['packagePins'][self.index],
             'TARGET_RUNTIME_OLD_PACKAGE_CHANGED')
        self._no_retired_workers(successor.spec['current']['controllers'])
        after = successor._observe(documents_created=True)
        self._compare(before, after, successor_pid)
        self._no_retired_workers(successor.spec['current']['controllers'])
        self.original.lock_guard()
        return dict(schemaVersion='MainProgramTargetRuntimeTransition/v1', status='TARGET_SUCCESSOR_RUNTIME_VERIFIED',
            host=self.candidate['host'], targetConfigRef=self.original.spec['targetConfigRef'],
            service=self.old['service'], successorController=deepcopy(successor.spec['current']['controllers'][self.index]),
            before=deepcopy(before), after=after, retainedEnvironmentBaseline=deepcopy(self.retained_environment),
            retainedRowEnvironment=deepcopy(self.retained_row_environment),
            retainedHistoryUsesOriginalSpec=True, serverWrites=False,
            installationReceiptCreated=False, restoreDispatched=False)
