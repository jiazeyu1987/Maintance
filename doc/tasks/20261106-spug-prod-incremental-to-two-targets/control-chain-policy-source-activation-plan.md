# 链策略升级的来源激活准入设计

## Current Status

`DESIGN_REVIEW_REQUIRED`。本阶段只读审查和设计，不修改已冻结待提交的八个文件，不运行测试、构建、服务器命令或激活。父任务已记录新证据合同 103 项与旧合同 172 项实际通过；这些通过不能替代本设计后续的 RED/GREEN，也不能证明新源控制已经激活。

## 目标与范围

新程序对原 FULL → I1 → I2 链正确实施原 owner 的 24 小时上限后，会返回 `BASELINE_REQUIRED / INCREMENTAL_CHAIN_AGE_EXPIRED`。安装器必须证明原链及物理来源保持不变，同时接受这项经过审验的程序行为变化。不得把它当作备份链丢失，也不得为通过安装修改原链、延长上限或重新备份。

范围仅为已完整验证 `MainProgramControlCoverage/v2` 且 `profile=incremental-chain-policy-admission/v1` 的 `MainProgramControlActivationInputs/v4`、57、source。旧 v1/v2/v3、旧 coverage/v1，以及三个 target 控制的激活规则保持。继续使用现有 v4 inputs、activation/v1 core 和实际 rich 原件；不引入 v5 或新的通用状态转换框架。

## 经验门禁

- Trigger：同一来源的链策略升级使安装前后的增量计划状态合法变化。
- Preflight check：完整验证同提交双包及 coverage、原 I2 审计、真实旧/新程序配置 pins、原物理锁、来源/目标 epoch 配对、来源空闲和原业务/历史保护；根时间只能来自原 FULL point 绑定的 manifest。
- Blocker：原链、epoch、配置、锁、进程或历史变化；候选返回 BLOCKED、其它需要全量原因、未知计划结构；新旧来源不是同一物理身份；候选与实际切换后结果不一致。
- Verification：真实临时元数据、共享策略函数、候选包入口和本机协议边界的 RED → GREEN；原激活和分层 custody 回归。实际远端验证由父单独执行并保留原始 rich/进程/HTTP 结果。
- Forbidden action：不把所有 BASELINE_REQUIRED 当成功；不改 owner 限制；不从 finishedAt、文件名或当前日期推导根时间；不追填 epoch；不把新候选结果伪装成旧控制 READY；不派发备份/恢复或抹去失败原件。
- Evidence：`docs/release-agent-checklist.md` 的“自动增量链与恢复周期门禁”；本任务原 `automatic-i2-audit.json`、已审 `control-upgrade-chain-policy-evidence-design.md`，以及后续专属 TDD 原件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。只有被完整证明的精确状态变化可通过；其它失败保留并阻断。
- 是否从根因和长期维护角度解决：是。区分历史链完整性与当前增量准入结论，直接复用候选程序的正式共享策略和实际计划。
- 是否存在临时补丁或绕过：否。不改策略值、不强制 READY、不伪造引用、不创建替代基线。

## 只读根因与已有证据

1. `main_program_control_activation.py::REMOTE_SCRIPT.source_plan` 目前同时用于切换前和切换后，固定要求 READY 及原 `sourceExpected` 三引用。切换后调用约在第 1377 行，新程序合法返回过期就被误判 `SOURCE_BASELINE_CHANGED`。
2. `recovery_control_incremental_plan.build_plan` 已验证唯一完整根/叶和 epoch 后，调用同包 `repository_records.incremental_chain_admission`。过期响应保留标准 `AutomaticIncrementalPlan/v1`，但 parent/base/generation、类型和时间为空，chainDepth 为 0。不能用这些空字段证明原 I2 丢失，也不能只信这个 reason 字符串。
3. 原 `automatic-i2-audit.json` 已绑定 FULL、I1、I2 的不可变 point 和 epoch pins，原 sourceExpected 保持。审计顶层 manifestPin 是 I2 的 manifest，不能把它误用成 FULL 根时间；必须经 `chain[0].pointPin` 读取根 point 内的 manifestPin，再验证其 createdAt。
4. 现有 CANDIDATE_GATE 已在候选包内核真实 Native、owner/capture 的 generation 解析、物理来源身份和 READY epoch，但还没有运行候选 incremental_plan。现有 first/final 全等、原147成员逐项校验、实际服务 argv/env/PID、物理 flock、业务/mount/history 保全均可继续复用。
5. 当前 stager 虽分别运行旧/新 CANDIDATE_GATE，其 source HTTP 始终查询仍运行的旧控制；本轮升级前应继续是旧 READY+I2。它不需要因为本次切换后的状态变化放宽门禁。publication 没有另一处 source READY 判断；其历史 rich 验证目前只核 sourceCaptureVerified/sourceBaselineVerified 布尔值，见下方历史消费边界。

## 最小接缝（待父审后实现）

### A. prepare 只从已验证 coverage 派生有限输入

在现有 v4 `validate_generation_coverage` 返回后，且 suffix=57、role=source 时，只有上述 schema/profile 精确匹配才给内部 SPEC 增加 `sourcePolicyTransition`。该内部值不由 inputs 自报，不改变输入 schema。

内容限于已存在的 `coveragePin`、profile、`sourceBaselinePin`、原 sourceExpected、原审计 chain 中三个 point/epoch pins。根 manifestPin 在远端由原 root point 取出并核 pin；不能在本机填一个猜测根时间。该数据沿现有 source 工具调用显式传给 CANDIDATE_GATE，未提供时维持原行为。

### B. 切换前在原物理锁内证明两种真实结论

原锁前 SOURCE_IDLE、旧 HTTP READY+I2、capture/epoch 配对及原件校验全部保留。获得原 physical flock 后、写 dropin 前，增加一次旧 HTTP READY+原三引用复核，并记录为实际 `sourcePlanBeforeLocked`。这样空引用的新计划不能掩盖锁获取前刚出现的新 FULL/叶点。

候选 gate 在同一锁保护区内：

1. 核原三个 point 的身份、类型、generation、父前缀和 epoch 绑定，与已验证原审计完全一致；原 I2 全链验证仍由旧 READY 和新 Native planner 完成，不另造缩减的链验收器。
2. 经原根 point 的 manifestPin 读取根 createdAt。调用候选包实际 `incremental_chain_policy(owner)`，并核新旧 owner 的两个限制完全相同；不内置 86400 或默认上限。
3. 使用候选包实际 `incremental_chain_admission(policy, root_created_at, 3)` 取得当前结论，再实际调用候选 `native.incremental_plan(source_ref)`。模块实际 __file__ 必须位于已逐文件验证的候选 engine，代码与新 coverage/包 pins 相同。
4. 允许的组合只有：共享策略返回 None 且候选 READY、引用精确为原 I2；或者共享策略精确返回 `INCREMENTAL_CHAIN_AGE_EXPIRED` 且候选为同 reason 的 BASELINE_REQUIRED。此次不扩展到点数上限或其它新 FULL 原因；它们仍阻断。
5. 对过期计划核完整原 schema/source、公有字段集合、所有 nullable 引用/类型/时间为 None、chainDepth=0，以及规范 JSON 计算的 planDigest/evidenceDigest 结构。对 READY 仍核完整原三引用和既有合同。

结果复用 `candidateBefore` 的有限嵌套字段，包含原链 pins、根 manifestPin/createdAt、实际原 owner policy、精确候选 plan 与来源 epoch。证据不加入易变当前时间或日志末尾，从而保留 first/final 全等；策略每次仍用真实当前时钟重新计算。若恰在激活中跨过期限，前后结果不同即失败，不能静默替换预期。

候选门禁继续使用现有总预算和 Native plan 预算。缺配、超时或异常都阻止写 dropin，不扩大超时，不执行备份。

### C. 切换后的真实 HTTP 与候选计划逐值相等

`source_plan` 保留默认旧 READY 分支。仅在已准入的 sourcePolicyTransition 下，切换后显式传入刚取得的候选计划，校验实际新 PID/argv/env 对应的认证 HTTP 全响应与它相等。仍记录真实 `sourcePlanAfter`，不回填原 I2 引用。

随后现有 final=package_gate、final==first、preserve、完整包复核继续执行。旧 `sourcePlanBefore`、新增锁内 `sourcePlanBeforeLocked` 是真实旧控制响应；`candidateBefore/After` 和 `sourcePlanAfter` 是真实新程序响应，不能互相替代。

`sourceBaselineVerified` 表示原完整历史链与物理来源保持，不意味着该历史链今天仍可继续增量。该标记仅在上述完整检查完成后置 true。

### D. core 投影与历史读取不只信布尔值

`project_core` 对这项已验证新 profile，必须复核原锁内 READY+原 I2、candidateBefore==candidateAfter、候选 policy/原件关联、sourcePlanAfter 与候选 plan 全等；缺任一原始字段拒绝投影。其它 profile 保持原逻辑。

历史 generation 在其既有唯一 coverage 完整验证后，对新 profile 的 source rich 调用同一有限纯验证函数，传入已经验证的 inputs、原 sourceBaseline 和 privatePlan 中原/新 owner 值。历史检查只能验证原结果及冻结证据，不能用当前时钟重新推翻历史过期结论，不能查询 live latest。时间准入事实由当次已核候选实际结果与原 root/policy 绑定；不能把它降为任意 reason 自报。

这最多需要 `main_program_control_generation.py` 在新 profile 下加一个显式调用接缝，由其唯一 owner 或父协调；旧 rich 不要求新字段。暂不改 publication 通用 schema 或各 target 规则，不复制第二份状态转换逻辑。

## BDD 与 RED/GREEN 计划

- Given 原完整 FULL/I1/I2、同 epoch、原 owner 限制、过期根；When 运行实际候选共享策略/Native plan，再比较切换后实际协议响应；Then 接受精确 AGE_EXPIRED+空引用，并证明原三点、业务和保护保持。先用冻结安装函数取得真实 `SOURCE_BASELINE_CHANGED` RED，不能仅断言缺少新函数。
- Given 原合法未过期链；When 相同准入；Then 仍只接受 READY+原 I2，不把 profile 本身当作允许过期的事实。
- Given 旧 schema/profile 或错误 source/host/role；When 提供 BASELINE_REQUIRED；Then 保持原拒绝，不可通过传入内部字段开启例外。
- Given 根 manifest/point/epoch/owner limits 或旧锁内三引用变化；When 准入；Then 在写 dropin 前失败。根时间替换成 I2 finishedAt、错误 manifest 或未来时间均拒绝。
- Given BLOCKED、无基线、epoch失配、日志 purge、点数上限、其它 reason，或过期理由却共享策略未过期；Then 全部拒绝。非法 null/chainDepth/digest 也拒绝。
- Given 候选正确但新 HTTP、final gate、程序 pin、原锁身份或 history 后置证明变化；Then 不产生 PASS/core。缺锁内旧 READY 或只保留 sourceBaselineVerified=true 也拒绝。
- Given 真实原 rich 固定记录；When 历史读取；Then 只在已验证新 profile 接受原有限证据，缺嵌套原件关联或四项计划不一致拒绝；旧 v1-v3/v4旧coverage 原正反例逐项保持。

测试使用真实临时私有文件/pins、正式共享策略与候选模块，本机子进程和有限 HTTP 协议边界；它们不冒称实际服务器激活。使用真实 epoch/链 fixture，不把 Native/来源/策略成功 mock 掉。Linux 实际 flock 验证交父统一执行，本子阶段不访问远端或 Docker。

## 里程碑与预期验证

1. 只读根因与本设计：完成，父审限定范围通过。
2. 限定正式测试 RED：完成，原始失败与逐步 GREEN 见 source-policy-activation-tdd-log.md。
3. 最小 activation 接缝及历史有限消费 GREEN：完成；新增来源策略场景 50 项通过。
4. 父独立必要回归：214 PASS / 0 FAIL / 0 ERROR / 0 SKIP，90.29 秒，输入前后 SHA 相同；原日志与 JUnit 的精确 pin 见 source-policy-activation-parent-20261110-r1.json。子阶段更宽回归的历史 Spug 证据读取出现 2 FAIL / 26 setup ERROR；原旧 attempt 固定的 activation helper 已合法升级、但历史 custody 未收录它，不能把历史原件改写为新代码。该缺口不属于来源策略行为，仍明确阻止依赖这条旧 Spug 读取链的验收；原失败全部保留，未宣称宽回归通过。
5. 同提交干净发布 worktree 的完整双包/coverage、实际候选准备、父授权激活及真实 Spug 验证：父任务后续里程碑；本设计与本机测试均不能标记它们完成。

不得把本设计写入已冻结旧证据或改写原失败；后续命令与终态使用新专属 TDD 原件。当前仍有正式验证和真实产品验收未完成，未宣称总任务完成。
