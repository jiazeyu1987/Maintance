import json
import subprocess
from pathlib import Path

base=Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
config=json.loads((base/'configuration/capture.json').read_bytes())['source']
container=config['mysqlContainerId']
info=json.loads(subprocess.check_output(['docker','inspect',container],timeout=5))[0]
assert info['Name']=='/intruoyi-mysql' and info['State']['Running']
names=['system_menu','system_role','system_role_menu','system_user_role','system_tenant','system_tenant_package','system_dept','system_post','system_user_post','system_role_category']
queries=["USE `ruoyi-vue-pro`; START TRANSACTION READ ONLY; SELECT 'identity',@@server_uuid;"]
for name in names:
    queries.extend(["SELECT 'TABLE','{}';".format(name),'DESCRIBE `'+name+'`;'])
queries.append('COMMIT;')
password=Path(config['passwordPin']['path']).read_text(encoding='utf-8').strip()
p=subprocess.run(['docker','exec','-i',container,'sh','-c','read -r MYSQL_PWD; export MYSQL_PWD; exec mysql -uroot --batch --skip-column-names --default-character-set=utf8mb4'],input=(password+'\n'+'\n'.join(queries)).encode(),capture_output=True,timeout=15)
assert p.returncode==0 and not p.stderr
lines=[line.split('\t') for line in p.stdout.decode('utf-8').splitlines()]
assert lines[0]==['identity',config['databaseUuid']]
out={'serverWrites':False,'tables':{}}
for row in lines[1:]:
    if row[0]=='TABLE':current=row[1];out['tables'][current]=[]
    else:out['tables'][current].append({'column':row[0],'type':row[1]})
print(json.dumps(out))
