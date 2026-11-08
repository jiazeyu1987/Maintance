"""Correct the extension of an exact original 504 body without changing bytes."""
import hashlib,json
from common import PRIVATE,TASK,write,now
p=PRIVATE/'restore-58-r3-accepted-catalogue.private.json'
q=PRIVATE/'restore-58-r3-accepted-catalogue.original-http-body'
assert p.resolve().parent==PRIVATE.resolve() and not q.exists()
raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
assert len(raw)==562 and sha=='64e0d721da1996b3da241306e370b2353fbf861904911668820051d3ad12794b'
assert b'<html>' in raw and b'504 Gateway Time-out' in raw
p.rename(q)
assert q.read_bytes()==raw and not p.exists()
out=dict(status='PASS',observedAt=now(),originalName=p.name,preservedName=q.name,bytes=len(raw),sha256=sha,
 originalHttpError=504,bodyUnchanged=True,reason='Original HTTP failure body was stored with a JSON extension; preserve it as its actual format.')
write(TASK/'failed-catalogue-http-body-preserved.json',out);print(json.dumps(out))
