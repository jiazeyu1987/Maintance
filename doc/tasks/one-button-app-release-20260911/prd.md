# 一键式不可变程序发布工作流 PRD

- Task ID: one-button-app-release-20260911
- Created: 2026-09-11T09:20:03+08:00
- Workspace: D:\ProjectPackage\Int\IntRuoyiMaintance
- User Request: 将程序发布过程固化到受门禁按钮中；标准安装包必须是 without-data，即 PublishScope=app-release，不携带业务数据。

## Current Status

blocked

本文件只定义后续实施契约。本规划阶段不得运行构建、产品测试、NAS 上传、数据库迁移或任何服务器发布。规划文档可完成评审，但 P1 实施在独立 worktree 建立、验证线差异审查和主工作区同路径改动归属确认前保持 `blocked`；测试服真实发布仍需当次明确授权，正式服任何写入仍需当次明确授权。

## Goal

把当前依赖人工拼参数、跨线程记忆和多轮试错的发布过程，改造成持久化、可审计、可恢复的 ReleaseWorkflow 编排流程。操作者只使用三个受门禁按钮：生成程序安装包、发布测试服、晋级正式服。系统负责生成 releaseTag、固定环境参数、创建并冻结独立 release worktree、执行前置门禁、构建一次不可变程序包、原子入库 NAS，并让测试服和正式服消费同一个 package digest。

目标不是假定错误永远不会发生，而是让可预知错误在 Maven、Docker、NAS 大文件上传或真实服务器写入前失败；让剩余失败具有明确的 errorCode、failedStage、证据和可重试条件；任何失败都不得显示为成功。

## 术语

- without-data：用户口语，产品内统一映射为 PublishScope=app-release。UI 不显示 with-data，workflow API 不接受客户端指定发布范围。
- app-release：只交付程序镜像、部署描述、版本化 required SQL、manifest/摘要及验证材料的标准程序安装包。
- required SQL：随程序版本演进所必需的结构或受控增量迁移，是程序升级契约，不是 MySQL 全量业务数据，也不是数据库备份。
- packageDigest：对包内不可变 artifact 清单按本 PRD 的固定算法计算的 SHA-256；不包含 manifest.json、READY/test/prod attestation 或部署后运行态证据，因此不存在摘要自引用。其排序使用规范化 path 的 UTF-8 bytes 无符号字典序。
- manifestDigest：最终 manifest.json 精确 UTF-8 no-BOM、LF 字节的 SHA-256，写入包外 READY attestation；manifest.json 是唯一资格与摘要权威。
- READY：包已在唯一 NAS staging 目录完成上传、禁止项扫描和整包哈希校验，并在同一 NAS 卷内原子改名后进入制品目录 READY 状态。只有 READY 包可部署。
- 环境 preset：后端维护的受控配置，包含环境主机、远端目录、端口、MinIO 容器名、NAS secret 引用和仓库根路径。前端只显示脱敏摘要，不允许操作者手填这些参数。
- test attestation：测试服完整自动验证后，由工作流详情内“记录测试验收”动作生成，绑定 workflowId、releaseTag、packageDigest、manifestDigest、publish-test/SUCCESS、smoke 结果、验收结论和确认人；该动作不是第四个主发布按钮。
- 授权记录：正式服发布所需的一次性、可审计、有时效外部批准引用，精确绑定 workflow、包摘要、生产 preset 与批准范围；点击按钮和输入 PROD 不能替代授权记录。
- 失败前移：在昂贵构建或真实写入之前完成可执行检查并 fail fast。

## Scope

- 在主程序后端 `E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra` 的 runtimecontrol 模块增加持久化 ReleaseWorkflow 编排层、状态机、工作流仓储、阶段证据、错误码、心跳、取消、恢复检查和跨流程环境锁。
- 复用主程序现有 `/admin-api/infra/runtime-control/actions` 底层执行器和维护仓发布脚本，但由编排层生成固定参数；浏览器统一通过主程序 48081 API 访问。
- 普通 UI 不再组织 releaseTag、publishScope、host、NAS 配置、MinIO 容器、repo roots 或 LocalCacheRoot。
- 将标准构建范围固定为 app-release，并同时在构建完成后和每次部署前执行包内容白名单、禁止项和哈希验证。
- 将 Git 源码冻结、CI 测试、迁移策略检查、schema-only 隔离演练、目标只读 preflight、NAS preflight、目标环境 preflight 置于对应写动作之前。
- 将 NAS staging、原子 READY 入库、唯一 package digest、本地缓存隔离或严格 purge、自包含 verifier 纳入制品契约。
- 实现测试服发布、测试证明、正式服晋级守卫和失败后运行态核验。
- 测试服与正式服只能使用同一个 package digest，不能重建或修改包。
- 在主程序 Vue 页面 `E:\IntRuoyi\IntRuoyiFronted\src\views\infra\runtime-control\index.vue` 增加三步发布工作台和工作流详情，API 封装归属 `src\api\infra\runtimeControl\index.ts`。
- 数据备份/恢复继续作为完全独立的运维流程。
- 增加后端、脚本、前端和真实浏览器测试，并建立 R31-R44 防复发回归矩阵。
- 更新发布操作说明、错误码说明、恢复/重试规则和证据目录规范。

## Non-Goals

- 本规划阶段不构建、不上传、不部署 R44，也不修改测试服、正式服、审查服、NAS 或数据库。
- 不把 MySQL 全量 dump、MinIO 数据、DCC 对象清单或 runtime data 放入程序安装包。
- 不把数据备份、数据恢复、灾难恢复与程序发布合并为一个按钮或一个 workflow。
- 不自动发布正式服。
- 不用“测试服健康”替代测试证明、同制品校验、正式授权和 PROD 二次确认。
- 不在当前脏的 int_main 工作树中实施，不覆盖 frontend/ 的未提交删除或其他任务修改。
- 不借本任务重写所有备份/恢复、巡检、告警或业务健康功能。
- 不改变 IntRuoyi 业务功能。
- 不以 mock 成功、跳过测试、吞异常、缓存命中或脚本 guard 提前 return 作为发布成功。
- 不承诺未经授权的正式服真实 E2E；正式服验收只验证守卫、预览、参数契约和无写入事实。

## Preconditions

- 后续执行前必须新建本任务独立 worktree，并按 E:\IntRuoyi\docs\worktree-memory.md 记录路径、基线、提交、融合和删除证据。
- 当前维护仓基线为 int_main@eaaa47ac320dd197dba646d6870fed0cb7d2534c。
- 已验证维护提交 8080c0d3c7076d2305d945dea26bf1a22ceaf026 支持 app-release 和 NAS cache /PURGE，但不在当前基线祖先链；P1 必须显式审查并融合所需变更。
- 应用提交 713c64112d7b626a2ba71788fd36cc32d686addc 含 active username 迁移修复；后续选源必须验证该修复或等价提交进入批准源。
- 当前主工作树有未提交修改，且 frontend/ 为未提交删除状态；实施不得 reset、checkout 或覆盖这些改动。
- 必须具备 Java 17、Maven、Node.js、Corepack/pnpm、Python UTF-8、Git、Docker、PowerShell 5.1 和项目规定的 Playwright 1.60.0。当前只读核验发现权威路径 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 缺少 `package.json`、`node_modules\playwright` 和 `.bin\playwright.cmd`；P4/P5 在该依赖按项目规则恢复前阻塞，禁止临时安装或切换版本兜底。
- 环境 preset 必须完整且通过启动校验。
- 秘密只能通过受控 secret 引用解析；文档、请求、响应、命令预览和日志不得出现密码、token、私钥或完整连接串。
- NAS preset 必须在 Maven 前通过 schema、连通性、同目录 staging 临时可写、原子改名能力、releaseTag 未占用和空间检查。
- 测试服真实发布前必须重新取得用户明确授权。
- 正式服写入必须另行取得当次明确授权和有效授权记录。
- Playwright 浏览器验收必须从 `http://localhost:8081` 登录测试租户 `aoteman`，进入 `/infra/monitors/runtime-control`，通过主程序 48081 API 完成真实用户路径；写入只允许测试租户，API 只作页面路径完成后的最终校验。通过用例把截图和 trace 保存到任务目录之外的 `output/playwright/one-button-app-release-20260911/`。
- 任一前置缺失时停止并写入 task-state.json.blocking_prereqs；不得切换到其他主机、目录、数据源或发布范围。

## 当前基线

- 正式产品入口是主程序 `http://localhost:8081/infra/monitors/runtime-control`；页面位于 `E:\IntRuoyi\IntRuoyiFronted\src\views\infra\runtime-control\index.vue`，请求封装位于 `src\api\infra\runtimeControl\index.ts`，后端 API 端口为 48081。
- 主程序后端 `E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\controller\admin\runtimecontrol\RuntimeControlController.java` 已提供 `/actions` preview/execute、operations/logs、release-packages 和 release-status；service/runtimecontrol 下已有 build、publish、mark、promote 底层动作。
- 维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 持有发布脚本、包治理与独立诊断/契约同步实现；其 `frontend/` 和 standalone 48181 不是最终产品入口，也不得作为真实 E2E 用户界面 PASS 依据。
- 当前主分支发布范围仍是 code-only/with-data 契约，尚未统一为 app-release。
- RuntimeControlOperationStore 只记录单个操作的 RUNNING/SUCCESS/FAILED。
- 当前缺少跨操作 workflow、全局环境锁、可靠心跳/超时、取消、进程重启恢复和阶段级证据。
- 当前前端直接暴露动作、releaseTag 和发布范围，包含 with-data 选择。
- 本规划启动时 R44 app-release 包已构建并上传但尚未部署；规划期间另一个发布线程随后完成 R44 测试服部署与运行态/页面验证。该外部结果不属于本规划任务执行动作。
- R44 当前只证明旧链路可完成测试服发布，未执行 `mark-tested` 或任何正式/备份/审查服晋级；新 workflow 不得把旧 operation 自动导入为 READY、TESTED 或正式授权。
- R44 的“线程中断后人工恢复”仍作为持久化 workflow 回归来源：新流程在纯 READY 状态重启后必须保持 READY 并等待明确的发布测试服动作，不自动部署或生成 TESTED attestation。

## Impacted Areas

- 主程序后端仓：`E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\controller\admin\runtimecontrol\`、`service\runtimecontrol\`、`framework\runtimecontrol\config\`，以及对应测试和新增 workflow domain/service/store/lock/preset 类。
- 主程序前端仓：`E:\IntRuoyi\IntRuoyiFronted\src\views\infra\runtime-control\index.vue`、其 runtime-control 组件、`src\api\infra\runtimeControl\index.ts` 和对应测试。
- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1`、`ops\release\`、`scripts\tests\`、包治理、迁移策略、target preflight 和自包含 verifier；维护仓 frontend/standalone 不承担最终产品 UI。
- 配置：主程序后端 runtime-control 配置与维护仓不含秘密值的 preset 示例；维护仓和 IntRuoyi 根仓两个 Git root/版本及 maintenance/backend/frontend 三个 source role 必须显式进入冻结证据。
- 测试：主程序后端 JUnit、主程序前端类型/组件测试、维护仓脚本回归、固定摘要向量和主程序真实 Playwright E2E。
- 文档：任务执行记录、验证报告、发布运行手册、错误码/重试表、环境与 secret owner 清单。
- 下游：NAS 制品库、测试服/正式服 Docker Compose 运行态、migration ledger、release-info、发布锁和审计记录。

## 经验门禁

- Trigger: 生成程序安装包。Preflight check: 源提交存在、release worktree clean/frozen、migration metadata 与目录 allowlist、CI 测试、schema-only 同镜像演练、非 schema/历史数据约束的 target readonly preflight、NAS schema/连通/临时写/原子改名/tag 未占用、规范化 LocalCacheRoot。Blocker: 任一失败。Verification: 阶段证据均为 PASS。Forbidden action: 开始 Maven/Docker/NAS 正式目录写入。Evidence: workflow stage evidence。
- Trigger: 包构建完成或准备部署。Preflight check: 按固定排序向量重算 packageDigest 与 manifestDigest，反向拒绝 ruoyi-vue-pro-current.sql、reset-db.sql、post-import.sql、minio/**、manifest/dcc-object-inventory.json、MySQL dump、runtime data、.env 和秘密。Blocker: 非白名单、非法/冲突路径、跨实现向量不一致、缺文件、哈希漂移或秘密命中。Verification: package governance report。Forbidden action: 使用 release-manifest.json 代替 manifest.json 判定资格、标记 READY 或连接目标写入。Evidence: 包外 READY attestation 与扫描报告。
- Trigger: 发布测试服或正式服。Preflight check: READY、同 digest、环境 preset、Docker/磁盘/容器/端口/秘密存在性、目标只读 migration preflight、环境锁。Blocker: 锁冲突、FAILED/RUNNING migration、旧 staging、目标漂移。Verification: deploy preflight evidence。Forbidden action: 仅凭本地缓存或线程内标志继续。
- Trigger: 切换远端版本。Preflight check: 写 .env.next、校验后原子替换 .env，保留旧值用于本次失败恢复。Blocker: 非原子切换或旧值不可验证。Verification: 切换前后哈希、actual image tag。Forbidden action: 先覆盖 .env 再尝试启动。
- Trigger: 声明发布成功。Preflight check: operation=SUCCESS、manifest/digest、远端 .env IMAGE_TAG、backend/frontend actual image tag、两容器 running、backend health=UP、frontend HTTP 200、release-info/lock/migration 无 FAILED/RUNNING。Blocker: 任一缺失。Verification: final attestation。Forbidden action: 只看 HTTP 200、命令退出码或旧容器存活即判绿。
- Trigger: 晋级正式服。Preflight check: 同一 workflow 的 app-release tag/packageDigest/manifestDigest、测试发布 SUCCESS、TESTED attestation、与 workflow/摘要/prod/preset/scope 精确绑定且未撤销未消费的一次性授权、输入 PROD。Blocker: promotion attestation 只允许 code-only、包被重建/修改、授权 tuple 不一致/过期/撤销/已消费或 nonce 重放。Verification: promotion preview、双摘要 compare 与原子 consumedAt 审计。Forbidden action: 自动晋级、重新构建、清空 consumedAt 或复用授权。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。所有失败均进入明确失败或恢复待处理状态。
- 是否从根因和长期维护角度解决：是。使用持久化 workflow、固定 preset、不可变制品、分阶段门禁和真实运行态证明。
- 是否存在临时补丁或绕过：否。R44 不作为特例，8080c0d 必须正式融合后才能成为基线。

## 目标流程

批准的已提交源码
→ 生成程序安装包
→ 创建并冻结独立 release worktree
→ 源码、迁移、NAS、目标只读前置门禁
→ CI 测试，禁止只跑 -DskipTests
→ schema-only 同镜像隔离演练
→ Maven、前端、Docker 构建一次
→ 构建后白名单、禁止项、秘密和哈希检查
→ NAS 唯一 staging 上传、复算哈希、同卷原子改名
→ READY(app-release, packageDigest)
→ 发布测试服，仍使用该 digest
→ 测试服运行态与 smoke 完整证明
→ TEST_DEPLOYED
→ 在工作流详情记录测试验收并生成 TESTED attestation
→ TESTED，等待与该 workflow/digest/preset 精确绑定的正式授权
→ PROD 二次确认
→ 晋级正式服，仍使用该 digest，禁止重建
→ 正式服运行态证明或明确失败/恢复待处理

数据备份和恢复不在该链中，使用独立入口、状态、授权和证据。

## 状态机与重试规则

稳定主链为 `CREATED → SOURCE_FREEZING → PREFLIGHTING → TESTING → BUILDING → VERIFYING_PACKAGE → PUBLISHING_ARTIFACT → READY → DEPLOYING_TEST → VERIFYING_TEST → TEST_DEPLOYED → TESTED → DEPLOYING_PROD → VERIFYING_PROD → COMPLETED`。`TESTED` 已明确表示测试验收记录完成并等待正式授权，不再设置含义重叠的 AWAITING_PROD_AUTHORIZATION。

| Current state | Event | Guard | Next state | Lock | Side effect |
| --- | --- | --- | --- | --- | --- |
| CREATED | 接受生成包意图 | 参数合同有效且 `build:app-release` 可取得 | SOURCE_FREEZING | 取得 build 租约 | 固定 workflowId/tag/preset；开始后任一失败均退休 tag |
| CREATED | 参数或 build 锁拒绝 | workflow 已创建但启动门禁失败 | FAILED | 无或释放 build 租约 | 记录 errorCode；退休 tag；不启动源码/构建动作 |
| SOURCE_FREEZING | 发布来源冻结成功 | 维护仓 worktree 与 IntRuoyi 根仓 app worktree 均为批准提交且 clean；app worktree 内后端/前端两个 source role 可追溯 | PREFLIGHTING | 保持 build 租约 | 创建两个冻结 worktree，记录两个 Git root 及 maintenance/backend/frontend 三个 source role 的 path/commit/dirty=false |
| SOURCE_FREEZING | 冻结失败或取消完成 | 任一仓缺失、dirty、提交漂移或取消 | FAILED 或 CANCELED | 释放 build 租约 | 清理任务自有 worktree；退休 tag |
| PREFLIGHTING | 所有前置门禁通过 | 迁移、目标只读、NAS、Docker、磁盘、端口、secret 均 PASS | TESTING | 保持 build 租约 | 固定 preflight fingerprint 与证据 |
| PREFLIGHTING | 任一门禁失败 | fail-fast | FAILED | 释放 build 租约 | 记录 failedStage；退休 tag；Maven/Docker/NAS 正式写入不得开始 |
| TESTING | 显式测试通过 | 后端、前端、脚本测试均完成 | BUILDING | 保持 build 租约 | 固定测试报告摘要 |
| TESTING | 测试失败、跳过或取消 | 任何 required test 非 PASS | FAILED 或 CANCELED | 释放 build 租约 | 退休 tag；不进入 Maven skipTests/Docker 构建 |
| BUILDING | 构建成功且二次冻结一致 | 两个 Git worktree 的 HEAD/dirty 与冻结证据相同，三个 source role 仍指向已批准路径 | VERIFYING_PACKAGE | 保持 build 租约 | 固定 artifact 原始字节摘要；禁止修改冻结输入 |
| BUILDING | 构建失败、冻结漂移或取消 | 任一构建/二次冻结非 PASS | FAILED 或 CANCELED | 释放 build 租约 | 删除任务自有临时产物；永久退休 tag |
| VERIFYING_PACKAGE | 白名单与双摘要通过 | packageDigest/manifestDigest 固定向量一致且无禁止项 | PUBLISHING_ARTIFACT | 保持 build 租约 | 写最终 manifest.json；生成包外 READY 候选证明 |
| VERIFYING_PACKAGE | 验包失败 | 非白名单、路径非法、摘要漂移或秘密命中 | FAILED | 释放 build 租约 | 隔离制品；永久退休 tag |
| PUBLISHING_ARTIFACT | NAS 原子入库成功 | 唯一 staging 全哈希通过且同卷原子改名 | READY | 释放 build 租约 | 写包外 READY attestation；制品变为只读可部署 |
| PUBLISHING_ARTIFACT | 上传、哈希或原子切换失败 | READY 尚未成立 | FAILED | 释放 build 租约 | 隔离/精确清理 staging；永久退休 tag |
| READY | 测试发布参数、preview 或部署前 preflight 拒绝 | operationId 未创建、`env:test` 未取得且目标零写入 | READY | 不持锁 | 记录可见拒绝原因；允许原 workflow 重新检查 |
| READY | 测试部署初始化成功 | 所有 guard PASS，CAS 取得 `env:test` 并持久化 operationId | DEPLOYING_TEST | 保持 test 租约 | 开始后任一确定失败均退休 tag |
| READY | 取得 test 锁或创建 operation 后初始化失败 | 锁曾取得或 operationId 已存在 | FAILED | 核验后释放/封锁 test 租约 | 记录零写入与否；永久退休 tag，不回 READY |
| DEPLOYING_TEST | 命令成功 | 同一 READY packageDigest/manifestDigest | VERIFYING_TEST | 保持 test 租约 | 执行 .env.next 事务并收集 actual runtime |
| DEPLOYING_TEST 或 VERIFYING_TEST | 确定失败 | operation 已创建、锁已取得或发生目标写入 | FAILED | 完成恢复核验后释放 test 租约 | 恢复旧 env 并核旧镜像；永久退休 tag |
| DEPLOYING_TEST 或 VERIFYING_TEST | 心跳超时、重启或状态不明 | 无法证明终态 | RECOVERY_REQUIRED | test 租约隔离，不自动接管 | 禁止重试/晋级，启动只读恢复审计 |
| RECOVERY_REQUIRED | 恢复审计证明零写入 | 同时证明未取得有效锁、无 operation 效果、目标/摘要未变 | READY | 释放隔离租约 | 记录审计签名后仅允许重新做部署前门禁 |
| RECOVERY_REQUIRED | 发现操作、锁、写入或无法证明零写入 | 任一证据存在或证据不完整 | FAILED | 核验后释放或人工封锁 | 永久退休 tag；已消费授权不得复用 |
| VERIFYING_TEST | 完整运行态验证通过 | 全部成功条件 PASS，锁/migration 无 FAILED/RUNNING | TEST_DEPLOYED | 释放 test 租约 | 固定自动测试证据；尚未生成 TESTED attestation |
| TEST_DEPLOYED | 验收表单参数无效 | 结论/证据缺失或摘要不匹配 | TEST_DEPLOYED | 无环境锁 | 显示错误；不生成 attestation |
| TEST_DEPLOYED | 工作流详情记录测试验收通过 | 人工结论 PASS 且绑定同 workflow/tag/packageDigest/manifestDigest | TESTED | workflow CAS | 原子写 test attestation；该详情动作不是主发布按钮 |
| TEST_DEPLOYED | 测试验收不通过 | 人工结论 FAIL | FAILED | workflow CAS | 记录缺陷并退休 tag；禁止正式晋级 |
| TESTED | 正式 preview、参数、授权或 preflight 拒绝 | prod 锁/operation 未创建，授权未消费且正式服零写入 | TESTED | 不持 prod 锁 | 保留只读拒绝证据；可更换有效授权后重试 preview |
| TESTED | 正式部署初始化成功 | 同 digest/preset、权限、开关、授权、PROD 全部 PASS | DEPLOYING_PROD | CAS 取得 prod 租约 | 原子消费授权、持久化 operationId，然后才允许目标写入 |
| TESTED | 取得 prod 锁、消费授权或创建 operation 后失败 | 任一不可逆初始化已发生 | FAILED | 核验后释放/封锁 prod 租约 | 永久退休 tag；授权保持已消费，禁止复用 |
| DEPLOYING_PROD | 命令成功 | 只消费已测试的 NAS READY 同一双摘要包 | VERIFYING_PROD | 保持 prod 租约 | 收集正式运行态，不执行任何 rebuild |
| DEPLOYING_PROD 或 VERIFYING_PROD | 确定失败 | operation/锁/写入已发生 | FAILED | 完成恢复核验后释放 prod 租约 | 恢复旧 env 并核旧镜像；退休 tag，不自动重试 |
| DEPLOYING_PROD 或 VERIFYING_PROD | 心跳超时、重启或状态不明 | 无法证明终态 | RECOVERY_REQUIRED | prod 租约隔离 | 不自动继续；授权保持已消费；执行只读恢复审计 |
| VERIFYING_PROD | 完整运行态验证通过 | 全部成功条件、审计和双摘要一致 | COMPLETED | 释放 prod 租约 | 固定正式 attestation 与最终审计 |
| 任一写阶段 | 收到取消请求 | 不能证明子进程和目标写入已安全终止 | RECOVERY_REQUIRED | 原租约隔离 | 协作式取消；不得直接标记 CANCELED |
| FAILED、CANCELED 或 COMPLETED | 再次执行主动作 | 终态不可变 | 原状态 | 无 | 拒绝；需要发布时新建 workflow 与新 tag |

- 每次转换使用 stateVersion/CAS 并持久化 stageAttempt、startedAt、heartbeatAt、completedAt、errorCode、failedStage、脱敏摘要和证据引用。
- 生成包链任一冻结、preflight、测试、构建、验包或 NAS 失败都永久退休 releaseTag；修复后必须创建新 workflow 和新 tag。
- 只有 READY/TESTED 上且发生在 operationId 创建、环境锁取得、授权消费和目标写入之前的参数、preview 或部署前 preflight 拒绝，才能保留原状态重试。
- operationId 已创建、环境锁已取得或目标写入已发生后的确定失败一律进入 FAILED 并退休 tag；不得用“远端似乎没变”复用。
- 状态不明必须先进入 RECOVERY_REQUIRED。只有签名恢复审计同时证明没有有效 operation 效果、没有遗留锁、没有目标写入且双摘要未变，才可保守退回 READY 并重新走测试发布；否则进入 FAILED。该恢复审计是未知状态收敛规则，不是失败 tag fallback。
- 迁移、程序内容或 manifest 需要修改时必须新包新 tag。线程缓存、进程内布尔量或脚本 guard return 不能充当锁或成功证据。

## 包内容白名单与禁止清单

标准 app-release 包只允许：

- 后端、前端程序 Docker 镜像归档及其 SHA-256。
- docker-compose.yml 和 manifest 明确列出的非秘密部署描述。
- required-sql/ 下版本化 required SQL、迁移 metadata 和目标只读 preflight。
- 唯一权威 manifest.json、每文件摘要、源码提交、dirty=false 证明、工具版本和包类型 app-release。P1 必须把全部消费者迁移到该文件后删除双 manifest 契约。
- manifest/ 下迁移策略、schema-only 演练、依赖与构建验证证据。
- smoke/ 下自包含、版本化、已哈希的 verifier、smoke 定义和构建时 smoke 证据。
- manifest 明确列出的非秘密静态资源。

构建后和部署前均反向拒绝：

- ruoyi-vue-pro-current.sql、reset-db.sql、post-import.sql，无论位于何处。
- minio/**、任何 MinIO 快照、对象导出或同步清单。
- manifest/dcc-object-inventory.json 及任何 DCC object inventory。
- MySQL 全量 dump、数据库数据目录、Redis dump、runtime data、上传文件、业务导出或恢复点。
- .env、.env.*、密码、token、私钥、连接串、NAS 凭据或其他秘密。
- release-manifest.json 或其他第二份资格清单；新 workflow 不接受兼容投影、双权威或临时读取分支。
- 未列入 manifest 的文件、绝对路径、父目录跳转、外部软链接和构建临时文件。

路径比较必须大小写归一化并防止目录穿越。部署后环境 smoke/运行态证据存放在 workflow evidence 中并绑定 digest，不回写不可变包。

### 双摘要算法合同

- `manifest.json` 是包资格、artifact 列表、来源、范围和摘要的唯一权威；P1 同步迁移所有构建、NAS、部署、测试证明和晋级消费者，新 workflow 禁止生成或读取 `release-manifest.json`。
- 每个 immutable artifact 先对文件原始 bytes 计算 SHA-256，小写十六进制表示；`bytes` 是原始文件字节数的无符号十进制表示。
- packageDigest 输入包含全部 immutable artifact，但明确排除 manifest.json、包外 READY attestation、test/prod attestation 和部署后运行态证据；不存在第二份 manifest 或兼容投影。
- 每个 artifact path 必须是以 `/` 分隔的规范化相对路径；拒绝反斜杠、绝对路径、空段、`.`、`..`、控制字符、外部链接及大小写折叠后冲突。
- 将规范化 path 编码为 UTF-8 bytes，并按无符号字节字典序排序；每项编码为 `path<TAB>bytes<TAB>sha256-lowercase<LF>`，拼接后按 UTF-8 no-BOM 字节计算 SHA-256，结果即 packageDigest。禁止使用语言或区域相关字符串排序。
- 最终 manifest.json 以 UTF-8 no-BOM、LF 固化后，对其精确 bytes 计算 SHA-256，结果即 manifestDigest；manifestDigest 只写入包外 READY attestation，不回写 manifest.json。
- Java、Python、PowerShell 三个实现必须对同一固定向量输出完全相同的每文件 SHA-256、排序输入 bytes、packageDigest 和 manifestDigest；任一差异阻断 READY。

## API 与数据模型

新增 workflow API，客户端请求只表达业务意图：

- POST /admin-api/infra/runtime-control/release-workflows：请求 reason 和受控 sourceSelectionId；后端生成 workflowId/releaseTag 并固定 app-release。
- GET /admin-api/infra/runtime-control/release-workflows：分页查询。
- GET /admin-api/infra/runtime-control/release-workflows/{workflowId}：返回状态、阶段、digest、可用动作、失败原因和脱敏证据。
- GET /admin-api/infra/runtime-control/release-workflows/{workflowId}/events：返回有序转换和心跳摘要。
- POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/publish-test：只消费 READY 包，请求仅含 reason。
- POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/test-attestation：仅在 TEST_DEPLOYED 状态记录验收结论和证据引用；入口位于工作流详情内，不是第四个主发布按钮。
- POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/promote-prod/preview：只读验证同制品、测试证明和授权。
- POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/promote-prod：请求 reason、authorizationGrantId、prodConfirmText=PROD。
- POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/cancel：写取消请求，不伪造终止。
- POST /admin-api/infra/runtime-control/release-workflows/{workflowId}/retry：只重新检查 READY/TESTED 的前操作门禁；FAILED/CANCELED/COMPLETED 不接受原 tag 重试。

持久化模型：

- ReleaseWorkflowRecord：workflowId、releaseTag、维护仓与 IntRuoyi 根仓两个 Git source root/commit/dirty，以及 maintenance/backend/frontend 三个 path role、publishScope、packageDigest、manifestDigest、state、stateVersion、failedStage、errorCode、retryable、createdBy、timestamps。
- ReleaseStageAttempt：stage、attempt、operationId、leaseId、heartbeat、exit/result、error summary。
- ReleaseEvidenceRef：type、path、sha256、createdAt、environment、packageDigest。
- ReleaseArtifactRef：NAS 相对路径、packageDigest、manifestDigest、READY 时间、文件数、总字节数。
- ReleaseAttestation：测试环境、同一 workflowId/tag/packageDigest/manifestDigest、publish operation、smoke checks、test conclusion、testedBy、testedAt。
- ReleaseAuthorizationRef：authorizationGrantId、workflowId、releaseTag、packageDigest、manifestDigest、targetEnvironment=prod、presetId、presetVersion、approvedScope、approver、issuedAt、validUntil、nonce、revokedAt、consumedAt；不存秘密值。
- ReleaseLease：resourceKey、ownerWorkflowId、stage、acquiredAt、heartbeatAt、expiresAt、recoveryState。

首版在 state-dir/release-workflows/ 使用原子临时文件加同卷替换持久化 JSON，并维护 append-only event journal。写入失败必须让阶段失败。底层 /actions 继续执行命令，但面向 UI 的发布必须经过 workflow；标准流程中的 with-data build 必须拒绝，数据备份/恢复继续使用独立受控流程。

正式 preview 必须逐字段核验 ReleaseAuthorizationRef 与当前 workflow、双摘要、prod 目标和 preset 版本完全一致，且当前时间位于有效期内、revokedAt/consumedAt 为空、nonce 未使用。execute 在取得 prod 锁并创建 operation 的同一 CAS 决策中写 consumedAt；重复消费、跨 workflow、跨环境、跨 tag/digest/manifestDigest、跨 preset 或扩大 approvedScope 均 fail fast 且零目标写入。preview 不消费授权；执行失败也不得清空 consumedAt 或复用 nonce。

## UI 交互

- 产品页面固定为主程序 `http://localhost:8081/infra/monitors/runtime-control`，实现归属 IntRuoyiFronted 的 runtime-control 页面；维护仓 frontend/standalone 不作为交付入口。
- 页面采用安静、紧凑的运维控制台布局，遵循 FRONTEND_STYLE.md。
- 使用连续工具栏、阶段时间线、固定列宽表格和短状态标签。
- 标准发布只显示生成程序安装包、发布测试服、晋级正式服三个主路径按钮。
- 明确显示“程序包（不含数据）”，不存在 with-data 选项。
- 不显示 host、NAS 配置、MinIO 容器、repo roots、LocalCacheRoot 或手填 releaseTag。
- 生成按钮显示来源提交只读摘要、固定包类型、预计阶段和操作原因。
- 提交后立即禁用重复点击。
- 测试按钮只在 READY 且 test 未锁定时可用，并显示 tag、digest、包类型和来源。
- TEST_DEPLOYED 后在工作流详情内显示“记录测试验收”表单动作；它只生成 TESTED attestation，不进入三个主发布按钮工具栏。
- 正式按钮只在 TESTED、digest 未漂移且授权有效时可用。
- 正式确认完整显示环境、tag、digest、测试证明和回滚候选，要求输入 PROD。
- 先决条件缺失必须显示禁用原因，不得隐藏。
- 详情显示阶段、耗时、最近心跳、errorCode、failedStage、证据、实际版本和 retry policy。
- API 错误必须可见，不得空 catch。
- 刷新或重开页面后从持久化 workflow 恢复状态。
- 真实 E2E 必须登录测试租户 `aoteman` 后从该页面操作；写入只允许测试租户，浏览器完成用户步骤后才可使用 48081 API 作最终一致性校验。
- 状态不只靠颜色；按钮有可访问名称；长 digest 可复制且不挤压布局；桌面和窄屏无重叠。
- 不使用营销 hero、渐变、装饰卡片或嵌套卡片。

## 权限、秘密与审计

- 三个 workflow 动作使用独立权限：构建、测试发布、正式晋级。
- 正式晋级还要求 production write feature flag、精确绑定且未撤销/未消费的一次性授权记录和 PROD。
- /actions 发布执行器不再作为普通 UI 的直接入口。
- 服务端验证 workflow 身份与阶段，防止绕过状态机。
- preset 只返回名称、版本和脱敏状态。
- 秘密在执行瞬间由后端解析；请求、响应、预览、operation parameters、日志和异常统一脱敏。
- 审计记录操作者、原因、两个 Git 根及三个 source role、tag、packageDigest、manifestDigest、preset 版本、授权引用/nonce/消费时间、状态转换、operationId、退出状态和验证结果。
- 授权 tuple 任一不一致、授权过期/撤销/已消费或 nonce 重放均阻断；授权校验、CAS 消费和 operation 初始化必须可审计且不能跨 workflow、环境、摘要或 preset 复用。
- 权限不足、授权过期、确认错误、preset/secret 缺失均 fail fast，且不得产生服务器写入。

## R31-R44 防复发矩阵

| 版本 | 已知失败原因 | 前移门禁/设计 | 阻断阶段 |
| --- | --- | --- | --- |
| R31 | required migration 缺 target readonly preflight | 从发布计划自动推导需要 preflight 的迁移并验证完整性 | PREFLIGHTING，Maven 前 |
| R32 | target-preflight 被错误扫描为 release migration | 目录和文件类型 allowlist 双向分类 | PREFLIGHTING，Maven 前 |
| R33 | role scope 迁移缺 preflight 文件 | 自动推导的引用存在性和摘要验证 | PREFLIGHTING，Maven 前 |
| R34 | 重复 DROP CHECK 导致非幂等失败 | 标识符、约束存在性、幂等性检查和二次演练 | PREFLIGHTING，Maven 前 |
| R35 | ledger 已应用但真实 schema 缺字段 | schema/ledger 一致性只读检查，不只信 ledger | PREFLIGHTING，Maven 前 |
| R36 | MySQL 默认 socket 与容器连接不一致 | 演练显式 TCP host/port，禁止隐式 socket | PREFLIGHTING，Maven 前 |
| R37 | release worktree 有未提交迁移 | 后端创建 clean detached worktree 并二次冻结校验 | SOURCE_FREEZING |
| R38 | type=schema 混入历史业务数据依赖 | schema 类型纯度；数据约束强制 target preflight | PREFLIGHTING，Maven 前 |
| R39 | procedure 多语句 SQL 缺 DELIMITER | delimiter/statement parser 门禁 | PREFLIGHTING，Maven 前 |
| R40 | 本地包完成但 NAS 无对应包 | Maven 前 NAS 预检；上传后原子 READY；部署只列 READY | PREFLIGHTING/PUBLISHING_ARTIFACT |
| R41 | LocalCacheRoot 拼出双层目录 | 规范化显式父目录；拒绝尾部 publish-int-ruoyi | PREFLIGHTING，Maven 前 |
| R42 | cache 遗留旧 .env 污染新包 | 唯一 staging 或严格 /PURGE；两次禁止项扫描 | VERIFYING_PACKAGE |
| R43 | MinIO/repo roots 手填错误、删除用户唯一约束遇历史数据冲突、失败后 .env 漂移 | preset 固化完整 MinIO/repo roots、相关迁移 requiresTargetPreflight、.env.next 原子切换和 actual image 核验 | PREFLIGHTING/VERIFYING_TEST |
| R44 | 包构建上传后线程中断，后由另一发布线程人工恢复并完成测试服验证 | 持久化 workflow 在重启后保持 READY，禁止自动部署/TESTED；后续明确动作与结果均可恢复追踪 | READY/后续阶段可审计 |

## Milestones / Expected Verification

| Milestone | Outcome | Expected Verification |
| --- | --- | --- |
| P1 | 基线与发布契约收敛 | Git/worktree 记录、app-release/参数/迁移/CI 合同测试 |
| P2 | ReleaseWorkflow 后端、状态、锁与可靠超时 | 后端状态机、并发、心跳、取消、重启恢复和脱敏测试 |
| P3 | 自包含 app-release 构建、NAS READY 与部署事务 | 脚本、包治理、迁移演练、同制品测试/正式守卫；获授权后才真实发布测试服 |
| P4 | 三按钮运维 UI | Vue 测试、typecheck/build、Playwright 桌面与窄屏证据 |
| P5 | R31-R44 回归、独立验收与收口 | 全量回归、blind-first-pass、真实测试服证据或授权 blocker、融合/清理证据 |

## Phase Plan

### P1: 基线与契约收敛

- Objective: 在维护仓独立 worktree 与 `E:\IntRuoyi` 根仓独立 app worktree 中审查并融合维护提交 8080c0d 与应用提交 713c641/等价修复，把标准发布范围、双摘要、三个 source role、preset 和测试顺序固化成唯一合同。
- Owned paths: 两个 Git 仓的发布 scope/manifest/preset/来源合同、后端/前端 path role、对应测试和任务实施记录。
- Dependencies: P1 从明确提交创建两个独立 worktree，不触碰主工作区；IntRuoyiBackend 与 IntRuoyiFronted 同属 `E:\IntRuoyi` 根 Git 仓并位于同一个 app worktree。最终融合前才必须确认同路径 dirty 改动及维护仓 frontend/ 删除的归属，无法无损融合即阻塞。8080c0d 与 713c641/等价实现的精确差异必须先审查。
- Deliverables: app-release 唯一标准、参数所有权、数据流程边界、clean/frozen source 与 CI gate 合同。

### P2: ReleaseWorkflow 编排内核

- Objective: 在主程序 IntRuoyiBackend 的 yudao-module-infra runtimecontrol 模块建立可持久化、可并发保护、可靠超时且可在重启后恢复判断的产品 ReleaseWorkflow 编排层。
- Owned paths: `E:\IntRuoyi\IntRuoyiBackend\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\controller\admin\runtimecontrol\`、`service\runtimecontrol\`、`framework\runtimecontrol\config\` 及对应测试；维护仓 backend 仅在保留时承担独立诊断和合同同步，不得成为产品 workflow 的唯一实现。
- Dependencies: P1 合同稳定；Java/Maven 可用。
- Deliverables: workflow domain/store/service/lease、状态转换、CAS、心跳/超时、恢复/取消/重试、preset 校验、底层 /actions 边界、脱敏审计。

### P3: 自包含制品与部署事务

- Objective: 从批准提交生成唯一 tag 和 clean/frozen worktree，在昂贵构建前完成门禁，原子入库 app-release READY 包，并以同一 digest 完成测试发布和受守卫的正式晋级。
- Owned paths: ops/deploy/**、ops/release/**、scripts/tests/**、workflow build/deploy/promotion orchestration。
- Dependencies: P2；NAS 与测试 preset 可验证；真实测试服步骤另需当次明确授权。
- Deliverables: preflight DAG、显式测试 gate、迁移演练、目标只读 preflight、包治理、自包含 verifier、NAS READY、.env.next 事务、完整 attestation、app-release 晋级守卫。

### P4: 三按钮发布工作台

- Objective: 在主程序 `/infra/monitors/runtime-control` 提供不暴露基础设施参数的三步 UI，显示阶段、失败证据、重试条件、测试验收动作和正式风险。
- Owned paths: `E:\IntRuoyi\IntRuoyiFronted\src\views\infra\runtime-control\`、`src\api\infra\runtimeControl\index.ts`、主程序后端 workflow controller/DTO/API、前后端测试和 Playwright。
- Dependencies: P1-P3 API 在主程序 48081 稳定；维护仓 frontend/standalone 已从产品验收面排除。
- Deliverables: 生成程序安装包、发布测试服、晋级正式服三个按钮，工作流详情、权限/禁用态、错误反馈、响应式与无障碍。

### P5: 防复发回归、独立验收与收口

- Objective: 将 R31-R44 和双摘要/授权重放固化为自动回归，通过主程序 8081 页面完成独立真实浏览器验收、运行手册、融合和清理。
- Owned paths: 本任务测试、运行手册、错误码/恢复表、任务证据。
- Dependencies: P1-P4 完成；独立 tester 可用；测试租户 `aoteman` 可登录；任何测试服写入已有明确授权，正式服保持只读。
- Deliverables: 回归套件、blind-first-pass 报告、任务目录外浏览器证据、真实测试服结论或授权 blocker、集成提交和 worktree 清理记录。

## Phase Acceptance Criteria

### P1

- P1-AC1: 维护仓与 IntRuoyi 根仓分别使用任务独立 worktree，后者同时承载 IntRuoyiBackend/IntRuoyiFronted；差异审查证明维护提交 8080c0d 的 app-release/PURGE 能力和应用提交 713c641 的 active username 修复或等价实现已正式融合；最终融合前确认两个主工作区同路径 dirty 改动及维护仓 frontend/ 删除的归属，无法无损融合即阻塞且不覆盖用户改动。
- P1-AC2: 标准 build contract 固定 PublishScope=app-release；UI/API 不接受 with-data，也不把备份/恢复纳入发布 workflow；所有消费者只认唯一 `manifest.json`，不生成或读取 `release-manifest.json`。
- P1-AC3: 后端生成 workflowId/releaseTag 并固定 preset；客户端不能提交 scope、host、NAS、MinIO、repo roots、LocalCacheRoot 或手填 releaseTag。
- P1-AC4: manifest/审计记录维护仓与 IntRuoyi 根仓两个规范化 Git root/批准 commit，并分别记录 maintenance/backend/frontend 三个 source role；构建前和打包前分别重验两个 Git worktree 的 HEAD 与 dirty=false，任一漂移立即阻断。
- P1-AC5: CI 合同要求后端、前端和脚本测试在 Maven/frontend/Docker 构建前显式执行，不能只运行 Maven -DskipTests；Java、Python、PowerShell 双摘要固定向量必须完全一致。
- Evidence expectation: Git/worktree 记录、API/manifest/preset/测试顺序合同和数据流程隔离测试。

### P2

- P2-AC1: 产品 workflow 的实现与测试以主程序 IntRuoyiBackend `yudao-module-infra/.../runtimecontrol/` 为唯一运行时来源，维护仓 backend 仅可提供独立诊断或契约同步；workflow 与 event journal 在进程重启后恢复，状态转换使用原子写和 stateVersion/CAS，损坏状态直接阻塞。
- P2-AC2: build/test/prod 使用同环境持久化租约锁；重复点击返回现有 workflow 或冲突，不能重复执行。
- P2-AC3: 心跳、可靠 timeout、取消和 RECOVERY_REQUIRED 有确定行为；进程重启或写阶段状态不明时不自动续跑，guard return 不产生 SUCCESS。
- P2-AC4: 阶段持久化 attempt、operationId、errorCode、failedStage、retryable 和证据引用；只有 verifier 可推进状态，客户端不能伪造 SUCCESS。
- P2-AC5: preset 固化基础设施参数与 secret 引用并在启动和执行前校验；API、预览、日志、异常和审计只返回脱敏摘要。
- P2-AC6: retry 只在服务端条件满足时开放；内容或迁移修复必须新包新 tag，正式服失败恢复后仍需新授权和 PROD。
- Evidence expectation: 后端状态机、原子持久化、并发锁、超时/心跳、取消、重启恢复、重试策略和秘密扫描测试。

### P3

- P3-AC1: 后端生成未占用 tag，并基于批准提交创建 clean/frozen worktree；构建前和打包前均验证 HEAD 与 dirty=false。
- P3-AC2: Maven 前完成 NAS、Docker、磁盘、容器、端口、secret、锁、目标状态和规范化 LocalCacheRoot 预检；LocalCacheRoot 尾部不得为 publish-int-ruoyi。
- P3-AC3: migration gate 强制目录 allowlist、metadata、delimiter、标识符、幂等性和 schema-only 同镜像隔离演练；需要 target preflight 的集合从本次计划自动推导。
- P3-AC4: 非 schema 迁移及 type=schema 但 DDL 约束依赖历史数据的迁移必须 requiresTargetPreflight=true，并执行目标只读检查。
- P3-AC5: 构建后和每次部署前均按白名单验包并拒绝全部禁止项；包包含自包含 verifier、required SQL、manifest、digest 和构建/迁移/smoke 证据，部署不依赖源码 worktree。
- P3-AC6: NAS 使用 workflow 唯一 staging，上传后复算全包哈希并同卷原子改名为 READY；本地 cache 非权威，只能使用唯一 staging 或严格 /PURGE 后全哈希。
- P3-AC7: 测试发布只接受 READY app-release 的同一 tag/packageDigest/manifestDigest；.env.next 校验后原子替换，失败恢复旧 .env 并核旧 actual images，状态不确定进入 RECOVERY_REQUIRED。
- P3-AC8: 成功同时满足 operation=SUCCESS、manifest/digests、.env IMAGE_TAG、backend/frontend actual tag、容器 running、backend JSON health=UP、frontend 200、release-info/lock/migration 无 FAILED/RUNNING；测试 attestation 绑定同一 digest。
- P3-AC9: promotion attestation 支持 app-release；正式 preview 只读并逐字段核验 authorizationGrantId 绑定的 workflowId、releaseTag、packageDigest、manifestDigest、targetEnvironment=prod、presetId+version、approvedScope、approver、issuedAt/validUntil、nonce、revokedAt、consumedAt。execute 还要求权限、production write 开关、TESTED、PROD 和无锁冲突，并以 CAS 一次性消费授权；跨 workflow/环境/摘要/preset/scope、过期、撤销、已消费和 nonce 重放测试均证明 operation/正式写入未开始，且全程禁止重新构建或修改包。
- P3-AC10: 任一门禁或成功条件缺失均记录 errorCode/failedStage 并停止；失败 tag 退休，正式失败不自动重试或假绿。
- Evidence expectation: 顺序/迁移/包治理/篡改/NAS/部署事务/晋级守卫测试；获授权后的真实测试服运行态证据，正式服只验证无写入守卫。

### P4

- P4-AC1: 主程序 8081 页面及 48081 API 的 workflow 构建/测试请求只接受业务原因与受控来源；正式请求另接受授权引用和 PROD，不接受客户端基础设施参数；维护仓 48181 页面不作为产品验收入口。
- P4-AC2: 标准 UI 只呈现生成程序安装包、发布测试服、晋级正式服三个按钮，并显示“程序包（不含数据）”；不存在 with-data。
- P4-AC3: UI 显示状态、阶段、耗时/心跳、tag、packageDigest、manifestDigest、errorCode、failedStage、证据、actual version 和 retry policy；刷新后一致。TEST_DEPLOYED 的工作流详情可记录测试验收并形成 TESTED，但该动作不是第四个主发布按钮。
- P4-AC4: 按钮由服务端 eligibility 控制并显示禁用原因；重复点击不重复启动；正式确认显示目标、双摘要、测试证明、一次性授权绑定摘要并要求 PROD。
- P4-AC5: 权限失败、API 错误和 secret 缺失可见；响应、预览、日志和复制内容不泄密；状态转换有审计。
- P4-AC6: UI 遵循统一控制台样式，桌面/窄屏无重叠，状态不只靠颜色，按钮可键盘操作并有可访问名称；Playwright 必须登录测试租户 `aoteman` 后打开 `/infra/monitors/runtime-control`，写操作只限测试租户且 API 仅用于最终校验。
- Evidence expectation: 主程序 API 契约、Vue 单元、typecheck/build，以及 `output/playwright/one-button-app-release-20260911/` 下真实 Playwright 桌面/窄屏截图与 trace。

### P5

- P5-AC1: R31-R44 每项至少有一个自动化负例或恢复测试并证明昂贵构建/真实写入未开始；另有 Java/Python/PowerShell 双摘要固定向量、非法路径/大小写冲突和授权跨 workflow/环境/摘要/preset/scope 重放负例。
- P5-AC2: 使用 app-release fixture 完整验证 build-release → NAS READY → publish-test SUCCESS → 工作流详情记录测试验收 → TESTED → promote-prod 使用同一 workflow/tag/packageDigest/manifestDigest，且过程中无重建；授权只消费一次。
- P5-AC3: 主程序后端、主程序前端、维护脚本、包治理和真实浏览器全回归通过；blind-first-pass tester 只以主程序 8081/48081 为产品 surface，浏览器通过项均引用任务目录外证据。
- P5-AC4: 运行手册记录环境、命令类别、secret owner、授权、错误码、恢复、制品和审计位置，不含秘密值。
- P5-AC5: 获当次授权才由登录测试租户 `aoteman` 的真实 UI 路径执行测试服发布，写操作只限测试租户且 API 仅最终校验；正式服只验证 preview/守卫且零写入。维护仓与 IntRuoyi 根仓两个 Git 仓的实现提交只含本任务文件，并分别记录 maintenance/backend/frontend 三个 source role；融合前确认同路径 dirty/frontend 删除归属，融合结果复验后清理 task worktree。
- Evidence expectation: 防复发报告、全量命令摘要、test-report.md、外部 Playwright 证据、授权记录或 blocker、Git/worktree 清理记录。

## Done Definition

- P1-P5 全部完成，每个 acceptance ID 均有 execution-log.md 或独立 test-report.md 证据。
- 规划与测试报告结构校验、completion gate 均通过，无模板占位符和秘密命中。
- 标准 workflow 只能产生/消费 app-release。
- 两阶段禁止项扫描、固定 packageDigest/manifestDigest 算法、三语言固定向量、NAS 原子 READY 和自包含 verifier 已验证。
- 三按钮流程使用持久化状态机；重复点击、重启、超时、取消、失败恢复和环境锁不产生重复执行或假 SUCCESS。
- 测试与正式晋级严格使用同一 workflow/tag/packageDigest/manifestDigest，授权绑定 tuple 只能消费一次且不可重放。
- 正式服自动发布不存在，正式守卫负例全部通过。
- UI 真实浏览器在主程序 8081 登录测试租户 `aoteman` 后完成桌面/窄屏、错误态、刷新恢复和正式确认验收；写入只限测试租户，API 仅最终校验，每个通过项有外部证据。
- R31-R44 防复发、完整 app-release 同制品链、运行手册和审计/secret 边界全部通过。
- 任务实现提交已验证并融合，任务 worktree 已按规则处理。

## Blocking Conditions

- 独立 task worktree 无法建立，或当前脏改动归属冲突无法解决。
- 8080c0d 所需能力未正式融合，或批准应用源不含 713c641 修复/等价变更。
- Java、Maven、Node/pnpm、Python、Git、Docker、PowerShell 5.1 或 Playwright 缺失。
- preset、secret、NAS 或目标只读检查缺失。
- migration allowlist、metadata、自动推导 preflight、delimiter、幂等性或 schema-only 演练失败。
- LocalCacheRoot 不是规范化显式父目录。
- 包命中禁止项、秘密、哈希漂移、非 app-release 或依赖源码 verifier。
- Java/Python/PowerShell 固定向量不一致、manifest.json 非唯一权威、路径含反斜杠/绝对/`..`、大小写冲突，或 packageDigest/manifestDigest 存在自引用。
- workflow/环境锁冲突，或 release-info/lock/migration 存在 FAILED/RUNNING。
- 正式授权未精确绑定 workflow/tag/双摘要/prod/preset/scope，已过期、已撤销、已消费或 nonce 重放。
- 主程序 `http://localhost:8081/infra/monitors/runtime-control`、48081 API 或测试租户 `aoteman` 不可用；不得用维护仓 48181 页面替代产品 E2E。
- 测试服未获当次授权；正式服未获当次授权、有效授权记录或 PROD。
- 任一 required test 失败、跳过或缺少证据。
- 试图 fallback、mock 成功、吞异常、复用失败 tag、修改 READY 包或重新构建晋级。
