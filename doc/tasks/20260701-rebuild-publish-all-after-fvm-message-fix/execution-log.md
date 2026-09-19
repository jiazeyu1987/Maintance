GREEN: experience-preflight -> PASS，已读取发布经验、发布执行清单、备份恢复基线、服务器访问、登录访问、worktree 与 PowerShell 编码门禁；用户本轮目标为构建并发布到测试服务器、正式服务器、备份服务器，授权范围限定为 ${releaseTag} 全链路发布验证。

BDD: 修复后必须重新构建新 releaseTag -> Given 旧 releaseTag 的正式服 required SQL 因 MESSAGE_TEXT 过长失败 When SQL 修复已提交 Then 必须构建新的 ${releaseTag}，不得继续使用失败旧包。

BDD: 单一 releaseTag 必须完成三环境发布闭环 -> Given ${releaseTag} 构建成功并发布测试服 When 测试服验证通过 Then 才能 mark-tested，并继续发布正式服和备份服。

BDD: 三环境运行态必须与 releaseTag 一致 -> Given 发布 operation 成功 When 验证远端环境 Then .env IMAGE_TAG、backend/frontend 镜像 tag、backend health 与 frontend HTTP 必须全部与 ${releaseTag} 一致。

BLOCKER: publish-test -> FAILED，operation op-2026-07-01T123539876166800Z-15e401f6-1bcc-4206-95eb-fcdc0b969183 未成功；summary=å½ä»¤éåºç é 0: 1。

BLOCKER: build-release -> FAILED，operation op-2026-07-01T125424244352400Z-791fc643-8b32-44bd-aafe-8387ea5765aa 未成功；summary=å½ä»¤éåºç é 0: 1。

GREEN: build-release -> PASS, releaseTag=release-20260701-1720-signal-syntax-fix-v2, operation=op-2026-07-01T130912960979Z-164a68db-fa11-4a87-af88-837528bc54ca, manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260701-1720-signal-syntax-fix-v2\manifest.json, backendCommit=bda2fbe91cb789798a304cdb55de7b021ab4f761, frontendCommit=9662a85e7e54c41cbbc594a843a47dff8d1dfa7f
GREEN: publish-test -> PASS, releaseTag=release-20260701-1720-signal-syntax-fix-v2, operation=op-2026-07-01T132409424788700Z-9463af03-38de-4088-beec-f30c3a96979a, release-status contains tag
GREEN: mark-release-tested -> PASS, releaseTag=release-20260701-1720-signal-syntax-fix-v2, operation=op-2026-07-01T134359041599800Z-7ba0347a-9180-4f11-a05c-e7e84cffdc57, selectedRecoverySetCandidateId=restore:20260621-063218
BLOCKER: promote-prod -> FAIL, releaseTag=release-20260701-1720-signal-syntax-fix-v2, operation=op-2026-07-01T134536550516100Z-98c14c30-4cce-4423-80e0-78db16ffab92, status=FAILED
BLOCKER: promote-prod -> FAIL, releaseTag=release-20260701-1720-signal-syntax-fix-v2, operation=op-2026-07-01T134536550516100Z-98c14c30-4cce-4423-80e0-78db16ffab92, reason=DCC_FILE_VIEW_MATRIX_CATEGORY_PRECHECK_FAILED duplicate categories in prod live data
GREEN: release-worktree-create -> PASS, maintenance=D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260701-2220-category@fb18456ade89c3e07192ba927816f127830e76e0, backend=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260701-2220-category@bf5b04feaa9e2f3ee4c3b67c428c6beff956d794, frontend=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260701-2220-category@5ece14735a23f86fc04a1741156ba4389628532d
GREEN: release-frontend-deps -> PASS, worktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260701-2220-category, command=pnpm install --frozen-lockfile
GREEN: release-backend-pytest -> PASS, worktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260701-2220-category, command=python -m pytest script/tests/test_dcc_view_matrix_message_text_sql.py -q
GREEN: release-backend-migration-gate -> PASS, worktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260701-2220-category, command=python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql
GREEN: runtime-config-update -> PASS, config=D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.yaml, backup=D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.before-category-20260701-221522.yaml, backend=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-2220-category, frontend=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-2220-category
GREEN: runtime-control-restart-preview -> PASS, releaseTag=release-20260701-1720-category-code-fix, preview uses category worktrees
GREEN: build-release -> PASS, releaseTag=release-20260701-1720-category-code-fix, operation=op-2026-07-01T141554926887800Z-52c91cde-25b7-47bc-8be6-95b7e8ab86b6, manifest=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260701-1720-category-code-fix\manifest.json, backendCommit=bf5b04feaa9e2f3ee4c3b67c428c6beff956d794, frontendCommit=5ece14735a23f86fc04a1741156ba4389628532d
GREEN: publish-test -> PASS, releaseTag=release-20260701-1720-category-code-fix, operation=op-2026-07-01T143021322425300Z-60c9139e-96c4-47d5-b448-846de1150f87, testCurrentReleaseTag matched, .env/image/health/frontend verified
GREEN: mark-release-tested -> PASS, releaseTag=release-20260701-1720-category-code-fix, operation=op-2026-07-01T144453007496100Z-fe764743-b08e-4b95-b426-43b5faea5b48, selectedRecoverySetCandidateId=restore:20260621-063218
BLOCKER: promote-prod -> FAIL, releaseTag=release-20260701-1720-category-code-fix, operation=op-2026-07-01T144702130435100Z-d43c35e7-9c79-4128-8059-57f5b619ae4a, status=FAILED

GREEN: release-worktree-create -> PASS, maintenance=D:\ProjectPackage\Int\release-worktrees\IntRuoyiMaintance-20260701-2320-mes-scheduler@fb18456ade89c3e07192ba927816f127830e76e0, backend=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260701-2320-mes-scheduler@ae1d91ebe34c9c1ec1b31a0c3177f633ba3c2821, frontend=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260701-2320-mes-scheduler@5ece14735a23f86fc04a1741156ba4389628532d
GREEN: release-backend-pytest -> PASS, worktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260701-2320-mes-scheduler, command=python -X utf8 -m pytest script/tests/test_mes_smart_scheduling_role_scope_sql.py script/tests/test_mes_smart_scheduling_role_assignment_sql.py -q, result=26 passed
GREEN: release-backend-migration-gate -> PASS, worktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-backend-20260701-2320-mes-scheduler, command=python -X utf8 script/release/run-release-migration-policy-gate.py --sql-root sql/mysql
GREEN: release-frontend-deps -> PASS, worktree=D:\ProjectPackage\Int\release-worktrees\IntRuoyi-frontend-20260701-2320-mes-scheduler, command=pnpm install --frozen-lockfile
GREEN: runtime-config-update -> PASS, config=D:\ProjectPackage\Int\IntRuoyiMaintance\config\runtime-control.local.yaml, backend=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-backend-20260701-2320-mes-scheduler, frontend=D:/ProjectPackage/Int/release-worktrees/IntRuoyi-frontend-20260701-2320-mes-scheduler
BLOCKER: build-release -> FAIL, releaseTag=release-20260701-1720-mes-scheduler-role-fix, operation=op-2026-07-01T150926362509700Z-c52e6e92-5f66-455b-b191-a495be74a809, reason=DCC_OBJECT_SNAPSHOT_MISSING fileId=9198354891784 object=dcc/original/20260609/empty.docx

BDD: DCC 发布对象清单不得包含临时上传表 -> Given dcc_controlled_file_temporary_file 记录的是上传暂存/绑定过程数据 When 构建 with-data 发布包 Then DCC 对象清单只应覆盖正式业务引用表，不能因临时表孤儿或待审草稿对象阻断发布。
RED: python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py -q -> FAIL, expected reason=发布脚本仍从 dcc_controlled_file_temporary_file broad select 收集 storage_file_id。
GREEN: dcc-object-restore-preflight -> PASS, source=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260616-121500-e2e\minio\yudao\dcc\original\{20260609,20260610,20260611}\empty.docx, size=3306, sha256=fd9160a87bcbe94570d998499f1b1ed9b39f381fde1688c2ed2b0b0a6d562bf2, target=local MinIO yudao/dcc/original/{20260609,20260610,20260611}/empty.docx
GREEN: python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py scripts/tests/test_release_package_slimming.py scripts/tests/test_release_sql_preflight_gate.py -q -> PASS, result=16 passed
GREEN: powershell-parse -> PASS, command=[System.Management.Automation.Language.Parser]::ParseFile(ops/deploy/publish-int-ruoyi.ps1)

BLOCKER: build-release -> FAIL, releaseTag=release-20260701-1720-mes-scheduler-dcc-inventory-fix, operation=op-2026-07-01T161418982943200Z-f3a9cdb2-d4e4-4cb2-9671-9e13a9fd9545, reason=DCC_OBJECT_SNAPSHOT_MISSING fileId=9198354894835 object=dcc/original/20260614/QMS文件清单.xlsx
BLOCKER: dcc-full-object-restore-preflight -> FAIL, source=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\20260615-merge-chunk-test-001\minio\yudao\dcc\original\{20260614,20260615}, target=local MinIO yudao/dcc/original/{20260614,20260615}, checked=17935, missing=2, impact=继续构建会再次因缺失 DCC 对象阻塞；后续按 UTF-8 key 精确恢复两个文件后重验。

GREEN: dcc-final-object-restore-preflight -> PASS, source=E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\20260615-merge-chunk-test-001\minio\yudao, restored=dcc/original/20260615/旋转接头 接三通旋塞-I 11105-LJ-601.PDF sha256=8165f67c6e43fc16560bea1b03f7fc5ca3d8ef3014ed668f270be7f6d962c4ac; dcc/original/20260615/胶塞 82041-LJ-108.PDF sha256=823669414fa584cc1453bbb62f48b23159e8fc95f1dfad4eb810a51a85e00299, checked=14165, missing=0

BLOCKER: build-release -> ABORTED, releaseTag=release-20260701-1720-mes-scheduler-dcc-objects-restored, operation=op-2026-07-01T173402387281300Z-afcc65f1-c1cf-4561-af59-b0f391fcba89, reason=local publish process remained RUNNING after DCC package generation and NAS mount log for multiple hours; process killed to prevent indefinite release lock. Impact: release tag abandoned; next attempt requires root-cause fix and a fresh releaseTag.
BDD: NAS release config share authority -> Given runtime-control writes a UTF-8 NAS config containing the Chinese share name, When build-release receives a command-line NasShare value that may be mojibake from process invocation, Then the publish script must keep the UTF-8 config share and must not override it from CLI.
RED: python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py -q -> FAIL, expected reason=Read-NasReleaseConfig still overrides UTF-8 config share from NasShare CLI parameter

GREEN: python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py scripts/tests/test_release_package_slimming.py scripts/tests/test_release_sql_preflight_gate.py -q -> PASS

GREEN: powershell-parse -> PASS, command=[System.Management.Automation.Language.Parser]::ParseFile(ops/deploy/publish-int-ruoyi.ps1)

GREEN: build-release-start -> PASS, releaseTag=release-20260701-1720-mes-scheduler-nas-config-fix, operation=op-2026-07-01T213950557605Z-849f65ae-408d-462e-b49b-223ad200348d

BLOCKER: build-release -> ABORTED, releaseTag=release-20260701-1720-mes-scheduler-nas-config-fix, operation=op-2026-07-01T213950557605Z-849f65ae-408d-462e-b49b-223ad200348d, reason=process idle after DCC object inventory start with no manifest/inventory output and stale log ageSeconds=324. Impact: release tag abandoned; requires DCC inventory performance/root-cause fix and new releaseTag.

BDD: DCC object inventory must finish for large release snapshots -> Given with-data release snapshot contains thousands of DCC file references, When build-release generates manifest/dcc-object-inventory.json, Then the script must use linear append collections and emit progress so inventory generation cannot silently appear stuck after the start marker.
RED: python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py -q -> FAIL, expected reason=DCC inventory uses PowerShell array += without progress logging

GREEN: python -X utf8 -m pytest scripts/tests/test_publish_dcc_codex_runtime_contract.py scripts/tests/test_release_package_slimming.py scripts/tests/test_release_sql_preflight_gate.py -q -> PASS

GREEN: powershell-parse -> PASS, command=[System.Management.Automation.Language.Parser]::ParseFile(ops/deploy/publish-int-ruoyi.ps1)

GREEN: build-release-start -> PASS, releaseTag=release-20260701-1720-mes-scheduler-dcc-inventory-fast, operation=op-2026-07-01T221723175750800Z-10540648-baef-461d-a1c6-39667c8aec6c
