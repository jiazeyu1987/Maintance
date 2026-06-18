# 任务: 沉淀发布验证通用经验

## 任务目标

- 将“本机能跑到服务器不行”的通用预防经验沉淀到维护仓长期经验文档。
- 经验必须覆盖功能修改、构建发布包和部署服务器三个阶段，避免只针对某一个功能。

## 上一任务检查

- 上一任务：`doc/tasks/20260618-maintenance-persist-scheduler-smoke-release/`。
- 状态：`completed`。
- 处理：上一任务已完成，本任务可以开始。

## 授权范围

- 用户需求：“将上面123456补充到经验或者基线里”。
- 允许：更新维护仓已有经验文档、短记忆和任务记录。
- 禁止：创建新的经验文档；修改发布脚本；执行服务器写入、构建发布包或部署。

## 经验门禁

- 来源：`docs/experience-index.md`。
- 命中文档：
  - `docs/release-build-preflight-lessons.md`：适合作为“源码验证、发布包验证、目标环境运行态验证”的长期发布经验归宿。
  - `docs/agent-memory/project-error-prevention.md`：适合补充高频短记忆，提醒后续任务不要只看本机源码或健康检查。
- 适用强制门禁：
  - 只更新已有经验文档，不新建长期经验文档。
  - 经验必须写成通用规则，不绑定智能排产单一功能。
  - 本任务不执行远端写入或发布。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，将经验放入发布经验与错误预防文档，后续任务开始时可被索引命中。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 发布验证经验可复用 -> Given 后续任务涉及功能修改、构建发布包或部署 When Agent 读取经验索引和发布经验文档 Then 能看到唯一发布源头、配置代码化、发布产物验证、环境差异检查、目标运行态验证、故障补门禁六条通用规则。`

## 里程碑

- [x] M1 建立任务文档并确认上一任务完成。
- [x] M2 RED：确认经验文档尚未包含通用六条规则。
- [x] M3 GREEN：更新已有经验文档和短记忆。
- [x] M4 验证、cleanup 预览和提交。

## 预期验证

- `rg -n "唯一发布源头|配置必须代码化|验证发布产物|环境差异|目标环境真实运行态|故障补成门禁" docs\release-build-preflight-lessons.md docs\agent-memory\project-error-prevention.md`
- `git diff --check` 限定本任务文件通过。

## 当前状态

completed

## Current Status

completed

## Cleanup Keep

- `doc/tasks/20260618-release-validation-experience-baseline/task.md`
- `doc/tasks/20260618-release-validation-experience-baseline/execution-log.md`
