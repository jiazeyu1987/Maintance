# 测试服务器备份与恢复演练方案

## Current Status
completed

## 任务目标
响应用户关于“备份按钮、选择备份包恢复按钮”的方案咨询，基于维护仓现有机制分析应用升级/降级、数据库版本变化、换机及故障场景，形成可实施的设计与验收要求。本任务只做本地只读调查和方案文档，不实施备份、恢复、部署或服务器操作。

## 任务归属
当前对话首个任务，无当前线程所属的前置未完成任务；不处理其他并发任务。

## 里程碑
1. M1：检查适用规则、经验路由及现有备份恢复契约。
2. M2：形成备份包、操作流程、兼容矩阵、故障处理及验收方案。
3. M3：核对来源、明确现有能力与建议能力，完成文档验证和收尾。

## 预期验证
仅文档与代码只读交叉核对；使用数据库等官方资料验证版本兼容边界。不得将设计审查写成真实恢复演练成功。无生产代码修改，BDD 场景作为未来实现验收要求，TDD 执行不适用。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；版本不兼容、缺失包或密钥必须明确阻断。
- 是否从根因和长期维护角度解决：是；以可验证恢复单元和明确兼容契约设计。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger：测试服备份恢复方案设计。Preflight check：先读 `E:\IntRuoyi\docs\release-backup-restore.md`，依据经验索引只读取命中条目。Blocker：缺少现有契约时不能宣称现有系统支持。Verification：方案逐项标注现有/建议/待确认。Forbidden action：不执行服务器写入、恢复或部署。Evidence：本任务 execution-log.md。
- Trigger：Windows 中文文档读写。Preflight check：显式 UTF-8，PowerShell 不使用 `&&`，输出编码设为 UTF-8。Blocker：编码异常必须停止写入。Verification：保存后 UTF-8 回读。Forbidden action：默认编码重写、输出明文凭据。Evidence：本任务 execution-log.md。
- Trigger：任务收尾。Preflight check：先标记 ready_for_closeout，再进行仅任务自有文件的 cleanup preview/apply，调用经验沉淀技能。Blocker：未经验证不能标记 completed。Verification：保留 task.md、execution-log.md、verification-report.md 和正式方案。Forbidden action：删除其他任务产物、操作无关 worktree 或进程。Evidence：verification-report.md。

## 当前进度
M1 完成：已读取适用规则、经验路由、服务器访问、登录访问、发布备份恢复与灾备技能契约。

M2 完成：已形成备份包、操作流程、兼容矩阵、故障处理、RTO/RPO、权限、API/UI 和验收方案。

M3 完成：已静态核对当前备份计划页、运行控制台、backup-ops 配置和脚本契约；已生成正式方案 `docs/recovery/backup-disaster-recovery.md` 与 `verification-report.md`。

任务已完成：实现范围为本地文档方案，无服务器操作。正式方案、验证报告、cleanup preview/apply、经验沉淀和关键词路由验证均已完成。
