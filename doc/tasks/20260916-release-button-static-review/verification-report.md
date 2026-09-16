# 发布按钮静态代码审查

## 最新复查结论（2026-09-16 17:40 +08:00）

**仍为 FAIL，但不能继续沿用下方首轮 6 项 P1 全部未修的结论。** 应用最新提交为 `c3220239de7f06a6c2eabc31c9b840d9a599d768`，维护最新提交为 `71b86b719d70bff77f37966a54ddd9a6e8c51a13`。审查根与首轮相同；应用所审文件无未提交差异，维护 ops/deploy 与 ops/release 相对首轮无代码差异。主工作区仍为 `cd147f697dcdf69b7ff7e551c8c9aaf8edf8bcde`，不能把 worktree 修复当作主线已经运行。

### 首轮问题的当前状态

| 原问题 | 本轮静态复核 |
| --- | --- |
| F1 app-release 被拒绝 | 已修正：Action 只接受正式 app-release，并生成对应 scope 与禁数据同步参数。 |
| F2 旧脚本绑定 | 已修正：发布动作使用 releaseWorkflow.publishScriptPath，workingDirectory 绑定 maintenanceRepoRoot，build 显式传应用前后端根目录。真实配置仍需在运行验收中确认。 |
| F3 旧 actions 授权旁路 | 已封堵原外部请求旁路：新增必需的内部 workflow context，三个字段 @JsonIgnore，外部 JSON 无法填充它们，缺少 context 会被 guard 拒绝。 |
| F4 等待状态超时 | 已修正：isHeartbeatMonitored 明确排除 READY/TEST_DEPLOYED/TESTED。 |
| F5 TESTED 锁泄漏 | 正常验收成功路径已修正：TESTED 释放 test lease，map 改为 workflowId:environment。另有超时恢复路径泄漏，见 R2。 |
| F6 派发早于持久化 | 主要顺序已修正：预分配 operationId 并先保存状态再派发；派发成功后异常的处理仍不完整，见 R3。 |
| F7 成功后补写阶段 | 仍存在，见 R5。 |
| F8 无法选择工作流 | 已修正：新增 selectedReleaseWorkflowId 和选择框，刷新时保留有效选择。 |

这里的“已修正”均为代码层面确认；本轮没有执行产品测试或真实按钮验收。

### 当前剩余问题

#### R1 / P1：批准提交变化后，“生成程序安装包”可能直接返回旧包

- `ReleaseWorkflowService.java:53` 的去重只比较非终态、reason、sourceSelectionId，未比较批准的 maintenance/application/frontend commits 和 preset。
- `ReleaseWorkflowOrchestrator.java:61` 创建后，只要已有 operationId 就直接 reconcile 返回；不会重新执行源码冻结或构建。
- 触发：A 包处于 READY 或 TESTED；服务端批准源码从 A 更新为 B，但仍使用同一合法 sourceSelectionId 和同一发布原因。前端 `index.vue:1271` 固定传 approved-source，默认原因也相同，因此该场景并非只靠非法参数才能发生。
- 后果：点击生成新包返回 A 的旧 workflow/tag，B 不会构建。页面仍提示已创建工作流，可能让操作者误认为拿到新源码产物。
- 修复：去重绑定完整已批准来源 tuple，或使用明确的一次请求幂等键；不能仅用可重复的原因文本作为身份。

#### R2 / P1：超时取消构建后仍可能永久占用 build 锁

- `ReleaseWorkflowOrchestrator.java:343` 取消超时 operation 后，`:352` 直接调用 service 的恢复方法；未释放相应 lease。
- `ReleaseWorkflowService.java:199` 将非写阶段标成 FAILED；正常实际构建一直处于 PREFLIGHTING，因此会走此分支。
- 后续 `reconcileActiveWorkflows:266` 跳过 terminal；直接 reconcile 在 `:232` 也提前返回，没有机会进入 `:246` 的释放逻辑。
- `ReleaseWorkflowLease.java:51` 只把 ttlSeconds 写进文件，没有定时释放机制；OS lock 需 `Handle.close:86` 才会正常释放。
- 后果：底层进程确认终止且 workflow 已失败后，build lease 仍保存在 activeLeases，新构建持续锁冲突。不能用重启服务代替正式生命周期处理。
- 修复：对恢复返回的终态逐项释放已确认安全结束的对应租约；RECOVERY_REQUIRED 的隔离锁按恢复合同保留，不能一概释放。

#### R3 / P1：派发成功后的异常仍会提前释放锁

- 当前已先保存 operation 关联，原顺序缺陷不再完整适用。
- 但 `startTestPublish:127` 派发返回后仍执行 `requireOperationBinding:128` 和 `workflowService.require:129`；持久化文件读取异常或 operation 绑定异常会进入 `:130`，直接释放 test lease、尝试记 FAILED，却未确认已派发进程停止。build 和正式晋级存在同型 catch。
- 后果：在这一异常触发条件下，部署可能仍执行，workflow 却已失败且环境锁释放。它不是正常点击必现问题，但属于真实 I/O/一致性故障路径。
- 修复：区分派发前拒绝与派发后状态未知；后者应保留隔离并进入恢复流程，确认底层终态和目标状态后再处理锁。

#### R4 / P2：正式发布开关关闭时，会把已验收包判废

- `ReleaseWorkflowOrchestrator.java:201` 调用 authorizationService.preview；该方法以 execute=false 校验，`:154` 的 productionWriteEnabled/PROD 检查只在 execute=true 时执行。
- 编排器在 `:206-210` 已把 TESTED 推进到 PROMOTING_PROD，`:211` 才执行正式开关/确认校验；被拒绝后 `:225` 把 workflow 置 FAILED。
- 触发：已验收包和有效 grant，productionWriteEnabled=false（默认值）或确认文本不合要求。
- 后果：没有启动底层发布也没有消费授权，仍使合法 TESTED 包变成 FAILED，之后不能直接重试。这是前置拒绝被当成发布失败，违背 PRD 的“preview/参数/授权拒绝保留 TESTED”行为。
- 修复：在占用正式执行状态和创建 operation 意图前完成全部只读准入检查；真正进入执行后的失败再按退休规则处理。

#### R5 / P2：真实阶段和失败定位仍未接入

- `startBuild:75` 进入 PREFLIGHTING，只有在 operation 整体 succeeded 后，`advanceSucceeded:371-385` 才依次补写 TESTING、BUILDING、READY。
- Maven、前端和 Docker 执行中不会显示相应阶段，失败仍使用 `reconcile:243` 的当前状态报 PREFLIGHTING；阶段 evidenceRefs 仍为拼接路径而非逐阶段验证产物。
- 修复：让受控执行器输出真实阶段事件并绑定实际证据，不能把最终 succeeded 回填成各阶段均已验证。

### 本轮证据与建议顺序

- 通过 git diff 逐项核对 c3220239d 相对首轮的 12 个相关生产文件改动，并回读完整失败/恢复分支、授权服务、租约实现和新增测试。
- 新增测试已覆盖 scope/toolchain、直接 action 拒绝、READY 等待、TESTED 释放和预分配 ID；本轮只读取测试，没有将其视作本次运行通过。
- 建议先修 R1/R2/R3，再修 R4/R5；保持已修复六项的回归，随后再进行已授权范围内的真实按钮验收。
- 本轮未运行构建、产品测试、E2E、远端操作或修改生产代码，未启用子 Agent。

---

下方为 12:49 首轮审查历史，旧问题状态以上方最新复查为准。

## 结论与审查边界

**结论：FAIL，当前发布按钮逻辑不能放行。** 存在新旧调用合同断裂、授权旁路、状态超时与锁生命周期问题。下面结论来自静态调用链，不等同于已执行按钮、构建、发布或远端验证。

- 时间：2026-09-16 12:49 +08:00。
- 应用审查根：`D:/IntRuoyiWorktree/r260911-release-button/a`，HEAD `8ef8b1a5f0ddbdacd53c2a4bcdb3e94839c98936`。
- 维护审查根：`D:/ProjectPackage/Int/IntRuoyiWorktrees/r260911-release-button/m`，HEAD `a2c73110a90eb7344c6ae5f4eceb1085954426ca`。
- 开始与结束时 HEAD 一致，所审文件无未提交差异。
- 主工作区 `E:/IntRuoyi` HEAD 为 `cd147f697dcdf69b7ff7e551c8c9aaf8edf8bcde`，页面、API、Controller 与任务 worktree 不同，且没有新的 ReleaseWorkflowOrchestrator。以下审查的是正在开发的新版按钮代码，不据此推断当前端口所加载的版本。
- 仅检查代码；没有读取秘密配置，没有运行产品测试或发布，没有服务器请求。发现问题后未自动修改并发任务代码。

## 实际调用链

主程序 `IntRuoyiFronted/src/views/infra/runtime-control/index.vue` 的三个按钮，经 `src/api/infra/runtimeControl/index.ts` 调用 `/infra/runtime-control/release-workflows` 及 publish-test/promote-prod 子路径，进入 `RuntimeControlController -> ReleaseWorkflowOrchestrator -> RuntimeControlServiceImpl -> RuntimeControlOperationAction -> RuntimeControlCommandExecutorImpl`。

关键断点是：新 orchestrator 使用 app-release，但低层 action 仍使用旧 scope 与 `script/deploy/publish-int-ruoyi.ps1`。维护任务最近修复的是 `ops/deploy/publish-int-ruoyi.ps1`，不在这个相对路径上。

## 阻塞问题

### F1 / P1：生成安装包按钮必然被旧 scope 校验拒绝

- 触发：配置与权限前置均满足，点击“生成程序安装包”。
- 证据：`ReleaseWorkflowOrchestrator.java:75` 设置 `ReleaseWorkflowContract.PUBLISH_SCOPE`，该常量在 `ReleaseWorkflowContract.java:11` 为 `app-release`；`RuntimeControlServiceImpl.java:912` 调用 `supportsPublishScope`，而 `RuntimeControlOperationAction.java:64`、`:65`、`:183` 仅允许 `code-only/with-data`。
- 后果：真实 service 在进入脚本前报 publishScope 参数无效；orchestrator catch 随后将 workflow 标为 FAILED。配置 approved commits 或修改服务器均不能解决这个代码冲突。
- 修复方向：统一正式 scope 到同一 action/guard/参数生成链，不通过转换为 code-only 规避。
- 验证缺口：`ReleaseWorkflowOrchestratorTest.java:46` mock 了 RuntimeControlService，`:58` 直接返回 operation；因此该测试只证明传了 app-release，没有验证真实下游接受它。没有据此否定所有测试，只限定该用例的证明范围。

### F2 / P1：按钮执行器仍绑定另一套旧发布脚本

- 证据：`RuntimeControlOperationAction.java:18`、`:22`、`:30`、`:34` 指向 `script/deploy/publish-int-ruoyi.ps1`，`resolveScriptPath:87` 对发布动作不改写路径；`RuntimeControlCommandExecutorImpl.java:588` 将此路径直接拼到 repoRoot。
- 对照：应用 worktree 的 `IntRuoyiBackend/script/deploy/publish-int-ruoyi.ps1` 是独立旧脚本，仍有 direct 模式和 code-only/with-data 分支；未声明新 ExpectedMaintenanceCommit、ExpectedApplicationCommit、ExpectedFrontendCommit、SourceSelectionId 和 TestOperationEvidencePath 等顶层参数。维护 worktree 中该旧相对路径不存在，实际正式脚本在 `ops/deploy/publish-int-ruoyi.ps1`。
- 后果：repoRoot 指向应用后端时运行旧实现；指向维护根时找不到该脚本。只修 F1 仍不能让按钮使用最近修复的发布链。
- 修复方向：明确单一脚本所有权和正式调用入口，同步 builder、执行目录、源根参数与脚本合同；不保留互相漂移的两套发布实现。

### F3 / P1：低层 /actions 能绕过新版正式授权守卫

- 证据：`RuntimeControlController.java:127` 的 POST /actions 与新 workflow 操作均只要求 `infra:runtime-control:operate`，随后直接调用 runtimeControlService。`RuntimeControlServiceImpl.java:882` 的 guard 检查原因、PROD、环境、负责人、包已 tested 和 test-operation evidence，但不检查 workflow grant、一次性消费、stateVersion 或 releaseWorkflow.productionWriteEnabled；这些检查仅存在于 `ReleaseWorkflowAuthorizationService.java:125`、`:154` 和 orchestrator 正式晋级分支。
- 触发：有 operate 权限的调用方绕过新页面，向旧 /actions 提交 promote-prod 并满足旧 guard。
- 后果：请求可以越过新版 productionWriteEnabled=false 和一次性授权约束进入低层执行路径。现有脚本合同错误可能进一步阻断执行，但不能作为授权边界。
- 修复方向：低层发布动作统一强制验证服务端 workflow 执行上下文，或禁止外部请求直接调这些发布动作；隐藏旧前端入口不等于后端已封闭。

### F4 / P1：正常等待人工操作会被误判为心跳失败

- 证据：`ReleaseWorkflowService.java:168` 只排除 terminal 状态，按 lastHeartbeatAt 统一超时；`:199` 对非 write-stage 直接写 FAILED。`ReleaseWorkflowRecord.java:151` 的 terminal 不包括 READY、TEST_DEPLOYED、TESTED；`RuntimeControlProperties.java:361` 默认 15 分钟。`ReleaseWorkflowRecoveryScheduler.java:24` 每 30 秒执行。
- 触发：包构建就绪后 15 分钟未点击发布，或测试已部署/已验收后等待人工操作超过 15 分钟。
- 后果：这些合法等待状态变为 FAILED；正常刷新不会续心跳，因为 succeeded operation 的 reconcile 在这些稳定状态不产生新状态事件。
- 修复方向：心跳只用于有活动执行阶段的工作流；稳定等待状态不继承进程存活超时。

### F5 / P1：测试验收成功后测试环境锁不释放

- 证据：`ReleaseWorkflowOrchestrator.java:139` 在 acceptTest 获取 test 租约，`:145` 放入 activeLeases；mark-release-tested 成功后 `:369` 推进到 TESTED，但 `:225` 只在 terminal、READY、TEST_DEPLOYED 时 releaseLease。TESTED 不满足任何释放分支。
- 后果：下一次测试发布/验收获取 test.lock 失败。后续正式晋级还会在 `:181` 用同一 workflowId 的 prod lease 覆盖 map 中 test lease 引用，不能保证旧锁正常关闭。
- 修复方向：按底层操作生命周期管理租约，在验收终态明确释放对应环境锁；不依靠 GC 或服务重启回收。

### F6 / P1：异步进程启动早于工作流持久化，异常路径会释放仍在使用的锁

- 证据：`RuntimeControlServiceImpl.java:255` 已提交后台执行；orchestrator 的 `startTestPublish:118` 返回后才在 `:119` assignOperation、`:121` 推进状态。若这些持久化操作抛异常，`:123` 仅释放租约并抛出，未取消已启动 operation、未进入 RECOVERY_REQUIRED。正式晋级 `:196` 至 `:205` 具有同类顺序，且 `:188` 已先消费授权。
- 触发：后台任务已启动后发生文件系统写失败、CAS 冲突或其他状态保存异常。
- 后果：后台部署可能继续运行，而 workflow 仍显示旧状态、没有正确 operation 绑定且环境锁已释放；后续请求可能重入。远端锁可能再阻断重入，但不修复本地丢失关联和错误状态。
- 修复方向：先原子持久化执行意图/operation 关联并占有租约再派发；派发或保存后续失败时保留隔离状态并明确确认进程终态后处理锁。

## 其他可证实问题

### F7 / P2：构建阶段是成功后补写，失败阶段不真实

- `startBuild:87` 只写 PREFLIGHTING；`advanceSucceeded:346` 仅在整个 build-release succeeded 后连续写 TESTING、BUILDING、READY。
- Maven、前端或 Docker 执行中，页面一直显示预检；失败通过 `reconcile:220` 使用当前状态作为 failedStage，因此实际构建失败也显示 PREFLIGHTING。
- `ReleaseWorkflowService.java:143` 生成 `workflow/<stage>.json` 引用，store 只持久化 workflow envelope，未见这些路径对应的阶段证据文件创建。
- 应由真实阶段事件和对应证据推进，不将“进程成功”回填成曾逐阶段验证。

### F8 / P2：页面只操作排序第一条工作流，无法选择之前的包

- `index.vue:852` 固定取 releaseWorkflows[0]；模板无 workflow 选择入口；`ReleaseWorkflowStore.java:63` 按文件修改时间倒序，不按用户选择。
- 创建另一个工作流或别的工作流发生心跳/状态更新后，刷新会改变当前按钮目标。之前 READY/TESTED 的包不能从该面板重新选中；等待异步确认时用户还需留意目标漂移。
- 应显式保留用户选中的 workflowId，并提供历史工作流/包的选择入口；修改时间排序不能替代操作对象选择。

## 已确认正常或本轮不作缺陷结论的部分

- 主页面三个新按钮已调用对应 workflow API，客户端未提交主机、NAS 或路径参数。
- 新 workflow 授权服务实现了 tuple 绑定、有效期与消费检查；F3 是旧入口未统一受到其约束。
- 当前维护脚本 `publish-int-ruoyi.ps1:6032` 仍检查 route hook 退出码为 0；此前讨论中的“非零退出仅诊断”不能当作当前代码缺陷。应用 runner 已改为传递命令退出码。此处只确认当前源码，不声称运行验证通过。
- 没有执行真实 UI、操作系统进程、NAS 或服务器验证，不对当前运行服务版本及本轮发布是否成功作结论。

## 文件根与定位说明

上述 Java 类除 MES runner 外均位于应用根的 `IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/`；controller 在 `controller/admin/runtimecontrol`，配置在 `framework/runtimecontrol/config`，其余在 `service/runtimecontrol` 或下级 `releaseworkflow`。测试在同模块 `src/test/java`。Vue 文件位于 `IntRuoyiFronted/src/views/infra/runtime-control/index.vue`。

## 审查与执行状态

- logic_status: fail
- usability_status: fail（F7/F8 静态可证实）
- ui_status: not_assessed_static_scope
- final_decision: fail
- 审查任务完成不代表被审功能完成。用户仅要求静态审查，未执行修复。
- 原拟使用独立 reviewer，读取目标仓 AGENTS 后发现需要当轮明确授权，已中断全部子 Agent；无子审查结果被用作本报告的独立验收证据。此报告为主任务直接静态审查。
