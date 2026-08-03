# Execution Log

## User Intent

- 用户要求“修复并继续”，即先修复上一轮 required SQL 菜单主键冲突根因，再继续仅测试服发布。

## BDD

- BDD: required SQL checksum 漂移重放安全 -> Given 测试服已有 `system_menu.id=6813` 且 required SQL checksum 与 manifest 不一致, When 发布流程判定 `20260513_dcc_base_schema` 需要重放, Then SQL 必须幂等跳过等价菜单或在发布前 fail fast，不能在发布过程中触发 duplicate primary key 并造成部分切换。
- BDD: 修复后仅测试服发布 -> Given 修复已提交并从新 HEAD 创建 clean release worktree, When 构建新 releaseTag 并仅执行 `publish-test`, Then 测试服运行态和运行控制台都指向同一新 releaseTag，且不触发正式服或备份服动作。

## TDD Evidence

- RED: `python -X utf8 -m pytest IntRuoyiBackend\script\tests\test_release_sql_idempotency_contract.py -q` -> FAIL，新增合同测试先证明 `20260513_dcc_base_schema.sql` 仍硬编码 `id` / `6813`，无法防止 checksum 漂移重放时的主键冲突。
- GREEN: `python -X utf8 -m pytest IntRuoyiBackend\script\tests\test_release_sql_idempotency_contract.py -q` -> PASS，`15 passed`。
- GREEN: `node IntRuoyiBackend\script\tests\dcc_controlled_print_contract.test.mjs` -> PASS。
- GREEN: `python -X utf8 -m pytest script\tests\test_release_migration_policy_gate.py script\tests\test_release_sql_idempotency_contract.py -q` -> PASS，`22 passed`。
- GREEN: `python -X utf8 IntRuoyiBackend\script\release\run-release-migration-policy-gate.py --sql-root IntRuoyiBackend\sql\mysql --output doc\tasks\20260803-fix-dcc-base-schema-menu-id-release\migration-policy-gate.json` -> PASS，`status=passed`，`migrationCount=415`。
- GREEN: `mvn -pl yudao-module-dcc -am "-Dtest=DccControlledPrintContractTest" "-Dsurefire.failIfNoSpecifiedTests=false" test` -> PASS，3 tests。
- REGRESSION-NOTE: 宽 Maven `DccBaseSchemaTest,DccControlledPrintContractTest` 暴露既有 `DccBaseSchemaTest` 非破坏性检查失败；本任务修复的 controlled print Java 合同 PASS，宽测失败已按非本次引入问题记录，未作为绕过发布依据。

## Experience Preflight

- GREEN: experience-preflight -> PASS；已读取 `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\worktree-restrictions.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\powershell-memory.md`、`E:\IntRuoyi\docs\powershell-encoding.md`、`E:\IntRuoyi\docs\task-closeout-rules.md`；本轮高风险动作只限测试服发布，禁止正式服、备份服、mark/promote。

## Milestone Updates

- Startup: 已确认上一轮 blocker 为 `20260513_dcc_base_schema.sql` 重放时 `system_menu.id=6813` 主键重复；本任务不复用失败 releaseTag。
- Source fix: 主程序修复已在 clean worktree `D:\IntRuoyiWorktree\20260803-fix-dcc-base-schema-menu-id-release` 提交，commit `ae4c85511f050785f91b51f29c22c511df8e7cdc`，提交后 `git status --short --branch` clean。
- Release scope: 下一轮发布使用新 releaseTag，不能复用 `release-20260803-intmain-head-test-r260803a-r1`；只执行 build-release 与 publish-test。

## Issue Log

### P001 required SQL checksum 漂移重放触发菜单固定主键冲突

- 现象：上一轮 `publish-test` 在 `20260513_dcc_base_schema.sql` line 1298 报 `ERROR 1062 Duplicate entry '6813' for key 'system_menu.PRIMARY'`。
- 阶段：测试服 publish-test required SQL。
- 影响：发布失败，失败 releaseTag 判废，不能继续 mark/promote 或复用。
- 原因判断：目标库历史 checksum 与新 manifest checksum 不一致导致 required SQL 重放，SQL 用业务键 `permission` 做存在判断却硬编码 `system_menu.id=6813`，当同 ID 已被其它菜单占用时触发主键冲突。
- 处理动作：修复源 SQL，移除 `id=6813` 固定写入，改用自增 ID；补静态合同测试和 migration policy gate。
- 结果：修复提交 `ae4c85511f050785f91b51f29c22c511df8e7cdc` 已完成，目标测试和迁移门禁通过。
- 是否可前置检查：是，发布前静态扫描 required SQL 菜单 seed 的固定 ID 与业务键不一致。
- 是否可自动化：是，已新增 `test_release_sql_idempotency_contract.py` 合同覆盖。
- 下次如何避免：required SQL 菜单/角色 seed 优先使用稳定业务键幂等；若必须固定 ID，发布前只读核验目标库 ID 占用并 fail fast。

## Build / Publish Evidence

- GREEN: app dependency restore -> PASS；`corepack pnpm@10.25.0 install --frozen-lockfile` 在 `D:\IntRuoyiWorktree\r260803b-release-app\IntRuoyiFronted` 完成，临时 `pnpm.onlyBuiltDependencies` + `pnpm rebuild` 后 `pnpm ignored-builds` 为 `None`，随后恢复 `package.json`，app worktree clean。
- GREEN: maintenance build -> PASS；`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build.ps1` 在 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b\m` 成功，前端 typecheck/build 通过，Maven tests `26` run / `0` failures / `0` errors，jar `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar` 生成。
- GREEN: build-release preview -> PASS；`build-release-preview-gate-r260803b-r1.json` 显示构建动作不包含正式服、备份服、mark/promote。
- GREEN: build-release operation -> PASS；`op-2026-08-03T014004195140200Z-27256ee2-7aa4-4539-a982-044bd4f86239` 最终 `SUCCESS`。
- GREEN: manifest validation -> PASS；`manifest-validation-r260803b-r1.json` 为 `MANIFEST_VALIDATION_PASSED`，`manifest-summary-r260803b-r1.json` 显示 `releaseTag` 匹配、`publishScope=code-only`、`component=intruoyi`、artifactCount `429`、requiredSqlCount `419`、无 website 组件。
- GREEN: source provenance -> PASS；manifest `sourceRepos` 中 backend/frontend commit 均为 `ae4c85511f050785f91b51f29c22c511df8e7cdc` 且 `dirty=false`；frontend image `release-info.json` 同步显示相同 releaseTag/sourceRepos/changeSet。
- GREEN: publish-test precheck -> PASS；`remote-release-precheck-r260803b-r1.json` 显示 SSH、MySQL、release state tables、无 RUNNING test lock、目标 release failed/running=0、backend health、frontend HTTP 均通过。
- GREEN: publish-test preview -> PASS；`publish-test-preview-gate-r260803b-r1.json` 显示 `action=publish-test`、`Mode=deploy-release`、`Environment=test`、`ReleaseTag=release-20260803-dcc-menu-replay-fix-test-r260803b-r1`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，且无 `mark-tested`、`promote-prod`、`promote-backup`。
- GREEN: publish-test operation -> PASS；`op-2026-08-03T020027072659300Z-324edfd7-4658-4822-89ed-0e35e37f7feb` 最终 `SUCCESS`，未执行正式服、备份服或 mark/promote。
- GREEN: remote postcheck -> PASS；`remote-release-postcheck-r260803b-r1.json` 显示 `.env IMAGE_TAG`、backend/frontend image tag、容器 Up、backend health=UP、frontend HTTP=200、release-info tag/source commit、release lock=APPLIED、target release applied rows>0、failed/running=0。
- GREEN: runtime-control page -> PASS；Playwright 打开 `http://127.0.0.1:48181/`，页面显示测试服 `release-20260803-dcc-menu-replay-fix-test-r260803b-r1`，点击“查看变更”后弹窗显示同一版本号、`发布包：release-20260803-dcc-menu-replay-fix-test-r260803b-r1` 和 `组件范围：intruoyi`。
- GREEN: test frontend page -> PASS；Playwright 打开 `http://172.30.30.58:8081/`，页面跳转登录页，标题 `瑛泰管理系统 - 登录`。

## Long Process Review

- 当前进度：测试服发布链路、主程序合回、48181 恢复和本任务 worktree/state 清理均已完成，剩余为 task-closeout-cleanup 预览/应用和最终状态标记。
- 已完成步骤：SQL 修复、回归测试、migration policy gate、维护控制台构建、release 包构建、manifest 验证、publish-test、远端运行态验证、运行控制台页面验证、测试服前端页面验证。
- 阻塞点：原 closeout 阻塞已解除；当前仅保留其它任务在 `E:\IntRuoyi` 的 dirty/ahead 状态作为非本任务遗留。
- 耗时原因：clean app worktree 首次前端依赖恢复约 11m32s；publish-test 上传 704,409,600 bytes 镜像 tar 并逐个 scp 419 个 required SQL 文件，operation 第 80 次轮询才 `SUCCESS`。
- 下一步动作：运行 task-closeout-cleanup preview/apply，确认只清理允许范围后把任务标记 completed。

### P002 pnpm ignored-builds 需要临时 onlyBuiltDependencies

- 现象：clean frontend worktree 中 `pnpm ignored-builds` 初始包含 esbuild、vue-demi 等构建脚本，直接构建存在风险。
- 阶段：构建前依赖恢复。
- 影响：若不处理，前端构建可能缺少 native/postinstall 产物，发布包来源不可确认。
- 原因判断：pnpm 10.25 对 build script 审批需要通过 `onlyBuiltDependencies` 明确允许后 rebuild。
- 处理动作：临时写入 `pnpm.onlyBuiltDependencies`，执行 `pnpm rebuild`，确认 `pnpm ignored-builds` 为 `None` 后恢复 `package.json`。
- 结果：app release worktree 与维护 release worktree 均恢复 clean，构建通过。
- 是否可前置检查：是，build 前运行 `corepack pnpm@10.25.0 ignored-builds`。
- 是否可自动化：是，构建脚本可在 clean worktree 内自动检查并 fail fast。
- 下次如何避免：前端 frozen install 后必须先清零 ignored-builds，再进入 typecheck/Vite/Docker build。

### P003 build-release helper 首次缺少 publishScope

- 现象：build-release 预览曾因 payload 缺少 `publishScope` 无法通过。
- 阶段：运行控制台 build-release API 调用。
- 影响：若不修正，无法构建可验证的 release 包。
- 原因判断：build-release action schema 需要 `publishScope` 等 build-only 字段；deploy action 反而不能带这些字段。
- 处理动作：helper payload 加入 `publishScope=code-only`、`includeOnlyOffice=false`、`includeShowroomBuildPackage=false`、`enableSmartReleaseReport=false` 后重新预览。
- 结果：build-release preview gate 通过，operation `SUCCESS`。
- 是否可前置检查：是，先 preview 并字段化校验。
- 是否可自动化：是，按 action 区分 build-only 与 deploy-only schema。
- 下次如何避免：build-release 和 publish-test 使用不同最小 payload 模板，preview 不通过不得提交 operation。

### P004 publish-test 镜像和 required SQL 上传耗时长

- 现象：publish-test 长时间 `RUNNING`，日志显示先上传 704,409,600 bytes image tar，再逐个 scp 419 个 required SQL 文件。
- 阶段：测试服发布包传输。
- 影响：operation 轮询时间长，容易误判为卡死。
- 原因判断：脚本按 128MB 分片上传镜像并逐文件传 SQL，日志持续推进。
- 处理动作：持续轮询 operation，同时抽查脱敏日志尾部确认从镜像上传推进到 required SQL 上传再到 migration 状态写入。
- 结果：operation 第 80 次轮询返回 `SUCCESS`。
- 是否可前置检查：部分可行，可提前记录 image tar 大小和 required SQL 数量。
- 是否可自动化：是，可增加阶段性进度摘要和 expected-duration 提示。
- 下次如何避免：长时间 `RUNNING` 先看日志是否推进，不要直接中断；若日志停滞再按卡死排障。

### P005 SSH IO pending 警告不可误判为失败

- 现象：远端 postcheck stderr 出现 `close - IO is still pending on closed socket`。
- 阶段：远端 SSH 验收脚本。
- 影响：若只看 stderr 文本，可能误判验收失败。
- 原因判断：SSH 关闭时的 Windows/OpenSSH socket 警告，命令 returncode=0 且 stdout 完整解析。
- 处理动作：以 returncode、解析字段和所有 checks 为准，同时把 stderrRedacted 记录到证据。
- 结果：postcheck `passed=true`，全部运行态检查通过。
- 是否可前置检查：是，验收脚本应区分 carrier warning 与业务检查失败。
- 是否可自动化：是，保留 stderr 但以结构化 checks 判定。
- 下次如何避免：SSH 验收必须输出 JSON checks，禁止仅按 stderr 字符串判定。

### P006 主程序 int_main 并发脏改动阻塞合回收口

- 现象：`E:\IntRuoyi` 的 `int_main` 未包含修复提交 `ae4c85511f050785f91b51f29c22c511df8e7cdc`；工作区有并发未提交和已暂存改动，且 `20260513_dcc_base_schema.sql` 同时存在非本任务 hunk。
- 阶段：发布成功后的 closeout / merge。
- 影响：不能安全提交本任务补丁，不能删除产生修复提交的 worktree，任务不能标记 completed。
- 原因判断：主程序主工作区被其它任务占用；直接整文件暂存会混入 product onboarding 等非本任务 SQL 变更，直接普通 commit 会包含并发暂存文件。
- 处理动作：只把本任务 hunk 落到工作区并运行聚焦 pytest `15 passed`；尝试用索引级暂存隔离 hunk，但发现已有并发暂存文件，随后撤销本任务两个文件的暂存，未提交、未清理 worktree。
- 结果：测试服发布成功不受影响；closeout 阻塞，修复 worktree和 release worktree 保留。
- 是否可前置检查：是，closeout 前检查目标主工作区 `git diff --cached --name-only`、目标文件是否已有非本任务 hunk。
- 是否可自动化：是，任务收口脚本可在 merge 前 fail fast 报告“目标主线有并发 staged/dirty”。
- 下次如何避免：修复提交发布成功后，应先检查主线索引是否干净；若不干净，不尝试合回或删除 worktree，等待所属任务收口。

### P007 Git index.lock 与后台状态扫描干扰精确暂存

- 现象：首次执行路径级 reset / update-index / add 时出现 `.git/index.lock`，后续检查发现多个 `git status` 后台进程正在扫描仓库。
- 阶段：主程序合回暂存。
- 影响：精确暂存失败，存在误判为 Git 损坏或强行清理 index 的风险。
- 原因判断：编辑器/后台 Git 状态扫描与本任务 index 写操作短暂竞争；锁文件随后消失。
- 处理动作：先只读检查 Git 进程和 lock 状态；不重置全 index；改用带重试的路径级命令完成 unstage/stage。
- 结果：暂存区最终只包含本任务两个文件，commit 成功。
- 是否可前置检查：是，合回前检查 `.git/index.lock` 和 `git.exe` 命令行。
- 是否可自动化：是，精确暂存脚本可内置 lock retry 和最终 cached diff allowlist。
- 下次如何避免：遇到 index.lock 先查进程和锁新鲜度，不直接删锁或扩大 reset 范围；最终必须以 `git diff --cached --name-only` allowlist 放行。

### P008 48181 仍指向 release worktree

- 现象：发布成功后 `http://127.0.0.1:48181/admin-api/infra/runtime-control/release-status` 仍显示 r260803b state/log 路径和本轮 releaseTag，PID `33196` 来自 release worktree 启动。
- 阶段：发布后 closeout。
- 影响：若直接删除 release worktree，运行控制台可能引用已删除路径；若不恢复主路径，后续任务会误用本轮 state。
- 原因判断：本轮为了构建/发布启动了 release worktree 维护控制台，发布完成后需要恢复稳定主维护目录。
- 处理动作：停止 PID `33196`；从 `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\start.ps1` 启动主维护目录服务；验证新 PID `57912` 启动日志和 health。
- 结果：48181 health=`UP`，进程启动目录为 `D:\ProjectPackage\Int\IntRuoyiMaintance`。
- 是否可前置检查：是，删除 release worktree 前检查 48181 PID、命令行、health 和 release-status。
- 是否可自动化：是，closeout 脚本可要求 48181 不再引用待删除 worktree。
- 下次如何避免：发布页面验收完成后先恢复主维护路径，再删除 release worktree/state。

### P009 release worktree 注销后物理目录残留

- 现象：`git worktree remove --force` 对 r260803b 维护/app release worktree 返回 `Directory not empty`；维护 worktree 后续已注销但物理目录残留；app release 目录因 pnpm node_modules 断链/权限导致 `.NET Directory.Delete` 报 `Access to the path 'remapping' is denied`。
- 阶段：worktree/state 清理。
- 影响：若只看 Git 注册会误判已清理；若递归删除范围不受控，可能误删其它并发任务 worktree。
- 原因判断：构建产物、ignored 前端依赖、pnpm symlink/断链和只读属性造成 Windows 物理目录删除失败。
- 处理动作：先确认 Git worktree clean/已注销、绝对路径在本任务 allowlist 内、48181 已恢复主路径；维护目录用 `attrib -R` 后 `.NET Directory.Delete` 清理；app release 目录用 Node `fs.rmSync(..., { recursive:true, force:true })` 清理；state 目录同样用固定路径删除。
- 结果：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260803b-state`、`D:\IntRuoyiWorktree\r260803b-release-app`、`D:\IntRuoyiWorktree\20260803-fix-dcc-base-schema-menu-id-release` 均不存在。
- 是否可前置检查：是，cleanup 前后分别检查 Git 注册和物理路径，不把两者混为一谈。
- 是否可自动化：是，可在 cleanup 脚本中加入 fixed allowlist、`existsAfter=false` 和 pnpm symlink-safe 删除器。
- 下次如何避免：先恢复/停止引用进程，再 `git worktree remove`，最后用受限路径清理 ignored 物理残留；禁止跳过物理路径复核。

## Closeout Updates

- MAINLINE COMMIT: `6b1fd19eb` (`任务: 合回DCC受控打印菜单重放修复`) -> files: `IntRuoyiBackend/script/tests/test_release_sql_idempotency_contract.py`, `IntRuoyiBackend/sql/mysql/20260513_dcc_base_schema.sql` only.
- GREEN: `python -X utf8 -m pytest IntRuoyiBackend\script\tests\test_release_sql_idempotency_contract.py -q` in `E:\IntRuoyi` -> PASS, `15 passed in 0.33s`.
- GREEN: immediately after `6b1fd19eb`, `git -C E:\IntRuoyi diff --name-status ae4c85511f050785f91b51f29c22c511df8e7cdc..HEAD -- <task files>` -> no output, target files match fix commit content.
- FINAL-RECHECK: after unrelated later commits, `git -C E:\IntRuoyi merge-base --is-ancestor 6b1fd19eb HEAD` -> PASS; current HEAD `134434c78`, task commit remains in mainline history and target files have no cached/worktree changes for this task.
- RESTORE: stopped release worktree runtime-control PID `33196`; started main maintenance runtime-control PID `57912` from `D:\ProjectPackage\Int\IntRuoyiMaintance`; health `UP`.
- CLEANUP: removed r260803b maintenance/app release worktrees, fix worktree, state dir, and empty parent directory; unrelated concurrent worktrees remain untouched.
- TASK-CLOSEOUT: `task_closeout.py --task-id 20260803-fix-dcc-base-schema-menu-id-release --mode preview` -> PASS, `delete=<none>`, `blocked=<none>`, `warnings=<none>`.
- TASK-CLOSEOUT: `task_closeout.py --task-id 20260803-fix-dcc-base-schema-menu-id-release --mode apply` -> PASS, `deleted_paths=<none>`.
