# 20260706-codeonly-three-env-current-head-release 执行日志

## 2026-07-06 19:02:41 +08:00 task-start

- 请求：执行 IntRuoyi code-only / 不带数据完整三环境发布闭环，使用三仓当前 `int_main` 已提交 HEAD，必须新建本次专用临时发布 worktree。
- 发布范围：code-only，不执行备份、恢复或回滚；构建必须使用 `SkipDatabaseSync` 与 `SkipMinioSync`。
- 正式/备份授权：用户确认口径 `PROD`。
- backend HEAD：`042037a42a91ac3e285bccbbccebd05f7507628d`
- frontend HEAD：`ab36017e80982b9f308b2324b4d18c6f83792424`
- maintenance HEAD：`19b121a72e0fe65c38137a154bf45e4f5391c438`

BDD: code-only 三环境发布闭环 -> Given 后端、前端、维护仓当前 `int_main` 已提交 HEAD 被检出到本轮专用干净发布 worktree When 使用 `SkipDatabaseSync` 与 `SkipMinioSync` 构建同一 releaseTag 并依次发布测试服、正式服、备份服 Then 五个 operation 必须均为 SUCCESS，三环境运行态必须全部匹配同一 releaseTag，备份服必须确认 `/mnt/intruoyi-data` 挂载与发布路径正确。

GREEN: experience-preflight -> PASS, 已读取并摘录 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`docs/release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`；本轮为 code-only 发布，不执行备份/恢复/回滚，正式服和备份服发布已获 `PROD` 授权。

## M1 前置门禁摘录

- 已提交 HEAD 是唯一发布输入；主工作区 dirty 和未跟踪文件不得进入发布包。
- 必须创建本次专用临时发布 worktree，构建和发布在干净 worktree 中执行。
- code-only 发布必须带 `SkipDatabaseSync` 与 `SkipMinioSync`，但仍需校验 migration / manifest / 发布脚本契约。
- manifest 必须记录 `publishScope=code-only` 和 `sourceRepos dirty=false`，发布包不得包含数据目录。
- 同一 releaseTag 必须完成 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`，不得拼接多轮 releaseTag 证据。
- 失败时先冻结 operation JSON、operation log、预览参数、manifest 状态、远端关键输出和失败时间点；先沉淀经验，再修复根因或重试。
- promote-prod 和 promote-backup 必须带 `ConfirmText=PROD` 与 `RequireTested`。
- promote-backup 必须显式使用 `/mnt/intruoyi-data`，并验证挂载和发布路径。
- 收尾必须恢复 `runtime-control.local.yaml` 主路径，验证运行控制台 health=UP，删除本次临时发布 worktree。


## 2026-07-06 19:04:42 +08:00 M2 临时发布 worktree 创建失败冻结

- RED: release-worktree-create -> FAIL, 维护仓在长路径 $tempRoot 检出历史 evidence 文件时触发 Filename too long，后端/前端可能已部分创建。
- 失败影响：不得继续构建或发布；必须先冻结现场、清理部分 worktree，再使用更短的本轮专用临时路径重建。
- 证据：D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\release-worktree-create-failure-long-path.json
## 2026-07-06 19:05:58 +08:00 M2 临时发布 worktree 重建

- GREEN: failed-worktree-cleanup -> PASS, 已清理失败路径 D:\ProjectPackage\Int\IntRuoyiWorktrees\20260706-codeonly-three-env-current-head-release 下本次部分后端/前端 worktree，并 prune worktree 元数据。
- GREEN: release-worktree-create-short-path -> PASS, base=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce
- maintenance=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\m commit=19b121a72e0fe65c38137a154bf45e4f5391c438 dirty=False
- backend=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\b commit=042037a42a91ac3e285bccbbccebd05f7507628d dirty=False
- frontend=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\f commit=ab36017e80982b9f308b2324b4d18c6f83792424 dirty=False
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\release-worktree-create-short-path.json

## 2026-07-06 19:06:30 +08:00 长路径失败经验沉淀

- GREEN: release-long-path-experience -> PASS, 已将维护仓发布 worktree 长路径导致 `Filename too long` 的前置门禁写入 `docs/release-build-preflight-lessons.md`，并同步更新 `docs/experience-index.md`。
## 2026-07-06 19:07:31 +08:00 project-experience-consolidation

- 请求：执行 project-experience-consolidation，将当前发布任务中可复用经验沉淀到长期经验文档。
- 经验来源：M2 临时发布 worktree 使用完整任务 ID 长路径导致维护仓 checkout Filename too long，后续以短路径 D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce 重建成功。
- 沉淀归宿：D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md、docs/release-build-preflight-lessons.md、docs/release-agent-checklist.md。
- GREEN: project-experience-consolidation -> PASS, 已优先合并到已有长期文档，未新建经验文档。

## 2026-07-06 19:07:50 +08:00 M3 临时运行控制台配置

- GREEN: runtime-control-worktree-config -> PASS, 已在临时维护仓生成本轮本地配置 $wtConfig。
- repo-root=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\b
- frontend-root=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\f
- ops-root=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\m\ops
- state-dir=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\m\runtime\runtime-control
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-worktree-config.json

## 2026-07-06 20:30:48 +08:00 M3 frontend typecheck

- RED: runtime-control-frontend-typecheck -> FAIL, exitCode=。
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-frontend-typecheck.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-frontend-typecheck.err.log

## 2026-07-06 20:31:25 +08:00 M3 frontend typecheck native

- GREEN: runtime-control-frontend-typecheck-native -> PASS, exitCode=0。
- started=2026-07-06 20:31:22 +08:00
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-frontend-typecheck-native.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-frontend-typecheck-native.err.log

## 2026-07-06 20:31:53 +08:00 M3 frontend build native

- GREEN: runtime-control-frontend-build-native -> PASS, exitCode=0, distIndexExists=True。
- started=2026-07-06 20:31:41 +08:00
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-frontend-build-native.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-frontend-build-native.err.log

## 2026-07-06 20:32:22 +08:00 M3 copy frontend static

- GREEN: runtime-control-copy-static -> PASS, frontend dist 已复制到 backend static。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-copy-static.txt

## 2026-07-06 20:33:08 +08:00 M3 Maven package native

- GREEN: runtime-control-maven-package-native -> PASS, exitCode=0, jarExists=True。
- started=2026-07-06 20:32:22 +08:00
- jar=D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\m\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-maven-package-native.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-maven-package-native.err.log

## 2026-07-06 20:41:36 +08:00 M3 临时运行控制台直接启动失败冻结

- RED: runtime-control-worktree-java-start -> FAIL, healthOk=True, processExited=False。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-worktree-java-start-verification.txt

## 2026-07-06 20:42:42 +08:00 M3 临时运行控制台最终复核

- GREEN: runtime-control-worktree-health-final -> PASS, 48181 health=UP，启动日志确认 jar 与工作目录均指向本轮临时维护仓。
- 注：前一条直接启动记录因 Win32_Process commandLine 读取为空误判为失败，本条以 health、netstat 和启动 stdout 复核更正。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-worktree-java-start-final-pass.txt

## 2026-07-06 21:37:16 +08:00 M4 build-release 首次失败冻结

- RED: build-release-command -> FAIL, releaseTag=release-20260706-2045-codeonly-three-env，发布脚本返回缺少 -TestServerHost。
- 失败影响：未生成可继续发布的 releaseTag，不得执行 publish-test；必须使用新的 releaseTag 并补齐 TestServerHost=172.30.30.58 后重新 build-release。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-failure-missing-testserverhost.txt

## 2026-07-06 21:38:20 +08:00 M4 build-release 前运行控制台恢复

- GREEN: runtime-control-restart-before-build-v3 -> PASS, 48181 health=UP。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\runtime-control-worktree-restart-before-build-v3.txt

## 2026-07-06 21:38:22 +08:00 M4 build-release v3

- RED: build-release-command-v3 -> FAIL, releaseTag=release-20260706-2145-codeonly-three-env-v3, exitCode=1，已显式传入 TestServerHost=172.30.30.58。
- preflight: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v3-preflight.json
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v3-operation.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v3-operation.err.log
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v3-command-summary.txt

## 2026-07-06 21:40:17 +08:00 M4 build-release v3 失败经验沉淀

- RED: build-release-command-v3 -> FAIL, 已冻结缺少 -BackupServerHost 的 preflight/stdout/stderr/summary。
- 失败影响：releaseTag=release-20260706-2145-codeonly-three-env-v3 判废，不得继续 publish-test；必须用新 releaseTag 并显式传入 TestServerHost/ProdServerHost/BackupServerHost。
- GREEN: release-host-parameter-experience -> PASS, 已将 build-release 目标主机参数门禁写入 docs/release-build-preflight-lessons.md 并同步 docs/experience-index.md。
## 2026-07-06 21:53:16 +08:00 M4 build-release v4

- RED: build-release-command-v4 -> FAIL, releaseTag=release-20260706-2205-codeonly-three-env-v4, exitCode=1，已显式传入 TestServerHost/ProdServerHost/BackupServerHost。
- preflight: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v4-preflight.json
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v4-operation.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v4-operation.err.log
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v4-command-summary.txt
## 2026-07-06 21:55:04 +08:00 M4 build-release v4 失败经验沉淀

- RED: build-release-command-v4 -> FAIL, releaseTag=release-20260706-2205-codeonly-three-env-v4，构建镜像已完成但脚本收尾读取 NasConfigPath 时将 YAML 当 JSON 解析失败。
- 失败影响：v4 releaseTag 判废，不得继续 publish-test；必须生成正确 NAS JSON 并用新的 releaseTag 重新 build-release。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v4-failure-json-parse-snapshot.txt
- GREEN: nas-config-json-experience -> PASS, 已将 NasConfigPath 必须使用 NAS JSON 的门禁写入 docs/release-build-preflight-lessons.md 并同步 docs/experience-index.md。
## 2026-07-06 22:06:55 +08:00 M4 build-release v5

- GREEN: build-release-command-v5 -> PASS, releaseTag=release-20260706-2235-codeonly-three-env-v5, exitCode=0，NasConfigPath 使用 NAS JSON，显式传入 TestServerHost/ProdServerHost/BackupServerHost，并使用 SkipDatabaseSync/SkipMinioSync。
- preflight: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v5-preflight.json
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v5-operation.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v5-operation.err.log
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v5-command-summary.txt
## 2026-07-06 22:07:22 +08:00 M5 build-release v5 产物校验

- GREEN: build-release-package-validation -> PASS, releaseTag=release-20260706-2235-codeonly-three-env-v5，manifest.json 存在，publishScope=code-only，backend/frontend sourceRepos commit 匹配且 dirty=false，发布包无 database/mysql/minio/files/data 等顶层数据目录。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v5-package-validation.json
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v5-package-validation-summary.txt
## 2026-07-06 22:18:24 +08:00 M6 publish-test v5

- RED: publish-test-command -> FAIL, releaseTag=release-20260706-2235-codeonly-three-env-v5, exitCode=1，目标测试服 172.30.30.58。
- preflight: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v5-preflight.json
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v5-operation.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v5-operation.err.log
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v5-command-summary.txt
## 2026-07-06 22:19:15 +08:00 M6 publish-test v5 失败冻结与经验沉淀

- RED: publish-test-command -> FAIL, releaseTag=release-20260706-2235-codeonly-three-env-v5，required SQL 20260706_mes_edhr_process_form_permission_rule.sql 在测试服执行失败：Menu id 900301 or 900302 is already used by another permission。
- 失败影响：测试服发布未完成，不能 mark-tested，不能晋级正式/备份；同一 v5 tag 当前处于测试服 FAILED 状态，需先修复 SQL 根因后重新构建新 releaseTag。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v5-required-sql-menu-id-conflict-snapshot.txt
- GREEN: required-sql-menu-id-experience -> PASS, 已将 system_menu 硬编码 ID 目标库占用门禁写入 docs/release-build-preflight-lessons.md 并同步 docs/experience-index.md。
## 2026-07-06 22:21:06 +08:00 M6 required SQL 菜单 ID 修复验证

- GREEN: required-sql-menu-id-fix-pytest -> PASS, 已将工序表单权限菜单改为 900363/900364 并同步测试断言。
- GREEN: release-migration-policy-gate -> PASS, 修复后 SQL 迁移门禁通过。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\required-sql-menu-id-fix-verification-summary.txt
## 2026-07-06 22:21:31 +08:00 M6 后端 SQL 修复提交

- RED: backend-menu-id-fix-commit -> FAIL, commitExit=1。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\backend-menu-id-fix-commit-and-main-merge-recon.txt
## 2026-07-06 22:21:58 +08:00 M6 后端 SQL 修复提交

- GREEN: backend-menu-id-fix-commit -> PASS, fixCommit=0cb706c5ded7b890f31c8d9550efa4f6657471ec，已设置 TDD_TASK_DIR。
- BLOCKER: backend-menu-id-fix-merge-main -> 合回条件未满足，详见证据。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\backend-menu-id-fix-commit-with-tdd-and-main-merge.txt
## 2026-07-06 22:22:22 +08:00 M6 后端 SQL 修复 cherry-pick 合回

- GREEN: backend-menu-id-fix-cherry-pick-main -> PASS, fixCommit=0cb706c5ded7b890f31c8d9550efa4f6657471ec 已作为单独提交合入当前后端 int_main，newHead=18537705e7eff0fce10d7306d4d076e19d9065eb。
- 合回范围：仅 sql/mysql/20260706_mes_edhr_process_form_permission_rule.sql 与 script/tests/test_mes_edhr_process_form_permission_rule_sql.py；未暂存或提交无关未跟踪文件。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\backend-menu-id-fix-cherry-pick-main.txt
## 2026-07-06 22:22:54 +08:00 M6 发布输入重定基

- RED: release-input-rebaseline-after-sql-fix -> FAIL, 后端/前端发布 worktree 未满足目标 HEAD 或 dirty=false。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\post-fix-release-input-rebaseline.txt
## 2026-07-06 22:23:30 +08:00 M6 发布输入重定基 v2

- GREEN: release-input-rebaseline-after-sql-fix-v2 -> PASS, 后端发布 worktree 已切到修复后 HEAD=18537705e7eff0fce10d7306d4d076e19d9065eb，前端发布 worktree 已切到当前 int_main HEAD=d03af99c0337e299e0d292231b673b45e20f7cae，前后端 dirty=false。
- 注：v5 releaseTag 因测试服 required SQL 失败判废，后续必须使用新的 releaseTag。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\post-fix-release-input-rebaseline-v2.txt
## 2026-07-06 22:33:45 +08:00 M7 build-release v6

- GREEN: build-release-command-v6 -> PASS, releaseTag=release-20260706-2245-codeonly-three-env-v6, exitCode=0，使用 SQL 修复后的后端 HEAD 与当前前端 HEAD，NasConfigPath 使用 NAS JSON，显式传入 TestServerHost/ProdServerHost/BackupServerHost，并使用 SkipDatabaseSync/SkipMinioSync。
- preflight: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v6-preflight.json
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v6-operation.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v6-operation.err.log
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v6-command-summary.txt
## 2026-07-06 22:34:08 +08:00 M7 build-release v6 产物校验

- GREEN: build-release-package-validation-v6 -> PASS, releaseTag=release-20260706-2245-codeonly-three-env-v6，manifest.json 存在，publishScope=code-only，backend/frontend sourceRepos commit 匹配且 dirty=false，发布包无 database/mysql/minio/files/data 等顶层数据目录。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v6-package-validation.json
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\build-release-v6-package-validation-summary.txt
## 2026-07-06 22:46:48 +08:00 M8 publish-test v6

- GREEN: publish-test-command-v6 -> PASS, releaseTag=release-20260706-2245-codeonly-three-env-v6, exitCode=0，目标测试服 172.30.30.58。
- preflight: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v6-preflight.json
- stdout: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v6-operation.out.log
- stderr: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v6-operation.err.log
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\publish-test-v6-command-summary.txt
## 2026-07-06 22:47:16 +08:00 M8 测试服 v6 独立验证

- RED: publish-test-remote-verification-v6 -> FAIL, 至少一项测试服验证未通过。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification.txt
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification-summary.txt
## 2026-07-06 22:48:25 +08:00 M8 测试服 v6 独立验证重跑 v3

- RED: publish-test-remote-verification-v6-rerun-v3 -> FAIL, 至少一项测试服验证未通过。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification-v3.txt
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification-v3-summary.txt
## 2026-07-06 22:49:21 +08:00 M8 测试服 v6 独立验证重跑 v4

- RED: publish-test-remote-verification-v6-rerun-v4 -> FAIL, 至少一项测试服验证未通过。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification-v4.txt
- docker inspect: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-docker-inspect.json
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification-v4-summary.txt
## 2026-07-06 22:49:54 +08:00 M8 测试服 v6 独立验证重跑 v5

- RED: publish-test-remote-verification-v6-rerun-v5 -> FAIL, 至少一项测试服验证未通过。
- evidence: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification-v5.txt
- summary: D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260706-codeonly-three-env-current-head-release\evidence\test-server-v6-verification-v5-summary.txt

- BLOCKER: mark-tested-v6-argument-tokenization -> FAIL，2026-07-06 22:54:48 +08:00，mark-tested 子进程启动失败，Start-Process -ArgumentList 将带空格的 TestConclusion 拆词，三环境 被误绑定到 Component 并触发 ValidateSet。失败证据已冻结：evidence/mark-tested-v6-command-summary.txt、evidence/mark-tested-v6-operation.out.log、evidence/mark-tested-v6-operation.err.log。
- GREEN: preflight-lesson-mark-tested-argument-tokenization -> PASS，2026-07-06 22:54:48 +08:00，已沉淀到 docs/release-build-preflight-lessons.md 并同步 docs/experience-index.md；下一步改用无歧义参数包装方式重试同一 releaseTag 的 mark-tested。

- GREEN: mark-tested-v6 -> PASS，2026-07-06 22:55:27 +08:00，同一 releaseTag release-20260706-2245-codeonly-three-env-v6 已通过 publish-int-ruoyi.ps1 -Mode mark-tested 标记测试通过；NAS 写入 tested.json，并记录 rollback-compatibility.json status=BLOCKED。证据：evidence/mark-tested-v6-retry-command-summary.txt、evidence/mark-tested-v6-retry-operation.out.log、evidence/mark-tested-v6-retry-operation.err.log。

- GREEN: promote-prod-v6 -> PASS，2026-07-06 23:26:01 +08:00，同一 releaseTag release-20260706-2245-codeonly-three-env-v6 已执行正式服 promote-prod，参数包含 ConfirmText=PROD、RequireTested、ProdDryRunEvidencePath，operation op-2026-07-06T145929632013700Z-6235332a-37e7-46fb-9802-10b30080ac88 最终 SUCCESS。正式服 172.30.30.57 验证通过：.env IMAGE_TAG、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200、release lock=APPLIED。证据：evidence/promote-prod-v6-operation-state.json、evidence/promote-prod-v6-command-summary-corrected.txt、evidence/prod-server-v6-verification-summary.txt、evidence/prod-server-v6-verification.txt。

## 2026-07-06 23:48:10 +08:00 M10 备份服 v6 验证与收尾

- GREEN: promote-backup-v6 -> PASS，同一 releaseTag release-20260706-2245-codeonly-three-env-v6 已执行备份服 promote-backup，参数包含 ConfirmText=PROD、RequireTested、ServerHost=172.30.30.59、RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases、RemoteDataRoot=/mnt/intruoyi-data/runtime-data、RemoteDataDiskMount=/mnt/intruoyi-data、RemoteDataDiskDevice=/dev/mapper/cl-home，operation op-2026-07-06T152642480550500Z-f8bfc329-aab8-4400-b723-7beada4fa2e3 最终 SUCCESS。证据：evidence/promote-backup-v6-command-summary.txt、evidence/promote-backup-v6-operation-state-verified.json、evidence/promote-backup-v6-operation.log。
- GREEN: backup-server-v6-verification -> PASS，备份服 172.30.30.59 验证 .env IMAGE_TAG、backend/frontend 实际镜像 tag、backend health=UP、frontend HTTP 200、PDF worker HTTP 200、release lock=APPLIED，且 /mnt/intruoyi-data 已挂载，/mnt/intruoyi-data/intruoyi-releases/release-20260706-2245-codeonly-three-env-v6 与 /mnt/intruoyi-data/runtime-data 路径存在。证据：evidence/backup-server-v6-verification-summary.txt、evidence/backup-server-v6-verification.txt。
- GREEN: runtime-control-main-restore -> PASS，本机运行控制台已恢复主工作区 jar D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar，http://127.0.0.1:48181/actuator/health=UP。证据：evidence/runtime-restore-failure-inspection.txt、evidence/worktree-removal-final-force-residual.txt。
- GREEN: release-worktree-cleanup -> PASS，本次临时发布目录 D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce 已删除；后端、前端、维护仓 worktree list 已不包含本次 260706ce worktree。证据：evidence/worktree-removal-final-force-residual.txt。
- GREEN: task-closeout-cleanup-preview -> PASS，已按收尾基线执行 cleanup preview；由于 preview 将删除本次发布冻结证据，而本任务要求保留真实失败/成功证据，未执行 apply 删除 evidence。证据：evidence/task-closeout-cleanup-preview.txt。
