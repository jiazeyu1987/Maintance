# Test Report

- Task ID: `20260616-runtime-control-align-original`
- Created: `2026-06-16T16:44:42`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- User Request: `将独立运行控制台与原 IntRuoyi 的运行控制台逻辑对齐到原版一致，保留本机独立运行目标，但补齐原版候选校验、治理接口、前端动作和发布包校验`

## Environment Used

- Evaluation mode: blind-first-pass
- Validation surface: real-browser
- Tools: playwright, Maven, pnpm
- Initial readable artifacts: prd.md, test-plan.md
- Initial withheld artifacts: execution-log.md, task-state.json
- Initial verdict before withheld inspection: yes

Record the tester's first-pass visibility honestly. In `blind-first-pass`, the tester should record `yes` only after writing an initial verdict before inspecting withheld artifacts.

## Results

Add one subsection per executed test case using the test case ids from `test-plan.md`.

Each subsection should use this shape:

`### T1: concise title`

- `Result: passed|failed|blocked|not_run`
- `Covers: P1-AC1`
- `Command run: exact command or manual action`
- `Environment proof: runtime, URL, browser session, fixture, or deployment proof`
- `Evidence refs: screenshot, video, trace, HAR, or log refs`
- `Notes: concise findings`

For `real-browser` validation, include at least one evidence ref that resolves to an existing non-task-artifact file, such as `evidence/home.png`, `evidence/trace.zip`, or `evidence/session.har`.

### T1: 后端公共接口与无权限依赖

- Result: passed
- Covers: P1-AC1
- Command run: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- Environment proof: Spring Boot MockMvc, standalone backend test context
- Evidence refs: doc/tasks/20260616-runtime-control-align-original/evidence/runtime-control-standalone-e2e.png, execution-log.md
- Notes: 原版运行控制台补充接口可被独立应用匹配；测试同时断言无 Spring Security / PreAuthorize 依赖。

### T2: 候选实际值禁止客户端直传

- Result: passed
- Covers: P1-AC2, P1-AC4
- Command run: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- Environment proof: 后端临时 NAS fixture，未访问远端服务器
- Evidence refs: doc/tasks/20260616-runtime-control-align-original/evidence/runtime-control-standalone-e2e.png, execution-log.md
- Notes: `selectedImageTag` / `selectedBackupId` 客户端直传失败；只传候选 ID 时预览命令使用服务端解析值。

### T3: 发布包 manifest/tested 校验

- Result: passed
- Covers: P1-AC3
- Command run: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- Environment proof: 后端临时 release package fixture
- Evidence refs: doc/tasks/20260616-runtime-control-align-original/evidence/runtime-control-standalone-e2e.png, execution-log.md
- Notes: 缺 manifest/checksum 的发布包不可用；正式/备份晋级要求 tested 证据。

### T4: SQL 动作校验

- Result: passed
- Covers: P1-AC5
- Command run: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- Environment proof: 本地临时 SQL 文件 fixture
- Evidence refs: doc/tasks/20260616-runtime-control-align-original/evidence/runtime-control-standalone-e2e.png, execution-log.md
- Notes: 缺失、空文件、非 `.sql` 均失败；非空 `.sql` 可预览测试服 SQL 快应用命令。

### T5: 前端原版请求契约

- Result: passed
- Covers: P2-AC1, P2-AC2, P2-AC3, P2-AC4
- Command run: `python -X utf8 scripts\verify_contracts.py`; `pnpm --dir frontend typecheck`
- Environment proof: frontend static contract scanner and vue-tsc
- Evidence refs: doc/tasks/20260616-runtime-control-align-original/evidence/runtime-control-standalone-e2e.png, execution-log.md
- Notes: API 类型不含内部候选实际值字段；页面含 `apply-test-db-sql`；owner-matrix/wizard/resend/candidate/release API 方法存在。

### T6: 前端构建和真实浏览器只读验证

- Result: passed
- Covers: P2-AC2, P2-AC3
- Command run: `pnpm --dir frontend build`; `.\scripts\build.ps1`; Playwright CLI screenshot with `--channel chrome`; in-app Browser DOM/log inspection
- Environment proof: local app at `http://127.0.0.1:48181/`, health UP
- Evidence refs: doc/tasks/20260616-runtime-control-align-original/evidence/runtime-control-standalone-e2e.png
- Notes: 页面显示 `运行控制台`；动作入口包含 `构建发布包`、`测试服数据库快应用`、`回滚应用`、`恢复数据`；NAS 缺配置错误在页面告警可见；console error 为 0。Playwright CLI 默认 Chromium 缺失，使用系统 Chrome channel 截图成功。

## Final Verdict

- Outcome: passed
- Verified acceptance ids: P1-AC1, P1-AC2, P1-AC3, P1-AC4, P1-AC5, P2-AC1, P2-AC2, P2-AC3, P2-AC4
- Summary: 独立运行控制台已按原 IntRuoyi 运行控制台的候选解析、发布包校验、SQL 动作、治理 API 和前端请求契约完成对齐；验证只包含本机只读/构建路径，未执行真实发布或数据操作。

## Open Issues

- None.
