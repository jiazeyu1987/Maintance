# 运行控制台原版逻辑一致性审计报告

## 结论

结论：当前 `D:\ProjectPackage\Int\IntRuoyiMaintance` 的独立运行控制台与原版 `D:\ProjectPackage\Int\IntRuoyi` 运行控制台在核心逻辑上已一致，可以视为“独立化边界内的一致”。

本次审计没有执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。

## 已确认一致

- HTTP 接口：独立版 `RuntimeControlController` 与原版控制器归一到 `/admin-api/infra/runtime-control/*` 后，33 个 HTTP 方法与路径一致。
- 动作枚举：10 个 action id 顺序一致，包含 `build-release`、`publish-test`、`apply-test-db-sql`、`mark-release-tested`、`promote-prod`、`promote-backup`、`backup-now`、`rollback-app`、`rehearsal`、`restore-data`。
- 发布包候选：读取 manifest/checksum/tested 证据后才展示或放行；缺失 manifest/checksum 时 fail fast。
- 高风险候选：`rollback-app` 的 `selectedImageTag`、`restore-data/rehearsal` 的 `selectedBackupId` 均由服务端候选解析，前端不可自由提交。
- 测试通过标记：`mark-release-tested` 使用测试环境当前发布版本，并绑定恢复集候选、manifest hash、程序版本与 Redis 策略。
- 恢复候选：读取备份 manifest、DCC manifest、checksum、恢复集和演练证据；DCC `chainStatus` 不是 `COMPLETE` 时阻断。
- 前端 payload：只按动作提交对应字段，避免把 `publishScope`、`includeOnlyOffice`、`releaseTag`、`targetEnvironment`、`sqlPath` 等不相关字段带到其他动作。
- 前端入口：独立版移除了登录、菜单、权限依赖，但保留运行控制台动作、候选选择、预览、执行和操作日志入口。
- 运维脚本：`apply-test-db-sql.ps1`、`backup-ops.ps1`、`show-int-ruoyi-local-status.ps1`、`restart-int-ruoyi-local.ps1` 与原版 SHA256 一致。

## 独立化预期差异

- 权限体系：原版保留 `@PreAuthorize`、`SecurityFrameworkUtils/getLoginUserId`、`v-hasPermi/checkPermi`；独立版按用户要求不接入芋道登录、角色、菜单权限。
- 操作者来源：原版使用登录用户；独立版使用 `local-operator` / 显式本机操作者标识。
- 监听边界：独立版默认 `127.0.0.1:48181`，原版作为芋道后端模块运行。
- 配置来源：原版依赖芋道配置服务与 NAS 设置服务；独立版读取 `config/runtime-control.local.yaml` 与独立配置类，缺少必填项直接失败。
- 运行态存储：独立版将运行记录、治理状态、告警、事故等写入独立仓库 `runtime/runtime-control/`，并由 `.gitignore` 排除。
- 正式服写门禁：独立版保留更严格的 `production-write-enabled=false` 默认禁写；这是拆分计划中的安全边界，不回退到原版权限体系。
- 发布脚本：`publish-int-ruoyi.ps1` 非字节级一致，独立版保留前序真实发布包 E2E 中修复的被管理源码路径参数和 DCC inventory UTF-8/base64 传输修正。

## 剩余风险

- 独立版不是原芋道模块的 1:1 运行环境复制；凡涉及真实站内信、登录用户审计、菜单权限响应，行为不会与原系统完全相同。
- `publish-int-ruoyi.ps1` 与原版不同，当前差异属于独立化必要修正；后续如果原版脚本继续演进，需要再做一次三方合并，防止独立版脚本落后。
- 生产确认源码语义有一处不可达差异：独立版 `restore-data` 的生产确认判断包含 `prod|backup`，但参数校验只允许 `test|backup`，因此有效请求行为与原版一致，建议后续小清理时收窄为 `backup` 提升源码可读性。

## 验证证据

- `python -X utf8 scripts\verify_contracts.py` -> PASS。
- `mvn -f backend\pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS，7 tests / 0 failures。
- `pnpm --dir frontend typecheck` -> PASS。
- `mvn -f backend\pom.xml test` -> PASS，14 tests / 0 failures。
- `pnpm --dir frontend build` -> PASS，Vite 仅提示单 chunk 超过 500 kB。
- 静态比对脚本输出：`ENDPOINT_COUNT standalone=33 original=33 equal=True`；`ACTION_COUNT standalone=10 original=10 ids_equal=True`。
- 脚本哈希比对：4 个脚本字节级一致；`publish-int-ruoyi.ps1` 差异为独立应用路径与编码修正。