# 任务：复盘页面发布全链路 v6 经验

## 任务目标

基于 `20260620-frontend-release-full-flow` 的任务文档、执行日志、请求记录和现有项目短记忆，提炼可复用的项目级防错经验，更新 `docs/agent-memory/project-error-prevention.md`。只沉淀跨任务通用规则，不记录一次性页面点击细节、operation ID 或临时排障步骤。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-frontend-release-full-flow\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成真实页面 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服` 全链路，可作为本次复盘证据来源。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 告警：本任务不执行服务器写入、发布、恢复或真实 E2E，只做本地文档与项目短记忆更新。
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 复盘只能使用任务文档、执行日志、请求记录和既有项目记忆等可读证据，不从印象编造“历史共识”。
  - 发布类经验只保留项目级通用规则，如 manifest、operation、远端运行态、多环境迁移契约、发布锁和受保护数据边界。
  - 不把具体页面控件、弹窗按钮、单次 operation ID、release tag 或临时排障动作写入长期短记忆。
  - 项目短记忆默认保持 800 字以内；若溢出，保留更新且通用的条目，合并或移除旧的等价条目。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。只把反复适用的发布门禁沉淀到项目短记忆，详细证据留在任务文档。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 证据驱动复盘 -> Given 发布全链路任务已有 task/execution-log/request-log 证据 / When 执行复盘 / Then 只把由证据支持的项目级经验写入短记忆。`
- `BDD: 拒绝一次性细节 -> Given 候选证据包含具体按钮、operation ID、release tag 或单次报错 / When 选择长期规则 / Then 这些细节只留在任务文档，不进入项目短记忆。`

## 里程碑

1. 建立复盘任务文档并确认上一任务已完成。`DONE`
2. 读取 `$fupan` 技能、经验索引、命中经验文档和既有短记忆。`DONE`
3. 采集并阅读候选证据，筛选项目级可复用经验。`DONE`
4. 更新项目短记忆并校验 800 字约束。`DONE`
5. 记录接受/拒绝项、运行收尾预览并提交本任务改动。`DONE`

## 预期验证

- 候选证据文件已生成并被读取。
- `docs/agent-memory/project-error-prevention.md` 保持紧凑，整体不超过 800 字。
- `execution-log.md` 记录接受、合并、拒绝的经验项。
- `git diff --check` 通过。
- 任务收尾前运行 `task-closeout-cleanup` 预览。

## Cleanup Keep

- `doc/tasks/20260621-fupan-frontend-release-full-flow-v6/candidate-error-evidence.md`

## 当前状态

COMPLETED：已基于真实页面发布全链路任务证据更新项目短记忆，接受 2 条项目级规则，拒绝页面/operation/tag 等一次性细节；短记忆当前 `750` 字符，`git diff --check` 与 `task-closeout-cleanup` 预览均通过。
