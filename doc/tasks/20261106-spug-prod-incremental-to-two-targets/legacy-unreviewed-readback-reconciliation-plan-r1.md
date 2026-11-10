# 旧点正文读回证据的本机衔接

## Current Status

completed（仅本机衔接）。属于既有三服恢复任务，仅核对已保存原件，不重新访问 NAS，不执行 SQL 或恢复。

## 目标、里程碑及预期验证

1. 固定旧 54 点映射及本机索引核对报告，关联已经完成的 legacy-database-original-readback-r5 与其原私密证据。
2. 对 54 点逐项复核原读回副本、原 bytes/SHA 与 material 绑定；保留失败和未发布状态。先前“411 个索引中未找到”仅为该索引范围事实，不扩大为正文未采集。
3. 输出逐点格式、绑定和缺口，不输出业务正文或凭据；未核完整恢复链、载荷及目标，不标记可恢复。

## 经验门禁

- Trigger：旧 54 点的原映射尚未衔接后续已完成的正文读回证据。
- Preflight check：冻结原映射 SHA、readback-r5 与原私密证据 pin；只读其明确列出的本机副本，不递归扫描。
- Blocker：原件 pin 不符、重复点或读取关系不唯一、格式未知；失败逐点保留，不改旧原件。
- Verification：本机副本完整 SHA/前后身份、54 点完整计数、格式和绑定分类、零网络/SQL/恢复。
- Forbidden action：不重新读取 NAS，不修改归档、旧报告或校验值，不将解析成功当成来源快照证明或恢复成功。
- Evidence：legacy-database-original-readback-r5.json、legacy-database-original-parent-verification-r1.json、legacy-unreviewed-local-read-20261110-r2.json 及新衔接报告。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，保留原索引范围并连接现有后续证据，避免重复 NAS 读取。
- 是否存在临时补丁或绕过：否。


## 实际终态

- 原 session60149 exit0；54点完整衔接：50份正文完整 bytes/SHA 实读通过且均为 typed observation，53份材料实读且原 expectedDataPin 与声明完全绑定，4份正文原校验不符，继续禁用。
- 已逐件复核原本机副本和前后身份；0网络请求、0SQL、0归档写入、0恢复。解析通过不代表完整恢复准入。
- 报告 legacy-unreviewed-readback-reconciliation-20261110-r1.json：149203 B / SHA256 fa1c1f745630ef45ab55a9f7f31e50c9ed7ad092fa71b761bd2bc1e16d63d888。
