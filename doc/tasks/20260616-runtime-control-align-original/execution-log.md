# Execution Log

- Task ID: `20260616-runtime-control-align-original`
- Created: `2026-06-16T16:44:42`

## Phase Entries

Append one reviewed section per executor pass using real phase ids and real evidence refs.

### 2026-06-16 16:45-17:45 P1/P2 原版逻辑对齐

- BDD: 原版接口保持可访问 -> Given 独立运行控制台不接入芋道登录/菜单权限, When 请求原 IntRuoyi 运行控制台公共接口, Then 接口应由独立应用暴露且不依赖 Spring Security / PreAuthorize。
- BDD: 高风险候选值由服务端解析 -> Given 客户端只提交候选 ID, When 预览 rollback/restore/rehearsal/mark-tested 命令, Then imageTag、backupId、recoverySetId、manifestHash、programVersion、redisPolicy 均由后端候选记录解析；客户端直传内部值应失败。
- BDD: 发布包按原版证据校验 -> Given NAS 发布包目录, When 查询或晋级发布包, Then 必须读取 release-manifest.json、artifact sha256、tested.json 与恢复集证据，缺失时 fail fast 或标记不可用。
- BDD: 测试库 SQL 快应用入口存在 -> Given 选择 `apply-test-db-sql`, When 填写 SQL 路径并预览命令, Then 仅 `.sql` 普通非空文件可通过，缺失、空文件或非 SQL 文件失败。
- BDD: 前端不暴露内部候选实际值 -> Given 打开独立运行控制台, When 查看运维动作表单, Then 有原版动作入口，且不出现“镜像标签”“备份点”自由文本输入。
- GREEN: experience-preflight -> PASS, 本任务只执行本机代码构建、契约测试和浏览器只读验证；未执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
- RED: `python -X utf8 scripts\verify_contracts.py` -> FAIL, expected reason: 前端缺少原版 `apply-test-db-sql` 动作入口。
- RED: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> FAIL, expected reason: 新增原版一致性测试要求 NAS browser 提供 `listFiles` / `isRegularFile` / `readText`，生产实现尚未补齐。
- GREEN: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS, 4 tests, 覆盖原版接口、候选解析、发布包校验、SQL 校验。
- GREEN: `python -X utf8 scripts\verify_contracts.py` -> PASS, 静态契约检查通过。
- GREEN: `pnpm --dir frontend typecheck` -> PASS。
- GREEN: `pnpm --dir frontend build` -> PASS。
- GREEN: `mvn -f backend/pom.xml test` -> PASS, 9 tests, failures 0, errors 0。
- GREEN: `.\scripts\build.ps1` -> PASS after stopping stale local `127.0.0.1:48181` maintenance jar process that locked the target jar; script completed pnpm install/typecheck/build and Maven test/package.
- GREEN: Browser E2E -> PASS, `http://127.0.0.1:48181/` health `UP`, page heading `运行控制台`, action labels include `构建发布包`、`测试服数据库快应用`、`回滚应用`、`恢复数据`, backend error shown visibly as `backupOps.nasUsername is required`, browser console error count 0。
- Evidence: `doc/tasks/20260616-runtime-control-align-original/evidence/runtime-control-standalone-e2e.png`。
- GREEN: task-closeout-cleanup preview -> PASS, blocked none, warnings none; apply skipped because preview would delete this spec-driven task's PRD/test-plan/test-report/task-state and E2E screenshot evidence.

## Outstanding Blockers

- None.
