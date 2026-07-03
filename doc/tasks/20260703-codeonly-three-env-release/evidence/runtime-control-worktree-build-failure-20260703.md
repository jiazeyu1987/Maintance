# runtime-control worktree build failure evidence

- capturedAt: 2026-07-03 23:29:55 +08:00
- worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\20260703-codeonly-three-env-release\IntRuoyiMaintance`
- failure: `scripts/build.ps1` failed before producing `backend/target/runtime-control-maintenance-2026.06-SNAPSHOT.jar`.
- observed output: `ERR_PNPM_IGNORED_BUILDS` for `esbuild@0.27.7` and `vue-demi@0.14.10`; frontend dist missing `frontend/dist/index.html`.
- impact: local runtime control cannot yet be switched to the release maintenance worktree; no build-release/publish operation has been started.
- port 48181 status after failure: no listener after stopping previous main-workspace process.
