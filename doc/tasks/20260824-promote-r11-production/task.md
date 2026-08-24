# 20260824 r11 正式服晋级

## Task Goal

将已在测试服务器成功验证的同一发布包 `release-20260823-intmain-training-r260823f-r11` 按正式发布文档晋级到正式服务器 `172.30.30.57`。不得重建、换包、换 releaseTag 或拼接不同 releaseTag 的环境结果；必须先完成 `mark-release-tested`，再执行 `promote-prod`，并验证正式服真实运行态、版本说明、回滚与备份前置证据。

## Milestones

1. 读取正式发布、服务器、worktree、登录和经验门禁，建立正式晋级任务记录。
2. 核对 r11 发布包、manifest、测试服 SUCCESS、正式服 preflight、负责人矩阵和 prod dry-run 证据。
3. 对同一 r11 执行 `mark-release-tested`，核对 operation 终态和 tested manifest。
4. 对同一 r11 执行 `promote-prod`，仅写正式服务器并轮询 operation。
5. 验证正式服 `.env`、实际镜像、容器、health、HTTP、release-info、页面和运行控制台版本说明。
6. 记录问题、沉淀正式发布经验，完成 closeout 与最终验证报告。

## Expected Verification

- r11 package/manifest 与测试服 SUCCESS 证据保持同一 releaseTag。
- `mark-release-tested` 和 `promote-prod` 均有明确 SUCCESS 结果。
- 正式服 `.env IMAGE_TAG`、backend/frontend 实际镜像、容器状态、backend health=UP、frontend HTTP=200、release-info 和页面版本说明均与 r11 一致。
- 未访问或写入备用服务器；未执行 `promote-backup`，除非用户在本任务中另行明确授权。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；任何正式发布门禁缺失或失败均停止。
- 是否从根因和长期维护角度解决：是；复用已验证 r11 包并遵循正式发布脚本责任人、PROD、RequireTested 和 dry-run 合同。
- 是否存在临时补丁或绕过：否；不重建、不改 tested/lock/migration 状态、不跳过正式 preflight。

## 经验门禁

- Trigger：将测试服已验证 releaseTag 晋级正式服。
- Preflight check：读取正式发布文档、服务器访问和 worktree 规则；核对同一包 manifest/test SUCCESS；正式服 DCC 只读质量预检、负责人矩阵、挂载/MinIO/数据盘和 prod dry-run 必须通过。
- Blocker：包/manifest/test evidence 缺失或不一致、正式服 preflight 非 PASS、责任人缺失、未带 `PROD`/`RequireTested`、operation 非 SUCCESS、运行态任一关键字段不符时 fail fast。
- Verification：在 `execution-log.md` 记录 BDD、GREEN experience-preflight、每个 operation、远端运行态和页面验证证据。
- Forbidden action：禁止重建 r11、复用失败 operation、手工写 tested/lock/migration、访问备用服务器或用旧容器健康状态代替目标版本验证。
- Evidence：本任务 `execution-log.md`、`verification-report.md`、既有 r11 测试服 `verification-report.md`，以及正式发布脚本产生的脱敏 operation/manifest/preflight 证据。

## Current Status

blocked

## Blocker

`promote-prod` operation `op-2026-08-24T162302044432900Z-4eca53c5-366b-4699-b2a7-5a9876992d65` 因正式库迁移预检 `status=blocked` 失败。r11 是 `code-only` 包，但正式库存在未满足的 scope dependency（`20260803_dcc_product_onboarding_flow -> 20260607_product_master_data` 及其下游）。已恢复正式服发布前 `.env` 与旧运行态；不得手工修改迁移状态、改包或绕过门禁。
