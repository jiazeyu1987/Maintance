"""Real Redis DUMP snapshot and readback under stopped application writers."""
import base64
from contextlib import contextmanager
import hashlib
import json
import subprocess
from formal_capture_incremental import require

LUA = '''
local keys=redis.call('KEYS','*')
if #keys>100000 then return redis.error_reply('SNAPSHOT_KEY_LIMIT') end
table.sort(keys)
local t=redis.call('TIME')
local result={t[1],t[2]}
for _,k in ipairs(keys) do
 local value=redis.call('DUMP',k)
 if value then
  if string.len(value)>16777216 then return redis.error_reply('SNAPSHOT_VALUE_LIMIT') end
  table.insert(result,k);table.insert(result,value)
  table.insert(result,tostring(redis.call('PEXPIRETIME',k)))
 end
end
return result
'''

@contextmanager
def source_client(config, guard):
    import redis
    guard()
    row=json.loads(subprocess.check_output(['docker','inspect',config['containerId']],timeout=10))[0]
    require(row['Id']==config['containerId'] and row['State']['Running'] and
        any(n['IPAddress']==config['host'] for n in row['NetworkSettings']['Networks'].values()),
        'MINIMAL_REDIS_SOURCE_CHANGED')
    authentication = {}
    if 'passwordPin' in config:
        from formal_capture_recovery_inputs import original_bytes
        authentication['password'] = original_bytes(config['passwordPin'], limit=16384).decode('utf-8').removesuffix('\n')
    client=redis.Redis(host=config['host'],port=6379,db=config['database'],
        socket_timeout=30,socket_connect_timeout=5,**authentication)
    try:
        version=client.info('server')['redis_version']
        require(tuple(map(int,version.split('.'))) >= (7,0,0),'REDIS_ABSOLUTE_EXPIRY_REQUIRED')
        guard()
        yield client, row, version
    finally:client.close()


def preflight(config, guard):
    # Check only connectivity/identity/version; do not scan keys before capture.
    with source_client(config, guard):
        pass


def observe(config, guard):
    with source_client(config, guard) as (client, row, version):
        raw=client.eval(LUA,0)
        require(len(raw)>=2 and (len(raw)-2)%3==0,'REDIS_SNAPSHOT_INVALID')
        values=[]
        for i in range(2,len(raw),3):
            key,dump,expiry=raw[i:i+3];expiry=int(expiry)
            require(expiry==-1 or expiry>0,'REDIS_SNAPSHOT_INVALID')
            values.append(dict(keyBase64=base64.b64encode(key).decode(),
                dumpBase64=base64.b64encode(dump).decode(),dumpSha256=hashlib.sha256(dump).hexdigest(),
                expiresAtUnixMs=expiry))
        guard()
        return dict(schemaVersion='RedisDumpSnapshot/v1',database=config['database'],
            sourceContainerId=row['Id'],serverVersion=version,
            observedAtUnixMs=int(raw[0])*1000+int(raw[1])//1000,entries=values)

def verify_current(snapshot, config, guard):
    current=observe(config,guard);now=current['observedAtUnixMs']
    expected=[r for r in snapshot['entries'] if r['expiresAtUnixMs']==-1 or r['expiresAtUnixMs']>now]
    require(expected==current['entries'],'REDIS_SOURCE_CHANGED_DURING_CAPTURE')
    return current
