# MAIN 目标保全 3A：最小实施划分与首批 RED

## Current Status

design_ready_for_review。父已认可阶段 3 总方向，但本轮只交付划分与 BDD／RED 清单。阶段 2b 仍在父批准的有限最终 GREEN，尚未 freeze；在父明确确认冻结前，不写产品／测试、不运行测试／Docker、不构建、不访问远端或安装。

本文独立于已冻结的 `main-target-preservation-phase3-design.md`，不修改其原 SHA 或阶段 1／2a／2b 的证明。3A 实现完成可单独提交，但源码合同通过、实际新双包验证和现场安装是不同里程碑，不能相互代替。

## 目标、里程碑与验证

- 3A1：长期静态 policy／template 能为不同 operation 正式派生独占读回配置，并被 live／历史消费者精确验证。
- 3A2：两个实际包都可达严格 MAIN 捕获及保全入口，普通 SAFE／LIGHT 来源合同保持；独立有限 profile 核新成员和真实同提交验证证据。
- 不含 3B 的三服配置生成、3C 的安装／新 current 选择、Spug 发布或业务恢复；不引入 generation adoption。
- 验证顺序：2b freeze → 有限 RED → 最小实现 → 受影响 GREEN／REGRESSION → 父限定实现提交 → 本次专用干净 release worktree 的同提交实际双包验证。最后一步的产物前提尚未具备，不提前记 PASS。

## 设计约束检查

- 是否引入 fallback／降级／吞异常：否。未知模板、目录／pin 漂移、缺严格语义或缺实际包证据均阻断。
- 是否从根因和长期维护角度解决：是。操作目录从已绑定 ctx 派生；MAIN 严格语义和普通来源生命周期分开，旧证据继续走原精确合同。
- 是否存在临时补丁或绕过：否。不安装单次操作 policy、不临时改配置字典、不改旧 147／146 常量，不以源码 PASS 代替实际包验证。

## 经验门禁

索引依据 `docs/experience-index.md`，适用 `docs/release-agent-checklist.md` 中实际封包构造配置传递、覆盖前保留备份完整读回、授权控制升级的活动回执历史保全三项。

- Trigger：模板新增或 SAFE reviewed transform／成员变化。Preflight check：2b 最终源码及测试 pins 冻结，确认完整调用和配置传播边界；实际包来自已提交干净输入。Blocker：无 freeze、构造丢字段、未知模块或不完整读回。Verification：真实 ctx／锁／文件、两实际包的新进程及完整原始测试终态。Forbidden action：手填 native 属性、mock 成功、skip、扩大旧白名单。Evidence：本计划与后续独占 RED／GREEN／REGRESSION 原件。
- Trigger：准备进入现场配置或安装。Preflight check：完整新 profile／实际包和三服新鲜捕获身份／资源／写根准入。Blocker：任一未证。Verification：由父另行组织。Forbidden action：把本轮只读 epoch 事实或 3A 测试当作安装／恢复验收。Evidence：阶段 3 总设计及下节 r4 原件。

## 已核新鲜事实：当前无需 generation adoption

父报告 `main-target-generation-readonly-reconciliation-20261110-r4.json` 已在本机按原 bytes／SHA 读核：11,055 B，SHA256 `d53eda63132a01877e320b48918879ac9b8976aa751afd3c3b40d377d3b9954a`。三服原 control／owner、实际 PID／argv、147 引擎及原 generation／epoch reader 的观察证明均由父采集；本轮没有再次远端读取。

| 主机 | current 与 initial READY | 成功程序代次／currentGenerationPin | capture 映射 |
| --- | --- | --- | --- |
| .57 | 同一原 sequence 0，原初始事件未变 | 0／null | 仅 `intruoyi-57-safe-20261024-v1` |
| .58 | 同一原 sequence 0，原初始事件未变 | 0／null | 空 |
| .59 | 同一原 sequence 0，原初始事件未变 | 0／null | 空 |

据此排除当前 generation adoption 的实施需求。后续登记仍须在实际准入时复核原件及 current 未变，不能把今天的观察永久当作不变事实；不增加 adoption API、迁移事件或回写旧 policy／initialEpoch／generation。

r1／r2 载体失败原件保留。r3 的真实远端 exit0、完整 stdout 与 Windows SSH `pending-socket-close` stderr 同时保留；r4 是父本机对这些原件的说明，`networkCalls=0`、`originalCarrierResultsRewritten=false`，状态为 OBSERVED，不是消除 stderr 后伪造的安装 PASS。三服捕获身份、容量、保全可写根、SMB 权限等仍未因此验收。

## 3A1：静态模板的每操作派生

### 独立提交边界

最小产品范围优先仅 `ops/recovery/recovery_target_preservation.py`：在 2b 冻结后的 `TargetPreservation.prepare`、持续检查和 `validate_preservation_evidence` 内加入明确版本分派及具名派生／验证函数。不新增通用配置引擎，不修改 `recovery_program_generation.py`、epoch、Native lock、普通 `SmbReadback` 或已冻结安装 reader。若确需改变外层 evidence 传播，只可沿 2b 已有 `targetPreservationPin` 固定链，先证明现有链缺哪个字段，再由父审查该精确接缝。

新增专属 `scripts/tests/test_recovery_target_preservation_template.py` 与 3A1 TDD 日志。阶段 2b 原测试及旧 v1 正反合同保持；不得通过改其期望来获得 GREEN。3A1 可以在不改 package mapping／build 的情况下独立完成源码合同提交。

版本、字段和固定路径采用已审阶段 3 第 3 节：`MainTargetPreservationPolicy/v2` → `MainTargetPreservationRepository/v2` → `MainTargetPreservationReadbackTemplate/v1`，唯一 `recordRootPolicy=CURRENT_OPERATION_TARGET_PRESERVATION_PUBLICATION`。原 v1 policy／repository 路径逐项保留。实际派生结果仍是严格 `RepositorySmbReadbackConfig/v1`；只把模板字段逐值投影并生成固定 ctx 操作根，不接受模板表达式或宿主命令。

同 ctx 原锁／预约／不可变 request/binding 验证后，且首 quiesce／capture fence 前，独占写 `publication/readback-configuration.json` 和 `publication/readback-derivation.json`。二者固定模式 0600、O_EXCL／NOFOLLOW、目录 FD 身份及 fsync；从 ctx._root 取操作根。新 intent 版本显式绑定 derivation pin，后续 proof/final 通过该固定原件闭合；仅实际增加字段／改变解释的记录升级版本，不给每个无变化 sidecar 复制一套 schema。旧 exact v1 不增加可选字段，不接受未知版本。

正式 `PreservationReadback` 仍核原 auth/library pins，并建立真实协议连接；派生记录不能代替连接成功。history 独立读取旧 policy/template/derived config/intent 原件并重建全等，不读当前 owner 来替换历史，也不授予 live clear 能力。

### 首批有限 BDD／RED

| 场景 | Given／When／Then 与真实验证边界 |
| --- | --- |
| A1 单模板两操作 | Given 一个真实私有静态 v2 policy/template 和两套真实 ctx／flock／预约；When A、B 分别运行正式 prepare；Then各自固定配置／derivation原件被写，连接声明相同、recordRoot不同、模板 bytes不变，且均尚未派发 quiesce。第一轮只到 prepare，不为证明派生重复导出大 FULL。 |
| A2 同 operation 重入 | Given A 的实际派生文件已经存在；When再次进入同 ID／目录；Then在 O_EXCL 边界失败，原字节／inode／mode不变，不覆盖也不自动恢复执行。 |
| A3 路径与模板拒绝 | Given未知 tag、显式 recordRoot、命令／额外字段、路径别名或目录symlink；When解析／派生；Then明确拒绝，既不创建任意路径，也无首停写。有限参数集，不枚举无关输入。 |
| A4 原身份与引用漂移 | Given实际原件；When改模板 pin、跨 operation／target／binding复用derivation、篡改 credential/library引用或 repositoryRoot；Then live与独立history均拒绝，不重新测SHA后接受新值。 |
| A5 历史完整闭合 | Given真实一次 2b producer原件加正式新派生链；When成功后独立验证，随后逐次缺固定derivation／改configurationPin／改root；Then原完整链可读，三个缺口分别拒绝，`clearAuthorized=false`。复用同一实际归档，只复制有限私密协议原件做负例，不手造成功backup。 |
| A6 旧合同保持 | Given原 v1真实prepare／historyfixture；When新分派代码运行；Then原 v1字段、读取、拒绝原因保持；v2失败不得掉回v1。 |

首个 RED 集合先做 A1、A2、A3 与 A6；A4、A5在同一最小实现前补齐明确失败事实，避免以只解析 schema 的 GREEN冒充历史闭环。复用真实 ctx/锁/私有文件及原有限SMB协议fixture，不能 mock ctx／resolve／protection成功。Linux锁用例必须实际Linux执行且零skip；父安排执行空档，不在2b或Spug独占测试期间另起载体。

GREEN 后只跑新文件与原 2b handoff/runtime/producer/history/retention受影响组、原v1 preservation和源FULL三生命周期。除非新失败显示相关，不重跑无变化SQL导入和整仓测试。

## 3A2：真实两包严格 MAIN 入口与独立包证据

### 两个连续、可审查的提交单元

**3A2a 材料接线**：`files.json`、`standard_fixes.py` 及经事前确认的具名严格材料适配边界；优先在现有 `recovery_capture_materials.py` 内形成唯一严格MAIN适配实现。普通SAFE worker生命周期与完整检查保持，LIGHT普通来源不被整体提升或替换。三个新增common成员显式列举；当前不能先硬编码“新包150／149”作为准入。任何第四成员必须先证明必要并重新冻结有限成员集合。

具体接线仅覆盖：SAFE worker共享材料调用、其parent lease/restore收尾；MAIN的StrictSemantic、SQL/query/schema/data/image/endpoint/Redis observer；SAFE `publish_materials`／严格readback共享；2b `target_preservation` typed参数经过实际 runtime构造到stage/clear；结果/history/retention消费者使用2b最终冻结模块。普通LIGHT源码worker不能因为名字相同而被当作SAFE，`complete=False`不能成为MAIN保全成功。

**3A2b 独立证据合同**：新增 TASK `main_target_preservation_package_evidence.py`、固定 runner、专属测试／日志。只接受已审 `main-target-preservation/v1` profile、新delta和coverage v3；完整原tar/tgz逐成员、源码／变换关联、实际模块加载路径／字节、完整collection与原命令终态。旧三模块 chain-policy profile及旧147／146 reader不改。此提交可先以真实临时tar和子进程原件验证正反协议，但不能据此发布“新产品包验证PASS”。同提交实际产品证明必须待父提交3A源码后在新干净release worktree产生。

### 第一轮材料 RED（有限五项）

1. **成员缺失**：给定已冻结 b5 实际两包，按只读原tar读成员；三新common入口必须缺失并明确失败。原包不重构、不改写；测试失败只证明当前交付缺口。
2. **真正调用入口**：给定实际SAFE候选和原完整普通FULLfixture，正式worker须调用共享材料核心且恢复源并保留parent lease；目前仅源码接线不能通过该项。
3. **LIGHT MAIN严格性**：给定LIGHT实际加载模块与真实MAIN构造／transport边界，`process_observer`必须可达且完整references/bucket/multipart检查有效；不能只修TypeError而保留`complete=False`。
4. **SAFE源方法保持**：给定认证冻结方法与具名transform，核五项既有严格义务、readback内容／前后身份和source restoration；未认证输入段或遗漏方法立即失败。
5. **typed传播**：给定新owner及阶段2b真实ctx/能力，通过实际包entry→runtime到首次clear前；同一preservation能力必达，错目标／缺字段拒绝；不得手填构造对象属性。

旧 b5 包的失败证据与待构建新包的 GREEN 分开记录；新tests在当前源码中运行不等于其已经进发布输入。材料接线完成后先源码／候选单元回归，再由父提交和构建实际双包；最终两包在独立进程做同一必要完整链，不能以两个不同mock成功拼成producer→consumer证明。

### 独立证据 RED（有限四组）

- 成员集合：少一个新模块、多未知成员、重复/链接/外逃tar member、跨variant；完整manifest闭包拒绝。
- 同提交来源：源／transform／测试／runner／原冻结tar或实际tgz任一跨commit／原件不符；不能仅信build自报SHA。
- 测试终态：缺批准必要suite、collection不全、非零exit、任一fail/error/skip、原stdout/exitReceipt改动；全部拒绝。
- 历史边界：新包不能通过旧147／146或三模块profile；旧真实证据仍由旧reader保持原结果。新profile只从显式 predecessor build/generation取原件，不扫描“最新”。

最终实际包验证四组固定职责：严格材料与普通生命周期、出版读回/handoff、producer→history→retention、配置构造及旧恢复回归。每条完整collection、exit0、tests>0、fail/error/skip0、输入前后不变，STANDARD/LIGHT分别记录__file__与原字节。最终具体node集合在2b freeze和3A2首RED时固定，数量不能替代功能集合，也不预报尚未执行的数量。

## 明确不进入当前阶段的事项

不创建三服policy/capture配置、不改旧目标sources/targets或27保留文件、不运行新代次planner/stager/activation、不改current dispatcher和1630闭包、不更新Spug565、不新增source服务。不为已被真实事实排除的generation adoption增加模块或schema。三服实际捕获权限、资源和可写目的仍由父后续准入；不足时阻断对应登记。

本轮仅新增本文；r4按原SHA读取通过。产品RED开始条件仍是父明确确认2b freeze和分配3A1文件所有权，随后按以上有限集合一次次保存真实终态，不抢占父当前Docker／Spug执行。
