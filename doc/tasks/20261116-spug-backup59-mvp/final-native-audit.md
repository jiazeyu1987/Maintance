# 增量恢复原生回执最小审查

## 范围与结论

2026-11-16，仅在备份服务器 .59 只读读取指定操作的小型回执、三个恢复点元数据、配置路径存在性和进程信息；未连接 .57/.58，未读取附件或数据库载荷，未执行恢复、安装、清理或服务器写入。

- 恢复操作：`smallapp-f0c503e401204fd0a2d263937e1d3b13`。
- 目标：`spug-empty59-e4261b44a5f3`。
- 原生 `result.json` 与 `worker-result.json` 均为 `SUCCEEDED`，`failureCode=null`，`actualExitCode=0`；完成时间记录为 `2026-11-15T23:43:35.228567Z`。`child-exit.json` 同样为退出码 0。
- 本记录证明原生执行与释放资源成功；真实页面、业务数据和附件验收由父任务的独立证据记录。

## 实际恢复链

下列顺序直接来自本操作 `result.json.data.orderedChainPins`，并与对应 `point.json` 的 `backupId`、`pointType`、父点 pin 对应。哈希为现有回执的 pin 值，本次没有重新计算载荷哈希。

| 顺序 | 类型 | 备份 ID | point.json 字节数 | point pin SHA-256 |
| --- | --- | --- | ---: | --- |
| 1 | FULL | `smallapp-3c2395ff88bd474e9fc007649565b848` | 6255235 | `cef87f61b74e20aaa196cab005f9637a2a46b1e496f91510d23c2f5287514164` |
| 2 | I1 / INCREMENTAL | `smallapp-20a1bb9b78ac402693289675d16c63dd` | 33746 | `94e9b7e141ff9b3869f3dc7d0a08ebc71c771b2e86c91d040194f80903adbb5f` |
| 3 | I2 / INCREMENTAL | `smallapp-e7b668792c8f4bce945a52f984d3c660` | 42335 | `510109069fda26c8f8a0d6fc264ecbf6f0ed1363422d1fb145a4be691ebee6b2` |

FULL 无父点；I1 父点为上述 FULL；I2 的父点列表依次为上述 FULL、I1，各 pin 一致。

## 准备、保护范围与释放

- 准备操作 `prepare-681e546d-2bd3-45c2-ba15-159ddc5bcadc` 的原生回执为 `INITIALIZED`，dependencies、cleanup、initialize 三阶段均 `SUCCEEDED`，错误码为空，选定恢复点为上述 I2。
- 清理阶段实际成功回执时间为 `2026-11-15T23:05:47.617341+00:00`。配置中的清理目录与 NAS 归档根目录、tools、state、控制认证文件及目标凭据文件的路径祖先交集为空；这些 10 个受保护路径在恢复后全部存在，NAS 的三个既有网络挂载点仍在。
- 这项保护核查是阶段回执、路径边界、路径存在性及挂载状态证据；没有逐文件读取，也不将其表述为保护目录全部内容的完整性复验。
- 恢复暂存清理 `staging-cleanup.json` 为 `SUCCEEDED`，清理本操作 6 个暂存文件，共 18,657,552,710 字节。
- `resource-release.json.reason=VALIDATED_CHILD_SUCCESS`，释放时间 `2026-11-15T23:43:35.677404Z`；共享 `active.json` 已不存在；未发现恢复 worker。控制服务保留运行，未人工删除锁或修改终态。

## 私密证据索引

原始证据仅保存在本机私密目录 `C:/Spug/runtime/private/spug-backup59-mvp-20261116`：

- `final-incremental-metadata.private.json`
- `final-incremental-protection.private.json`

本文件是可提交的脱敏摘要，不包含认证值、业务文件名或数据库内容。
