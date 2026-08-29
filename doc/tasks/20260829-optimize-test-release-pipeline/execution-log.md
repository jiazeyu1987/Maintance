# 20260829 优化测试服发布链路执行日志

- BDD: 发布前 SQL 晚失败前移 -> Given required SQL 中存在临时表 collation、短字段回填或破坏性清空风险, When 构建/发布前运行维护仓发布门禁, Then 风险必须在 build-release/publish-test 前失败并给出文件和规则，不得等到远端测试库执行后才失败。
- BDD: publish-test required SQL 批量处理 -> Given release package 包含数百条 required SQL, When publish-test 上传并登记迁移状态, Then 脚本应批量上传和批量登记可批量化状态，保留每个 SQL 的执行开始/成功/失败证据，减少逐条 SSH/MySQL 启动开销。
- BDD: 发布日志脱敏与心跳 -> Given publish-test 输出 SSH/MySQL/Docker 命令和长耗时阶段, When operation log 记录命令与进度, Then 日志不得泄露明文密码，并应输出当前阶段、总数、批次或当前文件进度。
- GREEN: experience-preflight -> PASS，本任务只修改本地维护仓脚本/测试/文档和必要的发布门禁，不执行真实服务器发布、生产操作、备份、恢复或数据库写入。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\red` -> FAIL，新增 3 个测试命中当前脚本仍逐文件上传 required SQL、逐条写入 `SKIP_ALREADY_APPLIED` 状态、SSH 日志/异常未脱敏。
- 修复动作：`Copy-RequiredDatabaseSqlScriptsToServer` 改为生成 `required-sql-<releaseTag>.tar`、一次 `scp` 到远端 `required-sql.tar` 后 `tar -xf` 解包并检查文件数；新增 `Invoke-ReleaseMigrationStateBatchUpdate`，`SKIP_ALREADY_APPLIED` 改为批量 upsert；`Invoke-SshCommand` 和 `Invoke-SshCapture` 使用 `Protect-ReleaseSensitiveText` 脱敏显示命令、输出和异常。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\green` -> PASS，`42 passed in 0.21s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\regression` -> PASS，`53 passed in 0.21s`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-test-release-pipeline/task.md doc/tasks/20260829-optimize-test-release-pipeline/execution-log.md` -> PASS，仅 LF/CRLF warning。
- GREEN: tool-preflight -> PASS，本机 `tar.exe`、`ssh.exe`、`scp.exe` 存在。
- COMMIT: implementation -> `9c5d64f`（`任务: 优化测试服发布链路`），提交范围仅 `ops/deploy/publish-int-ruoyi.ps1` 与 `scripts/tests/test_release_sql_preflight_gate.py`。
- REGRESSION-BLOCKED: `python -X utf8 -m pytest scripts\tests\test_deploy_precheck_report_contract.py scripts\tests\test_runtime_control_frontend_deploy_contract.py scripts\tests\test_frontend_version_badge_contract.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\release-adjacent` -> FAIL，`test_deploy_precheck_report_contract.py` 2 passed，但两个前端合同文件因本任务前已有 `frontend/src/App.vue`、`frontend/package.json` 删除状态报 `FileNotFoundError`。该阻塞不属于本任务改动，未恢复或覆盖并行脏改动。
- GREEN: task-closeout-cleanup preview -> PASS，状态 `ready`，仅计划清理本任务 `pytest-parent` 临时产物。
- GREEN: task-closeout-cleanup apply -> PASS，状态 `applied`，保留 `task.md`、`execution-log.md`、`verification-report.md`。
- GREEN: project-experience-consolidation -> PASS，长期经验合并到 `docs/release-build-preflight-lessons.md`，索引路由更新到 `docs/experience-index.md`。
- FINAL: task status -> completed；本任务未执行真实服务器发布、数据库写入、正式服、备份服、备份或恢复。
