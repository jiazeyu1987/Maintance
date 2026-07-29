# 当前 HEAD 仅测试服发布执行日志

## BDD Scenarios

BDD: 当前 HEAD 构建输入冻结 -> Given 当前分支存在未提交改动或后续提交继续产生, When 本次仅测试服发布开始构建, Then 构建目录必须为本次专用干净临时 worktree 且 `HEAD` 等于发布起点目标提交，未提交改动不得进入产物。

BDD: 仅测试服发布边界 -> Given 发布包已由目标提交构建并通过 manifest / 版本 / 变更说明校验, When 执行发布动作, Then 只能执行测试服发布并验证测试服运行态，不得执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

BDD: 测试服运行态验收 -> Given 测试服发布脚本返回成功, When 验收真实运行态, Then 必须同时确认远端 `.env IMAGE_TAG`、backend/frontend 镜像 tag、容器状态、backend health、frontend HTTP 200、前端页面、运行控制台版本号和变更说明。

## Execution Evidence

- BOOTSTRAP: previous-task-status -> PASS，最近任务 `20260724-main-program-path-description` 的 `## Current Status` 为 `completed`。
- BOOTSTRAP: initial-maintenance-git-status -> branch `int_main`, HEAD `4a77055f4a90209bae9bbba4fc2b75c03eb9aa88`, 工作区存在脏改动；本次必须创建干净临时发布 worktree。
- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`docs/release-agent-checklist.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-memory.md`；本任务只允许测试服发布，禁止 `mark-tested`、`promote-prod`、`promote-backup`，发布输入必须来自冻结 clean release worktree 的已提交 HEAD。
- GREEN: release-start-freeze -> PASS，维护仓 `int_main` HEAD `4a77055f4a90209bae9bbba4fc2b75c03eb9aa88`，主程序仓 `int_main` HEAD `3a556a26750464e126d2373ecf5ab80df19ce3b9`；两个主工作区均存在未提交改动，因此创建本轮专用 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\m` 与 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\app`。
- GREEN: clean-release-worktree -> PASS，维护 worktree HEAD=`4a77055f4a90209bae9bbba4fc2b75c03eb9aa88`、主程序 worktree HEAD=`3a556a26750464e126d2373ecf5ab80df19ce3b9`，两者 `git status --porcelain --ignored=no` 均为空；构建目录固定为 `...\app\IntRuoyiBackend`、`...\app\IntRuoyiFronted`、`...\m`。
- GREEN: migration-policy-gate -> PASS，`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql --output ...\evidence\migration-policy-gate-r260729a.json`，结果 `status=passed`、`migrationCount=390`。
- GREEN: frontend-build-test-precheck -> PASS，`pnpm install --frozen-lockfile` 与 `pnpm build:test` 在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\app\IntRuoyiFronted` 通过，输出 `dist-test`，构建后 git 状态仍干净。
- GREEN: backend-mes-compile-gate -> PASS，`mvn.cmd -pl yudao-module-mes -am "-DskipTests" compile` 在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\app\IntRuoyiBackend` 通过。
- GREEN: maintenance-console-build -> PASS，`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build.ps1` 在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\m` 通过；维护前端 install/typecheck/build 与后端 Maven tests/package 成功，jar 为 `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`。
- GREEN: runtime-control-start -> PASS，运行控制台从临时维护 worktree jar 启动，PID `32032`，health endpoint 返回 `{"status":"UP"}`；命令行覆盖 repo-root/frontend-root/ops-root/state-dir 到本轮 worktree/state 路径，prod/backup access-enabled=false，test access-enabled=true。
- INFO: releaseTag-selected -> `release-20260729-intmain-head-test-r260729a-r1`；后续 build-release、publish-test、manifest、运行态和页面验证必须全部使用该同一 releaseTag。
- GREEN: build-release-preview -> PASS，preview JSON `evidence/build-release-preview-r260729a.json` 确认 `action=build-release`、`environment=release`、script 位于 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\m\ops\deploy\publish-int-ruoyi.ps1`，参数包含 `-Mode build-release`、`-ReleaseTag release-20260729-intmain-head-test-r260729a-r1`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、`-BackendRepoRoot ...\r260729a\app\IntRuoyiBackend`、`-FrontendRepoRoot ...\r260729a\app\IntRuoyiFronted`、`-TestServerHost 172.30.30.58`；未出现 `deploy-release`、`mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: build-release -> PASS，operation `op-2026-07-29T021940057540400Z-d38c9e73-44c2-4e94-bed1-997d5502ee2a` 返回 `SUCCESS`；本地包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260729-intmain-head-test-r260729a-r1` 存在，包含 `manifest.json`、`release-manifest.json`、`intruoyi-images_release-20260729-intmain-head-test-r260729a-r1.tar`、`required-sql/`、`resources/`、`runtime-env/`、`smoke/`；日志尾部证据见 `evidence/build-release-log-tail-r260729a.txt`。
- GREEN: manifest-validator -> PASS，`validate-release-manifest.ps1 -PackagePath E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260729-intmain-head-test-r260729a-r1 -Mode report-only -OutputPath evidence\manifest-validation-r260729a.json` 返回 `MANIFEST_VALIDATION_PASSED`，package declarations、sha256、forbidden target/secret scan 均通过。
- GREEN: manifest-source-version-change-notes -> PASS，`evidence/manifest-summary-r260729a.json` 确认 Manifest v1 `publishScope=code-only`，legacy manifest `component=intruoyi`、`gitCommit=3a556a26750464e126d2373ecf5ab80df19ce3b9`，Manifest v1 `sourceRepos` 中 `backend` 和 `admin-frontend` commit 均等于 `3a556a26750464e126d2373ecf5ab80df19ce3b9` 且 `dirty=false`，`changeSet.summary` 和 `items` 包含本轮 releaseTag 与 `组件范围：intruoyi`。
- GREEN: test-server-prepublish-collision-check -> PASS，测试服 `172.30.30.58` 无 active `publish-int-ruoyi` 进程；`infra_release_operation_lock` schema 已按真实字段查询，目标 releaseTag 无锁记录且无 `RUNNING/LOCKED`；当前 `.env IMAGE_TAG=release-20260728-codeonly-noonlyoffice-test-r2`。
- GREEN: publish-test-preview -> PASS，preview JSON `evidence/publish-test-preview-r260729a.json` 确认 `action=publish-test`、`environment=test`、`-Mode deploy-release`、`-Environment test`、`-ReleaseTag release-20260729-intmain-head-test-r260729a-r1`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`；无 `-ConfirmText`、无 `-RequireTested`、无 `mark-tested`/`promote-prod`/`promote-backup`。
- RED: publish-test -> FAIL，operation `op-2026-07-29T024258673743700Z-1774cd02-0579-420e-86eb-bcd0ed97475a` 状态 `FAILED`，summary `命令退出码非 0: 1`；失败 SQL 为 `required-sql/20260726_dcc_codex_test_items_seed.sql`，错误为 `ERROR 1267 (HY000) at line 291: Illegal mix of collations (utf8mb4_0900_ai_ci,IMPLICIT) and (utf8mb4_unicode_ci,IMPLICIT) for operation '='`。
- GREEN: failure-state-freeze -> PASS，测试服冻结证据 `evidence/test-server-failure-freeze-r260729a.out`：`.env IMAGE_TAG=release-20260729-intmain-head-test-r260729a-r1`，但 backend/frontend 容器实际仍为 `release-20260728-codeonly-noonlyoffice-test-r2` 且 running，backend health=`UP`、frontend HTTP=`200`；release lock `test-release-20260729-intmain-head-test-r260729a-r1` 为 `FAILED`，migration counts `APPLIED=10`、`SKIPPED_ALREADY_APPLIED=341`、`FAILED=1`。
- GREEN: failure-collation-evidence -> PASS，测试服 `system_codex_test_case` / `system_codex_test_checkpoint` 相关文本列为 `utf8mb4_0900_ai_ci`，发布 SQL `20260726_dcc_codex_test_items_seed.sql` 的临时表声明为 `utf8mb4_unicode_ci`，在 `CALL ensure_dcc_codex_test_items_seed()` 内字符串比较触发 collation mismatch。
- GREEN: forbidden-operation-check -> PASS，`evidence/operations-for-releaseTag-r260729a.json` 确认本轮 releaseTag 只有 `build-release=SUCCESS` 与 `publish-test=FAILED` 两个 operation，未执行 `mark-release-tested`、`promote-prod`、`promote-backup`。
- GREEN: blocked-worktree-state -> PASS，失败后维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\m` 与主程序 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729a\app` 均为 detached HEAD 且 `git status --porcelain --ignored=no` 为空；按项目规则，因发布验证未通过，本轮 worktree/state 暂不删除。
- GREEN: evidence-secret-scan -> PASS，`doc/tasks/20260729-head-test-only-release/evidence` 未命中已知密码、HMAC、JWT、base64 key、`-p123456`、未脱敏 `password=` 等模式；原始 publish operation log 包含敏感 MySQL `-p<redacted>` 类参数，未复制到任务证据，仅保留 sanitized tail。
- GREEN: experience-consolidation -> PASS，已将本轮 SQL collation 阻塞与 publish-test 失败后 `.env` / 实际镜像漂移沉淀到 `docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md`，并更新 `docs/experience-index.md` 关键词路由；因测试服发布未成功，完整 closeout 经验沉淀仍随任务保持 blocked。
- GREEN: final-evidence-gate -> PASS，经验索引关键词可定位，任务证据 refined secret scan PASS，相关 Markdown `git diff --check` 无错误；维护与主程序 release worktree 均保持干净并按阻塞规则保留。
- RED: r260729b-build-release -> FAIL，`release-20260729-sqlfix-test-r260729b-r1` 在 clean app release worktree 首次 build-release 时失败，前端缺少 `node_modules`，`cross-env` 不可用；该 releaseTag 未进入 publish-test。
- RED: r260729b-publish-test -> FAIL，`release-20260729-sqlfix-test-r260729b-r2` 的 `publish-test` operation `op-2026-07-29T044320236880700Z-fb6c43d9-09d3-435d-bf81-72f84370cdb4` 失败于 `20260726_system_codex_smart_scheduling_test_items.sql`，MySQL `ERROR 1267 Illegal mix of collations (utf8mb4_general_ci,IMPLICIT) and (utf8mb4_0900_ai_ci,IMPLICIT)`。
- GREEN: r260729c-freeze -> PASS，修复 smart scheduling seed collation 后创建 clean worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729c\m` 与 `D:\IntRuoyiWorktree\r260729c-release-app`，Manifest validator PASS，sourceRepos commit `8304bd8ac6baf4d7c2b0bc810847831a4febfefd` 且 dirty=false。
- RED: r260729c-publish-test -> FAIL，`release-20260729-sqlfix-test-r260729c-r1` 的 `publish-test` operation `op-2026-07-29T094257340883100Z-4739d06c-ef4d-4c24-956b-e2d82d5294e3` 失败于 `20260726_system_codex_smart_scheduling_test_items.sql`，MySQL `ERROR 1137 Can't reopen table: 'seed'`。
- GREEN: r260729d-freeze -> PASS，修复临时表重开后从本地已提交 commit `919122b6f72e2f0cf7e4cdb7f2ee913294af0473` 创建 clean app release worktree `D:\IntRuoyiWorktree\r260729d-release-app`，维护 release worktree 为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729d\m`，两者发布前后 `git status --porcelain --ignored=no` 为空。
- GREEN: r260729d-build-release -> PASS，`build-release` operation `op-2026-07-29T101921985772400Z-05210b94-fafa-43d9-990e-dca0ea15c7e1` 为 `SUCCESS`；发布包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260729-sqlfix-test-r260729d-r1` 存在，Manifest validator `MANIFEST_VALIDATION_PASSED`，sourceRepos backend/admin-frontend commit 均为 `919122b6f72e2f0cf7e4cdb7f2ee913294af0473` 且 dirty=false。
- GREEN: r260729d-publish-test -> PASS，`publish-test` preview 字段确认 `action=publish-test`、`environment=test`、`-Mode deploy-release`、`-ServerHost 172.30.30.58`、`-RemoteAppDir /opt/intruoyi/runtime`，无 `mark-tested` / `promote-prod` / `promote-backup`；operation `op-2026-07-29T103744548087400Z-d86c6a40-3508-43f9-933c-7c63af704bb3` 为 `SUCCESS`。
- GREEN: test-runtime-verification-r260729d -> PASS，测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 均为 `release-20260729-sqlfix-test-r260729d-r1`，容器 running，backend health `UP`，backend HTTP `200`，frontend HTTP `200`，PDF worker HTTP `200 application/javascript`，release lock `APPLIED`，migration counts `APPLIED=7`、`SKIPPED_ALREADY_APPLIED=353`、`FAILED=0`。
- GREEN: playwright-runtime-control-version -> PASS，Playwright `--channel chrome` 打开测试服前端登录页；运行控制台页面显示测试服 releaseTag `release-20260729-sqlfix-test-r260729d-r1`，版本变更说明对话框显示 `发布包：release-20260729-sqlfix-test-r260729d-r1` 与 `组件范围：intruoyi`。
- GREEN: runtime-control-release-status -> PASS，`/admin-api/infra/runtime-control/release-status` 的 `testCurrentReleaseNotes` 为 `release-20260729-sqlfix-test-r260729d-r1`，sourceRepos commit 均为 `919122b6f72e2f0cf7e4cdb7f2ee913294af0473` 且 dirty=false，blockedReasons 为空。
- GREEN: forbidden-operation-check-r260729d -> PASS，本 releaseTag 仅存在 `build-release=SUCCESS` 与 `publish-test=SUCCESS`，未执行 `mark-release-tested`、`promote-prod`、`promote-backup`。
- GREEN: runtime-control-restore -> PASS，停止引用 r260729d worktree 的维护控制台进程后，从主维护路径 `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 重启 48181，PID `48676`，health=`UP`，命令行不再引用 r260729d。
- GREEN: project-experience-consolidation -> PASS，已将 r260729d 成功和本轮新增问题合并进已有经验文档：`docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md`、`docs/powershell-preflight-lessons.md`、`docs/experience-index.md`。

## Problem Records

1. 现象：执行 `pnpm approve-builds --all` 返回 `ERROR Unknown option: 'all'`。
   阶段：前端构建前门禁。
   影响：不能按旧经验命令一次性 approve；若误判为依赖不可用会阻断发布。
   原因判断：本机 pnpm `10.22.0` 的 `approve-builds` 帮助仅支持 `-g/--global`，无 `--all` 参数。
   处理动作：读取当前 help 与 `pnpm-workspace.yaml`，确认 `allowBuilds` 已声明后改用 `pnpm install --frozen-lockfile` + `pnpm build:test` 作为真实门禁。
   结果：前端构建通过，未修改发布 worktree 已提交内容。
   是否可前置检查：是，发布前运行 `pnpm --version` 与 `pnpm help approve-builds`，禁止硬编码 `--all`。
   是否可自动化：是，在发布前置脚本中按 pnpm 版本和 help 输出选择检查方式。
   下次如何避免：将 `approve-builds --all` 从强制命令降级为版本感知检查项，并优先确认 `pnpm-workspace.yaml` / package approval 配置。

2. 现象：`pnpm ignored-builds` 在前端构建通过后仍报告 `core-js`、`esbuild`、`@parcel/watcher`、`vue-demi`、`@swc/core` 等 ignored scripts。
   阶段：前端构建后检查。
   影响：可能掩盖依赖构建脚本审批漂移；本轮 `pnpm build:test` 已通过，因此未作为发布阻塞。
   原因判断：当前仓库使用 `pnpm-workspace.yaml allowBuilds`，pnpm 提示更偏向 `pnpm.onlyBuiltDependencies` 配置；审批模型与版本存在差异。
   处理动作：记录 warning，继续以后续真实 build/test 退出码与产物为准。
   结果：前端 build 成功且 git 状态干净。
   是否可前置检查：是，发布前运行 `pnpm ignored-builds` 并将非空结果记录为 warning 或按项目配置升级处理。
   是否可自动化：是，可将 ignored-builds 输出纳入 release preflight report。
   下次如何避免：在非发布任务中统一 pnpm build script approval 配置，避免发布时临时改配置。

3. 现象：维护控制台构建后出现 untracked `runtime/runtime-control-original-governance-parity-test/`。
   阶段：维护控制台测试构建。
   影响：若不处理，release worktree 不再干净，不能证明构建来源只来自 HEAD。
   原因判断：维护控制台 Maven 测试在仓库内生成运行态测试目录。
   处理动作：先 `git clean -nd -- runtime/runtime-control-original-governance-parity-test` 预览，只确认本次测试产物后执行 `git clean -fd -- runtime/runtime-control-original-governance-parity-test`。
   结果：维护 release worktree 恢复干净。
   是否可前置检查：是，维护构建后固定执行 `git status --porcelain --ignored=no`。
   是否可自动化：是，测试应将临时 runtime 输出迁移到 build/temp 或由构建脚本自动清理已知测试产物。
   下次如何避免：维护仓测试输出目录不要落在仓库根 `runtime/`，或在 release build 后做白名单化 git clean preview/apply。

4. 现象：PowerShell 直接 `Remove-Item -Recurse` 清理已确认 untracked 测试目录被本地安全规则拒绝。
   阶段：worktree 清理。
   影响：清理动作需要改用可审计命令，避免误删范围扩大。
   原因判断：Windows 安全规则禁止未验证路径的递归删除。
   处理动作：改用 git 归属命令 `git clean -nd` 预览再 `git clean -fd` 清理单一路径。
   结果：目标测试目录清理成功，worktree 干净。
   是否可前置检查：是，清理前固定记录 git clean dry-run 输出。
   是否可自动化：是，封装为只接受相对路径且先 dry-run 的清理步骤。
   下次如何避免：release worktree 内未跟踪测试产物优先使用 `git clean` 的 preview/apply 闭环处理。

5. 现象：运行控制台 `release-status` endpoint 在 20 秒内超时。
   阶段：运行控制台启动后检查。
   影响：不能把全量 release-status 作为本轮 build 前候选包唯一证明；后续必须直接读取本轮 releaseTag manifest。
   原因判断：当前 release-status 会扫描较多历史候选包，已知可能耗时较长。
   处理动作：保留 health、overview 和 operation API 作为控制台可用性证明；build 后改为直接校验目标 manifest 路径。
   结果：未阻断 build-release 前置；后续 manifest 验收必须 fail fast。
   是否可前置检查：是，release-status 超时需提前记录并切换到目标 manifest 直读校验。
   是否可自动化：是，提供按 releaseTag 查询/直读 manifest 的轻量校验命令。
   下次如何避免：控制台 release-status 增加分页/limit 或发布流程改用目标 releaseTag 查询接口。

6. 现象：运行控制台 business health 返回整体 `NO_GO`，多个业务采集项显示未配置。
   阶段：运行控制台启动后检查。
   影响：业务健康采集不能替代本次发布运行态验收；若误用会阻塞无关发布。
   原因判断：独立业务健康采集器尚未配置登录、ERP、MES、file、job 等真实探针。
   处理动作：记录为独立运维检查项，不作为本次代码发布门禁；仍执行远端镜像、health、HTTP、页面和 release-info 验收。
   结果：发布流程继续，真实运行态验证不降级。
   是否可前置检查：是，区分控制台自身 health、业务 health 和发布验收。
   是否可自动化：是，在报告中拆分显示，不让未配置业务探针覆盖发布运行态结果。
   下次如何避免：发布门禁只采信已配置且与本次发布目标直接相关的探针。

7. 现象：首次 build-release preview 校验脚本误按旧参数名查找 `-BackendRoot` / `-FrontendRoot`，实际 preview 使用 `-BackendRepoRoot` / `-FrontendRepoRoot`，导致本地断言失败。
   阶段：build-release preview。
   影响：没有创建发布 operation，也没有写服务器；但如果不复核 preview 原文，可能误判有效 preview 为失败。
   原因判断：维护控制台动作契约已演进，字段名与旧经验不一致。
   处理动作：读取 preview 原始 JSON 与 `RuntimeControlOperationAction`，修正校验为真实参数名。
   结果：preview 结构化校验 PASS。
   是否可前置检查：是，preview 校验应从当前代码枚举/DTO 生成或同步更新。
   是否可自动化：是，将 build-release/publish-test preview 字段检查固化为脚本。
   下次如何避免：不要手写旧字段名；每次发布前按当前 HEAD 的 action enum 验证参数契约。

8. 现象：build-release 日志中 Docker backend image build 报 `InvalidDefaultArgInFrom` warning。
   阶段：Docker 镜像构建。
   影响：Docker build 成功，镜像 tag 与 releaseTag 正确；warning 表示 Dockerfile 默认 ARG 在未传入时可能为空，不阻塞本轮。
   原因判断：Dockerfile 依赖外部传入 `BACKEND_RUNTIME_BASE_IMAGE`，默认值为空触发 Docker lint warning。
   处理动作：确认实际 build 已传入 backend runtime base image、导出镜像成功、manifest validator PASS。
   结果：本轮继续；记录为后续可清理的构建契约 warning。
   是否可前置检查：是，构建前可用 Dockerfile lint 检查默认 ARG。
   是否可自动化：是，将 Docker build warning 摘要写入 release report。
   下次如何避免：在非发布修复中给 ARG 设置合法默认值或调整 Dockerfile lint 策略。

9. 现象：build-release 日志中 NAS share 中文名显示为 `IT����`，Maven warning 也出现中文乱码。
   阶段：build-release 日志采集。
   影响：不影响 operation 成功、manifest 或包上传；但不能把乱码日志作为唯一变更说明/路径证据。
   原因判断：PowerShell/外部 native 输出编码混杂，日志采集链路未完全 UTF-8 化。
   处理动作：以结构化 JSON、manifest validator、manifest summary 和 API 状态作为验收依据；日志只作为辅助。
   结果：manifest 与包校验通过。
   是否可前置检查：是，涉及中文 NAS 路径时应单独校验结构化路径和 operation exit/status。
   是否可自动化：是，日志采集可增加 UTF-8 转码/乱码检测。
   下次如何避免：中文路径验收不依赖 native raw log，固定读取 manifest/API 字段。

10. 现象：首次测试服预发布检查的进程过滤过宽，打印 Java 运行命令行，包含敏感启动参数；同时锁表查询误用不存在列 `operation`，导致 SQL 失败。
    阶段：测试服 publish-test 前碰撞检查。
    影响：该次检查失败，且生成的原始证据不能提交；若不处理会违反凭据日志规则。
    原因判断：进程正则匹配了 `runtime-control` 参数，锁表字段未先按真实库 schema 确认。
    处理动作：立即脱敏覆盖 stdout/stderr 证据并运行 secret pattern 扫描 PASS；随后 `SHOW COLUMNS FROM infra_release_operation_lock`，按真实字段 `target_environment/operation_id/release_tag/status/started_at/finished_at/update_time` 重跑检查。
    结果：第二次预发布检查 PASS，无 active publish 进程、无 active release lock。
    是否可前置检查：是，高风险远端命令前必须先限定输出字段并 `DESCRIBE/SHOW COLUMNS`。
    是否可自动化：是，发布前碰撞检查脚本应输出最小非敏感字段，并内置 schema probe。
    下次如何避免：禁止 `ps args` 广泛输出；锁表查询先查 schema，再生成白名单字段查询。

11. 现象：`publish-test` 在 required SQL `20260726_dcc_codex_test_items_seed.sql` 执行阶段失败，MySQL 报 `ERROR 1267 Illegal mix of collations ... for operation '='`。
    阶段：测试服 required SQL 应用。
    影响：测试服发布失败，目标 releaseTag 未完成镜像切换和运行态验收；本任务不能判定测试发布成功。
    原因判断：发布 SQL 中临时 seed 表使用 `utf8mb4_unicode_ci`，测试服真实 `system_codex_test_case` / `system_codex_test_checkpoint` 文本列为 `utf8mb4_0900_ai_ci`，在过程内 `name` 等字符串比较时触发 collation mismatch。
    处理动作：冻结 operation、sanitized log、lock/migration 状态、真实运行态和 live column collation；按 fail-fast 终止本轮，不执行 mark/prod/backup，不用临时 SQL 绕过。
    结果：release lock 为 `FAILED`，migration counts `APPLIED=10`、`SKIPPED_ALREADY_APPLIED=341`、`FAILED=1`，失败 migration 为 `20260726_dcc_codex_test_items_seed`。
    是否可前置检查：是，发布前应以真实测试库 collation 检查 required SQL 临时表/字面量/目标表比较。
    是否可自动化：是，migration policy gate 可增加 MySQL 8 `utf8mb4_0900_ai_ci` 目标列与 `utf8mb4_unicode_ci` 临时表比较扫描，或在测试库 dry-run 中提前执行。
    下次如何避免：修复并提交 SQL，给比较双方显式统一 `COLLATE` 或让临时表字段继承目标列 collation；修复后必须重新 build-release 生成新的 releaseTag。

12. 现象：`publish-test` 失败后测试服 `.env IMAGE_TAG` 已变更为本轮 releaseTag，但 backend/frontend 实际容器仍运行旧镜像 tag `release-20260728-codeonly-noonlyoffice-test-r2`。
    阶段：publish-test 失败后状态冻结。
    影响：测试服当前服务仍可用且 health/HTTP 正常，但配置文件与实际容器不一致；若后续直接重启 compose，可能尝试使用未完成发布的目标 tag。
    原因判断：发布脚本在 required SQL 完整成功前已写入 `.env IMAGE_TAG`，失败清理只释放 release lock，未恢复 `.env`。
    处理动作：冻结 `.env`、容器实际镜像、health、HTTP、lock 和 migration 状态；未擅自改回 `.env`，等待用户批准正式修复/恢复动作。
    结果：任务阻塞，不宣称测试发布完成。
    是否可前置检查：是，publish-test 脚本应在失败路径校验/回滚 `.env IMAGE_TAG`，最终验收必须同时查 `.env` 与实际镜像。
    是否可自动化：是，发布失败清理钩子可恢复旧 `.env` 或记录明确 drift blocker；运行态验收脚本应自动报 drift。
    下次如何避免：调整发布顺序或失败补偿，让 `.env` 更新与镜像切换成为原子阶段，失败时自动回写旧 tag。

13. 现象：publish operation 原始日志打印 `docker exec ... mysql -uroot -p<redacted>` 类命令行，包含 MySQL 密码参数。
    阶段：publish-test 日志采集。
    影响：原始 operation log 不能提交；若任务证据直接复制 raw log 会违反凭据日志规则。
    原因判断：发布脚本 `Run:` 日志记录了完整 native 命令行，未对 MySQL `-p` 参数做脱敏。
    处理动作：后续只保存 `publish-test-log-tail-sanitized-r260729a.txt`，并对 evidence 目录执行 secret pattern scan PASS；不提交原始 operation log。
    结果：任务证据中未保留已知明文密码模式。
    是否可前置检查：是，发布脚本日志输出前应统一走参数脱敏器。
    是否可自动化：是，operation log 写入和任务 closeout 前增加 secret scan gate。
    下次如何避免：将 MySQL 密码改为 stdin/env/config 文件承载，并在 `Run:` 记录中屏蔽 `-p<redacted>` 类参数。

14. 现象：远端 SSH/MySQL 查询多次输出 `mysql: [Warning] Using a password on the command line interface can be insecure.` 和 `close - IO is still pending on closed socket`。
    阶段：远端状态冻结与 DB 查询。
    影响：不影响查询退出码和结构化结果，但会污染 stderr，不能将 stderr warning 直接判定为失败或成功。
    原因判断：MySQL CLI 使用 `-p"$MYSQL_ROOT_PASSWORD"` 承载密码，SSH 关闭 stdin 后 OpenSSH/Windows 侧有 pending IO 噪声。
    处理动作：以进程 exit code、stdout 分段标记和后续 secret scan 判定；warning 作为流程问题记录。
    结果：远端冻结命令 exit code 0，证据可用。
    是否可前置检查：是，远端查询工具应使用 `--defaults-extra-file` 或容器内受控脚本，减少 password warning。
    是否可自动化：是，封装发布验收查询脚本，统一处理 stdout/stderr 和退出码。
    下次如何避免：避免在验证命令中直接使用 MySQL `-p` 参数，或将 warning 纳入已知非阻塞噪声白名单并单独扫描秘密。

15. 现象：第二轮 `build-release` 首次尝试 `release-20260729-sqlfix-test-r260729b-r1` 在前端构建阶段失败，日志显示新 release worktree 缺少 `node_modules`，`cross-env` 命令不可用。
    阶段：第二轮 build-release。
    影响：该 releaseTag 未形成可发布包，不能继续发布或复用；必须使用新的 releaseTag 重建，防止失败证据与成功产物混淆。
    原因判断：clean app release worktree 只包含 Git 已提交文件，前端依赖目录被 Git 忽略且未在 build-release 前预热。
    处理动作：保留失败 operation 和脱敏日志证据；在同一 clean HEAD worktree 内执行 `pnpm install --frozen-lockfile` 与 `pnpm build:test`，通过后改用 `release-20260729-sqlfix-test-r260729b-r2` 重新 build-release。
    结果：已执行 `pnpm install --frozen-lockfile` 与 `pnpm build:test` 预热，改用 `release-20260729-sqlfix-test-r260729b-r2` 重建；`r260729b-r1` 未进入 publish-test。
    是否可前置检查：是，所有新建前端发布 worktree 在 build-release 前必须检查 `node_modules` 和 `pnpm build:test`。
    是否可自动化：是，build-release preview/action 前可增加 frontend dependency preflight，缺少依赖时 fail fast。
    下次如何避免：创建 clean release worktree 后固定执行 `pnpm install --frozen-lockfile`，并把 `pnpm build:test` 作为构建前必查项。

16. 现象：`release-20260729-sqlfix-test-r260729b-r2` 在 `20260726_system_codex_smart_scheduling_test_items.sql` 执行阶段失败，MySQL 报 `ERROR 1267 Illegal mix of collations (utf8mb4_general_ci,IMPLICIT) and (utf8mb4_0900_ai_ci,IMPLICIT)`。
    阶段：第二轮 publish-test required SQL。
    影响：测试服发布失败，不能判定运行态成功；必须修复后重新 build-release 新 releaseTag。
    原因判断：smart scheduling Codex test seed 临时表字符串列与真实目标表 `system_codex_test_*` 字符串列 collation 不一致。
    处理动作：冻结 operation、失败日志、远端状态；补 SQL 静态测试并修复 collation。
    结果：修复后创建 r260729c clean release worktree 并重建。
    是否可前置检查：是，发布前扫描新增/修改 seed SQL 的临时表 collation 与目标列比较。
    是否可自动化：是，migration policy gate 或 SQL 静态测试可增加 `system_codex_test_*` collation 检查。
    下次如何避免：所有 Codex seed SQL 临时字符串列按目标列显式 `COLLATE`，并用真实目标库 schema 只读探针校验。

17. 现象：`release-20260729-sqlfix-test-r260729c-r1` 在同一 smart scheduling seed SQL 中失败，MySQL 报 `ERROR 1137 Can't reopen table: 'seed'`。
    阶段：第三轮 publish-test required SQL。
    影响：r260729c 容器切换未能成为成功发布，必须继续修复并重新出新 releaseTag。
    原因判断：SQL 在同一校验表达式中重复读取临时 seed 表，触发 MySQL 临时表重开限制。
    处理动作：冻结失败证据；补 RED 测试；将 checkpoint expected/actual count 拆为独立 `SELECT COUNT(*) INTO` 变量。
    结果：本地提交 `919122b6f72e2f0cf7e4cdb7f2ee913294af0473` 后创建 r260729d clean release worktree 并成功发布测试服。
    是否可前置检查：是，静态扫描同一语句或嵌套子查询中重复引用临时 seed 表。
    是否可自动化：是，SQL 测试可针对 `tmp_*_seed` / `seed` 重复读取模式建规则。
    下次如何避免：临时 seed 表的校验计数使用独立变量或拆分语句，不在一个 SQL 表达式中多次读取同一临时表。

18. 现象：修复分支 `codex/20260729-test-release-sql-collation` 推送 GitHub 多次返回 `Recv failure: Connection was reset`。
    阶段：修复提交发布前同步。
    影响：远端分支未更新到 `919122b6`；但本次构建输入只要求本地已提交代码，r260729d 从本地提交创建 clean release worktree，未把未提交改动带入构建。
    原因判断：GitHub HTTPS 连接在传输阶段被重置。
    处理动作：记录失败；不把推送作为构建输入前置；修复 worktree 保留并在其任务文档标记 push 阻塞。
    结果：测试服发布成功；修复分支仍需后续网络恢复后推送。
    是否可前置检查：部分可，推送前可检查网络和 remote，但连接 reset 仍可能运行中出现。
    是否可自动化：是，推送失败时自动记录远端 HEAD、本地 HEAD 和错误文本。
    下次如何避免：发布构建来源以本地 clean commit 为准，同时把远端同步作为独立非发布门禁记录，不误写为已推送。

19. 现象：运行控制台 operation log API 返回原始 MySQL 命令行，任务第一次保存 r260729d 日志时出现未脱敏 `mysql -uroot -p...`；早期脱敏正则还误伤 `ruoyi-vue-pro`。
    阶段：publish-test 日志采集。
    影响：原始日志不得提交；脱敏规则误伤会降低证据可读性。
    原因判断：发布脚本 `Run:` 日志仍输出完整 native 命令行，任务侧初始脱敏正则匹配任意 `-p` 子串。
    处理动作：立即覆盖 `publish-test-log-tail-sanitized-r260729d-r1.txt`，改为只脱敏空白后的 CLI 参数 `\s-p...`；新增经验到 `docs/powershell-preflight-lessons.md`。
    结果：最终保存的日志尾部不含明文 `-p` 参数，且不再误伤 `ruoyi-vue-pro`。
    是否可前置检查：是，保存 operation log 前强制运行脱敏和 secret pattern scan。
    是否可自动化：是，封装统一 sanitizer 并在 closeout 前扫描 `-p(?!<redacted>)`。
    下次如何避免：发布脚本源头脱敏，任务侧只保存 sanitizer 后的日志。

20. 现象：Playwright CLI 首次截图失败，提示浏览器 executable 缺失；执行 `npx playwright install chromium` 超过 300 秒超时。
    阶段：前端页面 / 运行控制台页面验收。
    影响：若依赖默认缓存会阻塞页面验收。
    原因判断：本机 Playwright browser cache 缺少当前版本 Chromium，但系统已安装稳定 Chrome。
    处理动作：改用 `npx playwright screenshot --channel chrome` 和 `npx playwright cli open --browser chrome`。
    结果：测试服前端截图、运行控制台截图和版本变更说明快照均通过。
    是否可前置检查：是，Playwright 验收前检查 `npx playwright --version`、浏览器缓存和 Chrome/Edge 可用性。
    是否可自动化：是，页面验收脚本可优先使用稳定安装浏览器 channel。
    下次如何避免：发布验收中不临时下载浏览器；缓存缺失时直接使用已安装 Chrome/Edge。

21. 现象：r260729d 发布前测试服 `.env IMAGE_TAG=release-20260729-sqlfix-test-r260729c-r1`，但实际 backend/frontend 容器仍运行旧镜像 `release-20260728-codeonly-noonlyoffice-test-r2`。
    阶段：r260729d publish-test 前碰撞检查。
    影响：说明前序失败 releaseTag 留下 `.env` / 实际镜像漂移；若只重启而不重新发布，可能尝试错误目标。
    原因判断：失败发布曾写 `.env`，但容器没有完成切换或后续恢复到旧运行态。
    处理动作：记录漂移；确认无 active publish 进程和无 active release lock；r260729d 正式 publish-test 以新 releaseTag 覆盖并最终使 `.env` 与实际镜像一致。
    结果：r260729d 运行态验收中 `.env`、实际镜像和 release-info 已一致。
    是否可前置检查：是，每次 publish-test 前后都同时查 `.env` 与实际镜像。
    是否可自动化：是，预发布脚本应自动输出 drift 状态并在成功后复核消除。
    下次如何避免：失败路径要么自动恢复 `.env`，要么后续发布前显式标记 drift 并用新 releaseTag 覆盖验证。

22. 现象：第一次 r260729d 远端预发布脚本通过 SSH stdin 发送时仍带 `ssh -n`，只返回 `close - IO is still pending on closed socket`，没有执行脚本正文。
    阶段：测试服 prepublish 碰撞检查。
    影响：如果不复核输出，会把空检查误判为 PASS。
    原因判断：`ssh -n` 会关闭 stdin，与管道传脚本冲突。
    处理动作：去掉 `-n` 后重跑并覆盖证据，得到真实 `.env`、容器、health、release-info 和锁表输出。
    结果：预发布碰撞检查有效通过。
    是否可前置检查：是，所有 SSH stdin 脚本禁止加 `-n`。
    是否可自动化：是，在 PowerShell/SSH wrapper 中根据是否传 stdin 自动禁止 `-n`。
    下次如何避免：只有远端命令不需要 stdin 时才允许 `ssh -n`；管道脚本必须检查输出中包含预期锚点和 `EXIT_CODE=0`。

23. 现象：closeout 时 `git worktree remove --force` 已移除 Git 注册，但多个 release worktree 物理目录仍报 `Directory not empty`；首次物理清理 `r260729a/app` 又因 pnpm `node_modules` 内长路径/瞬时文件返回 `FileNotFoundError`。
    阶段：task closeout / release worktree 清理。
    影响：不能仅凭 Git 注册消失就判定清理完成；若物理目录残留，后续发布可能误复用旧目录或被残留依赖占用磁盘。
    原因判断：前端 `node_modules`、pnpm 硬链接/软链接和运行态输出导致 Git 无法完全删除物理目录；Windows 长路径和瞬时文件删除顺序触发普通递归删除失败。
    处理动作：先确认目标路径均为本任务 `r260729a/b/c/d` release worktree 或 state 目录、Git 注册已移除、无 `.git` marker、无进程命令行引用；再使用带 `\\?\` 长路径前缀和 FileNotFound 容错的受控删除脚本清理精确目标。
    结果：维护仓 release worktree `r260729a/b/c/d`、主程序 release worktree `r260729a/app` 与 `r260729b/c/d-release-app`、状态目录 `r260729a/b/c/d-state` 均已删除；父目录为空后删除；维护仓与主程序 `git worktree list --porcelain` 不再包含 `r260729a/b/c/d`。
    是否可前置检查：是，closeout 应在 `git worktree remove` 后同时核 Git 注册、`.git` marker、进程引用、物理路径和父目录残留。
    是否可自动化：是，task-closeout 或 release cleanup 可增加“Git 注册已移除但物理目录残留”的长路径清理分支，并记录精确路径白名单。
    下次如何避免：不要把 `git worktree remove` 的退出码或注册列表作为唯一清理证据；对含前端依赖的 release worktree 固定执行物理路径复核与长路径安全删除。

## Long Process Review

2026-07-29 09:58 当前进度：发布输入冻结、经验门禁、migration gate、前端 build:test、后端 MES compile、维护控制台 build 和运行控制台启动已完成。阻塞点：无；耗时原因：前端 install/build 和后端 Maven compile 时间较长，维护控制台 release-status 全量扫描超时。下一步：执行 build-release preview/action，生成并校验 manifest、版本号和变更说明。

2026-07-29 10:39 当前进度：build-release 已 SUCCESS，manifest/source/version/change notes 验收 PASS，测试服发布前碰撞检查 PASS。阻塞点：无；耗时原因：backend package、frontend build、Docker image build/export 与 NAS upload 均为长耗时步骤，另有一次远端碰撞检查因 schema 假设错误重跑。下一步：仅执行 publish-test preview/action，并做测试服真实运行态与运行控制台页面验收。

2026-07-29 11:03 当前进度：publish-test 已失败并完成状态冻结。阻塞点：`20260726_dcc_codex_test_items_seed.sql` collation mismatch；同时测试服 `.env IMAGE_TAG` 已变更但容器实际镜像仍为旧 tag。耗时原因：required SQL 文件量大，上传和逐条 migration 记录耗时；失败发生在后段 SQL。下一步：等待用户批准后进入独立修复任务，修复并提交 SQL，再用新的 release worktree / releaseTag 重建重发；当前任务按发布规则保持 blocked，保留 worktree/state。

2026-07-29 11:12 当前进度：已完成失败证据收束、问题记录、敏感信息扫描、经验关键词路由和 worktree 干净状态复核。阻塞点未变化：required SQL collation mismatch，且测试服 `.env IMAGE_TAG` 与实际容器镜像存在漂移。下一步：先修复并提交 `20260726_dcc_codex_test_items_seed.sql` 的 collation 比较问题；修复后必须使用新的 clean release worktree 和新的 releaseTag 重新构建发布。

2026-07-29 12:04 当前进度：SQL collation 修复已在独立主程序 worktree 提交并推送，提交 `b06cf220bda8ebfc8989318d6f75cf88b64f8cd9`；第二轮发布 worktree `r260729b` 已冻结维护仓 HEAD `4a77055f4a90209bae9bbba4fc2b75c03eb9aa88` 和主程序修复提交 `b06cf220bda8ebfc8989318d6f75cf88b64f8cd9`。阻塞点：首次 `build-release` 尝试 `release-20260729-sqlfix-test-r260729b-r1` 因新前端 worktree 缺少 `node_modules` 导致 `cross-env` 不可用而失败。耗时原因：重新建立 clean worktree 后依赖目录不随 Git 复制，需要显式依赖预热。下一步：在前端构建目录执行 `pnpm install --frozen-lockfile` 与 `pnpm build:test` 预检，通过后用新 releaseTag `release-20260729-sqlfix-test-r260729b-r2` 重建。

2026-07-29 18:10 当前进度：r260729c publish-test 失败根因已修复为本地提交 `919122b6`；GitHub push 连续三次 `Recv failure: Connection was reset`，不作为构建输入前置，下一步从本地已提交 commit `919122b6` 创建新的 clean release worktree / releaseTag 重建，仅测试服发布继续验证。

2026-07-29 19:15 当前进度：r260729d `build-release` 与 `publish-test` 已 SUCCESS，测试服真实运行态、release-info、运行控制台版本变更说明和 forbidden operation 检查全部通过；经验沉淀已合并到已有文档。阻塞点：非发布范围的 GitHub 推送仍因连接 reset 阻塞，修复 worktree 保留。下一步：将任务置为 `ready_for_closeout`，执行 task-closeout-cleanup preview/apply，清理本任务 release worktree 和 state。

2026-07-29 19:41 当前进度：task-closeout-cleanup preview/apply 已通过；本任务 `r260729a/b/c/d` release worktree、主程序 release worktree 和 state 目录已清理，物理路径与 Git 注册复核均为不存在；运行控制台 48181 health=`UP` 且仍指向主维护路径。阻塞点：无；非发布范围的 GitHub push reset 问题仍保留在 `D:\IntRuoyiWorktree\r260729-sql-collation`。下一步：将任务状态标记为 `completed` 并提交本任务记录与经验沉淀文件。
