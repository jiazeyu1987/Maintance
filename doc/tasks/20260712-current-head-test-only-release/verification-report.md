# 20260712 当前 HEAD 仅测试服发布验证报告

## Current Status

completed - build-release、publish-test、测试服真实运行态、运行控制台版本说明和 closeout 清理均通过。

## Verification Checklist

- [x] 三仓临时 release worktree clean 且 HEAD 等于冻结提交。
- [x] 维护控制台构建成功。
- [x] build-release operation SUCCESS。
- [x] Manifest v1 sourceRepos 等于冻结提交且 dirty=false。
- [x] 版本号和变更说明与本次 releaseTag / Manifest / release-info 一致。
- [x] publish-test operation SUCCESS。
- [x] 测试服真实运行态检查通过。
- [x] 运行控制台版本号和变更说明检查通过。
- [x] 问题记录完成。
- [x] 前置经验沉淀完成。
- [x] 本任务临时 worktree 清理完成。

## Blocker Evidence

- evidence/release-migration-policy-gate-rerun.json: migration policy gate exit=1。
- 缺失 metadata 文件：D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712t\b\sql\mysql\20260711_mes_batch_record_cell_link_rule.sql。
- 测试服写入：未执行。
- 正式服/备份服/mark-tested/promote：未执行。

## int_main Recheck Evidence

- 当前 int_main worktree：D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712i
- Migration gate：exit=1，见 evidence/intmain-release-migration-policy-gate.json。
- 测试服写入：未执行。

## Successful Release Evidence

- Release tag: `release-20260712-intmain-test-r260712p-r3`。
- Clean release worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p`。
- Frozen commits: maintenance=`481d03c1940f233ba12576801286ff2617e3a441`，backend=`c7753b28997dbd8d8b3581250961646f00b14ccb`，frontend=`2d10335f75a72f934aac52839fdb78a696036304`。
- Build release: operation `op-2026-07-12T031646245278700Z-f1006e17-c7b6-445b-9eaa-5d67e4b66ed1`，status=`SUCCESS`，证据 `evidence/build-release-r3-continue-status.json`。
- Manifest/package: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260712-intmain-test-r260712p-r3\manifest.json`，sourceRepos 均为冻结提交且 dirty=false；证据 `evidence/release-package-manifest-validation-r3-corrected.json`。
- Publish test: operation `op-2026-07-12T043308044248700Z-d8e299c3-a64e-43cc-bd5a-949db86dc67f`，environment=`test`，status=`SUCCESS`；证据 `evidence/publish-test-r3-final-status.json`。
- Test runtime: `IMAGE_TAG=release-20260712-intmain-test-r260712p-r3`，backend/frontend 实际镜像 tag 均为该 releaseTag，backend health=`UP`，frontend HTTP=200，frontend release-info 包含版本号、变更说明和冻结提交；证据 `evidence/test-server-runtime-verification-r3.json`。
- Boundary: 未执行 `mark-tested`、`promote-prod`、`promote-backup`，未发布正式服或备份服。

## Closeout Verification

- Runtime-control: 本地 48181 health=`UP`，已恢复主工作区稳定路径。
- Worktree cleanup: 本任务临时 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260712p` 已从 Git 注册和物理目录移除；维护仓当前仅保留 `int_main` 主 worktree。
- Task cleanup: task-closeout apply 成功，保留核心记录与 `issues.md`，删除一次性 evidence/helper 文件；原始 secret-bearing 日志未保留为可提交产物。
