# 单一来源控制组件的候选绑定

## Current Status

local_verified。此模块只提供 BOUND 投影，未安装、未证明运行态，正式 current loader/selector 仍拒绝该 schema；整体任务继续 in_progress。

## 目标与设计约束

为仅更新 .57 来源控制组件提供明确的候选合同，保留已验证 r7 的三个 target、Spug 和旧 I1 原件，避免为自动登记修复重装四个角色。目标分为 BDD/RED、纯绑定实现、相关回归、后续真实激活四阶段；前三项已通过，真实激活尚未实施。

不引入 fallback、吞异常或临时绕过；不把候选当已安装。调用方必须先正式验证 base；本模块再次核对 selection/generation/build/四 controller 原件，实际完整读取两个已 pin 的 STANDARD 包，成员及实际差异必须恰为 Ledger 和 Native 两文件。只替换有效投影的 .57/source，逐角色保留自身 build；最后复核所有已读 pin。

## BDD 与验证

- Given 真实 r7 公开文件和明确的本地候选包，When 纯绑定，Then 只替换 .57/source，三 target、Spug、base 文件与旧 I1 原件保持；输出 installationVerified/runtimeVerified 均为 false。
- Given 错状态/额外字段/错 base/错前驱/错 role/错 source/pid 或第三个实际包文件差异，When 绑定，Then 明确拒绝，不能隐藏在自报 changedFiles 后。
- Given 原 base 投影漂移或将 BOUND 传给正式 loader/selector，Then 拒绝，不授予执行资格。
- RED：既有 `source-control-binding-red-r1.xml` 实际11 FAIL/0 ERROR/0 SKIP，fixture建立后均因缺新模块失败；先前缺 pytest 前置另行保留，不计 RED。
- GREEN：新增11 PASS，native0/13.156s，输入保持，JUnit `73c9f3f8ae1adebbd5e269f61a53e177ceb5c47b2cf20604d80b2b2c87984d43`。
- REGRESSION：既有安装选择器62 PASS，native0/5.125s，输入保持，JUnit `5420966c1dedb662d356066aaa3f5d49cd4bdadeaa1f7b494284eed45623e8be`。

固定 Python、PRIVATE/test-dependencies、禁第三方插件/bytecode、180秒原生期限；完整命令、结果和输入 SHA 位于 PRIVATE/source-control-binding-{green,regression}-r1/native.json。仅真实本地文件/包的合同单元测试，未执行 Docker/HTTP/SSH/业务备份恢复。

## 经验门禁

- Trigger：来源控制组件单独升级，但旧 generation 是四角色共代证明。
- Preflight check：明确已验证 base 与候选状态、原角色文件、逐角色 build 和实际两包全成员差异。
- Blocker：原件漂移、包额外差异、错误身份，或没有真实配置/dropin/进程与其它角色保持证明却要求激活。
- Verification：文件式 RED→GREEN、既有选择器回归；后续安装和真实 Spug 连续增量另验。
- Forbidden action：改原 generation/旧 I1，伪造 ACTIVATED/PID/运行证明，或使 BOUND 自动进入执行准入。
- Evidence：本日志、原 RED XML、两原生 native.json 及主 execution-log。
