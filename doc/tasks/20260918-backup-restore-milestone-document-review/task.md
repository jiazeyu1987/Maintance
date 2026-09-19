# 备份恢复六个里程碑文档审查与修复

## Current Status

completed

## 任务目标

对 `docs/recovery/backup-restore-milestones.md` 执行灾备合同和独立验证审查，识别逻辑矛盾、不可执行表述、安全风险、遗漏场景和验收歧义；直接修复阻塞问题并复审，形成可放行文档。

## 里程碑

1. [完成] 建立任务记录，读取适用经验和恢复合同。
2. [完成] 建立“要求 -> 文档章节 -> 证据”审查清单并输出首轮问题。
3. [完成] 修复首轮问题，保持六个主里程碑结构不变。
4. [完成] 独立复审修订结果，验证结构、UTF-8、关键合同和 Git 差异。
5. [完成] 完成任务收尾和经验归并判断。

## 预期验证

- 恢复候选状态不存在“先演练通过才能成为演练候选”的循环依赖。
- RPO/RTO 口径覆盖数据库与对象的共同恢复点以及完整恢复时间。
- 几百 GB 的“备份包”明确为逻辑恢复集，不诱导生成单一巨大压缩包或经用户电脑中转。
- 隔离演练阻止通知、任务、MQ、Webhook 等外部副作用。
- Redis、密钥 escrow、不可变镜像/恢复工具、外部依赖和配置分类有明确恢复策略。
- 演练证明绑定链摘要、工具/目标环境并可失效，不能永久复用一次 PASS。
- 保留策略按恢复依赖图和法规归档边界执行。
- M1-M6 标题数量仍为 6，关键验收门禁齐全。
- UTF-8 回读和 `git diff --check` 通过。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；缺少证据、依赖或支持组合时继续 fail fast。
- 是否从根因和长期维护角度解决：是；修复恢复合同、状态模型和验收边界，而非补充含糊免责声明。
- 是否存在临时补丁或绕过：否；只修订正式文档，不操作服务器或伪造恢复证据。

## 技能使用

- `backup-disaster-recovery-readiness`：按恢复合同审查范围、RTO/RPO、密钥、恢复测试和灾难场景。
- `independent-verification-gate`：建立要求到文档证据的映射，未覆盖要求判为未完成。
- `review-fix-loop`：已读取但不适用；该技能绝对约束仅允许代码任务，本次为纯文档审查。

## 经验门禁

- Trigger：审查几百 GB 备份恢复里程碑、按钮化恢复、增量链、secret/key 恢复和保留清理。
- Preflight check：核对实际规模 FULL 与隔离恢复、数据库/对象共同恢复点、`baseBackupId/parentBackupId/position`、对象 tombstone、独立控制平面、服务端候选、Redis policy、secret escrow、支持矩阵、容量和 RTO/RPO 口径。
- Blocker：演练候选与覆盖候选循环依赖、writer/storage fence 不完整、历史密钥不可恢复、对象增删改或链位置缺失、恢复控制平面与目标同故障域、备份仓库依赖源机、演练可触发外部副作用、法规归档可能被灾备清理、或用小样本外推几百 GB 时不得放行。
- Verification：逐要求映射到修订章节；M2 实际规模 FULL 隔离恢复；M3 至少三个真实增量并恢复中间/最新点；M4 区分演练候选和覆盖候选；M5 验证支持矩阵、换机和不兼容阻断；M6 验证最大允许链、保留图和故障注入。
- Forbidden action：禁止把生成文件当可恢复、把数据库增量当整系统增量、用一次永久 PASS 演练授权未来覆盖、让浏览器/用户电脑中转几百 GB、静默切换 FULL/INCREMENTAL、在隔离演练中连接真实外部系统、用灾备保留替代法规归档。
- Evidence：`E:\IntRuoyi\docs\release-backup-restore.md` 中“恢复一致性、秘密恢复与归档可用性门禁”“按钮化备份恢复入口门禁”“大数据量备份恢复首版里程碑顺序门禁”，以及 `docs/recovery/backup-disaster-recovery.md`。

## 审查结果摘要

- 首轮审查判定：FAIL，发现 10 项 P1/P2 文档合同问题。
- 修订后判定：PASS for document/design scope；当前实现候选分层和真实 M2-M6 演练仍是明确 blocker。
- 主要修订：候选分层、manifest/动态证据分离、共同 RPO/RTO、隔离副作用、半恢复保护、源/仓库权限边界、日志/对象连续性、审计/四眼确认、终态 `UNKNOWN`、保留/法规边界。
- 关联设计文档已同步，避免总体设计与里程碑文档使用相互矛盾的候选口径。

## 当前验证结果

- 六个主里程碑标题数量：6。
- 文档 UTF-8、代码围栏、行尾空白和关键合同检查：通过。
- 灾备验证器 self-test 与总体设计文档验证：通过。
- 未访问测试服务器，未执行真实备份、恢复、发布、数据库、MinIO 或 E2E。

## 复审证据

- PASS：候选状态循环依赖已消除，`COMPLETE + NOT_RUN` 只允许隔离演练，目标绑定 `PASSED` 才允许受控恢复。
- PASS：不可变 manifest、detached signature、payload inventory 与可变候选证明分离。
- PASS：共同恢复点 RPO、当前保护点年龄、已证明恢复点年龄、演练 RTO、覆盖 RTO 已定义。
- PASS：隔离副作用、半恢复环境、源/仓库权限、`UNKNOWN` 终态、最大链和保留/法规边界已写入门禁。
- PASS：关联总体设计同步候选分层和 BDD 场景。
- PASS：两份正式文档结构、UTF-8、代码围栏、行尾空白和关键合同检查通过。

## 收尾结果

- task-closeout cleanup preview/apply：通过。
- 保留 `task.md`、`execution-log.md`、`verification-report.md`，删除 0 个文件。
- 当前为主工作区，无 worktree 合并或删除动作。
- 上一轮任务状态：completed；关联设计文档修订后已重新完成验证和 closeout。
- 本轮最终任务状态：completed。
- 关联设计文档后续复审发现旧的 freshness/RPO、空目标 snapshot 和 `FAIL` 终态口径，已同步修正，需重新执行 closeout。
