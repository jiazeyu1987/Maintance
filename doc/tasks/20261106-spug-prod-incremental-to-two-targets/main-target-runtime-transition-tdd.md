# 目标控制服务后继过渡检查

## Current Status

ready_for_closeout。实现与有限回归84 PASS，已发父审，等待父统一审查/提交及真实切换验收。父任务承接上一持久视图3文件的审查/提交/真实主机验收；该前项状态不由本子项改写。本项仅新增独立runtime helper、测试和本文，不改原RuntimeGates、不连接远端、不提交；未创建worktree，所有自有测试容器已移除。

## 目标、里程碑与预期验证

1. DONE：阅读原RuntimeGates、原spec/controller及candidate结构，设计严格单目标后继合同，父审通过后实现。
2. DONE：BDD→RED→GREEN，明确区分后继运行spec与原历史绑定，复用原进程/包/单位/历史/业务门禁，所有原件实读。
3. DONE：隔离Linux有限回归84 PASS；实际文件/PID/proc边界，明确systemd/Docker命令仅为协议，不是实际服务切换或安装证明。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；未知变化和缺失历史拒绝，不临时篡改spec或跳过custody。
- 是否从根因和长期维护角度解决：是；将指定target后继运行态和原历史绑定显式分离，复用既有完整观测。
- 是否存在临时补丁或绕过：否；不触发切换、不创造receipt/安装选择、不改旧合同。

## 经验门禁

- Trigger：单角色控制代次升级、原receipt/custody、真实PID/argv/env/exe、dropin集合、原挂载及历史保护。
- Preflight check：固定旧spec/完整before、唯一target、candidate旧绑定、新153包与16配置、唯一新增dropin；原custody仍用完整原spec实读。
- Blocker：未验证旧绑定、改变source/物理/历史/原单位/原包/原配置、旧PID仍在原workingDirectory活动、未知观测差异或旧新进程不匹配。
- Verification：RED→GREEN→REGRESSION；原生边界由调用者实际提供，父另做真实服务器切换前后验收。
- Forbidden action：不修改原RuntimeGates、不将旧custody改成新证据、不临时替换actual spec、不reload/发布/restore、不用mock PASS充当实际安装。
- Evidence：main-final-target-upgrade-plan.md“目标控制服务切换的明确过渡检查”、既有RuntimeGates完整观察和后续TDD原始记录。

## BDD

- Given 完整旧spec/运行态和严格重建的target候选；When 核验指定目标后继；Then 只允许该target的owner/control/engine/PID/唯一新dropin及新153包变化，其它角色和所有原件保持。
- Given 原receipt/custody仍绑定旧owner/control；When 观察新target；Then 用原spec真正实读旧链和旧包，完整保留原历史；不重写成后继证据。
- Given 任意额外dropin、旧PID仍处理原workingDirectory、source/业务/挂载/原历史变化或新PID实际argv/env/exe不符；When 过渡检查；Then 明确拒绝，无服务/文件写入。
- Given 原Requires/After已经包含同host精确保全服务；When 显式追加同一依赖；Then 按原token并集去重，拒绝未知服务或额外network依赖。
- Given 原row携带旧环境baseline具体字段和未知字段；When 构造新CONFIG_EXACT row；Then 旧四种已知环境字段只保留在历史spec/retained上下文，不冒称新进程证据，未知字段精确保持；观察新增的未知字段变化也拒绝。

## 执行证据

- 已读取经验索引和原RuntimeGates；本项命中运行资源依赖闭包、历史来源/挂载保护、单角色代次门禁，沿用父计划的经验摘要。无远端动作。
- RED: `python -X utf8 PRIVATE/run-target-runtime-transition-linux.py red-r1` -> native exit1；1 failed +45 setup errors，全部预期 `MISSING_TARGET_RUNTIME_TRANSITION_GATE`。源613文件，snapshot SHA `7a10d1bdfc64a2c0a07da70df5c3ee2b4458b4fdea4e1393a3ef53e3623d3992`，inputsUnchanged/containerRemoved=true、remoteWrites=0；随后才创建实现。
- `... green-r1` 的固定快照实际pytest46 PASS/6.16s、native exit0，但载体因父并发修改独立view parser导致inputsUnchanged=false而exit1；原件保留，不视为完整GREEN。父已知该并发变动；后续重跑。
- 增补实际旧row四个已知环境baseline字段、未知row保留断言；旧字段明确移出新运行row而精确保留在原spec和retained结果，unknown字段不删除。
- RED: `... red-r2` -> native exit1；1 failed/46 passed in6.58s；未知target观测字段改变未被拒绝（DID NOT RAISE），snapshot `79cfd6ad92e0af7b02d926c8d18ba4b6b407863c37fa08b61ff1cf59c111598d`，inputsUnchanged/containerRemoved=true；随后最小加入观测字段白名单以外逐值保持检查。
- 父对磁盘策略的正式接线方向保持16文档、owner顶层targetResourceAdmissionPolicies；本项不修改物理target/baseline和容量策略，也未引入17文档例外。
- 最终载体以实际依赖闭包9个完整源文件取代全仓无关源：本项helper/test、原RuntimeGates/test、main_program_control_activation、main_program_installation_selection、installation_history_custody、原真实文件custody fixture及common。原7依赖逐字与RED2已固定pins一致；未抽AST或替换模块，父可并发修改无关candidate/staging。测试nodes、image、12 wheels、预算完全保持。
- GREEN + REGRESSION: `python -X utf8 PRIVATE/run-target-runtime-transition-linux.py regression-r1` -> native exit0、载体exit0；84 passed in20.53s（本项47 +原RuntimeGates37），9完整依赖源，tar256000 bytes SHA `22d85525f61170facd5d5612d187b260228969e7968bfcc6e5fb2cc532925649`。stdout180 bytes SHA `5f115c6d391833276d606d0eb1c3cc28698396427d230ec922d664d44b5b217c`，stderr0，inputsUnchanged/containerRemoved=true、remoteWrites=0、actualBusinessRestore=false。
- 固定image `sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735`，12已pin wheels、network none、read-only root、cap-drop ALL、no-new-privileges、pids128、512MiB、cpu1、work256MiB/tmp64MiB、600秒有限进程预算；未扩预算或构建新包。
- 自有两份Python源码显式UTF-8读取、compile成功、无行尾空格；helper16784 bytes SHA `61de004ecff45104088c5091bcbffdda76aba9332aec26d3f379b64039673bbc`；test19953 bytes SHA `229ab00103d7e32a31f8fc6e36f2f6089844b19baa818006bdff06a42d6ce0bc`。

## 最终接口与边界

`TargetControlRuntimeTransition(original_spec, *, candidate, dropin_pin, added_dependencies=None, verify_environment, verify_custody, lock_guard, run=None, pin=None, read=None, paths=None)` 保留完整原spec副本。构造时仅纯输入校验：固定主机/target、旧绑定和147→153、新engine、16文档canonical pins、同原unit目录且优先级更高的唯一dropin，以及精确同host保全服务依赖。

`before()` 必须在新dropin不存在、16份文档和新包已暂存时执行。复用原RuntimeGates完整实际观测，逐份真读新配置/新153包，内部保留精确基线；不把外部给定dict当成历史观察。

`after(before, *, successor_pid)` 只接受本对象捕获的基线。外部明确PID必须不同于所有原控制PID；新row只重绑定指定目标的engine/owner/control/commit/包/PID/dropin和CONFIG_EXACT，移除旧argv摘要及四种明确baseline字段，所有未知row字段保持。目标unit允许集合显式包含全部原dropin和原current额外dropin，新pin唯一追加。

后继观测通过原RuntimeGates完整执行；`RetainedHistoryRuntimeGates` 仅将custody/inventory委托持有完整原spec的原gate。旧配置和旧147包仍实际实读；无历史custody的目标也不能漏查。来源和其它包逐项保持，containers/fstab/全部mountinfo/historyGuard/原custody/inventory及其它所有观察字段精确相等。目标属性只允许明确PID/dropin及Requires/After并集变化，未知观察变化拒绝；旧scope和旧control入口仍有进程/worker活动拒绝。

返回 `MainProgramTargetRuntimeTransition/v1`、`TARGET_SUCCESSOR_RUNTIME_VERIFIED`，包含真实before/after与明确retained baseline上下文；`serverWrites=false`、`installationReceiptCreated=false`、`restoreDispatched=false`。本项没有服务切换、远端dispatch、挂载、构建、receipt或安装选择功能，不能据此冒称真实服务器切换或业务验收。
