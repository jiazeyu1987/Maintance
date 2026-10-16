"""Native Linux lab publisher: real owner stream, held author and SMB originals."""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import re
import secrets
import selectors
import stat
import subprocess
import sys
import time

from repository_records import (Configuration, Deadline, RepositoryError, atomic_output,
    canonical, document, exact, pin_file, read_pin, require, safe_path, signed_pin,
    utc, write_new)
from repository_native_lab import (SOURCE_FIELDS, ROLES, command, contained, context,
    execution_host, private, launch_trust, owner_template_records, readback_selection)


def identity(path):
    path = private(path, directory=True)
    info = path.stat()
    return dict(path=str(path), device=info.st_dev, inode=info.st_ino,
                uid=info.st_uid, gid=info.st_gid, mode=stat.S_IMODE(info.st_mode))


def preflight(config, request_pin):
    request = document(read_pin(request_pin))
    require(config.native_lab, 'REPOSITORY_NATIVE_SERVICE_REQUIRED')
    config.request(request)
    config.authorization(request, request['sourceOrTargetRef'])
    config.copy_protection()
    source = document(read_pin(request['sourceOrTargetRef']))
    exact(source, SOURCE_FIELDS, 'RepositoryNativeBackupSource/v1')
    require(source['repositoryId'] == config.value['repositoryId'] and
            source['sourceIdentityPin'] == config.policy['sourceIdentityPin'] and
            source['executionHostPin'] == config.value['executionHostPin'] and
            safe_path(source['workspaceDirectory']) == config.root and
            safe_path(source['archiveRoot']) == config.root / 'archives' and
            source['workspacePin']['path'] == str(config.root / 'workspace-config.json'),
            'REPOSITORY_NATIVE_SOURCE_SCOPE_MISMATCH')
    require(config.root not in Path(source['localStagingRoot']).parents and
            Path(source['localStagingRoot']) not in config.root.parents and
            Path(source['localStagingRoot']) != config.root,
            'REPOSITORY_STAGING_OVERLAP')
    require(document(read_pin(source['localRootIdentityPin'])) == identity(source['localStagingRoot']),
            'REPOSITORY_NATIVE_STAGING_IDENTITY_CHANGED')
    host = execution_host(source['executionHostPin'], config.value['authorityKeyPins'])
    require(source['pythonPin'] == host['pythonPin'] and source['resourceObserverPin'] == host['resourceObserverPin'],
            'REPOSITORY_NATIVE_SOURCE_HOST_CHANGED')
    require(type(source['nativeAuthorityKeyPins']) is list and source['nativeAuthorityKeyPins'],
            'REPOSITORY_NATIVE_AUTHORITY_REQUIRED')
    for pin in source['nativeAuthorityKeyPins']: private(pin['path']); read_pin(pin)
    peer = signed_pin(source['nativePeerConfigPin'], config.value['authorityKeyPins'])
    require(peer['schemaVersion'] == 'RepositoryNativePeerConfig/v2' and
            peer['programPin'] == config.implementation['nativePeer'] and
            peer['executionHostPin'] == source['executionHostPin'] and peer['labScopePin'] == config.value['labScopePin'] and
            peer['sourceIdentityPin'] == source['sourceIdentityPin'] and
            peer['repositoryId'] == source['repositoryId'] and peer['ownerPythonPin'] == source['pythonPin'],
            'REPOSITORY_NATIVE_PEER_SCOPE_MISMATCH')
    context(config, source, request_pin)
    launch_trust(config,source,request_pin)
    for name in ('baseSchemaPin', 'controlAddendumPin', 'workspacePin', 'archiveCredentialPin',
                 'evidenceSigningKeyPin', 'prepareRequestPin', 'captureRequestPin'):
        private(source[name]['path']); read_pin(source[name], 64 * 1024 * 1024)
    recipe=document(read_pin(peer['recipeTemplatePin']))
    assembly=document(read_pin(peer['assemblyTemplatePin']))
    owner_template_records(config, source, request, recipe, assembly)
    from repository_native_lab import capture_asset_preflight
    capture_asset_preflight(config, source, request, assembly)
    require(recipe['nativeInitializationProgramPin']==pin_file(Path(__file__).with_name('repository_native_initializer.py')) and
        assembly['inputReferences']['archive_program']==pin_file(Path(__file__).with_name('repository_native_archive.py')),
        'REPOSITORY_LAB_NATIVE_PROGRAM_NOT_SELECTED')
    require(assembly['binding']['capturePolicySha256']==source['bootstrapBinding']['ownerBinding']['capturePolicySha256'],
        'REPOSITORY_LAB_CAPTURE_POLICY_CHANGED')
    for name in ('ownerCommand', 'nativeVerifierCommand'):
        arguments = ['-B', peer['programPin']['path'], '--service-configuration', config.pin['path'],
            '--service-sha256', config.pin['sha256'], '--configuration', source['nativePeerConfigPin']['path'],
            '--configuration-sha256', source['nativePeerConfigPin']['sha256']]
        if name == 'ownerCommand': arguments.append('--launch')
        command(source[name], source['pythonPin'], arguments)
        require(peer['programPin'] in source[name]['programPins'], 'REPOSITORY_NATIVE_PEER_PROGRAM_REQUIRED')
    reader = peer['readbackConfig']
    protection=signed_pin(config.policy['copyProtectionPin'],config.value['authorityKeyPins'])
    endpoint=signed_pin(protection['readbackEndpointEvidencePin'],config.value['authorityKeyPins'])
    readback_selection(reader, source, endpoint)
    from repository_native_readback import SmbReadback
    # Constructor opens the real strict connection only during publication;
    # the installer selects every config field and library Pin here.
    require(reader['libraryPins'], 'REPOSITORY_SMB_LIBRARY_PINS_REQUIRED')
    for pin in reader['libraryPins']: read_pin(pin, 32 * 1024 * 1024)
    config.current()
    return dict(schemaVersion='RepositoryInstallerPreflight/v1', configurationPin=config.pin,
                requestPin=request_pin, sourceConfigPin=request['sourceOrTargetRef'])


class WorkspaceAuthor:
    """Held real directory and flock, bounded usage and rechecked device identity."""
    def __init__(self, publisher, intent_pin):
        import fcntl
        self.publisher, self.config = publisher, publisher.config
        self.intent_pin = intent_pin
        self.intent = document(read_pin(intent_pin))
        require(self.intent['binding'] == publisher.binding, 'REPOSITORY_NATIVE_INTENT_CHANGED')
        self.workspace_pin = publisher.source['workspacePin']
        self.workspace = document(read_pin(self.workspace_pin))
        exact(self.workspace, 'schemaVersion repositoryId root rootIdentityPin budgetBytes reserveBytes maxAttemptBytes allocationProofPin resourceObservationPin',
              'RepositoryNativeWorkspace/v1')
        require(self.workspace['repositoryId'] == self.config.value['repositoryId'] and
                self.workspace['root'] == str(self.config.root) and
                all(type(self.workspace[k]) is int and self.workspace[k] > 0 for k in
                    ('budgetBytes', 'reserveBytes', 'maxAttemptBytes')) and
                self.workspace['budgetBytes'] <= 80 * 1024**3 and
                self.workspace['maxAttemptBytes'] + self.workspace['reserveBytes'] <= self.workspace['budgetBytes'],
                'REPOSITORY_NATIVE_WORKSPACE_BUDGET_INVALID')
        self.root_identity = document(read_pin(self.workspace['rootIdentityPin']))
        require(self.root_identity == identity(self.config.root), 'REPOSITORY_NATIVE_WORKSPACE_CHANGED')
        self.directory_fd = os.open(self.config.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.lock_path = self.config.root / '.repository-control/native-author.lock'
        self.lock_fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            os.close(self.lock_fd); os.close(self.directory_fd)
            raise
        info = os.fstat(self.lock_fd)
        self.lock_identity = info.st_dev, info.st_ino
        self.released = False
        self.author_pin = publisher.save(dict(schemaVersion='RepositoryNativeWorkspaceAuthor/v1',
            pid=os.getpid(), bootId=publisher.host['bootId'], rootIdentity=self.root_identity,
            lockPath=str(self.lock_path), device=info.st_dev, inode=info.st_ino, fd=self.lock_fd,
            workspacePin=self.workspace_pin, requestPin=publisher.request_pin), 'workspace-author')

    def check(self):
        self.publisher.authority()
        require(not self.released and identity(self.config.root) == self.root_identity,
                'REPOSITORY_NATIVE_AUTHOR_LOST')
        directory = os.fstat(self.directory_fd)
        held, named = os.fstat(self.lock_fd), safe_path(self.lock_path).stat()
        require((directory.st_dev, directory.st_ino) == (self.root_identity['device'], self.root_identity['inode']) and
                (held.st_dev, held.st_ino) == (named.st_dev, named.st_ino) == self.lock_identity,
                'REPOSITORY_NATIVE_AUTHOR_LOST')
        read_pin(self.workspace_pin)
        read_pin(self.intent_pin)
        for key in ('allocationProofPin', 'resourceObservationPin'): read_pin(self.workspace[key])
        disk = os.statvfs(self.config.root)
        usage = 0
        for root, directories, files in os.walk(self.config.root, followlinks=False):
            self.publisher.deadline.check()
            for name in directories + files:
                info = safe_path(Path(root) / name).stat()
                require(info.st_dev == self.root_identity['device'], 'REPOSITORY_NATIVE_WORKSPACE_DEVICE_CHANGED')
                usage += info.st_blocks * 512
        logical, peak = self.intent['logicalPayloadUpperBoundBytes'], self.intent['nasAllocatedUpperBoundBytes']
        require(type(logical) is int and type(peak) is int and 0 < logical <= self.workspace['maxAttemptBytes'] and
                0 < peak <= self.workspace['maxAttemptBytes'] and
                usage + peak + self.workspace['reserveBytes'] <= self.workspace['budgetBytes'] and
                disk.f_bavail * disk.f_frsize >= peak + self.workspace['reserveBytes'],
                'REPOSITORY_NATIVE_WORKSPACE_CAPACITY_INSUFFICIENT')
        return usage, disk.f_bavail * disk.f_frsize

    def admission(self):
        usage, available = self.check()
        value = dict(schemaVersion='backup-lab-nas-admission/v1', binding=self.publisher.binding,
            intent=self.intent, intentReference=self.intent_pin, admissionId=secrets.token_hex(32),
            authorIdentityReference=self.author_pin, resourceObservationReference=self.workspace['resourceObservationPin'],
            allocationProofReference=self.workspace['allocationProofPin'], workspaceUsageBytes=usage,
            availableBytes=available, workspaceBudgetBytes=self.workspace['budgetBytes'],
            maxAttemptBytes=self.workspace['maxAttemptBytes'], reserveBytes=self.workspace['reserveBytes'],
            logicalPayloadUpperBoundBytes=self.intent['logicalPayloadUpperBoundBytes'],
            nasAllocatedUpperBoundBytes=self.intent['nasAllocatedUpperBoundBytes'],
            budget=dict(remainingMilliseconds=self.publisher.milliseconds(), observationReference=self.author_pin),
            authorHeld=True, preCaptureAdmitted=True, exclusionScope='cooperative-workspace-writers',
            spaceGuaranteed=False, allWritersExcluded=False, nasHardQuotaConfigured=False, automaticDeletion=False,
            labContextPin=self.config.lab_context_pin, workspacePin=self.workspace_pin)
        return self.publisher.publish_control(value, 'lab-nas-admission')

    def release(self, publication_pin):
        self.check()
        publication = document(read_pin(publication_pin))
        require(publication['actualExitCode'] == 0, 'REPOSITORY_NATIVE_AUTHOR_RELEASE_UNPROVEN')
        self.released = True
        os.close(self.lock_fd); os.close(self.directory_fd)

    def retain_unknown(self):
        self.publisher.save(dict(schemaVersion='RepositoryNativeAuthorTerminal/v1', state='TERMINAL_UNKNOWN',
            requestPin=self.publisher.request_pin, authorPin=self.author_pin, at=utc()), 'author-unknown')
        # The original author retains its descriptors; never an automatic unlock.
        while True: time.sleep(1)


class Publisher:
    def __init__(self, config, request_pin, evidence_root, deadline):
        self.config, self.request_pin, self.deadline = config, request_pin, deadline
        self.request = document(read_pin(request_pin))
        self.source = document(read_pin(self.request['sourceOrTargetRef']))
        self.root = private(evidence_root, directory=True)
        self.host = execution_host(config.value['executionHostPin'], config.value['authorityKeyPins'])
        self.sequence = self.control_sequence = self.archive_sequence = 0
        self.binding = self.source['bootstrapBinding']['ownerBinding']
        self.process = self.author = None
        self.buffer = bytearray()

    def authority(self):
        self.deadline.check()
        self.config.request(self.request)
        self.config.authorization(self.request, self.request['sourceOrTargetRef'])
        context(self.config, self.source, self.request_pin)
        launch_trust(self.config,self.source,self.request_pin)

    def milliseconds(self):
        return int(self.deadline.remaining() * 1000)

    def save(self, value, role):
        self.sequence += 1
        path = self.root / ('native-' + str(self.sequence) + '-' + role + '.json')
        pin = write_new(path, value); path.chmod(0o600)
        return pin

    def exchange(self, action, payload):
        from repository_native_bridge import exchange
        self.authority()
        request = self.save(dict(schemaVersion='RepositoryNativeBridgeRequest/v1',
            operationRequestPin=self.request_pin, remainingMilliseconds=self.milliseconds(), payload=payload), 'bridge-input')
        output = self.root / ('bridge-' + str(self.sequence) + '.json')
        exchange(self.request['sourceOrTargetRef'], action, request, output)
        return document(read_pin(pin_file(output)))

    def publish_control(self, value, role):
        raw = canonical(value)
        answer = self.exchange('publish-control', dict(bytesBase64=base64.b64encode(raw).decode('ascii'),
            role=role, binding=self.binding))['result']['pin']
        require(read_pin(answer) == raw, 'REPOSITORY_NATIVE_CONTROL_CHANGED')
        return answer

    def line(self, limit=1500000):
        while b'\n' not in self.buffer:
            self.deadline.check()
            require(len(self.buffer) <= limit, 'REPOSITORY_NATIVE_STREAM_TOO_LARGE')
            ready = self.selector.select(self.deadline.remaining())
            if not ready: raise RepositoryError('REPOSITORY_NATIVE_STREAM_UNKNOWN', unknown=True)
            chunk = os.read(self.process.stdout.fileno(), min(65536, limit + 1 - len(self.buffer)))
            if not chunk: raise RepositoryError('REPOSITORY_NATIVE_STREAM_EOF', unknown=True)
            self.buffer.extend(chunk)
        raw, _, rest = self.buffer.partition(b'\n'); self.buffer = bytearray(rest)
        require(len(raw) <= limit, 'REPOSITORY_NATIVE_STREAM_TOO_LARGE')
        self.save(dict(rawBase64=base64.b64encode(raw + b'\n').decode('ascii')), 'owner-raw-response')
        return document(bytes(raw))

    def send(self, value):
        self.authority()
        raw = canonical(value) + b'\n'
        require(len(raw) <= 8192, 'REPOSITORY_NATIVE_REQUEST_TOO_LARGE')
        self.save(value, 'owner-request')
        with selectors.DefaultSelector() as writable:
            writable.register(self.process.stdin, selectors.EVENT_WRITE)
            offset = 0
            while offset < len(raw):
                if not writable.select(self.deadline.remaining()):
                    raise RepositoryError('REPOSITORY_NATIVE_WRITE_UNKNOWN', unknown=True)
                offset += os.write(self.process.stdin.fileno(), raw[offset:])

    def control(self, action, payload=None):
        self.control_sequence += 1
        budget_pin = self.publish_control(dict(binding=self.binding, sequence=self.control_sequence-1,
            remainingMilliseconds=self.milliseconds()), 'control-budget')
        self.send(dict(schemaVersion='release-production-backup-control/v1', binding=self.binding,
            sequence=self.control_sequence, action=action, payloadReference=payload,
            budget=dict(remainingMilliseconds=document(read_pin(budget_pin))['remainingMilliseconds'],
                        observationReference=budget_pin)))
        answer = self.line(65536)
        exact(answer, 'schemaVersion binding sequence action state resultReference chunk ownerRemainingMilliseconds failureCode',
              'release-production-backup-control/v1')
        require(answer['binding'] == self.binding and answer['sequence'] == self.control_sequence and
                answer['action'] == action and answer['failureCode'] is None,
                'REPOSITORY_NATIVE_OWNER_CONTROL_FAILED')
        expected = {'prepare':'PREPARED', 'admit':'PREFLIGHT_VALIDATED', 'capture':'ARCHIVE_READY',
                    'read-manifest':'ARCHIVE_READY', 'begin-archive':'ARCHIVE_SERVING', 'guard':self.state}[action]
        require(answer['state'] == expected and type(answer['ownerRemainingMilliseconds']) is int and
                answer['ownerRemainingMilliseconds'] > 0, 'REPOSITORY_NATIVE_CONTROL_STATE_INVALID')
        self.deadline.end = min(self.deadline.end, time.monotonic() + answer['ownerRemainingMilliseconds']/1000)
        self.state = answer['state']
        return answer

    def archive_request(self, action, relative=None, offset=None):
        self.archive_sequence += 1
        value = dict(schemaVersion='release-production-backup-archive-session/v1',
            attemptId=self.binding['attemptId'], sourceContextSha256=self.binding['sourceContextSha256'],
            sequence=self.archive_sequence, action=action)
        if action == 'read-chunk': value.update(relativePath=relative, offset=offset)
        self.send(value)
        answer = self.line()
        fields = 'schemaVersion attemptId sourceContextSha256 sequence state treeDigest productionEvidence'
        if action == 'read-chunk': fields += ' relativePath offset bytesBase64 chunkSha256'
        exact(answer, fields, value['schemaVersion'])
        require(all(answer[k] == value[k] for k in ('attemptId','sourceContextSha256','sequence')) and
                answer['treeDigest'] == self.header['treeDigest'] and answer['productionEvidence'] is False,
                'REPOSITORY_NATIVE_ARCHIVE_BINDING_CHANGED')
        expected = {'guard':'OWNER_GUARD_CURRENT','close':'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF',
                    'read-chunk':'ARCHIVE_CHUNK_READ'}[action]
        require(answer['state'] == expected, 'REPOSITORY_NATIVE_ARCHIVE_STATE_INVALID')
        if action == 'read-chunk':
            require(answer['relativePath'] == relative and answer['offset'] == offset,
                    'REPOSITORY_NATIVE_ARCHIVE_OFFSET_CHANGED')
            raw = base64.b64decode(answer['bytesBase64'], validate=True)
            require(hashlib.sha256(raw).hexdigest() == answer['chunkSha256'], 'REPOSITORY_NATIVE_CHUNK_CHANGED')
            return raw
        return answer

    def guard(self):
        self.author.check()
        self.archive_request('guard')
        self.exchange('observe-owner', dict(bound=self.bound))

    def stream(self, target, tree):
        require(not target.exists() and target.parent == Path(self.source['archiveRoot']),
                'REPOSITORY_NATIVE_ARCHIVE_REPLAY_OR_ESCAPE')
        target.mkdir(mode=0o700)
        folded = set()
        for relative, spec in sorted(tree.items(), key=lambda row:(row[0].count('/'), row[0])):
            require(type(relative) is str and relative and not re.search(r'[\\:*?"<>|\x00-\x1f]',relative) and
                    not relative.startswith('/') and all(part not in ('','.','..','.repository') and
                    part.rstrip(' .') == part for part in relative.split('/')) and
                    relative.casefold() not in folded, 'REPOSITORY_NATIVE_PAYLOAD_PATH_INVALID')
            folded.add(relative.casefold())
            path = target / relative
            safe_path(path.parent)
            self.guard()
            if spec == 'directory': path.mkdir(mode=0o700); continue
            require(type(spec) is str and re.fullmatch(r'file\|(0|[1-9][0-9]*)\|[0-9a-f]{64}',spec),
                    'REPOSITORY_NATIVE_PAYLOAD_TREE_INVALID')
            _, size_text, expected_hash = spec.split('|'); size = int(size_text)
            offset = 0; digest = hashlib.sha256()
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd,'wb') as stream:
                while offset < size:
                    self.guard()
                    raw = self.archive_request('read-chunk', relative, offset)
                    require(len(raw) == min(1024*1024, size-offset), 'REPOSITORY_NATIVE_CHUNK_SIZE_CHANGED')
                    stream.write(raw); digest.update(raw); offset += len(raw)
                stream.flush(); os.fsync(stream.fileno())
            require(digest.hexdigest() == expected_hash, 'REPOSITORY_NATIVE_PAYLOAD_CORRUPT')
            actual = pin_file(path, self.deadline)
            require(actual['bytes'] == size and actual['sha256'] == expected_hash, 'REPOSITORY_NATIVE_PAYLOAD_CORRUPT')
        actual_names = {p.relative_to(target).as_posix() for p in target.rglob('*')}
        require(actual_names == set(tree), 'REPOSITORY_NATIVE_PAYLOAD_SET_CHANGED')
        self.guard()

    def run(self, output):
        from repository_publish import seal, complete
        from repository_native_peer import process_identity
        preflight(self.config, self.request_pin)
        cmd = self.source['ownerCommand']
        argv = [cmd['executablePin']['path'], *cmd['arguments'], '--operation-request',
                self.request_pin['path'], '--operation-sha256', self.request_pin['sha256']]
        stderr = (self.root/'native-owner.stderr').open('xb')
        self.selector = selectors.DefaultSelector()
        try:
            self.authority()
            self.process = subprocess.Popen(argv, cwd=cmd['workingDirectory'], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=stderr, bufsize=0)
            os.set_blocking(self.process.stdin.fileno(),False)
            os.set_blocking(self.process.stdout.fileno(),False)
            self.selector.register(self.process.stdout,selectors.EVENT_READ)
            bound = self.line(65536)
            exact(bound, 'schemaVersion state bootstrapBinding binding nativeOriginalReferences ownerRemainingMilliseconds',
                  'release-production-backup-owner-bound/v1')
            require(bound['state']=='BOUND_READONLY' and bound['bootstrapBinding']==self.binding,
                    'REPOSITORY_NATIVE_OWNER_BINDING_CHANGED')
            self.binding = bound['binding']; self.bound=bound; self.state=bound['state']
            peer = signed_pin(self.source['nativePeerConfigPin'], self.config.value['authorityKeyPins'])
            session_root=Path(peer['sessionRoot'])/hashlib.sha256(self.request['requestId'].encode()).hexdigest()
            session=signed_pin(pin_file(session_root/'session.json'),self.source['nativeAuthorityKeyPins'])
            descriptor=document(read_pin(pin_file(session_root/'lab-owner-initialized.json')))
            self.exchange('observe-initialized',dict(descriptor=descriptor,currentInput=dict(
                schemaVersion='RepositoryLabInitializerInput/v1',configurationPin=self.config.pin,
                labContextPin=self.config.lab_context_pin)))
            self.exchange('observe-owner',dict(bound=bound))
            runtime_assembly=document(read_pin(pin_file(session_root/'assembly.json')))
            owner=session['ownerIdentity']
            require(process_identity(owner['pid'],peer['ownerEntryPin'])==owner,
                    'REPOSITORY_NATIVE_ORIGINAL_OWNER_LOST')
            self.process_pin=self.save(dict(schemaVersion='RepositoryOriginalProcess/v1', requestPin=self.request_pin,
                binding=self.binding,ownerPid=owner['pid'],processStartTicks=owner['processStartTicks'],
                ownerCommand=cmd),'original-process')
            prepared=self.control('prepare',self.source['prepareRequestPin'])
            self.exchange('observe-prepared',dict(intentPin=prepared['resultReference'],binding=self.binding))
            self.author=WorkspaceAuthor(self,prepared['resultReference'])
            self.control('admit',self.author.admission())
            captured=self.control('capture',runtime_assembly['captureRequestPin'])
            header_pin=captured['resultReference'];self.header=document(read_pin(header_pin))
            proof=self.exchange('observe-capture',dict(binding=self.binding,archiveHeaderPin=header_pin,
                                                       originalProcessPin=self.process_pin))
            tree=proof['result']['payloadTree']
            ordered=sorted(tree,key=lambda name:name.encode('utf-16-be'))
            tree_digest=hashlib.sha256(b''.join((name+'\0'+tree[name]+'\0').encode('utf-8') for name in ordered)).hexdigest()
            require(tree_digest==self.header['treeDigest'] and self.header['binding']==self.binding and
                self.header['fileCount']==sum(spec.startswith('file|') for spec in tree.values()) and
                self.header['totalBytes']==sum(int(spec.split('|')[1]) for spec in tree.values() if spec.startswith('file|')),
                'REPOSITORY_NATIVE_ARCHIVE_HEADER_CHANGED')
            # Read original manifest through the bounded owner interface before
            # the permanent switch to archive-serving mode.
            manifest_raw=bytearray()
            while True:
                request=self.publish_control(dict(schemaVersion='release-production-backup-manifest-read/v1',
                    manifestSha256=self.header['manifestReference']['sha256'],offset=len(manifest_raw)),'manifest-read')
                chunk=self.control('read-manifest',request)['chunk']
                require(chunk['offset']==len(manifest_raw), 'REPOSITORY_NATIVE_MANIFEST_OFFSET_CHANGED')
                raw=base64.b64decode(chunk['bytesBase64'],validate=True)
                require(hashlib.sha256(raw).hexdigest()==chunk['chunkSha256'] and len(manifest_raw)+len(raw)<=64*1024*1024,
                        'REPOSITORY_NATIVE_MANIFEST_CHANGED')
                manifest_raw.extend(raw)
                if chunk['eof'] is True: break
                require(raw, 'REPOSITORY_NATIVE_MANIFEST_STALLED')
            require(bytes(manifest_raw)==read_pin(self.header['manifestReference'],64*1024*1024) and
                    document(bytes(manifest_raw))==tree, 'REPOSITORY_NATIVE_MANIFEST_CHANGED')
            self.control('begin-archive')
            target=Path(self.source['archiveRoot'])/('prod-'+self.binding['attemptId'])
            self.stream(target,tree)
            payload=self.exchange('observe-readback',dict(binding=self.binding,archivePath=str(target),
                expectedEntries=tree,material=None,phase='PAYLOAD_BEFORE_OWNER_CLOSE'))
            require(payload['result']['payloadTree']==tree and payload['result']['independentConnectionId'],
                    'REPOSITORY_NATIVE_PAYLOAD_READBACK_FAILED')
            archive=dict(archivePath=str(target),transportVerified=True,serverDurabilityVerified=False,
                         treeDigest=self.header['treeDigest'])
            facts=dict(archive=archive,nativeProof=proof,binding=self.binding,ownerPid=owner['pid'],
                originalProcessPin=self.process_pin,archiveHeaderPin=header_pin,expectedEntries=tree)
            material=seal(self.config,self.request_pin,self.source,facts,self.deadline)
            self.guard()
            close=self.archive_request('close');self.process.stdin.close()
            # The custodian remains alive until explicit release. Its launcher
            # exit is distinct from the original owner's signed actual exit.
            while not (session_root/'owner-terminal.json').exists():
                self.authority()
                require(self.process.poll() is None, 'REPOSITORY_NATIVE_CUSTODIAN_EXITED_EARLY')
                time.sleep(min(0.02,self.deadline.remaining()))
            terminal_pin=pin_file(session_root/'owner-terminal.json')
            native=signed_pin(terminal_pin,self.source['nativeAuthorityKeyPins'])
            exact(native,'schemaVersion requestPin binding ownerIdentity processTerminated actualExitCode state at',
                'RepositoryNativeOwnerTerminal/v1')
            require(type(native['actualExitCode']) is int and native['actualExitCode']==0 and native['processTerminated'] is True and
                    native['ownerIdentity']==owner and native['requestPin']==self.request_pin and
                    native['binding']==self.binding and native['state']=='EXITED', 'REPOSITORY_NATIVE_ORIGINAL_EXIT_UNPROVEN')
            trailing=os.read(self.process.stdout.fileno(),65536)
            require(not self.buffer and trailing==b'' and (self.root/'native-owner.stderr').stat().st_size==0,
                    'REPOSITORY_NATIVE_OWNER_TERMINAL_OUTPUT_INVALID')
            terminal=dict(attemptId=self.binding['attemptId'],sourceContextSha256=self.binding['sourceContextSha256'],
                treeDigest=self.header['treeDigest'],closeResponse=close,originalOwnerPid=owner['pid'],
                actualExitCode=0,processTerminated=True,rawTerminalVerified=True)
            self.save(terminal,'owner-terminal')
            readback=self.exchange('observe-readback',dict(binding=self.binding,archive=archive,material=material,
                nativeCaptureResponsePin=proof['nativeResponsePin'],phase='SEALED_MATERIAL',
                payloadReadbackResponsePin=payload['nativeResponsePin']))
            publication=complete(self.config,self.request_pin,self.source,dict(archive=archive,terminal=terminal,
                material=material,readbackProof=readback,ownerPid=owner['pid']),self.deadline)
            atomic_output(output,publication);publication_pin=pin_file(output)
            self.exchange('release-peer',dict(publicationPin=publication_pin))
            try: code=self.process.wait(timeout=self.deadline.remaining())
            except subprocess.TimeoutExpired as error:
                raise RepositoryError('REPOSITORY_NATIVE_CUSTODIAN_EXIT_UNKNOWN',unknown=True) from error
            require(code==0,'REPOSITORY_NATIVE_CUSTODIAN_EXIT_FAILED')
            self.save(dict(schemaVersion='RepositoryNativeCustodianTerminal/v1',pid=self.process.pid,
                actualExitCode=code,state='EXITED',requestPin=self.request_pin,at=utc()),'custodian-terminal')
            self.author.release(publication_pin)
            return publication
        except BaseException as error:
            self.save(dict(schemaVersion='RepositoryNativePublisherTerminal/v1',state='TERMINAL_UNKNOWN',
                requestPin=self.request_pin,actualExitCode=None if self.process is None else self.process.poll(),
                failureCode=error.code if isinstance(error,RepositoryError) else type(error).__name__,at=utc()),'publisher-unknown')
            if self.author is not None: self.author.retain_unknown()
            if self.process is not None:
                raise RepositoryError('REPOSITORY_NATIVE_PUBLICATION_TERMINAL_UNKNOWN',unknown=True) from error
            raise
        finally:
            self.selector.close();stderr.close()


def invoke(config, request_pin, deadline, evidence_root, output):
    return Publisher(config,request_pin,evidence_root,deadline).run(output)


def main():
    require(sys.platform.startswith('linux') and os.geteuid()==os.getegid()==0,
            'REPOSITORY_NATIVE_LINUX_ROOT_REQUIRED')
    os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('configuration','configuration-sha256','request','request-sha256','output','evidence-root','remaining-milliseconds'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    config_pin,request_pin=pin_file(args.configuration),pin_file(args.request)
    require(config_pin['sha256']==args.configuration_sha256 and request_pin['sha256']==args.request_sha256,
            'REPOSITORY_NATIVE_PUBLISHER_INPUT_CHANGED')
    config=Configuration(config_pin)
    deadline=Deadline(int(args.remaining_milliseconds))
    require(int(args.remaining_milliseconds)<=document(read_pin(request_pin))['deadlineMilliseconds'],
            'REPOSITORY_NATIVE_BUDGET_INCREASE_REFUSED')
    invoke(config,request_pin,deadline,args.evidence_root,args.output)


if __name__=='__main__':
    sys.dont_write_bytecode=True
    try: main()
    except Exception as error:
        print(error.code if isinstance(error,RepositoryError) else 'REPOSITORY_NATIVE_PUBLISHER_'+type(error).__name__.upper(),file=sys.stderr)
        sys.exit(2 if isinstance(error,RepositoryError) and error.unknown else 1)
