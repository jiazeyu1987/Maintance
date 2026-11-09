# 已完成控制暂存的历史回执收尾

## Current Status

implementation / ready_for_parent_validation。延续同一控制代次任务。59/r6远端已返回STAGED_NOT_ACTIVATED/complete并实际写入，原本地发布因SSH stderr非空拒绝；原始attempt/transport/stdout/stderr/result保留。仅新增main_program_control_staging_finalize.py、本专属测试和日志；不修改原stager/runtime/activation、旧输入或服务器，不重新派发暂存。

## 目标、里程碑与验证

1. 显式读取已pin三份PRIVATE原件，关联真实stdout/stderr，唯一完整JSON终态与原结果逐字节对应。
2. RED证明缺失、篡改、非零、超时、未知/未完整终态、任意stderr、输入/执行源码变化、重复收尾都拒绝。
3. GREEN最小实现：复用原纯prepare重建generation/两代实际包/coverage/planner/观察完整闭包；重建原payload SHA，核所有原输入/执行pin，再调用原validate_generation_staging。
4. 默认prepare零写；显式--finalize只O_EXCL发布两份原stage core，附privateSnapshotPin与transportEvidencePin，原件不重写。不冒充当前现场准入；后续activation仍需真实实时门禁。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。仅严格接受空stderr或完整锚定的已知Windows SSH收尾诊断，且必须真实exit0、timeout=false、完整成功终态和全部原件闭包通过；其他stderr拒绝。
- 是否从根因和长期维护角度解决：是。分离已完成远端动作与本地历史报告发布，显式使用不可变原件收尾，避免重复服务器写入；不通过改变旧源码使原attempt执行pins失效。
- 是否存在临时补丁或绕过：否。原runtime/factory/锁/epoch/历史门禁及原stage validator不降低；收尾仅承认原已完成stage，不创造新的远端成功或激活。

## 经验门禁

- Trigger：远端已完整成功、原日志已保全，但本地stage core尚未发布。
- Preflight check：显式attempt/transport/result pins、原stdout/stderr pins及唯一JSON；实际0/非timeout、原终态/false flags；精确旧源码与输入字节、实际generation/plan/build/coverage完整闭包；两目的文件不存在。
- Blocker：任一缺失/变化、未知执行状态、未知stderr、部分或失败终态、已有输出或任何正式validator拒绝。仅阻断收尾，不重跑原服务器动作。
- Verification：真实临时文件及实际两代tar/原纯prepare/原validator测试；保存RED/GREEN原日志、冻结SHA；父实际输入只读验证后才决定本地发布。
- Forbidden action：不重派transport，不修改旧attempt/result/stager或运行配置，不扩大stderr白名单，不改写失败原件为PASS，不删除部分输出再重复。
- Evidence：主任务既有release-agent-checklist的历史保全与代次门禁；本专属BDD/TDD；原59/r6三份PRIVATE原件pins。

## 固定输入、输出及BDD

MainProgramControlStagingFinalizeInputs/v1仅schemaVersion、attemptPin、transportPin、resultPin；三pin均PRIVATE相对单一filename/bytes/sha256。stem、host、commit、revision、公共输出名均从已核原attempt重建，无路径覆盖参数。stdout/stderr由transport记录的精确path pin读取，result必须等于stdout完整JSON的canonical字节。允许的非空stderr仅`close - IO is still pending on closed socket. read:1, write:0, io:<16hex>\r\n`一行；无附加文字、额外行、缺结束符或其他错误。

- BDD：Given真实完整已完成stage原件，When默认prepare，Then全部原闭包通过且无文件写入/transport；显式finalize只发布两份原core，原stage validator可正式消费。
- BDD：Given缺失或篡改任一原件/pin、非零/timeout/未知/未完整/危险flag，When收尾，Then明确拒绝且零公共输出。
- BDD：Given任意未知stderr，When已有stdout成功，Then仍拒绝；仅严格原SSH诊断或空stderr可按原退出与完整结果判断。
- BDD：Given原prepare输入、执行源码或payload已改变，When收尾，Then当前字节/重建闭包拒绝，不调用远端来补证。
- BDD：Given两份输出任一已存在，When再次finalize，ThenO_EXCL拒绝且所有原件与现有输出不变。

实际原59/r6：attempt2200291B SHA533248c000691e65e742e53671edf9dcb8d73e827daa49f5ee02ad04089d5165；transport643B SHA821e9139ef2b35841d81c4313cbbe5bd7baec9aa2c8e90402eec43e56cd34939；result2713612B SHA6a53bae649bbb26b1963929edab6876264a0848cacc558b177369baf9df9525a。只读核实，不修改。


## 接口与真实RED

新模块仅提供prepare(task, private, inputs)、finalize(task, private, inputs)、run_request(task, private, inputs_file, *, finalize_output=False)。不提供transport参数，不导入/执行SSH、Docker或其他服务器命令。输入文件由父任务显式写TASK，建议名main-program-control-staging-finalize-inputs-<suffix>-45dd7dc-r6.json，三个PRIVATE相对pin固定到原attempt/transport/result。默认命令：

```text
python -X utf8 -B <TASK>/main_program_control_staging_finalize.py --inputs main-program-control-staging-finalize-inputs-59-45dd7dc-r6.json
```

默认只输出READY_TO_FINALIZE与历史身份/诊断类别，不写文件。唯一显式发布追加--finalize，输出STAGED_NOT_ACTIVATED、engineStagedPin/configurationStagedPin、historicalStageOnly=true、activationPerformed=false、remoteDispatched=false。58使用其独立原件pins；57/r6是实际FAILED/candidate-before，必须拒绝，不能据exit0或无timeout当业务成功。

实现先核三原件及原日志、完整终态和创建闭包，再核原全部inputPins/executionInputPins；重跑冻结stager的纯prepare以真实generation/plan/两代tar/coverage/观察重建，再重建原bootstrap payload的字节数和SHA。fresh输入集合须与原完整集合精确相等；从原inputPins中唯一匹配已pin的显式inputs原文件，先将其读入原Records，完整保留该原件并重建原字典顺序。原actual经冻结project_stage_reports重建后必须精确等于原reports，最后原validate_generation_staging通过。发布只给两份原core加privateSnapshotPin和transportEvidencePin；后者指原transport私密原件，其stderrPin保留可查诊断，不改写原执行结果。

RED：23 FAIL / 0error / exit1，125.12s。所有真实临时原件、两代tar、原prepare先成功构造，实际失败均是待新增main_program_control_staging_finalize模块缺失。PRIVATE/control-staging-finalize-red-r1.log，28735B，SHA256 `6184c51cd8c0d1ff2fe321bd88670834ccee49aa65a4680f3653824567585326`。不是缺测试依赖或伪造运行成功。协议fixture明确标记远端终态与宿主观察边界，不能把本机测试称为现场stage。


首轮GREEN真实21 PASS / 2 FAIL / exit1，131.88s：两个成功例在新增payload摘要门禁失败。原因是原attempt用canonical JSON保全prepared，丢失原repr生成脚本使用的字典插入顺序。未放宽摘要比较；改为从原inputPins中唯一已pin的显式inputs原文件读取其原始键顺序，再用原纯prepare完整重建prepared及全部输入集合，最后生成固定payload核原bytes/SHA。PRIVATE/control-staging-finalize-green-r1.log，2350B，SHA256 `80247fc338770c94b8a55a7072477508fd46f784eea2458199f875c8737279d8`。

针对两成功例GREEN：2 PASS / 21 deselected / exit0，26.99s。包括默认prepare零写、空stderr/精确已知诊断、两原core O_EXCL发布、原正式validator消费、原件保持和重复拒绝。PRIVATE/control-staging-finalize-positive-green-r2.log，116B，SHA256 `2924cd9a9ae4421f0fdf4901f9b0cf77f215764b5fe13f9506180a755c76f2b2`。不存在重写原attempt或跳过payload比较。


## 最终回归与冻结

REGRESSION：`python -X utf8 -B -m pytest -q --tb=short test_main_program_control_staging_finalize.py test_main_program_control_generation_activation.py -k "not v4 or staging"`，35 PASS / 47 deselected / 0skip / exit0，142.56s；新23项与既有v4 staging12项。PRIVATE/control-staging-finalize-regression-r2.log，128B，SHA256 `aeaf0ab4b791e161f21b6e4880bd1fd7dbc07cb6b63b144b53b7adfad8d315b0`。完整原pure prepare、实际两代tar/full coverage、原stage projection和正式validator均在成功用例实际执行，零transport。两个新增Python文件compile PASS，不生成pyc。

冻结新增模块main_program_control_staging_finalize.py：12165B，SHA256 `169495e184809a8d84a8c9ffeb4fb3ec8544d0a642a24114ecdb71f85875669f`；测试test_main_program_control_staging_finalize.py：9855B，SHA256 `19cf5ae6d601b471f0f1fa1d3c795f9adcd569684c79a4d83d48a1641e2b9c88`。本次最终回归期间实现和测试未修改；日志自身SHA另行交父。

保留原冻结模块：stager ef5461391a132001586c4c559f1278aa9de8d624c556672b8b31ca7b7f95568c；runtime 9d88085f82b4b08c4a5241314b032dc907145b13758e0a46303bb54a88687bc8；activation a8249f563347f2f88f0e202a9696e8a687c7c82b681ad7540b3bcb69752d99fd。末尾只读逐SHA核验保持，未修改旧plan/观察/attempt/result、未访问服务器、未构建或提交。本子任务没有对实际59/58执行finalize，也没有创建实际finalize inputs；由父任务审查、独立测试并只读核验真实原件后决定本地O_EXCL发布。57/r6实际FAILED/candidate-before不得消费。
