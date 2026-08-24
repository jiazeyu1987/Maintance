# Execution Log

## User Intent

用户同意将近期发布问题前置到检查阶段，并要求优化发布前置门禁与构建依赖复用。

## Scope Boundary

- 本任务只修改 `D:\ProjectPackage\Int\IntRuoyiMaintance` 维护仓的正式脚本、测试和经验入口。
- 不操作服务器、不提交 `publish-test`、不修改正在运行的其他任务、worktree、operation、租户数据或默认展厅资源。

## BDD

- BDD: 发布前阻止 MySQL 临时表重复读取 -> Given required SQL 在同一语句或嵌套子查询重复读取同一 `tmp_*` 临时表；When 迁移策略门禁扫描 SQL；Then 门禁失败并指出文件、行号和 `MySQL temp table reopen risk`，后端构建不启动。
- BDD: 发布前阻止临时表隐式字符集排序规则 -> Given `CREATE TEMPORARY TABLE tmp_*` 含字符列但未声明 `COLLATE`；When 迁移策略门禁扫描 SQL；Then 门禁失败并要求显式 collation，避免远端库默认排序规则差异。
- BDD: 冻结 worktree 内复用前端依赖 -> Given `package.json`、`pnpm-lock.yaml`、Node/pnpm 版本和受信任构建依赖均与已记录状态一致；When build 脚本准备前端依赖；Then 复用现有 `node_modules`，不再次执行 `pnpm install`，状态不一致时直接执行一次冻结安装并重新校验。

## TDD Evidence

- GREEN: experience-preflight -> PASS；已读取 `docs/experience-index.md` 命中的发布/PowerShell 经验和 `E:\IntRuoyi\docs\powershell-memory.md`，本任务未执行服务器写入、发布、真实 E2E 或并发 operation/worktree 操作。
- RED: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -q` -> FAIL/ERROR；新增 SQL/依赖契约未实现，且本机默认 pytest 临时目录 `C:\Users\BJB110\AppData\Local\Temp\pytest-of-BJB110` 返回 `WinError 5`，后续改用任务目录 basetemp。
- RED: `python -X utf8 -m pytest scripts/tests/test_spring_constructor_contract.py -q --basetemp ...\spring-red` -> FAIL（4 failed）；Spring 构造器门禁脚本和发布脚本入口尚不存在。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_spring_constructor_contract.py -q --basetemp ...\regression2` -> PASS（34 passed）。
- GREEN: PowerShell AST 解析 `scripts/build.ps1`、`scripts/prepare-frontend-dependencies.ps1`、`ops/deploy/publish-int-ruoyi.ps1` -> PASS（`POWERSHELL_PARSE_PASS`）。
- GREEN: `python -X utf8 ops/release/spring_constructor_contract_gate.py --source-root E:\IntRuoyi\IntRuoyiBackend` -> 真实源码扫描执行，按门禁预期 FAIL：`MesProRouteVersionSnapshotMigrationRunner.java:24`，`constructorCount=2`、`autowiredCount=0`、`noArgCount=0`。
- BLOCKER: `python -X utf8 -c "...assert_release_sql_contracts(...)..."` 扫描当前后端 SQL -> 按门禁预期 FAIL：`20260814_mes_production_release_roles.sql:294` 的 `tmp_mes_production_release_required_role_menu` 重复读取风险；当前并发发布任务不在本任务范围内，不修复其 worktree/提交。
- REGRESSION: 发布相关 Python 套件 -> `50 passed, 3 failed`；3 个失败均为并发任务删除维护仓 `frontend/src/App.vue`、`frontend/package.json` 等文件导致的既有前端契约读取失败，不属于本任务修改。
- BLOCKER: `python -X utf8 scripts/verify_contracts.py` -> `FAIL: missing required file: frontend/src/App.vue`，同一并发删除前置条件，未恢复或绕过。

## Verification

- 通过：新增/相邻发布门禁测试 34 条；PowerShell 语法解析；`git diff --check`（目标实现文件）。
- 通过：测试只读临时 SQL、临时源码，不连接服务器、不写测试库、不读取或记录凭据。
- 未执行：真实 `scripts/build.ps1`、`build-release`、`publish-test`、Maven/前端完整构建；维护仓 `frontend` 当前由并发任务删除，且用户未授权服务器发布。

## Current Blockers

- 并发任务删除维护仓 `frontend` 文件，阻塞完整 `verify_contracts.py`、完整前端契约测试和真实构建；不得恢复/覆盖并发改动。
- 当前后端冻结源码存在 Spring 多构造器无注入标注和 `20260814` SQL temp-table reopen 风险；新门禁已按预期 fail-fast 报告，修复应在对应应用任务中完成并重新构建新 releaseTag。

## Closeout

- `task-closeout-cleanup --mode preview` -> PASS；仅删除任务声明的 `.tmp-pytest/`，保留 `task.md` 与 `execution-log.md`，无 blocked/warning。
- `task-closeout-cleanup --mode apply` -> PASS；`.tmp-pytest/` 已删除；当前仓为主 worktree，未执行合并或 worktree 删除。
- Long-term experience -> PASS；已合并到现有 `docs/release-build-preflight-lessons.md`，并在 `docs/experience-index.md` 增加脚本/错误关键词路由。
- Final status: completed；未执行服务器、发布 operation、真实构建或 E2E，未修改并发任务及其 worktree/运行态。
