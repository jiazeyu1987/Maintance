# 控制升级只读观察正式提取

## Current Status

ready_for_closeout。本组件生产/测试已冻结，最终同轮 145 PASS / 0 skip / exit 0；父独立核验、限定提交及后续现场只读观察由父收口。前代 generation/custody 五文件已由父代理以 3b8ac7241c9ea769f4daae784ce190216b8a2890 独立提交，52 项验证通过；本阶段未修改。父分派本阶段只新增正式 observation 模块、专属测试与本日志，实际 SSH 和观察原件由父执行。

## 目标与里程碑

1. 读取旧私有 carrier 和正式 v4 消费合同，冻结输入/输出及只读 transport 接口。
2. BDD/RED：明确 generation pin 与候选 commit/revision；unit/env 原件、漂移/错误/秘密隔离及重复写拒绝。
3. 最小实现并 GREEN/相关合同回归，提供真实可调用只读入口，不执行远程。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；无旧 automatic 选择兜底，schema/pin/运行态不符明确拒绝。
- 是否从根因和长期维护角度解决：是；正式模块与共享 runtime gates，替代一次性 carrier 的模板替换。
- 是否存在临时补丁或绕过：否；不 replace/exec 旧 carrier，不伪造当前观察，不弱化 v4 字段和历史保全。

## 经验门禁

- Trigger：已安装控制代次的升级前只读 unit/环境观察。
- Preflight check：显式真实 generation pin、候选计划 commit/revision，正式 select_control_generation，当前 unit/dropin/PID/argv/env、业务/history/mount 及原件 pin；敏感原环境仅写 PRIVATE。
- Blocker：输入代次混用、当前身份漂移、读失败/超时、已有输出、public 泄露秘密、共享现态 gate 不完整。
- Verification：本机真实临时文件与有限只读协议 seam 分开记录；RED/GREEN/退出码/零 skip/源 SHA；实际服务器观察由父单独记录。
- Forbidden action：远程写入、安装/重启、旧 automatic fallback、carrier 模板替换、伪造 PASS 或把本机协议测试说成现场验证。
- Evidence：control-generation-upgrade-plan、前代 generation 日志；docs/experience-index 指向实际封包配置传递、多机器接管、PowerShell 编码门禁。

## BDD

- Given 显式 generation 和同一候选 plan/build/revision，When prepare 只读观察，Then 选择真实现有控制器并固定所有输入 pins，输出 v4 所需唯一命名。
- Given transport 返回实际 unit/dropin/process/env/business/history/mount 读值，When observe，Then 全门禁通过才写独占 public 报告与 PRIVATE 原始快照，public 不含原环境或认证文本。
- Given 任一输入/当前身份漂移、读取失败或输出已存在，When observe，Then 明确失败且不执行业务写入、服务重载或吞异常。

## 接口与实现边界

- `prepare_observation(task, private, *, suffix, generation_pin, plan_pin, source_commit, revision_id)` 只读解析正式 generation 和 selection，绑定候选公开/私密计划、四控制器及本机所有原件。不会观察服务器或生成新 generation。
- `observe_units(context, *, transport=None)`、`observe_environment(context, unit_pin, *, transport=None)`、`observe_all(context, *, transport=None)` 是真实 dispatch 入口；默认复用 `common.remote` 的固定 SSH 身份与严格 host key，父代理可直接调用。返回 `observationPin`、`privateSnapshotPin` 和只读事实；本组件不代父执行。
- `ReadonlyObserver` 复用正式 `RuntimeGates` 的独立只读方法，先发现真实 systemd/proc 环境，再以 `ORIGINAL_BASELINE` 完整复核；不使用需要真实物理锁的 `before/preserve`，不把 deadline 当锁证明。
- unit v1 保留目录、完整 conf 名单、前后单位/PID/argv/env、历史 guard 和 custody/inventory 核验；加入候选 sourceCommit/revisionId/previousControlGenerationPin。env v1 只按正式消费者增加 revisionId/previousControlGenerationPin。原 systemd 环境声明和声明字典仅在 PRIVATE，公开投影逐层白名单校验。
- 本地输出以 O_EXCL 创建，PRIVATE 原始响应先固化；输出已有则 dispatch 前拒绝。输入原件在编译前后、dispatch 后和最终写入后重核。私密失败响应保留，不能因此伪造公开 PASS。
- 远端程序仅内存加载新正式 runtime/observation 模块及正式 environment/custody 定义，不加载或替换旧 carrier。命令边界仅 systemctl show/is-enabled、Docker ps/inspect；不安装、重载、remount 或派发备份/恢复。
- source baseline 的 epochBindingPin 属于 57 本地 registry，仅 57 读取三来源 pin；58/59 读取本机历史、共享历史 guard 和完整 target layered custody。已与 runtime owner 对齐，原 activation 的 source 分支作用域保持。

## TDD 原始证据

- RED r1：`python -X utf8 -B -m pytest -q --tb=short test_main_program_control_observation.py`，16 FAIL / 0 skip，exit 1，1.27s；全部唯一原因为正式模块缺失。原件 `control-observation-red-r1.log`。
- GREEN 候选 r1：13 PASS / 3 FAIL，exit 1，30.21s；我把公开 `MainProgramConfigurationPlan/v2` 与私密 `MainProgramConfigurationInstallationPlan/v2` 的名称混用。按正式规划器精确修正两个合同，未放宽产品校验。原件 `control-observation-green-r1.log`。
- GREEN r2：16 PASS / 0 skip，exit 0，26.97s。原件 `control-observation-green-r2.log`。
- 新 BDD：Given 实际采集 unit/env 原件，When 本地独占持久化后送正式 activation v4 reader，Then 完整接受原合同；Given 采集后输入变化、嵌套未知私密字段或环境响应 PID 变化，Then 私密原件保留且不发布公开 PASS。
- 边界 RED r1：3 FAIL / 1 PASS / 16 deselected，exit 1，25.34s。两个真实预期缺口为 runtime 嵌套字段未拒、env 响应 PID 未在发布前绑定；另一个是 Windows 实际路径载体不符合正式 POSIX remote_pin，不能通过弱化消费者解决。原件 `control-observation-boundary-red-r1.log`。
- 载体纠正：只在该消费集成测试的外部 transport 协议边界映射显式 path/engine/directory 字段到 POSIX，保留真实临时文件、子进程、环境声明与原摘要；PRIVATE 快照仍是真实本机路径。不是服务器事实或产品 fallback。其余原 16 场景不变。
- GREEN r3：20 PASS / 0 skip，exit 0，34.60s；包含正式 `validate_environment_baseline` 消费闭合、两项安全边界和输入漂移保留。原件 `control-observation-green-r3.log`。
- REGRESSION r1：observation 20 + runtime/environment/generation/layered-custody 121，共 141 PASS / 0 skip，exit 0，132.87s。原件 `control-observation-regression-r1.log`。
- 三项补充回归没有另行声称 RED：57/59 使用实际 899 generation 保留四角色和 57 本地 source scope；生成的程序实际执行内存 bootstrap 与两个正式模块，再经真实本地文件/子进程采集，只有命令、proc、路径属于明确协议 seam。3 PASS / 20 deselected，exit 0，2.11s，原件 `control-observation-bootstrap-r1.log`。执行后恢复本进程模块注册，避免导入顺序污染。
- 最后一个 BDD：Given unit 原件已固定真实 argv/environment/systemd 摘要，When 两次观察之间环境发生变化，Then env 采集明确拒绝，不能将新状态当作原始基线。RED 为 1 FAIL / 23 deselected，exit 1，2.94s，真实 DID NOT RAISE；原件 `control-observation-environment-red-r1.log`。最小实现只比较原 unit.runtimeEvidence 已固定的三个摘要。
- 最终 REGRESSION r2：observation 24 + runtime/environment/generation/layered-custody 121，同轮 145 PASS / 0 skip，exit 0，88.64s。原件 `control-observation-regression-r2.log`；源文件和测试 SHA 与冻结值保持，未生成实际观察原件。

## 冻结候选与父执行入口

生产和测试已冻结；不会继续增加阶段外场景。

- `main_program_control_observation.py`：27505 bytes，SHA256 `25817299e84b4e45754e8905ef12f32ea2d50f045c053737b308002ecd4ea0fc`。
- `test_main_program_control_observation.py`：16568 bytes，SHA256 `d9840bfac0842daa66fd4fa9facf9222d250ff87ea1c93bbb5ed3fd13eae26bb`。
- 两文件显式 UTF-8 read/compile 通过；正式 runtime source 18815 bytes SHA256 `9d88085f82b4b08c4a5241314b032dc907145b13758e0a46303bb54a88687bc8`，父已以 f03bfd9 提交。
- 父独立验证命令：`python -X utf8 -B -m pytest -q --tb=short doc/tasks/20261106-spug-prod-incremental-to-two-targets/test_main_program_control_observation.py`；插件自动加载关闭，PYTHONPATH 为既定独立 test-dependencies。

真实只读观察由父另行执行，逐 host/逐阶段调用：

```python
context = prepare_observation(TASK, PRIVATE, suffix='59',
    generation_pin={
        'file': 'main-program-control-generation-899730d-r1.json', 'bytes': 2526,
        'sha256': '9ca1cc30ddabc0594a8066f90a7d0f7ca0300d1a972eea196cbc6ac66a9d43f9'},
    plan_pin={
        'file': 'main-program-configuration-plan-45dd7dc-r5.json', 'bytes': 14714,
        'sha256': '201b897582afdfc9ee41f3b9f29e9178236cde81b4a78e670c92836c7cbde009'},
    source_commit='45dd7dc65409c87fe856584b85873ea96c0b830e', revision_id='r5')
unit = observe_units(context)
environment = observe_environment(context, unit['observationPin'])
```

如单位观察已成功，可重新 prepare 同一显式上下文，再仅调用 `observe_environment(context, actual_unit_pin)`；不得盲目重跑 observe_all。已有原件绝不覆盖，失败 PRIVATE 原件同样保留。此阶段没有 SSH、Docker 调用、构建、安装或提交，单机协议 PASS 不代表已观察、激活或发布 45/r5。
