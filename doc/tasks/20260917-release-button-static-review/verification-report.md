# 指定提交发布按钮静态复查报告

## 结论

**FAIL：当前指定两份代码仍有 3 项 P1、1 项 P2。** 上一轮 R1-R5 已有实质代码修复，本轮没有沿用旧问题全部未修的结论；剩余问题是恢复状态与阶段解析、取消隔离、验收失败分支和验收人传递。

## 审查基线

- 应用根：`D:/IntRuoyiWorktree/r260911-release-button/a`；指定和实际 HEAD 均为 `548c5b151693c6ebb1ac3b1201364c561673a2a2`。
- 维护根：`D:/ProjectPackage/Int/IntRuoyiWorktrees/r260911-release-button/m`；指定 `0e0869` 唯一解析为实际 HEAD `0e08698ab0205b3643ea23bac1df6f5a058243c1`。
- 2026-09-17 00:27 +08:00 结束复核时，所审生产源码和测试源码相对指定提交无差异。两个 worktree 有未提交任务文档/经验记录，本报告不把这些文档当作新生产实现或发布成功证据。
- 仅静态读取 Vue/API、Controller、Workflow 服务、运行执行器、维护脚本、验收凭证模块、相关测试与 PRD。不运行构建、产品测试、E2E、服务器请求；不修改被审 worktree；不启用子 Agent。

## 已修正的上一轮问题

| 上轮问题 | 指定提交中的变化 |
| --- | --- |
| R1 来源更新后复用旧包 | 去重新增批准的三个 commit、preset、版本与 scope tuple 比较。 |
| R2 超时转失败后残留锁 | recoverStaleWorkflows 对恢复结果调用 releaseLeasesForState，终态释放相应锁。 |
| R3 派发后异常直接放锁 | 新增 dispatched / executionCommitted 边界；已派发异常进入 RECOVERY_REQUIRED，保持隔离锁。 |
| R4 正式开关拒绝判废 | 新增 previewExecution，在获取正式租约、推进状态前校验生产开关及确认文字。 |
| R5 成功后补写阶段 | 脚本在执行块前写阶段事件，编排器在 operation 运行期间消费 TESTING/BUILDING，缺失阶段不再伪造成功。 |

上述为源码层面确认，不代表本轮已执行相应测试。R5 新增的解析逻辑存在下述 S1。

## S1 / P1：恢复中的构建会使整个工作流列表报错

- 触发条件：build-release 已输出 TESTING 或 BUILDING 标记，随后取消、超时或派发后异常使 workflow 进入 RECOVERY_REQUIRED；用户刷新工作流列表或读取详情。
- [ReleaseWorkflowOrchestrator.java:259](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/releaseworkflow/ReleaseWorkflowOrchestrator.java:259) 仅对无 operationId 和 terminal 提前返回。RECOVERY_REQUIRED 不是 terminal，因此继续调用 advanceObservedBuildStages。
- [同文件:452](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/releaseworkflow/ReleaseWorkflowOrchestrator.java:452) 重读全部既有阶段标记；buildStageOrder 在 503-510 行将 RECOVERY_REQUIRED 映射为 -1，TESTING 为 1、BUILDING 为 2，均不满足下一阶段条件，457 行抛 `RELEASE_WORKFLOW_STAGE_SEQUENCE_INVALID`。
- [RuntimeControlController.java:175](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/runtimecontrol/RuntimeControlController.java:175) 在返回列表时对每项调用 reconcile；一项异常会使整个列表请求失败。前端 loadReleaseWorkflows 捕获后清空列表，其他健康工作流也无法从面板选择。
- 建议：阶段观察仅作用于明确的活动构建状态；RECOVERY_REQUIRED 作为隔离状态读取，不能因为 GET 请求重新进入构建推进。补“带阶段日志的恢复状态详情/列表可读且不改变状态”的回归。

## S2 / P1：取消写阶段后标记待恢复，却立即释放隔离锁

- 触发条件：TEST_DEPLOYING / PROMOTING_PROD 取消，底层本地进程确认结束，但尚未完成目标状态或补偿核验。
- [ReleaseWorkflowService.java:181](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/releaseworkflow/ReleaseWorkflowService.java:181) 将写阶段取消转为 RECOVERY_REQUIRED，并保留 zeroWriteEvidence=false。
- [ReleaseWorkflowOrchestrator.java:337](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/releaseworkflow/ReleaseWorkflowOrchestrator.java:337) 收到这一结果后无条件调用 releaseAllLeases。没有目标运行态、远端锁、数据库写入或补偿完成证明。
- 后果：状态仍为“需要恢复确认”，同环境另一 workflow 却可以取得本地执行租约，隔离保护失效。本地进程结束不能单独证明远端任务和目标写入安全停止。
- 与现有 PRD 163、175、177 行要求的 RECOVERY_REQUIRED 原租约隔离不符。正常 FAILED/CANCELED 可释放与待恢复必须隔离应明确区分。
- 建议：取消后复用按结果状态处理租约的统一规则，对 RECOVERY_REQUIRED 保持环境隔离，完成恢复审计后再释放；补取消写阶段后第二个 workflow 获取同环境租约仍受阻的回归。

## S3 / P1：测试验收没有失败分支，失败结论也走“测试通过”链

- 触发条件：测试发布及包验证前置满足，用户在验收结论填入例如 `FAIL：登录验证未通过`，点击“记录测试验收”。
- [index.vue:1334](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiFronted/src/views/infra/runtime-control/index.vue:1334) 仅检查结论非空；[RuntimeControlReleaseWorkflowTestAcceptanceReqVO.java:10](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/controller/admin/runtimecontrol/vo/RuntimeControlReleaseWorkflowTestAcceptanceReqVO.java:10) 只有 NotBlank，没有结构化 PASS/FAIL 结果。
- [ReleaseWorkflowOrchestrator.java:172](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/releaseworkflow/ReleaseWorkflowOrchestrator.java:172) 无条件调用 mark-release-tested；其成功后 434-437 行无条件进入 TESTED。
- [ReleasePackageGovernance.psm1:545](/D:/ProjectPackage/Int/IntRuoyiWorktrees/r260911-release-button/m/ops/release/lib/ReleasePackageGovernance.psm1:545) 也只检查 TestConclusion 非空，并在 553-575 行写 tested.json。晋级验收凭证校验 655 行同样只检查非空。
- 后果：失败结论文本不会阻断 TESTED 或测试凭证生成，在其他门禁满足后可继续申请正式授权；正式授权本身仍受独立保护，但“验收未通过不得晋级”的门禁缺失。PRD 169 行明确要求人工 FAIL -> FAILED、退休 tag。
- 建议：使用明确的验收结果字段与独立失败路径；失败结果记录缺陷并退休 workflow，不写成功凭证。不使用关键词猜测自由文本代替正式结果字段。

## S4 / P2：测试验收人被记为机器账户，而非登录用户

- 应用已知真实操作者：RuntimeControlServiceImpl 的 operation.requestedBy 被传入 action.buildArguments。
- [RuntimeControlOperationAction.java:120](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeControlOperationAction.java:120) 只在 backup action 添加 OperatorName；[同文件:370](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeControlOperationAction.java:370) 的 mark-tested 参数没有操作者。
- [publish-int-ruoyi.ps1:12](/D:/ProjectPackage/Int/IntRuoyiWorktrees/r260911-release-button/m/ops/deploy/publish-int-ruoyi.ps1:12) 默认 OperatorName=$env:USERNAME，3257 行将该值作为 TestedBy；凭证在 ReleasePackageGovernance.psm1:564 原样记录。
- 后果：不同应用用户通过按钮验收，正式 tested.json 中都可能成为同一个 Windows/服务账户，与工作流及 operation 的真实操作者不一致。USERNAME 缺失时则在 testedBy 校验失败。
- 建议：由后台将已认证操作者显式传给 mark-tested，凭证与 operation/workflow 审计身份绑定；禁止让客户端自由提交验收人。

## 静态验证说明

- 已对比上轮 c3220239d/71b86b7 与指定提交的所有相关代码差异，并追踪各问题的完整入口和分支。
- 新增测试覆盖来源 tuple、超时终态释放、派发隔离、正式预检以及正常阶段事件；未见覆盖恢复状态读列表、取消后隔离锁、验收 FAIL 分支及 testedBy 参数传递的行为断言。
- 不将“测试里未覆盖”单独当成产品缺陷；S1-S4 的结论均有可达代码路径和明确后果。
- 未执行测试，不给出运行态成功或服务器部署结论。两个被审 worktree 未修改。

## 最终判定

- logic_status: fail
- runtime_verified: false
- independent_agent_review: not_used
- findings: P1=3，P2=1
- 建议先关闭 S1-S3，再修审计身份传递；保持已修 R1-R5 的回归，之后才进行另行授权的真实按钮验收。
