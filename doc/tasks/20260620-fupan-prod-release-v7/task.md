# 任务：复盘正式发布 v7 的长期门禁

## 任务目标

基于本次 `release-20260620-current-head-prod-target-v7` 的真实发布任务证据，提炼可长期复用的项目级发布/验证规则，更新维护仓短记忆文件；不把一次性模块细节、页面步骤或纯事故现场描述误写成长期规则。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-prod-release-current-latest\task.md`
- 状态：`COMPLETED`
- 处理：正式发布任务已完成并有完整证据，可作为本次复盘的主证据源。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 项目记忆只保留跨任务稳定规则，不写页面点击步骤、单模块排障细节或一次性事故现场。
  - 证据不足或只证明症状、不证明纠正动作时，不得强行提升为长期记忆。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。只提炼跨任务稳定的发布门禁，不用短期事故覆盖长期基线。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 复盘只接纳项目级稳定规则 -> Given 本次正式发布任务存在多轮阻塞与修复证据 / When 提炼长期记忆 / Then 只保留跨任务稳定、能指导未来发布任务的规则，任务级细节留在执行日志。`

## 里程碑

- [x] 建立复盘任务文档并确认主证据源。
- [x] 读取本次正式发布证据与现有短记忆，筛选候选规则。
- [x] 更新短记忆并记录接受/拒绝结论。

## 当前状态

COMPLETED：已从 `20260620-prod-release-current-latest` 的正式发布证据中提炼 1 条新的项目级发布门禁，并合并压缩现有短记忆到 783 字符；未把任务级页面/UI 细节或单次事故字段说明提升为长期规则。

## 最终结论

- 接纳：`正式环境只读 preflight + 版本一致性` 作为项目级发布门禁，已合并进 `docs/agent-memory/project-error-prevention.md`
- 合并压缩：把原先重复的发布验证/预检表述压缩为 5 条项目级规则，保持在技能默认 800 字符内
- 拒绝/延后：`ProdDryRunEvidencePath`、`writeActions=[]`、具体 migrationId、具体角色/菜单/页面细节，仅保留在任务证据，不提升到长期记忆
