# 运行控制台逻辑一致性审计

## Task Goal

分析当前独立维护应用与 `D:\ProjectPackage\Int\IntRuoyi` 中原运行控制台的逻辑一致性，覆盖后端接口、服务行为、命令脚本参数、前端交互契约与安全边界；本任务只读审计，不修改生产代码，不触发发布、备份、恢复、回滚、重启或远端清理动作。

## Milestones

- [x] 创建任务文档，记录目标、门禁、验证方式。
- [x] 定位当前独立应用与原 IntRuoyi 运行控制台相关代码。
- [x] 对比接口路径、VO、服务逻辑、脚本参数与前端调用。
- [x] 输出一致性报告与风险分级。
- [x] 更新任务记录并按项目规则提交文档。

## Expected Verification

- 使用 `rg`、`git diff --no-index --stat`、文件读取等只读命令定位差异。
- 不执行运行控制台写动作，不连接远端服务器，不触发发布、备份、恢复、回滚、重启或清理。
- 输出 `doc/tasks/20260616-runtime-control-consistency-audit/verification-report.md`。

## 经验门禁

- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：运行控制台涉及构建、发布、备份、恢复、回滚能力；审计期间不得用 mock、默认成功、静默跳过或自动降级掩盖失败。
- 未获用户授权时，本任务不访问正式服务器，不执行 SSH、HTTP 写入、对象存储写入、数据库写入或真实运维动作。
- `code-only` 与 `with-data`、发布包 manifest、候选识别、恢复候选、操作证据等边界必须按文档判断，不以界面健康或单行日志替代 operation 结果。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否，本任务只读审计。
- `是否从根因和长期维护角度解决`：是，通过源代码和接口契约逐项比较，报告一致/不一致位置。
- `是否存在临时补丁或绕过`：否。

## Verification Result

- `rg --files` 与 `rg -n` 静态检查 PASS，已覆盖当前独立应用与原 IntRuoyi 后端、前端运行控制台文件。
- 端点提取比对 PASS：独立版 27 个、原版 33 个；公共路径一致，原版额外包含负责人矩阵、向导推荐、告警站内信重发 6 个接口。
- 审计报告已输出：`doc/tasks/20260616-runtime-control-consistency-audit/verification-report.md`。
- 高风险动作限制 PASS：未执行发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。

## Current Status

completed
