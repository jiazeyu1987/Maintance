# Bug Regression Evidence：backup 环境仍被 test 硬编码阻断

## Bug Summary

`ops/backup-ops` 顶层入口宣称支持 `TargetEnvironment=backup`，但 `FileOps`、`DockerOps` 等关键 helper 仍把目标证明、SSH 环境与恢复候选识别硬编码到 `test/172.30.30.58`，导致备份服链路无法把 `backup/172.30.30.59` 识别为合法环境。

## Expected Behavior

- `TargetEnvironment=backup` 时，备份服 `172.30.30.59` 应被识别为合法目标证明。
- `FileOps` 应能解析 `backup` SSH 目标。
- `DockerOps.Get-BackupOpsRestoreCandidates` 不应因为 `manifest.targetEnvironment=backup` 而丢弃候选。

## Reproduction

- 回归命令：`Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests\BackupTargetEnvironment.Tests.ps1 -EnableExit`
- 首次失败现象：
  - `Test-BackupOpsKnownBackupTarget -Environment backup -Host 172.30.30.59` 返回 `False`
  - `Get-BackupOpsFileSshRequest -Environment backup` 因 `ValidateSet('production','test')` 直接抛错
  - `Get-BackupOpsRestoreCandidates` 把 `manifest.targetEnvironment=backup` 的候选过滤为 `0`

## Root Cause

- `FileOps.psm1`
  - `Get-BackupOpsFileSshRequest` 的 `Environment` 参数只允许 `production,test`
  - `Get-BackupOpsExpectedBackupTargetHost` / `Assert-BackupOpsKnownBackupTarget` 未纳入 `backup`
- `DockerOps.psm1`
  - `Get-BackupOpsRestoreCandidates` 与 `Get-BackupOpsRehearsalCandidate` 只接受 `manifest.targetEnvironment=test && targetHost=172.30.30.58`
- `ObjectOps.psm1`
  - 对象恢复 stage 只允许 `/mnt/nas/Backup/BackupPackage/.restore-stage/...`
  - 对象 inventory 回放只接受 `/mnt/nas/Backup/BackupPackage/object-store`
  - 这会导致 backup 环境 `/mnt/intruoyi-data/Backup/BackupPackage` 生成的可恢复对象仓库在恢复阶段被误判非法
  - `Get-BackupOpsMinioCredentials` 参数仍只允许 `production,test`，真实 `backup-now` 无法读取备份服 MinIO 凭据
- `DccBackupChainValidator.psm1`
  - DCC 恢复链校验仍硬编码只接受 `targetEnvironment=test`，导致 backup manifest 在恢复演练前置校验中被误判非法
- `MySqlOps.psm1` / `DockerOps.psm1`
  - rehearsal config 把 `environment` 改为 `rehearsal` 后丢失原始 `backup` 仓库环境证明，MySQL 恢复默认期待测试服 `172.30.30.58`
- `UseCases/Rehearsal.psm1`
  - 恢复演练证据写回仍硬编码 `servers.test`，导致已通过的 backup rehearsal 把 `现场快照.md` 上传到 `172.30.30.58:/mnt/nas/...`
- 备份服测试租户数据
  - `tenant_id=122` 中 96 条 `CODEX-E2E-T4-*` active DCC 测试残留记录引用 `/codex-e2e/%` 对象，但对象 inventory 中不存在这些对象，DCC manifest gate 正确阻断备份

## Regression Test

- 新增：`ops/backup-ops/tests/BackupTargetEnvironment.Tests.ps1`
- 覆盖点：
  - `backup` 目标证明
  - `FileOps` 的 `backup` SSH 请求解析
  - `DockerOps` 对 `manifest.targetEnvironment=backup` 候选的保留行为
  - `ObjectOps` 对 backup 数据盘 restore stage 和 object-store 的恢复回放规划
  - `ObjectOps` 对 backup MinIO 凭据读取
  - DCC backup manifest 能被 chain validator 接受为 `backup/172.30.30.59`
  - rehearsal MySQL restore 保留 backup 仓库环境证明
  - rehearsal evidence 写回 backup 仓库而不是测试服

## RED

- RED: `Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests\BackupTargetEnvironment.Tests.ps1 -EnableExit` -> FAIL，3 个用例全部失败，证明 `backup` 环境契约未实现。
- RED: `Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests\BackupTargetEnvironment.Tests.ps1 -EnableExit` -> FAIL，新增对象恢复回归后 2 个用例失败，证明对象恢复仍只接受测试服 NAS 根。
- RED: `backup-now -TargetEnvironment backup -NonInteractive` -> FAIL，备份点 `20260621-185935` 在读取 MinIO 凭据前被 `ValidateSet('production','test')` 阻断。
- RED: `backup-now -TargetEnvironment backup -NonInteractive` -> BLOCKED，备份点 `20260621-191229` 被 DCC manifest gate 阻断，96 条 active DCC 测试残留记录引用缺失对象。
- RED: `rehearsal -TargetEnvironment backup -SelectedBackupId 20260621-202814` -> BLOCKED，DCC chain validator 不接受 `targetEnvironment=backup`。
- RED: `rehearsal -TargetEnvironment backup -SelectedBackupId 20260621-202814` -> BLOCKED，MySQL rehearsal restore 把 backup 仓库主机误判为测试服主机错配。
- RED: `rehearsal -TargetEnvironment backup -SelectedBackupId 20260621-202814` -> FAIL，核心演练校验通过后 evidence 写回错误上传到测试服路径。

## GREEN

- GREEN: `Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests\BackupTargetEnvironment.Tests.ps1 -EnableExit` -> PASS，12 个 targeted 用例全部通过。
- GREEN: `Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests -EnableExit` -> PASS，13 个本地回归全部通过。
- GREEN: `backup-now -TargetEnvironment backup -NonInteractive` -> PASS，备份点 `20260621-202814` 成功生成完整产物。
- GREEN: `rehearsal -TargetEnvironment backup -SelectedBackupId 20260621-202814` -> PASS，恢复演练完成并写入 `rehearsalStatus=PASSED`。
- GREEN: `restore-data -TargetEnvironment backup -SelectedBackupId 20260621-202814 -NonInteractive` -> PASS，真实恢复完成且备份服健康检查通过。

## Verification

- `python -X utf8 C:\Users\BJB110\.codex\skills\bug-regression-fix-loop\scripts\validate_bug_regression.py --evidence D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-backup-server-backup-restore-rehearsal\bug-regression-evidence.md` -> PASS。
- `Invoke-Pester -Path D:\ProjectPackage\Int\IntRuoyiMaintance\ops\backup-ops\tests -EnableExit` -> PASS，13/13。

## Blockers

- 当前无未解决阻塞。

## Risk / Regression Scope

- 当前已修复 backup 环境在 `FileOps`、`DockerOps`、`ObjectOps`、`MySqlOps`、`DccBackupManifestBuilder`、`DccDatabaseSnapshotExporter`、`DccBackupChainValidator`、`UseCases/Rehearsal` 的关键契约。
- 备份服测试租户 96 条历史 E2E 残留 DCC 主记录已软删除；这是对不可恢复 active 记录的数据一致性治理，不是绕过 manifest gate。

## Follow-up

- 后续应补一个专用的 DCC 测试残留巡检/清理任务，避免历史 E2E 数据再次污染全量备份 gate。
- 后续可优化对象恢复耗时；本次保持完整真实对象回放，未引入跳过或降级。
