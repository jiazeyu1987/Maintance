"""Generalize this task's existing real-page probe for explicit target bindings."""
from pathlib import Path
task=Path(__file__).resolve().parent
source=Path('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125/test/menu-page-check.cjs')
s=source.read_text(encoding='utf-8')
s=s.replace("const tag=process.argv[2];", "const [environment,tag,commit,explicitOrigin]=process.argv.slice(2);\nif(!['test','prod','prod-maintenance'].includes(environment)||! /^[0-9a-f]{40}$/.test(commit))throw Error('EXPLICIT_TARGET_REQUIRED');")
s=s.replace("const base='http://172.30.30.58:8081',out=__dirname;", "const host=environment==='test'?'172.30.30.58':'172.30.30.57';\nconst base=explicitOrigin||'http://'+host+':8081';if(new URL(base).hostname!==host)throw Error('TARGET_HOST_MISMATCH');\nconst out=path.join('C:/SpugHandoff/release/private/intruoyi-fenbeitong-test-prod-20261125',environment);fs.mkdirSync(out,{recursive:true});")
s=s.replace("environment:'test'",'environment')
s=s.replace("process.argv[3]==='login-only'",'false')
s=s.replace('releaseInfo?.sourceCommit!==process.argv[4]','releaseInfo?.sourceCommit!==commit')
(task/'menu-page-check.cjs').write_text(s,encoding='utf-8')
print('Explicit target menu probe prepared')
