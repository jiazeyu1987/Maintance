"""Inspect an existing operation only; never resend its effect payload."""
from pathlib import Path
import json,sys
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center');sys.path.insert(0,str(live))
from intruoyi_runtime import Runtime
runtime=Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
job,operation=sys.argv[1:]
value=runtime.call('test','inspect-operation',originalOperationId=operation,originalJobId=job)
output=Path(__file__).with_name('operation-inspection-'+operation+'.json');assert not output.exists()
output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:value.get(k) for k in ('operationId','jobId','status','worker','action','effectsStarted')}))
