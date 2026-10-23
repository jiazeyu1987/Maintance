"""Explicit private lab contracts and current native authority. No prod fallback."""
import base64
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sys
import threading
import time

from formal_normal_owner import canonical, pin, require, strict_document
import formal_snapshot_linux as snapshot

LAB_ROOT = '/mnt/intruoyi-data/backup-restore-lab/20261012-w01-w07'
LAB_ID = 'backup-server-rehearsal-20261012-r1'
CONTEXT_FIELDS = set(('schemaVersion rehearsalId environment sourceIdentityPin executionHostPin '
    'labScopePin operationRequestPin installedClosurePin authorizationPin leasePin authorityKeyPin '
    'issuedAt expiresAt').split())
SCOPE_FIELDS = {'schemaVersion', 'environment', 'targetRawSha256', 'targetFingerprint',
                'database', 'databaseUuid', 'labContextPin'}
active_lab = ContextVar('formal_explicit_backup_lab', default=None)
LAB_ACTIONS = {'BACKUP_FULL','BACKUP_INCREMENTAL','LIST_POINTS','POINT_DETAIL','READBACK_VERIFY',
    'RESTORE_PREFLIGHT','PREPARE_TARGET','RESTORE_EXECUTE','START_APPLICATION','VERIFY_RECOVERY',
    'REHEARSAL','PLAN_REHEARSAL'}


def exact(value, fields, schema):
    require(type(value) is dict and set(value) == set(fields) and value['schemaVersion'] == schema,
            'BACKUP_LAB_SCHEMA_INVALID')
    return value


def timestamp(value):
    require(type(value) is str and value.endswith('Z'), 'BACKUP_LAB_TIME_INVALID')
    try:
        result = datetime.fromisoformat(value[:-1] + '+00:00').timestamp()
    except ValueError:
        raise snapshot.FormalSnapshotError('BACKUP_LAB_TIME_INVALID') from None
    return result


def validate_context(value, authority_key_pin):
    exact(value, CONTEXT_FIELDS, 'BackupRehearsalAuthorityContext/v1')
    require(value['environment'] == 'backup-lab' and value['rehearsalId'] == LAB_ID and
            value['authorityKeyPin'] == authority_key_pin and
            timestamp(value['issuedAt']) < timestamp(value['expiresAt']), 'BACKUP_LAB_CONTEXT_INVALID')
    for name in CONTEXT_FIELDS - {'schemaVersion', 'environment', 'rehearsalId', 'issuedAt', 'expiresAt'}:
        pin(value[name])
    return value


def validate_source_scope(value):
    exact(value, SCOPE_FIELDS, 'backup-lab-source-scope/v1')
    require(value['environment'] == 'backup-lab' and
            all(type(value[k]) is str and re.fullmatch('[0-9a-f]{64}', value[k])
                for k in ('targetRawSha256', 'targetFingerprint')) and
            type(value['database']) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}', value['database']) and
            type(value['databaseUuid']) is str and
            re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['databaseUuid']),
            'BACKUP_LAB_SOURCE_INVALID')
    pin(value['labContextPin'])
    return value


def validate_capture_request(request, approved_source):
    from formal_capture_producer import validate_shared_request
    validate_source_scope(approved_source)
    require(type(request) is dict and request.get('schemaVersion') == 'backup-lab-capture-request/v1' and
            request.get('sourceScope') == approved_source and
            request.get('labContextPin') == approved_source['labContextPin'] and
            request.get('action') == 'capture-shared-payload' and
            request.get('database') == approved_source['database'] and
            type(request.get('claimBinding')) is dict and
            request['claimBinding'].get('databaseUuid') == approved_source['databaseUuid'] and
            request['claimBinding'].get('sourceFingerprint') == approved_source['targetFingerprint'],
            'BACKUP_LAB_CAPTURE_SOURCE_CHANGED')
    common = {k: v for k, v in request.items() if k not in ('sourceScope', 'labContextPin')}
    common['schemaVersion'] = 'release-formal-capture-request/v3'
    validate_shared_request(common)
    return request


class LabAuthority:
    """Retain original signed context, current grant/lease, and actual Linux host.

    The key is independently selected by the private launcher, never obtained
    from the payload. No new authority is signed/consumed by this capture module.
    """
    def __init__(self, context_pin, authority_key_pin, *, expected, guard):
        require(callable(guard) and type(expected) is dict and set(expected) == {
            'sourceIdentityPin', 'executionHostPin', 'labScopePin', 'operationRequestPin', 'installedClosurePin'},
            'BACKUP_LAB_TRUST_REQUIRED')
        self.context_pin = dict(pin(context_pin)); self.key_pin = dict(pin(authority_key_pin))
        self.expected = strict_document(canonical(expected)); self.guard = guard
        self.originals = {}; self.directories = {}; self.native_originals = {}
        self.native_runtime = None; self.native_trust = None; self.native_proof = None
        self.pid = os.getpid(); self.thread = threading.get_ident()
        self.wall = time.time(); self.clock = time.monotonic()
        self.context = validate_context(self.signed(context_pin), authority_key_pin)
        require(all(self.context[k] == v for k, v in self.expected.items()), 'BACKUP_LAB_CONTEXT_CHANGED')
        self.request = self.document(self.context['operationRequestPin'])
        self.scope = self.signed(self.context['labScopePin'])
        self.grant = self.signed(self.context['authorizationPin']); self.lease = self.signed(self.context['leasePin'])
        self.host = self.document(self.context['executionHostPin'])
        self.installation = self.signed(self.context['installedClosurePin'])
        self.identity = self.document(self.context['sourceIdentityPin'])
        self.source = self.document(self.request['sourceOrTargetRef'])
        self.policy = self.signed(self.request['policyPin'])
        self.peer = self.signed(self.source['nativePeerConfigPin'])
        self.check()

    def read(self, reference, limit=128*1024*1024, *, executable=False, installed=False, native_role=None):
        pin(reference); path = Path(reference['path'])
        if not (path == Path(LAB_ROOT) or Path(LAB_ROOT) in path.parents):
            require((executable or installed) and native_role is not None,
                    'BACKUP_LAB_PATH_OUTSIDE_SCOPE')
            return self.read_native(reference, role=native_role, limit=limit)
        import formal_boot_state as boot
        path = boot._absolute(reference['path'])
        require(native_role is None, 'BACKUP_LAB_NATIVE_ROLE_PATH_INVALID')
        require(path == Path(LAB_ROOT) or Path(LAB_ROOT) in path.parents, 'BACKUP_LAB_PATH_OUTSIDE_SCOPE')
        import stat
        mode=stat.S_IMODE(path.lstat().st_mode) if executable or installed else 0o600
        require(not executable or mode in (0o700,0o750,0o755),'BACKUP_LAB_EXECUTABLE_NOT_TRUSTED')
        require(not installed or mode in (0o600,0o644,0o700,0o750,0o755),'BACKUP_LAB_INSTALLED_MODE_INVALID')
        require(not installed or path.suffix not in ('.py','.json','.pem') or mode==0o600,
                'BACKUP_LAB_PRIVATE_RECORD_MODE_INVALID')
        pair = boot._read_secure(path, mode, limit, no_atime=True)
        require(len(pair[0]) == reference['bytes'] and hashlib.sha256(pair[0]).hexdigest() == reference['sha256'],
                'BACKUP_LAB_ORIGINAL_CHANGED')
        if path in self.originals:
            require(self.originals[path][0] == pair and self.originals[path][2]==mode, 'BACKUP_LAB_ORIGINAL_CHANGED')
        else:
            with boot._directory(path.parent, no_atime=True) as (_, chain): self.directories[path.parent] = chain
            self.originals[path] = (pair, limit, mode)
        return pair[0]

    def _load_native_runtime(self):
        """Load only W03 originals co-installed beside this approved module.

        No import-path override or copy of the shared wire implementation. Exact
        descriptor-read bytes are executed, not reopened by an import loader.
        """
        import importlib.util
        selected = self.installation['filePins']
        modules = []
        root = Path(__file__).absolute().parent
        for name in ('repository_records', 'repository_native_runtime'):
            matches = [p for p in selected if p['path'] == str(root / (name + '.py'))]
            require(len(matches) == 1, 'BACKUP_LAB_NATIVE_HELPER_NOT_INSTALLED')
            reference = matches[0]; raw = self.read(reference, installed=True)
            existing = sys.modules.get(name)
            if existing is not None:
                require(getattr(existing, '__file__', None) == reference['path'] and
                        getattr(existing, '_backup_lab_original_pin', None) == reference,
                        'BACKUP_LAB_NATIVE_HELPER_IMPORT_CHANGED')
                modules.append(existing)
                continue
            spec = importlib.util.spec_from_file_location(name, reference['path'])
            require(spec is not None, 'BACKUP_LAB_NATIVE_HELPER_REQUIRED')
            module = importlib.util.module_from_spec(spec)
            module._backup_lab_original_pin = dict(reference)
            sys.modules[name] = module
            try:
                exec(compile(raw, reference['path'], 'exec'), module.__dict__)
            except BaseException:
                if sys.modules.get(name) is module:
                    del sys.modules[name]
                raise
            modules.append(module)
        helper = modules[-1]
        require(callable(getattr(helper, 'verify_native_installation', None)) and
                callable(getattr(helper, 'read_native_member', None)), 'BACKUP_LAB_NATIVE_HELPER_API_REQUIRED')
        self.native_runtime = helper

    def verify_installation(self):
        fields = {'schemaVersion', 'root', 'sourceToolkitPin', 'filePins', 'pythonPin', 'dependencyPins'}
        schema = self.installation.get('schemaVersion')
        if schema == 'RepositoryNativeInstallation/v1':
            exact(self.installation, fields, schema)
            require(self.native_runtime is None, 'BACKUP_LAB_INSTALLATION_CHANGED')
        else:
            exact(self.installation, fields | {'nativeRuntimeTrustPin', 'nativeRuntimeProofPin'},
                  'RepositoryNativeInstallation/v2')
        require(self.installation['root'] == LAB_ROOT and self.installation['pythonPin'] == self.host['pythonPin'] and
                type(self.installation['filePins']) is list and self.installation['filePins'] and
                type(self.installation['dependencyPins']) is list and self.installation['dependencyPins'],
                'BACKUP_LAB_INSTALLATION_CHANGED')
        selected = self.installation['filePins'] + self.installation['dependencyPins'] + [self.installation['pythonPin']]
        paths = [pin(p)['path'] for p in selected]
        require(len(paths) == len(set(paths)), 'BACKUP_LAB_INSTALLATION_DUPLICATE')
        if schema == 'RepositoryNativeInstallation/v1':
            require(all(Path(LAB_ROOT) in Path(p).parents for p in paths), 'BACKUP_LAB_PATH_OUTSIDE_SCOPE')
        # Programs, Python and all private records retain LAB-only admission.
        for reference in self.installation['filePins'] + [self.installation['pythonPin'], self.installation['sourceToolkitPin']]:
            path = Path(reference['path'])
            require(Path(LAB_ROOT) in path.parents, 'BACKUP_LAB_PATH_OUTSIDE_SCOPE')
        if schema == 'RepositoryNativeInstallation/v2':
            self._load_native_runtime()
            verified = self.native_runtime.verify_native_installation(
                self.context['installedClosurePin'], [self.key_pin])
            require(verified == self.installation, 'BACKUP_LAB_INSTALLATION_CHANGED')
            self.native_trust = self.signed(self.installation['nativeRuntimeTrustPin'])
            self.native_proof = self.signed(self.installation['nativeRuntimeProofPin'])
            require(self.native_trust['runtimeRole'] == 'EXECUTOR' and
                    self.native_proof['hostId'] == self.host['hostId'] and
                    self.native_proof['bootId'] == self.host['bootId'] and
                    self.native_proof['pidNamespace'] == self.host['pidNamespace'] and
                    self.native_proof['mountNamespace'] == self.host['mountNamespace'],
                    'BACKUP_LAB_NATIVE_RUNTIME_BINDING_CHANGED')
        for reference in self.installation['filePins'] + self.installation['dependencyPins']:
            path = Path(reference['path'])
            role = None if Path(LAB_ROOT) in path.parents else self.native_member_role(reference)
            self.read(reference, installed=True, native_role=role)
        self.read(self.installation['pythonPin'], executable=True)

    def native_member_role(self, reference):
        require(self.native_runtime is not None and self.native_trust is not None,
                'BACKUP_LAB_NATIVE_RUNTIME_REQUIRED')
        entries = [entry for entry in self.native_trust['nativeFilePins'] if entry['pin'] == reference]
        require(len(entries) == 1 and type(entries[0]['roles']) is list and entries[0]['roles'],
                'BACKUP_LAB_NATIVE_MEMBER_NOT_DECLARED')
        return entries[0]['roles'][0]

    def read_native(self, reference, *, role, limit=128*1024*1024):
        require(self.installation.get('schemaVersion') == 'RepositoryNativeInstallation/v2' and
                self.native_runtime is not None and self.native_trust is not None and self.native_proof is not None and
                reference in self.installation['dependencyPins'], 'BACKUP_LAB_NATIVE_MEMBER_NOT_DECLARED')
        raw = self.native_runtime.read_native_member(reference, self.installation['nativeRuntimeTrustPin'],
            self.installation['nativeRuntimeProofPin'], role=role, limit=limit)
        pin(reference)
        require(type(raw) is bytes and len(raw) == reference['bytes'] and len(raw) <= limit and
                hashlib.sha256(raw).hexdigest() == reference['sha256'], 'BACKUP_LAB_ORIGINAL_CHANGED')
        identity = (dict(reference), role); member = (reference['path'], role)
        if member in self.native_originals:
            require(self.native_originals[member][0] == identity and
                    self.native_originals[member][1] == raw, 'BACKUP_LAB_ORIGINAL_CHANGED')
        else:
            self.native_originals[member] = (identity, raw, limit)
        return raw

    def document(self, reference):
        return strict_document(self.read(reference), 128*1024*1024)

    def signed(self, reference):
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        envelope = exact(self.document(reference), {'schemaVersion', 'keySha256', 'payload', 'signature'},
                         'RepositorySignedRecord/v1')
        require(envelope['keySha256'] == self.key_pin['sha256'], 'BACKUP_LAB_AUTHORITY_UNKNOWN')
        try:
            key = load_pem_public_key(self.read(self.key_pin, 65536))
            require(isinstance(key, Ed25519PublicKey), 'BACKUP_LAB_KEY_INVALID')
            key.verify(base64.b64decode(envelope['signature'], validate=True), canonical(envelope['payload']))
        except (ValueError, TypeError, InvalidSignature):
            raise snapshot.FormalSnapshotError('BACKUP_LAB_SIGNATURE_INVALID') from None
        return envelope['payload']

    def check(self):
        import formal_boot_state as boot
        require(os.getpid() == self.pid and threading.get_ident() == self.thread,
                'BACKUP_LAB_OWNER_CHANGED')
        self.guard()
        validate_context(self.context,self.key_pin)
        require(all(self.context[k]==v for k,v in self.expected.items()),'BACKUP_LAB_CONTEXT_CHANGED')
        for reference, retained, signed in ((self.context_pin,self.context,True),
                (self.context['operationRequestPin'],self.request,False),
                (self.context['labScopePin'],self.scope,True),
                (self.context['authorizationPin'],self.grant,True),
                (self.context['leasePin'],self.lease,True),
                (self.context['executionHostPin'],self.host,False),
                (self.context['installedClosurePin'],self.installation,True),
                (self.context['sourceIdentityPin'],self.identity,False),
                (self.request['sourceOrTargetRef'],self.source,False),
                (self.request['policyPin'],self.policy,True),
                (self.source['nativePeerConfigPin'],self.peer,True)):
            original = self.document(reference)
            require((original['payload'] if signed else original) == retained, 'BACKUP_LAB_CONTEXT_CHANGED')
        elapsed = time.monotonic() - self.clock; now = time.time()
        require(elapsed >= 0 and abs(now-self.wall-elapsed) < 2 and
                timestamp(self.context['issuedAt']) <= now < timestamp(self.context['expiresAt']),
                'BACKUP_LAB_AUTHORITY_EXPIRED')
        request = self.request; scope = self.scope; host = self.host
        exact(scope, set(('schemaVersion rehearsalId repositoryId sourceIdentityPin host root resourcePrefix '
            'allowedActions expiresAt').split()), 'RepositoryLabScope/v1')
        require(scope['rehearsalId'] == LAB_ID and scope['host'] == '172.30.30.59' and
                scope['root'] == LAB_ROOT and scope['resourcePrefix'] == 'brlab-20261012' and
                scope['sourceIdentityPin'] == self.context['sourceIdentityPin'] and
                valid_action_scope(scope['allowedActions'],request['action'],self.grant['actions']) and
                request['mode'] == 'REHEARSAL' and request['action'] in {'BACKUP_FULL', 'BACKUP_INCREMENTAL'} and
                request['action'] in scope['allowedActions'] and timestamp(scope['expiresAt']) > now and
                self.context['authorizationPin'] in request['authorizationRefs'] and
                self.context['leasePin'] == request['leaseRef'], 'BACKUP_LAB_OPERATION_NOT_AUTHORIZED')
        exact(self.grant, set(('schemaVersion repositoryId operationId actions sourceOrTargetRef policyPin resourcePin '
            'notBefore expiresAt leaseRef').split()), 'RepositoryAuthorization/v1')
        exact(self.lease, {'schemaVersion', 'repositoryId', 'operationId', 'ownerIdentityPin', 'expiresAt'},
              'RepositoryLease/v1')
        repository_binding(self.source,self.policy,self.peer,scope,self.grant,self.lease,self.context,request)
        require(self.grant['repositoryId'] == self.lease['repositoryId'] == scope['repositoryId'] and
                self.grant['operationId'] == self.lease['operationId'] == request['operationId'] and
                request['action'] in self.grant['actions'] and
                self.grant['sourceOrTargetRef'] == self.grant['resourcePin'] == request['sourceOrTargetRef'] and
                self.grant['policyPin'] == request['policyPin'] and self.grant['leaseRef'] == self.context['leasePin'] and
                timestamp(self.grant['notBefore']) <= now < timestamp(self.grant['expiresAt']) and
                timestamp(self.lease['expiresAt']) > now, 'BACKUP_LAB_GRANT_LEASE_CHANGED')
        self.read(self.lease['ownerIdentityPin'])
        exact(host, set(('schemaVersion hostOs hostId bootId uid gid pidNamespace mountNamespace pythonPin '
            'sourceProfilePin dispatcherPin resourceObserverPin workingDirectory evidenceRoot environment '
            'installationManifestPin').split()), 'RepositoryNativeExecutionHost/v1')
        require(sys.platform.startswith('linux') and os.geteuid() == os.getegid() == 0 and
                host['hostOs'] == 'Linux' and host['uid'] == host['gid'] == 0 and
                host['hostId'] == Path('/etc/machine-id').read_text(encoding='ascii').strip() and
                host['bootId'] == Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip() and
                host['pidNamespace'] == os.readlink('/proc/self/ns/pid') and
                host['mountNamespace'] == os.readlink('/proc/self/ns/mnt') and
                Path(host['pythonPin']['path']) == Path(sys.executable).absolute() and
                host['installationManifestPin'] == self.context['installedClosurePin'], 'BACKUP_LAB_NATIVE_HOST_CHANGED')
        self.verify_installation()
        for (reference, role), raw, limit in tuple(self.native_originals.values()):
            require(self.read_native(reference, role=role, limit=limit) == raw, 'BACKUP_LAB_ORIGINAL_CHANGED')
        for path, chain in self.directories.items(): boot._directory_unchanged(path, chain)
        for path, (pair, limit, mode) in self.originals.items():
            require(boot._read_secure(path, mode, limit, no_atime=True) == pair, 'BACKUP_LAB_ORIGINAL_CHANGED')
        for path, (pair, _, _) in self.originals.items():
            require(boot._signature(path.lstat()) == pair[1], 'BACKUP_LAB_ORIGINAL_CHANGED')

    @contextmanager
    def activate(self):
        self.check(); token = active_lab.set(self)
        try: yield self
        finally: active_lab.reset(token)

    def verify_service(self, reference):
        service=self.document(reference)
        require(service.get('schemaVersion')=='RepositoryNativeServiceConfig/v1' and
            service['repositoryId']==self.scope['repositoryId'] and
            service['executionHostPin']==self.context['executionHostPin'] and
            service['labScopePin']==self.context['labScopePin'] and
            self.key_pin in service['authorityKeyPins'] and
            service['policyPin']==self.request['policyPin'],'BACKUP_LAB_SERVICE_BINDING_CHANGED')
        return service


def repository_binding(source, policy, peer, scope, grant, lease, context, request):
    """Frozen request intentionally has no repositoryId field."""
    require(source.get('schemaVersion')=='RepositoryNativeBackupSource/v1' and
        policy.get('schemaVersion')=='RepositoryPolicy/v1' and peer.get('schemaVersion')=='RepositoryNativePeerConfig/v2' and
        type(scope.get('repositoryId')) is str and scope['repositoryId'] and
        all(record.get('repositoryId')==scope['repositoryId'] for record in (source,policy,peer,grant,lease)) and
        source['sourceIdentityPin']==policy['sourceIdentityPin']==peer['sourceIdentityPin']==scope['sourceIdentityPin']==context['sourceIdentityPin'] and
        source['executionHostPin']==peer['executionHostPin']==context['executionHostPin'] and
        peer['labScopePin']==context['labScopePin'] and grant['sourceOrTargetRef']==request['sourceOrTargetRef'] and
        grant['policyPin']==request['policyPin'],'BACKUP_LAB_REPOSITORY_BINDING_CHANGED')
    return scope['repositoryId']


def valid_action_scope(actions, action, grant_actions):
    require(type(actions) is list and actions and all(type(a) is str for a in actions) and
        len(set(actions))==len(actions) and set(actions)<=LAB_ACTIONS and
        type(action) is str and action in actions and type(grant_actions) is list and
        all(type(a) is str for a in grant_actions) and len(set(grant_actions))==len(grant_actions) and
        set(grant_actions)<=LAB_ACTIONS and action in grant_actions, 'BACKUP_LAB_OPERATION_NOT_AUTHORIZED')
    return True


def nas_capacity(document, workspace, intent):
    """Finite 80GiB lab ceiling; production constants remain independent."""
    from formal_normal_owner import integer
    for name in ('budgetBytes','reserveBytes','maxAttemptBytes'):integer(workspace[name],1,80*1024**3)
    for name in ('workspaceUsageBytes','availableBytes'):integer(document[name])
    for name in ('logicalPayloadUpperBoundBytes','nasAllocatedUpperBoundBytes'):integer(document[name],1)
    require(document['workspaceBudgetBytes']==workspace['budgetBytes'] and
        document['maxAttemptBytes']==workspace['maxAttemptBytes'] and document['reserveBytes']==workspace['reserveBytes'] and
        workspace['maxAttemptBytes']+workspace['reserveBytes']<=workspace['budgetBytes'] and
        all(type(document[k]) is int for k in ('workspaceBudgetBytes','maxAttemptBytes','reserveBytes')) and
        all(document[k]==intent[k] for k in ('logicalPayloadUpperBoundBytes','nasAllocatedUpperBoundBytes')),
        'BACKUP_LAB_NAS_BUDGET_CHANGED')
    require(document['logicalPayloadUpperBoundBytes']<=workspace['maxAttemptBytes'] and
        document['nasAllocatedUpperBoundBytes']<=workspace['maxAttemptBytes'] and
        document['workspaceUsageBytes']+document['nasAllocatedUpperBoundBytes']+workspace['reserveBytes']<=workspace['budgetBytes'] and
        document['availableBytes']>=document['nasAllocatedUpperBoundBytes']+workspace['reserveBytes'],
        'BACKUP_INTERFACE_CAPACITY_INSUFFICIENT')


def validate_nas_admission(document, intent, authority):
    from formal_normal_owner import NAS_ADMISSION_FIELDS, binding, integer
    require(type(authority) is LabAuthority,'BACKUP_LAB_CURRENT_AUTHORITY_REQUIRED');authority.check()
    exact(document,NAS_ADMISSION_FIELDS|{'labContextPin','workspacePin'},'backup-lab-nas-admission/v1')
    binding(document['binding'])
    require(document['binding']==intent.document['binding'] and document['intent']==intent.document and
        document['intentReference']==intent.reference.reference and document['labContextPin']==authority.context_pin and
        document['workspacePin']==authority.source['workspacePin'] and
        document['binding']['nasWorkspaceConfigSha256']==document['workspacePin']['sha256'],
        'BACKUP_LAB_NAS_BINDING_CHANGED')
    require(type(document['admissionId']) is str and re.fullmatch('[0-9a-f]{64}',document['admissionId']),
        'BACKUP_LAB_NAS_BINDING_CHANGED')
    for name in ('authorIdentityReference','resourceObservationReference','allocationProofReference','workspacePin'):pin(document[name])
    workspace=authority.document(document['workspacePin'])
    exact(workspace,set(('schemaVersion repositoryId root rootIdentityPin budgetBytes reserveBytes maxAttemptBytes '
        'allocationProofPin resourceObservationPin').split()),'RepositoryNativeWorkspace/v1')
    require(workspace['repositoryId']==authority.scope['repositoryId'] and
        workspace['root']==authority.source['workspaceDirectory'] and
        document['allocationProofReference']==workspace['allocationProofPin'] and
        document['resourceObservationReference']==workspace['resourceObservationPin'], 'BACKUP_LAB_NAS_WORKSPACE_CHANGED')
    nas_capacity(document,workspace,intent.document)
    require(document['authorHeld'] is True and document['preCaptureAdmitted'] is True and
        document['exclusionScope']=='cooperative-workspace-writers' and all(document[k] is False for k in
        ('spaceGuaranteed','allWritersExcluded','nasHardQuotaConfigured','automaticDeletion')), 'BACKUP_INTERFACE_ADMISSION_REQUIRED')
    author=authority.document(document['authorIdentityReference'])
    exact(author,set(('schemaVersion pid bootId rootIdentity lockPath device inode fd workspacePin requestPin').split()),
        'RepositoryNativeWorkspaceAuthor/v1')
    require(author['workspacePin']==document['workspacePin'] and author['requestPin']==authority.context['operationRequestPin'] and
        author['bootId']==authority.host['bootId'] and type(author['pid']) is int and author['pid']>0 and
        type(author['fd']) is int and author['fd']>=0,'BACKUP_LAB_NAS_AUTHOR_CHANGED')
    root=Path(workspace['root']);info=root.lstat()
    import stat
    require(Path(LAB_ROOT) in root.parents and stat.S_ISDIR(info.st_mode) and info.st_uid==0 and
        stat.S_IMODE(info.st_mode)==0o700 and not root.is_symlink(),'BACKUP_LAB_NAS_WORKSPACE_CHANGED')
    root_identity=authority.document(workspace['rootIdentityPin'])
    require(root_identity==author['rootIdentity']==dict(path=str(root),device=info.st_dev,inode=info.st_ino,uid=info.st_uid,
        gid=info.st_gid,mode=stat.S_IMODE(info.st_mode)),'BACKUP_LAB_NAS_WORKSPACE_CHANGED')
    resource=authority.peer['resourceRoots']['nas'];geometry=authority.document(resource['identityPin'])
    disk=os.statvfs(root)
    require(resource['root']==str(root) and resource['observationPin']==workspace['resourceObservationPin'] and
        resource['budgetBytes']==workspace['budgetBytes'] and resource['reserveBytes']==workspace['reserveBytes'] and
        geometry==dict(device=info.st_dev,inode=info.st_ino,fragmentBytes=disk.f_frsize,blockBytes=disk.f_bsize,filesystemId=disk.f_fsid),
        'BACKUP_LAB_NAS_GEOMETRY_CHANGED')
    proof=authority.document(workspace['allocationProofPin'])
    require(proof.get('schemaVersion')=='release-production-backup-allocation-proof/v1' and
        proof.get('deviceIdentitySha256')==resource['identityPin']['sha256'] and
        type(proof.get('rules')) is dict and proof['rules']['allocationUnitBytes']>=disk.f_frsize,
        'BACKUP_LAB_NAS_ALLOCATION_UNPROVEN')
    authority.read(proof['verificationReference']);authority.read(workspace['resourceObservationPin'])
    lock=Path(author['lockPath']);require(lock==root/'.repository-control/native-author.lock','BACKUP_LAB_NAS_AUTHOR_CHANGED')
    held=os.stat('/proc/%d/fd/%d'%(author['pid'],author['fd']));named=lock.lstat()
    require((held.st_dev,held.st_ino)==(named.st_dev,named.st_ino)==(author['device'],author['inode']) and
        named.st_uid==0 and stat.S_IMODE(named.st_mode)==0o600,'BACKUP_LAB_NAS_AUTHOR_CHANGED')
    lock_identity='%02x:%02x:%d'%(os.major(named.st_dev),os.minor(named.st_dev),named.st_ino)
    locks=[line.split() for line in Path('/proc/locks').read_text(encoding='ascii').splitlines()]
    require(any(len(row)>=8 and row[1:4]==['FLOCK','ADVISORY','WRITE'] and
        row[4]==str(author['pid']) and row[5]==lock_identity and row[6:8]==['0','EOF'] for row in locks),
        'BACKUP_LAB_NAS_AUTHOR_LOCK_NOT_HELD')
    require(document['availableBytes']<=disk.f_bavail*disk.f_frsize,'BACKUP_LAB_NAS_OBSERVATION_STALE')
    wire=exact_budget(document['budget']);require(wire['observationReference']==document['authorIdentityReference'],
        'BACKUP_LAB_NAS_OBSERVER_CHANGED')
    authority.check();return document


def exact_budget(value):
    from formal_normal_owner import integer
    require(type(value) is dict and set(value)=={'remainingMilliseconds','observationReference'},'BACKUP_LAB_BUDGET_INVALID')
    integer(value['remainingMilliseconds'],1,7200000);pin(value['observationReference']);return value


def require_authority(scope):
    validate_source_scope(scope)
    authority = active_lab.get()
    require(type(authority) is LabAuthority and authority.context_pin == scope['labContextPin'],
            'BACKUP_LAB_CURRENT_AUTHORITY_REQUIRED')
    authority.check()
    require(authority.identity['sourceFingerprint'] == scope['targetFingerprint'] and
            authority.identity['databaseUuid'] == scope['databaseUuid'], 'BACKUP_LAB_SOURCE_IDENTITY_CHANGED')
    return authority


def selected_authority(authority_key_pin, *, expected, guard):
    """Out-of-band selection after the immutable operation request exists."""
    import formal_boot_state as boot
    path=os.environ.get('INTRUOYI_BACKUP_LAB_CONTEXT_PATH')
    digest=os.environ.get('INTRUOYI_BACKUP_LAB_CONTEXT_SHA256')
    require(type(path) is str and type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest),
            'BACKUP_LAB_EXPLICIT_CONTEXT_REQUIRED')
    pair=boot._read_secure(boot._absolute(path),0o600,65536,no_atime=True)
    require(hashlib.sha256(pair[0]).hexdigest()==digest,'BACKUP_LAB_CONTEXT_CHANGED')
    return LabAuthority(dict(path=path,bytes=len(pair[0]),sha256=digest),authority_key_pin,expected=expected,guard=guard)


def launch_authority(guard):
    """The installed launcher selects trust separately from the signed context."""
    import formal_boot_state as boot
    path=os.environ.get('INTRUOYI_BACKUP_LAB_TRUST_PATH')
    digest=os.environ.get('INTRUOYI_BACKUP_LAB_TRUST_SHA256')
    require(type(path) is str and type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest),
            'BACKUP_LAB_INSTALLED_LAUNCH_TRUST_REQUIRED')
    trust_path=boot._absolute(path);pair=boot._read_secure(trust_path,0o600,65536,no_atime=True)
    require(hashlib.sha256(pair[0]).hexdigest()==digest,'BACKUP_LAB_LAUNCH_TRUST_CHANGED')
    trust=exact(strict_document(pair[0],65536),{'schemaVersion','authorityKeyPin','expectedContextPins','hostBoundaryPin'},
                'backup-lab-launch-trust/v1')
    key_path=os.environ.get('INTRUOYI_BACKUP_LAB_AUTHORITY_KEY_PATH')
    key_digest=os.environ.get('INTRUOYI_BACKUP_LAB_AUTHORITY_KEY_SHA256')
    require(type(key_path) is str and type(key_digest) is str and
            trust['authorityKeyPin']['path']==key_path and trust['authorityKeyPin']['sha256']==key_digest,
            'BACKUP_LAB_INDEPENDENT_AUTHORITY_SELECTION_REQUIRED')
    def checked():
        guard()
        require(boot._read_secure(trust_path,0o600,65536,no_atime=True)==pair,'BACKUP_LAB_LAUNCH_TRUST_CHANGED')
    authority=selected_authority(trust['authorityKeyPin'],expected=trust['expectedContextPins'],guard=checked)
    boundary=authority.signed(trust['hostBoundaryPin'])
    exact(boundary,{'schemaVersion','executionHostPin','labScopePin','managerRoot','writerEvidencePins',
        'pidNamespace','mountNamespace','networkNamespace','hostPidNamespace','hostMountNamespace',
        'systemdBusSocketPin','managerIdentityPin'},'backup-lab-native-host-boundary/v1')
    require(boundary['executionHostPin']==authority.context['executionHostPin'] and
        boundary['labScopePin']==authority.context['labScopePin'] and
        boundary['pidNamespace']==os.readlink('/proc/self/ns/pid') and
        boundary['mountNamespace']==os.readlink('/proc/self/ns/mnt') and
        boundary['networkNamespace']==os.readlink('/proc/self/ns/net') and
        boundary['pidNamespace']!=boundary['hostPidNamespace'] and
        boundary['mountNamespace']!=boundary['hostMountNamespace'] and
        Path(LAB_ROOT) in Path(boundary['managerRoot']).parents and
        type(boundary['writerEvidencePins']) is list and boundary['writerEvidencePins'],
        'BACKUP_LAB_ISOLATED_HOST_MANAGER_REQUIRED')
    # Existing systemctl must actually reach a task-owned private manager.
    # A path mapping/wrapper is not evidence and shared fixed host units cannot
    # be closed by this profile. The native operations remain unchanged.
    bus=Path('/run/systemd/private');info=bus.lstat()
    import stat
    require(stat.S_ISSOCK(info.st_mode) and not bus.is_symlink(), 'BACKUP_LAB_SYSTEMD_BUS_REQUIRED')
    proof=authority.document(boundary['systemdBusSocketPin'])
    require(proof==dict(path=str(bus),dev=info.st_dev,ino=info.st_ino,managerRoot=boundary['managerRoot']),
            'BACKUP_LAB_SYSTEMD_BUS_CHANGED')
    for reference in boundary['writerEvidencePins']:authority.read(reference)
    manager=authority.document(boundary['managerIdentityPin'])
    exact(manager,set(('schemaVersion pid uid gid processStartTicks executablePin rootDevice rootInode '
        'pidNamespace mountNamespace networkNamespace bootId').split()),'backup-lab-native-manager-identity/v1')
    # Late operation/host records are deliberately outside the installation
    # manifest: embedding them would form installedClosure -> host -> closure
    # and operationRequest -> context cycles. The independent launcher selects
    # their original Pins, while the stable authority key is installed first.
    require(trust['authorityKeyPin'] in authority.installation['filePins'],
            'BACKUP_LAB_AUTHORITY_KEY_NOT_INSTALLED')
    def isolated_guard():
        checked()
        current=bus.lstat()
        require(os.readlink('/proc/self/ns/pid')==boundary['pidNamespace'] and
            os.readlink('/proc/self/ns/mnt')==boundary['mountNamespace'] and
            os.readlink('/proc/self/ns/net')==boundary['networkNamespace'] and
            current.st_dev==info.st_dev and current.st_ino==info.st_ino and stat.S_ISSOCK(current.st_mode),
            'BACKUP_LAB_HOST_BOUNDARY_CHANGED')
        verify_native_manager(manager,boundary,authority)
    authority.guard=isolated_guard
    authority.check()
    return authority


def verify_native_manager(manager, boundary, authority):
    """Observe the real bus peer PID, executable bytes, root and namespaces."""
    import socket
    import struct
    import stat
    require(type(manager['pid']) is int and manager['pid']==1 and manager['uid']==manager['gid']==0 and
        manager['bootId']==authority.host['bootId'] and manager['executablePin'] in
        authority.installation['filePins']+authority.installation['dependencyPins'],
        'BACKUP_LAB_NATIVE_MANAGER_CHANGED')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.settimeout(snapshot.observation_timeout(2))
        connection.connect('/run/systemd/private')
        pid,uid,gid=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize('3i')))
    require((pid,uid,gid)==(manager['pid'],0,0),'BACKUP_LAB_NATIVE_MANAGER_PEER_CHANGED')
    process=Path('/proc')/str(pid)
    raw=(process/'stat').read_text(encoding='ascii');tail=raw[raw.rfind(')')+2:].split()
    require(len(tail)>19 and tail[19]==str(manager['processStartTicks']) and
        (process/'comm').read_text(encoding='ascii').strip()=='systemd','BACKUP_LAB_NATIVE_MANAGER_CHANGED')
    for name,ns in (('pidNamespace','pid'),('mountNamespace','mnt'),('networkNamespace','net')):
        require(os.readlink(process/'ns'/ns)==manager[name]==boundary[name],'BACKUP_LAB_NATIVE_MANAGER_CHANGED')
    root=(process/'root').stat()
    own_root=Path('/').stat()
    require(root.st_dev==manager['rootDevice']==own_root.st_dev and root.st_ino==manager['rootInode']==own_root.st_ino,
        'BACKUP_LAB_NATIVE_MANAGER_ROOT_CHANGED')
    executable_path=Path(manager['executablePin']['path'])
    if Path(LAB_ROOT) in executable_path.parents:
        approved=authority.read(manager['executablePin'],executable=True)
    else:
        approved=authority.read_native(manager['executablePin'],role='native-manager')
    exe=process/'exe';before=exe.stat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid==0 and not before.st_mode&0o022,
        'BACKUP_LAB_NATIVE_MANAGER_EXECUTABLE_CHANGED')
    with exe.open('rb') as stream:
        first=os.fstat(stream.fileno());digest=hashlib.file_digest(stream,'sha256').hexdigest();last=os.fstat(stream.fileno())
    require((first.st_dev,first.st_ino,first.st_size,first.st_mtime_ns)==
        (last.st_dev,last.st_ino,last.st_size,last.st_mtime_ns)==
        (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) and
        len(approved)==before.st_size and digest==manager['executablePin']['sha256'],
        'BACKUP_LAB_NATIVE_MANAGER_EXECUTABLE_CHANGED')


def current_authority():
    authority=active_lab.get()
    require(type(authority) is LabAuthority,'BACKUP_LAB_CURRENT_AUTHORITY_REQUIRED')
    authority.check();return authority


def approved_capture_source(target_raw, approved_sha, claim_raw, database):
    from formal_source_migration_ledger import approved_source_scope, approved_lab_source_scope
    authority=active_lab.get()
    if authority is None:return approved_source_scope(target_raw,approved_sha,claim_raw,database)
    require(type(authority) is LabAuthority,'BACKUP_LAB_CURRENT_AUTHORITY_REQUIRED')
    authority.check()
    scope=approved_lab_source_scope(target_raw,approved_sha,claim_raw,database,authority.context_pin)
    require_authority(scope);return scope


def validate_recipe(value):
    from formal_normal_owner_entry import validate_recipe as production_recipe
    require(type(value) is dict,'BACKUP_LAB_SCHEMA_INVALID')
    exact(value, {'schemaVersion','action','totalSeconds','attribution','executionContractPin','creationResultsPin',
        'claimRoot','claimBinding','nativeAssemblyProgramPin','nativeAssemblyConfigPin',
        'nativeInitializationProgramPin','nativeInitializationConfigPin','labContextPin'}, 'backup-lab-normal-owner-recipe/v1')
    pin(value['labContextPin'])
    common={k:v for k,v in value.items() if k!='labContextPin'}
    common['schemaVersion']='backup-normal-owner-recipe/v2';production_recipe(common)
    return value


def validate_assembly(value):
    from formal_normal_owner_assembly import validate_configuration
    require(type(value) is dict and value.get('schemaVersion')=='backup-lab-native-assembly-config/v1' and
            'labContextPin' in value,'BACKUP_LAB_SCHEMA_INVALID')
    pin(value['labContextPin'])
    common={k:v for k,v in value.items() if k!='labContextPin'}
    common['schemaVersion']='backup-normal-owner-assembly/v1';validate_configuration(common)
    return value


def verify_runtime_derivation(recipe, assembly, profile, authority):
    """Verify W03's actual late originals against the original selected templates."""
    require(type(authority) is LabAuthority,'BACKUP_LAB_CURRENT_AUTHORITY_REQUIRED');authority.check()
    require(profile['schemaVersion']=='RepositoryLabNativeInitialization/v1' and
        profile['assemblyPin']==recipe['nativeAssemblyConfigPin'] and
        profile['requestPin']==authority.context['operationRequestPin'] and
        profile['labContextPin']==authority.context_pin and
        authority.document(profile['assemblyPin'])==assembly,'BACKUP_LAB_RUNTIME_PIN_CHANGED')
    service=authority.verify_service(profile['configurationPin'])
    require(profile['sourceConfigPin']==authority.request['sourceOrTargetRef'] and
        profile['peerConfigPin']==authority.source['nativePeerConfigPin'] and
        profile['assemblyTemplatePin']==authority.peer['assemblyTemplatePin'], 'BACKUP_LAB_RUNTIME_TEMPLATE_CHANGED')
    stable_recipe=authority.document(authority.peer['recipeTemplatePin'])
    stable_assembly=authority.document(profile['assemblyTemplatePin'])
    capture=authority.document(stable_assembly['captureRequestPin'])
    original_scope=exact(capture['sourceScope'],SCOPE_FIELDS-{'labContextPin'},'backup-lab-source-scope-template/v1')
    source_scope=dict(original_scope,schemaVersion='backup-lab-source-scope/v1',labContextPin=authority.context_pin)
    expected=derive_owner_records(stable_recipe,stable_assembly,capture,authority=authority,source_scope=source_scope)
    expected_assembly=expected['assembly'];expected_recipe=expected['recipe']
    for name,key in (('captureRequestPin','capture'),('resumeRequestPin','resume')):
        require(authority.document(assembly[name])==expected[key], 'BACKUP_LAB_RUNTIME_DERIVATION_CHANGED')
        expected_assembly[name]=assembly[name]
    resume_template=authority.document(stable_assembly['resumeRequestPin'])
    exact(resume_template,{'schemaVersion'},'backup-lab-resume-template/v1')
    release_template=authority.document(stable_assembly['inputReferences']['release_binding'])
    exact(release_template,{'schemaVersion','rehearsalId','claimBindingSha256','approvedSourceTargetSha256','productionEvidence'},
        'backup-lab-original-package-binding-template/v1')
    require(dict(release_template,schemaVersion='backup-lab-original-package-binding/v1',labContextPin=authority.context_pin)==
        expected['originalBinding'] and authority.document(assembly['inputReferences']['release_binding'])==expected['originalBinding'],
        'BACKUP_LAB_RUNTIME_RELEASE_CHANGED')
    expected_assembly['inputReferences']['release_binding']=assembly['inputReferences']['release_binding']
    expected_assembly['binding']['originalReleaseBindingSha256']=assembly['inputReferences']['release_binding']['sha256']
    channel=authority.document(assembly['channelPin'])
    require(channel.get('schemaVersion')=='backup-native-observation-channel/v1' and
        channel['bindingSha256']==hashlib.sha256(canonical(assembly['binding'])).hexdigest(),
        'BACKUP_LAB_RUNTIME_CHANNEL_CHANGED')
    expected_assembly['channelPin']=assembly['channelPin']
    expected_recipe['nativeAssemblyConfigPin']=profile['assemblyPin']
    expected_recipe['nativeInitializationConfigPin']=recipe['nativeInitializationConfigPin']
    require(recipe==expected_recipe and assembly==expected_assembly and
        assembly['inputReferences']['source_context']==authority.context['sourceIdentityPin'] and
        assembly['inputReferences']['installed_context']==authority.context['executionHostPin'] and
        assembly['binding']['nasWorkspaceConfigSha256']==authority.source['workspacePin']['sha256'] and
        assembly['binding']['releaseTag']==LAB_ID,'BACKUP_LAB_RUNTIME_DERIVATION_CHANGED')
    require(recipe['nativeInitializationProgramPin'] in authority.installation['filePins'],
        'BACKUP_LAB_INITIALIZER_NOT_INSTALLED')
    authority.check()
    return expected


def derive_owner_records(recipe_template, assembly_template, capture_template, *, authority, source_scope):
    """Derive late records from pinned templates, never repin the request graph.

    Callers read templates via LabAuthority.document. This function only returns
    validated values; writing them is an explicit current-owner operation.
    """
    from formal_normal_owner_entry import validate_recipe as validate_prod_recipe
    from formal_normal_owner_assembly import validate_configuration
    require(type(authority) is LabAuthority,'BACKUP_LAB_CURRENT_AUTHORITY_REQUIRED')
    authority.check();validate_source_scope(source_scope)
    require(source_scope['labContextPin']==authority.context_pin,'BACKUP_LAB_CONTEXT_CHANGED')
    recipe=strict_document(canonical(recipe_template),65536)
    assembly=strict_document(canonical(assembly_template),16*1024*1024)
    capture=strict_document(canonical(capture_template),65536)
    require(recipe.get('schemaVersion')=='backup-lab-normal-owner-recipe-template/v1' and
        assembly.get('schemaVersion')=='backup-lab-native-assembly-template/v1' and
        capture.get('schemaVersion')=='backup-lab-capture-request-template/v1' and
        all('labContextPin' not in value for value in (recipe,assembly,capture)), 'BACKUP_LAB_TEMPLATE_INVALID')
    recipe['schemaVersion']='backup-normal-owner-recipe/v2';validate_prod_recipe(recipe)
    assembly['schemaVersion']='backup-normal-owner-assembly/v1';validate_configuration(assembly)
    template_scope=exact(capture.get('sourceScope'),SCOPE_FIELDS-{'labContextPin'},'backup-lab-source-scope-template/v1')
    require(template_scope==dict((k,'backup-lab-source-scope-template/v1' if k=='schemaVersion' else v)
        for k,v in source_scope.items() if k!='labContextPin'),'BACKUP_LAB_TEMPLATE_SOURCE_CHANGED')
    capture.update(schemaVersion='backup-lab-capture-request/v1',sourceScope=source_scope,
                   labContextPin=authority.context_pin)
    validate_capture_request(capture,source_scope)
    recipe.update(schemaVersion='backup-lab-normal-owner-recipe/v1',labContextPin=authority.context_pin)
    assembly.update(schemaVersion='backup-lab-native-assembly-config/v1',labContextPin=authority.context_pin)
    validate_recipe(recipe);validate_assembly(assembly);authority.check()
    return dict(recipe=recipe,assembly=assembly,capture=capture,
        resume=dict(schemaVersion='backup-lab-resume-request/v1',labContextPin=authority.context_pin),
        originalBinding=dict(schemaVersion='backup-lab-original-package-binding/v1',rehearsalId=LAB_ID,
            labContextPin=authority.context_pin,claimBindingSha256=hashlib.sha256(
                snapshot._canonical_bytes(recipe['claimBinding'])).hexdigest(),
            approvedSourceTargetSha256=source_scope['targetRawSha256'],productionEvidence=False))


def validate_original_binding(raw, authority, claim):
    require(type(authority) is LabAuthority, 'BACKUP_LAB_CURRENT_AUTHORITY_REQUIRED')
    authority.check()
    value = exact(strict_document(raw), {'schemaVersion', 'rehearsalId', 'labContextPin',
        'claimBindingSha256', 'approvedSourceTargetSha256', 'productionEvidence'}, 'backup-lab-original-package-binding/v1')
    require(value['rehearsalId'] == LAB_ID and value['labContextPin'] == authority.context_pin and
            value['claimBindingSha256'] == hashlib.sha256(claim._plan).hexdigest() and
            value['productionEvidence'] is False and
            re.fullmatch('[0-9a-f]{64}', value['approvedSourceTargetSha256']), 'BACKUP_LAB_ORIGINAL_BINDING_CHANGED')
    return value


def resume_binding(release_raw, inventory_raw, expected_sha, authority):
    release = strict_document(release_raw); inventory = strict_document(inventory_raw, 65536)
    from formal_capture_producer import PRODUCTION_A_SOURCE_FILES
    exact(inventory, {'schemaVersion', 'claimBindingSha256', 'approvedSourceTargetSha256', 'hostBootId', 'files'},
          'backup-lab-original-sources/v1')
    require(hashlib.sha256(inventory_raw).hexdigest() == expected_sha and
            set(inventory['files']) == PRODUCTION_A_SOURCE_FILES and
            all(inventory[k] == release[k] for k in ('claimBindingSha256', 'approvedSourceTargetSha256')) and
            inventory['hostBootId'] == authority.host['bootId'], 'BACKUP_LAB_INVENTORY_CHANGED')
    return dict(environment='backup-lab', operationId=authority.request['operationId'],
        approvedSourceTargetSha256=inventory['approvedSourceTargetSha256'], sourceBindingSha256=expected_sha,
        hostBootId=inventory['hostBootId'], labContextPin=authority.context_pin)


class LabResumeChecks:
    """Signed lab operation under the same claim; production A is never consumed."""
    def __init__(self, claim, release_raw, inventory_raw, expected_sha, authority, *, guard, thaw_guard):
        import formal_boot_state as boot
        from formal_capture_producer import ProductionAResumeChecks, _production_a_database_flags
        validate_original_binding(release_raw,authority,claim)
        self.claim=claim; self.authority=authority; self.guard=guard; self.thaw_guard=thaw_guard
        self.binding=resume_binding(release_raw,inventory_raw,expected_sha,authority)
        self.binding_raw=canonical(self.binding); self.pins={}; self.directories={}
        inventory=strict_document(inventory_raw,65536); self.control_device=claim.root.stat().st_dev
        for name,reference in inventory['files'].items():
            path=boot._absolute(reference['path'])
            require(path == claim.root/name, 'BACKUP_LAB_INVENTORY_CHANGED')
            pair=boot._read_secure(path,0o600,16777216,no_atime=True)
            require(pair[1][0]==self.control_device and hashlib.sha256(pair[0]).hexdigest()==reference['sha256'],
                    'BACKUP_LAB_INVENTORY_CHANGED')
            self.pins[path]=(0o600,16777216,pair)
        require(self.pins[claim.root/'binding.json'][2][0]==claim._plan, 'BACKUP_LAB_INVENTORY_CHANGED')
        require(strict_document(claim._plan)['operationId']==authority.request['operationId'] and
                Path(LAB_ROOT) in claim.root.parents,'BACKUP_LAB_OPERATION_CLAIM_CHANGED')
        path=claim.root/'original-release-binding.json'
        pair=boot._read_secure(path,0o600,16384,no_atime=True)
        require(pair[0]==release_raw, 'BACKUP_LAB_ORIGINAL_BINDING_CHANGED')
        self.pins[path]=(0o600,16384,pair)
        with boot._directory(claim.root,no_atime=True) as (_,chain):
            self.database_original_directory=chain; self.directories[claim.root]=chain
        self.database_prefence_path=claim.root/'database-prefence-original.json'
        self.database_prefence_raw=self.pins[self.database_prefence_path][2][0]
        self.database_prefence_flags=_production_a_database_flags(self.database_prefence_raw,strict_document(claim._plan)['databaseUuid'])
        self.database_original_path=claim.root/'database-original.json'; self.database_original_pair=None
        self.prefix=strict_document(canonical(claim.events),65536)
        # This records an already independently signed lab authority, not a
        # production resume consumption or service-action admission.
        self.consumed=dict(state='LAB_SIGNED_OPERATION_BOUND', labContextPin=authority.context_pin,
            issuedAt=timestamp(authority.context['issuedAt']), expiresAt=timestamp(authority.context['expiresAt']))
        self.pid=os.getpid();self.thread=threading.get_ident();self.fd=claim._fd;self.plan=claim._plan
        self.lock_pair=boot._signature(os.fstat(self.fd));self.root_identity=(claim.root.stat().st_dev,claim.root.stat().st_ino)
        self.journal={};self._check_database_original=lambda:ProductionAResumeChecks._check_database_original(self)
        self()

    def _private(self):
        import formal_boot_state as boot
        self.authority.check()
        require(os.getpid()==self.pid and threading.get_ident()==self.thread and self.claim._fd==self.fd and
            self.claim._plan==self.plan and boot._signature(os.fstat(self.fd))==self.lock_pair and
            boot._signature(self.claim._lock.lstat())==self.lock_pair and
            (self.claim.root.stat().st_dev,self.claim.root.stat().st_ino)==self.root_identity and
            self.binding_raw==canonical(self.binding) and
            self.claim.events[:len(self.prefix)]==self.prefix, 'BACKUP_LAB_OWNER_CHANGED')
        self.claim.assert_owned()
        for path,chain in self.directories.items():boot._directory_unchanged(path,chain)
        for path,(mode,limit,pair) in self.pins.items():
            require(boot._read_secure(path,mode,limit,no_atime=True)==pair,'BACKUP_LAB_ORIGINAL_CHANGED')
        for event in self.claim.events:
            path=self.claim.root/('event-%06d.json'%event['sequence'])
            pair=boot._read_secure(path,0o600,16384,no_atime=True)
            require(pair[0]==canonical(event) and pair[1][0]==self.control_device,'BACKUP_LAB_JOURNAL_CHANGED')
            if path not in self.journal:self.journal[path]=pair
            require(self.journal[path]==pair,'BACKUP_LAB_JOURNAL_CHANGED')
        self._check_database_original()
        for path,(_,_,pair) in self.pins.items():
            require(boot._signature(path.lstat())==pair[1],'BACKUP_LAB_ORIGINAL_CHANGED')

    def __call__(self):
        self._private();self.thaw_guard();self.guard();self._private()

    def control_phase_guard(self, *, maintenance_end, deadline):
        require(type(maintenance_end) in (int,float) and type(deadline) in (int,float), 'BACKUP_LAB_DEADLINE_INVALID')
        def check():
            self._private()
            require(time.time()<maintenance_end and time.monotonic()<deadline,'BACKUP_LAB_AUTHORITY_EXPIRED')
        check();return check
