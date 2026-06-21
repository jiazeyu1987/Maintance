# 任务：备份服完整备份恢复演练

## 任务目标

在备份服务器 `172.30.30.59` 上真实走一遍完整的备份与恢复流程。过程中如出现脚本、配置、候选、环境或校验错误，必须先记录失败证据，再按严格 TDD 修复并重走，直到可以一次性完成一整套备份恢复闭环。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-fupan-frontend-release-full-flow-v6\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成项目短记忆复盘与收尾，不存在未收口的远端操作阻塞；本任务作为新的高风险备份恢复演练单独建档。

## 用户要求与执行边界

- 用户要求：
  - 在备份服真实走一遍完整备份恢复流程
  - 发现错误时必须修改并记录
  - 持续重试直到可以一次性走完整套流程
- 当前任务授权：
  - 允许对备份服务器 `172.30.30.59` 执行备份、恢复、排障和必要修复
  - 允许本机代码、脚本、配置与任务文档修改
- 禁止范围：
  - 未经本任务额外授权，不访问或写入正式服 `172.30.30.57`
  - 不用 mock、默认成功、静默跳过或降级掩盖备份恢复失败
  - 不把备份、恢复或演练数据写到 `/mnt/intruoyi-data` 之外的默认根分区路径

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 备份、恢复、回滚和演练前，必须先确认目标环境、目标主机、目标库、对象存储 endpoint、发布包或备份点。
  - 备份或恢复前必须检查根分区、NAS、数据盘、临时目录、日志目录和挂载写入权限；备份服必须显式使用 `/mnt/intruoyi-data` 相关路径与 `/dev/mapper/cl-home` 数据盘。
  - 备份成功不能只看 operation 或脚本退出码，必须同时校验最终备份目录、manifest、数据库备份、对象 inventory 和 checksum。
  - 恢复前必须校验 `IMAGE_TAG`、schema、恢复链、对象仓库与 DCC manifest 契约；缺证据时直接阻塞。
  - 真实登录或 E2E 验证前必须先走最小登录路径，登录失败要明确报告实际入口、租户、账号和影响，不得静默切换环境或账号。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。发现问题后优先修脚本、契约、配置或测试，而不是手工绕过当前步骤。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 备份服完整备份流程 -> Given 备份服发布版本、数据盘、对象存储和备份脚本前置条件齐全 / When 执行真实备份流程 / Then 生成可校验的备份点，包含 manifest、数据库备份、对象 inventory、checksum 和恢复契约证据。`
- `BDD: 备份服完整恢复流程 -> Given 已有同环境可恢复备份点且当前运行版本与 manifest imageTag 兼容 / When 执行真实恢复流程 / Then 恢复动作成功，恢复后服务健康，目标业务入口与关键校验通过。`
- `BDD: 遇错先记录再修复重走 -> Given 备份或恢复任一阶段失败 / When 采集 operation、日志、脚本输出和环境证据 / Then 先把失败与根因写入 execution-log，再按严格 TDD 修复并从头重走直至一次性通过。`

## 里程碑

1. 处理上一任务状态检查并建立本任务文档、执行日志与请求记录。`DONE`
2. 读取技能、经验门禁和恢复契约，核对备份服目标、脚本入口、配置与恢复候选。`DONE`
3. 完成高风险动作前的 `experience-preflight` 与环境 preflight。`DONE`
4. 在备份服执行完整备份流程并校验产物。`DONE`
5. 在备份服执行完整恢复流程并完成健康与业务验证。`DONE`
6. 如有失败，补 RED/GREEN 证据、修复并重走直到一次性通过。`DONE`
7. 完成收尾预览、任务结论与提交范围整理。`DONE`

## 预期验证

- `execution-log.md` 在任何远端写入前存在 `GREEN: experience-preflight -> PASS`
- 明确记录本次目标主机、目标数据盘、目标发布目录、目标备份根目录和对象存储目标
- 至少一套真实备份点产物校验通过：`manifest/manifest.json`、`manifest/dcc-backup-manifest.json`、数据库备份文件、对象 inventory、checksum
- 恢复流程完成后，备份服后端健康、前端入口可访问，必要时补真实登录和核心路径验证
- 若发现脚本或配置缺陷，存在对应 `BDD`、`RED`、`GREEN` 记录和测试/回归证据
- 最终存在“一次性走通”的完整备份恢复链路证据

## 当前状态

COMPLETED：备份服 `20260621-202814` 已完成真实 `backup-now`、`rehearsal` 和 `restore-data`，恢复后备份服健康检查通过；本任务缺陷修复均已有 RED/GREEN 证据和本地回归测试覆盖。

## Current Status

completed

## 最终验证结果

- `backup-now -TargetEnvironment backup -NonInteractive`：PASS，备份点 `20260621-202814` 成功生成完整产物。
- `rehearsal -TargetEnvironment backup -SelectedBackupId 20260621-202814`：PASS，演练健康、登录可达和样本文件下载均通过，远端 manifest 已记录 `rehearsalStatus=PASSED`。
- `restore-data -TargetEnvironment backup -SelectedBackupId 20260621-202814 -NonInteractive`：PASS，真实恢复完成，恢复后备份服后端、前端、PDF Worker、OnlyOffice 均 HTTP 200。
- `Invoke-Pester -Path ops/backup-ops/tests -EnableExit`：PASS，13/13 通过。

## Cleanup Keep

- `doc/tasks/20260621-backup-server-backup-restore-rehearsal/bug-regression-evidence.md`
