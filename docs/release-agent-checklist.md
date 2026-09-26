# IntRuoyi Codex 发布执行检查清单

## 完整包、逐目标计划与持久恢复门禁

- Trigger: 构建或部署 `full-app-release/v1`，或处理部署中断、失败重试。
- Preflight check: `intruoyi` 固定 backend/frontend；`full` 另含 Website；OnlyOffice 在构建时决定。核对唯一 manifest、全部制品、来源提交、包双摘要及 tested v2；目标端不能覆盖组件或用工作区模板补包。旧包缺少新合同必须重新构建。
- Blocker: 历史 FAILED/RUNNING、未知状态、摘要漂移、缺控制 schema/工具/持久挂载、未解决 operation、锁内事实变化均拒绝；常规部署不自动准备平台、不补目录/表/存储过程、不重新派发可能写入的失败。
- Verification: 先本地验包，再目标只读采集/目标数据检查/规划，再持久门禁和既有租约锁，锁内重采复核后才能执行 APPLY。SKIP 历史不重写。保存逐目标计划与期望/实际内容身份、配置、完整台账及健康结果；最终化、历史、回执和锁终态全部成功才完成。
- Forbidden action: 禁止源库 dump 覆盖、MinIO 快照导入、重建平台数据服务、自动回滚或清理失败证据；过期 heartbeat 不是恢复授权。标签相同不能替代 imageId/configDigest、静态文件集合及 SHA 校验。
- Evidence: 包外控制目录中的计划；目标 `$RemoteAppDir/.release-state/$Environment/` 的 `gate.json`、`gate.lock`、`operations/<attemptId>.json` 与回执；数据库原 operationId/lease fence。只保留 leaseTokenDigest，日志不保存凭据或租约明文。

### 独立的平台准备（需要后续目标环境明确授权）

1. 核对目标服务器、部署用户/组和正式 RemoteAppDir；持久状态根不能在每版临时目录，也不能在受保护 `/mnt/nas` 共享盘。确认父目录、所有权、0700 权限、备份/保留约定以及受支持控制 schema。
2. 经授权后使用目标配置中的真实值执行 `install -d -m 0700 -o <部署用户> -g <部署组> -- <已核对的持久控制路径>/operations`；占位值禁止原样执行。由部署用户复核属主、可写性、非符号链接，并独立建立同属主可用的 `gate.lock`。
3. 只有核实没有旧 operation/未决恢复事实后，才可在单独的受审准备动作中原子初始化 `gate.json`：schemaVersion=`release-deployment-gate/v1`、revision=0、state=`READY`、attemptId/operationDigest/receiptDigest=null；scope 必须采用真实 environment/host/machineId/database/serverUuid。不能覆盖已有 gate 或用新 READY 遮蔽历史故障。普通发布不会初始化这些文件。
4. 当前容量/存储支持限定可核验路径的 Docker classic `overlay2`；containerd/未知驱动明确拒绝。数据库 1 GiB 是最低预留，不是任意 DDL 足够空间的承诺；按真实迁移增长另行提高并核对所有实际目的文件系统。

### 中断与恢复

先保全包双摘要、目标身份、gate/operation/receipt/历史及数据库锁/完整台账；核实已执行 SQL、配置和容器实际内容、未知观测及原始错误。执行过或可能执行过写入时保持 `RECOVERY_REQUIRED`，不得直接重试或按超时清锁。显式恢复入口 `ops/deploy/recover-release-operation-lock.ps1` 会消费同一持久门禁，仅满足其零运行写入、身份、旧租约与锁内复核条件时才可按后续批准流程执行；它不是自动回滚或数据恢复工具。人工修复、数据恢复或现场 bootstrap 必须另立授权任务。

本任务的本机 MySQL/classic 集成只证明相应 SQL、文件、计划、身份与失败合同；不代表三台服务器旧基线可升级、真实 backend UP、产品 E2E 或远端发布完成。

## 触发条件

当任务涉及以下任一事项时，Codex 必须先读本文，再决定是否进入真实发布动作：

- 运行控制台 `build-release`
- 发布到测试服
- `mark-tested`
- 发布到正式服
- 发布到备份服
- 发布失败后的重试

本文面向 Codex 执行，不替代正式规则。正式边界仍以以下文档为准：

- `E:\IntRuoyi\docs\release-backup-restore.md`
- `E:\IntRuoyi\docs\server-access.md`
- `E:\IntRuoyi\docs\login-access.md`
- 仅测试服发布还必须先读：`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\test-release-preflight.md`

## 执行模型

- Windows 发布测试显示100%但JUnit未落盘时，先执行 `docs/powershell-preflight-lessons.md` 的“Python JUnit 收尾与 Windows WMI”检查；缺进程退出码/有效报告不得放行，宿主OOM恢复后重型套件串行运行。

- 发布函数通过 AST 抽取测试时，先执行 `docs/powershell-preflight-lessons.md` 的“AST 测试载体与生产入口前提一致性”门禁，核对真实 UTF-8 初始化、JSON 数组形状及故障注入实际命中阶段；SQL 包含 FAILED 不等于正在更新 FAILED。载体失败不得充当产品 RED 或驱动未经验证的生产修改。

Codex 必须把完整发布任务视为以下严格顺序：

1. `build-release`
2. `publish-test`
3. 测试服运行态验证
4. `mark-tested`
5. `promote-prod`
6. 正式服运行态验证
7. `promote-backup`
8. 备份服运行态验证

以上八步仅适用于用户明确授权的完整发布。仅测试服任务必须以 `docs/test-release-preflight.md` 为范围权威，在第 3 步测试服运行态验证通过后停止；不得执行 `mark-tested`、`promote-prod`、`promote-backup` 或任何正式服、备份服动作。

任何一步失败，都必须先记录真实证据，再修复，再从合适步骤重新执行；不得把不同 releaseTag 的成功结果拼接成一次完成。

## 0. 开始前必做

### 必做动作

- 创建或识别任务目录。
- 读取 `docs/experience-index.md`。
- 命中并读取：
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\test-release-preflight.md`（仅测试服发布或 publish-test 任务）
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - `E:\IntRuoyi\docs\release-backup-restore.md`
  - `E:\IntRuoyi\docs\server-access.md`
  - 如涉及登录验证，再读 `E:\IntRuoyi\docs\login-access.md`
- 在 `execution-log.md` 先写 `GREEN: experience-preflight -> PASS` 或明确 blocker。
- 在 `docs/request-command-log.md` 记录用户需求与关键命令。

### 放行条件

- 任务目录存在。
- 命中文档已读取并在任务文档写出 `经验门禁`。
- 高风险动作前已有 `experience-preflight` 记录。

### 阻塞条件

- 没有任务目录。
- 没有 experience-preflight 记录。
- 正式服或备份服操作缺少当前任务授权。

## 1. 构建前检查

### 必做动作

- 确认发布源头在 `D:\ProjectPackage\Int\IntRuoyiMaintance`。
- 确认后端、前端、维护仓三方主分支名、当前提交与 dirty 状态。
- 每次发布一律先创建本次专用的临时发布 `worktree`，禁止直接在主工作区执行构建、验证或发布。
- 必须先核对测试服当前 releaseTag/manifest 与本次目标提交是否一致；不一致时不能复用旧发布结论。
- 必须显式核对 runtime-control 当前 `repo-root` / `frontend-root` 指向的就是本次最新临时发布 worktree，而不是主工作区或旧 worktree。
- 在临时发布 worktree 上先过前端 lockfile / 依赖恢复与后端目标模块构建门禁；未通过时，先提交修复再重建 worktree。
- `build-release` 前先用脱敏/白名单方式核对本地 Docker 可用性和必需容器存在；不得直接打印 `docker inspect` 的完整 env。
- 运行控制台指向 release worktree 后，再查一次三仓 `git status --porcelain --ignored=no`；`state-dir`、logs、operation state 和 cache 不得落在 release worktree 内造成 `dirty=true`。
- 先跑发布门禁或契约测试，尤其是：
  - migration policy gate
  - 影响发布链路的 SQL 契约测试
  - 影响产物契约的发布脚本测试
- required SQL 静态门禁必须覆盖 MySQL 64 字符标识符限制；约束、索引、触发器、过程、函数和事件名超长时必须在 build-release 前失败。
- 运行控制台 `state-dir` 根目录不得放任务自定义证据 JSON；operation 列表只应读取 `op-*.json`，其他证据放入 `evidence/`、`logs/` 或约定子目录。
- 快速、只读、可 fail-fast 的 migration/manifest/脚本契约门禁必须先于依赖恢复、前端构建、Maven 打包等耗时步骤；门禁失败后只停止本任务进程，不继续等待或并发重启无发布价值的构建。
- 确认本机运行控制台是当前版本，必要时重启后再核对。
- 核对构建预览命令包含：
  - `-Mode build-release`
  - `-Component intruoyi`
  - 本次目标 `releaseTag`
- 校验 preview arguments 时必须兼容 `-RequireTested`、`-SkipDatabaseSync`、`-SkipMinioSync` 等 switch flag；不得用简单偶数配对解析。

### 放行条件

- migration / manifest / 脚本契约未报错。
- 本次使用的后端、前端、维护仓输入关系清晰。
- 三仓主分支状态、本次目标提交与临时发布 worktree 路径已明确记录。
- 运行控制台预览命令指向正确 repo-root / frontend-root / scriptPath。

### 阻塞条件

- SQL 缺少 `release-migration` 元数据。
- `dependsOn` 错误。
- 发布脚本仍引用旧产物名、旧变量、旧路径。
- 运行控制台仍加载旧 worktree 或旧逻辑。
- 临时发布 worktree 自身无法通过 frozen-lockfile、依赖恢复或目标模块构建门禁。

### 2026-07-19 r260719k 发布失败复发防止清单

- Trigger: 完整三环境 code-only 发布在 clean release worktree 中执行 `build-release`、`publish-test`、`promote-prod` 或 `promote-backup`。
- Preflight check: `build-release` 前必须同时跑迁移元数据全量门禁、近期 SQL 静态测试、MES companion contract 编译门禁、前端 API export 静态门禁、`pnpm build:test`、Docker CLI/BuildKit 健康检查；required SQL 静态测试必须覆盖结构化 `release-migration`、`dependsOn` 无 `.sql` 后缀、单值 `type`、字符串 collation、动态角色 ID、DCC `OBSOLETE_CHAIN`、`content_key` CAST collation、`system_tenant_package.menu_ids` 扩容顺序。
- Blocker: 出现 `missing release-migration metadata`、`unknown release-migration metadata key`、`dependsOn missing migration`、`invalid type`、MES/前端 companion export 编译失败、MySQL `ERROR 1267`、`ERROR 1644`、`dcc master points to obsolete revision`、`ERROR 1406 Data too long for column 'menu_ids'`，或 Docker build 日志长时间不推进且 Docker CLI/BuildKit 同步异常。
- Verification: 失败时先冻结 operation JSON、脱敏日志、preview 参数、manifest 状态、远端关键输出和失败时间；修复后必须用新的 releaseTag 重新 `build-release`，并在同一 releaseTag 上完成测试服、正式服、备份服运行态验证。
- Forbidden action: 不得手工改测试库/正式库/备份库、手工更新发布锁或迁移状态、跳过 SQL/编译/BuildKit 门禁、复用失败 releaseTag，或拼接不同 releaseTag 的环境结果。
- Evidence: `doc/tasks/20260719-current-head-codeonly-three-env/execution-log.md`；最终 releaseTag `release-20260719-intmain-codeonly-three-env-r260719k-r1`。

### release worktree 路径长度门禁

- 创建 release worktree 时，临时根目录必须短而稳定；推荐 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r<日期><短标识>`。
- 维护仓、后端仓、前端仓子目录优先使用 `m`、`b`、`f`；不要使用完整任务 ID + 完整仓库名的深层嵌套路径。
- 若 checkout 报 `Filename too long`，必须冻结证据、清理已部分创建的 worktree、`git worktree prune`，再用短路径重建；不得继续沿用部分成功的 worktree。

## 2. 构建完成判定

### 必做动作

- 检查 build operation 最终状态。
- 读取 manifest。
- 核对：
  - `releaseTag`
  - backend commit
  - frontend commit
  - `sourceRepos.dirty=false`
  - manifest 中 `branch` 仍是本轮计划分支，且未在构建过程中漂移到新的未计划 commit
- 若任务要求“只发布 Git 已提交版本”，必须把 manifest 视为最终发布输入证明；构建前的 `git status clean` 不能替代构建后的 manifest 校验。

### 放行条件

- build operation=`SUCCESS`
- manifest 存在
- manifest 与本次目标 releaseTag、提交、发布范围一致

### 阻塞条件

- 只看到页面成功提示，但无 manifest
- manifest 与本次提交或 releaseTag 不一致
- `dirty=true`
- 构建完成后 manifest 记录的 commit 与构建前计划值不一致

## 3. 测试服发布与验证

### 必做动作

- 预览测试服发布命令，确认：
  - `-Environment test`
  - `-ServerHost 172.30.30.58`
  - `-RemoteAppDir /opt/intruoyi/runtime`
- 真实写入前检查本地/远端发布进程和 `infra_release_operation_lock`；存在活动发布或 `RUNNING` 锁时阻塞，不与其他任务重叠发布同一测试环境。
- 执行 `publish-test`
- 只读核对测试服：
  - `.env IMAGE_TAG`
  - compose 解析后的 backend/frontend 镜像
  - backend/frontend 实际镜像 tag
  - backend health
  - frontend HTTP
  - `release-info.json`
  - `infra_release_operation_lock`
  - operation 最终状态
- 最终判定前重新执行上述运行态检查，确认未被并发任务的新 releaseTag 覆盖。
- 保存或提交发布日志前扫描明文凭据；日志含密码、token、私钥、连接串或 `mysql -p...` 时先脱敏并删除原始秘密日志。

### 放行条件

- test operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- operation 未成功
- `.env` 已变但容器镜像仍是旧版本
- `.env`、compose、实际镜像、`release-info.json` 或 operation lock 指向不同 releaseTag
- 存在其他任务的活动发布进程或目标版本在最终验收前被覆盖
- 待保留或待提交日志含明文凭据
- health 不通
- frontend 不通

## 4. mark-tested 放行规则

### 必做动作

- 只有在测试服验证通过后，才允许执行 `mark-tested`
- 预览和执行 `mark-tested` 时不得传 `targetEnvironment`。
- 必须从 `/restore-candidates` 或真实页面候选中选择 `selectedRecoverySetCandidateId`，不得省略候选。
- 记录 operation ID、结果与 recovery candidate

### 放行条件

- 测试服运行态验证已完成
- `mark-tested` operation=`SUCCESS`

### 阻塞条件

- 测试服未验证就尝试 mark-tested
- 预览返回 `targetEnvironment` 或 `selectedRecoverySetCandidateId is required`
- 手工改 tested 状态代替 action

## 5. 正式服发布与验证

### 5.0 “已测试包发布正式服”按钮入口门禁

- Trigger: 运行控制台新增或使用“发布到正式服务器/晋级正式服”按钮。
- Preflight check: 按钮必须绑定服务端 `TESTED` release workflow、同一 `releaseTag`、package digest、manifest digest、测试 operation/验收证据和服务端正式目标；运行配置必须与本次冻结 worktree 的批准提交、绝对发布器路径和实际文件 SHA 一致。点击后先生成只读 production preview，目标 host/目录/访问开关变化使旧预览失效；再由服务端签发短时一次性授权；确认请求只能携带 workflow/preview/grant/状态版本/幂等键/原因/精确 `PROD`，不得由客户端传 host、path、targetEnvironment、releaseTag 或 evidence path。
- 本地页面审阅前还必须确认运行控制台 mount 自动读取的 overview、release-status 和远端磁盘状态是否触发 SSH；禁写开关不等于禁读，缺少本轮远端只读边界时不得启动该页面 E2E。只用本任务 PID/端口，使用真实测试租户凭据，不能以 admin 只读对照替代权限验收。
- Blocker: 维护 standalone console 或通用动作选择器仍允许手填 releaseTag/目标环境直接调用旧 `/actions` 生产动作；缺少专用 production 权限、preview blockers、执行器字节 SHA、同包双摘要、幂等键、最终运行态证据或 `RECOVERY_REQUIRED` 隔离时，不得放行按钮。
- Verification: Playwright 从真实工作流页面选择 `TESTED` 包，核对 preview checks、摘要、测试验收和确认顺序；最终只在 operation、manifest、正式 `.env IMAGE_TAG`、实际镜像、backend health、frontend HTTP、页面版本和生产锁全部一致时显示成功；不自动执行 promote-backup。
- Forbidden action: 禁止把旧 generic `promote-prod` radio/手填包入口当成新按钮；禁止 API-only/mock 代替真实按钮路径；禁止在派发或写入不明后释放生产隔离或允许普通重试；禁止重新构建已测试包。
- Evidence: `doc/tasks/20260918-prod-promotion-button-design/`；应用候选 `IntRuoyiFronted/src/views/infra/runtime-control/index.vue` 与 `RuntimeControlController` 的现状审计；维护 standalone `frontend/src/App.vue` 的 generic action 风险审计。

### 必做动作

- 预览正式服发布命令，逐项核对：
  - `-Environment prod`
  - `-ConfirmText PROD`
  - `-TestOperationId`、`-TestOperationEvidencePath`
  - `-ExpectedPackageDigest`、`-ExpectedManifestDigest`（与 TESTED 工作流相同）
  - 目标 host、目录、数据路径、MinIO 参数
- 执行 `promote-prod`
- 只读核对正式服：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - backend health
  - frontend HTTP
  - operation 最终状态

### 放行条件

- prod operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- 正式服未带 `PROD`
- 正式服缺少 TESTED 测试 operation/evidence 或工作流批准双摘要
- operation 未成功
- `/mnt/nas`、数据盘、MinIO、挂载状态异常

## 6. 备份服发布与验证

### 必做动作

- 预览备份服发布命令，逐项核对：
  - `-Environment backup`
  - `-ServerHost 172.30.30.59`
  - `-RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases`
  - `-RemoteDataRoot /mnt/intruoyi-data/runtime-data`
  - `-RemoteDataDiskMount /mnt/intruoyi-data`
  - `-RemoteDataDiskDevice /dev/mapper/cl-home`
  - `-RemoteMinioContainer intruoyi-minio`
- 执行 `promote-backup`
- 只读核对备份服：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - 数据盘挂载
  - backend health
  - frontend HTTP
  - operation 最终状态

### 放行条件

- backup operation=`SUCCESS`
- `.env IMAGE_TAG=<releaseTag>`
- backend/frontend 镜像 tag = `<releaseTag>`
- `/mnt/intruoyi-data` 挂载正确
- backend health=`UP`
- frontend HTTP=`200`

### 阻塞条件

- 备份服未显式使用 `/mnt/intruoyi-data`
- 备份服误继承 Docker 根目录路径或正式服参数
- operation 未成功

## 7. 失败时的排查优先级

Codex 必须按这个顺序排查：

1. migration / manifest / required SQL 契约
2. 维护仓发布脚本与业务仓产物契约
3. 运行控制台当前加载版本
4. 测试服 / 正式服 / 备份服环境状态

禁止在第 1、2 层未排干净前，直接把问题归因到服务器。

若失败点在 required SQL：

1. 先只读回查真实库状态、主键占用、历史数据与 tenant 范围
2. 再决定修 SQL、修迁移契约还是修发布脚本
3. 禁止手工改测试库绕过发布门禁

## 8. 2026-07-01 新增前置门禁

### 发布输入与 releaseTag

- 修复任何发布 blocker 后，必须重新执行 `build-release` 并生成新的 `releaseTag`。
- 禁止用旧失败包继续 `publish-test`、`mark-tested`、`promote-prod` 或 `promote-backup`。
- 禁止拼接不同 `releaseTag` 的测试服、正式服、备份服结果。
- `build-release` 成功后必须复核 manifest 中 backend/frontend `commit` 与 `dirty=false`。

### 测试服参数

- `publish-test` 预览必须显式核对测试服真实参数：
  - `ServerHost=172.30.30.58`
  - `RemoteAppDir=/opt/intruoyi/runtime`
  - Docker root 不得误套备份服路径
  - 数据盘设备、MinIO 容器名必须与 `server-access.md` 一致
- 如果预览中出现备份服或正式服参数，必须先修正维护控制台配置、脚本或文档，不得继续真实发布。

### required SQL 与真实库基线

- 发布前对新增或改动的 required SQL 做可重入检查，重点检查：
  - `ADD COLUMN` 是否有存在性保护
  - 菜单插入是否有冲突检测
  - 角色绑定是否兼容真实角色编码
  - 租户包与菜单权限是否同步
  - DCC 分类、编码、字段长度和唯一性是否有前置校验
  - 被后续迁移重命名的 legacy 表是否有双表或 `table exists` 守卫，尤其是 `mes_pro_route_use_process_batch_record` 与 `mes_pro_route_use_process_batch_record_legacy_20260709`
- SQL 依赖角色、菜单、租户或账号时，先只读查真实库，不能只按历史角色码或文档推断。
- 如果真实库基线不满足 SQL 契约，必须阻塞并修 SQL/迁移/数据契约；禁止手工改测试库帮助发布过关。

### DCC promote 前检查

- `promote-prod` 前必须对正式服 live data 做只读 DCC 质量预检。
- 至少覆盖分类重复、分类编码缺失、字段长度超限、必填关系缺失。
- 任一 DCC 质量预检失败时，不得推进正式服发布；失败 releaseTag 只保留为排障证据。

### 自动经验候选

- 发布类 operation 完成后必须生成 `runtime/runtime-control/release-experience-candidates.md`。
- 候选内容至少包含 operationId、action、environment、releaseTag、status、summary、候选前置经验和关键日志摘录。
- 如果候选文件缺失，任务收口不得视为完成；如果运行控制台写候选失败，operation 必须 fail fast。
- 任务收尾时读取候选文件，将稳定、可复用经验正式写入 `release-build-preflight-lessons.md` 或本清单。

## 8.1 2026-07-03 不带数据发布新增前置门禁

### code-only 不跳过 SQL

- `code-only`、`-SkipDatabaseSync`、`-SkipMinioSync` 只表示不携带业务数据和文件，不表示跳过 schema、required SQL、migration 或字段约束变更。
- 不带数据发布在 `build-release` 后仍必须核验 required SQL、migration 门禁和真实库约束变更结果。

### DCC lifecycle_stage / NOT NULL

- DCC 分类 `lifecycle_stage` 或任何字段改为 `NOT NULL` 前，必须先查全表空值，不能只查 `deleted=0` 活动行。
- `deleted=1` 历史归档行同样会阻塞 `NOT NULL`，必须在可重复 SQL 中定义归档归一化规则和注释。
- required SQL 报 `Invalid use of NULL value` 时，先只读按 `deleted` 等关键维度统计空值分布，再修 SQL、迁移顺序或数据契约；禁止手工改测试库绕过。

### 远端 MySQL 查询

- 测试服业务库名以真实容器为准；当前确认业务库为 `ruoyi-vue-pro`，不得默认写成 `yudao_ruoyi`。
- MySQL root 密码必须在容器内展开，优先使用 `docker exec -i intruoyi-mysql sh -lc 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" ruoyi-vue-pro'` 并通过标准输入传 SQL。
- PowerShell、SSH、sh、mysql 多层引号失败时，改用标准输入、临时脚本或 here-doc，并记录 `$LASTEXITCODE`；不得把查询失败误判为数据库无数据。

### runtime-control 配置

- 修改 `runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 后，必须回读确认 YAML 缩进、实际路径和 `http://127.0.0.1:48181/actuator/health`。
- 配置指向临时发布 worktree 后，收尾前必须恢复稳定主路径，或明确确认该 worktree 不会被删除。
- 运行控制台启动入口以维护仓当前脚本为准；本轮确认入口是 `scripts\start.ps1`。

### no-data manifest

- 标准一键 without-data 发布必须验证 manifest `publishScope=app-release`；历史 `code-only` 只作为旧链路兼容术语，不得作为新 workflow 放行条件。
- 发布包不得包含 `database`、`db-dump`、`mysql-dump`、`minio`、`files`、`runtime-data`、`data`、`docker-build-context` 等数据目录。
- 允许存在 `required-sql`、`resources`、`runtime-env`、`smoke` 等代码发布必要目录；operation `SUCCESS` 不能替代 manifest 与目录检查。
- `target-data-preflight.json` 等目标服务器证据不得写入不可变包；`ops-runtime` 不得携带 `backup-ops.config*.json`、secret 示例或 `manage-int-ruoyi-remote-root-disk.ps1` 等 target-bound 文件。

### promote-prod 目标库迁移依赖

- Trigger: 对测试服已验证包执行 `promote-prod`，尤其是 `publishScope=code-only`。
- Preflight check: 在任何远程应用容器切换前，必须针对正式库生成 target-bound `preflight-plan.json`，检查 `status=passed`，并展开所有 `BLOCKED_SCOPE_DEPENDENCY` 的依赖链。
- Blocker: code-only 不代表跳过 schema/required SQL；正式库缺失依赖、依赖路径被 scope 排除或 checksum 不一致时必须 fail fast，不能把预览 PASS 或旧容器健康误判为新包可发布。
- Verification: 失败后确认正式服 `.env`、实际容器镜像、backend health、frontend HTTP 和 release lock 已恢复/保持发布前状态；记录失败 operation 与恢复动作。
- Forbidden action: 禁止手工补迁移、更新迁移状态/lock/tested、修改已构建包或用 `-SkipDatabaseSync` 绕过 scope dependency。
- Evidence: 保存 target preflight report、operation 日志、远端旧运行态检查和下一次放行前的依赖修复证据。

## 9. 完成判定

Codex 只有在以下条件同时成立时，才能判定完整发布完成：

- 同一 `releaseTag` 已走完 `build-release -> publish-test -> mark-tested -> promote-prod -> promote-backup`
- 五个 operation 都有明确结果证据
- 测试服、正式服、备份服三环境都已验证：
  - `.env IMAGE_TAG`
  - backend/frontend 实际镜像 tag
  - backend health=`UP`
  - frontend HTTP=`200`
- 任务日志与请求命令日志已回写
- 发布和运行态验证完成后，任务先进入 `ready_for_closeout`
- `task-closeout-cleanup` preview/apply 已通过，`verification-report.md` 位于默认 keep 集
- 所有临时 worktree 的 Git 注册和物理目录均已清理，运行控制台已恢复稳定主路径
- 只有上述 closeout 证据全部通过后，任务状态才更新为 `completed`

任何缺项都不得宣称“完整发布已完成”。

## 8.2 2026-07-11 仅测试服发布补充检查

### publish-test preview 稳定性

- 对单一 releaseTag 发布，先直接校验目标 manifest，不让候选包全量扫描成为唯一门禁。
- preview/submit 任一步导致运行控制台断连且无 operationId 时，必须记录失败并停止；不得把脚本执行或旧 operation 当成本次成功。

### 运行态验收

- 测试服成功判定必须同时具备：build operation SUCCESS、publish-test operation SUCCESS、manifest sourceRepos clean、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 Up、backend health UP、frontend HTTP 200、`release-info.json`、运行控制台 release-status、真实页面版本对话框。
- 运行控制台有历史 dead RUNNING operation 时，必须证明它不是本次 releaseTag 且不占用发布锁；否则阻塞。

### PowerShell/SSH/Playwright

- Host:port URL 用 `${hostIp}` 写法。
- bash `$()`/`||` 不放入 PowerShell 双引号。
- Playwright 先检查模块与浏览器路径；可用已安装 Chrome/Edge，不在发布验收中临时安装浏览器。
- 同一 Playwright CLI 会话的 `open/resize/snapshot/click/find/console/close` 必须串行执行；出现 `ECOMPROMISED Lock compromised` 时本轮组合结果不可放行，改为串行重验并取得页面字段与 console errors=0。
- release-info 中文说明以 UTF-8 parser 或浏览器页面为准；PowerShell mojibake 只记录为采集问题。

### 独立探针与稳定控制台收尾

- 远端数据库探针必须先从冻结 migration 和真实库 `DESCRIBE` 确认表/字段；容器未定义 Docker healthcheck 时只核 `state=running`，应用健康必须独立核 Actuator HTTP 200/UP。
- 删除 release worktree 前，48181 PID/命令行/JAR 必须指向主维护路径，完整 `/admin-api/infra/runtime-control/release-status` 必须显示目标 tag、notes 和 changes；只看 health=UP 不足以收尾。
- 同 HEAD 重新构建的 Spring Boot JAR 可能因归档元数据产生不同 hash；必须记录并验证本次实际产物 hash，不得用历史重建 hash 作为当前复制/恢复门禁。
- 外部 release worktree/state 先按 `E:\IntRuoyi\docs\worktree-memory.md` 验证 Git 注册、物理路径、进程和 allowlist 后清理；再运行仓库内 task-closeout preview/apply，禁止绕过 workspace 边界。

## 8.3 2026-08-31 code-only target plan 与历史 ADD COLUMN 幂等门禁

### publish-test 提交前

- 最终 manifest 生成后，先针对测试服当前 target state 运行 `release_preflight_plan.py`；必须 `status=passed`、`BLOCKED*=0`，并记录 APPLY/SKIP 数量和目标 migration action。
- 校验 manifest 的 `requiredSql`、`migrationPlan`、`database.schemaMigrations` 三份投影对同一 migrationId 的 type/dependsOn/sha256 一致。
- 对 APPLY 中的历史 `ALTER TABLE ADD COLUMN`，只读查询 live `information_schema.COLUMNS` 与 ledger；列已存在但 ledger/checksum 不一致时，SQL 必须逐列可重放。
- 以上 gate 必须在远端 `.env IMAGE_TAG` 修改、镜像上传和 release lock 获取前通过；当前脚本若尚未自动前移，Agent 必须手工完成并保存结构化证据。

### Fail Fast

- `BLOCKED_SCOPE_DEPENDENCY`、schema 依赖 scope-excluded data、裸多列 ADD 命中已存在列、target state 过期、manifest 三投影不一致、或 `.env` 已改但 actual image 未切换。
- 失败 tag 立即判废；禁止 with-data/手工 SQL/ledger 修改绕过。修复需独立 worktree、严格 TDD、提交融合、新 releaseTag 重建。

### 发布后

- 核 lock=APPLIED、FAILED/RUNNING=0、target migration APPLIED/checksum；`.env`、compose/actual image、containers、health、HTTP、release-info、release-status、Playwright 和 final gate 全通过。
- 运行控制台发布标签输入框可能有历史默认值，preview/submit 必须始终显式传入并结构化核对本轮 tag，不得信任 UI 默认值。
- 日常 backend `build-release` 在 Maven 前必须完成 schema-only 临时库迁移演练；不得复制完整业务数据或 MinIO。最终计划中的非 schema APPLY 必须存在 `sql/mysql/target-preflight/<migrationId>.preflight.sql`，通过只读合同校验和测试服只读断言；缺失或失败即废弃 releaseTag。
