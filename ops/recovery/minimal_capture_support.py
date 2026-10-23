"""Explicit single-operator capture inputs, bounded writes and existing formats.

Pins here describe actual bytes. They are not grants or lifecycle approvals.
The formal entry remains separate; this module implements the selected minimal path.
"""
from contextlib import contextmanager
import hashlib
import json
import subprocess
import os
from pathlib import Path
import re
import shutil
import stat
import time
import uuid

from formal_capture_incremental import (CaptureSeries, canonical, digest, require,
    validate_file_inventory, validate_position)
from formal_capture_recovery_inputs import original_bytes
from formal_capture_semantics import (SemanticCapture, validate_reference_recipe,
    validate_source)
from formal_normal_owner import pin, strict_document
from formal_s3_export import ReadOnlyS3


def path_checked(value, *, directory=False):
    require(type(value) is str and value and '\0' not in value, 'MINIMAL_PATH_INVALID')
    path = Path(value)
    require(path.is_absolute() and all(p.resolve() == p and not p.is_symlink()
        for p in (path, *path.parents)), 'MINIMAL_PATH_INVALID')
    if directory:
        require(path.is_dir(), 'MINIMAL_DIRECTORY_REQUIRED')
    return path


def actual_pin(path, guard=lambda: None):
    path = path_checked(str(path)); before = path.lstat()
    def identity(i):
        return (i.st_dev, i.st_ino, i.st_mode, i.st_nlink, i.st_size, i.st_mtime_ns, i.st_ctime_ns)
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'MINIMAL_FILE_INVALID')
    checksum = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        require(identity(os.fstat(stream.fileno())) == identity(before), 'MINIMAL_INPUT_CHANGED')
        while True:
            guard(); chunk = stream.read(1024*1024)
            if not chunk: break
            size += len(chunk); checksum.update(chunk)
        require(identity(os.fstat(stream.fileno())) == identity(before), 'MINIMAL_INPUT_CHANGED')
    require(identity(path.lstat()) == identity(before), 'MINIMAL_INPUT_CHANGED')
    return dict(path=str(path), bytes=size, sha256=checksum.hexdigest())


def document(path):
    reference = actual_pin(path)
    return strict_document(original_bytes(reference), 64*1024*1024), reference


def exclusive_json(path, value):
    path = path_checked(str(path)); raw = canonical(value)
    temporary = path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.pending')
    try:
        with temporary.open('xb') as out:
            os.chmod(temporary, 0o600); out.write(raw); out.flush(); os.fsync(out.fileno())
        # Publish complete bytes exclusively, with no replace/copy fallback.
        os.link(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()
    if os.name == 'posix':
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    return actual_pin(path)


def validate_job(config, request):
    require(type(request) is dict and set(request) == {'schemaVersion', 'operationId', 'action',
        'sourceConfigRef', 'parentChainRef', 'recoveryPointRef', 'targetConfigRef'} and
        request['schemaVersion'] == 'SmallAppBackupUiRequest/v1' and
        type(request['operationId']) is str and
        re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', request['operationId']) and
        request['action'] in ('FULL', 'INCREMENTAL') and request['recoveryPointRef'] is None and
        request['targetConfigRef'] is None, 'MINIMAL_CAPTURE_REQUEST_INVALID')
    require(type(config) is dict and set(config) == {'schemaVersion', 'sourceConfigRef', 'archiveRoot',
        'sourceLockPath', 'tools', 'limits', 'source', 'parent'} and
        config['schemaVersion'] == 'minimal-source-capture-config/v1' and
        type(config['sourceConfigRef']) is str and config['sourceConfigRef'] and
        request['sourceConfigRef'] == config['sourceConfigRef'], 'MINIMAL_CAPTURE_CONFIG_INVALID')
    source = config['source']
    require(type(source) is dict and set(source) - {'databaseLogMode', 'minioPhysicalScopes', 'redisSnapshot'} == {'sourceIdentity', 'sourceFingerprint', 'databaseUuid',
        'database', 'mysqlContainerId', 'minioContainerId', 'minioDataPath', 'minioMountDestination',
        'writerContainerIds', 'applicationImageIds', 'passwordPin', 'objectSourcePin',
        'configurationPins', 'materialPins'}, 'MINIMAL_SOURCE_CONFIG_INVALID')
    require(all(type(source[k]) is str and source[k] for k in ('sourceIdentity', 'sourceFingerprint')) and
        source['sourceIdentity'] == source['sourceFingerprint'] and
        type(source['database']) is str and re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}', source['database']) and
        type(source['databaseUuid']) is str and re.fullmatch('[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',
            source['databaseUuid']), 'MINIMAL_SOURCE_CONFIG_INVALID')
    mode = source.get('databaseLogMode', 'GTID')
    require(mode in ('GTID', 'FILE_POSITION'), 'MINIMAL_DATABASE_LOG_MODE_INVALID')
    writers = source['writerContainerIds']
    require(type(writers) is list and writers and len(writers) <= 100 and
        len(set(writers)) == len(writers), 'MINIMAL_WRITER_SET_REQUIRED')
    containers = [source['mysqlContainerId'], source['minioContainerId'], *writers]
    require(len(set(containers)) == len(containers) and all(type(c) is str and
        re.fullmatch('[0-9a-f]{64}', c) for c in containers), 'MINIMAL_CONTAINER_ID_INVALID')
    images = source['applicationImageIds']
    require(type(images) is list and images and len(set(images)) == len(images) and
        all(type(i) is str and re.fullmatch('sha256:[0-9a-f]{64}', i) for i in images),
        'MINIMAL_IMAGE_IDS_REQUIRED')
    for key in ('passwordPin', 'objectSourcePin'): pin(source[key])
    for key, label in (('configurationPins', 'role'), ('materialPins', 'purpose')):
        require(type(source[key]) is list and source[key] and len(source[key]) <= 1000,
            'MINIMAL_MATERIALS_REQUIRED')
        names = set()
        for row in source[key]:
            require(type(row) is dict and set(row) == {label, 'reference'} and
                type(row[label]) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,100}', row[label]) and
                row[label] not in names, 'MINIMAL_MATERIALS_INVALID')
            names.add(row[label]); pin(row['reference'])
    require(type(config['tools']) is dict and set(config['tools']) == {'docker', 'ip'},
        'MINIMAL_TOOL_PATHS_REQUIRED')
    bounds = {'workSeconds': (1, 43200), 'cleanupSeconds': (1, 600), 'clientWaitSeconds': (0, 7200),
        'maxWrittenBytes': (1, 2**63-1), 'minimumFreeBytes': (1, 2**63-1), 'stopSeconds': (1, 120),
        'querySeconds': (1, 120), 'readySeconds': (1, 300), 'dataMaxRows': (1, 10000000),
        'dataMaxNodes': (1, 100000000), 'dataMaxBytes': (1, 16*1024**3), 'dataSeconds': (1, 7200)}
    limits = config['limits']
    require(type(limits) is dict and set(limits) == set(bounds) and all(type(limits[k]) is int and
        low <= limits[k] <= high for k, (low, high) in bounds.items()), 'MINIMAL_LIMITS_INVALID')
    parent = config['parent']
    if request['action'] == 'FULL':
        require(parent is None and request['parentChainRef'] is None, 'MINIMAL_FULL_PARENT_REFUSED')
    else:
        require(type(parent) is dict and set(parent) == {'parentChainRef', 'capturePointPin',
            'repositoryPointPin', 'objectContentIndexPin'} and type(parent['parentChainRef']) is str and
            parent['parentChainRef'] and parent['parentChainRef'] == request['parentChainRef'],
            'MINIMAL_INCREMENTAL_PARENT_REQUIRED')
        for key in ('capturePointPin', 'repositoryPointPin', 'objectContentIndexPin'): pin(parent[key])
    root = path_checked(config['archiveRoot'], directory=True)
    path_checked(config['sourceLockPath'])
    return root/request['operationId']


class Originals:
    """Retain real input bytes and recheck identities without an authorization claim."""
    def __init__(self, guard):
        self.guard = guard; self.records = {}; self.identities = {}; self.directories = {}

    def read(self, reference, limit=64*1024*1024):
        self.guard(); raw = original_bytes(pin(reference), limit=limit)
        previous = self.records.get(reference['path'])
        require(previous is None or previous == (reference, raw), 'MINIMAL_INPUT_CHANGED')
        self.records[reference['path']] = (dict(reference), raw)
        path = Path(reference['path'])
        self.identities[str(path)] = self.identity(path.lstat())
        for directory in path.parents:
            info = directory.lstat()
            require(stat.S_ISDIR(info.st_mode), 'MINIMAL_INPUT_CHANGED')
            value = (info.st_dev, info.st_ino, info.st_mode)
            require(str(directory) not in self.directories or self.directories[str(directory)] == value,
                'MINIMAL_INPUT_CHANGED')
            self.directories[str(directory)] = value
        return raw

    def document(self, reference, limit=64*1024*1024):
        return strict_document(self.read(reference, limit), limit)

    def current(self):
        self.check(full=False)

    @staticmethod
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

    def check(self, *, full=True):
        self.guard()
        # Between the initial and final full reads, any replacement, content,
        # permission or ancestor-link change invalidates the captured inputs.
        for path, expected in self.directories.items():
            info = Path(path).lstat()
            require((info.st_dev, info.st_ino, info.st_mode) == expected, 'MINIMAL_INPUT_CHANGED')
        for reference, raw in self.records.values():
            require(self.identity(Path(reference['path']).lstat()) == self.identities[reference['path']],
                'MINIMAL_INPUT_CHANGED')
            if full:
                require(original_bytes(reference) == raw, 'MINIMAL_INPUT_CHANGED')


class Budget:
    """Finite cumulative write/time/disk budget, including temporary exports."""
    def __init__(self, root, limits):
        self.root = path_checked(str(root), directory=True)
        self.deadline = time.monotonic()+limits['workSeconds']
        self.maximum = limits['maxWrittenBytes']; self.reserve = limits['minimumFreeBytes']
        self.written = 0

    def check(self):
        require(time.monotonic() < self.deadline, 'MINIMAL_WORK_TIMEOUT')
        require(shutil.disk_usage(self.root).free >= self.reserve, 'MINIMAL_FREE_SPACE_REQUIRED')

    def target(self, path):
        self.check(); path = path_checked(str(path))
        require(self.root in path.parents, 'MINIMAL_OUTPUT_SCOPE_INVALID')
        return path

    def mkdir(self, path):
        path = self.target(path); path.mkdir(mode=0o700)

    @contextmanager
    def open(self, path, component):
        path = self.target(path)
        with path.open('xb') as stream:
            os.chmod(path, 0o600)
            budget = self
            class Sink:
                def write(self, data):
                    budget.check()
                    require(budget.written+len(data) <= budget.maximum, 'MINIMAL_WRITE_LIMIT')
                    size = stream.write(data); budget.written += size
                    require(size == len(data), 'MINIMAL_SHORT_WRITE')
                    return size
                def flush(self): return stream.flush()
                def fileno(self): return stream.fileno()
                def tell(self): return stream.tell()
            yield Sink()

    def link(self, source, target):
        os.link(self.target(source), self.target(target))

    def unlink_complete(self, path):
        self.target(path).unlink()

    @contextmanager
    def activate(self):
        from formal_capture_budget import active_budget
        require(active_budget.get() is None, 'MINIMAL_BUDGET_ALREADY_ACTIVE')
        token = active_budget.set(self)
        try: yield self
        finally: active_budget.reset(token)


class MinimalSeries(CaptureSeries):
    """Reuse real dump/binlog/physical algorithms; no old producer admission."""
    def __init__(self, config, request, catalog_pin, originals, guard):
        self.guard = guard; self.originals = originals
        self.catalog = originals.document(catalog_pin)
        parent = config['parent']
        self.parent = None if parent is None else originals.document(parent['capturePointPin'])
        self.repository_parent = None if parent is None else originals.document(parent['repositoryPointPin'])
        self.spec = dict(schemaVersion='backup-capture-series/v1', backupId=request['operationId'],
            generationId=request['operationId'] if parent is None else self.parent['generationId'],
            pointType=request['action'], catalogPin=catalog_pin,
            parentPointPin=None if parent is None else parent['capturePointPin'],
            parentRepositoryPointPin=None if parent is None else parent['repositoryPointPin'])
        if self.parent is not None:
            p = self.parent; r = self.repository_parent
            require(p['schemaVersion'] == 'backup-capture-point/v1' and
                p['pointType'] in ('FULL', 'INCREMENTAL') and
                p['sourceIdentity'] == config['source']['sourceIdentity'] and
                p['backupId'] != request['operationId'] and
                r['schemaVersion'] == 'RepositoryPoint/v1' and
                all(r[k] == p[k] for k in ('backupId', 'generationId', 'pointType', 'commonRecoveryPoint')),
                'MINIMAL_PARENT_CHAIN_INVALID')
            validate_position(p['databaseEnd']); validate_file_inventory(p['fileInventory'])
            require(p['databaseEnd']['databaseUuid'] == config['source']['databaseUuid'] and
                p['commonRecoveryPoint'] == 'sha256:'+digest(canonical(dict(
                    database=p['databaseEnd'], files=p['fileInventory']))) and
                any(ref['sha256'] == parent['capturePointPin']['sha256'] and
                    ref['bytes'] == parent['capturePointPin']['bytes'] for ref in r['payloadRefs']),
                'MINIMAL_PARENT_CHAIN_INVALID')
            originals.read(pin(r['manifestPin']))
            modes = [ref for ref in r['payloadRefs']
                     if ref['path'].endswith('/payload/database-log-mode.json')]
            if config['source'].get('databaseLogMode', 'GTID') == 'FILE_POSITION':
                require(len(modes) == 1 and originals.document(modes[0]) ==
                    dict(mode='FILE_POSITION', observedGtidMode='OFF') and
                    p['databaseEnd']['executedGtidSet'] == '', 'MINIMAL_PARENT_LOG_MODE_CHANGED')
        self.raw = canonical(self.spec); self.catalog_raw = canonical(self.catalog)
        self.start = self.end = self.file_inventory = self.file_delta = self.database_delta = None
        self.last_physical = None
        self.binlog_database_scope = [config['source']['database']]
        self.binlog_tool = None
        self.mysql_source = config['source']['mysqlContainerId']
        if request['action'] == 'INCREMENTAL':
            exporters = [r['reference'] for r in config['source']['materialPins']
                         if r['purpose'] == 'mysqlbinlog-exporter']
            require(len(exporters) == 1, 'MINIMAL_BINLOG_TOOL_REQUIRED')
            self.binlog_tool = originals.document(exporters[0])
            self.binlog_container(None)
        self.check()

    def check(self):
        self.guard(); self.originals.current()
        require(canonical(self.spec) == self.raw and canonical(self.catalog) == self.catalog_raw,
            'MINIMAL_SERIES_CHANGED')

    def binlog_connection(self):
        return ['--protocol=SOCKET', '--socket=/proc/1/root/var/run/mysqld/mysqld.sock']

    def binlog_container(self, mysql):
        tool = self.binlog_tool
        require(type(tool) is dict and set(tool) == {'schemaVersion', 'containerId',
            'imageId', 'executable', 'sha256'} and tool['schemaVersion'] == 'MysqlBinlogContainerTool/v1'
            and type(tool['containerId']) is str and re.fullmatch('[0-9a-f]{64}', tool['containerId'])
            and type(tool['imageId']) is str and re.fullmatch('sha256:[0-9a-f]{64}', tool['imageId'])
            and tool['executable'] == '/usr/local/bin/mysqlbinlog'
            and type(tool['sha256']) is str and re.fullmatch('[0-9a-f]{64}', tool['sha256']),
            'MINIMAL_BINLOG_TOOL_INVALID')
        row = json.loads(subprocess.check_output(['docker', 'inspect', tool['containerId']], timeout=10))[0]
        require(row['Id'] == tool['containerId'] and row['Image'] == tool['imageId']
            and row['State']['Running'] and row['HostConfig']['ReadonlyRootfs']
            and row['HostConfig']['NetworkMode'] == 'container:'+self.mysql_source
            and row['HostConfig']['PidMode'] == 'container:'+self.mysql_source,
            'MINIMAL_BINLOG_TOOL_CHANGED')
        checksum = subprocess.check_output(['docker', 'exec', tool['containerId'],
            'sha256sum', tool['executable']], timeout=10).decode().split()
        require(checksum == [tool['sha256'], tool['executable']], 'MINIMAL_BINLOG_TOOL_CHANGED')
        self.guard()
        return tool['containerId']


def source_config_redis(config):
    value = config.get('redisSnapshot')
    require(type(value) is dict and set(value) == {'containerId', 'host', 'database'} and
        type(value['containerId']) is str and re.fullmatch('[0-9a-f]{64}', value['containerId']) and
        type(value['host']) is str and type(value['database']) is int and
        0 <= value['database'] < 16, 'MINIMAL_REDIS_SNAPSHOT_CONFIG_INVALID')
    return value


class MinimalSemantic(SemanticCapture):
    """Selected config + actual S3/SQL export, retaining the existing W03 format."""
    def check(self):
        from formal_capture_recovery_inputs import original_bytes
        self.originals.current(); self.series.check()
        require(canonical(self.source) == self.raw, 'FORMAL_CAPTURE_SEMANTIC_SOURCE_CHANGED')
        require(canonical(dict(scope=self.scope, identity=self.identity, references=self.reference_recipe,
            recipe=self.derived_recipe, derived=self.derived)) == self.provisioned_raw,
            'FORMAL_CAPTURE_SEMANTIC_SOURCE_CHANGED')
        for reference, raw, allow_empty in self.parent_originals:
            require(original_bytes(reference, allow_empty=allow_empty) == raw,
                'FORMAL_CAPTURE_SEMANTIC_PARENT_CHANGED')
        for path, identity in self.parent_content_identities:
            require(self.file_identity(path.lstat()) == identity, 'FORMAL_CAPTURE_OBJECT_PARENT_CHANGED')


    def __init__(self, series, originals, descriptor, source_config):
        self.series = series; self.originals = originals
        self.source_config = source_config
        self.source = validate_source(descriptor, series.spec['pointType'])
        self.raw = canonical(self.source)
        self.scope = originals.document(self.source['sourceScopePin'])
        self.identity = originals.document(pin(self.scope['sourceIdentityPin']))
        import urllib.parse
        endpoint = urllib.parse.urlsplit(self.source['endpoint'])
        require(self.source['sourceIdentity'] == source_config['sourceIdentity'] and
            self.source['minioContainerId'] == source_config['minioContainerId'] and
            self.identity['sourceFingerprint'] == source_config['sourceFingerprint'] and
            self.identity['databaseUuid'] == source_config['databaseUuid'] and
            endpoint.hostname in self.scope['endpointHosts'], 'MINIMAL_SOURCE_BINDING_CHANGED')
        self.reference_recipe = validate_reference_recipe(originals.document(self.source['referenceRecipePin']),
            self.source['sourceIdentity'], self.source['sourceScopePin'])
        self.derived_recipe = originals.document(self.source['derivedRecipePin'])
        self.derived = self._derived()
        self.provisioned_raw = canonical(dict(scope=self.scope, identity=self.identity,
            references=self.reference_recipe, recipe=self.derived_recipe, derived=self.derived))
        public = [self.source['sourceScopePin'], self.scope['sourceIdentityPin'],
            self.source['referenceRecipePin'], self.source['derivedRecipePin'], *self.source['versionPins'],
            *(r for item in self.derived_recipe['classes'].values() for r in item['configurationReferences'])]
        require(all(r['path'] != self.source['credentialReference']['path'] for r in public),
            'MINIMAL_SECRET_AS_MATERIAL_REFUSED')
        for reference in self.source['versionPins']: originals.document(reference)
        credential = originals.document(self.source['credentialReference'], 16384)
        require(set(credential) == {'schemaVersion', 'endpoint', 'accessKey', 'secretKey'} and
            credential['schemaVersion'] == 'backup-source-s3-credential/v1' and
            credential['endpoint'] == self.source['endpoint'], 'MINIMAL_S3_CREDENTIAL_INVALID')
        self.client = ReadOnlyS3(self.source['endpoint'], credential['accessKey'], credential['secretKey'])
        self.parent_originals = []; self.parent_content_identities = []
        self.parent = self._parent()
        self.entries = {}; self.records = []; self.contents = {}
        self.position = None; self.rows = None; self.captured = False; self.finished = False

    def capture(self, mysql, database, root, guard):
        super().capture(mysql, database, root, guard)
        if 'redisSnapshot' in self.source_config:
            from minimal_redis_snapshot import observe
            self.redis_snapshot = observe(source_config_redis(self.source_config), guard)
            reference = self._record('redis-dump-snapshot.json', self.redis_snapshot)
            item = self.derived['redis']
            require(item['classification'] == 'RESTORE' and item['executorKey'] == 'REDIS_DUMP_ABSOLUTE_EXPIRY',
                'MINIMAL_REDIS_POLICY_INVALID')
            item['payloadPins'] = [reference]
            self.provisioned_raw = canonical(dict(scope=self.scope, identity=self.identity,
                references=self.reference_recipe, recipe=self.derived_recipe, derived=self.derived))
            self.check()

    def finalize(self, point, guard):
        if 'redisSnapshot' in self.source_config:
            from minimal_redis_snapshot import verify_current
            verify_current(self.redis_snapshot, source_config_redis(self.source_config), guard)
        return super().finalize(point, guard)

    def _derived(self):
        recipe = self.derived_recipe
        require(set(recipe) == {'schemaVersion', 'sourceIdentity', 'classes'} and
            recipe['schemaVersion'] == 'backup-capture-derived-recipe/v1' and
            recipe['sourceIdentity'] == self.source['sourceIdentity'] and
            set(recipe['classes']) == {'redis', 'queue'}, 'MINIMAL_DERIVED_RECIPE_INVALID')
        result = {}
        for name, item in recipe['classes'].items():
            require(set(item) == {'classification', 'requiredForBusiness', 'executorKey',
                'rebuildFrom', 'configurationReferences'} and
                item['classification'] in ('NOT_PRESENT', 'REBUILD', 'RESTORE') and
                type(item['requiredForBusiness']) is bool and
                type(item['configurationReferences']) is list and item['configurationReferences'],
                'MINIMAL_DERIVED_RECIPE_INVALID')
            for reference in item['configurationReferences']: self.originals.read(pin(reference))
            if item['classification'] == 'NOT_PRESENT':
                require(item['requiredForBusiness'] is False and item['executorKey'] is None and
                    item['rebuildFrom'] is None, 'MINIMAL_DERIVED_RECIPE_INVALID')
            elif item['classification'] == 'RESTORE':
                require(name == 'redis' and item['executorKey'] == 'REDIS_DUMP_ABSOLUTE_EXPIRY' and
                    item['rebuildFrom'] is None and source_config_redis(self.source_config),
                    'MINIMAL_DERIVED_RECIPE_INVALID')
            else:
                require(type(item['executorKey']) is str and item['executorKey'] and
                    item['rebuildFrom'] in ('DATABASE', 'OBJECTS'), 'MINIMAL_DERIVED_RECIPE_INVALID')
            value = dict(classification=item['classification'], requiredForBusiness=item['requiredForBusiness'],
                executorKey=item['executorKey'], payloadPins=[], configurationSourcePins=item['configurationReferences'])
            if item['classification'] == 'REBUILD': value['rebuildFrom'] = item['rebuildFrom']
            result[name] = value
        return result
