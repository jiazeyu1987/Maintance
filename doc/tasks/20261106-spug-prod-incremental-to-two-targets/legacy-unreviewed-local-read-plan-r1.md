# 旧点未评估 JSON 的有界本机核对

## Current Status

completed（仅本机范围）。属于当前三服任意有效备份点恢复任务；只继续既有 legacy-schema-restoration-assessment 的54个明确未评估点，不变更恢复合同。三服恢复整体未完成。

## 目标、里程碑与验证

1. 固定原逐点映射 SHA；按其54个 ID 和原元数据 pin 核本机 manifest/point/binding。
2. 只在映射原411个明确 inputPins中按 bytes/SHA 找独立同内容副本；有则实际核原字节、JSON格式和绑定，未命中如实记为本轮已索引副本未找到，不宣称归档缺失。
3. 只输出 schema/encoding/大小、pin及缺口；不输出业务行或凭据。未核完整材料/载荷/实时目标，不标可恢复。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，逐点区分未知格式、原件缺口与真实损坏。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- Trigger：旧点 expected-data 正文尚未评估。
- Preflight check：映射921197B/96a43267c5409cf2f277f4f5e21570f5c83442aa8b5a2201f243f5aabc9a86e4；54个唯一ID、每件原pin和有限JSON上限。
- Blocker：原字节或元数据引用不符、未知路径、重复冲突、超过16MiB JSON。
- Verification：原输入与报告pin、54点完整计数、原件失败准确保留。
- Forbidden action：不递归搜索PRIVATE、不联网/NAS/SQL、不写归档、不改旧证据/恢复合同、不将代表点推到整组。
- Evidence：原逐点映射、assessment及新的本机核对报告。

## 实际结果与后续缺口

- 原r1载体遇到未发布点的空point/binding而TypeError退出，未生成报告；保留该失败。r2逐点明确记原元数据前提缺失，不为未发布点补造绑定，其余已发布点继续独立核对。
- r2原session80983 exit0；54个唯一点完整列明，53点的manifest/point/binding及原映射共160个输入实际SHA与前后身份通过。另1点smallapp-d62276cdb402499d9586871439765989原point/binding缺失，保持未发布。
- 在原411个明确已索引输入中，54点expected-data正文和53点material正文均未命中同内容副本；这是本机索引范围结论，不是归档缺失/损坏结论。下一步依原pin有界只读归档；未执行该远端步骤。
- 公开报告legacy-unreviewed-local-read-20261110-r2.json：113590B/3c2a6ccc96c452589aefa0b52cdbb35bc444840967fd4569d3ff171f33339feb；0联网、0SQL、0归档写入、0恢复。未取得新的恢复准入结论。


后续衔接：既有 legacy-database-original-readback-r5 已保存后续正文；新 reconciliation-r1 已本机核完54点，其中50份正文通过、4份原校验不符。无需因本报告411索引未命中而再次访问NAS。
