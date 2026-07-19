# 20260719 current HEAD code-only three-env release

## Task Goal

Execute an IntRuoyi code-only / no-data release from the current committed `int_main` HEADs of backend, frontend, and maintenance repositories through the full three-environment chain: `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`.

## Scope

- Release type: code-only / no data.
- Build flags: require `SkipDatabaseSync` and `SkipMinioSync`.
- Source input: only committed clean `int_main` HEAD content from:
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
  - `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance`
- Execution workspace: dedicated temporary release worktrees only.
- Explicit approval: production and backup promotion authorized with `ConfirmText=PROD`.
- Backup promotion must explicitly use `/mnt/intruoyi-data`.
- Excluded actions: no backup, restore, rollback, mock success, manual green marking, data sync, or data release.

## Milestones

- [x] Create task records and initial release behavior scenario.
- [x] Read and摘录 release preflight gates from the requested documents.
- [x] Record `GREEN: experience-preflight -> PASS` before high-risk actions.
- [x] Verify source repository `HEAD`, branch, and main-workspace dirty boundary.
- [x] Create dedicated backend and frontend temporary release worktrees and verify `HEAD`, branch, dirty=false.
- [x] Point runtime control to release worktrees and verify local health is `UP`.
- [x] Run `build-release` with code-only skip flags and capture a new `releaseTag`.
- [x] Validate build operation, manifest, source repos, and no-data package contents.
- [x] Run and verify `publish-test` on `172.30.30.58`.
- [x] Run and verify `mark-tested`.
- [x] Run and verify `promote-prod` with `ConfirmText=PROD` and `RequireTested`.
- [x] Run and verify `promote-backup` on `172.30.30.59` with explicit `/mnt/intruoyi-data`.
- [x] Restore runtime control main paths and verify local health is `UP`.
- [x] Remove this task's temporary release worktrees.
- [x] Run closeout cleanup preview/apply, mark completed, and commit only task-owned records.

## Expected Verification

- Same `releaseTag` completes all five operations with `SUCCESS`.
- Test, production, and backup environments verify `.env IMAGE_TAG`, backend/frontend actual image tags, backend health `UP`, frontend HTTP 200, and PDF worker HTTP 200.
- Backup additionally verifies `/mnt/intruoyi-data` mount and publish path correctness.
- Build manifest verifies `publishScope=code-only`, `sourceRepos dirty=false`, and no data directories in package.
- Runtime control is restored to main paths and reports health `UP`.
- Temporary release worktrees are deleted.
- `git diff --check`, UTF-8 checks, task-closeout preview/apply, and task-owned commit isolation pass.

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；按既有发布脚本、manifest、operation 和服务器真实运行态验证契约执行，不用临时绕过。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- Task-doc gate: task directory and minimal `task.md` / `execution-log.md` must exist before release actions; each milestone must append evidence and blockers.
- PowerShell / encoding gate: read UTF-8 explicitly, do not use `&&`, do not use Bash heredoc, judge native commands by exit code plus result assertion, send SSH scripts with LF/UTF-8-safe carrier, and never commit raw secret-bearing logs.
- Release input gate: backend, frontend, and maintenance release input is the committed `int_main` `HEAD`; uncommitted, untracked, or dirty main workspace content is excluded by fresh release worktrees and must not appear in manifest `sourceRepos`.
- Worktree gate: create this task's dedicated short-path release worktrees under `D:\ProjectPackage\Int\IntRuoyiWorktrees`, use short child names, verify `HEAD`, branch/detached state, and `dirty=false`; do not reuse old worktrees and do not delete before runtime-control paths are restored.
- Runtime-control gate: point `repo-root` and `frontend-root` to this release worktree before build, keep `state-dir` / logs / cache outside the release worktree, verify `http://127.0.0.1:48181/actuator/health=UP`, then re-check all release worktrees are clean.
- Code-only build gate: `build-release` must use `-Component intruoyi`, `SkipDatabaseSync`, `SkipMinioSync`, and explicit `TestServerHost=172.30.30.58`, `ProdServerHost=172.30.30.57`, `BackupServerHost=172.30.30.59`; build preview must not carry `targetEnvironment`.
- Dependency and contract gate: run current frozen script help for migration policy gate, run migration policy gate with supported parameters, restore business frontend dependencies by lockfile if missing, confirm Docker/base image preconditions without printing full env, and block on schema/required SQL contract failures.
- Manifest gate: validate release package root `manifest.json` as source of truth for `releaseTag`, `component`, `publishScope=code-only`, backend/frontend/maintenance source repos, `dirty=false`, artifact hashes, and absence of data directories such as `database`, `db-dump`, `mysql-dump`, `minio`, `files`, `runtime-data`, `data`, or `docker-build-context`.
- Deploy action gate: `publish-test`, `promote-prod`, and `promote-backup` reuse the built `releaseTag` and send only required deployment fields; deployment preview parsing must handle switch flags such as `RequireTested`, `SkipDatabaseSync`, and `SkipMinioSync`.
- Test gate: `publish-test` targets `172.30.30.58` and `/opt/intruoyi/runtime`; do not reuse old release conclusions, and verify operation `SUCCESS`, `.env IMAGE_TAG`, actual backend/frontend image tag, backend health `UP`, frontend HTTP 200, PDF worker HTTP 200, release-info, operation lock, and migration state.
- Mark-tested gate: run only after test-server verification; payload must not carry `targetEnvironment` and must include real `selectedRecoverySetCandidateId`; no manual tested-state edits.
- Production gate: `promote-prod` requires `ConfirmText=PROD` and `RequireTested`; preview must confirm target host and paths, then verify production operation `SUCCESS`, `.env IMAGE_TAG`, actual image tags, backend health `UP`, frontend HTTP 200, PDF worker HTTP 200, and release-info.
- Backup gate: `promote-backup` requires `ConfirmText=PROD`, `RequireTested`, `ServerHost=172.30.30.59`, `RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`, `RemoteDataRoot=/mnt/intruoyi-data/runtime-data`, `RemoteDataDiskMount=/mnt/intruoyi-data`, `RemoteDataDiskDevice=/dev/mapper/cl-home`, and `RemoteMinioContainer=intruoyi-minio`; verify mount and publish paths.
- DCC promote preflight gate: before `promote-prod`, run the required read-only DCC live data quality preflight for classification duplicates, missing classification codes, field length overflow, and missing required relationships; block instead of hand-fixing live data.
- Failure gate: on any failed build or publish, freeze operation JSON, operation log, preview parameters, manifest state, remote key output, and failure time; write reusable preflight experience before retrying, then fix the root cause and rebuild a new `releaseTag` unless evidence safely supports retrying the same step.
- Controlled content lifecycle gate: for `20260718_controlled_content_lifecycle.sql`, treat `dcc_controlled_file_master.status='OBSOLETE_CHAIN'` with no active revisions as a legitimate all-obsolete historical chain that the migration should skip; only non-obsolete masters pointing to missing/deleted/obsolete current files or ambiguous active candidates are blockers.
- Controlled content collation gate: any `controlled_content_version_ref.content_key` comparison with `CAST(<id> AS CHAR)` must explicitly use the target column collation, currently `utf8mb4_unicode_ci`; target DB default `utf8mb4_0900_ai_ci` must not leak into required SQL comparisons.
- MES companion contract gate: before `build-release`, the clean backend worktree must prove that MES implementation calls and VO/Mapper/Service contracts are committed together, covering `releaseActionLocked`, `workTaskId`, `batchRecordVersionNo`, `withdrawVoidBatchExecution`, and `updateApprovalFieldsToDraft`; then run `mvn.cmd -pl yudao-module-mes -am "-DskipTests" compile`.
- Frontend companion API gate: before `build-release`, the clean frontend worktree must prove page imports and `src/api` exports are committed together; `withdrawVoidBatchExecution` must be exported from `src/api/mes/pro/edhr/change.ts` and call `/mes/pro/edhr-change/void-batch-execution/withdraw`; then run `pnpm build:test`.
- Closeout gate: after release verification, mark `ready_for_closeout`, restore runtime-control to stable main paths, verify local health `UP`, delete only this task's worktrees and external state dir after Git registration and physical path checks, run task-closeout preview/apply, then mark `completed`.

## Current Status

completed - Release `release-20260719-intmain-codeonly-three-env-r260719k-r1` completed the full `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup` chain with all five operations `SUCCESS`. Test, production, and backup runtime verification passed; backup additionally verified `/mnt/intruoyi-data` mount and release/data paths. Runtime control has been restored to the main maintenance path, this task's temporary release worktrees/state directories have been deleted, task-closeout cleanup apply passed, and only task-owned records are prepared for the final maintenance-repo commit.

## Final Verification Result

- ReleaseTag: `release-20260719-intmain-codeonly-three-env-r260719k-r1`.
- Operations: build-release, publish-test, mark-tested, promote-prod, and promote-backup all `SUCCESS`.
- Runtime verification: test, production, and backup all passed `.env IMAGE_TAG`, backend/frontend image tag, backend health `UP`, frontend HTTP 200, PDF worker HTTP 200, and release-info checks.
- Backup verification: `/mnt/intruoyi-data` mounted from `/dev/mapper/cl-home`; release directory and runtime-data directory exist under `/mnt/intruoyi-data`.
- Closeout: runtime-control restored to the main maintenance path with health `UP`; task-owned release worktrees/state directories removed; task-closeout preview/apply passed with blocked=`<none>` and warnings=`<none>`.
