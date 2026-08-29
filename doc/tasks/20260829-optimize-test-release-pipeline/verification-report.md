# 20260829 优化测试服发布链路验证报告

## Result

PASS with boundary.

## Implemented Optimization

- required SQL 远端上传从逐文件 `scp` 改为一次 tar 归档上传并远端解包校验。
- `SKIP_ALREADY_APPLIED` 迁移状态从逐条远端 MySQL 写入改为批量 upsert。
- SSH command/capture 的日志输出和异常文本统一脱敏，避免 `mysql -p...` / `MYSQL_PWD=...` 原文进入 operation log。

## Verification

- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\red` -> FAIL，3 个新增合同测试命中旧实现。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\green` -> PASS，`42 passed in 0.21s`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\regression` -> PASS，`53 passed in 0.21s`。
- PowerShell AST parse: `PSSCRIPT_PARSE_OK`。
- `git diff --check`: PASS，仅 LF/CRLF warning。
- Tool preflight: `tar.exe`、`ssh.exe`、`scp.exe` present。

## Boundary

- 未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 相邻前端合同测试因本任务前已有 `frontend/` 删除状态失败，未作为本次优化阻塞：`frontend/src/App.vue`、`frontend/package.json` 缺失。

## Commits

- Implementation: `9c5d64f`（`任务: 优化测试服发布链路`）。

## Closeout

- task-closeout-cleanup preview/apply: PASS。
- project-experience-consolidation: PASS，经验已合并到发布前置经验文档并更新索引。
