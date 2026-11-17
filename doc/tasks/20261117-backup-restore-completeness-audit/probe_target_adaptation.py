import hashlib
import json
import subprocess
from pathlib import Path

root=Path('/mnt/intruoyi-data/recovery-preparation/a029c09a7b8b2466821419b0b7664b1c15b4fec165c790d39c293098b418e024/recovery-operations/smallapp-9ddf6a1391f14bddb7af731a53f69a5e')
config=json.loads((root/'target-configuration.json').read_bytes())
result=json.loads((root/'result.json').read_bytes())
out={'serverWrites':False,'preparedFileStorage':json.loads((root/'final/prepared-file-storage.json').read_bytes()),'sourceBinding':config['preparedFileStorage']}
container=next(s['id'] for s in config['services'] if s['role']=='mysql')
query="USE `ruoyi-vue-pro`; SET SESSION time_zone='+00:00'; START TRANSACTION READ ONLY; SELECT 'identity',@@server_uuid; DESCRIBE system_users; SELECT 'users_with_login_after_restore',COUNT(*) FROM system_users WHERE login_date>'2026-11-16 22:25:52'; COMMIT;"
p=subprocess.run(['docker','exec','-i',container,'mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','--batch','--skip-column-names'],input=query.encode(),capture_output=True,timeout=15)
assert p.returncode==0 and not p.stderr
rows=[line.split('\t') for line in p.stdout.decode().splitlines()]
assert rows[0]==['identity','f6ccd898-e207-11f1-bd88-0242ac1dee20']
out['userSchemaColumnNames']=[r[0] for r in rows[1:-1]]
out['usersWithLoginAfterRestore']=int(rows[-1][1])
print(json.dumps(out))
