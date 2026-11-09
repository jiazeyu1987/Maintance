# Spug 运行依赖补齐：阶段 A BDD / TDD

## Current Status

阶段A本机实现及必要验证已完成并冻结，等待父独立验证及实际安装。父已批准设计 edd637287fc126901883631bf9edfea6e510e53fdf33fa3e10c699a095729dd0 的第一阶段。只新增依赖合同/正式单文件安装器、专属测试和本日志；旧350项闭包、产品、reader、资源及记录不改。无 Docker/服务器/浏览器/构建/提交；实际安装由父执行。整体发布尚未完成。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；未知依赖、漂移、缺原件拒绝。
- 是否从根因和长期维护角度解决：是；同一真实入口图固定构建和安装闭包。
- 是否存在临时补丁或绕过：否；同 c772 正式字节，只有 simple 可替换；不重发配置。

## 经验门禁

- Trigger：已提交解析器未纳入部署清单。
- Preflight check：实际14依赖、原11及另外2保持、c1七APPLIED/三HOST PASS/末项FAILED与runner原生终态、原entry/实例/mount身份。
- Blocker：未知/多文件变化、旧原件变化、测试/工作树/依赖缺失、已有未知安装。
- Verification：实际旧代码解析RED、候选真实解析与闭包GREEN、真实磁盘状态/原生过程与受影响回归；现场另由父验证。
- Forbidden action：不改旧350输入/报告，不操作Docker/服务器或手工替换，不把fixture当现场成功。
- Evidence：设计文档、父实际观察、专属原始日志/输入pins。

## BDD（先于实现）

1. Given 同c772真实entry/index及原11清单，When 检查运行闭包，Then 拒绝三项准确缺漏；完整14才通过。
2. Given c1实际55106B配置和旧runtime解析器，When 调真实configuration，Then SIMPLE_CONFIGURATION_INVALID；同提交候选真实解析和public投影保持全部binding选择状态。
3. Given 可读真实14文件，When 遗失进度载体/样式、增加未声明本地导入、动态导入、路径别名，Then 严格失败，不能把未知当平台依赖。
4. Given 原13项完全相同，When 准备安装，Then 仅simple；任意其它差异、未闭合c1或runner拒绝，默认prepare不构造真实传输。
5. Given 真文件、完整旧字节保全与写前guard，When 原子替换后回执/读回失败，Then 如实保留新字节和失败/未知，不能自动回滚重试。
6. Given 候选旁路解析通过但entry旧身份，When 验收，Then 不足PASS；必须精确原entry受控重载及新14文件、真实配置/入口合同和保护项证明。

## 测试限制

本机真实配置放临时文件调用真实解析函数；不输出内容。磁盘和原生子进程测试真实执行，但不会调用Docker/服务器。外部边界若需fixture，明确只验证协议且不能宣称真实安装；父独立原容器/隔离Linux验证另记。

## 已批准历史源码托管补充

Completion 增加唯一 `sourceCustodyPin`，共12字段。托管 `MainProgramSpugRuntimeDependencySourceCustody/v1` 严格三字段 `schemaVersion/baseResourceBuildPin/entries`；16行仅为14候选文件和本模块/专属测试，每行 `originalPin/preservedPin`，原始字节/SHA一致，私密排他原件必须完整读回。准备核当前干净源码；历史读取只从托管字节及原覆盖证据重建，不依赖已删除发布工作树，也不把融合后的 reader 路径当成旧执行路径。旧11证明复用已有 published_resource_evidence，不改旧记录。

BDD: 历史读取 -> Given 真实16文件独占副本及相应覆盖输入，When 候选副本被删除或调用 reader 位置迁移，Then 历史模式仍严格按原角色路径和16字节验证；准备模式拒绝缺件；重复角色、额外文件、原件变更拒绝。

BDD: 原生负向执行 -> Given 实际生成的 runtime/reload 程序和候选真实模块，When 本机不存在容器原entry，Then 原生进程明确失败且不能发任何信号；不能把可编译当真实安装。

BDD: 验收边界 -> Given 旁路解析成功，When 缺14文件/原配置/导入来源/重载新身份任一证据，Then 不生成安装PASS；写后未知保持实际新字节和原失败门禁，不重试。

## RED → GREEN 原生记录

所有日志位于本任务 PRIVATE，均排他创建并保留；相同 stem 的 `.private.json` 保存实际 argv、原生退出码、耗时和 logPin。pytest 固定缓存 Python，`-X utf8 -B -m pytest -q --tb=short -p no:cacheprovider`；`PYTHONPATH` 只指既有 `test-dependencies`，未安装依赖。

|阶段/日志|真实结果|原始日志SHA256|
|---|---|---|
|runtime-dependency-red-r1.log|13 FAIL；12项缺实现；真实旧解析器异常类型为 Refused，测试原先错捕获 ValueError，已按真实异常修正|547b6a4c4b05053abcaa3137e9c5d7f5cd71c80d374ab5654074b3ff68835acd|
|runtime-dependency-green-graph-r1.log|4 FAIL/9 PASS；误把数据文件 with_name 当执行依赖；限定 `__file__` 实际载体后13 PASS|17bb981ea5003150f3ba605b145bb354d7b13c51c8a64839a19f3fad73a884a9|
|runtime-dependency-red-records-r1.log|7 FAIL/13 PASS；真实checkout/c1/runner证据API尚缺|987dcac7c93a4e497771845b6d59efd497fa2c55a3e61a7d36531890f5040b20|
|runtime-dependency-green-records-r1.log|1 FAIL/19 PASS；真实Git argv是 --porcelain=v1，按原命令精确核验修正|46721215f71624fd585605307adf052e827ac7a4161e78b659ebc3a03a9f1711|
|runtime-dependency-red-prepare-r1.log|2 FAIL/20 deselected；缺completion/runtime观察API|6f65cabb03d9984489ee6ae4ffe285511f80e4dbcbd9aeda3efade994da3408c|
|runtime-dependency-green-records-r2.log|22 PASS/exit0/29.66s|922520e8b32c28dd7d56eac7c1b27ded3ce59d6d5fe99c02cec030e315d10128|
|runtime-dependency-red-historical-r1.log|4 FAIL/3 PASS/19 deselected；动态import别名、封存图、精确CIM命令|8e28c83d4b5149bfa143348ffcc2eb377a6c17b4603fa52fc0eba6ed8a57bcba|
|runtime-dependency-red-install-r1.log|5 FAIL/26 deselected；缺单文件替换/CLI/prepare|51b3fd4aa311cd30d5dd8c4504e1f737161ee931a3e14a0b8d77456615fd14bf|
|runtime-dependency-green-install-r1.log|31 PASS/exit0/31.23s；会话91519已收终态|1232323f0f25e8900a35c462e60a7cd400dd5624830c4ab3d5fcc43085783d7e|
|runtime-dependency-red-final-contracts-r1.log|2 FAIL/5 PASS/31 deselected；迁移reader旧角色拒绝及统一reload validator尚缺|72c2a8be75c3bad81df4fc1941ede9ec898ca733ebc152aa29ea5232bfd1d9dc|
|runtime-dependency-green-final-contracts-r1.log|39 PASS/exit0/44.21s；会话35407已收终态|cf8dd51afc902c18a73913a496ef9ded564421303ea0dc5f47084e16fcda165c|
|runtime-dependency-regression-r1.log|收集ERROR/exit2；两个不同工作树绝对路径使pytest根提升C:/，Windows受保护目录拒绝。未执行用例，10输入SHA保持；改为各自明确cwd/rootdir/confcutdir分组|47c8013360a64cf95c28b5eb0e92625fa9c7567f67e631b303f8fc5e3dc717f1|
|runtime-dependency-regression-r2-local.log|100 PASS/0skip/exit0/239.28s；新A+原resource activation/deployment delta|6a58d4782f4fbed1815181d8bcf70185840ba60d71018ccd42519622f4c882b3|
|runtime-dependency-regression-r2-candidate.log|35 PASS/0skip/exit0/7.46s；c772原routing/cross-route|be39dbae23398542dad974963e94b7402951d3fe666810d4b9af16da80c8d675|

测试真实运行候选模块解析父保存的55106B原配置；旧解析器是父实际现网保全6431B原字节，安装后回归不依赖活跃文件保持旧版。历史模式测试删除仅 pytest 临时副本并迁移 reader 路径；未删除任何发布工作树。生成 runtime/reload 程序通过真实本机 Python 子进程执行，真实候选导入成功、缺容器 `/proc` 原entry明确拒绝；该负向证明不代表现场安装。

## 阶段A调用合同与剩余现场门禁

1. 父先核冻结源码/测试与回归，将14候选及两工具源码原字节正式排他封存；创建严格16输入的覆盖原件。`make_dependency_completion(task, private, base_resource_build_pin, coverage_evidence_pin, source_checkout_evidence_pin, source_custody_pin, verify_checkout=True)` 纯重建12字段completion。
2. 激活输入严格11字段：schemaVersion=`MainProgramSpugRuntimeDependencyActivationInputs/v1`、sourceCommit（c772资源提交）、dependencyCompletionPin、baseResourceActivationPin、continuationInputsPin、continuationFailurePin、continuationCompletionPin、runnerExitObservationPin、runtimeObservationPin、operationId（如r1）、outputFile（`main-program-spug-runtime-dependency-activation-c7728ad-r1.json`）。c1控制45/r6独立绑定，不混为同一提交。
3. 默认 `python -X utf8 -B <TASK>/spug_runtime_dependency_completion.py --inputs <输入文件名>` 仅纯准备；显式追加 `--activate` 才安装。可独立只读调用 `prepared=prepare(task,private,input_basename)`、`ActualTransport(private,prepared).observe('before')`，不创建安装gate或重载。
4. 激活只能一次：固定容器独占gate和attempt，保全旧simple并复核原entry/实例/config/历史路径后原子替换一次；新字节原容器读回后精确SIGTERM原entry并验证受supervisor重生的完整身份/env。没有配置写入、host调用、备份恢复、重发c1或自动重试/回滚。
5. 独占输出：TASK `<outputFile>` 仅全成功；PRIVATE 同stem `.attempt.private.json`、`.private.json`、`.before-simple.private.py`、阶段原件及原生receipt/program/request/stdout/stderr。固定gate `spug-runtime-dependency-<完整容器ID>.gate.private.json` 保留；失败如实保存阶段、replacementState与原生回执，不产生core。
6. 资源PASS仅证明依赖安装与受控重载，`liveUiVerified=false`、返回 `publicationCompleted=false`。父仍须实际安装、原容器新14pin/配置解析和后续独立阶段B只验收；本阶段不处理最终selection、真实UI或整体任务完成。

## 最终冻结与命令

- 已批准原设计SHA：`edd637287fc126901883631bf9edfea6e510e53fdf33fa3e10c699a095729dd0`。
- `spug_runtime_dependency_completion.py`：48077B，SHA256 `050c1d175437db2d6977448a1f10738551f28daa0da4465d3e448466d6f2f2a5`。
- `test_spug_runtime_dependency_completion.py`：18801B，SHA256 `835f0b295ef2ef692ef38c2f65fe7fd99a3bd2e31a6a3c55940a5e719f92e6d6`。
- 两源码均内存 `compile(bytes, path, 'exec')` PASS，无pycache。回归前后10个实际受测源码/测试pin一致，两组原生退出均0；会话16594已收终态。
- 本工作区 cwd 下，`python -X utf8 -B -m pytest -q --tb=short -p no:cacheprovider --rootdir <当前repo> --confcutdir <当前repo> <TASK>/test_spug_runtime_dependency_completion.py <TASK>/test_main_program_spug_resource_activation.py <TASK>/test_main_program_spug_resource_deployment_delta.py`。
- c772工作树 cwd 下，同一pytest固定参数和该工作树 rootdir/confcutdir，执行 `<TASK>/test_archived_source_catalogue_routing.py ops/spug/test_smallapp_cross_route.py`。完整实际argv/cwd/输入pins分别保存在 `runtime-dependency-regression-r2-local.request.private.json`、`runtime-dependency-regression-r2-candidate.request.private.json`。
- 135项限定回归包含39项新A测试，不将重复执行叠加成不同用例数量；本机协议/文件测试不冒充现场验收。
