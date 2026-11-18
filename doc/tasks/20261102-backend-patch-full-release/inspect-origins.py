"""Read actual targets only; write safe identities, never container secrets."""
from pathlib import Path
import concurrent.futures
import hashlib,json,sys,time

source=Path('C:/SpugHandoff/release/source/ops/spug/release-center')
sys.path.insert(0,str(source))
from intruoyi_runtime import Runtime

root=Path('C:/SpugHandoff/release')
config=json.loads((root/'executor.private.json').read_text('utf-8'))
runtime=Runtime(config)
output=Path(__file__).with_name('origin-observations.json')

def read(env):
    try:
        value=runtime.call(env,'backend-patch-observe')
        return env,dict(status='passed',observation=value)
    except Exception as error:
        # The runtime's controlled errors contain no raw SSH/container output.
        return env,dict(status='failed',errorType=type(error).__name__,error=str(error))

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    result=dict(pool.map(read,('test','prod','backup')))
output.write_text(json.dumps(dict(collectedAt=time.strftime('%Y-%m-%dT%H:%M:%S'),targets=result),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
