# 两入口发布开发交付测试计划

- Task ID: `20260924-two-button-release-delivery`
- Created: `2026-09-24T10:49:16+08:00`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiMaintance`
- User Request: 验证锁/状态根因、后台自动推进、两个入口、真实验收及同包晋级。

## Test Scope

覆盖 P1–P5；内部四阶段、锁 lease/fence、持久编排、UI、真实测试/正式运行态。备份服、业务数据复制、芋道源码租户、冻结 worktree 和未授权远程写入不在范围。

## Environment

Windows UTF-8 PowerShell（不使用 `&&`）；应用根 `E:\IntRuoyi`（后端 `IntRuoyiBackend`、前端 `IntRuoyiFronted`）；独立 worktree；隔离 MySQL；Maven、pytest、pnpm；前端 `http://localhost:8081`；Playwright 1.60.0。远程闭环需新 GO、环境访问、NAS、镜像和恢复候选。

## Accounts and Fixtures

测试租户“测试租户”/`aoteman`，测试写入带任务标识且可清理；admin 仅只读核验。隔离库含无锁、旧终态、同 tag 旧 lease、活动他人锁、失权 fence、并发和未知结果。应用含批准提交、执行器 SHA、有效/漂移摘要、manifest、有效/过期证据/候选/grant/stateVersion。凭据不入证据。

## Commands

所有命令在本任务对应 worktree 的仓库/后端/前端目录执行。锁测试的 `MYSQL_ROOT_PASSWORD` 从既有本地容器配置安全注入进程环境，不在日志或命令文本保存值。跨仓迁移回归显式设置 `$env:INTRUOYI_TEST_APP_BACKEND = 'D:/IntRuoyiWorktree/two-button-release-delivery-app/IntRuoyiBackend'`；禁止依赖旧相邻目录名或把其他 worktree 的源码作为本轮输入。

- `python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_release_operation_lock_behavior.py scripts/tests/test_publish_release_lock_cleanup.py -q`：真实生成 SQL 锁测试 PASS。
- `mvn.cmd -pl yudao-module-infra -am "-Dtest=ReleaseWorkflowOrchestratorTest,ReleaseWorkflowSourceBindingTest,ReleaseWorkflowLeaseTest,ReleaseWorkflowStoreTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowRecoverySchedulerTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowProductionPreviewTest,ReleaseWorkflowTestEvidenceStoreTest,RuntimeControlServiceImplTest" "-Dsurefire.failIfNoSpecifiedTests=false" test`：后端行为 PASS。
- `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py -q`：维护回归 PASS。
- `python -X utf8 -m pytest scripts/tests/test_release_input_preparation.py -q`（P2交付）：真实Git批准对象与隔离输入、正式依赖准备、重入/崩溃/路径边界、受控清理；fixture不能把伪造或提交的node_modules stamp当成依赖安装成功。
- `pnpm ts:check`（前端目录）：类型 PASS。
- `python <skill-dir>\scripts\validate_artifacts.py --cwd D:\ProjectPackage\Int\IntRuoyiMaintance --task-id 20260924-two-button-release-delivery`：规划结构 PASS。
- Playwright 真实用例：由 P3 交付 `E:\IntRuoyi\IntRuoyiFronted\tests\e2e\runtime-control-two-entry-release.e2e.cjs`，在独立 worktree 注册端口运行 `node tests/e2e/runtime-control-two-entry-release.e2e.cjs`；记录截图/trace/HAR、console/request 失败计数。只读 API/SSH 仅最终核验 operation/manifest/tag/health/HTTP。

## Test Cases

### T1: 基线与锁根因

- Covers: P1-AC1, P1-AC2, P1-AC4
- Level: review/integration
- Command: 上述锁 pytest；审查差异清单、`0e5d785...` 和真实 SQL 输出。
- Expected: 新 lease/fence 正确绑定，活动锁拒绝，差异和 GO 门禁可追踪。
- BDD: Given 当前 main 与 R22 有差异且存在旧锁行；When 逐项选择性合入并执行生产生成 SQL；Then 差异归属可追踪且新 operation 不继承旧 lease。
- RED/GREEN: 旧源码真实 SQL/行为测试 FAIL 暴露旧 lease；修复提交同一命令 PASS。

### T2: 未知态与状态边界

- Covers: P1-AC3
- Level: backend integration/fault
- Command: Maven ReleaseWorkflow 测试并增加 dispatched 抛异常、verifyAdvance 无 zeroWriteEvidence、reconcile preflight/执行未知、save/guard/submit 边界行为测试。
- Expected: 明确 zero-write blocked 可控重试；执行后未知隔离，不把 retryable 或 FAILED 一概放行。
- BDD: Given executeAction 可能已产生副作用后抛异常；When verify/reconcile；Then 只有明确 zero-write blocked 可重试，执行后未知保持隔离。
- RED/GREEN: 先运行新增边界测试 FAIL，再最小实现 GREEN。

### T3: 后台一次测试发布

- Covers: P2-AC1, P2-AC2, P2-AC3, P2-AC4
- Level: backend integration/concurrency
- Command: Maven Orchestrator/Store/Recovery/Scheduler/Lease 测试。
- Expected: 持久目标、READY 自动 publish-test、重启续接、并发幂等、历史记录不接管、失败证据保留。
- BDD: Given 用户提交一次批准源；When 构建进入 READY、浏览器关闭并 scheduler 重启；Then 受控代码自动创建隔离 worktree/依赖并继续 publish-test 一次。
- RED/GREEN: 现有停在 READY 的测试 FAIL；实现后同一 Maven 命令 PASS。

### T4: 两入口与晋级门禁

- Covers: P3-AC1, P3-AC2, P3-AC3, P3-AC4, P3-AC5
- Level: e2e
- Command: `pnpm ts:check`；Playwright 登录运行控制台，验证两个入口、缺证据、取消/过期/漂移、preview/grant/stateVersion 和错误反馈。
- Expected: 仅两入口；缺证据不晋级；同包且不重构建；错误可见。
- BDD: Given TEST_DEPLOYED 缺结论或候选；When 点击晋级并取消/确认；Then 不产生 TESTED/grant/正式 operation，真实错误可见。
- RED/GREEN: 前端行为测试/Playwright 脚本先 FAIL，再实现 GREEN。

### T5: 独立故障回归

- Covers: P4-AC1, P4-AC2, P4-AC3, P4-AC4
- Level: independent real-runtime
- Command: tester blind-first-pass 执行双击、双窗口/推进者、关页、重启、临界中断、锁失权、迁移失败、摘要/证据/授权失效。
- Expected: 首轮不读 execution-log/task-state；每个通过浏览器 case 引用截图/trace/HAR；失败为 BLOCKER 或明确阻断。
- BDD: Given 新代码已通过独立预发布门禁；When tester 注入故障；Then 每个状态均有明确阻断/恢复证据且不修改产品代码。
- RED/GREEN: 故障用例先 FAIL，再修复后 GREEN，最后 REGRESSION。

### T6: 新 GO 后真实双按钮闭环

- Covers: P5-AC1, P5-AC2, P5-AC3, P5-AC4
- Level: e2e
- Command: 新专用 worktree/new tag；Playwright 测试租户点击测试发布一次并完成真实验收/恢复候选，再点击晋级；只读核验全量运行态。
- Expected: 同一 package/manifest/digest，operation SUCCESS，远端 `.env IMAGE_TAG`/实际镜像 tag、backend UP、frontend 200、业务页面和版本说明通过；无新 GO 或前提缺失时不触发远程动作。
- BDD: Given 新 GO、干净 worktree、批准源和真实候选；When Playwright 执行两个按钮；Then 同包完成测试/正式运行态全量核验。
- RED/GREEN: 新 GO 前保持 BLOCKER；新 GO 后首轮 FAIL/修复 GREEN，最终 REGRESSION 通过。

## Coverage Matrix

| Case | Acceptance | Evidence |
| --- | --- | --- |
| T1 | P1-AC1, P1-AC2, P1-AC4 | 差异清单、真实 SQL、锁测试 |
| T2 | P1-AC3 | 后端边界测试、事件/状态 |
| T3 | P2-AC1..P2-AC4 | Maven 测试、持久事件、operation |
| T4 | P3-AC1..P3-AC5 | ts-check、截图/trace/console |
| T5 | P4-AC1..P4-AC4 | 独立 test-report、故障证据 |
| T6 | P5-AC1..P5-AC4 | Playwright、manifest/tag/health/page |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-browser
- Required tools: playwright
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 真实登录/数据；写入只限测试租户。独立 worktree 使用注册端口，不占用固定 8081；通过 UI case 必须引用真实文件证据。
- Escalation rule: 缺前提/入口/权限/锁归属/批准源/恢复候选/新 GO 即 BLOCKER；tester 不改代码或规划，不用 mock。

## Pass / Fail Criteria

- Pass when: 每个 AC 有可复核证据，命令/真实浏览器路径通过，锁/未知态/证据门禁正确阻断，P5 全量运行态满足。
- Fail when: 缺证据、使用 mock/手写 SQL/旧 GO/tag、默认 PASS、吞异常、未知态盲重放、正式重构建、接口冒充按钮或触碰非测试租户。

## Regression Scope

ReleaseWorkflow 状态/CAS/lease/fence/scheduler；四阶段参数、manifest、迁移、摘要和日志脱敏；运行控制台权限/错误/UI；worktree clean input、同包晋级、测试/正式运行态和 closeout。

## Reporting Notes

结果写入 `test-report.md`，使用 `BDD:`、`RED:`、`GREEN:`、`REGRESSION:`、`BLOCKER:` 标记并记录 cwd、提交、operation/tag/digest、证据路径；禁止凭据和明文秘密。
