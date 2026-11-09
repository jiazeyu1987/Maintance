"""Pinned, read-only control-unit and process-environment observations.

Preparation never dispatches. The explicit observe_* entries do dispatch the
read-only program, retain the private response and publish a strict projection.
This is observation, not a physical-lock or installation-success certificate.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from main_program_control_runtime import RuntimeGates, RuntimePaths, canonical, need, pin_file, read_pinned


FALSE_FIELDS = ('serverFilesWritten', 'controlServicesReloaded', 'backupDispatched', 'restoreDispatched')
ENVIRONMENT_FIELDS = {'schemaVersion', 'status', 'host', 'observedAt', 'unitObservationPin',
    'controllers', *FALSE_FIELDS, 'revisionId', 'previousControlGenerationPin'}
ENVIRONMENT_ROW_FIELDS = {'service', 'pid', 'engine', 'controlConfigurationPin', 'ownerConfigurationPin',
    'argvSha256', 'unitPin', 'dropinPins', 'environmentSha256', 'systemdEnvironmentSha256',
    'systemdEnvironmentRaw', 'declaredEnvironment'}
UNIT_FIELDS = {'schemaVersion', 'status', 'host', 'observedAt', 'controllers', 'requiredHistoryGuard',
    'historyGuardEnabledAndActive', 'historyGuardProperties', 'historyUnitPins',
    'allOriginalControlsAndBusinessUnchanged', 'fstabAndMountsUnchanged', 'containerCount',
    'fstabSha256', 'mountinfoSha256', 'originalWorkingDirectoriesHaveNoWorker',
    'sourceCommit', 'revisionId', 'previousControlGenerationPin', 'runtimeEvidence', *FALSE_FIELDS}
UNIT_ROW_FIELDS = {'service', 'pid', 'unitPin', 'dropinPins', 'properties', 'directory',
    'existingNames', 'nextDropinLeadingZCount', 'matchingControlPids'}


def now():
    return datetime.now(timezone.utc).isoformat()


class ObservationPaths(RuntimePaths):
    def unit_directory(self, service):
        need(type(service) is str and re.fullmatch('[A-Za-z0-9_.@:-]+\\.service', service), 'SERVICE_NAME_INVALID')
        return Path('/etc/systemd/system') / (service + '.d')


class ReadonlyObserver:
    """Complete discovery over the shared runtime gates, without write guards."""
    def __init__(self, gates, *, paths=None, parse_environment=None, deadline=None):
        need(isinstance(gates, RuntimeGates), 'TYPED_RUNTIME_REQUIRED')
        self.gates = gates
        self.paths = ObservationPaths() if paths is None else paths
        if parse_environment is None:
            from main_program_control_activation import parse_declared_environment
            parse_environment = parse_declared_environment
        self.parse_environment = parse_environment
        self.deadline = time.monotonic() + 600 if deadline is None else deadline

    def check(self):
        need(time.monotonic() < self.deadline, 'OBSERVATION_DEADLINE_EXCEEDED')

    def _small_pin(self, path):
        self.check(); ref = self.gates.pin(path)
        need(0 < ref['bytes'] <= 65536, 'UNIT_FILE_LIMIT')
        return ref

    def _unit(self, row):
        self.check(); props = self.gates.properties(row['service'])
        need(props['MainPID'] == str(row['pid']) and props['ActiveState'] == 'active' and
             props['LimitNOFILE'] == '65536', 'CONTROL_PROCESS_CHANGED')
        path = Path(props['FragmentPath'])
        need(path.name == row['service'], 'UNIT_NAME_CHANGED')
        directory = self.paths.unit_directory(row['service'])
        need(directory.is_dir() and not directory.is_symlink() and directory.resolve(strict=True) == directory,
             'DROPIN_DIRECTORY_ALIAS')
        names = sorted(p.name for p in directory.glob('*.conf'))
        need(names and all((directory / name).is_file() and not (directory / name).is_symlink()
             for name in names), 'DROPIN_SET_INVALID')
        drops = props['DropInPaths'].split()
        need(drops and len(drops) == len(set(drops)), 'LOADED_DROPIN_SET_INVALID')
        return dict(service=row['service'], pid=row['pid'], unitPin=self._small_pin(path),
            dropinPins=[self._small_pin(p) for p in drops], properties=props, directory=str(directory),
            existingNames=names, nextDropinLeadingZCount=max(len(n)-len(n.lstrip('z')) for n in names)+1,
            matchingControlPids=[row['pid']])

    def _environment(self, row, unit):
        self.check(); paths = self.gates.paths
        control = self.gates.read(row['controlConfigurationPin']); self.gates.read(row['ownerConfigurationPin'])
        args = paths.process_bytes(row['pid'], 'cmdline')
        environment = paths.process_bytes(row['pid'], 'environ')
        raw = self.gates.run(['systemctl', 'show', row['service'], '-p', 'Environment']).decode('utf-8')
        declared = self.parse_environment(raw)
        result = dict(**{key:row[key] for key in ('service', 'pid', 'engine', 'controlConfigurationPin', 'ownerConfigurationPin')},
            argvSha256=hashlib.sha256(args).hexdigest(), unitPin=unit['unitPin'], dropinPins=unit['dropinPins'],
            environmentSha256=hashlib.sha256(environment).hexdigest(),
            systemdEnvironmentSha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
            systemdEnvironmentRaw=raw, declaredEnvironment=declared)
        # Baseline discovery is never a substitute for the critical Python
        # contract or for systemd declarations actually present in /proc.
        self.gates.verify_environment(control['environment'], environment, baseline=result, systemd_raw=raw)
        need(paths.process_bytes(row['pid'], 'cmdline') == args and
             paths.process_bytes(row['pid'], 'environ') == environment, 'CONTROL_CHANGED_DURING_READ')
        return result

    def _runtime(self):
        self.check(); g = self.gates; rows = g.spec['current']['controllers']
        g.original_units(); g.no_workers(rows)
        controls = [g.verify_process(row) for row in rows]
        packages = [g.verify_package(row) for row in rows]
        guard = g.guard(); custody = g.retained_custody(); inventory = g.original_inventory(custody)
        for ref in g.spec['historyPins']:
            need(g.pin(ref['path']) == ref, 'HISTORICAL_METADATA_CHANGED')
        for ref in g.spec['sourceEvidencePins']:
            g.read(ref)
        for ref in g.spec['retainedDocuments']:
            need(g.pin(ref['path']) == ref, 'RETAINED_CONFIGURATION_CHANGED')
        self.check()
        return dict(controllers=controls, packagePins=packages, historyGuard=guard,
            previousCustodyObservation=custody, originalInventoryObservation=inventory)

    def _collect(self, expected_unit=None):
        self.check(); g = self.gates; paths = g.paths
        # Capture mounts before the first command; a command-side change cannot
        # be adopted as the baseline of this observation.
        fstab = g.pin(paths.fstab_path); mounts = paths.read_bytes(paths.mountinfo_path)
        containers = g.snapshot(); rows = g.spec['current']['controllers']
        need(rows and len({r['service'] for r in rows}) == len(rows) and
             len({r['pid'] for r in rows}) == len(rows), 'CONTROL_SET_INVALID')
        units = [self._unit(row) for row in rows]
        if expected_unit is not None:
            need(expected_unit['schemaVersion'] == 'MainControlUnitObservation/v1' and
                 expected_unit['status'] == 'PASS' and expected_unit['host'] == g.spec['current']['host'] and
                 all(expected_unit[k] == g.spec[k] for k in ('sourceCommit', 'revisionId', 'previousControlGenerationPin')) and
                 expected_unit['controllers'] == units and
                 expected_unit['requiredHistoryGuard'] == g.spec['unit']['requiredHistoryGuard'] and
                 expected_unit['historyUnitPins'] == g.spec['unit']['historyUnitPins'], 'UNIT_OBSERVATION_CHANGED')
        environments = [self._environment(row, unit) for row, unit in zip(rows, units)]
        if expected_unit is not None:
            observed = expected_unit['runtimeEvidence']['controllers']
            need(len(observed) == len(environments) and all(
                 (old['service'], old['pid'], old['argvSha256']) == (new['service'], new['pid'], new['argvSha256']) and
                 all(old['environmentVerification'][key] == new[key] for key in
                 ('environmentSha256', 'systemdEnvironmentSha256'))
                 for old, new in zip(observed, environments)), 'UNIT_ENVIRONMENT_BINDING_CHANGED')
        g.spec['unit']['controllers'] = deepcopy(units)
        g.spec['environmentBaseline'] = dict(controllers=deepcopy(environments))
        for row, baseline in zip(rows, environments):
            row.update(argvSha256=baseline['argvSha256'], environmentMode='ORIGINAL_BASELINE')
        before = self._runtime()
        need([self._unit(row) for row in rows] == units, 'UNIT_CHANGED_DURING_OBSERVATION')
        after = self._runtime()
        need(before == after and g.snapshot() == containers and g.pin(paths.fstab_path) == fstab and
             paths.read_bytes(paths.mountinfo_path) == mounts, 'ORIGINALS_CHANGED_DURING_OBSERVATION')
        self.check()
        return units, environments, dict(controllers=before['controllers'], packagePins=before['packagePins'],
            previousCustodyObservation=before['previousCustodyObservation'],
            originalInventoryObservation=before['originalInventoryObservation']), before['historyGuard'], containers, fstab, mounts

    def collect_units(self):
        units, environments, runtime, guard, containers, fstab, mounts = self._collect()
        spec = self.gates.spec
        return dict(schemaVersion='MainControlUnitObservation/v1', status='PASS',
            host=spec['current']['host'], observedAt=now(), controllers=units,
            requiredHistoryGuard=spec['unit']['requiredHistoryGuard'], historyGuardEnabledAndActive=True,
            historyGuardProperties=guard, historyUnitPins=deepcopy(spec['unit']['historyUnitPins']),
            allOriginalControlsAndBusinessUnchanged=True, fstabAndMountsUnchanged=True,
            containerCount=len(containers), fstabSha256=fstab['sha256'], mountinfoSha256=hashlib.sha256(mounts).hexdigest(),
            originalWorkingDirectoriesHaveNoWorker=True, serverFilesWritten=False, controlServicesReloaded=False,
            backupDispatched=False, restoreDispatched=False, runtimeEvidence=runtime,
            **{k:deepcopy(spec[k]) for k in ('sourceCommit', 'revisionId', 'previousControlGenerationPin')})

    def collect_environment(self, unit, unit_pin):
        units, environments, runtime, guard, containers, fstab, mounts = self._collect(unit)
        spec = self.gates.spec
        return dict(schemaVersion='MainControlEnvironmentBaseline/v1', status='PASS', host=spec['current']['host'],
            observedAt=now(), unitObservationPin=deepcopy(unit_pin), controllers=environments,
            serverFilesWritten=False, controlServicesReloaded=False, backupDispatched=False, restoreDispatched=False,
            **{k:deepcopy(spec[k]) for k in ('revisionId', 'previousControlGenerationPin')})


def project_environment(value, private_pin):
    need(type(value) is dict and set(value) == ENVIRONMENT_FIELDS and
         value['schemaVersion'] == 'MainControlEnvironmentBaseline/v1' and value['status'] == 'PASS' and
         all(value[k] is False for k in FALSE_FIELDS), 'ENVIRONMENT_PROJECTION_INVALID')
    rows = []
    for row in value['controllers']:
        need(type(row) is dict and set(row) == ENVIRONMENT_ROW_FIELDS, 'ENVIRONMENT_ROW_PROJECTION_INVALID')
        rows.append({k:deepcopy(v) for k,v in row.items() if k not in ('systemdEnvironmentRaw', 'declaredEnvironment')})
    return dict({k:deepcopy(v) for k,v in value.items() if k != 'controllers'},
        controllers=rows, privateSnapshotPin=deepcopy(private_pin))


def _projection_pin(reference):
    need(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'} and
         type(reference['path']) is str and type(reference['bytes']) is int and reference['bytes'] > 0 and
         type(reference['sha256']) is str and re.fullmatch('[0-9a-f]{64}', reference['sha256']), 'PIN_PROJECTION_INVALID')


def _runtime_projection(value):
    """Whitelist every public runtime field, including nested observations."""
    need(type(value) is dict and set(value) == {'controllers', 'packagePins', 'previousCustodyObservation',
         'originalInventoryObservation'}, 'RUNTIME_PROJECTION_INVALID')
    properties = {'MainPID', 'FragmentPath', 'DropInPaths', 'Requires', 'After', 'LimitNOFILE', 'ActiveState', 'SubState'}
    for row in value['controllers']:
        need(type(row) is dict and set(row) == {'service', 'pid', 'argvSha256', 'executable',
             'environmentVerification', 'properties'} and type(row['properties']) is dict and
             set(row['properties']) == properties and all(type(v) is str for v in row['properties'].values()),
             'RUNTIME_ROW_PROJECTION_INVALID')
        env = row['environmentVerification']
        need(type(env) is dict and set(env) == {'mode', 'environmentSha256', 'systemdEnvironmentSha256'} and
             env['mode'] == 'ORIGINAL_BASELINE' and all(type(env[k]) is str and re.fullmatch('[0-9a-f]{64}', env[k])
             for k in ('environmentSha256', 'systemdEnvironmentSha256')), 'RUNTIME_ENVIRONMENT_PROJECTION_INVALID')
    custody = value['previousCustodyObservation']
    if custody is not None:
        need(type(custody) is dict and set(custody) == {'status', 'activationCount', 'legacyActivationCount',
             'legacyLogicalTerminalPin', 'legacyPhysicalTerminalPin', 'selectedCurrentReceiptPin',
             'originalInventoryVerified', 'allReceiptAndConfigurationPinsVerified', 'packageManifestsVerified',
             'verifiedPins', 'serverWrites', 'packagePins'} and custody['status'] == 'PASS' and
             custody['serverWrites'] is False and all(custody[k] is True for k in
             ('originalInventoryVerified', 'allReceiptAndConfigurationPinsVerified', 'packageManifestsVerified')) and
             all(type(custody[k]) is int and custody[k] > 0 for k in ('activationCount', 'legacyActivationCount')),
             'RUNTIME_CUSTODY_PROJECTION_INVALID')
        for key in ('legacyLogicalTerminalPin', 'legacyPhysicalTerminalPin', 'selectedCurrentReceiptPin'):
            _projection_pin(custody[key])
        for reference in custody['verifiedPins'] + custody['packagePins']:
            _projection_pin(reference)
    inventory = value['originalInventoryObservation']
    need(type(inventory) is dict and set(inventory) == {'originalPathInventoryVerified', 'verifiedPins'} and
         inventory['originalPathInventoryVerified'] is True, 'RUNTIME_INVENTORY_PROJECTION_INVALID')
    for reference in value['packagePins'] + inventory['verifiedPins']:
        _projection_pin(reference)


def project_units(value, private_pin):
    need(type(value) is dict and set(value) == UNIT_FIELDS and value['schemaVersion'] == 'MainControlUnitObservation/v1' and
         value['status'] == 'PASS' and all(value[k] is False for k in FALSE_FIELDS) and
         all(value[k] is True for k in ('historyGuardEnabledAndActive', 'allOriginalControlsAndBusinessUnchanged',
         'fstabAndMountsUnchanged', 'originalWorkingDirectoriesHaveNoWorker')) and
         type(value['containerCount']) is int and value['containerCount'] > 0, 'UNIT_PROJECTION_INVALID')
    _runtime_projection(value['runtimeEvidence'])
    rows = []
    for row in value['controllers']:
        need(type(row) is dict and set(row) == UNIT_ROW_FIELDS, 'UNIT_ROW_PROJECTION_INVALID')
        rows.append({k:deepcopy(v) for k,v in row.items() if k != 'properties'})
    return dict({k:deepcopy(v) for k,v in value.items() if k not in ('controllers', 'historyGuardProperties')},
        controllers=rows, privateSnapshotPin=deepcopy(private_pin))


def _finish(context):
    for reference in context['inputPins']:
        need(pin_file(reference['path']) == reference, 'OBSERVATION_INPUT_CHANGED')


def prepare_observation(task, private, *, suffix, generation_pin, plan_pin, source_commit, revision_id):
    from main_program_control_generation import load_control_generation, select_control_generation
    from main_program_installation_selection import Records
    from main_program_control_activation import private_document
    task, private = Path(task).resolve(strict=True), Path(private).resolve(strict=True)
    need(suffix in ('57', '58', '59') and type(source_commit) is str and re.fullmatch('[0-9a-f]{40}', source_commit) and
         type(revision_id) is str and re.fullmatch('r[1-9][0-9]*', revision_id), 'OBSERVATION_IDENTITY_INVALID')
    bundle = load_control_generation(task, private, generation_pin)
    selection = select_control_generation(suffix, task, private, generation_pin=generation_pin)
    records = Records(task); plan = records.pinned(plan_pin)
    stem = source_commit[:7] + '-' + revision_id
    need(plan_pin['file'] == 'main-program-configuration-plan-' + stem + '.json' and
         plan['schemaVersion'] == 'MainProgramConfigurationPlan/v2' and
         plan['sourceCommit'] == source_commit and plan['revisionId'] == revision_id and
         plan['predecessorGenerationPin'] == generation_pin and
         plan['previousPlanPin'] == bundle['generation']['planPin'] and
         plan['status'] == 'PLAN_ONLY_NOT_ACTIVATED' and plan['installationPerformed'] is False,
         'OBSERVATION_PLAN_CHANGED')
    secret = private_document(private, plan['privatePlanPin'], 'main-program-configuration-plan-' + stem + '.private.json')
    need(secret['schemaVersion'] == 'MainProgramConfigurationInstallationPlan/v2' and
         all(secret[k] == plan[k] for k in ('sourceCommit', 'revisionId', 'predecessorGenerationPin',
         'previousPlanPin', 'buildPin', 'packageDeltaPin', 'archiveViewDependencies', 'status')) and
         secret['currentSelections'] == bundle['selections'], 'OBSERVATION_PRIVATE_PLAN_CHANGED')
    for host in ('57', '58', '59'):
        need([{k:r[k] for k in ('role', 'service', 'engine', 'controlPin', 'ownerPin')}
             for r in secret['controllers'][host]] == plan['controllers'][host], 'OBSERVATION_PLANNED_CONTROLS_CHANGED')
    dependency = plan['archiveViewDependencies'][suffix]
    guard = 'spug-history-prod57-readonly-' + suffix + '.service'
    need(dependency['requiredServices'] == [guard], 'OBSERVATION_HISTORY_DEPENDENCY_CHANGED')
    history = records.read('legacy-canonical-view-' + suffix +
        ('-installation-r1.json' if suffix == '59' else '-selfbind-installation-r1.json'))
    history_view = history['historyViewInstallation' if suffix == '59' else 'selfbindInstallation']
    need(history_view['unitPins'] == dependency['legacyUnitPins'], 'OBSERVATION_HISTORY_UNITS_CHANGED')
    inventory = records.read('protected-history-' + suffix + '.json') if suffix != '57' else None
    baseline = bundle['sourceBaseline']
    spec = dict(current={k:deepcopy(selection[k]) for k in ('host', 'suffix', 'controllers')},
        sourceCommit=source_commit, revisionId=revision_id, previousControlGenerationPin=deepcopy(generation_pin),
        unit=dict(requiredHistoryGuard=guard, historyUnitPins=deepcopy(dependency['legacyUnitPins'])),
        targetConfigRef=selection['targetConfigRef'], oldReceiptPin=selection['activeReceiptPin'],
        previousCustody=bundle['custodyByHost'].get(suffix), originalInventory=inventory,
        historyPins=[deepcopy(r['pin']) for r in secret['originalMetadata'] if r['originalHost'] == selection['host']],
        sourceEvidencePins=[deepcopy(baseline[k]) for k in ('pointPin', 'manifestPin', 'epochBindingPin')] if suffix == '57' else [],
        retainedDocuments=[deepcopy(r['pin']) for r in secret['retainedDocumentsByHost'][suffix]], newDocuments=[])
    pins = [*bundle['inputPins'], *records.path_pins(), plan['privatePlanPin']]
    pins += [pin_file(task / name) for name in ('main_program_control_observation.py', 'main_program_control_runtime.py',
        'main_program_control_activation.py', 'installation_history_custody.py')]
    unique = {}
    for reference in pins:
        reference = dict(reference, path=str(Path(reference['path'])))
        need(reference['path'] not in unique or unique[reference['path']] == reference, 'OBSERVATION_INPUT_CONFLICT')
        unique[reference['path']] = reference
    context = dict(task=str(task), private=str(private), selection=selection, spec=spec,
        generationPin=deepcopy(generation_pin), planPin=deepcopy(plan_pin), sourceCommit=source_commit,
        revisionId=revision_id, readOnly=True, unitFile='main-program-control-units-' + suffix + '-' + stem + '.json',
        environmentFile='main-program-control-environment-baseline-' + suffix + '-' + stem + '.json',
        inputPins=list(unique.values()))
    _finish(context)
    return context


REMOTE_ENTRY = r'''
import shlex,types,sys,traceback
deadline=time.monotonic()+600
def readonly_run(args,timeout=90,env=None):
 need(time.monotonic()<deadline,'OBSERVATION_DEADLINE_EXCEEDED')
 valid=(len(args)>=3 and args[:2] in (['systemctl','show'],['systemctl','is-enabled'])) or (
  args[:3]==['/usr/bin/docker','--host','unix:///var/run/docker.sock'] and
  ((args[3:]==['ps','-aq','--no-trunc']) or (len(args)>4 and args[3]=='inspect')))
 need(valid,'READ_ONLY_COMMAND_REQUIRED')
 return run_command(args,timeout=min(timeout,max(.001,deadline-time.monotonic())),env=env)
def no_lock_claim():
 raise ValueError('OBSERVATION_IS_NOT_A_LOCK_CERTIFICATE')
gates=RuntimeGates(SPEC,run=readonly_run,verify_environment=verify_environment_values,
 verify_custody=verify_layered_receipt_custody,lock_guard=no_lock_claim)
observer=ReadonlyObserver(gates,parse_environment=parse_declared_environment,deadline=deadline)
value=observer.collect_units() if MODE=='units' else observer.collect_environment(UNIT,UNIT_PIN)
print(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False))
'''


def build_remote_program(context, mode, *, unit=None, unit_pin=None):
    need(mode in ('units', 'environment') and (mode == 'units' or type(unit) is dict and type(unit_pin) is dict),
         'OBSERVATION_MODE_INVALID')
    _finish(context)
    from main_program_control_activation import ENVIRONMENT_PROGRAM
    from installation_history_custody import SCRIPT
    task = Path(__file__).resolve().parent
    sources = {name:(task / (name + '.py')).read_text(encoding='utf-8') for name in
        ('main_program_control_runtime', 'main_program_control_observation')}
    # Only these new formal modules are loaded in memory. No installation
    # carrier, executable file or server-side source file is created/rewritten.
    payload = 'import types,sys,hashlib,json,re,shlex,time\n'
    for name, source in sources.items():
        payload += '_module=types.ModuleType(' + repr(name) + ')\nsys.modules[' + repr(name) + ']=_module\n'
        payload += 'exec(compile(' + repr(source) + ',' + repr('<' + name + '>') + ',"exec"),_module.__dict__)\n'
    payload += 'from main_program_control_runtime import *\nfrom main_program_control_observation import *\n'
    payload += ENVIRONMENT_PROGRAM + '\n' + SCRIPT + '\n'
    payload += 'SPEC=' + repr(context['spec']) + '\nMODE=' + repr(mode) + '\nUNIT=' + repr(unit) + '\nUNIT_PIN=' + repr(unit_pin) + '\n'
    payload += REMOTE_ENTRY
    compile(payload, '<main-control-readonly-observation>', 'exec')
    _finish(context)
    return payload


def _write_exclusive(path, value):
    raw = canonical(value)
    need(path.parent.resolve(strict=True) == path.parent and not os.path.lexists(path), 'OBSERVATION_OUTPUT_EXISTS')
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    except FileExistsError as error:
        raise ValueError('OBSERVATION_OUTPUT_EXISTS') from error
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    need(path.read_bytes() == raw, 'OBSERVATION_OUTPUT_CHANGED')
    return pin_file(path)


def _observe(context, mode, *, transport=None, unit=None, unit_pin=None):
    name = context['unitFile' if mode == 'units' else 'environmentFile']
    public_path = Path(context['task']) / name
    private_path = Path(context['private']) / (name[:-5] + '.private.json')
    need(not os.path.lexists(public_path) and not os.path.lexists(private_path), 'OBSERVATION_OUTPUT_EXISTS')
    _finish(context); payload = build_remote_program(context, mode, unit=unit, unit_pin=unit_pin)
    if transport is None:
        from common import remote
        transport = remote
    value = transport(context['selection']['host'], payload, timeout=660)
    # Retain the complete private response even when a later validation fails.
    need(type(value) is dict, 'OBSERVATION_RESPONSE_INVALID')
    private_pin = _write_exclusive(private_path, value)
    _finish(context)
    need(value['host'] == context['selection']['host'] and
         all(value[k] == context['spec'][k] for k in ('revisionId', 'previousControlGenerationPin')),
         'OBSERVATION_RESPONSE_BINDING_CHANGED')
    if mode == 'units':
        need(value['sourceCommit'] == context['sourceCommit'] and
             [(r['service'], r['pid']) for r in value['controllers']] ==
             [(r['service'], r['pid']) for r in context['selection']['controllers']], 'OBSERVATION_RESPONSE_CONTROLS_CHANGED')
        projected = project_units(value, private_pin)
    else:
        need(value['unitObservationPin'] == unit_pin, 'OBSERVATION_UNIT_BINDING_CHANGED')
        keys = ('service', 'pid', 'engine', 'controlConfigurationPin', 'ownerConfigurationPin')
        need([{k:r[k] for k in keys} for r in value['controllers']] ==
             [{k:r[k] for k in keys} for r in context['selection']['controllers']] and
             all(row['unitPin'] == fixed['unitPin'] and row['dropinPins'] == fixed['dropinPins']
             for row, fixed in zip(value['controllers'], unit['controllers'])), 'OBSERVATION_RESPONSE_CONTROLS_CHANGED')
        projected = project_environment(value, private_pin)
    public_pin = _write_exclusive(public_path, projected)
    _finish(context)
    return dict(status='PASS', observationPin={k:public_pin[k] for k in ('bytes', 'sha256')} | {'file':name},
        privateSnapshotPin=private_pin, readOnly=True, serverFilesWritten=False)


def observe_units(context, *, transport=None):
    return _observe(context, 'units', transport=transport)


def observe_environment(context, unit_pin, *, transport=None):
    from main_program_installation_selection import Records
    from main_program_control_activation import private_document
    records = Records(context['task']); unit = records.pinned(unit_pin)
    need(unit_pin['file'] == context['unitFile'], 'OBSERVATION_UNIT_NAME_CHANGED')
    secret = private_document(Path(context['private']), unit['privateSnapshotPin'], context['unitFile'][:-5] + '.private.json')
    need(project_units(secret, unit['privateSnapshotPin']) == unit, 'OBSERVATION_UNIT_PROJECTION_CHANGED')
    copied = deepcopy(context)
    copied['inputPins'] += [*records.path_pins(), unit['privateSnapshotPin']]
    return _observe(copied, 'environment', transport=transport, unit=secret, unit_pin=unit_pin)


def observe_all(context, *, transport=None):
    unit = observe_units(context, transport=transport)
    environment = observe_environment(context, unit['observationPin'], transport=transport)
    return dict(status='PASS', unit=unit, environment=environment, readOnly=True, serverFilesWritten=False)
