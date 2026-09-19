# Execution Log

## Request

- 用户要求仅基于当前分支最新已提交代码完成一次测试服发布；未提交改动不得进入构建产物；发布成功后必须验证真实运行态、记录全过程问题并沉淀前置经验。

## Timeline

- Bootstrap: 读取适用 `AGENTS.md`、最近任务状态、`docs/experience-index.md` 和 `E:\IntRuoyi\docs\powershell-memory.md`。
- ISSUE: PowerShell bootstrap 初次使用 Bash heredoc `<<'PY'` 导致 ParserError。
  - 阶段：只读引导。
  - 影响：未读取任何目标文件，需改用 PowerShell 兼容承载方式。
  - 原因判断：PowerShell 5.1 不支持 Bash heredoc 重定向语法。
  - 处理动作：改用 PowerShell here-string 传给 `python -X utf8 -c`。
  - 结果：只读引导成功。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：PowerShell 中禁止使用 Bash heredoc；多行 Python 使用 here-string 或独立脚本文件。

## BDD

- BDD: 仅测试服 HEAD 发布 -> Given 当前分支存在已提交 HEAD 且工作区可能有未提交改动, When 创建干净临时发布 worktree 并基于该 worktree 构建发布包后仅执行 publish-test, Then 构建产物只包含冻结 HEAD、测试服运行态指向同一 releaseTag，且正式服/备份服未被发布。

## TDD / Verification Evidence

- GREEN: experience-preflight -> PASS, 已读取并摘取 `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\powershell-memory.md` 的本次仅测试服发布强制门禁。
- GREEN: git-freeze-maintenance -> PASS, 维护仓 branch=`int_main`, HEAD=`ed7ef820d57fc0185e5c16a8be2e820a13384b15`; 主工作区 dirty，因此禁止直接构建，必须使用 clean release worktree。
- GREEN: git-freeze-main-program -> PASS, 主程序仓 `E:\IntRuoyi` branch=`int_main`, HEAD=`1606947b7598eca15e904362759a7236a255dbbf`; 后端与前端同属该 Git root，主工作区 dirty，因此禁止直接构建，必须使用 clean release worktree。

## Issues

- 见 Timeline 初始 PowerShell heredoc 问题；后续问题按同一结构追加。
- ISSUE: 维护仓和主程序主工作区均存在未提交改动。
  - 阶段：Git / worktree 冻结。
  - 影响：直接从主工作区构建会污染发布来源，不能证明产物只包含 HEAD 已提交代码。
  - 原因判断：系统持续开发中，主工作区存在并发/历史脏改动。
  - 处理动作：本轮使用 `r260803a` 专用 clean release worktree，构建开始后只认冻结 HEAD。
  - 结果：待创建并复核。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：发布前固定执行三仓 `git status --short --branch`、`git rev-parse HEAD`；dirty 时强制 release worktree。
- ISSUE: 主程序后端/前端 `git status` 输出大量 `target_corrupt_m4_20260802_1327` 缺失目录 warning。
  - 阶段：Git / worktree 冻结。
  - 影响：状态命令仍成功，但 warning 会干扰日志阅读；构建不得使用该 dirty 主工作区。
  - 原因判断：主工作区存在历史构建残留或损坏 target 目录。
  - 处理动作：记录 warning，并通过 clean release worktree 隔离构建输入。
  - 结果：不阻塞 clean HEAD worktree 发布；若 clean worktree 复现则阻塞。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：发布前状态输出应分层记录 warning；构建前必须复核 release worktree clean。

## Progress Reviews

- Startup: 维护仓与主程序仓主工作区均 dirty，本轮计划使用 `r260803a` clean release worktrees，releaseTag=`release-20260803-intmain-head-test-r260803a-r1`。

## Continued Evidence - Build and Publish

- GREEN: release-worktrees-clean -> PASS, 维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803a\m` 与主程序 release worktree `D:\IntRuoyiWorktree\r260803a-release-app` 均指向冻结 HEAD 且构建输入 clean。
- GREEN: migration-policy-gate -> PASS, evidence `migration-policy-gate-r260803a.json`，`migrationCount=415`。
- GREEN: maintenance-console-build -> PASS, `scripts\build.ps1` 成功，前端 typecheck/build 成功，Maven tests `26` run / `0` failures / `0` errors，jar `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 生成。
- GREEN: build-release -> PASS, operation=`op-2026-08-02T164907897014700Z-a76bd666-e3b7-449a-b77f-e4541826cd8f`，releaseTag=`release-20260803-intmain-head-test-r260803a-r1`，发布包路径 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260803-intmain-head-test-r260803a-r1`。
- GREEN: manifest-validation -> PASS, `manifest-validation-r260803a-r1.json` status=`passed` / code=`MANIFEST_VALIDATION_PASSED`；`manifest-summary-r260803a-r1.json` 记录 sourceRepos 均为主程序冻结 commit `1606947b7598eca15e904362759a7236a255dbbf` 且 dirty=false，artifactCount=`429`，requiredSqlCount=`419`。
- GREEN: frontend-release-info-image -> PASS, `frontend-release-info-image-r260803a-r1.json` 中 releaseTag、changeSet、sourceRepos commit 与 manifest 一致。
- GREEN: publish-test-preview -> PASS, `publish-test-preview-gate-r260803a-r1.json` 确认 action=`publish-test`、mode=`deploy-release`、Environment=`test`、ServerHost=`172.30.30.58`、RemoteAppDir=`/opt/intruoyi/runtime`，无 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: remote-prepublish-status -> PASS, `remote-prepublish-status-r260803a-r1.json` 显示测试服 backend HTTP 200、frontend HTTP 200、PDF worker HTTP 200、当前 releaseTag=`release-20260802-feedback-fix-test-r260802h-r1`。
- GREEN: remote-release-precheck-before-publish -> PASS, 首次只读 release lock/migration gate 显示 `RUNNING_LOCK_COUNT=0`、目标 releaseTag `FAILED/RUNNING=0`、target migration rows=0。
- RED: publish-test -> FAIL, operation=`op-2026-08-02T171256308397600Z-05598a68-af1a-4f8f-8db2-3b7806418241`，status=`FAILED`，summary=`命令退出码非 0: 1`；脱敏日志 `publish-test-log-tail-r260803a-r1.redacted.txt` 显示 required SQL `20260513_dcc_base_schema.sql` 执行失败，MySQL `ERROR 1062 (23000) at line 1298: Duplicate entry '6813' for key 'system_menu.PRIMARY'`。
- GREEN: failed-publish-state-frozen -> PASS, `remote-release-postrestore-r260803a-r1.json` 显示 release lock=`FAILED`、目标 releaseTag migration rows=`378`、`FAILED/RUNNING=1`、无 running lock；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: failed-env-stabilized -> PASS, 失败后 `.env IMAGE_TAG` 一度变为目标 releaseTag 但容器仍运行上一轮 tag；`remote-env-restore-after-failed-publish-r260803a-r1.json` 已将 `.env IMAGE_TAG` 恢复为 `release-20260802-feedback-fix-test-r260802h-r1`，且 backend/frontend 容器镜像均为该 tag。
- GREEN: postfailure-health-after-env-restore -> PASS, `remote-postfailure-health-after-env-restore-r260803a-r1.json` 显示 backend health=UP、frontend HTTP 200、远端 `/release-info.json` 仍为上一轮成功 release。

## Additional Issues

- ISSUE: 本地 PowerShell inline 脚本多次因 Bash heredoc、正则引号或 `$()` 被宿主 PowerShell 提前解析失败。
  - 阶段：远端预检与轮询工具编排。
  - 影响：未触发服务器写入，但延长排障时间，且容易误判为远端失败。
  - 原因判断：PowerShell 不是 Bash；复杂 Python/SSH/正则内容直接放入命令字符串会被本地 shell 先解析。
  - 处理动作：改为任务目录内 helper 脚本 `remote_release_probe.py`、`runtime_control_publish_test.py`、`runtime_control_monitor_publish.py`、`restore_failed_publish_env.py`。
  - 结果：预检、发布轮询和失败收束证据可复现。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：发布长链路只用文件化 helper 或 UTF-8 bytes stdin，避免 inline 多行脚本。
- ISSUE: 远端 `.env` 不能直接 `source`。
  - 阶段：只读 release lock/migration 预检。
  - 影响：首次 helper 误把未加引号的 `JAVA_OPTS=-Xmx2g ...` 当命令执行并失败。
  - 原因判断：`.env` 并非严格 shell source 文件。
  - 处理动作：helper 改为只用 `sed` 读取所需 key，不 source 整个 `.env`。
  - 结果：release state gate 通过。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：远端 `.env` 只读解析 key/value，不整体 source。
- ISSUE: `publish-test` 长时间无状态变化，日志看似停在 NAS mount。
  - 阶段：发布包远端分发与 required SQL 状态更新。
  - 影响：runtime-control operation summary 长时间保持“提交到本机执行队列”，初看像卡死。
  - 原因判断：脚本逐文件 `scp` 419 个 required SQL，并逐条通过 SSH/MySQL 记录迁移状态；operation summary 不反映子阶段进度。
  - 处理动作：通过进程树和脱敏日志确认 `scp`/`ssh` 子进程持续推进，未重提 operation。
  - 结果：等待到真实失败点，避免重复发布。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：监控 result log `LastWriteTime`、子进程命令和当前 SQL 文件；不要因 summary 未更新就重试。
- ISSUE: 原始 publish log / 进程命令行包含 MySQL `-p...` 形态。
  - 阶段：publish-test required SQL。
  - 影响：原始日志不能提交或复制到任务记录；进程扫描也可能短暂暴露命令行凭据。
  - 原因判断：现有发布脚本通过命令行传递 MySQL 密码并记录 SSH/MySQL 命令。
  - 处理动作：任务证据只保存 `publish-test-log-tail-r260803a-r1.redacted.txt`；最终记录只写脱敏摘要。
  - 结果：任务记录不包含明文密码。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：发布脚本应使用 `MYSQL_PWD` 或远端临时配置并默认脱敏；进程扫描只输出 PID/阶段，不输出完整 command line。
- ISSUE: publish-test required SQL checksum 漂移后重放 `20260513_dcc_base_schema.sql`，在 `system_menu.id=6813` 失败。
  - 阶段：测试服 required SQL 执行。
  - 影响：发布失败，release lock=`FAILED`，目标 releaseTag migration `FAILED/RUNNING=1`，不得判定测试服发布成功，不得继续 mark/promote。
  - 原因判断：目标 state 中该 migration 已有旧 checksum `9c6d4004565813ebfc8b1ad0454c6eb7d27302a348f426f1ad94795774c2bd33`，本轮 manifest checksum 为 `4751b23cf28e932d936f3c6a81d9aee109afbd6fa509189dd50d589ac6abfe28`；preflight-plan 将其判为 `APPLY`，但 SQL 中部分 `INSERT INTO system_menu ... SELECT ... WHERE NOT EXISTS(permission)` 未同时防护固定主键 ID，占用时触发 duplicate primary key。
  - 处理动作：冻结 preview、operation final、脱敏 log、preflight-plan summary、远端 release lock/migration 状态；不手工改 release lock/migration，不复用失败 releaseTag。
  - 结果：任务 blocked，继续需修复 SQL 幂等性/checksum 漂移根因后重新构建新 releaseTag。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：preflight-plan 中出现 `target checksum differs -> APPLY` 的菜单/权限 SQL 时，必须先只读核对目标库固定 ID 与业务键，发现占用或非幂等时在镜像加载、`.env` 更新和 SQL 执行前 fail fast。
- ISSUE: publish-test 失败后 `.env IMAGE_TAG` 与实际容器镜像短暂漂移。
  - 阶段：失败收束。
  - 影响：若后续误重启，测试服可能尝试以失败 releaseTag 启动，掩盖 required SQL 失败状态。
  - 原因判断：发布脚本在 required SQL 完成前已写入远端 `.env IMAGE_TAG`。
  - 处理动作：冻结失败证据后，仅将 `.env IMAGE_TAG` 恢复到实际运行容器 tag `release-20260802-feedback-fix-test-r260802h-r1`，不改 release lock/migration。
  - 结果：测试服继续运行上一轮成功 release，backend health=UP、frontend HTTP 200。
  - 是否可前置检查：是。
  - 是否可自动化：是。
  - 下次如何避免：失败后必须同时核 `.env`、实际镜像、release-info、lock/migration；恢复 `.env` 只能作为失败收束并记录，不能当作发布成功。

## Blocked Result

- 本轮 releaseTag `release-20260803-intmain-head-test-r260803a-r1` 判定失败并保留证据；禁止复用该 releaseTag 继续发布。
- 下一步必须先修复 `20260513_dcc_base_schema.sql` 的 checksum 漂移与菜单主键幂等问题，补 RED/GREEN 测试和 migration policy gate，再基于新的已提交修复创建新 releaseTag 重新执行仅测试服发布。
