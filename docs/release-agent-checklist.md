# IntRuoyi Codex 发布执行检查清单

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

### 必做动作

- 预览正式服发布命令，逐项核对：
  - `-Environment prod`
  - `-ConfirmText PROD`
  - `-RequireTested`
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
- 正式服未带 `RequireTested`
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

- no-data 发布必须验证 manifest `publishScope=code-only`。
- 发布包不得包含 `database`、`db-dump`、`mysql-dump`、`minio`、`files`、`runtime-data`、`data`、`docker-build-context` 等数据目录。
- 允许存在 `required-sql`、`resources`、`runtime-env`、`smoke` 等代码发布必要目录；operation `SUCCESS` 不能替代 manifest 与目录检查。

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
- release-info 中文说明以 UTF-8 parser 或浏览器页面为准；PowerShell mojibake 只记录为采集问题。
