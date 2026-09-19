# 执行记录

## 用户需求
设计测试服务器一键备份及选择备份包恢复演练方案，详细考虑服务器升级、降级、硬件更换等变化。

## 授权与范围
只读调查和本地方案文档；未授权真实备份恢复、服务器写入、部署或改变业务数据。

## 初始化
- UTF-8 bootstrap：读取适用 AGENTS.md、经验索引及 PowerShell 经验。输出过大，后续按命中内容定向读取，不将截断部分视为已完整审阅。
- 创建 task.md，记录目标、里程碑、设计约束及经验门禁。
- 当前线程无前置所属任务。

## 规则与经验
- 读取 `E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`。
- 使用 `backup-disaster-recovery-readiness` 技能，读取技能说明与 recovery contract。
- GREEN: experience-preflight -> PASS, 本任务仅执行本地只读调查和方案文档；未授权也未执行真实备份、恢复、发布、服务器写入、数据库写入或 MinIO 写入。

## BDD 场景
- BDD: 立即全量备份 -> Given 测试服 preflight 全通过，When 操作人点击 FULL 备份，Then 后端创建异步 operation，并生成 COMPLETE 备份包、manifest、checksum、operation report。
- BDD: 立即增量备份 -> Given 存在完整全量基线且 binlog 可用，When 操作人点击 INCREMENTAL 备份，Then 生成带 parent/base 信息的增量恢复链。
- BDD: 缺少 BackupKind -> Given 备份请求没有明确 FULL/INCREMENTAL，When 请求进入后端，Then 返回阻断，不能默认选择一种。
- BDD: 候选包恢复演练 -> Given 候选包完整且兼容，When 操作人点击恢复演练，Then 系统恢复到隔离槽位并验证 health、登录、文件 hash、关键业务路径。
- BDD: 兼容恢复 -> Given 候选包已演练通过且当前测试服 fingerprint 兼容，When 操作人确认恢复，Then 系统创建 pre-restore snapshot、恢复数据、启动服务并生成 restore report。
- BDD: 升级后不兼容 -> Given 当前测试服 schema 比备份包新且没有迁移方案，When 用户选择旧包恢复，Then preview 阻断且不写任何数据。
- BDD: 降级风险 -> Given 目标 runtime 比备份包旧，When 用户选择备份包，Then 系统阻断并说明程序版本和 schema 不兼容。
- BDD: 换硬件容量不足 -> Given 新硬件磁盘容量或架构不满足备份包要求，When 用户发起恢复，Then preflight 阻断且不执行恢复。

## 静态核对证据
- 确认测试服务器静态基线：`172.30.30.58`，前端 `http://172.30.30.58:8081/`，后端 health `http://172.30.30.58:48081/actuator/health`，展厅 `http://172.30.30.58:8083/`。
- 确认 `backup-ops.config.json` 当前 schema 为 `v2-minimal`，仓库环境为 `test`，最大新鲜度 25 小时，最少可恢复链 2 条，测试服演练槽位根目录 `/backup/int-ruoyi/rehearsal/runtime`。
- 确认备份计划后台已有 `backup-now?backupKind=FULL|INCREMENTAL`；运行控制台已有恢复候选、预览和恢复动作。
- 确认备份计划页已有备份按钮和历史列表；恢复数据目前在运行控制台处理。
- 确认 `.bat` 控制台静态入口未显式传 `BackupKind`，不应作为 ChatGPT 网页直接绑定入口。
- 确认当前任务未进行服务器实时状态检查；现状介绍必须区分“静态已证实能力”和“待实时验证状态”。

## 产出
- 生成正式方案：`docs/recovery/backup-disaster-recovery.md`。

## 验证
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\backup-disaster-recovery-readiness\scripts\validate_backup_disaster_recovery.py --self-test` -> PASS, validator self-test passed.
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\backup-disaster-recovery-readiness\scripts\validate_backup_disaster_recovery.py --evidence docs\recovery\backup-disaster-recovery.md` -> PASS, evidence structure valid.
- GREEN: `python -X utf8 -c <UTF-8 read task-owned docs>` -> PASS, UTF8_OK 5.
- GREEN: `git diff --check -- <task-owned files>` -> PASS, no whitespace errors；Git reported only existing LF/CRLF normalization warning for `docs/request-command-log.md`.

## 收尾
- GREEN: `task_closeout.py --task-id 20260918-test-backup-restore-design --mode preview` -> PASS, keep core task records, delete none, blocked none.
- GREEN: `task_closeout.py --task-id 20260918-test-backup-restore-design --mode apply` -> PASS, deleted none, linked worktree false.
- Experience: 使用 `project-experience-consolidation` 规则，备份/恢复类经验合并到既有 `E:\IntRuoyi\docs\release-backup-restore.md#按钮化备份恢复入口门禁`，同步更新 `docs/experience-index.md` 关键词路由；未新建经验文件。
- GREEN: `rg -n <new backup button keywords> E:\IntRuoyi\docs\release-backup-restore.md docs\experience-index.md` -> PASS。
- GREEN: UTF-8 复读长期经验与任务文档 -> PASS, UTF8_OK 5。
- GREEN: 维护仓与 IntRuoyi 文档 `git diff --check` -> PASS，仅 LF/CRLF 规范化提示，无 whitespace error。
