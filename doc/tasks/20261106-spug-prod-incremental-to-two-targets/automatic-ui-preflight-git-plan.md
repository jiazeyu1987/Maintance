# 自动增量 UI 预检的部署输入合同

## Current Status
ready_for_closeout — TASK helper/测试/说明已完成并通过20项真实 Git/实际请求合同测试，交根任务收口。未调用服务器，未改生产源码或原回执。

## 目标与里程碑
- [x] 查明预检把仓库 HEAD 与已安装版本误耦合的边界，定义精确部署输入。
- [x] 使用真实临时 Git 仓库编写无关提交允许、相关变更拒绝的 BDD / RED 测试。
- [x] 最小修复并 GREEN / REGRESSION；补独立源健康报告与收尾合同。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。已安装提交不存在、不是 HEAD 祖先、部署输入变化或组件证明不符均拒绝。
- 是否从根因和长期维护角度解决：是。仓库开发状态与精确安装的组件状态分别验证，按部署输入边界判断兼容性。
- 是否存在临时补丁或绕过：否。无关 release-center 提交可继续，但不放宽 active/source/capacity/物理锁/当前 plan 和实际文件 SHA。

## 经验门禁
- Trigger：同仓无关提交使旧版本实际安装的自动增量 UI 预检误拒绝。
- Preflight check：读取实际安装/build/Spug 组件提交；核 commit 存在、HEAD 祖先及自动增量部署输入差异，保持安装文件 SHA 校验。
- Blocker：祖先关系或任一部署输入不一致、原现场准入失败，均不能通过。
- Verification：真实临时 Git 提交验证无关目录允许、相关提交及未提交变更拒绝；原 helper 的现场门禁保留。
- Forbidden action：不得通过改安装回执、忽略相关代码变化或服务器写入凑 PASS。
- Evidence：本计划、任务 execution-log.md、任务级真实 Git 单测。

## BDD
- Given 已安装提交仍存在且是 HEAD 祖先，之后仅 release-center 提交变化，When 预检部署输入，Then 允许且记录各自提交。
- Given 已安装提交后自动增量部署输入已修改（已提交或工作区变化），When 预检，Then 明确拒绝。
- Given 已安装提交不存在或不属于当前 HEAD 历史，When 预检，Then 拒绝。
- Given 独立审计报告要求 sourceIndependentHealthCheckRequired，When 收尾，Then 必须绑定指定操作后的独立源健康报告，不能以 sourceRestoration 替代。

## 验证
- RED：新增 test_automatic_ui_preflight_git.py，原 helper 尚无 verify_deployment_inputs，ImportError 失败。
- GREEN：19项真实 Git 历史/工作树测试 PASS（57.43秒）；补实际 FULL373 submission identity 合同后20项全部 PASS（84.41秒，零 skip）。
- REGRESSION：实际本机 HEAD=b5c8817de2b4cc5efdad566f0fb65fdabefcb8d8，安装提交0d445782dc06995b3c84b1b45146ea4b75483f92仍为祖先，部署输入不变、已安装 Spug 实际文件 SHA 全部匹配；未调用服务器。
- 语法、UTF-8 与针对本项文件的 diff whitespace 检查 PASS。active/source/capacity/锁/当前plan现场门禁未放宽。
