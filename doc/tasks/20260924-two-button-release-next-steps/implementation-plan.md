# 两入口发布下一步实施计划

## Request：已确认目标
保留构建、部署、验收、晋级阶段及代码，前端收敛为“发布到测试服”“晋级正式服”两个主要入口。每次发布的准备、执行、验证、进度和失败处理由固定后端代码完成，不依赖Agent临时拼命令。本轮仅分析和规划，没有修改产品或执行发布。

## Baseline：已核对事实
- R22批准应用：`b15b52e0c4c14ed46ebe0772ba4aea2caa8df090`；维护：`2a867b91c9add6ec681831e927b347d2e7b088bf`。
- 参照工作区：`D:/IntRuoyiWorktree/r260924-r22-button-release-r2/app`、`maintenance`。冻结发布输入只读，不在其中开发新功能。
- 规划时应用主线HEAD=`f46b0bdc2`，维护HEAD=`151d976`；与R22分支的发布相关代码有差异：应用3个文件、维护7个文件。实施前必须辨明未集成修复和后续改动，不能从主线直接开工而丢失已审查能力。
- 前端 `IntRuoyiFronted/src/views/infra/runtime-control/index.vue:77–99` 有四阶段按钮。`publishWorkflowToTest` 只接收READY，构建和部署未合并编排。
- 后端已有 `ReleaseWorkflowOrchestrator.startBuild/startTestPublish/acceptTest/startProductionPromotion`。构建成功推进到READY后停止；`ReleaseWorkflowRecoveryScheduler`已有周期收束，可扩展为自动推进，不另建调度平台。
- `ReleaseWorkflowRecord/Store/Service` 已有源提交、状态版本、操作ID、事件、双摘要和租约；正式预览、一次性授权、测试证据服务已存在。
- 维护执行器仍复用 `ops/deploy/publish-int-ruoyi.ps1` 及迁移、包校验、锁/fence组件。当前锁赋值顺序疑点必须先用真实生成SQL复现，不能把静态推断写成已验证根因。

## Classification / Decision
分类：产品交互收敛、后端编排增强和可靠性修复。**Decision：接受方向、分阶段实施**，依据用户明确同意。

旧R22 GO只对应旧精确提交。新增代码必须提交和独立复检；不得修改冻结发布器后重设SHA继续沿用旧批准。本轮产出计划，不执行当前失败发布的解锁或重试。

## 两个入口的行为合同

### 发布到测试服
用户选择服务端批准的版本来源并填写原因，点击一次；后台完成：

`冻结三角色源 → 准备本次隔离worktree和依赖 → 前置检查/测试 → 构建/打包/校验 → 测试服取锁/部署 → 健康与版本验证 → TEST_DEPLOYED`

READY保留为内部检查点，由后台继续，不再要求用户点第二次部署。浏览器只提交意图和读取状态，不承担串联阶段的职责。

### 晋级正式服
- 选择同一发布记录，点击晋级。若处于TEST_DEPLOYED，在弹窗中收集真实验收结论、测试证据和有效恢复候选，复用acceptTest形成TESTED。
- 已TESTED则直接进入既有正式预览；用户确认后复用授权grant、stateVersion和幂等键，部署测试过的同一不可变包。
- 打开弹窗不能自动标PASS。取消不触发生产操作，证据缺失/过期/目标变化则阻断。
- 测试验收与正式确认仍是页面内必要决定；“两个入口”不是取消验收或限定只能点击两次。

### 范围
只收敛顶层入口，不删除内部四阶段能力，不另起部署平台，不顺带复制业务数据。沿用app-release和正式版本化迁移，不改写已执行的旧migration。

一次性安装/安全配置可由管理员完成；每轮源冻结、临时worktree、依赖核对、构建和部署必须进入受控代码。操作者不得需要临时SSH、SQL、改状态或清锁才能完成正常发布。

## Impact：改动面与复用
| 层 | 复用 | 增量 |
| --- | --- | --- |
| 前端 | 现有运行控制台、候选控件、生产弹窗 | 两个主入口；测试验收移入晋级弹窗；阶段进度/错误/结果；保持IntPP样式 |
| API | 专用workflow controller及API模型 | 明确测试发布意图和幂等身份，服务端决定环境、源和执行器；不收任意host/path/command |
| 编排 | Orchestrator、Service、RecoveryScheduler | 持久化执行目标，READY后自动部署，安全续接、防重复派发 |
| 存储 | Record、Store、事件、stateVersion、operation | 持久记录目标和阶段派发事实；不依赖内存回调 |
| 输入准备 | 源冻结、worktree和依赖工具 | 每次批准输入自动隔离，记录源提交和执行器SHA |
| 发布器 | 现有PowerShell和迁移/manifest合同 | 锁SQL及失败边界修复；保留lease、heartbeat、fence和未知态保护 |
| 生产保护 | 测试证据、Preview、Authorization | 同包晋级，真实验收和一次性确认，目标变化使旧授权失效 |

历史READY/FAILED记录缺少新执行目标时不得自动部署。仅明确由新入口创建的测试发布任务自动推进，不能把旧失败tag作为新版验收。

## 六个交付阶段

### M0：基线与现场边界
在新开发worktree选择性对齐当前int_main与R22发布相关实现/测试，保留无关并发业务改动。参与仓库按实际Git根确定，应用与维护使用同名任务分支；不在无关仓库创建分支。建议开发目录 `D:/IntRuoyiWorktree/two-button-release/app|maintenance`，本规划不实际创建。

当前失败operation/tag保留证据；由原任务同步FAILED状态并脱敏日志，查锁owner/lease/fence，不手工清锁。**完成条件：**源码基线、差异归属、工作区/端口和验证命令明确。

### M1：发布锁与状态可靠性
先在隔离真实MySQL中执行生产生成的获取锁SQL，覆盖首次获取、APPLIED/FAILED旧行重获、同tag新lease、活动他人锁拒绝、旧owner失权和SSH/SQL异常。不能用另一条手写UPDATE代替实际SQL。

确认根因后最小修复赋值/条件更新顺序，保留现有租约协议。统一workflow/operation/页面终态：只在证明零写入且目标未变时允许安全重试；派发后未知或部分迁移必须隔离。**完成条件：**真实RED/GREEN和状态回归通过，不以retryable=true代替放行证据。

### M2：后台一次请求推进到测试服部署完成
复用现有状态机，新增持久执行目标和阶段意图。先保存唯一操作身份再派发；API与scheduler并发推进利用stateVersion/CAS/lease防重。READY后自动调用受控测试部署；关闭页面不影响任务。重启后根据真实操作证据续接，无法确认是否已写入时阻断，不盲目重放。

源准备也由受控步骤完成，客户端只选择批准版本。**完成条件：**点击一次可完成测试部署，重复请求/重启不重复构建、迁移或串包。

### M3：前端两入口与验收对话框
把构建/测试部署合为“发布到测试服”；把测试验收放到“晋级正式服”弹窗，随后复用正式预览与确认。显示当前阶段、失败原因和服务端允许的下一动作。移除顶层入口不下线内部能力。

**完成条件：**两个主入口准确表达权限、运行、失败、待验收、成功；验收证据不全不能晋级。M2接口合同冻结后，M3可并行开发。

### M4：故障回归与独立复检
验证双击、双窗口/双推进者、浏览器关闭、控制台重启、派发临界中断、锁占用/失权、包摘要变化、测试证据失效、授权过期、迁移失败。必须检查真实命令和副作用，源码字符串检查只能补充。

涉及重构按项目Subagent-Driven Development规则执行；独立reviewer/tester审查逻辑、易用性和UI。实现提交后提供精确应用/维护提交及证据，按既定门禁取得新GO。**完成条件：**相关测试与独立复检通过；不能沿用旧精确GO。

### M5：真实两按钮闭环及收尾
从新批准提交准备本轮专用干净发布输入和新tag。固定Playwright真实登录，点击“发布到测试服”，无需第二个部署动作；核对测试服页面版本/变更说明并完成真实验收。

再点击“晋级正式服”，在弹窗完成验收和正式确认，对同一包上线。最终同时核operation=SUCCESS、manifest、远端IMAGE_TAG、backend/frontend实际镜像tag、health=UP、HTTP200及业务页面结果。接口只作最终只读核验，禁止脚本/API直接发起冒充按钮。

合并后验证与任务资源收尾通过后才能completed；按用户目标仅测试服/正式服，不扩大到备份服。**完成条件：**操作者无需终端补命令即可得到真实一致的结果。

## 顺序与并行限制
M0→M1→M2为主链，M3在接口合同确定后并行；M4在完整实现上验证，M5必须在新GO之后。不要并行编译同一Maven target、复用同一测试数据库或争用同一环境写租约。

## Downstream：实施配套
实施阶段按范围使用backend-api-delivery、frontend-feature-delivery、ci-cd-environment-delivery；独立验证使用independent-verification-gate，真实前端使用playwright，收尾使用task-closeout-cleanup。本任务的BDD/TDD/E2E和数据计划在 `docs/acceptance/`。

## Blockers：实施前置
- 原发布锁的真实归属和写入边界须核实；本计划不解锁。
- M0形成实现基线，M4形成新提交GO。当前旧批准分支和主线有差异，不能略过。
- 需要隔离MySQL、规定的Playwright1.60.0/浏览器、已授权账号、NAS容量、镜像工具和真实目标配置；缺失即阻断对应阶段，不换数据源或假成功。
- R22的supersession、allowedPublishScopes、旧迁移不可变和真实target-preflight门禁持续有效。
- 一般使用测试租户；例外身份必须有明确授权并记录范围，不在文档保存口令。页面mount的隐式远端GET也受环境授权控制。

## 首个具体交付
先完成M0+M1：基线对齐、锁SQL真实RED/GREEN、失败状态与脱敏记录纠正。通过后再实现READY自动推进和两个入口。
