"""Explicit capacity admission for an operation's historical program import.

The original database/object budget remains authoritative. Program projection
and Docker-store capacity are additional reservations, aggregated by the actual
filesystem device. This records admission, never business acceptance.
"""
from copy import deepcopy
import json
import os
from pathlib import Path, PurePosixPath
import stat
import time

from recovery_engine import digest, utc, write
import recovery_resource_admission as admission


BUDGET_FIELDS = frozenset(('schemaVersion', 'targetConfigRef', 'projectionBytes',
                           'dockerImportBytes', 'minimumFreeBytes'))


def _integer(value, minimum=0):
    return type(value) is int and minimum <= value < 2**63


def _path(value):
    return (type(value) is str and bool(value) and '\x00' not in value and
            PurePosixPath(value).is_absolute() and '..' not in PurePosixPath(value).parts and
            str(PurePosixPath(value)) == value)


def _program_budget(policy, source):
    invalid = 'RESTORE_PROGRAM_RESOURCE_BUDGET_INVALID'
    admission.need(type(policy) is dict and set(policy) == BUDGET_FIELDS and
        policy['schemaVersion'] == 'MainProgramResourceBudget/v1' and
        type(policy['targetConfigRef']) is str and 0 < len(policy['targetConfigRef']) <= 256 and
        not any(ord(char) < 32 for char in policy['targetConfigRef']) and
        all(_integer(policy[key], 1) for key in
            ('projectionBytes', 'dockerImportBytes', 'minimumFreeBytes')), invalid)
    admission.need(type(source) is dict and source.get('schemaVersion') == 'MainProgramSourceArchive/v1' and
        _integer(source.get('maxImportBytes'), 1) and type(source.get('archivePin')) is dict and
        _integer(source['archivePin'].get('bytes'), 1), invalid)
    admission.need(policy['projectionBytes'] >= source['maxImportBytes'] and
        policy['dockerImportBytes'] >= source['archivePin']['bytes'],
        'RESTORE_PROGRAM_RESOURCE_BUDGET_INCOMPLETE')


def check_program_budget(data_policy, observed, program_budget, source_program, extra_disks):
    """Keep the existing memory/data checks and add all program device demand."""
    decision = admission.check_budget(data_policy, observed)
    _program_budget(program_budget, source_program)
    invalid = 'RESTORE_PROGRAM_RESOURCE_OBSERVATION_INVALID'
    admission.need(type(extra_disks) is list and len(extra_disks) == 2 and all(
        type(row) is dict and set(row) == {'role', 'path', 'device', 'freeBytes'} and
        type(row['role']) is str and row['role'] in ('projection', 'docker') and
        _path(row['path']) and _integer(row['device']) and _integer(row['freeBytes'])
        for row in extra_disks) and
        {row['role'] for row in extra_disks} == {'projection', 'docker'}, invalid)
    grouped = {row['device']: deepcopy(row) for row in decision['diskRequirements']}
    for row in extra_disks:
        current = grouped.setdefault(row['device'], dict(device=row['device'],
            requiredBytes=0, availableBytes=row['freeBytes']))
        current['requiredBytes'] += program_budget[
            'projectionBytes' if row['role'] == 'projection' else 'dockerImportBytes']
        current['availableBytes'] = min(current['availableBytes'], row['freeBytes'])
    requirements = [grouped[device] for device in sorted(grouped)]
    for row in requirements:
        row['requiredBytes'] += program_budget['minimumFreeBytes']
        admission.need(row['availableBytes'] >= row['requiredBytes'],
            'RESTORE_PROGRAM_DISK_SPACE_INSUFFICIENT', row)
    return dict(decision, diskRequirements=requirements)


def _identity(path, *, private=False):
    invalid = 'RESTORE_PROGRAM_RESOURCE_DIRECTORY_INVALID'
    admission.need(_path(str(path)) and path.resolve(strict=True) == path, invalid)
    item = path.lstat()
    admission.need(stat.S_ISDIR(item.st_mode) and
        (not private or stat.S_IMODE(item.st_mode) == 0o700 and item.st_uid == os.geteuid()), invalid)
    return item.st_dev, item.st_ino, item.st_mode, item.st_uid, item.st_gid


def _observe_directory(role, path, *, private=False):
    before = _identity(path, private=private)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        item = os.fstat(fd)
        admission.need((item.st_dev, item.st_ino, item.st_mode, item.st_uid, item.st_gid) == before,
            'RESTORE_PROGRAM_RESOURCE_DIRECTORY_CHANGED')
        usage = os.fstatvfs(fd)
        observation = dict(role=role, path=str(path), device=item.st_dev,
            freeBytes=usage.f_bavail * usage.f_frsize)
        admission.need(_identity(path, private=private) == before,
            'RESTORE_PROGRAM_RESOURCE_DIRECTORY_CHANGED')
        return observation, before
    finally:
        os.close(fd)


def admit_program_resources(native, source_program, claim, *, reservation_configuration,
                            execution_binding_pin, execution_lock_fd):
    """Measure before protection/stop/load, under the original PREPARATION view.

    Full archive validation and its active lease belong to the calling restore
    flow. Import capacity is an explicit registered allowance, not an inferred
    bound on arbitrary Docker filesystem expansion.
    """
    from recovery_program_native import _NativeView, MainNativeExecutionContext
    from recovery_program_execution import resolve_execution_configuration
    from recovery_program_source import validate_source_policy, _pin_contract

    view = getattr(native, 'native_context', None)
    admission.need(type(view) is _NativeView and
        type(view._context) is MainNativeExecutionContext,
        'RESTORE_PROGRAM_RESOURCE_CONTEXT_REQUIRED')
    context = view._context
    root, request = context._root, deepcopy(context._request)
    started, tick = utc(), time.monotonic()
    record = dict(operationId=request['operationId'], targetConfigRef=request['targetConfigRef'],
        startedAt=started, admitted=False, businessAcceptance='NOT_PERFORMED')
    try:
        view.guard_native(native)
        admission.need(view.phase == 'PREPARATION' and context.phase == 'PREPARATION' and
            execution_binding_pin == context._binding and execution_lock_fd == context._lock_fd and
            reservation_configuration == context._owner and Path(claim) == context._claim,
            'RESTORE_PROGRAM_RESOURCE_EXECUTION_CHANGED')
        owner = reservation_configuration
        configuration, proof = resolve_execution_configuration(owner, request, root,
            binding_pin=execution_binding_pin, lock_fd=execution_lock_fd, guard=view.guard)
        admission.need(configuration == view.configuration,
            'RESTORE_PROGRAM_RESOURCE_CONFIGURATION_CHANGED')
        reservation = admission.verify_reservation(owner, request, root)
        record.update(configurationSha256=digest(configuration),
            reservationConfigurationSha256=digest(owner), reservationPin=reservation,
            programExecution=proof)
        policies = owner.get('targetProgramResourceBudgets')
        target_ref = request['targetConfigRef']
        admission.need(type(policies) is dict and set(policies) <= set(owner['targets']) and
            target_ref in policies, 'RESTORE_PROGRAM_RESOURCE_BUDGET_INVALID')
        policy = policies[target_ref]
        _program_budget(policy, source_program)
        admission.need(policy['targetConfigRef'] == target_ref,
            'RESTORE_PROGRAM_RESOURCE_BUDGET_INVALID')
        source_policy = validate_source_policy(owner, request['sourceConfigRef'])
        admission.need(source_program.get('sourceConfigRef') == request['sourceConfigRef'] and
            source_program.get('policySha256') == digest(source_policy) and
            all(source_program.get(key) == source_policy[key] for key in
                ('architecture', 'maxArchiveBytes', 'maxImportBytes')),
            'RESTORE_PROGRAM_RESOURCE_SOURCE_CHANGED')
        _pin_contract(source_program['archivePin'])
        admission.need(source_program['archivePin']['bytes'] <= source_policy['maxArchiveBytes'],
            'RESTORE_PROGRAM_RESOURCE_SOURCE_CHANGED')
        record.update(sourceProgramPolicySha256=digest(source_policy), programBudget=deepcopy(policy))
        data_policy = configuration['targets'][target_ref].get('resourceBudget')
        admission.need(type(data_policy) is dict, 'RESTORE_RESOURCE_BUDGET_INVALID')
        record['budget'] = deepcopy(data_policy)
        observed = admission.observe_resources(configuration, request, data_policy)
        record['observation'] = observed
        # Preserve original memory/data rejection before probing an import store.
        admission.check_budget(data_policy, observed)
        view.guard_native(native)
        info = json.loads(native.docker(['info', '--format', '{{json .}}']))
        admission.need(type(info) is dict and info.get('ID') == native.config['dockerEngineId'] and
            _path(info.get('DockerRootDir')), 'RESTORE_PROGRAM_RESOURCE_ENGINE_CHANGED')
        docker_root = Path(info['DockerRootDir'])
        projection, claim_identity = _observe_directory('projection', Path(claim), private=True)
        docker, docker_identity = _observe_directory('docker', docker_root)
        record['programObservation'] = dict(dockerEngineId=info['ID'], disks=[projection, docker])
        decision = check_program_budget(data_policy, observed, policy, source_program, [projection, docker])
        view.guard_native(native)
        after_configuration, after_proof = resolve_execution_configuration(owner, request, root,
            binding_pin=execution_binding_pin, lock_fd=execution_lock_fd, guard=view.guard)
        admission.need(after_configuration == configuration and after_proof == proof and
            admission.verify_reservation(owner, request, root) == reservation and
            _identity(Path(claim), private=True) == claim_identity and
            _identity(docker_root) == docker_identity,
            'RESTORE_PROGRAM_RESOURCE_OBSERVATION_CHANGED')
        view.guard_native(native)
        record.update(**decision)
        return decision
    except Exception as error:
        record.update(failureCode=getattr(error, 'code', 'RESTORE_PROGRAM_RESOURCE_OBSERVATION_FAILED'),
            details=getattr(error, 'details', {}), errorType=type(error).__name__)
        raise
    finally:
        record.update(finishedAt=utc(), elapsedSeconds=round(time.monotonic()-tick, 3))
        write(root/'resource-admission-program.json', record)
