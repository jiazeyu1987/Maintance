"""Run the committed read-only worker inventory on the actual test server."""
from pathlib import Path
import inspect,json,subprocess,sys
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'ops/spug/release-center'))
import backend_patch_agent as agent
from intruoyi_runtime import Runtime,ssh_source_bytes
runtime=Runtime(json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8')))
profile=runtime.profile('test')
code='import os,re\nfrom pathlib import Path\ndef need(value,message):\n if not value: raise ValueError(message)\n'
code+=inspect.getsource(agent.require_no_other_stdin_workers)
code+='\nrequire_no_other_stdin_workers()\nprint("WORKER_INVENTORY_PASS")\n'
result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],input=ssh_source_bytes(code),capture_output=True,timeout=30)
output=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/worker-inventory.private.log');assert not output.exists()
output.write_bytes(result.stdout+b'\n'+result.stderr)
assert result.returncode==0 and result.stdout.strip()==b'WORKER_INVENTORY_PASS','Live worker inventory failed'
log=Path(__file__).with_name('execution-log.md');text=log.read_text('utf-8')
text+='\n- 未开始切换恢复分支已提交443d0b73，仅agent及4项新测试，92项回归PASS；首次内联只读核验因PowerShell引号解析在本机SyntaxError，未连接远端；改用UTF-8文件后真实58 Linux /proc读取PASS，无其他Python标准输入worker。\n- GREEN: experience-preflight -> PASS，安装443d0b73。执行器无活动任务，原中断任务保留；只变更1个已提交agent文件、精确停止自有普通执行器，完整历史/私密配置前后保持。\n'
log.write_text(text,encoding='utf-8')
print(json.dumps(dict(status='PASS',realLinuxWorkerInventory=True,otherStdinWorkers=False)))
