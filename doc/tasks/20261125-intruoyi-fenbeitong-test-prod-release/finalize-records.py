"""Write final task records only after all owned resources pass closeout."""
import json
from datetime import datetime
from pathlib import Path

task=Path(__file__).resolve().parent
repo=task.parents[2]
proofs={name:json.loads((task/(name+'-cleanup-proof.json')).read_text(encoding='utf-8')) for name in ('failed-build','source-fix','tenant-fix','maintenance')}
assert all(p['status']=='passed' and p['registeredAfter'] is False and p['physicalPathExists'] is False for p in proofs.values())
local=json.loads((task/'local-closeout-proof.json').read_text(encoding='utf-8'))
assert local['status']=='PASS' and local['privateConfigBytesPreserved'] and local['stableExecutorCwdVerified']
assert json.loads((task/'release-result.json').read_text(encoding='utf-8'))['status']=='PASS'
for p in local['ownedWorktreesAbsent']: assert not Path(p).exists()

text=(task/'task.md').read_text(encoding='utf-8')
assert '\nready_for_closeout\n' in text
text=text.replace('\nready_for_closeout\n','\ncompleted\n',1)
text=text.replace('- [ ] 收口证据、删除任务自有 worktree、恢复稳定控制台路径并提交最终记录。','- [x] 收口证据、删除任务自有 worktree、核验稳定控制台路径；最终记录按独立提交归档。',1)
old='本轮6个自有worktree（3次构建、SQL修复、租户修复、维护执行）需完成最终物理/Git登记与稳定执行器路径核验；两次成功构建目录已自动删除，其余4个准备按正式清理器收口。其它任务worktree、进程及控制台不属于本任务。'
assert old in text
text=text.replace(old,'本轮6个自有worktree均已删除，物理路径和Git登记均无残留；SQL和租户实现已融合int_main并验证，slot9/10已释放。稳定执行器PID '+str(local['executorPid'])+'、argv和cwd核验通过，私密配置字节保持；其它任务资源保持。最终证明见local-closeout-proof.json。',1)
(task/'task.md').write_text(text,encoding='utf-8')

text=(task/'verification.md').read_text(encoding='utf-8')
old='用户要求的两服发布及运行态、真实页面验收已通过；当前进入任务自有工作区清理。最终收尾证明见 local-closeout-proof.json，任务终态以 task.md 为准。'
assert old in text
text=text.replace(old,'用户要求的两服发布及运行态、真实页面验收已通过，本任务自有工作区清理及本地运行路径核验已完成。最终收尾证明见 local-closeout-proof.json，任务状态 completed。',1)
text+='\n## 最终收尾\n\n'
for name,p in proofs.items():
    text+='- '+name+'：正式清理器通过，逐字节核'+str(p['verifiedTrackedFiles'])+'项受控文件、拆除'+str(p['generatedLinksDetached'])+'项生成链接；Git登记和物理目录均已删除。\n'
text+='\n维护工作区首轮因两个未知缓存被保护拒绝；后续核tracked源码、pyc头部与完整marshal编译结果逐字节相同，私密保留原缓存后仅精确删除这两个派生文件，再走原清理器通过。没有扩大清理白名单。详见maintenance-generated-cache-proof.json。\n'
text+='\n两次成功构建目录已由构建流程自动校验并删除，加上上述4个目录，本任务6个工作区均无残留。SQL/租户修复提交均已融合int_main，维护及构建目录无新提交。本任务slot9/10仅在端口无监听、其它登记保持后释放。稳定执行器PID '+str(local['executorPid'])+'的入口、配置参数及cwd与稳定路径一致，运行agent符合已提交字节，私密配置摘要保持；没有停止或清理其它任务资源。\n'
(task/'verification.md').write_text(text,encoding='utf-8')

stamp=datetime.now().astimezone().isoformat(timespec='seconds')
entry='''## 20261125-intruoyi-fenbeitong-test-prod-release 最终结果

- 用户需求：发布intruoyi到测试服务器和正式服务器；本次不包含助手、审查服或财务配置修改。
- 命令意图：同一已提交输入隔离构建，build-release -> publish-test -> mark-tested -> promote-prod -> accept-prod，再独立核两服运行态和真实登录页面；全部使用正式执行器，未重新构建正式包。
- 结果：2026-11-26-01-52-12 / eb866bbaf4ea1b1c6db93daa63e77576766c3684，两服operation、manifest、IMAGE_TAG、实际双镜像一致，backend UP/frontend HTTP200，三阶段数据库合同PASS，正常入口和维护验收入口页面PASS_WITH_OBSERVATIONS。
- 修复及验证：SQL发布登记6a099294a、分贝通可信签发租户上下文eb866bbaf，均先RED再GREEN并融合int_main；67项JUnit和24项维护配置回归通过。旧构建失败和第二包认证503保留，不拼接版本成功记录。
- 收尾命令：cleanup.py前三项PASS、第四项因未知缓存保护拒绝；核精确派生后finish-maintenance-cleanup.py调用原清理器PASS，release-slot.ps1、release-tenant-slot.ps1、final-local-proof.py均PASS；本任务6个worktree无Git/物理残留，slot9/10释放，稳定执行器和私密配置保持。
- 未完成业务：两服助手报销字段映射未保存、部分租户注册证提醒配置缺失；财务同步/生成/记账和工作台初始化没有验收通过，全部观察显式保留。
- 证据：doc/tasks/20261125-intruoyi-fenbeitong-test-prod-release/verification.md、release-result.json、local-closeout-proof.json。原始私密证据不进入Git。
'''
entry+='- 收尾记录时间：'+stamp+'。\n'
(task/'request-command-log.md').write_text(entry,encoding='utf-8')
shared=repo/'docs/request-command-log.md'
existing=shared.read_text(encoding='utf-8')
assert '## 20261125-intruoyi-fenbeitong-test-prod-release 最终结果' not in existing
with shared.open('a',encoding='utf-8',newline='') as out: out.write('\n'+entry)
log='\n- GREEN: owned-worktree-cleanup -> PASS（cleanup.py前三项；finish-maintenance-cleanup.py证明两个ignored pyc精确派生后调用原清理器完成maintenance）。原始缓存保护失败保留，未扩大白名单；四项正式清理证明均为passed，Git登记及物理路径无残留；两项实现先提交、融合和验证，另外两次成功构建目录先前自动清理。\n- GREEN: release-slot.ps1 / release-tenant-slot.ps1 -> PASS，仅释放本任务slot9/10，端口无监听，其它注册保持。\n- GREEN: final-local-proof.py -> PASS，六个自有worktree均无残留，最终源码在int_main；稳定执行器PID '+str(local['executorPid'])+'的argv/cwd和受保护配置、已安装agent摘要核验通过。\n- completed: '+stamp+'；同包两服运行态和真实页面验收、任务自有资源清理全部完成。最终任务记录单独提交，不暂存共享request-command-log的其它并发修改。\n'
with (task/'execution-log.md').open('a',encoding='utf-8',newline='') as out:out.write(log)
for path in (task/'task.md',task/'verification.md',task/'request-command-log.md',task/'execution-log.md',shared):
    assert '\ufffd' not in path.read_text(encoding='utf-8')
print(json.dumps(dict(status='PASS',taskStatus='completed',ownedWorktreesAbsent=6,sharedLogAppended=True),ensure_ascii=False))
