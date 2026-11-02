# 镜像、容器、发布包和恢复资料的产生入口核查

## Current Status
completed（本轮只读核查完成；主任务目录收尾仍为 ready_for_closeout）

## 目标与范围
用户要求检查旧 Docker 镜像、旧容器、旧包和旧恢复资料分别由哪些操作产生。沿用发布后自动清理任务，核查本机活跃执行器及维护仓入口，不连接服务器、不触发发布/备份/恢复/删除，不读取或输出凭据。此结果说明代码行为，不冒充三服实时库存盘点。

## 里程碑与预期验证
1. 定位完整发布、前端补丁、备份、恢复、失败重试和历史隔离演练的创建入口。
2. 对照创建、保留和删除路径，列出四类产物的来源与条件，避免把操作日志等元数据算成大包。
3. 记录文件与行号证据，说明现有自动清理覆盖边界。

## 经验门禁
- Trigger：涉及发布、备份、恢复产物与空间占用的机制核查。
- Preflight check：先核任务链状态及经验索引；按索引阅读发布/备份恢复与 PowerShell 经验；使用 UTF-8 读取代码，区分运行副本和 Git 代码。
- Blocker：无法找到真实创建调用链时不得推定；原任务的主检出无法归档限制仍影响目录收尾，保持 ready_for_closeout，不重试删除工作副本。
- Verification：以创建文件、docker load/run/rename、备份归档与恢复替换调用为证据；明确仅静态代码核查、无远端执行。
- Forbidden action：禁止启动发布、备份或恢复来验证；禁止删除任何镜像/容器/文件；禁止访问私密配置或输出凭据；禁止触碰正式服 /mnt/nas。
- Evidence：本文件核查结果及同目录 execution-log.md。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否，本轮不修改行为。
- 是否从根因和长期维护角度解决：是，按真实入口解释空间积累来源。
- 是否存在临时补丁或绕过：否。

## 核查结果
“旧”通常不是单独执行一次“生成旧包”：新版本导入、安装时创建本轮资料，后续版本取代它后，该资料成为旧版本资料。失败、中断或保留引用会阻止自动清理。Docker 镜像归档文件与 Docker 已导入镜像是两份不同存储，删除 images.tar 不等于删除 Docker 镜像。

| 操作 | 镜像和容器 | 包和恢复资料 |
| --- | --- | --- |
| 完整包上传、发布及验收开放 | stage 导入新的 backend/frontend 镜像，旧镜像保留；replace 将原容器改名为 `*-before-<tag>` 后创建新容器；维护模式后端在开放时再替换一次，留下 `*-before-<tag>-maintenance`。正常开放会删除临时验收前端，失败可能保留。 | 上传 `release.tar`，解包得到 `images.tar` 及发布文件。checkpoint 模式发布前生成 `recovery.sql.gz` 和 Redis/MinIO 登记数据卷的 `recovery-volume-*.tar`；正式 external 模式仅记录外部恢复责任，不在此步骤复制正式全量数据。 |
| 前端补丁上传和发布 | stage 导入新前端镜像；部署保留 `frontend-before-JOB-*`，后端、数据库容器不替换。 | 每个补丁/部署任务目录上传包、解出 images.tar，并保留原前端配置与部署回执；补丁发布不生成数据库/MinIO全量检查点。 |
| 手动或计划独立备份 | 备份一般不替换业务容器；某些入口导出原程序镜像成文件，这不会凭空产生一个新的旧镜像版本。工具容器使用 `--rm` 的正常退出路径会自行删除。 | 创建数据库全量或增量、对象与配置等备份载荷及封存资料；例如 minimal capture 导出 `original-application-images.tar`。备份传输或封存可能有源暂存和目标副本。旧版计划备份另有本地/远端 retention 调用，不等于本轮发布后清理覆盖全部备份入口。 |
| Spug 发布失败恢复 | 失败程序容器改名 `*-failed-JOB-*` 后按原配置创建恢复容器，失败镜像仍可能被这些容器引用。 | 恢复前保存失败数据库至 `failed-database-*`；Redis/MinIO 待替换目录保留为 `*.failed-JOB-*`，恢复过程另有 `*.restore-JOB-*` 暂存和日志。原检查点继续存在。 |
| 补丁恢复、程序回滚 | 将候选容器保留为 `*-failed-JOB-*`，原容器恢复名称/连接和运行；程序回滚不等于数据库还原。 | 增加恢复/回滚回执、配置证据；不应描述为每次都会再生成一套完整数据库备份。 |
| 独立数据恢复 | 依具体恢复入口启动、替换或复用目标运行资源，不能把所有入口统一归结为 Spug 的 `recover-release` 行为。 | 使用原备份链，可能物化待恢复对象/数据，保留恢复运行证据。旧 PowerShell 的 pre-restore snapshot 仅保存运行配置和元数据，不能当作完整数据备份；额外全量数据副本须按实际入口确认。 |
| 历史/单独隔离演练 | 恢复镜像、创建独立 backend/frontend/MySQL/Redis/MinIO 等容器、网络和数据卷。 | 创建/传输数据库、Redis、MinIO、必要原镜像的副本和传输分块。new_seed 已有目录会改名 `-retained-*` 保留。当前直接三服主流程已取消该步骤，历史产物不会因此自动消失。 |
| 失败、中断及新一轮部署重试 | 在导入后失败，候选镜像也会留下；替换后失败会留下旧容器及候选。 | 上传中断、capture 失败可能留下不完整归档。完整发布/补丁的新尝试使用独立目录，原尝试证据保留；严格 resume 和已验证 stage 复用不会无条件重造全部副本。 |

单纯本机构建只在构建机生成镜像、缓存和发布包，尚未传入目标时不会因此占三服空间。只读查询、页面验收或不换镜像/配置的普通 stop/start/restart 本身不会生成一套新的业务镜像、发布包或全量恢复资料。

## 当前清理覆盖与限制

- 完整发布和前端补丁仅三服最终验收成功才调用 post-release 自动清理，候选限登记旧 `release.tar`/`images.tar`、归属完整的旧 `recovery.sql[.gz]`/`recovery-volume-*.tar`。
- 自动清理保留当前版本、当前恢复点、未结束任务/演练引用、归属不明资料和元数据，不删除容器/镜像/卷，也不触及独立备份系统。失败数据库、`*.failed-*` 数据目录、旧演练环境和独立恢复资料不在该回收列表。
- 旧容器继续引用旧镜像，解释了为何只清发布包后 Docker 用量仍可能增长。当前资源大小、是否仍被引用和实际可删范围须单独远端盘点，本轮没有作此盘点。

## 可复核代码证据

活跃运行源 `C:/SpugHandoff/release/source/ops/spug/release-center/`：

- `intruoyi_runtime.py:584` 上传原包；`intruoyi_runtime_agent.py:1504` 导入新镜像。
- `intruoyi_runtime_agent.py:674` replace；`:813` deploy 的 checkpoint/external 分流；`:1008` reopen 二次替换维护后端；`:1053` 正常移除验收前端。
- `intruoyi_recovery_agent.py:221` capture 和 `:243` 数据卷归档；`:146` 数据替换暂存/失败目录；`:438` failed database；`:449` retainedData；`:476` 容器恢复。
- `frontend_patch.py:146` 按补丁及任务分目录上传；`frontend_patch_agent.py:77` 导入镜像；`:144` 部署调用 replace；`:117` 恢复保留失败容器。
- `rollback_agent.py:118` 程序回滚保留当前候选容器；`backup_retry.py:25` 新尝试 staging root。
- `intruoyi_rehearsal_agent.py:931` new_seed 保留旧目录；`:1160` 原镜像归档；`:1192` MinIO 归档；`:1251` 导入；`:1256` 独立数据卷；`:1285` 独立容器。
- `post_release_cleanup.py:34` 触发；`artifact_files.py:44` 文件白名单；`:214` 自动清理。

维护仓 `C:/Users/D01021/Documents/ChatGPT/Maintance/`（核查起点 `int_main` / `d7067d1`）：

- `ops/recovery/minimal_capture_worker.py:366` 备份镜像归档；`ops/recovery/formal_capture_incremental.py:304` FULL/INCREMENTAL 数据差量分流。
- `ops/backup-ops/linux/backup_ops_linux.py:2148` 创建备份暂存、导出数据库/对象；`:2229` 数据恢复。
- `ops/backup-ops/scripts/modules/UseCases/BackupNow.psm1:95` 手动备份工作目录；`BackupScheduled.psm1:111`、`:135` 旧入口独立 retention；`Infra/DockerOps.psm1:1227` 仅运行配置的 pre-restore snapshot。
- `ops/spug/release-center/intruoyi_build.py:401`、`frontend_patch_build.py:77` 构建机导出镜像包。

验证结论：交叉核对创建、重命名、回收入口完成，无生产代码变更，不需要行为测试；没有连接三服或触发任何远端动作。此次静态核查不宣称真实清理验收通过。
