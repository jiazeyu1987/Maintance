"""Render final records only from successful independent evidence."""
from pathlib import Path
import json
task=Path(__file__).resolve().parent;repo=task.parents[2]
proof=json.loads((task/'final-verification.json').read_text('utf-8'))
audit=json.loads((task/'closeout-verification.json').read_text('utf-8'))
assert proof['status']==audit['status']=='PASS'
safety=json.loads((task/'runtime-safety-full-cleanup-final.json').read_text('utf-8'))
assert all(v['status']=='passed' and not v['publicLockHeld'] and not v['operations'] and v['readOnly'].strip()=='0\t0' for v in safety['targets'].values())
tag=proof['fullReleaseTag'];patch=proof['backendPatchTag'];total=proof['totalCleanupFileBytes']
summary=f'''已完成后端补丁{patch}三服发布及验收，随后同源码全量{tag}按测试→正式→备份闭环完成。三服实际JAR/前后端镜像相同、885张表及13段结构一致、各自迁移历史保持，旧补丁程序挂载为空。真实Playwright维护/开放登录、版本变更说明、本地及三服GxP关闭、健康UP/HTTP200通过，正式Quartz原有15秒心跳推进。清理最终JOB-763953cdce三服成功，原失败保持；合计删除旧文件{total}字节（约{total/1024**3:.2f}GiB），四组证据不足旧资料整组保留。全部本轮构建副本已删除，未产生构建提交；稳定普通执行器PID14264路径已恢复、无服务/活动任务/远端锁、数据库临时保护0/0，私密配置保持。实现先提交，最终记录独立提交；不自动合并/推送int_main。'''
path=task/'task.md';text=path.read_text('utf-8');start=text.index('## Current Status');end=text.index('## 目标及授权')
text=text[:start]+'## Current Status\ncompleted\n\n'+summary+'\n\n'+text[end:]
start=text.index('## 当前进度');end=text.index('## 预期验证')
text=text[:start]+'''## 当前进度

1. 起点/源码/锁/写者/GxP/恢复依据核对完成，目标源码ee2d7c79356e79e1180ab03e03873cd3f924a6f5。
2. v2补丁三服构建、只读维护探针、正常启动及真实页面验收完成，真实JAR和各自schema/ledger保持。
3. 同源码全量同一releaseTag闭环完成：构建原包续传JOB-eeaf3711eb；测试续接JOB-b68b4b0044及mark-tested JOB-f4cd60ec96；正式JOB-31001c8bcb/开放JOB-1807d7a63b；备份JOB-2714f1ba96/开放JOB-7f32aa47ab。原构建/测试失败保持并与真实重试关联，不拼接不同releaseTag。
4. 独立final-verification.json、closeout-verification.json及runtime-safety-full-cleanup-final.json全部PASS；清理JOB-763953cdce成功，保留旧证据缺口和最新有效恢复点。所有本轮临时构建worktree登记及物理路径不存在，无新提交、不需合回；开发分支按用户范围保留，未自动合并推送。

'''+text[end:];path.write_text(text,encoding='utf-8')
report=f'''# 后端补丁衔接全量发布验收

状态：completed，2026-11-03。

先完成后端补丁 `{patch}` 三服发布，再完成同源码全量 `{tag}`；原失败记录及实际重试关联均保留。

| 环境 | 访问地址 | 最终版本 | 健康 / 页面 | GxP |
|---|---|---|---|---|
'''
for env,name in [('test','测试服'),('prod','正式服'),('backup','备份服')]:
    value=proof['targets'][env];report+=f"| {name} | {value['url']} | {tag} | UP / 200 | 关闭 |\n"
report+=f'''
源码固定 `{proof['sourceCommit']}`。补丁JAR SHA为`8c3c670d57c77c84d76fe335e3918e1a9f4cd5b47ba097fe10908ab07c7d9135`；全量重新编译JAR SHA为`{proof['targets']['test']['jarSha256']}`。两者源码相同；全量吸收日志/DCC/展厅/Quartz修复后，移除旧补丁程序挂载，实际运行新镜像内JAR。三服全量JAR和镜像一致，启动完成日志各1次。

三服885表、15594列、5480索引及约束/触发器等13段结构一致，各自原迁移历史保持。本轮SQL APPLY=0；测试服原有4条测试租户限定历史继续保留，未伪造跨服历史。后端补丁发布脚本没有迁移、改表或配置/业务SQL；先维护只读探针，再解除本任务保护正常启动。正式既有Quartz15秒心跳已真实验证推进，正常运行不作全库零写入承诺。

真实Playwright登录维护和开放入口、真实版本对话框及变更说明通过；本地和三服保存/运行GxP均DEVELOPMENT_DISABLED，auditEnabled=false，无待重启。这里只验收登录、展示和权限入口，没有新增/保存/审批写入功能回归。

发布后清理原JOB-7f32aa47ab失败、重试JOB-a7a180c9c4部分成功，最终JOB-763953cdce三服成功。合计删除旧文件{total}字节，约{total/1024**3:.2f}GiB；镜像共享层不按逻辑大小重复计数。测试服2026-10-22-01-09-56、10-45-28、20-45-19缺清单，以及2026-10-31-19-13-08旧恢复日志与归档绑定不一致，四组及其依赖完整保留。没有补写清单/摘要、删除NAS或正在使用的演练。正式/备份旧资源按精确身份回收，当前及最近恢复点保留。

必要实现修复已独立提交：维护仓a93fe3e（停止态补丁取证和同包检查点续接）、5f9cf1e（挂载无序身份和旧恢复组保留）、9638d6e（缺旧清单组保留）；相关164项、随后142项及真实Docker、Linux锁测试PASS。Java DCC118/展厅15/Quartz63项回归PASS。构建封包后Git清理超时通过校验原包续传处理，没有重新编译掩盖原失败。

全部本轮临时构建副本已删除，无新提交；目标开发分支保留，不自动融合或推送int_main。普通脚本执行器PID14264从稳定路径运行，18112；Spug http://127.0.0.1:18081 。未安装Windows服务。配置/凭据原样保留，原始日志和截图仅留private。

普通启动命令（只在现有进程已停止时使用）：

```powershell
& 'C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14/python.exe' 'C:/SpugHandoff/release/source/ops/spug/release-center/intruoyi_executor.py' --config 'C:/SpugHandoff/release/executor.private.json'
```

证据：final-verification.json核61份远端持久回执且worker均停止；program-full-*.json、ui-gxp-full-*.json、database-full.json、quartz-heartbeat-full.json、runtime-safety-full-cleanup-final.json及closeout-verification.json。凭据不进入报告或Git。
'''
(task/'acceptance-report.md').write_text(report,encoding='utf-8')
with (task/'execution-log.md').open('a',encoding='utf-8') as stream:
    stream.write('\n# 最终收尾\n\n- '+summary+'\n')
    stream.write('- 最终证据助手首次对artifact-auto-clean错误沿用正式attempts根而找不到回执；只读诊断核实际Runtime明确将清理切回基础根，修正证据助手路径后61份持久回执全通过。未修改任何远端回执、状态或成功判据。\n')
    stream.write('- closeout-verification.json：固定源码程序内容未变、所有本轮构建副本删除、稳定普通执行器/代码SHA/私密配置、UTF-8及凭据扫描PASS。最终状态由ready_for_closeout转completed，最终记录随后独立提交。\n')
with (repo/'docs/request-command-log.md').open('a',encoding='utf-8') as stream:
    stream.write('\n- 2026-11-03 最终结果：'+summary+'详见doc/tasks/20261102-backend-patch-full-release/acceptance-report.md。凭据与原始日志仅private。\n')
source=Path('C:/SpugHandoff/backend-log-src-20261102/doc/tasks/20261102-backend-patch-startup-noop')
path=source/'task.md';value=path.read_text('utf-8').replace('## Current Status\nin_progress','## Current Status\ncompleted',1)
value+='\n## 最终验收\n'+summary+'完整证据位于维护仓同名发布任务。此目录是开发工作区，发布只使用另建并已删除的固定提交构建副本；用户明确不自动合入/推送int_main，开发分支保留。\n'
path.write_text(value,encoding='utf-8')
with (source/'execution-log.md').open('a',encoding='utf-8') as stream:stream.write('\n# 最终发布及收尾\n'+summary+'\n')
print(json.dumps(dict(status='written',taskStatus='completed',fullReleaseTag=tag,totalCleanupFileBytes=total)))
