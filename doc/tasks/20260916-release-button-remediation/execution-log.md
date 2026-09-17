# 20260916 发布按钮复查遗留问题修复 Execution Log

## Bootstrap
- 用户输入: 发布按钮静态复查报告，维护仓仅覆盖 R5 阶段事件脚本合同。
- Worktree: `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m`。
- BDD: build stages reflect real execution events -> Given build-release enters contract tests and application build, When the maintenance script logs progress, Then it emits TESTING before tests and BUILDING before build so the app workflow can show real stages.
- GREEN: experience-preflight -> PASS, only static pytest is in scope; no release, server write, database write, E2E, service restart, commit, push, or worktree cleanup is authorized.

## GREEN / REGRESSION
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py -k "workflow_stage_markers or app_release"` -> PASS, 3 selected tests, confirms app-release scope and stage marker contract.
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py` -> PASS, 12 tests, confirms full static workflow preflight file.
- GREEN: `rg -n "RELEASE_WORKFLOW_STAGE|Write-ReleaseWorkflowStage|PublishScope|code-only|with-data|app-release" ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_workflow_preflight.py` -> PASS by inspection, TESTING marker appears before backend contract tests and BUILDING marker before expensive artifact build.
- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence doc/tasks/20260916-release-button-remediation/bug-regression-evidence.md` -> PASS.
- GREEN: `git diff --check -- ops/deploy/publish-int-ruoyi.ps1 scripts/tests/test_release_workflow_preflight.py` -> PASS, no whitespace errors on task-owned maintenance script/test files.

## Closeout Boundary
- Current status set to `ready_for_closeout`.
- Not executed by policy: real build-release, publish-test, mark-tested, promote-prod, promote-backup, server access, database write, E2E, service restart, commit, push, worktree cleanup.

## 2026-09-17 S1-S4 reopen for authorized test publish
- USER_REQUEST: 用户要求继续修复指定提交静态复查 S1-S4，修复后通过发布按钮执行一次测试服发布并解决发布后问题。
- WORKTREE: 维护仓继续使用 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260911-release-button\m`；应用仓继续使用 `D:\IntRuoyiWorktree\r260911-release-button\a`。当前代码尚未融合到主干，发布前必须先提交并从新临时发布 worktree 出包。
- GREEN: experience-preflight -> PASS；用户本轮授权覆盖本机修复、提交、测试服 `build-release -> publish-test` 与发布后问题处理；禁止正式服、审查服、`mark-tested`、`promote-prod`、`promote-backup`、全量数据库复制或 MinIO 数据同步。
- BDD: recovery workflow is read-only -> Given workflow 为 `RECOVERY_REQUIRED` 且 operation log 含 TESTING/BUILDING markers / When 列表或详情 reconcile / Then 直接返回恢复态，不推进阶段、不抛 `RELEASE_WORKFLOW_STAGE_SEQUENCE_INVALID`。
- BDD: canceled write stage retains isolation -> Given `TEST_DEPLOYING` 拥有 test lease / When operation 已确认终止后取消 / Then workflow 进入 `RECOVERY_REQUIRED` 且同环境下一 workflow 获取 test lease 失败。
- BDD: test acceptance branches explicitly -> Given `TEST_DEPLOYED` / When 提交 `PASS` / Then 派发 `mark-release-tested`；When 提交 `FAIL` / Then workflow 进入 `FAILED` 且不派发成功凭证写入。
- BDD: TestedBy is authenticated -> Given `PASS` 验收 / When 服务端派发 `mark-release-tested` / Then `RuntimeControlOperationAction` 显式传入 `-OperatorName <requestedBy>` 和 `-TestResult PASS`，不使用客户端或机器账户兜底。
- BDD: direct mark-tested operation keeps structured PASS contract -> Given the generic mark-tested operation is still available / When the frontend submits it / Then `RuntimeControlActionReqVO` and payload include `testResult=PASS` so the backend's explicit PASS gate remains usable.
- GREEN: `mvn.cmd -f D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiBackend\pom.xml -pl yudao-module-infra '-Dtest=ReleaseWorkflowOrchestratorTest,ReleaseWorkflowSourceBindingTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowStoreTest,RuntimeControlServiceImplTest' '-Dsurefire.failIfNoSpecifiedTests=false' test` -> PASS，102 tests，0 failures/errors/skips。
- GREEN: `node D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiFronted\tests\e2e\runtime-control-one-button-static.spec.cjs` -> PASS，确认 workflow PASS/FAIL 验收和直接 `mark-release-tested` PASS payload 静态合同。
- GREEN: `corepack pnpm run ts:check` from `D:\IntRuoyiWorktree\r260911-release-button\a\IntRuoyiFronted` -> PASS。
- GREEN: `python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py scripts/tests/test_release_package_governance.py --basetemp .pytest-tmp-release-button-current-all` -> PASS，86 tests。
- GREEN: `git diff --check` -> PASS，应用仓和维护仓均仅有 CRLF 提示。
- RESULT: S1-S4 与补充的直接 mark-tested 前端合同均已本机验证通过；下一步提交两仓实现，创建新的临时发布 worktree，通过按钮执行全新 releaseTag 的测试服发布。

## 2026-09-17 菜单身份冲突根因闭环与 R82 冻结
- USER_REQUEST: 用户要求不要空等，按“通用、长期可用的一键按钮发布”方向修复；发布包必须先在本地验证成功，再发布测试服；最终使用芋道源码/admin 进行只读页面验收。
- GREEN: `app-registration-certificate-menu-regression` -> PASS，应用 worktree `D:\IntRuoyiWorktree\r260917-button-publish7\a` 提交 `6435dfc54c37291f2b54a4c734aea43475155fd5` 的 `test_registration_certificate_management_menu_hierarchy_sql.py` 与 `test_release_target_preflight_files.py` 共 12 tests 通过。
- RED: `publish-test` operation `42384949-c0d1-40b7-baa5-8ec14adc5d4c` -> FAIL，旧应用提交 `d7f4901aa65bec54c2b56b44fbc2e387a2be07e1` 执行 `20260829_registration_certificate_management_menu_hierarchy.sql` 在第 543 行返回 `ERROR 1644: Registration certificate management retired menu contract mismatch: enterprise company scope`；测试服 `.env` 与实际容器未切换，发布锁已写回 `FAILED` 并释放。
- ROOT_CAUSE: 旧 SQL 将退休菜单 `(605071320, 605071321)` 当作固定身份直接退休，同时又对 ID 605071320 的历史身份做强一致性断言；测试服存在同 ID 的企业公司范围身份漂移，造成迁移在版本切换前失败。当前修复将退休集合改为“完整旧身份匹配才加入”，避免错误删除或因可保留的未知身份阻断发布。
- BDD: retired menu identity drift is safe and explicit -> Given target `system_menu` may contain a reused legacy ID with a different active identity / When registration certificate menu hierarchy migration runs / Then the migration only retires rows matching the complete legacy identity, preserves unknown identities, and the SQL contract test forbids blind fixed-ID retirement.
- GREEN: `python -X utf8 -m pytest -q script/tests/test_registration_certificate_management_menu_hierarchy_sql.py script/tests/test_release_target_preflight_files.py --basetemp D:\IntRuoyiWorktree\r260917-button-publish7\a\.pytest-temp\registration-certificate-fix` -> PASS，12 tests。
- SOURCE_FREEZE: 新 releaseTag=`release-20260917-one-button-app-r82`；维护源 `7381c6e4d27b183cca79fafda623bccb52f8a2f6`；应用/前端源 `6435dfc54c37291f2b54a4c734aea43475155fd5`；仅测试服 `172.30.30.58`，`PublishScope=app-release`，禁止 `mark-tested`、正式服、备份服、全量数据库复制和 MinIO 同步。
- NEXT: 先提交本段任务记录保持维护 worktree clean，再在新的发布 worktree 完成本地 build-release、schema-only rehearsal、package integrity 与 manifest validation；仅本地全部通过后，才执行同一 R82 的测试服 publish-test。
