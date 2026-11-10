# MAIN 自动备份 UI 驱动命名空间与部署绑定

## Current Status

ready_for_closeout。本机新9项+旧6项实际15 PASS/零skip，node --check通过；驱动和测试冻结，等待父独立核验/提交及新鲜gate后的真实UI。父事前计划为 continuation-review-20261110-r6.md。本阶段仅本机重构验收驱动/测试/说明，不改产品、不运行真实浏览器、E2E、服务器或备份，不提交或清理。新鲜 MAIN 计划已由父确认 READY，可承接已有父/根，不能假设需要重做 FULL。

## 目标、里程碑与预期验证

1. 新增成对显式 `--cycle` / `--selection`，所有本轮产物和私密观察按 cycle 隔离，wx/fsync 原件不可覆盖。
2. 新 MAIN gate 明确绑定正式 v4 selection、source/control/capture/owner 和当前 Spug 部署；原无 cycle 分支及旧 receipt 合同保持。
3. 新 cycle 从当前已验证 READY 链开始；新鲜 baseline observation 与 gate/CLI 的 state/parent/base/digest 精确绑定。旧 FULL/I1/I2 仍核原成功文件链。父已确认baseline schema和精确九字段。
4. BDD→真实本机 RED→最小实现→GREEN→旧/新回归；语法检查与原件不覆盖测试必需。父另做真实页面验收。

## 经验门禁

- Trigger：同 sourceConfigRef 由演练转真实 MAIN，已装正式 v4 后需新的自动增量验收周期。
- Preflight check：读 continuation-review-20261110-r6.md 与 docs/release-agent-checklist.md“自动增量链与恢复周期门禁”；当前部署/父链/UUID/日志/来源恢复由父新鲜 Python gate 独立核验。既有 FULL373/374/375 不能凭名称当演练或重做。
- Blocker：缺 cycle/selection 之一、错 schema/部署 pin、旧 cycle 原件冒用、计划/基线错配、过期门禁、未知提交、已有不可变回执。
- Verification：Node 纯函数和真实临时文件用例，旧合同回归；真实 UI 由父事先记录高风险 preflight 再执行。本阶段不将纯函数或协议测试称为 E2E。
- Forbidden action：不覆盖旧 automatic-full/i1/i2；不以 API 替代 Playwright click，不 force click、不注入页面业务状态；不自动重发未知 POST，不改产品或重做已有 FULL。
- Evidence：本日志、新 Node 测试与实际 RED/GREEN 原输出，父后续真实 preflight/观察/提交回执。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。无 cycle 保持旧合同，显式新 cycle 只能新 schema，不能退旧选择。
- 是否从根因和长期维护角度解决：是。周期作为验收产物作用域，当前部署和原编号显式绑定，不依赖旧演练文件名。
- 是否存在临时补丁或绕过：否。

## BDD

- Given 旧无 cycle 参数和旧 gate/receipt，When 验证，Then 原选择/部署/链与文件名严格保持，不能接受新 MAIN receipt。
- Given cycle 与 v4 selection 成对提供，When MAIN preflight，Then schema/cycle/文件原 SHA/source45/Spug565/control/capture/owner 全绑；缺项/漂移拒绝。
- Given 当前正式 READY 计划和真实 observation，When 本 cycle I1，Then 精确承接其已存在 parent/base，不要求同 cycle 新 FULL；baseline 错绑/过期/不一致拒绝。
- Given 不同 cycle 相同 kind/observation，When 产生 public/private 文件，Then 路径不重叠；同 cycle 原件只能 wx 独占写，未知回执只能 verify 同编号。
- Given 新 submission/terminal v3，When verify，Then 同 cycle/selection/部署 pins，旧分支不可接纳；通过原 UI 只读原编号，不能重新 POST。
- Given 新 MAIN 模式，When 实际运行（父阶段），Then headed 普通 click/bringToFront；最终 POST 前先 wx+fsync，未知只查询原编号。

## 正式接口

成对 `--cycle <namespace> --selection <TASK/v4.json>`。gate schema MainProgramAutomaticIncrementalUiPreflight/v1，原范围/新鲜度/健康/空闲门禁保持；cycle/deploymentSelectionPin/controlGenerationPin/spugInstallationPin/sourceCaptureConfigurationPin/sourceOwnerConfigurationPin/mainDeploymentVerified严格绑定。impl/install/build取v4.sourceCommit，Spug为实际资源提交；源与owner pin为严格绝对Linux pathpin，TASK pin严格三字段与实际字节。selection必须是TaskMainProgramInstallations/v4精确五字段。

baselineEvidencePin指向MainProgramAutomaticIncrementalUiBaseline/v1，精确九字段schemaVersion/status/cycle/observedAt/applicationId/sourceConfigRef/deploymentSelectionPin/expectedPlan/operationId。preview/submit operationId=null；verify为原请求ID，plan始终原提交计划。baseline年龄最多15分钟，cycle/app/source/selection及四计划字段全等。新I1/I2不要求本cycle FULL文件，旧mode仍核原FULL/I1/I2完整终态链。

产物与私密观察以cycle分离；submission/terminal新v3显式全部部署绑定，旧mode不接纳v3。新MAIN headed+bringToFront，页面click/最终POST前wx+fsync/未知仅查询原编号保持。没有新增产品入口或通用执行框架。

## 实际 TDD

RED：`node --test TASK/automatic_main_cycle_ui_contract.test.cjs` 实际exit1，8 FAIL / 0 PASS / 0 skip，248.4828ms；前7项缺artifactPaths/MAIN合同，最后一项缺MAIN headed。输出在原工具终态，未伪造原始log文件。

首最小实现后实际7 PASS / 1 FAIL，616.2772ms。失败是测试载体让gate.deploymentSelectionPin和CLI实际selectionPin共享同一个可变对象，篡改同时改变两者，未模拟两个独立JSON读取；仅将fixture pins改为独立对象，不改业务期望。随后新8+旧6实际14 PASS / 0 skip，442.3354ms，原日志automatic-main-cycle-ui-green-r1.log。

补BDD/RED：MAIN terminal也必须绑定source implementationCommit。新增精确负例 `node --test --test-name-pattern="terminal binding" TASK/automatic_main_cycle_ui_contract.test.cjs` 实际exit1，1 FAIL / 0 skip，91.3561ms，Missing expected exception。最小实现将同cycle record的source commit加入原部署绑定检查，既有terminal再核kind/app/原计划与实际SUCCEEDED；不覆盖旧文件。

REGRESSION：`node --test TASK/automatic_main_cycle_ui_contract.test.cjs TASK/automatic_stage_ui_contract.test.cjs TASK/automatic_incremental_login_contract.test.cjs` 实际exit0，15 PASS / 0 skip，655.6717ms，原日志automatic-main-cycle-ui-regression-r1.log。`node --check TASK/automatic_incremental_ui_acceptance.cjs`实际exit0。测试只VM及真实临时文件，明确没有浏览器/网络/凭据/真实preflight，实际UI仍由父执行。
