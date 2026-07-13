# Execution Log - 20260713 当前 HEAD code-only 三环境发布 r260713v

## Initial Request

- User requested full IntRuoyi code-only three-environment release loop from current committed `int_main` HEADs of maintenance, backend, and frontend repositories.
- Required chain: `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`.
- Required build flags: `SkipDatabaseSync` and `SkipMinioSync`.
- Authorized production and backup promotion confirmation: `PROD`.
- Forbidden: data sync, backup, restore, rollback, mock success, manual green status, mixing releaseTags, using dirty or untracked workspace content in the release package.

## BDD

- BDD: clean committed release input -> Given 三个主工作区可能存在未提交或未跟踪内容, When 本轮发布开始, Then 发布包只能来自本轮冻结的 `int_main` HEAD 干净 worktree。
- BDD: code-only publish scope -> Given 用户要求 code-only 且不带数据, When 执行 build-release, Then 必须使用 `SkipDatabaseSync` 与 `SkipMinioSync` 且 Manifest `publishScope=code-only`。
- BDD: three-environment release chain -> Given 测试服验证通过, When 执行发布闭环, Then 同一 releaseTag 必须完成 test、mark-tested、prod、backup 且三环境运行态一致。
- BDD: backup data disk verification -> Given 发布到备份服, When 验证完成标准, Then 必须证明 `/mnt/intruoyi-data` 挂载和发布路径正确。

## Evidence

- 2026-07-13: Created task directory `doc/tasks/20260713-current-head-codeonly-three-env-r260713v/`.
- RED: experience-preflight -> PENDING, release preflight gates not yet extracted.
- 2026-07-13: Read required preflight sources: `docs/experience-index.md`, `docs/release-build-preflight-lessons.md`, `docs/release-agent-checklist.md`, `D:/ProjectPackage/Int/IntRuoyi/docs/release-backup-restore.md`, `D:/ProjectPackage/Int/IntRuoyi/docs/server-access.md`, `D:/ProjectPackage/Int/IntRuoyi/docs/worktree-memory.md`, `D:/ProjectPackage/Int/IntRuoyi/docs/powershell-memory.md`, `docs/powershell-preflight-lessons.md`, and `docs/test-release-preflight.md`.
- GREEN: experience-preflight -> PASS, applicable gates extracted into `task.md` before release worktree creation, server write, build-release, publish-test, promote-prod, promote-backup, and closeout.
- GREEN: release-worktree-freeze -> PASS, created clean detached release worktrees at `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713v/m|b|f`; commits maintenance=`872a17bc5d2f01cf3b6d4bc4b53f3605ffc9309a`, backend=`a69271e228c7738cd0ade0e12f9b7f8a85aec205`, frontend=`69df78f24279d4f144fa252230f6571202409bf7`; dirty=false for all.
- GREEN: maintenance-runtime-control -> PASS, built maintenance console tests/package, created external config/state outside release worktree, started PID `28668`, and verified `http://127.0.0.1:48181/actuator/health` status=`UP`.
- GREEN: migration-policy-gate -> PASS, frozen backend script accepted `--output`; status=`passed`, migrationCount=`281`; evidence `migration-policy-gate-r260713v.json`.
- RED: frontend-esbuild-probe -> FAIL, extra `pnpm exec esbuild --version` probe returned command not found because esbuild is not exposed as a top-level command in this pnpm structure; no release action occurred.
- GREEN: frontend-dependency-gate -> PASS, `corepack pnpm@10.25.0 install --frozen-lockfile` completed, `cross-env.cmd` found, `pnpm exec vite --version` passed, frontend worktree dirty=false.
- GREEN: build-release-preview -> PASS, preview includes `-Component intruoyi`, `-SkipDatabaseSync`, `-SkipMinioSync`, test/prod/backup hosts, and r260713v backend/frontend worktree roots.
- GREEN: build-release -> PASS, operation `op-2026-07-13T143350577788200Z-3d861300-83a9-4b8a-a453-96b7ae54e225` completed `SUCCESS` for `release-20260713-intmain-codeonly-three-env-r260713v-r1`.
- GREEN: manifest-validation -> PASS, Manifest v1 is present, `publishScope=code-only`, sourceRepos match frozen backend/frontend commits with dirty=false, 295 artifact hashes pass, and forbidden data directories are absent.
- GREEN: publish-test-preview -> PASS, preview action=`publish-test`, mode=`deploy-release`, environment=`test`, `ServerHost=172.30.30.58`, `RemoteAppDir=/opt/intruoyi/runtime`, and no mark-tested/prod/backup action.
- GREEN: publish-test-remote-preflight -> PASS, SSH to `172.30.30.58` succeeded, target host/app dir confirmed, `infra_release_operation_lock` schema uses `update_time`, and `running_lock_count=0`; OpenSSH printed `IO is still pending` with exit code 0 and was treated as collection noise per PowerShell/SSH gate.
- GREEN: publish-test -> PASS, operation `op-2026-07-13T145223142838Z-f31e7309-5106-4c25-ac53-5ddbf4efefa3` completed `SUCCESS`.
- GREEN: test-runtime-verification -> PASS, test server `.env IMAGE_TAG`, backend/frontend images, backend health, frontend HTTP, PDF worker HTTP, release-info commits, release lock, target migration failure count and running lock check all passed for `release-20260713-intmain-codeonly-three-env-r260713v-r1`.
- GREEN: mark-tested-preview -> PASS, selected recovery candidate `restore:20260621-063218`, preview mode=`mark-tested`, no `targetEnvironment`, and `SelectedRecoverySetCandidateId` present.
- GREEN: mark-tested -> PASS, operation `op-2026-07-13T150911502243700Z-029f98c3-29d6-4104-9f34-d36bfe281ea1` completed `SUCCESS`.
- GREEN: promote-prod-preview -> PASS, preview environment=`prod`, `ConfirmText=PROD`, `RequireTested` present, `ServerHost=172.30.30.57`, and `RemoteAppDir=/opt/intruoyi/runtime`.
- GREEN: promote-prod -> PASS, operation `op-2026-07-13T151108922995700Z-109cd33a-e66b-4297-b73d-9ea4d6f2f488` completed `SUCCESS`.
- GREEN: prod-runtime-verification -> PASS, prod `.env IMAGE_TAG`, backend/frontend images, backend health, frontend HTTP, PDF worker HTTP, release-info commits, release lock, target migration failure count and running lock check all passed.
- GREEN: promote-backup-preview -> PASS, preview environment=`backup`, `ConfirmText=PROD`, `RequireTested` present, `ServerHost=172.30.30.59`, `RemoteReleaseRoot=/mnt/intruoyi-data/intruoyi-releases`, `RemoteDataRoot=/mnt/intruoyi-data/runtime-data`, `RemoteDataDiskMount=/mnt/intruoyi-data`, `RemoteDataDiskDevice=/dev/mapper/cl-home`, and `RemoteMinioContainer=intruoyi-minio`.
- GREEN: promote-backup -> PASS, operation `op-2026-07-13T152649835481600Z-c8a04317-1b9d-4ed7-8b43-61002803e87c` completed `SUCCESS`.
- RED: backup-runtime-verification-python3 -> FAIL, first backup verification carrier used remote `python3`, which is not installed; SSH exited before runtime assertions, no release or server write was performed by the verification script.
- GREEN: backup-runtime-verification -> PASS, rewritten pure shell verification passed backup `.env IMAGE_TAG`, backend/frontend images, backend health, frontend HTTP, PDF worker HTTP, release-info commits, release lock, target migration failure count, running lock check, `/mnt/intruoyi-data` mount on `/dev/mapper/cl-home`, release directory, and data root.
- GREEN: runtime-control-main-restore -> PASS, restored local 48181 to main workspace jar; health=`UP`; command line points to `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`.
- RED: git-worktree-remove-maintenance -> FAIL, `git worktree remove --force D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713v\m` removed Git registration but left a physical directory with `Directory not empty`; no unrelated path was touched.
- RED: git-worktree-remove-frontend -> FAIL, `git worktree remove --force D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713v\f` removed Git registration but left a physical directory with `Directory not empty`; no unrelated path was touched.
- GREEN: release-worktree-cleanup -> PASS, after confirming no `r260713v` Git registrations and no process command line references, deleted fixed residual paths under `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713v` and `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260713v-state`; final root/state exists=false.
- GREEN: task-closeout-preview -> PASS, keep set contained `task.md`, `execution-log.md`, and `verification-report.md`; blocked=<none>, warnings=<none>.
- GREEN: task-closeout-apply -> PASS, deleted temporary JSON evidence files, kept core task records, blocked=<none>, warnings=<none>.
