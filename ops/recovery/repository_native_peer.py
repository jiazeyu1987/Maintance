"""Root Linux custodian, inherited W02 AF_UNIX peer and existing native verifier.

The launcher and verifier select an independently signed host-local configuration.
The persistent custodian owns the socket, resource locks, observations and actual
owner child through explicit publication release. No channel is reconnected.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import selectors
import re
import socket
import stat
import struct
import subprocess
import sys
import time

from repository_native_readback import SmbReadback
from repository_records import (Configuration, Deadline, RepositoryError, absolute,
    atomic_output, canonical, document, exact, pin_file, read_pin, require,
    safe_path, sign_record, signed_pin, utc, write_new)

MAX_FRAME = 96 * 1024 * 1024


def private(path, directory=False):
    path = safe_path(path)
    info = path.stat()
    require(os.name == 'posix' and sys.platform.startswith('linux') and os.geteuid() == 0 and
            info.st_uid == info.st_gid == 0 and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600),
            'REPOSITORY_NATIVE_PRIVATE_PREREQUISITE_REQUIRED')
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
            'REPOSITORY_NATIVE_PRIVATE_PREREQUISITE_REQUIRED')
    return path


def process_identity(pid, program_pin):
    require(type(pid) is int and pid > 0, 'REPOSITORY_NATIVE_PROCESS_INVALID')
    root = Path('/proc') / str(pid)
    raw = (root / 'stat').read_bytes()
    fields = raw[raw.rfind(b')') + 2:].split()
    require(len(fields) > 19 and fields[0] not in (b'Z', b'X'), 'REPOSITORY_NATIVE_PROCESS_LOST')
    credentials = {line.split(b':', 1)[0]: line.split(b':', 1)[1].split()
                   for line in (root / 'status').read_bytes().splitlines()
                   if line.startswith((b'Uid:', b'Gid:'))}
    require(credentials == {b'Uid': [b'0'] * 4, b'Gid': [b'0'] * 4}, 'REPOSITORY_NATIVE_PROCESS_AUTHORITY_LOST')
    require(os.fsencode(program_pin['path']) in (root / 'cmdline').read_bytes().split(b'\0'),
            'REPOSITORY_NATIVE_PROCESS_PROGRAM_CHANGED')
    read_pin(program_pin, 1024 * 1024)
    return dict(pid=pid, processStartTicks=int(fields[19]),
                hostBootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
                pidNamespace=os.readlink(root / 'ns/pid'), mountNamespace=os.readlink(root / 'ns/mnt'),
                programPin=program_pin)


def pinned_private(reference, limit=64 * 1024 * 1024):
    private(reference['path'])
    return read_pin(reference, limit)


def write_private(path, value):
    safe_path(path.parent)
    raw = canonical(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return pin_file(path)


def executable(reference):
    path = safe_path(reference['path'])
    info = path.stat()
    require(info.st_uid == info.st_gid == 0 and not stat.S_IMODE(info.st_mode) & 0o022 and
            stat.S_ISREG(info.st_mode) and os.access(path, os.X_OK),
            'REPOSITORY_NATIVE_EXECUTABLE_UNTRUSTED')
    return read_pin(reference, 64 * 1024 * 1024)


class PeerConfiguration:
    def __init__(self, service_pin, peer_pin, request_pin):
        require(os.name == 'posix' and sys.platform.startswith('linux') and os.geteuid() == 0,
                'REPOSITORY_NATIVE_LINUX_ROOT_REQUIRED')
        # The installation authority selects native code originals separately
        # from the Windows publisher's originals; neither Pin is rewritten.
        service = document(read_pin(service_pin))
        selected = signed_pin(peer_pin, service['authorityKeyPins'])
        native_lab = service['schemaVersion'] == 'RepositoryNativeServiceConfig/v1'
        if native_lab:
            from repository_native_lab import ROLES
            require(selected['schemaVersion'] == 'RepositoryNativePeerConfig/v2' and
                    set(selected['nativeImplementationPins']) == set(ROLES),
                    'REPOSITORY_NATIVE_IMPLEMENTATION_PINS_REQUIRED')
        else:
            pinned_private(selected['hostViewPin'])
        require(type(selected['nativeImplementationPins']) is dict and (native_lab or
                set(selected['nativeImplementationPins']) == {'records', 'catalog', 'retention', 'cli',
                    'nativeBridge', 'installerProgram', 'publishProgram', 'binding', 'nativePeer',
                    'nativeReadback', 'hostView', 'wslCarrier', 'wslDispatcher'}),
                'REPOSITORY_NATIVE_IMPLEMENTATION_PINS_REQUIRED')
        for reference in selected['nativeImplementationPins'].values():
            pinned_private(reference)
        self.service = (Configuration(service_pin) if native_lab else
                        Configuration(service_pin, native_implementation=selected['nativeImplementationPins'],
                                      host_view_pin=selected['hostViewPin']))
        self.request_pin, self.request = request_pin, document(read_pin(request_pin))
        self.service.request(self.request)
        self.service.authorization(self.request, self.request['sourceOrTargetRef'])
        self.source_pin = self.request['sourceOrTargetRef']
        self.source = document(read_pin(self.source_pin))
        require(self.source['nativePeerConfigPin'] == peer_pin, 'REPOSITORY_NATIVE_CONFIG_NOT_SELECTED')
        self.pin = peer_pin
        self.value = signed_pin(peer_pin, self.service.value['authorityKeyPins'])
        fields = 'schemaVersion repositoryId sourceIdentityPin programPin ownerPythonPin ownerEntryPin ownerDependencyPins recipeTemplatePin assemblyTemplatePin sessionRoot custodyPaths resourceRoots sourceRoots sourceRootProofPins writerContainers dockerPin nftPin writerRulesSha256 readbackConfig signingKeyPin nativeImplementationPins '
        exact(self.value, fields + ('executionHostPin labScopePin' if native_lab else 'hostViewPin'),
              'RepositoryNativePeerConfig/v2' if native_lab else 'RepositoryNativePeerConfig/v1')
        if native_lab:
            require(self.value['executionHostPin'] == self.service.value['executionHostPin'] and
                    self.value['labScopePin'] == self.service.value['labScopePin'] and
                    self.value['nativeImplementationPins'] == {k:self.service.implementation[k]
                        for k in selected['nativeImplementationPins']}, 'REPOSITORY_NATIVE_PEER_PROFILE_MISMATCH')
        require(self.value['repositoryId'] == self.service.value['repositoryId'] and
                self.value['sourceIdentityPin'] == self.service.policy['sourceIdentityPin'] and
                absolute(self.value['programPin']['path']) == Path(__file__).absolute(),
                'REPOSITORY_NATIVE_CONFIG_SCOPE_MISMATCH')
        require(self.value['programPin'] in self.source['nativeVerifierCommand']['programPins'] and
                self.value['programPin'] in self.source['ownerCommand']['programPins'],
                'REPOSITORY_NATIVE_PROGRAM_NOT_APPROVED')
        require(self.value['nativeImplementationPins']['nativePeer'] == self.value['programPin'],
                'REPOSITORY_NATIVE_PEER_PROGRAM_CHANGED')
        for name in ('programPin', 'ownerEntryPin', 'recipeTemplatePin',
                     'assemblyTemplatePin', 'signingKeyPin'):
            pinned_private(self.value[name])
        for name in ('ownerPythonPin', 'dockerPin', 'nftPin'):
            executable(self.value[name])
        require(type(self.value['ownerDependencyPins']) is list and self.value['ownerDependencyPins'],
                'REPOSITORY_NATIVE_OWNER_DEPENDENCIES_REQUIRED')
        approved = {absolute(reference['path']): reference for reference in self.value['ownerDependencyPins']}
        approved[absolute(self.value['ownerEntryPin']['path'])] = self.value['ownerEntryPin']
        for path in absolute(self.value['ownerEntryPin']['path']).parent.glob('*.py'):
            require(path in approved, 'REPOSITORY_NATIVE_OWNER_DEPENDENCY_NOT_APPROVED')
            pinned_private(approved[path])
        require(type(self.value['sourceRoots']) is list and self.value['sourceRoots'] and
                type(self.value['sourceRootProofPins']) is list and len(self.value['sourceRootProofPins']) == len(self.value['sourceRoots']),
                'REPOSITORY_NATIVE_SOURCE_ROOTS_REQUIRED')
        for path, reference in zip(self.value['sourceRoots'], self.value['sourceRootProofPins']):
            root = safe_path(path)
            require(root.is_dir(), 'REPOSITORY_NATIVE_SOURCE_ROOT_REQUIRED')
            proof = document(pinned_private(reference))
            require(proof == dict(path=str(root), device=root.stat().st_dev, inode=root.stat().st_ino),
                    'REPOSITORY_NATIVE_SOURCE_ROOT_CHANGED')
        base = private(self.value['sessionRoot'], directory=True)
        self.root = base / hashlib.sha256(self.request['requestId'].encode('utf-8')).hexdigest()
        if self.root.exists():
            private(self.root, directory=True)
        self.deadline = Deadline(self.request['deadlineMilliseconds'])

    def current(self):
        self.deadline.check()
        read_pin(self.pin)
        if self.service.native_lab:
            self.service.authorization(self.request, self.source_pin)
        else:
            pinned_private(self.value['hostViewPin'])
        read_pin(self.source_pin)
        for reference in self.value['nativeImplementationPins'].values():
            pinned_private(reference)
        for name in ('programPin', 'ownerEntryPin', 'recipeTemplatePin', 'assemblyTemplatePin'):
            pinned_private(self.value[name])
        for reference in self.value['ownerDependencyPins']:
            pinned_private(reference)
        for path, reference in zip(self.value['sourceRoots'], self.value['sourceRootProofPins']):
            root = safe_path(path)
            require(document(pinned_private(reference)) ==
                    dict(path=str(root), device=root.stat().st_dev, inode=root.stat().st_ino),
                    'REPOSITORY_NATIVE_SOURCE_ROOT_CHANGED')
        self.service.authorization(self.request, self.source_pin)

    def signed(self, value):
        self.current()
        return sign_record(value, self.value['signingKeyPin'], self.source['nativeAuthorityKeyPins'])


class Custodian:
    def __init__(self, config):
        self.config, self.owner = config, None
        self.root = config.root
        self.files, self.sequence = [], 0
        self.binding = document(pinned_private(config.value['assemblyTemplatePin']))['binding']
        self.binding_sha = hashlib.sha256(canonical(self.binding)).hexdigest()
        self.originals = {}
        self.release = False
        self.initialization_descriptor = None
        self.initialization_pin = None
        self.initialization_originals = {}
        self.program = config.value['programPin']
        self.identity = process_identity(os.getpid(), self.program)
        assembly = document(pinned_private(config.value['assemblyTemplatePin']))
        capture = document(pinned_private(assembly['captureRequestPin']))
        self.original_roots = [private(path, directory=True) for path in
            (assembly['controlRoot'], assembly['registryRoot'], capture['claimRoot'])]
        self.original_roots.append(self.root)
        self.approved_originals = {}
        def collect(value):
            if type(value) is dict:
                if set(value) == {'path', 'bytes', 'sha256'}:
                    self.approved_originals[value['path']] = value
                else:
                    for item in value.values(): collect(item)
            elif type(value) is list:
                for item in value: collect(item)
        collect(config.value); collect(assembly)
        collect(document(pinned_private(config.value['recipeTemplatePin'])))

    def read_original(self, reference):
        path = absolute(reference['path'])
        require(self.approved_originals.get(reference['path']) == reference or
                any(root in path.parents for root in self.original_roots),
                'REPOSITORY_NATIVE_ORIGINAL_SCOPE_MISMATCH')
        return pinned_private(reference)

    def initialization_holder(self, descriptor):
        lab = self.config.service.native_lab
        fields = 'schemaVersion configurationPin sourceConfigPin peerConfigPin assemblyPin requestPin sourceContextPin installedContextPin holder'
        exact(descriptor, fields + (' labContextPin' if lab else ''),
              'RepositoryLabInitialized/v1' if lab else 'ReleaseProductionBackupInitialized/v2')
        if lab:
            require(descriptor['labContextPin']==self.config.service.lab_context_pin,
                    'REPOSITORY_LAB_INITIALIZATION_CONTEXT_CHANGED')
        require(self.owner is not None and self.owner.poll() is None and
                process_identity(self.owner.pid, self.config.value['ownerEntryPin']) == self.owner_identity,
                'REPOSITORY_INITIALIZATION_OWNER_LOST')
        require(descriptor['configurationPin'] == self.config.service.pin and
                descriptor['sourceConfigPin'] == self.config.source_pin and
                descriptor['peerConfigPin'] == self.config.pin and descriptor['requestPin'] == self.config.request_pin and
                descriptor['assemblyPin'] == self.assembly_pin, 'REPOSITORY_INITIALIZATION_BINDING_CHANGED')
        holder = descriptor['holder']
        require(type(holder) is dict and set(holder) == {'pid', 'fd', 'device', 'inode', 'claimRoot', 'claimBindingSha256'} and
                all(type(holder[key]) is int for key in ('pid', 'fd', 'device', 'inode')) and
                holder['pid'] == self.owner.pid and holder['fd'] >= 0 and holder['device'] >= 0 and holder['inode'] > 0,
                'REPOSITORY_INITIALIZATION_HOLDER_INVALID')
        recipe = document(pinned_private(self.config.value['recipeTemplatePin']))
        require(recipe['schemaVersion'] == ('backup-lab-normal-owner-recipe-template/v1' if lab else 'backup-normal-owner-recipe/v2') and
                holder['claimRoot'] == recipe['claimRoot'] and
                holder['claimBindingSha256'] == hashlib.sha256((json.dumps(recipe['claimBinding'],
                    sort_keys=True, separators=(',', ':'))+'\n').encode('utf-8')).hexdigest(),
                'REPOSITORY_INITIALIZATION_CLAIM_CHANGED')
        lock = private(absolute(holder['claimRoot']) / 'ownership.lock').stat()
        fd_root = Path('/proc') / str(holder['pid'])
        actual = (fd_root / 'fd' / str(holder['fd'])).stat()
        require((actual.st_dev, actual.st_ino) == (lock.st_dev, lock.st_ino) == (holder['device'], holder['inode']) and
                stat.S_ISREG(actual.st_mode) and actual.st_nlink == lock.st_nlink == 1,
                'REPOSITORY_INITIALIZATION_FD_CHANGED')
        locks = re.findall(r'^lock:\s+\d+:\s+FLOCK\s+ADVISORY\s+WRITE\s+(\d+)\s+([0-9a-fA-F]+):([0-9a-fA-F]+):(\d+)\s+0\s+EOF\s*$',
                           (fd_root / 'fdinfo' / str(holder['fd'])).read_text(encoding='ascii'), re.M)
        require(any((int(pid), int(major, 16), int(minor, 16), int(inode)) ==
                    (holder['pid'], os.major(holder['device']), os.minor(holder['device']), holder['inode'])
                    for pid, major, minor, inode in locks), 'REPOSITORY_INITIALIZATION_FLOCK_UNPROVEN')
        assembly = document(pinned_private(self.assembly_pin))
        refs = assembly['inputReferences']
        require(refs['source_context'] == descriptor['sourceContextPin'] and
                refs['installed_context'] == descriptor['installedContextPin'] and
                assembly['binding']['installedContextSha256'] == descriptor['installedContextPin']['sha256'],
                'REPOSITORY_INITIALIZATION_ORIGINAL_CHANGED')
        for reference in (descriptor['sourceContextPin'], descriptor['installedContextPin']):
            pinned_private(reference, 16384)
        if self.initialization_descriptor is not None:
            require(canonical(descriptor) == canonical(self.initialization_descriptor),
                    'REPOSITORY_INITIALIZATION_HOLDER_CHANGED')
            for path, (reference, identity) in self.initialization_originals.items():
                pinned_private(reference)
                info = private(path).stat()
                require((info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) == identity,
                        'REPOSITORY_INITIALIZATION_ORIGINAL_CHANGED')
        self.check()

    def acquire(self):
        import fcntl
        require(type(self.config.value['custodyPaths']) is list and self.config.value['custodyPaths'],
                'REPOSITORY_NATIVE_CUSTODY_REQUIRED')
        for reference in self.config.value['custodyPaths']:
            path = private(reference['path'])
            pinned_private(reference)
            fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                info = os.fstat(fd)
                self.files.append((fd, reference, (info.st_dev, info.st_ino)))
            except BaseException:
                os.close(fd)
                raise
        self.check()

    def check(self):
        self.config.current()
        require(process_identity(os.getpid(), self.program) == self.identity,
                'REPOSITORY_NATIVE_CUSTODY_LOST')
        for fd, reference, identity in self.files:
            info = os.fstat(fd)
            path = private(reference['path']).stat()
            require((info.st_dev, info.st_ino) == identity == (path.st_dev, path.st_ino),
                    'REPOSITORY_NATIVE_CUSTODY_LOST')
            pinned_private(reference)

    def save(self, value, role):
        self.check()
        require(type(role) is str and re.fullmatch('[a-z0-9-]{1,128}', role),
                'REPOSITORY_NATIVE_RECORD_ROLE_INVALID')
        self.sequence += 1
        reference = write_private(self.root / ('observation-' + str(self.sequence) + '-' + role + '.json'), value)
        self.originals[reference['path']] = reference
        return reference

    def resource(self, target, peak):
        roots = self.config.value['resourceRoots']
        require(target in roots, 'REPOSITORY_NATIVE_RESOURCE_REQUIRED')
        resource = roots[target]
        require(type(resource) is dict and set(resource) == {'root', 'identityPin', 'observationPin', 'reserveBytes', 'budgetBytes'},
                'REPOSITORY_NATIVE_RESOURCE_INVALID')
        path = private(resource['root'], directory=True)
        actual, disk = path.stat(), os.statvfs(path)
        identity = document(pinned_private(resource['identityPin']))
        require(identity == dict(device=actual.st_dev, inode=actual.st_ino, fragmentBytes=disk.f_frsize,
                                blockBytes=disk.f_bsize, filesystemId=disk.f_fsid),
                'REPOSITORY_NATIVE_RESOURCE_CHANGED')
        available = disk.f_bavail * disk.f_frsize
        require(type(peak) is int and peak > 0 and peak <= resource['budgetBytes'] and
                available >= peak + resource['reserveBytes'], 'REPOSITORY_NATIVE_CAPACITY_INSUFFICIENT')
        return dict(root=str(path), device=actual.st_dev, inode=actual.st_ino,
                    availableBytes=available, allocatedUpperBoundBytes=peak)

    def source_protection(self):
        self.check()
        require(self.config.value['writerContainers'], 'REPOSITORY_NATIVE_WRITER_SCOPE_REQUIRED')
        executable(self.config.value['dockerPin'])
        executable(self.config.value['nftPin'])
        listing = subprocess.run([self.config.value['dockerPin']['path'], 'ps', '-aq', '--no-trunc'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=self.config.deadline.remaining(), check=True)
        all_ids = listing.stdout.decode('ascii').split()
        expected_ids = {value['containerId'] for value in self.config.value['writerContainers']}
        source_roots = [absolute(value) for value in self.config.value['sourceRoots']]
        unexpected = []
        observed_containers = []
        for container in all_ids:
            result = subprocess.run([self.config.value['dockerPin']['path'], 'inspect', '--type=container', container],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=self.config.deadline.remaining(), check=True)
            data = document(result.stdout)
            require(type(data) is list and len(data) == 1 and data[0]['Id'] == container,
                    'REPOSITORY_NATIVE_WRITER_CHANGED')
            observed_containers.append(data[0])
            for mount in data[0]['Mounts']:
                source = absolute(mount['Source'])
                if (not mount.get('RW', True)):
                    continue
                if any(source == root or root in source.parents or source in root.parents for root in source_roots):
                    if container not in expected_ids:
                        unexpected.append(container)
        require(not unexpected, 'REPOSITORY_NATIVE_UNAPPROVED_WRITER')
        for expected in self.config.value['writerContainers']:
            container = expected['containerId']
            data = [value for value in observed_containers if value['Id'] == container]
            require(len(data) == 1 and data[0]['Mounts'] == expected['mounts'] and
                    data[0]['NetworkSettings']['Ports'] == expected['ports'],
                    'REPOSITORY_NATIVE_WRITER_CHANGED')
        rules = subprocess.run([self.config.value['nftPin']['path'], '-j', 'list', 'ruleset'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=self.config.deadline.remaining(), check=True)
        require(hashlib.sha256(rules.stdout).hexdigest() == self.config.value['writerRulesSha256'],
                'REPOSITORY_NATIVE_WRITER_PROTECTION_LOST')
        after_listing = subprocess.run([self.config.value['dockerPin']['path'], 'ps', '-aq', '--no-trunc'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=self.config.deadline.remaining(), check=True)
        require(after_listing.stdout == listing.stdout, 'REPOSITORY_NATIVE_WRITER_SET_CHANGED')
        self.check()

    def observe(self, action, payload, expected):
        self.check()
        if 'binding' in payload:
            require(payload['binding'] == self.binding, 'REPOSITORY_NATIVE_BINDING_CHANGED')
        raw = None if expected is None else self.read_original(expected)
        value = None if raw is None else document(raw)
        if action == 'allocation-local':
            proof = document(pinned_private(payload['allocationProofReference']))
            identity = document(pinned_private(payload['deviceIdentityReference']))
            root = private(payload['root'], directory=True)
            info, disk = root.stat(), os.statvfs(root)
            require(identity == dict(device=info.st_dev, inode=info.st_ino, fragmentBytes=disk.f_frsize,
                                    blockBytes=disk.f_bsize, filesystemId=disk.f_fsid) and
                    proof['verificationReference'] == expected and
                    proof['deviceIdentitySha256'] == payload['deviceIdentityReference']['sha256'] and
                    proof['rules']['allocationUnitBytes'] >= disk.f_frsize and
                    value['target'] == str(root) and value['deviceIdentityReference'] == payload['deviceIdentityReference'] and
                    value['allocationProofReference'] == payload['allocationProofReference'] and
                    value['rulesSha256'] == hashlib.sha256(canonical(proof['rules'])).hexdigest(),
                    'REPOSITORY_NATIVE_ALLOCATION_UNPROVEN')
        elif action in ('allocation-nas', 'allocation-staging'):
            target = action.split('-', 1)[1]
            observed = self.resource(target, payload['allocatedUpperBoundBytes'])
            require(value['target'] == target and value['allocatedUpperBoundBytes'] == observed['allocatedUpperBoundBytes'],
                    'REPOSITORY_NATIVE_ALLOCATION_UNPROVEN')
            require(value['resourceObservationReference'] == self.config.value['resourceRoots'][target]['observationPin'],
                    'REPOSITORY_NATIVE_RESOURCE_OBSERVATION_MISMATCH')
            document(pinned_private(value['resourceObservationReference']))
        elif action == 'admission-nas':
            candidates = [reference for reference in self.originals.values()
                          if reference['sha256'] == payload['admissionSha256']]
            require(len(candidates) == 1, 'REPOSITORY_NATIVE_ADMISSION_ORIGINAL_REQUIRED')
            expected = candidates[0]
            raw, value = pinned_private(expected), document(pinned_private(expected))
            require(value['intentReference'] == payload['intentReference'] and
                    value['admissionId'] == payload['admissionId'], 'REPOSITORY_NATIVE_ADMISSION_CHANGED')
            self.resource('nas', value['nasAllocatedUpperBoundBytes'])
        elif action == 'admission-staging':
            self.resource('staging', payload['peakAllocatedBytes'])
            require(value['intentSha256'] == payload['intentSha256'] == payload['intentReference']['sha256'] and
                    value['peakAllocatedBytes'] == payload['peakAllocatedBytes'], 'REPOSITORY_NATIVE_ADMISSION_CHANGED')
        elif action == 'control-budget':
            # Relative budgets are validated on each side; remote absolute clock
            # ticks cannot be compared, and transport time cannot increase ours.
            require(raw is not None and type(payload['remainingMilliseconds']) is int and
                    0 < payload['remainingMilliseconds'] <= self.config.request['deadlineMilliseconds'],
                    'REPOSITORY_NATIVE_BUDGET_CHANGED')
            require(value['binding'] == self.binding and
                    (payload['sequence'] == 1 and 'sequence' not in value or
                     value.get('sequence') == payload['sequence'] - 1),
                    'REPOSITORY_NATIVE_BUDGET_CHANGED')
            self.config.deadline.end = min(self.config.deadline.end,
                time.monotonic() + payload['remainingMilliseconds'] / 1000)
        elif action == 'repository-parent':
            from repository_catalog import Catalog
            catalog = Catalog(self.config.service, self.config.deadline)
            chain = catalog.chain(payload['repositoryPointPin'])
            require(expected == payload['repositoryPointPin'] and chain, 'REPOSITORY_NATIVE_PARENT_INVALID')
            capture = document(pinned_private(payload['capturePointPin']))
            require(capture['backupId'] == chain[-1][1]['backupId'] and
                    capture['commonRecoveryPoint'] == chain[-1][1]['commonRecoveryPoint'],
                    'REPOSITORY_NATIVE_PARENT_INVALID')
        elif action == 'writer-protection':
            inventory = document(self.read_original(payload['sourceInventoryReference']))
            assembly = document(pinned_private(self.assembly_pin if self.config.service.native_lab
                else self.config.value['assemblyTemplatePin']))
            catalog_binding = document(self.read_original(assembly['catalogBindingPin']))
            require(inventory['schemaVersion'] == ('backup-lab-original-sources/v1' if self.config.service.native_lab
                    else 'release-formal-production-a-original-sources/v1') and
                    inventory['claimBindingSha256'] == self.binding['claimBindingSha256'] and
                    catalog_binding['writerReferences'] == payload['writerReferences'],
                    'REPOSITORY_NATIVE_WRITER_SCOPE_MISMATCH')
            for writer in payload['writerReferences']:
                self.read_original(writer['protectionReference'])
            self.source_protection()
            value = dict(schemaVersion='backup-native-writer-protection/v1', binding=self.binding,
                sourceInventoryReference=payload['sourceInventoryReference'], writerReferences=payload['writerReferences'],
                authorHeld=True, protectionHeld=True)
            expected = self.save(value, action)
            raw = pinned_private(expected)
        else:
            raise RepositoryError('REPOSITORY_NATIVE_ACTION_INVALID')
        require(raw is not None, 'REPOSITORY_NATIVE_OBSERVATION_REQUIRED')
        self.check()
        return raw, expected

    def socket_request(self, channel):
        def take(count):
            output = bytearray()
            while len(output) < count:
                channel.settimeout(self.config.deadline.remaining())
                chunk = channel.recv(count - len(output))
                if not chunk:
                    raise EOFError('REPOSITORY_NATIVE_OWNER_CHANNEL_LOST')
                output.extend(chunk)
            return bytes(output)
        length = struct.unpack('!I', take(4))[0]
        require(0 < length <= 1048576, 'REPOSITORY_NATIVE_FRAME_TOO_LARGE')
        request = document(take(length))
        exact(request, 'schemaVersion action nonce sequence bindingSha256 input expectedReference',
              'backup-native-observation-request/v1')
        require(request['bindingSha256'] == self.binding_sha and request['sequence'] == self.channel_sequence + 1,
                'REPOSITORY_NATIVE_SEQUENCE_INVALID')
        require(type(request['sequence']) is int and type(request['input']) is dict and
                type(request['nonce']) is str and re.fullmatch('[0-9a-f]{64}', request['nonce']),
                'REPOSITORY_NATIVE_REQUEST_INVALID')
        self.channel_sequence = request['sequence']
        raw, reference = self.observe(request['action'], request['input'], request['expectedReference'])
        answer = canonical(dict(schemaVersion='backup-native-observation-reply/v1', nonce=request['nonce'],
            sequence=request['sequence'], bindingSha256=self.binding_sha, reference=reference,
            payloadBase64=base64.b64encode(raw).decode('ascii')))
        require(len(answer) <= MAX_FRAME, 'REPOSITORY_NATIVE_FRAME_TOO_LARGE')
        channel.sendall(struct.pack('!I', len(answer)) + answer)

    def adapter_request(self, invocation):
        exact(invocation, 'schemaVersion action challenge request sourceConfigPin remainingMilliseconds',
              'RepositoryNativeRequest/v1')
        require(invocation['sourceConfigPin'] == self.config.source_pin and
                invocation['request']['operationRequestPin'] == self.config.request_pin,
                'REPOSITORY_NATIVE_REQUEST_SCOPE_MISMATCH')
        require(type(invocation['remainingMilliseconds']) is int and
                0 < invocation['remainingMilliseconds'] <= 7200000,
                'REPOSITORY_NATIVE_REQUEST_BUDGET_INVALID')
        action_deadline = Deadline(min(invocation['remainingMilliseconds'],
                                       int(self.config.deadline.remaining() * 1000)))
        action, payload = invocation['action'], invocation['request']['payload']
        if action == 'observe-initialized':
            require(type(payload) is dict and set(payload) == {'descriptor', 'currentInput'},
                    'REPOSITORY_INITIALIZATION_INPUT_INVALID')
            descriptor, current = payload['descriptor'], payload['currentInput']
            self.initialization_holder(descriptor)
            if self.config.service.native_lab:
                exact(current, 'schemaVersion configurationPin labContextPin','RepositoryLabInitializerInput/v1')
                require(current['configurationPin']==self.config.service.pin and
                    current['labContextPin']==self.config.service.lab_context_pin,
                    'REPOSITORY_LAB_INITIALIZATION_CONTEXT_CHANGED')
                if self.initialization_pin is None:
                    self.initialization_descriptor = document(canonical(descriptor))
                    for reference in (descriptor['sourceContextPin'],descriptor['installedContextPin'],descriptor['labContextPin']):
                        info=private(reference['path']).stat()
                        self.initialization_originals[reference['path']] = (reference,
                            (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns))
                    self.initialization_pin=self.save(self.config.signed(dict(
                        schemaVersion='RepositoryNativeInitializationObservation/v1',descriptor=descriptor,
                        binding=self.binding,requestPin=self.config.request_pin,ownerIdentity=self.owner_identity,at=utc())),action)
                return dict(state='CURRENT',descriptor=descriptor,observationPin=self.initialization_pin)
            exact(current, 'schemaVersion configurationPin transport', 'ReleaseProductionBackupInitializerInput/v1')
            require(current['configurationPin'] == self.config.service.pin, 'REPOSITORY_INITIALIZATION_BINDING_CHANGED')
            transport = current['transport']
            require(type(transport) is dict and set(transport) == {'context_raw', 'expected_context_sha256', 'operation_raw', 'gate_raw'},
                    'REPOSITORY_INITIALIZATION_INPUT_INVALID')
            context_raw = base64.b64decode(transport['context_raw'], validate=True)
            source_context = document(pinned_private(descriptor['sourceContextPin'], 16384))
            installed = document(pinned_private(descriptor['installedContextPin'], 16384))
            require(pinned_private(descriptor['sourceContextPin'], 16384) == context_raw and
                    descriptor['sourceContextPin']['sha256'] == transport['expected_context_sha256'] ==
                    self.binding['sourceContextSha256'], 'REPOSITORY_INITIALIZATION_ORIGINAL_CHANGED')
            for key in ('expectedAttemptId', 'expectedLeaseTokenDigest'):
                require(source_context[key] == installed[key], 'REPOSITORY_INITIALIZATION_BINDING_CHANGED')
            refs = [descriptor['sourceContextPin'], descriptor['installedContextPin']]
            for name in ('operation', 'gate'):
                raw = base64.b64decode(transport[name+'_raw'], validate=True)
                reference = dict(installed[name], bytes=len(raw))
                require(pinned_private(reference, 1048576) == raw and source_context[name]['sha256'] == reference['sha256'],
                        'REPOSITORY_INITIALIZATION_ORIGINAL_CHANGED')
                refs.append(reference)
            if self.initialization_pin is None:
                self.initialization_descriptor = document(canonical(descriptor))
                for reference in refs:
                    info = private(reference['path']).stat()
                    self.initialization_originals[reference['path']] = (reference,
                        (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
                self.initialization_holder(descriptor)
                self.initialization_pin = self.save(self.config.signed(dict(
                    schemaVersion='RepositoryNativeInitializationObservation/v1', descriptor=descriptor,
                    binding=self.binding, requestPin=self.config.request_pin, ownerIdentity=self.owner_identity, at=utc())), action)
            return dict(state='CURRENT', descriptor=descriptor, observationPin=self.initialization_pin)
        if action == 'read-original':
            raw = self.read_original(payload['pin'])
            return dict(bytesBase64=base64.b64encode(raw).decode('ascii'))
        if action == 'publish-control':
            raw = base64.b64decode(payload['bytesBase64'], validate=True)
            value = document(raw)
            require(payload['binding'] == self.binding, 'REPOSITORY_NATIVE_BINDING_CHANGED')
            reference = self.save(value, payload['role'])
            # Preserve original bytes, including the producer's encoding.
            if canonical(value) != raw:
                path = self.root / ('control-' + str(self.sequence) + '.raw')
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, 'wb') as out:
                    out.write(raw); out.flush(); os.fsync(out.fileno())
                os.chmod(path, 0o600)
                reference = pin_file(path)
                self.originals[reference['path']] = reference
            return dict(pin=reference)
        if action == 'observe-readback':
            sealed = payload['phase'] == 'SEALED_MATERIAL'
            archive = payload['archive']['archivePath'] if sealed else payload['archivePath']
            material = payload['material'] if sealed else None
            expected = document(read_pin(material['payloadTreePin'])) if sealed else payload['expectedEntries']
            with SmbReadback(self.config.value['readbackConfig'], action_deadline) as reader:
                connection_id, original_records = reader.verify(archive, expected, material)
            observation = self.save(dict(schemaVersion='RepositorySmbObservation/v1', connectionId=connection_id,
                archivePath=archive, payloadTree=expected, at=utc()), action)
            result = dict(schemaVersion='RepositoryNativeReadback/v1' if sealed else 'RepositoryNativePayloadReadback/v1',
                binding=self.binding, archivePath=archive, payloadTree=expected, independentConnectionId=connection_id,
                nativeEvidencePins=[observation], serverDurabilityVerified=False)
            if self.initialization_pin is not None:
                if not sealed: self.initialization_holder(self.initialization_descriptor)
                result['nativeEvidencePins'].append(self.initialization_pin)
            if sealed:
                require(self.owner_terminal is not None and self.owner_terminal['state'] == 'EXITED' and
                        self.owner_terminal['actualExitCode'] == 0,
                        'REPOSITORY_NATIVE_ORIGINAL_EXIT_REQUIRED')
                result['nativeEvidencePins'].append(self.terminal_pin)
                result.update(manifestPin=material['manifestPin'], payloadTreePin=material['payloadTreePin'],
                              payloadRefs=material['payloadRefs'], originalRecordsPin=original_records)
            return result
        if action == 'release-peer':
            require(self.owner_terminal is not None and self.owner_terminal['actualExitCode'] == 0 and
                    self.owner_terminal['state'] == 'EXITED' and
                    payload['publicationPin'] is not None, 'REPOSITORY_NATIVE_RELEASE_UNPROVEN')
            publication = document(read_pin(payload['publicationPin']))
            require(publication['actualExitCode'] == 0, 'REPOSITORY_NATIVE_RELEASE_UNPROVEN')
            if self.config.service.native_lab:
                exit_record = signed_pin(publication['originalExitEvidencePin'], self.config.service.value['evidenceKeyPins'])
                process = document(read_pin(exit_record['originalProcessPin']))
                require(exit_record['operationId'] == self.config.request['operationId'] and
                    exit_record['repositoryId'] == self.config.service.value['repositoryId'] and
                    process['requestPin'] == self.config.request_pin and process['binding'] == self.binding and
                    process['ownerPid'] == self.owner_identity['pid'], 'REPOSITORY_NATIVE_RELEASE_UNPROVEN')
            from repository_catalog import Catalog
            candidate = {key: document(read_pin(publication['manifestPin']))[key] for key in
                         ('backupId','generationId','pointType','parentPointPins','commonRecoveryPoint','payloadRefs')}
            candidate['manifestPin'] = publication['manifestPin']
            Catalog(self.config.service, self.config.deadline).evidence(publication | candidate)
            self.release = True
            return dict(state='RELEASED', terminalPin=self.terminal_pin)
        if action == 'observe-capture':
            if self.initialization_descriptor is not None: self.initialization_holder(self.initialization_descriptor)
            header = document(pinned_private(payload['archiveHeaderPin']))
            tree = document(pinned_private(header['manifestReference']))
            assembly = document(pinned_private(self.assembly_pin if self.config.service.native_lab
                else self.config.value['assemblyTemplatePin']))
            capture = document(pinned_private(assembly['captureRequestPin']))
            claim_root = absolute(capture['claimRoot'])
            inputs = document(pinned_private(pin_file(claim_root / 'capture-recovery-inputs.json')))
            point = document(pinned_private(inputs['capturePointPin']))
            require(header['binding'] == self.binding and point['backupId'] == inputs['backupId'],
                    'REPOSITORY_NATIVE_CAPTURE_CHANGED')
            parents = []
            from repository_catalog import Catalog
            if self.config.request['selectedPointPin'] is not None:
                parents = [r[0] for r in Catalog(self.config.service, self.config.deadline).chain(self.config.request['selectedPointPin'])]
            metadata = dict(schemaVersion='RepositoryCaptureMetadata/v1', backupId=inputs['backupId'],
                generationId=inputs['generationId'], pointType=inputs['pointType'], parentPointPins=parents,
                commonRecoveryPoint=inputs['recoveryPoint'], sourceIdentityPin=self.config.service.policy['sourceIdentityPin'],
                createdAt=utc(), versionPins=inputs['semanticSupplement']['versionPins'],
                toolPins=self.config.service.policy['supportedToolPins'])
            evidence = self.save(dict(schemaVersion='RepositoryNativeCaptureObservation/v1',
                ownerIdentity=self.owner_identity, archiveHeaderPin=payload['archiveHeaderPin'], at=utc()), action)
            return dict(schemaVersion='RepositoryNativeCapture/v1', repositoryId=self.config.value['repositoryId'],
                operationId=self.config.request['operationId'], requestPin=self.config.request_pin,
                sourceConfigPin=self.config.source_pin, binding=self.binding,
                originalProcessPin=payload['originalProcessPin'], archiveHeaderPin=payload['archiveHeaderPin'],
                payloadTree=tree, metadata=metadata, nativeEvidencePins=[evidence] +
                    ([self.initialization_pin] if self.initialization_pin is not None else []))
        require(action in {'observe-owner', 'observe-prepared', 'observe-intent', 'observe-workspace', 'read-current-input'},
                'REPOSITORY_NATIVE_ACTION_INVALID')
        if action == 'observe-owner':
            if self.initialization_descriptor is not None: self.initialization_holder(self.initialization_descriptor)
            require(self.owner is not None and self.owner.poll() is None and
                    process_identity(self.owner.pid, self.config.value['ownerEntryPin']) == self.owner_identity,
                    'REPOSITORY_NATIVE_OWNER_LOST')
            require(payload['bound']['binding'] == self.binding and
                    payload['bound']['bootstrapBinding'] == (self.config.source['bootstrapBinding']['ownerBinding']
                        if self.config.service.native_lab else self.config.source['bootstrapBinding']),
                    'REPOSITORY_NATIVE_OWNER_BINDING_CHANGED')
        if action == 'observe-prepared':
            intent = document(self.read_original(payload['intentPin']))
            require(intent['binding'] == self.binding, 'REPOSITORY_NATIVE_INTENT_BINDING_CHANGED')
        if action in ('observe-intent', 'observe-workspace'):
            raw = base64.b64decode(payload['bytesBase64'], validate=True)
            value = document(raw)
            if action == 'observe-intent':
                require(value['binding'] == self.binding, 'REPOSITORY_NATIVE_INTENT_BINDING_CHANGED')
                self.resource('staging', value['windowsStagingPeakAllocatedBytes'])
            else:
                selected = self.config.source['workspacePin']
                require(hashlib.sha256(raw).hexdigest() == selected['sha256'] and len(raw) == selected['bytes'],
                        'REPOSITORY_NATIVE_WORKSPACE_CHANGED')
        self.check()
        observation = self.save(dict(schemaVersion='RepositoryNativeObservation/v1', action=action,
            binding=self.binding, peerIdentity=self.identity, ownerIdentity=self.owner_identity, at=utc()), action)
        return dict(state='CURRENT', binding=self.binding, observationPin=observation)

    def retain_unknown(self, error):
        write_private(self.root / 'custodian-failure.json', dict(
            schemaVersion='RepositoryNativeCustodianFailure/v1', requestPin=self.config.request_pin,
            peerIdentity=self.identity, ownerIdentity=getattr(self, 'owner_identity', None),
            actualOwnerExitCode=None if self.owner is None else self.owner.poll(), state='TERMINAL_UNKNOWN',
            failureCode=error.code if isinstance(error, RepositoryError) else 'REPOSITORY_NATIVE_' + type(error).__name__.upper(), at=utc()))
        while True:
            time.sleep(1)

    def serve(self):
        try:
            self.serve_owned()
        except BaseException as error:
            if self.owner is not None:
                self.retain_unknown(error)
            for fd, _, _ in self.files:
                os.close(fd)
            raise

    def serve_owned(self):
        self.acquire()
        private(self.root, directory=True)
        inbox = self.root / 'inbox'; inbox.mkdir(mode=0o700)
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        self.channel_sequence = 0
        recipe = document(pinned_private(self.config.value['recipeTemplatePin']))
        assembly = document(pinned_private(self.config.value['assemblyTemplatePin']))
        if self.config.service.native_lab:
            from repository_native_lab import derive_owner
            recipe,assembly=derive_owner(self.config.service,self.config.source,self.config.request_pin,
                recipe,assembly,self.save)
            self.binding=assembly['binding']
            self.binding_sha=hashlib.sha256(canonical(self.binding)).hexdigest()
        channel = dict(schemaVersion='backup-native-observation-channel/v1', fd=child.fileno(),
            peerPid=os.getpid(), peerUid=0, peerGid=0, peerStartTicks=self.identity['processStartTicks'],
            hostBootId=self.identity['hostBootId'], pidNamespace=self.identity['pidNamespace'],
            mountNamespace=self.identity['mountNamespace'], programPin=self.program, bindingSha256=self.binding_sha)
        assembly['channelPin'] = write_private(self.root / 'channel.json', channel)
        self.assembly_pin = write_private(self.root / 'assembly.json', assembly)
        recipe['nativeAssemblyConfigPin'] = self.assembly_pin
        if recipe['schemaVersion'] in ('backup-normal-owner-recipe/v2', 'backup-lab-normal-owner-recipe/v1'):
            approved_initializer = (recipe['nativeInitializationProgramPin']==pin_file(Path(__file__).with_name('repository_native_initializer.py'))
                if self.config.service.native_lab else recipe['nativeInitializationProgramPin'] in self.config.value['ownerDependencyPins'])
            require(approved_initializer,
                    'REPOSITORY_INITIALIZATION_PROGRAM_NOT_APPROVED')
            pinned_private(recipe['nativeInitializationProgramPin'], 4*1024*1024)
            template = document(pinned_private(recipe['nativeInitializationConfigPin'], 65536))
            exact(template, 'schemaVersion controlRoot controlIdentity', 'ReleaseProductionBackupNativeInitializationTemplate/v1')
            require(template['controlRoot'] == assembly['controlRoot'], 'REPOSITORY_INITIALIZATION_CONTROL_CHANGED')
            profile = dict(template, schemaVersion='ReleaseProductionBackupNativeInitialization/v1',
                configurationPin=self.config.service.pin, sourceConfigPin=self.config.source_pin,
                peerConfigPin=self.config.pin, requestPin=self.config.request_pin,
                assemblyTemplatePin=self.config.value['assemblyTemplatePin'], assemblyPin=self.assembly_pin)
            if self.config.service.native_lab:
                profile['schemaVersion'] = 'RepositoryLabNativeInitialization/v1'
                profile['labContextPin'] = self.config.service.lab_context_pin
            recipe['nativeInitializationConfigPin'] = write_private(self.root / 'initialization.json', profile)
        recipe_pin = write_private(self.root / 'recipe.json', recipe)
        if self.config.service.native_lab:
            def collect_runtime(item):
                if type(item) is dict:
                    if set(item)=={'path','bytes','sha256'}:self.approved_originals[item['path']]=item
                    else:
                        for child_value in item.values():collect_runtime(child_value)
                elif type(item) is list:
                    for child_value in item:collect_runtime(child_value)
            collect_runtime(recipe);collect_runtime(assembly)
        self.owner = subprocess.Popen([self.config.value['ownerPythonPin']['path'], '-B',
            self.config.value['ownerEntryPin']['path'], '--request', recipe_pin['path'],
            '--expected-request-sha256', recipe_pin['sha256']], stdin=sys.stdin.buffer,
            stdout=sys.stdout.buffer, stderr=sys.stderr.buffer, pass_fds=(child.fileno(),))
        child.close()
        self.owner_identity = process_identity(self.owner.pid, self.config.value['ownerEntryPin'])
        self.owner_terminal, self.terminal_pin = None, None
        write_private(self.root / 'session.json', self.config.signed(dict(schemaVersion='RepositoryNativeSession/v1',
            requestPin=self.config.request_pin, peerIdentity=self.identity, ownerIdentity=self.owner_identity,
            binding=self.binding, configurationPin=self.config.pin)))
        # Only the owner keeps the publisher's pipes. The custodian persists
        # beyond that child's actual exit until publication explicitly releases it.
        os.close(0); os.close(1); os.close(2)
        selector = selectors.DefaultSelector(); selector.register(parent, selectors.EVENT_READ)
        channel_open = True
        try:
            while not self.release:
                self.check()
                if self.owner_terminal is None and self.owner.poll() is not None:
                    self.owner_terminal = dict(schemaVersion='RepositoryNativeOwnerTerminal/v1',
                        requestPin=self.config.request_pin, binding=self.binding,
                        ownerIdentity=self.owner_identity, processTerminated=True,
                        actualExitCode=self.owner.returncode, state='TERMINAL_UNKNOWN' if self.owner.returncode == 2 else 'EXITED', at=utc())
                    self.terminal_pin = write_private(self.root / 'owner-terminal.json', self.config.signed(self.owner_terminal))
                    if channel_open:
                        selector.unregister(parent); channel_open = False
                if channel_open and selector.select(0.02):
                    try:
                        self.socket_request(parent)
                    except EOFError:
                        try:
                            self.owner.wait(timeout=min(1, self.config.deadline.remaining()))
                        except subprocess.TimeoutExpired as error:
                            raise RepositoryError('REPOSITORY_NATIVE_OWNER_CHANNEL_TERMINAL_UNKNOWN', unknown=True) from error
                        selector.unregister(parent); channel_open = False
                else:
                    time.sleep(0.02)
                for path in sorted(inbox.glob('*.json')):
                    answer = path.with_suffix('.answer')
                    if answer.exists():
                        continue
                    entry = document(pinned_private(pin_file(private(str(path)))))
                    exact(entry, 'schemaVersion carrierPin', 'RepositoryNativeInboxEntry/v1')
                    reference = entry['carrierPin']
                    require(path.name == reference['sha256'] + '.json', 'REPOSITORY_NATIVE_INBOX_CHANGED')
                    invocation = document(read_pin(reference))
                    result = self.adapter_request(invocation)
                    envelope = dict(schemaVersion='RepositoryNativeResponse/v1', action=invocation['action'],
                        challenge=invocation['challenge'], sourceConfigPin=self.config.source_pin,
                        requestPin=reference, result=result)
                    write_private(answer, self.config.signed(envelope))
        except BaseException as error:
            # An uncertain owner/effect must retain the original custody. This
            # fail-stop state accepts no further work or replacement channel.
            self.retain_unknown(error)
        finally:
            parent.close(); selector.close()
            for fd, _, _ in self.files:
                os.close(fd)


def forward_response(answer_pin, authority_pins, invocation_pin, invocation, source_pin, output):
    """Preserve the signed native original, including its original path."""
    raw = read_pin(answer_pin, MAX_FRAME)
    from repository_records import verify_signed, atomic_output_bytes
    response = verify_signed(document(raw), authority_pins)
    exact(response, 'schemaVersion challenge action sourceConfigPin requestPin result', 'RepositoryNativeResponse/v1')
    require(response['requestPin'] == invocation_pin and response['challenge'] == invocation['challenge'] and
            response['action'] == invocation['action'] and response['sourceConfigPin'] == source_pin,
            'REPOSITORY_NATIVE_RESPONSE_REPLAYED')
    atomic_output_bytes(output, raw)
    atomic_output(output + '.native-receipt.json',
        dict(schemaVersion='RepositoryNativeCarrierReceipt/v1', nativeResponsePin=answer_pin,
             transportedResponsePin=pin_file(output), requestPin=invocation_pin))


def verifier(config, request_path, output):
    invocation_pin = pin_file(request_path)
    invocation = document(read_pin(invocation_pin))
    while not (config.root / 'session.json').exists():
        if (config.root / 'custodian-failure.json').exists():
            raise RepositoryError('REPOSITORY_NATIVE_CUSTODIAN_TERMINAL_UNKNOWN', unknown=True)
        config.current()
        time.sleep(0.02)
    session_pin = pin_file(config.root / 'session.json')
    session = signed_pin(session_pin, config.source['nativeAuthorityKeyPins'])
    require(session['requestPin'] == config.request_pin and session['configurationPin'] == config.pin,
            'REPOSITORY_NATIVE_SESSION_MISMATCH')
    identity = session['peerIdentity']
    require(process_identity(identity['pid'], config.value['programPin']) == identity,
            'REPOSITORY_NATIVE_CUSTODY_LOST')
    pending = config.root / 'inbox' / (invocation_pin['sha256'] + '.json')
    require(not pending.exists(), 'REPOSITORY_NATIVE_REQUEST_REPLAY_FORBIDDEN')
    write_private(pending, dict(schemaVersion='RepositoryNativeInboxEntry/v1', carrierPin=invocation_pin))
    answer = pending.with_suffix('.answer')
    try:
        while not answer.exists():
            if (config.root / 'custodian-failure.json').exists():
                raise RepositoryError('REPOSITORY_NATIVE_CUSTODIAN_TERMINAL_UNKNOWN', unknown=True)
            config.current()
            require(process_identity(identity['pid'], config.value['programPin']) == identity,
                    'REPOSITORY_NATIVE_CUSTODY_LOST')
            time.sleep(0.02)
    except BaseException as error:
        raise RepositoryError('REPOSITORY_NATIVE_REQUEST_TERMINAL_UNKNOWN', unknown=True) from error
    answer_pin = pin_file(private(answer))
    forward_response(answer_pin, config.source['nativeAuthorityKeyPins'], invocation_pin,
                     invocation, config.source_pin, output)


def main():
    from repository_host_view import bootstrap
    bootstrap()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service-configuration', required=True)
    parser.add_argument('--service-sha256', required=True)
    parser.add_argument('--configuration', required=True)
    parser.add_argument('--configuration-sha256', required=True)
    parser.add_argument('--operation-request', required=True)
    parser.add_argument('--operation-sha256', required=True)
    parser.add_argument('--launch', action='store_true')
    parser.add_argument('--serve', action='store_true')
    parser.add_argument('--request')
    parser.add_argument('--output')
    args = parser.parse_args()
    references = []
    for path, digest in ((args.service_configuration, args.service_sha256),
                         (args.configuration, args.configuration_sha256),
                         (args.operation_request, args.operation_sha256)):
        reference = pin_file(path)
        require(reference['sha256'] == digest, 'REPOSITORY_NATIVE_INPUT_CHANGED')
        references.append(reference)
    config = PeerConfiguration(*references)
    if args.serve:
        Custodian(config).serve()
        return 0
    if args.launch:
        require(not config.root.exists(), 'REPOSITORY_NATIVE_SESSION_REPLAY_FORBIDDEN')
        config.root.mkdir(mode=0o700)
        arguments = [sys.executable, '-B', str(Path(__file__).absolute()), *sys.argv[1:]]
        arguments[arguments.index('--launch')] = '--serve'
        peer = subprocess.Popen(arguments, stdin=sys.stdin.buffer, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer)
        terminal = config.root / 'owner-terminal.json'
        try:
            while not terminal.exists():
                if (config.root / 'custodian-failure.json').exists():
                    raise RepositoryError('REPOSITORY_NATIVE_CUSTODIAN_TERMINAL_UNKNOWN', unknown=True)
                config.current()
                require(peer.poll() is None, 'REPOSITORY_NATIVE_CUSTODIAN_FAILED')
                time.sleep(0.02)
        except BaseException as error:
            raise RepositoryError('REPOSITORY_NATIVE_OWNER_TERMINAL_UNKNOWN', unknown=True) from error
        result = signed_pin(pin_file(terminal), config.source['nativeAuthorityKeyPins'])
        require(result['processTerminated'] is True and type(result['actualExitCode']) is int,
                'REPOSITORY_NATIVE_OWNER_TERMINAL_UNKNOWN')
        return result['actualExitCode']
    require(args.request is not None and args.output is not None, 'REPOSITORY_NATIVE_REQUEST_REQUIRED')
    verifier(config, args.request, args.output)
    return 0


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    try:
        sys.exit(main())
    except Exception as error:
        # No commands, credentials, raw exception messages or source bytes.
        print(error.code if isinstance(error, RepositoryError) else
              'REPOSITORY_NATIVE_' + type(error).__name__.upper(), file=sys.stderr)
        sys.exit(2 if isinstance(error, RepositoryError) and error.unknown else 1)
