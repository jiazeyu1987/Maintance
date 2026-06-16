# 运行控制台逻辑一致性审计执行记录

## BDD

BDD: 独立维护应用与原运行控制台逻辑一致性 -> Given 审计者只读检查当前独立维护应用和原 IntRuoyi 运行控制台代码，When 对比接口、服务、脚本、前端契约与安全门禁，Then 应明确列出一致项、刻意拆分差异、潜在漂移风险与验证证据。

BDD: 审计不触发运维写动作 -> Given 运行控制台包含发布、备份、恢复、回滚、重启等高风险能力，When 本任务执行一致性分析，Then 只能使用只读文件检查和静态命令，不得提交或执行任何运维动作。

## Verification Evidence

- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md` 与命中的 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`；本任务只读审计，不执行高风险动作。
- GREEN: `rg --files doc/tasks/20260616-runtime-control-consistency-audit` -> PASS，确认任务文档目录存在。
- GREEN: `git status --short` -> PASS，开始审计时仅任务目录为新增文档，未发现生产代码改动。
- GREEN: `rg --files backend/src/main/java/com/intruoyi/maintenance/runtime backend/src/test/java/com/intruoyi/maintenance/runtime` 与原 IntRuoyi runtimecontrol 目录 -> PASS，定位当前独立应用和原运行控制台后端文件。
- GREEN: 修正端点提取脚本 -> PASS，独立版 27 个运行控制台接口，原版 33 个；公共路径一致，原版额外包含 owner-matrix、wizard、alerts resend site message 6 个接口。
- GREEN: `rg -n "selectedImageTag|selectedBackupId|apply-test-db-sql|owner-matrix|wizard|resend-site-message"` -> PASS，确认候选字段、SQL 动作入口、治理接口差异。
- GREEN: `rg -n "PreAuthorize|SecurityFrameworkUtils|getLoginUserId|CommonResult|ApiResult"` -> PASS，确认独立版已去除芋道权限/登录依赖，响应外形使用本地最小等价类型。
- GREEN: `rg -n "code-only|with-data|SkipDatabaseSync|SkipMinioSync|BackendRepoRoot|FrontendRepoRoot|WebsiteRepo|opsRoot|script/|ops/"` -> PASS，确认构建发布包 code-only 参数一致，脚本路径和源码根参数为独立化改造差异。
- GREEN: `rg -n "maintenance.runtime-control|yudao.runtime-control|productionWriteEnabled|ConfigService|infra_config"` -> PASS，确认独立版配置来源与原系统 ConfigService 来源不同且符合独立化边界。
- GREEN: static-audit-no-risk-action -> PASS，未执行发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。

## Blockers

- 暂无。
