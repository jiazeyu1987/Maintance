import json,sys
from pathlib import Path
from urllib.parse import urlsplit
base=Path('C:/SpugHandoff/release'); sys.path.insert(0,str(base/'source/ops/spug/release-center'))
from intruoyi_runtime import Runtime
p=Runtime(json.loads((base/'executor.private.json').read_bytes())).profile('prod')
u=urlsplit(p['acceptanceUrl'])
assert u.hostname==p['host']=='172.30.30.57' and u.port!=8081 and not u.username and not u.password
print(json.dumps(dict(acceptanceUrl=p['acceptanceUrl'])))
