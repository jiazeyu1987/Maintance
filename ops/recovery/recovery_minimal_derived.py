"""Reuse the real smallapp Redis rebuild and absolute-expiry readback."""
import importlib
from pathlib import Path
import sys

from recovery_engine import absolute, check_pin, pinned_json, require, write


def rebuild(native):
    inventory = pinned_json(native.material['derivedInventoryPin'])
    results = []
    for name, item in inventory['classes'].items():
        if item['classification'] == 'NOT_PRESENT':
            require(item['requiredForBusiness'] is False and item['payloadPins'] == [] and
                    item['executorKey'] is None, 'REQUIRED_DERIVED_DATA_CANNOT_BE_ABSENT')
            results.append(dict(className=name, classification='NOT_PRESENT'))
            continue
        require(name == 'redis' and item['classification'] == 'REBUILD' and item['rebuildFrom'] == 'DATABASE' and
                item['payloadPins'] == [], 'DERIVED_ADAPTER_NOT_CONFIGURED')
        adapter = native.config['redisRebuild']
        require(adapter['kind'] == 'SMALLAPP_SESSIONS', 'DERIVED_ADAPTER_NOT_SUPPORTED')
        root = absolute(adapter['moduleDirectory']); sys.path.insert(0, str(root))
        core = importlib.import_module('core'); cache = importlib.import_module('redis_cache')
        require(all(Path(module.__file__).resolve().parent == root for module in (core, cache)),
                'DERIVED_MODULE_WRONG_ORIGIN')
        configuration = pinned_json(adapter['configurationPin'])
        secret_pin = adapter['secretsPin']
        require(absolute(secret_pin['path']).stat().st_mode & 0o077 == 0, 'SECRET_NOT_PRIVATE')
        private = pinned_json(secret_pin)
        settings = core.config(configuration)
        from recovery_minimal_runtime import json_value
        require(adapter['versionPin'] in native.material['versionPins'] and
                json_value(adapter['versionPin'], adapter['versionValuePath']) == settings['version'],
                'DERIVED_ARCHIVED_APPLICATION_VERSION_MISMATCH')
        require(tuple(map(int, settings['redis']['serverVersion'].split('.'))) >= (7, 0, 0),
                'REDIS_ABSOLUTE_EXPIRY_READBACK_UNSUPPORTED')
        require(settings['runtimeRole'] == 'TARGET' and settings['startState'] == 'PROTECTED' and
                settings['database']['name'] == native.config['database'] and
                settings['database']['host'] == native.config_services['mysql']['ip'] and
                settings['database']['port'] == 3306 and
                settings['s3']['endpoint'] == 'http://'+native.config_services['minio']['ip']+':9000' and
                settings['s3']['bucket'] in native.config['buckets'] and
                settings['redis']['host'] == native.config_services['redis']['ip'], 'DERIVED_TARGET_BINDING_MISMATCH')
        require(settings['redis']['port'] == 6379, 'DERIVED_TARGET_BINDING_MISMATCH')
        artifacts = native.config['application']['artifactBindings']
        for module in (core, cache):
            require(any(binding['targetPin']['path'] == str(Path(module.__file__).resolve()) and
                        binding['archivePin']['sha256'] == binding['targetPin']['sha256'] for binding in artifacts),
                    'DERIVED_APPLICATION_CODE_NOT_ARCHIVED')
        from recovery_data_redis_sessions import independent_readback, session_provenance
        reference, provenance = session_provenance(native, {'rebuildFromPin': native.request['databaseResultPin']})

        def guard():
            native.bound()
            check_pin(adapter['configurationPin']); check_pin(secret_pin)

        guard(); store = core.Store(settings, private)
        try:
            native.mutation_dispatched = True
            observation = store.rebuild_redis_from_database(guard)
        finally:
            store.cache.client.close(); store.s3.close()
        require(observation['schemaVersion'] == 'SmallAppRedisRebuildObservation/v1' and
                observation['state'] == 'READ_BACK' and observation['version'] == settings['version'] and
                observation['runtimeRole'] == 'TARGET' and observation['gateState'] == 'PROTECTED',
                'REDIS_BUSINESS_READBACK_REQUIRED')
        guard(); observer = core.Store(settings, private)
        try:
            readback = independent_readback(observer, cache, guard, reference, native.plan['recoveryPoint'], provenance)
        finally:
            observer.cache.client.close(); observer.s3.close()
        results.append(dict(className=name, classification='REBUILD',
            observationPin=write(native.root/'redis-business-rebuild.json', observation),
            readbackPin=write(native.root/'redis-independent-readback.json', readback)))
    native.bound()
    return dict(recoveryPoint=native.plan['recoveryPoint'], classes=results)
