"""Private CONNECT/observed-connection issuance; no business wire changes.

Only an independently provisioned, positive-UID, nondumpable authority in its
selected separate mount namespace holds the Ed25519 key. The root controller
uses an authenticated Unix peer; the capability-free SQL child gets no key,
signer endpoint descriptor or signing API. No callback stands in for issuance.
Provisioning and live use are separate authorizations, not performed on import.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys
import time

from recovery_environment_contract import canonical, decode, exact, require, utc, utc_now
from recovery_environment_supervisor import MODEL, identity
from recovery_native_browser import current_window, descriptor_read, literal_path
from recovery_native_process import authenticate_payload, file_metadata, lab_path, open_lab_file

BASE_FIELDS = set(('rehearsalId operationId batchId executor tenantId schema serverUuid containerId '
                   'schemaAllocationId imageTag imageDigest').split())
CONNECT_FIELDS = set(('schemaVersion binding action approved sourceScopePin executorInstallationPin '
    'hostIdentity controllerIdentity driverClassPin driverClass cursorClassPin cursorClass evidenceRoot observationRoot '
    'issuerSelectionPin issuancePermitPin connectionPublicOptions supervisionModel dedicatedSupervisor '
    'issuedAt expiresAt').split())
ISSUER_FIELDS = set(('schemaVersion role authorityKeyPin identity hostIdentity socketPath privateKeyReference '
    'entryPin issuerRootPath keyIsolationModel issuedAt expiresAt').split())
PERMIT_FIELDS = set(('schemaVersion binding action approved sourceScopePin executorInstallationPin inputPins '
    'adapterPin adapterDependencyPins adapterReviewPin driverClassPin driverClass cursorClassPin cursorClass '
    'evidenceRoot claimPin tenantBoundaryPin containerIdentityPin newSchema issuedAt expiresAt').split())
MAX_RPC = 1048576


def left(deadline):
    budget = deadline-time.monotonic()
    require(math.isfinite(deadline) and budget > 0, 'GOVIEW_AUTHORITY_DEADLINE')
    return budget


def host_identity():
    return dict(hostname=Path('/proc/sys/kernel/hostname').read_text(encoding='ascii').strip(),
        bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
        namespaces={k: os.readlink('/proc/self/ns/'+k) for k in ('pid', 'mnt', 'net', 'user')})


def stable_identity(pid):
    return {k:v for k,v in identity(pid).items() if k != 'state'}


class ConnectScope:
    def __init__(self, connect_pin, authority_pin, *, deadline, issuer_role=False):
        require(sys.platform == 'linux' and 0 < left(deadline) <= 300, 'GOVIEW_NATIVE_CONNECT_REQUIRED')
        self.connect_pin, self.authority_pin, self.deadline = connect_pin, authority_pin, deadline
        self.issuer_role = issuer_role
        self.selection = self.signed(connect_pin)
        exact(self.selection, CONNECT_FIELDS, 'GOVIEW_CONNECT_AUTHORIZATION_SHAPE')
        self.issuer = self.signed(self.selection['issuerSelectionPin'])
        self.permit = self.signed(self.selection['issuancePermitPin'])
        self.guard(controller=not issuer_role)

    def raw(self, pin):
        if self.issuer_role:
            # Selected issuer view grants only root:A-group read access to
            # current provision/material Pins; SQL evidence stays root-private.
            return descriptor_read(pin,owners={0},owner_gid=os.getegid(),deadline=self.deadline,modes=(0o440,0o550))
        return descriptor_read(pin, owners={0}, deadline=self.deadline, modes=(0o440, 0o550, 0o444, 0o555, 0o600))

    def signed(self, pin):
        literal_path(pin['path'], lab=True)
        return authenticate_payload(decode(self.raw(pin)), self.raw(self.authority_pin), self.authority_pin['sha256'])

    def guard(self, *, controller=True):
        c = self.selection; p = self.permit; a = self.issuer
        exact(c['binding'], BASE_FIELDS, 'GOVIEW_PRECONNECT_BINDING_SHAPE')
        exact(p, PERMIT_FIELDS, 'GOVIEW_ISSUANCE_PERMIT_SHAPE')
        exact(a, ISSUER_FIELDS, 'GOVIEW_ISSUER_SELECTION_SHAPE')
        require(c['schemaVersion'] == 'W05GoViewConnectAuthorization/v1' and
            c['action'] == 'CONNECT_AND_OBSERVE_ONLY' and c['approved'] is True and
            c['supervisionModel'] == MODEL and c['dedicatedSupervisor'] is True and
            type(c['binding']['tenantId']) is int and c['binding']['tenantId'] == 122 and
            c['controllerIdentity']['uid'] == c['controllerIdentity']['gid'] == 0,
            'GOVIEW_EXPLICIT_CONNECT_AUTHORIZATION_REQUIRED')
        require(all(type(v) is str and v and len(v) <= 512 for k,v in c['binding'].items() if k != 'tenantId') and
            re.fullmatch(r'[A-Za-z0-9_]+',c['binding']['schema']) and set(p['inputPins']) == {'sql','contract','design','manifest'} and
            type(p['adapterDependencyPins']) is list and p['adapterDependencyPins'], 'GOVIEW_CONNECT_SOURCE_BINDING_REQUIRED')
        require(host_identity() == (a['hostIdentity'] if self.issuer_role else c['hostIdentity']), 'GOVIEW_CONNECT_HOST_CHANGED')
        if controller:
            require(stable_identity(os.getpid()) == c['controllerIdentity'], 'GOVIEW_CONNECT_EXECUTOR_CHANGED')
        require(p['schemaVersion'] == 'W05GoViewIssuancePermit/v1' and p['approved'] is True and
            p['action'] == 'EXECUTE_APPROVED_GOVIEW_CREATE' and p['newSchema'] is True and
            p['binding'] == c['binding'] and all(p[k] == c[k] for k in ('sourceScopePin',
            'executorInstallationPin', 'driverClassPin', 'driverClass', 'cursorClassPin', 'cursorClass', 'evidenceRoot')),
            'GOVIEW_POSTCONNECT_ISSUANCE_PERMIT_REQUIRED')
        require(a['schemaVersion'] == 'W05GoViewIssuerSelection/v1' and a['role'] == 'AUTHORIZED_GOVIEW_ISSUER' and
            a['authorityKeyPin'] == self.authority_pin and a['identity']['uid'] > 0 and a['identity']['gid'] > 0 and
            a['keyIsolationModel'] == 'separate-mount-namespace-capability-free-sql-worker/v1' and
            a['hostIdentity']['bootId'] == c['hostIdentity']['bootId'] and
            a['hostIdentity']['namespaces']['mnt'] != c['hostIdentity']['namespaces']['mnt'] and
            all(a['hostIdentity']['namespaces'][k] == c['hostIdentity']['namespaces'][k] for k in ('pid','net','user')),
            'GOVIEW_SEPARATE_AUTHORIZED_ISSUER_REQUIRED')
        exact(a['privateKeyReference'], {'path', 'uid', 'gid', 'mode'}, 'GOVIEW_PRIVATE_KEY_REFERENCE_SHAPE')
        require(a['privateKeyReference']['uid'] == a['identity']['uid'] and
            a['privateKeyReference']['gid'] == a['identity']['gid'] and a['privateKeyReference']['mode'] == 0o600,
            'GOVIEW_PRIVATE_KEY_ROLE_CUSTODY_REQUIRED')
        literal_path(a['privateKeyReference']['path'], lab=True)
        literal_path(c['evidenceRoot'], lab=True)
        observation_root = literal_path(c['observationRoot'],lab=True)
        require(observation_root != c['evidenceRoot'], 'GOVIEW_OBSERVATION_LANE_SEPARATION_REQUIRED')
        od = os.open(observation_root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            oi = os.fstat(od)
            require(oi.st_uid == 0 and oi.st_gid == a['identity']['gid'] and stat.S_IMODE(oi.st_mode) == 0o750,
                    'GOVIEW_ISSUER_OBSERVATION_DIRECTORY_CUSTODY_REQUIRED')
        finally: os.close(od)
        from recovery_native_launcher import validate_qualification_scope
        source = self.signed(c['sourceScopePin']); validate_qualification_scope(source)
        self.raw(source['sourceIdentityPin'])
        require(source['rehearsalId'] == c['binding']['rehearsalId'], 'GOVIEW_CONNECT_TASK_CHANGED')
        if self.issuer_role:
            # SQL native admission is measured by its real root controller and
            # again by the real child. A validates the signed exact installation
            # graph in its separate mount view; it never claims to be that root
            # runtime or mutates the stable root-only runtime verifier.
            manifest = self.signed(c['executorInstallationPin'])
        else:
            from repository_native_runtime import verify_native_installation
            manifest = verify_native_installation(c['executorInstallationPin'], [self.authority_pin], deadline=self.deadline)
        require(manifest['schemaVersion'] == 'RepositoryNativeInstallation/v2', 'GOVIEW_EXPLICIT_INSTALLATION_REQUIRED')
        selected = manifest['filePins']+manifest['dependencyPins']
        require(all(pin in selected for pin in (c['driverClassPin'], c['cursorClassPin'], p['adapterPin'],
            *p['adapterDependencyPins'], *p['inputPins'].values())), 'GOVIEW_CONNECT_SOURCE_NOT_INSTALLED')
        for pin in selected: self.raw(pin)
        self.manifest = manifest
        claim = self.signed(p['claimPin'])
        exact(claim, {'schemaVersion','binding','state','owner','leaseId','fenceGeneration','issuedAt','expiresAt'},
              'GOVIEW_PRECONNECT_CLAIM_SHAPE')
        require(claim['schemaVersion'] == 'W05GoViewPreConnectClaim/v1' and claim['binding'] == c['binding'] and
            claim['state'] == 'HELD' and claim['owner'] == c['binding']['executor'] and
            type(claim['leaseId']) is str and bool(claim['leaseId']) and
            type(claim['fenceGeneration']) is int and claim['fenceGeneration'] > 0,
            'GOVIEW_CURRENT_PRECONNECT_HELD_CLAIM_REQUIRED')
        for pin, version in ((p['tenantBoundaryPin'], 'W05GoViewPreConnectTenantBoundary/v1'),
                             (p['containerIdentityPin'], 'W05GoViewPreConnectContainerIdentity/v1')):
            value = self.signed(pin)
            require(value['schemaVersion'] == version and value['binding'] == c['binding'],
                    'GOVIEW_PRECONNECT_RESOURCE_BINDING_REQUIRED')
            current_window(value)
        boundary = self.signed(p['tenantBoundaryPin']); container = self.signed(p['containerIdentityPin'])
        common = {'schemaVersion','binding','issuedAt','expiresAt'}
        exact(boundary,common|{'tenantId','schemaAllocationId','isolatedFromProtectedTenants'},'GOVIEW_PRECONNECT_BOUNDARY_SHAPE')
        exact(container,common|{'containerId','imageTag','imageDigest','state','containerOriginalPin','imageOriginalPin'},
              'GOVIEW_PRECONNECT_CONTAINER_SHAPE')
        require(boundary['tenantId'] == 122 and boundary['schemaAllocationId'] == c['binding']['schemaAllocationId'] and
            boundary['isolatedFromProtectedTenants'] is True and container['state'] == 'RUNNING' and
            all(container[k] == c['binding'][k] for k in ('containerId','imageTag','imageDigest')),
            'GOVIEW_PRECONNECT_RESOURCE_OWNERSHIP_REQUIRED')
        inspect = decode(self.raw(container['containerOriginalPin'])); image = decode(self.raw(container['imageOriginalPin']))
        b = c['binding']
        require(type(inspect) is list and len(inspect) == 1 and type(image) is list and len(image) == 1 and
            inspect[0]['Id'] == b['containerId'] and inspect[0]['Config']['Image'] == b['imageTag'] and
            inspect[0]['State']['Running'] is True and inspect[0]['Image'] == image[0]['Id'] and
            any(d.rsplit('@',1)[-1] == b['imageDigest'] for d in image[0]['RepoDigests']), 'GOVIEW_CONNECT_CONTAINER_ORIGINAL_CHANGED')
        # The root issuer's current preclaim is an input, never a fabricated
        # HELD/fence flag. Read all authority again after installation callbacks.
        require(self.signed(self.connect_pin) == c and self.signed(c['issuancePermitPin']) == p and
            self.signed(c['issuerSelectionPin']) == a and self.signed(p['claimPin']) == claim and
            self.signed(c['sourceScopePin']) == source and self.signed(p['tenantBoundaryPin']) == boundary and
            self.signed(p['containerIdentityPin']) == container, 'GOVIEW_CONNECT_CURRENT_AUTHORITY_DRIFT')
        for value in (c,p,a,claim,boundary,container): current_window(value)
        require(datetime.now(timezone.utc) < utc(source['expiresAt']) and left(self.deadline) > 0,
                'GOVIEW_CONNECT_CURRENT_WINDOW_EXPIRED')
        self.claim = claim
        return c


def socket_custody(selected, expected=None):
    path = lab_path(selected['socketPath'], exists=False)
    # Anchor each ancestor; the sole selected issuer may own private directories.
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = child
            info = os.fstat(directory)
            require(info.st_uid in (0, selected['identity']['uid']) and not info.st_mode & 0o022,
                    'GOVIEW_ISSUER_SOCKET_ANCESTOR_UNSAFE')
        info = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        require(stat.S_ISSOCK(info.st_mode) and info.st_uid == selected['identity']['uid'] and
            info.st_gid == selected['identity']['gid'] and stat.S_IMODE(info.st_mode) == 0o600,
            'GOVIEW_ISSUER_SOCKET_CUSTODY_REQUIRED')
        token = file_metadata(info)
        require(expected is None or token == expected, 'GOVIEW_ISSUER_SOCKET_REPLACED')
        return token
    finally: os.close(directory)


def rpc_send(channel, message, deadline):
    raw = canonical(message)+b'\n'; require(len(raw) <= MAX_RPC, 'GOVIEW_ISSUER_FRAME_LIMIT')
    channel.settimeout(left(deadline)); channel.sendall(raw)


def rpc_read(channel, deadline):
    raw = bytearray()
    while not raw.endswith(b'\n'):
        channel.settimeout(left(deadline)); part = channel.recv(min(65536, MAX_RPC+1-len(raw)))
        require(part and len(raw)+len(part) <= MAX_RPC, 'GOVIEW_ISSUER_FRAME_LIMIT')
        raw.extend(part)
    require(b'\n' not in raw[:-1], 'GOVIEW_ISSUER_EXTRA_FRAME')
    return decode(bytes(raw[:-1]))


class IssuerClient:
    def __init__(self, scope): self.scope = scope

    def preflight(self):
        scope = self.scope; a = scope.issuer
        require(stable_identity(a['identity']['pid']) == a['identity'], 'GOVIEW_ISSUER_IDENTITY_CHANGED')
        actual_host = dict(hostname=Path('/proc/sys/kernel/hostname').read_text(encoding='ascii').strip(),
            bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
            namespaces={k:os.readlink('/proc/'+str(a['identity']['pid'])+'/ns/'+k) for k in ('pid','mnt','net','user')})
        require(actual_host == a['hostIdentity'], 'GOVIEW_ISSUER_ACTUAL_NAMESPACE_CHANGED')
        status = dict(line.split(':',1) for line in Path('/proc/'+str(a['identity']['pid'])+'/status').read_text(encoding='ascii').splitlines())
        require(all(int(status[k].strip(),16) == 0 for k in ('CapInh','CapPrm','CapEff','CapBnd')) and
            int(status['NoNewPrivs'].strip()) == 1, 'GOVIEW_ISSUER_CAPABILITY_CUSTODY_REQUIRED')
        socket_custody(a)

    def issue(self, observation_pin, observation):
        scope = self.scope; a = scope.issuer; scope.guard(); self.preflight()
        token = socket_custody(a); response = None; primary = None; cleanup = []
        channel = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            channel.settimeout(left(scope.deadline)); channel.connect(a['socketPath'])
            peer = struct.unpack('3i', channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            require(peer == (a['identity']['pid'],a['identity']['uid'],a['identity']['gid']) and
                stable_identity(peer[0]) == a['identity'], 'GOVIEW_ISSUER_REAL_PEER_REQUIRED')
            socket_custody(a, token)
            rpc_send(channel, dict(schemaVersion='W05GoViewObservedIssuanceRequest/v1', connectPin=scope.connect_pin,
                observationPin=observation_pin, observation=observation), scope.deadline)
            response = rpc_read(channel, scope.deadline)
        except BaseException as error: primary = error
        finally:
            try: channel.close()
            except BaseException as error: cleanup.append(error)
        if primary is not None or cleanup:
            from recovery_native_goview_errors import GoViewFailure, safe_failure
            raise GoViewFailure('GOVIEW_ISSUER_OUTCOME_UNKNOWN_NO_RETRY', dict(state='UNKNOWN',retryAllowed=False,
                primary=safe_failure(primary) if primary else None, cleanup=[safe_failure(e) for e in cleanup])) from None
        scope.guard(); socket_custody(a, token)
        require(stable_identity(a['identity']['pid']) == a['identity'], 'GOVIEW_ISSUER_IDENTITY_CHANGED')
        validate_bundle(scope, response, observation_pin, observation)
        return response


def validate_observation(scope, observation):
    c = scope.selection
    exact(observation, {'schemaVersion','connectPin','controllerIdentity','workerIdentity','hostIdentity',
        'supervision','engine','workerSecurity','keyDenial','observedAt'}, 'GOVIEW_CONNECTION_OBSERVATION_SHAPE')
    require(observation['schemaVersion'] == 'W05GoViewOwnedConnectionObservation/v1' and
        observation['connectPin'] == scope.connect_pin and observation['controllerIdentity'] == c['controllerIdentity'] and
        observation['hostIdentity'] == c['hostIdentity'] and observation['workerIdentity']['parent'] == c['controllerIdentity']['pid'],
        'GOVIEW_OBSERVATION_LINEAGE_CHANGED')
    exact(observation['engine'], {'schema','serverUuid','connectionId'}, 'GOVIEW_OBSERVED_ENGINE_SHAPE')
    e = observation['engine']; require(e['schema'] == c['binding']['schema'] and
        e['serverUuid'] == c['binding']['serverUuid'] and type(e['connectionId']) is int and e['connectionId'] > 0,
        'GOVIEW_REAL_OBSERVED_CONNECTION_REQUIRED')
    sec = observation['workerSecurity']; exact(sec, {'uid','gid','CapInh','CapPrm','CapEff','CapBnd','NoNewPrivs'}, 'GOVIEW_WORKER_SECURITY_SHAPE')
    require(sec['uid'] == sec['gid'] == 0 and all(sec[k] == 0 for k in ('CapInh','CapPrm','CapEff','CapBnd')) and
        sec['NoNewPrivs'] == 1, 'GOVIEW_SQL_WORKER_CAPABILITY_DENIAL_REQUIRED')
    expected = [scope.issuer['privateKeyReference']['path'], '/proc/'+str(scope.issuer['identity']['pid'])+'/root',
                '/proc/'+str(scope.issuer['identity']['pid'])+'/mem']
    require(type(observation['keyDenial']) is list and len(observation['keyDenial']) == 3 and
        [v['path'] for v in observation['keyDenial']] == expected and
        all(set(v) == {'path','errno'} and v['errno'] in (2,13) for v in observation['keyDenial']),
        'GOVIEW_SQL_WORKER_ACTUAL_KEY_DENIAL_REQUIRED')
    sup = observation['supervision']
    exact(sup, {'model','parentIdentity','workerIdentity','subreaper','acknowledged'}, 'GOVIEW_SUPERVISION_ACK_SHAPE')
    require(sup['model'] == MODEL and sup['parentIdentity'] == c['controllerIdentity'] and
        sup['workerIdentity'] == observation['workerIdentity'] and sup['subreaper'] is True and sup['acknowledged'] is True,
        'GOVIEW_CONNECT_BEFORE_SUPERVISION_ACK_REJECTED')


def read_observation(scope, pin):
    require(Path(pin['path']).parent == Path(scope.selection['observationRoot']), 'GOVIEW_OBSERVATION_ORIGINAL_PATH')
    return decode(descriptor_read(pin,owners={0},owner_gid=scope.issuer['identity']['gid'],
        deadline=scope.deadline,readonly=scope.issuer_role,modes=(0o440,)))


def validate_bundle(scope, response, observation_pin, observation):
    exact(response, {'schemaVersion','selectionPin','intentPin','documents','observationPin'}, 'GOVIEW_ISSUANCE_REPLY_SHAPE')
    require(response['schemaVersion'] == 'W05GoViewObservedIssuance/v1' and response['observationPin'] == observation_pin and
        type(response['documents']) is list and len(response['documents']) == 9, 'GOVIEW_REAL_SIGNED_ISSUANCE_REQUIRED')
    validate_observation(scope, observation)
    documents = {}
    for item in response['documents']:
        exact(item, {'pin','envelope'}, 'GOVIEW_ISSUED_DOCUMENT_SHAPE')
        raw = canonical(item['envelope']); pin = item['pin']
        exact(pin, {'path','bytes','sha256'}, 'GOVIEW_ISSUED_PIN_SHAPE')
        require(pin['bytes'] == len(raw) and pin['sha256'] == hashlib.sha256(raw).hexdigest() and
            Path(pin['path']).parent == Path(scope.selection['evidenceRoot']) and pin['path'] not in documents,
            'GOVIEW_ISSUED_DOCUMENT_PIN_CHANGED')
        documents[pin['path']] = authenticate_payload(item['envelope'], scope.raw(scope.authority_pin), scope.authority_pin['sha256'])
    require(response['selectionPin']['path'] in documents and response['intentPin']['path'] in documents,
            'GOVIEW_ISSUED_SELECTION_OR_INTENT_MISSING')
    s = documents[response['selectionPin']['path']]; intent = documents[response['intentPin']['path']]
    from consume_goview import SELECTION_FIELDS
    exact(s,SELECTION_FIELDS,'GOVIEW_ISSUED_SELECTION_SHAPE')
    require(all(s[k] == scope.permit[k] for k in ('sourceScopePin','executorInstallationPin','inputPins','adapterPin',
        'adapterDependencyPins','adapterReviewPin','driverClassPin','driverClass','cursorClassPin','cursorClass','evidenceRoot')),
        'GOVIEW_ISSUED_SOURCE_SELECTION_CHANGED')
    require(s['connectionId'] == observation['engine']['connectionId'] and all(s[k] == v for k,v in scope.selection['binding'].items()) and
        intent['observationPin'] == observation_pin and intent['selectionPin'] == response['selectionPin'] and
        intent['connectionId'] == s['connectionId'] and intent['operationId'] == s['operationId'] and
        intent['batchId'] == s['batchId'] and intent['sqlPin'] == scope.permit['inputPins']['sql'],
        'GOVIEW_ISSUED_ACTUAL_CONNECTION_INTENT_CHANGED')
    for value in documents.values(): current_window(value)
    lease = documents[s['leasePin']['path']]
    require(lease['state'] == 'HELD' and lease['leaseId'] == scope.claim['leaseId'] and
        type(lease['fenceGeneration']) is int and lease['fenceGeneration'] == scope.claim['fenceGeneration'] > 0,
        'GOVIEW_ISSUED_CURRENT_FENCE_CHANGED')


def issued_context(connect, issued):
    """Approved context is captured from real signed issue BEFORE CREATE."""
    documents = {v['pin']['path']:authenticate_payload(v['envelope'],connect.raw(connect.authority_pin),
                 connect.authority_pin['sha256']) for v in issued['documents']}
    s = documents[issued['selectionPin']['path']]; lease = documents[s['leasePin']['path']]
    return dict(authorizationPin=s['authorizationPin'], operationId=s['operationId'], batchId=s['batchId'],
        executor=s['executor'],schema=s['schema'],serverUuid=s['serverUuid'],containerId=s['containerId'],connectionId=s['connectionId'],
        schemaAllocationId=s['schemaAllocationId'],exclusiveClaimPin=lease['exclusiveClaimPin'],fenceId=lease['leaseId'],
        fenceGeneration=lease['fenceGeneration'],sqlExecutionReleased=True,exclusiveClaimHeld=True,newSchema=True,
        **{k+'Pin':v for k,v in s['inputPins'].items()},imageTag=s['imageTag'],imageDigest=s['imageDigest'],mode='standalone')


def build_signed_bundle(scope, observation_pin, observation, private_key):
    """Issuer-only real signing, solely from current authentic permit/claim."""
    from consume_goview import ACTION, SELECTION_FIELDS
    scope.guard(controller=False); validate_observation(scope, observation)
    c = scope.selection; p = scope.permit; a = scope.issuer; claim = scope.claim
    require(stable_identity(os.getpid()) == a['identity'] and host_identity() == a['hostIdentity'],
            'GOVIEW_SIGNING_ROLE_IDENTITY_REQUIRED')
    binding = dict(c['binding'], connectionId=observation['engine']['connectionId'])
    end = min(utc(v['expiresAt']) for v in (c,p,a,claim))
    common = dict(binding=binding, issuedAt=utc_now(), expiresAt=end.isoformat().replace('+00:00','Z'))
    documents = []; prefix = 'issued-'+scope.connect_pin['sha256']+'-'
    def sign(label, payload):
        current_window(payload)
        encoded = json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
        envelope = dict(schemaVersion='RepositorySignedRecord/v1', keySha256=scope.authority_pin['sha256'],
                        payload=payload, signature=base64.b64encode(private_key.sign(encoded)).decode('ascii'))
        raw = canonical(envelope); pin = dict(path=c['evidenceRoot']+'/'+prefix+label+'.json', bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        documents.append(dict(pin=pin,envelope=envelope)); return pin
    boundary = scope.signed(p['tenantBoundaryPin']); container = scope.signed(p['containerIdentityPin'])
    boundary = {**boundary, **common, 'schemaVersion':'W05GoViewTenantBoundary/v1'}
    container = {**container, **common, 'schemaVersion':'W05GoViewContainerIdentity/v1'}
    boundary_pin = sign('boundary', boundary); container_pin = sign('container', container)
    ownership = sign('ownership', dict(schemaVersion='W05GoViewResourceOwnership/v1', **common, state='HELD',
        owner=binding['executor'],newSchema=True,tenantBoundaryPin=boundary_pin,containerIdentityPin=container_pin))
    release = sign('release', dict(schemaVersion='W05GoViewSQLRelease/v1', **common, action=ACTION,
        sourceScopePin=p['sourceScopePin'],executorInstallationPin=p['executorInstallationPin'],inputPins=p['inputPins'],
        evidenceRoot=p['evidenceRoot'],adapterReviewPin=p['adapterReviewPin']))
    grant = sign('grant', dict(schemaVersion='W05GoViewSQLAuthorization/v1', **common, action=ACTION, approved=True,
        releasePin=release,ownershipPin=ownership,sourceScopePin=p['sourceScopePin'],inputPins=p['inputPins']))
    exclusive = sign('claim',dict(schemaVersion='W05GoViewExclusiveClaim/v1', **common,state='HELD',owner=binding['executor'],
        leaseId=claim['leaseId'],fenceGeneration=claim['fenceGeneration']))
    lease = sign('lease',dict(schemaVersion='W05GoViewSQLLease/v1', **common,state='HELD',leaseId=claim['leaseId'],
        fenceGeneration=claim['fenceGeneration'],exclusiveClaimPin=exclusive,releasePin=release,ownershipPin=ownership))
    s = {**binding, **{k:p[k] for k in ('sourceScopePin','executorInstallationPin','inputPins','adapterPin',
        'adapterDependencyPins','adapterReviewPin','driverClassPin','driverClass','cursorClassPin','cursorClass','evidenceRoot')},
        'schemaVersion':'W05GoViewConsumerSelection/v1','releasePin':release,'ownershipPin':ownership,'authorizationPin':grant,
        'leasePin':lease,'issuedAt':common['issuedAt'],'expiresAt':common['expiresAt']}
    exact(s, SELECTION_FIELDS, 'GOVIEW_ISSUED_SELECTION_SHAPE')
    selection = sign('selection', s)
    intent = sign('intent', dict(schemaVersion='W05GoViewOwnedConnectionIntent/v1',**common,
        operationId=binding['operationId'],batchId=binding['batchId'],connectionId=binding['connectionId'],
        connectPin=scope.connect_pin,issuancePermitPin=c['issuancePermitPin'],observationPin=observation_pin,
        selectionPin=selection,sqlPin=p['inputPins']['sql'],leaseId=claim['leaseId'],fenceGeneration=claim['fenceGeneration']))
    scope.guard(controller=False)
    return dict(schemaVersion='W05GoViewObservedIssuance/v1',selectionPin=selection,intentPin=intent,
                documents=documents,observationPin=observation_pin)


def serve_one(issuer_selection_pin, authority_pin, listening_socket, *, deadline):
    """A separately authorized launcher passes its already bound private socket.

    No process is started and no role/namespace is manufactured here. Missing
    real provision, key, listener or approved connect/issuance permit fails.
    One reservation is permanent, including failed/disconnected responses.
    """
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    import ctypes
    a_raw = descriptor_read(issuer_selection_pin,owners={0},owner_gid=os.getegid(),deadline=deadline,modes=(0o440,))
    public = descriptor_read(authority_pin,owners={0},owner_gid=os.getegid(),deadline=deadline,modes=(0o440,))
    a = authenticate_payload(decode(a_raw), public, authority_pin['sha256']); exact(a, ISSUER_FIELDS, 'GOVIEW_ISSUER_SELECTION_SHAPE')
    require(a['identity']['uid'] == os.geteuid() > 0 and a['identity']['gid'] == os.getegid() > 0 and
        stable_identity(os.getpid()) == a['identity'] and host_identity() == a['hostIdentity'] and
        listening_socket.getsockname() == a['socketPath'], 'GOVIEW_ACTUAL_ISSUER_ROLE_REQUIRED')
    libc = ctypes.CDLL(None,use_errno=True)
    require(libc.prctl(4,0,0,0,0) == 0 and libc.prctl(3,0,0,0,0) == 0, 'GOVIEW_ISSUER_NONDUMPABLE_REQUIRED')
    source = Path(__file__).resolve(); require(a['entryPin']['path'] == str(source), 'GOVIEW_ISSUER_ENTRY_NOT_SELECTED')
    descriptor_read(a['entryPin'],owners={0},owner_gid=os.getegid(),deadline=deadline,modes=(0o440,0o550))
    keyref = a['privateKeyReference']; fd, directory = open_lab_file(keyref['path'], os.O_RDONLY)
    try:
        metadata = os.fstat(fd)
        require(metadata.st_uid == os.geteuid() and metadata.st_gid == os.getegid() and
            stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1 and stat.S_IMODE(metadata.st_mode) == 0o600 and
            metadata.st_size <= 8192, 'GOVIEW_ACTUAL_ISSUER_KEY_CUSTODY_REQUIRED')
        secret = os.read(fd,8193); require(file_metadata(os.fstat(fd)) == file_metadata(metadata), 'GOVIEW_ISSUER_KEY_CHANGED')
    finally: os.close(fd); os.close(directory)
    key = load_pem_private_key(secret,password=None); del secret
    require(isinstance(key,Ed25519PrivateKey) and key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo) == public,
            'GOVIEW_ISSUER_PRIVATE_PUBLIC_KEY_MISMATCH')
    listening_socket.settimeout(left(deadline)); channel,_ = listening_socket.accept()
    with channel:
        request = rpc_read(channel,deadline)
        exact(request, {'schemaVersion','connectPin','observationPin','observation'}, 'GOVIEW_ISSUER_REQUEST_SHAPE')
        require(request['schemaVersion'] == 'W05GoViewObservedIssuanceRequest/v1', 'GOVIEW_ISSUER_REQUEST_VERSION')
        scope = ConnectScope(request['connectPin'],authority_pin,deadline=deadline,issuer_role=True)
        require(scope.issuer == a, 'GOVIEW_ISSUER_SELECTION_CHANGED')
        peer = struct.unpack('3i',channel.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        controller = scope.selection['controllerIdentity']
        require(peer == (controller['pid'],controller['uid'],controller['gid']) and stable_identity(peer[0]) == controller,
                'GOVIEW_ISSUER_AUTHORIZED_CONTROLLER_PEER_REQUIRED')
        observed = read_observation(scope,request['observationPin'])
        require(observed == request['observation'], 'GOVIEW_ISSUER_REAL_OBSERVATION_ORIGINAL_CHANGED')
        validate_observation(scope,observed)
        require(stable_identity(observed['workerIdentity']['pid']) == observed['workerIdentity'], 'GOVIEW_OBSERVED_WORKER_CHANGED')
        # Reservation uses the issuer's private directory and never retries or
        # deletes a partial issue. The reply's signed bytes are published by the
        # finite owned SQL child, as root-private originals in the source view.
        reservation = lab_path(a['issuerRootPath']+'/reservation-'+request['connectPin']['sha256'],exists=False)
        rfd, rd = open_lab_file(str(reservation),os.O_WRONLY|os.O_CREAT|os.O_EXCL)
        try:
            os.write(rfd,canonical(dict(connectPin=request['connectPin'],observationPin=request['observationPin'],observedAt=utc_now())))
            os.fsync(rfd); os.fsync(rd)
        finally: os.close(rfd); os.close(rd)
        response = build_signed_bundle(scope,request['observationPin'],observed,key)
        rpc_send(channel,response,deadline)
