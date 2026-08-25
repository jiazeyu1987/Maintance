# 执行日志

## BDD

- BDD: code-only 迁移依赖闭包必须在远程写入前阻断 -> Given code-only 会过滤 pending data migration，When 可执行 schema/menu/config/permission/seed 迁移直接或传递依赖该祖先，Then 计划必须返回 `BLOCKED_SCOPE_DEPENDENCY` 并输出最小依赖路径。
- BDD: 正式库 checksum 漂移不得被旧台账掩盖 -> Given target ledger 标记已应用但 checksum 与当前 manifest 不一致，When 生成 target-bound preflight plan，Then 计划必须阻断并要求正式 reconciliation，不得按旧状态放行。

## RED

- RED: `python -X utf8 -m pytest script/tests/test_release_preflight_plan.py -q` -> 14 passed, 3 errors；3 个 CLI 场景被 Windows 默认 pytest 临时目录 `C:\Users\BJB110\AppData\Local\Temp\pytest-of-BJB110` 的 `WinError 5` 阻塞，非业务断言失败。
- RED: 只读复核正式 r11 preflight -> `status=blocked`、`BLOCKED_SCOPE_DEPENDENCY=6`；正式库 `20260607_product_master_data` checksum 与 r11 manifest 不一致，当前流程无 reconciliation 入口。

## GREEN

- GREEN: `python -X utf8 -m pytest script/tests/test_release_preflight_plan.py -q --basetemp=D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260825-continue-release-blocker-fix/evidence/pytest-preflight` -> `17 passed`。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q --basetemp=D:/ProjectPackage/Int/IntRuoyiMaintance/doc/tasks/20260825-continue-release-blocker-fix/evidence/pytest-maintenance` -> `32 passed`。
- GREEN: maintenance 与 backend `release_preflight_plan.py` 字节一致，SHA-256 均为 `bea4af16614cc31d193328b0ab3022432c7ea68ddc1e7fbe3dc5a043302ed2a8`。

## 根因与范围结论

- 当前本地代码已经实现 scope-aware 依赖闭包，未发现可安全提交的代码缺陷；不引入 reconciliation fallback、忽略 checksum 或默认成功分支。
- 正式服剩余阻塞是历史迁移基线漂移：r11 manifest 的 `20260607_product_master_data` 与正式库 target checksum 不一致，后续依赖链因此被正确阻断。
- 未执行服务器写入、数据库写入、migration ledger 修改、发布、mark-tested、promote-prod、promote-backup 或失败 releaseTag 重试。

## Closeout

- task-closeout-cleanup preview: PASS；仅发现 pytest 临时证据文件，核心任务记录保留。
- task-closeout-cleanup apply: PASS；删除本任务 pytest 临时证据，保留 task.md 与 execution-log.md。
- 当前任务无生产代码提交；仅提交任务证据。

## Current Status

ready_for_closeout
