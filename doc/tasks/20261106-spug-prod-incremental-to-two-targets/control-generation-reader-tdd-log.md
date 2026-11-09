# 控制代次读取与分层 custody

## Current Status

ready_for_closeout。本阶段实现与本机定向验证完成，等待父代理统一集成/独立提交；当前没有本组件创建的 worktree、远端进程或待清理测试服务。事前设计为 `control-generation-upgrade-refactor-design.md`，父代理已审阅并限定本阶段：新 generation 读取/选择模块、新测试、本日志，以及 `installation_history_custody.py` 的严格分层校验；不改 activation/publication/selection/observe，不生成实际 generation，不执行远端、Docker、构建或提交。

## 目标与里程碑

1. BDD/真实 RED：真实临时 JSON/pins 验证四 core/rich、typed 前代、显式未发布、环路/漂移拒绝；实际 899 原件只读集成审计，保留两个 r2 失败续办校验。
2. GREEN：正式 load/inspect/select 与分层 receipt 校验；旧 custody 默认合同不变。
3. REGRESSION：相关既有 custody、activation/selection/publication 本机合同；如需 Linux 特有物理验证由父统一派发，不把 Windows 或协议读取当真实服务器验收。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；schema/前代/完整 pins 必须明确，缺失立即失败。
- 是否从根因和长期维护角度解决：是；独立阶段凭据及分层历史，保持完整产品发布证明边界。
- 是否存在临时补丁或绕过：否；不改旧原件，不伪造 Spug 成功，不修改旧固定 r4 合同。

## 经验门禁

- Trigger：四控制已激活、产品发布尚未完成的下一代升级。
- Preflight check：四 core/rich/r4 原件、原 automatic 与 inventory/custody、来源 I2 基线及新 schema 完整绑定；原件只读，凭据只在 PRIVATE 读取且不输出。
- Blocker：任一前代、文件字节、闭包、失败续办、receipt 连续性或阶段事实冲突。
- Verification：真实临时文件与实际只读原件分别记录；严格 RED/GREEN、旧合同回归、退出码/零 skip/输入 SHA。
- Forbidden action：控制成功冒称 Spug 发布、改原 r4/失败/历史、按最新文件猜前代、远端动作或构建提交。
- Evidence：上位升级计划/事前设计；`docs/experience-index.md` 指向的包清单、自动增量及多机器接管前置门禁。

## BDD

- BDD: control-only generation -> Given 四份 pin 绑定的同代 core/rich 与未发布状态，When load/select，Then 得到真实控制器身份及原 receipt，不能返回完整安装选择。
- BDD: immutable predecessor -> Given typed automatic 或 control-generation 前代，When 任一原件/角色/提交/plan/build/失败续办变化或环路出现，Then 明确拒绝且不写任何文件。
- BDD: layered receipt -> Given 原旧 custody 与 MAIN 实际归档层，When 验证，Then 旧 active 仅按同字节映射到首 MAIN archive，逐层只准四个 receipt 字段变化，保留所有原 owner/control/dropin/包及 inventory；缺失、重排或任意附加路径映射拒绝。
- BDD: actual audit -> Given 四份实际 899 成功及 r2 原失败链，When inspect 内存索引，Then 只读全部既有原件、返回 generationPin=None，不生成实际控制代次或发布原件。

## 执行证据

RED: 本机两个新测试文件 -> exit1，43 FAIL / 0 skip，52.45s；27 项缺新 generation 模块、14 项缺 layered API、2 项缺旧 verifier 的显式读取 seam。日志 `control-generation-reader-red-r1.log` 保持。

最小实现后先独立核实际 899 原件与 16 项 custody：首轮 1 FAIL/16 PASS，原因是最终物理输入清单将同一 Windows 原件的正反斜线拼写误判漂移；物理清单统一宿主 Path 拼写后实际 17 PASS / 0 skip（2.85s），原 JSON 内 pin 不改写。该检查包含两个实际 r2 的原失败续办闭包。

RED 后精确补齐局部协议 fixture 的 `packageJsonPin` 和旧 `previousCustodyObservation`（实际 rich 均存在）；它们是新 recipe 必需输入，不以产品 fallback 容纳缺字段，原断言不改。测试的本地文件协议证明校验器行为，不能证明服务器安装或业务恢复成功。

GREEN: 同两文件 -> exit0，43 PASS / 0 skip，18.04s，`control-generation-reader-green-r1.log`。

后继最小 BDD：Given 已核前代和显式 v2 新修订、generic build 及独立 coverage，When load 新控制代次，Then 读取带 revision 的四 core，追加真实轮转层，原 automatic/r4 不改；缺/错前代、分组图或分层原件拒绝。此子项 metadata 单元明确隔离 coverage 接口，不替换四 core/rich/receipt/配置读取；实际 coverage 验证由 activation owner 唯一实现，父已有真实双包报告，另按正式 API 集成。

RED: 后继 6 项 -> exit1，6 FAIL / 27 deselected / 0 skip，5.88s，日志 `control-generation-reader-successor-red-r1.log`。成功用例实际进入旧 `_build` 后因 generic build 无 packages 拒绝；五项内层拒绝也被该旧入口提前挡住，错误码不符合后继合同，因此均真实失败，不把它们算作已验证内层安全行为。

接口核对发现 `packageDeltaPin` 与独立 `coveragePin` 是不同原件。父确认保持 generation/v1 字段集合：后继每 rich 明确含 activationInputsPin/coveragePin/previousControlGenerationPin/revisionId，读取正式 v4 输入，四份核共同 coverage/前代/revision。唯一 coverage verifier 每代一次；后继纯 planner 以受核包字节重建 plan 全等。metadata 单元仅隔离该材料边界，不能当实际安装。旧 899 generation 与 rich 入口不改。

接口 BDD: Given 正式 planner 消费 selection.controllers，When 读取任一 host，Then 每项从实际 core 保留 role。更新后真实 RED r2 为 9 FAIL/24 deselected/0 skip（16.66s）：3 项缺 role，6 项旧 generic build 入口；不在载体中手补 role。

后继首 GREEN 尝试实际 1 FAIL/48 PASS（39.68s）：递归复用 Records 使前代 inputPins 混入已读取的后代索引，改变前代 selections.localInstallationPins，精确 currentSelections 因而拒绝。改为各前代独立 Records，完整前代 pins 显式合并外层；不放宽全等断言。随后实际 49 PASS/0 skip，exit0，22.77s，日志 `control-generation-reader-successor-green-r2.log`。

BDD: completed layered custody -> Given v4 同时保留激活前 previousCustodyObservation 与完成后的 currentLayeredCustodyObservation，When 缺完成观察、计数仍旧代或选定 receipt 不对应本代，Then 后继 loader 明确拒绝；初始 899 不新增该字段要求。

RED: completed custody 3 项 -> exit1，3 FAIL/33 deselected/0 skip，3.78s，均为 DID NOT RAISE，日志 `control-generation-reader-custody-red-r1.log`。随后最小增加双观察明确校验，不静默降为旧代证明。

GREEN: 两个完整新测试文件 -> exit0，52 PASS/0 skip，21.83s，日志 `control-generation-reader-final-green-r1.log`。其中 generation 36 项（含实际 899 原件只读审计），layered/legacy custody 16 项（含旧入口仍接受原 current、拒绝变更 current 两个回归）。全程真实临时 JSON/文件/pins；路径读取 seam 不返回伪造的成功观察。

## 冻结 API 与验证边界

- `load_control_generation(task, private, generation_pin)` 返回独立完整 bundle；`inspect_control_generation(value, task, private)` 只核内存提案且 generationPin=None；`select_control_generation(suffix, task, private, *, generation_pin)` 返回对应 selection。
- bundle 字段固定为 generationPin/generation/build/plan/privatePlan/controllersByHost/selections/inputPins/targets/sourceBaseline/custodyByHost。selection 明确 currentControlGenerationPin 和 baseAutomaticSelectionPin，不产生 currentInstallationSelectionPin。
- `SELECTION_CONTROLLER_KEYS=('role', *contract.CONTROLLER_KEYS, 'dropinPin')`；四角色从实际 core 提取，供正式 consumer 与协议载体共享，不能在载体补字段冒充接口。
- 后继明确读取四份 v4 inputs 及其阶段/单位/环境原报告、共同独立 coverage、精确前代/修订/顺序。唯一 `activation.validate_generation_coverage` 每代一次；同一材料交给纯 `validate_control_upgrade_plan` 重建全等。35 文档按 8 新/27 原件分组互斥闭合，保留行按前代逐行全等。
- `verify_layered_receipt_custody` 与旧 verifier 共用可嵌入 SCRIPT；旧逻辑 active 仅能按同 bytes/SHA 映射到首 MAIN 的固定归档路径。后继逐层实际读取原 receipt、配置、dropin、package.json、历史清单。`packageManifestsVerified` 只证明清单原件及其内部 hash，实际包成员仍由 activation 的正式 verify_package 负责，不把清单 pin 冒称包内容验证。
- 当前 52 项为 Windows 本机验证；临时文件通过显式路径 reader seam，不冒称 Linux 默认 O_NOFOLLOW/flock 或真实服务器安装。实际四份 899/r4/r2 只读审计独立于 metadata 协议 fixture。后继材料 seam 隔离唯一 coverage 与纯 planner 校验边界，不能证明新的控制激活成功；父及对应 owner 的真实双包/coverage/纯 planner 证据另行记录，不合并成“全部测试重跑”。
- 未生成实际 generation、后继配置或安装原件，未接触服务器/Docker，未构建或提交。原 r4、899、失败续办及凭据原件保持。
