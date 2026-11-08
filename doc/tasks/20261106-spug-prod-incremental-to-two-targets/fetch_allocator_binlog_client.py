"""Read the already pinned export client, never mutate the source host."""
import base64
import hashlib
import json
from common import TASK, PRIVATE, now, remote, write

proof = json.loads((TASK / 'binlog-tmpfs-tool-provisioned.json').read_text(encoding='utf8'))
script = '''import base64,hashlib,json,subprocess
p=PROOF
row=json.loads(subprocess.check_output(['docker','inspect',p['containerId']]))[0]
assert row['Id']==p['containerId'] and row['Image']==p['imageId'] and row['State']['Running']
raw=subprocess.check_output(['docker','exec',p['containerId'],'cat',p['executable']],timeout=60)
assert hashlib.sha256(raw).hexdigest()==p['executableSha256']
print(json.dumps(dict(raw=base64.b64encode(raw).decode(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())))
'''.replace('PROOF', repr(proof))
result = remote('172.30.30.57', script, timeout=90)
raw = base64.b64decode(result.pop('raw'), validate=True)
assert hashlib.sha256(raw).hexdigest() == proof['executableSha256']
path = PRIVATE / 'allocator-mysqlbinlog.private'
assert not path.exists();path.write_bytes(raw)
report = dict(status='PASS', observedAt=now(), sourceReadOnly=True, **result,
              sourceContainerId=proof['containerId'], sourceExecutable=proof['executable'])
write(TASK / 'allocator-client-pin.json', report);print(json.dumps(report))
