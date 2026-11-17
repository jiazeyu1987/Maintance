# 理解“检测进程”线程

## Goal
只读分析用户指定线程 01a1cd7e-0968-7632-aa3f-edacd2e92c83，说明实际目标、已完成结果、当前动作和剩余事项。当前线程无前序自有任务；被分析线程的任务不属于本任务接管范围。

## Milestones
- [x] 读取最近线程状态和关键执行输出。
- [x] 核对近期用户要求，区分前一轮和当前轮次。
- [x] 给出有证据、明确时效边界的中文说明。

## Expected Verification
用户要求、执行命令与真实输出交叉核对；不把历史成功当作当前轮成功，不将线程活动状态等同于构建或发布运行中。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；按会话证据解释目标与阶段。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：Windows 中文线程分析及本地任务记录。
- Preflight check：已读取 AGENTS.md、docs/experience-index.md、docs/powershell-memory.md；中文读写显式 UTF-8，退出码单独检查；优先原生 read_thread 和游标读取。
- Blocker：缺失轮次或输出不足时只标记未知，不能推断已经发布完成。
- Verification：核对用户指令、最近命令及输出；说明仅基于线程记录。
- Forbidden action：未经本任务授权不得发送消息干预目标线程、运行发布、连接服务器、修改业务源码或清理其 worktree。
- Evidence：read_thread 最近轮次，目标标题“检测进程”，当前处于 active，最新正在修复迁移输入检查。

## Current Status
completed：已核对后续数据一致性问题；上轮恢复点的8表计数及抽查附件相符，当前实时全库一致性没有新证据，不宣称完全一致。

## Follow-up Milestone
- [x] 核对当前线程最新恢复进度、上次恢复点时间及一致性验证范围。
- [x] 给出当前可证明与不可证明的结论；不启动备份、恢复或数据库写入。

## Follow-up Verification Result
已读取 server-access.md、release-backup-restore.md、上轮验收报告及本轮任务状态，独立读取原始 selected-counts/PDF-object-integrity JSON。原始校验绑定 smallapp-bf67a867d3ec4e369ca31657c45e62c6 和目标 spug-empty59-a029c09a7b8b，expected/actual 8表计数全部相同，matched=true、serverWrites=false；PDF对象206586字节及SHA一致。计数与样本不能证明所有行内容相同，更不能证明备份点后无新增变化。

最新线程已前进至新包2026-11-17-11-53-04测试服发布 JOB-800548d984 running，正式服发布、正式服新增量备份和.59恢复仍待执行。前文“尚未构建发布”为先前读取快照，后续进度以本段为准。本任务没有实时连接两台服务器比对，因此当前实时完全一致应答为尚未证明；可证明的是上轮恢复点的已验收范围一致。

## Verification Result
已按游标读取最近十轮并对照命令输出。上一轮六步在目录删除确认后完成，收尾提交 de3da81；历史 PDF 页面问题按原用户确认范围保留。随后启动第二轮：同步代码、测试服发布、同包正式发布、正式服增量备份、备份服清空恢复、数据附件与真实公开 URL 验收。

最新快照：已恢复 GitHub 同步；独立候选整合远端 21 项与本地 6 项提交；5 个新增 SQL 中登记 4 个通用迁移、排除本机专用迁移，修正空依赖和临时表 collation。migration_inputs 静态检查通过，不代表目标准入通过。实际测试/正式目标预检均出现 TARGET_PREFLIGHT_BLOCKED:20261116_erp_data_operation_roles:CONDITION_1；迁移将 605071322 视作生产补料单，实际记录为 parent_id=991514、path=/mes/pro/craft、component=mes/pro/craft/index。偏差管理员迁移目标预检通过。本轮尚未看到构建、发布、备份或清空恢复的执行证据。

本任务仅解释线程记录，没有接管其目标或更改其工作区；无本任务 worktree、进程或运行控制台需清理。未运行产品测试（无功能或行为变更）。
