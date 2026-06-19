# 任务: 发布后测试服三角色真实 E2E 验收门禁

## 任务目标

每次发布之后，在测试服务器 `172.30.30.58` 使用 `芋道源码` 租户真实账号完成三角色验收：

1. `gaomin / 111111` 登录后只能看到 `展厅` 页签，展厅页签下每个子页签访问无错误。
2. `zhaojie / 111111` 登录后只能看到 `智能排产` 页签，并运行智能排产冒烟测试直到运行结束。
3. `wangsiyu / 111111` 登录后只能看到 `DCC文控中心` 页签，DCC 文控中心下每个子页签访问无错误。

如果任一角色或页面失败，先完整记录全部错误；全部测试跑完后统一修复，再构建发布到测试服务器并重新运行三角色验收，循环直到全部满足。

## 授权范围

- 用户已明确授权测试服真实登录验证。
- 目标环境：测试服 `172.30.30.58`。
- 登录租户：`芋道源码`。
- 账号：`gaomin`、`zhaojie`、`wangsiyu`，密码均为 `111111`。
- 允许：Playwright 真实浏览器登录、页面访问、运行智能排产冒烟测试、记录错误、必要修复、重新构建发布到测试服、复测。
- 禁止：正式服、备份服、备份、恢复、回滚、mock 登录、接口绕过 E2E、静默切换租户或账号。

## 上一任务检查

- 上一维护仓任务：`doc/tasks/20260618-build-deploy-test-server-maintenance/task.md`。
- 状态：`completed`。
- 处理：上一任务已完成，本任务可以开始。

## 经验门禁

- `docs/release-build-preflight-lessons.md`：发布后必须看目标环境真实运行态、真实页面和权限响应；故障要补成门禁。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布入口必须是维护仓；再次修复后构建发布必须验证 manifest、远端 IMAGE_TAG、镜像和真实浏览器入口。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`：测试服 IP 为 `172.30.30.58`，远端运行目录 `/opt/intruoyi/runtime`，服务器凭据不得写入仓库。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`：登录失败必须记录真实租户、账号、入口、失败位置；不得静默切换账号/租户/环境。用户本次明确授权测试服登录。
- `docs/agent-memory/project-error-prevention.md`：不能只看健康检查，必须核对真实浏览器入口和权限响应。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。登录、菜单、页面访问或冒烟失败必须记录为失败，不隐藏错误。
- `是否从根因和长期维护角度解决`：是。先完整复现三角色验收，再统一修复并发布复测。
- `是否存在临时补丁或绕过`：否。不得通过前端隐藏、接口绕过或手工改测试结果伪装成功。

## BDD 场景

- `BDD: gaomin 展厅角色验收 -> Given 测试服发布完成且 gaomin 登录芋道源码租户 / When 打开管理前端 / Then 只看到展厅页签，并且展厅每个子页签访问无页面错误、网络错误或控制台错误。`
- `BDD: zhaojie 智能排产角色验收 -> Given 测试服发布完成且 zhaojie 登录芋道源码租户 / When 打开管理前端并进入智能排产 / Then 只看到智能排产页签，并且智能排产冒烟测试可运行直到结束。`
- `BDD: wangsiyu DCC角色验收 -> Given 测试服发布完成且 wangsiyu 登录芋道源码租户 / When 打开管理前端 / Then 只看到DCC文控中心页签，并且DCC文控中心每个子页签访问无页面错误、网络错误或控制台错误。`
- `BDD: 失败统一修复发布复测 -> Given 三角色验收发现错误 / When 全部错误记录完成 / Then 统一修复、重新构建发布到测试服并完整复测三角色，直到全部通过。`
- `BDD: ERP smoke 手动同步权限 -> Given zhaojie 智能排产 smoke 使用 ERP 冒烟创建员创建 Kingdee 工单 / When 打开 ERP 金蝶同步运行页 / Then 页面必须显示生产工单“执行一次”，且该账号具备定时任务查询和触发接口权限。`
- `BDD: 智能排产 smoke 路线就绪产品 -> Given smoke 通过 Kingdee 创建真实生产工单 / When MES 同步工单并查询排产入池差异 / Then 默认产品必须已绑定启用路线、激活版本和工序，不能停留在 BLOCKED_MISSING_ROUTE。`
- `BDD: 智能排产 smoke 动态报工 Excel -> Given smoke 每次运行都有新的工单号和产品配置 / When 执行第三方报工导入 / Then 上传 Excel 必须按本次 smokeRunId、工单号、产品编码和工序动态生成，不能依赖测试服残留静态文件。`

## 里程碑

- [x] M1 建立任务文档、读取经验门禁、确认上一任务完成。
- [x] M2 编写并运行测试服三角色真实 E2E 探测，记录全部错误。
- [x] M3 汇总失败根因并统一修复。
- [x] M4 重新构建发布到测试服。
- [x] M5 重新运行三角色测试服验收直到全部通过。
- [x] M6 补齐证据、收尾清理并提交。

## 预期验证

- Playwright 真实登录 `http://172.30.30.58:8081/`。
- 每个账号验证登录后一级可见菜单只包含目标页签。
- 自动遍历目标页签子菜单，记录 URL、页面文本、控制台错误、请求失败、接口错误。
- `zhaojie` 触发智能排产冒烟测试并轮询到终态。
- 若修复代码，必须补 RED/GREEN 测试、构建发布、部署测试服并重新跑三角色验收。

## 当前状态

COMPLETED：已通过多轮“记录全部错误 -> 根因修复 -> 正式构建发布 -> 测试服真实复测”的闭环，最终测试服发布 `release-20260619-2230-role-e2e-gate-feedback-approver-wrapper` 在 `172.30.30.58` 上满足全部验收要求。最终真实 E2E 证据 `evidence/post-release-role-e2e-1781882555897.json` 显示：

- `gaomin / 111111` 登录 `芋道源码` 后仅可见 `展厅`，6 个子页全部无页面、接口或控制台错误。
- `zhaojie / 111111` 登录 `芋道源码` 后仅可见 `智能排产`，6 个子页全部通过；智能排产真实 smoke 全链路 `PASS`，远端 `smoke-report.json` 中 ERP 建单、MES 同步、入池、自动排产、日历核验、第三方报工导入、归属、审批与任务回写全部通过。
- `wangsiyu / 111111` 登录 `芋道源码` 后仅可见 `DCC文控中心`，16 个子页全部无页面、接口或控制台错误。

## 最终验证

- 构建发布：`evidence/runtime-console-build-deploy-1781882335880.json` -> PASS，`releaseTag=release-20260619-2230-role-e2e-gate-feedback-approver-wrapper`。
- 测试服运行态：`ssh root@172.30.30.58 "grep '^IMAGE_TAG=' /opt/intruoyi/runtime/.env"` -> `IMAGE_TAG=release-20260619-2230-role-e2e-gate-feedback-approver-wrapper`。
- 三角色真实 E2E：`evidence/post-release-role-e2e-1781882555897.json` -> PASS，`failures=0`。
- 智能排产 smoke：`ssh root@172.30.30.58 "cat /opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/smoke-report.json"` -> PASS，`smokeRunId=SMART-SCHED-20260619T152027017032296`。

## Current Status

completed

## Cleanup Keep

- `doc/tasks/20260618-post-release-role-e2e-gate/task.md`
- `doc/tasks/20260618-post-release-role-e2e-gate/execution-log.md`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781882335880.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781882555897.json`

## Cleanup Candidates

- `doc/tasks/20260618-post-release-role-e2e-gate/bug-regression-evidence.md`
- `doc/tasks/20260618-post-release-role-e2e-gate/qa-evidence.md`
- `doc/tasks/20260618-post-release-role-e2e-gate/scripts/`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/minio-showroom-cover-20260602-repair/`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/minio-showroom-cover-20260602-repair-1781842832636.tar`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/minio-sync-20260619-0129/`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/minio-sync-20260619-0129.tar`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/screenshots/`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/zhaojie-smoke-job-trigger-failure-1781848897783.png`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781790158540.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781790390014.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781793297319.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781797026325.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781826823171.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781844580.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781844580.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781844737245.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781846770336.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781846770336.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781846902055.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781848741121.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781848741121.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781848897783.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781851764170.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781856280345.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781858432621.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781862916125.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781865453288.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781869546155.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781875259932.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/post-release-role-e2e-1781877963367.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781793015251.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781794983814.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781798745131.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781800357389.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781801871169.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781803561178.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781843350.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781843350.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781844498623.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781845332298.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781845332298.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781845499425.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781845499425.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781846618912.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781847450295.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781847450295.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781848691651.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781851424303.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781854878582.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781858207843.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781860013539.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781861116267.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781862032847.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781865311739.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781875017403.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-1781877791317.json`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-20260619-142434.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-20260619-142434.out.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-20260619-152237.err.log`
- `doc/tasks/20260618-post-release-role-e2e-gate/evidence/runtime-console-build-deploy-20260619-152237.out.log`
