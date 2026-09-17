# 指定 worktree 发布按钮静态复查

## Current Status
completed

## 任务目标
按用户指定的应用 worktree `D:/IntRuoyiWorktree/r260911-release-button/a`（提交 548c5b151）与维护 worktree `D:/ProjectPackage/Int/IntRuoyiWorktrees/r260911-release-button/m`（提交 0e0869）静态检查发布按钮的实际调用链、参数、状态、错误传播与权限边界。

## 里程碑与预期验证
1. [completed] 指定短提交均解析为实际 HEAD，相关生产与测试源码无未提交差异；存在的脏文档不参与产品结论。
2. [completed] 上轮 R1-R5 均已有实质修复，本轮确认 S1-S4：恢复列表异常、取消隔离锁释放、验收失败分支缺失、验收人错误归属。
3. [completed] 报告已保存，当前任务 preview/apply 通过且零删除；审查结论仍 FAIL，不放行产品。
4. [completed] 已复查应用 3f059bec3 / 维护 ade217a，首轮 S1-S4 已修，新增确认 T1/T2/T3（2 项 P1、1 项 P2）；最新结论位于报告顶部。
5. [completed] 18:21 当前磁盘复查：T1-T3已修；确认U1终止未确认却改失败/放锁、U2已验证标记仅查JSON可解析（1项P1/1项P2）。118个相关文件哈希前后稳定。
6. [completed] 用户明确调整重点；已由同任务链20260917-release-failure-cause-analysis核对真实日志，确认当前构建重启中断且恢复未收束。旧静态展示/审计问题不作为本轮发布失败根因。

## 经验门禁
- 当前对话上一审查任务已 completed；不接管或改动其他发布任务。
- 经验索引命中 app-release/ReleaseWorkflow 门禁：新按钮必须与正式执行器同一参数合同；不能用旧版本结论、单元测试数量或命令成功替代当前代码证据。
- 明确 UTF-8 编码与退出码；不读取秘密配置、不输出凭据。
- 本轮只做静态源码审查，不运行构建、产品测试、发布、E2E 或服务器请求。
- 应用仓要求当轮明确授权才启用子 Agent；本轮由主任务直接审查，不启用旧子 Agent。
- 仅修改维护主工作区内当前任务记录及请求日志增量，不修改两个被审 worktree。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；检查完整调用链与异常恢复条件。
- 是否存在临时补丁或绕过：否。

## Verification Evidence
- 09:08 最新复查：应用 3f059bec334d6b5ecec6dd7b413c379315c36415、维护 ade217a07f0ea9c0ecf36ae7f484096b893c7c50，相关源码无未提交差异；以下旧 HEAD 为历史。
- 应用 HEAD=548c5b151693c6ebb1ac3b1201364c561673a2a2，维护 HEAD=0e08698ab0205b3643ea23bac1df6f5a058243c1；开始/结束一致。
- 静态问题 3 项 P1、1 项 P2，详见 verification-report.md；未运行产品测试或发布。
- 经验沉淀复核：本会话既有发布合同/隔离/真实证据门禁覆盖通用原则，当前缺陷按指定版本留在任务报告，不新增长期经验文件。

## Cleanup Keep
- doc/tasks/20260917-release-button-static-review/task-state.json
