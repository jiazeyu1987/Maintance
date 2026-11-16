"""Reviewed safe-engine fixes applied to the authenticated frozen baseline.

Patch contexts fail closed. The stored baseline stays intact; only the reviewed
transforms alter delivered behavior. Timing also compares the original AST.
"""
from pathlib import Path
import ast
import hashlib

from standard_timing import backup_timings, restore_timings


def application_database_phase(payload):
    """Application writers are expected after start; identity and scope remain fixed."""
    name = 'common/recovery_minimal_runtime.py'
    source = payload[name].decode('utf-8').replace('\r\n', '\n')
    before = "        (sql.import_database_state if importing else sql.database_state)(self.mysql, self.db_target)\n"
    after = """        if self.running_applications:
            sql.import_database_state(self.mysql, self.db_target)
            databases = self.mysql.query('SHOW DATABASES;').splitlines()
            require(len(databases) == len(set(databases)) and
                    set(databases) == sql.SYSTEM_DATABASES | {self.db_target['database']},
                    'FORMAL_SQL_DATABASE_SCOPE_INVALID')
        else:
            (sql.import_database_state if importing else sql.database_state)(self.mysql, self.db_target)
"""
    if source.count(before) != 1:
        raise ValueError('STANDARD_APPLICATION_DATABASE_PHASE_CONTEXT_CHANGED')
    payload[name] = source.replace(before, after).encode('utf-8')


def incremental_sql_stream(payload, root):
    """Replace only the frozen SQL marker read, retaining safe digest gates."""
    name = 'common/recovery_data.py'
    source = payload[name].decode('utf-8').replace('\r\n', '\n')
    changes = (
        ('        raw = expanded.read_bytes()\n', ''),
        ("        require(raw.startswith(b'-- IntRuoyi binlog incremental;'), 'CAPTURED_BINLOG_SQL_REQUIRED')\n", ''),
        ("""        require(mode in ('GTID', 'FILE_POSITION'), 'CAPTURED_BINLOG_LOG_MODE_INVALID')
        if mode == 'GTID':
            require(not delta['segments'] or b'BINLOG ' in raw or
                    re.search(rb"SET @@SESSION\\.GTID_NEXT\\s*=\\s*'[0-9a-fA-F-]+:[0-9]+'", raw),
                    'CAPTURED_BINLOG_SQL_REQUIRED')
""", """        from recovery_sql_stream import inspect_incremental_sql
        with self.timed_stage('sql-inspect'):
            inspect_incremental_sql(expanded, mode=mode, has_segments=bool(delta['segments']),
                guard=self.guard, seconds=self.seconds())
"""),
    )
    for before, after in changes:
        if source.count(before) != 1:
            raise ValueError('STANDARD_SQL_STREAM_CONTEXT_CHANGED ' + name)
        source = source.replace(before, after)
    payload[name] = source.encode('utf-8')
    payload['common/recovery_sql_stream.py'] = (root/'ops/recovery/recovery_sql_stream.py').read_bytes()


def native_invocation_transports(payload, root):
    """Share only authenticated native transports, preserving SAFE readers."""
    name = 'common/recovery_data.py'
    frozen = payload[name].decode('utf-8').replace('\r\n', '\n')
    current = (root/'ops/recovery/recovery_data.py').read_text(encoding='utf-8').replace('\r\n', '\n')

    def method(source, method_name):
        owners = [item for item in ast.parse(source).body
                  if isinstance(item, ast.ClassDef) and item.name == 'NativeData']
        if len(owners) != 1:
            raise ValueError('STANDARD_NATIVE_TRANSPORT_OWNER_CHANGED')
        methods = [item for item in owners[0].body
                   if isinstance(item, ast.FunctionDef) and item.name == method_name]
        if len(methods) != 1 or methods[0].decorator_list:
            raise ValueError('STANDARD_NATIVE_TRANSPORT_BOUNDARY_CHANGED ' + method_name)
        item = methods[0]
        return ''.join(source.splitlines(keepends=True)[item.lineno-1:item.end_lineno])

    for method_name, expected in {
        'command': 'e92e7e09641a2c2b4684d92fcbf827d7a706ed76ff1d031d6cf4b68736643937',
        'import_sql': '2e2a2be52c4c43b22deae57b3040e597e0dcc5597e6a51f99e4f6573fe7f9636',
    }.items():
        before = method(frozen, method_name)
        if hashlib.sha256(before.encode('utf-8')).hexdigest() != expected or frozen.count(before) != 1:
            raise ValueError('STANDARD_NATIVE_TRANSPORT_BASELINE_CHANGED ' + method_name)
        frozen = frozen.replace(before, method(current, method_name))
    payload[name] = frozen.encode('utf-8')


def incremental_chain_admission(payload, root):
    """Share only the admission policy; keep all frozen SAFE archive checks."""
    name = 'common/repository_records.py'
    frozen = payload[name].decode('utf-8').replace('\r\n', '\n')
    if hashlib.sha256(frozen.encode('utf-8')).hexdigest() != \
            'f192fe6222b295c59844ed375776dc2f7bdafce3bf1b625c5b08053f64c032af':
        raise ValueError('STANDARD_CHAIN_POLICY_BASELINE_CHANGED')
    current = (root/'ops/recovery/repository_records.py').read_text(encoding='utf-8')
    functions = []
    for function in ('incremental_chain_policy', 'incremental_chain_admission'):
        matches = [node for node in ast.parse(current).body if
                   isinstance(node, ast.FunctionDef) and node.name == function]
        if len(matches) != 1 or matches[0].decorator_list:
            raise ValueError('STANDARD_CHAIN_POLICY_SOURCE_CHANGED ' + function)
        node = matches[0]
        functions.append(''.join(current.splitlines(keepends=True)[node.lineno-1:node.end_lineno]))
    anchor = 'def utc():\n'
    if frozen.count(anchor) != 1:
        raise ValueError('STANDARD_CHAIN_POLICY_BOUNDARY_CHANGED')
    payload[name] = frozen.replace(anchor, '\n\n'.join(functions) + '\n\n\n' + anchor).encode('utf-8')


def program_restore_handoff(payload, root):
    """Add typed execution custody to SAFE without replacing its data checks."""
    name = 'common/recovery_minimal_runtime.py'
    frozen = payload[name].decode('utf-8').replace('\r\n', '\n')
    current = (root/'ops/recovery/recovery_minimal_runtime.py').read_text(encoding='utf-8')

    def function(source):
        matches = [node for node in ast.parse(source).body
                   if isinstance(node, ast.FunctionDef) and node.name == 'execute_empty']
        if len(matches) != 1 or matches[0].decorator_list:
            raise ValueError('STANDARD_PROGRAM_EXECUTE_BOUNDARY_CHANGED')
        node = matches[0]
        return ''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno])

    before = function(frozen)
    if hashlib.sha256(before.encode('utf-8')).hexdigest() != \
            '3ac5948b84441c74619509a7699e830b7acb89bcef99a4f39b963120c501c51a':
        raise ValueError('STANDARD_PROGRAM_EXECUTE_BASELINE_CHANGED')
    source = function(current)

    def fragment(start, end):
        if source.count(start) != 1 or source.count(end) != 1:
            raise ValueError('STANDARD_PROGRAM_HANDOFF_SOURCE_CHANGED')
        first, last = source.index(start), source.index(end)
        if first >= last:
            raise ValueError('STANDARD_PROGRAM_HANDOFF_ORDER_CHANGED')
        return source[first:last]

    target_checks = "    try:\n        with step_timing(root, 'target-checks'):\n"
    changes = (
        ('def execute_empty(configuration, request, root, input_pins, *, reservation_configuration=None):\n',
         fragment('def execute_empty(', "    with step_timing(root, 'restore-admission'):\n")),
        ("        admit(configuration, request, root, 'target', reservation_configuration=reservation_configuration)\n",
         fragment('        execution = {}\n', "        reservation = absolute(target['dataRoot'])/")),
        ('        native = MinimalData(configuration, request, source, policy, chain, target, root, input_pins)\n',
         fragment('        constructor = {}', '    try:\n        if native_context is not None:')),
        (target_checks, '    try:\n' + fragment('        if native_context is not None:\n            # Construction',
             "        with native.timed_stage('target-quiesce'):\n") +
             "        with step_timing(root, 'target-checks'):\n"),
        ("            cleanup_pin = pin(cleanup(root, restore_paths(root), request['operationId'], guard=native.guard))\n",
         fragment('            if native_context is not None:\n                from recovery_program_sql_staging',
                  '            cleanup_pin = pin(cleanup(root') +
         "            cleanup_pin = pin(cleanup(root, restore_paths(root), request['operationId'], guard=native.guard))\n"),
        ('    finally:\n        native.archive_guard.close()\n',
         '    finally:\n        # MAIN retains this lease through protection release in its caller.\n'
         '        if native_context is None:\n            native.archive_guard.close()\n'),
    )
    after = before
    for old, new in changes:
        if after.count(old) != 1:
            raise ValueError('STANDARD_PROGRAM_HANDOFF_SITE_CHANGED')
        after = after.replace(old, new)
    if frozen.count(before) != 1:
        raise ValueError('STANDARD_PROGRAM_EXECUTE_BOUNDARY_CHANGED')
    # The original SAFE fresh-target checks, archive verification, strict
    # cleanup and exception handling remain byte-for-byte outside these sites.
    updated = frozen.replace(before, after)
    compile(updated, name, 'exec')
    payload[name] = updated.encode('utf-8')


def program_worker_handoff(payload, root):
    """Share the result handoff while retaining the SAFE success contract."""
    name = 'common/recovery_minimal_worker.py'
    frozen = payload[name].decode('utf-8').replace('\r\n', '\n')
    if hashlib.sha256(frozen.encode('utf-8')).hexdigest() != \
            'e4461e9b9abcb88566d1b9bfae2564c96d4b1397b7368a7a89870d24dc74e14b':
        raise ValueError('STANDARD_PROGRAM_WORKER_BASELINE_CHANGED')
    current = (root/'ops/recovery/recovery_minimal_worker.py').read_text(encoding='utf-8')

    def declaration(source, name):
        matches = [node for node in ast.parse(source).body if
            isinstance(node, ast.FunctionDef) and node.name == name or
            isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and
                target.id == name for target in node.targets)]
        if len(matches) != 1:
            raise ValueError('STANDARD_PROGRAM_WORKER_DECLARATION_CHANGED ' + name)
        node = matches[0]
        return ''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno])

    original_result = declaration(frozen, 'operation_result')
    original_main = declaration(frozen, 'main')
    frozen = frozen.replace(original_main, declaration(current, 'main'))
    frozen = frozen.replace('import argparse\n', 'import argparse\nfrom copy import deepcopy\n')
    frozen = frozen.replace(original_result, declaration(current, 'PROGRAM_FAILURE_FIELDS') + '\n\n' + original_result)
    if declaration(frozen, 'operation_result') != original_result:
        raise ValueError('STANDARD_PROGRAM_WORKER_SUCCESS_CONTRACT_CHANGED')
    compile(frozen, name, 'exec')
    payload[name] = frozen.encode('utf-8')


def _preservation_declaration(source, owner, name):
    """Select one reviewed AST boundary, never a textual best match."""
    body = ast.parse(source).body
    if owner is not None:
        classes = [item for item in body if isinstance(item, ast.ClassDef) and item.name == owner]
        if len(classes) != 1:
            raise ValueError('STANDARD_PRESERVATION_OWNER_CHANGED ' + owner)
        body = classes[0].body
    nodes = [item for item in body if isinstance(item, (ast.FunctionDef, ast.ClassDef)) and item.name == name]
    if len(nodes) != 1:
        raise ValueError('STANDARD_PRESERVATION_BOUNDARY_CHANGED ' + name)
    node = nodes[0]
    return ''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno])


def _preservation_method(payload, member, owner, name, expected, replacement):
    text = payload[member].decode('utf-8').replace('\r\n', '\n')
    original = _preservation_declaration(text, owner, name)
    if hashlib.sha256(original.encode()).hexdigest() != expected or text.count(original) != 1:
        raise ValueError('STANDARD_PRESERVATION_BASELINE_CHANGED ' + member + ':' + name)
    updated = text.replace(original, replacement)
    compile(updated, member, 'exec')
    payload[member] = updated.encode('utf-8')


def target_preservation_capture(payload, root):
    """Bind MAIN to SAFE while preserving its authenticated SOURCE algorithms."""
    def current(path):
        return (root/path).read_text(encoding='utf-8').replace('\r\n', '\n')

    # Only these reviewed observer boundaries are shared. In particular the
    # SAFE content reader, capture/finalize and parent verifier stay in place.
    snapshot = current('ops/backup_engine/formal/formal_snapshot_linux.py')
    member = 'formal/formal_snapshot_linux.py'
    for name, expected in {
        '__init__': '284357ba908e417154dbb1081e7e61bb0c4778315d75e4b2cd7cdc38398b82ce',
        'query': '4c51e60b56610c3e1a8187911d757d5840389210a91b5831d709bfeaa27675d8',
        '_dump_current': 'b0f1b0b3dbca081e9d3e620355273f9ff86621eb4b2f4ffc98b0e2920a2003ac',
    }.items():
        replacement = _preservation_declaration(snapshot, 'PrivateDockerMySql', name)
        if name == '_dump_current':
            # Keep the authenticated SAFE compression policy. This transform
            # adds client ownership, not the source tree's timing policy.
            if replacement.count(',mtime=0,compresslevel=1)') != 1:
                raise ValueError('STANDARD_PRESERVATION_DUMP_POLICY_CHANGED')
            replacement = replacement.replace(',mtime=0,compresslevel=1)', ',mtime=0)')
        _preservation_method(payload, member, 'PrivateDockerMySql', name, expected, replacement)
    payload[member] += ('\n\n' + _preservation_declaration(snapshot, None, '_drain_observed_process') + '\n').encode()

    semantics = current('ops/backup_engine/formal/formal_capture_semantics.py')
    for owner, name, expected in (
        ('SemanticCapture', 'verify_endpoint', '7b591ab228449f558e8321d0460136cdf3782e5b01a7a9688c909dbb803dc3c1'),
        (None, 'bounded_reference_query', 'ccd39f0b336df4f6e3c6db8abd870da3aa8abc76ef9681b0bd984120f06fcdd0'),
    ):
        _preservation_method(payload, 'formal/formal_capture_semantics.py', owner, name, expected,
            _preservation_declaration(semantics, owner, name))

    # MAIN owns the endpoint subprocess observer through its typed session.
    # Retain the complete SAFE offline listing/content verifier; SOURCE keeps
    # the original endpoint call when no observer was explicitly supplied.
    member = 'formal/minimal_capture_worker.py'
    offline = _preservation_declaration(payload[member].decode('utf-8').replace('\r\n', '\n'),
        None, 'verify_objects_after_offline')
    changes = (
        ('def verify_objects_after_offline(semantic, runtime):',
         'def verify_objects_after_offline(semantic, runtime, *, process_observer=None):'),
        ('    semantic.verify_endpoint(guard)\n',
         '    if process_observer is None:\n'
         '        semantic.verify_endpoint(guard)\n'
         '    else:\n'
         '        semantic.verify_endpoint(guard, process_observer=process_observer)\n'),
    )
    replacement = offline
    for before, after in changes:
        if replacement.count(before) != 1:
            raise ValueError('STANDARD_PRESERVATION_OFFLINE_CONTEXT_CHANGED')
        replacement = replacement.replace(before, after)
    _preservation_method(payload, member, None, 'verify_objects_after_offline',
        'f923288d37c422db7ee7443ee00603a2b5eb01bf528834fb5dbf8cc6e2da9091', replacement)

    member = 'formal/minimal_capture_support.py'
    support = payload[member].decode('utf-8').replace('\r\n', '\n')
    original_semantic = _preservation_declaration(support, None, 'MinimalSemantic')
    if hashlib.sha256(original_semantic.encode()).hexdigest() != \
            '8ec1628a9895df0de597c386815bf687e317288b562fced8023f99413d544fc6':
        raise ValueError('STANDARD_PRESERVATION_SEMANTIC_BASELINE_CHANGED')
    original_job = _preservation_declaration(support, None, 'validate_job')
    if hashlib.sha256(original_job.encode()).hexdigest() != \
            '7e89c50e294bf6e992b36a65e4f7af50885a9e4d4ce1a7ee87d3f4b1db08a5b1':
        raise ValueError('STANDARD_PRESERVATION_CONFIGURATION_BASELINE_CHANGED')
    shared_support = current('ops/recovery/minimal_capture_support.py')
    declarations = [_preservation_declaration(shared_support, None, name) for name in
        ('_configuration_header', '_configuration_values', '_configuration_paths', 'validate_config',
         'validate_main_target_config')]
    # The ordinary validate_job remains byte-for-byte, including its order and
    # request/parent contract. MAIN uses the separate registered config entry.
    support += '\n\n' + '\n\n'.join(declarations) + '\n'
    changes = (
        ('    def __init__(self, series, originals, descriptor, source_config):',
         '    def __init__(self, series, originals, descriptor, source_config, *, process_observer=None):'),
        ('            self._initialize(series, originals, descriptor, source_config)',
         '            self._initialize(series, originals, descriptor, source_config, process_observer=process_observer)'),
        ('    def _initialize(self, series, originals, descriptor, source_config):',
         '    def _initialize(self, series, originals, descriptor, source_config, *, process_observer=None):'),
        ('        self.source_config = source_config\n',
         '        self.source_config = source_config\n        self.process_observer = process_observer\n'),
        ('            self.redis_snapshot = observe(source_config_redis(self.source_config), guard)',
         '            self.redis_snapshot = (observe(source_config_redis(self.source_config), guard)\n'
         '                if self.process_observer is None else observe(source_config_redis(self.source_config), guard,\n'
         '                    process_observer=self.process_observer))'),
        ('            verify_current(self.redis_snapshot, source_config_redis(self.source_config), guard)',
         '            if self.process_observer is None:\n'
         '                verify_current(self.redis_snapshot, source_config_redis(self.source_config), guard)\n'
         '            else:\n'
         '                verify_current(self.redis_snapshot, source_config_redis(self.source_config), guard,\n'
         '                    process_observer=self.process_observer)'),
    )
    for before, after in changes:
        if support.count(before) != 1:
            raise ValueError('STANDARD_PRESERVATION_SEMANTIC_CONTEXT_CHANGED')
        support = support.replace(before, after)
    if _preservation_declaration(support, None, 'validate_job') != original_job:
        raise ValueError('STANDARD_PRESERVATION_SOURCE_ADMISSION_CHANGED')
    payload[member] = support.encode()

    # Keep the SAFE password/mode/encoding checks; add only the actual inspect
    # observer and pass it through the existing Redis algorithms.
    member = 'formal/minimal_redis_snapshot.py'
    redis = payload[member].decode('utf-8').replace('\r\n', '\n')
    before = _preservation_declaration(redis, None, 'source_client')
    if hashlib.sha256(before.encode()).hexdigest() != \
            '0eff5081351f61abb27d2fabd11d2b3273b1ed59442a899ce81cfc6b995ccee1':
        raise ValueError('STANDARD_PRESERVATION_REDIS_BASELINE_CHANGED')
    after = before.replace('def source_client(config, guard):',
        'def source_client(config, guard, *, process_observer=None):')
    old = "    row=json.loads(subprocess.check_output(['docker','inspect',config['containerId']],timeout=10))[0]"
    new = """    if process_observer is None:
        raw=subprocess.check_output(['docker','inspect',config['containerId']],timeout=10)
    else:
        from formal_schema_evidence import _bounded_process
        raw=_bounded_process(['docker','inspect',config['containerId']],b'',8*1024*1024,10,
            process_observer=process_observer)
    row=json.loads(raw)[0]"""
    if after.count(old) != 1:
        raise ValueError('STANDARD_PRESERVATION_REDIS_CONTEXT_CHANGED')
    redis = redis.replace(before, after.replace(old, new))
    payload[member] = redis.encode()
    redis_current = current('ops/backup_engine/formal/minimal_redis_snapshot.py')
    for name, expected in {
        'observe': 'b0d13a03be4e4f4b63683e88f888232240092e7dcea59c1fefde2e9f2221a9be',
        'verify_current': '0d156a80535bd84bbfc3463b5b825835c71b2289f2658a5a31fb68df667b7321',
    }.items():
        _preservation_method(payload, member, None, name, expected,
            _preservation_declaration(redis_current, None, name))

    core = current('ops/recovery/recovery_capture_materials.py')
    core = core.replace(_preservation_declaration(core, 'SourceCaptureLifecycle', '_capture_database'),
        """    def _capture_database(self,prepared):
        self.worker.capture_database(prepared.config,prepared.identity,prepared.root,self.runtime,
            prepared.series,prepared.mysql,prepared.data_mysql)
""")
    core = core.replace(_preservation_declaration(core, 'SourceCaptureLifecycle', '_save_images'),
        """    def _save_images(self,path,images,budget):
        from minimal_image_export import capture_images
        import time
        image_started=time.monotonic();image_pin={}
        reused=capture_images(self.runtime.config,path,budget,self.worker.validate_image_export,result=image_pin)
        self.runtime.event('IMAGE_EXPORT_COMPLETE',reused=reused,
            elapsedSeconds=round(time.monotonic()-image_started,3))
        return image_pin
""")
    core = core.replace(_preservation_declaration(core, 'SourceCaptureLifecycle', '_verify_parent'),
        '    def _verify_parent(self,semantic):\n        semantic.verify_parent()\n')
    payload['common/recovery_capture_materials.py'] = core.encode()
    for name in ('recovery_target_capture', 'recovery_target_preservation', 'recovery_preservation_source',
                 'recovery_restore_inputs', 'recovery_preservation_inputs'):
        payload['common/' + name + '.py'] = (root/'ops/recovery'/(''+name+'.py')).read_bytes()

    # STANDARD's authenticated repository APIs always verify content. Adapt
    # only the new preservation caller; keep those strict callees unchanged.
    member = 'common/recovery_target_preservation.py'
    preservation = payload[member].decode('utf-8').replace('\r\n', '\n')
    for before, after, expected_count in (
        ('publisher.stream(self.archive,tree,verify_content=True)',
         'publisher.stream(self.archive,tree)', 1),
        ('reader.verify(str(self.archive),tree,material,payload_content=True)',
         'reader.verify(str(self.archive),tree,material)', 1),
        ('binder.assemble_repository_capture_records,verify_content=True)',
         'binder.assemble_repository_capture_records)', 2),
        (',verify_metadata=True)', ')', 2),
    ):
        if preservation.count(before) != expected_count:
            raise ValueError('STANDARD_PRESERVATION_PUBLICATION_API_CHANGED')
        preservation = preservation.replace(before, after)
    compile(preservation, member, 'exec')
    payload[member] = preservation.encode('utf-8')

    member = 'formal/minimal_capture_worker.py'
    original = _preservation_declaration(payload[member].decode('utf-8').replace('\r\n', '\n'), None, 'capture_locked')
    # Its restoration/parent cleanup tail is retained exactly; only the shared
    # material owner replaces the old inline SOURCE material algorithm.
    replacement = '''def capture_locked(config, request, root, budget, runtime):
    from recovery_capture_materials import (SourceCaptureLifecycle, prepare_materials,
        capture_protected_materials)
    source = config['source']; runtime.preflight()
    originals = Originals(budget.check)
    lifecycle = None
    token = observation_deadline.set(budget.deadline)
    try:
        with budget.activate():
            lifecycle = SourceCaptureLifecycle(runtime)
            prepared = prepare_materials(config, request, root, output_budget=budget,
                originals=originals, transport=lifecycle)
            mysql = prepared.mysql; semantic = prepared.semantic
            primary = None; result = None
            try:
                runtime.phase = 'STOP_WRITERS'
                for container in source['writerContainerIds']: runtime.stop(container)
                runtime.fence_attempted = True
                runtime.phase = 'SET_DATABASE_READ_ONLY'
                mysql.query('SET GLOBAL read_only=ON; SET GLOBAL super_read_only=ON;')
                runtime.phase = 'WRITERS_STOPPED_DATABASE_FENCE_CHECK'
                runtime.protected(force=True); runtime.event('WRITERS_STOPPED_DATABASE_FENCED')
                result = capture_protected_materials(prepared, lifecycle).result
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
            semantic.verify_parent()
            runtime.event('CAPTURE_MATERIAL_COMPLETE_SOURCE_RESTORED')
            return result
    finally:
        semantic = None if lifecycle is None else lifecycle.semantic
'''
    tail = original[original.index('        import sys\n'):]
    replacement += tail
    _preservation_method(payload, member, None, 'capture_locked',
        '3b749f4163b64a0d2663ce11c2066e4d9d0927335e6983e8da41b5f1892acc7f', replacement)

    member = 'common/recovery_minimal_runtime.py'
    runtime = payload[member].decode('utf-8').replace('\r\n', '\n')
    selected = current('ops/recovery/recovery_minimal_runtime.py')
    helper = _preservation_declaration(selected, None, '_require_main_capability')
    anchor = 'MinimalData = guarded_type(MinimalData)\n'
    if runtime.count(anchor) != 1:
        raise ValueError('STANDARD_PRESERVATION_RUNTIME_BOUNDARY_CHANGED')
    runtime = runtime.replace(anchor, anchor + '\nsupports_main_target_preservation = True\n\n' + helper + '\n')
    for function in ('execute', 'execute_empty'):
        method = _preservation_declaration(runtime, None, function)
        lines = method.splitlines(keepends=True)
        signature_end = next(index for index, line in enumerate(lines) if line.rstrip().endswith(':'))
        gate = '    _require_main_capability(configuration, request)\n'
        if function == 'execute_empty':
            # The existing typed signature fragment already carries the
            # source admission line; require it instead of inserting twice.
            if lines[signature_end+1] != gate or method.count(gate) != 1:
                raise ValueError('STANDARD_PRESERVATION_EMPTY_ADMISSION_CHANGED')
        else:
            if gate in method:
                raise ValueError('STANDARD_PRESERVATION_EXECUTE_ADMISSION_CHANGED')
            lines.insert(signature_end+1, gate)
        runtime = runtime.replace(method, ''.join(lines))
    payload[member] = runtime.encode()


def target_preservation_repository(payload, root):
    """Add explicit MAIN readback/holds without replacing ordinary SAFE readers."""
    member = 'common/repository_native_readback.py'
    text = payload[member].decode('utf-8').replace('\r\n', '\n')
    imports = ('from repository_records import (absolute, document, exact, pin_file, read_pin,\n'
               '                                require, safe_path, write_new)\n')
    if text.count(imports) != 1:
        raise ValueError('STANDARD_PRESERVATION_READBACK_IMPORTS_CHANGED')
    text = text.replace(imports,
        'from repository_records import (absolute, canonical, document, exact, pin_file, read_pin,\n'
        '                                require, safe_path, validate_pin, write_new)\n')
    original = _preservation_declaration(text, 'SmbReadback', 'verify')
    if hashlib.sha256(original.encode()).hexdigest() != \
            '6fe357635400bf0a1336fcd78eef11e32ccd4030c3b32805f98d7055be089d17':
        raise ValueError('STANDARD_PRESERVATION_READBACK_BASELINE_CHANGED')
    before = "original_records_pin = write_new(self.records / 'readback-originals.json',"
    if original.count(before) != 1:
        raise ValueError('STANDARD_PRESERVATION_READBACK_CONTEXT_CHANGED')
    text = text.replace(original, original.replace(before, 'original_records_pin = self._write_original_records('))
    current = (root/'ops/recovery/repository_native_readback.py').read_text(encoding='utf-8')
    hook = _preservation_declaration(current, 'SmbReadback', '_write_original_records')
    anchor = 'class SmbReadback:\n'
    if text.count(anchor) != 1:
        raise ValueError('STANDARD_PRESERVATION_READBACK_OWNER_CHANGED')
    text = text.replace(anchor, anchor + hook + '\n')
    for name in ('_private_record', 'read_verified', 'PreservationReadback'):
        value = _preservation_declaration(current, None, name)
        if name == 'PreservationReadback':
            # SAFE's original constructor already mandates authentication and
            # strict environment checks; it has no LIGHT verification switch.
            old = 'super().__init__(configuration, deadline, verify_environment=True)'
            if value.count(old) != 1:
                raise ValueError('STANDARD_PRESERVATION_READBACK_SUPER_CHANGED')
            value = value.replace(old, 'super().__init__(configuration, deadline)')
        text += '\n\n' + value + '\n'
    payload[member] = text.encode()
    member = 'common/repository_minimal.py'
    text = payload[member].decode('utf-8').replace('\r\n', '\n')
    original = _preservation_declaration(text, None, 'publish')
    if hashlib.sha256(original.encode()).hexdigest() != \
            '79d6d40d4fd27f184846e0850d3bc4a66f75b52326483dcd2026d880a9b513bc':
        raise ValueError('STANDARD_PRESERVATION_SOURCE_PUBLICATION_CHANGED')
    if any(isinstance(item, ast.FunctionDef) and item.name == 'publish_materials'
           for item in ast.parse(text).body):
        raise ValueError('STANDARD_PRESERVATION_MATERIAL_ENTRY_ALREADY_PRESENT')
    current = (root/'ops/recovery/repository_minimal.py').read_text(encoding='utf-8')
    entry = _preservation_declaration(current, None, 'publish_materials')
    text = text.replace(original, entry + '\n\n\n' + original)
    compile(text, member, 'exec')
    payload[member] = text.encode()
    member = 'common/repository_retention.py'
    text = payload[member].decode('utf-8').replace('\r\n', '\n')
    for name, expected in {
        'plan_retention': 'd5422e8a37785c5f8cd92f3515d7254a80b202541f223bf2c964ffb138b6bde4',
        'execute_retention': '56cd9b9b3760fd7e7825731265d9a0aaf560d8c11fd7e7aa27f54bf60d9b7836',
    }.items():
        original = _preservation_declaration(text, None, name)
        if hashlib.sha256(original.encode()).hexdigest() != expected:
            raise ValueError('STANDARD_PRESERVATION_RETENTION_BASELINE_CHANGED ' + name)
    changes = (
        ('plan_retention', '    points = inventory(catalog)\n',
         '    from recovery_target_preservation import preservation_holds\n'
         '    held = preservation_holds(config, guard=catalog.deadline.check)\n'
         '    points = inventory(catalog)\n'),
        ('plan_retention', '    protected = set()\n', '    protected = set(held)\n'),
        ('execute_retention', '            # shutil uses the current platform end to end. No command-built shell deletion.\n',
         '            from recovery_target_preservation import preservation_holds\n'
         '            held = preservation_holds(config, guard=owner.check)\n'
         "            require(pin['path'] not in held, 'REPOSITORY_DELETE_RETAINED_POINT')\n"
         '            # shutil uses the current platform end to end. No command-built shell deletion.\n'),
    )
    for method, before, after in changes:
        selected = _preservation_declaration(text, None, method)
        if selected.count(before) != 1:
            raise ValueError('STANDARD_PRESERVATION_RETENTION_CONTEXT_CHANGED')
        text = text.replace(selected, selected.replace(before, after))
    payload[member] = text.encode()


def prepare_target_bind_mounts(payload, root):
    """Use the resources explicitly created by the empty-target preparer."""
    member = 'common/recovery_minimal_runtime.py'
    source = payload[member].decode('utf-8').replace('\r\n', '\n')
    helper = '''def prepared_data_bind(config, source, role, mount):
    destinations = {'mysql': '/var/lib/mysql', 'minio': '/data', 'redis': '/data'}
    if (config.get('preparedEmptyTarget') is not True or role not in destinations or
            mount['Type'] != 'bind' or mount['RW'] is not True):
        return False
    path, root = absolute(mount['Source']), absolute(config['dataRoot'])
    return (path == root / role and mount['Source'] in config['dataPaths'] and
            mount['Destination'] == destinations[role] and
            all(disjoint(str(path), protected) for protected in
                (*source['sourcePaths'], *source['archiveRoots'])))


'''
    changes = (
        ('class MinimalData(NativeData):', helper + 'class MinimalData(NativeData):'),
        ("        app = self.config['application']\n",
         "        app = self.config['application']\n"
         "        if self.config.get('preparedEmptyTarget') is True:\n"
         "            # Native creation and bound() already bind actual images and mounts.\n"
         "            applications = set(self.config_services) - {'mysql', 'minio', 'redis'}\n"
         "            require(set(app['startOrder']) == applications and len(app['startOrder']) == len(applications),\n"
         "                    'APPLICATION_START_ORDER_INVALID')\n"
         "            return\n"),
        ("        if not registered_main(target):\n            executables.append(target['iptablesPin'])\n",
         "        if not registered_main(target) and target.get('preparedEmptyTarget') is not True:\n"
         "            executables.append(target['iptablesPin'])\n"),
        ("                require(mount['Type'] != 'bind' or mount['RW'] is False, 'WRITABLE_HOST_BIND_REJECTED')\n",
         "                require(mount['Type'] != 'bind' or mount['RW'] is False or\n"
         "                        prepared_data_bind(self.config, self.source, role, mount), 'WRITABLE_HOST_BIND_REJECTED')\n"),
        ("        for rule in rules:\n", "        for rule in ([] if self.config.get('preparedEmptyTarget') is True else rules):\n"),
        ("                    require(mount['Type'] == 'volume' and mount['Source'] not in writable, 'SHARED_TARGET_DATA_VOLUME')\n"
         "                    writable[mount['Source']] = self.config_services[role]['id']\n",
         "                    require((mount['Type'] == 'volume' or prepared_data_bind(self.config, self.source, role, mount))\n"
         "                            and mount['Source'] not in writable, 'SHARED_TARGET_DATA_VOLUME')\n"
         "                    writable[mount['Source']] = self.config_services[role]['id']\n"
         "                    if mount['Type'] == 'bind':\n                        continue\n"),
        ("            require(len(mounts) == 1 and mounts[0]['Type'] == 'volume' and mounts[0]['RW'],\n"
         "                    'DEDICATED_MINIO_DATA_VOLUME_REQUIRED')\n"
         "            mount = mounts[0]\n"
         "            volume = json.loads(self.docker(['volume', 'inspect', mount['Name']]))[0]\n"
         "            require(volume['Driver'] == 'local' and not volume['Options'] and volume['Mountpoint'] == mount['Source'],\n"
         "                    'PHYSICAL_TARGET_VOLUME_INVALID')\n",
         "            require(len(mounts) == 1 and mounts[0]['RW'] and (mounts[0]['Type'] == 'volume' or\n"
         "                    prepared_data_bind(self.config, self.source, 'minio', mounts[0])),\n"
         "                    'DEDICATED_MINIO_DATA_VOLUME_REQUIRED')\n"
         "            mount = mounts[0]\n"
         "            if mount['Type'] == 'volume':\n"
         "                volume = json.loads(self.docker(['volume', 'inspect', mount['Name']]))[0]\n"
         "                require(volume['Driver'] == 'local' and not volume['Options'] and volume['Mountpoint'] == mount['Source'],\n"
         "                        'PHYSICAL_TARGET_VOLUME_INVALID')\n"),
        ("                    require(all(item.get('Name') != mount['Name'] and item['Source'] != mount['Source']\n",
         "                    require(all((mount['Type'] != 'volume' or item.get('Name') != mount['Name'])\n"
         "                        and item['Source'] != mount['Source']\n"),
    )
    for before, after in changes:
        if source.count(before) != 1:
            raise ValueError('STANDARD_PREPARED_TARGET_CONTEXT_CHANGED ' + member)
        source = source.replace(before, after)
    compile(source, member, 'exec')
    payload[member] = source.encode('utf-8')


def restore_admission_metadata(payload, root):
    """Resolve the selected chain without reopening or leasing every payload.

    Keep the frozen target/MAIN contracts and actual SAFE data readers. Payloads
    are read by the restore steps; admission protects only its metadata/tools.
    """
    member = 'common/recovery_minimal_plan.py'
    source = payload[member].decode('utf-8').replace('\r\n', '\n')
    current = (root/'ops/recovery/recovery_minimal_plan.py').read_text(encoding='utf-8')
    before = _preservation_declaration(source, None, 'selected_chain')
    after = _preservation_declaration(current, None, 'selected_chain')
    payload[member] = source.replace(before, after).encode('utf-8')

    member = 'common/recovery_minimal_runtime.py'
    source = payload[member].decode('utf-8').replace('\r\n', '\n')
    changes = (
        ("            for ref in step[2]['payloadPins'] + step[2]['versionPins'] + [step[0], step[3]]:\n",
         "            # Payloads are consumed by the actual restore, not leased en masse.\n"
         "            for ref in step[2]['versionPins'] + [step[0], step[3]]:\n"),
        ("        with step_timing(native.root, 'archive-verification'):\n"
         "            for step in chain:\n"
         "                for ref in step[2]['payloadPins']:\n"
         "                    check_pin(ref, content=False)\n",
         "        with step_timing(native.root, 'archive-verification'):\n"
         "            native.archive_guard.check()\n"),
    )
    for before, after in changes:
        if source.count(before) != 1:
            raise ValueError('STANDARD_RESTORE_ADMISSION_CONTEXT_CHANGED ' + member)
        source = source.replace(before, after)
    payload[member] = source.encode('utf-8')


def physical_restore_reads(payload, root):
    """Read physical payloads for copying, without extra whole-content passes."""
    def update(member, owner, name, changes):
        text = payload[member].decode('utf-8').replace('\r\n', '\n')
        before = _preservation_declaration(text, owner, name)
        after = before
        for old, new in changes:
            if after.count(old) != 1:
                raise ValueError('STANDARD_PHYSICAL_READ_CONTEXT_CHANGED ' + name)
            after = after.replace(old, new)
        payload[member] = text.replace(before, after).encode('utf-8')

    member = 'common/recovery_data_files.py'
    update(member, None, 'physical_chain_inputs', (
        ('def physical_chain_inputs(chain):', 'def physical_chain_inputs(chain, *, verify_content=True):'),
        ('"""Validate every capture/delta/content before stopping or clearing storage."""',
         '"""Resolve capture/delta metadata, optionally checking payload content."""'),
        ('            check_pin(ref, content=False)\n',
         '            if verify_content:\n                check_pin(ref, content=False)\n'),
    ))
    update(member, None, 'apply_tree', (
        ('*, full, guard, ownership=None):', '*, full, guard, ownership=None, verify_content=True):'),
        ("    require(inventory(root, guard) == before, 'OFFLINE_TARGET_TREE_CHANGED')\n",
         "    if verify_content:\n        require(inventory(root, guard) == before, 'OFFLINE_TARGET_TREE_CHANGED')\n"),
        ("        require(not before, 'FULL_FILE_TARGET_NOT_EMPTY')\n",
         "        require(not before and not any(root.iterdir()), 'FULL_FILE_TARGET_NOT_EMPTY')\n"),
        ('        relative(name); check_pin(ref, content=False)\n',
         '        relative(name)\n        if verify_content:\n            check_pin(ref, content=False)\n'),
        ("            check_pin(payloads[name], content=False)\n"
         "            require(pin(temporary)['sha256'] == item['sha256'] and pin(temporary)['bytes'] == item['bytes'],\n"
         "                    'COPIED_FILE_READBACK_MISMATCH')\n",
         "            if verify_content:\n"
         "                check_pin(payloads[name], content=False)\n"
         "                require(pin(temporary)['sha256'] == item['sha256'] and pin(temporary)['bytes'] == item['bytes'],\n"
         "                        'COPIED_FILE_READBACK_MISMATCH')\n"),
        ("    require(inventory(root, guard) == after, 'OFFLINE_FILE_READBACK_MISMATCH')\n",
         "    if verify_content:\n        require(inventory(root, guard) == after, 'OFFLINE_FILE_READBACK_MISMATCH')\n"),
        ("'completeTreeReadback': True", "'completeTreeReadback': verify_content"),
    ))
    update('common/recovery_minimal_runtime.py', 'MinimalData', 'physical_object_chain', (
        ('        from recovery_data_objects import compare_indexed_restore\n', ''),
        ('physical_chain_inputs(self.chain)', 'physical_chain_inputs(self.chain, verify_content=False)'),
        ("                               ownership=self.policy['minioFileOwnership'])",
         "                               ownership=self.policy['minioFileOwnership'], verify_content=False)"),
        ("        export = self.modules['formal_s3_export'].export_s3_versions(self.object_client(), self.config['buckets'],\n"
         "            self.root/'physical-export', guard=self.guard, timeout=self.seconds())\n"
         "        self.bound()\n"
         "        comparison = compare_indexed_restore(self.chain, self.policy, self.root/'physical-export', export,\n"
         "            self.modules['formal_physical_restore_readback'], self.guard)\n",
         "        comparison = dict(state='NOT_PERFORMED', payloadContentVerified=False,\n"
         "            exactVersionIdentityVerified=False, productionEvidence=False)\n"),
        ('            permissionEvidencePin=self.check_bucket_permissions(), originalVersionIdsPreserved=True)',
         '            permissionEvidencePin=self.check_bucket_permissions(), originalVersionIdsPreserved=True,\n'
         '            payloadContentVerified=False)'),
    ))
    update('common/recovery_data.py', 'NativeData', 'consistency', (
        ("            response, headers = client.content(match['targetBucket'], match['key'], match['targetVersionId'])\n",
         "            if objects.get('payloadContentVerified') is False:\n                continue\n"
         "            response, headers = client.content(match['targetBucket'], match['key'], match['targetVersionId'])\n"),
        ('                    invariantsVerified=True, applicationVerified=False, observedAt=utc())',
         "                    invariantsVerified=True, payloadContentVerified=objects.get('payloadContentVerified', True),\n"
         '                    applicationVerified=False, observedAt=utc())'),
    ))


def prepared_database_readback(payload, root):
    """Prepared targets prove SQL completion, not whole-database equivalence."""
    member = 'common/recovery_data.py'
    text = payload[member].decode('utf-8').replace('\r\n', '\n')
    changes = (
        ('database_readback',
         "        self.bound()\n",
         "        self.bound()\n"
         "        if self.config.get('preparedEmptyTarget') is True:\n"
         "            require(self.mysql.schema_query('SELECT 1;', database=self.config['database'],\n"
         "                expected_uuid=self.db_uuid) == [['1']], 'PREPARED_DATABASE_NOT_QUERYABLE')\n"
         "            self.bound()\n"
         "            # Reached only after SQL application returned successfully.\n"
         "            return dict(recoveryPoint=self.material['recoveryPoint'], databaseUuid=self.db_uuid,\n"
         "                endPosition=self.material['database']['endPosition'],\n"
         "                operationId=self.original['operationId'], targetId=self.config['targetId'],\n"
         "                databaseApplyCompleted=True, databaseQueryable=True, verificationState='NOT_PERFORMED',\n"
         "                fullSchemaDataEquivalenceVerified=False, incrementalReplayAndAffectedDataVerified=False,\n"
         "                applicationVerified=False)\n"),
        ('incremental_database',
         "                 previous.get('incrementalReplayAndAffectedDataVerified') is True),\n",
         "                 previous.get('incrementalReplayAndAffectedDataVerified') is True or\n"
         "                 (self.config.get('preparedEmptyTarget') is True and\n"
         "                  previous.get('databaseApplyCompleted') is True and previous.get('databaseQueryable') is True and\n"
         "                  previous.get('operationId') == self.original['operationId'] and\n"
         "                  previous.get('targetId') == self.config['targetId'])),\n"),
    )
    for name, before, after in changes:
        method = _preservation_declaration(text, 'NativeData', name)
        # database_readback has entry and exit bounds; only its entry branches.
        if before not in method:
            raise ValueError('STANDARD_PREPARED_DATABASE_CONTEXT_CHANGED ' + name)
        text = text.replace(method, method.replace(before, after, 1))
    payload[member] = text.encode('utf-8')


def prepared_service_health(payload, root):
    """Probe prepared services without requiring image-defined HEALTHCHECKs."""
    member = 'common/recovery_minimal_runtime.py'
    text = payload[member].decode('utf-8').replace('\r\n', '\n')
    method = _preservation_declaration(text, 'MinimalData', 'wait_healthy')
    before = '        self.bound()\n'
    branch = '''        if self.config.get('preparedEmptyTarget') is True:
            from recovery_main_health import ROLES, STARTUP_SECONDS, probe
            require(role in ROLES, 'PREPARED_HEALTH_ROLE_UNSUPPORTED')
            self.bound()
            service = self.config_services[role]
            port, path = ROLES[role]
            url = 'http://' + service['ip'] + ':' + str(port) + path
            deadline = time.monotonic() + min(STARTUP_SECONDS, self.budget.remaining())
            while True:
                self.guard()
                require(time.monotonic() < deadline, 'PREPARED_SERVICE_HEALTH_TIMEOUT')
                row = self.inspect(service['id']); state = row['State']
                require(row['Id'] == service['id'] and row['Image'] == service['imageId'] and
                        state['Running'] and not state['Paused'] and not state['Restarting'],
                        'PREPARED_HEALTH_SERVICE_CHANGED')
                declared = bool(row['Config'].get('Healthcheck')); health = state.get('Health')
                if declared or health is not None:
                    require(type(health) is dict and health.get('Status') in ('starting', 'healthy'),
                            'APPLICATION_OR_STORAGE_UNHEALTHY')
                observed = probe(url, role, max(0.001, min(5, deadline-time.monotonic(), self.budget.remaining())))
                if observed['ready'] and (health is None or health['Status'] == 'healthy'):
                    require(time.monotonic() < deadline, 'PREPARED_SERVICE_HEALTH_TIMEOUT')
                    self.bound()
                    evidence = write(self.root/('prepared-health-'+role+'.json'), dict(role=role,
                        containerId=row['Id'], imageId=row['Image'], endpoint=url, observedAt=utc(),
                        dockerHealthcheckConfigured=declared, **observed))
                    return dict(containerId=row['Id'], imageId=row['Image'], status='healthy',
                        observedAt=utc(), readinessPin=evidence)
                require(time.monotonic() < deadline, 'PREPARED_SERVICE_HEALTH_TIMEOUT')
                time.sleep(min(0.25, deadline-time.monotonic(), self.budget.remaining()))
'''
    if before not in method:
        raise ValueError('STANDARD_PREPARED_HEALTH_CONTEXT_CHANGED')
    payload[member] = text.replace(method, method.replace(before, branch+before, 1)).encode('utf-8')


def apply(payload):
    payload = dict(payload)
    root = Path(__file__).resolve().parents[2]
    incremental_sql_stream(payload, root)
    native_invocation_transports(payload, root)
    incremental_chain_admission(payload, root)

    def replace(name, before, after):
        source = payload[name].decode().replace('\r\n', '\n')
        if source.count(before) != 1:
            raise ValueError('STANDARD_FIX_CONTEXT_CHANGED ' + name)
        payload[name] = source.replace(before, after).encode()

    replace('formal/minimal_capture_support.py',
        "set(value) == {'containerId', 'host', 'database'} and",
        "set(value) - {'passwordPin'} == {'containerId', 'host', 'database'} and")
    replace('formal/minimal_capture_support.py',
        "        0 <= value['database'] < 16, 'MINIMAL_REDIS_SNAPSHOT_CONFIG_INVALID')\n    return value",
        "        0 <= value['database'] < 16, 'MINIMAL_REDIS_SNAPSHOT_CONFIG_INVALID')\n    if 'passwordPin' in value: pin(value['passwordPin'])\n    return value")
    replace('formal/minimal_redis_snapshot.py',
        "    client=redis.Redis(host=config['host'],port=6379,db=config['database'],\n        socket_timeout=30,socket_connect_timeout=5)",
        """    options={}
    if 'passwordPin' in config:
        import stat
        from pathlib import Path
        from formal_capture_recovery_inputs import original_bytes
        reference=config['passwordPin']
        raw=original_bytes(reference,limit=16384)
        require(stat.S_IMODE(Path(reference['path']).stat().st_mode)==0o600,
            'MINIMAL_SECRET_MODE_REQUIRED')
        password=raw.decode('utf-8').removesuffix('\\n')
        require(bool(password) and '\\n' not in password and '\\r' not in password,
            'MINIMAL_REDIS_PASSWORD_INVALID')
        options['password']=password
    client=redis.Redis(host=config['host'],port=6379,db=config['database'],
        socket_timeout=30,socket_connect_timeout=5,**options)""")
    replace('formal/minimal_capture_worker.py',
        "    secrets = {source['passwordPin']['path'], descriptor['credentialReference']['path']}\n    for reference in (source['passwordPin'], descriptor['credentialReference']):",
        """    secret_refs = [source['passwordPin'], descriptor['credentialReference']]
    if 'passwordPin' in source.get('redisSnapshot', {}):
        secret_refs.append(source['redisSnapshot']['passwordPin'])
    secrets = {reference['path'] for reference in secret_refs}
    for reference in secret_refs:
        originals.read(reference, 16384)""")
    payload['formal/formal_binlog_scope.py'] = (root/'ops/backup_engine/formal/formal_binlog_scope.py').read_bytes()
    payload['formal/formal_data_evidence.py'] = (root/'ops/backup_engine/formal/formal_data_evidence.py').read_bytes()
    name = 'formal/formal_schema_evidence.py'
    if hashlib.sha256(payload[name].replace(b'\r\n', b'\n')).hexdigest() != \
            'c174a1bab42bc7df6c6576fc30948c2e390274e64c9337f2b04b2dc246455211':
        raise ValueError('STANDARD_SCHEMA_BASELINE_CHANGED')
    payload[name] = (root/'ops/backup_engine/formal/formal_schema_evidence.py').read_bytes()
    replace('common/recovery_minimal_runtime.py',
        "             'formal_physical_restore_readback')",
        "             'formal_physical_restore_readback', 'formal_schema_evidence')")
    replace('common/recovery_minimal_runtime.py',
        "        self.config_services = {row['role']: row for row in target['services']}\n",
        "        self.config_services = {row['role']: row for row in target['services']}\n"
        "        self.frontend_readiness = configuration.get('frontendReadiness', {}).get(request['targetConfigRef'])\n")
    replace('common/recovery_data.py',
        "             'formal_physical_restore_readback', 'formal_data_evidence', 'formal_s3_export')",
        "             'formal_physical_restore_readback', 'formal_data_evidence', 'formal_s3_export', 'formal_schema_evidence')")
    replace('common/recovery_data.py',
        "                self.import_sql(expanded, checksum)\n        with self.timed_stage('sql-readback'):",
        "                self.import_sql(expanded, checksum)\n        with self.timed_stage('sql-allocator-state'):\n"
        "            self.restore_allocator_state()\n        with self.timed_stage('sql-readback'):")
    source = (root/'ops/recovery/recovery_data.py').read_text(encoding='utf8')
    start = '    def restore_allocator_state(self):\n'
    end = '    def database_readback(self):\n'
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError('STANDARD_ALLOCATOR_METHOD_BOUNDARY_CHANGED')
    method = start + source.split(start)[1].split(end)[0]
    replace('common/recovery_data.py', end, method + end)
    replace('common/recovery_data.py',
        "scope['schemaVersion'] in (('backup-binlog-event-scope/v2',) if scoped else\n                    ('backup-binlog-event-scope/v1', 'backup-binlog-event-scope/v2'))",
        "scope['schemaVersion'] in (('backup-binlog-event-scope/v2', 'backup-binlog-event-scope/v3') if scoped else\n                    ('backup-binlog-event-scope/v1', 'backup-binlog-event-scope/v2', 'backup-binlog-event-scope/v3'))")
    replace('common/recovery_data.py',
        "scope['policy'] == 'MYSQL80_ROW_AND_SCOPED_TABLE_DDL' and",
        "(scope['policy'] == ('MYSQL80_ROW_AND_SCOPED_DATABASE_DDL' if scope['schemaVersion'] == 'backup-binlog-event-scope/v3' else 'MYSQL80_ROW_AND_SCOPED_TABLE_DDL')) and")
    replace('control/recovery_control_smallapp_native.py',
        "        self.document(owner_configuration)\n        return dict(schemaVersion=",
        """        self.document(owner_configuration)
        if value['action'] in ('FULL', 'INCREMENTAL'):
            from recovery_control_capture_config import for_request
            owner_configuration = for_request(self, config, value, owner_configuration, point_pin)
        return dict(schemaVersion=""")
    payload['control/recovery_control_capture_config.py'] = (root/'backend/src/main/resources/recovery_control_capture_config.py').read_bytes()
    payload['control/recovery_control_restore_catalogue.py'] = (root/'backend/src/main/resources/recovery_control_restore_catalogue.py').read_bytes()
    replace('control/recovery_control_smallapp_native.py',
        "            row['freshTargetConfigRefs'] = [target['configRef'] for target in registered['allowedRestoreTargets']\n                if type(targets) is dict and target['configRef'] in targets]",
        """            from recovery_control_target_availability import available
            row['freshTargetConfigRefs'] = [target['configRef'] for target in registered['allowedRestoreTargets']
                if type(targets) is dict and target['configRef'] in targets and
                available(self, targets[target['configRef']], target['configRef'], source_ref)]""")
    payload['control/recovery_control_target_availability.py'] = (root/'backend/src/main/resources/recovery_control_target_availability.py').read_bytes()
    replace('control/recovery_control_smallapp_native.py',
        "        binding_pin = self.selector(Path(config['registryRoot']) / 'points', reference)\n        point = self.document(binding_pin)",
        """        binding_pin = self.selector(Path(config['registryRoot']) / 'points', reference)
        from recovery_control_point_quarantine import quarantined
        need(not quarantined(self, config, reference, source_ref, binding_pin), 'POINT_QUARANTINED')
        point = self.document(binding_pin)""")
    replace('control/recovery_control_smallapp_native.py',
        "                    self.point(config, reference, source_ref)\n                    references.append(reference)",
        """                    from recovery_control_point_quarantine import quarantined
                    if quarantined(self, config, reference, source_ref, self.selector(path.parent, reference)):
                        continue
                    self.point(config, reference, source_ref)
                    references.append(reference)""")
    payload['control/recovery_control_point_quarantine.py'] = (root/'backend/src/main/resources/recovery_control_point_quarantine.py').read_bytes()
    payload = backup_timings(restore_timings(payload))
    replace('common/repository_minimal.py',
        'from staging_cleanup import cleanup, capture_paths\n',
        'from staging_cleanup import cleanup, capture_paths\nfrom repository_records import incremental_chain_admission\n')
    replace('common/repository_minimal.py',
        "            require(len(parents) < config.value['maxChainPoints'], 'REPOSITORY_NEW_FULL_REQUIRED')\n",
        "            require(incremental_chain_admission(config.value, parents[0][2].get('createdAt'), len(parents)) is None,\n"
        "                    'REPOSITORY_NEW_FULL_REQUIRED')\n")
    replace('common/repository_minimal.py',
        "        while True:\n            role = 'capture' if query == 0 else 'capture-query-' + str(query)\n",
        "        while True:\n"
        "            if query == 0 and parents:\n"
        "                require(incremental_chain_admission(config.value, parents[0][2].get('createdAt'), len(parents)) is None,\n"
        "                        'REPOSITORY_NEW_FULL_REQUIRED')\n"
        "            role = 'capture' if query == 0 else 'capture-query-' + str(query)\n")
    payload['formal/formal_capture_parent_guard.py'] = (root/'ops/backup_engine/formal/formal_capture_parent_guard.py').read_bytes()
    # Only MinimalSemantic adopts continuous parent custody. The normal formal
    # owner keeps its original full verifier through the base-class hook.
    replace('formal/formal_capture_semantics.py',
        '    def _parent(self):\n',
        '    def _parent(self):\n        self.parent_guard = None\n')
    replace('formal/formal_capture_semantics.py',
        "            self.verify_content(content, self.originals.check)\n"
        "            self.parent_content_identities.append((Path(content['path']), self.file_identity(Path(content['path']).lstat())))\n"
        "        return index['contentPins']\n",
        "        self.parent_guard = self._verify_parent_inputs(index['contentPins'])\n"
        "        return index['contentPins']\n\n"
        "    def _verify_parent_inputs(self, contents):\n"
        "        for content in contents.values():\n"
        "            self.verify_content(content, self.originals.check)\n"
        "            self.parent_content_identities.append((Path(content['path']), self.file_identity(Path(content['path']).lstat())))\n"
        "        return None\n")
    replace('formal/minimal_capture_support.py',
        '        self.originals.current(); self.series.check()\n',
        '        if self.parent_guard is not None:\n            self.parent_guard.check()\n'
        '        self.originals.current(); self.series.check()\n')
    replace('formal/minimal_capture_support.py',
        "        for reference, raw, allow_empty in self.parent_originals:\n"
        "            require(original_bytes(reference, allow_empty=allow_empty) == raw,\n"
        "                'FORMAL_CAPTURE_SEMANTIC_PARENT_CHANGED')\n"
        "        for path, identity in self.parent_content_identities:\n"
        "            require(self.file_identity(path.lstat()) == identity, 'FORMAL_CAPTURE_OBJECT_PARENT_CHANGED')\n",
        '')
    replace('formal/minimal_capture_support.py',
        '    def __init__(self, series, originals, descriptor, source_config):\n',
        '''    def _verify_parent_inputs(self, contents):
        from formal_capture_parent_guard import ParentInputGuard
        return ParentInputGuard(self.parent_originals, contents.values(),
            self.originals.current, self.verify_content)

    def verify_parent(self):
        self.check()
        if self.parent_guard is not None:
            self.parent_guard.verify()

    def close(self):
        parent, self.parent_guard = self.parent_guard, None
        if parent is not None:
            parent.close()

    def __init__(self, series, originals, descriptor, source_config):
        self.parent_guard = None
        try:
            self._initialize(series, originals, descriptor, source_config)
        except BaseException:
            self.close()
            raise

    def _initialize(self, series, originals, descriptor, source_config):
''')
    replace('formal/minimal_capture_support.py',
        '        super().capture(mysql, database, root, guard)\n',
        '        self.verify_parent()\n        super().capture(mysql, database, root, guard)\n')
    replace('formal/minimal_capture_support.py',
        '            self.check()\n\n    def finalize(self, point, guard):\n',
        '            self.check()\n        self.verify_parent()\n\n    def finalize(self, point, guard):\n        self.verify_parent()\n')
    replace('formal/minimal_capture_support.py',
        '        return super().finalize(point, guard)\n',
        '        result = super().finalize(point, guard)\n        self.verify_parent()\n        return result\n')
    replace('formal/minimal_capture_worker.py',
        "    require(len(runtime.flags) == 2 and all(x in ('0', '1') for x in runtime.flags), 'MINIMAL_DATABASE_FLAGS_INVALID')\n"
        "    token = observation_deadline.set(budget.deadline)\n",
        "    require(len(runtime.flags) == 2 and all(x in ('0', '1') for x in runtime.flags), 'MINIMAL_DATABASE_FLAGS_INVALID')\n"
        "    semantic = None\n    token = observation_deadline.set(budget.deadline)\n")
    replace('formal/minimal_capture_worker.py',
        '                originals.check(full=True); runtime.protected(force=True)\n',
        '                semantic.verify_parent()\n                originals.check(full=True); runtime.protected(force=True)\n')
    replace('formal/minimal_capture_worker.py',
        "            runtime.event('CAPTURE_MATERIAL_COMPLETE_SOURCE_RESTORED')\n"
        "            return result\n    finally: observation_deadline.reset(token)\n",
        """            semantic.verify_parent()
            runtime.event('CAPTURE_MATERIAL_COMPLETE_SOURCE_RESTORED')
            return result
    finally:
        import sys
        primary = sys.exception()
        try:
            if semantic is not None:
                semantic.close()
        except BaseException as error:
            if primary is None:
                raise
            primary.diagnostic = diagnostic_value(dict(
                getattr(primary, 'diagnostic', None) or {},
                parentLeaseCleanupFailureCode=failure_code(error)))
        finally:
            observation_deadline.reset(token)
""")
    # Install the one continuous inode lease before the frozen strict readers
    # collect identity baselines. All original hash/metadata checks remain.
    replace('common/recovery_minimal_runtime.py',
        '    def __init__(self, configuration, request, source, policy, chain, target, root, input_pins):\n',
        '''    def __init__(self, configuration, request, source, policy, chain, target, root, input_pins, *, native_context=None):
        self.archive_guard = None
        try:
            self._initialize(configuration, request, source, policy, chain, target, root, input_pins,
                native_context=native_context)
        except BaseException:
            if self.archive_guard is not None:
                self.archive_guard.close()
            raise

    def _initialize(self, configuration, request, source, policy, chain, target, root, input_pins, *, native_context=None):
''')
    replace('common/recovery_minimal_runtime.py',
        "        self.original = request\n",
        """        from recovery_program_native import _NativeView
        require(native_context is not None or request['targetConfigRef'] not in
                configuration.get('targetProgramPolicies', {}), 'PROGRAM_NATIVE_CONTEXT_REQUIRED')
        if native_context is not None:
            require(type(native_context) is _NativeView, 'PROGRAM_NATIVE_CONTEXT_INVALID')
            native_context.validate_inputs(configuration, request, target)
        self.native_context = native_context
        self.original = request
""")
    replace('common/recovery_minimal_runtime.py',
        "        self.budget = Budget(configuration['deadlineMilliseconds'])\n",
        "        self.budget = native_context.budget if native_context is not None else Budget(configuration['deadlineMilliseconds'])\n")
    replace('common/recovery_minimal_runtime.py',
        '        self.db_uuid = self.database_uuid()\n',
        '        self.guard()\n        self.db_uuid = self.database_uuid()\n')
    replace('common/recovery_minimal_runtime.py',
        '    def guard(self):\n        self.budget.remaining()\n',
        '    def guard(self):\n        if self.native_context is not None:\n'
        '            self.native_context.guard_native(self)\n        self.budget.remaining()\n')
    replace('common/recovery_minimal_runtime.py',
        "        for ref in (target['dockerPin'], target['iptablesPin'], *self.input_pins):\n",
        "        # Registered MAIN uses resource custody; rehearsal uses firewall isolation.\n"
        "        from recovery_main_target import enabled as registered_main\n"
        "        executables = [target['dockerPin']]\n"
        "        if not registered_main(target):\n"
        "            executables.append(target['iptablesPin'])\n"
        "        for ref in (*executables, *self.input_pins):\n")
    replace('common/recovery_minimal_runtime.py',
        "        for ref in references.values():\n            path = absolute(ref['path'])\n            before = signature(path.stat())\n",
        "        from recovery_archive_guard import ArchivePathGuard\n"
        "        self.archive_guard = ArchivePathGuard.capture(references)\n"
        "        for ref in references.values():\n            path = absolute(ref['path'])\n"
        "            before = self.archive_guard.signatures[ref['path']]\n"
        "            require(signature(path.stat()) == before, 'PIN_CHANGED')\n")
    replace('common/recovery_minimal_runtime.py',
        "            self.payload_signatures[ref['path']] = before\n"
        "        from recovery_archive_guard import ArchivePathGuard\n"
        "        self.archive_guard = ArchivePathGuard(self.payload_signatures)\n",
        "            self.payload_signatures[ref['path']] = before\n"
        "            self.archive_guard.check()\n")
    replace('common/repository_minimal.py',
        '        super().__init__(root, entries, *args, **kwargs)\n',
        '''        self.baseline_ready = False
        try:
            if os.name == 'posix':
                from recovery_archive_guard import ArchivePathGuard
                require(type(root) is str and Path(root).is_absolute() and
                        type(entries) is dict and entries, 'ARCHIVE_SESSION_INVALID')
                for name in entries:
                    self._relative(name)
                files = [Path(root) / name for name, marker in entries.items() if marker != 'directory']
                directories = [Path(root), *(Path(root) / name for name, marker in entries.items()
                                              if marker == 'directory')]
                self.path_guard = ArchivePathGuard.capture(files, closed_directories=directories)
                owner_guard, path_guard = kwargs['guard'], self.path_guard
                def current():
                    owner_guard()
                    path_guard.check()
                kwargs['guard'] = current
            super().__init__(root, entries, *args, **kwargs)
            self.baseline_ready = True
        except BaseException:
            self.close()
            raise

    def close(self):
        # Resource cleanup is not the protocol's successful close ACK.
        if not getattr(self, 'closed', False):
            self.failed = True
        if self.path_guard is not None:
            self.path_guard.close()

    def __del__(self):
        self.close()
''')
    replace('common/repository_minimal.py',
        '''        if self.path_guard is None:
            from recovery_archive_guard import ArchivePathGuard
            files = {self.root / name: (saved[0], saved[1], saved[6], saved[7], saved[8])
                     for name, saved in self.pins.items() if stat.S_ISREG(saved[2])}
            directories = [self.root / name for name, saved in self.pins.items()
                           if stat.S_ISDIR(saved[2])]
            self.path_guard = ArchivePathGuard(files, closed_directories=directories)
''',
        '''        if not self.baseline_ready:
            for name, saved in self.pins.items():
                path = self.root / name
                if stat.S_ISREG(saved[2]):
                    require((saved[0], saved[1], saved[6], saved[7], saved[8]) ==
                            self.path_guard.signatures[str(path)], 'ARCHIVED_PAYLOAD_CHANGED')
                else:
                    require(saved[:2] == self.path_guard.identities[path], 'ARCHIVED_PAYLOAD_CHANGED')
            for path, saved in self.ancestors.items():
                require(saved[:2] == self.path_guard.identities[path], 'ARCHIVED_PAYLOAD_CHANGED')
''')
    replace('common/repository_minimal.py',
        '''        target = config.archives / ('prod-' + publisher.binding['attemptId'])
        published = publisher.stream(target, tree)
        close = publisher.archive_request('close')
        require(close['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF', 'REPOSITORY_ARCHIVE_CLOSE_FAILED')
''',
        '''        try:
            target = config.archives / ('prod-' + publisher.binding['attemptId'])
            published = publisher.stream(target, tree)
            close = publisher.archive_request('close')
            require(close['state'] == 'ARCHIVE_READER_CLOSED_NOT_NAS_PROOF', 'REPOSITORY_ARCHIVE_CLOSE_FAILED')
        finally:
            publisher.reader.close()
''')
    name = 'common/recovery_minimal_runtime.py'
    replace('common/recovery_minimal_plan.py',
        'def target_configuration(configuration, request, source):\n',
        '''def target_configuration(configuration, request, source):
    from recovery_main_target import enabled, target_configuration as registered_main
    if enabled(configuration['targets'][request['targetConfigRef']]):
        return registered_main(configuration, request, source)
''')
    replace(name,
        "        require(self.db_uuid != self.material['sourceDatabaseUuid'], 'SOURCE_DATABASE_TARGET_REJECTED')",
        "        from recovery_main_target import database_identity\n        database_identity(self)")
    replace('common/recovery_data.py',
        "        require(endpoint not in pinned_json(self.material['sourceScopePin'])['endpointHosts'], 'SOURCE_ENDPOINT_REJECTED')",
        "        from recovery_main_target import object_endpoint\n        object_endpoint(self, endpoint)")
    replace(name,
        '''        mounts = [item for item in row['Mounts'] if item['Destination'] == self.policy['minioDataMount']]
        require(len(mounts) == 1 and mounts[0]['Type'] == 'volume' and mounts[0]['RW'],
                'DEDICATED_MINIO_DATA_VOLUME_REQUIRED')
        mount = mounts[0]
        volume = json.loads(self.docker(['volume', 'inspect', mount['Name']]))[0]
        require(volume['Driver'] == 'local' and not volume['Options'] and volume['Mountpoint'] == mount['Source'],
                'PHYSICAL_TARGET_VOLUME_INVALID')
''',
        '''        from recovery_main_target import enabled, physical_mount
        if enabled(self.config):
            mount = physical_mount(self, row)
        else:
            mounts = [item for item in row['Mounts'] if item['Destination'] == self.policy['minioDataMount']]
            require(len(mounts) == 1 and mounts[0]['Type'] == 'volume' and mounts[0]['RW'],
                    'DEDICATED_MINIO_DATA_VOLUME_REQUIRED')
            mount = mounts[0]
            volume = json.loads(self.docker(['volume', 'inspect', mount['Name']]))[0]
            require(volume['Driver'] == 'local' and not volume['Options'] and volume['Mountpoint'] == mount['Source'],
                    'PHYSICAL_TARGET_VOLUME_INVALID')
''')
    replace(name,
        '''        for identity in self.docker(['ps', '--all', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines():
            if identity != row['Id']:
                require(all(item.get('Name') != mount['Name'] and item['Source'] != mount['Source']
                    for item in self.inspect(identity)['Mounts']), 'PHYSICAL_VOLUME_SHARED')
''',
        '''        if not enabled(self.config):
            for identity in self.docker(['ps', '--all', '--no-trunc', '--format', '{{.ID}}']).decode().splitlines():
                if identity != row['Id']:
                    require(all(item.get('Name') != mount['Name'] and item['Source'] != mount['Source']
                        for item in self.inspect(identity)['Mounts']), 'PHYSICAL_VOLUME_SHARED')
''')
    old = 'def execute(configuration, request, root, input_pins):\n'
    new = '''from recovery_main_target import guarded_type
MinimalData = guarded_type(MinimalData)


def execute(configuration, request, root, input_pins):
    from recovery_replace import enabled, execute as replace
    if enabled(configuration['targets'][request['targetConfigRef']]):
        return replace(configuration, request, root, input_pins, execute_empty, MinimalData, selected_chain)
    return execute_empty(configuration, request, root, input_pins)


def execute_empty(configuration, request, root, input_pins, *, reservation_configuration=None):
'''
    text = payload[name].decode()
    if text.count(old) != 1:
        raise RuntimeError('STANDARD_REPLACE_EXECUTE_SITE_CHANGED')
    payload[name] = text.replace(old, new).encode()
    replace(name, '    def secret(self, role, environment):\n', '''    def import_sql(self, path, checksum):
        from recovery_replace import enabled, preserve_binary_logging
        if enabled(self.config):
            checksum = preserve_binary_logging(self, path, checksum)
        return super().import_sql(path, checksum)

    def secret(self, role, environment):
''')
    payload['common/recovery_replace.py'] = (root/'ops/recovery/recovery_replace.py').read_bytes()
    # The frozen SAFE file engine always hashes and verifies the entire tree.
    # Keep its original contract; FAST-only options cannot cross this boundary.
    replace('common/recovery_replace.py',
        'before = inventory(root, native.guard, content=False)',
        'before = inventory(root, native.guard)')
    replace('common/recovery_replace.py',
        'apply_tree(root, before, {}, {}, full=False, guard=native.guard, verify_content=False)',
        'apply_tree(root, before, {}, {}, full=False, guard=native.guard)')
    replace(name, '            def query(self, statement):\n',
        '            def query(self, statement, *, mutation=False):\n')
    replace(name, "                    '-e', statement]).decode('utf-8')",
        "                    '-e', statement], mutation=mutation).decode('utf-8')")
    payload['common/recovery_main_target.py'] = (root/'ops/recovery/recovery_main_target.py').read_bytes()
    payload['common/recovery_archive_versions.py'] = (root/'ops/recovery/recovery_archive_versions.py').read_bytes()
    payload['common/recovery_program_archive.py'] = (root/'ops/recovery/recovery_program_archive.py').read_bytes()
    payload['common/recovery_program_containers.py'] = (root/'ops/recovery/recovery_program_containers.py').read_bytes()
    payload['common/recovery_program_generation.py'] = (root/'ops/recovery/recovery_program_generation.py').read_bytes()
    payload['common/recovery_program_activation.py'] = (root/'ops/recovery/recovery_program_activation.py').read_bytes()
    payload['common/recovery_program_targets.py'] = (root/'ops/recovery/recovery_program_targets.py').read_bytes()
    payload['common/recovery_program_execution.py'] = (root/'ops/recovery/recovery_program_execution.py').read_bytes()
    payload['common/recovery_program_retry.py'] = (root/'ops/recovery/recovery_program_retry.py').read_bytes()
    payload['common/recovery_program_derivation.py'] = (root/'ops/recovery/recovery_program_derivation.py').read_bytes()
    payload['common/recovery_program_import.py'] = (root/'ops/recovery/recovery_program_import.py').read_bytes()
    payload['common/recovery_program_native.py'] = (root/'ops/recovery/recovery_program_native.py').read_bytes()
    payload['common/recovery_program_source.py'] = (root/'ops/recovery/recovery_program_source.py').read_bytes()
    payload['common/recovery_program_protection.py'] = (root/'ops/recovery/recovery_program_protection.py').read_bytes()
    payload['common/recovery_program_resources.py'] = (root/'ops/recovery/recovery_program_resources.py').read_bytes()
    payload['common/recovery_program_restore.py'] = (root/'ops/recovery/recovery_program_restore.py').read_bytes()
    payload['common/recovery_program_evidence.py'] = (root/'ops/recovery/recovery_program_evidence.py').read_bytes()
    payload['common/recovery_program_sql_staging.py'] = (root/'ops/recovery/recovery_program_sql_staging.py').read_bytes()
    payload['common/recovery_target_sources.py'] = (root/'ops/recovery/recovery_target_sources.py').read_bytes()
    payload['common/recovery_mysql_scheduler.py'] = (root/'ops/recovery/recovery_mysql_scheduler.py').read_bytes()
    payload['common/recovery_main_health.py'] = (root/'ops/recovery/recovery_main_health.py').read_bytes()
    payload['common/recovery_published_fence.py'] = (root/'ops/recovery/recovery_published_fence.py').read_bytes()
    payload['common/recovery_archive_view.py'] = (root/'ops/recovery/recovery_archive_view.py').read_bytes()
    replace('common/recovery_minimal_redis_dump.py',
        "    options=dict(host=native.config_services['redis']['ip'],port=6379,db=adapter['database'],\n"
        "        password=native.secret('redis','REDIS_PASSWORD'),socket_timeout=10,socket_connect_timeout=5)",
        "    from recovery_main_target import redis_password\n"
        "    options=dict(host=native.config_services['redis']['ip'],port=6379,db=adapter['database'],\n"
        "        password=redis_password(native),socket_timeout=10,socket_connect_timeout=5)")
    payload['common/recovery_replacement_storage.py'] = (root/'ops/recovery/recovery_replacement_storage.py').read_bytes()
    payload['common/recovery_retained_retry.py'] = (root/'ops/recovery/recovery_retained_retry.py').read_bytes()
    replace(name,
        "        self.modules = modules_from(configuration['formalModuleDirectory'])\n",
        "        self.modules = modules_from(configuration['formalModuleDirectory'])\n"
        "        self.policy['dataLimits'] = self.modules['formal_data_evidence'].validate_limits(configuration['dataLimits'])\n")
    payload['common/recovery_resource_admission.py'] = (root/'ops/recovery/recovery_resource_admission.py').read_bytes()
    payload['common/recovery_archive_guard.py'] = (root/'ops/recovery/recovery_archive_guard.py').read_bytes()
    replace('common/recovery_minimal_worker.py',
        "        result = operation_result(request, started, 'TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED', code,",
        "        if code == 'ARCHIVED_PAYLOAD_CHANGED' and hasattr(error, 'archive_diagnostic'):\n"
        "            data['archiveDiagnostic'] = error.archive_diagnostic\n"
        "        result = operation_result(request, started, 'TERMINAL_UNKNOWN' if unknown else 'FAILED_RETAINED', code,")
    replace('common/recovery_minimal_worker.py',
        "                    actualNativeExitCode=None if native is None else native.last_exit)",
        "                    actualNativeExitCode=None if native is None else native.last_exit,\n"
        "                    mutationDispatched=bool(native is not None and native.mutation_dispatched) or\n"
        "                    (absolute(args.output).parent/'replacement-preparation/replacement-intent.json').exists())")
    payload['common/recovery_firewall.py'] = (root/'ops/recovery/recovery_firewall.py').read_bytes()
    replace('common/recovery_minimal_runtime.py',
        "            first = next((line for line in raw.decode().splitlines() if line.startswith('-A ')), None)\n"
        "            require(first and shlex.split(first) == ['-A', *rule], 'TARGET_FIREWALL_CHANGED')",
        "            from recovery_firewall import subnet_isolation_rule_effective\n"
        "            require(subnet_isolation_rule_effective(raw.decode('utf-8'), rule), 'TARGET_FIREWALL_CHANGED')")
    replace('common/recovery_data.py',
        "        import shlex\n        for rule in firewall['rules']:",
        "        from recovery_firewall import isolation_rule_effective\n        for rule in firewall['rules']:")
    replace('common/recovery_data.py',
        "            first = next((line for line in raw.decode().splitlines() if line.startswith('-A ')), None)\n"
        "            require(first and shlex.split(first) == ['-A', *rule], 'TARGET_FIREWALL_CHANGED')",
        "            require(isolation_rule_effective(raw.decode('utf-8'), rule), 'TARGET_FIREWALL_CHANGED')")
    replace('common/recovery_minimal.py',
        "        require(request['action'] == 'RESTORE', 'CAPTURE_ACTION_REQUIRES_W03_ENTRY')\n",
        "        require(request['action'] == 'RESTORE', 'CAPTURE_ACTION_REQUIRES_W03_ENTRY')\n"
        "        from recovery_resource_admission import reserve, release_success\n")
    replace('common/recovery_minimal.py',
        "        check_pin(configuration['pythonPin'], content=False)\n",
        "        check_pin(configuration['pythonPin'], content=False)\n"
        "        reserve(configuration, request, root)\n")
    replace('common/recovery_minimal.py',
        "            result['originalResultPins'].extend([pin(worker_output), receipt_pin])\n",
        "            result['originalResultPins'].extend([pin(worker_output), receipt_pin])\n"
        "            if result['state'] == 'SUCCEEDED':\n"
        "                result['originalResultPins'].append(release_success(configuration, request, root,\n"
        "                    pin(worker_output), receipt_pin))\n"
        "            elif result['state'] == 'FAILED_RETAINED' and result['data'].get('mutationDispatched') is False:\n"
        "                from recovery_resource_admission import release_no_mutation\n"
        "                result['originalResultPins'].append(release_no_mutation(configuration, request, root,\n"
        "                    pin(worker_output), receipt_pin))\n")
    replace('common/recovery_minimal.py',
        "                result['originalResultPins'].extend([pin(root/'worker-result.json'), receipt_pin])\n",
        "                result['originalResultPins'].extend([pin(root/'worker-result.json'), receipt_pin])\n"
        "                if result['state'] == 'SUCCEEDED' and (root/'resource-reservation.json').exists():\n"
        "                    from recovery_resource_admission import release_success\n"
        "                    result['originalResultPins'].append(release_success(configuration, request, root,\n"
        "                        pin(root/'worker-result.json'), receipt_pin))\n"
        "                elif result['state'] == 'FAILED_RETAINED' and result['data'].get('mutationDispatched') is False:\n"
        "                    from recovery_resource_admission import release_no_mutation\n"
        "                    result['originalResultPins'].append(release_no_mutation(configuration, request, root,\n"
        "                        pin(root/'worker-result.json'), receipt_pin))\n")
    replace('common/recovery_minimal.py',
        "    write(root/'result.json', result)\n    publish(output, result)\n    return result\n",
        "    for evidence in root.glob('resource-*.json'):\n"
        "        reference = pin(evidence)\n"
        "        if reference not in result['originalResultPins']:\n"
        "            result['originalResultPins'].append(reference)\n"
        "    write(root/'result.json', result)\n    publish(output, result)\n    return result\n")
    replace('common/recovery_minimal_runtime.py',
        "        reservation = absolute(target['dataRoot'])/'.recovery-operation.json'\n",
        "        from recovery_resource_admission import admit\n"
        "        admit(configuration, request, root, 'target', reservation_configuration=reservation_configuration)\n"
        "        reservation = absolute(target['dataRoot'])/'.recovery-operation.json'\n")
    # The control plane is shared by both modes. Authenticate the frozen
    # modules before applying the reviewed execution and automatic-chain fixes;
    # never copy lightweight archive/data readers into the safe package.
    for name, expected in {
        'recovery_control_smallapp.py': 'a5dfbb9173a77eae43227869f92e834abccb195d2bcd4020322501386690d508',
        'recovery_control_smallapp_native.py': '1ddb9e448f1a96cc33835429b4e86ddc0c72daee741c516008eeeb206e89f043',
        'recovery_control_executor.py': '5b69c014cfe2838891a9cc1b22965d5e5288306e4344dd8fd3a25a8499f8c136',
        'recovery_control_smallapp_http.py': 'f3046ea7b16dbfb2f39ed25c5ab0fa5647f1056eb21b90127a6d109e38789f6f',
    }.items():
        path = 'control/' + name
        if hashlib.sha256(payload[path].replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('STANDARD_CONTROL_BASELINE_CHANGED ' + name)
        payload[path] = (root/'backend/src/main/resources'/name).read_bytes()
    payload['control/recovery_control_incremental_plan.py'] = (
        root/'backend/src/main/resources/recovery_control_incremental_plan.py').read_bytes()
    payload['common/recovery_backup_epoch.py'] = (root/'ops/recovery/recovery_backup_epoch.py').read_bytes()
    program_restore_handoff(payload, root)
    program_worker_handoff(payload, root)
    target_preservation_capture(payload, root)
    target_preservation_repository(payload, root)
    restore_admission_metadata(payload, root)
    physical_restore_reads(payload, root)
    prepare_target_bind_mounts(payload, root)
    prepared_database_readback(payload, root)
    prepared_service_health(payload, root)
    application_database_phase(payload)
    return payload
