# 自动增量真实页面验收 helper

## Current Status
2026-11-10 MAIN cycle 扩展 ready_for_closeout：新增9项+旧6项实际15 PASS/零skip，语法通过；本组件未运行真实E2E。父正式v4已安装验收，新验收承接当前已验证MAIN READY链，不能因新cycle而重做FULL。完整接口见本文末尾“MAIN cycle 显式模式”。

ready_for_closeout — M1/M2 已完成，脚本已准备并通过语法检查；M3 由根 Agent 在安装与现场预检后执行。当前未登录、未读取秘密、未派发备份、未更新运行环境，不代表真实验收通过。

## 目标与里程碑
- 准备同一真实页面上的 FULL / I1 / I2 三轮独立验收；FULL 为点击增量后计划明确要求的新全量，I1/I2 为真正增量。
- M1：固定真实入口、认证、前置门禁和防重提合同。
- M2：编写 helper，检查语法并向根 Agent 提供调用方式。
- M3：根 Agent 完成安装和新鲜高风险预检后实际执行，保留每轮原编号和真实终态；不以脚本准备完成代表验收完成。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；缺门禁、身份、链或计划摘要即失败。未知提交结果只查询同一原编号。
- 是否从根因和长期维护角度解决：是；helper 只验收已实现产品，不替代产品日常选链或派发。
- 是否存在临时补丁或绕过：否；不调用写入 API，不注入业务请求，不改页面状态，不执行服务器命令。

## 经验门禁
- 真实 E2E 必须先由根 Agent 在 execution-log.md 记录本次 `GREEN: experience-preflight -> PASS`，并提供新鲜的专属 gate JSON；脚本检查门禁及已安装提交的一致性。
- 只访问 `http://127.0.0.1:18080`，真实登录或验证既有已登录身份，经侧栏进入 `/backup-center` 的真实 iframe。
- 只允许正式服务器 `172.30.30.57`、safe、来源 `intruoyi-57-safe-20261024-v1`；FULL/I1/I2 的类型、父点、根及计划摘要必须显式固定。
- 提交前使用 wx 写入并 fsync 不可变回执；每 kind 至多放行一次最终 POST。任何错误或超时保留回执，只能 verify。
- 认证状态、凭据、截图仅运行时在私密目录读取/保存；公开 JSON 使用字段白名单，不输出密码、token、页面全文或原始异常。
- 本 helper 不覆盖独立数据库、附件、源服务、恢复周期及日志完整性验收；这些事实由根 Agent 的 sourceIdentityVerified / sourceServicesHealthy 等 gate 证明。

## BDD
- Given 首轮计划 BASELINE_REQUIRED；When 经页面选择增量；Then 确认框显示真实 FULL 和原因，只有显式 execute 才放行一次完全一致的自动提交。
- Given FULL 成功且独立门禁通过；When I1 选择增量；Then 父点及根均为 FULL 原编号；I2 父点为 I1，根仍为 FULL。
- Given 已写原编号回执；When 超时、进程中断或重新打开；Then 禁止重提，只从页面查询同一编号。
- Given 当前身份/计划/来源/门禁任一不符；When 准备最终点击；Then 无业务 POST，明确失败。

## 调用合同
脚本：`automatic_incremental_ui_acceptance.cjs`。以下命令仅为调用说明，准备阶段未执行。

```powershell
node TASK/automatic_incremental_ui_acceptance.cjs --kind FULL --phase preview --observation plan-1 --preflight TASK/full-preview-preflight.json --expected-application APP --expected-source intruoyi-57-safe-20261024-v1 --expected-state BASELINE_REQUIRED --expected-parent NONE --expected-base NONE --expected-plan PLAN_SHA256
node TASK/automatic_incremental_ui_acceptance.cjs --kind FULL --phase submit --execute --observation submit-1 --preflight TASK/full-submit-preflight.json --expected-application APP --expected-source intruoyi-57-safe-20261024-v1 --expected-state BASELINE_REQUIRED --expected-parent NONE --expected-base NONE --expected-plan PLAN_SHA256
node TASK/automatic_incremental_ui_acceptance.cjs --kind FULL --phase verify --expect-terminal --observation terminal-1 --preflight TASK/full-verify-preflight.json
```

I1/I2 使用相同参数；state=READY，I1 的 parent/base 均为 FULL 回执中的 operationId，I2 的 parent 为 I1 回执 operationId、base 为 FULL。每轮必须先取得前轮通过 verify 保存的成功终态文件。`APP` 和计划摘要由根 Agent 的当前安装与只读核对确定，不允许脚本猜测。

gate JSON 必须位于 TASK 内，格式：

```json
{
  "schemaVersion": "AutomaticIncrementalUiPreflight/v1",
  "status": "PASS", "experiencePreflight": "PASS",
  "kind": "FULL", "phase": "submit",
  "origin": "http://127.0.0.1:18080",
  "server": "172.30.30.57", "mode": "safe",
  "applicationId": "APP", "sourceConfigRef": "intruoyi-57-safe-20261024-v1",
  "implementationCommit": "40位最终提交SHA",
  "installationCommit": "与implementationCommit完全一致",
  "buildCommit": "与implementationCommit完全一致",
  "observedAt": "当前UTC时间，最多15分钟前",
  "expectedUserLabel": "管理员",
  "sourceIdentityVerified": true, "installationVerified": true,
  "sourceServicesHealthy": true, "archiveReady": true, "capacityReady": true,
  "noConcurrentMaintenance": true, "sourceIdleVerified": true,
  "expectedPlan": {"state":"BASELINE_REQUIRED", "parentChainRef":null, "baseFullRef":null, "planDigest":"64位当前计划SHA256"}
}
```

submit 必须 sourceIdleVerified=true；verify 允许原任务仍运行，仅检查同一回执原件。verify 的 expectedPlan 取本 kind 已落盘不可变回执，不填写新的 CLI 计划参数。原始鉴权失败可经真实登录恢复，不能跳过身份检查。

## 输出与限制
- TASK：`automatic-<kind>-ui-submission.json` 为提交前不可变回执；每次公开结果按 phase/observation 独立命名；成功终态为 `automatic-<kind>-ui-terminal.json`。
- PRIVATE/automatic-incremental-ui：截图和按 kind 保存的 session；运行时可复用 PRIVATE/spug-active-session.private.json，过期时读取既有 Spug 登录资料经真实页面登录。
- 计划或提交超时不重新提交；`UNKNOWN_KEEP_ORIGINAL` 必须使用 verify 跟踪。HTTP 409 的明确未受理仍保留本次回执，脚本不会自行删除回执或再执行。
- 页面报告 SUCCEEDED 仅证明对应原任务结果；根 Agent 仍需完成 gate 所要求的独立验证。

## 准备验证与冻结
- `node --check doc/tasks/20261106-spug-prod-incremental-to-two-targets/automatic_incremental_ui_acceptance.cjs` → PASS。只作静态语法检查，未执行 helper。
- 读代码核对：仅真实页面最终确认触发的自动提交可通过；放行前 wx/fsync 持久化原编号回执，计划/来源/应用/摘要逐项匹配。响应等待、正文读取或最终点击异常均仅尝试一次原编号的页面 GET 查询，保留回执且禁止再次 POST。
- verify 只读原件，RUNNING 与无查询错误的 SUCCEEDED 才能报告已观察状态；只有 SUCCEEDED 保存成功终态，不把未知、失败或查询异常当作成功。
- 最终实现提交必须为 40 位 SHA，且 implementationCommit / installationCommit / buildCommit 完全相等；不固定旧的 3019c2e。
- 2026-11-08 01:08:43 北京时间准备冻结。根 Agent 执行前必须填入新鲜 gate，并把本 helper 的实际执行结果另记为真实验收证据。

## 首次真实登录诊断修正
- 父任务首次 preview 在登录后等 token 超时；loginPosts=1、businessPosts=0，尚无提交。原失败观察保留。
- 只读核对当前 18080 静态主包 `/static/js/main.c2153b97.chunk.js`：内部 Axios 取根 data；`data.required_mfa` 进入验证码流程；正常登录依赖 `data.access_token`，`data.has_real_ip=false` 先确认安全提示再保存 token。旧 helper 只判断根 error，缺少成功数据与 MFA 阶段识别。
- BDD: Given HTTP200 但 required_mfa 或缺少最终 access_token；When helper 解析真实响应；Then 立即明确失败，不误等 token、不自动第二次登录。
- BDD: Given 真实成功数据且 has_real_ip=false；When 登录；Then 等真实安全提示可见、点击知道了、等待隐藏，随后验证 token 与平台身份；has_real_ip=true 直接等待已登录身份。
- BDD: Given 任一真实登录响应；When 响应到达；Then 原响应仅保存到该 observation 私密独立文件，公开输出只含 HTTP 状态与固定字段类型/布尔诊断，绝不输出 token、密码或原消息。
- RED：新增 TASK 内 `automatic_incremental_login_contract.test.cjs`，原 helper 未区分真实登录响应的成功/挑战合同，2 项失败。
- GREEN：响应检查提取为 classifyLoginContract；2 项通过，覆盖 MFA、缺失 data/token、根 error、HTTP 401/500，以及直接成功和安全提示两条正常路径。该测试只在 VM 中加载纯函数，不调用 main、不启动浏览器、不访问凭据或网络，不属于真实登录验收。
- 语法验证：`node --check .../automatic_incremental_ui_acceptance.cjs` → PASS；产品文件保持冻结。本轮仅只读获取 18080 的 HTML 和静态 JS 合同，未执行登录或业务请求。
- 下一次真实 preview 的响应保存于 PRIVATE/automatic-incremental-ui/<kind>-<phase>-<observation>-login-response.private.json；失败页面诊断保存为同前缀 -login-state.private.json。公开 loginShape 仅含固定 HTTP/布尔字段。第一次超时的真实原因仍待新响应证实，不将可能的 MFA 或安全提示当作已证实原因。

## MAIN cycle 显式模式

`--cycle` 和 `--selection` 必须成对。当前父选择为 `main-program-current-installations-45dd7dc-r6-v4.json`；脚本读取实际TASK文件字节生成pin，须与新鲜gate.deploymentSelectionPin完全相同。无这两个参数时继续原 stage/receipt/链合同；MAIN不得退回旧 automatic-full/i1/i2 选择或终态。

新gate schema为 `MainProgramAutomaticIncrementalUiPreflight/v1`。保留原 kind、phase、origin、server、safe、applicationId、sourceConfigRef、expectedPlan、15分钟新鲜度及身份/服务/归档/容量/无并发/submit空闲布尔门禁；再要求：

- cycle等于命令行；mainDeploymentVerified严格true。
- deploymentSelectionPin、controlGenerationPin、spugInstallationPin为TASK `{file,bytes,sha256}`，与严格五字段 `TaskMainProgramInstallations/v4` 选择逐项绑定。
- implementationCommit / installationCommit / buildCommit均为正式选择sourceCommit（当前45）；spugCommit为父已核实际Spug资源提交（当前565），不沿用旧演练Spug提交。
- sourceCaptureConfigurationPin、sourceOwnerConfigurationPin为已核绝对Linux路径 `{path,bytes,sha256}`。父Python验证实际MAIN范围/UUID及部署闭包，UI驱动不得替代该证明。
- baselineEvidencePin为TASK精确字节pin，文档schema `MainProgramAutomaticIncrementalUiBaseline/v1`，精确九字段：schemaVersion、status=PASS、cycle、observedAt、applicationId、sourceConfigRef、deploymentSelectionPin、expectedPlan、operationId。其cycle/app/source/selection及state/parentChainRef/baseFullRef/planDigest全等本次gate/CLI，文档自身也须15分钟内。

preview/submit baseline.operationId必须null；verify必须是原receipt.request.operationId，expectedPlan必须为原提交计划，不能用已经推进后的当前计划冒充。新cycle的I1表示本cycle首增量，可直接承接正式原生计划已证明的既有parent/base；不要求在本cycle先做FULL。FULL仍仅对应BASELINE_REQUIRED，I1/I2仍仅对应READY，类型不得改称。父负责原生完整链、实际来源恢复和独立终态验证。

以下仅调用说明，未在本阶段执行。TASK须展开为实际任务目录，gate与APP/计划取父新鲜预检：

```powershell
node TASK/automatic_incremental_ui_acceptance.cjs --cycle main-20261110-r6 --selection TASK/main-program-current-installations-45dd7dc-r6-v4.json --kind I1 --phase preview --observation plan-1 --preflight TASK/main-i1-preview-preflight.json --expected-application APP --expected-source intruoyi-57-safe-20261024-v1 --expected-state READY --expected-parent PARENT --expected-base BASE --expected-plan PLAN_SHA256
node TASK/automatic_incremental_ui_acceptance.cjs --cycle main-20261110-r6 --selection TASK/main-program-current-installations-45dd7dc-r6-v4.json --kind I1 --phase submit --execute --observation submit-1 --preflight TASK/main-i1-submit-preflight.json --expected-application APP --expected-source intruoyi-57-safe-20261024-v1 --expected-state READY --expected-parent PARENT --expected-base BASE --expected-plan PLAN_SHA256
node TASK/automatic_incremental_ui_acceptance.cjs --cycle main-20261110-r6 --selection TASK/main-program-current-installations-45dd7dc-r6-v4.json --kind I1 --phase verify --expect-terminal --observation terminal-1 --preflight TASK/main-i1-verify-preflight.json
```

MAIN使用headed Chrome并bringToFront，仍通过普通Playwright点击登录、选择与最终确认，不force click、不API提交或注入页面状态。最终POST放行前wx写入并fsync原请求回执，未知结果只从页面查询同一编号。

新产物为 `automatic-<cycle>-<kind>-ui-submission.json`、`automatic-<cycle>-<kind>-ui-terminal.json`（schema均v3）及同cycle观察结果。私密截图/响应/session位于 `PRIVATE/automatic-incremental-ui/<cycle>/`；旧路径原件不会覆盖。v3记录明确cycle及source/Spug/selection/control/capture/owner绑定；旧分支拒绝v3，新分支拒绝旧schema和错cycle。

本机验证：新增 `automatic_main_cycle_ui_contract.test.cjs` 9项+原stage4/login2共15 PASS、零skip；`node --check`通过。纯VM/临时文件测试没有启动浏览器、读取真实凭据或访问网络，不能冒称真实UI验收。完整RED/GREEN及范围见 `automatic-main-cycle-ui-tdd.md`。
