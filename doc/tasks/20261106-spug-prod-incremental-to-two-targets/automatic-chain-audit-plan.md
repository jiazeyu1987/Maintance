# 自动 FULL / I1 / I2 独立验收 helper

## Current Status
ready_for_closeout — TASK 内 helper、说明及15项测试已完成，交根任务统一收口。仅执行本机 prepare-only，无远程验收/等待/重载/备份/SQL/业务写；现场 PASS 须由父任务在每个真实终态后独立取得。

## 目标与里程碑
- [x] 核现有 point/readback 验证和 Planner/read_point/epoch sidecar 正式合同。
- [x] 写验收 BDD 与任务内 RED 测试，随后实现共享真实证据审计核心与只读远端调用入口。
- [x] 以真实合同的测试样例证明 FULL 和连续增量及拒绝边界；交付调用说明，不把单测称为实际备份验收。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。证据缺失、未成功、错父链、周期不等或实际程序不符一律明确失败。
- 是否从根因和长期维护角度解决：是。将原点367专属脚本的固定假设转为显式 FULL / INCREMENTAL 与参数化前序报告，不改原脚本或原回执。
- 是否存在临时补丁或绕过：否。TASK 内正式验收工具只读取现有原生证据；不创建成功证明、不重新读取大 payload 掩盖实际证据。

## 经验门禁
- 核 130 文件实际 STANDARD 引擎逐文件 SHA、真实 owner/worker 程序 pins、原生唯一请求与退出证据。
- FULL 无父；I1/I2 精确绑定前一实际 pointPin、同 generation、相同 source/epoch、数据库日志起止连续；缺 epoch 绑定不追认历史。
- SAFE 内容读取依据完整独立 SMB readback records 与程序实现合同，不能仅凭 point COMPLETE 或缺少布尔字段判断，不能重复大 payload 全读。
- 验收必须核 sourceRestoration.restored=True/errors=[]；仅命令成功不等于当前来源语义健康，报告明确区分。
- 不输出凭据或连接；远程只读，报告只包含必要摘要、pins 与状态。先 RED 后 GREEN，现场结果由父任务运行真实完成点取得。

## BDD
- Given 同一程序代次生成一个真实成功 FULL，When 审计，Then 验证无父、唯一原生成功、完整 readback、epoch 绑定与源恢复证据。
- Given 以上 FULL 后依次生成 I1/I2，When 传入前序审计报告，Then 精确核 parent pointPin/generation/epoch 与日志连续性。
- Given 终态不成功、父链错误、内容 readback 不完整、错 epoch 或程序 pins 漂移，When 审计，Then 明确失败，不能输出 PASS。

## 交付与验证

- 核心 `automatic_chain_audit.py`；入口 `verify_automatic_backup_chain.py`；用法 `automatic-chain-audit-usage.md`；任务内测试 `test_automatic_chain_audit.py`。
- RED：入口模块未创建时测试收集失败。首次实现后9 passed/4 failed揭示测试fixture对增量使用FULL请求，改正fixture为真实INCREMENTAL后13通过；扩展纯请求binder测试后15通过。
- 最终冻结回归：同一15项全部 PASS，31.28秒，零 skip；测试使用真实临时文件、生产纯合同及本机实际130文件STANDARD包，不是现场备份证明。
- FULL373 `--prepare-only` -> PREPARED、remoteReadDispatched=false。原点367脚本、历史回执、生产源码、服务器及当前控制进程均未修改。
- 报告固定命名 `automatic-full-audit.json`、`automatic-i1-audit.json`、`automatic-i2-audit.json`，schema `AutomaticBackupChainAudit/v1`，已通知根任务与独立收尾agent。
