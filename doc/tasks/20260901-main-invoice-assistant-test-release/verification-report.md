# 20260901 主系统与发票打印助手测试服联合发布验证报告

## Verification Summary

- 状态：PASS，已完成。
- 目标：主系统与发票打印助手一起发布到测试服务器 `172.30.30.58`，主程序可通过 `18733` 助手入口打开查看。
- 结论：已完成测试服联合发布。主系统运行 releaseTag=`release-20260901-main-invoice-assistant-test-r260901a-r1`，发票打印助手运行 image tag=`ba55fb8`，真实 Playwright 已证明 `测试租户/aoteman` 可从 ERP 菜单打开助手 iframe。

## Evidence

- 冻结输入：主系统提交 `a1c5604b7f2135550e26289d882077163e0c9afa`；发票助手提交 `ba55fb8ddb5aa507d70e7d64f4a5d8c44a12179b`；维护仓提交 `7b3771aff09a2a91b856a923ba5ccac2240fa1fe`。三者均通过本轮 clean release worktree 发布，主工作区脏改动未进入发布包。
- 助手发布：artifact SHA256=`38ad2384eae2809baecc95581a8c9d4493d3789e5e2c81109c7a5ebf2ae7aa17`；测试服 `erp-invoice-voucher-print-assistant.service` active；容器 `erp-invoice-voucher-print-assistant:ba55fb8` running；`0.0.0.0:18733` LISTEN；直连 HTTP `403`。
- 主系统构建：`build-release` operation `op-2026-08-31T175950833708200Z-2bced8b6-7544-44f4-ba35-338702f541bf` 为 `SUCCESS`；manifest validator 通过；manifest `publishScope=code-only`，sourceRepos commit 均为 `a1c5604b7f2135550e26289d882077163e0c9afa` 且 `dirty=false`。
- 测试服发布：`publish-test` operation `op-2026-08-31T182540028464Z-a9c8f0fc-93ee-4808-b9f8-96b3215b2fc1` 为 `SUCCESS`；远端 `.env IMAGE_TAG` 与 releaseTag 一致；backend/frontend 实际镜像 tag 与 releaseTag 一致且 running。
- 运行态：backend health `{"status":"UP"}`；frontend HTTP `200`；`release-info.json` 的 releaseTag/packageId/sourceRepos 与本轮发布包一致。
- 数据库账本：release lock `test:test-release-20260901-main-invoice-assistant-test-r260901a-r1:release-20260901-main-invoice-assistant-test-r260901a-r1:APPLIED`；migration `APPLIED:2`、`SKIPPED_ALREADY_APPLIED:495`；`failed_running=0`；`global_running_locks=0`。
- 真实页面：Playwright 从 `http://172.30.30.58:8081` 登录 `测试租户/aoteman`，菜单链 `ERP 系统 / 财务管理 / 发票凭证打印` 可见；点击后票据接口 HTTP `200`、业务 code `0`；页面 URL `http://172.30.30.58:8081/erp/finance/invoice-voucher-print`；iframe 通过 `http://172.30.30.58:18733/auth/callback` 打开助手，助手页面渲染成功；console/page error 均为 `0`。
- 范围边界：本轮只执行测试服 `build-release -> publish-test`；未执行 `mark-tested`、`promote-prod`、`promote-backup`，未操作正式服或备份服。
- 收尾：本任务临时 artifact/helper 已清理；本轮维护仓、主系统、助手 release worktree 均已注销并删除；运行控制台会话已停止，`48181` 无监听；本轮 stateDir 已删除。
