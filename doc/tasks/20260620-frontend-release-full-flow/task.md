# 任务：前端页面走完整构建发布测试服/正式服/备份服全流程

## 任务目标

严格使用运行控制台前端页面，真实执行一次“构建发布包 -> 发布测试服务器 -> 发布正式服务器 -> 发布备份服务器”的全流程。过程中禁止用接口替代页面提交；如页面链路或后台链路出现问题，必须先记录到任务文档，修复后继续从页面重走，直到整条链路可以一次性走通。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260620-fupan-prod-release-v7\task.md`
- 状态：`COMPLETED`
- 处理：上一任务只做复盘与短记忆更新，不存在未收尾发布阻塞；本任务作为新的真实页面发布演练单独建档。

## 用户要求与执行边界

- 用户要求：
  - 正式走一遍构建发布到测试服务器、发布到正式服务器、发布到备份服务器的全流程
  - 必须使用页面前端进行操作
  - 禁止直接调用接口替代页面
  - 遇到问题先记录、修复后继续，直到全流程一次性走通
- 本任务边界：
  - 可使用本机终端做只读核验、日志排障、代码修复和必要重启
  - 不得用接口直接提交 build/deploy 动作替代页面按钮
  - 涉及真实服务器写入前，必须先在 `execution-log.md` 记录 `GREEN: experience-preflight -> PASS`

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 构建发布包必须通过运行控制台页面按钮提交，不得命令行替代页面产出正式候选包。
  - 发布验证不能只看健康检查，必须同时核 operation、manifest、远端 `IMAGE_TAG`/镜像、迁移状态和真实页面入口。
  - 正式环境发布前必须先补齐目标环境只读 preflight 证据并校验版本一致；缺证据或存在写动作直接阻塞。
  - 备份服必须显式使用 `/mnt/intruoyi-data` 相关参数，不得回退到 `/var/lib/docker` 默认路径。
  - 遇到发布链问题要先记录完整失败，再统一修复并重新从页面重走。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。所有页面链路阻塞都以正式修复运行控制台/发布脚本/契约为目标，不靠接口绕过完成。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 页面真实提交发布全链路 -> Given 运行控制台前端可访问 / When 用户在页面上依次执行构建发布包、发布测试服、发布正式服、发布备份服 / Then 每一步都必须由真实页面动作触发并最终成功。`
- `BDD: 页面链路失败必须记录并修复后重走 -> Given 任一步页面提交或后台执行失败 / When 排查和修复问题 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整流程直到一次性通过。`

## 里程碑

1. 建立任务文档并确认页面入口、经验门禁与高风险动作前置。`DONE`
2. 通过页面真实执行构建发布包并完成候选包核验。`DONE`
3. 通过页面真实发布测试服并验证成功。`DONE`
4. 通过页面真实发布正式服并验证成功。`DONE`
5. 通过页面真实发布备份服并验证成功。`DONE`
6. 汇总全流程问题、修复与最终一次性走通证据。`DONE`

## 预期验证

- `execution-log.md` 中存在 `GREEN: experience-preflight -> PASS`
- 运行控制台页面真实产生 build/deploy operation，且每一步均有成功证据
- 测试服/正式服/备份服远端 `.env` 与运行镜像 `IMAGE_TAG` 和页面选择的 `releaseTag` 一致
- 正式服 `website` 数据边界未被破坏
- 遇到的每个问题都有失败记录、根因修复记录和重跑结果

## 当前状态

IN_PROGRESS：已确认旧 tag `release-20260620-page-full-flow-v1` 的页面链路虽然曾跑通到“标记测试通过”，但用于正式服 dry-run 的本地缓存目录后来被同名后端单测夹具污染，因此必须改用新 tag `release-20260621-page-full-flow-v2` 从页面整条重跑。新 tag 首次页面构建 `op-2026-06-20T235144305204100Z-e8b0a823-14ad-4eb0-8f6b-6629f49a1c1b` 已确认因为源码仓 `yudao-server.jar` 被锁而失败；随后已按门禁提示执行 `D:\ProjectPackage\Int\IntRuoyi\restart-ruoyi-backend.bat` 解除该锁，并回到真实页面再次点击“构建发布包”，生成新的 operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea`。
当前新 tag `release-20260621-page-full-flow-v2` 的页面构建 operation `op-2026-06-20T235900978902100Z-cd7053fd-48c2-4f27-ad42-9ac8cf36baea` 已最终 `SUCCESS`，并确认发布包已上传到 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v2`。过程中一度出现“前端 `vite build --mode test` 长时间无新日志”的现象；后续用独立 `vite --debug` 复现核对后，证实它属于高耗时长解析阶段而非永久失败，因此当前不再以“前端构建阻塞”作为主阻塞。
随后在真实页面执行“部署测试服”时，operation `op-2026-06-21T002749215627300Z-ceee763a-3578-4831-8ff5-c075d7295215` 被 required SQL `20260619_srm_d7_2_supplier_access_risk.sql` 阻断，根因已通过严格 TDD 复现并修复：D7-2 SQL 的页面路由幂等守卫把查询按钮误当成页面路由存在证据，导致缺失 `supplier-profile` 路由时跳过插入、随后又被 fail-fast 校验拦住。当前回归测试 `python -X utf8 -m pytest script\tests\test_srm_d7_d10_sql_contract.py -q` 与迁移门禁 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 已全部通过。
当前主阻塞已更新为新的真实页面测试服发布失败：`release-20260621-page-full-flow-v3` 的真实页面构建 operation `op-2026-06-21T024523486951200Z-fc58e07c-db7d-4604-8f5a-3539af0ad13d` 已最终 `SUCCESS`，并确认发布包已上传到 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v3`。随后回到真实页面执行“部署测试服”，operation `op-2026-06-21T030252892482500Z-0cf0dc70-5cbe-48bd-8d3c-740fbc777f96` 先成功执行 `20260619_srm_d7_2_supplier_access_risk.sql`，但在 required SQL `20260620_srm_phase1_supplier_access_profile.sql` 阶段失败：测试服真实 MySQL 返回 `ERROR 1064 (42000) ... near 'IF NOT EXISTS \`portal_contact_name\` varchar(64) ...'`。这说明当前阻塞根因不是页面提交流程，也不是上一轮 D7-2 修复未进包，而是 `20260620_srm_phase1_supplier_access_profile.sql` 直接采用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，与真实发布目标库的语法契约不兼容。下一步必须先按严格 TDD 修复该 SQL 的正式幂等写法，再重新从真实页面重走“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”。
现已在源码仓按严格 TDD 完成该阻塞修复：`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\tests\test_srm_phase1_schema_sql.py -q` 已 `10 passed`，`python -X utf8 D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 已 `status=passed`。随后已通过真实页面重新构建新 release tag `release-20260621-page-full-flow-v4`，operation `op-2026-06-21T033855757114300Z-eeb75421-362d-407a-82b3-b0887b4491e0` 已最终 `SUCCESS`，并确认本地发布目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v4` 与 NAS `Backup/ReleasePackage/release-20260621-page-full-flow-v4` 都已生成完整候选包。
当前 `release-20260621-page-full-flow-v4` 的真实页面测试服部署 operation `op-2026-06-21T035603828833Z-c1598389-017f-4d4e-8c9c-43fb3fea82e5` 也已最终 `SUCCESS`：本机 operation log 已确认 required SQL、远端 schema 检查、`backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 核对与发布锁释放全部通过；随后只读核对测试服 `/opt/intruoyi/runtime/.env`、运行容器镜像以及 `48081/8081/pdf.worker` 入口，均与 `release-20260621-page-full-flow-v4` 一致。因此当前待执行动作已推进为：必须在同一真实页面链路继续“标记测试通过 -> 上线正式服 -> 上线备份服”。
随后已在同一真实页面链路完成“标记测试通过”：Playwright 通过页面表单真实选择恢复点 `20260621-063218 · AVAILABLE`、预览确认 `-Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v4 -SelectedRecoverySetCandidateId restore:20260621-063218` 后点击执行，生成 operation `op-2026-06-21T041405918994500Z-24330a04-ecfe-4786-8a55-8c95fc0e1f18`。只读核对状态文件与本机 log 后确认该 operation 已 `SUCCESS`，`release-20260621-page-full-flow-v4` 已被真实标记为测试通过。当前待执行动作继续推进为：必须在同一真实页面链路执行“上线正式服 -> 上线备份服”，并在每次新阻塞出现时先补执行日志再修复重走。
当前新的真实页面主阻塞已经通过严格 TDD 收口：此前 Playwright 在“上线正式服”点击“预览命令”时，页面直接返回 `正式 deploy precheck report-only 失败`，证据文件为 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v4-deploy-precheck-report.json`。进一步核对已确认根因不是 build-release 时 manifest 漏写，而是 `RuntimeControlService#generateProdDryRunEvidence` 直接复用了 `local-cache/publish-int-ruoyi/<releaseTag>` 本地缓存目录；该目录在真实页面测试服部署后已被写入 `.env`、`post-import.sql`、`ops-runtime/`、`preflight-plan.json`、`preflight-target-state-test.json` 等运行期工件，导致正式 `report-only` 把这些部署期脏文件误判为“原始发布包未声明文件”。现已在维护仓后端完成正式 dry-run 隔离工作区修复，并通过 `RuntimeControlOriginalParityTest#promoteProdPreviewUsesSanitizedPackageWorkspace` 的 RED/GREEN 回归及整套 `RuntimeControlOriginalParityTest`。随后已重建本地维护控制台并回到同一真实页面链路继续重试“上线正式服”，页面预览与提交都已恢复可用，真实 operation `op-2026-06-21T050013146743700Z-46beb4fb-5f6c-4d2a-ba1c-4f1171a3f54b` 已成功由页面点击生成。
当前阻塞已在代码层收口：源码仓 `20260621-release-preflight-environment-contract` 已按严格 TDD 完成正式修复，维护仓真实运行脚本也已同步。修复内容包括：非目标环境迁移改为 `SKIP_ENV_NOT_ALLOWED`、dependency allowedEnvironments 必须是父迁移环境集合的子集、build-release 统一打包跨环境 required SQL、deploy-release 改为从包内 `manifest.json` 读回真实 `allowedEnvironments`。相关回归命令 `test_release_preflight_plan.py`、`test_release_deploy_executor.py`、`test_release_migration_policy_gate.py`、`test_publish_int_ruoyi_to_test_tooling.py` 与真实 SQL 树 migration policy gate 均已通过。
下一步必须回到真实页面，从新的 release tag 重新执行 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`，以“修复后的单次完整链路”作为本任务最终完成证据；当前不能再把旧的 `release-20260621-page-full-flow-v4` 当作修复后全链路一次性走通的验收依据。
现已补读 `login-access.md`，并重新确认 `npx`、本机运行控制台 `http://127.0.0.1:48181/` 与 Playwright 会话 `frontend-release-full-flow` 仍可用。随后已在真实页面切回“构建发布包”，预览确认 `-Mode build-release -ReleaseTag release-20260621-page-full-flow-v5 -Component intruoyi -SkipDatabaseSync -SkipMinioSync ...` 参数正确，并点击“执行”生成 operation `op-2026-06-21T063453670081300Z-d06ecbd1-508c-4014-a2fc-eb97e0b749e6`。该 operation 现已最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v5` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-v5.tar`，页面顶部操作记录也已刷新为 `SUCCESS / 命令执行完成`。当前下一步为继续在同一真实页面链路切到“部署测试服”，验证 `v5` 能否顺利进入测试环境。
现已在同一真实页面链路继续执行“部署测试服”：Playwright 预览确认 `targetEnvironment=test`、`releaseTag=release-20260621-page-full-flow-v5` 后点击“执行”，生成 operation `op-2026-06-21T065051239510Z-922f4185-63ef-4e8b-9045-210a4298d355`。只读轮询状态文件与本机 log 后确认该 operation 已最终 `SUCCESS`；日志显示远端 required SQL、Quartz/showroom schema 检查、`backend/frontend` 容器重建、scheduler smoke runtime 核对、发布锁释放与远端临时文件清理全部通过。随后再次只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env`、运行容器镜像与 `48081/8081/pdf.worker` 入口，均与 `release-20260621-page-full-flow-v5` 一致。因此当前真实页面链路已推进到：继续在同一会话执行“标记测试通过 -> 上线正式服 -> 上线备份服”，以 `v5` 作为修复后单次完整走通证据。
现已在同一真实页面链路完成“标记测试通过”：Playwright 通过页面表单真实填写原因“页面真实发布全链路验证：标记测试通过（v5）”、验证结论“回归通过，允许上线正式服（v5）”，并从页面恢复点下拉真实选中 `20260621-063218 · AVAILABLE`。预览弹窗确认本次将执行 `-Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v5 -SelectedRecoverySetCandidateId restore:20260621-063218` 后点击“执行”，生成 operation `op-2026-06-21T070744282571900Z-f9bdfe1e-7382-4a1d-979f-da8fc18335e5`。只读核对状态文件与本机 log 后确认该 operation 已 `SUCCESS`，并已把 `release-20260621-page-full-flow-v5` 真实标记为测试通过，同时写入 `rollback-compatibility.json status=BLOCKED` 元数据。当前下一步为继续在同一真实页面链路执行“上线正式服 -> 上线备份服”。
现已在同一真实页面链路尝试“上线正式服（v5）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-v5 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v5-preflight-release-dry-run.json ...`，随后点击“执行”生成 operation `op-2026-06-21T071527391565200Z-43bbbf19-75ce-473f-9747-5693c04947ff`。只读核对状态文件、本机 log 与 `release-20260621-page-full-flow-v5-preflight-release-dry-run.json` 后确认：本次失败不是正式 dry-run 证据缺失，也不是 releaseTag 未测试通过；dry-run 证据本身仍为 `status=passed`。实际执行在完成 target-bound `post-import.sql`、引导 `infra_release_migration/infra_release_operation_lock` 状态表后，于获取正式服发布锁阶段失败。
进一步只读查询正式库 `infra_release_operation_lock` 后确认，当前 `target_environment='prod'` 仅存在 1 条锁记录，且仍停留在旧链路 `operation_id=prod-release-20260621-page-full-flow-v4`、`release_tag=release-20260621-page-full-flow-v4`、`status=RUNNING`、`started_at=2026-06-21 13:04:44`、`finished_at=NULL`。这导致新的 `prod-release-20260621-page-full-flow-v5` 无法得到 `LOCK_ACQUIRED`，最终以 `命令退出码非 0: 1` 失败。当前新的正式服主阻塞已经收敛为“旧 v4 失败链路残留 prod 发布锁未释放”；下一步必须先按严格 TDD 修复正式服发布锁生命周期并清理该陈旧锁，再回到真实页面继续“上线正式服 -> 上线备份服”。若修复仅涉及维护控制台/发布脚本而不改变发布包内容，则继续以 `release-20260621-page-full-flow-v5` 作为同一页面链路的候选包重试。
现已按严格 TDD 收口正式服残留锁问题：在 `D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py` 先新增“持锁后 fail-fast 也必须释放发布锁”的回归用例，`python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_publish_release_lock_cleanup.py -q` 先稳定 `2 failed` 复现；随后在 `D:\ProjectPackage\Int\IntRuoyiMaintance\ops\deploy\publish-int-ruoyi.ps1` 修复 `Fail()` 路径，使其在已持锁时先调用 `Invoke-ReleaseOperationLockRelease -Status 'FAILED'` 再退出，并补上脚本级锁持有/释放状态位保护。修复后同一回归已 `PASS`，联同 `test_release_package_slimming.py`、`test_scheduler_smoke_release_config.py`、`test_showroom_release_sql_contract.py` 的相关回归一并 `10 passed`。随后只读确认当前无活动中的同类本地发布进程后，已将正式库残留锁 `prod-release-20260621-page-full-flow-v4` 从 `RUNNING` 手动收口为 `FAILED`，并记录 `error_message='manual stale-lock cleanup after release lock fail-fast bug fix for page-flow v5'`，从而为同一真实页面链路的正式服重试清空阻塞。
清理陈旧锁后，已回到同一真实页面会话继续“上线正式服（v5）”并再次点击预览/执行，生成新的真实 operation `op-2026-06-21T073844572460600Z-694fba69-6b1c-4507-994e-9aac8f490123`。只读轮询状态文件与本机 log 后确认：该 operation 已真实完成生产包同步、required SQL 登记/执行、Quartz/showroom schema 检查、`backend/frontend` 容器重建、远端 readiness、scheduler smoke runtime 核对、NAS 发布历史写入、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。随后再次只读核对正式服 `172.30.30.57` 的 `/opt/intruoyi/runtime/.env`、运行容器镜像、`48081/8081/pdf.worker` 入口以及展厅受保护边界，结果分别为 `IMAGE_TAG=release-20260621-page-full-flow-v5`、`intruoyi-backend/intruoyi-frontend` 都运行在 `release-20260621-page-full-flow-v5`、三条 HTTP 入口均返回 `200`、`config_id=28 AND path LIKE 'showroom/%'` 下 `url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0` 且 `url LIKE 'http://172.30.30.57:9000/yudao/%'` 的受保护记录数为 `1434`。因此当前里程碑已推进为：正式服真实页面发布和只读核验均已完成，下一步继续在同一真实页面链路执行“上线备份服”，随后汇总 `v5` 的整条一次性走通证据。
现已在同一真实页面链路尝试“上线备份服（v5）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment backup -ReleaseTag release-20260621-page-full-flow-v5 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home ...`，随后点击“执行”生成 operation `op-2026-06-21T075931265053700Z-7d81cab2-c347-4f49-8618-1427c837cf2f`。只读轮询状态文件与本机 log 后确认，该 operation 在备份服 required SQL `20260618_post_release_role_e2e_gate.sql` 阶段失败：远端 MySQL 返回 `ERROR 1644 (45000) ... Missing enabled scheduler role; cannot prepare zhaojie smart scheduling E2E account`，随后发布锁已按修复后的生命周期收口为 `FAILED`。这说明当前新的主阻塞不是页面提交、不是发布锁残留，也不是 `release-20260621-page-full-flow-v5` 包在测试/正式环境下不可用，而是备份服在执行 post-release E2E gate 迁移时缺少“enabled scheduler role”前置条件，或该迁移对备份环境的 fail-fast 契约本身存在设计缺陷。下一步必须先把该阻塞按严格 TDD/缺陷合同收口清楚，再回到真实页面继续“上线备份服”，以拿到单次完整链路最终成功证据。
现已在业务源码仓 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro` 按严格 TDD 收口该阻塞：新任务 `doc/tasks/20260621-post-release-role-e2e-gate-backup-scheduler-role/` 已确认根因是 `20260618_post_release_role_e2e_gate.sql` 默认 `tenant_id=1 / 芋道源码` 预先存在启用中的排产员角色，而备份服真实基线只有 `showroom_publicity` 与 `wenkong`。修复后该 SQL 会在缺角色时正式插入新的 `排产员` 角色，在命中历史角色时统一启用并继续复用；相关 `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q`、`python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_mes_scheduler_role_smart_scheduling_tab_sql.py -q` 与 `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` 均已通过。由于本次修复改变了业务仓发布输入，当前 `release-20260621-page-full-flow-v5` 包不包含该 SQL 变更，不能继续拿它重试备份服；下一步必须回到真实页面，用新的 release tag 从“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”整链重走，新的单次链路成功才算本任务完成。
现已按该约束回到同一真实页面会话 `frontend-release-full-flow`，使用新的 release tag `release-20260621-page-full-flow-v6` 重建候选包。页面预览确认本次执行 `publish-int-ruoyi.ps1 -Mode build-release -ReleaseTag release-20260621-page-full-flow-v6 -Component intruoyi -SkipDatabaseSync -SkipMinioSync ...`，随后点击“执行”生成 operation `op-2026-06-21T084758011335300Z-cabf4fb6-0ce0-4f3c-930b-0b6a876caa10`。只读轮询页面、状态文件与本机日志后确认：该 operation 已真实完成 backend `mvn ... clean package`、前端 `vite build --mode test`、backend Docker 镜像构建、迁移 policy gate、NAS 上传等完整链路，并最终收口为 `SUCCESS`。当前本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-v6` 已生成 `manifest.json`、`release-manifest.json`、`intruoyi-images_release-20260621-page-full-flow-v6.tar` 等关键产物，日志也确认 NAS 路径为 `Backup/ReleasePackage/release-20260621-page-full-flow-v6`。因此当前真实页面下一步已推进为：继续在同一会话执行“部署测试服（v6） -> 标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”，以 `v6` 作为修复后单次完整链路的最终验收对象。
现已在同一真实页面链路继续执行“部署测试服（v6）”：Playwright 预览确认 `targetEnvironment=test`、`releaseTag=release-20260621-page-full-flow-v6` 与原因“页面真实发布全链路验证：部署测试服（v6）” 后点击“执行”，生成 operation `op-2026-06-21T090329614747700Z-cf86a6a0-e411-4ce2-a2fa-cdcb10bc2517`。随后只读轮询状态文件与本机 log 后确认该 operation 已最终 `SUCCESS`；日志显示 `20260618_post_release_role_e2e_gate.sql`、`20260621_srm_phase45_simulated_execution.sql` 等 required SQL 已正确 `APPLIED/SKIPPED_ALREADY_APPLIED`，并完成远端 Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、测试服发布锁释放与远端临时文件清理。继续只读核对测试服 `172.30.30.58` 的 `/opt/intruoyi/runtime/.env`、运行镜像与 `48081/8081/pdf.worker` 入口，均与 `release-20260621-page-full-flow-v6` 一致。因此当前真实页面链路已推进到：继续在同一会话执行“标记测试通过（v6） -> 上线正式服（v6） -> 上线备份服（v6）”，以 `v6` 作为修复后单次完整链路的最终验收对象。
现已在同一真实页面链路继续执行“标记测试通过（v6）”：Playwright 在页面真实填写原因“页面真实发布全链路验证：标记测试通过（v6）”、验证结论“回归通过，允许上线正式服（v6）”，并从恢复点下拉真实选中 `20260621-063218 · AVAILABLE`。预览弹窗确认将执行 `publish-int-ruoyi.ps1 -Mode mark-tested -ReleaseTag release-20260621-page-full-flow-v6 -TestConclusion 回归通过，允许上线正式服（v6） -SelectedRecoverySetCandidateId restore:20260621-063218 ...`，随后点击“执行”生成 operation `op-2026-06-21T091823235755100Z-c8d2d09d-d2a8-4982-952b-366613690af2`。只读轮询状态文件与本机 log 后确认该 operation 已 `SUCCESS`，并把 `release-20260621-page-full-flow-v6` 真实标记为测试通过，同时写入 `rollback-compatibility.json status=BLOCKED` 元数据。因此当前真实页面下一步已推进为：继续在同一会话执行“上线正式服（v6） -> 上线备份服（v6）”，以 `v6` 作为修复后单次完整链路的最终验收对象。
现已在同一真实页面链路继续执行“上线正式服（v6）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment prod -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ProdDryRunEvidencePath D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\prod-preflight-release-evidence\release-20260621-page-full-flow-v6-preflight-release-dry-run.json ...`，随后通过真实弹窗点击“执行”，生成 operation `op-2026-06-21T092843334367500Z-223e010b-722c-4d05-ba35-887515eba339`。只读轮询状态文件与本机 log 后确认：该 operation 已真实完成生产包同步、required SQL 登记/执行、Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、NAS 发布历史写入、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。随后再次只读核对正式服 `172.30.30.57` 的 `/opt/intruoyi/runtime/.env`、运行镜像、`48081/8081/pdf.worker` 入口以及展厅受保护边界；其中运行态分别为 `IMAGE_TAG=release-20260621-page-full-flow-v6`、`intruoyi-backend/intruoyi-frontend` 都运行在 `release-20260621-page-full-flow-v6`、三条 HTTP 入口均返回 `200`。展厅边界核验时先 `DESCRIBE infra_file_config` 确认该表不含 `config_id/path/url`，随后按真实表 `infra_file` 只读查询得到：`config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0`，`url LIKE 'http://172.30.30.57:9000/yudao/%'` 的受保护记录数为 `1434`。因此当前里程碑已推进为：`release-20260621-page-full-flow-v6` 的正式服真实页面发布和只读核验均已完成，下一步继续在同一真实页面链路执行“上线备份服（v6）”，随后汇总单次完整链路证据。
现已在同一真实页面链路继续执行“上线备份服（v6）”：Playwright 先在页面预览确认 `-Mode deploy-release -Environment backup -ReleaseTag release-20260621-page-full-flow-v6 -ConfirmText PROD -RequireTested -ServerHost 172.30.30.59 -RemoteReleaseRoot /mnt/intruoyi-data/intruoyi-releases -RemoteDataRoot /mnt/intruoyi-data/runtime-data -RemoteDataDiskMount /mnt/intruoyi-data -RemoteDataDiskDevice /dev/mapper/cl-home ...`，随后通过真实弹窗点击“执行”，生成 operation `op-2026-06-21T094430298907500Z-870bf604-f8f1-4b4d-a9a8-f193e5d6f9c2`。只读轮询状态文件与本机 log 后确认：该 operation 已真实完成备份服 required SQL 登记/执行、Quartz/showroom schema 检查、`backend/frontend` 容器重建、HTTP readiness、scheduler smoke runtime 核对、NAS 发布历史写入、发布锁释放与远端临时文件清理，最终收口为 `SUCCESS`。此前阻断 `v5` 的 `20260618_post_release_role_e2e_gate.sql` 与其后一组 `post_release_role_e2e_gate_smoke_*` SQL 均已在本轮真实页面链路中正确 `APPLIED`。随后再次只读核对备份服 `172.30.30.59` 的 `/opt/intruoyi/runtime/.env`、运行镜像、`48081/8081/pdf.worker` 入口以及展厅受保护边界；其中运行态分别为 `IMAGE_TAG=release-20260621-page-full-flow-v6`、`intruoyi-backend/intruoyi-frontend` 都运行在 `release-20260621-page-full-flow-v6`、三条 HTTP 入口均返回 `200`，且按真实表 `infra_file` 只读查询得到：`config_id=28 AND path LIKE 'showroom/%' AND url LIKE '%127.0.0.1:9000%'` 的漂移记录数为 `0`，`url LIKE 'http://172.30.30.59:9000/yudao/%'` 的受保护记录数为 `1434`。COMPLETED：`release-20260621-page-full-flow-v6` 已按“页面前端点击操作”的真实流程一次性完整走通 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`，过程中未用接口替代页面提交；本任务所遇阻塞也都已先记录、再修复、再从页面重走，并形成最终通过证据。

## Current Status

COMPLETED：`release-20260621-page-full-flow-v6` 已按真实页面链路一次性完整走通 `构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服`，并已完成测试服、正式服、备份服的只读运行态与受保护边界核验。
