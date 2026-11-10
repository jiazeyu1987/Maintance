# 3A1 真实 CIFS 验证设施：测试服独立窄视图

## Current Status

`read_only_preflight_pending`。本阶段承接已审阅的 phase3A、layout-addendum 和 bind-view-review，不修改其原件。先只读核对 .58 真实路径、现有 CIFS、工具和登记的 SMB 凭据/库引用，再决定是否建立本任务专属验证仓库；当前尚未创建远端目录、挂载或写文件。

## 目标、里程碑与预期验证

1. 只读固定原全部 mountinfo、fstab、原业务容器状态、控制配置、路径祖先身份、可用容量及挂载工具原件。
2. 准入通过后，仅新增独立测试 NAS 子目录与独立窄 bind 视图，不改原 incoming/company NAS/fstab。
3. 用真实 CIFS 和独立加密签名 SMB 连接验证正式 v2 两个不同 operation 的 prepare；不停止主程序，不采集数据库，不 clear，不执行恢复。
4. 保存每次当时挂载观察、派生原件、真实锁与读回结果及原业务保持证据。测试仓库与将来的正式保全仓库分离，测试 hold 不混入业务历史。

## 固定候选路径与范围

- 主机：测试服 `172.30.30.58`。
- 现有 CIFS 入口：`/mnt/intruoyi-backup-nas`；预期共享为 `//172.30.30.4/IT共享`，实际可见层必须由 O_PATH/fdinfo 确认，不依赖列表顺序或最大 mountId。
- NAS 相对仓库：`Backup/BackupPackage/spug-target-preservation/validation-20261110-3a1-58`。
- backing 路径：`/mnt/intruoyi-backup-nas/Backup/BackupPackage/spug-target-preservation/validation-20261110-3a1-58`。
- 窄 bind 目标：`/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/validation-view-3a1-20261110`。
- 本地私有验证根：`/var/lib/docker/intruoyi-data/spug-main-restore-20261104-v3/validation-3a1-20261110`，与 runtime、replacement-state、recovery-operations 为兄弟。
- 原 `preservation-repository-view` 正式路径本阶段不使用。测试 repositoryId 与正式仓库明确不同。

授权沿用本任务“安装控制组件和登记配置、不执行恢复”及完成自动增量/三服选择的明确范围。此步骤只为新增控制能力提供有限验证设施，不启动/停止原应用或存储，不改业务 SQL、原配置、原 mount 或 fstab；不借此增加其它服务器操作。任何超出上述范围的事实先记录并评估，不默认为许可。

## 经验门禁

- Trigger：真实 NAS 验证布局与同 superblock 独立视图。
- Preflight check：读取 server-access/release-backup-restore/PowerShell 编码规则；固定新目录白名单，lstat 全部父路径与目标存在性，实际 mountinfo/fdinfo、所有别名/输入/数据/epoch/state 边界，原 fstab 与容器状态，挂载工具和 SMB 配置/库 pins。
- Blocker：缺/错/只读 CIFS、路径链接或未知别名、已有不明任务目录、权限或容量不足、SMB 映射/凭据/库引用无法闭合、原状态漂移或活动冲突。
- Verification：只读准入与实际新增布局分别生成独占原件；两次正式 prepare 的真实文件/锁/SMB 与当次 view 原件分别验证；before/after 比较原 mounts/fstab/业务及配置。
- Forbidden action：不卸载原 automount/CIFS、不改公司 NAS/fstab、不 remount 原 incoming、不用本地 fallback、不 privileged Docker/mock CIFS，不把准备成功当实际保全或恢复成功，不删除未知 hold 或覆盖原件。
- Evidence：本计划、3A1 BDD/TDD、原 mount-layout r1/r2、后续独立只读/布局与验证报告。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。缺视图或权限必须明确拒绝。
- 是否从根因和长期维护角度解决：是。用将来正式路径合同对应的独立窄视图验证自动准入，不把操作编号写入长期配置。
- 是否存在临时补丁或绕过：否。这里是明确隔离的验证设施，不作为生产路径或临时产品逻辑；后续清理仅针对本任务确认拥有的空控制目录/窄挂载，并保留验证原件。NAS 验证 hold/元数据没有自动删除授权。

## BDD 与执行约束

- Given 原业务和 CIFS 可见身份已固定，When 仅为本任务新增窄 bind，Then 原 mounts/fstab/容器及配置保持，新 mount 的 root 精确为仓库相对路径且 rw；新增量逐项记录。
- Given 同一静态 v2 模板和真实 CIFS/SMB，When 两个不同 operation 顺序完整 prepare，Then 生成各自的 0600/O_EXCL 派生与 view 原件，共享仓库锁正确释放，且零 quiesce/SQL/export/clear。
- Given 缺挂载、错误 UNC/root 或只读视图，When 首写准入，Then 明确拒绝且 `.repository-control` 尚未创建；不得将非 CIFS 普通目录当成功。

只读 helper 只读取指定配置并只输出凭据/库的路径与指纹引用，不输出值。远端 Python 设置有限 SIGALRM，宿主保存原 stdout/stderr/退出及超时事实。每个远端写入前重新记录 `GREEN: experience-preflight -> PASS`；本计划本身不是通过证据。真实布局动作与只读动作使用不同原件和明确 execute 范围，不自动重试。

## 18:29 UTC 真实只读准入增补

只读 prerequisites r1 已实际 exit0：父路径无链接，验证三目录和 NAS 的 spug-target-preservation 父目录均未存在；实际 CIFS 由 O_PATH/fdinfo 选中 mount1192，root=/、rw，NAS 可用约10.6TB，本地控制盘可用约872GB。挂载工具 `/usr/bin/mount` 为50320B/SHA `292af1c4ffbbf187a38fd00564419a40c2a11e9a3604989764e03558b87df2fb`。

原 source-repository 复制的57 credentialPath 在58不存在，r1 SMB 引用探测真实失败并保留。r2 证明58现有 fstab 挂载凭据为 `/root/intruoyi-nas-default-20261021/mount.credentials`，0600，含非空 username/password，仅保存原pin。默认 Python 未带现网 PYTHONPATH 查无库，不可据此认定现网缺依赖；随后按真实 target control PID30094 的环境验证，现网已有 smbprotocol1.17.0、pyspnego0.12.4、cryptography46.0.5、cffi2.0.0、pycparser3.0，实际库根 `/var/lib/docker/intruoyi-data/backup-restore-lab/test58-20261016/installed/runtime/lib/python3.12/site-packages`，模块原件与57匹配。不安装新库或改变现网 PYTHONPATH。

布局步骤在新 `validation-3a1-20261110/private` 下，直接在58将上述已pin的挂载认证转换为同服务器/共享的 `RepositorySmbCredential/v1`，文件0600且不输出值；此文件只供本验证，不替换任何原凭据。仅在新的验证 NAS 仓库根保留 `.validation-probe.json` 小原件；验证 O_EXCL、fsync、目录/FD身份、inotify与fcntl调用，再用新的签名加密 SMB 会话读回该精确小文件并核原字节。环境探测不计产品 prepare 或保全成功，也不声称独立故障域/服务端持久化/跨客户端锁排他已验证。

新增窄 bind 使用固定工具 `mount -i -n -o bind -- <backing> <target>`，再仅对该新视图 `--make-private`。阶段前持原目标共同锁，核固定原owner、工具、credential pins与新路径不存在；阶段后要求全部原mount行、fstab、五业务容器配置/镜像/状态/启动时间及原owner保持，仅允许这一已记录新mount。错误保留已创建路径与原始退出，不自动卸载或删除 NAS 资料，不重发布局。
