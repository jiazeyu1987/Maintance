# Execution Log

- Task ID: `20260924-two-button-release-delivery`
- Created: `2026-09-24T10:49:16`

## Phase Entries

Append one reviewed section per executor pass using real phase ids and real evidence refs.

## Phase-P1-Maintenance-Review
- 主代理review已核对实际Acquire SQL、同tag/同operation/同executor但不同lease的完整生命周期、真实Ownership函数与本地MySQL传输、实际carrier非零退出故障注入；补充断言旧owner不执行成功后续标记、新owner heartbeat使fence从2增至3。
- GREEN: isolated local MySQL credentials injected from existing Docker configuration; python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_release_operation_lock_behavior.py scripts/tests/test_publish_release_lock_cleanup.py -q -> PASS, 31 passed in 36.56s, exit 0.
- REGRESSION: INTRUOYI_TEST_APP_BACKEND set to the task app backend; python -X utf8 -m pytest scripts/tests/test_release_preflight_r20_regressions.py scripts/tests/test_release_migration_supersession_contract.py scripts/tests/test_release_package_governance.py -q -> PASS, 113 passed in 52.57s, exit 0.
- cwd: D:/IntRuoyiWorktree/two-button-release-delivery-maintenance。MySQL用例均随机隔离库并finally清理；未SSH远程或改业务库。P1-AC2本地锁与命令合同通过；不表示真实服务器发布已完成。
- 长期门禁已合并本任务维护WT的既有docs/release-build-preflight-lessons.md与experience-index.md，包含Trigger/Preflight/Blocker/Verification/Forbidden/Evidence及checklist，UTF-8回读通过。
- P1仍等待应用状态P1-AC3，未进入P2、未提交或发布。
- REGRESSION: python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py scripts/tests/test_release_migration_preflight_matrix.py scripts/tests/test_release_schema_rehearsal.py scripts/tests/test_release_sql_preflight_gate.py -q -> PASS, 138 passed in 11.43s, exit 0；覆盖其余合入的维护基线改动。
- 维护实现已提交：772fc46（任务: 对齐发布基线并验证真实租约锁），包含已审R22基线合并与本次锁/测试/经验门禁；git diff --check通过，未推送、未改main或远端。本段前项“未提交”为当时状态。

## Outstanding Blockers

- BLOCKER: requested GPT-5.6 Luna development service -> HTTP 503 on three consecutive application-agent attempts; maintenance agent also HTTP 503. Model was not substituted. P2 remains unverified; P1 commits retained. See verification-report.md for concrete remaining review gaps and resume scope.
- Resource inspection: no process matching this task worktree/test markers and no listeners on reserved8208/48208 were found. No task server was started; no worktree deletion/integration or deployment was performed. P2 drafts remain in the task worktrees.

## Phase-P1-Application-Review
- 应用源：D:/IntRuoyiWorktree/two-button-release-delivery-app；与维护输入保持两个Git根、三个source role。
- BDD/RED/GREEN详见应用仓同名任务execution-log：初始74 tests中的2个业务失败证明retryable和guard证据缺口；新增RECOVERY_REQUIRED重复stale扫描用例曾6 tests中1 FAIL，修复后不再覆盖原始错误/阶段/证据。
- GREEN: mvn.cmd -B -pl yudao-module-infra -am '-Dtest=ReleaseWorkflow*,RuntimeControlServiceImplTest' '-Dsurefire.failIfNoSpecifiedTests=false' test -> PASS, 146 tests, 0 failure/error/skip, exit 0；主代理核对Surefire XML并审查正面blocked、错位绑定、正常派发窗口、未知失败、日志损坏和stale隔离。
- 应用Python基线：6个已合入测试文件86 PASS/1 FAIL；唯一失败为expected dict漏allowedPublishScopes，精确补齐字段后该完整文件8 PASS，未放宽生产校验。前端pnpm ts:check和原页面静态合同PASS。
- 应用实现提交d30f7ee02（任务: 对齐发布基线并隔离未知执行状态）；git diff --check与port guard PASS。历史SQL仅恢复批准Git字节，未产生其Git内容差异；任务文档因ignored规则用精确git add -f保留。
- P1-AC3主审通过；P1只解决基线/锁/状态，不代表两入口已实现或可发布。

### P1-AC2 maintenance lock SQL slice

- BDD: terminal lock reacquire -> Given an existing `FAILED` lock row and no active `RUNNING` row, When the production PowerShell `Invoke-ReleaseOperationLockAcquire` function emits SQL, Then the isolated MySQL database accepts the new operation with a fresh generated lease and `RUNNING` status.
- RED: `python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py::test_mysql_reacquire_terminal_row_refreshes_lease_and_reports_new_owner -q` -> FAIL, old SQL assignment order emitted `LOCK_HELD` for the terminal row because `status` was updated before lease/owner fields.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py -q` -> PASS, 4 passed; SQL was captured from the PowerShell function AST and executed against a random `release_lock_test_*` MySQL database.
- Evidence: test now reads `MYSQL_ROOT_PASSWORD` from the process environment, extracts the real function body with PowerShell AST, captures the generated heredoc SQL, and removes the temporary wrapper and isolated database in `finally`; no remote SSH was invoked.
- Remaining risk: the existing acquire pipeline still needs a dedicated non-zero SSH/MySQL carrier test to prove a success marker cannot mask command failure; this remains within P1-AC2 and is not claimed complete by this slice.

### P1-AC2 maintenance lock contract expansion

- RED: `python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py::test_acquire_transport_does_not_mask_mysql_exit_with_grep -q` -> FAIL while the production acquire carrier piped MySQL through `grep`.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py -q` -> PASS, 11 passed; acquire carrier now preserves the SSH/MySQL exit code, and a PowerShell function probe with `Ok=false`, exit 17, and success text throws before setting lock-held state.
- Coverage: actual generated SQL covers APPLIED and FAILED terminal rows, fresh lease/fence, active other-owner rejection with unchanged owner/fence, concurrent two-acquire one-winner behavior, old-owner write-fence rejection after actual reacquire, and MySQL nonzero after success text.
- Test input contract: `test_release_migration_supersession_contract.py` now requires absolute existing `INTRUOYI_TEST_APP_BACKEND` with no fallback. With `INTRUOYI_TEST_APP_BACKEND=D:\IntRuoyiWorktree\two-button-release-delivery-app\IntRuoyiBackend` and container password supplied only through the process environment, the targeted maintenance suite passed 43 tests.
- I/O guard: PowerShell and Docker/MySQL subprocesses use UTF-8, strict decoding, and 30-second timeouts; generated lease is returned as a tuple with the actual SQL. No SSH server or business database was contacted.
- Follow-up evidence: lock suite now passes 12 tests after adding local bash/container carrier injection: a command that prints `LOCK_ACQUIRED:<marker>` and exits 17 returns 0 through the old grep pipeline but returns 17 with pipefail/direct transport. The production acquire command no longer appends grep. The transport-failure probe now returns the actual generated random lease in `Ok=false` output and confirms `RELEASE_OPERATION_LOCK_ACQUIRE_FAILED` without setting lock-held.
- Final narrow follow-up: `python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py -q` -> PASS, 13 passed. A same-tag lifecycle now executes actual Acquire SQL twice in the isolated MySQL database (`fence=1`/`lease1`, then `fence=2`/`lease2`), runs the real PowerShell `Assert-ReleaseOperationLockOwnership` with SQL extracted from its heredoc against that database, rejects lease1 with `RELEASE_OPERATION_LOCK_LOST` and `LockHeld=false`, and renews heartbeat for lease2. The carrier test now captures the actual generated Acquire command, injects a local bash `docker` function that emits the success marker and returns 17, and proves old appended grep returns 0 while the actual new command returns 17 without pipefail.

### P2 maintenance input preparation RED/GREEN

- BDD: controlled input lifecycle -> Given two clean approved Git roots and a workflow-owned state directory, When `prepare-release-inputs` prepares inputs and `cleanup-release-inputs` runs after preparation, Then exactly maintenance/application worktrees are created from approved commits, dependency stamp/digests are recorded, and only those worktrees are removed with cleanup evidence.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_input_preparation.py -q` -> PASS, 2 passed; real temporary Git repositories and commits covered prepare/cleanup and source HEAD drift rejection.
- Implementation: added `ops/release/release_input_preparation.py` plus internal PowerShell modes and explicit workflow/source/state parameters. Preparation is local-only, uses Git worktree with LF settings, ownership/prepared/cleanup evidence, and requires the real frontend dependency stamp; cleanup validates prepared identity, clean worktrees, source Git registration, and controlled roots.
- P2 review correction: source repositories are allowed to contain unrelated dirty/advanced development state; preparation validates that the approved 40-character commit objects exist, then creates clean detached worktrees from those objects. It no longer requires source HEAD/dirty cleanliness. The fixture no longer commits a fake dependency stamp; the approved helper is invoked and missing generated stamp blocks preparation. Git/dependency deadlines are configurable (default 1800 seconds) rather than a 60-second checkout limit. The prior 2-test GREEN was only a controlled fixture contract and is not evidence of successful real dependency installation.
- P2 resume hardening: added BDD coverage for untrusted cleanup digest (`test_cleanup_requires_saved_preparation_digest`) and replay/approved-object blocking; `python -X utf8 -m pytest scripts/tests/test_release_input_preparation.py -q` -> PASS, 3 passed. Ownership is now acquired under the OS lock, prepared replay revalidates both exact controlled roots, approved HEADs, clean state, publish/lock/dependency digests, and cleanup requires `ExpectedPreparationDigest` before any deletion. Preparation writes atomic per-stage journal evidence (`STARTED`, `MAINTENANCE_CREATED`, `APPLICATION_CREATED`, `PREPARED`).
- Remaining blockers: a real successful dependency installation chain and fully streamed helper heartbeat were not claimed in this slice; the disposable helper fixture intentionally blocks because it does not produce a real stamp. Cleanup was not run against any actual developer source or R22 worktree.

- MAIN REVIEW: NOT ACCEPTED. 上述首段2 PASS只证明测试fixture的Git操作；fixture把手写dependency stamp提交进node_modules，代码当时未调用正式依赖helper，不能作为真实依赖准备证据。首段“仅clean源/HEAD相同”的前提也不符合批准Git对象隔离合同。清理尚缺完整双路径/HEAD/所有权/重入验证，不得按上述Implementation描述放行。已要求逐段修正prepare，再审cleanup；P2仍未完成，禁止在真实开发仓上调用草稿cleanup。


- None yet.

## Initialization
项目规则要求先写task.md；init_task.py拒绝已有目录，因此使用其相同task_lib初始化函数补齐五份核心文件，未修改技能或产品。前序规划completed。主代理独占task-state。

## Main review preflight
- 用户授权：GPT-5.6 Luna 子代理开发，主代理review和把控方向；现有两入口计划为实施合同。
- 当前维护基线：7230ddc81aff1a3b53d2ce02df226c57a4dc3c61；应用基线：f46b0bdc20d80ee7fa6e5d6b86898bcae0d0b357。两仓主工作区有无关并发改动，不暂存、不复制、不清理。
- 应用实际Git根为E:/IntRuoyi，前后端同仓；仅应用/维护两仓建立同名任务分支。
- 只读发现另一任务维护提交0e5d785added60ed742455c37efe3612fcf60ba3，父为R22批准提交2a867b9。其修复将锁UPSERT的status赋值移到最后。详细diff纠正初判：新增MySQL用例仍执行手写_acquire_sql副本，另有源码顺序断言，不能证明真实生产SQL；P1必须提取/调用真实生成SQL再复验，不修改原任务worktree。
- 静态审查待证实：verifyAdvance的retryable未依赖zeroWriteEvidence；dispatch异常边界和failed/blocked收束须验证真实副作用边界。未把静态发现记作RED。
- 规则优先级：用户当前明确要求仅提交任务产物，优先于外部task-closeout-rules中笼统的全脏工作区基线提交要求；本任务不得纳入他人修改。
- 预备环境：Docker真实MySQL 8.0.39容器存在；Java/Maven/Python/pwsh/Git可用。隔离数据库测试仅允许release_lock_test_任务随机库，不修改业务租户或服务器。
- 命令意图：只读查看规则、Git提交差异和状态机；没有执行构建、业务测试或远程写入。

## Baseline independent review
- GPT-5.6 Luna只读review：应用merge-base=489c637280771b9dacb250e41ef1202bac4ffe36，main侧9提交、R22侧10提交；维护merge-base=1ce47efe7e3e958524cca529ea22b47b478c0d33，main侧15提交、R22/锁修复侧8提交。
- 两仓双方修改文件集合无重叠，git merge-tree未报冲突。新worktree从各当前main创建，再普通merge批准提交；不从旧分支整树覆盖、不复制脏main。
- 预定本任务工作区：D:/IntRuoyiWorktree/two-button-release-delivery-app 与 D:/IntRuoyiWorktree/two-button-release-delivery-maintenance，分支均codex/two-button-release-delivery。只读确认路径和分支尚不存在。
- 应用端口必须通过reserve-worktree-slot.ps1分配，不占8081/48081，不触碰其他active entry。创建/合并前保持PRD审批门禁。
- GREEN: experience-preflight -> PASS（限本任务独立worktree创建、发布基线合入、隔离测试；已读worktree-memory/restrictions/端口协议、release-backup-restore、PowerShell/编码与任务收尾规则；不覆盖远程写入/E2E门禁）。
- 初轮规划review：结构字段和可执行测试合同需修订，重点补齐-am、真实SQL、派发异常、独立端口、BDD与真实浏览器命令；尚未批准进入开发。

## Blocked checkpoint
- 应用侧阻塞记录已单独提交2f789e604；P1产品实现仍为d30f7ee02，P2生产/测试草稿未提交。
- 中央规划/状态/审查记录结构校验通过；未启动最终独立tester，test_status保持not_started。
- 原blocked于用户明确要求Luna服务恢复后继续时解除；随后主代理复跑prepare窄测2 passed、intent窄测3 passed，进入P2主审，不能据此宣称P2完成。
- P2当前剩余：intent的FileLock未涵盖所有工作流写方法/API仍走旧startBuild；prepare部分失败恢复与cleanup安全证据未完成。继续保留两WT草稿，不运行真实cleanup、不发布。

## P2 intent/store review result
- 主代理审查通过意图/CAS窄切片：`d0824cc97`，验证命令 `mvn.cmd -B -pl yudao-module-infra -am '-Dtest=ReleaseWorkflow*,RuntimeControlServiceImplTest' '-Dsurefire.failIfNoSpecifiedTests=false' test` -> PASS, 151 tests, 0 failures/errors/skips。
- 覆盖：固定test目标、同键同载荷回读、同键异载荷冲突、不同键同源活动冲突、双Store并行回放、双Store同stateVersion CAS单赢家；所有主要Store写路径使用ReentrantLock+OS FileLock。
- 边界：controller仍调用旧startBuild，scheduler/prepare/cleanup未接入；P2不可标记完成。

## P2 source preparation review result
- 维护prepare/cleanup草稿已加入批准commit对象检查、detached LF worktree、workflow ownership、prepare-journal、prepared摘要复核和ExpectedPreparationDigest cleanup门槛；当前窄测试为2 passed，但没有真实依赖安装成功证据。
- 主代理不放行真实cleanup或发布；必须先补完整失败清理、路径/HEAD/摘要重验证、实时进度/退出码，再接入受控执行器。
