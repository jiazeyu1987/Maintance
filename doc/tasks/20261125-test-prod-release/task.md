# 当前系统测试与正式发布
## Current Status
completed
## 目标与范围
发布当前已提交系统到测试58与正式57；不补业务数据，不操作59。前序20261124正式发布已completed。
## 里程碑
1. 核实源码、工具、远端版本和锁。
2. 新建专用临时worktree，固定提交构建并发布测试服。
3. 同包验收后晋级正式，验证并清理自有worktree。
## 预期验证
operation、manifest、IMAGE_TAG、实际镜像、UP、200、真实页面和打印助手；业务未验证项单独记录。
## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，沿正式发布链。
- 是否存在临时补丁或绕过：否。
## 经验门禁
- Trigger：构建、发布、真实页面验证及worktree清理。
- Preflight check：核server-access、release-backup-restore、login-access、release-agent-checklist、worktree-memory；固定提交、任务锁、恢复依据、同包身份。
- Blocker：身份不一致、并发发布、契约失败或必要验收缺失。
- Verification：同tag三阶段契约与运行态、真实页面、清理回执。
- Forbidden action：不混入脏文件、不补业务数据、不伪造验收、不删其他任务资源。
- Evidence：execution-log.md及私密脱敏回执。

## 里程碑结果
1. 完成：7890代理同步IntRuoyi；应用发布提交462d6647fc484ef4d3433a5a640015c9559c37db，维护提交5b341d9a9fd68d79d75830dac1df705e8c016b0e。
2. 完成：版本2026-11-25-10-22-04构建成功，测试58发布、实际运行态及真实页面通过。
3. 完成：正式57同包晋级、开放、实际运行态及真实页面通过；本次全部临时worktree核验并删除。

## 工作区与验证
维护工作区C:/SpugHandoff/release/test-prod-20261125；两次失败构建工作区为build/2026-11-25-08-59-37与build/2026-11-25-09-59-57，失败已由正式提交修复并在新构建验证；最终build/2026-11-25-10-22-04已自动删除。均未产生新提交，无需融合。
构建命令actions.py action build-release；目标发布沿publish-test、mark-tested、promote-prod、accept-prod；验证命令menu-page-check.cjs、print-page-check.cjs、final-runtime.py及正式运行态/契约读取。详细结果见release-report.md、release-result.json与execution-log.md。

## 剩余事项
自有工作区全部删除，清理回执均passed且无新提交；控制台PID21804保持原稳定source路径。没有当前发布阻塞。全业务入单与实际打印未验证，未补业务数据。59不在本次范围。
