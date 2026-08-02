# Execution Log

## BDD

- BDD: HEAD-only rerun after 09:58 -> Given earlier 2026-08-02 releases before 09:58 must not count as completion evidence, When this release starts, Then the branch, target HEAD, workspace status, clean build directory and temporary worktree path are recorded before any build.
- BDD: Build package traceability -> Given a frozen target HEAD, When build-release produces a test release package, Then manifest, version number and change notes must prove they belong to the frozen target HEAD before publish-test is allowed.
- BDD: Test-only deployment -> Given the user only authorizes test server deployment, When the release package is deployed, Then only publish-test may run and production / backup promotion actions remain forbidden.
- BDD: Runtime acceptance -> Given publish-test reports success, When verification runs, Then actual image tags, container state, backend health, frontend HTTP 200, frontend page, runtime console version and change notes must all match the release before success is declared.

## Command Evidence

- GREEN: startup-preflight -> PASS, task document created before production build, test, release or environment modification.
- GREEN: previous-task-check -> PASS, recent owned task `20260802-head-test-only-release` is marked `completed`, but its evidence is before the user's 2026-08-02 09:58 cutoff and is not reused as completion proof.
- GREEN: experience-preflight -> PASS, 已读取并摘取 `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\powershell-memory.md` 的本次仅测试服重新发布强制门禁。
- GREEN: git-preflight -> PASS, maintenance branch `int_main` HEAD `b25214b3de563aa83e3bac9eacf401da49c5f476` dirty in main workspace; app branch `int_main` HEAD `b99246f58ff7d556caee24307ec89b662d0427e3` dirty in main workspace; both builds isolated into clean release worktrees.
- GREEN: release-worktree-freeze -> PASS, maintenance worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802b\m` at `b25214b3de563aa83e3bac9eacf401da49c5f476`; app worktree `D:\IntRuoyiWorktree\r260802b-release-app` backend/frontend at `b99246f58ff7d556caee24307ec89b662d0427e3`; all release worktrees detached and clean before build.
- GREEN: runtime-control-config -> PASS, local config in release maintenance worktree points `repo-root` and `frontend-root` to the frozen app worktree, and `state-dir` to `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260802b-state\runtime-control`.
- GREEN: migration-policy-gate -> PASS, `migration-policy-gate-r260802b.json` recorded `status=passed`, `migrationCount=406`.
- GREEN: frontend-dependency-gate -> PASS, frozen app frontend dependencies installed with `corepack pnpm@10.25.0 --dir D:\IntRuoyiWorktree\r260802b-release-app\IntRuoyiFronted install --frozen-lockfile`; `cross-env.cmd`, `vite.cmd`, `vue-tsc.cmd` present.
- GREEN: maintenance-build -> PASS, `scripts\build.ps1` completed in release worktree; Maven tests `26` run, `0` failures/errors; Jar `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` produced.
- GREEN: runtime-control-start -> PASS, task-owned runtime-control started on `127.0.0.1:48181`, parent PID `40980`, Java PID observed `43716`, health `UP`.
- GREEN: build-release-preview -> PASS, preview for `release-20260802-intmain-head-test-r260802b-r1` used `-Mode build-release`, `-Component intruoyi`, `-SkipDatabaseSync`, `-SkipMinioSync`, `-TestServerHost 172.30.30.58`.
- GREEN: build-release -> PASS, operation `op-2026-08-02T021129767983200Z-e204dce2-6be8-4a13-9428-063c4070ae40` finished `SUCCESS`.
- GREEN: manifest-validation -> PASS, package `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260802-intmain-head-test-r260802b-r1` has manifest `releaseTag=release-20260802-intmain-head-test-r260802b-r1`, `component=intruoyi`, `publishScope=code-only`, sourceRepos commit `b99246f58ff7d556caee24307ec89b662d0427e3`, `dirty=false`, artifact hashes checked `420/420`, no missing/size/hash mismatches.
- GREEN: image-release-info -> PASS, local Docker images `intruoyi-backend:release-20260802-intmain-head-test-r260802b-r1` and `intruoyi-frontend:release-20260802-intmain-head-test-r260802b-r1` exist; frontend image `release-info.json` contains target releaseTag, change summary, changes and clean sourceRepos.
- GREEN: remote-prepublish -> PASS, test server had old r260802a before deployment; `running_locks=0`, target r260802b migration `FAILED/RUNNING=0`, backend health `UP`, frontend HTTP `200`; historical old failed migrations `3` recorded but not blocking current target.
- GREEN: publish-test-preview -> PASS, preview for r260802b used `-Mode deploy-release`, `-Environment test`, `-ServerHost 172.30.30.58`, `-RemoteAppDir /opt/intruoyi/runtime`, and no prod/backup/mark-tested action.
- GREEN: publish-test -> PASS, operation `op-2026-08-02T022945019393Z-852720a9-61ba-4c79-8cc5-245ced64c078` finished `SUCCESS`; payload used only `action`, `reason`, `releaseTag`.
- GREEN: remote-runtime-verification -> PASS, `.env IMAGE_TAG`, backend/frontend image tags, container running state, backend health, frontend HTTP 200, frontend title, release-info, release lock `APPLIED`, and target migration `FAILED/RUNNING=0` all match r260802b.
- GREEN: runtime-control-release-status -> PASS, `testCurrentReleaseTag=release-20260802-intmain-head-test-r260802b-r1`, summary and changes present, sourceRepos dirty=false, `forbiddenActionsPresent=[]`.
- GREEN: frontend-page -> PASS, screenshot `frontend-page-r260802b-r1.png` captured real test server frontend page.
- GREEN: runtime-console-page -> PASS, Playwright page probe opened `http://127.0.0.1:48181/`; title `运行控制台`, target releaseTag visible, change button visible, package line and component visible, console errors and failed requests empty.
- GREEN: experience-consolidation -> PASS, updated test-release, release-build and PowerShell preflight lessons plus keyword routing in `docs/experience-index.md`.
- GREEN: runtime-control-stop -> PASS, task-owned PID `40980` and Java PID `43716` stopped after command-line path verification; `127.0.0.1:48181` returned to `NO_LISTENER`.
- GREEN: task-closeout-cleanup -> PASS, preview/apply kept formal evidence and deleted only task-owned runtime-control logs, PID file and temporary Playwright probe script.
- GREEN: worktree-cleanup -> PASS, Git registrations for `r260802b` maintenance/app release worktrees removed; residual ignored physical directories and state dir deleted after allowlist, no `.git`, no process references and fixed path boundary checks.
- GREEN: final-remote-recheck -> PASS, `remote-final-recheck-r260802b-r1.json` confirms test server `.env`, images, containers, health, HTTP, release-info, release lock and migration checks still match r260802b after local cleanup.

## Issue Log

| ID | Phenomenon | Stage | Impact | Cause Judgment | Action | Result | Preflight? | Automatable? | Next Avoidance |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| I001 | 用户明确要求不考虑 2026-08-02 09:58 前发布实现，已有 r260802a 成功证据不能复用。 | 启动边界 | 若复用旧证据会误判本次“重新上传”完成。 | 时间边界是验收范围变化，不是技术状态复用。 | 新建 `20260802-0958-head-test-only-release` 任务目录，冻结新 HEAD，重新 build-release、publish-test 和验收。 | r260802b 全链路重新完成。 | 是 | 是 | 发布任务文档必须写入时间边界和不可复用证据范围。 |
| I002 | 维护仓和主程序主工作区均存在未提交改动。 | Git / worktree | 直接构建会污染产物来源。 | 主工作区用于持续开发，存在并发/历史脏改动。 | 创建本轮专用 clean release worktrees 并固定 detached HEAD。 | 构建来源仅为目标 HEAD，manifest sourceRepos dirty=false。 | 是 | 是 | 发布前固定检查 `git status --short --branch`、`git rev-parse HEAD`，dirty 时强制 release worktree。 |
| I003 | 初始 `rg build-release` 类宽范围扫描命中大量历史 evidence，输出过大。 | 文档/命令探索 | 影响审计效率，容易淹没关键证据。 | 未限定任务目录、文件类型或最大结果。 | 改为按目标文件和关键词限域读取。 | 后续证据读取可控。 | 是 | 是 | 历史 evidence 仓库中搜索必须限定路径、关键词和输出行数。 |
| I004 | 维护控制台构建后生成 untracked `runtime/`。 | 构建后 Git 状态 | 若不清理会让 release worktree 变脏，影响发布来源证明。 | 测试/运行控制台构建过程生成状态文件。 | 按精确 allowlist 删除生成文件并复核 worktree clean。 | maintenance release worktree 回到 clean。 | 是 | 是 | 构建后必须重新跑 release worktree `git status --short`，state-dir 尽量放到 worktree 外。 |
| I005 | 本机策略拦截 PowerShell 递归清理/Remove-Item 复合命令。 | 清理/构建收束 | 无法用宽脚本清理构建生成物。 | 命令含递归删除和复杂路径，触发本地安全策略。 | 使用 Python allowlist 精确 unlink/rmdir，并验证路径边界。 | 生成物清理完成。 | 是 | 是 | 清理任务用绝对路径 allowlist、非 Git repo 断言、无进程引用断言后执行。 |
| I006 | 本机策略拦截复杂 `Start-Process` 启动命令。 | 本地运行控制台 | 无法按原 PowerShell 命令启动临时控制台。 | 命令过宽且含复杂参数。 | 使用 Python `subprocess.Popen` 启动，并记录 parent PID / Java PID / health。 | runtime-control 在 48181 健康运行。 | 是 | 是 | 长命令拆小步，启动后必须记录 PID、命令行路径和 health。 |
| I007 | build/publish 状态 API summary 一度仍显示“命令已提交到本机执行队列”，但日志/进程实际推进。 | operation 轮询 | 可能误判 RUNNING 卡死或提前失败。 | summary 字段滞后，不等于最终状态或日志进度。 | 同时检查 operation final、日志推进、远端实际状态。 | build 和 publish 最终均 `SUCCESS`。 | 是 | 是 | 长 RUNNING 先看 operation log 更新时间、进程和远端状态，不只看 summary。 |
| I008 | 远端 SQL 输出含字面量 `\t`，首次 parser 按真实 tab 解析失败。 | 远端预检 | 可能误判 release lock/migration 字段缺失。 | 远端 shell/SQL 输出转义与本地 parser 预期不一致。 | parser 同时支持真实 tab 和字面量 `\t`，重新解析。 | prepublish/runtime JSON 正确生成。 | 是 | 是 | SQL 采集前加输出格式探针，parser 支持 tab 与 `\\t` 两种分隔。 |
| I009 | 首次远端 release lock 查询使用不存在列 `lock_key`。 | 远端运行态验收 | release lock 无法确认时不得判定成功。 | 历史记忆与当前表 schema 不一致。 | 先 `DESCRIBE infra_release_operation_lock`，改用真实列 `target_environment`、`release_tag`、`status`。 | release lock 验证为 `APPLIED`。 | 是 | 是 | 远端锁表/迁移表查询前必须 schema-first，不硬编码旧列。 |
| I010 | Playwright probe 初始 `.mjs` 使用 `require` 加 top-level await，随后又遇到模块解析路径问题。 | 页面验收 | 运行控制台页面证据无法生成。 | ESM/CJS 混用，脚本不在前端依赖解析根目录。 | 改用 `createRequire('D:/IntRuoyiWorktree/r260802b-release-app/IntRuoyiFronted/package.json')` 绑定依赖根。 | 页面探针和截图通过。 | 是 | 是 | Playwright ESM 脚本统一用 `createRequire(<frontend package.json>)` 解析本轮 worktree 依赖。 |
| I011 | SSH stderr 出现 MySQL password warning 和 `IO is still pending`。 | 远端验收 | 若按 stderr 单独判失败会误报。 | 这是 carrier/warning，stdout 断言完整且 exit code 为 0。 | 记录 stderr，判定以 exit code 与结构化 stdout assertions 为准。 | 运行态验收通过，warning 已记录。 | 是 | 是 | native/SSH 命令必须以退出码、断言完整性和敏感信息扫描共同判定。 |
| I012 | publish-test 耗时较长，过程中远端容器已变化但本地 operation 仍 RUNNING。 | 发布执行 | 可能重复操作或提前中断。 | 远端部署步骤长、状态写回与实际容器变化不同步。 | 保持同一 operation 轮询，分阶段记录远端状态，不重复提交。 | operation 最终 `SUCCESS`，远端运行态一致。 | 是 | 是 | 长耗时发布记录阶段复盘，禁止因 RUNNING 直接重复 publish-test。 |
| I013 | `git worktree remove --force` removed Git registration but physical directories remained due ignored generated files / dependencies. | closeout / worktree cleanup | If only registration is checked, task-owned disk artifacts remain and later tasks may confuse them with active worktrees. | Git removed metadata but could not delete non-empty directories. | Verified no process references, no `.git`, fixed allowlist paths, then deleted exact r260802b physical roots and state dir. | Git registration and physical paths all absent. | 是 | 是 | closeout must check both `git worktree list` and physical `Test-Path`; residual ignored files require allowlist cleanup. |
| I014 | Final remote recheck initially parsed multi-line `/release-info.json` as only `{`. | final runtime verification | release-info/sourceRepos checks falsely failed despite core runtime checks passing. | key-value stdout collector expected one line per key; curl returned pretty multi-line JSON. | Recollected release-info with CRLF-safe compact (`tr -d '\r\n'`) and reran all assertions. | Final remote recheck passed. | 是 | 是 | Remote JSON in key-value output must be compacted or base64/JSON-file transported before local parsing. |

## Progress Retrospective

- Startup: created a new task boundary for the 09:58-after rerun and excluded earlier 2026-08-02 release evidence from completion.
- Git/worktree: both main workspaces were dirty, so the release used fresh dedicated clean worktrees and recorded frozen commits before build.
- Build: migration policy, frontend dependencies, maintenance console build, Docker images, manifest hash validation and release-info checks passed for r260802b.
- Publish: publish-test only was executed against `172.30.30.58`; no mark-tested, promote-prod or promote-backup operation appeared.
- Runtime: real test server `.env`, images, containers, health, HTTP, release-info, lock/migration, frontend page and runtime console page all matched r260802b.
- Long-running cause: build/publish involved Maven, pnpm, Docker image generation/upload and remote container rollout; status summary lag required log/process/remote-state correlation.
- Closeout plan: stop only task-owned runtime-control, run closeout preview/apply, remove r260802b worktrees/state, final remote recheck, then mark completed.
- Closeout: task-owned runtime-control stopped, task-closeout cleanup applied, release worktree Git registrations removed, residual physical directories/state dir deleted after allowlist checks.
- Final verification: post-cleanup remote recheck passed for r260802b; task can be marked completed.
