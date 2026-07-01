GREEN: experience-preflight -> PASS，已读取发布经验、发布执行清单、备份恢复基线、服务器访问、登录访问与 PowerShell 编码门禁；用户本轮明确要求发布正式服和备份服，授权范围限定为 `release-20260701-1720-current` 的 `mark-tested -> promote-prod -> promote-backup`。

BDD: 只有测试服成功的 releaseTag 才能继续上线 -> Given `release-20260701-1720-current` 已完成测试服发布并通过运行态验证 When 用户要求发布正式服和备份服 Then 必须先执行 `mark-tested`，再按同一 releaseTag 发布正式服和备份服。

BDD: 正式服和备份服运行态必须与 releaseTag 一致 -> Given 发布 operation 成功 When 验证远端环境 Then `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health 与 frontend HTTP 必须全部与 `release-20260701-1720-current` 一致。

GREEN: pre-promote-release-evidence -> PASS，已复核 releaseTag=release-20260701-1720-current 的 build-release 与 publish-test operation 均为 SUCCESS，manifest sourceRepos dirty=false，测试服 .env、backend/frontend 镜像、后端 health 与前端 HTTP 均与 releaseTag 一致。

BLOCKER: promote-prod-required-sql-message-text-too-long -> 正式服发布 operation op-2026-07-01T114634769559Z-27398231-9d1e-49dd-b12f-7ade558e4e1a 失败；失败点为 required SQL 20260613_dcc_file_view_matrix_seed.sql，MySQL 返回 ERROR 1648 (HY000) at line 496: Data too long for condition item 'MESSAGE_TEXT'。发布锁已释放为 FAILED。按发布规则，正式服未完成，禁止继续备份服发布，需先修复该 SQL 的 MESSAGE_TEXT 过长契约并重新构建/发布同一流程。

BLOCKER: stop-before-backup -> 正式服 promote-prod 未成功，按 release-agent-checklist 与 release-backup-restore 门禁，禁止继续 promote-backup；本轮停止在正式服 required SQL 失败点，等待修复 20260613_dcc_file_view_matrix_seed.sql。
