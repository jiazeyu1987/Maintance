# 20260715 current HEAD code-only three-env release

## Task Goal

Execute an IntRuoyi code-only release from the current committed `int_main` HEADs of backend, frontend, and maintenance repositories through the full three-environment chain: `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`.

## Scope

- Release type: code-only / no data.
- Build flags: require `SkipDatabaseSync` and `SkipMinioSync`.
- Source input: only committed clean HEAD content from:
  - `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`
  - `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance`
- Execution workspace: dedicated temporary release worktrees only.
- Explicit approval: production and backup promotion authorized with `ConfirmText=PROD`.
- Excluded actions: no backup, restore, rollback, mock success, manual green marking, or data release.

## Milestones

- [x] Create task records and release preflight gate summary.
- [x] Verify source repository HEAD, branch, and dirty=false inputs.
- [x] Create dedicated backend and frontend temporary release worktrees.
- [x] Point runtime control to release worktrees and verify local health is UP.
- [x] Run `build-release` with code-only skip flags and capture `releaseTag`.
- [x] Validate build operation, manifest, source repos, and no-data package contents.
- [x] Run and verify `publish-test` on `172.30.30.58`.
- [x] Run and verify `mark-tested`.
- [x] Run and verify `promote-prod` with `ConfirmText=PROD` and `RequireTested`.
- [x] Run and verify `promote-backup` on `172.30.30.59` with `/mnt/intruoyi-data`.
- [x] Restore runtime control main paths and verify local health is UP.
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
- `是否从根因和长期维护角度解决`：是；本任务按既有发布脚本、manifest 和服务器验证契约执行，不用临时绕过。
- `是否存在临时补丁或绕过`：否。

## 经验门禁

- Task-doc gate: task directory and minimal `task.md` / `execution-log.md` must exist before release actions; each milestone must append evidence and blockers.
- PowerShell / encoding gate: all Chinese or structured release evidence must use explicit UTF-8 reads/writes; no `&&`, no Bash heredoc, and no raw secret-bearing logs in committed records.
- Release input gate: backend, frontend, and maintenance inputs must be committed `int_main` HEADs; uncommitted, untracked, or dirty content must not enter the package.
- Worktree gate: create this task's dedicated short-path release worktrees, verify `HEAD`, branch, and `dirty=false`; do not reuse old worktrees and delete them only after runtime-control paths are restored.
- Runtime-control gate: `config/runtime-control.local.yaml` must point `repo-root` and `frontend-root` to this release worktree before build, keep `state-dir` outside the release worktree, and `http://127.0.0.1:48181/actuator/health` must be `UP`.
- Code-only build gate: `build-release` must use `-Component intruoyi`, `SkipDatabaseSync`, `SkipMinioSync`, and all three host parameters; build preview must not carry `targetEnvironment`.
- Manifest gate: validate Manifest v1 and legacy manifest by their own schema; `manifest.json` is the source of truth for `publishScope=code-only`, backend/frontend commits, `dirty=false`, and no Website/package-data directories.
- SQL/data gate: `code-only` skips data and MinIO sync only; schema/required SQL metadata still must pass, and `type=data` required SQL must not execute during code-only publish.
- Deploy action gate: `publish-test`, `promote-prod`, and `promote-backup` pass `targetEnvironment` and `releaseTag`, not `publishScope`; preview parsing must handle switch flags such as `RequireTested`, `SkipDatabaseSync`, and `SkipMinioSync`.
- Test gate: `publish-test` targets `172.30.30.58` and `/opt/intruoyi/runtime`; success requires operation `SUCCESS`, `.env IMAGE_TAG`, actual backend/frontend image tag, backend health `UP`, frontend HTTP 200, PDF worker HTTP 200, release-info, and manifest source repo verification.
- Mark-tested gate: run only after test-server verification; `mark-tested` must not carry `targetEnvironment` and must include the required recovery-set candidate fields from the release package candidates.
- Production gate: `promote-prod` requires `ConfirmText=PROD` and `RequireTested`; success requires production `.env IMAGE_TAG`, actual image tags, backend health `UP`, frontend HTTP 200, and PDF worker HTTP 200.
- Backup gate: `promote-backup` requires `ConfirmText=PROD`, `RequireTested`, explicit `/mnt/intruoyi-data` remote data mount parameters, and backup verification of mount correctness plus runtime health/HTTP/image checks.
- Failure gate: on any failed build or publish, freeze operation JSON, operation log, preview parameters, manifest state, remote key output, and failure time before fixing; add reusable preflight experience before retrying or rebuilding a new `releaseTag`.
- Closeout gate: after release verification, mark `ready_for_closeout`, restore main runtime-control paths, verify local health `UP`, delete only this task's worktrees, run task-closeout preview/apply, then mark completed and commit only task-owned records.

## Current Status

completed - `release-20260715-intmain-codeonly-three-env-r260715w-r1` completed the full code-only chain `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`; all five operations are `SUCCESS`. Test, production, and backup servers independently verify `.env IMAGE_TAG`, backend/frontend image tags, backend health `UP`, frontend HTTP `200`, and PDF worker HTTP `200`; backup additionally verifies `/mnt/intruoyi-data` mount plus release/data paths. Runtime-control has been restored to the main workspace and reports health `UP`; task-owned `r260715v` / `r260715w` release worktrees are absent from Git registrations and physical worktree roots; task-closeout preview/apply passed with no delete, blocked, or warning items.

## Release Result

- ReleaseTag: `release-20260715-intmain-codeonly-three-env-r260715w-r1`
- Build operation: `op-2026-07-14T165644637047400Z-6a9ac983-7cf6-4874-99ca-1f120e2b2047` = `SUCCESS`
- Publish-test operation: `op-2026-07-14T171101441161400Z-3ce7c6d8-1dcc-49c9-aaa8-ca98bd35e318` = `SUCCESS`
- Mark-tested operation: `op-2026-07-14T173039483650500Z-c55bbe7e-4fd4-48cd-bca6-864397c535cb` = `SUCCESS`
- Promote-prod operation: `op-2026-07-14T173414012244200Z-be4dccfd-ba21-4511-9833-6ab3f07a136c` = `SUCCESS`
- Promote-backup operation: `op-2026-07-15T004326358968100Z-0f5e222a-a4b0-43d6-ba36-2cc3d08dc540` = `SUCCESS`
- Source commits in `manifest.json`: backend `a33743cd059b0de18f647466941603adabec8c3e`, frontend `9a59dd50ff67e66573ecca7ffcd957b4fe15686a`, both `dirty=false`.
- Release package: `publishScope=code-only`, component `intruoyi`, no blocked data directories (`database`, `db-dump`, `mysql-dump`, `minio`, `files`, `runtime-data`, `data`, `docker-build-context`, `website`, `package-data`).
- Runtime-control restore: main workspace jar `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`, health `UP`.
- Closeout: `git worktree list` in maintenance/backend/frontend repos contains no `r260715v` or `r260715w` entries; `D:\ProjectPackage\Int\IntRuoyiWorktrees` contains no matching physical directories; task-closeout preview/apply returned `blocked=<none>` and `warnings=<none>`.
