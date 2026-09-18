# 正式发布按钮测试数据

## Purpose and Scope

定义实现和 E2E 所需的真实/隔离测试数据、归属和清理规则。业务数据不进入发布包，不为测试修改芋道源码租户业务数据。

## Evidence Reviewed

- 项目规定写入型 E2E 只允许测试租户 `tenant_id=122`、账号 `aoteman`，最终 admin 仅做只读验证。
- 发布 workflow/preview/grant/operation 是运维状态数据，不是业务数据，但必须带任务标识并可追踪。
- 正式服操作必须另行授权，不能以测试数据名义绕过。

## Required Test Data

### 单元/合同 fixture

- `READY`、`TEST_DEPLOYED`、`TESTED`、`PROMOTING_PROD`、`RECOVERY_REQUIRED` 工作流 fixture。
- 成对合法和不匹配的 package/manifest SHA-256。
- succeeded/failed/running publish-test operation evidence。
- eligible、blocked、expired、stale production preview。
- valid、expired、revoked、consumed、binding-mismatch authorization grant。
- 重复 idempotency key、不同 payload 同 key、活动 prod lease。
- 全 PASS 与单项漂移的最终运行态证据。

fixture 全部位于测试临时目录，不能引用真实凭据或把 mock 成功用于真实 E2E 结论。

### 测试服真实数据

- 新 releaseTag 构建的不可变 app-release 包。
- 真实测试服 publish operation 和完整运行态证据。
- 通过真实页面提交的 PASS 测试验收，acceptedBy 来自服务端认证上下文。
- TESTED workflow 及 tested proof。
- 运行控制台测试租户专用操作者权限；任何权限变更先走独立迁移和真实菜单投影验证。

### 正式服真实数据

- 仅使用已在测试服验收的同一发布包和 workflow。
- 不创建业务 fixture、不修改芋道源码租户业务数据。
- 正式发布产生的 workflow/preview/grant/operation/审计/运行态证据属于任务证据。

## Reset Procedure

- 单元/合同临时目录由测试进程清理，仅删除任务自有路径。
- 未消费 preview/grant 可按保留策略过期，不通过手工改 JSON 复位。
- 测试服权限/菜单 fixture 由对应 migration/任务清理，禁止直接清空角色菜单。
- 正式服发布成功后不“清理”正式版本；失败时按 `RECOVERY_REQUIRED` 的正式恢复流程处置。
- 禁止通过删除 operation、workflow、migration ledger 或远端锁伪造干净状态。

## Data Ownership

- workflow、preview、grant、operation：运行控制台服务拥有。
- manifest、tested proof：发布治理模块拥有，内容不可变。
- 环境锁：发布执行器拥有，恢复流程才能释放异常锁。
- 测试租户业务数据：测试任务拥有，必须带任务标识。
- 正式业务数据：不属于本功能测试，不得修改。

## Test Blockers

- 缺真实 TESTED 包、目标配置、专用权限或恢复负责人。
- 测试服/正式服存在无法归属的活动发布或锁。
- 目标 preview 需要通过修改业务数据才能 PASS。
- 任何凭据只能以明文写入测试文件或命令日志时必须停止。
