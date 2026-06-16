# 运行控制台原版一致性修复

## Task Goal

按用户要求将独立维护应用 `IntRuoyiMaintance` 的运行控制台逻辑改成与原版 IntRuoyi 运行控制台一致，优先补齐上轮审计发现的非预期差异：Linux-local 备份命令参数、原版治理接口的本地持久化行为、前端运行控制台日志/治理接口契约。保持独立本机应用边界：不接入芋道登录、角色、菜单权限；不执行真实发布、备份、恢复、回滚、重启或远端清理。

## Milestones

- [x] 创建任务文档、经验门禁和 RED 验证用例。
- [x] 对齐后端核心动作命令与原版 Linux-local 备份参数。
- [x] 对齐原版运行治理接口的本地持久化行为：巡检、告警、责任矩阵、事故、向导场景。
- [x] 补齐前端运行控制台日志入口与治理接口契约，保持 IntPP 操作台风格。
- [x] 跑后端、前端、契约验证并提交当前任务改动。

## Expected Verification

- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalGovernanceParityTest test`
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test`
- `mvn -f backend/pom.xml test`
- `python -X utf8 scripts\verify_contracts.py`
- `pnpm --dir frontend typecheck`
- `pnpm --dir frontend build`

## 经验门禁

- 命中 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布、备份、恢复、回滚不得用 mock、默认成功、静默跳过或自动降级掩盖失败；缺少 manifest、schema 版本、备份链、恢复证据、环境凭据或授权时必须 fail fast。本任务不执行真实发布、备份、恢复、回滚、重启、SSH、远端清理、数据库写入或对象存储写入。
- 命中 `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：运行控制台作为运维操作界面应保持白色工作面、蓝灰边框、紧凑表格、工具条和安静的行内操作，不做营销式大标题、装饰卡片或渐变背景。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是，本次以原版源码契约补齐独立版非预期差异。
- `是否存在临时补丁或绕过`：否。

## Current Status

completed

## Completed Work

- 后端 `linux-local` 备份动作改为原版 `--mode/--config/--non-interactive` 参数，并且 Linux 模式不再追加 PowerShell 专用 `-OperatorName`。
- 后端运行治理接口改为本地 `runtime-ops/*.json` 持久化：巡检报告、告警、责任矩阵、事故和探针最新结果。
- 责任矩阵、向导场景、事故 DTO 与原版 IntRuoyi 语义对齐；缺记录时明确失败，不返回模拟成功。
- 前端补齐原版治理接口 wrapper，并在操作记录表加入日志查看入口。

## Final Verification

- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalGovernanceParityTest test` -> PASS
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS
- `mvn -f backend/pom.xml test` -> PASS，14 tests
- `python -X utf8 scripts\verify_contracts.py` -> PASS
- `pnpm --dir frontend typecheck` -> PASS
- `pnpm --dir frontend build` -> PASS
