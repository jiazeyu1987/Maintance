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
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'MINIMAL_FILE_INVALID')
    checksum = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        while True:
            guard(); chunk = stream.read(1024*1024)
            if not chunk: break
            size += len(chunk); checksum.update(chunk)
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
    # Retain command/SQL identifier syntax, not host/source/environment admission.
    require(request['action'] in ('FULL', 'INCREMENTAL'), 'MINIMAL_CAPTURE_ACTION_INVALID')
    require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', request['operationId']), 'OPERATION_ID_INVALID')
    require(re.fullmatch('[A-Za-z_][A-Za-z0-9_-]{0,63}', config['source']['database']), 'DATABASE_NAME_INVALID')
    return Path(config['archiveRoot'])/request['operationId']


class Originals:
    """Retain real input bytes and recheck identities without an authorization claim."""
    def __init__(self, guard):
        self.guard = guard; self.records = {}; self.identities = {}; self.directories = {}

    def read(self, reference, limit=64*1024*1024):
        self.guard()
        raw = original_bytes(reference, limit=limit)
        self.records[reference['path']] = (dict(reference), raw)
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
        self.check(); path = Path(path)
        require(self.root in path.parents, 'MINIMAL_OUTPUT_SCOPE_INVALID')
        require('..' not in path.parts, 'MINIMAL_OUTPUT_SCOPE_INVALID')
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
        self.guard()

    def binlog_connection(self):
        return ['--protocol=SOCKET', '--socket=/proc/1/root/var/run/mysqld/mysqld.sock']

    def binlog_container(self, mysql):
        return self.binlog_tool['containerId']


def source_config_redis(config):
    value = config.get('redisSnapshot')
    require(type(value) is dict and set(value) in ({'containerId', 'host', 'database'},
        {'containerId', 'host', 'database', 'passwordPin'}) and
        type(value['containerId']) is str and re.fullmatch('[0-9a-f]{64}', value['containerId']) and
        type(value['host']) is str and type(value['database']) is int and
        0 <= value['database'] < 16, 'MINIMAL_REDIS_SNAPSHOT_CONFIG_INVALID')
    return value


class MinimalSemantic(SemanticCapture):
    """Selected config + actual S3/SQL export, retaining the existing W03 format."""
    def check(self):
        self.series.check()


    def __init__(self, series, originals, descriptor, source_config):
        self.series = series; self.originals = originals
        self.source_config = source_config
        self.source = descriptor
        self.raw = canonical(self.source)
        self.scope = originals.document(self.source['sourceScopePin'])
        self.identity = originals.document(pin(self.scope['sourceIdentityPin']))
        self.reference_recipe = originals.document(self.source['referenceRecipePin'])
        self.derived_recipe = originals.document(self.source['derivedRecipePin'])
        self.derived = self._derived()
        self.provisioned_raw = canonical(dict(scope=self.scope, identity=self.identity,
            references=self.reference_recipe, recipe=self.derived_recipe, derived=self.derived))
        credential = originals.document(self.source['credentialReference'], 16384)
        self.client = ReadOnlyS3(self.source['endpoint'], credential['accessKey'], credential['secretKey'])
        self.parent_originals = []; self.parent_content_identities = []
        self.parent = self._parent()
        self.entries = {}; self.records = []; self.contents = {}
        self.position = None; self.rows = None; self.captured = False; self.finished = False

    def _parent(self):
        self.parent_versions = {}
        reference = self.source['parentExportIndexPin']
        if reference is None:
            return {}
        index = self.originals.document(reference)
        raw = self.originals.read(index['inventoryPin'])
        rows = [strict_document(line, 1048576) for line in raw.splitlines()]
        self.parent_versions = {(r['bucket'], r['key'], r['versionId']): r
            for r in rows if r['kind'] == 'version'}
        return index['contentPins']

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
