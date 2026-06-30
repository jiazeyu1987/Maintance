# Development Plan：DCC 短编码文件名直连识别硬化

## Milestones

### M1. 建立失败样例与阈值基线

- 在 `DccControlledFileProjectCodeRecognitionServiceTest` 中新增短编码误命中失败用例。
- 明确当前文件名直连的规则断点：
  - 纯子串命中
  - 最长唯一编码优先
  - 命中后跳过内容读取和 Codex 调用
- 如阈值存在争议，先只读统计启用编码长度分布，再冻结低置信度集合。

### M2. 实现高置信度直连规则

- 在 `DccControlledFileProjectCodeRecognitionServiceImpl` 中把文件名命中逻辑改为边界感知匹配。
- 为低置信度短编码增加显式拦截，不允许仅凭文件名直连。
- 保留“高置信度长编码唯一命中 -> 直接回写”的快捷路径。

### M3. 回归与联动验证

- 跑 DCC 模块定向单测与 Codex CLI 客户端回归。
- 记录与第二任务的联动边界：短编码不再误命中后，低置信度文件名场景应交给内容识别任务验证。

## Implementation Steps

1. 在 `DccControlledFileProjectCodeRecognitionServiceTest` 先补四类 RED 用例：
   - 短编码作为普通长 token 子串时不应直连
   - 两位短编码作为独立片段时仍不应直连
   - 长编码边界清晰时仍应直连
   - 同长度多命中时不得直连
2. 在 `DccControlledFileProjectCodeRecognitionServiceImpl` 提取“规范化文件名 + 边界检查 + 低置信度阈值”逻辑。
3. 保持现有“直连失败 -> 读取内容 -> 调用 Codex CLI”的主流程不变，只修改进入直连分支的门槛。
4. 完成后执行模块回归，确认不会破坏既有长编码快捷识别。

## Files and Modules

- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-dcc\src\main\java\cn\iocoder\yudao\module\dcc\service\file\DccControlledFileProjectCodeRecognitionServiceImpl.java`
- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-dcc\src\test\java\cn\iocoder\yudao\module\dcc\service\file\DccControlledFileProjectCodeRecognitionServiceTest.java`

## Verification Gates

- Gate 1：新增 RED 用例先失败，证明风险可复现。
- Gate 2：实现后定向单测通过。
- Gate 3：`DccProjectCodeCodexCliClientImplTest` 与 DCC 相关回归一起通过，证明未破坏内容识别调用面。
- Gate 4：若进入测试服联调，必须在第二任务跑通后再验证低置信度路径。

## Rollback or Stop Conditions

- 若规则收紧后会把既有高价值长编码快捷路径一并打掉，则暂停实现并先补更多真实样本。
- 若实现方案需要引入新的 fallback、静默降级或“猜测即回写”，直接停止。
- 若最终验证仍依赖测试服内容识别，但第二任务未完成，不把本任务误报为“线上已验证通过”。
