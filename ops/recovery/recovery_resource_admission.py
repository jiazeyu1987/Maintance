"""Explicit restore resource budgets; admission is never business acceptance."""
from pathlib import Path, PurePosixPath
import json
import os
import subprocess
import time
import stat
from contextlib import contextmanager

PROC_ROOT = Path('/proc')
CGROUP_ROOT = Path('/sys/fs/cgroup')
HOST_ROOT = Path('/var/lib/spug-restore-resources')
MACHINE_ID = Path('/etc/machine-id')


class ResourceAdmissionError(RuntimeError):
    def __init__(self, code, details=None):
        super().__init__(code)
        self.code = code
        self.details = {} if details is None else details


def need(condition, code, details=None):
    if not condition:
        raise ResourceAdmissionError(code, details)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


@contextmanager
def _host_lock():
    """Serialize metadata only; the durable active record survives every process."""
    need(os.name == 'posix', 'RESTORE_HOST_RESOURCE_PLATFORM_INVALID')
    import fcntl
    try:
        before = HOST_ROOT.stat()
        need(HOST_ROOT.is_absolute() and HOST_ROOT.resolve(strict=True) == HOST_ROOT and
             stat.S_ISDIR(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o700 and
             before.st_uid == os.geteuid(), 'RESTORE_HOST_RESOURCE_ROOT_INVALID')
    except OSError as error:
        raise ResourceAdmissionError('RESTORE_HOST_RESOURCE_ROOT_INVALID') from error
    fd = os.open(HOST_ROOT / 'lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        item = os.fstat(fd)
        need(stat.S_ISREG(item.st_mode) and item.st_nlink == 1 and item.st_uid == os.geteuid() and
             stat.S_IMODE(item.st_mode) == 0o600, 'RESTORE_HOST_RESOURCE_LOCK_INVALID')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ResourceAdmissionError('RESTORE_HOST_RESOURCE_BUSY') from error
        current = HOST_ROOT.stat()
        need((before.st_dev, before.st_ino) == (current.st_dev, current.st_ino),
             'RESTORE_HOST_RESOURCE_ROOT_CHANGED')
        yield
    finally:
        os.close(fd)


def _sync_host():
    fd = os.open(HOST_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _binding(configuration, request, root):
    from recovery_engine import digest
    target = configuration['targets'][request['targetConfigRef']]
    machine = MACHINE_ID.read_text(encoding='ascii').strip()
    need(machine and machine == target['machineId'], 'RESTORE_HOST_RESOURCE_IDENTITY_CHANGED')
    need(root.is_absolute() and root.resolve(strict=True) == root, 'RESTORE_RESOURCE_OPERATION_ROOT_INVALID')
    return dict(operationId=request['operationId'], targetConfigRef=request['targetConfigRef'],
                configurationSha256=digest(configuration), machineId=machine, operationRoot=str(root))


def reserve(configuration, request, root):
    """One host-wide restore at a time, including across SAFE/FAST executors."""
    from recovery_engine import utc, write
    if type(configuration['targets'][request['targetConfigRef']].get('resourceBudget')) is not dict:
        admit(configuration, request, root, 'owner')  # Persist the original budget rejection.
        raise ResourceAdmissionError('RESTORE_RESOURCE_BUDGET_INVALID')
    binding = _binding(configuration, request, root)
    with _host_lock():
        need(not os.path.lexists(HOST_ROOT / 'active.json'), 'RESTORE_HOST_RESOURCE_RESERVED')
        admit(configuration, request, root, 'owner')
        path = root / 'resource-reservation.json'
        need(not os.path.lexists(path), 'RESTORE_RESOURCE_RESERVATION_ALREADY_EXISTS')
        reference = write(path, dict(binding, schemaVersion='RestoreHostReservation/v1', startedAt=utc()))
        write(HOST_ROOT / 'active.json', dict(binding, reservationPin=reference))
        _sync_host()
        return reference


def _verify_reservation(configuration, request, root):
    from recovery_engine import load, pin, pinned_json
    binding = _binding(configuration, request, root)
    reference = pin(root / 'resource-reservation.json')
    value = pinned_json(reference)
    need(all(value.get(key) == item for key, item in binding.items()),
         'RESTORE_RESOURCE_RESERVATION_CHANGED')
    active = load(HOST_ROOT / 'active.json')
    need(active == dict(binding, reservationPin=reference), 'RESTORE_RESOURCE_RESERVATION_CHANGED')
    return reference, active


def verify_reservation(configuration, request, root):
    with _host_lock():
        return _verify_reservation(configuration, request, root)[0]


def release_success(configuration, request, root, result_pin, exit_pin):
    """Only a validated successful child permits normal release; failures retain it."""
    from recovery_engine import load, pin, pinned_json, utc, write
    need(result_pin['path'] == str(root / 'worker-result.json') and
         exit_pin['path'] == str(root / 'child-exit.json'), 'RESTORE_RESOURCE_RELEASE_EVIDENCE_INVALID')
    result, exited = pinned_json(result_pin), pinned_json(exit_pin)
    need(result.get('operationId') == request['operationId'] and result.get('state') == 'SUCCEEDED' and
         type(result.get('actualExitCode')) is int and result['actualExitCode'] == 0 and
         type(exited.get('actualExitCode')) is int and exited['actualExitCode'] == 0 and
         exited.get('timedOut') is False, 'RESTORE_RESOURCE_RELEASE_NOT_PROVEN')
    with _host_lock():
        release_path = root / 'resource-release.json'
        if release_path.exists():
            binding = _binding(configuration, request, root)
            reference = pin(root / 'resource-reservation.json')
            original = pinned_json(reference)
            need(all(original.get(key) == item for key, item in binding.items()),
                 'RESTORE_RESOURCE_RESERVATION_CHANGED')
            receipt = pin(release_path)
            recorded = pinned_json(receipt)
            need(recorded.get('reservationPin') == reference and recorded.get('resultPin') == result_pin and
                 recorded.get('exitPin') == exit_pin and recorded.get('reason') == 'VALIDATED_CHILD_SUCCESS',
                 'RESTORE_RESOURCE_RELEASE_EVIDENCE_INVALID')
            # Repeated queries are read-only for every later operation. A crash
            # after the authorization receipt may leave only our pointer to remove.
            active_path = HOST_ROOT / 'active.json'
            if not active_path.exists() or load(active_path) != dict(binding, reservationPin=reference):
                return receipt
            active = load(active_path)
        else:
            reference, active = _verify_reservation(configuration, request, root)
            receipt = write(release_path, dict(reservationPin=reference,
                resultPin=result_pin, exitPin=exit_pin, releasedAt=utc(), reason='VALIDATED_CHILD_SUCCESS'))
        (HOST_ROOT / 'active.json').unlink()
        try:
            _sync_host()
        except Exception:
            # An uncertain removal never enables another restore in this process.
            write(HOST_ROOT / 'active.json', active)
            raise
        return receipt


def release_no_mutation(configuration, request, root, result_pin, exit_pin):
    """Release only an exited child with explicit, complete no-mutation evidence."""
    from recovery_engine import check_pin, load, pin, pinned_json, utc, write
    need(result_pin['path'] == str(root / 'worker-result.json') and
         exit_pin['path'] == str(root / 'child-exit.json'), 'RESTORE_RESOURCE_RELEASE_EVIDENCE_INVALID')
    output, exited = pinned_json(result_pin), pinned_json(exit_pin)
    need(output.get('operationId') == request['operationId'] and output.get('state') == 'FAILED_RETAINED' and
         type(output.get('actualExitCode')) is int and output['actualExitCode'] == 1 and
         output.get('data', {}).get('mutationDispatched') is False and
         type(exited.get('actualExitCode')) is int and exited['actualExitCode'] == 1 and
         exited.get('timedOut') is False, 'RESTORE_RESOURCE_NO_MUTATION_NOT_PROVEN')
    need(not any(root.rglob('importer-*.json')) and
         not (root / 'replacement-preparation/replacement-intent.json').exists(),
         'RESTORE_RESOURCE_NO_MUTATION_NOT_PROVEN')
    for reference in output['originalResultPins']:
        check_pin(reference)
    for path in root.rglob('native-*.json'):
        reference = pin(path)
        value = pinned_json(reference)
        need(reference in output['originalResultPins'] and value.get('mutation') is False and
             type(value.get('actualExitCode')) is int and value.get('finishedAt'),
             'RESTORE_RESOURCE_NO_MUTATION_NOT_PROVEN')
    with _host_lock():
        binding = _binding(configuration, request, root)
        reservation = pin(root / 'resource-reservation.json')
        original = pinned_json(reservation)
        need(all(original.get(key) == item for key, item in binding.items()),
             'RESTORE_RESOURCE_RESERVATION_CHANGED')
        expected = dict(binding, reservationPin=reservation)
        active_path = HOST_ROOT / 'active.json'
        release_path = root / 'resource-no-mutation-release.json'
        if release_path.exists():
            receipt = pin(release_path)
            value = pinned_json(receipt)
            need(value.get('reservationPin') == reservation and value.get('resultPin') == result_pin and
                 value.get('exitPin') == exit_pin and value.get('reason') == 'PROVEN_NO_MUTATION',
                 'RESTORE_RESOURCE_RELEASE_EVIDENCE_INVALID')
            if not active_path.exists() or load(active_path) != expected:
                return receipt
        else:
            need(load(active_path) == expected, 'RESTORE_RESOURCE_RESERVATION_CHANGED')
            receipt = write(release_path, dict(reservationPin=reservation, resultPin=result_pin,
                exitPin=exit_pin, reason='PROVEN_NO_MUTATION', releasedAt=utc(), partialTargetRetained=True))
        active_path.unlink()
        try:
            _sync_host()
        except Exception:
            write(active_path, expected)
            raise
        return receipt


def release_proven_oom(configuration, request, root, result_pin, verify_stopped):
    """The controller supplies its strict live proof while exclusion is held."""
    from recovery_engine import check_pin, load, pin, pinned_json, utc, write
    need(result_pin['path'] == str(root / 'result.json'), 'RESTORE_RESOURCE_RELEASE_EVIDENCE_INVALID')
    with _host_lock():
        binding = _binding(configuration, request, root)
        reservation = pin(root / 'resource-reservation.json')
        original = pinned_json(reservation)
        need(all(original.get(key) == item for key, item in binding.items()),
             'RESTORE_RESOURCE_RESERVATION_CHANGED')
        output = pinned_json(result_pin)
        need(output.get('operationId') == request['operationId'] and
             output.get('state') == 'TERMINAL_UNKNOWN' and output.get('failureCode') in
             ('FORMAL_SQL_IMPORT_FAILED', 'FORMAL_SQL_IMPORT_STREAM_FAILED') and
             reservation in output.get('originalResultPins', []), 'RESTORE_RESOURCE_RELEASE_NOT_PROVEN')
        proofs = verify_stopped()
        need(type(proofs) is list and proofs, 'RESTORE_RESOURCE_RELEASE_NOT_PROVEN')
        for reference in [reservation, result_pin, *proofs]:
            check_pin(reference)
        release_path = root / 'resource-oom-release.json'
        active_path = HOST_ROOT / 'active.json'
        expected = dict(binding, reservationPin=reservation)
        if release_path.exists():
            receipt = pin(release_path)
            recorded = pinned_json(receipt)
            need(recorded.get('reservationPin') == reservation and recorded.get('resultPin') == result_pin and
                 recorded.get('reason') == 'PROVEN_STOPPED_OOM', 'RESTORE_RESOURCE_RELEASE_EVIDENCE_INVALID')
            for reference in recorded['proofPins']:
                check_pin(reference)
            if not active_path.exists() or load(active_path) != expected:
                return [*proofs, receipt]
        else:
            need(load(active_path) == expected, 'RESTORE_RESOURCE_RESERVATION_CHANGED')
            receipt = write(release_path, dict(reservationPin=reservation, resultPin=result_pin,
                proofPins=proofs, reason='PROVEN_STOPPED_OOM', releasedAt=utc(), partialTargetRetained=True))
        active_path.unlink()
        try:
            _sync_host()
        except Exception:
            write(active_path, expected)
            raise
        return [*proofs, receipt]


def cgroup_memory_limits(record, root=Path('/sys/fs/cgroup')):
    """Read the process's memory hierarchy, including tighter parent limits."""
    entries = [line.split(':', 2) for line in record.splitlines()]
    need(entries and all(len(row) == 3 and row[0].isdigit() for row in entries),
         'RESTORE_CGROUP_RECORD_INVALID')
    v1 = [row for row in entries if 'memory' in row[1].split(',')]
    v2 = [row for row in entries if row[:2] == ['0', '']]
    need(len(v1) <= 1 and len(v2) <= 1 and (v1 or v2), 'RESTORE_CGROUP_MEMORY_UNAVAILABLE')
    # In a hybrid hierarchy, an explicit v1 memory controller owns the limit.
    version, entry = (1, v1[0]) if v1 else (2, v2[0])
    relative = PurePosixPath(entry[2])
    need(relative.is_absolute() and '..' not in relative.parts and str(relative) == entry[2],
         'RESTORE_CGROUP_PATH_INVALID')
    mount = Path(root) / 'memory' if version == 1 else Path(root)
    current = mount.joinpath(*relative.parts[1:])
    leaf = current
    limits, paths = [], []
    try:
        need(mount.is_absolute() and mount.resolve(strict=True) == mount and
             current.resolve(strict=True) == current, 'RESTORE_CGROUP_PATH_INVALID')
        while True:
            path = current / ('memory.limit_in_bytes' if version == 1 else 'memory.max')
            # The v2 host root has no limit file; intermediate groups must have one.
            if not (version == 2 and current == mount and not path.exists()):
                raw = path.read_text(encoding='ascii').strip()
                need(raw == 'max' and version == 2 or raw.isdigit(), 'RESTORE_CGROUP_LIMIT_INVALID')
                paths.append(str(path))
                enforced = True
                if version == 1 and current != leaf:
                    hierarchy = (current / 'memory.use_hierarchy').read_text(encoding='ascii').strip()
                    need(hierarchy in ('0', '1'), 'RESTORE_CGROUP_HIERARCHY_INVALID')
                    enforced = hierarchy == '1'
                if raw != 'max' and enforced:
                    limits.append(int(raw))
            if current == mount:
                break
            current = current.parent
    except (OSError, UnicodeError) as error:
        raise ResourceAdmissionError('RESTORE_CGROUP_OBSERVATION_FAILED') from error
    need(paths, 'RESTORE_CGROUP_MEMORY_UNAVAILABLE')
    return dict(version=version, limitsBytes=limits, observedPaths=paths)


def check_budget(policy, observed):
    """Check a measured snapshot, aggregating disk demand by actual device."""
    invalid = 'RESTORE_RESOURCE_BUDGET_INVALID'
    need(type(policy) is dict and set(policy) == {'schemaVersion', 'mysqlMemoryBytes',
         'hostAvailableMemoryBytes', 'diskBytesByPath'} and
         policy['schemaVersion'] == 'RestoreResourceBudget/v1', invalid)
    need(integer(policy['mysqlMemoryBytes'], 1) and integer(policy['hostAvailableMemoryBytes'], 1), invalid)
    disks = policy['diskBytesByPath']
    need(type(disks) is dict and disks and all(type(path) is str and
         PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts and
         str(PurePosixPath(path)) == path and integer(size) for path, size in disks.items()) and
         sum(disks.values()) > 0, invalid)
    invalid = 'RESTORE_RESOURCE_OBSERVATION_INVALID'
    need(type(observed) is dict and integer(observed.get('mysqlMemoryLimitBytes'), 1) and
         integer(observed.get('hostAvailableMemoryBytes')) and type(observed.get('disks')) is list, invalid)
    measurements = observed['disks']
    need(len(measurements) == len(disks) and all(type(row) is dict and
         type(row.get('path')) is str and row['path'] in disks and integer(row.get('device')) and
         integer(row.get('freeBytes')) for row in measurements) and
         {row['path'] for row in measurements} == set(disks), invalid)
    need(observed['mysqlMemoryLimitBytes'] >= policy['mysqlMemoryBytes'],
         'RESTORE_MYSQL_MEMORY_INSUFFICIENT', dict(requiredBytes=policy['mysqlMemoryBytes'],
         availableBytes=observed['mysqlMemoryLimitBytes']))
    # Swap is deliberately excluded: it is neither MySQL capacity nor RAM headroom.
    need(observed['hostAvailableMemoryBytes'] >= policy['hostAvailableMemoryBytes'],
         'RESTORE_HOST_MEMORY_INSUFFICIENT', dict(requiredBytes=policy['hostAvailableMemoryBytes'],
         availableBytes=observed['hostAvailableMemoryBytes']))
    grouped = {}
    for row in measurements:
        device = row['device']
        current = grouped.setdefault(device, dict(device=device, requiredBytes=0, availableBytes=row['freeBytes']))
        current['requiredBytes'] += disks[row['path']]
        current['availableBytes'] = min(current['availableBytes'], row['freeBytes'])
    requirements = [grouped[device] for device in sorted(grouped)]
    for row in requirements:
        need(row['availableBytes'] >= row['requiredBytes'], 'RESTORE_DISK_SPACE_INSUFFICIENT', row)
    return dict(admitted=True, businessAcceptance='NOT_PERFORMED', diskRequirements=requirements,
                mysqlMemoryLimitBytes=observed['mysqlMemoryLimitBytes'],
                hostAvailableMemoryBytes=observed['hostAvailableMemoryBytes'])


def observe_resources(configuration, request, policy):
    """Read native host/cgroup/filesystem state; never change resource limits."""
    from recovery_engine import check_pin
    target = configuration['targets'][request['targetConfigRef']]
    services = [row for row in target['services'] if row['role'] == 'mysql']
    need(len(services) == 1, 'RESTORE_RESOURCE_MYSQL_IDENTITY_INVALID')
    service = services[0]
    check_pin(target['dockerPin'])
    response = subprocess.run([target['dockerPin']['path'], '--host', 'unix:///var/run/docker.sock',
        'inspect', service['id']], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, check=False)
    need(response.returncode == 0 and not response.stderr, 'RESTORE_RESOURCE_MYSQL_OBSERVATION_FAILED')
    rows = json.loads(response.stdout)
    need(type(rows) is list and len(rows) == 1, 'RESTORE_RESOURCE_MYSQL_OBSERVATION_FAILED')
    mysql = rows[0]
    need(mysql['Id'] == service['id'] and mysql['Image'] == service['imageId'] and
         mysql['Config']['Labels'].get('intruoyi.recovery.target') == target['targetId'] and
         mysql['State']['Running'] is True and mysql['State']['Paused'] is False and
         mysql['State']['Restarting'] is False and integer(mysql['State']['Pid'], 1),
         'RESTORE_RESOURCE_MYSQL_IDENTITY_INVALID')
    process = PROC_ROOT / str(mysql['State']['Pid'])
    before = process.joinpath('stat').read_text(encoding='ascii').rpartition(') ')[2].split()[19]
    memory = {}
    for line in (PROC_ROOT / 'meminfo').read_text(encoding='ascii').splitlines():
        key, value = line.split(':', 1)
        if key in ('MemTotal', 'MemAvailable', 'SwapFree'):
            amount, unit = value.split()
            need(unit == 'kB' and amount.isdigit(), 'RESTORE_RESOURCE_OBSERVATION_INVALID')
            memory[key] = int(amount) * 1024
    need(integer(memory.get('MemTotal'), 1) and integer(memory.get('MemAvailable')),
         'RESTORE_RESOURCE_OBSERVATION_INVALID')
    hierarchy = cgroup_memory_limits(process.joinpath('cgroup').read_text(encoding='ascii'), CGROUP_ROOT)
    configured = mysql['HostConfig']['Memory']
    need(integer(configured), 'RESTORE_RESOURCE_OBSERVATION_INVALID')
    limits = [memory['MemTotal'], *hierarchy['limitsBytes']]
    if configured:
        limits.append(configured)
    disks = []
    for name in policy['diskBytesByPath']:
        path = Path(name)
        need(path.is_absolute() and path.resolve(strict=True) == path and path.is_dir(),
             'RESTORE_RESOURCE_DISK_PATH_INVALID')
        usage = os.statvfs(path)
        disks.append(dict(path=name, device=path.stat().st_dev, freeBytes=usage.f_bavail * usage.f_frsize))
    required_paths = [configuration['operationsRoot'], target['dataRoot'], *target['dataPaths']]
    if 'replacement' in target:
        required_paths.append(target['replacement']['stateRoot'])
    for name in required_paths:
        path = Path(name)
        need(path.is_absolute() and path.resolve(strict=True) == path and
             any((path == Path(row['path']) or Path(row['path']) in path.parents) and
                 path.stat().st_dev == row['device'] for row in disks),
             'RESTORE_RESOURCE_DISK_BUDGET_INCOMPLETE')
    after = process.joinpath('stat').read_text(encoding='ascii').rpartition(') ')[2].split()[19]
    need(before == after, 'RESTORE_RESOURCE_MYSQL_PROCESS_CHANGED')
    return dict(mysqlMemoryLimitBytes=min(limits), mysqlConfiguredMemoryBytes=configured,
                mysqlContainerId=mysql['Id'], mysqlProcessStartTicks=before,
                hostAvailableMemoryBytes=memory['MemAvailable'], hostTotalMemoryBytes=memory['MemTotal'],
                cgroup=hierarchy, disks=disks)


def admit(configuration, request, root, stage, *, reservation_configuration=None):
    """Persist both rejection and admission before a restore mutation starts."""
    from recovery_engine import digest, utc, write
    need(stage in ('owner', 'target', 'replacement'), 'RESTORE_RESOURCE_STAGE_INVALID')
    started, tick = utc(), time.monotonic()
    record = dict(operationId=request['operationId'], targetConfigRef=request['targetConfigRef'],
                  configurationSha256=digest(configuration), startedAt=started,
                  businessAcceptance='NOT_PERFORMED', admitted=False)
    try:
        if reservation_configuration is not None:
            from copy import deepcopy
            expected = deepcopy(reservation_configuration)
            target = expected['targets'][request['targetConfigRef']]
            target['dataRoot'] = str(Path(target['replacement']['stateRoot']) / request['operationId'] / 'runtime')
            need(stage == 'target' and configuration == expected,
                 'RESTORE_REPLACEMENT_CONFIGURATION_CHANGED')
        if stage != 'owner':
            record['reservationPin'] = verify_reservation(
                configuration if reservation_configuration is None else reservation_configuration,
                request, Path(root))
        policy = configuration['targets'][request['targetConfigRef']].get('resourceBudget')
        need(type(policy) is dict and type(policy.get('diskBytesByPath')) is dict,
             'RESTORE_RESOURCE_BUDGET_INVALID')
        observed = observe_resources(configuration, request, policy)
        record.update(observation=observed)
        decision = check_budget(policy, observed)
        record.update(budget=policy, **decision)
        return decision
    except Exception as error:
        record.update(failureCode=getattr(error, 'code', 'RESTORE_RESOURCE_OBSERVATION_FAILED'),
                      details=getattr(error, 'details', {}), errorType=type(error).__name__)
        if isinstance(error, ResourceAdmissionError):
            raise
        raise ResourceAdmissionError('RESTORE_RESOURCE_OBSERVATION_FAILED') from error
    finally:
        record.update(finishedAt=utc(), elapsedSeconds=round(time.monotonic()-tick, 3))
        write(Path(root) / ('resource-admission-' + stage + '.json'), record)
