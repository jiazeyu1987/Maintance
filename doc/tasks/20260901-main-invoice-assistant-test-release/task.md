# 20260901 主系统与发票打印助手测试服联合发布

## Task Goal

再次将主系统 `E:\IntRuoyi` 与发票打印助手 `E:\ProjectPackage\erp-invoice-voucher-print-assistant` 一起发布到测试服务器 `172.30.30.58`；主程序前端通过 ERP 菜单打开助手 `18733` 端口。

## Milestones

1. 启动门禁与任务文档：创建任务记录，摘取发布、服务器、PowerShell、worktree、登录/E2E、发票助手入口门禁。
2. 发布输入冻结：确认主系统、维护仓、助手仓库的已提交 HEAD；未提交改动不得进入发布包。
3. 助手构建与部署：从助手 clean release worktree 构建 artifact，部署到测试服 `18733` 并验证服务运行。
4. 主系统构建与发布：从主系统和维护仓 clean release worktree 执行仅测试服 `build-release -> publish-test`。
5. 真实运行态与页面验证：验证主系统 releaseTag、manifest、镜像、health、HTTP、migration ledger，并用 Playwright 验证 ERP 菜单打开助手 iframe。
6. 收尾：记录验证报告，清理本任务临时 artifact 和 worktree，沉淀必要经验，标记 completed。

## Expected Verification

- BDD: Given 主系统与发票打印助手各自存在可发布的已提交版本，When 本轮发布到测试服，Then 测试服主程序运行在同一 releaseTag，助手监听 `18733`，授权用户可从 ERP 菜单打开助手，未授权访问被拒绝。
- 发布成功必须同时核：operation SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health `UP`、frontend HTTP `200`、release-info、release lock、migration ledger。
- 助手成功必须同时核：artifact 来源提交、服务 active、容器 running、`18733` LISTEN、直连 403、主程序 iframe 可达。
- 本轮只发布测试服；禁止执行 `mark-tested`、`promote-prod`、`promote-backup`；禁止将未提交改动、未跟踪文件或脏工作区内容纳入发布包。

## 经验门禁

- Trigger: 仅测试服发布、发票打印助手 `18733`、主系统 iframe/ticket 入口、PowerShell/SSH 编排、clean worktree 构建、Playwright 登录验收。
- Preflight check: 先读取 `E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\powershell-memory.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\login-access.md`、`docs\test-release-preflight.md`、`docs\release-build-preflight-lessons.md`；高风险动作前在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`。
- Blocker: 缺测试服访问方式、发布脚本参数不完整、releaseTag 漂移、manifest/sourceRepos dirty、远端镜像 tag 不一致、health/HTTP 失败、migration FAILED/RUNNING、助手端口被未知服务占用、Playwright 无法确认目标租户或菜单权限。
- Verification: 记录 worktree 路径、目标提交、构建/发布命令、releaseTag、manifest 摘要、远端运行态、migration ledger、助手 runtime、Playwright 页面证据、收尾清理结果。
- Forbidden action: 禁止操作正式服/备份服，禁止复用旧 releaseTag 结果，禁止手工修改测试库或跳过 SQL，禁止 mock 页面或 API-only 冒充真实页面，禁止记录明文密码/token/私钥/连接串。
- Evidence: `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\powershell-memory.md`、`E:\IntRuoyi\docs\worktree-memory.md`、`E:\IntRuoyi\docs\login-access.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Cleanup Candidates

- `doc/tasks/20260901-main-invoice-assistant-test-release/artifacts/`

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。
2. 发布输入冻结：completed。
3. 助手构建与部署：completed。
4. 主系统构建与发布：completed。
5. 真实运行态与页面验证：completed。
6. 收尾：completed。

### Latest Blocker

暂无。主系统已用 `release-20260901-main-invoice-assistant-test-r260901a-r1` 发布到测试服，助手已基于冻结提交 `ba55fb8` 部署到 `18733`；远端运行态、发布账本、Playwright 主程序入口验证、任务 artifact 清理、运行控制台停止、release worktree 删除和状态目录清理均已通过。
