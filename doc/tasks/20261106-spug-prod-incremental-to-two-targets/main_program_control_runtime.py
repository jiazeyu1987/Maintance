"""Read-only controller gates shared by immutable staging and activation.

This module imports no deployment helper and performs no I/O on import. The
caller owns the physical lock, exact subprocess transport and pinned readers.
It cannot restart a service, publish a receipt or admit business restoration.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess


def need(value, code):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _identity(info):
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_nlink',
        'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def _read_file(path):
    path = Path(path); before = path.lstat()
    need(path.resolve(strict=True) == path and stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
         'REMOTE_FILE_ALIAS')
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        opened = _identity(os.fstat(stream.fileno())); named = _identity(before)
        # Windows fstat exposes change time while lstat exposes creation time.
        # Each clock remains exact within its own before/after observation.
        need((opened[:-1] == named[:-1]) if os.name == 'nt' else (opened == named), 'REMOTE_FILE_CHANGED')
        raw = stream.read()
        need(_identity(os.fstat(stream.fileno())) == opened, 'REMOTE_FILE_CHANGED')
    need(_identity(path.lstat()) == _identity(before) and path.resolve(strict=True) == path,
         'REMOTE_FILE_CHANGED')
    return raw, dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def pin_file(path):
    return _read_file(path)[1]


def _document(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'REMOTE_JSON_DUPLICATE_KEY'); result[key] = value
    return result


def read_pinned(reference):
    raw, actual = _read_file(reference['path'])
    need(actual == reference, 'REMOTE_PIN_CHANGED')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=_document)


def run_command(args, timeout=90, env=None):
    need(type(args) is list and args and all(type(value) is str for value in args) and
         type(timeout) in (int, float) and 0 < timeout <= 900, 'RUNTIME_COMMAND_INVALID')
    result = subprocess.run(args, capture_output=True, timeout=timeout, env=env)
    need(result.returncode == 0, 'RUNTIME_COMMAND_FAILED_' + str(result.returncode))
    return result.stdout


class RuntimePaths:
    """Native read boundary; alternate paths are explicit test/host inputs."""
    def __init__(self, *, proc_root='/proc', reservation_path='/var/lib/spug-restore-resources/active.json',
                 fstab_path='/etc/fstab', mountinfo_path='/proc/self/mountinfo'):
        self.proc_root = Path(proc_root)
        self.reservation_path = Path(reservation_path)
        self.fstab_path = Path(fstab_path)
        self.mountinfo_path = Path(mountinfo_path)

    def read_bytes(self, path):
        return Path(path).read_bytes()

    def exists(self, path):
        return os.path.lexists(path)

    def dropin_names(self, path):
        path = Path(path)
        need(path.resolve(strict=True) == path and path.is_dir(), 'DROPIN_DIRECTORY_ALIAS')
        return sorted(item.name for item in path.glob('*.conf'))

    def process_ids(self):
        return [int(path.name) for path in self.proc_root.iterdir() if path.name.isdecimal()]

    def process_bytes(self, pid, name):
        need(name in ('cmdline', 'environ', 'limits'), 'PROC_FIELD_INVALID')
        return self.read_bytes(self.proc_root / str(pid) / name)

    def process_executable(self, pid):
        return str((self.proc_root / str(pid) / 'exe').resolve(strict=True))


class RuntimeGates:
    """Strict original-state checks, with no filesystem or service mutation."""
    def __init__(self, spec, *, verify_environment, verify_custody, lock_guard,
                 run=None, pin=None, read=None, paths=None):
        run = run_command if run is None else run
        pin = pin_file if pin is None else pin
        read = read_pinned if read is None else read
        paths = RuntimePaths() if paths is None else paths
        need(type(spec) is dict and all(callable(fn) for fn in
             (run, pin, read, verify_environment, verify_custody, lock_guard)), 'RUNTIME_BOUNDARY_INVALID')
        self.spec = deepcopy(spec)
        self.run, self.pin, self.read = run, pin, read
        self.verify_environment, self.verify_custody = verify_environment, verify_custody
        self.paths, self.lock_guard = paths, lock_guard

    def properties(self, service):
        raw = self.run(['systemctl', 'show', service, '-p', 'MainPID', '-p', 'FragmentPath', '-p', 'DropInPaths',
            '-p', 'Requires', '-p', 'After', '-p', 'LimitNOFILE', '-p', 'ActiveState', '-p', 'SubState'])
        return dict(line.split('=', 1) for line in raw.decode('utf-8').splitlines() if '=' in line)

    def verify_process(self, row):
        control = self.read(row['controlConfigurationPin']); self.read(row['ownerConfigurationPin'])
        props = self.properties(row['service'])
        need(props['MainPID'] == str(row['pid']) and props['ActiveState'] == 'active' and
             props['LimitNOFILE'] == '65536', 'CONTROL_PROCESS_CHANGED')
        raw_args = self.paths.process_bytes(row['pid'], 'cmdline')
        args = raw_args.rstrip(b'\0').split(b'\0')
        expected = [control['pythonPin']['path'].encode(), b'-B', (row['engine'] + '/control_entry.py').encode(), b'serve', b'--config-pin']
        # Path joining must preserve the registered spelling. Engine records use
        # native canonical spelling on local fixtures, POSIX paths on hosts.
        expected[2] = str(Path(row['engine']) / 'control_entry.py').encode()
        need(len(args) == 6 and args[:-1] == expected and json.loads(args[-1]) == row['controlConfigurationPin'],
             'CONTROL_ARGV_CHANGED')
        if 'argvSha256' in row:
            need(hashlib.sha256(raw_args).hexdigest() == row['argvSha256'], 'ORIGINAL_ARGV_HASH_CHANGED')
        else:
            need(args[-1] == canonical(row['controlConfigurationPin']), 'NEW_ARGV_ENCODING_CHANGED')
        if 'dropinPin' in row:
            need(self.pin(row['dropinPin']['path']) == row['dropinPin'], 'PEER_DROPIN_CHANGED')
        originals = [r for r in self.spec['unit']['controllers'] if r['service'] == row['service']]
        need(len(originals) == 1, 'CONTROL_UNIT_BINDING_CHANGED'); original = originals[0]
        expected_dropins = [r['path'] for r in original['dropinPins']]
        if 'dropinPin' in row and row['dropinPin']['path'] not in expected_dropins:
            expected_dropins.append(row['dropinPin']['path'])
        need(props['FragmentPath'] == original['unitPin']['path'] and props['DropInPaths'].split() == expected_dropins,
             'LOADED_UNIT_OR_DROPINS_CHANGED')
        executable = self.paths.process_executable(row['pid'])
        need(executable == str(Path(control['pythonPin']['path']).resolve()), 'CONTROL_EXECUTABLE_CHANGED')
        raw_environment = self.paths.process_bytes(row['pid'], 'environ'); baseline = None; declared = None
        registered = self.spec.get('environmentBaseline')
        if registered is not None:
            matches = [r for r in registered['controllers'] if r['service'] == row['service']]
            need(len(matches) == 1, 'ENVIRONMENT_BASELINE_MISSING'); candidate = matches[0]
            mode = 'ORIGINAL_BASELINE' if row['pid'] == candidate['pid'] else 'CONFIG_EXACT'
            need(row.get('environmentMode') == mode, 'ENVIRONMENT_MODE_CHANGED')
            if mode == 'ORIGINAL_BASELINE':
                need(all(row[k] == candidate[k] for k in ('service', 'pid', 'engine', 'controlConfigurationPin',
                     'ownerConfigurationPin', 'argvSha256')), 'ENVIRONMENT_ORIGINAL_IDENTITY_CHANGED')
                need(self.pin(candidate['unitPin']['path']) == candidate['unitPin'] and
                     all(self.pin(p['path']) == p for p in candidate['dropinPins']), 'ENVIRONMENT_UNIT_CHANGED')
                baseline = candidate
                declared = self.run(['systemctl', 'show', row['service'], '-p', 'Environment']).decode('utf-8')
        environment = self.verify_environment(control['environment'], raw_environment, baseline=baseline, systemd_raw=declared)
        limits = self.paths.process_bytes(row['pid'], 'limits').decode('utf-8')
        need(any(line.startswith('Max open files') and line.split()[3:5] == ['65536', '65536']
             for line in limits.splitlines()), 'CONTROL_LIMIT_CHANGED')
        need(self.paths.process_bytes(row['pid'], 'cmdline') == raw_args and
             self.paths.process_bytes(row['pid'], 'environ') == raw_environment and
             self.paths.process_executable(row['pid']) == executable, 'CONTROL_CHANGED_DURING_READ')
        return dict(service=row['service'], pid=row['pid'], argvSha256=hashlib.sha256(raw_args).hexdigest(),
            executable=executable, environmentVerification=environment, properties=props)

    def verify_package(self, row):
        root = Path(row['engine']); package_path = root / 'package.json'
        package_pin = self.pin(package_path); package = self.read(package_pin)
        need(type(package.get('files')) is dict and len(package['files']) == row['fileCount'] and
             package.get('packageSha256') == row['fileManifestSha256'] and
             hashlib.sha256(canonical(package['files'])).hexdigest() == row['fileManifestSha256'], 'PACKAGE_MANIFEST_CHANGED')
        for name, sha in package['files'].items():
            p = PurePosixPath(name)
            need(not p.is_absolute() and '..' not in p.parts and str(p) == name and '\\' not in name,
                 'PACKAGE_MEMBER_PATH_INVALID')
            need(self.pin(root / name)['sha256'] == sha, 'PACKAGE_MEMBER_CHANGED')
        need(self.pin(package_path) == package_pin, 'PACKAGE_MANIFEST_CHANGED')
        return package_pin

    def original_units(self):
        for original in self.spec['unit']['controllers']:
            need(self.pin(original['unitPin']['path']) == original['unitPin'], 'ORIGINAL_UNIT_CHANGED')
            for ref in original['dropinPins']:
                need(self.pin(ref['path']) == ref, 'ORIGINAL_DROPIN_CHANGED')
            rows = [row for row in self.spec['current']['controllers'] if row['service'] == original['service']]
            need(len(rows) == 1, 'CONTROL_UNIT_BINDING_CHANGED')
            expected = list(original['existingNames']); row = rows[0]
            if 'dropinPin' in row and row['dropinPin'] not in original['dropinPins']:
                expected.append(Path(row['dropinPin']['path']).name)
            need(self.paths.dropin_names(original['directory']) == sorted(expected), 'DROPIN_SET_CHANGED')

    def no_workers(self, rows):
        need(not self.paths.exists(self.paths.reservation_path), 'ACTIVE_RESOURCE_RESERVATION')
        roots = {self.read(r['controlConfigurationPin'])['workingDirectory'] for r in rows}
        expected = {r['pid'] for r in rows}
        for pid in self.paths.process_ids():
            try: args = self.paths.process_bytes(pid, 'cmdline').rstrip(b'\0').split(b'\0')
            except (FileNotFoundError, ProcessLookupError): continue
            if any(root.encode() in arg for root in roots for arg in args):
                need(pid in expected and any(arg.replace(b'\\', b'/').endswith(b'/control_entry.py') for arg in args),
                     'UNEXPECTED_CONTROL_OR_WORKER')

    def snapshot(self):
        command = ['/usr/bin/docker', '--host', 'unix:///var/run/docker.sock']
        ids = self.run(command + ['ps', '-aq', '--no-trunc']).decode('utf-8').split()
        need(ids and len(ids) == len(set(ids)), 'NO_BUSINESS_INVENTORY')
        values = json.loads(self.run(command + ['inspect', *ids]))
        need(type(values) is list and len(values) == len(ids) and {r['Id'] for r in values} == set(ids),
             'BUSINESS_INVENTORY_CHANGED')
        return {r['Id']: dict(image=r['Image'], restartCount=r['RestartCount'],
            state={k:r['State'][k] for k in ('Running', 'Paused', 'Restarting', 'Pid', 'StartedAt', 'FinishedAt')},
            definitionSha256=hashlib.sha256(canonical(dict({k:r[k] for k in ('Path', 'Args', 'HostConfig', 'Config')},
                Mounts=sorted(r['Mounts'], key=lambda m:m['Destination'])))).hexdigest()) for r in values}

    def guard(self):
        service = self.spec['unit']['requiredHistoryGuard']; value = self.properties(service)
        need(value['ActiveState'] == 'active' and value['SubState'] == 'exited' and
             self.run(['systemctl', 'is-enabled', service]).strip() == b'enabled', 'HISTORY_GUARD_NOT_ACTIVE')
        for ref in self.spec['unit']['historyUnitPins']:
            need(self.pin(ref['path']) == ref, 'HISTORY_GUARD_PIN_CHANGED')
        return value

    def retained_custody(self):
        custody = self.spec['previousCustody']
        if custody is None:
            need(self.spec['oldReceiptPin'] is None and self.spec['originalInventory'] is None, 'UNEXPECTED_RECEIPT')
            return None
        rows = [r for r in self.spec['current']['controllers'] if r['service'] == custody['service']]
        need(len(rows) == 1, 'PREVIOUS_CUSTODY_BINDING_CHANGED'); old = rows[0]
        need(custody['targetConfigRef'] == self.spec['targetConfigRef'] and
             custody['selectedOwnerPin'] == old['ownerConfigurationPin'] and
             custody['selectedControlPin'] == old['controlConfigurationPin'], 'PREVIOUS_CUSTODY_BINDING_CHANGED')
        layered = custody.get('schemaVersion') == 'MainProgramReceiptCustody/v1'
        terminal = custody['selectedCurrentReceiptPin'] if layered else custody['steps'][-1]['currentReceiptPin']
        need(terminal == self.spec['oldReceiptPin'], 'PREVIOUS_CUSTODY_CHAIN_CHANGED')
        proof = self.verify_custody(deepcopy(custody))
        need(type(proof) is dict and proof.get('status') == 'PASS' and proof.get('serverWrites') is False and
             type(proof.get('verifiedPins')) is list, 'ORIGINAL_CUSTODY_FAILED')
        steps = custody['legacyCustody']['steps'] + custody['mainSteps'] if layered else custody['steps']
        packages = []
        for step in steps:
            ref = self.pin(Path(step['engine']) / 'package.json')
            if 'packagePin' in step: need(ref == step['packagePin'], 'HISTORICAL_PACKAGE_IDENTITY_CHANGED')
            package = self.read(ref)
            self.verify_package(dict(engine=step['engine'], fileCount=len(package['files']), fileManifestSha256=package['packageSha256']))
            packages.append(ref)
        return dict(proof, packagePins=packages)

    def original_inventory(self, custody_observation):
        inventory = self.spec['originalInventory']
        if inventory is None:
            need(custody_observation is None and self.spec['oldReceiptPin'] is None, 'UNEXPECTED_CUSTODY_OBSERVATION')
            return dict(originalPathInventoryVerified=True, verifiedPins=[])
        need(custody_observation is not None and len(inventory['evidencePins']) == inventory['protectedFiles'] and
             len({p['path'] for p in inventory['evidencePins']}) == inventory['protectedFiles'], 'ORIGINAL_INVENTORY_COUNT_CHANGED')
        active = self.spec['oldReceiptPin']; count = 0; verified = []
        for ref in inventory['evidencePins']:
            expected = active if ref['path'] == active['path'] else ref
            if ref['path'] == active['path']: count += 1
            need(self.pin(ref['path']) == expected, 'ORIGINAL_INVENTORY_PATH_CHANGED'); verified.append(expected)
        need(count == 1, 'ORIGINAL_ACTIVE_PATH_NOT_VERIFIED')
        for ref in custody_observation['verifiedPins']:
            expected = active if ref['path'] == active['path'] else ref
            need(self.pin(ref['path']) == expected, 'CUSTODY_ORIGINAL_PATH_CHANGED'); verified.append(expected)
        return dict(originalPathInventoryVerified=True, verifiedPins=verified)

    def _documents(self, documents_created):
        need(type(documents_created) is bool, 'DOCUMENT_PHASE_INVALID')
        retained, new = self.spec['retainedDocuments'], self.spec['newDocuments']
        need(len({r['path'] for r in retained + new}) == len(retained) + len(new), 'DOCUMENT_SET_COLLISION')
        for ref in retained:
            need(self.pin(ref['path']) == ref, 'RETAINED_CONFIGURATION_CHANGED')
        for ref in new:
            if documents_created: need(self.pin(ref['path']) == ref, 'CANDIDATE_CONFIGURATION_CHANGED')
            else: need(not self.paths.exists(ref['path']), 'CANDIDATE_CONFIGURATION_ALREADY_EXISTS')

    def _observe(self, *, documents_created):
        self.lock_guard(); rows = self.spec['current']['controllers']
        containers = self.snapshot(); fstab = self.pin(self.paths.fstab_path)
        mounts = self.paths.read_bytes(self.paths.mountinfo_path)
        self.original_units(); self.no_workers(rows)
        controllers = [self.verify_process(row) for row in rows]
        packages = [self.verify_package(row) for row in rows]
        guard = self.guard(); custody = self.retained_custody(); inventory = self.original_inventory(custody)
        for ref in self.spec['historyPins']:
            need(self.pin(ref['path']) == ref, 'HISTORICAL_METADATA_CHANGED')
        for ref in self.spec['sourceEvidencePins']: self.read(ref)
        self._documents(documents_created)
        need(self.snapshot() == containers and self.pin(self.paths.fstab_path) == fstab and
             self.paths.read_bytes(self.paths.mountinfo_path) == mounts, 'BUSINESS_OR_MOUNTS_CHANGED')
        self.lock_guard()
        return dict(controllers=controllers, containers=containers, fstabPin=fstab,
            mountinfoSha256=hashlib.sha256(mounts).hexdigest(), historyGuard=guard,
            previousCustodyObservation=custody, originalInventoryObservation=inventory,
            packagePins=packages, documentsCreated=documents_created)

    def before(self):
        return self._observe(documents_created=False)

    def preserve(self, before, *, documents_created):
        self.lock_guard()
        need(type(before) is dict and before.get('documentsCreated') is False, 'RUNTIME_BEFORE_REQUIRED')
        current = self._observe(documents_created=documents_created)
        need({k:v for k,v in current.items() if k != 'documentsCreated'} ==
             {k:v for k,v in before.items() if k != 'documentsCreated'}, 'RUNTIME_ORIGINALS_CHANGED')
        self.lock_guard()
        return current
