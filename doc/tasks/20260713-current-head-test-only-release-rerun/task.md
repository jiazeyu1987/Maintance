# 20260713 当前 HEAD 仅测试服发布复跑

## Task Goal

基于当前分支最新已提交代码创建干净临时发布 worktree，构建维护控制台与仅测试服发布包，并只发布到测试服务器；未提交改动不得进入构建产物，发布后完成真实运行态、前端页面、运行控制台版本号和变更说明验收。

## Milestones

- [x] 创建任务记录并完成经验门禁摘取。
- [x] 检查 Git 状态，冻结当前分支 HEAD，创建干净临时发布 worktree。
- [x] 基于冻结 HEAD 构建维护控制台和测试发布包，校验 manifest、版本号、变更说明和来源提交。
- [x] 仅执行 `publish-test`，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- [x] 验证测试服真实运行态、前端 HTTP/页面、运行控制台版本号和变更说明。
- [x] 记录所有问题、耗时点和阶段复盘。
- [x] 发布成功后沉淀前置经验。
- [x] 完成 task-closeout cleanup、临时 release worktree 清理和任务完成记录。

## Expected Verification

- 构建产物只包含冻结 worktree 中当前分支 HEAD 已提交代码。
- 发布包 `manifest.json`、版本号、变更说明与本次构建提交一致。
- `build-release` 与 `publish-test` operation 均为 `SUCCESS`。
- 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health、frontend HTTP 200、前端页面和运行控制台 release-info 均通过。
- 运行控制台显示当前 releaseTag 和版本变更说明。
- 经验沉淀写入可执行前置门禁，并通过关键词路由验证。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，按现有发布契约和前置经验门禁执行，仅在发现契约缺失时 fail fast。
- 是否存在临时补丁或绕过：否。

## BDD Scenarios

- BDD: frozen HEAD test-only release -> Given 当前开发分支可能存在未提交改动, When 执行仅测试服发布, Then 构建包只能来自发布开始时记录的 HEAD 干净 worktree。
- BDD: test-only deployment boundary -> Given 用户只授权测试服发布, When 发布包构建成功, Then 只允许执行 `publish-test` 并禁止 mark-tested/prod/backup 操作。
- BDD: runtime evidence required -> Given 测试服发布脚本返回成功, When 验收发布结果, Then 必须同时校验镜像 tag、容器、健康检查、前端 HTTP/页面、运行控制台版本号和变更说明。

## 经验门禁

### 仅测试服发布范围门禁

- Trigger: 仅测试服发布、`publish-test`、测试服运行态验收、运行控制台版本变更说明核对。
- Preflight check: 本轮只允许 `build-release -> publish-test -> 测试服真实运行态验收`；目标测试服务器为 `172.30.30.58`，远端目录为 `/opt/intruoyi/runtime`；禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服和备份服动作。
- Blocker: 发布目标、releaseTag、目标服务器或动作边界无法确认；preview 出现 prod/backup/mark-tested 实际动作；复用旧 releaseTag 拼接新结果。
- Verification: `execution-log.md` 记录 releaseTag、preview 字段、build/publish operation、远端 `.env IMAGE_TAG`、实际镜像、health、HTTP、release-info 和页面版本对话框。
- Forbidden action: 不得因只发布测试服未走完整发布链而误判失败；不得执行任何正式服、备份服或 mark-tested 动作。
- Evidence: `docs/test-release-preflight.md`、`docs/release-agent-checklist.md` 与本任务执行日志。

### 冻结 HEAD 与临时发布 worktree 门禁

- Trigger: 当前分支 HEAD 发布、主工作区可能存在未提交改动、发布 worktree 创建/清理。
- Preflight check: 记录维护仓、后端仓、前端仓当前分支、HEAD、dirty 状态；在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r<日期><短标识>\m|b|f` 创建本轮专用短路径 release worktree；构建开始后只认该冻结提交，不追逐后续源分支新提交。
- Blocker: release worktree dirty、提交与冻结基线不一致、`runtime-control.local.yaml` 指向主工作区/旧 worktree、state/log/cache 污染 release worktree。
- Verification: 记录三仓 worktree 路径、`rev-parse HEAD`、`status --porcelain`、构建目录、是否产生新提交、是否需合回 `int_main`、最终 Git 注册与物理目录清理结果。
- Forbidden action: 不得从脏主工作区或旧 worktree 构建；不得只查主工作区 clean 而跳过构建后 manifest sourceRepos 校验。
- Evidence: `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/worktree-memory.md`。

### 构建、manifest 与变更说明门禁

- Trigger: `build-release`、发布包候选、manifest、版本号、变更说明校验。
- Preflight check: 运行控制台必须加载本轮 release worktree 逻辑；迁移元数据门禁按冻结脚本 `--help` 当前契约执行；前端依赖按锁文件恢复；`build-release` preview 包含 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync` 和目标 releaseTag。
- Blocker: build operation 非 `SUCCESS`、manifest 缺失、sourceRepos commit 不等于冻结提交、dirty=true、artifact 缺失/哈希不一致、版本号或变更说明不可追溯。
- Verification: 记录 manifest v1 路径、releaseTag、component、publishScope、sourceRepos、artifact hash、changeSet.summary/changes、legacy manifest 分 schema 结果。
- Forbidden action: 不得用界面成功提示、旧 `release-manifest.json`、Docker 缓存或半成品目录替代 Manifest v1。
- Evidence: `docs/test-release-preflight.md`、`docs/release-backup-restore.md`、`docs/release-build-preflight-lessons.md`。

### 测试服真实运行态与页面验收门禁

- Trigger: `publish-test` 后验证测试服状态、远端 Docker、release-info、运行控制台页面。
- Preflight check: 发布前后检查无并发发布或活动 `RUNNING` 锁；远端验收脚本以 UTF-8 bytes + LF 发送且不使用 `ssh -n`；发布后同时验证 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、PDF worker HTTP、release-info、release lock/migration 状态。
- Blocker: 任一运行态字段不等于同一 releaseTag；health/HTTP/release-info/锁表/migration 查询失败；页面版本号或变更说明不可见；console error 无法结构化判定。
- Verification: 记录 SSH/HTTP/JSON/Playwright 结构化证据，运行控制台“版本变更说明”对话框必须可见 releaseTag、summary/changeSet 与后端/前端冻结提交。
- Forbidden action: 不得用 HTTP 200 单项替代完整验收；不得用接口直读替代用户要求的真实页面验收；不得保存明文凭据日志。
- Evidence: `docs/test-release-preflight.md#2026-07-13-仅测试服发布远端验收脚本承载门禁`、`docs/powershell-preflight-lessons.md`。

### PowerShell、SSH 与日志脱敏门禁

- Trigger: Windows PowerShell、中文文本、SSH、MySQL、Playwright、发布日志和证据采集。
- Preflight check: 使用显式 UTF-8 读写；不使用 `&&`；复杂脚本避免 PowerShell 文本层污染；多行远端脚本用 bytes stdin；只输出配置字段名或脱敏摘要，不打印 `.env`、runtime-control 完整配置、容器 env 或 `mysql -p<secret>`。
- Blocker: 共同 PowerShell 规则未读取、输出/证据含 secret、CRLF 污染、中文 mojibake 作为唯一证据、native 命令非 0 仍继续。
- Verification: 记录退出码、结构化 JSON、UTF-8 回读、secret scan、目标状态后置断言。
- Forbidden action: 不得用乱码、默认编码、空 stdout、warning 或脱敏误伤结果继续长链路操作。
- Evidence: `D:\ProjectPackage\Int\IntRuoyi\docs\powershell-memory.md`、`docs/powershell-preflight-lessons.md`。

### 问题记录与经验沉淀门禁

- Trigger: 发布中出现 Git、worktree、构建、manifest、版本说明、发布脚本、镜像、容器、健康检查、页面、运行控制台、文档流程不一致、重复操作或耗时点。
- Preflight check: 每个问题记录现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次如何避免；发布成功后把可前移问题写入 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md` 或 `docs/experience-index.md`。
- Blocker: 发布问题未记录、可复用问题未沉淀、经验缺少 Trigger/Preflight check/Blocker/Verification/Forbidden action/Evidence 六字段、索引无法命中新经验。
- Verification: 任务日志、问题清单、经验文档 diff、`rg` 关键词路由、UTF-8 回读和 `git diff --check`。
- Forbidden action: 不得只写“下次注意”或把一次性流水混入长期经验；不得跳过可自动化/fail-fast 条件。
- Evidence: `docs/experience-index.md` 与 `preflight-experience-consolidation` skill。

## Current Status

completed - release-20260713-current-head-test-r260713u succeeded; experience consolidation completed; task-closeout apply passed; runtime-control restored to main workspace; temporary release worktree and state dir removed; final HTTP/release-info recheck passed.

## Frozen Release Baseline

- Maintenance main workspace: branch `int_main`, HEAD `efa0cfd79c75a48de807a40e1e80deefff63e6ee`, dirty=true。
- Backend main workspace: branch `int_main`, HEAD `a69271e228c7738cd0ade0e12f9b7f8a85aec205`, dirty=true。
- Frontend main workspace: branch `int_main`, HEAD `627f644d542902481809441efe5c1371f6a7d28c`, dirty=true。
- Maintenance release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u\m`, detached HEAD `efa0cfd79c75a48de807a40e1e80deefff63e6ee`, clean。
- Backend release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u\b`, detached HEAD `a69271e228c7738cd0ade0e12f9b7f8a85aec205`, clean。
- Frontend release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u\f`, detached HEAD `627f644d542902481809441efe5c1371f6a7d28c`, clean。
- Build source rule: 本轮构建只允许使用上述 release worktree 冻结提交；后续源分支漂移不纳入本轮发布。

## Release Evidence

- Release tag: `release-20260713-current-head-test-r260713u`
- Build operation: `op-2026-07-13T130433994984600Z-0ddaec3f-7a3b-465a-a40b-182c572b3508` = `SUCCESS`
- Publish-test operation: `op-2026-07-13T132238031788800Z-7427e313-5a0e-4bae-8bc3-be5decaa3c0a` = `SUCCESS`
- Manifest: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260713-current-head-test-r260713u\manifest.json`; `publishScope=code-only`; backend/frontend commits match frozen HEAD; dirty=false; 295 artifacts verified; forbidden data dirs absent.
- Test server: `.env IMAGE_TAG`、backend/frontend image tags、containers、backend health、frontend HTTP、PDF health、release-info、release lock and this release migration failures all passed.
- Runtime console page: `http://127.0.0.1:48181/` displayed the releaseTag and “版本变更说明”; Playwright console errors=0 and warnings=0.

## Issues And Review Notes

### P001 - Maintenance local config absent in clean worktree

- 现象: clean maintenance worktree only had `config/runtime-control.example.yaml`; local `runtime-control.local.yaml` was not tracked.
- 阶段: runtime-control config setup.
- 影响: 48181 could not safely point to frozen backend/frontend roots until a task-owned config was created outside the worktree.
- 原因判断: local operator config is intentionally gitignored because it contains environment-specific settings.
- 处理动作: created `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u-state\runtime-control.local.yaml` from the existing local config with only repo/frontend/ops/state roots changed; recorded only allowlisted non-secret fields.
- 结果: runtime-control health=`UP`, process command line points to frozen maintenance jar and task-owned config.
- 是否可前置检查: 是。
- 是否可自动化: 是。
- 下次如何避免: release setup should check for local config absence and create an external task state config before starting 48181.

### P002 - Maintenance build generated untracked runtime directory

- 现象: after `scripts\build.ps1`, maintenance worktree showed `?? runtime/`.
- 阶段: build preflight / worktree cleanliness.
- 影响: if left in place, source cleanliness proof could fail or sourceRepos could be marked dirty.
- 原因判断: tests/build defaults created runtime state under the checkout before task-owned state-dir was active.
- 处理动作: removed only `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u\m\runtime`, then rechecked all three worktrees clean.
- 结果: worktrees clean before build-release and publish-test.
- 是否可前置检查: 是。
- 是否可自动化: 是。
- 下次如何避免: after building maintenance console, always run `git status --porcelain --ignored=no` and clear/block on generated `runtime/`.

### P003 - Direct UNC NAS manifest check false negative

- 现象: `Test-Path \\172.30.30.4\IT共享\Backup\ReleasePackage\release-...\manifest.json` returned false after build.
- 阶段: publish-test package availability precheck.
- 影响: a guessed UNC path could incorrectly block a valid package if SMB mapping or path interpretation differs.
- 原因判断: deploy script owns the NAS mount/config path and package lookup; local direct UNC check is not authoritative.
- 处理动作: read frozen deploy script package directory conversion and used runtime-control publish-test preview, which successfully resolved configured NAS/package inputs.
- 结果: publish-test preview passed and publish-test operation succeeded.
- 是否可前置检查: 是。
- 是否可自动化: 是。
- 下次如何避免: specified releaseTag should be validated through manifest plus deploy preview/configured NAS lookup, not a single ad hoc UNC `Test-Path`.

### P004 - Historical failed migrations present on test server

- 现象: remote precheck found `failed_migration_count=2`.
- 阶段: publish-test precheck.
- 影响: could be mistaken as current release blocker.
- 原因判断: failed rows were historical releaseTags `release-20260709-codeonly-three-env-head-v8` and `release-20260628-1438-head-full-v8`.
- 处理动作: queried failed rows and separated historical failures from target release lock/precheck.
- 结果: current release had no active lock and later `this_failed_migration_count=0`.
- 是否可前置检查: 是。
- 是否可自动化: 是。
- 下次如何避免: migration failure checks should report both global historical failures and target-release failures separately.

### P005 - Local SSH verification script f-string brace error

- 现象: first runtime verification script failed locally with `SyntaxError: f-string: valid expression required before '}'`.
- 阶段: runtime verification script carrier.
- 影响: no server action happened; verification delayed.
- 原因判断: Python f-string was used around shell/SQL/JSON text containing literal braces.
- 处理动作: rewrote script carrier to use ASCII placeholders and `.replace(...)`, then sent UTF-8 bytes to SSH.
- 结果: remote runtime verification passed.
- 是否可前置检查: 是。
- 是否可自动化: 是。
- 下次如何避免: for SSH/bash/SQL scripts containing braces, avoid Python f-strings; use placeholder replacement or external UTF-8 script files.

### P006 - Runtime console dialog does not show source commits

- 现象: Playwright dialog probe showed version and change notes, but not backend/frontend commit hashes.
- 阶段: runtime console page verification.
- 影响: page alone cannot prove source commit identity.
- 原因判断: current UI version dialog exposes user-facing version/change notes; source commits are available in `release-info.json`.
- 处理动作: verified source commits through remote `release-info.json`; verified page only for user-visible releaseTag and “版本变更说明”.
- 结果: user acceptance passed: running console displayed current version and change notes; release-info commit verification passed separately.
- 是否可前置检查: 是。
- 是否可自动化: 是。
- 下次如何避免: split acceptance into page-visible version/change notes and API-visible source commit verification unless UI adds commit fields.

### P007 - Long-running build and publish stages

- 现象: build-release spent several minutes across Maven, frontend, Docker image build; publish-test spent additional time in large image chunk upload/copy.
- 阶段: build-release / publish-test.
- 影响: requires operation polling and progress notes; repeated submit would risk duplicate release actions.
- 原因判断: backend multi-module build, frontend production build, no-cache Docker image, 815MB image tar upload.
- 处理动作: polled recorded operation IDs only; used redacted log tails for progress.
- 结果: build and publish completed SUCCESS without duplicate operations.
- 是否可前置检查: 部分可。
- 是否可自动化: 是。
- 下次如何避免: always record operationId immediately and poll by ID; use redacted tail only for progress.

### P008 - Git worktree remove left physical directories

- Phenomenon: `git worktree remove --force` returned `Directory not empty` for maintenance/frontend release worktrees.
- Stage: closeout / temporary release worktree cleanup.
- Impact: task could not be marked completed until Git registrations, process references, physical root, and state dir were all cleared.
- Cause judgment: ignored build artifacts and node_modules remnants remained after Git worktree unregistration on Windows.
- Action: verified no Git registrations and no external process references, then cleared attributes and removed only fixed paths under `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713u*` with long-path PowerShell cleanup.
- Result: maintenance/backend/frontend registrations absent; `r260713u` and `r260713u-state` physical paths absent; runtime-control health remained UP from main workspace.
- Can precheck: yes.
- Can automate: yes.
- Next avoidance: after `git worktree remove`, always verify Git registration plus physical root; if Directory not empty occurs, apply the fixed-root residual cleanup gate.

## Experience Consolidation

- `docs/release-build-preflight-lessons.md`: 新增 clean maintenance worktree local config/runtime 输出门禁、发布包可用性与历史 migration 失败分层门禁，并补充长任务 operationId 证据。
- `docs/powershell-preflight-lessons.md`: 新增 Python f-string literal braces 与远端验收脚本门禁。
- `docs/test-release-preflight.md`: 新增运行控制台版本说明与 source commit 分层验收门禁。
- `docs/experience-index.md`: 新增 local config 缺失、runtime dirty、UNC NAS false negative、historical failed migration、f-string braces 和页面/source commit 分层验收关键词路由。

## Cleanup Keep

- `doc/tasks/20260713-current-head-test-only-release-rerun/migration-policy-gate-r260713u.json`
- `doc/tasks/20260713-current-head-test-only-release-rerun/runtime-console-page-probe-r260713u.json`
- `doc/tasks/20260713-current-head-test-only-release-rerun/runtime-console-r260713u-release-info.png`
