# 运行控制台逻辑一致性审计报告

## 结论

本次按 `yintruoyi` 指 `D:\ProjectPackage\Int\IntRuoyi` 理解，对比对象为当前独立维护应用 `D:\ProjectPackage\Int\IntRuoyiMaintance`。

总体结论：当前独立应用与原 IntRuoyi 运行控制台 **基础接口形状、主要动作枚举、命令脚本参数骨架基本一致**，并且已按独立应用目标移除了芋道登录、菜单权限和 `SecurityFrameworkUtils` 依赖；但它 **不是完整逻辑等价抽取**。高风险发布、晋级、回滚、恢复相关的候选绑定、发布包可用性校验、恢复集校验、负责人责任门禁和前端动作覆盖存在明显漂移。

若当前目标只是“本机轻量控制台 + 构建发布包预览/执行”，现状可解释为有意简化；若目标是“除权限登录外与原运行控制台行为一致”，需要补齐下列差异后再视为一致。

## 一致项

- HTTP 主路径基本一致。独立版暴露 `/admin-api/infra/runtime-control/*`，去掉 `/admin-api` 后与原控制器 `@RequestMapping("/infra/runtime-control")` 的公共路径一致；静态提取结果为独立版 27 个、原版 33 个，独立版无额外路径。
- 后端核心动作枚举一致。两边均包含 `build-release`、`publish-test`、`apply-test-db-sql`、`mark-release-tested`、`promote-prod`、`promote-backup`、`backup-now`、`rollback-app`、`rehearsal`、`restore-data`。
- 构建发布包 `code-only` 语义一致。两边 `build-release` 在 `code-only` 下都会追加 `-SkipDatabaseSync` 与 `-SkipMinioSync`。
- 独立化差异符合拆分目标：当前控制器不含 `@PreAuthorize` / `SecurityFrameworkUtils.getLoginUserId`；原控制器大量使用权限注解并从登录态取操作者。
- 响应外形兼容。独立版用最小 `ApiResult(code,data,msg)`，原版用芋道 `CommonResult`，成功响应外层语义一致。
- 配置来源变更符合独立化目标。独立版使用 `maintenance.runtime-control` 本地配置并 fail fast 校验源码、前端、展厅、脚本、运行目录；原版通过 `yudao.runtime-control` 与 `infra_config` / `ConfigService` 读取部分发布包配置。

## 明显不一致

### 1. 回滚/恢复候选绑定逻辑不一致

等级：高。

独立版前端和 DTO 允许提交 `selectedImageTag`、`selectedBackupId`，后端还要求回滚/恢复请求同时包含候选 ID 和这些实际值：

- `D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\src\App.vue:181`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\src\App.vue:183`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\src\api\runtimeControl.ts:65`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\src\api\runtimeControl.ts:67`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlOperationAction.java:179`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlOperationAction.java:183`

原 IntRuoyi 明确把 `selectedImageTag`、`selectedBackupId` 视为服务端候选解析结果，客户端直传会被拒绝：

- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:839`
- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:843`
- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:963`

影响：独立版允许手工填入镜像标签和备份点，绕过了原系统“候选 ID -> 服务端解析 -> 可用性校验”的安全边界。

### 2. 发布包可用性校验不一致

等级：高。

独立版 `getReleasePackages()` 主要按 NAS 目录列出发布包并标记为 `AVAILABLE`，动作准备阶段没有看到原系统同等级的 manifest、checksum、tested 状态校验：

- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:224`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:97`

原 IntRuoyi 会读取发布包仓库、构建完整发布包响应，并在发布/晋级前校验包存在、manifest/checksum 可用，正式/备份晋级还要求测试通过：

- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:436`
- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:855`
- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:941`

影响：独立版在 `publish-test`、`promote-prod`、`promote-backup` 上可能接受原系统会拒绝的发布包。

### 3. 前端动作覆盖不一致

等级：中。

独立版后端有 `apply-test-db-sql`，但前端动作组没有对应入口；原前端有按钮、SQL 路径表单、目标环境推断和提交校验：

- 独立版动作组：`D:\ProjectPackage\Int\IntRuoyiMaintance\frontend\src\App.vue:33`
- 原前端按钮：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\src\views\infra\runtime-control\index.vue:715`
- 原 SQL 表单：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\src\views\infra\runtime-control\index.vue:409`
- 原提交校验：`D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3\src\views\infra\runtime-control\index.vue:1628`

影响：独立版出现“后端动作存在、页面不可达”的行为缺口。

### 4. 候选、恢复、备份数据结构明显简化

等级：中到高。

独立版 `getRollbackCandidates()`、`getRestoreCandidates()`、`getBackupPoints()` 共用轻量 NAS 目录候选，返回结构为统一 `RuntimeControlCandidateRespVO`：

- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:241`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:245`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:249`

原系统有独立的 rollback、restore、backup point VO 与候选服务，包含恢复集状态、兼容性、DCC 链路、演练、校验和、不可恢复原因等更丰富逻辑。

影响：独立版不足以复刻原系统回滚/恢复前的风险判断。

### 5. 原系统治理能力未迁移

等级：中。

原控制台比独立版多 6 个接口：

- `GET /infra/runtime-control/owner-matrix`
- `POST /infra/runtime-control/owner-matrix`
- `PUT /infra/runtime-control/owner-matrix/{id}`
- `GET /infra/runtime-control/wizard/scenarios`
- `POST /infra/runtime-control/wizard/recommendation`
- `POST /infra/runtime-control/alerts/{id}/resend-site-message`

这些对应负责人矩阵、操作向导推荐和告警站内信重发。独立版也没有原系统的 `RuntimeOpsResponsibilityService`、`RuntimeOpsGuideService`、`RuntimeOpsOwnerMatrixStore` 等治理逻辑。

影响：这部分若被视为运行控制台业务逻辑，则独立版未覆盖；若拆分范围刻意只保留本机运维核心动作，需要在项目说明中明确排除。

### 6. 操作状态枚举不一致

等级：中。

独立版操作状态写入 `RUNNING`、`SUCCESS`、`FAILED`：

- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:363`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:372`
- `D:\ProjectPackage\Int\IntRuoyiMaintance\backend\src\main\java\com\intruoyi\maintenance\runtime\RuntimeControlService.java:375`

原系统操作状态使用 `running`、`succeeded`、`failed`：

- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:637`
- `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\yudao-module-infra\src\main\java\cn\iocoder\yudao\module\infra\service\runtimecontrol\RuntimeControlServiceImpl.java:640`

影响：如果后续复用原前端组件、日志分析或契约测试，会出现状态映射不兼容。

### 7. 远端根目录清理能力不是等价实现

等级：中。

独立版保留了 remote root disk 接口，但服务实现倾向于拒绝自动远端命令或要求额外授权；原系统有 `RuntimeRemoteRootDiskServiceImpl`，会调用 `script/deploy/manage-int-ruoyi-remote-root-disk.ps1` 执行状态检查/清理。

影响：这是安全上可接受的简化，但不是逻辑一致。

### 8. 测试覆盖不一致

等级：中。

独立版目前只有一个运行控制台契约测试文件；原 IntRuoyi 有运行控制台服务、高风险动作、候选、备份演练、负责人、探针、存储、远端清理等多组测试。

影响：独立版缺少对“客户端不得传内部候选值”“发布包必须 manifest/checksum/tested 可用”“恢复候选必须完整”的回归锁。

## 建议

如果目标是行为一致，优先修复顺序如下：

1. 移除独立版公共请求中的 `selectedImageTag`、`selectedBackupId` 输入能力，仅保留候选 ID；由服务端从候选仓库解析真实镜像标签和备份点。
2. 迁移或重建原系统发布包仓库解析与 `validateReleasePackageAvailability` 校验，确保发布/晋级前检查 manifest、checksum、tested 状态。
3. 恢复 rollback/restore/backup candidate 的独立 VO 和服务逻辑，至少覆盖恢复集、校验和、兼容状态、不可恢复原因。
4. 决定 `apply-test-db-sql` 是保留还是下线：保留则补前端入口和 SQL 校验；下线则同步移除后端动作。
5. 明确负责人矩阵、向导推荐、告警站内信重发是否属于独立版范围；若属于范围，需要迁移接口和服务。
6. 统一操作状态枚举，或在独立版 API 文档中明确状态值与原系统不同。

## 验证记录

- GREEN: `rg --files` 定位当前独立应用与原 IntRuoyi 后端、前端运行控制台文件 -> PASS。
- GREEN: 修正端点提取脚本，对比公共路径 -> PASS；独立版 27 个，原版 33 个，独立版无额外接口，原版多 6 个治理接口。
- GREEN: `rg -n` 静态检查权限、候选字段、发布包校验、前端动作、状态枚举、ConfigService 差异 -> PASS。
- GREEN: 高风险动作限制 -> PASS；未执行发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。
