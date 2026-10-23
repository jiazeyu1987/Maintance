"""Restore an archived Redis DUMP snapshot without extending its original TTL."""
import base64
import hashlib
from pathlib import PurePosixPath
from recovery_engine import pinned_json, require, write

def archived_snapshot(material, reference):
    root = PurePosixPath(material['database']['capturePointPin']['path']).parents[1]
    inputs_pins = [p for p in material['payloadPins'] if p['path'] == str(root/'capture-recovery-inputs.json')]
    require(len(inputs_pins) == 1, 'REDIS_CAPTURE_INPUTS_NOT_ARCHIVED')
    inputs = pinned_json(inputs_pins[0])
    require(inputs['schemaVersion'] == 'backup-capture-recovery-inputs/v1' and
        inputs['recoveryPoint'] == material['recoveryPoint'], 'REDIS_CAPTURE_POINT_MISMATCH')
    names = [name for name, pin in inputs['archiveFilePins'].items() if pin == reference]
    require(len(names) == 1, 'REDIS_SNAPSHOT_SOURCE_BINDING_INVALID')
    archived = dict(reference, path=str(root/names[0]))
    require(archived in material['payloadPins'], 'REDIS_SNAPSHOT_NOT_ARCHIVED')
    return archived

def restore(native,item):
    import redis
    adapter=native.config['redisRebuild']
    require(adapter['kind']=='REDIS_DUMP_ABSOLUTE_EXPIRY' and
        item['executorKey']==adapter['kind'] and len(item['payloadPins'])==1,
        'REDIS_DUMP_ADAPTER_INVALID')
    reference=archived_snapshot(native.material,item['payloadPins'][0])
    snapshot=pinned_json(reference)
    require(snapshot['schemaVersion']=='RedisDumpSnapshot/v1' and
        snapshot['database']==adapter['database'] and type(snapshot['entries']) is list,
        'REDIS_SNAPSHOT_INVALID')
    options=dict(host=native.config_services['redis']['ip'],port=6379,db=adapter['database'],
        password=native.secret('redis','REDIS_PASSWORD'),socket_timeout=10,socket_connect_timeout=5)
    client=redis.Redis(**options);expired=0;restored=0
    try:
        native.bound()
        for entry in snapshot['entries']:
            native.guard()
            key=base64.b64decode(entry['keyBase64'],validate=True)
            dump=base64.b64decode(entry['dumpBase64'],validate=True)
            expiry=entry['expiresAtUnixMs']
            t=client.time();now=t[0]*1000+t[1]//1000
            if expiry!=-1 and expiry<=now:expired+=1;continue
            native.mutation_dispatched=True
            require(client.restore(key,0 if expiry==-1 else expiry,dump,absttl=expiry!=-1) == b'OK',
                'REDIS_RESTORE_FAILED')
            restored+=1
    finally:client.close()
    return dict(className='redis', classification='RESTORE',
        observationPin=write(native.root/'redis-dump-execution.json', dict(
            schemaVersion='RedisDumpRestoreExecution/v1', snapshotPin=reference,
            database=adapter['database'], restoredKeyCount=restored, expiredBeforeRestoreCount=expired,
            independentlyVerifiedKeyCount=0, valuesVerified=False, absoluteExpiryVerified=False,
            verificationState='NOT_PERFORMED')))
