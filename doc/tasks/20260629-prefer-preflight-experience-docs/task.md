# 20260629 经验文档前置基线固化

## Task Goal

将用户在当前线程确认的长期偏好固化到仓库根 `AGENTS.md`：后续新增经验默认优先写入事前文档入口，只有事后复盘内容才进入 error-prevention 类文档。

## Scope

- `D:\ProjectPackage\Int\IntRuoyiMaintance\AGENTS.md`

## Non-Scope

- 不修改业务代码
- 不调整发布脚本
- 不改动服务器状态

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 当前仓库经验入口应优先承载任务开始即可命中的规则。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是；把线程已确认偏好固化为长期基线
- `是否存在临时补丁或绕过`：否

## Milestones

1. 识别当前线程已确认的长期偏好。`COMPLETED`
2. 检查 `AGENTS.md` 是否存在重复或冲突规则。`COMPLETED`
3. 将基线写入 `AGENTS.md`。`COMPLETED`

## Expected Verification

- `AGENTS.md` 存在该长期基线
- 新基线不与现有规则冲突

## Current Status

COMPLETED：已确认用户批准将“新增经验优先写入事前文档入口，事后复盘才进入 error-prevention 类文档”写入当前仓库 `AGENTS.md`。
