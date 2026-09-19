# Execution Log

## Scope

用户授权选择第 2 项：仅执行真实测试服发布链路 `build-release -> publish-test`，并验证测试服运行态；不得执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## BDD Scenarios

BDD: only test server release scope -> Given the user authorizes option 2 only, When the release is executed, Then the workflow must stop after `publish-test` and must not call `mark-tested`, `promote-prod`, `promote-backup`, prod, or backup targets.

BDD: clean immutable package to test server -> Given maintenance/app main workspaces may contain dirty or conflicted changes, When a release package is built, Then the package must be produced from this task's clean release worktrees at frozen committed HEADs and manifest `sourceRepos[*].dirty` must be false.

BDD: test runtime proves deployment -> Given `publish-test` reports success, When completion is evaluated, Then operation status, package manifest, remote `.env IMAGE_TAG`, actual backend/frontend image tags, container state, backend health, frontend HTTP, release-info, release lock, migration state, and Playwright page evidence must all match the same releaseTag.

## TDD / Gate Evidence

GREEN: experience-preflight -> PASS, read `docs/experience-index.md`, `docs/test-release-preflight.md`, `docs/release-build-preflight-lessons.md`, `docs/powershell-preflight-lessons.md`, `E:\IntRuoyi\docs\powershell-memory.md`, `E:\IntRuoyi\docs\release-backup-restore.md`, `E:\IntRuoyi\docs\server-access.md`, `E:\IntRuoyi\docs\login-access.md`, and `E:\IntRuoyi\docs\worktree-memory.md`; this task is authorized only for test server `172.30.30.58`.

GREEN: release-worktree-freeze -> PASS, created task-owned worktrees `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908a\m` at maintenance HEAD `bd4a05fa82263814cbf2828e86183f9413aa28b1` and `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908a\a` at app HEAD `de455c7ecf3b12e8ac74d61a173149274d910fc5`; both worktrees reported `## HEAD (no branch)` with no dirty paths.

RED: python -X utf8 ops\release\run-release-migration-policy-gate.py --sql-root D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908a\a\IntRuoyiBackend\sql\mysql --file-prefix sql/mysql --output D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\test-server-release-20260908\ops-migration-policy-gate.json -> FAIL, expected all executable SQL files to declare release metadata; actual error `missing release-migration metadata: D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908a\a\IntRuoyiBackend\sql\mysql\20260903_mes_process_pool_device_selection_mode.sql`.

BLOCKER: build-release -> not executed because migration policy gate failed before package creation. No NAS upload, no Docker build, no SSH publish, and no test server write occurred.

GREEN: release-worktree-cleanup -> PASS, ran `git worktree remove` for `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908a\m` and app worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908a\a`; final `Test-Path` for both paths returned `False`, and both repository worktree lists contain no `r260908a` entry.

## Preflight Snapshot

- Maintenance target HEAD: `bd4a05fa82263814cbf2828e86183f9413aa28b1`.
- App target HEAD: `de455c7ecf3b12e8ac74d61a173149274d910fc5`.
- Maintenance main workspace has unrelated dirty/untracked files; they are excluded from release input by using a task-specific worktree.
- App main workspace has unrelated dirty/untracked files and unresolved conflict markers in tracked status; they are excluded from release input by using a task-specific worktree at committed HEAD.

## Current Status

in_progress

## Attempt r260908c-r1

GREEN: user-release-source-authorization -> PASS, user explicitly authorized using verified app commit `b88c242f0` as the release source for test server publish.

GREEN: experience-preflight-refresh -> PASS, re-read CI/CD delivery skill, release/backup/restore, server access, login access, worktree memory, maintenance experience index, test release preflight, build preflight lessons, and PowerShell preflight lessons; scope remains test server only.

GREEN: release-worktree-freeze-r260908c -> PASS, created task-owned release worktrees `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\m` at maintenance commit `bd4a05fa82263814cbf2828e86183f9413aa28b1` and `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c\a` at app commit `b88c242f0aa3030f387695b500b3fb6e85fa54d8`; both are detached and clean.

GREEN: migration-policy-gate-r260908c-r1 -> PASS, maintenance and app migration policy gates both reported `status=passed`, `migrationCount=605`.

BLOCKER: build-release-r260908c-r1 -> FAIL before build/upload/server write, `Missing -BackupServerHost; release target host for environment 'backup' must be configured and passed explicitly so package URLs and storage checks are bound to the selected publish target.` No package was created and no remote operation occurred. Per no-reuse rule, continuing with new releaseTag `release-20260908-verified-branch-r260908c-r2`.

BLOCKER: build-release-r260908c-r2 -> FAIL before package completion and before test server publish, frontend dependency binary missing: `IntRuoyiFronted\node_modules\.bin\cross-env.cmd`. The clean release worktree has no installed frontend dependencies. Per no-reuse rule, continuing with new releaseTag `release-20260908-verified-branch-r260908c-r3` after running the repository dependency preparation script.

GREEN: frontend-dependencies-r260908c -> PASS, direct `pnpm install --frozen-lockfile`, `pnpm rebuild --pending`, `pnpm ignored-builds`, and repository `scripts\prepare-frontend-dependencies.ps1` completed; required binaries `cross-env.cmd`, `vite.cmd`, and `vue-tsc.cmd` exist and dependency stamp was written in the release worktree only.

BLOCKER: build-release-r260908c-r3 -> FAIL before package completion and before test server publish, target-state SSH command argument hit remote bash syntax error during migration ledger collection.

RED: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py -q -> FAIL, new test `test_build_preflight_target_state_collection_streams_remote_script_over_ssh_stdin` expected `bash -s` + SSH stdin for target-state collection.

GREEN: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py -q --basetemp <task-basetemp> -> PASS, `43 passed`; maintenance release script now streams the remote target-state script via SSH stdin and avoids non-stdin `docker exec` consuming the script.

GREEN: maintenance-release-script-fix -> PASS, committed maintenance fix `67ab5cf` on branch `codex/test-release-target-state-stdin-20260908`; subsequent build attempts use this committed script source.

BLOCKER: build-release-r260908c-r5 -> FAIL before package completion and before test server publish, `release_build_preflight.py` reported `status=blocked` because `publishScope=code-only` excludes required data/menu/permission dependency paths; summary: `APPLY=36`, `BLOCKED_SCOPE_DEPENDENCY=12`, `SKIP_ALREADY_APPLIED=497`, `SKIP_ENV_NOT_ALLOWED=1`, `SKIP_SCOPE_EXCLUDED=60`. Per no-reuse rule, continuing with with-data releaseTag `release-20260908-verified-branch-r260908c-r6`.

BLOCKER: build-release-r260908c-r6 -> FAIL before package completion and before test server publish, Docker image identity collection passed `--format '{{json .}}'` through `Start-Process`, and Docker returned `template parsing error: template: :1: unclosed action`. No test server write occurred. Per no-reuse rule, continuing only after a tested maintenance-script fix.

RED: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py::test_docker_image_identity_reads_raw_json_without_go_template_format -q --basetemp <task-basetemp> -> FAIL, `Get-DockerImageIdentity` still used Docker Go template format.

GREEN: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py::test_docker_image_identity_reads_raw_json_without_go_template_format -q --basetemp <task-basetemp> -> PASS, `Get-DockerImageIdentity` now reads raw `docker image inspect` JSON and parses the first image record.

GREEN: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py -q --basetemp <task-basetemp> -> PASS, `44 passed`.

GREEN: maintenance-release-script-fix-docker-identity -> PASS, committed maintenance fix `467f750` on branch `codex/test-release-target-state-stdin-20260908`.

BLOCKER: build-release-r260908c-r7 -> FAIL before package completion and before test server publish, with-data package export required MinIO client image but the script used bare `minio/mc:latest`; local cache missed and Docker Hub pull failed with TLS handshake timeout. No test server write occurred. Per no-reuse rule, continuing only after a tested maintenance-script fix and fixed tool image availability.

RED: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py::test_publish_script_uses_configured_minio_client_image -q --basetemp <task-basetemp> -> FAIL, publish script did not expose `$MinioClientImage` and still contained bare `minio/mc` runtime calls.

GREEN: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py::test_publish_script_uses_configured_minio_client_image -q --basetemp <task-basetemp> -> PASS, publish script now defaults `$MinioClientImage` to `quay.io/minio/mc:latest` and uses it for MinIO export/sync.

GREEN: python -X utf8 -m pytest scripts\tests\test_release_build_preflight_cache.py -q --basetemp <task-basetemp> -> PASS, `45 passed`.

GREEN: maintenance-release-script-fix-minio-client -> PASS, committed maintenance fix `8bd1481` on branch `codex/test-release-target-state-stdin-20260908`; `docker pull quay.io/minio/mc:latest` succeeded with digest `sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727`.

BLOCKER: build-release-r260908c-r8 -> FAIL before package completion and before test server publish, with-data package DCC object inventory detected local data/object drift: `DCC_OBJECT_SNAPSHOT_MISSING: DCC file id=9198354891791 object=dcc/original/20260611/empty.docx is missing from release MinIO snapshot.` Read-only DB check confirmed `infra_file.id=9198354891791`, `config_id=28`, `path=dcc/original/20260611/empty.docx`, `deleted=0`; read-only MinIO container path check found no matching object under `/data/yudao`. No test server write occurred.

GREEN: user-authorized-dcc-object-restore -> PASS, user authorized continuing from the blocked state. Restored the missing local MinIO object from historical release snapshot `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-121500-e2e\minio\yudao\dcc\original\20260611\empty.docx` to `docker-minio-1:/data/yudao/dcc/original/20260611/empty.docx`; verified size `3306` and SHA256 `fd9160a87bcbe94570d998499f1b1ed9b39f381fde1688c2ed2b0b0a6d562bf2`. No database rows were changed.

BLOCKER: build-release-r260908c-r9 -> FAIL before package completion and before test server publish. Backend Maven build, frontend `pnpm build:test`, Docker backend/frontend image builds, and docker image export completed, but MySQL dump failed with `SHOW CREATE PROCEDURE intruoyi_fix_esign_subject_id_capacity` returning `PROCEDURE ... does not exist (1305)`. No `publish-test` was executed and no test server write occurred.

GREEN: full-mysqldump-precheck-after-r9 -> PASS, a direct full `mysqldump --single-transaction --routines --triggers --hex-blob --default-character-set=utf8mb4 --databases ruoyi-vue-pro` inside `int-ruoyi-mysql` completed with exit code `0` and output size `13385341675` bytes; only the standard password-on-command-line warning appeared. Continue with a fresh releaseTag because failed releaseTags are not reused.

BLOCKER: build-release-r260908c-r10 -> FAIL before package completion and before test server publish. MySQL dump completed and MinIO mirror transferred `3.14 GiB`, but DCC object inventory still reported `DCC_OBJECT_SNAPSHOT_MISSING` for `dcc/original/20260611/empty.docx`. Root cause: the first restore wrote the file directly under `/data`, which `mc mirror` did not expose as a valid MinIO object.

GREEN: dcc-object-restore-via-minio-api -> PASS, restored the same historical snapshot object using MinIO/S3 API credentials from `infra_file_config.id=28`; `mc stat local/yudao/dcc/original/20260611/empty.docx` returned object name, size `3.2 KiB`, ETag `e02bf390e42e9c22f046918fcd724a16`, and DOCX content type. No database rows were changed.

## Attempt r260908c-r12

GREEN: user-authorization-refresh -> PASS, user explicitly replied `授权`; scope remains test server only and continues from verified app commit `b88c242f0aa3030f387695b500b3fb6e85fa54d8`.

GREEN: build-release-r260908c-r12-partial -> PASS until DCC inventory, using releaseTag `release-20260908-verified-branch-r260908c-r12`: migration policy gate passed, eDHR protected storage gate passed, build preflight target-state passed, backend Maven `BUILD SUCCESS`, frontend `pnpm build:test` succeeded, backend/frontend Docker images built and exported, MySQL dump completed, MinIO yudao mirror completed `3.14 GiB`.

BLOCKER: build-release-r260908c-r12 -> FAIL before manifest completion and before test server publish. DCC object inventory failed on `DCC_OBJECT_SNAPSHOT_MISSING: DCC file id=9198354894835 object=dcc/original/20260614/QMS文件清单.xlsx is missing from release MinIO snapshot.` No `publish-test` was executed and no test server write occurred.

GREEN: dcc-object-restore-qms-via-minio-api -> PASS, restored `dcc/original/20260614/QMS文件清单.xlsx` from historical release snapshot `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-121500-e2e\minio\yudao\dcc\original\20260614\QMS文件清单.xlsx` to local MinIO `yudao/dcc/original/20260614/QMS文件清单.xlsx`; source size `233712`, SHA256 `d21e3cdc752d299d82d06a3b3f4ec89be633db82515c1b147cb12d081b768e92`; `mc stat` returned object name, size `228 KiB`, ETag `493afd27b735d777c452d7f9cbc044c4`, and XLSX content type. No database rows were changed.

BLOCKER: dcc-batch-object-preflight -> FOUND SYSTEMIC LOCAL DATA/OBJECT DRIFT. A batch comparison of the r12 MinIO snapshot plus the newly restored QMS object against the same DCC reference query used by `publish-int-ruoyi.ps1` found `17870` missing referenced objects out of `17897` DCC file references. `17528` missing objects are present in the `release-20260616-121500-e2e` historical snapshot, while `342` were not covered by that snapshot. Largest groups: `dcc/original/20260615` = `16593`, `dcc/original/20260614` = `935`, `dcc/original/20260617` = `215`, `dcc/original/20260720` = `45`, `dcc/original/20260717` = `30`. Continuing to `publish-test` would publish broken DCC file references, so the release remains blocked before server write.

## 2026-09-09 Resume After Authorization

GREEN: user-authorization-refresh-20260909 -> PASS, user replied `授权`; scope remains test server only and data repair boundary remains restoring real historical objects without deleting or rewriting database business references.

GREEN: dcc-reference-export-current -> PASS, exported `17897` DCC file references using the same source tables and columns as `publish-int-ruoyi.ps1`; evidence: `doc/tasks/test-server-release-20260908/dcc-reference-rows-current.jsonl`.

GREEN: dcc-historical-object-restore-20260616 -> PASS, restored or confirmed `17529` objects from `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-121500-e2e\minio\yudao` into local MinIO `yudao`; existing objects were skipped and not overwritten. No database rows were changed and no test server write occurred.

GREEN: dcc-historical-object-source-search -> PASS, scanned local historical release snapshots containing `minio\yudao`; found `216` candidate rows beyond the 20260616 snapshot and `128` rows without a historical snapshot source; evidence: `dcc-missing-found-in-other-snapshots.jsonl` and `dcc-missing-not-found-in-snapshots.jsonl`.

GREEN: dcc-historical-object-restore-other-snapshots -> PASS, restored `215` additional objects from `release-20260701-1720-mes-scheduler-dcc-inventory-fast`; one candidate was already covered by the full-bucket check. No database rows were changed and no test server write occurred.

GREEN: dcc-full-bucket-object-preflight-after-restores -> PASS/BLOCKED, full local MinIO `yudao` bucket comparison reduced missing DCC references to `128`; evidence: `dcc-missing-current-after-restores-allbucket.jsonl`.

GREEN: dcc-infra-file-content-probe -> PASS/BLOCKED, read-only `infra_file_content` coverage check for the remaining `126` nonblank object paths returned `content_rows=0`, `content_bytes=0`; the missing objects cannot be restored from the local DB content table.

BLOCKER: dcc-object-consistency-after-restores -> FAIL before `publish-test`. Remaining missing DCC references: `128` total (`126` nonblank object paths plus `2` blank paths). Continuing would publish broken DCC file links to the test server. Per no-fallback/no-mock policy, do not bypass the gate, do not create placeholder files, and do not modify DCC database references without a separate explicit data repair decision.

## 2026-09-09 Authorized Invalid Reference Cleanup

BDD: remove invalid DCC file references -> Given DCC rows reference `infra_file` paths that have no object in local MinIO, no historical source snapshot, and no `infra_file_content` content, When the user explicitly authorizes deleting invalid references, Then nullable file-id columns are cleared and required-reference records are soft-deleted with backup evidence.

BDD: package gate remains strict -> Given invalid DCC references were repaired locally, When release packaging runs again, Then DCC object inventory must pass from real data and must not be bypassed by placeholder objects or skipped validation.

BDD: test server stays untouched until package is valid -> Given the repair is local data cleanup, When the DCC gate is still failing, Then `publish-test` must not run and no test server state may be changed.

RED: dcc-full-bucket-object-preflight-after-restores -> FAIL/BLOCKED, `128` DCC references remained unresolved and the packaging gate correctly blocked before `publish-test`.

GREEN: dcc-invalid-reference-cleanup -> PASS, after user authorization the invalid DCC file references were repaired locally using `dcc-invalid-reference-cleanup-20260909.sql`; backup evidence is `dcc-invalid-reference-cleanup-backup-20260909.json`, rollback evidence is `dcc-invalid-reference-cleanup-rollback-20260909.sql`, and no test server/prod/backup database was modified.

GREEN: dcc-object-consistency-after-cleanup -> PASS, current release-reference export has `17760` rows, `14016` unique object paths, `0` blank object paths; current local MinIO `yudao` inventory comparison found `missing_paths=0`. Evidence: `dcc-current-reference-query.tsv`, `dcc-current-object-paths.txt`, `dcc-yudao-current-inventory.jsonl`, `dcc-current-missing-paths-after-cleanup.txt`.

BLOCKER: build-release-r260908c-r13 -> INCOMPLETE, local package directory and manifest were generated, DCC inventory passed (`17760` refs), but the process ended before `Release package uploaded to NAS` / `Release package built` evidence and NAS candidate `\\172.30.30.4\IT共享\Backup\ReleasePackage\release-20260909-verified-branch-r260908c-r13` did not exist. Per no-reuse rule, do not deploy r13; continue with fresh releaseTag `release-20260909-verified-branch-r260908c-r14`.

## 2026-09-10 r14 NAS Resume

GREEN: build-release-r260908c-r14-local-package -> PASS/PARTIAL, using releaseTag `release-20260909-verified-branch-r260908c-r14`; backend Maven build, frontend `pnpm build:test`, Docker backend/frontend image build/export, MySQL dump, MinIO mirror, DCC object inventory (`17760/17760`), `manifest.json`, and `release-manifest.json` were generated from app commit `b88c242f0aa3030f387695b500b3fb6e85fa54d8`.

BLOCKER: build-release-r260908c-r14-nas-copy -> FAIL after local package creation and before `publish-test`; `Copy-Item` failed while copying the release package to NAS with `An unexpected network error occurred.` No test server, prod, backup, or review server publish was executed by this failed command.

GREEN: nas-robocopy-resume-r14 -> PASS, resumed only the task-owned NAS package path `\\172.30.30.4\IT共享\Backup\ReleasePackage\release-20260909-verified-branch-r260908c-r14` from local package `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260909-verified-branch-r260908c-r14` using robocopy `/E /Z /MT:16 /R:3 /W:5`; robocopy ended with code `1`, `FAILED=0`, `Mismatch=0`, `Files total=20579`, `Copied=17160`, `Skipped=3419`, `Bytes total=38.071 g`.

## 2026-09-10 NAS Copy-Item Resumable Transfer Fix

BLOCKER: deploy-release-test-r14-copyitem-download -> FAIL before test server mutation; first corrected `deploy-release -Environment test` run failed while downloading the NAS package back to local cache because `Copy-Item` hit `An unexpected network error occurred.` No SSH deploy, container restart, database import, or test server write occurred.

BDD: resumable NAS package transfer -> Given large release packages include database dumps, image tar, and MinIO objects, When build-release uploads to NAS or deploy-release downloads from NAS, Then the script must use resumable robocopy directory transfer, fail on robocopy exit code `>=8`, compare source/destination file count and bytes, and only then run `Test-ReleasePackageIntegrity`.

RED: python -X utf8 -m pytest scripts\tests\test_release_package_governance.py::test_nas_package_transfer_uses_resumable_robocopy_for_upload_and_download scripts\tests\test_release_package_governance.py::test_same_verifier_guards_all_four_package_lifecycle_points -q --basetemp <task-basetemp> -> FAIL, `Copy-ReleasePackageDirectory` did not exist and NAS package upload/download still used `Copy-Item`.

GREEN: python -X utf8 -m pytest scripts\tests\test_release_package_governance.py::test_nas_package_transfer_uses_resumable_robocopy_for_upload_and_download scripts\tests\test_release_package_governance.py::test_same_verifier_guards_all_four_package_lifecycle_points -q --basetemp <task-basetemp> -> PASS, `2 passed`; NAS upload/download now call resumable robocopy helper before package integrity verification.

GREEN: python -X utf8 -m pytest scripts\tests\test_release_package_governance.py -q --basetemp <task-basetemp> -> PASS, `58 passed`.

GREEN: maintenance-release-script-fix-nas-resume-preserve -> PASS, commit `3ce452e`; NAS 下载恢复时保留本地半包并续传，不再先删除已下载文件。

GREEN: maintenance-release-script-fix-nas-postcopy-fast -> PASS, commit `2da1cc4`; robocopy 成功后不再跨 NAS 递归统计全部文件和字节，避免复制完成后的二次长时间遍历。

GREEN: package-integrity-linear-list -> PASS, commit `3f79f59`; 包完整性产物集合改为线性追加，聚焦测试 `4 passed`。

GREEN: package-integrity-no-double-hash -> PASS, commit `4d314bf`; immutable artifact 收集不再重复计算载荷哈希，完整治理回归 `60 passed in 36.98s`。

## 2026-09-10 Abort With-Data And Switch To Lightweight Package

BDD: routine full application release is code-only by default -> Given an operator builds the complete IntRuoyi frontend and backend without asking for a data snapshot, When `build-release` resolves its publish scope, Then the manifest is `code-only` and no MySQL dump, MinIO snapshot, or DCC object inventory is produced.

BDD: with-data requires explicit intent -> Given full database and MinIO synchronization can overwrite target runtime data, When an operator requests `with-data`, Then the command must explicitly select `with-data` and provide the required confirmation; conflicting skip flags must fail before external actions.

BDD: deploy consumes immutable package scope -> Given a lightweight package has been built and stored on NAS, When it is deployed to test, Then deploy derives `code-only` from the package manifest, applies only allowed required SQL, and does not reset MySQL or synchronize MinIO.

GREEN: abort-with-data-r14 -> PASS, exact task-owned process PID `61812` was terminated after command-line and child-process verification; no SSH/SCP/Docker child process was active.

GREEN: test-server-unchanged-after-abort -> PASS, test server `.env IMAGE_TAG`, backend image and frontend image all remain `release-20260903-main-invoice-assistant-test-r260903b-r1`.

GREEN: experience-preflight-lightweight-release -> PASS, reviewed release build, immutable package, code-only required SQL, server, PowerShell, worktree and test-only release gates before changing the script or writing the test server.

RED: python -X utf8 -m pytest scripts\tests\test_release_package_governance.py::test_runtime_console_emits_explicit_publish_scope_for_build_release scripts\tests\test_release_package_governance.py::test_build_release_defaults_to_code_only_and_requires_explicit_with_data_confirm -q --basetemp <task-basetemp> -> FAIL as expected, the release script had no `PublishScope` parameter and runtime-control still emitted `-SkipDatabaseSync/-SkipMinioSync`.

GREEN: publish-scope-contract-focused -> PASS, `3 passed`; `build-release` now defaults `PublishScope=code-only`, runtime-control emits explicit scope, and `with-data` requires `-ConfirmText WITH-DATA`.

GREEN: publish-scope-contract-regression -> PASS, package governance plus build-preflight cache regression `106 passed in 44.84s`; PowerShell AST and `git diff --check` passed.

RED: mvn -f backend\pom.xml test -> FAIL as expected after the argument-contract change, one existing preview assertion still required the removed skip switches; production preview already emitted `-PublishScope code-only`.

GREEN: mvn -f backend\pom.xml test -> PASS, `26` tests, `0` failures; code-only preview asserts explicit scope and with-data preview asserts `-ConfirmText WITH-DATA`.

GREEN: maintenance-release-script-lightweight-default -> PASS, implementation commit `763ff8701c1571bd269f865fa647c89bb82ad480` in maintenance release worktree.

BLOCKER: build-release-codeonly-r15 -> FAIL FAST before Maven/Docker/NAS/server write, fresh test target-state collection `b8f440f3-a41c-40a4-99f7-46ea2c2f7dfa` produced `APPLY=36`, `SKIP_ALREADY_APPLIED=497`, `SKIP_SCOPE_EXCLUDED=60`, `BLOCKED_SCOPE_DEPENDENCY=12`; legacy `code-only` excludes pending type=data migrations that are declared dependencies of later schema/menu/permission migrations.

BDD: daily application package separates snapshots from migrations -> Given a routine full application release needs versioned required SQL but must preserve target business data and object storage, When `build-release` uses the default `app-release` scope, Then it includes and plans required incremental migrations while excluding MySQL dump, MinIO snapshot and DCC object inventory.

BDD: strict code-only remains available -> Given an operator explicitly selects `code-only`, When pending type=data migrations or their dependency chain exists, Then those migrations remain excluded or blocked exactly as before; the new daily default must not silently weaken the existing code-only contract.

BDD: immutable app-release promotes across environments -> Given an `app-release` package passed test deployment, When the same package is later considered for prod or backup, Then package governance accepts the scope while existing tested attestation, approval and environment gates remain mandatory.

RED: app-release-contract-focused -> FAIL as expected, `7 failed, 6 passed`; script, package governance, preflight planner and runtime-control UI did not yet recognize `app-release`.

GREEN: app-release-contract-regression -> PASS, package governance/build preflight/runtime frontend tests `113 passed in 47.51s`; the planner applies versioned type=data dependencies for `app-release` while legacy `code-only` behavior remains covered.

GREEN: app-release-maintenance-backend -> PASS, `mvn -f backend\pom.xml test` completed `26` tests with `0` failures.

BLOCKER: app-release-maintenance-frontend-prerequisite -> initial `pnpm typecheck` and `pnpm build` failed because the task release worktree had no `frontend/node_modules`; no test was skipped and no fallback was used.

GREEN: app-release-maintenance-frontend -> PASS after `pnpm install --frozen-lockfile`; `pnpm typecheck` passed and `pnpm build` completed `1419` transformed modules.

GREEN: cicd-validator-self-test -> PASS, CI/CD environment validator self-test passed.

GREEN: maintenance-app-release-contract -> PASS, implementation commit `80cfd6d` adds `app-release` across script, preflight planner, package governance, restore planner, runtime-control backend/frontend and tests.

GREEN: build-release-app-r16-preflight-and-build -> PASS/PARTIAL, fresh target-state collection `39ad3545-0f31-411c-9a98-9e8149cba7fe` passed app-release preflight; backend Maven build succeeded in `02:34`, frontend build succeeded, backend/frontend images built and docker save completed. No MySQL dump, MinIO export, DCC inventory, NAS upload or test-server write occurred.

BLOCKER: build-release-app-r16-manifest -> FAIL before NAS/server write, `Get-ReleaseComponentArtifactHash` received an empty artifact sha256 because commit `4d314bf` removed hashing from `Get-ReleasePackageImmutableArtifactEntries`, although `Write-ReleaseManifest` requires those hashes.

BDD: manifest hashes once and later boundaries reverify -> Given a release package payload is complete, When manifest generation runs, Then each immutable payload file is hashed exactly once and cached for the immediate local integrity check; NAS copy and deploy download must still independently recompute hashes.

RED: package-integrity-no-double-hash contract audit -> FAIL by real r16 build, the previous static test incorrectly required the manifest artifact collector not to hash at all and therefore allowed blank manifest hashes.

GREEN: manifest-hash-cache-focused -> PASS, `3 passed`; manifest generation computes real payload SHA-256, immediate local integrity reuses the same-process preverified artifacts, and NAS/deploy lifecycle points retain independent verification.

GREEN: manifest-hash-cache-regression -> PASS, release governance/build preflight/runtime frontend regression `113 passed in 46.29s`; `git diff --check` passed.

GREEN: maintenance-manifest-first-hash-fix -> PASS, implementation commit `2dab1c4`.

GREEN: build-release-app-r17 -> PASS, releaseTag `release-20260910-verified-branch-app-r260908c-r17`; target-state preflight passed, backend Maven `BUILD SUCCESS` in `02:53`, frontend build passed, Docker images built/exported, manifest and package integrity passed, resumable NAS upload completed.

GREEN: r17-lightweight-manifest -> PASS, package `684.73 MiB`, `616` files, `615` immutable artifacts with nonblank SHA-256; `publishScope=app-release`, `component=intruoyi`, backend/frontend commits both `b88c242f0aa3030f387695b500b3fb6e85fa54d8`, dirty count `0`, forbidden MySQL dump/MinIO/DCC inventory count `0`.

BLOCKER: deploy-release-test-r17-migration-ledger-gap -> FAIL after package/image upload and before application container switch, migration `20260629_mes_smart_scheduling_role_scope` failed with `Missing MES smart scheduling role-scope menu baseline`; operation lock released as FAILED.

GREEN: r17-migration-gap-readonly-diagnosis -> PASS, test server has 18/20 required enabled menu rows; 900121/900122 are intentionally disabled/deleted. Ledger shows 20260617 and 20260624 prerequisites `SKIPPED_ALREADY_APPLIED`, 20260709 route unification `SKIPPED_ALREADY_APPLIED`, 20260728 successor `APPLIED`, but 20260629 predecessor `FAILED`, proving historical dependency closure is inconsistent.

GREEN: r17-failure-runtime-stabilization -> PASS, actual backend/frontend containers remained on `release-20260903-main-invoice-assistant-test-r260903b-r1`; remote `.env IMAGE_TAG` was restored to that exact actual image tag after verifying both containers. No MySQL full replacement or MinIO sync occurred.

GREEN: user-authorized-migration-source-fix -> PASS, user authorized deriving a new main-program migration fix commit from `b88c242f0`; scope is limited to the incompatible historical migration and regression tests, followed by a fresh app-release package.

GREEN: migration-topology-fix-tdd -> PASS, source branch `codex/test-release-migration-chain-fix-20260910`; focused SQL tests RED `2 failed, 24 passed`, GREEN `26 passed`; combined migration regression `38 passed`.

GREEN: migration-topology-mysql-integration -> PASS, legacy and official replacement topology fixtures each ran twice successfully; incomplete replacement topology failed with expected MySQL 1644; exact temporary schemas were removed and verification count was `0`.

GREEN: migration-topology-policy-gate -> PASS, migration policy `status=passed`, `migrationCount=605`; the fix never updates `system_menu`, never reactivates 900121/900122, and maps the replacement topology to 5726/5727.

BLOCKER: app-fix-commit-runtime-profile -> FAIL, app pre-commit hook rejected the legacy release worktree path outside `D:\IntRuoyiWorktree`; no hook bypass was used. Moving the task app worktree to `D:\IntRuoyiWorktree\r260908c-app` and registering an `int_main` slot is required before commit.

GREEN: app-worktree-compliance -> PASS, app worktree moved to `D:\IntRuoyiWorktree\r260908c-app`, registered `int_main slot 38` (`8213/48213`), branch runtime guard passed, and no branch service was started.

GREEN: app-migration-fix-commit -> PASS, source commit `0684dbd06` derived from `b88c242f0`; scoped files are the historical role-scope migration and its regression test only.

BLOCKER: build-release-app-r18-frontend-link -> FAIL after backend build and before Docker/NAS/server write, moved app worktree retained stale pnpm junctions whose targets referenced the old path; `cross-env.cmd` existed but Node failed to load `cross-env/src/bin/cross-env.js`. The existing preflight checked wrapper-file existence only and produced a false pass before the 03:16 backend build.

BDD: frontend dependency preflight resolves real modules -> Given a moved or restored worktree contains stale node_modules wrappers/junctions, When build-release runs its cheap frontend preflight, Then Node must resolve cross-env, vite and vue-tsc from the actual frontend directory before Maven starts; wrapper existence alone must not pass.

RED: frontend-module-resolution-preflight -> FAIL, focused test showed `require.resolve` was absent; direct Node resolution in the moved frontend reproduced `Cannot find module 'cross-env'` before dependency repair.

GREEN: frontend-module-resolution-preflight -> PASS, release SQL/preflight regression plus PowerShell AST `55 passed in 1.26s`; script now resolves cross-env, vite and vue-tsc from the actual worktree before Maven.

GREEN: moved-frontend-dependency-repair -> PASS, `pnpm install --frozen-lockfile --force` rebuilt stale junctions at the new path, project Corepack pnpm `10.25.0` ran `rebuild --pending`, both direct/Corepack `ignored-builds` returned `None`, Node resolved all three modules, and `pnpm build:test` passed.

BLOCKER: build-release-app-r19-inline-js -> FAIL FAST before Maven/Docker/NAS/server write, Node received only `for` from the inline `-e` script because PowerShell `Start-Process ArgumentList` split the script; the new dependency gate correctly blocked but its carrier was invalid.

RED: frontend-resolver-file-contract -> FAIL, focused test required checked-in `ops/release/frontend_dependency_preflight.cjs` and the publish script reference; neither existed.

GREEN: frontend-resolver-file-contract -> PASS, fixed Node runner resolved cross-env/vite/vue-tsc from the actual frontend cwd and emitted structured PASS; release preflight plus PowerShell AST `55 passed`.

GREEN: maintenance-frontend-resolver-commit -> PASS, commit `35b7ba7` adds the fixed CJS runner and removes fragile inline JavaScript transport.

GREEN: build-release-app-r20-preflight -> PASS, actual frontend dependency resolver and ignored-builds checks passed before backend Maven; the existing r20 process continued into backend build and no duplicate build was started after command-output truncation.

GREEN: build-release-app-r20 -> PASS, local and NAS package integrity independently matched manifest digest `sha256:6e498c8905c82a3878419fab0c884bf68ac8e234ea8653ec273d8556837c11de` and package digest `sha256:abdb84aedf2202bb9964ba4a266f092e17c829235d57f7066c5b64d04d36fe81`; package `684.71 MiB`, 616 files, source commit `0684dbd06`, dirty=0, forbidden data artifacts=0.

BLOCKER: deploy-release-test-r20-rt000006 -> FAIL after `20260629` passed and before application container switch; `20260709_mes_rt000006_batch_record_mapping` raised `Missing RT000006 pressure pump route` because the environment-specific route id 922067 is absent. Operation lock released FAILED; remote `.env IMAGE_TAG` restored to the actual old container tag; no full database or MinIO sync occurred.

BDD: environment-specific data migration applicability -> Given RT000006 route 922067 is absent, When its versioned mapping migration runs, Then it must explicitly exit as not applicable with zero writes; if route id exists with mismatched identity or route exists with missing roles/reports, it must still fail fast.

RED: rt000006-applicability-contract -> FAIL, focused test `3 failed, 2 passed`; applicability branch was absent and two legacy assertions referenced retired route-use table names.

GREEN: rt000006-applicability-contract -> PASS, focused `5 passed`; isolated MySQL absent-route fixture passed twice with zero writes, active identity mismatch failed as expected, and temporary schema count returned `0` after cleanup.

GREEN: rt000006-migration-regression -> PASS, combined migration tests `43 passed in 3.16s`, full migration policy `status=passed`, `migrationCount=605`, and `git diff --check` passed.

BLOCKER: deploy-release-test-r21-route-00002-cleanup -> FAIL after six additional migrations applied and before application container switch; fixed-scope test-only migration `20260716_mes_balloon_xlsx_route_00002_invalid_process_cleanup` found no active B320 process at sort 26 and raised target mismatch. Read-only target evidence: route `ROUTE-XLSX-00002` has 26 active processes, sort 26 is Z2620, and no B320 route-process exists. Lock released FAILED and `.env IMAGE_TAG` restored to actual old containers.

BDD: route-00002 cleanup applicability -> Given the targeted invalid B320 process is absent, When the historical cleanup migration runs, Then it exits as not applicable with zero writes; if B320 exists with unexpected multiplicity or sort, the existing fail-fast guards remain.

RED: route-00002-cleanup-applicability -> FAIL, focused test `2 failed, 5 passed`; zero-target branch was absent.

GREEN: route-00002-cleanup-applicability -> PASS, focused `7 passed`; task-owned MySQL schema with the real 26-process/zero-B320 route executed twice, active process count stayed `26`, backup-table count stayed `0`, and schema cleanup returned `0`.

GREEN: route-00002-migration-regression -> PASS, combined migration tests `50 passed`, full migration policy `605` PASS, branch runtime guard and diff check PASS.

BDD: app-release inherits verified code-only exclusions -> Given the target runs a successful code-only package whose target-bound preflight plan excluded a data migration, When a later app-release contains the same migration ID and SHA, Then deploy marks it `SKIP_BASELINE_SCOPE_EXCLUDED`, treats the dependency as satisfied, and does not execute the historical business-data SQL; changed or new migrations are not inherited.

BDD: baseline evidence must match actual target -> Given app-release wants to inherit scope exclusions, When the target `.env` tag, actual backend/frontend image tags, release-info tag, baseline manifest scope/tag, or baseline preflight environment/status is missing or mismatched, Then deployment fails before runtime mutation.

RED: baseline-scope-exclusion-contract -> FAIL, `3 failed`; planner had no `--baseline-plan`, no inherited action, and deploy script had no target-baseline verification.

GREEN: baseline-scope-exclusion-focused -> PASS, `4 passed`; same ID/file/SHA data exclusions inherit as `SKIP_BASELINE_SCOPE_EXCLUDED`, changed SHA remains APPLY, and dependencies treat verified exclusions as satisfied.

GREEN: baseline-scope-exclusion-regression -> PASS, release governance/build preflight/SQL preflight/runtime frontend suites `170 passed in 52.56s`; PowerShell AST and diff check passed.

GREEN: r22-real-baseline-aware-plan -> PASS, current r22 manifest plus r22 target state plus verified 20260903 code-only plan produced `status=passed`: `SKIP_ALREADY_APPLIED=505`, `SKIP_BASELINE_SCOPE_EXCLUDED=52`, `SKIP_ENV_NOT_ALLOWED=1`, `APPLY=48`. APPLY types: schema 32, permission 10, menu 2, seed 1, data 3; one data item is the just-fixed cleanup already applied after the captured state.

BLOCKER: deploy-release-test-r23-baseline-dependency -> FAIL before application container switch, new permission migration `20260903_dcc_registration_certificate_upload_view_permission` depended on baseline-excluded `20260829_registration_certificate_management_menu_hierarchy`; treating the exclusion as dependency-satisfied skipped the required menu hierarchy change, so menu 990230 retained the old path and the new migration failed. Lock released FAILED and `.env` restored to actual old tag.

BDD: new migrations promote baseline-excluded dependencies -> Given a same-hash historical data migration was excluded by the target code-only baseline, When a pending new/changed migration directly or transitively depends on it, Then app-release must promote that dependency chain to APPLY; only unrelated exclusions remain inherited skips.

RED: baseline-dependency-promotion -> FAIL, focused planner test expected a baseline-excluded migration required by a pending schema migration to become APPLY, but the planner returned SKIP_BASELINE_SCOPE_EXCLUDED.

GREEN: baseline-dependency-promotion-focused -> PASS, direct and transitive baseline-excluded dependencies are promoted to APPLY while an unrelated exclusion remains SKIP_BASELINE_SCOPE_EXCLUDED; `1 passed`.

GREEN: baseline-dependency-promotion-regression -> PASS, release governance/build preflight/SQL preflight/runtime frontend suites `170 passed in 51.30s`.

GREEN: r23-real-dependency-aware-plan -> PASS, r23 manifest plus captured target state plus verified running baseline plan produced `status=passed`: `APPLY=54`, `SKIP_ALREADY_APPLIED=507`, `SKIP_BASELINE_SCOPE_EXCLUDED=44`, `SKIP_ENV_NOT_ALLOWED=1`; both `20260829_registration_certificate_management_menu_hierarchy` and its pending dependent `20260903_dcc_registration_certificate_upload_view_permission` are APPLY.

GREEN: maintenance-baseline-dependency-promotion-commit -> PASS, scoped implementation/test commit `659d77857775287f3df38f05f7bff3b0b6f00b3d`.

GREEN: build-release-app-r24 -> PASS, releaseTag `release-20260910-verified-branch-app-r260908c-r24`; migration policy `605` plus showroom `4`, eDHR protected storage, fresh test ledger preflight, backend Maven `BUILD SUCCESS` in `02:53`, frontend build, Docker images, manifest/integrity and resumable NAS upload all passed.

GREEN: r24-lightweight-package -> PASS, `publishScope=app-release`, `616` files / `720505606` bytes, `614` immutable artifacts, `606` versioned migrations, manifest checksum `sha256:8261168209c167983590f186edc772d481ae7a21dac17e3a4c0217ff4c3ddbfb`; backend/frontend source commit `dfc481c40b8d3dfc637322518bbd40359b6082f3`, dirty count `0`, forbidden MySQL dump/MinIO/DCC data artifact count `0`.

BLOCKER: deploy-release-test-r24-retired-menu-id-collision -> FAIL before application container switch, required historical hierarchy migration found menu IDs `605071320/605071321` occupied by unrelated active MES permissions rather than the expected retired registration-certificate pages. Operation lock released FAILED; remote `.env IMAGE_TAG` was restored to the actual running `release-20260903-main-invoice-assistant-test-r260903b-r1`, backend health remained UP and frontend HTTP remained 200.

GREEN: registration-menu-identity-fix-tdd -> PASS, static RED `1 failed, 3 passed`, GREEN `4 passed`; two isolated MySQL fixtures each passed twice, preserving unrelated active MES IDs while retiring exact legacy identities/descendants and cleaning package/role references. Combined migration regression `51 passed`, migration policy `605` PASS, temporary schema count `0`.

GREEN: registration-menu-identity-fix-commit -> PASS, new app release source commit `d1659f663`; next immutable releaseTag is r25 and failed r24 remains unusable.

BLOCKER: build-release-app-r25-rehearsal-auth-readiness -> FAIL FAST before Maven/Docker/NAS/test write, isolated migration rehearsal created a disposable MySQL container but treated `mysqladmin ping` as authenticated readiness; it advanced while root authentication was not yet usable and failed the first `CREATE DATABASE` with access denied. Rehearsal cleanup passed and r25 is not reusable.

BDD: migration rehearsal requires authenticated readiness -> Given the disposable MySQL process is alive but root credentials are not yet accepted, When build-release waits for rehearsal readiness, Then it must continue waiting until `mysql -e SELECT 1` succeeds with the exact rehearsal password; unauthenticated `mysqladmin ping` cannot open the migration gate.

RED: rehearsal-authenticated-readiness -> FAIL, focused contract found only `mysqladmin ping --silent`; no authenticated `mysql -e SELECT 1` readiness check existed.

GREEN: rehearsal-authenticated-readiness-focused -> PASS, readiness now requires exact output `1` from authenticated MySQL using the generated rehearsal password; `mysqladmin ping` is absent.

GREEN: rehearsal-authenticated-readiness-regression -> PASS, release governance/build preflight/SQL preflight/runtime frontend suites `172 passed in 46.08s`; `git diff --check` passed.

GREEN: rehearsal-authenticated-readiness-commit -> PASS, scoped maintenance commit `3fb9a8c`; failed r25 remains unusable and next releaseTag is r26.

BLOCKER: build-release-app-r26-rehearsal-plan-drift -> FAIL FAST before Maven/Docker/NAS/test write, isolated snapshot import passed but rehearsal used 80 APPLY items from a build plan that omitted the verified running baseline exclusions. It incorrectly attempted baseline-excluded `20260717_mes_balloon_excel_device_workstation_binding` and failed on target-specific business data. Rehearsal cleanup passed and r26 is not reusable.

BDD: build rehearsal and deploy share the verified baseline plan -> Given the target runs a verified code-only/app-release baseline, When app-release build preflight and migration rehearsal plan pending SQL, Then they must verify the same target `.env`/actual images/release-info/baseline manifest/plan and pass that baseline plan into the same planner used by deploy; the build evidence must record the resulting inherited exclusions.

RED: build-rehearsal-baseline-alignment -> FAIL, `2 failed`; build preflight rejected `--baseline-plan`, build setup did not resolve target baseline evidence, and rehearsal did not archive the baseline plan.

GREEN: build-rehearsal-baseline-alignment-focused -> PASS, `2 passed`; build preflight accepts the verified baseline plan, planner emits inherited exclusions, baseline digest participates in the evidence fingerprint, and rehearsal archives the exact baseline plan.

GREEN: build-rehearsal-baseline-alignment-regression -> PASS, release governance/build preflight/SQL preflight/runtime frontend suites `174 passed in 46.18s`.

GREEN: r26-real-baseline-aware-build-plan -> PASS, real prospective manifest plus captured target state plus verified running baseline produced `APPLY=34`, `SKIP_ALREADY_APPLIED=525`, `SKIP_BASELINE_SCOPE_EXCLUDED=46`, `SKIP_ENV_NOT_ALLOWED=1`; the failing balloon Excel data migration is inherited-excluded, while the corrected registration hierarchy and dependent upload-view permission remain APPLY; baselinePlanDigest is present.

GREEN: build-rehearsal-baseline-alignment-commit -> PASS, scoped maintenance commit `4f7642e` includes the build/deploy plan alignment on top of concurrent rehearsal fixes `d2cfd84` and `120df30`.

BLOCKER: shared-maintenance-worktree-drift -> DETECTED, another concurrent task created `scripts/tests/test_release_target_preflight_contract.py` and advanced the same branch during this release task. The unrelated file is preserved and not included. r27 will run from a new detached maintenance release worktree at exact commit `4f7642e` so build-time scripts cannot drift.

GREEN: r27-maintenance-release-worktree-freeze -> PASS, clean detached worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r27\m` at `4f7642e0f97272cda4fb11a92d575ec75b125758`; app release worktree remains clean at `d1659f66396a4c1553fb3d7075a62a188b5c2550`. No new commit is expected in the detached maintenance worktree; it must be removed during closeout.

BDD: 最终迁移计划在昂贵构建前演练 -> Given 测试服只读快照和最终 preflight 计划已生成 / When build-release 开始 / Then 一次性 MySQL 按 APPLY 顺序执行全部迁移且通过后才允许 Maven。

BDD: 演练失败阻断真实发布 -> Given 任一待执行迁移与目标快照不兼容 / When 一次性 MySQL 执行该迁移失败 / Then 生成失败证据、清理临时资源并在 Maven、NAS 上传和测试服写入前终止。

BDD: 演练环境隔离且不可复用 -> Given 任意成功或失败的 releaseTag / When 演练结束 / Then 临时容器和数据目录均被精确清理，真实测试库无写入且失败 releaseTag 不得继续发布。

GREEN: experience-preflight-migration-rehearsal -> PASS, 本阶段沿用测试服发布、构建、数据库、PowerShell、服务器访问和 worktree 强制门禁；只允许测试服只读快照，禁止正式服、真实测试库写迁移、fallback 和失败 releaseTag 复用。

RED: python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py -k "migration_rehearsal" --basetemp doc/tasks/test-server-release-20260908/pytest-red-migration-rehearsal -q -> FAIL, `2 failed`；发布脚本尚无 `Invoke-BuildReleaseMigrationRehearsal`，Maven 前顺序、只读快照、隔离、证据和清理契约均未实现。

GREEN: migration-rehearsal-capacity-preflight -> PASS, 测试服 MySQL 镜像 `mysql:8.0.39` 且容器内具备同版本 `mysqldump/mysql`；数据目录约 `15422838610` bytes，`/var/lib/docker` 可用约 `1369 GB`，满足一次性逻辑快照演练容量前置。

GREEN: migration-rehearsal-implementation-commit -> PASS, 维护 release worktree 提交 `53338f2c94909b30b00bd6a2f731c65cacfaa9c6`；只包含发布脚本与契约测试，发布输入已提交且 worktree clean。

BLOCKER: build-release-app-r25-rehearsal-df-contract -> FAIL FAST before Maven, Docker image build, NAS upload, or test database migration；真实门禁计划 `APPLY=84`，在容量检查处因 GNU `df` 的 `-P` 与 `--output` 互斥而失败。远端输出确认 `REHEARSAL_APPLIED_COUNT:0`、`REHEARSAL_CLEANUP:PASSED`；临时容器、volume 和精确 staging 目录均已清理，真实测试库未写入，r25 判废。

RED/GREEN: migration-rehearsal-df-contract -> PASS, 聚焦 RED 捕获错误参数；移除 `-P` 后 PowerShell AST、`git diff --check` 与完整 `test_release_build_preflight_cache.py` 回归 `50 passed`，修复提交 `6b3c02e02d95897f448ee503ab2dc01b30e92945`。

BLOCKER: build-release-app-r26-rehearsal-mysql-client-contract -> FAIL FAST before Maven, Docker image build, NAS upload, or test database migration；门禁已进入 `REHEARSAL_SNAPSHOT:START`，但源客户端依赖容器内密码环境且目标数据库初始化未确认，分别返回 root access denied 与 unknown database。`REHEARSAL_APPLIED_COUNT:0`、`REHEARSAL_CLEANUP:PASSED`；真实测试库未写入，r26 判废。

RED/GREEN: migration-rehearsal-mysql-client-contract -> PASS, 客户端改为由宿主读取后通过 `docker exec -e MYSQL_PWD` 注入，隔离库显式创建；PowerShell AST、`git diff --check` 与完整回归 `50 passed`，修复提交 `2261062dd2ef37a6c521b9e26b86cf9bff50d891`。

BLOCKER: build-release-app-r27-source-freeze -> FAIL FAST before rehearsal/Maven, 原 app release worktree 在运行期间出现非本任务写入的 `20260829` SQL 与测试改动，fresh build preflight 以 `dirty=false` 契约阻断；没有远端演练资源或测试库写入，r27 判废，未覆盖或提交并发改动。

BLOCKER: build-release-app-r28-rehearsal-readiness-contract -> FAIL FAST before Maven, Docker image build, NAS upload, or test database migration；独立 clean worktree `D:\IntRuoyiWorktree\r260908c-gate-verify` 精确检出 `dfc481c40`，最终计划 `APPLY=83`。MySQL 官方镜像初始化阶段 `mysqladmin ping` 过早返回成功，后续认证报 1045；`REHEARSAL_APPLIED_COUNT:0`、`REHEARSAL_CLEANUP:PASSED`，真实测试库未写入，r28 判废。

GREEN: build-release-app-r29-migration-rehearsal-gate -> PASS AS A FAIL-FAST GATE, 测试服当前 15.4 GB MySQL 一致性只读快照成功导入同镜像、`--network none`、无端口的一次性容器；最终计划 `APPLY=83`。前三条迁移成功，第 4 条 `20260717_mes_balloon_excel_device_workstation_binding` 因 `balloon Excel workstation machine count mismatch` 失败。脚本在 Maven、前端构建、Docker image、NAS 和真实测试库迁移前终止，`REHEARSAL_CLEANUP:PASSED`；真实 backend/frontend 保持旧 tag、backend health UP、frontend HTTP 200，r29 判废。

RED: migration-rehearsal-applied-count-evidence -> FAIL, r29 远端标记 `REHEARSAL_APPLIED_COUNT:3`，但本地 evidence 按 `REHEARSAL_APPLY` 开始标记计数为 4，错误地把失败迁移计入 appliedCount；门禁结论不受影响，但审计证据不准确。

GREEN: migration-rehearsal-applied-count-evidence -> PASS, final code parses the authoritative `REHEARSAL_APPLIED_COUNT` marker and requires successful count to equal the final plan；PowerShell AST and full focused regression `50 passed`，commit `120df30c5a9d7705f2459fb383f79d31f8445df3`。

RED: build-rehearsal-final-plan-baseline-binding -> FAIL, r29 build-time planner returned `APPLY=83` because it did not load the verified running code-only baseline exclusions, while deploy-time planning has a baseline-aware path；the rehearsal could block real defects but was not yet guaranteed to execute the exact deploy-equivalent plan.

CHANGE: daily-migration-gate-strategy -> ACCEPT AND SPLIT, 用户明确选择标准 CI/CD 快速路径；日常 build-release 改为 schema-only 演练 + 测试服只读依赖检查，完整数据快照只保留为高风险/定期流程。变更评审记录：`docs/changes/20260910-structure-only-migration-gate.md`。

BDD: 日常发布不复制业务数据 -> Given 测试服包含大体量业务数据 / When backend build-release 执行日常迁移门禁 / Then 只导出 schema、临时库无业务行、MinIO 不参与且门禁位于 Maven 前。

BDD: 非结构迁移必须有目标只读依赖断言 -> Given 最终计划包含 data/menu/permission/config/seed 迁移 / When build-release 生成迁移门禁计划 / Then 每条迁移必须绑定显式只读 preflight 并在测试服执行；缺失、写操作或断言失败均阻断 Maven。

BDD: 空结构库不得制造假绿 -> Given 数据迁移在空库会 no-op 或通过但目标真实数据不兼容 / When CI 门禁运行 / Then 只能由目标只读 preflight 判定兼容，不能把空库执行结果当作数据迁移通过证据。

RED: structure-only-and-target-readonly-gate -> FAIL, `13 failed, 2 passed`；缺少 target preflight 合同校验器，发布脚本仍执行完整数据 dump，尚未按 schema/non-schema 分流。

GREEN: app-rt000006-applicability-commit -> PASS, app source commit `40bd2fa77` contains only the RT000006 migration and its regression test on top of `0684dbd06`.

BDD: successful migration gate output is bounded -> Given migration policy validates hundreds of SQL files, When the gate passes, Then the release log prints only status and migration count; when it fails, full diagnostics remain visible and block the release.

RED: bounded-migration-policy-log -> FAIL, focused test confirmed successful gates still emitted the full migration JSON.

GREEN: bounded-migration-policy-log -> PASS, success output now parses JSON, requires `status=passed`, and prints only root/count; failure still emits full diagnostics. Release preflight plus PowerShell AST `56 passed`.

GREEN: app-target-preflight-contracts-commit -> PASS, 应用仓在 `D:\IntRuoyiWorktree\r260908c-app` 提交 `908c0fc43` 和 `512e17985`，补齐 11 个 `sql/mysql/target-preflight/*.preflight.sql`，新增 `script/tests/test_release_target_preflight_files.py`，并强制纳入被 `.gitignore` 排除的 `verification-report.md`。

GREEN: app-target-preflight-local-tests -> PASS, `python -X utf8 -m pytest script/tests/test_release_target_preflight_files.py -q` 返回 `2 passed`；维护仓 `release_target_preflight_contract.py` 对 11 个文件逐个返回 `TARGET_PREFLIGHT_CONTRACT_PASS`。

GREEN: r32-release-worktree-freeze -> PASS, 新建维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r32\m` 初始提交 `9c22049`，应用 release worktree `D:\IntRuoyiWorktree\r260908c-r32\a` 提交 `512e179858db`，两者均 detached 且 clean。

BLOCKER: build-release-app-r32-target-preflight-scan -> FAIL FAST before Maven, Docker, NAS upload, remote temporary database, or test DB writes；迁移策略门禁错误地递归扫描 `sql/mysql/target-preflight/*.preflight.sql`，并因这些文件使用 `release-target-preflight` metadata 而不是 `release-migration` metadata 报 `missing release-migration metadata`。r32 判废，未发布。

RED/GREEN: migration-policy-excludes-target-preflight -> PASS, 新增测试 `test_migration_policy_gate_ignores_target_preflight_directory`，修复 `release_migration_manifest.py` / `release_migration_policy_gate.py` 默认扫描逻辑，明确排除 `target-preflight` 目录；`test_release_sql_preflight_gate.py::test_migration_policy_gate_ignores_target_preflight_directory` PASS，相关发布回归 `120 passed`，PowerShell AST PASS，`git diff --check` PASS，维护提交 `0719d094b5dd`。

GREEN: resume-r33-after-r30-close -> PASS, 用户确认 `r30` 线程已关闭；本轮继续使用 r33 clean detached release worktree，维护提交 `0719d094b5dd6bc4a6e21e27ec938a49733b388a`，应用提交 `512e179858db92c5aaf637726cf748f98967aff6`，仅测试服 `build-release -> publish-test`，禁止复用 r15-r32 失败 releaseTag 或执行正式/审查/备份动作。

GREEN: experience-preflight-r33 -> PASS, 已确认测试服发布、构建、数据库、PowerShell、服务器访问、worktree、不可变安装包、无 fallback 和失败标签作废门禁继续适用；下一步先补齐 r33 前端冻结 worktree 依赖，再执行新的 `app-release` 构建。

GREEN: r33-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r33\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 按锁文件恢复依赖；随后 `corepack pnpm rebuild --pending` 完成，`pnpm ignored-builds` 返回 `Automatically ignored builds during installation: None`，发布脚本同款 `frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`。中间一次无效的直连 `node_modules\pnpm\bin\pnpm.cjs` 检查因路径不存在失败，属于本地验证命令选择错误，不影响 Corepack/pnpm 门禁结论。

BLOCKER: build-release-app-r33-target-preflight-missing -> FAIL FAST before Maven, Docker, NAS upload, remote temporary database, or test DB writes；build preflight 计划通过后，目标只读 preflight 门禁发现 `20260629_mes_smart_scheduling_role_scope` 缺少 `sql/mysql/target-preflight/20260629_mes_smart_scheduling_role_scope.preflight.sql`，r33 判废，未发布。

BDD: target preflight set covers all pending non-schema migrations -> Given app-release 计划中存在待 APPLY 的 data/menu/permission 迁移 / When Maven 前 target preflight gate 执行 / Then 每个待执行非结构迁移都有绑定的只读单 SELECT preflight，缺失时立即阻断。

RED: python -X utf8 -m pytest script/tests/test_release_target_preflight_files.py -q -> FAIL, `2 failed`；测试期望加入 `20260629_mes_smart_scheduling_role_scope`、`20260709_mes_rt000006_batch_record_mapping`、`20260716_mes_balloon_xlsx_route_00002_invalid_process_cleanup` 后，三个 preflight 文件缺失。

GREEN: target-preflight-files-r34-source -> PASS, 新增 3 个只读目标 preflight 文件；应用仓目标测试与相关迁移静态回归 `40 passed`，维护仓 `release_target_preflight_contract.py` 对 14 个 target-preflight 文件全部返回 `TARGET_PREFLIGHT_CONTRACT_PASS`，`git diff --check` PASS。

GREEN: app-target-preflight-completion-commit -> PASS, 应用仓提交 `d0942cf920980f79a7a6319f17ef8f88bd4be500`；下一 releaseTag 使用 r34，禁止复用 r33。

GREEN: resume-r34-source-freeze -> PASS, r33 已判废；继续使用全新 r34。维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r34\m` clean detached at `0719d094b5dd6bc4a6e21e27ec938a49733b388a`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r34\a` clean detached at `d0942cf920980f79a7a6319f17ef8f88bd4be500`；仅测试服 `build-release -> publish-test`，禁止正式/备份/审查动作和失败 releaseTag 复用。

GREEN: experience-preflight-r34 -> PASS, 已确认测试服发布、构建、数据库、PowerShell、服务器访问、worktree、不可变安装包、schema-only 迁移演练、target readonly preflight、无 fallback 和失败标签作废门禁继续适用；业务前端 `pnpm ignored-builds=None`，`frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`；NAS 配置字段完整；离线后端基础镜像参数完整。

BLOCKER: build-release-app-r34-repeat-drop-check -> FAIL FAST before Maven, Docker, NAS upload, remote test DB writes, or application restart；已有 r34 本地 preflight/package skeleton 无 final manifest。`migration-rehearsal-evidence.json` 显示 schema-only 演练 `status=failed`、`cleanupStatus=passed`、`applyCount=37`、`schemaMigrationCount=23`、`schemaAppliedCount=3`、`targetPreflightCount=14`、`targetPreflightPassedCount=0`，失败迁移 `20260904_dcc_registration_certificate_download_project_optional`，错误为 `ERROR 3821: Check constraint 'chk_dcc_reg_cert_access_request_project' is not found in the table`。r34 判废，未启动 Maven/NAS/publish-test。

BDD: optional project CHECK removal is repeatable -> Given 多个注册证下载项目可选迁移都需要移除同一 CHECK / When 前序迁移已经移除 `chk_dcc_reg_cert_access_request_project` / Then 后续迁移必须基于 information_schema 条件执行，不得裸 DROP；目标表缺失仍必须 fail fast。

RED: python -X utf8 -m pytest script/tests/test_dcc_registration_certificate_optional_project_sql.py -q -> FAIL, `2 failed`；三个迁移均缺少 `information_schema.TABLES`、`information_schema.TABLE_CONSTRAINTS`、`CREATE PROCEDURE` 和条件 `IF EXISTS`，且包含裸 `ALTER TABLE ... DROP CHECK`。

GREEN: optional-project-check-drop-fix -> PASS, 三个迁移改为校验目标表存在并基于 `information_schema.TABLE_CONSTRAINTS` 条件 `DROP CHECK`；目标测试与 target preflight 文件测试 `4 passed`，迁移策略 `605` PASS，维护仓发布回归 `108 passed`，`git diff --check` PASS。

GREEN: app-optional-project-check-drop-fix-commit -> PASS, 应用仓修复分支提交 `18bcfb225da38782e6622091eac5a521e546d46f`；下一 releaseTag 使用 r35，禁止复用 r34。

GREEN: r35-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r35` 本地 cache/preflight 目录未占用；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r35\m` clean detached at `0719d094b5dd6bc4a6e21e27ec938a49733b388a`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r35\a` clean detached at `18bcfb225da38782e6622091eac5a521e546d46f`。

GREEN: r35-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r35\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖，随后 `corepack pnpm rebuild --pending` 完成；`pnpm ignored-builds` 返回 None，发布脚本同款 `frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`；应用聚焦回归 `2 passed`。

BLOCKER: build-release-app-r35-pqc-missing-column -> FAIL FAST before Maven, Docker, NAS upload, remote test DB writes, or application restart；schema-only 演练 `status=failed`、`cleanupStatus=passed`、`applyCount=37`、`schemaMigrationCount=23`、`schemaAppliedCount=5`、`targetPreflightCount=14`、`targetPreflightPassedCount=0`，失败迁移 `20260904_mes_pqc_task_process_item_identity`，错误为 `ERROR 1054 Unknown column 'qa_item_code' in 'field list'`。目标台账中 `20260817_mes_pqc_item_level_task_identity` 为 `SKIP_ALREADY_APPLIED` 且 checksum 匹配，但真实 schema 缺列，r35 判废。

BDD: PQC process item identity closes prerequisite schema drift -> Given 目标迁移台账声称 `20260817_mes_pqc_item_level_task_identity` 已应用但 schema 缺少 `qa_item_code` / When `20260904_mes_pqc_task_process_item_identity` 执行 / Then 它必须在重复检测和唯一键创建前校验表存在并补齐 `qa_item_code`；表缺失仍 fail fast。

RED: python -X utf8 -m pytest script/tests/test_mes_pqc_task_process_item_identity_sql.py -q -> FAIL, `2 failed`；迁移缺少 `information_schema.TABLES`、`information_schema.COLUMNS`、`qa_item_code` 添加闭包和表缺失 fail-fast 文案。

GREEN: pqc-process-item-identity-column-closure -> PASS, `20260904_mes_pqc_task_process_item_identity` 在 duplicate query 前补齐 `qa_item_code` schema 闭包；应用聚焦测试 `8 passed`，迁移策略 `605` PASS，维护仓发布回归 `108 passed`，`git diff --check` PASS。

GREEN: app-pqc-process-item-identity-fix-commit -> PASS, 应用仓修复分支提交 `46b128f506b793674e593c70650733c00f574512`；下一 releaseTag 使用 r36，禁止复用 r35。

GREEN: r36-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r36` 本地 cache/preflight 目录未占用；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r36\m` clean detached at `0719d094b5dd6bc4a6e21e27ec938a49733b388a`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r36\a` clean detached at `46b128f506b793674e593c70650733c00f574512`。

GREEN: r36-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r36\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖并 `corepack pnpm rebuild --pending`；`pnpm ignored-builds` 返回 None，`frontend_dependency_preflight.cjs` PASS，应用聚焦测试 `4 passed`。

BLOCKER: build-release-app-r36-mysql-socket-contract -> FAIL FAST before Maven, Docker, NAS upload, remote test DB writes, or application restart；schema-only 迁移演练 `status=failed`、`cleanupStatus=passed`、`applyCount=37`、`schemaMigrationCount=23`、`schemaAppliedCount=0`、`targetPreflightCount=14`、`targetPreflightPassedCount=0`，错误为 `ERROR 2002 ... Can't connect to local MySQL server through socket '/var/run/mysqld/mysqld.sock'`。r36 判废，未发布。

BDD: migration rehearsal uses TCP client connections -> Given 源 MySQL 容器和一次性演练 MySQL 容器的 socket 路径可能不存在或初始化时机不同 / When build-release 执行 schema-only 迁移演练和目标只读 preflight / Then 所有 `mysql` 与 `mysqldump` 客户端必须使用 `-h127.0.0.1 --protocol=TCP`，不得依赖默认 socket。

RED: python -X utf8 -m pytest scripts/tests/test_release_build_preflight_cache.py::test_migration_rehearsal_is_read_only_isolated_auditable_and_always_cleaned -q --basetemp D:/ProjectPackage/Int/IntRuoyiMaintance/.tmp-pytest-r36-tcp-red -> FAIL, `1 failed`；测试捕获迁移演练仍使用 socket 默认连接。

GREEN: migration-rehearsal-tcp-client-contract -> PASS, 发布脚本已将 readiness、CREATE DATABASE、schema-only mysqldump、迁移执行和目标只读 preflight 全部改为 `-h127.0.0.1 --protocol=TCP`；聚焦测试 `1 passed`，相关发布回归 `108 passed`，PowerShell AST `AST_OK`，`git diff --check` PASS。

GREEN: maintenance-migration-rehearsal-tcp-fix-commit -> PASS, 维护 release worktree 提交 `8f38c94`；下一 releaseTag 使用 r37，禁止复用 r36。

GREEN: r37-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r37` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r37\m` clean detached at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r37\a` clean detached at `46b128f506b793674e593c70650733c00f574512`。

GREEN: r37-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r37\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖并 `corepack pnpm rebuild --pending`；发布脚本同款 `frontend_dependency_preflight.cjs` 从前端目录返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`。

BLOCKER: build-release-app-r37-dirty-release-worktree -> FAIL FAST before Maven, Docker, NAS upload, remote test DB writes, or application restart；构建前复核发现 `D:\IntRuoyiWorktree\r260908c-r37\a` 出现未提交的 `20260905_erp_kingdee_production_replenishment_list_sync` 拆分改动和新 target preflight 文件。r37 按 clean frozen source 规则判废，未发布。

BDD: 生产补料单迁移结构与配置分离 -> Given 日常 `app-release` 使用 schema-only 演练加 target readonly preflight / When 生产补料单迁移包含建表、菜单、角色授权和 job 配置 / Then 建表必须保留在 `type=schema`，菜单/角色/job 必须拆成独立 `type=config` 并绑定只读 target preflight。

GREEN: production-replenishment-migration-split -> PASS, 应用仓聚焦测试 `3 passed`，维护仓迁移策略 `status=passed migrationCount=606`，新 preflight 合同 `TARGET_PREFLIGHT_CONTRACT_PASS:20260905_erp_kingdee_production_replenishment_list_menu_config`，`git diff --check` PASS。

GREEN: app-production-replenishment-migration-split-commit -> PASS, 已在注册应用 worktree `D:\IntRuoyiWorktree\r260908c-app` 分支 `codex/test-release-migration-chain-fix-20260910` 提交 `95883471a1adae29c6045531074c3c05629fff30`；r37 失败标签不复用。

GREEN: r38-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r38` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r38\m` clean detached at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r38\a` clean detached at `95883471a1adae29c6045531074c3c05629fff30`。

GREEN: r38-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r38\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖并 `corepack pnpm rebuild --pending`；`pnpm ignored-builds` 返回 None，发布脚本同款 `ops/release/frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`。一次旧路径 `scripts/frontend_dependency_preflight.cjs` 检查因文件不存在失败，已按脚本真实路径重跑通过，不作为发布门禁证据。

GREEN: experience-preflight-r38 -> PASS, 继续使用测试服发布、构建、数据库、PowerShell、服务器访问、worktree、不可变安装包、schema-only 迁移演练、target readonly preflight、无 fallback、失败标签作废和无数据制品门禁；r38 两个 release worktree clean，未发现同 releaseTag 运行中的发布进程；NAS JSON 与本机配置的 server/share/username/password 一致，后续仅允许 `build-release -> publish-test` 到测试服 `172.30.30.58`。

ACTION: build-release-app-r38-start -> 仅从 clean detached release worktree 执行 `release-20260911-verified-branch-app-r260908c-r38` 的 `build-release`；范围 `PublishScope=app-release`、`Component=intruoyi`、`Environment=test`、`ServerHost=172.30.30.58`，显式传入 prod/backup host 仅满足 manifest/runtime 参数完整性，不执行正式服、备份服、审查服或 `mark-tested`/`promote-prod`/`promote-backup`。

BLOCKER: build-release-app-r38-dcc-publication-notification-config-in-schema -> FAIL FAST before Maven, Docker, NAS upload, remote test DB writes, or application restart；schema-only 迁移演练 `REHEARSAL_SCHEMA_SNAPSHOT:PASSED`，已成功执行 13 条 schema 迁移，失败迁移为 `20260907_dcc_publication_notification`，错误 `Missing or duplicate DCC parent menu 6800`。根因是该文件标记 `type=schema` 但包含 `system_menu/system_role/system_tenant_package/system_notify_template` 目标业务配置逻辑；r38 判废，不复用。

BDD: DCC 发布通知配置必须脱离 schema 迁移 -> Given 日常 `app-release` 使用 schema-only 演练 / When DCC 发布通知同时需要建表和菜单/通知/角色/套餐配置 / Then 建表保留在 `type=schema`，目标业务配置拆到独立 `type=config` 迁移，并由同名 target readonly preflight 在 Maven 前校验真实目标依赖。

RED: app-migration-policy-excludes-target-preflight -> FAIL, 业务仓 `run-release-migration-policy-gate.py --sql-root sql/mysql` 仍递归扫描 `sql/mysql/target-preflight/*.preflight.sql`，导致 `release-target-preflight` 文件被误判为缺少 `release-migration` 元数据。

GREEN: dcc-publication-notification-migration-split -> PASS, 应用仓提交 `a62d4f95cd941ef2b569488b9479884225a3a016`：`20260907_dcc_publication_notification.sql` 保留纯建表；新增 `20260907_dcc_publication_notification_menu_config.sql` 和 `target-preflight/20260907_dcc_publication_notification_menu_config.preflight.sql`；同步修复业务仓 policy gate 排除 `target-preflight` 目录。验证：聚焦测试 `15 passed`，业务仓迁移策略 `status=passed migrationCount=607`，新增 target preflight 合同 PASS。

GREEN: r39-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r39` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r39\m` clean detached at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r39\a` clean detached at `a62d4f95cd941ef2b569488b9479884225a3a016`。

GREEN: r39-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r39\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖并 `corepack pnpm rebuild --pending`；`pnpm ignored-builds` 返回 None，发布脚本同款 `ops/release/frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`；业务仓迁移策略 `status=passed migrationCount=607`。

ACTION: build-release-app-r39-start -> 仅从 clean detached release worktree 执行 `release-20260911-verified-branch-app-r260908c-r39` 的 `build-release`；范围 `PublishScope=app-release`、`Component=intruoyi`、`Environment=test`、`ServerHost=172.30.30.58`，禁止正式服、备份服、审查服和 promotion 动作。

BLOCKER: build-release-app-r39-signature-password-t1-delimiter -> FAIL FAST before Maven, Docker, NAS upload, remote test DB writes, or application restart；schema-only 演练已通过 DCC 发布通知拆分后的 `20260907_dcc_publication_notification`，失败迁移前进到 `20260908_system_signature_password_t1`；错误 `ERROR 1064 ... near '' at line 13`。根因：该文件包含两个 `CREATE PROCEDURE`，但未使用 MySQL 客户端 `DELIMITER` 包裹过程体；r39 判废，不复用。

BDD: MySQL procedure migration requires explicit delimiter -> Given schema migration contains `CREATE PROCEDURE` with multi-statement body / When MySQL client executes it during schema-only rehearsal / Then procedure blocks must use `DELIMITER $$` and `END$$` before resetting to `DELIMITER ;`，不得靠默认分号解析。

RED: signature-password-t1-delimiter-contract -> FAIL, 新增回归 `test_system_signature_password_t1_contract.py::test_signature_password_migration_adds_history_and_state_columns` 捕获 `DELIMITER $$` 缺失，返回 `1 failed`。

GREEN: signature-password-t1-delimiter-fix -> PASS, 应用仓提交 `66a10cd33af5970f04277d5bea103ff0e3a7693e` 为 `20260908_system_signature_password_t1.sql` 两个临时过程补齐 delimiter；验证 `16 passed`、业务仓迁移策略 `status=passed migrationCount=607`、`git diff --check` PASS。

GREEN: r40-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r40` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r40\m` clean detached at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r40\a` clean detached at `66a10cd33af5970f04277d5bea103ff0e3a7693e`。

GREEN: r40-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r40\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖并 `corepack pnpm rebuild --pending`；发布脚本同款 `frontend_dependency_preflight.cjs` PASS；业务仓迁移策略 `status=passed migrationCount=607`；两个 release worktree clean。

ACTION: build-release-app-r40-start -> 仅从 clean detached release worktree 执行 `release-20260911-verified-branch-app-r260908c-r40` 的 `build-release`；范围 `PublishScope=app-release`、`Component=intruoyi`、`Environment=test`、`ServerHost=172.30.30.58`，禁止正式服、备份服、审查服和 promotion 动作。

GREEN: build-release-app-r40 -> PASS, 轻量程序安装包已生成：`publishScope=app-release`，`artifactCount=621`，镜像 tar `709382144` bytes；sourceRepos 后端/前端均为 `66a10cd33af5970f04277d5bea103ff0e3a7693e` 且 `dirty=false`；包内无 `mysql/`、`minio/`、DCC object inventory 或全量数据快照制品；migration rehearsal、build preflight、preflight plan 与 Docker build evidence 均已写入 `manifest/`。

GREEN: pre-publish-r40-readonly -> PASS, 测试服 `172.30.30.58` 当前 `.env IMAGE_TAG`、backend/frontend 实际镜像仍为 `release-20260903-main-invoice-assistant-test-r260903b-r1`，backend health=`UP`，frontend HTTP=`200`，`RUNNING_LOCKS=0`；旧失败迁移记录属于已判废的历史 releaseTag，不复用。

BLOCKER: deploy-release-test-r40-nas-package-missing -> FAIL before any test server write；首次 deploy 调用误传 YAML `runtime-control.local.yaml` 给 `-NasConfigPath`，被 `ConvertFrom-Json` 本机失败拦截；改用现有 NAS JSON 后脚本能挂载 NAS，但 `Backup/ReleasePackage/release-20260911-verified-branch-app-r260908c-r40` 不存在，说明 r40 构建只留下本地 cache 包，未完成 NAS 发布包上传。r40 判废，不复用；下一轮使用全新 r41，并显式传入 NAS JSON 完成 build-release 上传。

GREEN: r41-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r41` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r41\m` clean detached at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r41\a` clean detached at `66a10cd33af5970f04277d5bea103ff0e3a7693e`。

GREEN: r41-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r41\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖；`pnpm ignored-builds` 返回 None，发布脚本同款 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r41\m\ops\release\frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`；一次从前端目录误调用 `ops/release/frontend_dependency_preflight.cjs` 因路径不存在失败，已按真实脚本路径重跑通过，不作为发布门禁证据。

ACTION: build-release-app-r41-start -> 仅从 clean detached release worktree 执行 `release-20260911-verified-branch-app-r260908c-r41` 的 `build-release`；范围 `PublishScope=app-release`、`Component=intruoyi`、`Environment=test`、`ServerHost=172.30.30.58`，显式传入 NAS JSON 确保安装包上传到 `Backup/ReleasePackage`；禁止正式服、备份服、审查服和 promotion 动作。

BLOCKER: build-release-app-r41-cache-root-contract -> FAIL FAST before Maven, Docker, NAS upload, remote test DB writes, or application restart；命令环境把 `INTRUOYI_LOCAL_CACHE_ROOT` 误设为 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi`，脚本再次追加 `publish-int-ruoyi` 后查找 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\publish-int-ruoyi\release-20260903-main-invoice-assistant-test-r260903b-r1\manifest.json`，导致 target baseline evidence missing。真实基线 manifest 存在于 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260903-main-invoice-assistant-test-r260903b-r1\manifest.json`。r41 未产生 cache 包、未上传 NAS、未发布；按失败标签作废规则不复用，下一轮使用 r42 并把 cache root 设为 `E:\Int\CacheData\IntRuoyi`。

GREEN: r42-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r42` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r42\m` clean detached at `8f38c941c86ce9ed776dec22cf2868d5f92bd4e8`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r42\a` clean detached at `66a10cd33af5970f04277d5bea103ff0e3a7693e`。

GREEN: r42-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r42\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖；`pnpm ignored-builds` 返回 None，发布脚本同款 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r42\m\ops\release\frontend_dependency_preflight.cjs` PASS；应用 worktree 仍为 clean detached。

ACTION: build-release-app-r42-start -> 仅从 clean detached release worktree 执行 `release-20260911-verified-branch-app-r260908c-r42` 的 `build-release`；范围 `PublishScope=app-release`、`Component=intruoyi`、`Environment=test`、`ServerHost=172.30.30.58`，`INTRUOYI_LOCAL_CACHE_ROOT=E:\Int\CacheData\IntRuoyi`，显式传入 NAS JSON；禁止正式服、备份服、审查服和 promotion 动作。

GREEN: build-release-app-r42 -> PASS, build preflight、target readonly preflight、schema-only migration rehearsal、Maven、前端 `build:test`、Docker 镜像构建、manifest 生成和 NAS 上传均通过；releaseTag `release-20260911-verified-branch-app-r260908c-r42` 已上传至 `Backup/ReleasePackage/release-20260911-verified-branch-app-r260908c-r42`。

GREEN: r42-lightweight-package -> PASS, `manifest.json` 显示 `publishScope=app-release`、`artifactCount=621`、镜像 tar `709384704` bytes；后端/前端 source commit 均为 `66a10cd33af5970f04277d5bea103ff0e3a7693e` 且 `dirty=false`；无 `mysql/`、`minio/`、DCC object inventory 或全量数据快照制品；迁移演练 `status=passed`、`schemaMigrationCount=23`、`schemaAppliedCount=23`、`targetPreflightCount=16`、`targetPreflightPassedCount=16`、`cleanupStatus=passed`。

ACTION: deploy-release-test-r42-start -> 使用同一 `release-20260911-verified-branch-app-r260908c-r42` 从 NAS 执行 `deploy-release` 到测试服 `172.30.30.58`；仅允许 `Environment=test`、`RemoteAppDir=/opt/intruoyi/runtime`，禁止正式服、备份服、审查服和 promotion 动作。

GREEN: resume-after-r30-close-r42 -> PASS, 用户确认 `r30` 线程已关闭；本线程接管后只读复核确认无本轮 r42/publish-int-ruoyi/deploy-release 后台进程在运行，r42 本地轻量程序包仍存在于 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260911-verified-branch-app-r260908c-r42`，manifest/release-manifest 均指向同一 releaseTag，包内 `.env` 指向测试服 `172.30.30.58`；继续使用同一不可变安装包执行测试服 `deploy-release`，不触碰正式服、备份服、审查服，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

GREEN: experience-preflight-r42-resume -> PASS, 已按经验索引命中发布、NAS、PowerShell、worktree、测试服运行态、schema-only 迁移演练、target readonly preflight、不可变安装包和失败 releaseTag 作废门禁；已确认 `-NasConfigPath` 必须使用 `runtime/runtime-control/nas-release-config/*.json` 形态的 NAS JSON，不得误传 `runtime-control.local.yaml`；继续使用 `INTRUOYI_LOCAL_CACHE_ROOT=E:\Int\CacheData\IntRuoyi`，只允许 `build-release -> publish-test` 范围内的测试服部署验证。

BLOCKER: deploy-release-test-r42-local-cache-stale-env -> FAIL before SSH, Docker, database migration, app container switch, or test server write；r42 deploy 首次重跑因本地命令误传不存在的 `-Json` 参数被 PowerShell 参数绑定拦截，未进入脚本主体；修正参数后，脚本只完成 NAS 挂载与包下载，随后 `Test-ReleasePackageIntegrity` 在本地缓存目录发现上一线程/上一尝试残留的 `.env`，报 `.env: undeclared file` 并停止。根因：`Copy-ReleasePackageFromNas` 用 `robocopy /E` 覆盖下载 NAS 包，但没有清除目标本地 release cache 中不属于 NAS 包的旧文件；r42 判废，不复用。

BDD: NAS 包下载必须与远端不可变包严格一致 -> Given 本地 release cache 已存在同名 releaseTag 且残留 deploy 期生成的 `.env` / When `deploy-release` 从 NAS 下载不可变安装包 / Then 下载必须清除目标目录中 NAS 包不存在的旧文件，再执行完整性校验，不能让旧缓存污染发布判断。

RED: python -X utf8 -m pytest scripts\tests\test_release_package_governance.py::test_nas_package_download_purges_stale_local_cache_files_before_integrity -q --basetemp doc\tasks\test-server-release-20260908\pytest-red-r42-nas-purge -> FAIL, 现有 `Copy-ReleasePackageDirectory` 未使用 `robocopy /PURGE`。

GREEN: nas-package-download-purge-contract -> PASS, 维护 release worktree 将 `Copy-ReleasePackageDirectory` 改为 `robocopy /E /PURGE /Z /MT:16 ...`，使 NAS 下载后的本地缓存与远端包一致；聚焦测试 `3 passed`，发布包治理与构建预检回归 `118 passed`，PowerShell AST PASS，`git diff --check` PASS。下一轮必须使用全新 r43 releaseTag，禁止复用 r42。

GREEN: r43-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r43` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r43\m` clean detached at `8080c0d3c7076d2305d945dea26bf1a22ceaf026`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r43\a` clean detached at `66a10cd33af5970f04277d5bea103ff0e3a7693e`；本地 cache 目标 tag 不存在。

GREEN: r43-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r43\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖，随后 `corepack pnpm rebuild --pending`；`pnpm ignored-builds` 返回 None，发布脚本同款 `frontend_dependency_preflight.cjs` 从前端目录返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`。一次从非前端目录执行同款脚本因 Node 模块解析根不正确失败，已按脚本真实运行目录重跑通过，不作为门禁证据。

ACTION: build-release-app-r43-start -> 仅从 clean detached release worktree 执行 `release-20260911-verified-branch-app-r260908c-r43` 的 `build-release`；范围 `PublishScope=app-release`、`Component=intruoyi`、`Environment=test`、`ServerHost=172.30.30.58`，`INTRUOYI_LOCAL_CACHE_ROOT=E:\Int\CacheData\IntRuoyi`，显式传入 NAS JSON；禁止正式服、备份服、审查服和 promotion 动作。
GREEN: build-release-app-r43 -> PASS, build preflight、target readonly preflight、schema-only migration rehearsal、Maven、前端 `build:test`、Docker 镜像构建、manifest 生成和 NAS 上传均通过；releaseTag `release-20260911-verified-branch-app-r260908c-r43` 已上传至 `Backup/ReleasePackage/release-20260911-verified-branch-app-r260908c-r43`。

GREEN: r43-lightweight-package -> PASS, 本地包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260911-verified-branch-app-r260908c-r43` 包含 `manifest/`、`required-sql/`、`resources/`、`smoke/`、`docker-compose.yml`、镜像 tar 和 manifests；无 `.env`、无 `mysql/`、无 `minio/`、无 DCC object inventory；后端/前端 source commit 均为 `66a10cd33af5970f04277d5bea103ff0e3a7693e` 且 `dirty=false`。

ACTION: deploy-release-test-r43-start -> 使用同一 `release-20260911-verified-branch-app-r260908c-r43` 从 NAS 执行 `deploy-release` 到测试服 `172.30.30.58`；显式传入 `RemoteMinioContainer=intruoyi-minio` 以完成目标文件配置重绑校验；仅允许 `Environment=test`、`RemoteAppDir=/opt/intruoyi/runtime`，禁止正式服、备份服、审查服和 promotion 动作。
BLOCKER: deploy-release-test-r43-wrong-remote-minio-container -> FAIL before release operation lock, required SQL execution, Docker image load, runtime `.env` switch, application restart, or test server app version change；r43 包从 NAS 下载和完整性校验已通过，eDHR protected storage verifier PASS，随后读取远端 MinIO 凭据时 `docker inspect ... intruoyi-minio` 报 `No such object: intruoyi-minio`。只读 `docker ps` 确认测试服实际 MinIO 容器名为 `ragflow_compose-minio-1`，当前 backend/frontend 仍为旧 tag `release-20260903-main-invoice-assistant-test-r260903b-r1`。本次属于部署参数错误，未生成 r43 release operation；继续使用同一不可变 r43 包纠正 `RemoteMinioContainer` 后重跑 deploy-release。
BLOCKER: deploy-release-test-r43-missing-repo-root-params -> FAIL before release operation lock, required SQL execution, Docker image load, runtime `.env` switch, application restart, or test server app version change；纠正 `RemoteMinioContainer` 后的第二次重跑漏传 `BackendRepoRoot/FrontendRepoRoot`，脚本在本地定位 eDHR verifier 到维护 worktree `m\tool\...` 并失败。继续使用同一不可变 r43 包，显式传入应用 release worktree 后端/前端根路径后重跑。

ACTION: resume-r43-after-thread-close -> 用户确认 `r30` 线程已关闭；继续使用同一不可变 `release-20260911-verified-branch-app-r260908c-r43` 轻量程序包，不重新构建，不复用 r15-r42 失败包。高风险动作前复核：维护 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r43\m` clean at `8080c0d3c7076d2305d945dea26bf1a22ceaf026`；应用 worktree `D:\IntRuoyiWorktree\r260908c-r43\a` clean at `66a10cd33af5970f04277d5bea103ff0e3a7693e`；本地无本轮发布后台进程。下一步显式传入 `RemoteMinioContainer=ragflow_compose-minio-1`、`BackendRepoRoot=D:\IntRuoyiWorktree\r260908c-r43\a\IntRuoyiBackend`、`FrontendRepoRoot=D:\IntRuoyiWorktree\r260908c-r43\a\IntRuoyiFronted` 后，仅执行测试服 `deploy-release`。

BLOCKER: resume-r43-original-app-worktree-dirty -> PASS/CONTAINED, 继续前复核发现原应用 release worktree `D:\IntRuoyiWorktree\r260908c-r43\a` 已被后续线程留下 3 个未提交改动，且本地 r43 cache 目录存在 deploy 残留 `.env`。未回滚、未删除、未覆盖这些未归属改动；为保持不可变包与校验源码干净，创建同一提交 `66a10cd33af5970f04277d5bea103ff0e3a7693e` 的临时 clean deploy 校验 worktree `D:\IntRuoyiWorktree\r260908c-r43-deploy-clean\a`，后续 `BackendRepoRoot/FrontendRepoRoot` 改指该 clean worktree；本地 cache `.env` 由 r43 已修复的 NAS 下载 `/PURGE` 合同清理，禁止手工修改安装包内容。

ACTION: deploy-release-test-r43-resume-clean-worktree-start -> 使用同一不可变 `release-20260911-verified-branch-app-r260908c-r43` 从 NAS 执行测试服 `deploy-release`；显式传入 `RemoteMinioContainer=ragflow_compose-minio-1`、`BackendRepoRoot=D:\IntRuoyiWorktree\r260908c-r43-deploy-clean\a\IntRuoyiBackend`、`FrontendRepoRoot=D:\IntRuoyiWorktree\r260908c-r43-deploy-clean\a\IntRuoyiFronted`、`RemoteAppDir=/opt/intruoyi/runtime`、测试服 `172.30.30.58`。禁止 `mark-tested`、`promote-prod`、`promote-backup`、正式服、备份服和审查服动作。

BLOCKER: deploy-release-test-r43-system-signature-active-duplicate -> FAIL after release operation lock and before backend/frontend container switch；r43 从 NAS 下载、`/PURGE` 清理本地 cache、完整性校验、eDHR protected storage verifier、镜像上传、required SQL 上传和 Docker image load 均通过；执行 `20260908_system_signature_password_t1.sql` 时 MySQL 报 `ERROR 1644 ... system_users contains duplicate tenant canonical username values`。读-only 诊断确认测试服 `system_users` 共有 `ALL_DUP_GROUPS=2`，但 `ACTIVE_DUP_GROUPS=0`，重复只存在已删除账号；r43 迁移把历史删除账号也纳入永久唯一约束，属于迁移约束定义过宽。operation lock 已释放为 `FAILED`。

GREEN: r43-env-drift-restored -> PASS, r43 失败后远端 `/opt/intruoyi/runtime/.env` 一度写入 r43，但实际 backend/frontend 容器仍运行 `release-20260903-main-invoice-assistant-test-r260903b-r1`。已将 `.env IMAGE_TAG` 恢复为实际运行 tag；backend health=`UP`，frontend HTTP=`200`。未重启应用，未切换 backend/frontend 容器。

BDD: 电子签名用户名唯一约束只约束未删除账号 -> Given `system_users` 中存在历史删除账号与当前账号规范化用户名相同 / When 执行 `20260908_system_signature_password_t1` / Then 迁移必须保留删除账号审计记录，只对未删除账号建立永久唯一约束；若未删除账号重复仍必须 fail fast。

RED: deploy-release-test-r43-system-signature-active-duplicate -> FAIL, 测试服真实数据触发 `ERROR 1644`，证明 r43 迁移错误地把已删除账号重复计入唯一性阻断。

GREEN: signature-password-t1-active-unique-fix -> PASS, 应用仓 `codex/test-release-signature-t1-active-unique-20260911` 提交 `713c64112d7b626a2ba71788fd36cc32d686addc`：新增 generated column `active_canonical_username`，其值仅在 `deleted=0` 时等于 `canonical_username`；迁移重复检查加 `WHERE CAST(deleted AS UNSIGNED)=0`；唯一键改为 `(tenant_id, active_canonical_username)`。验证：`test_system_signature_password_t1_contract.py` -> `10 passed`，迁移策略 `status=passed migrationCount=607`，相关元数据测试 `3 passed`，`git diff --check` PASS。下一轮必须使用全新 r44，禁止复用 r43。

GREEN: r44-release-worktree-freeze -> PASS, releaseTag `release-20260911-verified-branch-app-r260908c-r44` 使用全新 release worktree；维护 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c-r44\m` clean detached at `8080c0d3c7076d2305d945dea26bf1a22ceaf026`；应用 release worktree `D:\IntRuoyiWorktree\r260908c-r44\a` clean detached at `713c64112d7b626a2ba71788fd36cc32d686addc`；本地 cache 目标 tag 不存在。

GREEN: r44-frontend-dependency-restore -> PASS, `D:\IntRuoyiWorktree\r260908c-r44\a\IntRuoyiFronted` 使用 `corepack pnpm install --frozen-lockfile` 恢复依赖并执行 `corepack pnpm rebuild --pending`；`pnpm ignored-builds` 返回 `None`，发布脚本同款 `frontend_dependency_preflight.cjs` 返回 `{"status":"passed","packages":["cross-env","vite","vue-tsc"]}`。

ACTION: build-release-app-r44-start -> 仅从 clean detached release worktree 执行 `release-20260911-verified-branch-app-r260908c-r44` 的 `build-release`；范围 `PublishScope=app-release`、`Component=intruoyi`、`Environment=test`、`ServerHost=172.30.30.58`，`INTRUOYI_LOCAL_CACHE_ROOT=E:\Int\CacheData\IntRuoyi`，显式传入 NAS JSON；禁止正式服、备份服、审查服和 promotion 动作。

GREEN: build-release-app-r44 -> PASS, 本地 r44 包目录存在，`manifest.json` 指向 `release-20260911-verified-branch-app-r260908c-r44`，`publishScope=app-release`，backend/admin-frontend sourceRepos 均为 `713c64112d7b626a2ba71788fd36cc32d686addc` 且 `dirty=false`；包内未发现 MySQL dump、MinIO 快照或 DCC object inventory 数据目录。构建产物包含 backend/frontend 镜像 tar 与 `manifest/migration-rehearsal-evidence.json`、`manifest/build-preflight-evidence-test.json`、`manifest/docker-build-evidence.json`。

GREEN: deploy-release-test-r44-remote-runtime -> PASS, 测试服只读核验显示 `/opt/intruoyi/runtime/.env` 的 `IMAGE_TAG`、`intruoyi-backend` 实际镜像、`intruoyi-frontend` 实际镜像均为 `release-20260911-verified-branch-app-r260908c-r44`；backend 容器 running，frontend 容器 running，backend `/actuator/health` 为 `UP`，frontend HTTP 为 `200`，frontend `/release-info.json` 的 `releaseTag` 为 r44、`publishScope=app-release`、sourceRepos `dirty=false`。

GREEN: deploy-release-test-r44-migration-ledger -> PASS, 测试服 `infra_release_operation_lock` 最新 test 记录为 r44 `APPLIED`；`infra_release_migration` 中 r44 `APPLIED=6`、`SKIPPED_ALREADY_APPLIED=555`、`FAILED/RUNNING=0`；`system_users` 已存在 `canonical_username`、`active_canonical_username`、`password_credential_status`，且唯一键 `uk_system_users_tenant_active_canonical_username` 覆盖 `(tenant_id, active_canonical_username)`。

BLOCKER: playwright-test-server-r44-first-pass-request-aborts -> CONTAINED, 首次 Playwright 登录成功但把登录页跳转期间的 `net::ERR_ABORTED` 和二次导航中止请求计入 failed request；未判定页面失败，改为登录完成后稳定窗口复验。

GREEN: playwright-test-server-r44-post-login-stable -> PASS, Playwright 真实打开测试服 `http://172.30.30.58:8081`，使用 `测试租户/aoteman` 登录成功，最终 URL `http://172.30.30.58:8081/index`，标题 `瑛泰管理系统 - 首页`，权限响应 `menuCount=9`、`permissionCount=202`；登录后稳定窗口 `postLoginConsoleErrorCount=0`、`postLoginFailedRequestCount=0`。证据：`output/playwright/r44-test-release/playwright-test-server-r44-post-login-stable-summary.json` 与截图 `output/playwright/r44-test-release/test-server-dashboard-r44-post-login-stable.png`。

GREEN: test-release-r44-ready-for-closeout -> PASS, r44 发布范围仍限测试服；未执行 `mark-tested`、`promote-prod`、`promote-backup`、正式服、备份服或审查服动作。`task.md` 已标记 `ready_for_closeout`，下一步仅执行本任务产物与 release worktree 收尾。

GREEN: task-closeout-cleanup-preview-apply-r44 -> PASS, `task-closeout-cleanup` preview/apply 成功；保留核心任务记录、数据库/回归证据、DCC 清理备份与回滚 SQL、r44 迁移策略证据，删除 `doc/tasks/test-server-release-20260908` 下可再生 pytest/log/intermediate artifacts，无 blocked/warnings。

GREEN: release-worktree-cleanup-r44 -> PASS, 已先创建维护保护分支 `codex/release-r44-maintenance-script-20260911` 指向 `8080c0d3c7076d2305d945dea26bf1a22ceaf026`；应用修复提交由 `codex/test-release-signature-t1-active-unique-20260911` 保护。随后删除 r260908c 系列 release worktree Git 注册，并清理物理残留；复核 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260908c*` 与 `D:\IntRuoyiWorktree\r260908c-*` 本任务 release 残留路径不存在，维护仓和应用仓 `git worktree list --porcelain` 不再包含 r260908c。

GREEN: project-experience-consolidation-r44 -> PASS, 按 `project-experience-consolidation` 规则合并进现有经验文档：`docs/release-build-preflight-lessons.md` 新增“迁移唯一约束业务范围与发布包缓存清洁门禁”，`docs/test-release-preflight.md` 新增“发布后 Playwright 登录稳定窗口门禁”，并同步 `docs/experience-index.md` 关键词路由。

BLOCKER: int-main-integration-closeout -> 维护提交 `8080c0d3c7076d2305d945dea26bf1a22ceaf026` 不是维护仓 `int_main` 祖先，应用提交 `713c64112d7b626a2ba71788fd36cc32d686addc` 也不是 `E:\IntRuoyi` 的 `int_main` 祖先；应用分支与 `int_main` 分叉，维护仓主工作区有 38 个 tracked dirty，应用主工作区有 7 个 unrelated tracked dirty。按 no-fallback 与 worktree 融合规则，未执行风险 merge/cherry-pick，未覆盖并发改动；当前任务状态改为 `blocked`，阻塞范围仅为源代码主线融合，不影响 r44 已完成的测试服运行态结论。

GREEN: public-runtime-check-r44-after-closeout -> PASS, 公开只读检查返回 backend `/actuator/health` 为 `UP`，frontend `/release-info.json` 的 `releaseTag=release-20260911-verified-branch-app-r260908c-r44`、`publishScope=app-release`、sourceRepos dirty flags 为 `False,False`。
