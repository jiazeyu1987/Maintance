# 运行控制台原版一致性补齐

## Task Goal

将独立运行控制台中仍与原 IntRuoyi 不一致的行为补齐为原版逻辑：`release-status` 当前/已验证版本、`mark-release-tested` 服务端解析当前测试服版本、动作参数严格拒绝、恢复候选 DCC 链状态、后端动作文案、前端按动作提交字段。

## Milestones

- [x] 创建任务文档与经验门禁。
- [x] 编写原版差异回归测试并记录 RED。
- [x] 修正后端服务逻辑并记录 GREEN。
- [x] 修正前端 payload 契约并记录 GREEN。
- [x] 回归验证、收尾记录与提交。

## Expected Verification

- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- `mvn -f backend/pom.xml test`
- `python -X utf8 scripts\verify_contracts.py`
- `pnpm --dir frontend typecheck`
- `pnpm --dir frontend build`

## 经验门禁

- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：候选发布包、恢复候选和 tested 标记必须读取真实 manifest/checksum/tested/recoverySet 证据，缺少或不完整时 fail fast；本任务不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：前端只改提交契约与文案，不做额外视觉重设。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，按原版服务端契约收紧。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed

## Final Verification

- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS
- `python -X utf8 scripts\verify_contracts.py` -> PASS
- `pnpm --dir frontend typecheck` -> PASS
- `pnpm --dir frontend build` -> PASS
- `mvn -f backend/pom.xml test` -> PASS

## Cleanup Keep

- `doc/tasks/20260616-runtime-control-original-parity-fix/bug-regression-evidence.md`
- `doc/tasks/20260616-runtime-control-original-parity-fix/backend-api-evidence.md`
- `doc/tasks/20260616-runtime-control-original-parity-fix/frontend-feature-evidence.md`
