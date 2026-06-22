# 任务：备份服再次备份恢复演练

## 任务目标

在备份服务器 `172.30.30.59` 再次真实执行一轮完整备份恢复流程，重新生成备份点并完成 `backup-now -> rehearsal -> restore-data -> post-restore health` 闭环。如出现错误，先记录失败证据，再按严格 TDD 修复并重走。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-backup-server-backup-restore-rehearsal\task.md`
- 状态：`COMPLETED`
- 处理：上一轮备份服备份恢复已完成并提交 `764bb09`；本轮作为用户要求的再次演练单独建档。

## 用户要求与执行边界

- 用户要求：再进行一次备份恢复。
- 当前任务授权：
  - 允许对备份服务器 `172.30.30.59` 执行备份、恢复、演练、排障和必要修复。
  - 允许本机维护仓代码、脚本、配置与任务文档在本任务范围内修改。
- 禁止范围：
  - 未经本任务额外授权，不访问或写入正式服 `172.30.30.57`。
  - 不使用 mock、默认成功、静默跳过或降级掩盖备份恢复失败。
  - 不把备份、恢复、演练、临时目录写到 `/mnt/intruoyi-data` 之外的根分区路径。

## 技能与恢复契约

- 使用技能：`backup-disaster-recovery-readiness`。
- 恢复契约摘录：
  - 必须记录恢复范围和数据清单。
  - 必须记录恢复步骤、恢复测试证据或阻塞。
  - 必须记录配置、凭据和外部依赖注意事项。
  - 本轮不声明完整灾备 SLO 达标；RTO/RPO 未由用户本次指定，任务目标限定为再次证明备份恢复链路可真实执行。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 开始前必须确认目标环境、目标主机、目标库、对象存储 endpoint、发布包或备份点。
  - 备份、恢复、演练前必须检查根分区、数据盘、临时目录、日志目录和挂载写入权限。
  - 备份服必须显式使用 `/mnt/intruoyi-data`、`/dev/mapper/cl-home`、`/mnt/intruoyi-data/Backup/BackupPackage`。
  - 备份可用性必须以最终目录、manifest、checksum、对象清单和恢复演练证据共同判定。
  - 恢复前必须校验当前 `IMAGE_TAG` 与备份 manifest `imageTag` 匹配，恢复链、对象 manifest 和 DCC manifest 均可验证。
  - 高风险动作前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS` 或明确阻塞原因。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。如出现失败，优先修复脚本、契约、配置或测试。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 再次生成备份服备份点 -> Given 备份服运行态、数据盘、对象存储和备份仓前置条件齐全 / When 执行 backup-now / Then 生成新的可校验备份点，包含 manifest、数据库备份、对象 inventory、checksum 和 DCC 恢复契约证据。`
- `BDD: 再次执行备份服恢复演练 -> Given 新备份点与当前运行 IMAGE_TAG 匹配且恢复链可验证 / When 执行 rehearsal / Then 演练健康、登录可达和样本文件下载通过，并把演练证据写回备份仓。`
- `BDD: 再次执行备份服真实恢复 -> Given 新备份点已通过演练 / When 执行 restore-data / Then 备份服真实恢复成功，后端、前端、PDF Worker、OnlyOffice 健康检查通过。`
- `BDD: 遇错先记录再修复重走 -> Given 备份或恢复任一阶段失败 / When 采集日志、operation、manifest 和环境证据 / Then 先写入 execution-log，再按 RED/GREEN 修复并重新执行完整链路。`

## 里程碑

1. 建立本任务文档、执行日志与请求记录。`DONE`
2. 完成经验门禁、备份恢复技能与目标环境核对。`DONE`
3. 完成高风险动作前的 `experience-preflight`。`DONE`
4. 执行新的 `backup-now` 并校验产物。`DONE`
5. 执行新备份点 `rehearsal` 并校验证据写回。`DONE`
6. 执行新备份点 `restore-data` 并完成恢复后健康检查。`DONE`
7. 如有失败，补 RED/GREEN 证据、修复并重走。`DONE`
8. 完成收尾预览、任务状态和提交。`DONE`

## 预期验证

- `execution-log.md` 在远端写入前存在 `GREEN: experience-preflight -> PASS`。
- 明确记录目标主机 `172.30.30.59`、目标数据盘 `/mnt/intruoyi-data`、备份根 `/mnt/intruoyi-data/Backup/BackupPackage`、对象存储目标和当前 `IMAGE_TAG`。
- 新备份点产物校验通过：`manifest/manifest.json`、`manifest/dcc-backup-manifest.json`、`manifest/checksums.txt`、数据库备份文件、`objects/manifest-object-inventory.json`。
- 新备份点恢复演练通过，并记录 `rehearsalStatus=PASSED`。
- `restore-data` 完成后，备份服后端、前端、PDF Worker、OnlyOffice 均可访问。
- 本地受影响回归测试通过。

## 当前状态

COMPLETED：备份服新备份点 `20260622-063253` 已完成 `backup-now -> rehearsal -> restore-data -> post-restore health` 完整闭环；过程中无新增代码缺陷，首次 preflight 载体编码问题已记录并通过 UTF-8/LF 临时脚本重跑通过。

## Current Status

completed

## 最终验证结果

- `backup-now -TargetEnvironment backup -NonInteractive`：PASS，备份点 `20260622-063253` 成功生成。
- `backup-artifact-verification`：PASS，manifest、DCC manifest、checksum、MySQL dump、对象 inventory、deploy image tag 均非空且目标证明为 `backup/172.30.30.59`。
- `rehearsal -TargetEnvironment backup -SelectedBackupId 20260622-063253`：PASS，MySQL 恢复、对象回放、backend/frontend 健康、登录检查和样本文件下载均通过。
- `restore-data -TargetEnvironment backup -SelectedBackupId 20260622-063253 -NonInteractive`：PASS，真实恢复成功，pre-restore 快照为 `20260622_080538_pre-restore`。
- `post-restore-backup-server-health`：PASS，备份服后端、前端、PDF Worker、OnlyOffice 均 HTTP 200，`IMAGE_TAG=release-20260621-page-full-flow-v6`。
- `Invoke-Pester -Path ops/backup-ops/tests -EnableExit`：PASS，13/13。

## Cleanup Keep

- `doc/tasks/20260622-backup-server-backup-restore-rerun/task.md`
- `doc/tasks/20260622-backup-server-backup-restore-rerun/execution-log.md`
