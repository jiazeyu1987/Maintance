# Verification Report

## Summary

Main release and assistant deployment passed on the test server. Final authenticated ERP-menu-to-assistant iframe E2E is blocked because the current process does not have `INVOICE_ASSISTANT_E2E_PASSWORD`.

## Evidence

- Main releaseTag: `release-20260903-main-invoice-assistant-test-r260903b-r1`.
- Build operation: `op-2026-09-03T003416026425200Z-a77fef3a-6a7c-4e45-8b6e-9df3f3ca67c3` -> `SUCCESS`.
- Publish operation: `op-2026-09-03T004932354398500Z-004c967b-9fcd-47a5-b126-69aac9485585` -> `SUCCESS`.
- Manifest: `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260903-main-invoice-assistant-test-r260903b-r1\manifest.json`, `publishScope=code-only`, backend/frontend sourceRepos `65980ea01751c09146e2f0996a65689fc834ee44`, `dirty=false`.
- Test server: `.env IMAGE_TAG`, backend image and frontend image all match `release-20260903-main-invoice-assistant-test-r260903b-r1`; backend health is `UP`; frontend HTTP is `200`; `release-info.json` contains the releaseTag.
- Release state: lock status `APPLIED`; migration ledger `APPLIED:1`, `SKIPPED_ALREADY_APPLIED:501`, `FAILED/RUNNING=0`.
- Assistant artifact: `invoice-assistant-f077f49-r260903b-source.tar`, bytes `358400`, SHA256 `E67850143F9944BF2895A8D445002DDC5BF87745407D3DAD57C067DF530B7AA6`; remote SHA matched.
- Assistant runtime: image `erp-invoice-voucher-print-assistant:f077f49-r260903b`, systemd `active`, container `running`, `0.0.0.0:18733` listening, direct root HTTP `403`, `KINGDEE_RUNTIME_DIR` set and `KINGDEE_ENV_PATH` absent.
- E2E scope: 用户明确确认本次“测试发布成功即可，不用进行 E2E 测试”。因此不执行登录后菜单 iframe 验收；此前脚本仅记录了缺少 `INVOICE_ASSISTANT_E2E_PASSWORD` 的前置条件，未登录、未写业务数据、未记录凭据、未用 API-only 替代页面验收。
- Closeout: `task-closeout-cleanup` preview/apply 已通过；本任务 `r260903a/r260903b` 的维护仓、主系统、助手临时发布 worktree、残留依赖目录和 runtime-control state 均已删除。
