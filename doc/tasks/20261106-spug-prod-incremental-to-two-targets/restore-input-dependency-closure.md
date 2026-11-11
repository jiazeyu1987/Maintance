# 恢复输入重建模块的正式封包依赖

## Current Status

in_progress。延续原恢复功能交付，先 RED，再最小补齐两种引擎封包；不安装、不执行备份或业务恢复。

## 目标、里程碑与预期验证

普通归档控制入口已调用 `recovery_restore_inputs`，保全来源 v2 历史重建已调用 `recovery_preservation_inputs`；两者在工作源码存在，但当前 STANDARD transform 和 lightweight 清单均未包含它们。正式封包必须提供真实依赖，禁止从主机源码补加载。

1. BDD/RED：从实际 STANDARD 候选包的独立进程按清单闭包导入这两个模块，原构造应因未声明模块失败。
2. GREEN：仅增加明确的两个模块到现有正式构造与 lightweight 映射；相同入口通过，逐字节核成员来源。
3. REGRESSION：既有候选的缺件、摘要漂移、未声明导入、预加载及清单漂移拒绝保持；两种引擎清单均核真实模块来源。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。继续使用封包清单限定导入，不允许源码目录兜底。
- 是否从根因和长期维护角度解决：是。同步两个正式构造的声明依赖，并由真实候选导入测试固定。
- 是否存在临时补丁或绕过：否。只补实际已存在且已验证的模块，不复制运行目录或改历史包。

## 经验门禁

- Trigger：真实恢复入口新增 lazy import。
- Preflight check：先核实际 controller、source、两种 builder 的调用及成员集合；候选明确 candidateOnly，不作可安装发布包。
- Blocker：成员缺失、摘要或实际加载路径不符、外部源码参与加载即停止。
- Verification：真实独立进程、固定候选清单、原生退出码、RED/GREEN 及相邻拒绝用例；必要测试完整记录。
- Forbidden action：不从主机源码兜底、不改变旧 validator 或预算、不以此测试宣称三服已安装或业务恢复成功。
- Evidence：本任务 execution-log、候选导入测试及 PRIVATE 原始日志。

## BDD

- Given 当前 controller/source 的两个真实输入重建依赖；When 新进程在正式候选的清单导入闭包内导入；Then 两模块必须来自候选 common 路径，字节摘要与清单及冻结源码一致。
- Given 未声明、缺失、篡改或提前从外部加载的模块；When 使用同一导入闭包；Then 原拒绝条件保持，不从工作源码补齐。
