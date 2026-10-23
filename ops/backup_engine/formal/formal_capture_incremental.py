"""Bounded binlog and physical-file deltas under the original capture barriers.

An incremental request never calls mysqldump or copies unchanged file content.
The parent is an independently pinned captured point, not a path inferred from
the newest directory. Source restoration and repository acceptance are separate.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import time

import formal_snapshot_linux as snapshot

active_series = ContextVar('formal_capture_series', default=None)
ASSET_CLASSES = {'database', 'objects', 'configuration', 'images', 'deployment',
                 'tools', 'secret-references', 'redis', 'mq'}
WRITER_CLASSES = {'http', 'scheduler', 'worker', 'external-integration',
                  'direct-database', 'direct-object', 'host-administration'}


def require(value, code='FORMAL_CAPTURE_SERIES_INVALID'):
    snapshot.require(value, code)


def canonical(value):
    return snapshot._canonical_bytes(value)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pin(reference, *, limit=64*1024*1024):
    from formal_normal_owner import pin, strict_document
    pin(reference)
    path = Path(reference['path'])
    require(path.is_absolute() and path.resolve() == path and not path.is_symlink(),
            'FORMAL_CAPTURE_PARENT_CHANGED')
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    require(len(raw) <= limit, 'FORMAL_CAPTURE_RECORD_TOO_LARGE')
    return strict_document(raw, limit)


def validate_catalog(catalog):
    require(type(catalog) is dict and set(catalog) == {'schemaVersion', 'sourceIdentity',
            'assets', 'writers', 'rtoMilliseconds', 'rpoMilliseconds', 'stopWindowMilliseconds',
            'sourceLogicalBytes', 'temporaryPeakBytes'} and
            catalog['schemaVersion'] == 'backup-capture-catalog/v1')
    require(type(catalog['sourceIdentity']) is str and bool(catalog['sourceIdentity']))
    for name in ('rtoMilliseconds', 'rpoMilliseconds', 'stopWindowMilliseconds',
                 'sourceLogicalBytes', 'temporaryPeakBytes'):
        require(type(catalog[name]) is int and catalog[name] > 0)
    require(type(catalog['assets']) is list and type(catalog['writers']) is list)
    ids = set()
    for asset in catalog['assets']:
        require(type(asset) is dict and set(asset) == {'assetId', 'class', 'policy', 'reference'} and
                type(asset['assetId']) is str and asset['assetId'] and asset['assetId'] not in ids and
                asset['class'] in ASSET_CLASSES and asset['policy'] in
                {'CAPTURE', 'REBUILD', 'EXTERNAL_REFERENCE', 'NOT_PRESENT'})
        ids.add(asset['assetId'])
        value = read_pin(asset['reference'])
        if asset['class'] in {'database', 'objects', 'configuration', 'images', 'deployment', 'tools'}:
            require(asset['policy'] == 'CAPTURE', 'FORMAL_CAPTURE_ASSET_POLICY_INVALID')
        if asset['class'] == 'secret-references':
            require(asset['policy'] == 'EXTERNAL_REFERENCE' and type(value) is dict and
                    set(value) == {'schemaVersion', 'references'} and
                    value['schemaVersion'] == 'backup-secret-references/v1' and
                    type(value['references']) is list and value['references'] and
                    all(type(v) is dict and set(v) == {'provider', 'reference', 'version'} and
                        all(type(t) is str and t for t in v.values()) for v in value['references']),
                    'FORMAL_CAPTURE_SECRET_REFERENCE_INVALID')
        if asset['class'] in {'redis', 'mq'}:
            require(asset['policy'] in {'REBUILD', 'NOT_PRESENT'} and type(value) is dict and
                    set(value) == {'schemaVersion', 'class', 'policy', 'reason', 'configurationReference'} and
                    value['schemaVersion'] == 'backup-capture-ephemeral-policy/v1' and
                    value['class'] == asset['class'] and value['policy'] == asset['policy'] and
                    type(value['reason']) is str and value['reason'], 'FORMAL_CAPTURE_ASSET_POLICY_INVALID')
            read_pin(value['configurationReference'])
    require({v['class'] for v in catalog['assets']} == ASSET_CLASSES,
            'FORMAL_CAPTURE_ASSET_COVERAGE_REQUIRED')
    # The current capture path has one DB, one physical object root and one
    # approved configuration/image scope. Extra scopes need a real producer.
    require(all(sum(v['class'] == name for v in catalog['assets']) == 1 for name in
                {'database', 'objects', 'configuration', 'images', 'redis', 'mq'}),
            'FORMAL_CAPTURE_MULTIPLE_SOURCE_SCOPES_UNSUPPORTED')
    ids = set()
    for writer in catalog['writers']:
        require(type(writer) is dict and set(writer) == {'writerId', 'class', 'protectionReference'} and
                type(writer['writerId']) is str and writer['writerId'] and writer['writerId'] not in ids and
                writer['class'] in WRITER_CLASSES)
        ids.add(writer['writerId']); read_pin(writer['protectionReference'])
    require({v['class'] for v in catalog['writers']} == WRITER_CLASSES,
            'FORMAL_CAPTURE_WRITER_COVERAGE_REQUIRED')
    return catalog


def expected_gtid_mode(mysql):
    # Legacy configurations explicitly use the original GTID contract. A new
    # FILE_POSITION source must opt in; observed GTID failures never select it.
    mode = getattr(mysql, 'database_log_mode', 'GTID')
    require(mode in ('GTID', 'FILE_POSITION'), 'FORMAL_CAPTURE_LOG_MODE_INVALID')
    return 'ON' if mode == 'GTID' else 'OFF'


def position(mysql, *, guard):
    guard()
    flags = mysql.query('SELECT @@server_uuid,@@version,@@global.log_bin,@@global.binlog_format,'
                        '@@global.gtid_mode,@@global.read_only,@@global.super_read_only;').strip().split('\t')
    require(len(flags) == 7 and re.fullmatch('[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', flags[0]) and
            flags[1].startswith('8.0.') and flags[2:] == ['1', 'ROW',
                expected_gtid_mode(mysql), '1', '1'],
            'FORMAL_CAPTURE_BINLOG_PREREQUISITE_REQUIRED')
    rows = mysql.query('SHOW MASTER STATUS;').splitlines()
    require(len(rows) == 1, 'FORMAL_CAPTURE_BINLOG_POSITION_REQUIRED')
    row = rows[0].split('\t')
    require(len(row) == 5 and re.fullmatch(r'[A-Za-z0-9_-]+\.[0-9]{6}', row[0]) and
            row[1].isdigit() and int(row[1]) >= 4 and row[2:4] == ['', ''],
            'FORMAL_CAPTURE_BINLOG_SCOPE_INVALID')
    result = dict(databaseUuid=flags[0], serverVersion=flags[1], file=row[0],
                  position=int(row[1]), executedGtidSet=row[4])
    require(expected_gtid_mode(mysql) != 'OFF' or row[4] == '',
        'FORMAL_CAPTURE_FILE_POSITION_GTID_NOT_EMPTY')
    validate_position(result); guard(); return result


def gtid_intervals(text):
    require(type(text) is str, 'FORMAL_CAPTURE_GTID_INVALID')
    result = {}
    if text == '': return result
    for group in text.replace('\n', '').split(','):
        parts = group.strip().split(':'); source = parts[0]
        require(len(parts) >= 2 and re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', source) and
                source not in result, 'FORMAL_CAPTURE_GTID_INVALID')
        rows = []; last = 0
        for interval in parts[1:]:
            require(re.fullmatch(r'[1-9][0-9]*(?:-[1-9][0-9]*)?', interval), 'FORMAL_CAPTURE_GTID_INVALID')
            pair = [int(v) for v in interval.split('-')]; begin, end = pair[0], pair[-1]
            require(last < begin <= end < 2**63, 'FORMAL_CAPTURE_GTID_INVALID')
            rows.append((begin, end)); last = end
        result[source] = rows
    return result


def validate_position(value):
    require(type(value) is dict and set(value) == {'databaseUuid', 'serverVersion', 'file', 'position', 'executedGtidSet'} and
            type(value['databaseUuid']) is str and
            re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}', value['databaseUuid']) and
            type(value['serverVersion']) is str and re.fullmatch(r'8\.0\.[0-9]+(?:[.-][A-Za-z0-9_.-]+)?', value['serverVersion']) and
            type(value['file']) is str and re.fullmatch(r'[A-Za-z0-9_-]+\.[0-9]{6}', value['file']) and
            type(value['position']) is int and value['position'] >= 4, 'FORMAL_CAPTURE_BINLOG_POSITION_INVALID')
    gtid_intervals(value['executedGtidSet']); return value


def binlog_ranges(logs, start, end):
    """Select recorded log offsets without lineage/continuity comparisons."""
    names = [row['file'] for row in logs]
    selected = logs[names.index(start['file']):names.index(end['file'])+1]
    result = []
    for index, row in enumerate(selected):
        begin = start['position'] if index == 0 else 4
        stop = end['position'] if index == len(selected)-1 else row['bytes']
        if begin != stop:
            result.append(dict(file=row['file'], startPosition=begin, stopPosition=stop))
    return result


def _writer(path, component):
    from formal_capture_budget import active_budget
    budget = active_budget.get()
    require(budget is not None, 'FORMAL_CAPTURE_OUTPUT_ADMISSION_REQUIRED')
    return budget.open(path, component)


def write_record(path, document):
    raw = canonical(document)
    with _writer(path, 'proof') as output:
        output.write(raw); output.flush(); os.fsync(output.fileno())
    return dict(path=str(Path(path).absolute()), bytes=len(raw), sha256=digest(raw))


class CaptureSeries:
    def __init__(self, specification, *, guard):
        require(callable(guard) and type(specification) is dict and set(specification) ==
                {'schemaVersion', 'backupId', 'generationId', 'pointType', 'catalogPin', 'parentPointPin', 'parentRepositoryPointPin'} and
                specification['schemaVersion'] == 'backup-capture-series/v1' and
                specification['pointType'] in {'FULL', 'INCREMENTAL'} and
                all(type(specification[k]) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',
                    specification[k]) for k in ('backupId', 'generationId')))
        self.spec = specification; self.raw = canonical(specification); self.guard = guard
        self.catalog = validate_catalog(read_pin(specification['catalogPin']))
        self.catalog_raw = canonical(self.catalog); self.parent = self.repository_parent = None
        if specification['pointType'] == 'FULL':
            require(specification['parentPointPin'] is None and specification['parentRepositoryPointPin'] is None,
                    'FORMAL_CAPTURE_FULL_PARENT_FORBIDDEN')
        else:
            require(specification['parentPointPin'] is not None and specification['parentRepositoryPointPin'] is not None,
                    'FORMAL_CAPTURE_INCREMENTAL_PARENT_REQUIRED')
            self.parent = read_pin(specification['parentPointPin'])
            require(type(self.parent) is dict and set(self.parent) == {'schemaVersion', 'backupId', 'generationId',
                    'pointType', 'sourceIdentity', 'catalogPin', 'parentPointPin', 'parentRepositoryPointPin',
                    'databaseEnd', 'databaseDelta', 'fileInventory', 'fileDelta', 'sourceRestored',
                    'disasterRecoveryVerified', 'commonRecoveryPoint'} and
                    self.parent.get('schemaVersion') == 'backup-capture-point/v1' and
                    self.parent.get('generationId') == specification['generationId'] and
                    self.parent.get('sourceIdentity') == self.catalog['sourceIdentity'] and
                    self.parent.get('backupId') != specification['backupId'] and
                    type(self.parent.get('sourceRestored')) is bool and
                    self.parent.get('pointType') in {'FULL', 'INCREMENTAL'} and
                    type(self.parent.get('databaseEnd')) is dict and
                    type(self.parent.get('fileInventory')) is dict,
                    'FORMAL_CAPTURE_INCREMENTAL_LINEAGE_CHANGED')
            validate_file_inventory(self.parent['fileInventory'])
            validate_position(self.parent['databaseEnd'])
            require(self.parent['commonRecoveryPoint'] == 'sha256:'+digest(canonical(dict(
                database=self.parent['databaseEnd'], files=self.parent['fileInventory']))), 'FORMAL_CAPTURE_PARENT_CHANGED')
            self.repository_parent = read_pin(specification['parentRepositoryPointPin'])
            repository = self.repository_parent
            from formal_normal_owner import pin
            require(type(repository) is dict and type(repository.get('payloadRefs')) is list and
                    type(repository.get('parentPointPins')) is list, 'FORMAL_CAPTURE_PARENT_NOT_REPOSITORY_COMPLETE')
            for ref in repository['payloadRefs'] + repository['parentPointPins']: pin(ref)
            require(type(repository) is dict and set(repository) == {'schemaVersion', 'backupId', 'generationId',
                    'pointType', 'parentPointPins', 'commonRecoveryPoint', 'manifestPin', 'payloadRefs',
                    'readbackEvidencePin', 'ownerCloseEvidencePin', 'originalExitEvidencePin', 'integrityState',
                    'blockedReason', 'rehearsalEligible', 'controlledRestoreEligible'} and
                    repository['schemaVersion'] == 'RepositoryPoint/v1' and repository['integrityState'] == 'COMPLETE' and
                    repository['rehearsalEligible'] is True and repository['backupId'] == self.parent['backupId'] and
                    repository['generationId'] == self.parent['generationId'] and repository['pointType'] == self.parent['pointType'] and
                    repository['commonRecoveryPoint'] == self.parent['commonRecoveryPoint'] and
                    type(repository['payloadRefs']) is list and any(r['sha256'] == specification['parentPointPin']['sha256'] and
                        r['bytes'] == specification['parentPointPin']['bytes'] for r in repository['payloadRefs']),
                    'FORMAL_CAPTURE_PARENT_NOT_REPOSITORY_COMPLETE')
            for key in ('manifestPin', 'readbackEvidencePin', 'ownerCloseEvidencePin', 'originalExitEvidencePin'):
                pin(repository[key])
        self.start = self.end = self.file_inventory = self.file_delta = self.database_delta = None
        self.last_physical = None; self.binlog_database_scope = None; self.check()

    def check(self):
        self.guard()

    @contextmanager
    def activate(self):
        self.check(); require(active_series.get() is None)
        token = active_series.set(self)
        try: yield self
        finally: active_series.reset(token)

    def binlog_connection(self):
        return ['--host=127.0.0.1', '--port=3306']

    def binlog_container(self, mysql):
        return mysql.container

    def database(self, mysql, database, destination, *, guard):
        self.check(); self.start = position(mysql, guard=guard)
        from formal_capture_budget import active_budget
        budget = active_budget.get(); outer = snapshot.observation_deadline.get()
        require(budget is not None and outer is not None,
                'FORMAL_CAPTURE_OUTPUT_ADMISSION_REQUIRED')
        export_deadline = min(budget.deadline, outer)
        if self.spec['pointType'] == 'FULL':
            result = mysql.dump_until(database, destination, guard=guard, deadline=export_deadline)
            self.database_delta = dict(kind='SQL_FULL', segments=[])
        else:
            previous = self.parent['databaseEnd']
            mode = getattr(mysql, 'database_log_mode', 'GTID')
            log_rows = mysql.query('SHOW BINARY LOGS;').splitlines()
            logs = []
            for line in log_rows:
                fields = line.split('\t')
                require(len(fields) == 3 and fields[1].isdigit() and fields[2] == 'No',
                        'FORMAL_CAPTURE_BINLOG_ENCRYPTION_UNSUPPORTED')
                logs.append(dict(file=fields[0], bytes=int(fields[1])))
            ranges = binlog_ranges(logs, previous, self.start)
            raw_path = Path(destination).with_suffix('.incremental.raw')
            from formal_capture_budget import drain_owned_process
            with _writer(raw_path, 'sql-raw') as output:
                # Empty delta remains explicit executable SQL; no full dump.
                output.write(b'-- IntRuoyi binlog incremental; apply only after pinned parent.\n')
                for segment in ranges:
                    guard(); self.check()
                    script = ('test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; '
                              'test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; '
                              'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec mysqlbinlog "$@"')
                    argv = ['docker', 'exec', '-i', self.binlog_container(mysql), 'sh', '-ec', script, 'capture-binlog',
                            '--no-defaults', '--read-from-remote-server', *self.binlog_connection(),
                            '--user=root', '--disable-log-bin', '--database='+database,
                            '--start-position='+str(segment['startPosition']),
                            '--stop-position='+str(segment['stopPosition']), segment['file']]
                    end = export_deadline
                    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE)
                    observation = drain_owned_process(process, (mysql._password+'\n').encode(), output,
                                                       guard=guard, deadline=end)
                    require(observation['stdoutBytes'] > 0, 'FORMAL_CAPTURE_BINLOG_EMPTY')
                    output.write(b'\n')
                output.flush(); os.fsync(output.fileno())
            with raw_path.open('rb') as source, _writer(destination, 'sql-gzip') as output:
                with gzip.GzipFile(fileobj=output, mode='wb', mtime=0) as compressed:
                    while True:
                        guard(); block = source.read(1024*1024)
                        if not block: break
                        compressed.write(block)
                output.flush(); os.fsync(output.fileno())
            sha, size = snapshot._hash_object(destination, guard=guard)
            result = dict(sha256=sha[7:], bytes=size)
            # Retain raw log output as evidence; archive includes it explicitly.
            self.database_delta = dict(kind='BINLOG_SQL', logMode=mode, segments=ranges,
                                       parentPosition=previous, rawPin=_file_pin(raw_path, guard))
        self.end = position(mysql, guard=guard)
        self.check(); return result

    def files(self, source_root, destination, *, guard, scopes=None):
        """Runs only in the watchdog's frozen interval; guards must be SQL-free."""
        source = Path(source_root); target = Path(destination)
        before = scan_files(source, guard=guard, scopes=scopes, verify_files=False)
        old = {} if self.parent is None else self.parent['fileInventory']
        changed, deleted = calculate_file_delta(old, before, verify_inventory=False)
        from formal_capture_budget import active_budget
        budget = active_budget.get()
        require(budget is not None, 'FORMAL_CAPTURE_OUTPUT_ADMISSION_REQUIRED')
        require(source.is_absolute() and target.is_absolute() and source != target and
                source not in target.parents and target not in source.parents, 'FORMAL_CAPTURE_FILE_SCOPE_INVALID')
        budget.mkdir(target)
        # Directory metadata is cheap and permits independent validation of an
        # empty content delta without adding a synthetic object to the source.
        for name, row in sorted(before.items()):
            guard()
            if row['kind'] == 'directory':
                budget.mkdir(target/name)
            elif name in changed:
                with (source/name).open('rb') as original, _writer(target/name, 'physical') as output:
                    while True:
                        guard(); block = original.read(1024*1024)
                        if not block: break
                        output.write(block)
                    output.flush(); os.fsync(output.fileno())
                # Completed writes feed the final list; no destination content readback.
        # ponytail: retain the fingerprints needed to discover incremental changes,
        # but do not reread the source or copied bytes to verify storage corruption.
        copied = {n: r for n, r in before.items() if r['kind'] == 'directory' or n in changed}
        self.file_inventory = before
        self.file_delta = dict(changedPaths=sorted(changed), deletedPaths=deleted,
                               copiedFileCount=sum(r['kind'] == 'file' for r in copied.values()))
        chain = hashlib.sha256()
        for name, row in sorted(copied.items()):
            if row['kind'] == 'directory': chain.update(canonical(['directory', name]))
        for name, row in sorted(copied.items()):
            if row['kind'] == 'file': chain.update(canonical([name, 'sha256:'+row['sha256'], row['bytes']]))
        self.last_physical = dict(physicalTreeDigest=chain.hexdigest(),
                                 fileCount=self.file_delta['copiedFileCount'],
                                 totalBytes=sum(r['bytes'] for r in copied.values() if r['kind'] == 'file'),
                                 hostWritersVerified=False)
        return self.last_physical

    def materials(self, destination, *, guard):
        """Capture explicit deployment/tool/secret-reference originals privately."""
        from formal_capture_budget import active_budget
        root = Path(destination); budget = active_budget.get()
        require(budget is not None, 'FORMAL_CAPTURE_OUTPUT_ADMISSION_REQUIRED')
        budget.mkdir(root)
        entries = {'recovery-materials': 'directory'}; index_rows = []
        def copy(name, reference, purpose):
            from formal_normal_owner import pin
            pin(reference); guard(); self.check()
            source = Path(reference['path'])
            require(source.is_absolute() and source.resolve() == source and not source.is_symlink(),
                    'FORMAL_CAPTURE_RECOVERY_MATERIAL_CHANGED')
            sha = hashlib.sha256(); size = 0
            with source.open('rb') as original, _writer(root/name, 'config') as output:
                while True:
                    guard(); block = original.read(1024*1024)
                    if not block: break
                    output.write(block); sha.update(block); size += len(block)
                output.flush(); os.fsync(output.fileno())
            relative = 'recovery-materials/'+name
            entries[relative] = 'file|'+str(size)+'|'+sha.hexdigest()
            index_rows.append(dict(archivePath=relative, sourcePin=reference, purpose=purpose))
        copy('catalog.json', self.spec['catalogPin'], 'capture-catalog')
        for asset in self.catalog['assets']:
            key = digest(asset['assetId'].encode())[:16]
            copy('asset-'+key+'.json', asset['reference'], asset['class']+'-descriptor')
            if asset['class'] in {'redis', 'mq'}:
                descriptor = read_pin(asset['reference'])
                copy(asset['class']+'-'+key+'-configuration.json', descriptor['configurationReference'],
                     asset['class']+'-rebuild-configuration')
            if asset['class'] not in {'deployment', 'tools'}: continue
            descriptor = read_pin(asset['reference'])
            require(type(descriptor) is dict and set(descriptor) == {'schemaVersion', 'files'} and
                    descriptor['schemaVersion'] == 'backup-capture-materials/v1' and
                    type(descriptor['files']) is list and descriptor['files'],
                    'FORMAL_CAPTURE_RECOVERY_MATERIALS_REQUIRED')
            for number, reference in enumerate(descriptor['files']):
                copy(asset['class']+'-'+key+'-'+str(number)+'.bin', reference, asset['class'])
        for writer in self.catalog['writers']:
            copy('writer-'+digest(writer['writerId'].encode())[:16]+'.json',
                 writer['protectionReference'], writer['class']+'-protection-descriptor')
        index = write_record(root/'index.json', dict(schemaVersion='backup-capture-material-index/v1', files=index_rows))
        entries['recovery-materials/index.json'] = 'file|'+str(index['bytes'])+'|'+index['sha256']
        self.check(); return entries

    def point(self, *, source_restored):
        require(self.end is not None and self.file_inventory is not None and type(source_restored) is bool,
                'FORMAL_CAPTURE_POINT_INCOMPLETE')
        self.check()
        point = dict(schemaVersion='backup-capture-point/v1', backupId=self.spec['backupId'],
                     generationId=self.spec['generationId'], pointType=self.spec['pointType'],
                     sourceIdentity=self.catalog['sourceIdentity'], catalogPin=self.spec['catalogPin'],
                     parentPointPin=self.spec['parentPointPin'], databaseEnd=self.end,
                     parentRepositoryPointPin=self.spec['parentRepositoryPointPin'],
                     databaseDelta=self.database_delta, fileInventory=self.file_inventory,
                     fileDelta=self.file_delta, sourceRestored=source_restored,
                     disasterRecoveryVerified=False)
        # The identifier binds a real DB position and frozen content inventory.
        point['commonRecoveryPoint'] = 'sha256:'+digest(canonical(dict(database=self.end,
                                                      files=self.file_inventory)))
        return point


def _file_pin(path, guard, info=None):
    # Lightweight change token, NOT a content digest: same metadata can miss edits.
    guard()
    if info is None:
        info = Path(path).stat()
    token = hashlib.sha256(canonical(dict(bytes=info.st_size, mtime=info.st_mtime_ns,
                                          ctime=info.st_ctime_ns))).hexdigest()
    return dict(path=str(Path(path).absolute()), bytes=info.st_size, sha256=token)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def scan_files(root, *, guard, identity_sink=None, scopes=None, known_files=None, verify_files=True):
    root = Path(root)
    require(root.is_absolute() and root.resolve() == root and root.is_dir() and not root.is_symlink())
    if scopes is not None:
        require(type(scopes) is list and scopes and len(scopes) == len(set(scopes)) and
            all(type(n) is str and re.fullmatch(r'[A-Za-z0-9_.-]+', n) and n not in ('.', '..') and
                (root/n).is_dir() and not (root/n).is_symlink() for n in scopes),
            'FORMAL_CAPTURE_FILE_SCOPE_INVALID')
    root_info = root.lstat(); identities = {root: _identity(root_info)}; result = {}
    def walk_error(error): raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        guard()
        if Path(directory) == root and scopes is not None:
            dirs[:] = [name for name in dirs if name in scopes]
            files[:] = []
        for name in sorted(dirs+files):
            path = Path(directory)/name; info = path.lstat()
            if verify_files:
                require(not path.is_symlink() and info.st_dev == root_info.st_dev and
                        (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)) and
                        (not stat.S_ISREG(info.st_mode) or info.st_nlink == 1), 'FORMAL_CAPTURE_FILE_INVALID')
            relative = path.relative_to(root).as_posix()
            identities[path] = _identity(info)
            require(len(result) < 500000, 'FORMAL_CAPTURE_FILE_LIMIT')
            if stat.S_ISDIR(info.st_mode): result[relative] = dict(kind='directory')
            else:
                if known_files is not None and relative in known_files:
                    pin = known_files[relative]
                else:
                    pin = _file_pin(path, guard, info)
                result[relative] = dict(kind='file', bytes=pin['bytes'], sha256=pin['sha256'])
    guard()
    if identity_sink is not None:
        require(type(identity_sink) is dict and not identity_sink, 'FORMAL_CAPTURE_FILE_INVENTORY_INVALID')
        identity_sink.update(identities)
    if verify_files:
        validate_file_inventory(result)
    return result


def calculate_file_delta(parent, current, *, verify_inventory=True):
    if verify_inventory:
        validate_file_inventory(parent); validate_file_inventory(current)
    changed = {name: row for name, row in current.items() if parent.get(name) != row}
    removed = set(parent)-set(current)
    removed.update(name for name in parent.keys() & current.keys() if parent[name]['kind'] != current[name]['kind'])
    return changed, sorted(removed, key=lambda name: (-len(PurePosixPath(name).parts), name))


def validate_file_inventory(inventory):
    require(type(inventory) is dict and len(inventory) <= 500000, 'FORMAL_CAPTURE_FILE_INVENTORY_INVALID')
    for name, row in inventory.items():
        require(type(name) is str and name and '\\' not in name and '\0' not in name and
                not PurePosixPath(name).is_absolute() and
                all(p not in ('', '.', '..') for p in name.split('/')) and
                type(row) is dict and row.get('kind') in {'directory', 'file'},
                'FORMAL_CAPTURE_FILE_INVENTORY_INVALID')
        if row['kind'] == 'directory': require(set(row) == {'kind'})
        else:
            require(set(row) == {'kind', 'bytes', 'sha256'} and type(row['bytes']) is int and row['bytes'] >= 0 and
                    type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']),
                    'FORMAL_CAPTURE_FILE_INVENTORY_INVALID')
        parent = str(PurePosixPath(name).parent)
        require(parent == '.' or inventory.get(parent) == {'kind': 'directory'},
                'FORMAL_CAPTURE_FILE_INVENTORY_INVALID')
    return inventory


def verify_series_physical(root, expected, *, guard):
    series = active_series.get()
    if series is None:
        return snapshot.verify_physical_minio_tree(root, expected, lease_guard=guard)
    require(expected == series.last_physical and series.file_inventory is not None,
            'FORMAL_CAPTURE_FILE_DELTA_CHANGED')
    copied = scan_files(root, guard=guard)
    wanted = {n: r for n, r in series.file_inventory.items() if r['kind'] == 'directory' or
              n in series.file_delta['changedPaths']}
    require(copied == wanted, 'FORMAL_CAPTURE_FILE_DELTA_CHANGED')
    return expected
