# 20260903 主系统与发票打印助手测试服发布

## Task Goal

再次将 IntRuoyi 主系统和 `E:\ProjectPackage\erp-invoice-voucher-print-assistant` 发票打印助手一起发布到测试服务器，主程序可通过 `18733` 端口打开查看发票打印助手。

## Milestones

1. 准备发布任务记录、读取经验门禁与服务器/发布文档。`completed`
2. 在本次专用临时发布 worktree 中构建并发布主系统到测试服。`completed`
3. 发布发票打印助手到测试服，并确认 `18733` 入口可访问。`completed`
4. 验证测试服真实运行态、版本信息、镜像 tag 与 release operation 状态。`completed`: 用户明确将本次验收范围调整为测试发布成功，不要求登录后菜单 iframe E2E。
5. 清理本任务临时发布 worktree，记录最终证据并完成收尾。`completed`

## Expected Verification

- 主系统同一 releaseTag 完成 `build-release -> publish-test`，且 `operation=SUCCESS`。
- manifest 存在且与发布目标提交一致。
- 测试服远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 与 releaseTag 一致。
- backend health 返回 `UP`，frontend HTTP 返回 `200`。
- 发票打印助手容器/服务运行，测试服 `18733` 端口 HTTP 可访问。
- 发票打印助手固定端口 `18733` 已由测试服运行态探针确认监听且受鉴权保护。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，本任务按既有发布链路执行，不采用临时绕过。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- Trigger: 测试服发布、主系统 `build-release -> publish-test`、发票打印助手固定端口 `18733`、临时 release worktree、PowerShell/SSH、真实运行态和页面验收。
- Preflight check: 先读取 `docs/experience-index.md`、`docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\login-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\worktree-memory.md`；发布前冻结维护仓、主系统仓和助手仓已提交 HEAD 到本轮专用 clean release worktree。
- Blocker: 任一发布输入无法冻结为 clean worktree、测试服存在目标版本漂移且未获授权恢复、`publish-test` preview 非测试服 `172.30.30.58`、manifest/sourceRepos dirty 或 commit 不匹配、operation 非 SUCCESS、远端 `.env IMAGE_TAG`/实际镜像/health/frontend HTTP/release-info/release lock/migration 任一缺失或不一致、助手非 `18733` 或直连未拒绝。
- Verification: 记录 releaseTag、build/publish operation、manifest 路径和摘要、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、backend health、frontend HTTP、release-info、release lock、migration failed/running、助手 systemd/container/listen/HTTP、worktree 清理结果。登录后入口 E2E 不在本次验收范围。
- Forbidden action: 禁止复用失败 releaseTag、禁止主工作区 dirty 内容进入发布包、禁止在 release worktree 临时改代码继续发布、禁止 `mark-tested`/`promote-prod`/`promote-backup` 或访问正式/备份服、禁止手工修改测试库/release lock/migration ledger/schema/业务数据、禁止记录密码/token/私钥/连接串/完整 `.env` 或 raw secret-bearing log。
- Evidence: 本任务 `execution-log.md`、`verification-report.md`、发布包 manifest、运行控制台 operation JSON、远端只读探针和 Playwright/HTTP 证据。

## Current Status

completed

用户于 2026-09-03 明确确认“测试发布成功就可以，不用进行E2E测试”。主系统 releaseTag `release-20260903-main-invoice-assistant-test-r260903b-r1` 已完成测试服 `build-release -> publish-test`；发票打印助手镜像 `erp-invoice-voucher-print-assistant:f077f49-r260903b` 已在测试服 `18733` 运行。本任务未执行登录后入口 E2E；`task-closeout-cleanup` preview/apply 已通过，`r260903a/r260903b` 的维护仓、主系统、助手 worktree 与状态目录均已删除。
