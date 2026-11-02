# 三服空间清理候选分析

本次只读检查三台服务器，未删除文件、停止容器、清理镜像、修改挂载或执行发布。结论：有较大的历史资料清理空间，优先处理备份服，再处理测试服；正式服空间充足。下列容量是目录实际占用，附有保留条件的项目不能直接视为保证可释放量。

采集窗口：2026-11-02 01:01–01:15 UTC。单位统一为 GiB（1024³ 字节），不等同于磁盘厂商 GB。证据摘要见 [storage-facts.json](storage-facts.json)。详细清单、采集脚本及原始错误资料仅保存在本机 Git 外的 `C:/SpugHandoff/release/private/acceptance/storage-audit-20261102/`，未提交凭据、配置正文、数据库或业务文件。

## 当前磁盘情况

| 服务器 | 根分区可用 | Docker/发布数据盘可用 | 数据盘使用率 | 判断 |
|---|---:|---:|---:|---|
| 正式服 172.30.30.57 | 36.05 GiB | 1106.31 GiB，`/var/lib/docker` | 41% | 无紧急清理需要 |
| 测试服 172.30.30.58 | 6.89 GiB | 72.04 GiB，`/var/lib/docker` | 97% | 数据盘历史副本多，根分区也应整理 |
| 备份服 172.30.30.59 | 2.34 GiB | 24.38 GiB，`/mnt/intruoyi-data` | 98% | 根分区与数据盘都需要优先释放空间 |

测试、正式服的数据盘是 `/dev/vdb`，文件系统容量约 1967.6 GiB。备份服数据盘为 `/dev/mapper/cl-home`，约 926.2 GiB。本次未修改文件系统预留或扩容。

清理根分区不会增加数据盘发布目录的可用空间，反之亦然。Docker 的多个 overlay 挂载共用底层文件系统，不能重复相加。NAS 是共享盘，本次不将其计为本机清理对象。

## 优先级一：备份服 59

### 根分区：旧 Docker 引擎资料

当前 DockerRootDir 和 daemon 配置均为 `/mnt/intruoyi-data/docker-engine`。旧路径 `/var/lib/docker` 在根分区仍占 **36.56 GiB**。所有当前容器的 GraphDriver 路径均已核对，不在旧路径；未发现进程 fd/cwd 或 systemd service 文本直接引用旧路径。旧目录不是符号链接。

| 精确路径 | 占用 | 建议与条件 |
|---|---:|---|
| `/var/lib/docker/overlay2` | 10.78 GiB | 优先核销的旧引擎层目录；清理前核对旧容器迁移记录，确认没有唯一的未迁移可写层，并再次确认不存在当前 GraphDriver/挂载引用 |
| `/var/lib/docker/image` | 0.016 GiB | 与旧引擎层配套的镜像元数据；随已核销的旧引擎资料处理 |
| `/var/lib/docker/buildkit` | 0.070 GiB | 旧引擎构建资料；不是当前 Docker 的 build cache，确认旧引擎不再启用后处理 |
| `/var/lib/docker/containers` | 0.289 GiB | 旧容器元数据、日志；需先按日志及审计保留要求归档，优先级较低 |
| `/var/lib/docker/volumes` | 25.40 GiB（`du -x`） | **本轮不列入直接删除白名单**；含旧数据卷，并且路径下面存在指向当前数据盘的 MySQL、MinIO、Redis 子挂载 |

前三项合计约 **10.87 GiB**，是根分区最值得核实和清理的遗留副本；核销条件满足并获准处理后，根分区可用量理论上可从 2.34 增至约 13.21 GiB。它们仍需核对旧可写层归属，不将“当前引擎不用”直接等同于“没有唯一数据”。

**禁止整目录递归删除 `/var/lib/docker`。** 其中除了上述数据卷子挂载，还有 `intruoyi-data/runtime-data`、`intruoyi-releases` 和公司共享盘的挂载。已用设备号与 inode 确认：`/var/lib/docker/intruoyi-releases` 与 `/mnt/intruoyi-data/intruoyi-releases` 是同一目录的两个入口，不是两份可以分别清理的文件。

### 数据盘：旧发布恢复副本

共同父目录：`/mnt/intruoyi-data/intruoyi-release-workflow/backup/packages/`。

| 版本子目录 | 全目录约占用 | 其中数据库与对象恢复文件 | 核对结果 |
|---|---:|---:|---|
| `2026-10-28-23-36-26` | 21.97 GiB | 20.6204 GiB | deployment phase=succeeded，有 business-opened 记录；无容器挂载或进程 fd/cwd 引用 |
| `2026-10-29-16-28-18` | 21.97 GiB | 20.6207 GiB | 同上 |

这两个目录的主要大文件是 `recovery.sql`（每份约 11.60 GiB）与 `recovery-volume-1.tar`（每份约 9.02 GiB），另有小的 Redis 等恢复归档。**它们是恢复资料，不是普通缓存。**

建议先确认恢复保留策略、当前版本的独立恢复依据和备份链，若它们已经允许淘汰或已在有容量的独立位置完成复制、哈希校验与登记，再仅清理这两轮的大体积恢复载荷。保留 manifest、回执、校验摘要及发布历史。两轮合计约 **41.24 GiB**；只处理一轮就约 **20.62 GiB**。

只处理一轮后，数据盘理论可用约 45.00 GiB，可以越过当前 32 GiB 最低空间检查，但是否足够下一次完整发布仍需重算实际包、检查点与恢复预算。本次不据此宣称可以立即发布。

必须保留当前 `2026-11-01-13-08-35` 的恢复资料及 `2026-10-30-10-19-11` 等尚未核销的回退依据；`attempts`、`failed-JOB-3d916701fc-*` 和 `space-recovery-JOB-3d916701fc` 也不自动当垃圾删除。

另外，`/mnt/intruoyi-data/runtime-data/minio` 占 **127.35 GiB**，被仍运行的 `intruoyi-minio` 绑定，属于在用对象数据，**保留**。不能因当前 Spug 发布使用另一个 MinIO 容器就删除它。`/mnt/intruoyi-data/backup-ops/rehearsal` 约 6.79 GiB，需确认备份恢复链和归属后另行评估。

## 优先级二：测试服 58

### 数据盘候选

| 路径 | 占用 | 建议与条件 |
|---|---:|---|
| `/var/lib/docker/intruoyi-releases` | **143.10 GiB** | 旧发布归档目录，未发现容器挂载或进程 fd/cwd 引用；优先按旧版本清单淘汰可重建的程序包、镜像归档。目录内若有 base-data、业务文件或恢复资料须单独排除；143.10 是候选目录总量，不是保证释放量 |
| `/var/lib/docker/intruoyi-release-workflow/test/packages/rehearsal-seed` | **63.75 GiB** | 10 月 22 日种子及 retained 副本；无直接容器挂载，仍须确认恢复依赖、保留期限及重复内容，不能只因名字带 retained 就判断冗余 |
| `/var/lib/docker/intruoyi-release-workflow/rehearsal-test/packages` | **76.01 GiB** | 旧 rehearsal-test 发布与种子资料；必须与仍在运行的 rehearsal-prod 区分，确认旧环境已退役后只处理已核销的载荷 |
| `/var/lib/docker/intruoyi-release-workflow/rehearsal-prod/packages/rehearsal-transfer-cache` | **18.88 GiB** | 传输缓存候选；需校验对应原包、确认不再供恢复/演练使用，保护运行演练 |

上述目录有不同职责，不能直接批量删除；父目录与其子目录也不能再次累计。整个 workflow 约 663.07 GiB，其中 test/packages 约 356.20、rehearsal-prod/packages 约 223.61、rehearsal-test/packages 约 76.01 GiB，**整体大小不代表全部可清理**。

与备份服相似，`.../test/packages/2026-10-28-23-36-26` 和 `.../test/packages/2026-10-29-16-28-18` 的恢复载荷各约 **20.61 GiB**，都有成功及开放回执，没有容器挂载或进程 fd/cwd 引用。若符合相同的恢复资料核销条件，可以再释放合计约 **41.22 GiB**，保留发布历史元数据。不能和包含它们的 test/packages 总量重复计数。

### 根分区候选

| 路径 | 占用 | 建议与条件 |
|---|---:|---|
| `/backup/int-ruoyi` | **20.97 GiB** | 主要是 9 月旧演练目录；无直接 Docker 挂载，但尚未确认定时任务和完整恢复链，须先核销旧演练归属及保留期限 |
| `/var/lib/intruoyi-release-center/packages` | **13.61 GiB** | 旧 Spug 发布路径，主要是 10 月 21 日版本；当前执行器使用数据盘 workflow 路径。需核对旧任务、pre-effect 检查点和恢复绑定后，保留记录、清理已核销载荷 |

两处占用合计约 **34.57 GiB**，是根分区的重要候选。不能通过移到同一根分区的另一个目录释放空间；迁出时也不能不计算测试数据盘剩余容量。

必须保留：当前 test/packages 的 `2026-11-01-13-08-35`，本地状态明确绑定其 recovery.sql.gz；10 月 31 日失败/恢复资料、attempts、尚需的回退版本。用户要求保留的旧演练仍运行，`rehearsal-prod/packages/2026-10-30-10-19-11` 的验收配置和 `rehearsal-prod/packages/rehearsal-seed/2026-10-30-10-19-11` 的后端、网关配置有运行容器引用，均保留；相应 MySQL/MinIO 卷不能删。

## 优先级三：正式服 57

数据盘仍可用约 **1.08 TiB**，无需为本轮发布急删恢复资料。

| 路径 | 占用 | 建议与条件 |
|---|---:|---|
| `/var/lib/docker/intruoyi-release-workflow/prod/packages/rehearsal-seed` | **146.62 GiB** | 多轮完整种子与 retained 副本；优先建立过期/归档清单，按恢复链和保留政策核销，不按目录日期直接删除 |
| `/var/lib/docker/intruoyi-releases` | **9.77 GiB** | 旧发布目录，无直接容器挂载或进程 fd/cwd 引用；核清可重建程序包与数据文件后再处理 |
| `.../prod/packages/2026-10-28-23-36-26` | 恢复载荷 **20.6183 GiB** | 成功开放、无直接容器挂载或进程 fd/cwd 引用；按独立备份与恢复保留政策决定是否淘汰 |
| `.../prod/packages/2026-10-29-16-28-18` | 恢复载荷 **20.6193 GiB** | 同上 |

完整 workflow 约 259.08 GiB，已包含上表部分内容，不能再加一次。许多测试/演练 MySQL 卷各有十几 GiB，但仍有容器引用，部分正在运行；必须先确认用途与退役授权，本次不列为直接删除项。

## 不值得批量清理或必须保护的内容

- 三服当前 Docker **build cache 均为 0 B**，执行 builder prune 不能释放几十 GiB。
- 当前引擎没有完全无容器引用的数据卷；停止容器的可写层合计仅约 0、0.03、0.04 GiB（57、58、59）。删除大量停止容器并不自动释放其绑定数据目录，且可能损失回退入口。
- 镜像有共享层，多个 tag 也可能是同一镜像，不能把虚拟 SIZE 相加当可释放量。无容器引用的 Playwright、MinIO mc 等工具镜像还可能用于下次验收或备份，不直接删除。
- Docker JSON 日志、应用轮转日志和系统软件缓存可按既有保留策略定期处理，但实测远小于上述历史副本。`/run/log/journal` 在 tmpfs，清理释放的是内存，不会增加根分区或发布数据盘可用空间。
- 在用业务库、对象存储、Redis、审计/受监管记录、当前发布及恢复绑定、未结失败资料、共享 NAS 和运行演练均保留。不能执行全局 `docker system prune -a --volumes`，也不能手动删除当前 DockerRootDir 的 overlay2。

## 建议的实际处理顺序

1. 备份服：先核销旧引擎的约 10.87 GiB 文件，缓解根分区；另行核销一轮旧恢复载荷约 20.62 GiB，缓解发布数据盘。两项解决的是不同分区的问题。
2. 测试服：先梳理 143.10 GiB 旧发布目录；再处理根分区的旧演练和旧发布载荷。运行演练继续保留，不因取消未来发布演练步骤就自动删除已有环境。
3. 正式服：以建立历史种子、检查点的保留与归档清单为主，无需立即删除。
4. 后续若获准清理，先生成逐文件白名单与保留清单，确认挂载和恢复依赖；需要归档的文件先复制到有足够容量且符合保留要求的指定位置并完成校验，再删本地载荷；保留小体积 manifest、回执、摘要与历史索引。删除后重查 df、挂载、容器、服务健康及恢复绑定，再重跑发布空间预算。

本次没有验证独立备份的恢复可用性，没有计算所有候选的安全可释放总和。部分巨大历史数据树的 du 超时，仅保留已完成子目录结果，不把未完成项视为零。当前环境实际版本与本地历史存在信息差，当前引用及恢复资料采用保守保留，未将旧任务的完整包→前端补丁发布请求判为完成。
