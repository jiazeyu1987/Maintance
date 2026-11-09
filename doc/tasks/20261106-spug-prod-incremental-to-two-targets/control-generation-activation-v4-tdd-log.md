# 控制代次激活 v4：专属验证记录

## Current Status

ready_for_closeout。本机 v4 准备与证据校验阶段完成并冻结，待父代理审查和限定提交；实际现场 stage/unit/environment 原件尚未生成，现场激活保持阻断。已识别同一任务目录与上位 `control-generation-upgrade-plan.md`、`control-generation-upgrade-refactor-design.md`。仅修改本记录、`main_program_control_activation.py` 和新增 `test_main_program_control_generation_activation.py`；未访问服务器、构建、提交或生成实际 v4 安装原件。

## 目标、里程碑与预期验证

保持原 activation v1/v2/v3 及两次确切失败续办合同；新增 v4 的显式 revision、前控制代次、新 stage/unit/environment 和 coverage 绑定。复用唯一 owner 的 generation 与 layered custody API，不伪造 Spug 已发布或 57 活动 receipt。

1. 已完成：只读核对上位设计、原 prepare/dispatch/环境与回执保护合同；取得 generation owner API。
2. 已完成：冻结 v4 纯输入、stage、环境及派发阻断合同，并用真实本机临时文件记录 RED。
3. 已完成：最小实现、GREEN 和受影响旧入口回归；末次 202 passed / 0 skipped / exit 0，源码 SHA 如下，已冻结。
4. 现场阻塞：实际完整 prepare/远端执行仍须有新代真实 stage/unit/environment 原件；缺失不能用本机协议 fixture 放行。精确双包覆盖报告、planner 和分层 custody API 已由对应 owner 完成并被本阶段正式读取。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；显式版本分派，缺合同或原件立即阻断。
- 是否从根因和长期维护角度解决：是；原版本原样保留，新代以显式 pin 组合，公用校验不复制历史成功。
- 是否存在临时补丁或绕过：否；不能动态替换旧远程脚本字符串，不能把目录性能报告当完整引擎回归。

## 经验门禁

- Trigger：已激活控制代次升级、旧完整覆盖与新 delta 覆盖并存。
- Preflight check：核显式 generation、build、plan revision、stage/unit/environment 原件；58/59 分层 custody 由共享验证器完整读取；57 无 receipt。
- Blocker：旧 PID/观察混用、修订或任一 pin 漂移、缺本代覆盖、遗漏包差异、无法完整验证旧回执保全。
- Verification：本机真实临时文件 RED→GREEN→REGRESSION；测试不声称真实服务器安装或业务恢复。
- Forbidden action：猜最新原件、修改旧失败/成功历史、复用旧 461 为新 catalogue 绿证、服务器调用、构建或实际 v4 原件生成。
- Evidence：`docs/experience-index.md` 路由的包清单身份与桥接期限、自动增量链与恢复周期、多机器接管门禁，以及上位升级设计。

## BDD

- Given 明确 v4 输入及新 revision，When 校验输入，Then 仅接受同 revision/host/role/commit 的 plan/stage/unit/environment/output，缺 coverage 或混入 automatic/续办字段立即拒绝。
- Given 前代真实控制 PID/config 和新的只读 unit/environment 观察，When 准备新代，Then 两份公私观察的精确投影、环境原字节摘要与前代控制绑定，旧 r1/r2 或不同 PID 不接受。
- Given 新 stage 含 8 新/27 保留的完整 35 文档闭包，When 准备激活，Then 校验新/保留集合互斥且并集完整、27 保留仅验证而未重写，实际 factory 和业务保全门禁保持。
- Given 本代覆盖合同或远端分层 custody 尚未完成验证，When 请求 activate，Then 在创建 attempt、调用 transport 或写成功原件之前明确阻断。
- Given 原 v1/v2/v3 输入和旧测试，When 新分支加入，Then 原精确失败续办、环境、回执轮转及 dispatch 行为保持。
- Given 原完整覆盖与当前 delta 的显式原件，When v4 校验覆盖，Then 实读两代 STANDARD 147/轻量 146 的 tar、manifest 和每成员摘要，验证唯一 catalogue 语义改变、换行等价及 Linux 59/50/50 零失败零跳过原日志；遗漏差异、假未变、缺失败原件、日志或 module SHA 漂移均拒绝。
- Given 原 automatic 与 MAIN 分层回执，When 新代切换前后执行保全，Then 调用共享 layered verifier 并完整核原 engine 成员；最后仅追加本次实际发布的回执，不更改原 recipe。
- Given v4 rich 回执，When 投影核心成功证明，Then 必须回显原 activationInputsPin、coveragePin、previousControlGenerationPin、revisionId，58/59 还必须有本代最后回执的完整分层观察。

## 执行证据

父代理报告：旧 461 源 input 中 360 原字节相同、101 原字节改变（99 换行、2 语义）；双包 147 范围 28 原字节改变（27 换行、唯一 catalogue 语义），Linux 159 当前未有成功终态。此处只记录父报告，不冒称本代理实跑或覆盖完成。

RED（本代理实际）：`python -B -X utf8 -m pytest doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_control_generation_activation.py -q --tb=short`，退出 1，29 failed / 6 passed / 0 skipped，4.50 秒。28 项因缺 `validate_generation_inputs` / `validate_generation_staging`，1 项因原环境入口只认旧 r2；无 setup 错误。负例及缺原件阻断 6 项已通过。开始最小纯合同实现，尚无全链成功声明。

GREEN/REGRESSION 1（实际）：同新文件加原 activation/environment/preswitch/coverage 四文件，退出 0，178 passed / 0 skipped，13.59 秒。

RED 2（实际）：新文件 `-k coverage`，退出 1，12 failed / 2 passed / 33 deselected / 0 skipped，7.37 秒；12 项均缺新覆盖 API，无 setup 错误。父此时已产生精确 `main-program-control-coverage-45dd7dc-r1.json` 及 Linux r2 成功原件，原 r1 失败仍保留。最小实现后同命令退出 0，14 passed / 33 deselected / 0 skipped，10.63 秒；只读取已有真实双包和记录，不重新运行 Linux 或构建。

RED 3（实际）：`-k follows_only`，退出 1，1 failed / 47 deselected，原 prepare 尚拒绝 v4。随后显式 v4 分派复用旧共同准备逻辑，新增 plan 全等重建、stage/unit/environment 固定名、coverage 与 generation 原件绑定。

RED 4（实际）：`-k remote_retention`，退出 1，2 failed / 48 deselected；原远程函数只读旧 `steps`，对新 typed recipe 抛 KeyError。随后新增明确 schema 分派，调用唯一 owner 的 `verify_layered_receipt_custody`；原 v1 校验不改。

RED 5（实际）：`-k core_requires_unchanged`，退出 1，4 failed，均是篡改 v4 回显仍未被拒绝；新增四字段严格绑定。测试曾直接导入 unittest 类导致额外收集其 5 项旧场景，现改为模块引用，未改任何期望。

GREEN/REGRESSION 2（实际）：新54项加原143项，退出 0，197 passed / 0 skipped，43.63 秒。没有远程、构建、提交或实际代次原件写入。

完整 prepare 集成载体首次运行：退出 1，1 setup error / 54 deselected；正式 generation 选择形状不含 role，而 planner 要求 role。此为已证实接口集成缺陷，不冒称缺功能 RED；父确认由 generation 唯一 owner 正式新增角色字段及 SELECTION_CONTROLLER_KEYS，保持 planner 严格角色门禁，载体不得私自补字段绕过。待其冻结后继续完整准备验证。

集成修正：generation owner 已正式导出 `SELECTION_CONTROLLER_KEYS` 并在实际 loader 返回 `role`，本载体直接复用该常量；未弱化 planner。完整准备载体明确仅隔离已独立测试的 generation bundle 输入，真实读取本代 coverage、四个真实 tar、纯 planner 与临时 public/private/stage/unit/environment 文件。该 fixture 从不作为安装证明。

集成 GREEN（实际）：`-k 'complete_prepare or remote_final_custody'` 2 passed / 54 deselected / 0 skipped，5.13 秒。随后将完整准备扩至四个固定控制角色，实际 `-k complete_prepare` 4 passed / 55 deselected / 0 skipped，18.50 秒；57 无回执，57 source 精确引用先完成的本代 target，payload 仅编译而不执行。

本阶段正式 API：`validate_generation_inputs(inputs)`、`validate_generation_staging(inputs, plan, build, engine_report, configuration_report)`、`validate_generation_coverage(records, inputs, predecessor)`；coverage 返回 `coverage/build/delta/packageFiles/previousPackageFiles/physicalPins`。v4 `prepare` 使用唯一 generation loader 与 planner 全等 validator，不重写旧 schema。

v4 rich 新增 `activationInputsPin/coveragePin/previousControlGenerationPin/revisionId`。58/59 的 `previousCustodyObservation` 是实际切换前旧代完整观察，`currentLayeredCustodyObservation` 是最终本代追加后的完整观察；后继 generation 使用显式分派消费，旧 899 不追填新字段。

最终 REGRESSION（本代理实际，源与测试运行期间未修改）：

```text
python -B -X utf8 -m pytest
  doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_control_generation_activation.py
  doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_control_activation.py
  doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_control_environment.py
  doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_control_preswitch.py
  doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_activation_coverage.py
  -q --tb=short

202 passed in 44.75s
exitCode=0, skipped=0
```

Python 为 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`；pytest 依赖由显式 `PYTHONPATH=C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies` 提供。此为本机回归，不是新的 Linux/服务器运行；159 Linux 成功仅作为已固定原件被完整验证。

冻结实现：`main_program_control_activation.py` 107479 bytes，SHA256 `a8249f563347f2f88f0e202a9696e8a687c7c82b681ad7540b3bcb69752d99fd`。

冻结测试：`test_main_program_control_generation_activation.py` 31117 bytes，SHA256 `f67513703d57a7093081d7258dca5a97f88c424690bb05a290e2a51506500174`。新 59 项加旧 143 项共 202；所有旧输入/失败续办分支回归保持。没有扩大产品入口、修改共享日志或其他 owner 文件。
