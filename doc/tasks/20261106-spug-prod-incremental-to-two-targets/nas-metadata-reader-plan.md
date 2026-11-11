# NAS 元数据读取准入诊断与修复

## Goal

延续本任务已授权的 Spug 增量备份与测试服恢复。预计大额空间预算已按用户要求改为 OBSERVE_ONLY；当前恢复失败属于独立的 NAS 元数据单链接校验问题，不能报告为磁盘不足或恢复成功。

## Current Status

implementation_verified_pending_install：原测试服恢复操作 smallapp-b4f21de7a0c64d31beda7efa0204ced8 在 Native.resolve 阶段失败，未创建执行 worker。最小共享 reader 修复已通过 portable10、Linux25 和共享回归270项，真实 CIFS 原失败文件只读验证通过。保留原失败记录；正式封包、安装与真实恢复尚未完成。

## Milestones

1. 核对原失败证据、实际读取实现和 NAS 发布方式。
2. 如需修改，先记录可观察 Given/When/Then 与 RED 测试；共享读取逻辑重构遵循 Subagent-Driven Development。
3. 保留真实硬链接、文件变化和内容校验的拒绝能力，完成 GREEN 与受影响回归。
4. 如有产品变更，从已提交目标创建专用发布 worktree，构建并验证正式组件；不得原地改旧远端 engine。
5. 按既有授权完成测试服恢复；正式服、审查服仅做选择与准入验证，不执行覆盖恢复。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。不得忽略真实硬链接、内容变化或写入错误。
- 是否从根因和长期维护角度解决：是。先区分真实硬链接与 NAS 属性读取差异，禁止把手工预热缓存作为产品修复。
- 是否存在临时补丁或绕过：否。不得改写历史备份元数据，不修改共享 NAS 挂载配置。

## 经验门禁

- Trigger：真实恢复在准入阶段失败，错误为 BACKUP_EPOCH_REGULAR_SINGLE_LINK_REQUIRED。
- Preflight check：核对原操作 ledger、实际安装组件与解释器 pin；只读诊断不生成新恢复操作。服务器访问、备份恢复、PowerShell 编码和任务经验索引按现有入口执行。
- Blocker：无法证明原失败边界、真实文件身份不明、旧备份内容校验不符、或不能区分目录缓存与真实硬链接时，不得放宽校验后执行恢复。
- Verification：保留原失败证据；实际文件描述符与目录路径均验证；真实硬链接、文件替换、读取中变化继续拒绝；正式包回归和真实 Spug 用户路径分别记录。
- Forbidden action：禁止重提同一 operation id、修改旧证据、删 NAS 数据、移除单链接校验、静默重试掩盖错误、以接口代替前端提交恢复。
- Evidence：原操作、test58-original-resolve-diagnostic-r4.private.json、archive-link-evidence-r1.private.json；均位于本任务原私密证据目录。

## Expected Verification

- Given 可验证的单链接 NAS 备份元数据，When 控制组件派生恢复输入，Then 可以严格读取并验证原内容。
- Given 实际存在第二个硬链接或读取时发生替换，When 派生输入，Then 明确拒绝且不启动恢复 worker。
- Given 原恢复操作已失败，When 查询历史，Then 仍显示原失败；修复验证使用单独明确的新操作，不能覆盖旧记录。

## 独立合同审查后的最小设计

- 实际 r2 只读序列证明开前路径 nlink=2，首次 FD 与随后路径 nlink=1；原 dev/ino/mode/uid/gid/size/mtime/ctime 均保持，原内容 SHA 保持。
- 共享 epoch._read_file 仅拆分开前普通文件/权限校验与打开后完整单链接校验。_regular 本身及其它消费者不放宽；首次 FD、读取后 FD、最终路径都必须完整 _regular。
- 保持原 before/opened/after/path 的 _signature 精确相等，另核 mode/uid/gid 全程相等；不重建时间基线，不新增容忍硬链接开关或 NAS 特殊分支，不修改上层 _Reads。
- Linux 明确使用 NOFOLLOW/CLOEXEC/NONBLOCK，防止初查后换成 FIFO 阻塞；Windows 保留明确现有二进制只读兼容。有限测试实际读取真实文件与 FD，不模拟 stat 成功。
- Given 真实硬链接仍在，Then 首次 FD nlink=2 拒绝。Given 初查后删除第二链接，Then Linux ctime 变化仍拒绝，不能以此冒充 CIFS 正向。
- 真实 CIFS 原件是本问题的 RED，修复后的同一只读实际文件严格读取是必需 GREEN；其余真实 Linux 正向不替代现场证明。
