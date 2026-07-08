# 20260708 DCC 识别修复发布测试服

## 任务目标

将 IntRuoyi 后端已验证的 DCC 产品名称/基础信息识别非 Codex 修复发布到测试服务器，并用测试服真实运行态确认非 Codex 阻塞清零。

## 里程碑

- [ ] M1 创建干净发布 worktree，固定后端修复提交与前端发布提交。
- [ ] M2 将维护控制台发布配置切到临时发布 worktree 并重启验证。
- [ ] M3 通过 code-only build-release 构建发布包，确认 manifest dirty=false。
- [ ] M4 部署测试服并确认后端镜像包含修复版本。
- [ ] M5 测试服真实运行态审计：active claim=0、running task=0、无新增非 Codex 失败。
- [ ] M6 恢复维护控制台主配置并清理临时 worktree。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，仅发布已提交并回归通过的正式修复。
- 是否存在临时补丁或绕过：否。

## 预期验证

- 发布包 manifest 指向后端提交 `730072c720186579e8dd9a0b0e160eede0ac9699`，dirty=false。
- 测试服后端健康检查 HTTP 200。
- 测试服数据库审计 active claim=0、running task=0。
- 测试服失败分组中没有本次发布后的新增非 Codex 失败。

## 当前状态

- in_progress
