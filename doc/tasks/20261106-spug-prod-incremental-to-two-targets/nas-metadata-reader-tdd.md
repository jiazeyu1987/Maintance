# NAS 元数据读取阶段：有限 BDD / TDD

## Current Status

implementation_frozen_portable_green_linux_green_pending_parent。父实际完成 Linux RED 并明确放行后，唯一产品文件已最小修改；portable 10 项 GREEN，产品与测试冻结。Linux 同组 GREEN、共享回归和真实 NAS 只读 GREEN 仍由父执行，不把本机结果外推为现场恢复成功。

## Goal / Milestones / Expected Verification

1. 先固定真实文件、FD、原始输入 pin 与异常传播场景，不伪造成功 stat。
2. 父运行 RED；区分真实产品失败、载体前提失败和已有拒绝行为。
3. 只拆分开前普通文件/权限检查和打开后完整单链接检查；保留原时间/内容合同。
4. 同组 GREEN 与共享调用者回归；真实 NAS 原文件只读 GREEN 由父另行验证。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；任何读、身份、权限或限额失败均原样拒绝，不重采样或重试。
- 是否从根因和长期维护角度解决：是；正式读取以同一已核身份 FD 的真实单链接状态判定，不把路径缓存链接数当作最终授权。
- 是否存在临时补丁或绕过：否；不按 NAS/IP/路径特殊放行，不修改历史元数据，不给 epoch reader 新增宽松选项。

## 经验门禁

- Trigger：实际 CIFS 只读序列开前 nlink=2、首次 FD/后续路径 nlink=1，其它身份、时间和内容均相同。
- Preflight check：父保存的真实 NAS 原件与本轮产品/测试原 SHA；真实 Linux 专用节点只能在真实 Linux 运行，Windows 只选 portable 节点；父独占运行服务器和隔离载体。
- Blocker：伪造 stat 结果、静默 skip、依赖/权限前提失败、没有原生退出或输入漂移时不能记 GREEN。
- Verification：返回原 bytes/SHA；残留硬链接、真实 unlink 引发的 ctime 变化、inode 替换、读取区间变化与错误均拒绝；实际 open flags、FD 生命周期、输入上限分别核验。
- Forbidden action：不调用 SSH/Docker，不运行真实备份/恢复，不重写原失败或 NAS 文件，不用真实 Linux unlink 第二链接冒充缓存刷新正向。
- Evidence：新 `scripts/tests/test_backup_epoch_read_contract.py`、父隔离载体原 RED/GREEN 与 `PRIVATE/archive-link-sequence-r2.private.json`。

## BDD

- BDD: portable stable -> Given 自有真实空文件、UTF-8 文件和二进制文件，When 严格有界读取，Then 原内容及 pin 精确一致，FD 关闭。
- BDD: original bounds -> Given 超过原上限的真实文件，When 读取，Then 明确 INPUT_LIMIT，无返回 pin、无 FD 泄漏。
- BDD: hardlink -> Given 仍有第二个真实硬链接，When 打开/读取，Then 拒绝；读取后新增第二链接亦拒绝。仅真实 CIFS 原件可证明缓存链接数刷新正向。
- BDD: preopen boundary -> Given 初始 stat 后真实替换 inode、新增链接或删除第二链接，When 一次真实 open，Then 仍拒绝，后者必须保留 ctime 差异拒绝。
- BDD: actual read interval -> Given 首次真实 FD 基线，When 真实同大小改写且恢复 mtime、追加、截断、utime、chmod、chown 或短暂创建/删除硬链接，Then 原读失败并关闭 FD。
- BDD: native open -> Given 初查后变成 FIFO 或 symlink，When Linux open，Then 使用 NOFOLLOW/CLOEXEC/NONBLOCK，真实内核有界拒绝，不阻塞。
- BDD: final path and failures -> Given 成功打开真实 FD，When 末次路径校验或读/包装步骤异常，Then 校验时 FD 仍活着，异常对象原样传播，最终 FD 关闭。

## 有限载体权限边界

父明确批准本机隔离 Linux 单元载体在 `cap-drop ALL` 后仅 `cap-add CHOWN`，仍 network none、只读根文件系统、无业务或宿主仓可写挂载。uid/gid 节点只修改 pytest 自有 tmpfs 文件。此能力不用于服务器或真实恢复，不扩大产品运行权限。缺少真实 CHOWN 能力时节点必须失败，不能 skip 或模拟成功。

## Actual Evidence

此文件创建时尚未运行新测试，产品未修改。测试冻结、collection、Windows 有限执行和父 Linux RED/GREEN随后逐项追加；不把测试设计当执行成功。

- 2026-11-11T17:09:10Z（实际 UTC）：新测试 collection 原生 exit0，25 个节点。Windows 仅选择 portable 10 节点，原生 exit1，9 PASS / 1 FAIL / 0 ERROR / 0 SKIP，15 个真实 Linux 节点明确 deselected，不能计为通过。
- RED: portable 后读真实新增第二硬链接 -> FAIL，准确为 DID NOT RAISE ValueError。旧函数仅比较 Windows birthtime 身份，未在读后完整核 nlink，真实 NTFS 新链接在读后被错误接受；原文件 stat 真实为 nlink2，未伪造任何成功 stat。
- 其余 portable 9 项覆盖空/UTF-8/二进制原 pin、限额、残留硬链接、两异常对象保持、最终路径 FD 存活和最终路径异常/关闭，均实际通过。
- 原件仅 PRIVATE：`nas-metadata-reader-collection-r1.log`、`nas-metadata-reader-portable-red-r1.log/xml`、`nas-metadata-reader-portable-red-r1-result.private.json`。产品在此轮前后 18100B，SHA256 `32954ebf9d187cf245be4fe5b9f8ae19b187076a9880f3aaae7f316a13fc0c5d`，输入保持 true。
- 之后仅给测试流观察代理补标准属性透传，使其不限制产品使用真实流的 fileno；不改变读/变更/异常或断言语义。最终测试 SHA 另提供给父，原 r1 测试字节与原失败留在原报告，不覆盖。
- Linux 预期 RED 为实际 open 缺 CLOEXEC/NONBLOCK、FIFO 换入后阻塞，以及初查 nlink2 导致删除第二链接边界未到达。真实 unlink 产生的 ctime 变化在新函数必须仍拒绝，不能以它充当缓存刷新正向。最终确切失败集合以父真实原生结果为准。

## 父实际 Linux RED 与明确实现放行

- 已只读核对父原件 `PRIVATE/nas-reader-red-r1/result.json`：nativeExitCode=1，25 tests / 3 FAIL / 22 PASS / 0 ERROR / 0 SKIP，elapsedSeconds=24.813，sourceFilesUnchanged=true，containerRemoved=true。原 runner 110499B/SHA `aa104dcee180dcf6526e0936e3db90e9bb61fdcae16ac45e97c26d11e6199f05`，snapshot 8069120B/SHA `d567efa08f0b363ba6b54505f6d6a01e08a7a1619925307cd3212d027b09494d`。
- 父确认三确切失败与预期一致：缺 CLOEXEC/NONBLOCK、remove-second-link 在开前拒绝而未到实际 open 边界、FIFO 实际阻塞 3 秒。父随后明确放行仅 epoch reader 的阶段拆分；测试原字节保持，未放宽断言或时间范围。

## 最小实现与 portable GREEN

- `_regular` 的完整普通文件/单链接先验及现有错误顺序保持；仅抽出原权限检查 `_file_permissions`。开前仍必须普通文件且原 uid/mode 合法，首次真实 FD、读后 FD 和最终规范路径都执行完整 `_regular`。
- `_read_file` 的原 `_signature`（含原 mtime/ctime；Windows 原 birthtime 合同）在开前、打开后、读后与最终路径仍全部精确相等；另核 mode/uid/gid 全程相等，不重建时间基线、不更改全局 `_signature`。最后核路径时 FD 仍打开。
- Windows 明确只读 BINARY/NONINHERIT；POSIX 明确 NOFOLLOW/CLOEXEC/NONBLOCK，缺标志不能默认为 0。不改捕获 actual_pin、归档格式、上层三种 `_Reads` 或生产挂载/权限。
- GREEN: `run-nas-metadata-portable-green-r1.py` 2026-11-11T17:15:21Z（实际 UTC）原生 exit0；portable 10 PASS / 0 FAIL / 0 ERROR / 0 SKIP，15 个 Linux 节点明确 deselected，0.18 秒。真实 NTFS 后读新增硬链接负例现在拒绝；完整真实 Linux 和 NAS 结果仍待父执行。
- 本轮两输入前后 SHA 保持。冻结产品 18922B / SHA256 `c66714cf0d76a53d2644d17d0bd89a9b3b549a3152a943b88065a988e35f7a47`；测试 11600B / SHA256 `bd765e4891415a15f62bea699d3260ad55172635477f69b6d91672c318ec7bfa`。
- 原件 `PRIVATE/nas-metadata-reader-portable-green-r1.log/xml`、`nas-metadata-reader-portable-green-r1-result.private.json`。产品 UTF-8 无 BOM、全 LF 保持；AST 与 `git diff --check -- ops/recovery/recovery_backup_epoch.py` 通过，Git 提醒未来 checkout 的 CRLF 策略但本轮未转换字节。
- 本代理未调用 SSH、Docker、HTTP 或备份/恢复，没有提交。下一步由父审查该冻结 diff、运行同组 Linux GREEN、共享调用者回归及真实 CIFS 候选只读 GREEN；全部必要证据通过前不宣称可安装或任务完成。
# 父实际闭合结果

- RED：PRIVATE/nas-reader-red-r1 原生 exit1；25 tests / 22 PASS / 3 FAIL / 0 ERROR / 0 SKIP。确切失败为缺 CLOEXEC/NONBLOCK、开前链接删除未到真实 open 边界、FIFO open 阻塞；输入保持，隔离容器已移除。
- GREEN：PRIVATE/nas-reader-green-r1 原生 exit0；同25项全部 PASS，0 skip；原时间预算不改，源码保持、容器移除。
- REGRESSION：PRIVATE/nas-reader-regression-r1 原生 exit0；epoch、普通恢复输入、保全输入、program generation 与历史 evidence 五组270项全部 PASS，0 error/skip；153.469秒，源码保持、容器移除。
- 真实 CIFS GREEN：PRIVATE/nas-reader-cifs-candidate-r1.private.json，未安装候选 c66714cf0d76a53d2644d17d0bd89a9b3b549a3152a943b88065a988e35f7a47 在原失败文件实际只读 PASS；开前nlink2→读后nlink1，dev/ino/mode/uid/gid/size/mtime/ctime及219B SHA保持，原ledger/fstab/mountinfo保持。audit拒绝远端写/子进程，无恢复派发。
- 上述通过仅说明实现及相邻合同，不能宣称正式组件已更新或恢复成功。当前子项 implementation_verified_pending_install。
