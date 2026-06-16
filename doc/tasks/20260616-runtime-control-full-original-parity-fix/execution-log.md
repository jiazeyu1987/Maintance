# Execution Log

BDD: Linux-local 备份命令与原版一致 -> Given 独立控制台配置 `backupOps.executionMode=linux-local` / When 预览或执行 `backup-now|rollback-app|restore-data|rehearsal` / Then 命令必须使用 Linux 脚本和 `--mode --config --non-interactive --target-environment --selected-image-tag --selected-backup-id` 风格参数，不得继续提交 PowerShell `-Mode -NonInteractive` 参数。

BDD: 原版治理接口本地持久化 -> Given 独立控制台不接入芋道登录权限但仍暴露原版运行治理 API / When 创建告警、责任矩阵、事故并运行巡检 / Then 后续查询、确认、关闭、按 ID 获取必须返回同一批本地持久化事实，缺失记录必须明确失败，不得返回模拟成功。

BDD: 前端运行控制台暴露原版日志入口 -> Given 用户在独立运行控制台查看操作记录 / When 点击某条 operation 的日志操作 / Then 页面通过 `/admin-api/infra/runtime-control/operations/{id}/log` 展示真实日志或后端错误，不依赖登录、菜单权限或静默隐藏失败。

BLOCKER: experience-preflight -> 本任务不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入；因此无需通过高风险动作 preflight。若后续需要真实按钮操作，必须另行记录 `GREEN: experience-preflight -> PASS` 并获得授权。

RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalGovernanceParityTest test` -> FAIL，当前独立版 `linux-local` 备份预览仍提交 `-Mode/-NonInteractive/-SelectedImageTag/-OperatorName`，并且巡检、告警、事故接口没有按原版持久化。

RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL，前端缺少 `getRuntimeControlOperationLog` 等原版运行治理 API wrapper 和操作日志入口。

GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalGovernanceParityTest test` -> PASS，Linux-local 参数、巡检/告警/责任矩阵/事故持久化和原版向导场景通过。

GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS，前端原版运行治理 API wrapper 和操作日志入口契约通过。

GREEN: `pnpm --dir frontend typecheck` -> PASS。

GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS。

GREEN: `mvn -f backend/pom.xml test` -> PASS，14 tests。

GREEN: `pnpm --dir frontend build` -> PASS。

GREEN: `python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260616-runtime-control-full-original-parity-fix --mode preview` -> PASS，无删除项、无阻塞、无警告。

GREEN: `python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260616-runtime-control-full-original-parity-fix --mode apply` -> PASS，无删除项、无阻塞、无警告。
