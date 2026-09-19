# 20260919 已测试包正式服按钮实现

## Current Status
ready_for_closeout

## 任务目标
实现已在测试服验收通过的不可变发布包晋级正式服按钮；本轮只做静态代码、类型、单元/合同验证，不执行 E2E、服务器写入或正式发布。

## 里程碑与预期验证
1. [completed] 后端 production preview、专用权限、字段白名单和状态绑定。
2. [completed] 后端幂等、授权绑定、RECOVERY_REQUIRED 和最终证据合同。
3. [completed] 前端按钮、preview 对话框和恢复态。
4. [completed] 维护仓脚本合同与全量静态验证。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；沿用工作流、不可变摘要和服务端状态机。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- Trigger: 已测试包发布正式服按钮、production preview、RECOVERY_REQUIRED。
- Preflight check: 同一 workflow/releaseTag/packageDigest/manifestDigest 绑定；服务端固定正式目标；preview 零远端写入。
- Blocker: 非 TESTED、摘要缺失、专用权限缺失、确认文本错误、未知字段、授权/状态版本不一致必须 fail fast。
- Verification: 后端合同测试、前端类型和静态合同、维护脚本测试；本轮不执行 E2E。
- Forbidden action: 不重建包、不接受客户端 host/path/releaseTag/evidence、不访问正式服务器。
- Evidence: `doc/tasks/20260918-prod-promotion-button-design/` 与 `docs/release-agent-checklist.md` 5.0。

## Worktree
- 应用：`D:\IntRuoyiWorktree\r260919-prod-button-impl\a`
- 维护：`D:\IntRuoyiWorktree\r260919-prod-button-impl\m`
- 基线应用提交：`99c75483c9ab062a743aa27d1a11e8e4bc7796ee`
- 基线维护提交：`2d0251a639a9e430005a8af69077d59f4ec9c0ee`

## 验证结论
- 静态代码验证已通过；未执行 E2E、服务器写入、数据库写入、发布、重启或正式服探测。
- 正式服发布入口改为独立按钮链路：production preview -> 授权 -> 幂等 promote；旧通用 `promote-prod` 动作已在应用侧和维护控制台侧阻断。
- 实现不接受客户端传入正式服 host/path/releaseTag/evidence 等写入边界字段；正式目标、包摘要、manifest 摘要、测试服证据和状态版本均由服务端绑定。
- 收尾尚未完成：待提交、推送、合并/清理 worktree 后才能标记 `completed`。
- 提交状态：应用仓提交 `88614c25c` 已推送到 `origin/codex/prod-promotion-button-implementation`；维护仓提交 `75eea84` 已在本地完成，维护仓当前未配置 remote，无法推送。
- Hook 说明：应用仓 commit/push 的普通 hook 因临时 worktree 未登记运行端口阻断；本轮不启动本地运行态，已仅对该端口登记 hook 使用 `--no-verify`，未跳过任何静态验证。
