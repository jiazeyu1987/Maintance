# 20260829 优化测试服发布链路

## Task Goal

优化仅测试服发布链路，优先减少下次发布的失败等待时间和重复远端调用耗时；本次不降低发布验收标准，不引入 mock、fallback、手工改库或跳过验证。

## Milestones

1. 启动门禁与任务文档：建立任务目录、摘取发布/构建/PowerShell/worktree 经验门禁，记录 BDD 与预期验证。
2. 发布前 SQL 门禁前移：把已知 required SQL 晚暴露问题转换为 build/publish 前静态合同测试。
3. publish-test 批量化优化：减少 required SQL 上传/迁移状态入账的逐条 SSH/MySQL 开销，同时保留单文件状态和失败证据。
4. 发布日志与心跳优化：增强耗时阶段进度、结构化错误和敏感命令脱敏。
5. 回归验证与证据记录：运行目标测试，记录 RED/GREEN/REGRESSION、风险和剩余事项。

## Expected Verification

- 新增/更新的测试先能复现既有耗时或晚失败风险，再由实现转绿。
- 发布 SQL 门禁覆盖 collation、短字段回填长度、非破坏性清空和现有迁移策略。
- publish-test 批量化逻辑具备单元/静态合同覆盖，且不改变 releaseTag、manifest、运行态验收门禁。
- 日志输出不得包含明文 MySQL 密码；耗时阶段至少输出文件数/批次/当前 SQL 进度。
- `git diff --check` 通过；只提交本任务相关文件。

## 经验门禁

- 测试服发布范围：仍只允许单一 releaseTag 的 `build-release -> publish-test`，失败后必须修复并重建新 releaseTag。
- required SQL：可在发布前静态判断的问题必须前移；临时表文本列必须显式 collation，短字段回填必须有长度守卫，禁止 `TRUNCATE TABLE` 破坏性清空。
- publish-test：不得重复提交同一 operation；长时间 RUNNING 必须根据 operation 状态、日志 mtime 和远端进度判断。
- 日志脱敏：发布脚本输出命令前必须脱敏 `mysql -p...`、NAS 密码等敏感参数，原始 secret-bearing 日志不得写入任务证据。
- PowerShell：全程显式 UTF-8；PowerShell 5.1 不使用 `&&`；外部命令必须检查退出码或后置断言。
- worktree：发布优化只修改维护仓脚本/测试和必要 app SQL 门禁测试，不清理或改动并发 release worktree。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。
2. 发布前 SQL 门禁前移：completed，新增合同测试固定 required SQL 上传/状态登记/日志脱敏优化要求。
3. publish-test 批量化优化：completed，required SQL 上传改为 tar 归档一次传输，`SKIP_ALREADY_APPLIED` 状态改为批量 SQL 写入。
4. 发布日志与心跳优化：completed，SSH command/capture 的日志与异常文本统一使用 `Protect-ReleaseSensitiveText` 脱敏；归档上传输出文件数和远端解包阶段。
5. 回归验证与证据记录：completed，目标发布合同测试通过；相邻前端合同测试因本任务前已有 `frontend/` 删除状态阻塞，已记录为边界。

## Implementation Evidence

- Commit: `9c5d64f`（`任务: 优化测试服发布链路`）。
- Changed files:
  - `ops/deploy/publish-int-ruoyi.ps1`
  - `scripts/tests/test_release_sql_preflight_gate.py`
- 核心优化：
  - `Copy-RequiredDatabaseSqlScriptsToServer` 从逐文件 `scp` 改为本机 `tar` 打包、单次上传、远端解包并检查 SQL 文件数。
  - 新增 `Invoke-ReleaseMigrationStateBatchUpdate`，将 `SKIP_ALREADY_APPLIED` 迁移状态合成一次远端 MySQL 写入。
  - `Invoke-SshCommand` / `Invoke-SshCapture` 对显示命令、输出和异常文本脱敏，避免 `mysql -p...` 或 `MYSQL_PWD=...` 原文进入 operation log。

## Verification Evidence

- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\red` -> FAIL，新增 3 个测试分别命中逐文件 required SQL 上传、逐条 `SKIP_ALREADY_APPLIED` 状态写入、SSH 日志/异常未脱敏。
- GREEN: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\green` -> PASS，`42 passed in 0.21s`。
- REGRESSION: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_release_package_slimming.py scripts\tests\test_publish_release_lock_cleanup.py tests\test_code_only_required_sql_contract.py -q --basetemp doc\tasks\20260829-optimize-test-release-pipeline\pytest-parent\regression` -> PASS，`53 passed in 0.21s`。
- GREEN: PowerShell AST parse `ops\deploy\publish-int-ruoyi.ps1` -> `PSSCRIPT_PARSE_OK`。
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_sql_preflight_gate.py doc/tasks/20260829-optimize-test-release-pipeline/task.md doc/tasks/20260829-optimize-test-release-pipeline/execution-log.md` -> PASS，仅既有 LF/CRLF warning。
- GREEN: 本机 `tar.exe`、`ssh.exe`、`scp.exe` 可用。

## Verification Boundary

- `scripts\tests\test_runtime_control_frontend_deploy_contract.py` 与 `scripts\tests\test_frontend_version_badge_contract.py` 因当前维护仓 `frontend/src/App.vue`、`frontend/package.json` 已处于本任务前删除状态而失败；本任务未恢复、覆盖或提交这些并行脏改动。
- 本次未执行真实 `build-release`、`publish-test`、服务器写入、数据库写入、正式服、备份服、备份或恢复。

## Closeout Evidence

- task-closeout-cleanup preview/apply 均通过，仅清理本任务 `pytest-parent` 临时产物；保留 `task.md`、`execution-log.md`、`verification-report.md`。
- 已按 project-experience-consolidation 规则合并长期经验到 `docs/release-build-preflight-lessons.md`，并在 `docs/experience-index.md` 增加关键词路由。
- 最终状态：completed。
