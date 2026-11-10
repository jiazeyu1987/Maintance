# 3B 独立窄 bind 保全仓库：只读设计审阅

## Current Status

`design_ready_for_review`：已有代码与明确本机挂载原件的只读审阅完成。不改冻结 phase3A/layout 文档，不改产品、测试、配置或旧证据，不执行 Docker、远端、挂载、写探针或安装。父已收到2b冻结通知；3A1实施仍等待父完成该阶段验收/提交后单独放行。

## 目标、里程碑与验证

核对独立窄 bind 视图是否兼容原 incoming archive protection、保全 publication、SMB readback 与 retention 的路径身份合同；完成后列明成立条件、确定阻断与尚待真实准入的事实。证据限明确文件/函数和已绑定挂载原件；静态成立不等于可部署或真实写入成功。

## 经验门禁

- Trigger：同一 CIFS superblock 上的独立输入只读视图与目标保全写视图。
- Preflight check：精确 mount ID、parent/root/设备、同路径 autofs/CIFS、链接与物理别名；只保护明确 incoming 视图，核公司 NAS 与原 fstab 保持。
- Blocker：身份歧义、重叠数据/输入/保护范围、未证明独立写视图或 SMB 映射、缺当前容量/权限。
- Verification：本机代码检查、父原始 mountinfo pins、有限设计 BDD；真正挂载/写入/完整读回证据由后续已授权流程形成。
- Forbidden action：不为提案修改旧视图/fstab，不触发 NAS 挂载或目录写入，不把 rw 标记当写入准入，不跳过完整读回或原保留合同。
- Evidence：既有 `main-target-preservation-layout-addendum.md` 和父 `main-target-preservation-mount-layout-20261110-r2.json`（读取后核 pin）。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；明确区分输入保护视图与目标保全发布视图，复用原严格锁/身份/读回。
- 是否存在临时补丁或绕过：否；缺准入事实不宣称可执行。

## 结论

独立窄 bind 仓库在路径布局上与原归档保护相容，可以作为3B候选；当前还不能判为可部署。必须先解决“预期挂载不存在时落到本地底层目录”的首写准入缺口，证明真实独立视图身份及写入能力，并完成已列的 MAIN 配置/readback模板/双包合同。无需为此改27历史来源或原输入 mount 配置。

父 r2 原件已核：`main-target-preservation-mount-layout-20261110-r2.json`，13547 bytes / SHA256 `a1614485fb0d9aa87416902949b7d3abc9a3f945a533dca10b7b25280a8e6df8`。r2明确仅重读原r1观察、保留旧r1和原始 stdout；没有新远端、path stat或挂载变更。57 S57=432/rw，58 S59=1192/rw（覆盖同路径 autofs45，parent45），59 S59=268/rw。59 S57=511/ro与S59=268/rw共用设备0:39。原 SSH exit0及 Windows pending-socket-close stderr 均保留；`/mnt/nas`未lstat，不能从覆盖根挂载断言共享盘不存在。

## 1. 原归档视图保护支持的边界

`recovery_archive_view.py::ArchiveViewProtection._remount` 仅执行已pin的 `mount -i -n -o remount,bind,ro/rw -- <原mountPoint>`；不递归、不重挂 superblock。`install/verify/release` 核原 mountId、parentId、root、device、filesystem、source、superOptions 全部不变，仅将所选视图 options 的 rw切换ro；已只读v2不重挂。`select_configuration` 仍严格要求原 incoming archiveRoots 位于原视图下，且该视图不与数据/保留应用挂载重叠。窄 bind 不应被注册为 incoming archive protection，也不改变这套选择。

父提案源目录 `Backup/BackupPackage/spug-target-preservation/<host>` 与原六条 archives 无前后缀重叠。若它被独立 bind 到 control根的 `preservation-repository-view`，新 mountPoint 在原输入视图树之外、新mountId独立、其 root固定为该仓库子目录、底层 superblock原为rw，则原视图的单视图remount不会主动操作新mount。不能只凭理论宣布成功，后续有限真实Linux验证必须同时观察原视图ro、新视图rw和其余字段保持；错误的普通remount、recursivebind、共享传播或隐藏子挂载仍须拒绝。

## 2. control根下的确切位置与安装时序

三目标原配置显示：57/58 control根为 `/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3`，59为 `/mnt/intruoyi-data/spug-main-restore-20261104-v3`。`preservation-repository-view` 是 `runtime`、`replacement-state`、`recovery-operations` 的兄弟，不得放进这三者或ctx操作目录。原 `replacement.storage.protectedRoots` 已包含整个control根；其含义是禁止数据替换侵入，不是禁止该根内存在独立受保护仓库。`verify_storage` 对数据目录的隐藏子挂载/物理重叠检查仍保留；新视图不在数据目录下，静态上没有必然冲突。

但 TASK `main_program_control_runtime.RuntimeGates::_observe/preserve` 与 activation 的 before/after 都严格比较完整 `/proc/self/mountinfo` 原字节/SHA。**不能在既有 stager/activation 的 before→after 区间插入新bind**，否则 `BUSINESS_OR_MOUNTS_CHANGED` / `RUNTIME_ORIGINALS_CHANGED` 为正确拒绝。后续若授权布局，须作为单独明确阶段，记录仅新增的精确目录/挂载以及原所有mount、公司保护路径、fstab保持，再生成新的真实安装观察；不能重写r7原报告、把新增mount从比较中隐去或用旧baseline冒认新状态。

## 3. publication、读回、保留历史可复用的合同

- `TargetPreservation.prepare` 的仓库禁重叠集合是本次ctx根、dataPaths/dataRoot、replacement.stateRoot和epoch根。提议的兄弟目录不触发这些文字路径重叠；真实物理别名仍须另核，文字不同不是证明。
- `_directory/_path` 要求所有路径无链接/别名、父目录不可被非owner写入，仓库owner为当前euid、不得group/other write；新bind根必须满足实际lstat。`_new` 使用O_EXCL/O_NOFOLLOW并fsync文件和目录；CIFS上的有效UID/mode、单链接、目录fsync、O_PATH/inotify以及文件身份保持均须实际成立，不能用mount显示rw替代。本地ctx/readback原件仍要求原私有权限，不能因为仓库是CIFS就放宽。
- `RepositoryLock` 将 `.repository-control/write.lock` 的服务器字节锁、held fd/dev/ino与路径持续绑定；同仓库旧unknown或 `recovery-read-guard.json` 存在即阻断。新独立仓库需要自己的repositoryId/identity和同一原锁实现，不使用临时本机锁代替。部署时不能进入活动备份/恢复、另一个仓库writer或现有读guard。
- `SmbReadback.remote` 允许显式POSIX `repositoryRoot=<bind目标>` 映射到固定UNC+`Backup/BackupPackage/spug-target-preservation/<host>`，只将root内规范相对路径附到UNC。没有要求POSIX根必须位于 `/mnt`，故无需改读回算法或引入全局HostView映射。`PreservationReadback` 仍核原凭据/library pins、认证加密、新连接、每个payload完整SHA/前后stat和全部sidecar。
- publication固定 `<repositoryRoot>/preservations/<sha256(operation)>`；hold固定同root的 `.repository-control/preservation-holds`。`preservation_holds`、retention及离线history均核原绝对路径和同operation绑定。**从第一次发布起，bind目标路径是持久历史身份**；以后不能用backing源路径替换、改UNC相对目录或重算原pin。待用/未知hold均保留，原retention不得删除保留点。新独立仓库不因此获得删除授权。
- 当前proof明确 `serverDurabilityVerified=false`、`independentFailureDomain=false`；同NAS独立view不构成独立故障域，也不增加服务端持久化声明。

## 4. 确定需要补齐的首写门禁

当前 `TargetPreservation.prepare` 先 `_path/_directory(repositoryRoot)`，再建立RepositoryLock；它没有读取一个已登记的独立bind mountIdentity。`PreservationReadback` 构造只验证连接/认证，尚未以仓库内容证明映射。若bind未挂，而底下本地空目录仍符合UID/mode，当前逻辑可能在本地创建control/lock，通过本地容量观察，随后停写，直至publication的SMB完整读回才报错。不能把这个晚失败当作禁止本地fallback的可靠准入。

需要一个有限、显式、被repository配置pin绑定的写视图合同。首个RepositoryLock/仓库目录写入**之前**核：目标路径唯一可见mount、静态登记的精确mountPoint/root/source/filesystem、view及superblock均rw、无隐藏子挂载、SMB与POSIX指向同一预期仓库；把当次实际mountId/parentId/设备/目录FD身份保存为本操作观察，不能把这些重启可变值写死在长期配置。核已登记incoming roots、数据、epoch、state与保留应用挂载的物理别名边界。保全过程同ctx原锁下持续检查本次身份，缺失/替换/ro/错误映射立即失败；不主动创建底层本地备用目录。应复用 `visible_mount` 的真实O_PATH/fdinfo叠层消歧，不能采用“最长字符串/最大mountId”处理58 autofs。

不能仅比较同设备号：59两视图共享0:39但有不同只读属性；57不同CIFS连接可能访问同NAS目录却设备不同。必须结合mount root与固定UNC相对目录判断物理内容，且核 `/mnt/nas` 的真实alias后才判断与原公司/应用挂载关系。对.57原backend保留 `/mnt/nas/Backup/BackupPackage` 的实际写者权限尤其需父确认，不能把停住当前writer等同NAS无外部写者。

父尚未执行拟仓库lstat/权限ACL/statvfs/路径映射，也未创建/挂载/写探针；这些仍未知。bind本身不改变底层CIFS的UID、file_mode/dir_mode、服务器ACL或协议能力。实际新目录有效mode与fsync/锁行为必须在明确授权的布局/正式prepare证据中证明，不能静态宣称失败，也不能静态宣称通过。

## 5. 最小静态配置、操作原件与消费点提案

### 5.1 纳入已经计划的新v2，不另造v3

本节是对尚未实现的3A1设计的显式增补，冻结的phase3A/layout文档及其SHA保持原样。建议在已计划的 `MainTargetPreservationRepository/v2` 加一个必需字段 `writeView`；v2完整顶层字段固定为 `schemaVersion, repositoryId, repositoryRoot, sourceIdentityPin, captureBinderPin, readbackTemplatePin, writeView`。`writeView` 本身只有以下四字段，由外层v2解释，不再嵌套一个版本框架：

| 字段 | 静态含义与必须核对的关系 |
| --- | --- |
| `mountPoint` | 规范Linux绝对路径，必须逐值等于 `repositoryRoot`；不允许链接、路径别名、`..` 或通过backing路径改名消费。 |
| `filesystem` | 本次有限合同只接受精确 `cifs`。未知文件系统明确拒绝。 |
| `mountSource` | 精确 `//server/share`；与readback模板 `uncRoot` 的服务器/共享逐段相同，只允许固定UNC分隔符表示转换，不做DNS别名、大小写或路径猜测。 |
| `mountRoot` | 精确规范POSIX根，例如 `/Backup/BackupPackage/spug-target-preservation/57`；必须等于模板 `repositoryRelativePath` 加唯一前导 `/`，并匹配实际所选CIFS挂载行的root。若实际前缀共享布局不满足此关系，登记被阻断，不能归一化为“看起来等价”。 |

长期身份继续由被pin的repository配置、独立 `repositoryId`、原 `sourceIdentityPin` 和readback模板闭合；不新增单独可变身份文件。不能将原incoming仓库的repositoryId套给保全仓库；同一配置连续多次操作复用，配置不含mountId、parentId、device、inode、当前PID或操作编号。缺字段/多字段/未知版本拒绝；普通source配置及preservation旧v1历史逐项保持。

3A1应同时交付这份v2合同、首写前live admission和当次证据消费，不能只在3B安装helper中检查一次：服务器重启后日常恢复仍必须自行证明视图。3B只负责在真实事实支持下配置四字段、独立仓库与窄bind布局，以及权限/容量/工具/SMB读回准入；不需要为登记再改产品schema。本增补不引入generation adoption、全局路径映射或自动挂载功能。

### 5.2 每次操作固定的有限原件

建议固定本机操作路径 `ctx._root/target-preservation/write-view.json`，schema为 `MainTargetPreservationWriteViewObservation/v1`。精确字段为 `schemaVersion, operationId, targetConfigRef, repositoryConfigurationPin, executionBindingPin, mountIdentity, rootIdentity, mountInfoLine, observedAt`：

- `mountIdentity` 直接采用现有 `MOUNT_FIELDS` 的完整对象，即 `mountId,parentId,device,root,mountPoint,filesystem,source,options,superOptions`。禁止将观察值用作下一次操作的静态预期。
- `rootIdentity` 为实际打开目录FD及路径一致的 `device,inode,mode,uid,gid`。同一次操作持有O_PATH/目录FD，并以 `/proc/self/fdinfo` 的实际mnt_id选中可见行，逐项核 `writeView` 与rw模式。
- `mountInfoLine` 保留所选原始行，以便校验当前parser未展开的可选传播字段；必须能解析回同一 `mountIdentity`。只保存该有界行，不把整台主机的mount快照改成新的全局policy。
- 原件在现有 `_preservation_root(context)` 管理的0700操作根内，以0600、O_EXCL/NOFOLLOW及原目录身份/fsync写入；不在仓库写这份准入原件，不公开凭据。没有成功观察则不伪造成功记录。实际失败保留原异常与已产生原件。

已计划升级的 `MainTargetPreservationIntent/v2` 增加必需 `writeViewObservationPin`，与同一intent已有的repository/configuration/request/execution binding及新readback derivation闭合；原件pin进入本操作原始证据集合。成功proof/receipt继续通过已绑定intent消费，不给没有语义变化的sidecar逐个增版本。离线history核当次原件、静态配置、binding/op与intent pin；**不读取当前mountId来重判旧操作**。以后重启产生新mountId的新操作可以通过相同静态合同，旧观察和历史pins不能回写。

### 5.3 明确的代码消费边界与保证

`TargetPreservation.prepare` 在原ctx/预约/锁与静态policy/template验证后，且在 `RepositoryLock(...)` 以及所有仓库mkdir/open之前建立view lease、写本机观察并再次check；`preparation_guard` 在早期阶段消费该lease。对象建立后由现有非递归 `_check_resources` 加入 `lease.check()`，不得调用ctx guard造成循环。`_check_base`、实际capture/publish/hold/handoff沿原check链消费；原 `CapturedPublisher.check`、RepositoryLock及readback的业务合同保持。完成和失败的close均幂等关闭本操作FD，不调用已失效执行guard，不自行卸载新view。构造中途失败也必须释放已经持有的本机FD。

实际能证明：首写检查时缺bind、错view/root/共享、ro、隐藏子挂载或不符目录身份会在仓库control/lock创建和业务quiesce前拒绝；整个正常流程持有目录引用，原incoming保护只remount自身视图，产品不卸载保全视图；持续guard检测到与本次观察不符时保留未知结果，不授权clear、handoff或保全点删除。普通umount在持有引用时的busy行为仍需有限真实Linux验证，不用静态分析冒称已证。

不能证明：用户态 `check()` 与随后按绝对路径执行的 `mkdir/open` 不是原子mount事务。外部特权进程强制/懒卸载或在检查间替换挂载有竞态，O_PATH引用与本次静态门禁不能声称彻底阻止该外部行为，也不能承诺竞态下从未触及底层目录。任一后验身份异常必须传播unknown并阻止clear；不能把可能的错误写入“解释成成功”。本阶段不为这一外部特权威胁重写 `RepositoryLock`/全Publisher为FD相对写、不引入procfd逻辑pin或fallback；若日后正式产品自身新增卸载此视图的步骤，那将改变当前威胁前提，需独立设计，不能沿用本结论。

## 6. 后续有限验证（未执行）

1. Given同一底层的原输入view和独立窄view，When真实原`ArchiveViewProtection.install/verify/release`，Then原view EROFS、新view真实写入保持、原superblock与所有其它mount字段保持；原读取保护与业务容器不变。
2. Given缺bind但底层本地目录存在、错mount root/source、ro、隐藏子挂载或UNC映射不符，When正式v2首仓库写准入，Then明确拒绝且本地control/lock未创建、业务尚未quiesce；叠层autofs必须按真实fdinfo选中CIFS，不用最大ID猜测。
3. Given实际有限文件经新view发布，When正式严格SMB reader完整读回并生成hold，Then原bind绝对路径/payload/sidecar全部一致；改映射、缺hold、通过backing别名消费、已保护点纳入retention删除均拒绝。
4. Given独立布局步骤后新的完整mountinfo观察，When正式stager/activation，Then该阶段全程mountinfo保持；在before/after中新增mount仍正确失败。旧r7原件不改。
5. Given同一静态v2配置和两次真实挂载生命周期，When两个不同operation分别prepare，Then各自保存当次不同mountId的原件且均严格绑定同一静态根；历史消费第一份不要求第二次/当前mountId相等。相同operation已有原件不能覆盖，错operation/binding/repository pin必须拒绝，旧v1回归不增加新字段要求。
6. Given成功prepare后真实持目录引用，When普通卸载尝试或视图只读/身份漂移，Then记录真实busy或检测结果，后验不符进入unknown且不得clear；测试不通过任意mock成功替代真实mount/FD行为。外部强制/懒卸载竞态仅证明检测及失败闭合，不宣称完全防止特权攻击写入。

此轮仅新增本文。源码/原件读取与文档UTF8检查不算产品RED/GREEN；未做上述实验。继续等待父调度，不自行实施3A1、3B或安装。
