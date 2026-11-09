# 完整观察警告通道修正

## Current Status

in_progress。实现提交 df88eac 已通过245项回归及父36项独立验证；实际唯一观察 operation 5b70ac427cc442d1843e59ec3f58e9fd 在配置导入阶段遇到 CryptographyDeprecationWarning，宿主以 MAIN_RESOURCE_OBSERVATION_STDERR_UNEXPECTED 结束。原worker PID151701/startTicks119425375的真实终态必须先核查，不直接重派。实际r2宿主exit1/44.000秒、输入保持、runtimeWrites=false；无安装或恢复。

## Goal and milestones

1. 保存实际失败原件，按完整容器/PID/startTicks/argv nonce核唯一自有只读worker；如仍在运行，仅向该worker发送一次SIGTERM并核实际退出，随后显式查询释放自有gate。
2. Subagent-Driven Development：先写真实Python warning的BDD/失败测试，再修正专属观察协议。保留原stdout JSON、完整文件读取、原校验及现有预算。
3. 父独立验证新增场景和原受影响回归，通过后限定提交；再批准一次新完整观察。

## 根因与正式方案

Docker stderr同时承载Python库诊断和新进度协议。此前把全部非进度行当损坏协议，改变了既有原生命令的warning行为。正式方案将Python warnings.showwarning转为明确的WARNING协议事件，保存原warnings.formatwarning文本及真实类别到本操作私密原件；父只暴露类别、数量、原件pin，不在公共错误或进度中输出诊断正文。WARNING不得续停滞期限、改变阶段/文件计数或代替完整结果；原生异常、非warning任意stderr、损坏协议、非零退出仍明确失败。正常完成回执必须显式记录诊断存在和对应pin，不能静默隐藏。

该协议仅适用于本任务观察工具，不修改产品依赖、warning过滤配置、共享publication helper、源/目标控制或历史数据。不可设置PYTHONWARNINGS=ignore或屏蔽cryptography警告。

## BDD and expected verification

- Given 真实warnings.warn发出的DeprecationWarning及有效完整结果，When 实际Python子进程执行，Then 保存类别与格式化原文的诊断原件、终态显式报告warning，观察结果不变且只派发一次。
- Given warning连续发出但没有完成阶段/文件，When 超过idle，Then 仍STALLED、保留gate，不因warning续期。
- Given 任意原始stderr、畸形WARNING、伪造身份、超限正文、非零退出或不完整JSON，When 执行，Then 原拒绝和原件保留保持。
- Given 完整真实观察，When 成功，Then 仍核原PID实际退出、前后实例一致和完整v1合同。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。Python warning作为显式诊断保存并报告；异常和原生失败不放行。
- 是否从根因和长期维护角度解决：是。分离完成进度与运行诊断的协议语义，不按某个库的文本硬编码豁免。
- 是否存在临时补丁或绕过：否。

## 经验门禁

Trigger：实际库正常warning与进度共用stderr。Preflight check：先确认原worker身份与终态、保留实际r2失败及冻结源码，严格RED→GREEN→REGRESSION。Blocker：原worker未知、warning被忽略或驱动续期、输出原合同变化。Verification：真实子进程warning/停滞/异常测试与实际完整容器观察分开留证。Forbidden action：不屏蔽warning、不通配杀进程、不重启Docker/业务、不改完整读取、不过写历史。Evidence：resource-observation-5b70ac427cc442d1843e59ec3f58e9fd及spug-resource-observe-delta838-lifecycle-r2私密原件。
