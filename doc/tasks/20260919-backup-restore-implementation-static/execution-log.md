# 备份恢复实现静态验证执行日志

## 2026-09-19

BDD: 候选包按用途拆分 -> Given 测试服备份点恢复集完整且校验文件存在 When 管理端查询恢复候选 Then 同一备份点同时暴露 REHEARSAL 候选和 CONTROLLED_RESTORE 候选，前者用于恢复演练，后者仅在演练 PASSED 且 lastRehearsedAt 存在时可用于正式恢复。

BDD: 正式恢复拒绝未演练包 -> Given 备份点尚无 PASSED 演练证据 When 用户点击恢复数据并选择该备份点 Then 后端阻断提交，前端只允许选择 CONTROLLED_RESTORE 候选且显示阻断原因。

BDD: 备份按钮显式选择类型 -> Given 用户点击立即备份 When 操作对话框打开 Then 用户必须选择 FULL 或 INCREMENTAL，提交参数包含 backupKind，不能静默使用默认备份类型。

GREEN: experience-preflight -> PASS, 已读取当前任务适用 AGENTS、经验索引与备份恢复长期文档；本轮限制为本地代码和静态验证，不执行 E2E、服务器、数据库、MinIO 或远程写入。

RED: mvn -pl yudao-module-infra -Dtest=RuntimeRestoreCandidateServiceImplTest test -> FAIL, 恢复候选 VO 缺少 candidateType、rehearsalStatus、lastRehearsedAt，证明当前代码尚未表达“演练候选/正式恢复候选”拆分契约。

GREEN: mvn -pl yudao-module-infra -Dtest=RuntimeRestoreCandidateServiceImplTest test -> PASS, 16 个用例通过；恢复候选已拆分为 REHEARSAL 与 CONTROLLED_RESTORE，restore-data 拒绝 REHEARSAL 候选。

GREEN: pnpm ts:check -> PASS, 运行控制台前端类型检查通过；恢复候选按动作过滤，backup-now payload 包含 backupKind。

GREEN: pnpm exec prettier --check src/api/infra/runtimeControl/index.ts src/views/infra/runtime-control/index.vue src/views/infra/runtime-control/components/OpsCandidatePicker.vue -> PASS, 本次前端修改文件格式检查通过。

GREEN: python -m py_compile script/backup-ops/linux/backup_ops_linux.py -> PASS, linux-local 备份恢复脚本语法检查通过。

GREEN: python -m pytest --basetemp E:\Temp\backup-restore-pytest script/tests/test_backup_ops_linux_runtime_ports.py -q -> PASS, 45 个脚本静态/契约用例通过；backup-now 显式 backupKind，配置策略不匹配时阻断。

GREEN: mvn -pl yudao-module-infra -DskipTests compile -> PASS, yudao-module-infra 主代码编译通过。

GREEN: git diff --check -> PASS, 后端与前端本任务修改文件无 whitespace 错误。

BLOCKER: runtime-e2e -> 本轮用户明确要求不做 E2E；未访问测试服务器，未执行真实备份、恢复演练、受控恢复、数据库/MinIO 写入、重启或发布。实际几百 GB、升级/降级/换机/换硬件能力仍需后续运行态验证。
