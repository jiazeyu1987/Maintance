# 20260829 优化 deploy 控制文件上传执行日志

## Log

- BDD: deploy 控制文件上传合并 -> Given deploy 主段需要上传多个小控制文件，When publish-test 执行 deploy-release，Then 控制文件应通过单个归档上传并在远端校验关键文件，不应逐个 `scp` 放大启动开销。
- GREEN: experience-preflight -> PASS，命中发布链路批量化、secret redaction 和 PowerShell 编排门禁；本轮只做本地脚本/合同测试，不执行真实发布、服务器写入或数据库写入。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_uploads_deploy_control_files_as_single_archive -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\red` -> FAIL，`1 failed`；旧实现缺少 `Copy-DeployControlFilesToServer`，控制文件仍分散上传。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py::test_publish_script_uploads_deploy_control_files_as_single_archive -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\green2` -> PASS，`1 passed in 0.07s`。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\sql-gate2` -> PASS，`50 passed in 0.19s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> PASS，`PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-deploy-control-file-upload\pytest-parent\regression2` -> PASS，`61 passed in 0.20s`。
- GREEN: `Get-Command tar,ssh,scp` -> PASS，本机工具存在。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-deploy-control-file-upload/task.md doc/tasks/20260829-optimize-deploy-control-file-upload/execution-log.md doc/tasks/20260829-optimize-deploy-control-file-upload/verification-report.md` -> PASS，仅 LF/CRLF warning。
- GREEN: implementation-commit -> PASS，`ff1368a`（`任务: 优化deploy控制文件上传`），仅提交 `ops/deploy/publish-int-ruoyi.ps1` 与 `scripts/tests/test_release_sql_preflight_gate.py`。
- GREEN: task-closeout-cleanup preview/apply -> PASS，仅清理本任务 `pytest-parent` 临时产物。
- GREEN: project-experience-consolidation -> PASS，更新 deploy 控制文件上传门禁、经验索引与 request-command-log 条目。
