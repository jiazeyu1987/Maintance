# Verification Report

## Result

`NO-GO / blocked`。本轮未达到测试服发布成功标准。

## Frozen Inputs

| Repository | Branch | Frozen HEAD | Worktree | Status |
|---|---|---|---|---|
| Maintenance | `int_main` | `66c4ea05dda04459433bc22471ea2b6f4f3dfc32` | `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260823d\m` | detached clean |
| IntRuoyi app | `int_main` | `0002767c0486f11d82bd82666bf8b0f164aee597` | `D:\IntRuoyiWorktree\r260823d\a` | detached clean |

主工作区在冻结时均存在 dirty/untracked 内容；构建未使用主工作区。冻结后 app 主线推进到 `a6574c3631dfa3c5f8381596fcef5c91acd98db0`，按用户要求不追逐后续提交。

## Failed Gate

- Command: frozen app worktree recursive `*.vue` zero-byte scan。
- Result: `FAIL`，`zero-byte-vue-count=1`。
- File: `IntRuoyiFronted/src/views/dcc/controlled-file/training/components/TrainingRulesReadonlyTab.vue`。
- Git blob size: `0`；worktree file length: `0`。
- Impact: Vite SFC contract is invalid; no trustworthy build artifact, manifest, version, change note, operation, or runtime evidence can be produced.

## Not Executed

`pnpm build:test`、维护控制台构建、Maven package、`build-release`、`publish-test`、测试服务器写入/重启、镜像或容器切换、health/HTTP/page/release-info 验收、`mark-tested`、`promote-prod`、`promote-backup` 均未执行。

## Cleanup Boundary

任务为 blocked，按 worktree 规则保留本任务两个 clean worktree 作为证据；未执行 cleanup preview/apply，未删除目录或释放任何端口登记。
