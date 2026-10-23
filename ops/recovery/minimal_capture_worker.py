#!/usr/bin/env python3
"""Real Linux FULL/I1 capture worker for the explicitly selected minimal path."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone

from formal_capture_budget import drain_owned_process
from formal_capture_incremental import canonical, position, scan_files, write_record
from formal_capture_recovery_inputs import capture_recovery_inputs
from formal_capture_semantics import export_listing, observe_position
from formal_data_evidence import DataMySql, compare_data, observe_data, observe_affected_data
from formal_s3_export import _require_empty_multipart_observation
from formal_snapshot_linux import (PrivateDockerMySql, FormalSnapshotError, observation_deadline,
    observation_timeout, require)
from minimal_capture_support import (Budget, MinimalSeries, MinimalSemantic, Originals, actual_pin,
    document, exclusive_json, path_checked, validate_job)


def now(): return datetime.now(timezone.utc).isoformat()


def failure_code(error):
    # Never serialize exception text: subprocess/HTTP errors can contain credentials.
    code = getattr(error, 'code', None)
    import re
    if type(code) is str and re.fullmatch('[A-Z][A-Z0-9_]{0,150}', code): return code
    if isinstance(error, KeyboardInterrupt): return 'MINIMAL_OPERATOR_INTERRUPTED'
    if isinstance(error, FileNotFoundError): return 'MINIMAL_INPUT_FILE_MISSING'
    if isinstance(error, PermissionError): return 'MINIMAL_PERMISSION_DENIED'
    if isinstance(error, UnicodeError): return 'MINIMAL_INPUT_ENCODING_INVALID'
    return 'MINIMAL_CAPTURE_INTERNAL_ERROR'


def canonical_mount_records(mounts):
    """Ignore only outer record order; retain every field and duplicate record."""
    require(type(mounts) is list and all(type(record) is dict for record in mounts),
        'MINIMAL_SOURCE_MOUNTS_INVALID')
    return sorted(canonical(record) for record in mounts)


def diagnostic_value(value, *, private=False):
    """Keep inspect structure, never include credentials or raw process errors."""
    if type(value) is dict:
        return {key: diagnostic_value(item, private=private or bool(re.search(
            r'password|passwd|token|secret|credential|authorization|authentication|cookie|private.?key|access.?key|api.?key|^env$|environment|config|options',
            key, re.I))) for key, item in value.items()}
    if type(value) is list: return [diagnostic_value(item, private=private) for item in value]
    if private: return '[REDACTED]'
    if type(value) is str:
        value = re.sub(r'(?i)([a-z][a-z0-9+.-]*://)[^/\s@]+@', r'\1[REDACTED]@', value)
        value = re.sub(r'(?is)((?:password|passwd|token|secret|credential|authorization|access[_-]?key|api[_-]?key)\s*[=:]\s*).*',
            r'\1[REDACTED]', value)
        value = re.sub(r'(?i)\b(Bearer|Basic)\s+\S+', r'\1 [REDACTED]', value)
    return value


class Runtime:
    def __init__(self, config, budget, root):
        self.config = config; self.source = config['source']; self.limits = config['limits']
        self.budget = budget; self.root = root; self.events = 0
        self.initial = {}; self.touched = []; self.flags = None; self.fence_attempted = False
        self.mysql = None; self.minio_stopped = False; self.last_check = 0
        self.phase = 'SOURCE_PREFLIGHT'

    def event(self, stage, **data):
        self.events += 1
        exclusive_json(self.root/('event-%04d.json' % self.events), dict(at=now(), stage=stage, **data))

    def reject(self, code, **diagnostic):
        error = FormalSnapshotError(code)
        error.diagnostic = diagnostic_value(dict(captureStage=self.phase, **diagnostic))
        try: self.event('CAPTURE_CONDITION_FAILED', failureCode=code, **error.diagnostic)
        except Exception as write_error:
            # Keep the original refusal even when diagnostic persistence fails.
            error.diagnostic['diagnosticWriteFailureCode'] = failure_code(write_error)
            print('MINIMAL_DIAGNOSTIC_WRITE_FAILED '+failure_code(write_error), file=sys.stderr)
        raise error from None

    def container_diagnostic(self, container, observed, failed, *, running=None, paused=None):
        initial = self.initial.get(container)
        fields = ('id', 'image', 'running', 'paused', 'mounts')
        expected = dict(id=container, image=None if initial is None else initial.get('image'),
            running=running, paused=paused, mounts=None if initial is None else initial.get('mounts'))
        difference = None
        if initial is not None:
            before = initial.get('mounts'); after = observed.get('mounts')
            if (type(before) is list and type(after) is list and
                    all(type(m) is dict for m in [*before, *after])):
                old = Counter(canonical_mount_records(before)); new = Counter(canonical_mount_records(after))
                difference = dict(completeRecordsEqual=old == new, outerOrderEqual=before == after,
                    outerOrderOnly=old == new and before != after,
                    removed=[json.loads(m) for m in (old-new).elements()],
                    added=[json.loads(m) for m in (new-old).elements()])
        return dict(failedConditions=failed, expected=expected,
            initial=None if initial is None else {key: initial.get(key) for key in fields},
            observed={key: observed.get(key) for key in fields}, mountDifference=difference)

    def command(self, arguments, *, cleanup=False):
        if not cleanup: self.budget.check()
        seconds = observation_timeout(self.limits['querySeconds']) if cleanup else min(self.limits['querySeconds'],
            max(.001, self.budget.deadline-time.monotonic()))
        try:
            result = subprocess.run(['docker', *arguments], stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=seconds, check=False)
        except subprocess.TimeoutExpired:
            self.reject('MINIMAL_DOCKER_TIMEOUT', failedConditions=['docker_completed_before_timeout'],
                command=arguments[0], containerId=arguments[-1] if arguments[0] in ('stop', 'start', 'inspect') else None,
                cleanup=cleanup, actualExitCode=None, exitObserved=False, errorSummary='DOCKER_TIMEOUT')
        except OSError as error:
            self.reject('MINIMAL_DOCKER_START_FAILED', failedConditions=['docker_process_started'],
                command=arguments[0], containerId=arguments[-1] if arguments[0] in ('stop', 'start', 'inspect') else None,
                cleanup=cleanup, actualExitCode=None, exitObserved=False, errno=error.errno,
                errorSummary='DOCKER_PROCESS_START_FAILED')
        summary = None
        if result.stderr:
            summary = next((label for text, label in (
                (b'no such container', 'DOCKER_CONTAINER_NOT_FOUND'),
                (b'permission denied', 'DOCKER_PERMISSION_DENIED'),
                (b'cannot connect to the docker daemon', 'DOCKER_DAEMON_UNAVAILABLE'),
                (b'is not running', 'DOCKER_CONTAINER_NOT_RUNNING')) if text in result.stderr.lower()),
                'DOCKER_STDERR_REDACTED')
        diagnostic = dict(command=arguments[0],
            containerId=arguments[-1] if arguments[0] in ('stop', 'start', 'inspect') else None,
            cleanup=cleanup, actualExitCode=result.returncode, exitObserved=True,
            stderrBytes=len(result.stderr), stdoutBytes=len(result.stdout),
            errorSummary=summary)
        failed = [name for name, passed in [('docker_exit_zero', result.returncode == 0),
            ('docker_stderr_empty', not result.stderr), ('docker_stdout_bounded', len(result.stdout) <= 8*1024*1024)] if not passed]
        if failed: self.reject('MINIMAL_DOCKER_COMMAND_FAILED', failedConditions=failed, **diagnostic)
        if arguments[0] in ('stop', 'start'):
            self.event('CONTAINER_COMMAND_EXIT', captureStage=self.phase, **diagnostic)
        return result.stdout

    def inspect(self, container, *, cleanup=False):
        from formal_normal_owner import strict_document
        template = '{"id":{{json .Id}},"running":{{json .State.Running}},"paused":{{json .State.Paused}},"image":{{json .Image}},"mounts":{{json .Mounts}}}'
        observed = strict_document(self.command(['inspect', '--format', template, '--', container],
            cleanup=cleanup), 8*1024*1024)
        if observed['id'] != container:
            self.reject('MINIMAL_CONTAINER_CHANGED', **self.container_diagnostic(
                container, observed, ['container_id_matches_requested']))
        return observed

    def preflight(self):
        require(os.name == 'posix' and sys.platform.startswith('linux') and os.geteuid() == 0,
            'MINIMAL_NATIVE_LINUX_ROOT_REQUIRED')
        require(not os.environ.get('DOCKER_HOST') or os.environ['DOCKER_HOST'] == 'unix:///var/run/docker.sock',
            'MINIMAL_LOCAL_DOCKER_REQUIRED')
        require(not os.environ.get('DOCKER_CONTEXT') and not os.environ.get('DOCKER_TLS_VERIFY'),
            'MINIMAL_LOCAL_DOCKER_REQUIRED')
        os.environ['DOCKER_HOST'] = 'unix:///var/run/docker.sock'
        directories = []
        for name, value in self.config['tools'].items():
            tool = path_checked(value)
            require(tool.is_file() and os.access(tool, os.X_OK) and tool.name == name,
                'MINIMAL_TOOL_UNAVAILABLE')
            directories.append(str(tool.parent))
        os.environ['PATH'] = os.pathsep.join([*directories, os.environ.get('PATH', '')])
        require(all(Path(shutil.which(k)).resolve() == Path(v) for k, v in self.config['tools'].items()),
            'MINIMAL_TOOL_SELECTION_CHANGED')
        source = path_checked(self.source['minioDataPath'], directory=True)
        require(source != self.root and source not in self.root.parents and self.root not in source.parents,
            'MINIMAL_SOURCE_OUTPUT_OVERLAP')
        for container in [self.source['mysqlContainerId'], self.source['minioContainerId'],
                *self.source['writerContainerIds']]:
            row = self.inspect(container)
            require(row['running'] is True and row['paused'] is False and
                row['image'] in self.source['applicationImageIds'],
                'MINIMAL_SELECTED_CONTAINER_NOT_READY')
            self.initial[container] = row
        mount = [m for m in self.initial[self.source['minioContainerId']]['mounts'] if
            m['Source'] == str(source) and m['Destination'] == self.source['minioMountDestination'] and m['RW'] is True]
        require(len(mount) == 1, 'MINIMAL_MINIO_MOUNT_CHANGED')
        # A second local container sharing this directory invalidates an offline copy.
        ids = self.command(['ps', '-aq', '--no-trunc']).decode('ascii').splitlines()
        require(len(ids) <= 1000, 'MINIMAL_CONTAINER_LIST_LIMIT')
        for container in ids:
            if container == self.source['minioContainerId']: continue
            row = self.inspect(container)
            for m in row['mounts']:
                if not m['RW']: continue
                shared = Path(m['Source'])
                require(not (row['running'] and (shared == source or shared in source.parents or
                    source in shared.parents)), 'MINIMAL_MINIO_SHARED_WRITER_REFUSED')
        self.event('SOURCE_PREFLIGHT_VERIFIED')

    def stop(self, container):
        # Journal before issuing a command: a timed-out Docker client may have stopped it.
        self.touched.append(container); self.event('STOP_REQUESTED', containerId=container)
        seconds = min(self.limits['stopSeconds'], max(1, int(self.budget.deadline-time.monotonic())-1))
        self.command(['stop', '--time', str(seconds), '--', container])
        observed = self.inspect(container)
        if observed['running'] is not False:
            self.reject('MINIMAL_CONTAINER_STOP_UNPROVEN', **self.container_diagnostic(
                container, observed, ['stopped_running_false'], running=False))

    def protected(self, *, force=False):
        self.budget.check()
        if not force and time.monotonic()-self.last_check < .5: return
        for container in self.source['writerContainerIds']:
            observed = self.inspect(container)
            state_failed = [name for name, passed in [('writer_running_false', observed['running'] is False),
                ('writer_paused_false', observed['paused'] is False),
                ('image_id_matches_initial', observed['image'] == self.initial[container]['image'])] if not passed]
            mount_error = None
            try: mounts_equal = canonical_mount_records(observed['mounts']) == canonical_mount_records(self.initial[container]['mounts'])
            except FormalSnapshotError as error:
                mount_error = error; mounts_equal = False
            failed = state_failed+([] if mounts_equal else [
                'mount_records_valid' if mount_error else 'complete_mount_records_match_initial'])
            if failed: self.reject(failure_code(mount_error) if mount_error and not state_failed else
                'MINIMAL_WRITER_RESUMED', **self.container_diagnostic(
                container, observed, failed, running=False, paused=False))
        container = self.source['minioContainerId']; observed = self.inspect(container)
        if observed['running'] is not (not self.minio_stopped):
            self.reject('MINIMAL_MINIO_STATE_CHANGED', **self.container_diagnostic(
                container, observed, ['minio_running_matches_offline_phase'], running=not self.minio_stopped))
        flags = self.mysql.query('SELECT @@server_uuid,@@global.read_only,@@global.super_read_only;').strip()
        if flags != self.source['databaseUuid']+'\t1\t1':
            values = flags.split('\t')
            self.reject('MINIMAL_DATABASE_FENCE_LOST', failedConditions=[name for index, name in enumerate(
                ('database_uuid_matches_source', 'database_read_only_one', 'database_super_read_only_one'))
                if len(values) != 3 or values[index] != [self.source['databaseUuid'], '1', '1'][index]])
        # Measure the interval after a completed observation. Slow Docker/SQL
        # checks must not make every following buffer repeat the same checks.
        self.last_check = time.monotonic()

    def restore(self):
        """Attempt all data-service restoration before reopening the writers."""
        token = observation_deadline.set(time.monotonic()+self.limits['cleanupSeconds'])
        errors = []
        def attempt(step, fn):
            self.phase = step
            try: fn(); self.event(step)
            except Exception as error:
                row = dict(step=step, failureCode=failure_code(error))
                if hasattr(error, 'diagnostic'): row['diagnostic'] = error.diagnostic
                errors.append(row)
        try:
            if self.source['minioContainerId'] in self.touched:
                attempt('MINIO_RESTORED', lambda: self.restore_container(self.source['minioContainerId']))
            if self.fence_attempted:
                def restore_flags():
                    if self.mysql.query('SELECT @@server_uuid;').strip() != self.source['databaseUuid']:
                        self.reject('MINIMAL_DATABASE_UUID_CHANGED', failedConditions=['database_uuid_matches_source'])
                    self.mysql.query('SET GLOBAL super_read_only=OFF; SET GLOBAL read_only='+self.flags[0]+
                        '; SET GLOBAL super_read_only='+self.flags[1]+';')
                    if self.mysql.query('SELECT @@server_uuid,@@global.read_only,@@global.super_read_only;').strip() != self.source['databaseUuid']+'\t'+'\t'.join(self.flags):
                        self.reject('MINIMAL_DATABASE_RESTORE_FAILED', failedConditions=['database_uuid_and_flags_restored'])
                attempt('DATABASE_FLAGS_RESTORED', restore_flags)
            if not errors:
                for container in reversed(self.source['writerContainerIds']):
                    if container in self.touched:
                        attempt('WRITER_RESTORED', lambda c=container: self.restore_container(c))
            else:
                self.event('WRITERS_RETAINED_STOPPED_AFTER_DATA_RESTORE_FAILURE')
        finally: observation_deadline.reset(token)
        result = dict(schemaVersion='minimal-capture-source-restoration/v1', at=now(),
            sourceIdentity=self.source['sourceIdentity'], restored=not errors, errors=errors,
            touchedContainerIds=self.touched)
        reference = exclusive_json(self.root/'source-restoration.json', result)
        require(not errors, 'MINIMAL_SOURCE_RESTORATION_FAILED')
        return reference

    def restore_container(self, container):
        row = self.inspect(container, cleanup=True)
        image_matches = row['image'] == self.initial[container]['image']; mount_error = None
        try: mounts_equal = canonical_mount_records(row['mounts']) == canonical_mount_records(self.initial[container]['mounts'])
        except FormalSnapshotError as error:
            mount_error = error; mounts_equal = False
        failed = ([] if image_matches else ['image_id_matches_initial'])+([] if mounts_equal else [
            'mount_records_valid' if mount_error else 'complete_mount_records_match_initial'])
        if failed: self.reject(failure_code(mount_error) if mount_error and image_matches else
            'MINIMAL_SOURCE_CONTAINER_REPLACED', **self.container_diagnostic(container, row, failed))
        if not row['running']: self.command(['start', '--', container], cleanup=True)
        row = self.inspect(container, cleanup=True)
        if row['running'] is not True:
            self.reject('MINIMAL_SOURCE_START_UNPROVEN', **self.container_diagnostic(
                container, row, ['started_running_true'], running=True))


def capture(config, request, root):
    import fcntl
    limits = config['limits']; source = config['source']; budget = Budget(root, limits)
    runtime = Runtime(config, budget, root)
    lock = path_checked(config['sourceLockPath'])
    require(lock.parent.is_dir(), 'MINIMAL_SOURCE_LOCK_PARENT_REQUIRED')
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode) and os.fstat(fd).st_nlink == 1,
            'MINIMAL_SOURCE_LOCK_INVALID')
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise FormalSnapshotError('MINIMAL_SOURCE_BUSY') from None
        token = observation_deadline.set(budget.deadline)
        try: return capture_locked(config, request, root, budget, runtime)
        finally: observation_deadline.reset(token)
    finally: os.close(fd)


def capture_locked(config, request, root, budget, runtime):
    source = config['source']; limits = config['limits']; runtime.preflight()
    originals = Originals(budget.check)
    descriptor = originals.document(source['objectSourcePin'])
    expected_parent = None if config['parent'] is None else config['parent']['objectContentIndexPin']
    require(descriptor['parentExportIndexPin'] == expected_parent, 'MINIMAL_OBJECT_PARENT_CHANGED')
    secrets = {source['passwordPin']['path'], descriptor['credentialReference']['path']}
    for reference in (source['passwordPin'], descriptor['credentialReference']):
        require(stat.S_IMODE(path_checked(reference['path']).stat().st_mode) == 0o600,
            'MINIMAL_SECRET_MODE_REQUIRED')
    password = originals.read(source['passwordPin'], 16384).decode('utf-8').removesuffix('\n')
    mysql = PrivateDockerMySql(source['mysqlContainerId'], password, timeout=limits['querySeconds'])
    data_mysql = DataMySql(source['mysqlContainerId'], password, timeout=limits['querySeconds'])
    mysql.database_log_mode = source.get('databaseLogMode', 'GTID')
    mode = mysql.query('SELECT @@global.gtid_mode;').strip()
    require(mode == ('ON' if mysql.database_log_mode == 'GTID' else 'OFF'),
        'MINIMAL_DATABASE_LOG_MODE_CHANGED')
    runtime.mysql = mysql
    require(mysql.query('SELECT @@server_uuid;').strip() == source['databaseUuid'], 'MINIMAL_DATABASE_UUID_CHANGED')
    runtime.flags = mysql.query('SELECT @@global.read_only,@@global.super_read_only;').strip().split('\t')
    require(len(runtime.flags) == 2 and all(x in ('0', '1') for x in runtime.flags), 'MINIMAL_DATABASE_FLAGS_INVALID')
    token = observation_deadline.set(budget.deadline)
    try:
        with budget.activate():
            budget.mkdir(root/'payload'); budget.mkdir(root/'recovery-materials'); budget.mkdir(root/'original-configs')
            write_record(root/'payload'/'database-log-mode.json',
                dict(mode=mysql.database_log_mode, observedGtidMode=mode))
            catalog_pin = write_record(root/'recovery-materials'/'catalog.json', dict(
                schemaVersion='minimal-capture-catalog/v1', sourceIdentity=source['sourceIdentity'],
                configurationPins=source['configurationPins'], materialPins=source['materialPins']))
            series = MinimalSeries(config, request, catalog_pin, originals, budget.check)
            semantic = MinimalSemantic(series, originals, descriptor, source)
            # All public material inputs are retained and checked before any service stop.
            material_rows = []
            config_rows = {}
            for key, label, prefix in (('configurationPins', 'role', 'original-configs'),
                    ('materialPins', 'purpose', 'recovery-materials')):
                for item in source[key]:
                    reference = item['reference']
                    require(reference['path'] not in secrets, 'MINIMAL_SECRET_AS_MATERIAL_REFUSED')
                    raw = originals.read(reference)
                    relative = prefix+'/'+item[label]+'.bin'
                    with budget.open(root/relative, 'config') as out:
                        out.write(raw); out.flush(); os.fsync(out.fileno())
                    material_rows.append(dict(archivePath=relative, sourcePin=reference, purpose=item[label]))
                    if key == 'configurationPins':
                        config_rows[item[label]] = dict(source=reference, copyPath=item[label]+'.bin',
                            copySha256=reference['sha256'], copyBytes=reference['bytes'])
            write_record(root/'original-configs'/'config-capture-stage.json', dict(
                schemaVersion='minimal-capture-configuration-stage/v1', originals=config_rows))
            material_rows.append(dict(archivePath='recovery-materials/catalog.json', sourcePin=catalog_pin,
                purpose='capture-catalog'))
            write_record(root/'recovery-materials'/'index.json', dict(
                schemaVersion='backup-capture-material-index/v1', files=material_rows))
            runtime.phase = 'CONFIGURATION_AND_IMAGE_CAPTURE'
            image_path = root/'payload'/'original-application-images.tar'
            with budget.open(image_path, 'images') as sink:
                process = subprocess.Popen(['docker', 'image', 'save', *source['applicationImageIds']],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                drain_owned_process(process, b'', sink, guard=budget.check, deadline=budget.deadline)
                sink.flush(); os.fsync(sink.fileno())
            validate_image_export(image_path, source['applicationImageIds'], budget.check)
            write_record(root/'payload'/'050-original-images.json', dict(imageIds=source['applicationImageIds'],
                archivePin=actual_pin(image_path, budget.check)))
            runtime.event('CONFIGURATION_AND_IMAGES_CAPTURED')
            primary = None; result = None
            try:
                runtime.phase = 'STOP_WRITERS'
                for container in source['writerContainerIds']: runtime.stop(container)
                runtime.fence_attempted = True
                runtime.phase = 'SET_DATABASE_READ_ONLY'
                mysql.query('SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;')
                runtime.phase = 'WRITERS_STOPPED_DATABASE_FENCE_CHECK'
                runtime.protected(force=True); runtime.event('WRITERS_STOPPED_DATABASE_FENCED')
                runtime.phase = 'SEMANTIC_CAPTURE'
                semantic.capture(mysql, source['database'], root/'semantic-capture', runtime.protected)
                def data(name):
                    return observe_data(data_mysql, source['database'], source['databaseUuid'],
                        guard=runtime.protected, scratch=root/name, max_rows=limits['dataMaxRows'],
                        max_nodes=limits['dataMaxNodes'], max_bytes=limits['dataMaxBytes'], seconds=limits['dataSeconds'])
                if request['action'] == 'FULL':
                    runtime.phase = 'SOURCE_DATA_BEFORE'
                    before = data('scratch-before')
                    write_record(root/'payload'/'011-source-data.json', before)
                runtime.phase = 'DATABASE_CAPTURE'
                series.database(mysql, source['database'], root/'payload'/'database.sql.gz', guard=runtime.protected)
                if request['action'] == 'FULL':
                    runtime.phase = 'SOURCE_DATA_AFTER'
                    after = data('scratch-after'); compare_data(before, after)
                    write_record(root/'payload'/'012-source-data-after.json', after)
                else:
                    runtime.phase = 'SOURCE_AFFECTED_DATA'
                    changed = sorted({table for segment in series.database_scope['segments']
                        for table in segment['affectedTables']})
                    # MySQL case handling must be applied to DDL identifiers too.
                    case = mysql.query('SELECT @@lower_case_table_names;').strip()
                    require(case in ('0', '1', '2'), 'MINIMAL_DATABASE_CASE_INVALID')
                    observed = observe_affected_data(data_mysql, source['database'], source['databaseUuid'],
                        affected_tables=changed, lower_case_table_names=int(case), guard=runtime.protected, scratch=root/'scratch-affected',
                        max_rows=limits['dataMaxRows'], max_nodes=limits['dataMaxNodes'],
                        max_bytes=limits['dataMaxBytes'], seconds=limits['dataSeconds'])
                    write_record(root/'payload'/'source-affected-data.json', observed)
                    series.database_delta.update(dataObservation='AFFECTED_TABLES_V1', lowerCaseTableNames=int(case))
                runtime.phase = 'MINIO_OFFLINE_PRECHECK'
                runtime.protected(force=True)
                runtime.phase = 'MINIO_STOP'
                runtime.stop(source['minioContainerId']); runtime.minio_stopped = True
                runtime.phase = 'MINIO_PHYSICAL_CAPTURE'
                series.files(source['minioDataPath'], root/'payload'/'minio-physical', guard=runtime.protected,
                    scopes=source.get('minioPhysicalScopes'))
                runtime.protected(force=True)
                runtime.phase = 'MINIO_START'
                runtime.command(['start', '--', source['minioContainerId']]); runtime.minio_stopped = False
                runtime.phase = 'MINIO_READINESS'
                wait_ready(semantic, runtime)
                runtime.phase = 'OBJECT_RECHECK'
                verify_objects_after_offline(semantic, runtime)
                runtime.phase = 'DATABASE_POINT_RECHECK'
                require(observe_position(mysql, runtime.protected) == series.end,
                    'MINIMAL_DATABASE_POINT_CHANGED')
                point = series.point(source_restored=False)
                write_record(root/'payload'/'capture-content-point.json', point)
                write_record(root/'payload'/'capture-file-inventory.json', series.file_inventory)
                runtime.phase = 'SEMANTIC_FINALIZE'
                supplement, _ = semantic.finalize(point, runtime.protected)
                runtime.phase = 'CAPTURE_FINAL_CHECK'
                originals.check(full=True); runtime.protected(force=True)
                entries = archive_entries(root, budget.check)
                inputs = capture_recovery_inputs(point, source_root=str(root), entries=entries, supplemental=supplement)
                inputs_pin = write_record(root/'capture-recovery-inputs.json', inputs)
                entries['capture-recovery-inputs.json'] = marker(inputs_pin)
                entries_pin = write_record(root/'capture-archive-entries.json', entries)
                result = dict(captureRoot=str(root), captureInputsPin=inputs_pin, archiveEntriesPin=entries_pin,
                    capturePointPin=actual_pin(root/'payload'/'capture-content-point.json'),
                    objectContentIndexPin=actual_pin(root/'semantic-capture'/'object-content-index.json'),
                    recoveryPoint=point['commonRecoveryPoint'], sourceIdentity=source['sourceIdentity'])
            except BaseException as error:
                error.diagnostic = diagnostic_value(dict(
                    getattr(error, 'diagnostic', None) or {}, captureStage=runtime.phase))
                primary = error
            try:
                restored = runtime.restore()
            except Exception as error:
                runtime.event('CAPTURE_OR_RESTORATION_FAILED', captureFailureCode=None if primary is None else failure_code(primary),
                    restorationFailureCode=failure_code(error),
                    captureDiagnostic=None if primary is None else getattr(primary, 'diagnostic', None))
                raise
            if primary is not None: raise primary
            result['sourceRestorationPin'] = restored
            runtime.event('CAPTURE_MATERIAL_COMPLETE_SOURCE_RESTORED')
            return result
    finally: observation_deadline.reset(token)


def marker(reference): return 'file|'+str(reference['bytes'])+'|'+reference['sha256']


def archive_entries(root, guard):
    entries = {}
    for name in ('payload', 'semantic-capture', 'recovery-materials', 'original-configs'):
        entries[name] = 'directory'
        for relative, row in scan_files(root/name, guard=guard).items():
            entries[name+'/'+relative] = 'directory' if row['kind'] == 'directory' else marker(row)
    return entries


def validate_image_export(path, expected, guard):
    """Read exported image configs and bind their actual digest to immutable IDs."""
    from formal_normal_owner import strict_document
    with tarfile.open(path, 'r:') as archive:
        manifest = archive.getmember('manifest.json')
        require(manifest.isfile() and 0 < manifest.size <= 1048576, 'MINIMAL_IMAGE_EXPORT_INVALID')
        rows = strict_document(archive.extractfile(manifest).read(), 1048576)
        observed = set()
        for row in rows:
            guard(); member = archive.getmember(row['Config'])
            require(member.isfile() and 0 < member.size <= 16*1024*1024, 'MINIMAL_IMAGE_EXPORT_INVALID')
            observed.add('sha256:'+hashlib.sha256(archive.extractfile(member).read()).hexdigest())
        require(observed == set(expected), 'MINIMAL_IMAGE_EXPORT_CHANGED')


def wait_ready(semantic, runtime):
    # A finite explicit readiness wait is not a fallback or a capture retry.
    import http.client
    import urllib.parse
    endpoint = urllib.parse.urlsplit(semantic.source['endpoint'])
    end = min(runtime.budget.deadline, time.monotonic()+runtime.limits['readySeconds'])
    while True:
        runtime.protected(force=True)
        require(time.monotonic() < end, 'MINIMAL_MINIO_READINESS_TIMEOUT')
        connection_type = http.client.HTTPSConnection if endpoint.scheme == 'https' else http.client.HTTPConnection
        connection = connection_type(endpoint.hostname, endpoint.port, timeout=min(2, end-time.monotonic()))
        try:
            connection.request('GET', '/minio/health/ready')
            response = connection.getresponse(); status = response.status
            require(len(response.read(4097)) <= 4096, 'MINIMAL_MINIO_HEALTH_INVALID')
            require(status in (200, 503), 'MINIMAL_MINIO_HEALTH_FAILED')
            if status == 200:
                semantic.client.timeout = min(30, max(.01, runtime.budget.deadline-time.monotonic()))
                return
            runtime.event('MINIO_NOT_READY', status=status)
        except (OSError, http.client.HTTPException):
            runtime.event('MINIO_NOT_READY', failureCode='MINIMAL_MINIO_HEALTH_CONNECTION_UNAVAILABLE')
        finally: connection.close()
        time.sleep(min(.5, max(.001, end-time.monotonic())))


def verify_objects_after_offline(semantic, runtime):
    guard = runtime.protected
    semantic.verify_endpoint(guard)
    for bucket in semantic.source['buckets']:
        expected = [r for r in semantic.records if r['bucket'] == bucket]
        plain = [{k: v for k, v in r.items() if k not in ('bucket', 'sha256', 'repositoryPath', 'headers')}
            for r in expected]
        require(export_listing(semantic.client, bucket, guard) == plain, 'MINIMAL_OBJECT_OFFLINE_POINT_CHANGED')
        _require_empty_multipart_observation(semantic.client.multipart_empty(bucket), bucket)
        for row in expected:
            if row['kind'] == 'version':
                observed = semantic._read_content(bucket, row, guard)
                require(observed == (row['sha256'], row['size'], row['headers']),
                    'MINIMAL_OBJECT_OFFLINE_POINT_CHANGED')
        require(export_listing(semantic.client, bucket, guard) == plain, 'MINIMAL_OBJECT_OFFLINE_POINT_CHANGED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', required=True); parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(); root = None
    try:
        config, _ = document(args.configuration); request, _ = document(args.request)
        root = validate_job(config, request)
        require(os.name == 'posix' and sys.platform.startswith('linux'), 'MINIMAL_NATIVE_LINUX_ROOT_REQUIRED')
        require(root.is_dir() and not (root/'worker-completion.json').exists() and
            Path(args.output) == root/'worker-completion.json', 'MINIMAL_WORKER_ROOT_INVALID')
        data = capture(config, request, root)
        exclusive_json(args.output, dict(schemaVersion='minimal-capture-worker-completion/v1',
            operationId=request['operationId'], data=data, finishedAt=now()))
        return 0
    except (Exception, KeyboardInterrupt) as error:
        if root is not None and root.is_dir():
            exclusive_json(root/'worker-failure.json', dict(at=now(), failureCode=failure_code(error),
                diagnostic=getattr(error, 'diagnostic', None)))
        print(failure_code(error), file=sys.stderr)
        return 1


if __name__ == '__main__': sys.exit(main())
