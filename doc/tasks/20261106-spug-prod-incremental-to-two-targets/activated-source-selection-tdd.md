# 实际来源升级的验收识别

## Current Status

implementation_verified；仍未提交I2，也未完成整体三服恢复目标。

来源组件已单独安装6968b58，三个目标保持b5fa4c5、Spug保持5651efc。旧单提交选择不能表达这个实际状态。新增显式v2来源选择，先由原正式v4 loader完整验证基座，再核三代真实激活的完整原件、canonical远端receipt pin、包/配置/dropin、只重载来源及业务保持。安装记录不代表实时健康，runtimeVerified保持false。页面验收通过显式source-activation/v3接入；原入口语义保持。

## BDD 与 TDD

- Given原基座与三代真实激活；When按新协议读取；Then只替换57/source，各target仍引用原build，Spug保持，原I1回执不重绑定。
- Given缺代/乱序/重复、被改回执、错build/role/epoch、额外写入或业务变化；When读取；Then拒绝。纯解析负向用例不作为模拟服务器成功证据。
- RED：activated解析器缺失，6方法/28错误；最小实现后首次完整运行5方法通过、1负向子项未形成实际变化（MainPID原值就是0）。改为LimitNOFILE真实差异后同6方法及所有子项PASS，90.844秒/native0。产品断言未放宽。
- 正式原loader+新协议实际完整load PASS，176.985秒/1651输入；见activated-source-selection-verification-r1.json。来源6968b58、目标b5fa4c5，runtimeVerified=false。
- RED：页面Python context缺失，5方法/10错误；GREEN同5方法PASS，5.424秒/native0。
- RED：页面v3正向被旧协议拒绝，Node10PASS/1FAIL；GREEN新11场景和原有协议合计48PASS/0skip；历史source-custody协议另23PASS/0skip。
- REGRESSION：固定pytest8.3.5私有运行时，原Python构建根、Git输入、BOUND选择及来源升级范围合同80PASS/0skip，150.73秒/native0。私有依赖未加入仓库。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否。旧协议失败不会切换新协议，BOUND仍被拒绝；新协议须显式指定。
- 是否从根因和长期维护角度解决：是。每个控制角色持有自身构建身份，新来源不能冒充全部目标已升级。
- 是否存在临时补丁或绕过：否。所有原安装、旧回执、原结果及坏点校验保持。

## 经验门禁

Trigger：来源独立升级；Preflight check：原基座、完整激活链和每角色构建；Blocker：任何原件/链/角色漂移或BOUND冒充；Verification：实际全证据load、正负合同及旧协议回归；Forbidden action：重写原I1、跳过实时健康或扩权服务器；Evidence：上述公开摘要及PRIVATE原件。真实E2E/备份仍须另记experience-preflight PASS并按真实页面操作。
