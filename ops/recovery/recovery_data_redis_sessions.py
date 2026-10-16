"""Approved derived adapter: rebuild a bound target's SQL-authoritative sessions.

The common recovery engine still restores SQL, binlogs and objects. This child
only invokes the registered application's existing Redis rebuild callable.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime, timezone
import importlib
from importlib.metadata import version
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import urlsplit

from recovery_engine import (Budget, RecoveryError, absolute, authorities, check_pin,
    digest, pin, pinned_json, require, utc, validate_record, write, persist_evidence)
from recovery_engine_read_guard import inherit_read_guard
from recovery_plan import immutable_inputs, prepared_target, resolve_chain, trusted_configuration

EXECUTOR_KEY = 'smallapp.redis-session-cache.mysql.v1'
FIELDS = set(('schemaVersion operationId requestId action className targetIdentityPin recoveryPoint '
              'classificationPin originalRequestPin planPin recoveryTargetPin inputPins rebuildFromPin '
              'deadlineMilliseconds').split())


def request_contract(request):
    require(type(request) is dict and set(request) == FIELDS and
            request['schemaVersion'] == 'RecoveryDerivedRequest/v1' and
            request['action'] == 'DERIVED_REBUILD' and request['className'] == 'redis' and
            request['inputPins'] == [] and request['rebuildFromPin'] is not None,
            'REDIS_DERIVED_REQUEST_INVALID')


def registration(policy, trust):
    require(EXECUTOR_KEY in policy['derivedAdapters'], 'DERIVED_EXECUTOR_NOT_REGISTERED')
    adapter = policy['derivedAdapters'][EXECUTOR_KEY]
    require(adapter['className'] == 'redis' and adapter['classification'] == 'REBUILD' and
            adapter['scriptPin'] == pin(__file__) and adapter['scriptPin'] in policy['moduleSourcePins'] and
            adapter['scriptPin']['sha256'] in trust['derivedExecutorSha256s'],
            'DERIVED_EXECUTOR_NOT_APPROVED')
    return adapter


def database_result(request, material, database_uuid):
    database = pinned_json(request['rebuildFromPin'])
    require(database['recoveryPoint'] == request['recoveryPoint'] == material['recoveryPoint'] and
            database['endPosition'] == material['database']['endPosition'] and
            database['databaseUuid'] == database_uuid and
            database['fullSchemaDataEquivalenceVerified'] is True,
            'REDIS_RESTORED_DATABASE_REQUIRED')
    for ref in (database['observedPin'], database['comparisonPin']): check_pin(ref, content=False)


def target_configuration(settings, native, adapter):
    """Registered endpoints must refer to the already inspected target services."""
    require(settings['version'] == adapter['version'] and settings['runtimeRole'] == 'TARGET' and
            settings['startState'] == 'PROTECTED' and settings['tenantId'] == 122 and
            settings['username'] == 'aoteman' and settings['database']['name'] == native.config['database'] and
            settings['redis']['database'] == 0 and adapter['imagePins'] == native.config['imagePins'],
            'REDIS_APPLICATION_TARGET_BINDING_INVALID')
    endpoints = pinned_json(native.config['configurationPin'])['endpointMap']
    for role, key, endpoint in (('mysql', 'database', settings['database']),
                                ('redis', 'redis', settings['redis'])):
        require(endpoint['host'] in (role, native.config_services[role]['ip']) and
                endpoint['host'] == endpoints[key]['host'] and endpoint['port'] == endpoints[key]['port'],
                'REDIS_APPLICATION_ENDPOINT_MISMATCH')
    storage = urlsplit(settings['s3']['endpoint'])
    require(storage.hostname in ('minio', native.config_services['minio']['ip']) and
            storage.hostname == endpoints['objectStore']['host'] and
            (storage.port or (443 if storage.scheme == 'https' else 80)) == endpoints['objectStore']['port'] and
            settings['s3']['bucket'] in native.config['buckets'] and
            settings['redis']['instanceId'] == native.config_services['redis']['name'],
            'REDIS_APPLICATION_OBJECT_OR_INSTANCE_MISMATCH')


def application_modules(adapter):
    """Load the complete provisioned application Python closure, with no search fallback."""
    pins = adapter['moduleSourcePins']
    roots = {absolute(ref['path']).parent for ref in pins}
    require(len(roots) == 1, 'REDIS_APPLICATION_MODULE_ROOT_INVALID')
    root = roots.pop()
    require({absolute(ref['path']) for ref in pins} == set(root.glob('*.py')) and
            {root/'core.py', root/'redis_cache.py'} <= {absolute(ref['path']) for ref in pins},
            'REDIS_APPLICATION_MODULE_CLOSURE_REQUIRED')
    for ref in pins: check_pin(ref, content=False)
    require('core' not in sys.modules and 'redis_cache' not in sys.modules, 'REDIS_APPLICATION_ALREADY_IMPORTED')
    sys.path.insert(0, str(root))
    core = importlib.import_module('core'); cache = importlib.import_module('redis_cache')
    require(Path(core.__file__).resolve() == root/'core.py' and
            Path(cache.__file__).resolve() == root/'redis_cache.py' and
            core.VERSION == adapter['version'] and cache.EXECUTOR_KEY == EXECUTOR_KEY,
            'REDIS_APPLICATION_VERSION_OR_ORIGIN_MISMATCH')
    for ref in pins: check_pin(ref, content=False)
    require(len(adapter['toolPins']) == 1 and absolute(adapter['toolPins'][0]['path']) == root/'requirements.txt',
            'REDIS_APPLICATION_REQUIREMENTS_REQUIRED')
    for line in check_pin(adapter['toolPins'][0]).decode('ascii').splitlines():
        name, expected = line.split('==')
        require(version(name) == expected, 'REDIS_APPLICATION_DEPENDENCY_VERSION_MISMATCH')
    return core, cache


def private_envelope(adapter, native):
    """Use existing independent secret custody; read approved bytes through a private FD."""
    require(len(adapter['secretRefs']) == 1 and adapter['secretRefs'][0] in native.config['secretRefs'] and
            native.target['secretRefs'] == native.config['secretRefs'], 'REDIS_PRIVATE_ROLE_BINDING_REQUIRED')
    reference = pinned_json(adapter['secretRefs'][0])
    require(reference['schemaVersion'] == 'RecoverySecretReference/v1' and
            reference['service'] == 'backend' and reference['environment'] == 'SMALLAPP_BACKEND_PRIVATE' and
            reference['provider'] == 'FILE' and reference['custody'] == 'INDEPENDENT',
            'REDIS_PRIVATE_ROLE_CUSTODY_REQUIRED')
    ref = reference['filePin']; path = absolute(ref['path'])
    require(not path.is_symlink(), 'REDIS_PRIVATE_FILE_UNSAFE')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1 and
                stat.S_IMODE(info.st_mode) == 0o600 and 0 < info.st_size <= 65536,
                'REDIS_PRIVATE_FILE_UNSAFE')
        raw = stream.read(65537)
        import hashlib
        require(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'] and
                (info.st_dev, info.st_ino) == (path.stat().st_dev, path.stat().st_ino),
                'REDIS_PRIVATE_FILE_CHANGED')
    from recovery_engine import parse
    value = parse(raw)
    require(set(value) == {'config', 'secrets'} and value['config'] == pinned_json(adapter['configurationPin']),
            'REDIS_PRIVATE_CONFIGURATION_MISMATCH')
    return value


def external_isolation(native, phase):
    """Native network/firewall readback is independent of the business callable."""
    start = len(native.original_pins)
    native.bound()
    require(len(native.original_pins) > start, 'REDIS_EXTERNAL_ISOLATION_READBACK_REQUIRED')
    return write(native.root/('external-'+phase.lower()+'.json'), dict(
        schemaVersion='RecoveryDerivedExternalDispatchObservation/v1', operationId=native.original['operationId'],
        targetIdentityPin=native.target['targetIdentityPin'], recoveryPoint=native.plan['recoveryPoint'],
        phase=phase, externalDispatchBlocked=True, isolationProofPin=native.target['isolationProofPin'],
        sideEffectIsolationPin=native.target['sideEffectIsolationPin'],
        originalInvocationPins=list(native.original_pins[start:]), observedAt=utc()))


def original_expiry(expires_ms, raw, ttl, before_ms, after_ms):
    """Bound PTTL by the original absolute expiry and actual Redis TIME window."""
    require(all(type(value) is int for value in (expires_ms, ttl, before_ms, after_ms)) and
            before_ms <= after_ms, 'REDIS_EXPIRY_READBACK_INVALID')
    if expires_ms <= after_ms:
        require(raw is None or ttl == -2 or ttl >= 0, 'REDIS_EXPIRED_SESSION_READBACK_INVALID')
        return False
    require(type(raw) is bytes and 0 <= expires_ms-after_ms <= ttl <= expires_ms-before_ms,
            'REDIS_ORIGINAL_EXPIRY_NOT_PRESERVED')
    return True


def archived_expiries(reference, recovery_point, rows):
    """Match every restored expiry to an occurrence in the pinned SQL projection.

    Private session identities stay in memory. Duplicate projected rows retain
    multiplicity; the original full-table comparison binds the private columns.
    """
    require(reference['schemaVersion'] == 'RecoveryReferenceInventory/v1' and
            reference['complete'] is True and reference['recoveryPoint'] == recovery_point and
            type(reference['databaseRows']) is list and len(rows) <= 10000,
            'REDIS_ARCHIVED_SESSION_INVENTORY_REQUIRED')
    originals = defaultdict(deque); count = 0
    for index, row in enumerate(reference['databaseRows']):
        if row['table'] != 'smallapp_sessions': continue
        require(set(row) == {'table', 'tenant_id', 'user_id', 'expires_at'} and
                row['tenant_id'] == '122' and type(row['user_id']) is str and
                re.fullmatch(r'[1-9][0-9]{0,18}', row['user_id']) and int(row['user_id']) < 2**63 and
                type(row['expires_at']) is str and
                re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?',
                             row['expires_at']), 'REDIS_ARCHIVED_SESSION_ROW_INVALID')
        expiry = datetime.fromisoformat(row['expires_at'])
        originals[(122, int(row['user_id']), expiry)].append((index, expiry))
        count += 1
        require(count <= 10000, 'REDIS_SESSION_READBACK_LIMIT')
    require(count == len(rows), 'REDIS_ARCHIVED_SESSION_COUNT_MISMATCH')
    matches = []
    for row in rows:
        require(type(row['tenant_id']) is int and row['tenant_id'] == 122 and
                type(row['user_id']) is int and type(row['expires_at']) is datetime and
                row['expires_at'].tzinfo is None, 'REDIS_RESTORED_SESSION_ROW_INVALID')
        key = (row['tenant_id'], row['user_id'], row['expires_at'])
        require(key in originals and originals[key], 'REDIS_ARCHIVED_SQL_EXPIRY_MISMATCH')
        index, original = originals[key].popleft()
        delta = original.replace(tzinfo=timezone.utc)-datetime(1970, 1, 1, tzinfo=timezone.utc)
        milliseconds = (delta.days*86400+delta.seconds)*1000+delta.microseconds//1000
        matches.append(dict(referenceRowIndex=index, originalSqlExpiresAtUtc=original.isoformat(
                            timespec='microseconds')+'Z', originalSqlExpiryUtcMilliseconds=milliseconds))
    require(not any(originals.values()), 'REDIS_ARCHIVED_SESSION_COUNT_MISMATCH')
    return matches


def expiry_observation(match, expires_ms, raw, ttl, cache_expiry, before_ms, after_ms):
    """Retain measured scalars only; never serialize a cache payload or identity."""
    require(type(cache_expiry) is int and type(expires_ms) is int and 0 < expires_ms < 2**53 and
            match['originalSqlExpiryUtcMilliseconds'] == expires_ms,
            'REDIS_ABSOLUTE_EXPIRY_READBACK_INVALID')
    accepted = original_expiry(expires_ms, raw, ttl, before_ms, after_ms)
    if accepted:
        require(cache_expiry == expires_ms, 'REDIS_ABSOLUTE_EXPIRY_CHANGED')
    else:
        require(raw is None and ttl == -2 and cache_expiry == -2, 'REDIS_EXPIRED_SESSION_REVIVED')
    return dict(referenceRowIndex=match['referenceRowIndex'],
                originalSqlExpiresAtUtc=match['originalSqlExpiresAtUtc'],
                originalSqlExpiryUtcMilliseconds=match['originalSqlExpiryUtcMilliseconds'],
                restoredSqlExpiryUtcMilliseconds=expires_ms,
                cacheExpiryUtcMilliseconds=cache_expiry if accepted else None,
                observedAtUtcMilliseconds=after_ms, observedBeforeUtcMilliseconds=before_ms,
                pttlMilliseconds=ttl, redisExpireTimeMilliseconds=cache_expiry, accepted=accepted,
                decision='LIVE_ACCEPTED' if accepted else 'EXPIRED_ABSENT')


def session_provenance(native, request):
    """Recheck actual archived/full-table originals, not their aggregate success flag."""
    reference_pin = native.material['referenceInventoryPin']
    expected_pin = native.material['database']['expectedDataPin']
    require(reference_pin in native.material['payloadPins'] and expected_pin in native.material['payloadPins'],
            'REDIS_SESSION_ORIGINALS_NOT_ARCHIVED')
    database = pinned_json(request['rebuildFromPin'])
    expected = pinned_json(expected_pin); observed = pinned_json(database['observedPin'])
    require(expected['observationIdentity']['databaseUuid'] == native.material['sourceDatabaseUuid'] and
            observed['observationIdentity']['databaseUuid'] == native.db_uuid,
            'REDIS_SESSION_DATABASE_PROVENANCE_MISMATCH')
    comparison = native.modules['formal_data_evidence'].compare_data(expected, observed)
    require(comparison == pinned_json(database['comparisonPin']), 'REDIS_SESSION_DATABASE_COMPARISON_CHANGED')
    reference = pinned_json(reference_pin)
    require(sum(row['table'] == 'smallapp_sessions' for row in reference['databaseRows']) ==
            expected['tables']['smallapp_sessions']['rows'], 'REDIS_SESSION_ARCHIVE_PROJECTION_INCOMPLETE')
    return reference, dict(referenceInventoryPin=reference_pin, expectedDataPin=expected_pin,
                           databaseResultPin=request['rebuildFromPin'], observedPin=database['observedPin'],
                           comparisonPin=database['comparisonPin'])


def independent_readback(store, cache, guard, reference, recovery_point, provenance):
    """A separate Store/client reads authoritative rows and exact cache expiry."""
    guard(); store.environment(); guard(); store.require_clean(); guard()
    with store.transaction() as cur:
        cur.execute('SELECT s.session_hash,s.tenant_id,s.user_id,s.csrf,s.expires_at,u.username '
                    'FROM smallapp_sessions s JOIN smallapp_users u '
                    'ON u.id=s.user_id AND u.tenant_id=s.tenant_id '
                    'WHERE s.tenant_id=%s AND u.active=1 '
                    'ORDER BY s.session_hash LIMIT 10001', (store.tenant,))
        rows = cur.fetchall()
    require(len(rows) <= 10000, 'REDIS_SESSION_READBACK_LIMIT')
    guard()
    matches = archived_expiries(reference, recovery_point, rows)
    client = store.cache.client; expected = {}; observations = []; live = 0
    for ordinal, (row, match) in enumerate(zip(rows, matches)):
        guard(); value = cache.session_value(row)
        key = cache.cache_key(store.cache.prefix, row['session_hash'])
        expected[key.encode('utf-8')] = value
        before = client.time(); raw = client.get(key); ttl = client.pttl(key)
        cache_expiry = client.pexpiretime(key); after = client.time()
        before_ms = before[0]*1000 + before[1]//1000; after_ms = after[0]*1000 + after[1]//1000
        if value['expiresAtMilliseconds'] <= after_ms:
            # A key may expire during the first read. Prove actual absence with
            # fresh GET/PTTL/PEXPIRETIME; an elapsed clock alone is insufficient.
            guard(); before = client.time(); raw = client.get(key); ttl = client.pttl(key)
            cache_expiry = client.pexpiretime(key); after = client.time(); guard()
            before_ms = before[0]*1000 + before[1]//1000; after_ms = after[0]*1000 + after[1]//1000
        measured = expiry_observation(match, value['expiresAtMilliseconds'], raw, ttl, cache_expiry,
                                     before_ms, after_ms)
        if measured['accepted']:
            cache.decode_value(raw, value, after_ms)
            live += 1
        observations.append(dict(measured, sessionOrdinal=ordinal))
        guard()
    checked = set(); cursor = 0
    while True:
        guard(); cursor, keys = client.scan(cursor=cursor, count=100); guard()
        for key in keys:
            require(key in expected, 'REDIS_UNAUTHORIZED_SESSION_KEY')
            guard(); seconds, micros = client.time(); guard()
            if expected[key]['expiresAtMilliseconds'] <= seconds*1000 + micros//1000:
                guard(); raw = client.get(key); guard()
                require(raw is None, 'REDIS_EXPIRED_SESSION_REVIVED')
            checked.add(key)
            require(len(checked) <= 10000, 'REDIS_SESSION_READBACK_LIMIT')
        if cursor == 0: break
    guard(); health = store.cache.health(); guard()
    return dict(schemaVersion='SmallAppRedisIndependentReadback/v2', version=store.settings['version'],
                runtimeRole='TARGET', gateState=store.gate.state, database=0, recoveryPoint=recovery_point,
                rows=observations, expiryTimeUnit='UTC_UNIX_MILLISECONDS', sqlExpiryPrecision='MICROSECONDS',
                liveRowsRead=live, expiredRowsRead=len(rows)-live, keysRead=len(checked),
                originalAbsoluteExpiryVerified=True, health=health, observedAt=utc(), **provenance)


def execute(request, root):
    request_contract(request)
    budget = Budget(request['deadlineMilliseconds']); original = pinned_json(request['originalRequestPin'])
    trust, policy, config = trusted_configuration(original); adapter = registration(policy, trust)
    identity = pinned_json(policy['dataTargetPin'])['targetIdentityPin']
    authorities(original, identity, ['RESTORE_EXECUTE'], trust)
    inherit_read_guard(original, request['originalRequestPin'], policy, budget)
    plan = validate_record(pinned_json(request['planPin']), 'RestorePlan', policy['recordSchemasPin'])
    chain = resolve_chain(original['selectedPointPin'], policy); material_pin = chain[-1][3]; material = chain[-1][2]
    require(plan['immutableInputsSha256'] == digest(immutable_inputs(original, policy, chain)) and
            plan['operationId'] == request['operationId'] == original['operationId'] and
            plan['candidatePin'] == original['selectedPointPin'] and plan['targetRef'] == original['sourceOrTargetRef'] and
            plan['orderedChainPins'] == [step[0] for step in chain] and
            request['deadlineMilliseconds'] <= original['deadlineMilliseconds'], 'REDIS_DERIVED_PLAN_MISMATCH')
    target = prepared_target(dict(original, inputPins={'recoveryTarget': request['recoveryTargetPin']}), plan, policy, trust)
    require(request['targetIdentityPin'] == target['targetIdentityPin'] and
            request['recoveryPoint'] == plan['recoveryPoint'] == material['recoveryPoint'] and
            request['classificationPin'] == material['derivedInventoryPin'], 'REDIS_DERIVED_TARGET_OR_POINT_MISMATCH')
    inventory = pinned_json(request['classificationPin']); item = inventory['classes']['redis']
    require(inventory['schemaVersion'] == 'RecoveryDerivedInventory/v1' and inventory['complete'] is True and
            inventory['recoveryPoint'] == request['recoveryPoint'] and item['classification'] == 'REBUILD' and
            item['requiredForBusiness'] is True and item['executorKey'] == EXECUTOR_KEY and
            item['rebuildFrom'] == 'DATABASE' and item['payloadPins'] == [], 'REDIS_DERIVED_CLASSIFICATION_INVALID')
    from recovery_data import NativeData
    native = NativeData(dict(request, materialPin=material_pin), original, trust, policy, config,
                        target, plan, material, budget, root)
    mutation_started = False
    try:
        native.bound(); database_result(request, material, native.db_uuid)
        core, cache = application_modules(adapter)
        envelope = private_envelope(adapter, native); settings = core.config(envelope['config'])
        target_configuration(settings, native, adapter)
        require(tuple(map(int, settings['redis']['serverVersion'].split('.'))) >= (7, 0, 0),
                'REDIS_ABSOLUTE_EXPIRY_READBACK_UNSUPPORTED')
        reference, provenance = session_provenance(native, request)
        before_pin = external_isolation(native, 'BEFORE_REBUILD')
        def guard():
            native.bound(); registration(policy, trust)
            for field in ('planPin', 'recoveryTargetPin', 'targetIdentityPin',
                          'classificationPin', 'rebuildFromPin'): check_pin(request[field])
            check_pin(adapter['configurationPin']); check_pin(adapter['secretRefs'][0])
            private_envelope(adapter, native)
            for ref in adapter['moduleSourcePins'] + adapter['toolPins']: check_pin(ref, content=False)
            for ref in provenance.values(): check_pin(ref)
        guard(); store = core.Store(settings, envelope['secrets'])
        try:
            mutation_started = True
            observation = store.rebuild_redis_from_database(guard)
        finally:
            store.cache.client.close(); store.s3.close()
        require(observation['schemaVersion'] == 'SmallAppRedisRebuildObservation/v1' and
                observation['state'] == 'READ_BACK' and observation['version'] == adapter['version'] and
                observation['runtimeRole'] == 'TARGET' and observation['gateState'] == 'PROTECTED',
                'REDIS_BUSINESS_READBACK_REQUIRED')
        guard(); observer = core.Store(settings, envelope['secrets'])
        try:
            readback = independent_readback(observer, cache, guard, reference, plan['recoveryPoint'], provenance)
        finally:
            observer.cache.client.close(); observer.s3.close()
        require(observer.gate.state == 'PROTECTED', 'REDIS_TARGET_GATE_CHANGED')
        after_pin = external_isolation(native, 'AFTER_READBACK'); guard()
        observation_pin = write(root/'business-rebuild.json', observation)
        readback_path = root/'independent-readback.json'
        require(not readback_path.exists(), 'REDIS_ORIGINAL_READBACK_ALREADY_EXISTS')
        readback_pin = write(readback_path, readback)
        os.chmod(readback_path, 0o400); check_pin(readback_pin)
        guard()
        return dict(schemaVersion='RecoveryDerivedExecution/v1', state='VERIFIED', className='redis',
                    classification='REBUILD', targetIdentityPin=target['targetIdentityPin'],
                    recoveryPoint=plan['recoveryPoint'], externalDispatchBlocked=True,
                    verificationPins=[observation_pin, readback_pin, before_pin, after_pin]), native
    except Exception as error:
        error.native = native
        error.unknown = bool(getattr(error, 'unknown', False)) or mutation_started
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True); parser.add_argument('--output', required=True)
    args = parser.parse_args(argv); request = pinned_json(pin(args.request)); started = utc(); native = None
    try:
        data, native = execute(request, absolute(args.output).parent); state = 'SUCCEEDED'; code = None
    except Exception as error:
        native = getattr(error, 'native', None); data = None
        state = 'TERMINAL_UNKNOWN' if getattr(error, 'unknown', False) else 'FAILED_RETAINED'
        code = getattr(error, 'code', 'REDIS_DERIVED_' + type(error).__name__.upper())
    result = dict(schemaVersion='RecoveryDataStepResult/v1', operationId=request['operationId'],
        requestId=request['requestId'], action=request['action'], state=state, failureCode=code, data=data,
        originalResultPins=[] if native is None else native.original_pins,
        actualExitCode={'SUCCEEDED':0, 'FAILED_RETAINED':1, 'TERMINAL_UNKNOWN':2}[state],
        startedAt=started, finishedAt=utc())
    try:
        persist_evidence(args.output, result, result['originalResultPins'], unknown=state=='TERMINAL_UNKNOWN')
    except RecoveryError as error:
        print(error.code); return 2 if error.unknown or native is not None else 1
    return result['actualExitCode']


if __name__ == '__main__':
    raise SystemExit(main())
