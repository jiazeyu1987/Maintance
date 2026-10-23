"""Add step boundaries to the authenticated standard restore implementation.

Exact source matches are deliberate: a changed baseline must be reviewed before
building. The existing restore statements and verification remain intact.
"""
import ast
from pathlib import Path


def restore_timings(payload):
    payload = dict(payload)
    name = 'common/recovery_minimal_runtime.py'
    source = payload[name].decode('utf8').replace('\r\n', '\n')
    original_tree = ast.parse(source)

    def wrap(block, stage, root='native.root'):
        nonlocal source
        if source.count(block) != 1:
            raise ValueError('STANDARD_TIMING_SOURCE_CHANGED ' + stage)
        indent = block[:len(block) - len(block.lstrip())]
        wrapped = indent + "with step_timing(" + root + ", " + repr(stage) + "):\n"
        wrapped += ''.join('    ' + line if line.strip() else line for line in block.splitlines(keepends=True))
        source = source.replace(block, wrapped)

    if source.count('from recovery_data import NativeData\n') != 1:
        raise ValueError('STANDARD_TIMING_IMPORT_CHANGED')
    source = source.replace('from recovery_data import NativeData\n',
        'from recovery_data import NativeData\nfrom recovery_step_timing import step as step_timing\n')
    start = source.index('    source, policy, chain = selected_chain(configuration, request)\n')
    end = source.index('    try:\n        native.fresh_target()', start)
    wrap(source[start:end], 'restore-admission', 'root')
    wrap('        native.fresh_target()\n', 'target-checks', 'root')
    wrap('            result = native.full_database() if index == 0 else native.incremental_database()\n'
         "            db_pins.append(write(native.root/'result.json', result))\n", 'database-restore')
    wrap("            object_pins.append(write(native.root/'result.json', native.physical_object_chain()))\n",
         'object-restore')
    wrap('                result = native.full_objects() if index == 0 else native.incremental_objects()\n'
         "                object_pins.append(write(native.root/'result.json', result))\n", 'object-restore')
    wrap("        consistent = write(native.root/'consistency.json', native.consistency())\n", 'consistency')
    wrap("        derived = write(native.root/'derived.json', rebuild(native))\n", 'redis-rebuild')
    wrap("        application = write(native.root/'application-start.json', native.start_application())\n",
         'application-start')
    wrap("        for step in chain:\n"
         "            for ref in step[2]['payloadPins']:\n"
         "                check_pin(ref, content=False)\n", 'archive-verification')
    wrap("        cleanup_pin = pin(cleanup(root, restore_paths(root), request['operationId'], guard=native.guard))\n",
         'restore-cleanup', 'root')
    compile(source, name, 'exec')
    class OriginalStatements(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            return None if node.module == 'recovery_step_timing' else node

        def visit_With(self, node):
            node = self.generic_visit(node)
            if (len(node.items) == 1 and isinstance(node.items[0].context_expr, ast.Call)
                    and isinstance(node.items[0].context_expr.func, ast.Name)
                    and node.items[0].context_expr.func.id == 'step_timing'):
                return node.body
            return node

    observed = OriginalStatements().visit(ast.parse(source))
    if ast.dump(observed) != ast.dump(original_tree):
        raise ValueError('STANDARD_RESTORE_STATEMENTS_CHANGED')
    payload[name] = source.encode()
    helper_name = 'common/recovery_step_timing.py'
    if helper_name in payload:
        raise ValueError('STANDARD_TIMING_ALREADY_INSTALLED')
    payload[helper_name] = (Path(__file__).parents[1]/'recovery/recovery_step_timing.py').read_bytes()
    return payload


def backup_timings(payload):
    """Time the original safe publish stages, preserving every original statement."""
    payload = dict(payload)
    name = 'common/repository_minimal.py'
    source = payload[name].decode('utf8').replace('\r\n', '\n')
    original_tree = ast.parse(source)
    anchor = 'from staging_cleanup import cleanup, capture_paths\n'
    if source.count(anchor) != 1:
        raise ValueError('STANDARD_BACKUP_TIMING_IMPORT_CHANGED')
    source = source.replace(anchor, anchor + 'from recovery_step_timing import step as step_timing\n')

    def wrap(block, stage):
        nonlocal source
        if source.count(block) != 1:
            raise ValueError('STANDARD_BACKUP_TIMING_SOURCE_CHANGED ' + stage)
        indent = block[:len(block)-len(block.lstrip())]
        source = source.replace(block, indent + 'with step_timing(operation, ' + repr(stage) + '):\n' +
            ''.join('    '+line if line.strip() else line for line in block.splitlines(keepends=True)))

    def between(first, following, stage):
        start = source.index(first, source.index('def publish('))
        end = source.index(following, start)
        wrap(source[start:end], stage)

    between("    require(request['action'] in ('FULL', 'INCREMENTAL'), 'REPOSITORY_ARCHIVE_ACTION_UNSUPPORTED')\n",
        "    # The configured adapter is W02's real capture CLI, shared by all apps.\n", 'archive-admission')
    between("    command = list(config.source['captureCommand'])\n",
        "    root = safe_path(result['data']['captureRoot'])\n", 'source-capture')
    between("    root = safe_path(result['data']['captureRoot'])\n",
        '    publisher = CapturedPublisher(config, root, tree, request, deadline)\n', 'capture-validation')
    between('    publisher = CapturedPublisher(config, root, tree, request, deadline)\n',
        "    sidecar = target / '.repository'\n", 'nas-upload')
    between("    sidecar = target / '.repository'\n",
        '    with SmbReadback(smb_configuration(config, operation, deadline), deadline) as reader:\n', 'archive-metadata')
    between('    with SmbReadback(smb_configuration(config, operation, deadline), deadline) as reader:\n        connection_id, originals = reader.verify',
        '    config.current()\n', 'nas-readback')
    between('    catalog.chain(point_pin, candidate=point)\n',
        '    # Publish COMPLETE only after readback; operation success also needs cleanup.\n', 'archive-final-verification')
    between('    cleanup_pin = pin_file(cleanup(root, capture_paths(root), request[\'operationId\'],\n',
        '    # Recheck the published chain with the local captured payloads gone.\n', 'capture-cleanup')
    wrap('    catalog.chain(point_pin)\n', 'archive-chain-readback')
    compile(source, name, 'exec')

    class OriginalStatements(ast.NodeTransformer):
        def visit_ImportFrom(self, node):
            return None if node.module == 'recovery_step_timing' else node

        def visit_With(self, node):
            node = self.generic_visit(node)
            if (len(node.items) == 1 and isinstance(node.items[0].context_expr, ast.Call)
                    and isinstance(node.items[0].context_expr.func, ast.Name)
                    and node.items[0].context_expr.func.id == 'step_timing'):
                return node.body
            return node

    if ast.dump(OriginalStatements().visit(ast.parse(source))) != ast.dump(original_tree):
        raise ValueError('STANDARD_BACKUP_STATEMENTS_CHANGED')
    payload[name] = source.encode()
    helper = (Path(__file__).parents[1]/'recovery/recovery_step_timing.py').read_bytes()
    helper_name = 'common/recovery_step_timing.py'
    if helper_name in payload and payload[helper_name] != helper:
        raise ValueError('STANDARD_TIMING_HELPER_CHANGED')
    payload[helper_name] = helper
    return payload
