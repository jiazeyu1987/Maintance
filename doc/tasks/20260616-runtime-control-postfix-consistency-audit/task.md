# 任务: 运行控制台原版逻辑一致性审计

## 任务目标

分析当前独立维护应用 `D:\ProjectPackage\Int\IntRuoyiMaintance` 中运行控制台代码，与原版 `D:\ProjectPackage\Int\IntRuoyi` 下运行控制台逻辑的一致性，输出可追溯审计结论。

本任务只做代码、契约、测试和构建证据审计，不执行真实发布、备份、恢复、回滚、重启、远端清理、SSH、数据库写入或对象存储写入。

## 经验门禁

- `docs/experience-index.md`：本任务命中运行控制台、发布/备份/恢复、高风险动作、E2E 与前端一致性门禁。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`：发布、备份、恢复相关能力必须 fail fast，不得 mock 成功、默认成功或静默降级；本次只审计，不执行真实高风险动作。
- `D:\ProjectPackage\Int\IntPP\FRONTEND_STYLE.md`：涉及前端运行控制台展示一致性时，审计其是否保留紧凑、信息密集、操作台式布局。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。本任务不改生产逻辑。
- `是否从根因和长期维护角度解决`：是。通过原版与当前代码逐项比对，输出剩余偏差与后续修复边界。
- `是否存在临时补丁或绕过`：否。本任务不做临时代码补丁。

## 里程碑

- [x] 创建任务目录与任务文档。
- [x] 读取原版与当前运行控制台后端逻辑，比较接口、动作门禁、脚本参数和运行态治理行为。
- [x] 读取原版与当前运行控制台前端逻辑，比较页面入口、API 封装和关键操作可见性。
- [x] 运行现有契约、后端、前端验证命令，确认当前代码基线。
- [x] 生成 `verification-report.md` 审计报告。
- [x] 更新执行日志、命令日志，并在验证后提交本任务文档。

## 预期验证

- `mvn -f backend/pom.xml test`
- `python -X utf8 scripts\verify_contracts.py`
- `pnpm --dir frontend typecheck`
- `pnpm --dir frontend build`

## 当前状态

已完成。

## Cleanup Keep

- `doc/tasks/20260616-runtime-control-postfix-consistency-audit/verification-report.md`

## 最终验证

- `python -X utf8 scripts\verify_contracts.py` -> PASS。
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS，7 tests / 0 failures。
- `pnpm --dir frontend typecheck` -> PASS。
- `mvn -f backend/pom.xml test` -> PASS，14 tests / 0 failures。
- `pnpm --dir frontend build` -> PASS，Vite 仅提示现有单 chunk 体积超过 500 kB。
- 静态接口/动作比对：控制器 33 个 HTTP 接口一致，动作枚举 10 个 action id 顺序一致。

## 审计结论

当前独立维护应用与原 IntRuoyi 运行控制台在公开接口、核心动作枚举、候选门禁、发布包/恢复集 fail-fast、前端 payload 约束和主要脚本契约上保持一致。差异集中在用户要求的独立化边界：不接入芋道登录/角色/菜单权限，统一本机操作者，配置与运行态落在独立仓库，默认仅监听 `127.0.0.1` 且正式服写动作默认禁用。详见 `verification-report.md`。