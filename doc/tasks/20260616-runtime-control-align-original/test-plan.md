# Test Plan: 运行控制台原版逻辑对齐

- Task ID: `20260616-runtime-control-align-original`
- Created: `2026-06-16T16:44:42`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- User Request: `改成与原版也就是intruoyi一致`

## Test Scope

验证独立运行控制台与原 IntRuoyi 运行控制台在公共接口、服务端候选解析、发布包校验、SQL 动作入口和前端请求契约上的一致性。真实发布、备份、恢复、回滚、重启、SSH 和远端写入不在本次验证范围。

## Environment

- Windows PowerShell，命令不用 `&&`。
- Java 17 + Maven。
- Node + pnpm。
- 本地独立应用源码位于 `D:\ProjectPackage\Int\IntRuoyiMaintance`。
- 原版比较源位于 `D:\ProjectPackage\Int\IntRuoyi`。

## Accounts and Fixtures

- 不需要登录账号；独立应用不接入芋道登录。
- 后端测试使用本地临时目录构造 release package、rollback candidate、restore candidate、SQL 文件。
- 不使用远端服务器、真实发布、真实备份或真实恢复数据作为测试前置。

## Commands

- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`：后端原版一致性窄测试通过。
- `mvn -f backend/pom.xml test`：后端回归测试通过。
- `pnpm --dir frontend typecheck`：前端类型检查通过。
- `pnpm --dir frontend build`：前端生产构建通过。
- `.\scripts\build.ps1`：独立应用整体构建通过。
- Playwright 打开 `http://127.0.0.1:48181/`：页面可见、动作入口完整、无 console error；只做只读验证和命令预览，不执行真实动作。

## Test Cases

### T1: 后端公共接口与无权限依赖

- Covers: P1-AC1
- Level: contract
- Command: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#originalRuntimeControlEndpointsAreExposedWithoutSecurity test`
- Expected: 33 个原版运行控制台接口可请求或被 MockMvc 匹配；项目仍不依赖 Spring Security。

### T2: 候选实际值禁止客户端直传

- Covers: P1-AC2, P1-AC4
- Level: contract
- Command: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#highRiskCandidateValuesAreServerResolvedOnly test`
- Expected: `selectedImageTag` / `selectedBackupId` 直传返回错误；只传候选 ID 时预览命令包含服务端解析出的 `-SelectedImageTag` / `-SelectedBackupId`。

### T3: 发布包 manifest/tested 校验

- Covers: P1-AC3
- Level: contract
- Command: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#releasePackageValidationMatchesOriginalGate test`
- Expected: 缺 manifest/checksum 的发布包不作为 AVAILABLE；`promote-prod`/`promote-backup` 对未 tested 包失败。

### T4: SQL 动作校验

- Covers: P1-AC5
- Level: contract
- Command: `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest#applyTestDbSqlRequiresRealSqlFile test`
- Expected: 非 `.sql`、缺失或空 SQL 文件失败；非空 `.sql` 预览通过并附加测试服目标参数。

### T5: 前端原版请求契约

- Covers: P2-AC1, P2-AC2, P2-AC3, P2-AC4
- Level: static + typecheck
- Command: `pnpm --dir frontend typecheck`
- Expected: API 类型不含内部字段；页面含 `apply-test-db-sql`，不含自由文本镜像标签/备份点输入，原版 API 方法存在。

### T6: 前端构建和真实浏览器只读验证

- Covers: P2-AC2, P2-AC3
- Level: e2e
- Command: `pnpm --dir frontend build` and Playwright open local app
- Expected: 页面加载成功、动作入口完整、只读状态显示可见、console error 为 0。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | backend | 原版接口和无权限依赖 | contract | P1-AC1 | `execution-log.md`, `test-report.md` |
| T2 | backend | 高风险候选服务端解析 | contract | P1-AC2, P1-AC4 | `execution-log.md`, `test-report.md` |
| T3 | backend | 发布包 manifest/tested 校验 | contract | P1-AC3 | `execution-log.md`, `test-report.md` |
| T4 | backend | SQL 路径校验 | contract | P1-AC5 | `execution-log.md`, `test-report.md` |
| T5 | frontend | API 与表单契约 | static | P2-AC1, P2-AC2, P2-AC3, P2-AC4 | `execution-log.md`, `test-report.md` |
| T6 | frontend | 浏览器只读验证 | e2e | P2-AC2, P2-AC3 | screenshot evidence |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright, Maven, pnpm
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: Run against the real repo and local runtime. Browser validation must use the local page; no API-only replacement for UI checks.
- Escalation rule: Do not inspect withheld artifacts until the tester has written an initial verdict or the main agent explicitly asks for discrepancy analysis.

## Pass / Fail Criteria

- Pass when: listed commands pass, browser evidence exists, no high-risk operation is executed, every acceptance id has evidence.
- Fail when: any required command fails, frontend hides backend errors, internal candidate fields remain client-submittable, or validation relies on mock/default success.

## Regression Scope

- Existing build-release `code-only` and `with-data` preview argument behavior.
- Local-only no-login/no-permission standalone boundary.
- Production write guard and `PROD` confirmation.
- Existing frontend visual baseline.

## Reporting Notes

Write results to `test-report.md`. Browser validation must reference a real screenshot/trace file outside the task markdown.
