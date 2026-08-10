# 2026-08-11 当前 HEAD 仅测试服发布验证报告

## 结论

- 结果：PASS，最终 releaseTag 为 `release-20260811-intmain-head-test-r260811a-r2`。
- 发布范围：仅测试服；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 构建来源：维护仓冻结 HEAD `697f81688bf80527e9a3a7e4a680e8656f0e05b0`，主程序冻结 HEAD `5699b804576851ea8cdebf36045d381f044fb5e8`；两个构建目录均为本轮专用 clean release worktree。

## 构建与发布

- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m`，构建前后 clean。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260811a-release-app`，构建前后 clean。
- 维护控制台构建：`scripts\build.ps1` PASS，Maven tests 26 passed，JAR SHA256 `ae2b9cc2c0b4f3ed7119e27977e96ad2832c0efd6cc203b7c636c227e8ab1e37`。
- build-release r2：operation `op-2026-08-10T180157565021500Z-7a75427f-088a-4ec9-8fb7-74ac81973a84`，SUCCESS。
- manifest：`MANIFEST_VALIDATION_PASSED`；sourceRepos commit 均为 `5699b804576851ea8cdebf36045d381f044fb5e8`，dirty=false；变更说明包含 `发布包：release-20260811-intmain-head-test-r260811a-r2` 与 `组件范围：intruoyi`。
- publish-test r2：operation `op-2026-08-10T184419479334Z-b3dd4c79-c0f1-4a8c-bc32-5a930700a511`，SUCCESS。

## 运行态验收

- 测试服 `.env IMAGE_TAG`：`release-20260811-intmain-head-test-r260811a-r2`。
- 实际镜像：`intruoyi-backend:release-20260811-intmain-head-test-r260811a-r2`、`intruoyi-frontend:release-20260811-intmain-head-test-r260811a-r2`。
- 容器状态：backend/frontend 均 running。
- 健康检查：backend `{"status":"UP"}`，frontend HTTP 200，PDF worker HTTP 200 application/javascript。
- release-info：测试服 `/release-info.json` releaseTag、sourceRepos、dirty=false 和变更说明均匹配最终包。
- 数据库发布状态：test release lock=`APPLIED`；migration counts=`APPLIED 5`、`SKIPPED_ALREADY_APPLIED 419`，无 FAILED/RUNNING。
- 页面验收：Playwright CLI 打开测试服前端登录页与本机运行控制台；运行控制台可见 publish-test SUCCESS、软件版本 `2026.06.0`、测试服 releaseTag、发布包和组件范围变更说明。

## 问题与经验

- 已记录 I001-I010，覆盖 dirty worktree、worktree 初始化误读、pnpm ignored builds、端口空 PID、前端依赖缺失、manifest 参数误用、SSH/MySQL quoting、Playwright 依赖/浏览器缓存和 snapshot 敏感文本。
- 已沉淀到既有经验文档：`docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md`、`docs/powershell-preflight-lessons.md`、`docs/experience-index.md`。
- Secret scan：任务目录中原始 MySQL 密码、默认登录密码、password/token/secret 明文形态命中 0；publish-test 原始日志未提交，仅保留脱敏摘要。

## 收尾状态

- 当前状态：completed。
- closeout cleanup：preview/apply 已通过；仓库内一次性证据与临时 Playwright 输出已清理，只保留三份正式任务记录。
- 外部清理：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a\m`、`D:\IntRuoyiWorktree\r260811a-release-app`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260811a-state` 均不存在；worktree 注册无 `r260811a`；`48182` 无监听。
- 清理后复核：测试服仍运行 `release-20260811-intmain-head-test-r260811a-r2`，backend/frontend 镜像 tag 匹配，backend health=`UP`，frontend HTTP 200。
