# 154成员控制修复的最小安装延续

## Goal / Current Status
in_progress。b10三服已正式安装154成员；直接阻断修复仅control/recovery_control_smallapp_native.py。需要在独立新engine与独立控制配置中安装已提交正式包，保留b10和全部历史原件。当前task successor只支持153→153或153→154，需要最小支持154→154精确单成员升级，避免复制整套安装器。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。固定154→154、成员集合全同、仅明确单个控制成员变化，所有旧协议和旧pin保持。
- 是否从根因和长期维护角度解决：是。把旧payload数量作为已认证输入用于本来依赖旧包数量的校验，不扩大允许的差异集合。
- 是否存在临时补丁或绕过：否。不修改旧冻结对象，不改变当前程序/target身份，不绕过正式安装验收。

## 经验门禁
Trigger：必要新控制修复安装到已154成员目标。Preflight check：完整原b10安装链、旧正式包、精确单成员差异、新提交与新worktree。Blocker：任何其它payload差异、成员增删、原件或身份漂移。Verification：先BDD RED、新测试与原153升级回归，实际STAGE/PREPARE/ACTIVATE及UI新selection。Forbidden action：旧原件改写、任意profile、复制大验证器、业务恢复假成功。Evidence：原b10完整1716pin结果和released-main-failure-plan.md。

## BDD / Milestones
Given 正式154成员前代与仅native控制状态收口变化；When 建立并验收目标后继；Then 接受严格同集合154→154并保全前代全部pins。
Given 任何其它成员变化、增删、错误数量或未验证前代；When 建立后继；Then 拒绝。
按AGENTS重构规则由子Agent执行最小验收器重构，先RED再GREEN/REGRESSION；父任务负责必要产品修复、实际正式包与服务器操作。本轮不复制旧UI载体，不增加任意版本平台；全部原153合同回归保持。

## UI 验收桥接范围

Given 已完整验证的 b10 安装以前存在一份仅57已激活的 partial 前代；When 真实 UI 验收新的完整后继；Then 保留 partial 的原始身份和57/58/59分工，并验证其基线紧邻原 v3 完整安装，不把 partial 冒充完整祖先或当前直接前代。错误基线、主机分工、schema 或重复完整祖先必须拒绝。

仅修改现有 UI 验收桥的严格 ancestry 遍历；不增加页面控件、不改变唯一业务 POST 与提交前落盘合同。原 UI 完整冻结为私有 before-released-native 原件，旧报告仍绑定旧字节。单元桥接夹具只证明协议遍历；实际安装与真实页面另验收。Python 测试运行时由显式 SPUG_TEST_PYTHON 提供，避免把当前电脑路径写入可提交测试。
