# 独立保全视图持久控制 TDD

## 原生 Docker nsfs 兼容补充

后续58只读PREPARE确认同路径还有 `systemd-1` autofs 自动挂载底座，CIFS 的 parentId 正好指向该底座；这属于原 systemd automount 正常拓扑。新增BDD：接受精确一层 autofs(systemd-1, root=/) + 其直接子CIFS(登记UNC, root=/)，实际可见层仍须由O_PATH/fdinfo证明为可写CIFS；未知同路径叠层、父子关系错误或额外层全部拒绝。原挂载和fstab不修改。

- RED：6项 automount 场景，1 FAIL / 5 PASS / 45 deselected，合法原 systemd automount 拓扑被误拒。
- GREEN：同6项，6 PASS / 45 deselected，native 0。
- REGRESSION：隔离 Linux `run-preservation-view-linux.py regression-r5`，51项 view + 33项原 staging，84 PASS，native 0；pytest 2.12秒，完整载体11.484秒。源快照614件，SHA `6b37f2b6bb49d53dfe0afc83627fefd4825b8b492f1282c39c7584f9f788a3f1`；输入保持、容器移除、stderr 0，remoteWrites=0。真实服务器安装尚未执行。

- BDD：Given 实际 Docker 网络命名空间使用 nsfs `net:[4026531992]` root；When 读取整张 mountinfo；Then 接受该内核格式，CIFS 和其它文件系统仍要求绝对 root，畸形 nsfs root 拒绝。
- 实际57/58 PREPARE均在写入前停止；58为 VIEW_MOUNTINFO_PATH，已只读确认15条真实 nsfs root；57为父载体误用小配置读取上限验证31MB解释器，载体改用通用 Runtime pin_file。未安装文件、挂载或重载服务。
- RED：新增4项 parser 场景，native1，1 FAIL/3 PASS/41 deselected，合法nsfs被误拒。
- GREEN：native0，4 PASS/41 deselected，0.09s。
- REGRESSION：隔离Linux实际45视图+33暂存共78 PASS/4.33s，native0，原输入保持、容器移除、stderr0；source snapshot cd3e471fe6111d6249909d43aadb791e2bd9aec8aaa884f59a90ba124194cf29，614文件。保留原PREPARE失败，不将单元测试误称真实挂载成功。

## Current Status

ready_for_closeout；实现和有限回归已通过，已发父任务独立审查，等待父统一审查/提交及实际主机验收。仅新增独立helper、测试及本文，不连接服务器、不改旧载体/共享日志、不提交；未创建worktree或残留测试容器。

## 目标、里程碑与预期验证

1. DONE：阅读已验证O_PATH/mount载体，设计固定配置schema、install_once/startup和oneshot文本生成签名；父明确批准后才实现。
2. DONE：BDD→RED→GREEN：纯配置/首mount前完整预检、精确原mount保留及唯一新view身份、失败保留与启动不创建目录。
3. DONE：有限回归74 PASS；独立Linux协议测试可注入系统边界，明确不代表实际mount；最终真实host验证由父任务执行。

## 设计约束检查

- 是否引入fallback/降级/吞异常：否；未知身份、路径、已有mount、工具漂移均拒绝。
- 是否从根因和长期维护角度解决：是；独立固定pins的持久视图服务承接原NAS挂载，保持封闭16文档根。
- 是否存在临时补丁或绕过：否；不触碰fstab/原挂载、不自动卸载或回退。

## 经验门禁

- Trigger：保全CIFS视图、bind/private挂载、O_PATH/fdinfo身份、oneshot持久控制。
- Preflight check：固定host/UNC/root/rw/精确relativePath/view位置；工具/Python/helper/config实际pins；原mountinfo与O_PATH身份、所有目录无软链/叠层、首mount前全部条件通过。
- Blocker：原挂载/目录身份或pins不符、已存在view挂载、叠层、别名、原mountinfo行消失或任意新mount身份不唯一。
- Verification：先RED再最小实现和有限回归；系统边界注入仅验证协议，真实主机O_PATH/mount验收由父任务独立留证。
- Forbidden action：不改fstab/原挂载，不自动umount/rollback/retry，不写封闭16文档根，不自动备份/reload控制/启停业务，不用mock PASS代替实际挂载。
- Evidence：父计划“独立保全视图的持久控制”，private既有 `setup_preservation_validation_layout_remote_20261110_r1.py` 载体；后续父审设计与原始测试证据。

## BDD

- Given 精确固定源CIFS与工具pins、新自有目录；When install_once完成全部预检；Then 仅创建自有backing/view并bind/private，逐原mountinfo行保持，O_PATH证明唯一新mount和同源inode/device。
- Given 合法已存在自有目录且view当前无挂载；When startup；Then 仅验证既有目录后挂载，不创建目录、不改fstab或其它服务。
- Given 任何schema/源/工具/目录/已有mount漂移；When 操作；Then 首mount前拒绝；mount后失败保留现场和明确阶段，不自动卸载/重试。
- Given 首轮安装需要同一持久oneshot承接；When 明确render_service(mode='install_once')；Then 只为本次生成install_once命令，成功后的startup文本替换/daemon-reload/active回执由父执行；默认仍为startup，未知mode拒绝。
- Given bootstrap读取文件导致正常atime更新；When 核验Python/helper/config；Then 排除atime，仍要求mode/uid/gid/nlink/size/mtime/ctime/device/inode稳定且精确bytes+SHA；任何pin漂移均在执行helper前拒绝。

## 执行证据

- bootstrap：已确认父计划当前范围和上一子任务由父显式提交；当前仅进行独立设计，不承接服务器写入授权。
- 设计已发父审，尚无实现：`MainProgramPreservationView/v1` 配置固定host/targetParent/源mountpoint/relativePath/view/source合同和Python/mount/helper pins；helper/config在targetParent独立installed-tools/main-preservation-view-<helperSHA前12>/目录。API `validate_configuration`、`install_once`、`startup`、`render_service`；两阶段调用允许注入system边界，仅用于协议单元。
- preflight拟先核config/self/工具原pins、源CIFS唯一O_PATH可见mount/root/UNC/rw及所有原mount行，再核所有路径无别名/叠层/嵌套和全新或合法既有末级目录。install_once只建末级自有backing/view，已有共享祖先缺失即阻断；startup不建目录。bind和make-private后分别用可见mount ID、fstat device/inode及mountinfo精确增量验证；任何失败留现场。
- 权限细节待父审：已验证载体对CIFS backing只要求uid0且无022；不将mkdir0700请求误当CIFS回读必须0700，拟local view要求0700、NAS backing采用已验证无022合同，不chmod原NAS。
- service拟独立oneshot、RequiresMountsFor原NAS根、After network-online/remote-fs；固定Python的stdlib bootstrap在exec helper前核Python/helper/config bytes+SHA，无ExecStop/Restart、不写unit、不daemon-reload。实际systemd和真实host挂载验收由父任务执行。
- RED: `python -X utf8 PRIVATE/run-preservation-view-linux.py red-r1` -> native exit 1；1 failed + 34 setup errors，均为预期 `MISSING_PERSISTENT_PRESERVATION_VIEW_HELPER`；未创建实现。固定image/wheels/有限预算，源609文件SHA `0ddbf816b121eba2cf0b4aaeba386df288c20bee503e527ca9b26f72ff7f7bc0`，inputsUnchanged=true/containerRemoved=true/remoteWrites=0。这是隔离协议RED，并非真实挂载或业务验收。
- GREEN: `python -X utf8 PRIVATE/run-preservation-view-linux.py green-r1` -> native exit 0；35 passed in 0.17s；snapshot `326860d70477879d7fb9b948e3393e7b6ed965ea06aa724ab07aadc8d43c9119`。
- RED: `... red-r2` -> 3 failed/36 passed；工具在bind后变化未阻止第二条命令；bootstrap完整stat比较将真实读取引起的atime误判为READ_CHANGED。未知optional测试当时也改变了原来源行，已将测试修正为仅改变新view行，未更改产品后重跑。
- RED: `... red-r3` -> native exit 1；4 failed/35 passed；新增view未知optional确实未被拒绝，另3项同上。snapshot `9b0dc978f8166bebe540e732393ac33548f81feb025c9352f5e1c84b9741f242`；随后才增加逐命令工具再验、private optional必须为空和稳定文件身份（排除atime、保留ctime/mtime等）。
- GREEN: `... green-r2` -> native exit 0；39 passed in 0.19s；snapshot `2dd4f49e6d0f880d45ad90f6c147d925da7bce6aeeaa3c1469e2f1394b6f94d5`。
- 父审补充明确首轮持久unit激活方案：首次同一unit显式install_once成功后，由父替换成startup文本并daemon-reload，保留RemainAfterExit active；不放宽已有mount拒绝，不自动umount。
- RED: `... red-r4` -> native exit 1；2 failed/39 passed；render_service尚无mode参数，TypeError符合预期。snapshot `8b4c2be2d80f5763dac9c983b0f5c3469da2026a2549ab5226778bf91086c166`；随后最小加入显式参数和严格二选一校验。
- GREEN + REGRESSION: `python -X utf8 PRIVATE/run-preservation-view-linux.py regression-r1` -> native exit 0；74 passed in 2.08s（新41+相邻文件暂存33）；snapshot612文件，tar9553920 bytes，SHA `978b5e737a9bf8125562f54e5ea5143b728638456d1c49383b74e9da2bfe4227`；stdout179 bytes SHA `d0ab07dff5271e424c40090068753b89f9a63aca7145038fdb950181d077b8f7`；stderr0。
- 全部运行固定image `sha256:14a4933e6cef421424f7a66d89a3f4eafcbd0d90e0a822251f298e05132dc735`、既有12个已pin wheels、network none、read-only root、cap-drop ALL、no-new-privileges、pids128、512MiB、cpu1、work256MiB/tmp64MiB、600秒进程预算。每次inputsUnchanged=true/containerRemoved=true/actualBusinessRestore=false/remoteWrites=0；无放大预算、无包重建。
- 范围校验：两份Python源码显式UTF-8读取并compile成功、无行尾空格；全仓git diff --check命中父共享execution-log.md原有EOF空行，不属于本项3文件，未修改该文件。

## 最终接口与交付边界

- `validate_configuration(config)`：纯schema/固定host57/58/59及原targetParent/精确UNC/root/rw/relativePath/view/tool pins合同；返回副本。
- `install_once(config, *, system=None)`：首写前全部门禁，仅独占创建backing和view两个叶子，再bind/private并逐次核验；不创建缺失共享祖先。
- `startup(config, *, system=None)`：严格要求既有backing/0700 local view；无mkdir；已有view挂载包括同一源也拒绝。
- `render_service(config, *, configuration_pin, mode='startup')`：纯生成独立oneshot文本；固定stdlib bootstrap先验证Python/helper/config再exec；仅显式mode='install_once'生成首轮文本。无ExecStop/Restart、无写unit/reload/备份/业务动作。
- CLI：`--config PATH --config-bytes N --config-sha256 SHA --mode install_once|startup`；Linux/root/O_PATH、配置0400和工具/自文件pins、65秒上限。ViewFailure链式保留原错误及phase/createdPaths/commands；不回退、卸载或重试。
- helper 22480 bytes，SHA `62de7473e568a4556d854271893ece308ee5d871fc616c538b8b431a5957905e`；test15485 bytes，SHA `67617ab1c098eafbe8c75ddbcfa0cb2dc7f101a37414cac9a50eecad01846e04`。
- 系统边界注入仅为协议单元；真实O_PATH smoke只读观察当前Linux隔离容器。未运行真实bind/private、systemd或服务器动作；真实NAS/主机/开机持久控制与业务恢复结果均未由本子项验收。
