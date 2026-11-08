"""MAIN orchestration contracts, using real private files/locks/domain components.

This is an integration of replacement.execute and runtime.execute_empty with
the actual source, archive/import, switch, derivation, epoch, reservation,
native-context and ProtectionCustody implementations. ProtocolNative and
ProtocolDocker are explicit SQL/Docker/object transport unit boundaries; they
are not the production NativeData constructor, real SQL/object restore, kernel
mount/firewall protection, deployment admission or server acceptance evidence.
The separate constructor/MainData suites cover those production entry methods.
Each file can be collected by a fresh pytest process without import-order state.
"""
from contextlib import contextmanager
from copy import deepcopy
import gzip
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ops/recovery'))
from recovery_engine import RecoveryError, canonical, digest, pin, pinned_json, require, utc, write
from test_recovery_program_generation import case
from test_recovery_program_containers import original, image
from test_recovery_program_protection import TransportModel
import recovery_backup_epoch as epoch
import recovery_minimal_runtime as runtime
import recovery_main_target as main
import recovery_program_containers as containers
import recovery_resource_admission as resources
import recovery_replace as replacement

pytestmark = pytest.mark.skipif(not sys.platform.startswith('linux'), reason='real Linux flock/context required')
ROLES = ('mysql', 'minio', 'redis', 'backend', 'frontend')
PROGRAM_FIELDS = ('programExecutionPhase', 'programNativeEvidencePin',
                  'programProtectionCustodyPin', 'programGenerationPin')


def module():
    return importlib.import_module('recovery_program_restore')


def archive(path):
    """Five content-addressed Docker images; tags are deliberately untrusted."""
    path.parent.mkdir(parents=True, exist_ok=True)
    identities, members, entries, images = {}, [], [], {}
    for role in ROLES:
        layer = ('historical '+role+' layer').encode('ascii')
        diff = 'sha256:'+hashlib.sha256(layer).hexdigest()
        raw = canonical(dict(os='linux', architecture='amd64', rootfs=dict(type='layers', diff_ids=[diff])))
        checksum = hashlib.sha256(raw).hexdigest()
        identities[role] = 'sha256:'+checksum
        members.extend([(checksum+'.json', raw), (role+'/layer.tar', layer)])
        entries.append(dict(Config=checksum+'.json', RepoTags=['untrusted/'+role+':latest'], Layers=[role+'/layer.tar']))
        images[identities[role]] = dict(image(), Id=identities[role], RootFS=dict(Type='layers', Layers=[diff]))
    members.append(('manifest.json', canonical(entries)))
    with tarfile.open(path, 'w') as output:
        for name, raw in members:
            info = tarfile.TarInfo(name); info.size = len(raw)
            output.addfile(info, io.BytesIO(raw))
    path.chmod(0o600)
    return pin(path), identities, images


class ProtocolDocker:
    """Daemon HTTP protocol model; actual switch verification remains enabled."""
    def __init__(self, h):
        self.h, self.rows, self.images = h, {}, {}
        self.actions, self.counter = [], 0

    def inspect(self, identity):
        return deepcopy(self.rows[identity])

    def image(self, identity):
        return deepcopy(self.images[identity])

    def metadata(self):
        return dict(OperatingSystem='Linux')

    def network(self, identity):
        return dict(Id=identity, Name='task-network')

    def request(self, method, path, body=None):
        h = self.h
        self.actions.append((method, path, deepcopy(body)))
        h.events.append(('http', method, path))
        if h.fail == 'switch-unknown' and len(self.actions) == 2:
            error = TimeoutError('PROTOCOL_HTTP_TERMINAL_UNKNOWN'); error.unknown = True; raise error
        if '/rename?' in path:
            self.rows[path.split('/')[2]]['Name'] = '/'+unquote(path.split('name=')[1])
        elif path.endswith('/disconnect'):
            self.rows[body['Container']]['NetworkSettings']['Networks'] = {}
        elif path.startswith('/containers/create?'):
            self.counter += 1
            identity = ('8' if self.counter == 1 else '9')*64
            name = unquote(path.split('name=')[1])
            before = next(row for row in h.originals.values() if row['Name'] == '/'+name)
            row = deepcopy(before)
            row.update(Id=identity, Name='/'+name, Image=body['Image'],
                Config={key: deepcopy(value) for key, value in body.items()
                        if key not in ('HostConfig', 'NetworkingConfig')}, HostConfig=deepcopy(body['HostConfig']))
            row['State'].update(Running=False, Pid=0, Status='created')
            for network, endpoint in body['NetworkingConfig']['EndpointsConfig'].items():
                row['NetworkSettings']['Networks'][network].update(deepcopy(endpoint))
            self.rows[identity] = row
            return dict(Id=identity, Warnings=[])
        else:
            raise AssertionError(('unexpected Docker HTTP unit request', method, path))


def native_type(h):
    class ProtocolNative:
        """External data protocol adapter, with real typed context/custody guards."""
        def __init__(self, configuration, request, source, policy, chain, target, root, input_pins,
                     *, native_context=None, protection_custody=None):
            require(native_context is not None, 'PROGRAM_NATIVE_CONTEXT_REQUIRED')
            native_context.validate_inputs(configuration, request, target)
            self.native_context, self.budget = native_context, native_context.budget
            self.original, self.request = deepcopy(request), deepcopy(request)
            self.config, self.source, self.policy = deepcopy(target), deepcopy(source), deepcopy(policy)
            self.policy['environmentMysqlClientPath'] = configuration['environmentMysqlClientPath']
            self.root, self.input_pins, self.original_pins = Path(root), input_pins, []
            self.chain, self.material = chain, chain[-1][2]
            self.plan = dict(recoveryPoint=chain[-1][2]['recoveryPoint'])
            self.config_services = {row['role']: row for row in self.config['services']}
            self.db_container = self.config_services['mysql']['id']
            self.mutation_dispatched, self.last_exit, self.storage_running = False, None, False
            self.archive_guard = None
            self.running_applications = set()
            if protection_custody is not None: self.protection_custody = protection_custody
            h.natives.append(self)
            h.events.append(('construct', self.native_context.phase, self.budget))
            if h.fail == 'constructor-'+self.native_context.phase.lower():
                raise RecoveryError('PROTOCOL_NATIVE_CONSTRUCTOR_FAILURE')
            from recovery_archive_guard import ArchivePathGuard
            self.archive_guard = ArchivePathGuard.capture(reference['path'] for step in chain for reference in step[2]['payloadPins'])
            try:
                self.guard()
                current = epoch.read_current(h.case['epoch'])
                assert current['state'] == 'REPLACING' and current['operationId'] == request['operationId']
                self.database_uuid()  # First external DB protocol access must already have the real ctx.
            except BaseException:
                self.archive_guard.close()
                raise
            self.mysql = SimpleNamespace(query=lambda statement,**kwargs:self.query(statement,**kwargs).decode('utf-8').strip())

        def guard(self):
            self.native_context.guard_native(self)
            self.budget.remaining()
            if self.archive_guard is not None: self.archive_guard.check()

        def _invoke(self, kind, arguments, callback, mutation):
            self.guard()
            h.events.append((kind, self.native_context.phase, deepcopy(arguments), mutation))
            if mutation: self.mutation_dispatched = True
            h.sequence += 1
            path = h.root/('protocol-invocation-%05d.json' % h.sequence)
            value = dict(schemaVersion='RecoveryDataInvocation/v1', operationId=self.original['operationId'],
                action=self.request['action'], argvSha256=digest(arguments), mutation=mutation,
                startedAt=utc(), finishedAt=None, actualExitCode=None, state='TERMINAL_UNKNOWN')
            token = self.native_context.begin_invocation(self, write(path, value))
            try:
                result = callback()
            except BaseException as error:
                unknown = getattr(error, 'unknown', False)
                value.update(finishedAt=utc(), actualExitCode=None if unknown else 1,
                             state='TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED')
                terminal = write(path, value)
                self.original_pins.append(terminal); self.native_context.finish_invocation(token, terminal)
                raise
            value.update(finishedAt=utc(), actualExitCode=0, state='SUCCEEDED')
            terminal = write(path, value)
            self.original_pins.append(terminal); self.native_context.finish_invocation(token, terminal)
            self.last_exit = 0
            return result

        def command(self, arguments, *, mutation=False, **kwargs):
            return self._invoke('command', arguments,
                lambda: h.transport.command(self, arguments, mutation=mutation, **kwargs), mutation)

        def query(self, statement, *, mutation=False):
            def reply():
                if statement == 'SELECT @@server_uuid;': return (h.case['epoch']['databaseUuid']+'\n').encode('ascii')
                if '@@GLOBAL.log_bin' in statement: return b'1\n'
                if statement.startswith('SHOW FULL TABLES'):
                    return b'' if h.database_empty else b'protocol_table\tBASE TABLE\n'
                if statement.startswith(('DROP DATABASE', 'CREATE DATABASE')):
                    if h.fail == 'database': raise RecoveryError('PROTOCOL_DATABASE_FAILURE')
                    if statement.startswith('DROP DATABASE'): h.database_empty = True
                    return b''
                return h.transport.query(self, statement, mutation=mutation)
            return self._invoke('sql', statement, reply, mutation)

        def database_uuid(self):
            return self.query('SELECT @@server_uuid;').decode('ascii').strip()

        def inspect(self, identity):
            self.guard(); return h.engine.inspect(identity)

        def docker(self, arguments, *, mutation=False, **kwargs):
            def reply():
                if arguments[:1] == ['info']:
                    return canonical(dict(ID=self.config['dockerEngineId'], DockerRootDir=str(h.docker_root)))
                if arguments[:2] in (['image', 'inspect'], ['inspect', '--type=image']):
                    return canonical([h.engine.image(arguments[-1])])
                if arguments[:1] == ['inspect']:
                    return canonical([h.engine.inspect(identity) for identity in arguments[1:]])
                if arguments[:1] == ['ps']:
                    return ('\n'.join(h.engine.rows)+'\n').encode('ascii')
                if arguments[:2] == ['image', 'load'] or arguments[:1] == ['load']:
                    if h.fail == 'load-unknown':
                        error = TimeoutError('PROTOCOL_LOAD_TERMINAL_UNKNOWN'); error.unknown = True; raise error
                    path = Path(arguments[arguments.index('--input')+1] if '--input' in arguments
                                else arguments[arguments.index('-i')+1])
                    with tarfile.open(path, 'r:') as source:
                        entries = json.load(source.extractfile('manifest.json'))
                    assert all(row['RepoTags'] is None for row in entries)
                    assert len(entries) == 5
                    h.loaded = set(h.images.values())
                    return b'Loaded five immutable protocol images\n'
                if arguments[:1] in (['start'], ['stop']):
                    for identity in arguments[1:]:
                        running = arguments[0] == 'start'
                        h.engine.rows[identity]['State'].update(Running=running, Pid=100 if running else 0,
                            Status='running' if running else 'exited')
                    return b''
                raise AssertionError(('unexpected Docker CLI unit request', arguments))
            return self._invoke('docker', arguments, reply, mutation)

        @contextmanager
        def timed_stage(self, name):
            h.events.append(('stage', self.native_context.phase, name)); yield

        def replacement_preflight(self):
            self.guard(); h.events.append(('preflight', self.native_context.phase))
            for value in protection_values(self): value.preflight()

        def replacement_write_fence(self):
            view = main.protections(self)
            view.archive.install(); view.fence.install()

        def replacement_quiescence(self):
            main.protections(self).scheduler.install()

        def replacement_finish(self):
            main.protections(self)
            return self.protection_custody.release(self)

        def bound(self):
            self.guard()
            h.events.append(('bound', self.native_context.phase, getattr(self, 'protection_custody', None)))
            for value in protection_values(self): value.verify()

        def stop_application(self):
            self.bound()
            for role in reversed(self.config['application']['startOrder']):
                self.docker(['stop', self.config_services[role]['id']], mutation=True)

        def fresh_target(self):
            """SAFE empty-target protocol boundary, with real local object state.

            SQL/Redis are the declared finite transport model; their emptiness
            must follow the actual clear calls, never an unconditional reply.
            """
            from recovery_data_files import inventory
            assert self.native_context.phase == 'RESTORE'
            self.bound()
            main.application_inputs(self)
            assert self.query('SHOW FULL TABLES FROM `'+self.config['database']+'`;') == b''
            mounts = [m for m in self.inspect(self.config_services['minio']['id'])['Mounts']
                if m['Destination'] == self.policy['minioDataMount']]
            assert len(mounts) == 1 and mounts[0]['RW']
            assert inventory(mounts[0]['Source'], self.guard) == {}
            assert main.redis_command(self, ['-n',str(self.config['redisRebuild']['database']),'--raw','DBSIZE']) == b'0\n'
            h.events.append(('fresh-target', self.native_context.phase))

        def full_database(self):
            self.bound(); h.events.append(('data-chain', 'DATABASE_FULL'))
            self.query('CREATE DATABASE `app`;', mutation=True)
            return dict(recoveryPoint=self.material['recoveryPoint'], protocolBoundary='SQL')

        def incremental_database(self):
            self.bound(); h.events.append(('data-chain', 'DATABASE_INCREMENTAL'))
            self.query('CREATE DATABASE `app`;', mutation=True)
            return dict(recoveryPoint=self.material['recoveryPoint'], protocolBoundary='SQL')

        def physical_object_chain(self):
            self.bound(); h.events.append(('data-chain', 'OBJECT_CHAIN_PHYSICAL'))
            if h.fail == 'objects': raise RecoveryError('PROTOCOL_OBJECT_FAILURE')
            return self._invoke('objects', ['restore-chain', len(self.chain)],
                lambda: dict(recoveryPoint=self.material['recoveryPoint'], protocolBoundary='OBJECT'), True)

        def consistency(self):
            self.bound(); h.events.append(('data-chain', 'CONSISTENCY'))
            if h.fail == 'consistency': raise RecoveryError('PROTOCOL_CONSISTENCY_FAILURE')
            return dict(recoveryPoint=self.material['recoveryPoint'], protocolBoundary='CONSISTENCY')

        def start_application(self):
            self.bound(); h.events.append(('data-chain', 'START_APPLICATION'))
            if h.fail == 'start': raise RecoveryError('PROTOCOL_START_FAILURE')
            for role in self.config['application']['startOrder']:
                self.docker(['start', self.config_services[role]['id']], mutation=True)
            return dict(state='PROTOCOL_APPLICATION_STARTED', healthVerification='PROTOCOL_ONLY')

    return ProtocolNative


def protection_values(native):
    view = main.protections(native)
    return view.archive, view.fence, view.scheduler


def record_point(h, *, parent=None, name='point1'):
    """Seal the existing W03 material contract before any point is pinned.

    The shape follows test_recovery_minimal.MinimalTests.chain. All archive
    bytes and ancestry are real; SQL/object contents are protocol fixtures.
    """
    from recovery_data_files import tree_delta
    metadata = h.archive_root/name/'.repository'; metadata.mkdir(parents=True, mode=0o700)
    root = metadata.parent
    payload = root/'payload'; payload.mkdir(mode=0o700)
    def data(filename, value):
        path = root/filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else canonical(value))
        path.chmod(0o600)
        return pin(path)
    image_pin, images, rows = archive(payload/'original-application-images.tar')
    h.images, h.image_rows = images, rows
    kind = 'FULL' if parent is None else 'INCREMENTAL'
    generation, recovery_point = 'history-full-to-incremental', 'sha256:'+digest(name)
    identity = pinned_json(h.source_identity)
    end = dict(file='mysql-bin.000001', position=100 if parent is None else 200,
        databaseUuid=identity['databaseUuid'], serverVersion='8.0.protocol')
    start = None if parent is None else deepcopy(h.database_end)
    content = b'full-object-protocol-bytes' if parent is None else b'incremental-object-protocol-bytes'
    content_pin = data('payload/file.bin', content)
    filename = 'old.bin' if parent is None else 'new.bin'
    files = {filename:dict(kind='file', bytes=len(content), sha256=content_pin['sha256'])}
    changed, deleted = tree_delta(h.previous_files, files)
    capture = data('capture.json', dict(schemaVersion='backup-capture-point/v1', backupId=name,
        generationId=generation, sourceIdentity=identity['sourceFingerprint'], commonRecoveryPoint=recovery_point,
        pointType=kind, databaseEnd=end, databaseDelta={}, fileInventory=files,
        fileDelta=dict(changedPaths=changed, deletedPaths=deleted)))
    file_inventory = data('file-inventory.json', files)
    expected = data('expected.json', dict(protocolFixture=True, encoding='mysql8-typed-row-multiset-sha256/v1',
        observationIdentity=dict(databaseUuid=identity['databaseUuid'])))
    reference = data('references.json', dict(schemaVersion='RecoveryReferenceInventory/v1', complete=True,
        recoveryPoint=recovery_point, databaseRows=[], objectReferences=[]))
    derived = data('derived.json', dict(schemaVersion='RecoveryDerivedInventory/v1', complete=True,
        recoveryPoint=recovery_point, classes={key:dict(classification='NOT_PRESENT', requiredForBusiness=False,
            payloadPins=[], executorKey=None) for key in ('redis','queue')}))
    versions = data('version.json', dict(images=images))
    observation = dict(bucket='private', state='NO_MULTIPART_UPLOAD_OBSERVED', httpStatus=200,
        rawSha256=hashlib.sha256(b'protocol-empty-list').hexdigest(), rawBytes=len(b'protocol-empty-list'),
        maxUploads=1, uploadCount=0, isTruncated=False, scope='WHOLE_BUCKET_FROM_START')
    multipart = data('multipart-observations.json', dict(state='MULTIPART_EMPTY_POINT_OBSERVATIONS',
        before=[observation], after=[observation]))
    object_inventory = data('versions.jsonl', b'')
    export = data('export-receipt.json', dict(buckets=['private'], state='S3_EXPORTED_PENDING_RESTORE_PROOF',
        inventoryBytes=0, inventorySha256=object_inventory['sha256'], versionCount=0, deleteMarkerCount=0,
        totalVersionBytes=0, uniqueContentCount=0, multipartObservationsSha256=multipart['sha256']))
    sql = data('payload/database.sql.gz', gzip.compress(b'-- protocol SQL fixture only\n', mtime=0))
    raw_sql = None if parent is None else data('payload/raw.sql', b'-- protocol raw binlog fixture only\n')
    payloads = sorted((pin(path) for path in root.rglob('*') if path.is_file() and
        '.repository' not in path.relative_to(root).parts), key=lambda item:Path(item['path']).relative_to(root).as_posix())
    tree = {path.relative_to(root).as_posix(): ('directory' if path.is_dir() else
        'file|%d|%s' % (pin(path)['bytes'],pin(path)['sha256']))
        for path in root.rglob('*') if '.repository' not in path.relative_to(root).parts}
    tree_pin = write(metadata/'tree.json', tree)
    common = dict(backupId=name, generationId=generation, pointType=kind,
        parentPointPins=[] if parent is None else [parent], commonRecoveryPoint=recovery_point, payloadRefs=payloads)
    manifest = write(metadata/'manifest.json', dict(common, schemaVersion='RepositoryManifest/v1',
        payloadTreePin=tree_pin, sourceIdentityPin=h.source_identity, versionPins=[versions]))
    point_value = dict(common, schemaVersion='RepositoryPoint/v1', manifestPin=manifest)
    point = write(metadata/'point.json', point_value)
    material = write(metadata/'material.json', dict(schemaVersion='RecoveryMaterial/v1', manifestPin=manifest,
        pointType=kind, recoveryPoint=recovery_point, versionPins=[versions], sourceScopePin=h.source['sourceScopePin'],
        sourceFingerprint=identity['sourceFingerprint'], sourceDatabaseUuid=identity['databaseUuid'],
        payloadPins=payloads, referenceInventoryPin=reference, derivedInventoryPin=derived,
        database=dict(method='FORMAL_SQL_FULL' if parent is None else 'BINLOG_SQL', startPosition=start,
            endPosition=end, sqlPin=sql, rawSqlPin=raw_sql, expectedDataPin=expected, capturePointPin=capture),
        objects=dict(method='PHYSICAL_FILES', capturePointPin=capture, fileInventoryPin=file_inventory,
            filePayloadPins={filename:content_pin}, inventoryPin=object_inventory, exportReceiptPin=export)))
    index = write(metadata/'object-index.json', dict(schemaVersion='backup-capture-object-index/v1',
        backupId=name, generationId=generation, sourceIdentity=identity['sourceFingerprint'],
        recoveryPoint=recovery_point, pointType=kind, parentExportIndexPin=h.previous_index,
        inventoryPin=object_inventory, exportReceiptPin=export, contentPins={}, changedContentSha256=[],
        repositoryBound=True, manifestPin=manifest))
    binding = write(metadata/'binding.json', dict(schemaVersion='RecoveryRepositoryBinding/v1', backupId=name,
        generationId=generation, repositoryPointPin=point, manifestPin=manifest, recoveryMaterialPin=material,
        sourceScopePin=h.source['sourceScopePin'], objectContentIndexPin=index))
    h.source['recoveryPoints'][name] = point
    h.source['repositoryPointPins'].append(point)
    h.source['repositoryBindingPinsByManifestSha256'][manifest['sha256']] = binding
    h.selected = SimpleNamespace(point=point, material=material, binding=binding, manifest=manifest, archive=image_pin)
    h.previous_files, h.previous_index, h.database_end = files, index, end
    return point


@pytest.fixture
def restore_case(case, monkeypatch):
    """Real owner/reservation/journals, with explicit external protocol fixtures."""
    base = case['root']; archive_view = base/'archive-view'; archive_view.mkdir(mode=0o700)
    archives = archive_view/'backups'; archives.mkdir(mode=0o700)
    docker_root = base/'docker'; docker_root.mkdir(mode=0o700)
    operations = base/'operations'; operations.mkdir(mode=0o700)
    operation = operations/'restore-1'; operation.mkdir(mode=0o700)
    host = base/'host-reservation'; host.mkdir(mode=0o700)
    programs = base/'programs'; programs.mkdir(mode=0o700)
    for name in ('mount', 'xtables-multi', 'docker'):
        program = programs/name; program.write_bytes(b'private-protocol-program\n'); program.chmod(0o700)
    secret = base/'mysql.private'; secret.write_bytes(b'private-protocol-password'); secret.chmod(0o600)
    redis_secret = base/'redis.private'; redis_secret.write_bytes(b'private-protocol-redis'); redis_secret.chmod(0o600)
    application_config = base/'application.private'; application_config.write_bytes(b'APP=protocol\n'); application_config.chmod(0o600)
    source_metadata = base/'source-metadata'; source_metadata.mkdir(mode=0o700)
    source_identity = write(source_metadata/'identity.json', dict(sourceFingerprint=case['epoch']['sourceIdentity'],
        databaseUuid=case['epoch']['databaseUuid']))
    source_scope = write(source_metadata/'scope.json', dict(sourceIdentityPin=source_identity,
        endpointHosts=['http://127.0.0.1:9000']))
    mount = dict(mountId=2, parentId=1, device='0:1', root='/', mountPoint=str(archive_view),
        filesystem='cifs', source='//protocol/share', options=['rw', 'relatime'], superOptions=['rw'])
    h = SimpleNamespace(case=case, root=operation, claim=Path(case['target']['replacement']['stateRoot'])/'restore-1',
        archive_root=archives, docker_root=docker_root, source_identity=source_identity,
        source=dict(sourcePaths=[str(source_metadata)], archiveRoots=[str(archives)], sourceScopePin=source_scope,
            repositoryPointPins=[], recoveryPoints={}, parentChains={}, repositoryBindingPinsByManifestSha256={},
            minioDataMount='/data', sourceContainerIds=[s['id'] for s in case['target']['services']],
            sourceNetworkIds=['f'*64], sourceVolumeNames=[]),
        previous_files={}, previous_index=None, database_end=None, database_empty=False, redis_empty=False,
        natives=[], events=[], sequence=0, fail=None, loaded=set(), original_execute_calls=[])
    h.transport = TransportModel(mount, case['epoch']['databaseUuid'])
    first = record_point(h)
    record_point(h, parent=first, name='point2')
    h.engine = ProtocolDocker(h)
    target = case['target']
    for index, service in enumerate(target['services']):
        role = service['role']; row = original(); row.update(Id=service['id'], Name='/program-'+role)
        row['Config']['Labels'] = {}
        row['NetworkSettings']['Networks']['task-network'].update(Aliases=[role, service['id'][:12]],
            IPAddress=service['ip'], IPAMConfig=dict(IPv4Address=service['ip']))
        row['State'].update(Running=True, Pid=100+index, Status='running')
        if role in ('backend', 'frontend'):
            row['Image'] = 'sha256:'+('a' if role == 'backend' else 'b')*64
        else: row['Image'] = h.images[role]
        if role == 'backend':
            row['Mounts'] = [dict(Type='bind', Source=str(application_config), Destination='/app/application.private',
                RW=False, Mode='ro', Propagation='rprivate')]
            row['HostConfig']['Binds'] = [str(application_config)+':/app/application.private:ro']
        elif role == 'frontend':
            row['Mounts'] = []; row['HostConfig']['Binds'] = []
        else:
            directory = base/('service-data-'+role); directory.mkdir(mode=0o700)
            row['Mounts'][0]['Source'] = str(directory)
            row['HostConfig']['Binds'] = [str(directory)+':/data:rw']
            row['HostConfig']['PortBindings'] = {}
        if role == 'minio':
            service['ip'] = '127.0.0.1'
            row['HostConfig']['PortBindings'] = {str(port)+'/tcp':[dict(HostIp='0.0.0.0', HostPort=str(port))]
                for port in (9000,9001)}
        service['imageId'] = row['Image']; h.engine.rows[row['Id']] = row
    h.engine.images = deepcopy(h.image_rows)
    h.originals = {role:h.engine.inspect(next(s['id'] for s in target['services'] if s['role'] == role))
                   for role in ('backend', 'frontend')}
    target.update(machineId='private-protocol-machine', dockerEngineId='private-protocol-docker',
        dataRoot=str(base/'data'),
        dataPaths=[h.engine.rows[s['id']]['Mounts'][0]['Source'] for s in target['services']
            if s['role'] in ('mysql','minio','redis')],
        application=dict(startOrder=['backend', 'frontend']), buckets=['private'],
        redisRebuild=dict(database=0), secrets=dict(mysql=dict(MYSQL_ROOT_PASSWORD=pin(secret)),
            redis=dict(REDIS_PASSWORD=pin(redis_secret))), dockerPin=pin(programs/'docker'),
        iptablesPin=pin(programs/'xtables-multi'), redisClientPath='/usr/bin/redis-cli',
        dataPolicy=dict(businessInvariants=[]),
        resourceBudget=dict(schemaVersion='RestoreResourceBudget/v1', mysqlMemoryBytes=1,
            hostAvailableMemoryBytes=1, diskBytesByPath={str(base):1}))
    Path(target['dataRoot']).mkdir(mode=0o700)
    target['replacement'].update(schemaVersion='RegisteredApplicationReplacement/v2', services={
        role:dict(id=row['Id'], imageId=row['Image'], labels=row['Config']['Labels'],
                  mounts=sorted(row['Mounts'], key=lambda m:m['Destination'])) for role,row in
        ((s['role'],h.engine.rows[s['id']]) for s in target['services'])})
    # Explicit filesystem-observation protocol seam: tmpfs is never represented
    # as real ext4 evidence. All directories, device/inode checks and storage
    # scope validation are real; only the mount metadata comes from this model.
    local_mount = dict(mountId=1,parentId=0,device='0:2',root='/',mountPoint='/',
        filesystem='ext4',source='/dev/protocol-only',options=['rw'],superOptions=['rw'])
    def observed_directory(path, **kwargs):
        info = Path(path).stat()
        return dict(device=info.st_dev,inode=info.st_ino,mountIdentity=deepcopy(local_mount))
    import recovery_replacement_storage as storage
    monkeypatch.setattr(storage,'observe_directory',observed_directory)
    monkeypatch.setattr(storage,'parse_mountinfo',lambda text:[deepcopy(local_mount)])
    rows = {s['role']:h.engine.rows[s['id']] for s in target['services']}
    target['replacement']['storage'] = storage.snapshot_retained_storage(rows,
        ['/mnt/nas',str(archive_view),str(operations),str(Path(target['replacement']['stateRoot'])),target['dataRoot']], [])
    network = dict(Id='f'*64, Name='task-network', Driver='bridge', Internal=False, EnableIPv6=False,
        IPAM=dict(Driver='default', Config=[]), Options={}, Labels={}, Containers={row['Id']:{} for row in rows.values()})
    writer = write(base/'writer.json', dict(schemaVersion='RegisteredMainWriterEvidence/v1', database=target['database'],
        redisDatabase=0, objectBuckets=['private'], writerContainerIds=[rows['backend']['Id']],
        exclusiveResources=dict(database=True, objects=True, redis=True)))
    endpoint = dict(role='minio', ip='127.0.0.1', port=9000, containerPort='9000/tcp',
        bindings=deepcopy(rows['minio']['HostConfig']['PortBindings']),
        writeFence=dict(schemaVersion='PublishedHostWriteFence/v1', ports=[9000,9001],
            allowedWriterIPv4=[next(s['ip'] for s in target['services'] if s['role'] == 'backend')],
            programs={family:dict(pin=pin(programs/'xtables-multi'), applet=applet)
                for family,applet in [('ipv4','iptables'),('ipv6','ip6tables')]}))
    target['mainApplication'] = main.capture_main_application(target, rows, [network],
        [dict(role=role, versionPath=['images',role], imageId=rows[role]['Image']) for role in ('backend','frontend')],
        [pin(application_config)], writer, redis_authentication=dict(mode='PASSWORD'), published_data_endpoints=[endpoint])
    target['mainApplication']['archiveMountProtection'] = dict(schemaVersion='RegisteredArchiveViewProtection/v1',
        mountIdentity=mount, mountProgramPin=pin(programs/'mount'))
    case['capture']['source']['applicationImageIds'] = [s['imageId'] for s in target['services']]
    objects_pin = case['capture']['source']['objectSourcePin']; objects = pinned_json(objects_pin)
    objects['versionPins'] = [write(base/'current-versions.json', dict(images={s['role']:s['imageId'] for s in target['services']}))]
    case['capture']['source']['objectSourcePin'] = write(Path(objects_pin['path']), objects)
    case['base_pin'] = write(base/'capture.json',case['capture'])
    case['policy']['captureConfigurationPins'] = dict(source57=case['base_pin'])
    case['policy']['baselineTargetPin'] = write(base/'target.json', target)
    h.owner = dict(schemaVersion='RecoveryMinimalConfiguration/v1', pythonPin=pin(Path(sys.executable).resolve(strict=True)),
        operationsRoot=str(operations), targets=dict(target57=deepcopy(target)),
        sources=dict(source57=h.source), targetProgramPolicies=dict(target57=deepcopy(case['policy'])),
        targetBackupEpochPolicies=dict(target57=deepcopy(case['epoch'])),
        sourceProgramArchivePolicies=dict(source57=dict(schemaVersion='MainProgramSourceArchivePolicy/v1',
            sourceConfigRef='source57', roleVersionBindings=[dict(role=role,versionPath=['images',role]) for role in ROLES],
            architecture='amd64', maxArchiveBytes=1024*1024, maxImportBytes=2*1024*1024)),
        targetProgramResourceBudgets=dict(target57=dict(schemaVersion='MainProgramResourceBudget/v1',targetConfigRef='target57',
            projectionBytes=2*1024*1024, dockerImportBytes=2*1024*1024, minimumFreeBytes=4096)),
        deadlineMilliseconds=600000, maxChainLength=100, environmentMysqlClientPath='/usr/bin/mysql')
    h.request = dict(schemaVersion='SmallAppBackupUiRequest/v1', operationId='restore-1', action='RESTORE',
        sourceConfigRef='source57', parentChainRef=None, recoveryPointRef='point2', targetConfigRef='target57')
    machine = base/'machine-id'; machine.write_text(target['machineId'], encoding='ascii')
    original_absolute = replacement.absolute
    monkeypatch.setattr(replacement,'absolute',lambda path:machine if path == '/etc/machine-id' else original_absolute(path))
    monkeypatch.setattr(resources, 'HOST_ROOT', host)
    monkeypatch.setattr(resources, 'MACHINE_ID', machine)
    monkeypatch.setattr(resources, 'observe_resources', lambda owner, request, budget:dict(
        mysqlMemoryLimitBytes=1024**3, hostAvailableMemoryBytes=1024**3,
        disks=[dict(path=str(base), device=base.stat().st_dev, freeBytes=1024**3)]))
    import recovery_archive_view as archive_module
    monkeypatch.setattr(archive_module.ArchiveViewProtection, '_observed', lambda _:deepcopy(h.transport.mount))
    monkeypatch.setattr(main, 'mysql_query', lambda native, statement, *, mutation=False:
        native.query(statement, mutation=mutation))
    def redis_command(native, arguments, *, mutation=False):
        def reply():
            assert arguments[:2] == ['-n',str(native.config['redisRebuild']['database'])]
            if arguments[-1] == 'FLUSHDB':
                assert mutation
                h.redis_empty = True
                return b'OK\n'
            assert arguments[-2:] == ['--raw','DBSIZE'] and not mutation
            return b'0\n' if h.redis_empty else b'1\n'
        return native._invoke('redis', arguments, reply, mutation)
    monkeypatch.setattr(main, 'redis_command', redis_command)
    monkeypatch.setattr(containers, 'UnixDocker', lambda **kwargs:h.engine)
    h.native_type = native_type(h)
    monkeypatch.setattr(runtime, 'MinimalData', h.native_type)
    h.begin_original, h.finish_original = epoch.begin_restore, epoch.complete_restore
    def begin(*args, **kwargs):
        h.events.append(('begin-restore', args[1])); return h.begin_original(*args, **kwargs)
    def complete(*args, **kwargs):
        if args[3] == 'READY':
            receipt = pinned_json(args[4])
            assert receipt['state'] == 'SUCCEEDED'
            for key in PROGRAM_FIELDS[1:]:
                assert receipt[key] is not None
                pinned_json(receipt[key])
            h.events.append(('ready-publication', deepcopy(receipt)))
            if h.fail == 'ready': raise RecoveryError('PROTOCOL_READY_PUBLICATION_FAILURE')
        return h.finish_original(*args, **kwargs)
    monkeypatch.setattr(epoch, 'begin_restore', begin)
    monkeypatch.setattr(epoch, 'complete_restore', complete)
    h.freeze = lambda:freeze_inputs(h)
    h.freeze()
    return h


def freeze_inputs(h):
    """Fixture setup only, before reserve/binding/execute; never runtime mutation."""
    h.owner_pin = write(h.root/'configuration.json', h.owner)
    h.request_pin = write(h.root/'request.json', h.request)
    if not (h.root/'resource-reservation.json').exists():
        h.reservation = resources.reserve(h.owner, h.request, h.root)
    h.original_bytes = {Path(p['path']):Path(p['path']).read_bytes()
                        for p in (h.owner_pin,h.request_pin,h.reservation,h.case['policy']['baselineTargetPin'],h.case['base_pin'])}


def run(h):
    def original_execute(*args, **kwargs):
        h.original_execute_calls.append((args, kwargs))
        return runtime.execute_empty(*args, **kwargs)
    return replacement.execute(h.owner, h.request, h.root, [h.owner_pin,h.request_pin],
        original_execute, h.native_type, runtime.selected_chain)


def receipt(h):
    return pinned_json(pin(h.claim/'replacement-result.json'))


def assert_inputs_unchanged(h):
    assert all(path.read_bytes() == raw for path,raw in h.original_bytes.items())
    assert all(n.archive_guard is None or n.archive_guard.fd == -1 for n in h.natives)


def assert_no_external_writes(h):
    assert not h.engine.actions
    assert not any(row[0] in ('command','docker','sql','objects','redis') and row[-1] is True for row in h.events)


def assert_failure(h, *, phase=None, unknown=False):
    value = receipt(h)
    assert value['state'] == 'FAILED_RETAINED' and value['failureCode']
    if phase is not None: assert value['programExecutionPhase'] == phase
    assert value['terminalUnknown'] is unknown
    assert type(value['mutationDispatched']) is bool and type(value['originalResultPins']) is list
    for reference in value['originalResultPins']: pinned_json(reference)
    assert h.transport.scheduler != 'ON' or not any(row[0] == 'http' for row in h.events)
    assert not h.transport.releases
    assert not any(row[0] == 'docker' and row[2][:1] == ['start'] for row in h.events)
    assert_inputs_unchanged(h)
    return value


def test_real_entry_full_path_begins_before_first_db_and_shares_one_budget(restore_case):
    h = restore_case; result, native = run(h)
    assert [row[0] for row in h.events].count('begin-restore') == 1
    assert next(i for i,row in enumerate(h.events) if row[0] == 'begin-restore') < next(
        i for i,row in enumerate(h.events) if row[0] == 'sql')
    assert len(h.natives) == 2 and native is h.natives[-1]
    assert {n.native_context.phase for n in h.natives} == {'PREPARATION','RESTORE'}
    assert all(n.budget is h.natives[0].budget for n in h.natives)
    assert h.natives[0].protection_custody is native.protection_custody
    assert all(row[2] is native.protection_custody for row in h.events if row[:2] == ('bound','RESTORE'))
    with pytest.raises(RecoveryError,match='PROGRAM_NATIVE_(PHASE_CHANGED|CLOSED)'):
        h.natives[0].guard()
    assert epoch.read_current(h.case['epoch'])['state'] == 'READY'
    assert_inputs_unchanged(h)


def test_preparation_never_clears_data_and_loads_five_images_but_only_switches_two_apps(restore_case):
    h = restore_case; run(h)
    prep = [row for row in h.events if len(row)>1 and row[1] == 'PREPARATION']
    assert not any(row[0] == 'sql' and row[2].startswith(('DROP DATABASE','CREATE DATABASE')) for row in prep)
    assert not any(row[0] == 'objects' for row in prep)
    assert not any(row[0] == 'command' and 'FLUSHDB' in row[2] for row in prep)
    assert h.loaded == set(h.images.values())
    assert len([row for row in h.engine.actions if '/containers/create?' in row[1]]) == 2
    for role in ('mysql','minio','redis'):
        saved = next(s for s in h.case['target']['services'] if s['role'] == role)
        observed = h.engine.rows[saved['id']]
        assert observed['Id'] == saved['id'] and observed['Image'] == saved['imageId']
    assert [row[1] for row in h.events if row[0] == 'data-chain'] == [
        'DATABASE_FULL','DATABASE_INCREMENTAL','OBJECT_CHAIN_PHYSICAL','CONSISTENCY','START_APPLICATION']
    assert len(h.original_execute_calls) == 1
    assert h.original_execute_calls[0][1]['reservation_configuration'] == h.owner
    assert h.transport.releases == ['archive','fence','scheduler']


def test_success_fixed_evidence_is_pinned_in_result_receipt_before_ready(restore_case):
    h = restore_case; data,native = run(h); saved = receipt(h)
    assert data['replacementReceiptPin'] == pin(h.claim/'replacement-result.json')
    assert saved['programExecutionPhase'] == 'RESTORE'
    assert all(data[key] == saved[key] for key in PROGRAM_FIELDS)
    assert Path(saved['programNativeEvidencePin']['path']) == h.claim/'native-execution-evidence.json'
    assert Path(saved['programProtectionCustodyPin']['path']) == h.claim/'protection-custody-evidence.json'
    evidence = pinned_json(saved['programNativeEvidencePin'])
    assert evidence['schemaVersion'] == 'MainNativeExecutionEvidence/v1'
    assert evidence['generationPin'] == saved['programGenerationPin']
    assert {row['phase'] for row in evidence['invocations']} == {'PREPARATION','RESTORE'}
    assert not evidence['terminalUnknown'] and evidence['mutationDispatched']
    assert pinned_json(saved['programProtectionCustodyPin'])['state'] == 'RELEASED'
    assert all(reference in data['originalResultPins'] for n in h.natives for reference in n.original_pins)
    assert all(key in data for key in ('archiveViewReleasePin','publishedWriteFenceReleasePin','mysqlSchedulerReleasePin'))
    assert [row for row in h.events if row[0] == 'ready-publication'] == [('ready-publication',saved)]


def test_invalid_selected_history_is_refused_before_any_protection_or_stop(restore_case):
    h = restore_case
    selected = h.selected.binding
    path = Path(selected['path']); path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises((RecoveryError,ValueError)):
        run(h)
    assert_no_external_writes(h)
    assert not (h.claim/'archive-view').exists()
    assert not (h.claim/'published-fence').exists()
    assert not (h.claim/'mysql-scheduler').exists()


def test_constructor_failure_has_no_fabricated_custody_or_missing_context_evidence(restore_case):
    h = restore_case; h.fail = 'constructor-preparation'
    with pytest.raises(RecoveryError,match='PROTOCOL_NATIVE_CONSTRUCTOR_FAILURE'):
        run(h)
    value = assert_failure(h,phase='PREPARATION')
    assert value['programNativeEvidencePin'] is not None
    assert value['programProtectionCustodyPin'] is None and value['programGenerationPin'] is None
    assert_no_external_writes(h)


def test_context_construction_failure_records_not_started_without_fabricated_snapshots(restore_case,monkeypatch):
    h = restore_case
    import recovery_program_native as native_module
    class RefuseContext:
        def __init__(self,*args,**kwargs): raise RecoveryError('EXPECTED_CONTEXT_CONSTRUCTOR_FAILURE')
    monkeypatch.setattr(native_module,'MainNativeExecutionContext',RefuseContext)
    with pytest.raises(RecoveryError,match='EXPECTED_CONTEXT_CONSTRUCTOR_FAILURE'): run(h)
    value = assert_failure(h,phase='NOT_STARTED')
    assert value['programNativeEvidencePin'] is None and value['programProtectionCustodyPin'] is None
    assert value['programGenerationPin'] is None and not h.natives
    assert (h.claim/'program-context.json').exists() and (h.claim/'program-execution-binding.json').exists()
    assert_no_external_writes(h)


def test_unknown_http_outcome_retains_one_attempt_and_original_protections(restore_case):
    h = restore_case; h.fail = 'switch-unknown'
    with pytest.raises(TimeoutError,match='PROTOCOL_.*TERMINAL_UNKNOWN'): run(h)
    value = assert_failure(h,phase='PREPARATION',unknown=True)
    assert value['mutationDispatched'] and value['programGenerationPin'] is None
    assert value['programNativeEvidencePin'] is not None and value['programProtectionCustodyPin'] is not None
    count = len(h.events)
    with pytest.raises((RecoveryError,ValueError),match='REPLACEMENT_|PROGRAM_|BACKUP_EPOCH_'): run(h)
    assert len(h.events) == count
    assert any(Path(p['path']).name in ('load-failure.json','failure.json') for p in value['originalResultPins'])


def test_restore_failure_aggregates_both_natives_and_never_releases_or_restarts(restore_case):
    h = restore_case; h.fail = 'database'
    with pytest.raises(RecoveryError,match='PROTOCOL_.*FAILURE') as caught: run(h)
    value = assert_failure(h,phase='RESTORE')
    assert value['programGenerationPin'] is not None and len(h.natives) == 2
    evidence = pinned_json(value['programNativeEvidencePin'])
    assert {row['phase'] for row in evidence['invocations']} == {'PREPARATION','RESTORE'}
    assert all(reference in caught.value.evidence['originalResultPins'] for n in h.natives for reference in n.original_pins)
    assert epoch.read_current(h.case['epoch'])['state'] == 'FAILED_RETAINED'


def test_success_receipt_survives_ready_publication_failure_without_rewriting_pinned_snapshots(restore_case):
    h = restore_case; h.fail = 'ready'
    with pytest.raises(RecoveryError,match='PROTOCOL_READY_PUBLICATION_FAILURE') as caught: run(h)
    saved = receipt(h); assert saved['state'] == 'SUCCEEDED'
    assert epoch.read_current(h.case['epoch'])['state'] == 'REPLACING'
    evidence = pinned_json(saved['programNativeEvidencePin'])
    protection = pinned_json(saved['programProtectionCustodyPin'])
    assert not evidence['terminalUnknown'] and protection['state'] == 'RELEASED'
    assert getattr(caught.value,'native',None) is h.natives[-1]
    assert getattr(caught.value,'replacement_receipt_pin',None) == pin(h.claim/'replacement-result.json')
    assert h.transport.releases == ['archive','fence','scheduler']
    assert_inputs_unchanged(h)


def test_unregistered_program_keeps_legacy_replacement_branch_without_new_orchestrator(restore_case,monkeypatch):
    h = restore_case; owner = deepcopy(h.owner); owner.pop('targetProgramPolicies')
    owner.pop('targetBackupEpochPolicies')
    calls = []
    class LegacyNative:
        def __init__(self,*args,**kwargs): self.root=args[6]; calls.append('construct')
        @contextmanager
        def timed_stage(self,name): calls.append(name); yield
        def replacement_finish(self): calls.append('finish'); return {}
    monkeypatch.setattr(replacement,'prepare',lambda *args,**kwargs:calls.append('legacy-prepare'))
    monkeypatch.setattr(resources,'admit',lambda *args,**kwargs:calls.append('legacy-admit'))
    def old_execute(*args,**kwargs): calls.append('legacy-empty'); return {},SimpleNamespace()
    result = replacement.execute(owner,h.request,h.root,[],old_execute,LegacyNative,runtime.selected_chain)
    assert calls == ['legacy-admit','construct','target-replacement','legacy-prepare','legacy-empty','finish']
    assert pinned_json(result[0]['replacementReceiptPin'])['state'] == 'SUCCEEDED'
    assert not (h.claim/'program-context.json').exists()


def test_collector_retains_http_originals_after_sixth_step_for_multiple_networks(tmp_path):
    """Real private journal collection only; this is not a restored operation."""
    claim = tmp_path/'collector-only'; claim.mkdir(mode=0o700)
    switched = claim/'program-switch'; switched.mkdir(mode=0o700)
    expected = []
    for name in ('intent.json','0006-intent.json','0006-result.json',
                 '0007-intent.json','0007-result.json','0008-intent.json','failure.json'):
        expected.append(write(switched/name,dict(collectorFixture=name)))
    observed = module()._program_pins(claim)
    assert set(row['path'] for row in observed) == set(row['path'] for row in expected)
    assert all(pin(row['path']) == row for row in observed)
    # No result is invented for an unobserved final HTTP dispatch.
    assert not (switched/'0008-result.json').exists()
