# 自动增量当前来源与恢复周期登记清单

## 范围与结论

- 只读盘点时间：2026-11-08 00:02–00:27（北京时间）。读取当前 18080 精确容器 `f615a60c76f46e4f6ae20ea6298f737fb9786684ce941fcc15763654461265bf` 的 simple/entry 配置；未操作无关 18081 容器。
- 三服只读通过本任务 `common.remote` 的固定 SSH/known-hosts 与有界 Python stdin 执行，只读 systemd、监听端口、配置和精确容器身份。未启动、停止、重载、安装、恢复或备份；未触碰审查服原任务 372。
- 当前页面 21 条绑定中 10 条 `selectable=true`、11 条 `selectable=false`。后者只证明已不用于当前选择，不证明数据或历史可以删除。
- 10 个可选来源全部有独立 source bridge；只有正式服 IntRuoyi SAFE 的源控制正在运行。另 9 个登记端口在升级前已无监听，不能归因于本轮自动增量代码，也不能为了覆盖入口擅自启动旧源。
- 本轮最小实际升级闭包：正式服当前 SAFE 源控制 + 正式/测试/审查三个 MAIN 覆盖控制；页面其它入口保留身份，明确控制不可用原因。禁止把连接失败说成“没有基线”并改发 FULL。
- 产品和测试保持冻结。本清单为只读证据，不是安装或真实备份验收。

## 当前 10 个可选入口

本机 bridge 文件均位于 `C:/Spug/runtime/private`，命名为下表 `sourceConfigRef + -bridge.private.json`。entry 配置逐项证明 `applicationId == sourceConfigRef`，引擎引用均为 `common-engine-minimal-unified-20261015-r1`。

| sourceConfigRef | bridge 端口 | 实际物理组 | 升级前控制状态 |
|---|---:|---|---|
| intruoyi-57-safe-20261024-v1 | 32657 | MAIN57 | active，远端 32657，PID 13785 |
| intruoyi-57-fast-20261024-v1 | 32857 | MAIN57 | 无对应监听、无对应已登记 systemd 源服务 |
| intruoyi-59-safe-20261024-v1 | 32659 | MAIN59 | 无对应监听、无对应已登记 systemd 源服务 |
| intruoyi-59-fast-20261024-v1 | 32859 | MAIN59 | 无对应监听、无对应已登记 systemd 源服务 |
| smallapp-57-retest-safe-namespace3-20261024 | 29457 | SMALL57 | 无对应监听、无对应已登记 systemd 源服务 |
| smallapp-57-retest-fast-namespace3-20261024 | 29657 | SMALL57 | 无对应监听、无对应已登记 systemd 源服务 |
| smallapp-58-switch-safe-20261024 | 23258 | SMALL58 | 无对应监听；登记 MySQL/MinIO 均 exited |
| smallapp-58-recovered-fast-20261023 | 20758 | SMALL58 | 无对应监听；登记 MySQL/MinIO 均 exited |
| smallapp-59-retest-safe-20261024 | 24059 | SMALL59 | 无对应监听、无对应已登记 systemd 源服务 |
| smallapp-59-retest-fast-20261024 | 24259 | SMALL59 | 无对应监听、无对应已登记 systemd 源服务 |

MAIN57 本机现有 SSH 同时转发 `42657 -> 远端32657`、`32657 -> 远端32657`，不能把本机 42657 当成远端监听端口。源服务为 `spug-intruoyi-source-57-20261105.service`。

主 bridge 含 31 个 sourceConnections 和 124 个 targetConnections，但默认 `sourceConfigRefs` 只有 4 条旧引用；安装范围必须从实际 selectable binding → entry.sourceConfigRef → sourceConnections 逐项推导，不能只看默认数组。

## 固定配置引用

`R57=/var/lib/docker/intruoyi-data`，`R58=/var/lib/docker/intruoyi-data`，`R59=/mnt/intruoyi-data`。除当前 MAIN57 外，下列配置存在和摘要已读回，代表登记原件；并不表示控制正在运行或原配置已满足当前全部准入。

| 入口 | 控制配置 |
|---|---|
| MAIN57 SAFE | R57/spug-intruoyi-57-safe-20261024-v1/configuration/control-binlog-tmpfs-20261107-v3.json |
| MAIN57 FAST | R57/spug-intruoyi-57-fast-20261024-v1/configuration/control.json |
| MAIN59 SAFE | R59/spug-intruoyi-59-safe-20261024-v1/configuration/control.json |
| MAIN59 FAST | R59/spug-intruoyi-59-fast-20261024-v1/configuration/control.json |
| SMALL57 SAFE | R57/spug-retest-20261024-source57-safe-v3/configuration/control.json |
| SMALL57 FAST | R57/spug-retest-20261024-source57-fast-v3/configuration/control.json |
| SMALL58 SAFE | R58/smallapp-business-20261023/retest-switch-20261024-safe/configuration/control.json |
| SMALL58 FAST | R58/smallapp-business-20261023/retest-recovered-source-20261023-fast/configuration/control.json |
| SMALL59 SAFE | R59/spug-retest-20261024-safe/configuration/control.json |
| SMALL59 FAST | R59/spug-retest-20261024-fast/configuration/control.json |

源 owner pin 是 `control.sourceConfigurations[sourceRef]`；覆盖 owner pin 是 `control.restoreConfigurations[sourceRef][targetRef]`，不能少取 sourceRef 一层。owner 中 `sources[sourceRef].configurationPath` 指向捕获配置，`targets[targetRef].replacement` 指向覆盖合同。私密凭据引用没有解引用或输出。

## 物理来源分组和 epoch 配对

SAFE/FAST 是否同组由登记的完整 sourceIdentity、databaseUuid、MySQL/MinIO 完整容器 ID、物理挂载和 sourceLockPath 共同判断。以下 UUID 是已验证配置原件中的值，本次没有执行 SQL 查询当前 UUID。完整 ID/pin 留在任务 PRIVATE 摘要，表中只缩写便于阅读。

| 组 | sourceIdentity 前缀 | 配置 UUID | MySQL / MinIO ID 前缀 | 状态及物理目录 |
|---|---|---|---|---|
| MAIN57 | a36d337b14a9 | 0fa6c22b-5a90-11f1-ade1-0242ac150002 | 9a288d20d254 / b9f1d48ecf88 | 均 running；/opt/intruoyi/runtime/data/mysql、minio |
| MAIN59 | 18f689ead789 | a4f03708-cc74-11f1-9cce-0242ac1def16 | 4376cb8d12c9 / eb40cfe31e80 | 均 running；实际在 /mnt/intruoyi-data/docker-engine/volumes 下 |
| SMALL57 | e9fc6ba4d1d0 | e936961d-ce21-11f1-9f3e-0242ac120002 | 09a7210373b3 / 9af094862946 | 均 running；R57/rehearsal-smallapp-20261022/instance/data |
| SMALL58 | 0bcfe2393e9c | c93e230b-cecc-11f1-9f7b-0242ac1cf320 | fa6c66f5bf06 / cfea9f0b8405 | 均 exited；/var/lib/docker/volumes/smallapp-58-retest-20261023-recovered-r2-{mysql,minio}/_data |
| SMALL59 | 847a4c69a099 | e0ad93a7-ce22-11f1-9fa0-0242ac180002 | 07b05eb464ae / 535367d13159 | 均 running；R59/rehearsal-smallapp-20261022/instance/data |

同组 SAFE/FAST 必须使用相同完整 epoch policy，不能按 mode 创建不同恢复周期；不同组即使同 IP 也不得共用。

- MAIN57 源锁：`R57/prod-spug-backup-20261019/source-locks/source.lock`，与正式 MAIN 覆盖 `replacement.lockPath`、UUID 完全一致；本轮源端 policy 与正式覆盖 `replacement.backupEpoch` 必须精确相同。
- MAIN59 源锁：`R59/backup59-lightweight-20261022/source-locks/source.lock`，与审查 MAIN 覆盖完全相同。未来启用该源 SAFE/FAST 时必须沿审查 MAIN 自身 epoch，不能沿正式源 epoch。
- SMALL57 源锁：`R57/smallapp-safe-20261022/source-locks/source.lock`。当前可选覆盖目标为空；不能与正式 MAIN 配对。
- SMALL59 源锁：`R59/smallapp-safe-20261022/source-locks/source.lock`。当前可选覆盖目标为空；不能与审查 MAIN 配对。
- SMALL58 源锁：`R58/smallapp-business-20261023/retest-recovered-source-20261023-fast/source-locks/source.lock`；其旧覆盖 `smallapp-58-retest-20261024-original-source-replace`（控制 23858，无监听）与该组 UUID/锁相同。该旧覆盖控制位于 `R58/smallapp-business-20261023/retest-executor-20261024-original-source-replace/configuration/control.json`。
- MAIN58 覆盖 UUID 是 `20ca4c6c-cc31-11f1-9b95-0242ac1deb16`、锁是 `R58/prod-nas-restore-test58-20261020/target-r3/main-backup-restore.lock`，与 SMALL58 完全不同。当前页面没有 MAIN58 备份源，不能把 SMALL58 身份填给 MAIN58 的 epoch；MAIN58 policy 应由实际 MAIN58 合同明确登记，并由将来真实 MAIN58 捕获源复用。

## 当前 MAIN 覆盖最小集合

三个目标 bridge 均只授权来源 `intruoyi-57-safe-20261024-v1`。它们接收正式备份，但 epoch 属于各自被覆盖的物理实例。

| 目标引用 | 当前服务 / 端口 | 当前 control 配置 |
|---|---|---|
| intruoyi-main-57-safe-restore-20261105-v2 | spug-main-restore-57-20261105-v2.service / 43657 | R57/spug-main-restore-20261104-v3/configuration/control-43657-mainv2-9dce318.json |
| intruoyi-main-58-safe-restore-20261104-v1 | spug-main-restore-58-20261104-v3.service / 43658 | R58/spug-main-restore-20261104-v3/configuration/control-58-packaged-frontend-0c5828a.json |
| intruoyi-main-59-safe-restore-20261104-v1 | spug-main-restore-59-20261104-v3.service / 33659 | R59/spug-main-restore-20261104-v3/configuration/control-59-frontend-9c93449.json |

检查时这三个 replacement 尚无 backupEpoch，不能把现有同 UUID 解释成“从未恢复”。启用新 policy 后旧点无 sidecar 应明确要求新 FULL。

## 原有不可用入口应如何呈现

- 9 个源统一准确说明“该来源已登记，但当前备份控制服务未运行或未连通，无法规划增量”；保留来源和历史记录，不删除、不静默隐藏、不改向另一个源、不降级为 FULL。
- SMALL58 可进一步说明“登记的数据库和对象存储容器当前已停止”。只读证据证明 exited，未调查是谁、何时、为何停止，不能声称是本轮导致或推测历史操作原因。
- MAIN59 旧 SAFE/FAST 捕获配置仍登记 MinIO `/var/lib/docker/volumes/intruoyi-prod-nas-restore59-20261020-native-minio/_data`；实际同一容器 RW 挂载为 `/mnt/intruoyi-data/docker-engine/volumes/intruoyi-prod-nas-restore59-20261020-native-minio/_data`。这是明确的路径合同漂移，恢复该来源前必须按现有物理实例重新核完整登记，不能直接启动旧配置、照搬模板或换源身份。
- 其余 smallapp 的 MySQL/MinIO 虽 running，也不表示源控制可用；未核全部 writer、归档和程序准入，不能宣称可备份。
- 未来若单独恢复旧入口，必须升级其真实控制包、恢复有界且可信的转发、复核配置/程序/容器/数据锁，并让同物理源全部模式与实际覆盖目标共享 epoch。此项不属于本轮自动启动范围。

## 只读证据

证据位于 `C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106`，未提交私密文件：

- `automatic-source-services-172.30.30.{57,58,59}.private.json`：systemd 当前 MainPID、执行配置、程序路径及目标端口监听。
- `automatic-source-physical-172.30.30.{57,58,59}.private.json`：10 源配置/owner/capture pins、sourceIdentity、UUID、锁、精确容器及数据挂载。
- `automatic-target-pairing-172.30.30.{57,58,59}.private.json`：当前 MAIN 目标控制/owner pins 与 replacement UUID、锁。
- `automatic-smallapp-target-pairing-172.30.30.58.private.json`：旧 SMALL58 覆盖与两模式源的独立配对。
- 初次通用目录扫描误选跨机历史引用时遇缺文件/空 active 路径，已停止并保存明确错误，随后依据当前 simple progressRoot 与源专属配置定位；未把失败扫描当作成功或静默改用其他源。

状态：只读清单 completed；整项功能交付状态由父任务控制。
