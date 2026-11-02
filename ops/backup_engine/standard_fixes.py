"""Reviewed safe-engine fixes applied to the authenticated frozen baseline.

Patch contexts fail closed. The stored baseline and its original checks remain
intact; timing transforms additionally compare the original statement AST.
"""
from pathlib import Path
import hashlib

from standard_timing import backup_timings, restore_timings


def apply(payload):
    payload = dict(payload)
    root = Path(__file__).resolve().parents[2]

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
    # Install the one continuous inode lease before the frozen strict readers
    # collect identity baselines. All original hash/metadata checks remain.
    replace('common/recovery_minimal_runtime.py',
        '    def __init__(self, configuration, request, source, policy, chain, target, root, input_pins):\n',
        '''    def __init__(self, configuration, request, source, policy, chain, target, root, input_pins):
        self.archive_guard = None
        try:
            self._initialize(configuration, request, source, policy, chain, target, root, input_pins)
        except BaseException:
            if self.archive_guard is not None:
                self.archive_guard.close()
            raise

    def _initialize(self, configuration, request, source, policy, chain, target, root, input_pins):
''')
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
    old = 'def execute(configuration, request, root, input_pins):\n'
    new = '''def execute(configuration, request, root, input_pins):
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
    # The control plane is shared by both modes. These authenticated baseline
    # modules differed from the current sources only by the reviewed OOM fix;
    # do not copy any lightweight archive/data reader into the safe package.
    for name, expected in {
        'recovery_control_smallapp_native.py': '1ddb9e448f1a96cc33835429b4e86ddc0c72daee741c516008eeeb206e89f043',
        'recovery_control_executor.py': '5b69c014cfe2838891a9cc1b22965d5e5288306e4344dd8fd3a25a8499f8c136',
    }.items():
        path = 'control/' + name
        if hashlib.sha256(payload[path].replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('STANDARD_CONTROL_BASELINE_CHANGED ' + name)
        payload[path] = (root/'backend/src/main/resources'/name).read_bytes()
    return payload
