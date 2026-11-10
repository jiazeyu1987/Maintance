# MAIN 新点只读验收驱动 TDD

## Current Status

completed（仅本子任务的本机实现与合同验证范围）；代码与证据已冻结交父任务。本轮未访问服务器、Docker、浏览器，未提交或清理。根任务原业务 65ed6552 的真实终态及现场只读 UI 验收由父任务继续处理；本轮协议测试不能称作现场成功或原完整目标通过。

## 目标、里程碑与预期验证

按 main-new-point-ui-validation-plan.md 为 verify_goal_readonly.cjs 增加显式 --point-audit / --selection 成对输入；保留原 --observation rN 与无新参数的完整目录和恢复矩阵模式。新增模式核当前 MAIN 147、cycle、sourceCommit/spugCommit、v4 原始字节 pin，保持完整目录/分页/全量增量筛选，整条成功 audit 链必须 indexed，恢复确认仅针对 audit.operationId 一个新点。报告使用独立 schema 与 scope，最终按钮和所有业务写入继续禁止。

里程碑：读取实际合同与 v4 -> BDD 与真实 RED -> 最小实现 -> 新合同 GREEN 与旧合同回归 -> 精确 SHA/限制交父任务。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；以显式成功证据绑定独立验收范围，保留旧的完整目标语义。
- 是否存在临时补丁或绕过：否；不更改业务原件、页面或旧失败，不通过注释 eval 等方式绕过合同。

## 经验门禁

- Trigger：新 MAIN 成功点需要独立的三目标只读 UI 验收。
- Preflight check：只读实际 v4；audit 必须成功、actualExit0、sourceRestored、完整载荷读回；pin/cycle/来源提交和 MAIN 147 严格绑定；只有父任务在真实成功与新鲜门禁后运行 E2E。
- Blocker：缺少成对参数、非成功或 pin/身份不符、未知链或非 indexed；当前真实 audit 未生成；不得用 tmp 协议样例冒充现场。
- Verification：实际 tmp 文件协议样例 RED -> GREEN；旧合同回归；记录原命令/退出码/SHA。只验证准备与核验逻辑，不启动浏览器。
- Forbidden action：无服务器/Docker/浏览器、无业务 POST、无勾选覆盖同意或点击最终执行、无提交/清理、无原件改写。
- Evidence：父计划、本日志、新 test_main_new_point_ui_binding.cjs；现场证据由父任务另行取得。

## BDD（实现前）

1. Given 无新参数，When 解析原调用，Then 保持旧三点 expectedLatest 和全部 eligible 点矩阵合同。
2. Given 成对明确的 PASS/SUCCEEDED MAIN audit 与 v4 原字节，When 准备与核验完整目录，Then 整条 audit 链 indexed，矩阵只含唯一新 operationId，报告 schema=SpugSelectedPointReadonlyAudit/v1、scope=single_verified_point 且保留两份原 pin。
3. Given 参数缺失/路径越界/原 pin、cycle、来源提交、MAIN 数量或终态不符，When 准备，Then 明确失败，不进入浏览器。
4. Given audit 整链任一点不存在或非 indexed，When 完整目录核验，Then 明确失败，不能只核新点。
5. Given 任何模式，When 检查交互能力，Then 全目录刷新/分页/筛选、最终按钮禁用与覆盖未勾选、所有业务 POST abort 始终保留。

## 已识别合同冲突

旧 test_goal_ui_audit_binding.cjs 当前冻结整个 helper 的规范化 AST SHA（6bce041b...），任何新增可执行节点都会改变它；已向父任务报告。未修改旧测试；等待父任务协调如何对新增接缝正式归一化并继续冻结所有旧行为，不以运行时绕过规避。

## 执行记录

计划及适用 AGENTS、经验索引、UTF-8 PowerShell 门禁已按本轮本机范围核对。当前只有计划/日志写入；尚未实现或测试。

RED: 指定 Node `--test TASK/test_main_new_point_ui_binding.cjs` -> 实际 exit1；新模式纯协议 API 尚不存在，断言 `POINT_AUDIT_API_REQUIRED: parseAuditArguments`。原始输出固定于 main-new-point-ui-binding-red-r1.log。测试不导入浏览器，读取 helper 的真实 AST 函数声明后在 fs/path/crypto VM 中运行；临时协议文件与实际 v4 原 pin 两类证据明确区分。生产实现仍未修改。

父任务已明确追加授权：仅调整旧 test_goal_ui_audit_binding.cjs 最后第二项的全 AST 固定方式；其余八项保持。不得简单更换整个新 AST hash，只允许精确投影冻结原 UI 主体/保护块，并对新增模式的明确接缝单独做可执行合同验证。

## 最终实现与授权接缝

新增成对 `--point-audit <TASK JSON 文件名> --selection <TASK v4 JSON 文件名>`，保留原 `--observation rN`。参数、TASK 文件路径、原始字节/UTF-8/SHA/文件身份及全部传递 pin 均在浏览器启动前验证；finally 再复核原始 pin 与首次文件身份。无新参数时仍取全部 indexed FULL/INCREMENTAL 点及原完整矩阵；新模式必须整链全部唯一存在且 indexed，只将 audit.operationId 送入三目标确认矩阵。

新模式要求 AutomaticBackupChainAudit/v1 的 PASS、SUCCEEDED、数字 actualExitCode=0、sourceRestored、payloadContentVerified、唯一 owner、MAIN 147 及完整文件校验；audit 的 cycle/sourceCommit/spugCommit/controlGenerationPin/spugInstallationPin/deploymentSelectionPin 必须与显式 v4 及其实际原件链一致。报告独立使用 SpugSelectedPointReadonlyAudit/v1、scope=single_verified_point，保留 auditPin、deploymentSelectionPin 与整链 ID；不代表旧完整目标 PASS。

父任务批准的旧合同投影严格局限为：原 async UI IIFE 的 eligible initializer 与相邻 RESTORABLE_POINTS_REQUIRED 数量 need 规范化；排除唯一精确调用 `assertSelectedPointState(selectedPoint,state);`，以及 finally 中唯一精确的 `verifyPointAuditInputs(selectedPoint)` try/catch 保护块。其余原 UI 主体、指定原全局声明、原 UI helper、report 原非 schema 属性、独占原件证据保护块保持固定 AST 校验。新增两调用在实际 AST 位置被定位并执行验证可达失败，新增报告字段与完整/单点 eligible 行为另由新合同覆盖。没有宽泛源码替换或移除原保护。

- 原 whole-helper AST SHA256：`6bce041b7a35de9005fad2446033cbe2d5fd91e0422a1198a76fc3cad2fc748c`。
- Git HEAD 原 helper 原始 SHA256：`296470da32938a21fbc98882b889a73e0e335e063833f628e7776ebea7e846cb`。
- 从 Git HEAD 原 helper 计算的固定投影 SHA256：`cad31c5fc87269da16fcb7018238380017aea9e090cea4ebbf307755d5518c3c`；旧测试要求新 helper 同一投影严格相等。
- 旧 expectedLatest 三个 ID、三台目标、全部分页/筛选/刷新、确认摘要、不同意覆盖及最终按钮禁用、业务 POST abort、原完整矩阵计数/失败与证据独占检查均保持。

## RED -> GREEN -> REGRESSION 终态

命令均在当前维护仓工作目录执行；`NODE=C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe`，`TASK=doc/tasks/20261106-spug-prod-incremental-to-two-targets`。Node 仅执行本机合同测试，未运行 verify_goal_readonly.cjs 浏览器入口。

1. RED: `NODE --test TASK/test_main_new_point_ui_binding.cjs` -> exit1，35 FAIL / 0 PASS；实现前缺少 `parseAuditArguments` 等纯协议 API。完整原始失败保留于 main-new-point-ui-binding-red-r1.log。
2. GREEN: 同命令 -> exit0，35 PASS / 0 FAIL；保留 main-new-point-ui-binding-green-r1.log。
3. RED: 增加实际生产 initializer 顺序及新调用可达性合同后，同命令 -> exit1，37 PASS / 1 FAIL，实际 `ReferenceError: Cannot access 'sha' before initialization`。完整原始失败保留于 main-new-point-ui-binding-red-initializers-r2.log。
4. 最小修正：将原 sha 声明移至 preparePointAudit 初始化之前；不改变 SHA 算法或原保护行为。
5. GREEN: 同命令 -> exit0，38 PASS / 0 FAIL / 0 SKIP，duration_ms=2274.6002；原始日志 main-new-point-ui-binding-green-r2.log。
6. REGRESSION: `NODE --test TASK/test_goal_ui_audit_binding.cjs` -> exit0，9 PASS / 0 FAIL / 0 SKIP，duration_ms=129.5092；原始日志 main-new-point-ui-binding-regression-r1.log。
7. `git diff --check -- TASK/verify_goal_readonly.cjs TASK/test_goal_ui_audit_binding.cjs` -> exit0，无输出。后续只更新本日志，无实现变动，因此未重复测试或扩大范围。

新 38 项覆盖：旧/新参数、成对及重复/未知/越界拒绝、明确协议样例的原始 pin、全部成功前提与 22 类身份/终态/链异常、v4/传递资源 pin 原件漂移、请求中原件替换/变更、缺链点/非 indexed/类型或重复 ID、UI 来源严格匹配、实际生产初始化执行顺序、实际 eligible 数量接缝与新调用失败可达性。所有协议样例只在真实 tmp 文件中明确标记 `protocolFixtureOnly:true`；未伪造实际审计或运行态成功。

实际本机只读 v4：main-program-current-installations-45dd7dc-r6-v4.json（664 bytes，SHA256=`0e45e0a0b420e32318d53c99251dbadee8013d7e65b6fc772dae0cc089f84004`），sourceCommit=`45dd7dc65409c87fe856584b85873ea96c0b830e`；传递真实构建 fileCount=147，spugCommit=`5651efc5b9972b20bcacb50d0774e5862cbe8e6b`。此验证没有发明或代替真实终态 audit。

额外只读证据核对：尝试从 Git HEAD 读取旧 test_goal_ui_audit_binding.cjs 以逐项比较时，Git 报该文件尚未在 HEAD 跟踪；这是证据来源不可用，不是业务或测试失败，没有修改文件或声称完成八项逐字 Git 比对。本轮对该旧测试的补丁仅涉及获准的最后第二项，旧 9 项实际回归全部通过；原 helper 的 Git HEAD 固定投影基线已成功读取并计算。

## 冻结文件与 SHA256

| 文件 | SHA256 |
| --- | --- |
| verify_goal_readonly.cjs | dee4cdfe0b45c277aba72ceaedf4036d7b525856d0d68e037c57c322304562fc |
| test_main_new_point_ui_binding.cjs | 9f3187522a183e0505d7248d5f7400fb5567f3d9343a8c19cebe3d835a5348b8 |
| test_goal_ui_audit_binding.cjs | 5378e3e7c0a4964c0f9e6bb1d6e489e7cf2b82914ea0f3d2169f7e441003f036 |
| main-new-point-ui-binding-red-r1.log | d0998508649d9a22953893d74141a5f8760e352cd679b8ff5232774c37e45139 |
| main-new-point-ui-binding-red-initializers-r2.log | d8442b829460a6cd7ed53f5ae5f7b49f9b5ba8e28e1919fd4597ae4267579321 |
| main-new-point-ui-binding-green-r1.log | cd950dd71e298f7ecf574972fc3bfccde2444bbdd4ff34f8e9dc3e657a4d1522 |
| main-new-point-ui-binding-green-r2.log | fde2cbc8ae346e588ccd27c3e79e0aa24fc2af0f175394896e6e76d444b32ffc |
| main-new-point-ui-binding-regression-r1.log | 42b0595203a2e0feb060d75eb5089337fc50356e72c8e5309ae646acbd3cfd60 |

本轮新增/修改文本显式 UTF-8，无 BOM；本日志更新后再读取验证。没有改共享 task.md/execution-log.md、业务原件、模板、服务器或其它子代理文件。

## 交父任务的现场限制

父任务独立运行同一新旧两文件：实际exit0，47 PASS/0 FAIL/0 skip，Node总计1090.4326毫秒。运行后重读四文件，字节数/SHA与子代理冻结值一致；已审阅helper diff，原完整矩阵分支、三目标确认与零业务写保护保持，新增报告仅代表指定单点范围。实际新备份仍RUNNING，未运行此UI验收。

仅在真实成功 audit、当前 MAIN/v4 原件及新鲜门禁全部就绪后，由父任务使用未占用 rN 运行：`NODE TASK/verify_goal_readonly.cjs --observation rN --point-audit <实际成功审计文件名.json> --selection main-program-current-installations-45dd7dc-r6-v4.json`。这只是调用合同，本子任务未执行。旧无新参数模式及旧失败证据保持原义；不能以本机 38+9 合同 PASS 代替真实页面或原完整目标 PASS。
