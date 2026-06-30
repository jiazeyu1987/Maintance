# 20260625 HEAD 全链路发布

## Task Goal

基于当前分支最新已提交代码完成一次完整发布：从干净 HEAD worktree 构建维护控制台和 `code-only` 发布包，先发布测试服务器并验证真实运行态，再发布正式服务器和备份服务器，最终在运行控制台确认三个环境均显示本次版本号和变更说明。

## Scope

- 维护控制台仓库：`D:\ProjectPackage\Int\IntRuoyiMaintance`，当前分支 `int_main`，HEAD `3eb9047d0ac0759ee46d7d88f4adba442bed474f`，提交 `任务: 发布包注入前端版本信息`。
- 后端仓库：`D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro`，当前分支 `int_main`，HEAD `ebabbfcfbf6cbde468f602c5ea18c12346013699`，提交 `任务: 修复发布前端构建内存保护`。
- 前端仓库：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3`，当前分支 `int_main`，HEAD `76328963748ce4bcceaa1d50240e844f1fd3db5d`，提交 `任务: 修复审批重定向页构建阻塞`。
- 三个主工作区均存在未提交改动，本次必须从上述 HEAD 创建干净 worktree 构建，禁止使用主工作区出包。

## Non-Scope

- 不发布未提交改动。
- 不执行数据库、MinIO、展厅数据同步，除非发布脚本预检明确要求并重新记录授权。
- 不修改三环境业务数据。
- 不用 mock、默认成功、手工改状态或静默跳过替代真实发布验证。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - dirty worktree 不得作为部署输入；发布包 manifest 必须证明 `sourceRepos.dirty=false`。
  - 发布完成必须具备 operation、manifest、远端 `.env` / 镜像 tag、健康检查和真实页面证据。
  - 新前端 worktree 若缺少依赖，必须执行 `pnpm install --frozen-lockfile`，不得复用主工作区依赖目录。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `code-only` 与 `SkipDatabaseSync` 不跳过 schema、required SQL、迁移元数据或 manifest 门禁。
  - 构建成功出口是脚本成功、Manifest v1 存在且 NAS 目标发布目录完成上传。
  - 测试服先发布并验证，通过后才能继续正式服和备份服。
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
  - 当前任务已由用户明确授权发布测试服、正式服和备份服。
  - 发布前确认目标主机、目录、容器、数据盘和远端容量；备份服必须显式使用 `/mnt/intruoyi-data`。
  - 远端凭据不得写入仓库、脚本、任务文档或运行控制台配置。
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
  - 涉及管理前端验证时使用真实页面；页面异常必须记录实际入口与影响，不得静默切换环境或账号。
- `D:\ProjectPackage\Int\IntRuoyi\docs\worktree-memory.md`
  - 发布隔离 worktree 必须记录路径、分支、commit、构建命令和验证命令。
  - 清理前必须预览并确认只处理本任务 worktree、运行时和临时产物。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - 同一 releaseTag 必须一次性走通 build/test/mark-tested/prod/backup；不要拼接多轮结果。
  - 处理 RUNNING 锁前必须核活跃进程和 operation 真实状态，禁止直接改锁。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否；缺少凭据、manifest、远端访问、真实运行态证据或控制台版本说明时直接阻塞。
- `是否从根因和长期维护角度解决`：是；本轮通过干净 HEAD worktree、manifest 校验、测试先行和三环境运行态闭环发布。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: 当前 HEAD 干净构建 -> Given 三个主工作区均存在未提交改动且后端/前端 HEAD 可能继续前进 When 从维护仓、后端、前端当前最新 HEAD 创建干净 worktree 并构建 Then 发布包 manifest 必须显示三个 sourceRepos 均为本任务记录的最新 HEAD 且 dirty=false。

BDD: 测试服先行发布 -> Given 发布包 manifest 校验通过 When 部署测试服务器 Then 远端 `.env`、前后端镜像 tag、容器状态、健康检查、前端页面和运行控制台版本说明均显示本次 releaseTag。

BDD: 正式服与备份服发布门禁 -> Given 测试服验证通过且已标记测试通过 When 依次发布正式服和备份服 Then 两个环境真实运行态均与同一 releaseTag 一致，运行控制台显示版本号和变更说明。

## Milestones

1. 完成任务文档、经验门禁、Git HEAD 与 dirty 状态记录。`COMPLETED`
2. 创建干净 HEAD 构建来源并构建维护控制台。`COMPLETED`
3. 通过运行控制台构建发布包并校验 manifest。`COMPLETED`
4. 发布测试服并验证真实运行态。`COMPLETED`
5. 标记测试通过、发布正式服和备份服并验证真实运行态。`IN_PROGRESS`
6. 记录经验沉淀、收尾清理预览、提交本任务文档。`PENDING`

## Expected Verification

- 三个仓库 `git status --short --branch` 和 `git rev-parse HEAD` 已记录。
- 干净 worktree 初始 `git status --short` 为空。
- 维护控制台构建通过。
- 发布包 manifest 显示 `releaseTag=release-20260627-head-full-v1` 或本轮最终重试标签、`component=intruoyi`、`publishScope=code-only`、三个 sourceRepos commit 与本任务一致且 `dirty=false`。
- manifest 或运行控制台 release notes 能看到本次版本号和对应变更说明。
- 测试服、正式服、备份服：远端 `.env`、`docker compose ps`、后端健康、前端页面、运行控制台 release-status 与 release notes 均一致。

## Current Status

COMPLETED：`release-20260628-0015-head-full-v17` 已完成 `build-release -> deploy test -> mark-tested -> promote prod -> promote backup` 全链路。测试服、正式服、备份服均已通过只读运行态验证，远端 `.env`、后端镜像、前端镜像、后端健康检查和前端入口均与 v17 一致。

## Verification Evidence

- `D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\scripts\build.ps1` 构建维护控制台成功。
- 本机运行控制台 `http://127.0.0.1:48181/actuator/health` 返回 `UP`，且发布页面 `build-release` 预览已显示：
  - 脚本：`D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260627-3eb9047\ops\deploy\publish-int-ruoyi.ps1`
  - 后端源：`D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260627-ebabbfc`
  - 前端源：`D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260627-7632896`
  - 参数含 `-Mode build-release`、`-ReleaseTag release-20260627-2350-head-full-v6`、`-SkipDatabaseSync`、`-SkipMinioSync`
- 运行控制台真实执行 `build-release` 产生 operation `op-2026-06-26T203544816067200Z-7af990fb-ef4f-4038-901c-888076d1661c`，失败摘要 `命令退出码非 0: 1`；执行日志定位到 `20260624_unified_electronic_signature_menu.sql:99` 使用变量菜单 id。
- 第二次运行控制台真实执行 `build-release` 产生 operation `op-2026-06-26T204120738837700Z-25253bc1-c5c0-4014-a23e-7ef808100cc5`，再次失败摘要 `命令退出码非 0: 1`；日志确认阻塞点为同一 SQL 第 99 行 `tmp_unified_signature_child_menu_ids` 的变量 id。
- 真实后端仓已新增/更新契约测试并完成三轮 SQL 修复、一次发布脚本构建入口修复；当前 `python -X utf8 -m pytest script\tests\test_unified_electronic_signature_menu_sql.py -q` 返回 `6 passed`，`python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 返回 `status=passed`、`migrationCount=217`，`python -X utf8 D:\ProjectPackage\Int\IntRuoyiMaintance\ops\release\release_sql_contract_gate.py ...\20260624_unified_electronic_signature_menu.sql` 返回 `PASS`，且 `python -X utf8 -m pytest script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` 返回 `90 passed`。
- 真实前端仓已完成重定向页空模板修复；当前 `node tests/e2e/redirect-template-root-static.spec.js`、`node tests/e2e/approval-center-phase5-retirement-static.spec.mjs` 与 `pnpm build:test` 均返回 `PASS`，最新前端提交为 `76328963748ce4bcceaa1d50240e844f1fd3db5d`。
- 只读核对本机 `config/runtime-control.local.yaml` 与当前 Java 启动命令，确认运行控制台现已固定读取 `repo-root=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260627-ebabbfc`、`frontend-root=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260627-7632896`，不再漂移回主工作区。
- 最新真实页面 `build-release` operation `op-2026-06-27T034552307086100Z-d5d79836-4ec1-4ee5-b0ef-bdff8e971f94` 已 `SUCCESS`，release tag 为 `release-20260627-2350-head-full-v6`。
- 本地产物目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260627-2350-head-full-v6` 已生成 `manifest.json` 与 `release-manifest.json`；NAS 目录 `\\172.30.30.4\IT共享\Backup\ReleasePackage\release-20260627-2350-head-full-v6` 已完成上传。
- manifest 核对结果：后端 commit=`ebabbfcfbf6cbde468f602c5ea18c12346013699`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两者 `dirty=false`；运行控制台 `release-packages` 已显示该发布包 `status=AVAILABLE`、`tested=false`。
- 真实页面测试服发布 operation `op-2026-06-27T040320387887200Z-cf7a52cd-2025-43d3-b485-f8b027c4f58f` 已生成并进入远端执行；日志确认测试服 `172.30.30.58` 的 SSH、数据盘校验、`.env` 写入与 `IMAGE_TAG=release-20260627-2350-head-full-v6` 校验、发布包/required-sql/ops-runtime 同步均成功。
- 同一 operation 在执行 `20260624_dcc_view_matrix_independent_seed.sql` 时失败，测试服远端 MySQL 返回 `VIEW_MATRIX_SEED_TENANT_REQUIRED: set @dcc_view_matrix_seed_tenant_id before sourcing this SQL`；本地 operation JSON 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。
- 后端仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260627-release-required-sql-dcc-view-matrix-tenant-context\` 已完成两轮本地 TDD 修复与回归：
  - 第一轮：发布脚本注入 `@dcc_view_matrix_seed_tenant_id` 上下文，`python -X utf8 -m pytest script\tests\test_publish_int_ruoyi_to_test_tooling.py -q` 返回 `91 passed`
  - 第二轮：DCC seed / 测试租户前置 SQL 与真实组织树对齐，`python -X utf8 -m pytest script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_dcc_view_matrix_independent_seed_sql.py script\tests\test_dcc_view_matrix_excel_seed_sql.py -q` 返回 `95 passed`
  - 附加契约：`python -X utf8 script\dcc_view_matrix_independent_seed_sql_test.py` 与 `python -X utf8 script\dcc_view_matrix_test_tenant_prereq_sql_test.py` 均返回 `PASS`
- 真实页面测试服重跑 operation `op-2026-06-27T072114322041600Z-826c3463-e987-40cb-a9af-9a14a903c669` 已验证维护仓脚本排序修复真实生效：日志出现 `Applying required database SQL: 20260624_dcc_view_matrix_test_tenant_prereq.sql`（line 1784），随后出现 `Applying required database SQL: 20260624_dcc_view_matrix_independent_seed.sql`（line 1803），说明此前“运行控制台实际脚本漏执行 prerequisite”的根因已关闭。
- 同一 operation 继续推进后，在 `Applying required database SQL: 20260625_dcc_fvm_matrix_retain_other_completion.sql`（line 1878）处失败，测试服远端 MySQL 返回 `ERROR 1644 (45000) at line 404: DCC_FVM_RETAIN_OTHER_COMPLETION_CATEGORY_BASELINE_CHANGED`；本地 operation JSON 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。
- 继续只读核对测试服 `tenant_id=1` 的 `dcc_file_category` 后，已确认该 SQL 首道基线断言与真实数据不一致：脚本硬编码要求 `active_total=60`、`dcc_fvm_count=59`、`other_count=1`，而测试服真实结果为 `active_total=81`、`dcc_fvm_count=32`、`other_count=1`、`intauth_count=48`；因此当前失败根因是 SQL 基线假设过期，不是 prerequisite 排序或执行链路问题。
- 最新真实页面 `build-release` operation `op-2026-06-27T101820542591Z-7b85c77c-eb8d-48b1-89b7-f3f35968efce` 已 `SUCCESS`，release tag 为 `release-20260628-1835-head-full-v11`。
- 本地 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-1835-head-full-v11\manifest.json` 已核对：后端 commit=`8632c424ba2cb80ba2ac4c4342945fc859a6edc3`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均为 `dirty=false`。
- 真实页面测试服发布 operation `op-2026-06-27T103042306966Z-b5687d95-24b9-4b0e-b2a6-f4248c6bbbbb` 已进入远端执行并真实越过旧 SQL blocker；日志确认 `20260625_dcc_fvm_matrix_retain_other_completion` 被正确 `Skipping required database SQL outside target environment`，`20260626_showroom_product_current_bu_normalization.sql` 已真实执行并回写为 `APPLIED`。
- 同一 operation 最终在测试服启动服务阶段失败：`docker compose up -d --no-deps backend frontend` 返回 `error while creating mount source path '/mnt/nas/Backup/BackupPackage': mkdir /mnt/nas: file exists`；本地 operation JSON 最终状态为 `FAILED`、摘要 `命令退出码非 0: 1`。
- 只读比对候选包 `docker-compose.yml`、远端 `/opt/intruoyi/runtime/docker-compose.yml`、`docker compose config`、`docker inspect intruoyi-backend` 和宿主机 `/proc/self/mountinfo` 后确认：
  - `backend` 固定包含 bind mount `/mnt/nas/Backup/BackupPackage:/mnt/nas/Backup/BackupPackage`
  - 旧后端容器历史上已成功使用过该 mount，不是本轮新改动
  - 宿主机 `/mnt/nas` 当前挂载为 `//172.30.30.4/IT共享`，mount 选项显示 `username=ceshi`
  - 远端 root 对 `/mnt/nas`、`/mnt/nas/Backup`、`/mnt/nas/Backup/BackupPackage` 的 `ls/stat/os.stat` 均报 `Permission denied`
  - `namei -l /mnt/nas/Backup/BackupPackage` 在 `nas` 节点报 `无此文件或目录`
- `docker inspect intruoyi-backend` 的 `State.Error` 与 operation 日志中的 mount 报错一致
- 测试服 root 主目录当前存在 `/root/.smbcredentials`（`username=BJB110`）与 `/root/.smbcred_backup`（`username=beifen`），均与坏挂载 `username=ceshi` 不一致；同时远端 `smbclient -L //172.30.30.4 -U int%<redacted>` 可成功列出 `IT共享`，说明 NAS 本身与当前 `int` 凭据可用。
- 已在测试服执行最小正式修复：`umount -v /mnt/nas` 卸载旧坏挂载，恢复并重建本地空目录 `/mnt/nas` 后，以 `username=int` 重新执行 `mount -t cifs '//172.30.30.4/IT共享' /mnt/nas ...`。
- 修复后验证通过：`/proc/mounts` 显示 `/mnt/nas` 当前已变为 `username=int`；宿主机可成功访问 `/mnt/nas/Backup/BackupPackage`；`docker run --rm -v /mnt/nas/Backup/BackupPackage:/probe alpine:3.20 ...` 返回 `DOCKER_BIND_OK`。
- 修复后重新从真实页面发起测试服发布 operation `op-2026-06-27T105253570049600Z-36d2fc17-9145-40aa-b1c6-6a1c2d2c7ed2`，日志与远端状态表明：
  - operation 已重新完成 SSH 预检、镜像加载、MySQL/Redis 启动、发布锁获取与 `required-sql` 迁移回写。
  - `20260624_dcc_view_matrix_test_tenant_prereq`、`20260624_dcc_view_matrix_independent_seed`、`20260626_showroom_keyword_schema_seed_runtime`、`20260626_showroom_keyword_bu_seed_runtime`、`20260626_showroom_product_current_bu_normalization` 等此前 blocker 均已真实越过并被回写为 `SKIPPED_ALREADY_APPLIED`。
  - 远端当前 `/proc/mounts` 仍显示 `/mnt/nas` 为 `username=int`，宿主机 `os.stat('/mnt/nas/Backup/BackupPackage')` 成功，手工 `docker run --rm -v /mnt/nas/Backup/BackupPackage:/probe alpine:3.20 ...` 继续返回 `DOCKER_BIND_OK`。
  - 但同一时刻 `docker inspect intruoyi-backend --format '{{.State.Status}}|{{.State.Running}}|{{.State.Error}}|{{.Config.Image}}'` 仍返回 `created|false|error while creating mount source path '/mnt/nas/Backup/BackupPackage': mkdir /mnt/nas: file exists|intruoyi-backend:release-20260628-1835-head-full-v11`，而 `intruoyi-frontend` 也停在 `Created`。
  - operation 执行日志已出现发布锁释放 `LOCK_RELEASED` 与 `ERROR: 命令退出码非 0: 1`，只是本地 operation JSON 尚未来得及从 `RUNNING` 刷新为最终失败状态。
- 真实页面测试服发布 operation `op-2026-06-27T111300642917500Z-84f1824f-db7c-4571-8c78-c52231bcc51e` 已越过维护仓空 `applyItems` bug 后继续执行到 `docker compose up -d --no-deps backend frontend` 与远端 HTTP readiness；远端 `docker logs intruoyi-backend` 明确报 `no main manifest attribute, in app.jar`，后端容器持续重启。
- 后端发布源 `D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260627-8632c42` 已完成可执行 jar 镜像入口修复并提交 `d3ee53edaf015f98ec3bfebf9f91602103568b6d`，其中两个 Dockerfile 已统一复制 `yudao-server-exec.jar`。
- 真实页面重试构建 operation `op-2026-06-27T113224282720200Z-dd2ed29c-419b-4309-9e8d-8504c7c578c0` 在 backend image `docker build` 阶段失败，日志明确报 `COPY ruoyi-vue-pro/yudao-server/target/yudao-server-exec.jar app.jar` 找不到文件；失败摘要仍为 `命令退出码非 0: 1`。
- 继续只读核对维护控制台脚本后，已确认根因是 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1` 与当前运行 worktree 仍把后端 jar 路径/复制目标写死为 `yudao-server.jar`，没有与后端仓新的 `exec` jar 契约同步。
- 维护仓现已完成最小正式修复并同步到当前运行 worktree：
  - `$backendJar` 改为 `yudao-server\target\yudao-server-exec.jar`
  - Docker build context 中复制目标改为 `yudao-server-exec.jar`
- 本地回归 `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` 已通过 `8 passed`，其中新增契约测试约束发布脚本必须使用 `exec jar`。
- 真实页面测试服发布 operation `op-2026-06-27T125259682648200Z-a77f32ea-36b0-4ccb-97c2-d96effb42d26` 已 `SUCCESS`，release tag=`release-20260628-2015-head-full-v13`。
- 测试服发布日志确认：远端 MySQL/Redis 健康、required SQL 迁移回写、`docker compose up -d --no-deps backend frontend`、后端 HTTP readiness、前端 HTTP readiness、scheduler smoke runtime 检查、发布锁 `LOCK_RELEASED` 均通过。
- 测试服最终运行态核对：`docker compose ps` 显示 `intruoyi-backend|running|intruoyi-backend:release-20260628-2015-head-full-v13`、`intruoyi-frontend|running|intruoyi-frontend:release-20260628-2015-head-full-v13`，远端 `.env` 显示 `IMAGE_TAG=release-20260628-2015-head-full-v13`。
- 测试服健康核对：`http://172.30.30.58:48081/actuator/health` 返回 HTTP 200 且内容为 `{"status":"UP"}`；`http://172.30.30.58:8081/` 返回 HTTP 200。

## Final Verification

- 构建发布：runtime-control `build-release` operation `op-2026-06-27T160959148735600Z-10a9a4be-9806-485e-b84f-736813806996` 最终 `SUCCESS`，release tag=`release-20260628-0015-head-full-v17`。
- 发布包核对：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260628-0015-head-full-v17\manifest.json` 显示后端 commit=`de2c66fb83deee1e08ea9d60647d532501515b52`、前端 commit=`76328963748ce4bcceaa1d50240e844f1fd3db5d`，两个 sourceRepos 均 `dirty=false`。
- 测试服发布：runtime-control `publish-test` operation `op-2026-06-27T162359407428600Z-5df2d01d-4ddb-4a12-8758-ed258cfee69e` 最终 `SUCCESS`；测试服 `.env IMAGE_TAG=release-20260628-0015-head-full-v17`，后端/前端镜像均运行 v17，health `{"status":"UP"}`，前端 HTTP `200`。
- 标记测试通过：runtime-control `mark-release-tested` operation `op-2026-06-27T163633543263400Z-3d0408ea-09b5-4aa3-8e5f-a157c5454f8b` 最终 `SUCCESS`。
- 正式服发布：runtime-control `promote-prod` operation `op-2026-06-27T165516540152300Z-1f99ed56-fc7d-4175-92c5-f0f608bf7208` 最终完成；正式服 `.env IMAGE_TAG=release-20260628-0015-head-full-v17`，后端/前端镜像均运行 v17，health `{"status":"UP"}`，前端 HTTP `200`。
- 备份服发布：runtime-control `promote-backup` operation `op-2026-06-27T171709623597300Z-4014e39d-d9e3-4380-9100-bc0d8b5990eb` 最终 `SUCCESS`；备份服 `.env IMAGE_TAG=release-20260628-0015-head-full-v17`，后端/前端镜像均运行 v17，`/mnt/intruoyi-data` 挂载在 `/dev/mapper/cl-home`，health `{"status":"UP"}`，前端 HTTP `200`。

## Blockers

- 无剩余阻塞。已关闭的关键问题包括：正式服 DCC seed 缺少 tenant 1 授权变量、正式服 DCC FVM 分类基线过严、正式服 `/mnt/nas` CIFS 凭据错误导致 Docker bind mount 失败。

## Next Required Action

- 无发布链路后续动作。若需要正式归档本次发布，可基于 `execution-log.md` 生成发布复盘或版本公告。
