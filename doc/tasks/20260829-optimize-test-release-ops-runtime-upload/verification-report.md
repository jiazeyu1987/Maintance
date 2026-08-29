# 20260829 优化测试服发布 ops runtime 上传验证报告

## Result

PASS with boundary.

## Scope

- Target script: `ops\deploy\publish-int-ruoyi.ps1`
- Target tests: `scripts\tests\test_release_sql_preflight_gate.py`
- Boundary: 不执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。

## Implemented Optimization

- runtime-control ops package 从 5 次 `Copy-ToServer` 收敛为 1 次 tar 归档上传。
- 继续排除 `backup-ops.secrets.json`，远端解包后校验关键运行脚本存在。
- 远端保留 `config` 目录，不删除可能存在的 secrets 配置。

## Verification

- RED: `test_publish_script_uploads_ops_runtime_package_as_single_archive` -> FAIL，旧实现没有 `ops-runtime.tar`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-ops-runtime-upload\pytest-parent\green` -> PASS，`44 passed in 0.17s`。
- REGRESSION: 发布合同测试集合 -> PASS，`55 passed in 0.17s`。
- PowerShell AST parse: `PSSCRIPT_PARSE_OK`。
- `git diff --check`: PASS，仅 LF/CRLF warning。
- Tool preflight: `tar.exe`、`ssh.exe`、`scp.exe` present。

## Boundary

- 未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。
- 未恢复、覆盖或提交仓库中既有的并行脏改动和 `frontend/` 删除状态。

## Commits

- Implementation: `f33a8ec`（`任务: 优化发布ops运行包上传`）。

## Closeout

- task-closeout-cleanup preview/apply: PASS。
- project-experience-consolidation: PASS，经验已合并到发布前置经验文档并更新索引。
