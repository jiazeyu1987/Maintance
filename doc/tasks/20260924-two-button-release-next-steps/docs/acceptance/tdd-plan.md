# 两入口发布 TDD 顺序

## Purpose and Scope
本文件规定未来RED/GREEN顺序，没有声称本轮已运行产品测试。每条证据记录cwd、版本、命令、计数和失败原因。

## Evidence Reviewed
实施计划M0–M5、现有ReleaseWorkflow测试类、维护锁MySQL测试、前端ts:check及Playwright1.60.0。

## TDD Sequence
1. AC06/07/16：真实生产锁SQL与状态失败测试先红，最小修复后转绿。
2. AC01/02/11/12/13/15：Orchestrator/Store/Scheduler覆盖目标、防重、重启和源冻结，再实现编排。
3. AC03/04/08/09/14：证据、预览和授权合同先测试，再改API/前端，不降低门禁。
4. AC05/07/10：执行器与状态副作用集成，最后独立GO后跑真实按钮闭环。

## RED Commands
新维护开发worktree：
```powershell
python -X utf8 -m pytest scripts/tests/test_release_operation_lock_mysql_behavior.py scripts/tests/test_release_operation_lock_behavior.py scripts/tests/test_publish_release_lock_cleanup.py -q
```
新应用worktree的IntRuoyiBackend：
```powershell
mvn.cmd -pl yudao-module-infra '-Dtest=ReleaseWorkflowOrchestratorTest,ReleaseWorkflowSourceBindingTest,ReleaseWorkflowLeaseTest,ReleaseWorkflowStoreTest,ReleaseWorkflowRecoveryTest,ReleaseWorkflowRecoverySchedulerTest,ReleaseWorkflowAuthorizationTest,ReleaseWorkflowProductionPreviewTest,ReleaseWorkflowTestEvidenceStoreTest' '-Dsurefire.failIfNoSpecifiedTests=false' test
```
先添加可编译的行为测试；若增加测试类，同步命令清单。不能把缺类/缺依赖或编译错误当作业务RED。

## Expected Failures
旧锁行复用应暴露新operation/旧lease问题；若真实SQL不复现，则据证据重新查因，不修改断言造红。旧工作流会停READY，无法满足关闭页面后自动部署。原四入口不满足新交互。前置缺失属于环境BLOCKER。

## GREEN Commands
实现后复跑同一失败命令，再跑相关回归：
```powershell
python -X utf8 -m pytest scripts/tests/test_release_workflow_preflight.py -q
```
前端目录：
```powershell
pnpm ts:check
```
真实E2E拟新增至前端 `tests/e2e/runtime-control-two-entry-release.e2e.cjs`，按上级AGENTS固定运行目录加载Playwright；不临时安装npx版本。

## Refactor Checks
保留内部四阶段、权限、源/双摘要、一次性授权和未知态保护；重构采用项目要求的子代理实施/独立检查。同一Maven target禁止并发编译。静态字符串断言不能替代行为验证。

## Evidence Log Template
```text
BDD: ACxx -> Given 前提 / When 行为 / Then 结果
RED: 精确命令 -> FAIL, 可观察原因
GREEN: 同一命令 -> PASS, 计数
REGRESSION: 相关命令 -> PASS/FAIL, 范围
BLOCKER: 缺失条件 -> 原因与影响
```
同时记录提交、worktree、operation/tag/digest和脱敏证据位置。

## Test Blockers
真实锁测试只用本机自有临时库，不操作业务租户数据；真实发布需要独立GO及环境前提。现有通过测试不能自动覆盖新增行为。
