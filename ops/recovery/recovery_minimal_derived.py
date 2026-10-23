"""Reuse the real smallapp Redis rebuild and absolute-expiry readback."""
import importlib
from pathlib import Path
import sys

from recovery_engine import absolute, check_pin, pinned_json, require, write


def rebuild(native):
    import json
    import time
    inventory = pinned_json(native.material['derivedInventoryPin'])
    results = []
    for name, item in inventory['classes'].items():
        if item['classification'] == 'NOT_PRESENT':
            results.append(dict(className=name, classification='NOT_PRESENT'))
            continue
        if name == 'redis' and item['classification'] == 'RESTORE':
            from recovery_minimal_redis_dump import restore
            results.append(restore(native, item))
            continue
        if name != 'redis' or item['classification'] != 'REBUILD' or item['rebuildFrom'] != 'DATABASE':
            raise ValueError('Unsupported derived-data operation')
        adapter = native.config['redisRebuild']
        if adapter['kind'] != 'SMALLAPP_SESSIONS':
            raise ValueError('Unsupported Redis rebuild adapter')
        sys.path.insert(0, str(absolute(adapter['moduleDirectory'])))
        core = importlib.import_module('core'); cache = importlib.import_module('redis_cache')
        settings = core.config(pinned_json(adapter['configurationPin']))
        store = core.Store(settings, pinned_json(adapter['secretsPin']))
        rebuilt = 0
        try:
            # Read only the session records required to rebuild this derived cache.
            with store.transaction() as cursor:
                cursor.execute('SELECT s.session_hash,s.tenant_id,s.user_id,s.csrf,s.expires_at,u.username '
                    'FROM smallapp_sessions s JOIN smallapp_users u '
                    'ON u.id=s.user_id AND u.tenant_id=s.tenant_id '
                    'WHERE s.tenant_id=%s AND u.active=1 AND s.expires_at>UTC_TIMESTAMP(6) '
                    'ORDER BY s.session_hash', (store.tenant,))
                rows = cursor.fetchall()
            for row in rows:
                native.guard()
                value = cache.session_value(row)
                if value['expiresAtMilliseconds'] <= int(time.time()*1000):
                    continue
                native.mutation_dispatched = True
                accepted = store.cache.client.set(cache.cache_key(store.cache.prefix, row['session_hash']),
                    json.dumps(value, separators=(',', ':'), sort_keys=True).encode('utf-8'),
                    pxat=value['expiresAtMilliseconds'])
                require(accepted is True, 'REDIS_REBUILD_WRITE_FAILED')
                rebuilt += 1
        finally:
            store.cache.client.close(); store.s3.close()
        results.append(dict(className=name, classification='REBUILD', rebuiltCount=rebuilt,
            verificationState='NOT_PERFORMED'))
    return dict(recoveryPoint=native.plan['recoveryPoint'], classes=results, verificationState='NOT_PERFORMED')
