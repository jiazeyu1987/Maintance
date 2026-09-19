# 备份恢复实现静态验证报告

## 结论

本轮仅完成本地代码实现与静态验证，未执行 E2E、未访问测试服务器、未进行真实备份或恢复演练。

静态验证结论：通过。

## 已验证命令

- `mvn -pl yudao-module-infra -Dtest=RuntimeRestoreCandidateServiceImplTest test`：PASS，16 个用例通过。
- `mvn -pl yudao-module-infra -DskipTests compile`：PASS。
- `python -m py_compile script/backup-ops/linux/backup_ops_linux.py`：PASS。
- `python -m pytest --basetemp E:\Temp\backup-restore-pytest script/tests/test_backup_ops_linux_runtime_ports.py -q`：PASS，45 个用例通过。
- `pnpm ts:check`：PASS。
- `pnpm exec prettier --check src/api/infra/runtimeControl/index.ts src/views/infra/runtime-control/index.vue src/views/infra/runtime-control/components/OpsCandidatePicker.vue`：PASS。
- `git diff --check`：PASS。
- `task-closeout-cleanup preview/apply`：PASS，仅删除本任务临时 `test-plan.md`。

## 已完成能力

- 后端恢复候选拆分为 `REHEARSAL` 与 `CONTROLLED_RESTORE`。
- `REHEARSAL` 候选允许完整备份点进入隔离演练。
- `CONTROLLED_RESTORE` 候选必须具备 `rehearsalStatus=PASSED` 与 `lastRehearsedAt`。
- `restore-data` 和 `mark-release-tested` 只能绑定正式恢复候选，不能绑定演练候选。
- 候选 API 暴露 `manifestDigest`、`chainDigest`、`sourceFingerprint`、`targetFingerprint`。
- 前端恢复候选按动作过滤，避免演练、正式恢复和标记测试混选。
- `backup-now` 前端显式选择 `FULL` / `INCREMENTAL`，后端 linux-local 参数链传递 `--backup-kind`。
- linux-local 脚本校验请求备份类型与配置的 MySQL 备份策略一致，不一致时阻断。

## 未验证边界

- 未验证真实测试服当前运行状态。
- 未执行几百 GB 全量/增量真实备份。
- 未执行隔离恢复演练。
- 未执行受控恢复。
- 未验证升级、降级、换硬件、换数据盘、换 NAS、密钥轮换等运行态矩阵。
- 未验证真实 RTO/RPO。
- 未执行 Git 提交/推送；项目完成态仍需在确认提交范围后处理。
