# 20260723 正式服备份与备份服隔离恢复演练

## Task Goal

在用户明确授权的演练窗口内，对 IntRuoyi 执行一次真实正式服当前版本备份，并仅使用同一 `backupId` 在备份服当前脚本配置的隔离 rehearsal 目录完成恢复演练验证。

## Scope And Prohibitions

- 正式服仅允许执行当前版本 `backup-now`；禁止 `restore-data`、删除数据、重启服务、修改配置、发布或回滚应用。
- 备份服仅允许使用正式备份产生的同一 `backupId` 执行隔离 `rehearsal`；禁止覆盖备份服正常 runtime。
- 本次不授权 `restore-data -TargetEnvironment backup`；如需覆盖备份服正常 MySQL 和 `yudao` 桶，必须停止并要求用户单独书面授权。
- 禁止猜测凭据、切换环境、复用旧 `backupId`、手改 manifest、mock 成功、静默跳过校验或自动重试写入操作。
- 任务文档、日志和回复不得记录密码、token、私钥、连接串或完整敏感命令行。

## Milestones

- [x] 建立任务记录，读取备份/登录/服务器手册、经验门禁、当前 backup-ops 脚本与配置。
- [x] 只读核对正式服当前 `IMAGE_TAG`、运行容器、挂载、容量、备份根目录、临时目录、日志目录、对象存储和备份服隔离演练目录。
- [x] 在 `execution-log.md` 记录 `BLOCKER: experience-preflight -> ...`，停止所有远端写入。
- [x] 以显式的“正式来源 + 备份仓库”契约修复 backup-ops，并覆盖来源、仓库与演练目标的独立断言。
- [x] 在本地通过 BDD/TDD、解析、JSON、diff 和 UTF-8 回归验证。
- [x] 重新执行完整只读 preflight，并在通过后记录 `GREEN: experience-preflight -> PASS`。
- [x] 执行正式服 `backup-now`。最终成功备份点为 `20260724-030845`，报告 `D:\IntRuoyi-BackupOps\logs\202607\20260724_030844_backup-now_success.report.md`，状态 `success`，结果码 `INTBK-0000`。
- [x] 仅对新产生的同一 `backupId=20260724-030845` 执行备份服隔离 `rehearsal`，报告 `D:\IntRuoyi-BackupOps\logs\202607\20260724_033419_rehearsal_success.report.md`，状态 `success`，结果码 `INTBK-0000`。
- [x] 校验成功判定项并形成 Reviewer `GO` 结论。
- [x] 根据修复后的脚本重新形成 Reviewer 结论。
- [x] 完成任务收口清理与最终状态更新。

## Expected Verification

- `backup-now` 报告 `status=success` 且 `code=INTBK-0000`。
- 同一 `backupId` 的 manifest、checksum、MySQL dump、对象 inventory、部署元数据均存在且非空。
- manifest 中 `imageTag` 与本次正式服实测 `IMAGE_TAG` 一致。
- `rehearsal` 使用同一 `backupId` 并报告成功，`backendHealth`、`frontendHttp200`、`loginReachable`、`fileDownloadSample` 全部通过。
- 演练证据和 manifest 状态符合已确认的唯一状态枚举；若发现 `verified` / `PASSED` 冲突，立即记录 `BLOCKER` 并停止。

## Experience Gate

- 任务文档门禁：先建档并读取 `docs/experience-index.md`，高风险服务器写入前必须记录 `GREEN: experience-preflight -> PASS` 或 `BLOCKER: experience-preflight -> <原因>`。
- PowerShell / SSH 门禁：显式 UTF-8；PowerShell 不使用 `&&`；远端脚本避免 CRLF / stdin 污染；结构化记录退出码、目标主机和关键断言。
- 凭据脱敏门禁：不记录密码、token、私钥、连接串、完整 `.env` 或完整敏感命令行；日志只保留命令意图、目标环境、路径、退出码和脱敏错误摘要。
- 服务器访问门禁：远端动作前必须确认目标主机、目标目录、数据盘、目标容器和授权范围；正式服默认禁止写入，本任务仅授权正式 `backup-now`。
- 备份恢复门禁：备份点必须包含 manifest、checksum、MySQL dump、对象 inventory、部署元数据和 `imageTag`；未完成恢复演练不得声明备份可用。
- 备份服隔离门禁：备份服 rehearsal 只能使用 `/mnt/intruoyi-data/backup-ops/rehearsal/` 下隔离目录，不得覆盖正常 runtime；本次不授权 `restore-data -TargetEnvironment backup`。
- 当前新增门禁：正式源备份 + 备份服隔离 rehearsal 必须先证明当前脚本能把“正式服来源 backupId”落到备份服仓库，并由同一 `backupId` 驱动备份服 `rehearsal`；若 `TargetEnvironment=prod` 与 `TargetEnvironment=backup` 会改变来源或仓库语义，必须阻塞，不得切换环境、复用旧 `backupId` 或手工复制/修改 manifest。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。用户已明确授权修复脚本，使正式来源、备份仓库和隔离演练目标成为可独立证明的正式契约。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed

## Verification Evidence

- 前序任务状态：最近两个维护仓任务 `20260723-dcc-controlled-viewer-permission-test-release` 与 `20260723-codeonly-three-env-release-loop` 均为 `completed`。
- 文档读取：已读取 `server-access.md`、`login-access.md`、`release-backup-restore.md`、`powershell-memory.md`、维护仓 `powershell-preflight-lessons.md`、`experience-index.md`、backup-ops 当前脚本与配置。
- 正式服只读核对：`IMAGE_TAG=release-20260723-intmain-codeonly-three-env-r260723s-r1`；backend/frontend 容器同 tag 且运行；`/mnt/nas` 已挂载；`/mnt/nas/Backup/BackupPackage` 存在且可写；MinIO 容器运行且 `yudao` bucket 存在；`servers.production.tmpRoot=/opt/intruoyi/runtime/data/backup-ops/tmp` 当前不存在。
- 备份服只读核对：`IMAGE_TAG=release-20260723-intmain-codeonly-three-env-r260723s-r1`；正常 runtime backend/frontend 容器运行；`/mnt/intruoyi-data` 已挂载；`/mnt/intruoyi-data/Backup/BackupPackage`、`/mnt/intruoyi-data/runtime-data/backup-ops/tmp`、`/mnt/intruoyi-data/backup-ops/rehearsal/runtime` 均存在且可写；`yudao` 与 `yudao-rehearsal` bucket 均存在。
- 脚本契约核对：`backup-ops.ps1 -TargetEnvironment prod` 保留 `environment=production`；`FileOps.psm1` / `DockerOps.psm1` 对非 `backup` 的 repository 默认解析为 `test`；`backup-ops.ps1 -TargetEnvironment backup` 会把 `servers.production.host/appDir/tmpRoot` 改为备份服配置，意味着 `backup-now` 将备份备份服而非正式服。
- 当前入口核对：`00-备份恢复控制台.bat` 与 `actions/01-立即备份.bat` 仍写死 `backup-now -TargetEnvironment test`，不能作为本次正式服备份依据。
- 2026-07-23 23:37 +08:00 用户追加授权“显式支持”：允许在本机修改并测试 backup-ops，使“正式服来源 -> 备份服仓库 -> 备份服隔离 rehearsal”成为显式模式；该授权不扩大正式服 `backup-now`、备份服隔离 `rehearsal` 之外的远端写入范围。
- 脚本契约修复：新增 `-RepositoryEnvironment`，正式 `backup-now` 若未显式传入 `test|backup` 会以 `INTBK-1003` fail fast；本任务将使用 `TargetEnvironment=prod` 保持正式服来源，并使用 `RepositoryEnvironment=backup` 固定备份仓库和演练仓库到备份服。
- 跨主机 MySQL dump 修复：正式服 dump 先落到 `servers.production.tmpRoot` 的任务临时路径，再下载到本机临时 workspace 并上传到备份服 `BackupPackage`；禁止正式服直接写入备份服数据盘路径。
- DCC manifest 修复：新增 `backup.dccBackupScopeType=target-dataset` 与 `backup.dccBackupScopeId=tenant:122`，DCC manifest builder 和 chain validator 缺少范围字段时阻断。
- 本地回归：`Invoke-Pester -Script .\ops\backup-ops\tests\*.Tests.ps1` 通过 `18 passed, 0 failed`；PowerShell parser、JSON config parse、`git diff --check`、UTF-8 decode 均通过。
- 入口 fail-fast：`backup-now -TargetEnvironment prod -NonInteractive` 在未显式声明 `RepositoryEnvironment` 时以 `INTBK-1003` 阻断，证明不会静默落到测试仓库。
- 2026-07-24 远端只读 preflight：正式服 `172.30.30.57` 与备份服 `172.30.30.59` 实测 `IMAGE_TAG` 均为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`；两端 backend/frontend 镜像 tag 同步、backend health=`UP`、frontend HTTP=`200`。
- 远端路径/容量：正式服 `/mnt/nas/Backup/BackupPackage` 存在且可写，NAS 可用约 `18,095,780,460 KB`，数据盘 `/opt/intruoyi/runtime/data` 可用约 `1,866,094,092 KB`；正式服 `tmpRoot=/opt/intruoyi/runtime/data/backup-ops/tmp` 当前缺失，但其上级数据盘目录可写，允许在正式 `backup-now` 内创建任务临时目录。备份服 `/mnt/intruoyi-data/Backup/BackupPackage`、`/mnt/intruoyi-data/runtime-data/backup-ops/tmp`、`/mnt/intruoyi-data/backup-ops/rehearsal/runtime` 均存在且可写，数据盘可用约 `473,639,320 KB`。
- 对象存储：正式服 `ragflow_compose-minio-1` 的 `yudao` bucket 存在；备份服 `intruoyi-minio` 的 `yudao` 与 `yudao-rehearsal` bucket 均存在。
- 演练枚举：精确扫描 `rehearsalStatus` 字面量仅见 `PASSED`、`pending-review`、`unverified` 以及 restore-data 兼容读取的 `passed/pass`；未发现 `verified` 与 `PASSED` 写入枚举冲突。
- 门禁结论：`execution-log.md` 已记录 `GREEN: experience-preflight -> PASS`，允许进入用户授权范围内的正式 `backup-now`。
- 正式 `backup-now` 尝试：2026-07-24 00:27:24 +08:00 执行后，脚本在 `[1/7] 校验 NAS 挂载` 阶段返回 `status=blocked`、`code=INTBK-2003`、进程退出码 `1`；report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_002724_backup-now_blocked.report.md`，json=`D:\IntRuoyi-BackupOps\logs\202607\20260724_002724_backup-now_blocked.report.json`，log=`D:\IntRuoyi-BackupOps\logs\202607\20260724_002724_backup-now_blocked.log`。
- 失败完整性：未生成新 `backupId`；备份服 `BackupPackage` 未出现 2026-07-24 新备份点；正式服 `/opt/intruoyi/runtime/data/backup-ops` 未出现新目录；report `artifacts={}`、`steps=[]`。
- 失败后服务状态：正式服与备份服 backend health 均为 `UP`，frontend HTTP 均为 `200`，两端 `IMAGE_TAG` 仍为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`。
- 根因修复（未重试远端写入）：新增回归测试复现旧逻辑把备份服 `/mnt/intruoyi-data/Backup/BackupPackage` 仓库路径拿到正式源主机检查；修复 `Assert-BackupOpsRemoteNasMounted` 后，仓库主机检查仓库挂载，正式源主机仅检查 `tmpRoot` 的受控数据盘基础路径。`Invoke-Pester -Script .\ops\backup-ops\tests\*.Tests.ps1` 通过 `19 passed, 0 failed`，`FileOps.psm1` parser PASS。
- 经验沉淀：已将本轮 `INTBK-2003` / `backup-source NAS 未就绪` 可复用门禁合并到 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` 的既有正式源备份到备份服隔离演练仓库门禁，并更新 `docs/experience-index.md` 路由。
- 2026-07-24 00:44:03 +08:00 用户重新授权：允许在已修复 FileOps 挂载检查后再次提交一次正式 `backup-now`；授权范围仍不包含 `restore-data -TargetEnvironment backup`、覆盖备份服正常 runtime、手改 manifest、复用旧 `backupId` 或自动重复重试。
- 正式 `backup-now` 第二次尝试：2026-07-24 00:44:57 +08:00 执行后，脚本进入 `[3/7] 导出 MySQL` 阶段并生成 `backupId=20260724-004458`，随后以 `status=blocked`、`code=INTBK-3002`、进程退出码 `1` 阻断；report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_004457_backup-now_blocked.report.md`，json=`D:\IntRuoyi-BackupOps\logs\202607\20260724_004457_backup-now_blocked.report.json`，log=`D:\IntRuoyi-BackupOps\logs\202607\20260724_004457_backup-now_blocked.log`。
- 第二次失败完整性：备份服 `/mnt/intruoyi-data/Backup/BackupPackage/20260724-004458` 不存在；正式服仅存在临时目录 `/opt/intruoyi/runtime/data/backup-ops/tmp/backup-now/20260724-004458/mysql`，未发现 dump 文件；本机仅存在空工作目录 `D:\IntRuoyi-BackupOps\tmp\20260724-004458\deploy|manifest|mysql|objects`；blocked report `artifacts={}`、`steps=[]`。
- 第二次失败后服务状态：正式服与备份服 backend health 均为 `UP`，frontend HTTP 均为 `200`，两端 `IMAGE_TAG` 仍为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`。
- MySQL 根因修复（未重试远端写入）：新增回归测试复现 `Export-BackupMySqlDump` 对正式源中转路径仍强制 BackupPackage 校验；修复后只有显式 `AllowSourceTempDumpPath + SourceTempRoot` 的 cross-host 导出允许写正式源临时路径，恢复导入仍必须来自 BackupPackage。`Invoke-Pester -Script .\ops\backup-ops\tests\*.Tests.ps1` 通过 `20 passed, 0 failed`，MySQL parser PASS。
- 2026-07-24 00:52:52 +08:00 用户再次授权：允许在已修复 MySQL 导出中转路径校验后再次提交一次正式 `backup-now`；授权范围仍不包含 `restore-data -TargetEnvironment backup`、覆盖备份服正常 runtime、手改 manifest、复用旧 `backupId` 或自动重复重试。
- 正式 `backup-now` 第三次尝试：2026-07-24 00:54:13 +08:00 执行后，脚本进入 `[4/7] 备份 MinIO 对象` 阶段并生成 `backupId=20260724-005414`，随后以 `status=blocked`、`code=INTBK-4001`、进程退出码 `1` 阻断；report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_005413_backup-now_blocked.report.md`，json=`D:\IntRuoyi-BackupOps\logs\202607\20260724_005413_backup-now_blocked.report.json`，log=`D:\IntRuoyi-BackupOps\logs\202607\20260724_005413_backup-now_blocked.log`。
- 第三次失败完整性：备份服 `/mnt/intruoyi-data/Backup/BackupPackage/20260724-005414/mysql/ruoyi-vue-pro.sql.gz` 存在且大小约 `6080019020` bytes；但同一备份点缺少对象 inventory、manifest、checksum 和部署元数据，属于不完整备份点，禁止用于 rehearsal 或 restore。
- 第三次失败后服务状态：正式服与备份服 backend health 均为 `UP`，frontend HTTP 均为 `200`，两端 `IMAGE_TAG` 仍为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`。
- ObjectOps 根因修复（未自动重试远端写入）：新增回归测试复现远端 `mc --json` 输出前混入 Docker pull/status 行导致 `Invalid JSON primitive: Unable`；修复后对象元数据解析会跳过已知 Docker 拉取状态噪声，但仍阻断真实非 JSON 输出。`Invoke-Pester -Script .\ops\backup-ops\tests\*.Tests.ps1` 通过 `22 passed, 0 failed`，ObjectOps parser PASS。
- 2026-07-24 01:25:17 +08:00 用户再次回复“授权”：允许在已修复 ObjectOps 元数据解析后再次提交一次正式 `backup-now`；授权范围仍不包含 `restore-data -TargetEnvironment backup`、覆盖备份服正常 runtime、手改 manifest、复用旧 `backupId` 或自动重复重试。
- 第四次远端写入前本地门禁：首次复跑 Pester 暴露 2 个测试隔离断言问题，未触发远端写入；修复后 `Invoke-Pester -Script .\ops\backup-ops\tests\*.Tests.ps1` 通过 `22 passed, 0 failed`，PowerShell parser、JSON config parse、UTF-8 decode 和 `git diff --check` 均通过。
- 第四次只读 preflight：正式服与备份服 `IMAGE_TAG` 均为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`；两端 backend/frontend 镜像同 tag 且 running；backend health=`UP`；frontend HTTP=`200`；正式服 `/mnt/nas/Backup/BackupPackage` 可写且 `yudao` bucket 存在；备份服 `/mnt/intruoyi-data/Backup/BackupPackage`、`tmpRoot`、`rehearsalRoot` 可写，`yudao` 与 `yudao-rehearsal` bucket 存在。
- 正式 `backup-now` 第四次尝试：2026-07-24 01:38:15 +08:00 执行后，脚本进入 `[5/7] 生成 checksums 与 manifest` 阶段并生成 `backupId=20260724-013816`，随后以 `status=blocked`、`code=INTBK-6001`、进程退出码 `2` 阻断；report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_013815_backup-now_blocked.report.md`，json=`D:\IntRuoyi-BackupOps\logs\202607\20260724_013815_backup-now_blocked.report.json`，log=`D:\IntRuoyi-BackupOps\logs\202607\20260724_013815_backup-now_blocked.log`。
- 第四次阻断原因：DCC 备份 manifest 构建失败，诊断文件 `D:\IntRuoyi-BackupOps\tmp\20260724-013816\manifest\dcc-backup-manifest.json` 显示 `dcc_object_inventory_missing:384`；341 个受控文件记录、对象 inventory 44,207 项、缺失引用 384 项、唯一路径 288 项，首个缺失路径为 `codex-e2e/CODEX_E2E_T4_E11_1779725588169.pdf.original.pdf`。
- 第四次失败完整性：本机临时 workspace 存在 MySQL dump `6080009151` bytes、对象 inventory `15854307` bytes、deploy runtime.env `3625` bytes、image-tag.txt，且 imageTag 匹配正式服实测；本机和备份服均未生成最终 `manifest/manifest.json` 或 `checksums/sha256sums.txt`。备份服 `/mnt/intruoyi-data/Backup/BackupPackage/20260724-013816/mysql/ruoyi-vue-pro.sql.gz` 存在且大小 `6080009151` bytes；备份服缺少对象 inventory、DCC manifest、最终 manifest、checksum 和 deploy 元数据。
- 第四次失败后服务状态：正式服与备份服 backend health 均为 `UP`，frontend HTTP 均为 `200`，两端 `IMAGE_TAG` 仍为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`。
- 演练状态：未执行 `rehearsal`，因为 `backup-now` 未成功且 `backupId=20260724-013816` 不是完整可用备份点；禁止复用该 `backupId`。
- 2026-07-24 02:16:24 +08:00 用户回复“授权”：本轮按只读排查 DCC 缺失对象来源处理；未授权修生产数据、补对象、删除记录、调整备份范围、重试 `backup-now` 或执行 `rehearsal`。
- DCC 缺口只读定位：失败备份本机 DCC 快照显示 96 个 `ACTIVE` 的 `CODEX-E2E-*` 受控文件仍引用 `codex-e2e/` 前缀对象；原始查询共 384 条对象角色引用，规范化后为 288 个唯一对象路径，分布为 original/published/stamped 各 96，source 角色重复引用 original。
- 对象桶只读定位：失败备份对象 inventory 共 44,207 项，`codex-e2e/` 前缀为 0；正式 MinIO `yudao` bucket 内 `codex-e2e/` 目录缺失，抽样 original/published/stamped 三个对象均缺失；同样方法验证已知 inventory 对象存在，排除抽样路径检查失效。
- 历史来源只读定位：备份服 `/mnt/intruoyi-data/Backup/BackupPackage` 和正式服 `/mnt/nas/Backup/BackupPackage` 的历史备份 manifest/object inventory 均未命中 `codex-e2e/`；当前没有在备份仓内发现可直接恢复这些对象的证据。
- 2026-07-24 02:24:30 +08:00 用户再次回复“授权”：已记录为收到继续处理意向，但当前开放阻塞需要先在“恢复缺失对象 / 软删除或下线孤儿 DCC 记录 / 正式调整备份范围”之间选择具体策略；本条未指定策略，因此不得触发生产数据写入、对象补齐、备份范围修改、重新 `backup-now` 或 `rehearsal`。
- 历史修复清单比对：只读读取 `D:\ProjectPackage\Int\IntRuoyi\doc\tasks\20260613-prod-data-backup` 证据，历史任务曾在用户授权下对 96 条 `tenant_id=122`、`CODEX-E2E%`、`ACTIVE` 且对象路径为 `codex-e2e/%` 的测试残留主记录执行可回滚软删除，并在随后正式备份中得到 `INTBK-0000`；当前 `20260724-013816` 失败 manifest 中的 96 个 `controlled-file` ID 与历史 `affected-dcc-codex-e2e-records.csv` 完全一致（CurrentOnly=0、HistoricalOnly=0）。该证据支持“软删除/下线孤儿 DCC 记录”为当前最小可回滚候选策略，但仍需用户明确选择并授权后才可写入。
- 2026-07-24 02:28:35 +08:00 用户回复“授权”：按上一条要求解释为明确授权“按历史同清单软删除/下线这 96 条生产 DCC 测试残留记录，并先导出修复前快照与回滚 SQL，验证后重新执行正式 `backup-now`”。执行门禁：若当前正式库命中数不是 96、存在非 `tenant_id=122` / 非 `CODEX-E2E%` / 非 `ACTIVE` / 已删除记录、对象路径不全为 `codex-e2e/%`、存在其他活跃 DCC 主记录共享对象、无法导出回滚 SQL，立即阻塞且不得写入。
- 生产 DCC 修复预检：正式库只读预检通过，指标为 `target_rows=96`、`target_safe_rows=96`、`target_bad_rows=0`、`target_ref_rows=384`、`target_missing_infra_refs=0`、`target_non_codex_path_refs=0`、`target_deleted_infra_refs=0`、`target_unique_paths=288`、`other_active_records_sharing_target_file_ids=0`；已导出回滚 SQL `doc/tasks/20260723-prod-backup-rehearsal/evidence/prod-dcc-codex-e2e-before-20260724-rollback.sql`，大小 69,608 bytes。
- 生产 DCC 写入尝试：第一次软删除事务在构建事务内临时引用表时被 MySQL `ERROR 1137 (HY000): Can't reopen table` 阻断，发生在 `UPDATE dcc_controlled_file` 之前；随后只读 postcheck 确认 `target_rows=96`、`target_deleted_rows=0`、`target_active_rows=96`、`target_safe_rows=96`，即正式数据未发生变更。按“不得自动重试写入操作”要求停止，等待用户对修正后的无临时表重开 SQL 再次授权。
- 2026-07-24 02:35:39 +08:00 用户回复“授权”：按上一条要求解释为授权使用修正后的无临时表重开 SQL 再执行一次软删除；执行前重新跑正式库只读预检，事务内再次校验 96 条目标范围和共享引用计数，不满足即回滚。
- 修正版软删除结果：重新预检通过；无临时表重开事务返回 `commit_decision=COMMIT`、`updated_rows=96`、`post_deleted_rows_in_tx=96`、`post_active_rows_in_tx=0`；独立 postcheck 确认 `target_rows=96`、`target_deleted_rows=96`、`target_active_rows=0`、`target_updater_rows=96`。已保留回滚 SQL，下一步按授权重新执行正式 `backup-now`，不得复用旧 `backupId`。
- 正式 `backup-now` 第五次尝试：2026-07-24 02:38:39 +08:00 执行后生成新 `backupId=20260724-023840`，DCC manifest 已成功生成，但在 `[5/7] 生成 checksums 与 manifest` 阶段以 `status=fail`、`INTBK-6003`、进程退出码 `1` 失败；根因为当前子进程 PowerShell 运行时缺少 `Get-FileHash`。本机临时 workspace 有 MySQL dump、对象 inventory、DCC manifest、deploy 元数据；缺少最终 `manifest/manifest.json` 与 `manifest/checksums.txt`，备份服仅有 MySQL dump 和 object copy plan 脚本/TSV，未形成完整备份点，禁止用于 rehearsal。
- 本地根因修复：已将 checksum 生成改为 `Get-BackupOpsFileSha256`（.NET SHA256），不再依赖 `Get-FileHash`；新增回归测试 `computes checksum hashes without depending on Get-FileHash`。`Invoke-Pester -Script .\ops\backup-ops\tests\*.Tests.ps1` 通过 23 passed、0 failed；`FileOps.psm1` 与测试 parser PASS。按禁止自动重试写入要求，修复后未再次执行 `backup-now`。
- 2026-07-24 03:07 +08:00 用户重新授权：允许在已修复 checksum 逻辑后重新提交一次新的正式 `backup-now`；授权范围仍不包含 `restore-data -TargetEnvironment backup`、覆盖备份服正常 runtime、手改 manifest、复用旧 `backupId`、重启、发布、回滚或删除文件。
- 远端写入前本地门禁：`Invoke-Pester -Script .\ops\backup-ops\tests\*.Tests.ps1` 通过 23 passed、0 failed；PowerShell parser PASS；backup-ops JSON config parse PASS；`git diff --check` 无错误，仅既有 CRLF 工作区提示；`rehearsalStatus=verified` 写入枚举扫描无命中。
- 最终正式备份：`backup-now` 使用 `TargetEnvironment=prod` + `RepositoryEnvironment=backup` + 当前生产确认机制，返回 `status=success`、`code=INTBK-0000`、exitCode=0；新 `backupId=20260724-030845`；report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_030844_backup-now_success.report.md`，json=`D:\IntRuoyi-BackupOps\logs\202607\20260724_030844_backup-now_success.report.json`，log=`D:\IntRuoyi-BackupOps\logs\202607\20260724_030844_backup-now_success.log`。
- 最终备份产物完整性：本机和备份服仓库同一 `backupId=20260724-030845` 下 `manifest/manifest.json`、`manifest/checksums.txt`、`mysql/ruoyi-vue-pro.sql.gz`、`objects/manifest-object-inventory.json`、`manifest/dcc-backup-manifest.json`、`deploy/runtime.env`、`deploy/image-tag.txt` 均存在且非空；本机文件大小分别为 15,857,625 bytes、368 bytes、6,080,022,752 bytes、15,854,307 bytes、8,765,072 bytes、3,625 bytes、57 bytes。
- manifest 校验：`imageTag=release-20260723-intmain-codeonly-three-env-r260723s-r1` 与本次正式服实测一致；`recoverySet.status=COMPLETE`；对象清单 44,207 项；DCC manifest `status=success`；`manifest/checksums.txt` 的 SHA256 与 manifest `recoverySet.checksums.sha256=58744d240fe7c8bbdd6fbb9946d377b0c45bb2e25226d38d2fcb4ee7c8492faa` 一致。
- 备份服隔离演练：`rehearsal` 使用同一 `backupId=20260724-030845`，固定 `TargetEnvironment=backup` + `RepositoryEnvironment=backup`，使用脚本配置的 `/mnt/intruoyi-data/backup-ops/rehearsal/runtime` 与 `yudao-rehearsal`，返回 `status=success`、`code=INTBK-0000`；report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_033419_rehearsal_success.report.md`，json=`D:\IntRuoyi-BackupOps\logs\202607\20260724_033419_rehearsal_success.report.json`，log=`D:\IntRuoyi-BackupOps\logs\202607\20260724_033419_rehearsal_success.log`。
- 演练校验：`backendHealth=pass`、`frontendHttp200=pass`、`loginReachable=pass`、`fileDownloadSample=pass`；本地 evidence `ops/backup-ops/tmp/rehearsal/20260724-030845/evidence/rehearsal-report.json` 594 bytes，`现场快照.md` 315 bytes。
- 远端 manifest 写回：备份服仓库 manifest `validation.rehearsalStatus=PASSED`、`lastRehearsedAt=2026-07-24T04:10:18.3602097+08:00`；远端 `manifest/rehearsal-report.json` 594 bytes，`manifest/现场快照.md` 315 bytes，报告 `status=PASSED` 且四项 checks 全部 pass。
- 正常 runtime 未覆盖：备份服正常 `intruoyi-backend`、`intruoyi-frontend` 仍运行在 `release-20260723-intmain-codeonly-three-env-r260723s-r1` 且约 25 小时未重启；正常 frontend HTTP 200。隔离演练容器为 `intruoyi-rehearsal-*`，端口 `48082/18081`，与正常 runtime 并行独立。
- 经验沉淀：已按 `project-experience-consolidation` 将 `INTBK-6003` / `Get-FileHash` 缺失导致 checksum 失败的门禁合并到既有 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md#正式源备份到备份服隔离演练仓库门禁`，并更新维护仓 `docs/experience-index.md` 路由；未新建长期经验文档。

## Blockers

- 当前无开放阻塞：正式 `backup-now` 和备份服隔离 `rehearsal` 均已成功，成功判定项均满足。
- 仍禁止动作：未授权 `restore-data -TargetEnvironment backup`、覆盖备份服正常 MySQL 或正常 `yudao` 桶、复用旧失败 `backupId`、手改 manifest、自动重试写入、重启、发布、回滚、删除或配置修改。

## Cleanup Keep

- `doc/tasks/20260723-prod-backup-rehearsal/evidence/`
- `ops/backup-ops/tmp/rehearsal/20260724-030845/evidence/`

## Closeout Evidence

- `task-closeout-cleanup` preview/apply 均通过，status=`applied`，delete=`<none>`，blocked=`<none>`，warnings=`<none>`。
- 当前工作区是主工作区 `int_main`，不是 linked worktree；无需 worktree merge 或 removal。
