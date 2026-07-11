# 20260711-current-head-test-only-release 验证报告

## 结论

PASS。已按“仅测试服发布”范围完成 `release-20260711-current-head-test-r4` 的 build-release、publish-test 和测试服真实运行态验证；未执行 `mark-release-tested`、`promote-prod`、`promote-backup`，未发布正式服或备份服。

## 发布输入

- 维护仓：`266f0ae7349348dbeeac4fe553ac404da714dbd6`，worktree `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/m`，detached clean。
- 后端：`29cf684450849adc49433a6fb97fe44ec872d580`，worktree `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/b`，detached clean；该提交为用户授权的迁移 metadata 最小修复，已 ff-only 合入后端 `int_main`。
- 前端：`f3edb4202a8c8acd1ffa39c180a203bafbbc2ddf`，worktree `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/f`，detached clean。
- 主工作区存在无关 dirty/untracked 内容，构建发布未使用主工作区未提交改动。

## 构建验证

- 维护控制台 Jar：`D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t/m/backend/target/runtime-control-maintenance-2026.06-SNAPSHOT.jar`。
- Jar SHA256：`5fe32b4ca4a9893a8b84e05b194ed9e06ea166deed3aa5c80fa05d492e65e24a`。
- build-release operation：`op-2026-07-11T020116790952700Z-a56e7120-5a78-45a4-a2a3-a1016359d0f1`，状态 `SUCCESS`。
- 发布包：`E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260711-current-head-test-r4`；NAS：`Backup/ReleasePackage/release-20260711-current-head-test-r4`。
- Manifest：`manifestVersion=1.0`，`publishScope=code-only`，backend/frontend sourceRepos commit 均匹配冻结输入，`dirty=false`，changeSet 存在，573 项 artifact/requiredSql SHA256 校验通过。

## 测试服发布验证

- publish-test operation：`op-2026-07-11T022429337867100Z-391009c6-1e42-436e-bebd-075f15c4c65d`，状态 `SUCCESS`。
- 远端 `.env`：`IMAGE_TAG=release-20260711-current-head-test-r4`。
- 实际镜像：backend `intruoyi-backend:release-20260711-current-head-test-r4`，frontend `intruoyi-frontend:release-20260711-current-head-test-r4`。
- 容器：backend/frontend 均 `Up`。
- 后端健康：`http://172.30.30.58:48081/actuator/health` 返回 `UP`。
- 前端入口：`http://172.30.30.58:8081/` 返回 HTTP 200。
- 前端 release-info：`/release-info.json` 包含 releaseTag、changeSet、backend commit 和 frontend commit。
- 运行控制台：`http://127.0.0.1:48181/` release-status 当前测试服 releaseTag 为 `release-20260711-current-head-test-r4`；Playwright 已打开页面和 `版本变更说明` 对话框，核对 releaseTag 与变更摘要。

## 问题记录

- P001-P011：构建前主工作区 dirty、PowerShell/bootstrap、detached 校验、pnpm、migration metadata gate 等前置问题已记录。
- P012-P018：后端授权修复、首轮 build-release 失败、runtime console 进程死亡、启动方式不稳定等构建阶段问题已记录。
- P019-P026：publish-test preview runtime console 崩溃、远端 SSH/PowerShell 引号与 URI、release-info SSH、Playwright 模块/浏览器问题已记录。
- P027-P030：secret-bearing transient output 风险、PowerShell JSON 中文显示 mojibake、历史 dead RUNNING operation、worktree residual cleanup 已记录。

## 经验沉淀状态

- 已把本次可前置化问题整理为 release/worktree/PowerShell/Playwright/post-publish 验证门禁，更新项目经验入口、发布经验、测试服发布前置和发布 checklist。
- 高风险失败条件仍保持 fail fast：manifest 缺失或 sourceRepos 不匹配、operation 非 SUCCESS、远端 `.env`/镜像/health/HTTP/release-info/运行控制台任一缺失时不得判定发布成功。

## 收尾状态

completed。task-closeout apply、运行控制台主路径恢复、任务临时 release worktree 删除和最终状态更新均已完成。

## 最终收尾验证

- `task.md` 当前状态为 `completed`。
- 运行控制台已恢复到维护仓主路径并通过 `/actuator/health`。
- 本任务临时 worktree 根 `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260711t` 已删除，无剩余 Git worktree 注册。
- 任务目录仅保留 `task.md`、`execution-log.md`、`verification-report.md`。
