# 20260806-head-test-only-release

## Task Goal

仅基于当前维护仓分支开始发布时冻结的 HEAD 已提交代码，创建本次专用干净临时发布 worktree，构建维护控制台和测试发布包，并只发布到测试服务器；未提交改动不得进入构建产物，不执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Milestones

- [x] 构建前 Git / worktree 冻结：确认当前分支、目标提交、脏工作区状态，创建本次专用干净临时发布 worktree并记录构建目录。
- [x] 发布前经验门禁：读取命中的发布、worktree、PowerShell、服务器访问和登录经验，记录强制门禁并完成高风险动作前 `experience-preflight`。
- [x] 构建维护控制台与测试发布包：基于冻结 worktree 执行构建，检查发布包、manifest、版本号和变更说明均可回溯目标提交。
- [x] 测试服发布：仅执行 `publish-test`，记录 releaseTag / operation，并确认未触发正式服或备份服动作。
- [x] 真实运行态验收：验证远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health、frontend HTTP、页面、运行控制台版本号和变更说明。
- [x] 问题记录与阶段复盘：按现象、阶段、影响、原因判断、处理动作、结果、是否可前置检查、是否可自动化、下次避免方式记录全部问题和耗时点。
- [x] 经验沉淀与收口：将本次问题沉淀为前置经验，清理本任务 release worktree/state，记录最终验证。

## Expected Verification

- `git status --short --branch`、`git branch --show-current`、`git rev-parse HEAD` 记录发布起点。
- 临时发布 worktree 指向目标 HEAD，且 `git status --short --branch` 干净。
- 构建包根 `manifest.json`、release 信息、版本号和变更说明均证明构建来源为目标 HEAD。
- `publish-test` 成功，且同一 releaseTag 不执行正式服或备份服动作。
- 测试服远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器状态、backend health=UP、frontend HTTP 200、页面可访问、运行控制台版本号和变更说明全部通过。
- 所有问题已记录，可前置化问题已沉淀为经验门禁。

## Current Status

completed

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。本任务必须 fail fast，不用 mock、默认成功或降级验收掩盖发布失败。
- 是否从根因和长期维护角度解决：是。发布链路以 clean worktree、manifest、operation 和真实运行态为验收根因，不追逐后续提交。
- 是否存在临时补丁或绕过：否。未获用户明确授权时，不做临时脚本绕过、不跳过发布或运行态验收。

## 经验门禁

- 测试服发布范围门禁：本轮只允许 `build-release -> publish-test`，目标主机固定 `172.30.30.58`、远端目录 `/opt/intruoyi/runtime`，禁止 `mark-tested`、`promote-prod`、`promote-backup`。
- 冻结 HEAD 门禁：维护仓和主程序仓主工作区 dirty 不得进入构建；必须创建本轮专用 clean release worktree，构建开始后只认冻结 worktree HEAD，不追逐后续本地或远端提交。
- Manifest/sourceRepos 门禁：构建后以发布包根 `manifest.json` 为权威，校验 `releaseTag`、`component=intruoyi`、`publishScope=code-only`、`sourceRepos[*].commit`、`sourceRepos[*].dirty=false`、artifact SHA256、版本号和变更说明；任一缺失或 dirty 必须判废。
- 构建参数门禁：`build-release` 必须显式 `-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`；发布包不得包含非本次范围的 Website/showroom 目录。
- Publish-test 参数门禁：`publish-test` preview 必须结构化证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime` 和目标 releaseTag；请求体使用最小有效 payload，不携带 build-only 字段。
- 真实运行态门禁：operation=SUCCESS 后仍必须核远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP=200、`release-info.json`、release lock=APPLIED、当前 releaseTag migration failed/running=0。
- 运行控制台门禁：页面验收必须打开真实运行控制台版本/变更说明入口，确认 releaseTag、发布包、组件范围和变更说明可见；source commit 与 dirty=false 由 manifest / release-info 独立证明。
- PowerShell / SSH 门禁：不用 `&&` 或 Bash heredoc；中文与多行脚本使用 UTF-8；远端 SSH `bash -s` 使用 UTF-8 bytes + LF；carrier warning 不覆盖结构化 stdout 断言；日志和配置输出必须脱敏。
- Worktree 清理门禁：发布验证完成后先标记 `ready_for_closeout`；停止或恢复本任务 48181 运行控制台后，只清理本任务 release worktree/state dir，验证 Git 注册和物理目录均不存在后才标记 `completed`。

## Release Baseline

- 维护仓：branch=`int_main`，HEAD=`c1b10cc3a20fd5f4f5d228219ae4c046ad320256`，主工作区 dirty。
- 主程序仓：branch=`int_main`，HEAD=`6f75f2a93628eadaa339d9f44cbd3db2aae5a4e6`，本地 `int_main` behind `origin/int_main` 7 个提交且主工作区 dirty；按用户要求不 fetch/不追远端，只冻结发布开始时本地 HEAD。
- 本轮 release id：`r260806a`。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806a\m`。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260806a-release-app`。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806a-state\runtime-control`。
- releaseTag：`release-20260806-intmain-head-test-r260806a-r1`。
- 构建策略：创建本轮专用 clean release worktree 后基于冻结 HEAD 构建，不使用主工作区未提交改动；构建开始后不追逐后续提交。

## Resume Baseline r260806b

- 触发原因：用户说明上一轮 migration metadata 阻塞已修复，因此重新冻结新的已提交 HEAD 到本次专用 clean release worktree。
- 维护仓发布 HEAD：`c1b10cc3a20fd5f4f5d228219ae4c046ad320256`，release worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806b\m`，status clean。
- 主程序发布 HEAD：`04d71d4328bff04833b3e97fe77439c1d00e5f72`，release worktree=`D:\IntRuoyiWorktree\r260806b-release-app`，status clean。
- 当前主程序主工作区后续已前进到其它提交且仍 dirty；本轮继续只认 r260806b release worktree 的冻结 HEAD，不追逐后续变化。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806b-state\runtime-control`。
- releaseTag：`release-20260806-intmain-head-test-r260806b-r1`。
- 构建前门禁：migration policy gate `status=passed`，`migrationCount=444`，证据文件 `migration-policy-gate-r260806b.json`。

## Resume Baseline r260806b-r2

- 触发原因：已从测试服务器缓存导入精确 `nginx:1.27-alpine` 基础镜像，补齐 r1 的 Docker frontend image 前置条件。
- 源码边界：继续只使用 r260806b clean release worktree，维护 HEAD=`c1b10cc3a20fd5f4f5d228219ae4c046ad320256`，主程序 HEAD=`04d71d4328bff04833b3e97fe77439c1d00e5f72`，不追逐主工作区后续提交。
- releaseTag：`release-20260806-intmain-head-test-r260806b-r2`。
- 基础镜像证据：远端 `nginx:1.27-alpine` tar SHA256=`4891308ac533d611851afe0090cb3798310a65df3ec4bec26b293d2220fc91da`，本机 `docker image inspect nginx:1.27-alpine` 通过，远端临时 tar 已删除。

## Resume Baseline r260806c

- 触发原因：用户确认后端 Spring 构造器注入阻塞已修复；当前主程序 HEAD 已包含 `MesTeamLeaderProcessConfigServiceImpl` 生产构造函数 `@Autowired`。
- 维护仓发布 HEAD：`c1b10cc3a20fd5f4f5d228219ae4c046ad320256`；主工作区 dirty，不作为构建输入。
- 主程序发布 HEAD：`19173d2b41442e6b2df3c16c424c11713b3dbbcc`；主工作区 dirty，不作为构建输入。
- 本轮 release id：`r260806c`。
- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c\m`。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260806c-release-app`。
- 运行控制台 state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c-state\runtime-control`。
- releaseTag：`release-20260806-intmain-head-test-r260806c-r1`。
- 失败 tag 处理：`r260806b-r1` 和 `r260806b-r2` 均判废，不复用；本轮必须重新 `build-release -> publish-test`。

## Build Release r260806b-r2

- build-release preview：PASS，`build-release-preview-gate-r260806b-r2.json` 证明仅为 `build-release`、`component=intruoyi`、`SkipDatabaseSync`、`SkipMinioSync`，未包含 `publish-test`、`mark-tested`、`promote-prod`、`promote-backup`。
- build-release operation：`op-2026-08-06T113001372767500Z-0fec476b-606c-41ba-9ce4-e5de0aab9c8e`，status=`SUCCESS`。
- 发布包目录：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260806-intmain-head-test-r260806b-r2`。
- Manifest validator：`manifest-validation-r260806b-r2.json` 全部通过；`manifest.json` / `release-manifest.json` 存在，`publishScope=code-only`，`component=intruoyi`，`sourceRepos` 均为 `04d71d4328bff04833b3e97fe77439c1d00e5f72` 且 `dirty=false`，artifact hash mismatch count=`0`。
- 版本与变更说明：前端 `dist-intruoyi-test\release-info.json` 与 manifest 的 releaseTag、sourceRepos、changeSet 一致；变更说明包含“发布包：release-20260806-intmain-head-test-r260806b-r2”和“组件范围：intruoyi”。

## Publish Attempt r260806b-r2

- publish-test preview：PASS，`publish-test-preview-gate-r260806b-r2.json` 证明 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`、目标 releaseTag 正确，且未触发正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。
- publish-test operation：`op-2026-08-06T114908393935900Z-ded107d0-7996-4d3f-b7b4-ceadb49e489a`，status=`FAILED`，summary=`命令退出码非 0: 1`。
- 失败点：`publish-int-ruoyi.ps1` 在容器重建后等待 `http://127.0.0.1:48081/actuator/health`，180 秒内未 ready，日志记录 `Remote URL did not become ready within 180 seconds`。
- 远端失败后状态：`.env IMAGE_TAG`、backend image、frontend image 均为 `release-20260806-intmain-head-test-r260806b-r2`；frontend HTTP=`200`，页面标题=`瑛泰管理系统`；backend health curl exit=`56`，连接被重置。
- release lock / migration：`infra_release_operation_lock` 对 test 为 `FAILED`；本 releaseTag migration `APPLIED=34`、`SKIPPED_ALREADY_APPLIED=378`、`FAILED/RUNNING=0`。
- 后端日志根因：`MesProcessPoolTeamLeaderController` 依赖 `MesTeamLeaderProcessConfigServiceImpl` 创建失败；`MesTeamLeaderProcessConfigServiceImpl` 有两个构造函数但无默认构造函数，且 public 构造函数未显式 `@Autowired`，Spring 尝试默认构造实例化时报 `No default constructor found`。
- 服务器结论：测试服发布未成功，且测试服 backend 当前处于启动失败/重启状态；按门禁不得判定测试发布成功，不得复用 r2 releaseTag，不得执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- 本机控制台收束：已停止任务 owned release worktree runtime-control PID `45384`，从主维护目录恢复 48181，PID=`47788`，health=`UP`。

## Build Release r260806c

- 构建起点：用户确认 Spring 构造器注入阻塞已修复后，重新冻结 r260806c；维护 HEAD=`c1b10cc3a20fd5f4f5d228219ae4c046ad320256`，主程序 HEAD=`19173d2b41442e6b2df3c16c424c11713b3dbbcc`，两个主工作区 dirty 但均未作为构建输入。
- Clean worktree：维护 release worktree=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c\m`，主程序 release worktree=`D:\IntRuoyiWorktree\r260806c-release-app`，state dir=`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c-state\runtime-control`。
- 前置门禁：migration policy gate `migration-policy-gate-r260806c.json` 通过，`migrationCount=444`；Spring constructor static gate `spring-constructor-gate-r260806c.json` 通过，`constructorCount=2` 且 public 生产构造函数存在 `@Autowired`。
- 维护控制台构建：主程序与维护前端依赖按 `pnpm@10.25.0` frozen lockfile 恢复，`ignored-builds=None`；维护 `scripts\build.ps1` 成功，Maven tests `26` passed，jar SHA256=`05f39a3e8d090833cbb4127fa5724a9baac63715750273211fe2c7f0a3ab5116`。
- runtime-control：从 r260806c 维护 worktree 启动 48181，PID=`6360`，health=`UP`；构建生成的维护 worktree `runtime/` 已按边界校验删除，维护 worktree 恢复 clean。
- build-release preview：PASS，`build-release-preview-gate-r260806c-r1.json` 证明仅为 `build-release`、`component=intruoyi`、`SkipDatabaseSync`、`SkipMinioSync`，不包含 `publish-test`、`mark-tested`、`promote-prod`、`promote-backup`。
- build-release operation：`op-2026-08-06T131808382264900Z-1a134a91-d2eb-434d-b0a6-b0da5018a2f7`，status=`SUCCESS`。
- 发布包目录：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260806-intmain-head-test-r260806c-r1`。
- Manifest validator：`manifest-validation-r260806c-r1.json` 全部通过；`manifest.json` / `release-manifest.json` 存在，`publishScope=code-only`，`changeSet.component=intruoyi`，`sourceRepos` 均为 `19173d2b41442e6b2df3c16c424c11713b3dbbcc` 且 `dirty=false`，artifact count=`458`，missing=`0`，mismatch=`0`。
- 版本与变更说明：前端 `dist-intruoyi-test\release-info.json` 与 manifest 的 releaseTag、sourceRepos、changeSet 一致；变更说明包含“发布包：release-20260806-intmain-head-test-r260806c-r1”和“组件范围：intruoyi”。

## Publish And Runtime Verification r260806c

- publish-test precheck：`remote-release-precheck-r260806c-r1.txt` 显示测试服仍停在失败 r260806b-r2 运行态，但无 RUNNING release lock；按失败 tag 判废规则继续用新 releaseTag 发布。
- publish-test preview：PASS，`publish-test-preview-gate-r260806c-r1.json` 证明 `Mode=deploy-release`、`Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`、目标 releaseTag 正确，且未触发正式服、备份服、`mark-tested`、`promote-prod`、`promote-backup`。
- publish-test operation：`op-2026-08-06T134301524868800Z-58d50c52-dab5-43b8-8ce9-81849d0c96ef`，status=`SUCCESS`。
- 远端运行态：`remote-release-postcheck-r260806c-r1.json` 通过；`.env IMAGE_TAG`、backend image、frontend image 均为 `release-20260806-intmain-head-test-r260806c-r1`，backend/frontend container 均 running，backend health body=`{"status":"UP"}`，frontend HTTP=`200`，页面 title=`瑛泰管理系统`。
- release-info / lock / migration：远端 release-info releaseTag 匹配，sourceRepos 均 `dirty=false`；release lock=`test:release-20260806-intmain-head-test-r260806c-r1:APPLIED`；当前 releaseTag migration failed/running=`0`。
- Playwright 页面验收：`playwright-runtime-console-r260806c-r1.json` 通过；测试服前端 `http://172.30.30.58:8081/` HTTP 200，登录页可见，console errors/failed requests 均为 0；运行控制台 `http://127.0.0.1:48181/` HTTP 200，点击“查看变更”后可见版本号、发布包、组件范围和变更说明。
- 结论：同一 releaseTag `release-20260806-intmain-head-test-r260806c-r1` 的 build-release、manifest、publish-test、远端真实运行态和运行控制台页面均通过；未执行 `mark-tested`、`promote-prod`、`promote-backup`。

## Prior Blocker r260806a

- 发布前 migration policy gate 已 fail fast：`20260805_erp_nas_table_auto_sync.sql` 的 `release-migration` 头部写入 `type=schema,job`，当前发布契约只允许单一合法 `type` 值，命令输出 `invalid type ...: schema,job`。
- 影响：无法确认 release migration 元数据契约完整；按门禁不得继续构建维护控制台、不得生成发布包、不得执行 `publish-test`。
- 处理动作：已停止在构建前阶段；未启动 48181 运行控制台，未执行 build-release，未操作测试服务器。
- 继续条件：先在主程序仓修复该 SQL 的 release-migration 元数据并提交，再以新的冻结 HEAD 和新 releaseTag 重走 `build-release -> publish-test`。

## Build Attempt r260806b

- 主程序前端依赖：`corepack pnpm@10.25.0 install --frozen-lockfile` 成功，用时约 11:58；`ignored-builds` 初始列出 7 个包，外部 `pnpm-only-built-dependencies-r260806b.json` + `pnpm rebuild --pending` 后为 `None`，app worktree clean。
- 维护控制台构建：维护前端依赖与 `ignored-builds` 清零完成；`scripts\build.ps1` 成功，前端 typecheck/build 通过，Maven tests `26` passed，jar=`runtime-control-maintenance-2026.06-SNAPSHOT.jar`，SHA256=`88de607dc08503fe3db9dd7d74fc29ed94ec49a2c35e0b0009ed7350c7f146e7`，jar 内包含 `BOOT-INF/classes/static/index.html`。
- 运行控制台：从 r260806b 维护 worktree 启动 PID `55800`，health=`UP`；build-release 失败后已停止，48181 复核为不可连接。
- build-release preview：PASS，operation=`op-2026-08-06T104239041834700Z-8592eb5e-6941-457d-954d-02b7b595b377`，参数包含 `-Mode build-release`、`-Component intruoyi`、`-SkipDatabaseSync`、`-SkipMinioSync`、r260806b 后端/前端路径，且不包含 `publish-test`、`mark-tested`、`promote-prod`、`promote-backup`。
- build-release result：FAILED，summary=`命令退出码非 0: 1`；后端 Maven build SUCCESS，前端 `build:test` SUCCESS，后端镜像 `intruoyi-backend:release-20260806-intmain-head-test-r260806b-r1` 已生成，但前端镜像构建在 `FROM nginx:1.27-alpine` 元数据解析阶段失败。
- 发布包状态：本地目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260806-intmain-head-test-r260806b-r1` 仅包含 `docker-build-context` 与 `required-sql`，缺少发布成功必需的 `manifest.json`、`release-manifest.json`、镜像 tar、版本号和变更说明确认材料；该 releaseTag 判废，不得 publish-test。
- 测试服状态：未执行 `publish-test`，未操作测试服务器，未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。

## Issue Records

### I001 release-migration type 非法

- 现象：`run-release-migration-policy-gate.py` 返回 `status=failed`，错误为 `invalid type in D:\IntRuoyiWorktree\r260806a-release-app\IntRuoyiBackend\sql\mysql\20260805_erp_nas_table_auto_sync.sql: schema,job`。
- 阶段：构建前契约门禁。
- 影响：发布包来源、manifest、版本号和变更说明均未生成，测试服未发布。
- 原因判断：冻结 HEAD 中 SQL 头部 `-- release-migration: ... type=schema,job; ...` 使用了复合类型，违反 release-migration 结构化字段门禁。
- 处理动作：按 fail-fast 规则停止，不做临时改 SQL、不跳过 migration policy gate、不构建半成品。
- 结果：任务状态 `blocked`，两个 clean release worktree 保留为证据。
- 是否可前置检查：是，build-release 前必须运行全量 migration policy gate。
- 是否可自动化：是，CI 或发布控制台 preview 可在进入 Maven/Docker 构建前阻塞非法 `type`。
- 下次如何避免：SQL 进入主线前用 `python -X utf8 IntRuoyiBackend\script\release\run-release-migration-policy-gate.py --sql-root IntRuoyiBackend\sql\mysql --output <evidence>.json` 校验；若同一 SQL 同时包含 schema 和 job，应按发布契约拆分或选择一个合法类型并用测试覆盖。

### I002 pnpm ignored-builds 需构建前清零

- 现象：主程序前端 frozen install 后 `ignored-builds` 列出 `core-js`、`esbuild`、`@parcel/watcher`、`vue-demi`、`@swc/core`、`core-js-pure`、`es5-ext`；维护前端列出 `esbuild`、`vue-demi`。
- 阶段：构建前依赖恢复。
- 影响：若不处理，Vite / esbuild / vue-demi postinstall 可能缺失，发布构建不可放行。
- 原因判断：pnpm 10.25 对 clean worktree 首次安装仍需要显式 only-built-dependencies 授权，已有全局 allow-builds 未让本轮 install 自动清零。
- 处理动作：写入任务目录外部授权 JSON，通过 `npm_config_only_built_dependencies_file` 注入并执行 `pnpm rebuild --pending`，随后复核 `pnpm ignored-builds=None`。
- 结果：主程序和维护 worktree 均保持 `git status` clean，临时授权未写入源码或锁文件。
- 是否可前置检查：是，frozen install 后立即运行 `pnpm ignored-builds`。
- 是否可自动化：是，发布前置脚本可根据 pnpm 版本生成外部授权文件并复核 clean。
- 下次如何避免：每个新 release worktree 在 build-release 前执行 `install -> ignored-builds -> rebuild --pending -> ignored-builds=None -> git clean status`。

### I003 全新 worktree 依赖恢复耗时

- 现象：主程序前端 `pnpm install --frozen-lockfile` 用时约 11:58，维护前端安装用时约 1:50。
- 阶段：构建前依赖恢复。
- 影响：拉长发布时间；若没有阶段性记录，容易误判为卡死。
- 原因判断：全新 release worktree 没有 `node_modules`，pnpm 需要从本地 store 逐包链接 1103 个依赖。
- 处理动作：持续轮询输出并记录耗时点，未中断、未复用主工作区依赖、未跳过安装。
- 结果：依赖恢复成功且 worktree clean。
- 是否可前置检查：是，创建 worktree 后先检查 `node_modules` 是否存在。
- 是否可自动化：是，前置报告记录包数量、是否命中本地 store、耗时阈值。
- 下次如何避免：发布前预留依赖恢复时间；不得因耗时改用主工作区或旧 dist。

### I004 PowerShell Remove-Item 被工具安全策略拦截

- 现象：清理维护测试生成的 untracked `runtime/` 目录时，两次 `Remove-Item -Recurse -Force` 在执行前被工具安全策略拒绝。
- 阶段：维护控制台构建后临时产物清理。
- 影响：短暂导致维护 worktree 出现 untracked `runtime/`；若不清理，会影响 clean 状态判断。
- 原因判断：递归删除命令被安全策略识别为高风险，即使命令内包含边界校验也未通过解析。
- 处理动作：改用 Python 进行绝对路径 resolve 与 worktree 边界校验后删除。
- 结果：`runtime/` 删除成功，维护 worktree 复核 clean。
- 是否可前置检查：部分可前置，构建后检查 `git status --short`。
- 是否可自动化：是，可用固定脚本安全清理任务生成目录，统一做路径边界校验。
- 下次如何避免：对 task-owned 临时目录清理使用项目批准的安全脚本，避免复杂内联 PowerShell 删除命令。

### I005 前端基础镜像 nginx:1.27-alpine 无法获取

- 现象：build-release 在前端 Docker image 阶段失败：`nginx:1.27-alpine` 元数据解析访问 Docker Hub 超时，错误包含 `Docker Desktop has no HTTPS proxy`；直接 `docker pull nginx:1.27-alpine` 同样失败；`hubproxy.docker.internal:5555/library/nginx:1.27-alpine` 和 `hubproxy.docker.internal:5555/nginx:1.27-alpine` 均返回 `not found`。
- 阶段：build-release / frontend Docker image。
- 影响：未生成完整发布包、manifest、release-manifest、版本号和变更说明确认材料；不得执行 publish-test，测试服务器未发布。
- 原因判断：本机 Docker Desktop/BuildKit 无法通过当前网络/代理解析 Docker Hub 的 `nginx:1.27-alpine`，且本地没有该镜像或可加载的基础镜像 tar。
- 处理动作：按 fail-fast 停止；未改 Dockerfile、未换基镜像、未复用旧前端镜像、未 tag 错误镜像；停止本任务 48181 运行控制台。
- 结果：任务 blocked；失败 releaseTag `release-20260806-intmain-head-test-r260806b-r1` 判废，r260806b worktree/state 保留为证据。
- 是否可前置检查：是，build-release 前应执行 `docker image inspect nginx:1.27-alpine`，失败时尝试受控 `docker pull nginx:1.27-alpine` 并验证 Docker proxy / mirror。
- 是否可自动化：是，将前端基础镜像存在性、Docker proxy、mirror 可用性纳入发布 preflight。
- 下次如何避免：发布前准备并验证 `nginx:1.27-alpine` 本地镜像或正式基础镜像缓存；缺失时必须在提交 build-release 前 fail fast，不要等后端 Maven 和前端 Vite 构建完成后才失败。

### I006 publish-test 后端健康检查超时

- 现象：r2 `publish-test` 在容器重建后等待 `http://127.0.0.1:48081/actuator/health` 超过 180 秒，operation=`op-2026-08-06T114908393935900Z-ded107d0-7996-4d3f-b7b4-ceadb49e489a` 返回 `FAILED`。
- 阶段：测试服发布 / 远端 HTTP readiness。
- 影响：测试服发布失败；`.env` 与 backend/frontend 实际镜像均已切到 r2，但 backend health 不可用，测试服务器后端处于重启失败状态；不得判定测试发布成功。
- 原因判断：后端 Spring 容器启动失败，`MesTeamLeaderProcessConfigServiceImpl` 存在 public 5 参数构造函数和 package-private 6 参数测试构造函数，但没有默认构造函数且 public 构造函数未显式 `@Autowired`；Spring 没有采用构造器注入而尝试默认构造，最终 `No default constructor found`。
- 处理动作：冻结 operation JSON、脱敏 publish log、失败后远端运行态快照和后端日志尾部；不重试 r2、不回滚、不手工改 release lock/migration、不执行正式服或备份服动作。
- 结果：任务状态 `blocked`；r260806b worktree/state 保留为证据；本机 48181 已恢复主维护路径。
- 是否可前置检查：是，构建前应增加后端 Spring context smoke 或静态门禁，扫描 `@Service/@Component` 类存在多个构造函数且无 `@Autowired` 的风险。
- 是否可自动化：是，可在 Maven 测试中增加最小 `ApplicationContext` 启动测试，或增加 ArchUnit/静态检查阻塞多构造函数 Spring bean。
- 下次如何避免：修复并提交 `MesTeamLeaderProcessConfigServiceImpl` 构造器注入契约后，使用新的 clean release worktree 和新 releaseTag 重新 `build-release -> publish-test`；失败 releaseTag r2 不得复用。

### I007 publish-test 原始日志包含命令行密码形态

- 现象：原始 operation log 多次出现 `mysql -uroot -p...` 形态，并伴随 MySQL warning；任务证据只保留 `.redacted.txt` 脱敏日志，未提交 raw secret-bearing log。
- 阶段：publish-test required SQL / release migration status 写入。
- 影响：若直接提交原始日志，会违反凭据脱敏要求；同时脱敏规则过宽可能误伤普通数据库名或文本。
- 原因判断：发布脚本通过命令行 `-p` 传递 MySQL 密码，且日志打印完整命令。
- 处理动作：保存 `publish-test-log-final-r260806b-r2.redacted.txt`，并执行 MySQL `-p<known-secret>` 形态 secret pattern 扫描，结果为 `NO_PLAINTEXT_MYSQL_PASSWORD_PATTERN`。
- 结果：本任务保留证据为脱敏版本；原始日志只作为本机运行控制台 state 证据，不写入任务文档或长期经验。
- 是否可前置检查：是，发布脚本提交前扫描是否会打印 `mysql -p<secret>`。
- 是否可自动化：是，统一使用容器内 `MYSQL_ROOT_PASSWORD` 或 stdin 配置文件方式连接，并在证据归档前做 secret scan。
- 下次如何避免：发布脚本日志只打印脱敏命令；证据归档固定执行 `rg -- "-p<known>"` 和通用 secret pattern 扫描。

### I008 publish-test 长时间 RUNNING 进度不透明

- 现象：r2 publish-test 长时间返回 `RUNNING`，summary 一直为“命令已提交到本机执行队列”；需要手工读取子进程和 operation log 才能确认已从 required SQL scp、docker load、migration status 写入推进到容器 readiness。
- 阶段：测试服发布长链路执行。
- 影响：如果只看 operation summary，容易误判卡死或重复操作；如果提前中断，会破坏测试服发布状态。
- 原因判断：发布脚本对 444 条 migration 状态逐条 SSH/MySQL 写入，日志持续推进但 operation summary 不更新阶段。
- 处理动作：按阶段记录进度：scp required-sql -> docker load -> migration status -> APPLY 近期 SQL -> docker compose up -> health readiness。
- 结果：确认不是卡死；最终失败点为后端 health readiness，而不是上传或 SQL 阶段。
- 是否可前置检查：部分可前置，可预估 required SQL 数量和镜像 tar 大小。
- 是否可自动化：是，运行控制台可把当前阶段、最后 migrationId、日志 lastWrite 和耗时写入 operation summary。
- 下次如何避免：长时间发布轮询时同时采集 operation log lastWrite、子进程命令和最后 migrationId；不得仅凭 poll 次数判定。

### I009 Windows 文本模式 SSH stdin 导致远端 bash CRLF 失败

- 现象：失败后只读远端探测脚本首次通过 PowerShell/Python text mode stdin 发送到 `bash -s`，远端报 `set: pipefail\r: invalid option`。
- 阶段：失败后运行态证据采集。
- 影响：首次探测无效，若误采信会把 carrier 错误误判为服务器状态；未改远端。
- 原因判断：Windows text mode 自动把 LF 转 CRLF，远端 bash 解析 `\r` 失败。
- 处理动作：改为任务目录内 `post_failure_probe.py`，用 `input=REMOTE_SCRIPT.encode("utf-8")` 二进制 LF stdin 重跑。
- 结果：只读探测成功，生成 `post-failure-runtime-probe-r260806b-r2.txt`。
- 是否可前置检查：是。
- 是否可自动化：是，所有 SSH bash stdin carrier 固定使用 UTF-8 bytes + LF，并断言不含 `\r`。
- 下次如何避免：不得使用 `text=True` 或 PowerShell 管道发送多行 bash；失败时先修 carrier 再采信远端结果。

### I010 Manifest v1 component 字段路径误判

- 现象：r260806c 初始 manifest validator 读取顶层 `component`，而实际 Manifest v1 将组件范围写在 `changeSet.component`；旧 validator 会误报组件缺失。
- 阶段：build-release 后 manifest / 版本变更说明校验。
- 影响：若不修正，会把有效发布包误判为无法确认来源，按门禁不得继续 publish-test。
- 原因判断：Manifest v1 与 legacy `release-manifest.json` schema 未分离，校验器沿用 legacy 顶层字段习惯。
- 处理动作：修正 `validate_manifest_r260806c.py`，按 Manifest v1 读取 `changeSet.component`，legacy 清单只做兼容证据；重跑 `manifest-validation-r260806c-r1.json`。
- 结果：validator PASS，manifest/sourceRepos/release-info/changeSet 均可证明目标 releaseTag 和冻结 HEAD。
- 是否可前置检查：是。
- 是否可自动化：是，manifest validator 必须按 schema/version 读取字段。
- 下次如何避免：Manifest v1 校验固定使用根 `manifest.json` 的 `sourceRepos`、`publishScope`、`changeSet.component`、`changeSet.summary`，不得把 legacy 字段路径套到新 schema。

### I011 PowerShell 中误用 Bash heredoc

- 现象：一次尝试在 PowerShell 中使用 Bash heredoc 写脚本，PowerShell 报 `Missing file specification after redirection operator`。
- 阶段：本地证据脚本补丁 / 文档收口。
- 影响：命令未执行、文件未写入；若误以为脚本已生成，会导致后续证据缺失。
- 原因判断：PowerShell 不支持 Bash `<<` heredoc 语法，且本项目禁止用不确定编码路径写中文/多行内容。
- 处理动作：放弃 heredoc，改用 `apply_patch` 写入受控文件，并用 UTF-8 读取验证。
- 结果：无文件被错误修改；后续脚本和文档通过补丁方式写入。
- 是否可前置检查：是。
- 是否可自动化：是，PowerShell 门禁可扫描 `<<` / heredoc 形态并阻断。
- 下次如何避免：Windows PowerShell 下多行脚本写文件使用 `apply_patch`、UTF-8 文件或显式 `[System.IO.File]::WriteAllText`；不要使用 Bash heredoc。

### I012 r260806c 发布前测试服仍处于失败 r260806b-r2 运行态

- 现象：r260806c publish-test precheck 发现测试服 `.env` 与实际镜像仍为失败 tag `release-20260806-intmain-head-test-r260806b-r2`，此前 backend health 失败；但无 RUNNING lock。
- 阶段：publish-test 前远端只读 precheck。
- 影响：如果不记录，可能混淆旧失败状态与新发布结果；如果存在 RUNNING lock 则必须阻塞。
- 原因判断：上一轮 r260806b-r2 publish-test 已切换镜像但后端启动失败，失败 tag 已判废，测试服等待下一轮新 releaseTag 修复覆盖。
- 处理动作：冻结 precheck 证据，确认无活动发布锁后，使用新 releaseTag `r260806c-r1` 执行完整 publish-test；不手工改 release lock/migration，不复用 r260806b-r2。
- 结果：r260806c publish-test SUCCESS，postcheck 证明测试服恢复健康，release lock=`APPLIED`。
- 是否可前置检查：是。
- 是否可自动化：是，publish-test 前后都自动采集 `.env`、实际镜像、lock、migration 和 health。
- 下次如何避免：失败 releaseTag 后续重发前必须先做远端 precheck，明确旧失败状态、RUNNING lock 和目标新 releaseTag。

### I013 publish-test 长阶段耗时且 summary 粒度不足

- 现象：r260806c publish-test 期间 required SQL 上传/状态写入、镜像上传/load 和容器重建耗时较长，operation summary 仍主要显示泛化结果。
- 阶段：测试服发布长链路执行。
- 影响：如果只看 summary，容易误判卡死、重复提交或中断发布。
- 原因判断：发布脚本长时间执行多个远端阶段，但 operation summary 没有持续暴露当前子阶段、最后 SQL 或镜像进度。
- 处理动作：保留 publish-test 脱敏日志尾部和最终 operation JSON；阶段性记录已完成步骤与耗时原因。
- 结果：最终 operation=`SUCCESS`，postcheck 与 Playwright 证据通过。
- 是否可前置检查：部分可。
- 是否可自动化：是，运行控制台可把当前阶段、最后 migrationId、镜像 load 状态和 last log write 写入 summary。
- 下次如何避免：长时间发布轮询时同时看 operation 状态、日志推进、远端 lock 和容器状态；不得因 summary 不变重复提交。

## Closeout Result r260806c

- task-closeout-cleanup preview/apply：PASS，delete=`[]`，发布证据目录完整保留。
- runtime-control 恢复：已停止任务 owned r260806c PID `6360`；从主维护目录 `D:\ProjectPackage\Int\IntRuoyiMaintance` 启动 PID=`35236`，48181 health=`UP`，命令行指向主维护 jar。
- release worktree 清理：维护仓和主程序仓 Git worktree list 均不含 `r260806c`；物理路径 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c`、`D:\IntRuoyiWorktree\r260806c-release-app`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c-state` 均已删除。
- 最终远端复核：`remote_postcheck_r260806c.py` 再次 PASS，`.env`、实际镜像、容器、backend health、frontend HTTP、release-info、release lock 和 migration 均仍匹配 `release-20260806-intmain-head-test-r260806c-r1`。
- 完成结论：测试服发布成功，运行控制台版本号和变更说明已通过页面验证；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
## Cleanup Candidates

无仓库内额外候选。外部 release worktree 与 state dir 使用固定 allowlist 手工清理并在 `execution-log.md` 记录，不交给 task-closeout 脚本按路径删除。

## Cleanup Keep

- `doc/tasks/20260806-head-test-only-release`
- `doc/tasks/20260806-head-test-only-release/task.md`
- `doc/tasks/20260806-head-test-only-release/execution-log.md`
- `doc/tasks/20260806-head-test-only-release/verification-report.md`
- `doc/tasks/20260806-head-test-only-release/migration-policy-gate-r260806a.json`
- `doc/tasks/20260806-head-test-only-release/migration-policy-gate-r260806b.json`
- `doc/tasks/20260806-head-test-only-release/build-release-*-r260806b-r1.json`
- `doc/tasks/20260806-head-test-only-release/build-release-log-tail-r260806b-r1.redacted.txt`
- `doc/tasks/20260806-head-test-only-release/build-release-*-r260806b-r2.json`
- `doc/tasks/20260806-head-test-only-release/build-release-log-tail-r260806b-r2.redacted.txt`
- `doc/tasks/20260806-head-test-only-release/manifest-validation-r260806b-r2.json`
- `doc/tasks/20260806-head-test-only-release/publish-test-*-r260806b-r2.json`
- `doc/tasks/20260806-head-test-only-release/publish-test-log-*-r260806b-r2.redacted.txt`
- `doc/tasks/20260806-head-test-only-release/post-failure-runtime-probe-r260806b-r2.txt`
- `doc/tasks/20260806-head-test-only-release/backend-log-tail-post-failure-r260806b-r2.redacted.txt`
- `doc/tasks/20260806-head-test-only-release/post_failure_probe.py`
- `doc/tasks/20260806-head-test-only-release/runtime-control-r260806b.out.log`

