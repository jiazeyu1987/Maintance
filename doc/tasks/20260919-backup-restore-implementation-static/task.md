# 备份恢复六个里程碑开发与静态验证

## Current Status

ready_for_closeout

## 任务目标

依据 `docs/recovery/backup-restore-milestones.md` 和
`docs/recovery/backup-disaster-recovery.md` 完成本地代码开发，优先闭合备份、恢复演练和受控恢复的服务端状态契约，并完成后端、PowerShell、前端 TypeScript/静态契约验证。

本轮明确不执行：

- 测试服务器访问、备份、恢复、重启、发布或数据库/MinIO 写入。
- Playwright、真实浏览器 E2E 和运行态恢复演练。
- 生产服、备份服或共享 NAS 操作。

## 里程碑

1. 建立实现任务、读取适用经验门禁并冻结当前源码基线。
2. 修复服务端候选分流与动作参数契约：`REHEARSAL` 允许 `COMPLETE + NOT_RUN`，`CONTROLLED_RESTORE` 必须绑定当前目标有效 `PASSED` 证据。
3. 修复备份/演练/受控恢复的 manifest、chain、target fingerprint、保护点和 `UNKNOWN` 状态静态契约。
4. 同步前端候选模型、动作表单和按钮状态，确保前端不绕过服务端候选与阻断状态。
5. 执行静态验证、后端单元/契约测试、PowerShell 静态测试和前端类型/静态检查；失败则修复并重跑。
6. 记录未执行的 E2E/运行态验证、剩余 blocker，并按任务收尾门禁完成 closeout。

## 预期验证

- BDD 场景和 RED/GREEN 证据写入 `execution-log.md`。
- Java 定向测试与静态契约测试通过。
- PowerShell 备份恢复模块的静态测试通过。
- 前端 `pnpm ts:check` 和相关静态检查通过。
- 关键代码路径无 fallback、吞异常、默认成功、任意路径/命令输入或 `NOT_RUN -> PASSED` 绕过。
- 不执行 E2E；最终报告明确静态验证与运行态验证边界。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；缺少候选、链、签名、兼容性、保护点或目标证明时必须阻断。
- 是否从根因和长期维护角度解决：是；统一 candidate type、不可变 manifest、可变证据和目标绑定状态。
- 是否存在临时补丁或绕过：否；不通过前端隐藏、默认状态或测试 mock 掩盖后端缺口。

## 经验门禁

- Trigger：按钮化备份恢复、`backup-now`、`restore-rehearsal`、`restore-data`、`candidateType`、`NOT_RUN`、`PASSED`、`UNKNOWN`、manifest/chain digest、几百 GB 六里程碑实施。
- Preflight check：读取 `E:\IntRuoyi\docs\release-backup-restore.md`、`docs\recovery\backup-restore-milestones.md`、`docs/recovery/backup-disaster-recovery.md`，确认本轮只做本地静态开发，不执行服务器或数据写入。
- Blocker：源码、测试、配置或恢复候选契约缺失；无法区分演练候选与覆盖候选；静态验证不能证明 fail-fast、目标绑定或未知终态写保护。
- Verification：本任务 `execution-log.md`、`test-report.md`、`verification-report.md`，后端/前端/PowerShell 静态测试输出。
- Forbidden action：禁止访问远端服务器，禁止 E2E，禁止用 mock/API-only 替代真实运行态结论，禁止把历史演练报告或 `COMPLETE` 状态直接当作当前覆盖授权。
- Evidence：`docs/recovery/backup-restore-milestones.md`、`docs/recovery/backup-disaster-recovery.md`、`E:\IntRuoyi\docs\release-backup-restore.md`。

## 完成记录

- M1 完成：任务目录、经验门禁、请求日志、BDD 场景和验证计划已建立。
- M2 完成：后端候选拆分为 `REHEARSAL` / `CONTROLLED_RESTORE`，动作绑定按候选类型校验。
- M3 静态部分完成：候选 API 暴露 `manifestDigest`、`chainDigest`、`sourceFingerprint`、`targetFingerprint`；linux-local 备份类型与配置策略不一致时 fail fast。
- M4 完成：前端按动作过滤恢复候选，`backup-now` 显式选择 `FULL` / `INCREMENTAL` 并提交 `backupKind`。
- M5 完成：本地静态验证通过，详见 `verification-report.md`。
- Closeout cleanup 完成：`task-closeout-cleanup` preview/apply 已运行，仅删除本任务临时 `test-plan.md`，保留 `task.md`、`execution-log.md`、`verification-report.md`。
- 长期经验已沉淀到 `E:\IntRuoyi\docs\release-backup-restore.md` 的“按钮化备份恢复入口门禁”。

## 当前阻塞与运行态边界

- 实际服务器状态、几百 GB 真实备份/恢复、版本/换机和 E2E 本轮不验证，必须保留为运行态 blocker。
- 未执行真实 RTO/RPO、升级、降级、换硬件、换数据盘、密钥轮换或目标为空/保护点验证。
- 项目 closeout 规则要求提交/推送后才能标记 `completed`；当前仓库存在大量非本任务脏改动，且本轮未获得提交/推送指令，因此任务保持 `ready_for_closeout`，不扩大提交范围。
