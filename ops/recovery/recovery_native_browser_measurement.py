"""Real Linux originals for the selected root observer and effective B probe.

This module never reads the private key or signs records. Originals are root:
selected-B-group 0440 in the independently prepared publication view. W01
owns channels and role assembly; selected A validates these originals before
signing. No declared availability or successful process exit substitutes for
an actual syscall, effective credential read, or live owned ancestry.
"""
from __future__ import annotations

import ctypes
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import select
import signal
import socket
import stat
import struct
import sys
import time
import uuid

from recovery_environment_contract import EnvironmentFailure, canonical, decode, exact, require, utc, utc_now
from recovery_environment_supervisor import identity, prepare_local_supervision
from recovery_native_process import file_metadata


class Measurements:
    def __init__(self, selection_pin, proof_pin, intent_pin, authority_pin, deadline):
        from recovery_native_browser import validate_record, descriptor_read, read_signed_publication
        from recovery_native_process import authenticate_payload
        require(sys.platform == 'linux' and os.getresuid() == (0, 0, 0) and os.getresgid() == (0, 0, 0) and
                0 < deadline - time.monotonic() <= 300 and hasattr(os, 'pidfd_open'), 'BROWSER_NATIVE_OBSERVER_REQUIRED')
        self.deadline, self.authority_pin = deadline, authority_pin
        self.selection_pin, self.proof_pin, self.intent_pin = selection_pin, proof_pin, intent_pin
        self.raw = lambda pin: (read_signed_publication(self, pin) if hasattr(self, 'selection') and
            pin['path'].startswith(self.selection['signedPublicationRoot'] + '/') else
            descriptor_read(pin, owners={0}, deadline=deadline))
        self.signed = lambda pin: authenticate_payload(decode(self.raw(pin)), self.raw(authority_pin), authority_pin['sha256'])
        self.selection = validate_record(self.signed(selection_pin), 'RepositoryLabBrowserIdentitySelection/v1')
        self.proof = validate_record(self.signed(proof_pin), 'RepositoryLabBrowserRuntimeProof/v1')
        self.intent = validate_record(self.signed(intent_pin), 'RepositoryLabNativeQualificationIntent/v2')
        self.controller = self.signed(self.selection['controllerIdentityPin'])
        self.held = []; self.sequence = uuid.uuid4().hex
        self.guard()

    def guard(self):
        from recovery_native_browser import validate_record, current_window, security_identity
        require(time.monotonic() < self.deadline, 'BROWSER_MEASUREMENT_DEADLINE')
        for pin, value in ((self.selection_pin, self.selection), (self.proof_pin, self.proof), (self.intent_pin, self.intent)):
            require(self.signed(pin) == value, 'BROWSER_MEASUREMENT_SELECTION_CHANGED'); current_window(value)
        s, p, i = self.selection, self.proof, self.intent
        require(s['authorityKeyPin'] == i['authorityKeyPin'] == self.authority_pin and
                p['browserIdentitySelectionPin'] == i['browserIdentitySelectionPin'] == self.selection_pin and
                i['browserRuntimeProofPin'] == self.proof_pin and
                p['executorInstallationPin'] == i['installationPin'] == s['executorInstallationPin'] and
                p['controllerIdentityPin'] == s['controllerIdentityPin'] and
                all(i[k] == s[k] for k in ('hostId', 'targetId', 'executorId', 'sourceScopePin')),
                'BROWSER_MEASUREMENT_CURRENT_BINDING')
        actual = identity(os.getpid()); c = self.controller
        require((actual['pid'], actual['startTicks'], actual['uid'], actual['gid']) ==
                (c['pid'], c['startTicks'], 0, 0) and self.signed(s['controllerIdentityPin']) == c and
                self.host() == (c['hostId'], c['bootId']) and
                all(os.readlink('/proc/self/ns/' + name) == c[field] for field, name in
                    (('pidNamespace', 'pid'), ('mountNamespace', 'mnt'), ('networkNamespace', 'net'), ('userNamespace', 'user'))),
                'BROWSER_SELECTED_REAL_CONTROLLER_REQUIRED')
        require(os.readlink('/proc/self/ns/pid') == p['producerIdentity']['pidNamespace'], 'BROWSER_COMMON_OBSERVER_NAMESPACE_REQUIRED')
        for role, uid, gid in (('producer', s['browserUid'], s['browserGid']), ('signer', s['signerUid'], s['signerGid'])):
            security_identity(p[role+'Identity'], uid, gid, authority=role == 'signer')
            self.assert_live(p[role+'Identity'])
        grant = validate_record(self.signed(i['authorizationPin']), 'RepositoryLabNativeQualificationAuthorization/v2')
        lease = validate_record(self.signed(i['leasePin']), 'RepositoryLabNativeQualificationLease/v2')
        for record in (grant, lease): current_window(record, 'notBefore')
        fields = ('rehearsalId', 'qualificationId', 'operationId', 'phase', 'hostId', 'targetId', 'executorId',
                  'sourceScopePin', 'installationPin', 'browserIdentitySelectionPin', 'browserRuntimeProofPin')
        require(all(grant[k] == lease[k] == i[k] for k in fields) and grant['approved'] is True and
                grant['actions'] == [i['commandSelections'][0]['action']] and lease['state'] == 'HELD' and
                type(lease['fenceToken']) is int and lease['fenceToken'] > 0, 'BROWSER_MEASUREMENT_CURRENT_GRANT_LEASE')
        from repository_native_runtime import verify_native_installation
        manifest = verify_native_installation(i['installationPin'], [self.authority_pin], deadline=self.deadline)
        require(manifest['schemaVersion'] == 'RepositoryNativeInstallation/v2' and
                manifest['nativeRuntimeProofPin'] == s['controllerRuntimeProofPin'], 'BROWSER_MEASUREMENT_ROOT_INSTALLATION')
        trust = validate_record(self.signed(p['nativeRuntimeTrustPin']), 'RepositoryLabBrowserRuntimeTrust/v1')
        require(set(map(canonical, i['commandSelections'][0]['sourcePins'])) ==
                set(map(canonical, trust['installedSourcePins'] + [x['pin'] for x in trust['nativeFilePins']])) ==
                set(map(canonical, [x['pin'] for x in s['sourceAccess']])), 'BROWSER_MEASUREMENT_FULL_SOURCE')
        from recovery_native_launcher import validate_qualification_scope
        scope = self.signed(i['sourceScopePin']); validate_qualification_scope(scope)
        require(self.signed(i['authorizationPin']) == grant and self.signed(i['leasePin']) == lease,
                'BROWSER_MEASUREMENT_FINAL_AUTHORITY_CHANGED')
        current_window(grant, 'notBefore'); current_window(lease, 'notBefore')
        require(utc(utc_now()) < utc(scope['expiresAt']) and time.monotonic() < self.deadline, 'BROWSER_MEASUREMENT_DEADLINE')

    @staticmethod
    def host():
        return (Path('/etc/machine-id').read_text(encoding='ascii').strip(),
                Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip())

    def persist(self, label, value):
        from recovery_native_browser import literal_path, read_signed_publication
        raw = canonical(value); root = literal_path(self.selection['signedPublicationRoot'], lab=True)
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(directory)
            require(info.st_uid == 0 and info.st_gid == self.selection['browserGid'] and
                    stat.S_IMODE(info.st_mode) == 0o750, 'BROWSER_OBSERVER_ORIGINAL_DIRECTORY')
            name = 'measurement-' + self.sequence + '-' + label + '.json'
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            try:
                with os.fdopen(fd, 'wb', closefd=False) as stream:
                    stream.write(raw); stream.flush(); os.fsync(fd)
                os.fchown(fd, 0, self.selection['browserGid']); os.fchmod(fd, 0o440); os.fsync(fd); os.fsync(directory)
            finally: os.close(fd)
        finally: os.close(directory)
        pin = dict(path=root+'/'+name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        require(read_signed_publication(self, pin) == raw, 'BROWSER_OBSERVER_ORIGINAL_READBACK')
        return pin

    def snapshot(self, pid, ticks):
        require(type(pid) is int and pid > 0 and type(ticks) is int and ticks > 0, 'BROWSER_OBSERVER_PID_REQUIRED')
        handle = os.pidfd_open(pid); self.held.append(handle)
        before = identity(pid); require(before['startTicks'] == ticks and before['state'] != 'Z', 'BROWSER_OBSERVER_PID_CHANGED')
        base = Path('/proc') / str(pid)
        status = dict(line.split(':', 1) for line in (base/'status').read_text(encoding='ascii').splitlines())
        namespaces = {field: os.readlink(base/'ns'/name) for field, name in
            (('pidNamespace', 'pid'), ('mountNamespace', 'mnt'), ('networkNamespace', 'net'), ('userNamespace', 'user'))}
        root = os.stat(base/'root'); parent = identity(before['parent'])
        after = identity(pid)
        require(all(after[k] == before[k] for k in ('pid', 'parent', 'startTicks', 'uid', 'gid')) and
                not select.select([handle], [], [], 0)[0], 'BROWSER_OBSERVER_PROCESS_CHANGED')
        uid = [int(x) for x in status['Uid'].split()]; gid = [int(x) for x in status['Gid'].split()]
        host, boot = self.host()
        status = {k: status[k] for k in ('Uid', 'Gid', 'CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'Groups', 'NoNewPrivs',
                  'Seccomp', 'Seccomp_filters', 'CapAmb') if k in status}
        return dict(pid=pid, parentPid=before['parent'], parentStartTicks=parent['startTicks'], startTicks=ticks,
            uid=uid[1], realUid=uid[0], savedUid=uid[2], filesystemUid=uid[3], gid=gid[1], realGid=gid[0],
            savedGid=gid[2], filesystemGid=gid[3], hostId=host, bootId=boot, **namespaces,
            rootDevice=root.st_dev, rootInode=root.st_ino, status=status)

    def assert_live(self, selected):
        from recovery_native_browser import NS_FIELDS
        actual = self.snapshot(selected['pid'], selected['startTicks'])
        require(all(actual[k] == selected[k] for k in ('pid', 'parentPid', 'startTicks', 'uid', 'gid', 'realUid',
            'savedUid', 'filesystemUid', 'realGid', 'savedGid', 'filesystemGid', 'hostId', 'bootId',
            'rootDevice', 'rootInode', *NS_FIELDS)), 'BROWSER_OBSERVER_LIVE_IDENTITY_DRIFT')
        status = actual['status']; security = selected['security']
        require(all(int(status[a].strip(), 16) == int(security[b], 16) for a, b in
            (('CapEff', 'capEff'), ('CapPrm', 'capPrm'), ('CapInh', 'capInh'), ('CapBnd', 'capBnd'))) and
            [int(x) for x in status['Groups'].split()] == security['supplementaryGroups'] and
            int(status['NoNewPrivs']) == security['noNewPrivs'] and
            (('CapAmb' in status and security['capAmb'] is not None and int(status['CapAmb'], 16) == int(security['capAmb'], 16)) or
             ('CapAmb' not in status and security['ambientState'] == 'UNSUPPORTED_PROVEN')),
            'BROWSER_OBSERVER_LIVE_SECURITY_DRIFT')
        return actual

    def measured(self, selected, label, measured_at):
        actual = self.assert_live(selected); status = actual.pop('status'); actual.pop('parentStartTicks')
        # PR_GET_* evidence is from the actual selected role, never a syscall
        # attributed to an externally observed PID. Live status plus owned
        # stable PID proves current NNP/capability values; missing role API
        # originals refuse rather than invent unsupported/zero values.
        security = dict(selected['security'])
        for key in ('getNoNewPrivsEvidencePin', 'ambientEvidencePin'): self.raw(security[key])
        original = {k: security[k] for k in ('capEff', 'capPrm', 'capInh', 'capBnd', 'capAmb', 'supplementaryGroups', 'noNewPrivs')}
        original.update(schemaVersion='RepositoryLabBrowserSecurity/v1', pid=actual['pid'], startTicks=actual['startTicks'], measuredAt=measured_at)
        security['securityOriginalPin'] = self.persist(label+'-security', original)
        exe = os.readlink('/proc/'+str(actual['pid'])+'/exe')
        candidates = [a['pin'] for a in self.selection['sourceAccess'] if a['pin']['path'] == exe]
        require(len(candidates) == 1, 'BROWSER_ACTUAL_EXECUTABLE_NOT_SELECTED')
        from recovery_native_browser import descriptor_read
        actual['exePin'] = candidates[0]
        descriptor_read(actual['exePin'], owners={0}, deadline=self.deadline, modes=(0o555,))
        actual['security'] = security
        actual['kernelIdentityOriginalPin'] = self.persist(label+'-kernel', dict(actual, observedAt=measured_at))
        return actual

    def self_measured(self, label):
        snap = self.snapshot(os.getpid(), identity(os.getpid())['startTicks']); status = snap.pop('status')
        snap.pop('parentStartTicks'); api = ctypes.CDLL(None, use_errno=True); ctypes.set_errno(0)
        nnp = api.prctl(39, 0, 0, 0, 0); nnp_errno = ctypes.get_errno()
        require(nnp in (0, 1) and nnp_errno == 0, 'BROWSER_OBSERVER_NNP_API_FAILED')
        ctypes.set_errno(0); ambient = api.prctl(47, 1, 0, 0, 0); ambient_errno = ctypes.get_errno()
        require((ambient == 0 and ambient_errno == 0 and 'CapAmb' in status and int(status['CapAmb'], 16) == 0) or
                (ambient == -1 and ambient_errno == errno.EINVAL and 'CapAmb' not in status), 'BROWSER_OBSERVER_AMBIENT_API_FAILED')
        api_fields = dict(pid=snap['pid'], startTicks=snap['startTicks'])
        snap['security'] = dict(capEff=status['CapEff'].strip(), capPrm=status['CapPrm'].strip(), capInh=status['CapInh'].strip(),
            capBnd=status['CapBnd'].strip(), capAmb=status['CapAmb'].strip() if 'CapAmb' in status else None,
            ambientState='PRESENT' if ambient == 0 else 'UNSUPPORTED_PROVEN', supplementaryGroups=[int(x) for x in status['Groups'].split()],
            noNewPrivs=nnp, getNoNewPrivsEvidencePin=self.persist(label+'-nnp', dict(schemaVersion='RepositoryLabBrowserNoNewPrivileges/v1',
                **api_fields, prctl=39, returnValue=nnp, errno=nnp_errno)),
            ambientEvidencePin=self.persist(label+'-ambient', dict(schemaVersion='RepositoryLabBrowserAmbientCapability/v1',
                **api_fields, state='PRESENT' if ambient == 0 else 'UNSUPPORTED_PROVEN', returnValue=ambient,
                errno=ambient_errno, kernelRelease=os.uname().release)))
        return self.measured(snap, label, utc_now())

    def close(self):
        for handle in self.held: os.close(handle)


def _effective_b_probe(m, measured_at):
    """Direct owned child enters actual B root/mount before irreversibly dropping."""
    from recovery_native_launcher import drop_capabilities, native_call
    from recovery_native_browser import descriptor_read
    prepare_local_supervision(); selected = m.proof['producerIdentity']; m.assert_live(selected)
    namespace = os.open('/proc/'+str(selected['pid'])+'/ns/mnt', os.O_RDONLY)
    root = os.open('/proc/'+str(selected['pid'])+'/root', os.O_RDONLY | os.O_DIRECTORY)
    parent, child_channel = socket.socketpair(); pid = os.fork()
    if pid == 0:
        try:
            parent.close(); native_call('setns', namespace, 0); os.fchdir(root); os.chroot('.'); os.chdir('/')
            keep = child_channel.fileno(); os.closerange(3, keep); os.closerange(keep+1, os.sysconf('SC_OPEN_MAX'))
            drop_capabilities(m.selection['browserUid'], m.selection['browserGid'], 0)
            child_channel.settimeout(m.deadline-time.monotonic())
            api = ctypes.CDLL(None, use_errno=True); ctypes.set_errno(0)
            nnp = api.prctl(39, 0, 0, 0, 0); nnp_errno = ctypes.get_errno()
            ctypes.set_errno(0); ambient = api.prctl(47, 1, 0, 0, 0); ambient_errno = ctypes.get_errno()
            child_channel.sendall(canonical(dict(kind='READY', pid=os.getpid(), nnp=nnp, nnpErrno=nnp_errno,
                ambient=ambient, ambientErrno=ambient_errno)) + b'\n')
            require(child_channel.recv(1) == b'G', 'BROWSER_EFFECTIVE_PROBE_NOT_ADMITTED')
            sources = []
            for access in m.selection['sourceAccess']:
                descriptor_read(access['pin'], owners={access['ownerUid']}, owner_gid=access['ownerGid'],
                    modes=(int(access['mode'], 8),), deadline=m.deadline)
                sources.append(access['pin'])
            for access in m.selection['directoryAccess']:
                directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                try:
                    for component in PurePosixPath(access['path']).parts[1:]:
                        following = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                        os.close(directory); directory = following
                    info = os.fstat(directory)
                    require((info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) ==
                        (access['ownerUid'], access['ownerGid'], int(access['mode'], 8)) and
                        bool(os.fstatvfs(directory).f_flag & os.ST_RDONLY) == access['readOnly'], 'BROWSER_EFFECTIVE_DIRECTORY_CHANGED')
                    os.listdir(directory)  # Actual B read access, not root metadata.
                finally: os.close(directory)
            denied = []
            signer = m.proof['signerIdentity']['pid']; key = m.selection['privateKeyPin']['path']
            for path in (key, '/proc/'+str(signer)+'/root'+key, '/proc/'+str(signer)+'/mem'):
                try: fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                except OSError as exc:
                    require(exc.errno in (errno.EPERM, errno.EACCES, errno.ENOENT), 'BROWSER_EFFECTIVE_DENIAL_ERROR')
                    denied.append(dict(path=path, errno=exc.errno))
                else:
                    os.close(fd); raise EnvironmentFailure('BROWSER_EFFECTIVE_KEY_OPEN_SUCCEEDED')
            child_channel.sendall(canonical(dict(kind='MEASURED', sources=sources, directories=m.selection['directoryAccess'], denied=denied))+b'\n')
            os._exit(0)
        except BaseException: os._exit(72)  # Sole parent records actual failed wait, never PASSED.
    child_channel.close(); os.close(namespace); os.close(root); handle = os.pidfd_open(pid); waited = None
    def receive():
        raw = bytearray()
        while not raw.endswith(b'\n'):
            require(time.monotonic() < m.deadline, 'BROWSER_EFFECTIVE_PROBE_DEADLINE')
            parent.settimeout(m.deadline-time.monotonic()); part = parent.recv(65536)
            require(part and len(raw)+len(part) <= 1048576, 'BROWSER_EFFECTIVE_PROBE_FRAME'); raw.extend(part)
        return decode(bytes(raw))
    try:
        ready = receive(); exact(ready, {'kind', 'pid', 'nnp', 'nnpErrno', 'ambient', 'ambientErrno'}, 'BROWSER_EFFECTIVE_READY_SHAPE')
        require(ready['kind'] == 'READY' and ready['pid'] == pid and ready['nnp'] == 1 and ready['nnpErrno'] == 0 and
                ((ready['ambient'] == 0 and ready['ambientErrno'] == 0) or
                 (ready['ambient'] == -1 and ready['ambientErrno'] == errno.EINVAL)), 'BROWSER_EFFECTIVE_SELF_APIS')
        actual = identity(pid); selected_probe = dict(selected, pid=pid, parentPid=os.getpid(), startTicks=actual['startTicks'],
                                                    security=dict(selected['security']))
        selected_probe['security']['getNoNewPrivsEvidencePin'] = m.persist('probe-nnp', dict(schemaVersion='RepositoryLabBrowserNoNewPrivileges/v1',
            pid=pid, startTicks=actual['startTicks'], prctl=39, returnValue=ready['nnp'], errno=ready['nnpErrno']))
        selected_probe['security']['ambientEvidencePin'] = m.persist('probe-ambient', dict(schemaVersion='RepositoryLabBrowserAmbientCapability/v1',
            pid=pid, startTicks=actual['startTicks'], state=selected['security']['ambientState'], returnValue=ready['ambient'],
            errno=ready['ambientErrno'], kernelRelease=os.uname().release))
        probe = m.measured(selected_probe, 'probe', utc_now())
        parent.sendall(b'G'); result = receive()
        exact(result, {'kind', 'sources', 'directories', 'denied'}, 'BROWSER_EFFECTIVE_RESULT_SHAPE')
        require(result['kind'] == 'MEASURED', 'BROWSER_EFFECTIVE_RESULT_MISSING')
        require(select.select([handle], [], [], max(0, m.deadline-time.monotonic()))[0], 'BROWSER_EFFECTIVE_WAIT_DEADLINE')
        waited = os.waitpid(pid, 0)[1]; require(waited == 0, 'BROWSER_EFFECTIVE_WAIT_FAILED')
        return probe, result, waited
    finally:
        if waited is None:
            signal.pidfd_send_signal(handle, signal.SIGKILL); os.waitpid(pid, 0)
        parent.close(); os.close(handle)


def measure_browser_guard_originals(selection_pin, proof_pin, intent_pin, authorization_pin, lease_pin, authority_pin, *, deadline):
    from recovery_native_browser import validate_record, validate_guard_originals
    m = Measurements(selection_pin, proof_pin, intent_pin, authority_pin, deadline)
    try:
        require(m.intent['authorizationPin'] == authorization_pin and m.intent['leasePin'] == lease_pin,
                'BROWSER_GUARD_PROVIDER_BATCH')
        identities = {role+'Identity': m.measured(m.proof[role+'Identity'], role, utc_now())
                                     for role in ('producer', 'signer', 'manager')}
        controller = m.self_measured('controller')
        probe, result, waited = _effective_b_probe(m, utc_now())
        at = utc_now()
        common = dict(browserIdentitySelectionPin=selection_pin, browserRuntimeProofPin=proof_pin, measuredAt=at)
        source = dict(schemaVersion='RepositoryLabBrowserCompleteSourceRead/v1', **common,
            producerIdentity=identities['producerIdentity'], measuredSourcePins=result['sources'])
        directories = dict(schemaVersion='RepositoryLabBrowserDirectoryAccess/v1', **common,
            producerIdentity=identities['producerIdentity'], directoryAccess=result['directories'])
        denial = dict(schemaVersion='RepositoryLabBrowserKeyDenial/v1', **common, producerIdentity=identities['producerIdentity'],
            signerIdentity=identities['signerIdentity'], deniedOpens=result['denied'], probeIdentity=probe,
            actualWaitStatus=waited, soleParentPid=os.getpid())
        value = dict(schemaVersion='RepositoryLabBrowserGuardMeasurement/v1', rehearsalId=m.intent['rehearsalId'],
            **common, qualificationIntentPin=intent_pin, authorizationPin=authorization_pin, leasePin=lease_pin,
            controllerIdentity=controller, **identities, directoryAccessEvidencePin=m.persist('directories', directories),
            completeSourceReadEvidencePin=m.persist('source-read', source), workerKeyDenialEvidencePin=m.persist('denial', denial),
            expiresAt=min(m.intent['expiresAt'], m.proof['expiresAt']))
        validate_record(value, value['schemaVersion']); validate_guard_originals(m, value); m.guard()
        return value
    finally: m.close()


def measure_browser_sandbox_originals(selection_pin, proof_pin, intent_pin, capability_result_pin, authority_pin, *,
        browser_pid, browser_start_ticks, supervisor_pid, supervisor_start_ticks, deadline):
    from recovery_native_browser import validate_record, security_identity
    m = Measurements(selection_pin, proof_pin, intent_pin, authority_pin, deadline)
    try:
        require(m.intent['phase'] == 'NATIVE_BROWSER_QUALIFICATION' and m.intent['sandboxCapabilityResultPin'] == capability_result_pin,
                'BROWSER_SANDBOX_PROVIDER_BATCH')
        capability = validate_record(m.signed(capability_result_pin), 'RepositoryLabBrowserSandboxCapabilityResult/v1')
        require(capability['browserIdentitySelectionPin'] == selection_pin and capability['browserRuntimeProofPin'] == proof_pin,
                'BROWSER_SANDBOX_PROVIDER_CAPABILITY')
        b = m.proof['producerIdentity']; supervisor = m.snapshot(supervisor_pid, supervisor_start_ticks)
        browser = m.snapshot(browser_pid, browser_start_ticks)
        require((supervisor['parentPid'], supervisor['parentStartTicks']) == (b['pid'], b['startTicks']) and
                (browser['parentPid'], browser['parentStartTicks']) == (supervisor_pid, supervisor_start_ticks),
                'BROWSER_SANDBOX_PROVIDER_OWNED_PARENT')
        nodes = [supervisor, browser]; pending = [browser]; renderers = []
        while pending:
            parent = pending.pop()
            for task in (Path('/proc')/str(parent['pid'])/'task').iterdir():
                for token in (task/'children').read_text(encoding='ascii').split():
                    pid = int(token)
                    require(len(nodes) < 4096, 'BROWSER_SANDBOX_PROVIDER_NODE_LIMIT')
                    require(not any(n['pid'] == pid for n in nodes), 'BROWSER_SANDBOX_PROVIDER_DUPLICATE_CHILD')
                    child = m.snapshot(pid, identity(pid)['startTicks'])
                    require((child['parentPid'], child['parentStartTicks']) == (parent['pid'], parent['startTicks']),
                            'BROWSER_SANDBOX_PROVIDER_PARENT_CHANGED')
                    nodes.append(child); pending.append(child)
                    argv = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
                    if b'--type=renderer' in argv: renderers.append(child)
        require(renderers, 'BROWSER_REAL_RENDERER_NOT_OBSERVABLE')
        # Every actual ancestor in this owned tree has the selected external B
        # credentials, zero capabilities and immutable NNP. No root/A ancestor.
        for node in nodes:
            status = node['status']
            require(all(node[k] == m.selection['browserUid'] for k in ('uid', 'realUid', 'savedUid', 'filesystemUid')) and
                    all(node[k] == m.selection['browserGid'] for k in ('gid', 'realGid', 'savedGid', 'filesystemGid')) and
                    all(int(status[k], 16) == 0 for k in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd')) and
                    int(status['NoNewPrivs']) == 1 and not status['Groups'].split(), 'BROWSER_RENDERER_ANCESTOR_AUTHORITY')
        at = utc_now(); common = dict(browserIdentitySelectionPin=selection_pin, browserRuntimeProofPin=proof_pin,
            qualificationIntentPin=intent_pin, observedAt=at); host, boot = m.host()
        lineage = dict(schemaVersion='RepositoryLabBrowserOwnedLineage/v1', **common, hostId=host, bootId=boot,
            browserPid=browser_pid, browserStartTicks=browser_start_ticks, supervisorPid=supervisor_pid,
            supervisorStartTicks=supervisor_start_ticks, nodes=[{k: n[k] for k in ('pid', 'startTicks', 'parentPid', 'parentStartTicks')} for n in nodes])
        lineage_pin = m.persist('lineage', lineage); kernels = []; mappings = []; filters = []
        for n in renderers:
            pid, ticks = n['pid'], n['startTicks']; label = 'renderer-'+str(pid); status = n['status']
            selected = dict(b, **{k: v for k, v in n.items() if k not in ('status', 'parentStartTicks')})
            selected['security'] = dict(b['security'], capEff=status['CapEff'].strip(), capPrm=status['CapPrm'].strip(),
                capInh=status['CapInh'].strip(), capBnd=status['CapBnd'].strip(),
                capAmb=status['CapAmb'].strip() if 'CapAmb' in status else None)
            renderer_common = dict(common, observedAt=utc_now())
            measured = m.measured(selected, label, renderer_common['observedAt']); security_identity(measured, m.selection['browserUid'], m.selection['browserGid'])
            require(measured['pidNamespace'] != b['pidNamespace'] and measured['networkNamespace'] != b['networkNamespace'],
                    'BROWSER_RENDERER_FRESH_PID_NET_REQUIRED')
            ns = os.open('/proc/'+str(pid)+'/ns/user', os.O_RDONLY)
            try:
                import fcntl
                parent_ns = fcntl.ioctl(ns, 0xb702)  # NS_GET_PARENT: real nsfs kernel parent.
                try: parent_name = os.readlink('/proc/self/fd/'+str(parent_ns))
                finally: os.close(parent_ns)
            finally: os.close(ns)
            def mapping(name):
                return [[int(x) for x in line.split()] for line in (Path('/proc')/str(pid)/name).read_text(encoding='ascii').splitlines()]
            map_value = dict(schemaVersion='RepositoryLabBrowserNamespaceMapping/v2', **renderer_common, hostId=host, bootId=boot,
                pid=pid, startTicks=ticks, userNamespace=measured['userNamespace'], parentUserNamespace=parent_name,
                uidMap=mapping('uid_map'), gidMap=mapping('gid_map'), setgroups=(Path('/proc')/str(pid)/'setgroups').read_text(encoding='ascii').strip())
            require(map_value['uidMap'] == [[0, m.selection['browserUid'], 1]] and
                    map_value['gidMap'] == [[0, m.selection['browserGid'], 1]] and map_value['setgroups'] == 'deny' and
                    parent_name == b['userNamespace'], 'BROWSER_RENDERER_ACTUAL_MAP_REQUIRED')
            require('Seccomp_filters' in status, 'BROWSER_RENDERER_FILTER_COUNT_UNOBSERVABLE')
            kernel = dict(schemaVersion='RepositoryLabBrowserDescendantKernel/v2', **renderer_common, identity=measured,
                role='STABLE_RENDERER', seccomp=int(status['Seccomp']), seccompFilters=int(status['Seccomp_filters']),
                ancestorAuthority='NONE', ownedLineageOriginalPin=lineage_pin)
            require(kernel['seccomp'] == 2 and kernel['seccompFilters'] > 0, 'BROWSER_RENDERER_ACTUAL_FILTER_REQUIRED')
            kernel_pin = m.persist(label+'-descendant', kernel); kernels.append(kernel_pin); mappings.append(m.persist(label+'-map', map_value))
            filters.append(m.persist(label+'-filter', dict(schemaVersion='RepositoryLabBrowserSeccomp/v2', **renderer_common,
                hostId=host, bootId=boot, pid=pid, startTicks=ticks, seccomp=kernel['seccomp'],
                seccompFilters=kernel['seccompFilters'], originalKernelPin=kernel_pin)))
        for n in nodes:
            actual = m.snapshot(n['pid'], n['startTicks'])
            require(actual == n, 'BROWSER_RENDERER_WINDOW_CHANGED')
        m.guard()
        common['observedAt'] = utc_now()
        return validate_record(dict(schemaVersion='RepositoryLabBrowserSandboxEvidence/v1', rehearsalId=m.intent['rehearsalId'],
            **common, sandboxCapabilityResultPin=capability_result_pin, browserPid=browser_pid, browserStartTicks=browser_start_ticks,
            descendantKernelOriginalPins=kernels, namespaceMappingOriginalPins=mappings, seccompFilterOriginalPins=filters,
            selectedSandbox='USER_NAMESPACE_AND_SECCOMP_BPF', setuidSandboxUsed=False, sandboxDisabled=False),
            'RepositoryLabBrowserSandboxEvidence/v1')
    finally: m.close()


def assemble_browser_capability_result(context, process_pin, *, deadline):
    """Only an independently selected W03 original decoder can assemble probes.

    The helper decoder interface is an explicit prerequisite. Its actual source
    must be the installed selected helper; no guessed stdout format is accepted.
    """
    from recovery_native_browser import validate_record, validate_capability, PROCESS_VERSION
    require(deadline == context.deadline and time.monotonic() < deadline, 'BROWSER_CAPABILITY_ASSEMBLER_DEADLINE')
    process = validate_record(context.signed(process_pin), PROCESS_VERSION)
    helper = context.selection['capabilityProbeEntryPin']
    require(helper in context.command['sourcePins'], 'BROWSER_CAPABILITY_HELPER_NOT_SELECTED')
    module = sys.modules.get('repository_browser_capability')
    require(module is not None and getattr(module, '__file__', None) == helper['path'] and
            callable(getattr(module, 'read_completed_probe_originals', None)),
            'BROWSER_W03_COMPLETED_ORIGINAL_DECODER_INTERFACE_MISSING')
    context.raw(helper)
    measured = module.read_completed_probe_originals(process_pin, process['stdoutPin'], process['stderrPin'],
        context.selection_pin, context.proof_pin, deadline=deadline)
    exact(measured, {'kernelRelease', 'kernelConfigurationEvidencePin', 'containerSecurityPolicyEvidencePin', 'probes'},
          'BROWSER_W03_COMPLETED_ORIGINAL_DECODER_SHAPE')
    value = dict(schemaVersion='RepositoryLabBrowserSandboxCapabilityResult/v1', rehearsalId=context.intent['rehearsalId'],
        browserIdentitySelectionPin=context.selection_pin, browserRuntimeProofPin=context.proof_pin,
        qualificationIntentPin=context.intent_pin, processResultPin=process_pin, **measured,
        issuedAt=utc_now(), expiresAt=min(context.intent['expiresAt'], context.proof['expiresAt']))
    validate_record(value, value['schemaVersion'])
    # Validate unsigned result via a private unique token; no signed result is
    # fabricated or published by root. A performs the same validation itself.
    from recovery_native_browser import BrowserQualificationContext
    token = object(); prior_signed = context.signed
    proxy = object.__new__(BrowserQualificationContext); proxy.__dict__ = dict(context.__dict__)
    proxy.signed = lambda pin: value if pin is token else prior_signed(pin)
    proxy.raw = context.raw
    validate_capability(proxy, token); context.guard()
    require(time.monotonic() < deadline, 'BROWSER_CAPABILITY_ASSEMBLER_DEADLINE')
    return value
