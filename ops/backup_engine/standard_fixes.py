"""Reviewed safe-engine fixes applied to the authenticated frozen baseline.

Patch contexts fail closed. The stored baseline and its original checks remain
intact; timing transforms additionally compare the original statement AST.
"""
from pathlib import Path

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
    name = 'common/recovery_minimal_runtime.py'
    old = 'def execute(configuration, request, root, input_pins):\n'
    new = '''def execute(configuration, request, root, input_pins):
    from recovery_replace import enabled, execute as replace
    if enabled(configuration['targets'][request['targetConfigRef']]):
        return replace(configuration, request, root, input_pins, execute_empty, MinimalData, selected_chain)
    return execute_empty(configuration, request, root, input_pins)


def execute_empty(configuration, request, root, input_pins):
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
    return payload
