# 运行控制台当前一致性审计

## Task Goal

分析当前独立维护应用运行控制台与原 IntRuoyi 运行控制台逻辑的一致性，识别已对齐、独立化差异和仍需补齐的风险点。本任务只做静态审计与本地契约验证，不修改生产代码。

## Milestones

- [x] 创建任务文档与经验门禁。
- [x] 建立后端、前端、接口、脚本四类对比清单。
- [x] 运行本地契约验证命令。
- [x] 输出一致性验证报告。
- [x] 收尾记录。

## Expected Verification

- `python -X utf8 scripts\verify_contracts.py`
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- 静态比对原版与独立版运行控制台关键文件。

## 经验门禁

- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布包、tested 标记、恢复候选、DCC 链、manifest/checksum 等逻辑必须读取真实证据并 fail fast；本任务不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- 命中 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：本任务只审计前端契约与运行控制台风格一致性，不做视觉修改。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，本任务从原版源码和当前实现逐项对比。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed

## Final Verification

- `python -X utf8 scripts\verify_contracts.py` -> PASS
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS
- `pnpm --dir frontend typecheck` -> PASS

## Cleanup Keep

- `doc/tasks/20260616-runtime-control-current-consistency-audit/verification-report.md`
