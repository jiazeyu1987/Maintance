# 20260829 发票打印助手测试服部署验证报告

## Verification Summary

- 状态：completed。
- 目标：将 `E:\ProjectPackage\erp-invoice-voucher-print-assistant` 发布到测试服务器，并通过主程序 `18733` 助手入口打开查看。
- 结论：PASS。助手服务已部署到测试服 `172.30.30.58:18733`；主程序测试服 releaseTag `release-20260830-invoice-assistant-test-r260830k-r1` 已完成 `build-release -> publish-test`；授权账号可从 ERP 菜单打开助手，未授权账号看不到菜单，助手直连返回 403。

## Evidence

- Helper artifact：`invoice-voucher-print-assistant-92d47d5.tar`，size `296960` bytes，SHA256 `E5AED829A71D262FC445E162755F098D97CD16F9F71B43DF923B618A89D81491`；源提交 `92d47d54ca7ff831264a1b97742e0c4a174f15fa`。
- Helper runtime：systemd `erp-invoice-voucher-print-assistant.service` active；容器镜像 `erp-invoice-voucher-print-assistant:92d47d5` running；`ss` 显示 `0.0.0.0:18733` LISTEN；直连 `http://127.0.0.1:18733/` 返回 403。
- Main release：`release-20260830-invoice-assistant-test-r260830k-r1`；构建耗时 `1121.255s`，发布耗时 `307.292s`；未执行正式服/备份服推广。
- Manifest：本地发布包 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260830-invoice-assistant-test-r260830k-r1\manifest.json` 存在，`publishScope=code-only`，backend/frontend sourceRepos 均为 `60fb439d75659a4a9276e39a241f28f005292218` 且 dirty=false。
- Runtime：测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag 均为 `release-20260830-invoice-assistant-test-r260830k-r1`；backend health `UP`；frontend HTTP `200`；远端 `/release-info.json` releaseTag/sourceRepos 与 manifest 一致。
- Migration：release lock `test-release-20260830-invoice-assistant-test-r260830k-r1` 状态 `APPLIED`；migration ledger `APPLIED=4`、`SKIPPED_ALREADY_APPLIED=482`、`FAILED/RUNNING=0`；发票打印权限与测试租户用户迁移均 `APPLIED`。
- Playwright：`invoice-voucher-print-permission-real.e2e.cjs` PASS；授权 `测试租户/aoteman` 通过 ERP 菜单加载助手 iframe；无权限 `测试租户/dccmatrixregsvc` 不包含目标权限且看不到菜单；直连助手 403。截图已作为任务临时产物在 closeout 清理，结果摘要保留在本报告和执行日志。
- Timing notes：主要耗时来自前端 `pnpm build:test` 约 6m59s、Maven 后端约 4m57s、Docker context 约 90s、清理/打包/NAS 上传约 85s、publish-test 约 5m07s。
- Closeout：`task-closeout-cleanup --mode apply` 已删除本任务 `artifacts` 临时目录；任务拥有的 helper、主程序和维护仓临时发布 worktree 已删除。
