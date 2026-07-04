# 20260704-codeonly-three-env-release execution log

## BDD

BDD: code-only release package integrity -> Given 本轮发布输入为三个仓库当前 `int_main` 已提交 HEAD；When 在专用干净临时发布 worktree 中执行 code-only build-release；Then manifest 必须记录 `publishScope=code-only`、sourceRepos dirty=false，且发布包不包含数据目录。

BDD: test environment verification gate -> Given 测试服 `172.30.30.58` 已按同一 releaseTag 发布；When 验证 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP、PDF worker HTTP；Then 全部必须通过后才能 mark-tested。

BDD: production promotion gate -> Given releaseTag 已 mark-tested；When 使用 `ConfirmText=PROD` 和 `RequireTested` promote-prod；Then 正式服 `.env IMAGE_TAG`、镜像 tag、backend health、frontend HTTP、PDF worker HTTP 全部必须通过。

BDD: backup environment data mount verification -> Given 正式服验证通过；When 使用 `/mnt/intruoyi-data` 参数 promote-backup 到 `172.30.30.59`；Then 备份服 `.env IMAGE_TAG`、镜像 tag、backend health、frontend HTTP、PDF worker HTTP、数据盘挂载和发布路径全部必须通过。

## Initial state - 2026-07-04 23:44:12 +08:00

- Previous task check: `20260703-codeonly-three-env-release` is Completed.
- Maintenance repo: branch `int_main`, commit `3df8d5a96920f8fd9bb7ec7362499bb52940e55d`, dirty=true.
- Backend repo: branch `int_main`, commit `ddd93f9089b510c323417d0aee91708099448ebf`, dirty=false.
- Frontend repo: branch `int_main`, commit `cc2cef81e11220a6ba50b8931dfca5811a368401`, dirty=false.
- Release input rule: only committed HEAD content from dedicated clean release worktrees may enter the package.

## Preflight

- Read: `docs/experience-index.md`.
- Read: `docs/release-build-preflight-lessons.md`.
- Read: `docs/release-agent-checklist.md`.
- Read: `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`.
- Read: `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`.
- Read: `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`.
- Applicable gates: dedicated clean release worktrees; `SkipDatabaseSync` and `SkipMinioSync`; manifest `publishScope=code-only`; sourceRepos branch/commit/dirty=false; no data directories in package; same releaseTag for all five operations; real server runtime verification; backup publish uses `/mnt/intruoyi-data`; runtime-control restored to main path before cleanup.

GREEN: experience-preflight -> PASS, required release/worktree/server documents read and applicable gates recorded before worktree creation, server writes, publish actions, or cleanup.

## Release worktree creation - 2026-07-04 23:54:10 +08:00

GREEN: release-worktree-create -> PASS, created clean detached worktrees from planned committed HEADs.

| repo | worktree | commit | branch | dirty |
| --- | --- | --- | --- | --- |
| maintenance | `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release\IntRuoyiMaintance` | `3df8d5a96920f8fd9bb7ec7362499bb52940e55d` | `HEAD` | false before local config copy; local config copy is gitignored |
| backend | `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release\ruoyi-vue-pro` | `ddd93f9089b510c323417d0aee91708099448ebf` | `HEAD` | false |
| frontend | `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release\yudao-ui-admin-vue3` | `cc2cef81e11220a6ba50b8931dfca5811a368401` | `HEAD` | false |

Runtime config copied into maintenance release worktree and points repo-root/frontend-root/ops-root/state-dir to this release worktree set.

## Runtime control worktree build failure - 2026-07-04 23:56:00 +08:00

BLOCKER: runtime-control-worktree-build -> `scripts/build.ps1` failed before producing the maintenance jar because `pnpm install --frozen-lockfile` reported `ERR_PNPM_IGNORED_BUILDS` for `esbuild@0.27.7` and `vue-demi@0.14.10`; `pnpm approve-builds --all` had returned "There are no packages awaiting approval".

- Impact: release runtime control cannot be started from the clean maintenance worktree yet; build-release/publish-test/promote steps have not started.
- stdout evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260704-codeonly-three-env-release\evidence\runtime-control-worktree-build.out.log`
- stderr evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260704-codeonly-three-env-release\evidence\runtime-control-worktree-build.err.log`
- Required handling: freeze evidence, add reusable preflight lesson, then repair the missing frontend dependency approval precondition and rebuild.

## Runtime control worktree build retry - 2026-07-04 23:59:25 +08:00

GREEN: runtime-control-worktree-build -> PASS, corrected temporary `frontend/pnpm-workspace.yaml` approval state to `allowBuilds.esbuild=true` and `allowBuilds.vue-demi=true`, verified `pnpm install --frozen-lockfile`, then rebuilt the maintenance runtime control from the release worktree.

- frontend install: PASS, `esbuild` and `vue-demi` postinstall scripts executed.
- frontend build: PASS, `frontend/dist/index.html` generated.
- Maven tests: PASS, 26 tests run, 0 failures, 0 errors, 0 skipped.
- jar: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`
- stdout evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260704-codeonly-three-env-release\evidence\runtime-control-worktree-build-retry1.out.log`
- stderr evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260704-codeonly-three-env-release\evidence\runtime-control-worktree-build-retry1.err.log`

## Runtime control worktree start - 2026-07-05 00:04:30 +08:00

GREEN: runtime-control-worktree-start -> PASS, stopped the prior main-workspace runtime-control process on 48181, started the release worktree jar, and verified `http://127.0.0.1:48181/actuator/health` returns `{"status":"UP"}`.

- listener PID: `10544`
- command line: `java -jar D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`
- verification evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260704-codeonly-three-env-release\evidence\runtime-control-worktree-start-verification.json`
- note: release runtime worktree has only untracked local runtime artifacts (`frontend/pnpm-workspace.yaml`, `runtime/`); backend/frontend source package inputs remain dedicated detached worktrees recorded above.

## Build preflight - 2026-07-05 00:07:34 +08:00

GREEN: maintenance-release-script-tests -> PASS, `python -X utf8 -m pytest scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py scripts\tests\test_release_sql_preflight_gate.py` ran 17 tests, all passed.

BLOCKER: backend-migration-policy-gate -> `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` failed before build-release because migration `20260704_showroom_product_target_market_text` declares `dependsOn=20260519_showroom_v1_schema`, but no migration with that id exists in `sql\mysql`.

- Impact: build-release is blocked before package creation; no releaseTag has been generated.
- Failure evidence: `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260704-codeonly-three-env-release\evidence\migration-policy-gate-failure-20260705.json`
- Required handling: freeze evidence, add reusable preflight lesson, then repair the SQL release-migration metadata at the source and rerun RED/GREEN verification.

## 2026-07-05 00:17:58 +08:00 后端迁移依赖修复同步
- 后端主仓已提交根因修复：933de66d093e4c78dadddf6c56400160cbceb1fb。
- 发布后端临时 worktree 已切换到该修复提交；git status --porcelain=v1 结果为空表示 dirty=false。
- 前端发布 worktree 保持提交：cc2cef81e11220a6ba50b8931dfca5811a368401；git status --porcelain=v1 结果为空表示 dirty=false。
- 未触碰后端主仓现存无关改动：yudao-module-mes/.../MesProBatchRecordJingxiTableStructureVerificationTest.java。
GREEN: migration-policy-gate -> PASS, backend release worktree commit 933de66d093e4c78dadddf6c56400160cbceb1fb, sql-root=sql/mysql.
GREEN: maintenance-release-script-tests -> PASS, 17 pytest cases passed from release maintenance worktree.

## 2026-07-05 00:31:55 +08:00 build-release 追踪补录
- 继续使用已提交 operation，未重新生成 releaseTag。
- releaseTag: release-20260705-001827-codeonly-three-env
- operationId: op-2026-07-04T161827593170700Z-e0cfce0a-4529-4e34-aeb3-974546d7e83f
- operation evidence: evidence/build-release-operation.json
- operation log: evidence/build-release-operation.log
- package/status evidence: evidence/build-release-packages.json, evidence/build-release-status.json
GREEN: build-release -> PASS, operation=SUCCESS, releaseTag=release-20260705-001827-codeonly-three-env.

## 2026-07-05 00:33:06 +08:00 build-release manifest/package validation invalid attempt
- INVALID: this validation attempt used JSON files written with UTF-8 BOM and the Python reader opened them as utf-8, causing JSONDecodeError before validation completed.
- Impact: the prior PASS marker is void and superseded by the rerun below; no publish-test action was started from this invalid validation.

## 2026-07-05 00:37:41 +08:00 build manifest validation blocker freeze
- BLOCKER: build-manifest-package-validation-final -> FAIL, evidence/build-release-manifest-validation-final.json reports frontend commit missing from release-manifest.json.
- Freeze evidence before publish-test: package path, release-manifest.json, manifest.json, runtime operation JSON/log, release package/status snapshots.
- No publish-test/promote action has been executed after this validation failure.

## 2026-07-05 00:38:18 +08:00 build-release manifest contract validation
- experience updated: docs/release-build-preflight-lessons.md and docs/experience-index.md record that sourceRepos must be validated from package manifest.json.
- evidence: evidence/build-release-manifest-contract-validation.json
- manifest.json releaseTag/publishScope/sourceRepos commit/dirty=false checks passed.
- release-manifest.json publishScope compatibility check passed.
- data-directory scan passed; no database/db-dump/mysql-dump/minio/files/runtime-data/data/docker-build-context entries detected.
GREEN: build-manifest-contract-validation -> PASS.

## 2026-07-05 00:39:06 +08:00 publish-test preview blocker freeze
- BLOCKER: publish-test-preview -> FAIL before action execution; preview checks did not find releaseTag/test host/deploy mode/code-only markers in response.
- Frozen evidence: evidence/publish-test-preview.json. No publish-test operation was started by this failed preview gate.

## 2026-07-05 02:11:06 +08:00 publish-test operation status correction
- The previous polling script parsed composite status output and timed out after the operation had reached SUCCESS; no second publish-test was started.
- operationId: op-2026-07-04T164018694312200Z-1e1d3d80-0ef0-4e9b-94eb-825f27ef09e5
- evidence: evidence/publish-test-status-inspection.json; evidence/publish-test-operation.json; evidence/publish-test-operation.log
GREEN: publish-test -> PASS, operation=SUCCESS, releaseTag=release-20260705-001827-codeonly-three-env.

## 2026-07-05 02:13:15 +08:00 test verification local script correction
- INVALID: prior test verification attempt used a PowerShell double-quoted here-string, so remote shell substitutions like $(grep ...) were evaluated locally before SSH and failed. No remote verification write/deploy action was executed by that failed attempt.
- Correction: use a single-quoted here-string so the verification script runs only on 172.30.30.58.

## 2026-07-05 02:13:21 +08:00 test server verification
- evidence: evidence/test-server-verification-final.txt
- .env IMAGE_TAG=release-20260705-001827-codeonly-three-env confirmed on 172.30.30.58.
- backend/frontend actual container image tags match release-20260705-001827-codeonly-three-env.
- backend health=UP; frontend HTTP 200; PDF worker HTTP 200.
GREEN: test-server-verification -> PASS.

## 2026-07-05 02:15:37 +08:00 mark-tested
- releaseTag: release-20260705-001827-codeonly-three-env
- operationId: op-2026-07-04T181516637071500Z-3171b8c3-c937-4cfc-aafe-d7a7d9ebf9e6
- selectedRecoverySetCandidateId: restore:20260621-063218
- recoverySetId: 20260621-063218
- recoverySetManifestHash: 6806edb9075622a5dbe646e2a1dca1ea499472cc610e070161b68f7249aecf66
- preview evidence: evidence/mark-tested-preview.json
- operation evidence: evidence/mark-tested-operation.json
- operation log: evidence/mark-tested-operation.log
- release status evidence: evidence/release-status-after-mark-tested.json
GREEN: mark-tested -> PASS, operation=SUCCESS, releaseTag=release-20260705-001827-codeonly-three-env.

## 2026-07-05 02:29:24 +08:00 promote-prod
- releaseTag: release-20260705-001827-codeonly-three-env
- operationId: op-2026-07-04T181652100023900Z-d8241796-3fe2-4592-bf13-b042def4b797
- preview evidence: evidence/promote-prod-preview.json
- operation evidence: evidence/promote-prod-operation.json
- operation log: evidence/promote-prod-operation.log
- preview confirmed: -Mode deploy-release, -Environment prod, -ConfirmText PROD, -RequireTested.
GREEN: promote-prod -> PASS, operation=SUCCESS, releaseTag=release-20260705-001827-codeonly-three-env.

## 2026-07-05 02:30:15 +08:00 prod server verification
- evidence: evidence/prod-server-verification-final.txt
- prodHost: 172.30.30.57
- .env IMAGE_TAG=release-20260705-001827-codeonly-three-env confirmed.
- backend/frontend actual container image tags match release-20260705-001827-codeonly-three-env.
- backend health=UP; frontend HTTP 200; PDF worker HTTP 200.
GREEN: prod-server-verification -> PASS.

## 2026-07-05 02:46:53 +08:00 promote-backup
- releaseTag: release-20260705-001827-codeonly-three-env
- operationId: op-2026-07-04T183107725619Z-343fbd72-c548-4a66-898b-8017f7557a3f
- preview evidence: evidence/promote-backup-preview.json
- operation evidence: evidence/promote-backup-operation.json
- operation log: evidence/promote-backup-operation.log
- preview confirmed: -Mode deploy-release, -Environment backup, -ConfirmText PROD, -RequireTested, host 172.30.30.59, RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases, RemoteDataRoot=/mnt/intruoyi-data/runtime-data, RemoteDataDiskMount=/mnt/intruoyi-data, RemoteDataDiskDevice=/dev/mapper/cl-home, RemoteMinioContainer=intruoyi-minio.
GREEN: promote-backup -> PASS, operation=SUCCESS, releaseTag=release-20260705-001827-codeonly-three-env.

## 2026-07-05 02:47:27 +08:00 backup server verification
- evidence: evidence/backup-server-verification-final.txt
- backupHost: 172.30.30.59
- .env IMAGE_TAG=release-20260705-001827-codeonly-three-env confirmed.
- backend/frontend actual container image tags match release-20260705-001827-codeonly-three-env.
- backend health=UP; frontend HTTP 200; PDF worker HTTP 200.
- /mnt/intruoyi-data mounted from /dev/mapper/cl-home; release root and runtime-data paths are on the protected data disk; release directory exists.
GREEN: backup-server-verification -> PASS.

## 2026-07-05 02:48:11 +08:00 final release-loop operation summary
- evidence: evidence/final-release-loop-summary.json
- releaseTag: release-20260705-001827-codeonly-three-env
- operations SUCCESS: build-release, publish-test, mark-release-tested, promote-prod, promote-backup.
- release package status confirms tested metadata present before runtime restore.
GREEN: final-release-loop-operation-summary -> PASS.

## 2026-07-05 02:49:32 +08:00 runtime-control main restore
- Stopped release worktree runtime-control process on 48181 when command line pointed to this release worktree.
- Started main maintenance runtime-control from D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\start.ps1.
- health: UP; listener PID: 43044; command line points to main maintenance jar and not release worktree.
- evidence: evidence/runtime-control-main-restore-verification.json; stdout/stderr logs captured.
GREEN: runtime-control-main-restore -> PASS.

## 2026-07-05 02:51:32 +08:00 release worktree cleanup retry
- Previous cleanup preview completed, but git worktree remove left non-git residual directories because untracked local runtime/build artifacts were present under the dedicated release worktree root.
- Safety gate: only paths under D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release will be inspected and removed; unrelated 20260701 release worktrees remain untouched.

## 2026-07-05 02:52:12 +08:00 release worktree long-path cleanup retry
- Previous residual cleanup failed on pnpm/node_modules long-path entries under the dedicated release worktree root.
- Safety gate: resolve and verify exact root before deletion; only delete D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release.

## 2026-07-05 02:52:50 +08:00 release worktree node_modules cleanup retry
- Previous Python rmtree cleanup failed because pnpm/node_modules left non-empty long-path/link directories.
- Safety gate: exact release root is resolved before removal; cleanup remains scoped to D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release only.

## 2026-07-05 02:54:31 +08:00 release worktree cleanup verification
- Removed residual pnpm/node_modules long-path artifacts using an empty-directory mirror after exact path verification.
- Pruned worktree metadata for maintenance/backend/frontend repos.
- Verified D:\ProjectPackage\Int\IntRuoyiWorktrees\20260704-codeonly-three-env-release no longer exists and no repo worktree list contains this release root.
- evidence: evidence/worktree-removal-verification.json
GREEN: release-worktree-cleanup -> PASS.

## 2026-07-05 02:55:15 +0800 task completion
- releaseTag: release-20260705-001827-codeonly-three-env
- 五个 operation 均为 SUCCESS，三环境验证全部 PASS。
- 本机运行控制台已恢复主路径并 health=UP。
- 本轮临时 release worktree 已删除并完成元数据 prune。
GREEN: task-completion -> PASS.
