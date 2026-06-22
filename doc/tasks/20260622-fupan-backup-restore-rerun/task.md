# 任务：复盘备份服再次备份恢复演练

## 任务目标

基于 `20260622-backup-server-backup-restore-rerun` 的任务文档、执行日志、请求日志和现有项目短记忆，提炼可长期复用的项目级防错规则，并更新 `docs/agent-memory/project-error-prevention.md`。不把一次性备份点、日志路径或页面步骤提升为长期规则。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-backup-server-backup-restore-rerun\task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成再次备份恢复演练，本任务只做复盘沉淀。

## 用户要求与执行边界

- 用户要求：`$fupan`
- 当前任务授权：
  - 允许读取本地任务文档、执行日志、请求日志和项目短记忆。
  - 允许更新维护仓项目短记忆文件。
- 禁止范围：
  - 不修改服务器、数据库、备份点或运行环境。
  - 不把一次性任务细节写入 `AGENTS.md`。
  - 不编造历史共识；只从已读证据提炼规则。

## 技能与证据

- 使用技能：`fupan`。
- 已读取：
  - `C:\Users\BJB110\.codex\skills\fupan\SKILL.md`
  - `C:\Users\BJB110\.codex\skills\fupan\references\project-memory-template.md`
  - `doc/tasks/20260622-backup-server-backup-restore-rerun/task.md`
  - `doc/tasks/20260622-backup-server-backup-restore-rerun/execution-log.md`
  - `docs/request-command-log.md`
  - `docs/agent-memory/project-error-prevention.md`

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。只沉淀项目级通用防错规则。
- `是否存在临时补丁或绕过`：否。

## 候选经验

- 候选 1：PowerShell 管道传 Linux 脚本可能引入 BOM、CRLF 或引号污染；备份/恢复 preflight 应使用 UTF-8 无 BOM、LF 行尾临时脚本或已验证脚本入口。
- 候选 2：备份恢复不能只看脚本成功；必须同时校验 manifest、DCC manifest、对象 inventory、演练证据和恢复后健康。
- 候选 3：对象回放可能很久；应依据日志、临时容器、磁盘空间和最终报告判断，不把长时间运行直接等同失败。

## 采纳判断

- 采纳候选 1，并与现有“备份服路径固定”规则合并，形成更完整的备份/恢复 preflight 规则。
- 候选 2 已由现有“部署验证不能只看健康”“测试通过前确认 AVAILABLE 恢复点”等规则覆盖，本次不重复新增。
- 候选 3 属于操作判断经验，适合保留在任务日志和请求日志，不提升到短记忆。

## 里程碑

1. 建立复盘任务记录。`DONE`
2. 读取技能、模板、任务证据和现有短记忆。`DONE`
3. 提炼并筛选项目级候选经验。`DONE`
4. 更新项目短记忆并控制总长度。`DONE`
5. 记录收尾、验证和提交。`IN_PROGRESS`

## 预期验证

- 项目短记忆总长度不超过默认 800 字符。
- 新增或合并后的经验是项目级通用规则，不是单次任务细节。
- 不修改 `AGENTS.md`，除非用户另行明确批准。

## 更新结果

- 已更新：`docs/agent-memory/project-error-prevention.md`
- 当前长度：`760` 字符，未超过默认 800 字符上限。
- 新增规则：`备份/恢复 preflight 用 UTF-8无BOM、LF 脚本；核数据盘/备份根/对象存储/IMAGE_TAG；证据: 20260622-backup-rerun`
- 自动压缩取舍：为保持 800 字符上限，更新脚本移除了最早的旧条目 `提交前跑 TDD 钩子...`；该规则仍由仓库 AGENTS 与任务流程约束覆盖，本次不重复保留在短记忆里。
- 未提升到 `AGENTS.md`：本次规则适合项目短记忆；如要写入 `AGENTS.md`，需用户另行明确批准。

## 当前状态

COMPLETED：已完成备份恢复复盘并更新项目短记忆。

## Current Status

completed

## Cleanup Keep

- `doc/tasks/20260622-fupan-backup-restore-rerun/candidate-error-evidence.md`
