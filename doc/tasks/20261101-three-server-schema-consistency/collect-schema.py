"""Read-only complete table metadata, excluding rows and volatile AUTO_INCREMENT counters."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

TASK = Path(__file__).parent
SOURCES = Path('C:/SpugHandoff/release/source/ops/spug/release-center')
sys.path.insert(0,str(SOURCES))
from intruoyi_runtime import Runtime
config=json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8-sig'))
runtime=Runtime(config)
queries={
 'tables':"SELECT TABLE_NAME,TABLE_TYPE,ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME;",
 'columns':"SELECT TABLE_NAME,COLUMN_NAME,ORDINAL_POSITION,COLUMN_TYPE,IS_NULLABLE,COALESCE(HEX(COLUMN_DEFAULT),'<NULL>'),EXTRA,COALESCE(COLLATION_NAME,''),HEX(GENERATION_EXPRESSION) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,ORDINAL_POSITION;",
 'indexes':"SELECT TABLE_NAME,INDEX_NAME,NON_UNIQUE,SEQ_IN_INDEX,COALESCE(COLUMN_NAME,''),COALESCE(CAST(SUB_PART AS CHAR),''),INDEX_TYPE,IS_VISIBLE,COALESCE(EXPRESSION,'') FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX;",
 'constraints':"SELECT TABLE_NAME,CONSTRAINT_NAME,CONSTRAINT_TYPE,ENFORCED FROM information_schema.TABLE_CONSTRAINTS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,CONSTRAINT_NAME;",
 'foreignKeys':"SELECT TABLE_NAME,CONSTRAINT_NAME,COLUMN_NAME,ORDINAL_POSITION,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL ORDER BY TABLE_NAME,CONSTRAINT_NAME,ORDINAL_POSITION;",
 'foreignRules':"SELECT TABLE_NAME,CONSTRAINT_NAME,UPDATE_RULE,DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=DATABASE() ORDER BY TABLE_NAME,CONSTRAINT_NAME;",
 'checks':"SELECT t.TABLE_NAME,c.CONSTRAINT_NAME,HEX(c.CHECK_CLAUSE) FROM information_schema.CHECK_CONSTRAINTS c JOIN information_schema.TABLE_CONSTRAINTS t ON t.CONSTRAINT_SCHEMA=c.CONSTRAINT_SCHEMA AND t.CONSTRAINT_NAME=c.CONSTRAINT_NAME AND t.CONSTRAINT_TYPE='CHECK' WHERE c.CONSTRAINT_SCHEMA=DATABASE() ORDER BY t.TABLE_NAME,c.CONSTRAINT_NAME;"}
remote_source=(SOURCES/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
def collect(env):
    profile=runtime.profile(env)
    migration_query="SELECT migration_id,sha256,status FROM infra_release_migration WHERE deleted=b'0' AND migration_id='20261101_dcc_source_governance_all_environments' ORDER BY id;"
    code=remote_source+'\nprofile='+repr(profile)+'\nqueries='+repr(queries)+'\nmigration_query='+repr(migration_query)+"\nprint(json.dumps(dict(identity=sql(profile,'SELECT DATABASE(),@@version;'),forwardMigration=sql(profile,migration_query).splitlines(),schema={k:sql(profile,v).splitlines() for k,v in queries.items()})))\n"
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],shlex.quote(profile['python'])+' -'], input=code.encode('utf-8'),capture_output=True,timeout=180)
    if result.returncode:
        raise RuntimeError(env+' readonly metadata failed exit='+str(result.returncode))
    data=json.loads(result.stdout)
    data['host']=profile['host']
    data['sha256']=hashlib.sha256(json.dumps(data['schema'],sort_keys=True).encode()).hexdigest()
    return env,data
with ThreadPoolExecutor(max_workers=3) as pool:
    environments=dict(pool.map(collect,['test','prod','backup']))
diff={}
for target in ['prod','backup']:
    diff[target]={}
    for section,rows in environments['test']['schema'].items():
        reference=set(rows); actual=set(environments[target]['schema'][section])
        if reference != actual:
            diff[target][section]=dict(testOnly=sorted(reference-actual),targetOnly=sorted(actual-reference))
out=dict(time=datetime.now(timezone.utc).isoformat(),remoteMutations=False,environments=environments,differences=diff)
filename=sys.argv[1] if len(sys.argv)>1 else 'schema-before.json'
assert filename in ('schema-before.json','schema-after.json')
assert not (TASK/filename).exists(), 'Preserve existing metadata evidence'
(TASK/filename).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(evidence=filename,counts={e:len(x['schema']['tables']) for e,x in environments.items()},differences={e:{s:dict(testOnly=len(v['testOnly']),targetOnly=len(v['targetOnly'])) for s,v in sections.items()} for e,sections in diff.items()})))
