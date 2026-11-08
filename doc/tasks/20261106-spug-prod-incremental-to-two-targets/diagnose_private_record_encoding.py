"""Report only identities of malformed private JSON; never emit its contents."""
import hashlib,json
from common import PRIVATE
bad=[]
for p in PRIVATE.glob('*.json'):
 if p.stat().st_size>=32*1024*1024:continue
 raw=p.read_bytes()
 try:json.loads(raw.decode('utf-8-sig'))
 except (UnicodeError,ValueError) as e:
  bad.append(dict(name=p.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),errorType=type(e).__name__))
print(json.dumps(bad))
