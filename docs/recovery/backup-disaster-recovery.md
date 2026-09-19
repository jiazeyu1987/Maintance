# 测试服务器备份与恢复演练方案

日期：2026-09-18

对象：测试服务器备份恢复按钮化设计、ChatGPT 网页介绍稿、后续实现验收基线

## Scope

本方案用于向 ChatGPT 网页或后续实现团队说明：当前测试服务器的已知现状、一个按钮执行备份、选择备份包后恢复数据的正确架构，以及升级、降级、换硬件、版本差异和依赖缺失时应如何阻断或验收。

本方案只基于本地文档和源码静态核对，不代表已对测试服务器执行了实时健康检查、真实备份、真实恢复或远程演练。未经当轮明确授权，不访问测试服务器、不执行备份恢复脚本、不写数据库、不重启服务、不修改业务数据。

非目标范围：

- 不把 ChatGPT 网页或浏览器变成 SSH 终端。
- 不在前端保存服务器密码、数据库密码、MinIO 密钥、私钥或连接串。
- 不为不兼容版本做自动降级、自动跳过、吞异常或默认成功。
- 不把生产恢复、审查服恢复、备份服恢复混入测试服按钮流程。

## 总体结论

正确方案不是“网页按钮直接执行远程 shell”。正确方案是：

1. ChatGPT 网页或管理后台只作为受权限保护的操作入口。
2. 后端提供固定白名单动作：备份、恢复演练、恢复数据、查询状态、导出证据。
3. 后端把动作转成已有 `backup-ops` / `runtime-control` 的异步任务，生成 `operationId`。
4. 前端只轮询或订阅任务状态，不根据请求返回自行判断成功。
5. 备份集先通过 manifest、校验和、恢复集完整性后，成为可发起隔离演练的“演练候选”；只有绑定当前目标的有效演练报告、兼容性检查和保护条件全部通过后，才能成为“受控恢复候选”。不能把两种候选合并成一个状态。
6. 恢复按钮必须先做预览和阻断检查；不满足条件时 fail fast，不能降级为“尝试恢复一下”。

因此，“一个按钮备份”可以做成真实按钮；“一个按钮选择备份包恢复”应做成“选择候选包 -> 兼容预览 -> 必要时先恢复演练 -> 明确确认 -> 异步恢复”的受控流程。

## 当前已证实现状

静态核对依据包括 `E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\IntRuoyiBackend\script\backup-ops`、后台 `BackupPlanController`、`RuntimeControlController`、前端备份计划页和运行控制台页。

已知测试服务器基线：

- 测试服务器：`172.30.30.58`。
- 测试前端入口：`http://172.30.30.58:8081/`。
- 测试后端健康检查：`http://172.30.30.58:48081/actuator/health`。
- 展厅入口：`http://172.30.30.58:8083/`。
- 测试服务器运行根目录文档基线：`/opt/intruoyi/runtime`。
- 远端数据盘文档基线：`/var/lib/docker`，数据根：`/var/lib/docker/intruoyi-data/runtime-data`。
- 测试 MinIO 容器配置：`ragflow_compose-minio-1`。
- 当前备份运维配置 schema：`v2-minimal`。
- 当前备份仓库环境配置为 `test`。
- 当前配置中最大新鲜度阈值为 `25` 小时。
- 当前配置中保留策略包括：远端保留 30 天、最近备份点 5 个、最近全量链 4 条、最少可恢复链 2 条。
- 当前配置中对象桶为 `yudao`，演练桶为 `yudao-rehearsal`。
- 当前配置中测试服恢复演练槽位根目录为 `/backup/int-ruoyi/rehearsal/runtime`，演练后端端口为 `48082`，演练前端端口为 `18081`。

已存在的后台能力：

- 备份计划页后台已有 `POST /infra/backup-plan/backup-now?backupKind=FULL|INCREMENTAL`，用于触发立即备份。
- 备份计划页已有状态、计划、历史、证据导出能力。
- 运行控制台已有 `GET /infra/runtime-control/restore-candidates`，用于查询可恢复候选。
- 运行控制台已有 `POST /infra/runtime-control/actions/preview` 和 `POST /infra/runtime-control/actions`，用于预览和执行 `rehearsal` / `restore-data` 等动作。
- 当前前端备份计划页已有立即全量备份、立即增量备份和历史列表；恢复操作目前仍在运行控制台中处理。
- 当前运行控制台前端已有 `立即备份`、`恢复演练`、`恢复数据` 三类动作，并要求选择恢复候选。

需要注意的现有差异：

- 现有网页后台备份入口会传 `FULL` / `INCREMENTAL` 备份类型。
- 现有 `.bat` 控制台的备份按钮静态看未显式传 `-BackupKind`，而当前 `backup-ops.ps1` 对 `backup-now` 要求显式备份类型；因此后续 ChatGPT 网页不应直接绑定 `.bat` 文件，应绑定后端 operation gateway 或修正后的脚本契约。
- 当前 `restore-data` 脚本拒绝恢复到 `prod`，只允许测试服或备份服目标。
- 当前静态恢复动作要求恢复集 `COMPLETE`、DCC manifest、checksums、MySQL / object 证据、演练状态 `PASSED`、当前 runtime `IMAGE_TAG` 与恢复集 image tag 匹配；这只覆盖受控恢复，不代表当前接口已经支持从 `NOT_RUN` 演练候选发起首次隔离演练。后续实现必须拆分演练候选和受控恢复候选，否则会形成候选循环依赖。

尚未实时验证的状态：

- 当前测试服是否正在运行、当前 `IMAGE_TAG`、当前 Docker 镜像 digest、当前数据库版本、当前 MinIO 实例状态、当前磁盘容量、当前 NAS/备份目录可写性，未在本任务执行实时检查。
- 当前是否存在最新 `COMPLETE` 且已演练通过的备份包，未在本任务远程查询。
- 当前 RTO / RPO 尚未由业务正式定义，不能仅凭脚本配置宣称达标。
- `E:\IntRuoyi\IntRuoyiBackend\docs\recovery\current-dr-readiness.md` 曾记录当前灾备门禁为 `BLOCKED`；后续历史任务存在真实演练证据，但不能替代本次上线前实时门禁检查。

## Inventory

按钮化备份恢复必须覆盖以下资产清单。缺少任何一类的恢复策略，都不能宣称“测试服可恢复”。

| 类别 | 必须纳入的内容 | 恢复策略 |
| --- | --- | --- |
| 程序版本 | 后端、前端、展厅、OnlyOffice 等镜像 tag 与 digest，Compose 文件，release manifest | 只按 manifest 中的固定版本恢复，禁止使用 `latest` |
| MySQL | 数据库 dump、binlog 增量链、字符集、时区、collation、sql_mode、迁移台账、schema 指纹 | 全量基线 + 真实 binlog 增量；恢复前核对 schema / migration |
| MinIO / 对象存储 | `yudao` 桶对象、inventory、对象 hash、增删改 tombstone、DCC 文件清单 | 按 inventory 和 checksum 恢复，DCC 文件必须抽样下载验真 |
| DCC / 业务文件 | 受控文件路径、文件 hash、签章或历史验证所需材料 | manifest 必须记录并在演练中验证 |
| Redis | session、缓存、业务 Redis 数据分类 | 默认只记录恢复策略；session/cache 可清理重建，业务 Redis 数据必须单独定义 |
| 配置 | `.env` 结构、非敏感配置、端口、域名、文件配置、租户相关配置指纹 | 包内不得含秘密；恢复时按目标环境映射 |
| 秘密 | SSH、MySQL、MinIO、三方接口密钥、签章密钥 | 不进入备份包，只记录 `secretsRef`、保管人、版本和可用性验证 |
| 外部依赖 | NAS、Docker、Compose、对象锁或 WORM、副本服务器、三方接口 | 记录依赖与阻断条件；依赖不可用时不能 claim success |

## Backup

备份按钮的正确行为：

1. 操作人进入备份页，系统展示当前测试服状态、最近备份点、最近演练状态和阻断项。
2. 操作人选择 `FULL` 或 `INCREMENTAL`。如果产品上只做一个“立即备份”按钮，也必须在按钮前配置默认策略或弹出备份类型选择，后端必须收到明确 `backupKind`。
3. 后端创建异步 operation，返回 `operationId`。
4. 后端加全局互斥锁，禁止备份、恢复、演练并发。
5. 后端执行 preflight：目标环境必须是 `test`，备份根目录存在且可写，MySQL/binlog/MinIO/DCC/配置清单可读，当前版本指纹可采集，外部 writer 已隔离或可证明不存在。
6. 进入写入窗口：停止或隔离后端/前端 writer，并证明没有绕过后端直接写库或写对象存储的外部写入者；不能证明时阻断。
7. 生成备份包到临时目录，完成后原子发布为正式备份点。
8. 生成并保存 `manifest.json`、`checksums.txt`、`operation-report.json`、`evidence-manifest.json`。
9. 只有 manifest 状态为 `COMPLETE` 且 checksum 通过的备份点，才出现在演练候选中；受控恢复候选还必须有绑定当前目标的有效演练报告。

备份包必须包含：

- `backupId`、`parentBackupId`、`baseBackupId`、创建时间、源环境、目标环境、工具版本。
- 程序版本：`IMAGE_TAG`、镜像 digest、Compose 指纹、运行配置指纹。
- MySQL：全量 dump 或增量链位置、binlog 文件和 position、数据库版本、schema 指纹、迁移台账摘要。
- MinIO：bucket、对象列表、对象 hash、对象增删改记录、tombstone。
- DCC：受控文件 manifest、hash、样本验证路径。
- Redis policy：清理、重建、跳过或业务数据恢复策略。
- 配置和秘密引用：非敏感配置 hash、`secretsRef`、密钥保管人，不包含明文秘密。
- 校验与证据：SHA-256、文件数量、字节数、证据报告路径、演练状态。

禁止事项：

- 禁止把每日全量备份改名为“增量备份”。
- 禁止把不完整目录展示为可恢复候选。
- 禁止备份失败后返回默认成功。
- 禁止把明文密码、token、私钥、连接串写入备份包、日志或证据。
- 禁止把 NAS 不可用时的本地临时目录当作自动 fallback 仓库。

## Retention

当前配置可作为初始保留策略参考：远端保留 30 天、最近备份点 5 个、最近全量链 4 条、最少可恢复链 2 条、最大新鲜度 25 小时。`25` 小时是配置的新鲜度阈值，不是业务 owner 已批准的 RPO，也不代表备份点已经通过真实恢复演练。

正式方案仍需补齐：

- 谁审批删除旧备份链。
- 删除前如何证明至少保留 `minimumRecoverableChains` 条完整可恢复链。
- 是否需要 WORM / 对象锁 / 异地副本。
- NAS 空间达到阈值时是否阻断新备份，还是先由人工审批清理。
- 过期备份是否仍可能因审计要求保留。

按当前项目规则，正式服 `/mnt/nas` 是共享盘，任何任务都禁止删除、清空或移除挂载/fstab。即使是测试服方案，也不能把“空间不足”处理成自动清理共享盘。

## RTO

当前没有已审批的业务 RTO。不能在介绍中宣称“多久内一定恢复”。

建议定义三档：

| 场景 | 建议 RTO 目标 | 说明 |
| --- | --- | --- |
| 测试服普通数据误操作 | 以演练实测值为准，可先目标 2 小时内 | 需要先有完整恢复包和演练报告 |
| 测试服整机重建 | 以硬件/镜像拉取/数据恢复实测值为准，可先目标 4 小时内 | 换机时还要重建 Docker、网络、存储、域名 |
| 生产级灾难恢复参考 | 需业务审批 | 本方案不擅自定义生产 RTO |

RTO 只能来自真实演练计时，包括 preflight、恢复、启动、健康检查、登录、文件下载和业务路径验证的总耗时。

## RPO

当前没有已审批的业务 RPO。不能仅凭“每天增量”宣称 RPO 达标。

建议初始口径：

- 如果每周全量 + 每日真实增量链都正常、最近增量不超过 25 小时、且恢复演练通过，则测试服可暂按“最近一次成功可恢复备份点”描述实际 RPO。
- 如果最近备份失败、链断裂、checksum 失败、binlog 缺失、对象 inventory 缺失或演练失败，则 RPO 状态为 `BLOCKED`。
- 如果业务需要小时级 RPO，必须增加更高频率 binlog/object 增量和对应恢复演练，不能只调整页面文案。

## Restore

恢复按钮必须以“恢复候选”为中心，而不是以任意文件路径为中心。

恢复数据正确流程：

1. 用户点击“恢复数据”。
2. 后端分别返回演练候选和受控恢复候选：演练候选允许 `rehearsalStatus=NOT_RUN`，受控恢复候选必须绑定当前目标的 `rehearsalStatus=PASSED` 报告；两者都必须满足 manifest、checksum 和恢复集 `COMPLETE`。
3. 用户选择候选包。
4. 后端执行 preview：读取目标当前 fingerprint，包括环境、host、OS/arch、Docker/Compose、镜像 tag/digest、数据库版本、schema 指纹、迁移台账、MinIO bucket、Redis policy、磁盘容量、端口、域名和文件配置。
5. preview 比对备份包 manifest 与目标 fingerprint，输出 `PASS` 或明确 blockers。
6. 演练候选必须先走“恢复演练”到隔离槽位，不能直接覆盖当前测试服；只有生成未过期且绑定当前目标 fingerprint 的演练报告后，才可生成受控恢复候选。
7. `REPLACE_EXISTING` 恢复前必须创建当前目标的 pre-restore snapshot，并记录可回退路径；`REBUILD_EMPTY` 必须记录目标为空/已毁、资产归属和写入范围证明，不能伪造 snapshot。
8. 停止或隔离 writer。
9. 恢复 MySQL。
10. 恢复 MinIO / 文件对象 / DCC 对象。
11. 按 Redis policy 清理或恢复 Redis。
12. 启动服务。
13. 验证 backend health、frontend HTTP、登录、样本文件下载/hash、关键业务路径和恢复报告。
14. 生成 `restore-report.json`，并把 operation 状态置为 `SUCCESS`、`BLOCKED`、`FAILED` 或 `UNKNOWN`；进程终态未知时保持目标写保护，不能返回成功或伪造取消。

恢复成功的判定必须来自后端证据，不来自前端按钮返回。只要有一项关键验证失败，结论就是失败或阻断，不能显示成功。

## 升级、降级、换硬件和其他兼容矩阵

| 变化场景 | 正确处理 |
| --- | --- |
| 测试服务器应用已升级 | 比对当前 `IMAGE_TAG` / digest、迁移台账和备份包 schema；旧数据恢复到新程序必须有已测试的前向迁移路径，否则阻断 |
| 测试服务器应用降级 | 如果当前数据库 schema 或对象格式比备份包/目标程序更新，必须阻断；除非存在已测试的回滚迁移和回滚包 |
| 仅恢复数据但不切程序版本 | 必须要求当前 runtime 与恢复集 image tag 兼容；当前脚本已要求 image tag 精确匹配，这是安全默认值 |
| MySQL 版本升级 | 逻辑 dump 通常比物理快照更可迁移，但仍要核对字符集、collation、sql_mode、GTID/binlog、保留字和迁移台账 |
| MySQL 版本降级 | 默认阻断；没有官方支持矩阵和实测演练时，不能把高版本数据恢复到低版本引擎 |
| MinIO 版本变化 | 核对 bucket、versioning、对象锁、路径、hash、metadata；抽样和关键对象必须下载验真 |
| Redis 版本变化 | 区分 session/cache 与业务 Redis 数据；不盲目恢复旧 dump；按 policy 清理、重建或专门恢复 |
| 更换硬件 | 应用级备份可跨硬件，但必须核对 CPU 架构、OS、Docker/Compose、磁盘容量、inode、IOPS、挂载路径、时钟同步、网络和端口 |
| 更换 IP / 域名 | 恢复包不得强行带入旧 host 绑定；目标环境映射必须显式配置并验证 allowed origins、回调地址、文件域名、MinIO URL |
| 更换数据盘 / NAS | 必须验证挂载点、权限、剩余空间、文件系统语义和不可误删共享盘；缺一阻断 |
| 镜像仓库或离线镜像不可用 | 阻断；禁止自动拉 `latest` 或找相似 tag |
| 密钥轮换 | 备份包只含 `secretsRef`；恢复前验证密钥可用。历史签名/加密材料不可用时，相关业务路径不能判定成功 |
| 外部系统不可用 | 若关键业务路径依赖外部系统，则恢复结论只能是部分可用或阻断，不能显示全量成功 |
| 备份包缺文件或 hash 不一致 | 阻断；禁止尝试半包恢复 |
| 当前目标已有重要数据 | 必须先做 pre-restore snapshot 和人工确认；恢复覆盖后保留回退证据 |
| 备份过程中断 | 标记 `INCOMPLETE`，永不进入候选列表 |
| 恢复过程中断 | 保持目标隔离，优先使用 pre-restore snapshot 回退；不能继续对外提供“已恢复成功” |

## 推荐 UI

一个页面可以分成四块：

1. 当前测试服状态：测试服 IP、当前版本、健康状态、磁盘/NAS/DB/MinIO/Redis 状态、最近备份、最近演练、当前 Gate。
2. 立即备份：选择 `FULL` 或 `INCREMENTAL`，显示 preflight blockers，点击后创建异步 operation。
3. 备份包列表：显示 `backupId`、类型、链路、源版本、目标环境、checksum、演练状态、恢复可用性、证据导出。
4. 恢复操作：先选演练候选或受控恢复候选，再 preview。只有受控恢复候选的 preview、演练、权限、责任人确认和目标保护条件全部通过后，恢复按钮才可用。

危险操作文案建议：

- 备份按钮：`立即备份测试服数据`。
- 恢复演练按钮：`在隔离槽位演练恢复`。
- 恢复数据按钮：`恢复到测试服当前运行环境`。
- 确认文案：`RESTORE TEST <backupId>`。

恢复数据按钮应默认禁用，直到受控恢复候选满足以下条件：

- `COMPLETE`。
- checksum 通过。
- DCC manifest 通过。
- 已完成与当前目标 fingerprint、chain digest 和 manifest digest 绑定的隔离恢复演练且 `PASSED`。
- 当前目标 fingerprint 兼容。
- pre-restore snapshot 可创建。
- 责任人和权限确认通过。

## 推荐 API

优先复用已有运行控制台，不新建第二套执行器。

可复用能力：

- `GET /infra/backup-plan/status`
- `POST /infra/backup-plan/backup-now?backupKind=FULL|INCREMENTAL`
- `GET /infra/backup-plan/history/page`
- `GET /infra/backup-plan/evidence/export`
- `GET /infra/runtime-control/restore-candidates`
- `POST /infra/runtime-control/actions/preview`
- `POST /infra/runtime-control/actions`
- `GET /infra/runtime-control/operations`
- `GET /infra/runtime-control/operations/{id}/log`

如果要把恢复能力合并到备份计划页，建议只做 façade：

- 前端仍在备份计划页展示恢复按钮。
- 后端仍调用 Runtime Control 的候选、预览、动作执行、状态和日志能力。
- 不复制一套新的恢复脚本和状态机。

请求和响应原则：

- 请求只能传服务端签发的候选 ID、目标环境、备份类型和确认文本。
- `restore-candidates` 响应必须区分 `REHEARSAL` 与 `CONTROLLED_RESTORE`；服务端不得把 `NOT_RUN` 候选标记成可覆盖恢复候选。
- 禁止前端传任意文件路径、任意命令、任意 host、任意 ssh 参数。
- 响应必须返回 `operationId`、状态、blockers、报告引用；不得返回秘密。
- 状态枚举至少包括：`PENDING`、`PRECHECK`、`RUNNING`、`VERIFYING`、`SUCCESS`、`BLOCKED`、`FAILED`、`CANCELLED`、`UNKNOWN`；进程中断或终态未知不得自动判定成功。

## Verification

未来实现前应先写 BDD，并按严格 TDD 增加测试。

BDD 场景建议：

- BDD: 立即全量备份 -> Given 测试服 preflight 全通过，When 操作人点击 `FULL` 备份，Then 后端创建异步 operation，并生成 `COMPLETE` 备份包、manifest、checksum、operation report。
- BDD: 立即增量备份 -> Given 存在完整全量基线且 binlog 可用，When 操作人点击 `INCREMENTAL` 备份，Then 生成带 parent/base 信息的增量恢复链。
- BDD: 缺少 BackupKind -> Given 备份请求没有明确 FULL/INCREMENTAL，When 请求进入后端，Then 返回阻断，不能默认选择一种。
- BDD: 候选包恢复演练 -> Given 候选包完整且兼容，When 操作人点击恢复演练，Then 系统恢复到隔离槽位并验证 health、登录、文件 hash、关键业务路径。
- BDD: 未演练候选 -> Given 备份集 `COMPLETE`、manifest/checksum/依赖链完整且 `rehearsalStatus=NOT_RUN`，When 操作人选择恢复演练，Then 服务端允许进入隔离槽位，不允许直接执行 `restore-data`。
- BDD: 兼容恢复 -> Given 候选包已演练通过且当前测试服 fingerprint 兼容，When 操作人确认恢复，Then 系统创建 pre-restore snapshot、恢复数据、启动服务并生成 restore report。
- BDD: 演练副作用隔离 -> Given 隔离槽位启动恢复，When 定时任务、MQ、Webhook 或通知组件尝试运行，Then 组件被禁用或指向隔离端点，不得触发真实外部写入。
- BDD: 恢复终态未知 -> Given 恢复进程中断且后端无法确认写入阶段，When 操作状态收敛，Then 状态为 `UNKNOWN`、目标保持写保护，不得返回 `SUCCESS` 或伪造 `CANCELLED`。
- BDD: 升级后不兼容 -> Given 当前测试服 schema 比备份包新且没有迁移方案，When 用户选择旧包恢复，Then preview 阻断且不写任何数据。
- BDD: 降级风险 -> Given 目标 runtime 比备份包旧，When 用户选择备份包，Then 系统阻断并说明程序版本和 schema 不兼容。
- BDD: 换硬件容量不足 -> Given 新硬件磁盘容量或架构不满足备份包要求，When 用户发起恢复，Then preflight 阻断且不执行恢复。
- BDD: checksum 不一致 -> Given 备份包 hash 校验失败，When 候选列表刷新，Then 该包不可选且记录 blocker。
- BDD: 外部 writer 未隔离 -> Given 无法证明外部 writer 已停止，When 发起备份或恢复，Then 任务阻断。

最小验收证据：

- 操作记录：谁、何时、目标环境、动作、backupId、operationId。
- 备份证据：manifest、checksums、operation report、文件数量/字节数、hash。
- 演练证据：rehearsal report、健康检查、登录截图或日志、样本文件 hash、关键业务路径结果。
- 恢复证据：pre-restore snapshot、restore report、后端 health、前端 HTTP、版本指纹、DB/对象/DCC 验证。
- 审计证据：权限、责任人确认、确认文本、失败阻断原因。

## Blockers

当前如要真正上线或对外宣称“测试服务器可以一键备份恢复”，至少还需补齐以下 blockers：

1. 实时只读 preflight：确认测试服当前 health、版本、Docker、DB、MinIO、NAS、磁盘容量、备份根目录、脚本版本。
2. 当前备份候选：分别确认是否存在最新 `COMPLETE` 的演练候选，以及绑定当前目标、未过期且演练 `PASSED` 的受控恢复候选；两者不能混为一个状态。
3. RTO / RPO：业务侧正式定义目标，不能只写脚本默认值。
4. 兼容矩阵：填入当前 MySQL、MinIO、Redis、Docker、OS、CPU 架构的实际版本和支持范围。
5. 密钥保管：确认 `secretsRef`、密钥保管人、恢复时可用性，不把秘密写入包。
6. 外部 writer：确认所有写入路径是否都能通过停止后端隔离；如果存在外部写库/写对象路径，必须建 writer registry 或阻断。
7. 恢复演练槽位：确认隔离槽位可启动、端口不冲突、bucket 不污染正式或测试默认受保护资源。
8. UI 权限：区分查询、执行备份、执行演练、执行恢复、导出证据、管理员配置。
9. 脚本契约：修正或弃用未显式传 `BackupKind` 的 `.bat` 入口，统一走后端 operation gateway。
10. 证据导出：确保恢复报告、演练报告、manifest、checksum 能打包导出并脱敏。

## 给 ChatGPT 网页的介绍稿

可以直接粘贴下面这段作为背景：

我们当前的测试服务器是 `172.30.30.58`，测试前端入口是 `http://172.30.30.58:8081/`，后端健康检查是 `http://172.30.30.58:48081/actuator/health`。当前项目已有一套 `backup-ops` 和运行控制台能力：备份计划页可以触发 `FULL` / `INCREMENTAL` 备份，运行控制台可以查询恢复候选、执行恢复演练和恢复数据。恢复数据脚本禁止恢复到正式环境，只允许测试服或备份服目标。

我们要做的不是让 ChatGPT 网页直接 SSH 到服务器执行命令，而是让网页调用受权限保护的后端接口。后端只允许白名单动作：立即备份、恢复演练、恢复数据、查询状态、导出证据。每个动作都必须创建异步 operation，前端只能查看进度和结果，不能凭按钮点击直接判定成功。

备份按钮必须明确备份类型，至少支持 `FULL` 和 `INCREMENTAL`。备份前要检查测试服状态、备份目录、MySQL/binlog、MinIO、DCC 文件、配置清单、磁盘容量和 writer 隔离。备份包只有在 manifest 完整、checksum 通过、状态为 `COMPLETE` 后，才能进入备份包列表。

恢复按钮必须先选择一个服务端认可的恢复候选包，不能让用户输入任意路径。候选包必须包含 MySQL、MinIO / 文件对象、DCC manifest、checksum、程序版本指纹、配置指纹和 Redis policy。恢复前要做 preview，比对当前测试服务器的版本、schema、Docker、数据库、MinIO、磁盘、端口和域名。如果升级、降级、换硬件、换 IP、缺密钥、缺对象、hash 不一致、备份链断裂或外部 writer 未隔离，就必须阻断，不能降级执行。

恢复数据前最好先执行隔离恢复演练。演练通过后，如果确实要覆盖当前测试服，必须先创建 pre-restore snapshot，再停止 writer，恢复 MySQL、MinIO / 文件对象、DCC 文件，按 Redis policy 处理缓存或业务 Redis，启动服务并验证后端 health、前端 HTTP、登录、样本文件下载 hash 和关键业务路径。只有这些证据全部通过，才显示恢复成功。

服务器升级、降级或换硬件时，恢复不能靠“试一下”。升级后要确认旧备份数据能被新程序和新 schema 正确迁移；降级默认阻断，除非有测试过的回滚迁移；换硬件要核对 CPU 架构、Docker/Compose、磁盘容量、挂载路径、网络、时钟和依赖服务。所有不兼容都应明确显示 blocker，不允许静默 fallback。

当前仍需实时确认的事项包括：测试服当前运行版本和健康状态、是否存在最新完整且演练通过的备份包、RTO/RPO 业务目标、实际数据库/MinIO/Redis/Docker 版本、密钥保管和恢复演练槽位可用性。在这些实时门禁完成前，只能说“已有按钮化备份恢复机制和设计方案”，不能宣称“当前测试服已经完成可恢复演练”。
