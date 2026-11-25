"""Execute only task-owned read-only SQL with the installed release transport."""
import json
import subprocess
import sys
from pathlib import Path
BASE=Path('C:/SpugHandoff/release')
OUT=BASE/'private/intruoyi-fenbeitong-test-prod-20261125'
SRC=BASE/'source/ops/spug/release-center'
sys.path.insert(0,str(SRC))
from intruoyi_runtime import Runtime,ssh_source_bytes
c=json.loads((BASE/'executor.private.json').read_text(encoding='utf-8-sig'))
r=Runtime(c)
env=sys.argv[1]
assert env in ('test','prod')
if sys.argv[2]=='describe':
    queries={name:'DESCRIBE '+name for name in ('system_menu','system_tenant_package','system_role_menu')}
elif sys.argv[2]=='menus':
    queries={'menus':"SELECT id,name,parent_id,path,component,component_name,permission,type,status,visible+0 AS visible,deleted+0 AS deleted,sort FROM system_menu WHERE id IN (5580,900120,990200,990253,991503) ORDER BY id",'roleBindings':"SELECT menu_id,COUNT(*) AS bindings FROM system_role_menu WHERE deleted=0 AND menu_id IN (5580,900120,990200,990253,991503) GROUP BY menu_id ORDER BY menu_id"}
else:
    filename=Path(sys.argv[2])
    sys.path.insert(0,str(BASE/'intruoyi-fenbeitong-release-20261125'))
    from ops.release.release_target_preflight_contract import validate
    validate(filename,'20261125_registration_certificate_config_menu_parent')
    queries={'preflight':filename.read_text(encoding='utf-8')}
    if len(sys.argv)>3:
        assert sys.argv[3]=='wrong-permission'
        original=queries['preflight']
        queries={'wrong-permission':original.replace("config.permission='dcc:registration-certificate:config:query'", "config.permission='task-negative-unregistered-permission'")}
        assert queries['wrong-permission']!=original
p=r.profile(env)
module=(SRC/'intruoyi_remote.py').read_text(encoding='utf-8').split("if __name__ == '__main__':")[0]
code=module+'\np='+repr(p)+'\nqueries='+repr(queries)+'\nprint(json.dumps({k:sql(p,v) for k,v in queries.items()},ensure_ascii=False))\n'
result=subprocess.run(['ssh',*r.ssh_options(),'root@'+p['host'],p['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=90)
if result.returncode:
    (OUT/(env+'-readonly-sql-error.private.txt')).write_bytes(result.stderr)
    raise SystemExit('Read-only SQL failed; private diagnostic retained')
value=json.loads(result.stdout)
(OUT/(env+'-'+sys.argv[2].split('/')[-1]+'.private.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value,ensure_ascii=False))
if 'wrong-permission' in value:
    assert value['wrong-permission']=='TARGET_PREFLIGHT_BLOCKED:20261125_registration_certificate_config_menu_parent:CONFIG_IDENTITY'
