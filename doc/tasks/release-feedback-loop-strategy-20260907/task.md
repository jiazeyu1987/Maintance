# 发布失败反馈闭环长期方案

## Task Goal

针对“本地打包成功、发布到服务器后才发现错误、修复后反复完整打包”的长期问题，形成可执行的发布反馈前移、环境一致性、制品晋级和构建加速方案。本任务只做分析与建议，不修改发布实现，不执行构建或服务器操作。

## Milestones

- [completed] M1：复核前序安装包审查结论和适用 CI/CD 门禁。
- [completed] M2：区分可在打包前发现、必须在目标环境验证、必须重打包的故障类型。
- [completed] M3：形成分阶段长期方案、目标流程和衡量指标。
- [completed] M4：记录结论并进入任务收尾。

## Expected Verification

- 方案能减少服务器阶段才暴露的错误和无意义完整重打包。
- 保持失败后使用新 releaseTag，不修改或复用已经失败的不可变安装包。
- 同一合格安装包从测试服晋级正式服时不重新构建。
- 明确本项目最优先前移的 target-state、SQL、配置、镜像与容量门禁。

## 经验门禁

- Trigger：本地打包成功但服务器部署失败、反复打包、发布反馈过晚。
- Preflight check：先区分源码/构建错误、包完整性错误、目标环境状态错误和运行时业务错误；能只读获得的目标状态必须在昂贵构建前进入 preflight。
- Blocker：不得通过复用失败包、手工改服务器、跳过迁移/manifest/测试门禁或静默 fallback 缩短时间。
- Verification：记录 preflight 命中率、失败阶段、从失败到反馈耗时、完整构建耗时、缓存命中和同一制品跨环境晋级证据。
- Forbidden action：禁止修改已入库安装包；禁止测试服与正式服重新构建不同制品；禁止用服务器手工修补替代代码化门禁。
- Evidence：前序安装包审查报告、现有发布经验和本任务长期方案。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；以反馈前移、环境契约化和不可变制品晋级解决。
- 是否存在临时补丁或绕过：否。

## Current Status

completed

## Completed Work

- 已确认前序任务 `release-package-script-review-20260907` 状态为 completed。
- 已形成“快速静态预检、目标只读预检、缓存化构建、同构安装演练”四层长期方案。
- 已明确失败包不可修改复用，时间优化来自错误前移和受控缓存。

## Verification Evidence

- 复核现有发布经验、前序脚本审查报告和带计时真实发布报告。
- 实测基线：成功 build-release 840.638 秒，publish-test 290.605 秒；依赖缺失失败及恢复额外消耗 491.808 秒。
- 详细方案见 `verification-report.md`。

## Remaining Blockers

- 无。

## Final Verification

- `git diff --check` 对本任务记录、经验索引、发布经验和请求日志通过，仅有仓库既有 LF/CRLF 提示。
- `task-closeout-cleanup` preview/apply 均通过，保留三份核心任务记录，无删除项、阻塞或警告。
- 本任务未修改发布实现，未执行构建、测试、远程预检或发布。
