# 20260831 发票打印助手独立测试服发布验证报告

## Verification Summary

- 状态：completed。
- 目标：将 `E:\ProjectPackage\erp-invoice-voucher-print-assistant` 独立发布到测试服务器 `172.30.30.58:18733`。
- 结论：PASS。发票打印助手已独立发布到测试服，镜像从 `erp-invoice-voucher-print-assistant:92d47d5` 更新为 `erp-invoice-voucher-print-assistant:ba55fb8`；主程序未重新发布，`8081/48081` 仍保持可达。

## Evidence

- Source commits：助手仓库当前发布输入为 `ba55fb8ddb5aa507d70e7d64f4a5d8c44a12179b`（`任务: 更新销售组织名称`）。用户要求先整理提交当前改动后再发布；本轮已基于 clean HEAD 发布，助手仓库 `main` 当前领先 `origin/main` 5 个本地提交。
- Local verification：发布 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\invoice-assistant-standalone-r260831d` 内 `node --check server.js`、`assistant-auth-static.cjs`、`container-deploy-static.cjs`、`fixed-port-static.cjs`、`sales-org-copy-static.cjs` 均 PASS。
- Artifact：`invoice-voucher-print-assistant-ba55fb8.tar`，size `317440` bytes，SHA256 `3E6B6502AE2CD88AB8F17512EFA3DE42F106C5FF740C435F903EC6E3E0FCD5AB`；远端 `sha256sum` 复核一致。
- Deployment：测试服构建镜像 `erp-invoice-voucher-print-assistant:ba55fb8` 并仅重启 `erp-invoice-voucher-print-assistant.service`；未执行 IntRuoyi 主程序 `build-release` / `publish-test`，未操作正式服或备份服。
- Runtime：测试服 systemd active；容器 `erp-invoice-voucher-print-assistant` image=`erp-invoice-voucher-print-assistant:ba55fb8`、state=`running`；`ss` 显示 `0.0.0.0:18733` LISTEN；systemd unit `ExecStart` 已指向 `ba55fb8`。
- HTTP：远端和本机访问助手根路径均为 HTTP 403，且本机页面包含“无权访问发票凭证打印助手”；测试服主程序 `http://172.30.30.58:8081/` HTTP 200，后端 `http://172.30.30.58:48081/actuator/health` HTTP 200 且 `status=UP`。
- Invalid evidence excluded：首次 inline SSH 命令被 PowerShell 提前解析，已作为 ISSUE-001 作废，不作为发布成功证据；最终证据来自 `invoke-remote-deploy.ps1` 的 UTF-8 LF stdin helper 和后续独立复核。
- Closeout：`task-closeout-cleanup` preview/apply 均 PASS，已删除本任务临时 artifacts；助手 release worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\invoice-assistant-standalone-r260831d` 已移除，`Test-Path=False`。
- Boundary：本次只独立发布助手服务，未发布 IntRuoyi 主程序，未执行 `build-release` / `publish-test` / `mark-tested` / `promote-prod` / `promote-backup`，未操作正式服或备份服，未记录明文凭据。
