# Verification Report

## Reviewer Conclusion

GO

## Summary

- 正式 `backup-now` 已成功：`backupId=20260724-030845`，`status=success`，`code=INTBK-0000`，report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_030844_backup-now_success.report.md`。
- 备份服隔离 `rehearsal` 已成功：使用同一 `backupId=20260724-030845`，`status=success`，`code=INTBK-0000`，report=`D:\IntRuoyi-BackupOps\logs\202607\20260724_033419_rehearsal_success.report.md`。
- 未执行 `restore-data -TargetEnvironment backup`；未覆盖备份服正常 MySQL、正常 `yudao` bucket 或正常 runtime；未重启、发布、回滚、删除文件、手工修改 manifest 或复用旧失败 `backupId`。

## Requirement Checklist

- `backup-now status=success code=INTBK-0000`：PASS。
- 同一 `backupId` 产物完整：PASS，本机与备份服仓库均存在非空 `manifest/manifest.json`、`manifest/checksums.txt`、MySQL dump、对象 inventory、DCC manifest、`deploy/runtime.env`、`deploy/image-tag.txt`。
- manifest `imageTag` 匹配正式服实测：PASS，均为 `release-20260723-intmain-codeonly-three-env-r260723s-r1`。
- 备份服隔离 rehearsal 四项校验：PASS，`backendHealth=pass`、`frontendHttp200=pass`、`loginReachable=pass`、`fileDownloadSample=pass`。
- manifest / rehearsal 状态枚举一致：PASS，远端 manifest 写回 `validation.rehearsalStatus=PASSED`，`rehearsal-report.json` 写入 `status=PASSED`，未发现 `verified/PASSED` 写入冲突。
- Reviewer 结论：GO。

## Evidence

- 正式备份报告：`D:\IntRuoyi-BackupOps\logs\202607\20260724_030844_backup-now_success.report.json` 显示 `status=success`、`backupId=20260724-030845`。
- 本机备份产物：`D:\IntRuoyi-BackupOps\tmp\20260724-030845` 下 manifest 15,857,625 bytes、checksums 368 bytes、MySQL dump 6,080,022,752 bytes、对象 inventory 15,854,307 bytes、DCC manifest 8,765,072 bytes、runtime env 3,625 bytes、image tag 57 bytes。
- manifest 摘要：`recoverySet.status=COMPLETE`，对象清单 44,207 项，DCC manifest `status=success`，`manifest/checksums.txt` SHA256 与 manifest `recoverySet.checksums.sha256=58744d240fe7c8bbdd6fbb9946d377b0c45bb2e25226d38d2fcb4ee7c8492faa` 一致。
- 备份服仓库：`/mnt/intruoyi-data/Backup/BackupPackage/20260724-030845` 下关键产物均存在且非空，演练前候选状态为 `success`、`rehearsalStatus=unverified`。
- 演练报告：`D:\IntRuoyi-BackupOps\logs\202607\20260724_033419_rehearsal_success.report.json` 显示 `status=success` 且四项 checks 全 pass。
- 演练证据：本地 `ops/backup-ops/tmp/rehearsal/20260724-030845/evidence/rehearsal-report.json` 594 bytes、`现场快照.md` 315 bytes；远端 manifest 目录同名 evidence 文件非空。
- 远端 manifest 写回：备份服仓库 manifest `validation.rehearsalStatus=PASSED`，`lastRehearsedAt=2026-07-24T04:10:18.3602097+08:00`。
- 正常 runtime 状态：备份服正常 `intruoyi-backend`、`intruoyi-frontend` 仍在同一 release tag 下运行约 25 小时，正常 frontend HTTP 200；隔离演练容器为 `intruoyi-rehearsal-*`，端口 `48082/18081`。

## Residual Notes

- 本轮为可回滚生产数据最小修复后完成备份：96 条历史同清单 `CODEX-E2E` 测试残留 DCC 主记录已按授权软删除，并保留回滚 SQL `doc/tasks/20260723-prod-backup-rehearsal/evidence/prod-dcc-codex-e2e-before-20260724-rollback.sql`。
- 历史失败 `backupId=20260724-004458`、`20260724-005414`、`20260724-013816`、`20260724-023840` 均不是完整可用备份点，不得用于 rehearsal 或 restore。
