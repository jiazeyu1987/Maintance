# Bug Regression Evidence

## Bug Summary

独立运行控制台在上一轮对齐后仍有若干与原 IntRuoyi 运行控制台不一致的行为：`release-status` 版本字段为空、`mark-release-tested` 未服务端解析当前测试服版本、非动作字段未严格拒绝、DCC `chainStatus` 未要求 `COMPLETE`、前端 payload 未完全按动作过滤。

## Expected Behavior

与原 IntRuoyi 运行控制台一致，同时保留独立应用不接入登录/角色/菜单权限的边界。

## Evidence

- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> FAIL，复现 `release-status` 字段为空、非动作字段未拒绝、DCC 非完整链未阻断。
- RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL，复现前端 payload 未按原版动作契约裁剪。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS。
- REGRESSION: `mvn -f backend/pom.xml test`、`pnpm --dir frontend typecheck`、`pnpm --dir frontend build` -> PASS。
