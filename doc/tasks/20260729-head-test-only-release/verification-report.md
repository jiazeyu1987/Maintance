# 当前 HEAD 仅测试服发布验收报告

## 结论

PASS: 最终 releaseTag `release-20260729-sqlfix-test-r260729d-r1` 已完成仅测试服发布、真实运行态验收、经验沉淀和 closeout 清理。未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## 发布输入

- 维护仓 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260729d\m`，HEAD `4a77055f4a90209bae9bbba4fc2b75c03eb9aa88`，Git clean。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260729d-release-app`，HEAD `919122b6f72e2f0cf7e4cdb7f2ee913294af0473`，Git clean。
- 后端构建目录：`D:\IntRuoyiWorktree\r260729d-release-app\IntRuoyiBackend`。
- 前端构建目录：`D:\IntRuoyiWorktree\r260729d-release-app\IntRuoyiFronted`。
- Manifest sourceRepos：backend/admin-frontend commit 均为 `919122b6f72e2f0cf7e4cdb7f2ee913294af0473`，`dirty=false`。

## 构建与发布

- `build-release` operation：`op-2026-07-29T101921985772400Z-05210b94-fafa-43d9-990e-dca0ea15c7e1`，`SUCCESS`。
- 发布包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260729-sqlfix-test-r260729d-r1`。
- Manifest validator：`MANIFEST_VALIDATION_PASSED`。
- `publish-test` operation：`op-2026-07-29T103744548087400Z-d86c6a40-3508-43f9-933c-7c63af704bb3`，`SUCCESS`。
- Forbidden operation check：本 releaseTag 仅存在 `build-release` 与 `publish-test`，无正式服/备份服/mark-tested 动作。

## 运行态

- `.env IMAGE_TAG`：`release-20260729-sqlfix-test-r260729d-r1`。
- `intruoyi-backend` / `intruoyi-frontend` 镜像 tag：均为 `release-20260729-sqlfix-test-r260729d-r1`。
- 容器状态：backend/frontend running。
- Backend health：`{"status":"UP"}`，HTTP `200`。
- Frontend HTTP：`200`。
- PDF worker：HTTP `200 application/javascript`。
- Release lock：`APPLIED`。
- Migration：`APPLIED=7`、`SKIPPED_ALREADY_APPLIED=353`、`FAILED=0`。

## 页面与版本

- Playwright 使用本机 Chrome 打开测试服前端，页面标题为 `瑛泰管理系统 - 登录`。
- 运行控制台页面显示测试服版本 `release-20260729-sqlfix-test-r260729d-r1`。
- 运行控制台 `版本变更说明` 对话框显示：
  - `发布包：release-20260729-sqlfix-test-r260729d-r1`
  - `组件范围：intruoyi`
- `/admin-api/infra/runtime-control/release-status` 的 `testCurrentReleaseNotes` 与 Manifest sourceRepos 一致，`blockedReasons=[]`。

## 问题与经验

- 已记录 23 项问题，覆盖 Git/worktree、构建、manifest、required SQL、发布脚本、镜像/容器、健康检查、前端页面、运行控制台、日志脱敏、Playwright 浏览器缓存、重复操作、耗时点和 closeout 物理目录残留。
- 已更新长期经验入口：
  - `docs/release-build-preflight-lessons.md`
  - `docs/test-release-preflight.md`
  - `docs/powershell-preflight-lessons.md`
  - `docs/experience-index.md`

## Closeout

- task-closeout-cleanup preview/apply：`applied`，保留 `task.md`、`execution-log.md`、`verification-report.md`，无删除项，cleanup candidates 均已不存在。
- Release worktree 清理：维护仓 `r260729a/b/c/d`、主程序 `r260729a/app` 与 `r260729b/c/d-release-app`、状态目录 `r260729a/b/c/d-state` 均已删除。
- 清理验证：维护仓与主程序 `git worktree list --porcelain` 不再包含 `r260729a/b/c/d`；对应物理路径 `Test-Path=False`；无进程命令行引用本任务 release worktree。
- 运行控制台恢复：`http://127.0.0.1:48181/actuator/health` 返回 `UP`，PID `48676` 指向主维护路径。

## 剩余非发布阻塞

- 主程序修复 worktree `D:\IntRuoyiWorktree\r260729-sql-collation` 保留：本地提交 `919122b6f72e2f0cf7e4cdb7f2ee913294af0473` 已用于本次发布，但 GitHub push 仍返回 `Recv failure: Connection was reset`。
- 该阻塞不影响本次测试服运行态，但影响远端分支同步；后续网络恢复后需推送或按集成策略处理。
