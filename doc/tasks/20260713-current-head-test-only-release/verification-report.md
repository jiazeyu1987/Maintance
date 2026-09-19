# 20260713 当前 HEAD 仅测试服发布验证报告

## Result

PASS - `release-20260713-current-head-test-r260713t-r3` 已基于本轮冻结 release worktree 发布到测试服务器 `172.30.30.58`，并通过真实运行态与运行控制台页面验证。

## Release Input

- Maintenance worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/m`, HEAD `efa0cfd79c75a48de807a40e1e80deefff63e6ee`, clean after runtime residual cleanup.
- Backend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/b`, HEAD `bc38e943d6c7648ed10347dcfe64796c6348f085`, clean.
- Frontend worktree: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/f`, HEAD `07eb3c4ecf06b0f8e26ec4c36036f3116aa716aa`, clean.
- Build directory: `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t/m`; publish package: `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260713-current-head-test-r260713t-r3`.

## Build Evidence

- Build operation `op-2026-07-13T114933441747800Z-ea18fdef-4abd-44e8-a712-8615a67b95bf` = `SUCCESS`.
- Manifest v1 exists at `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260713-current-head-test-r260713t-r3/manifest.json`.
- Manifest `publishScope=code-only`; backend commit `bc38e943d6c7648ed10347dcfe64796c6348f085` dirty=false; frontend commit `07eb3c4ecf06b0f8e26ec4c36036f3116aa716aa` dirty=false.
- Artifact hash verification passed for manifest artifact list; forbidden data directories were not present.

## Publish Evidence

- Preview verified `publish-test` only: environment `test`, `ServerHost=172.30.30.58`, `RemoteAppDir=/opt/intruoyi/runtime`, no mark-tested/prod/backup action.
- Publish operation `op-2026-07-13T121325438123300Z-549989ce-c0b2-4cab-bc66-e7dfc0630394` = `SUCCESS`.
- No `mark-tested`, `promote-prod`, `promote-backup`, production release, or backup release was executed.

## Runtime Evidence

- Test server `.env IMAGE_TAG=release-20260713-current-head-test-r260713t-r3`.
- Backend image `intruoyi-backend:release-20260713-current-head-test-r260713t-r3`; frontend image `intruoyi-frontend:release-20260713-current-head-test-r260713t-r3`; both containers running.
- Backend health HTTP 200 with status `UP`; frontend HTTP 200 with non-empty HTML; PDF worker HTTP 200 `application/javascript`.
- `release-info.json` contains releaseTag `release-20260713-current-head-test-r260713t-r3`, `publishScope=code-only`, backend commit `bc38e943d6c7648ed10347dcfe64796c6348f085`, frontend commit `07eb3c4ecf06b0f8e26ec4c36036f3116aa716aa`, dirty=false.
- Release lock row: `test APPLIED test-release-20260713-current-head-test-r260713t-r3`; migration failed count `0`.

## Page Evidence

- Maintenance frontend served from the frozen maintenance worktree at `http://127.0.0.1:48182/`.
- Playwright opened the runtime console, found the releaseTag, clicked “查看变更”, and verified the “版本变更说明” dialog contained releaseTag and change notes.
- Browser console errors `0`; warnings `0`.

## Issues Recorded

- `runtime-dir-dirty-after-resume`: untracked `runtime/` made the maintenance release worktree dirty; cleaned after stopping task-owned runtime-control process.
- `config-read-secret-output`: full runtime-control config output can expose credentials; future evidence must use redacted allowlists.
- `manifest-maintenance-source-gap`: package manifest records backend/frontend sourceRepos, while maintenance execution source requires separate worktree/Jar evidence.
- `release-status-timeout`: release-status/release-packages candidate scanning timed out; direct target Manifest verification was used instead.
- `publish-test-log-secret`: publish-test operation log includes `mysql -p...`; raw log was not saved or committed.
- `ssh-stdin-n-flag`: `ssh -n ... bash -s` drops stdin and produces empty verification.
- `windows-textmode-crlf`: Windows text-mode stdin sent CRLF to bash; binary UTF-8 stdin fixed the verification path.
- `mysql-double-quote-filter`: MySQL double-quoted string filters returned empty results; heredoc + single-quoted SQL fixed lock/migration verification.

## Final Status

Completed. Runtime-control has been restored to the main workspace Jar, task-owned release worktree processes are stopped, `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t` and `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260713t-state` are removed, Git worktree registrations are absent, and task-closeout preview/apply completed with blocked=<none> and warnings=<none>.
