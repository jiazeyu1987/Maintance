# 目标保全：输入归档与目标采集布局核对

## Current Status

`design_ready_for_review`：本机明确原件核对及有限设计已完成；2b 未冻结，不改产品、测试、配置或旧证据，不执行 Docker、构建、远端或业务操作。以下 BDD 未执行，不计 RED/GREEN。

## 目标与里程碑

1. 从明确的 b5/r7 owner/source/capture 原件逐项核对三目标的历史来源 `archiveRoots` 与目标 capture `archiveRoot`，记录可证明的交集与身份关联。
2. 只引用既有挂载、SMB 读回和服务器映射证据，区分输入归档只读视图与目标保全发布写路径；缺新鲜容量、权限或挂载证明明确列为未知。
3. 给出解除错误耦合的有限版本检查方案及后续 RED 场景，保持普通来源、旧 pins、公司 NAS/fstab 不变。

## 经验门禁

- Trigger：MAIN 目标覆盖前保全；输入归档的读边界不能自动授权目标独立写路径。
- Preflight check：以显式绑定的原 owner/source/capture 小原件核字节与 SHA；先核真实部署路径和模式，再核 sourceIdentity/databaseUuid/五服务关联；不扫描 PRIVATE 或读取大包。
- Blocker：缺精确原件、未证明可写目标或现场状态已经过时，只阻塞对应登记与执行，不推断可用。
- Verification：本机原件 pins、逐目标来源布局表、代码精确检查点和未知项；不得以本次静态核对冒称安装验收。
- Forbidden action：不改 27 份历史来源配置，不把保全仓库塞入 incoming source 的 archiveRoots，不改挂载/fstab，不降级本地归档，不回写旧证据。
- Evidence：既有 phase3/3A 计划与 `main-target-generation-readonly-reconciliation-20261110-r4.json`；后续仅补明确关联的已有小原件。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；先区分输入归档读取准入与目标采集身份、目标发布路径的独立职责。
- 是否存在临时补丁或绕过：否；未确认布局前不实施。

## 1. 原件边界与核验

本次只读取明确文件，不扫描 PRIVATE、不读大包、不读取凭据文件。`main-program-configuration-plan-b5fa4c5-r7.json` 绑定的 PRIVATE 同名原件为 779836 bytes，SHA256 `e9f216ec0056713c99b468d862359f9963166b16f3a74aef8afe7c4f40ded5a2`；实际原字节已核。该原件的三份 owner JSON 经原规范序列化逐一匹配已部署 owner pin；其 `targets` 各原对象也逐一匹配 r4 中的 `baselineTargetPin`，不是另造新 target。

| 目标 | owner bytes / SHA256 | baseline target bytes / SHA256 |
|---|---|---|
| .57 | 52924 / `090f960a6cbfed4f418e17e888286b3b58b77d8197709682e9762b5ebd4ce2ef` | 40889 / `b7ae47b32bc5e0ba25c1dd051d525400338d73108d75a9f75a9afcf1243e519b` |
| .58 | 30048 / `e2444f7cbc449512d6e83bfaa6e8c7fddf578f9988d21592d7b4c02583bacaff` | 17760 / `c30ea4a9635713a52e85e0d324a79a28fd49ce23abee34ab0007cf0114a50e3a` |
| .59 | 32086 / `f6c88d55deea8c51367c64beb6e4016f7d8fcdf8b7a5f3ccd6ba101efbb04f32` | 20307 / `2d9b058529d3a6561d68a870fd9e9b2d198d07261c09283ca01d0f207d933ea2` |

父新鲜读取的 .57 capture 原字节保存在 PRIVATE `source-57-capture-original-read-20261110-r1.private.json`，4753 bytes，SHA256 `0c00504b14ca5715ab205d2c43ad7c958f6014ab205f80e4e511df0a241f1c6f`，本次再次核原字节。其远端原路径是 `/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/configuration/capture-binlog-tmpfs-20261107-v3.json`，与 b5/r7 policy 和 r4 的 capture pin 完全相同。公开记录 `small-registered-original-readback-20261110-r1.json` 为 3001 bytes / SHA256 `46e397bf6f4431b4d87ac62db1bc430cae6d60378c49d850d1ad113883dd0329`。

此读取的原 SSH exit0、完整 stdout 和 84-byte Windows pending-socket-close stderr 均由父保留；结论只到 `CONTENT_PINS_VERIFIED`，不作为安装准入或新路径可写证明。r4 的三服 initial READY/sequence0/generationCount0/currentGenerationPin=null 事实继续保持，本增补不需要也不设计 generation adoption。

## 2. 九个恢复组合的真实路径关系

三份 owner 的三来源 `archiveRoots` 逐对象相同。以下为完整六条路径，不把 NAS share 或共同祖先当作归档 root：

| 来源简称 / 正式 sourceConfigRef | 已登记 archiveRoots |
|---|---|
| S57 / `intruoyi-57-safe-20261024-v1` | `/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas/Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57/archives`；`/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas/Backup/BackupPackage/prod57/20261021-optimized-backup-restore/archives`；`/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas/Backup/BackupPackage/prod57/20261021-spug-backup-restore-rehearsal/archives` |
| S59 / `intruoyi-59-safe-20261024-v1` | `/mnt/intruoyi-backup-nas/Backup/BackupPackage/backup59/intruoyi-repository/archives`；`/mnt/intruoyi-backup-nas/Backup/BackupPackage/spug-intruoyi59-remediation-20261024/fast/59/archives` |
| S19 / `intruoyi-PROD57-20261019` | `/var/lib/docker/intruoyi-data/prod-spug-backup-20261019/archive/PROD/archives` |

三组两两交集均为空；每目标三组总交集也为空。不能选择一个普通 `archiveRoot` 来满足所有来源。

更直接的事实是，.57 已登记 capture 的 `archiveRoot` 实为 `/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1/capture-staging`，这是来源采集暂存路径，连 S57 自身的三条 incoming archiveRoots 都不包含它。

| 恢复目标 | S57 输入 | S59 输入 | S19 输入 |
|---|---|---|---|
| .57 | 已登记本目标 capture；其 archiveRoot 不属于 S57 | 同一 capture；不属于 S59 | 同一 capture；不属于 S19 |
| .58 | 本目标 capture 未登记；关系未知，禁止套 .57 | 本目标 capture 未登记 | 本目标 capture 未登记 |
| .59 | 本目标 capture 未登记；关系未知，禁止套 .57 | 本目标 capture 未登记 | 本目标 capture 未登记 |

`recovery_target_capture.py::_configuration` 当前第172–174行因此会在 .57 全部三来源组合以 `PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED` 拒绝，不只跨服场景。该检查尚未进入已运行 b5/r7 包，不能描述为已发生的真实恢复失败。

实际 MAIN 输出在 `_prepare` 第133–135行固定为 `ctx._root/target-preservation/capture`，并以该目录做资源与身份核验。`config.archiveRoot` 不作为该输出；普通 `minimal_capture_support.validate_config` 仅仍要求它是已存在目录。应区分四个概念：普通来源采集暂存、incoming 已发布归档的读取范围、本操作目标采集暂存、独立保全仓库。它们不能以字符串成员关系互相授权。

## 3. 身份已证与未知

.57 原 capture 的 `sourceIdentity == sourceFingerprint == backupEpochPolicy.sourceIdentity`，值为 `a36d337b14a907d64a542ea66a8f46bc07fd75a84d6bea9ca1bfff6f4fe44690`；数据库 `ruoyi-vue-pro`、UUID `0fa6c22b-5a90-11f1-ade1-0242ac150002` 与原 target/epoch 相等。capture 的共同锁与 target replacement/epoch 完全相同。

.57 capture 的 MySQL/MinIO ID、backend/frontend writer 集合、全部五服务 image ID 集合，以及 Redis container ID/host/database 均与原 baseline 精确相等。原 target 服务完整 ID 仍由表1固定 target pin 持有，本增补不复制完整容器配置或凭据。此结果是同一原件间的绑定证明，不替代当前 Docker inspect、实际数据库 UUID、全部外部写者和容量的现场准入；本次没有读取密码、MinIO credential 或连接凭据文件，不能声称这些原内容已独立复核。

.58/.59 各有完整五服务 baseline 和既有 epoch 身份：.58 UUID `20ca4c6c-cc31-11f1-9b95-0242ac1deb16`、identity `intruoyi-main-58-safe-restore-20261104-v1`；.59 UUID `a4f03708-cc74-11f1-9cce-0242ac1def16`、identity `18f689ead7895a6e6e128a6523b6c60c9024b5a5193f7e355569765352158af9`。两者 epoch 与各自 replacement 锁相等；但 capture map 为空，没有可证明的 capture→五服务/对象/Redis/版本材料关联。不得推导新增 capture 身份，或使用 SMALL58、旧 .59 来源路径、.57 descriptor 代替。

## 4. 保全写根的已知边界

已绑定配置的 archive protection 登记如下。这里展示 view mode，不打印完整 mount 认证选项：

| 目标 | S57 视图 `/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas` | S59 视图 `/mnt/intruoyi-backup-nas` | S19 精确 archives 视图 |
|---|---|---|---|
| .57 | CIFS，view rw / superblock rw | CIFS，view ro / superblock ro | ext4 bind，view ro / superblock rw |
| .58 | CIFS，view ro / superblock rw | CIFS，view rw / superblock rw | ext4 bind，view ro / superblock rw |
| .59 | CIFS，view ro / superblock rw | CIFS，view rw / superblock rw | ext4 bind，view ro / superblock rw |

因此“58/59 的输入全部只读”不准确；它们 S57/S19 是只读视图，S59 登记为可保护的可写视图。原 r7 `main-program-control-units-{57,58,59}-b5fa4c5-r7.json` 及各自精确 privateSnapshotPin 已核原字节，记录 2026-11-10 08:48Z 左右 fstab/mounts 保持；它们不能证明现在新增独立仓库的权限/可用容量，也没有对新 repositoryRoot 的 statvfs/ACL/路径身份观察。

.57 现有普通来源 repository 的 POSIX 根为 S57 第一条 archives 的父目录，映射到 `\\172.30.30.4\IT共享` 下 `Backup/BackupPackage/spug-intruoyi57-remediation-20261024/safe/57`。`automatic-i2-audit.json` 记录该普通来源旧点的真实独立 SMB 完整读回：91 payload files / 2106237601 bytes，`payloadContentVerified=true`，并绑定原 readback-originals pin；不是本次目标保全仓库的证明，也不声称服务端持久化。未重读大载荷。

目前三目标 owner 都没有已登记 `targetPreservationPolicies`，本次明确原件里没有一个已经完成独立保全发布准入的 repositoryRoot/template。因此结论是“独立可写目标尚未证明”，不是“所有服务器没有可写 NAS”。尤其不能直接拿上表 rw 视图：若同一视图被本次 incoming archive protection 改为只读，或 POSIX/SMB 别名落到受保护输入目录，后续保全 publication 就会失败或侵犯输入边界。

父后续只读现场核对至少应固定拟选仓库父路径/完整 mountinfo/精确 mount ID与 mode/UID-GID与访问身份/容量(statvfs)/符号链接与物理别名，以及 NAS UNC+relativePath 的一一映射和独立读回认证库引用。还须证明它与 data/epoch/state/input archive 及其本次受保护视图的写入范围不冲突。只读权限判断仍不是实际写成功；最终经授权正式 `prepare` 的独占 RepositoryLock/journal、后续发布及完整 SMB 读回才形成写入证据。缺任一项阻断准入，不选择临时本地归档，不换/move 公司共享 NAS 挂载，不改 fstab。

## 5. 最小正式设计接缝（待父定范围）

1. 普通 `minimal-source-capture-config/v1`、其 `archiveRoot` 和普通 source FULL/INCREMENTAL 生命周期逐项保持。旧 target capture/保全 v1 的历史 reader 按旧版本核旧记录，不删除旧检查追认新语义，不修改已部署原件。
2. 在已规划 `MainTargetPreservationPolicy/v2` 下，使用一个明确 MAIN 专用配置版本 `MainTargetCaptureConfiguration/v1`。保留 `sourceConfigRef` 作为 owner 登记的 captureRef，并保留 `sourceLockPath/tools/limits/source/parent`；`parent` 必须 null。替换无关的 `archiveRoot` 为单一标记 `outputRootPolicy= CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE`，没有用户自定输出路径、命令、模板表达式或可选绕过标志。该字段集/名称为本增补提案，父审后再冻结，不提前生成配置。
3. 以具名 `validate_target_capture_configuration` 和 `_require_target_capture_scope` 复用原 source/tools/limits 的严格字段验证，避免复制通用验证器。普通 v1 原 header/path 检查保持；MAIN 分支独立核 owner/policy/capture pin、同 ctx PREPARATION、原 target/epoch/共同锁、五服务/数据库/对象/Redis/版本材料，以及固定操作输出的真实目录身份与资源预算。只在该显式 MAIN 版本移除“属于 incoming archiveRoots”的错误要求，不将普通验证函数改为可跳过路径检查。
4. incoming source 的原点/全链/归档 read guard、archive view protection 和全部27历史来源原件保持。新的目标采集输出仍不得与读边界及业务卷重叠；独立 publication repository 另由 repository/template 的精确写根、固定 UNC映射、原共享仓库锁、容量和完整读回准入授权。来源身份不随用户选择的恢复包变化。
5. 新 MAIN capture pin 必须由本目标 `targetProgramPolicies.captureConfigurationPins` 与保全 policy 共同绑定；初始化状态事实允许父另做必要登记，但不回写旧 capture pin/target/epoch/旧generation。现阶段只追加设计，不扩大为 generation adoption、三服配置生成或安装。

## 6. 后续有限 BDD / RED 清单（未执行）

- **布局错误复现：** Given 原 .57 capture 与同 target 的 S57/S59/S19 三份来源原件，When 原 `_configuration`，Then 三项均在错误 archiveRoot 成员检查拒绝；保留本机实际合同 RED，不启动数据库或服务器。
- **独立目标身份：** Given 同一真实 ctx/目标及新 MAIN 配置，When 切换合法 incoming 历史来源，Then 固定目标身份及 `ctx._root/target-preservation/capture` 不变；真实未知 target/capture pin、错 UUID、错五服务、错锁或 parent 非 null 必须在停写前失败。
- **版本保持：** Given 普通 v1、旧 MAIN/v1历史及未知版本，When 新入口解析，Then 普通 source archiveRoot 检查逐项保持，旧历史只走原分支，未知版本/标记/额外路径或命令字段拒绝。
- **写根不冒认：** Given 只读 view、被 incoming 保护的同一 view、POSIX/SMB 别名重叠、未证权限/容量或错误 UNC，When 新保全 prepare，Then 在 quiesce 前拒绝；单独一个 rw 字符串或普通来源旧读回 PASS 不能放行。
- **正式多操作：** 接既定3A1的 A1–A6，真实同 ctx锁、原件 O_EXCL、多操作独立 recordRoot，旧 inputs/27文档保持；成功事实来自有限真实文件/进程/正式读回协议，不能手填成功。需要 Linux 原语的用例由父在2b冻结后统一排程。

## 验证与剩余边界

本次原件 Python 核验命令均 exit0；源码定位中的 rg 未命中返回1仅表示没有匹配，不是产品 RED。三份 owner 及三 target 规范原字节、.57 capture 原字节、明确 units private pins 与 r4 绑定已核；未执行产品测试、Docker、构建、安装、远端、备份或恢复。只新增本文。2b 冻结及父批准之前不进入上述 RED。新增 repositoryRoot 的现场可写/容量/别名与 SMB 映射、.58/.59 自身完整 capture 材料仍是登记前置缺口。
