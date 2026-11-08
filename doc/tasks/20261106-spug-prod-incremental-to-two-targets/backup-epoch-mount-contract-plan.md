# 恢复周期与既有挂载物理路径合同

## Current Status
completed — 根任务已完成 0d44578 正式提交、重新构建与 57 当前来源/MAIN 安装；实际 epoch/目标语义健康与计划门禁通过。此前 3019c2e staged 引擎未热改，历史 targets 保持。后续进入新 FULL 与连续增量验收。

## 目标与里程碑
- [x] 只读定位历史 RW 挂载别名及其真实用途、物理归属。
- [x] 写真实文件系统边界 BDD 与失败测试，记录 RED。
- [x] 实现正式存储合同校验：合法非数据挂载可验证；周期、锁、数据路径别名仍拒绝；所有可写物理路径仍进行重叠检查。
- [x] 运行 GREEN 与回归，将封包和现场候选复验交回根任务。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。不能捕获 PATH_ALIAS_REJECTED 后跳过挂载或仅按字符串猜安全。
- 是否从根因和长期维护角度解决：是。区分挂载真实用途，并把路径与物理存储验证落实到正式模型。
- 是否存在临时补丁或绕过：否。不能白名单特定服务器、忽略任意 RW 挂载或修改历史 targets。

## 经验门禁
- 新包真实入口校验失败即阻塞激活；只能改正式源码与测试后重新封包，不能热改 staged engine。
- 保持历史 targets 与旧失败恢复证据完全一致，不修改旧凭据、不放宽物理目标比较。
- 周期、锁和数据库/对象存储目录固定且禁止路径别名；所有 RW 存储必须检查物理重叠。
- 远程仅按已授权范围读取路径元数据/resolve，不读凭据内容、不修改文件或服务。
- UTF-8 文档、脚本与日志必须显式编解码；远程检查固定 Python 载荷并验证退出状态。

## BDD 与预期验证
- Given 历史已登记非数据保留挂载含操作系统合法路径别名，When 配置恢复周期，Then 根据真实路径验证其类型与不重叠关系且保留原 target 不变。
- Given 数据路径、周期根或锁路径含别名，When 验证恢复周期，Then 明确拒绝。
- Given 别名指向周期目录/锁/数据重叠位置或解析证据不完整，When 验证，Then 明确拒绝，不能跳过。
- 测试先运行真实文件系统 RED，再最小实现 GREEN 与 epoch/replacement 定向回归；Linux 特有约束必须由实际 Linux 测试证明。

## 根因与正式修复

真实 57 的唯一路径别名是 backend 的 `/var/run/docker.sock -> /run/docker.sock`，类型 socket；`/var/run -> ../run` 是原 v3 preservedApplicationMounts 中已固定的链接。实时只读 inode/device/mode 与登记相符，epoch root 和 source lock 没有链接。旧保留挂载合同本就支持固定链接与 socket，但新 `_validate_epoch` 对全部 RW Source 再套无链接路径规则，造成候选误拒绝。

正式修复仅复用 v3 非数据保留挂载的原合同：完整 role/mount 精确匹配，`observe_preserved_mount` 重新核对全部真实身份后取得 canonical resolvedPath，仍执行 absolute 和词法/物理重叠检查。未登记、旧版本、数据挂载不继承此规则。所有 RW 路径都继续参与门禁；live mountinfo 的设备/文件系统路径比较包括嵌套 bind，stateRoot 也核物理重叠。无服务器、路径或异常白名单，原 targets 保持不变。

## 验证记录

- RED：真实 Linux `stream-epoch --attempt 6`，epoch 4 failed / 49 passed；正向用例准确复现现场 PATH_ALIAS_REJECTED，另两项重叠预期尚未到达，物理 helper 尚不存在。SQL107通过；按失败立即结束；输入未变、容器已清。日志 SHA256 `16013e1cfa8c42a13913f7d6f5d62e7dfd3852f85bd664413e90af0488729456`。
- GREEN / REGRESSION：真实 Linux `stream-epoch --attempt 7` -> SQL107、epoch53、replacement11、resilience9，共 180 passed，零 skip，实际退出码0；inputFilesUnchanged=true，containerRemoved=true，networkDisabled=true。日志 SHA256 `290124e098d6b24d55fe0ecf6345873b737ae0d7192467819326707c1222c22f`。resilience 两项历史读取性能用例使该文件总耗时256秒，最终实际退出并通过，未用旧结果替代。
- 只修改 `ops/recovery/recovery_replace.py` 和 `scripts/tests/test_backup_epoch.py`；不需要新增封包文件登记。epoch 存储模块、来源实现、原 targets、远端 staged engine 未修改。
