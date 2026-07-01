# 20260702 自动发布经验沉淀

## 任务目标

让运行控制台在构建/发布 operation 完成后自动生成发布前置经验候选材料，减少后续人工复盘成本。

## 经验门禁

- 命中 `docs/experience-index.md` 的构建发布经验路由。
- 本任务涉及发布自动化能力变更，但不执行真实服务器发布。
- 生产代码变更必须先有 BDD/TDD 证据，失败时不得 mock 成功或静默跳过。
- 自动沉淀只生成候选经验，不直接篡改正式经验文档；正式经验仍需通过任务收口确认后写入。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；生成候选失败只记录到 operation log，不改变 operation 成败结论。
- 是否从根因和长期维护角度解决：是；在 operation 完成点统一生成可追溯候选经验。
- 是否存在临时补丁或绕过：否。

## BDD 场景

BDD: 发布 operation 完成后自动生成经验候选 -> Given build-release/publish-test operation 结束 When operation 状态更新为 SUCCESS 或 FAILED Then 运行控制台写入 release-experience-candidates.md，包含 action、environment、releaseTag、status、summary 和前置经验建议。

BDD: 非发布 operation 不生成候选 -> Given restart 等非发布动作结束 When operation 状态更新 Then 不写入发布经验候选。

## 里程碑

1. 建立任务记录与 RED 测试。`COMPLETED`
2. 实现 operation 完成后的经验候选自动生成。`COMPLETED`
3. 运行定向测试并记录 GREEN 证据。`COMPLETED`
4. 更新经验/清单文档说明自动化边界。`COMPLETED`

## 预期验证

- Maven 定向测试覆盖发布 operation 成功/失败与非发布动作边界。
- 生成的候选经验文件使用 UTF-8，内容可直接进入后续任务复盘。

## 当前状态

COMPLETED：运行控制台已在发布类 operation 完成时自动生成 `release-experience-candidates.md`；非发布动作不生成候选；候选写入失败会 fail fast。定向 Maven 测试已通过，经验文档和执行清单已记录自动化边界。
