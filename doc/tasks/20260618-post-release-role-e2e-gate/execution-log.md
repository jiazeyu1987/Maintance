# 发布后测试服三角色真实 E2E 验收执行日志

BDD: gaomin 展厅角色验收 -> Given 测试服发布完成且 gaomin 登录芋道源码租户 / When 打开管理前端 / Then 只看到展厅页签，并且展厅每个子页签访问无页面错误、网络错误或控制台错误。
BDD: zhaojie 智能排产角色验收 -> Given 测试服发布完成且 zhaojie 登录芋道源码租户 / When 打开管理前端并进入智能排产 / Then 只看到智能排产页签，并且智能排产冒烟测试可运行直到结束。
BDD: wangsiyu DCC角色验收 -> Given 测试服发布完成且 wangsiyu 登录芋道源码租户 / When 打开管理前端 / Then 只看到DCC文控中心页签，并且DCC文控中心每个子页签访问无页面错误、网络错误或控制台错误。
BDD: 失败统一修复发布复测 -> Given 三角色验收发现错误 / When 全部错误记录完成 / Then 统一修复、重新构建发布到测试服并完整复测三角色，直到全部通过。

- 用户需求：发布后在测试服务器按 `gaomin`、`zhaojie`、`wangsiyu` 三个芋道源码租户账号完成权限页签与页面访问验收；失败先统一记录，全部跑完后统一修复、构建发布、部署测试服并复测到通过。
- GREEN: experience-preflight -> PASS，已读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`docs/agent-memory/project-error-prevention.md`；用户本次明确授权测试服真实登录 E2E，范围仅限 `172.30.30.58` 和三个指定账号。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，首次脚本未收敛权限接口等待异常；修正后继续。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，真实测试服 E2E 证据 `evidence/post-release-role-e2e-1781790390014.json`：`gaomin` 登录业务码 500，后端日志为账号密码不正确；`zhaojie` 顶层菜单为 `MES 系统` 且缺 `智能排产` 根页签；`wangsiyu` DCC 审批任务页 BPM 待办接口 `Access Denied`。
- GREEN: root-cause-readonly-db -> PASS，只读核对测试服：`gaomin` 在 `芋道源码(tenant_id=1)` 缺用户记录；`zhaojie` 绑定排产员角色但角色菜单仍有 `MES 系统(5100)`，`智能排产(900120)` 的 `parent_id=5100`；`wangsiyu` 绑定 `wenkong` 角色但缺 `bpm:task:query` 权限菜单 `1221`。
- BDD: 发布后角色 E2E 数据契约 -> Given 测试服需要用 `芋道源码` 下 `gaomin/zhaojie/wangsiyu` 做真实发布后验收 / When 发布迁移执行 / Then 三个账号均可用 `111111` 登录，且展厅/智能排产/DCC 文控角色只暴露目标页签并具备目标页面读取所需权限。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，3 passed。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=151`，包含 `20260618_post_release_role_e2e_gate`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781797026325.json`：`gaomin` 展厅公司页图片 `/admin-api/infra/file/28/get/20260521/开园活动图-压缩版.jpg` 返回非图片；展厅产品页缺表 `showroom_product_revision_attachment`；展厅大厅页缺字段 `showroom_hall.canvas_background_image_url`；`zhaojie` 生产排产页缺 `mes:pro-work-order:query` 权限，智能排产冒烟缺 `MES_SMOKE_CAPACITY_MODE` 等必填运行变量。
- GREEN: root-cause-readonly-db -> PASS，测试服只读核对：`sql/showroom/20260605_showroom_product_revision_attachment_schema.sql` 和 `sql/showroom/20260615_showroom_hall_canvas_background.sql` 未纳入发布 required SQL；`publish-int-ruoyi.ps1` 的 smoke env 默认值为空；`ragflow_compose-minio-1` 缺少 `20260521/开园活动图-压缩版.jpg`，本机源 `docker-minio-1` 存在该对象。
- BDD: 展厅运行态 schema 发布契约 -> Given 代码已访问展厅产品附件表和大厅背景字段 / When 构建发布包并部署测试服 / Then required SQL 必须包含对应 showroom schema，部署后端启动前 preflight 缺表或缺字段必须 fail fast。
- BDD: 智能排产冒烟发布契约 -> Given zhaojie 触发真实智能排产冒烟 / When 发布脚本写入测试服运行 `.env` 并应用权限迁移 / Then smoke 必填变量、四个非 admin 真实账号、Excel 报工人和审批人、API 权限均存在。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> FAIL，新增契约尚未实现。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，112 passed。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=154`，包含 `20260618_post_release_role_e2e_gate_smoke_contract`。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\showroom --sql-file sql\showroom\20260605_showroom_product_revision_attachment_schema.sql --sql-file sql\showroom\20260606_showroom_hall_product_canvas_layout.sql --sql-file sql\showroom\20260613_showroom_award_and_hall_item_schema.sql --sql-file sql\showroom\20260615_showroom_hall_canvas_background.sql --file-prefix sql/showroom` -> PASS，`migrationCount=4`。
- GREEN: `git diff --check -- <current task files>` -> PASS。

## 2026-06-19 新线程接续

- 用户需求：刚刚线程中断，继续发布后三角色测试服门禁；发布后在测试服务器用 `芋道源码` 租户账号 `gaomin`、`zhaojie`、`wangsiyu` 全量验证，失败先全部记录，统一修复后重新构建发布到测试服并复测直到通过。
- GREEN: experience-preflight -> PASS，已重新读取 `docs/experience-index.md`、`docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`、`docs/agent-memory/project-error-prevention.md`；用户本次明确授权测试服 `172.30.30.58`、`芋道源码` 租户和三个指定账号真实 E2E，禁止正式服、备份服、备份、恢复、回滚、mock 或接口绕过。
- GREEN: resume-evidence-read -> PASS，最新构建/部署 evidence `runtime-console-build-deploy-1781803561178.json` 为 PASS，releaseTag `release-20260619-0112-role-e2e-gate-utf8-smoke-env`；最新真实 E2E evidence `post-release-role-e2e-1781826823171.json` 为 FAIL，4 failures。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781826823171.json`：`gaomin` 仅见 `展厅` 但产品管理页 16 个产品封面接口返回 200 空 JSON/非图片并显示 `加载失败`；`zhaojie` 仅见 `智能排产` 但 `/mes/pro/task` 调用 dependencies GET 时 URL 过长返回 414，工作台通知未读请求被中断，冒烟测试失败；`wangsiyu` 仅见 `DCC文控中心` 且 16 个 DCC 子页通过。
- BDD: 智能排产依赖查询长范围契约 -> Given 生产排产页会加载数百个工单范围 / When 查询甘特图依赖线 / Then 前端必须用 POST JSON body 提交 `workOrderIds/taskIds`，后端必须接受 request body，禁止因 URL 过长返回 414。
- BDD: 智能排产冒烟账号登录契约 -> Given smoke runner 需要三类非 admin 真实账号 / When 发布脚本写入 `.env` 并 SQL 准备账号 / Then 用户名必须符合登录校验 `^[a-zA-Z0-9]{4,30}$`，不得使用下划线账号导致登录 validation 失败。
- BDD: 展厅产品封面对象一致性修复 -> Given `infra_file.config_id=28` 中 154 条 `showroom/product/cover/20260602/%` 引用 / When 测试服 MinIO 缺失对应对象 / Then 只能用真实同名对象补齐默认 bucket 路径，不改 protected config、不改域名、不放占位图。
- RED: `mvn -pl yudao-module-mes -Dtest=MesProAutoScheduleControllerContractTest test` -> FAIL，新增 controller 契约编译失败：`getDependencies(MesProAutoScheduleDependencyReqVO)` 尚不存在。
- RED: `node tests\e2e\mes-auto-schedule-dependency-post-static.spec.js` -> FAIL，前端依赖查询仍使用 GET query params。
- RED: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> FAIL，发布脚本/测试契约未统一到登录规则允许的 smoke 用户名。
- GREEN: `mvn -pl yudao-module-mes -Dtest=MesProAutoScheduleControllerContractTest test` -> PASS，controller POST JSON body 契约通过。
- GREEN: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，9 passed，smoke 合法账号 SQL/发布契约通过。
- GREEN: `node tests\e2e\mes-auto-schedule-dependency-post-static.spec.js` -> PASS，前端依赖查询已改为 POST body。
- GREEN: test-server-minio-showroom-cover-repair -> PASS，使用 `evidence/minio-showroom-cover-20260602-repair-1781842832636.tar` 将测试服 MinIO `yudao/showroom/product/cover/20260602` 对象数从 1 补齐到 154；样例 `/admin-api/infra/file/28/get/showroom/product/cover/20260602/product-product_006-imported-cover-275dbe9f8a322d54.png` 与 `product-product_004-imported-cover-8d6b4cd211df01b9.png` 均返回 HTTP 200、`Content-Type: image/png`。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，113 passed。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=155`，包含 `20260619_post_release_role_e2e_gate_smoke_username_fix`。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\showroom --sql-file ... --file-prefix sql/showroom` -> PASS，4 migrations。
- GREEN: `pnpm exec vue-tsc --noEmit -p tsconfig.relaxed.json` -> PASS，需 `NODE_OPTIONS=--max-old-space-size=8192`，默认堆内存下曾 OOM。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781844498623.json`，releaseTag `release-20260619-1229-role-e2e-gate-post-deps-smoke-user`，构建和测试服部署均成功；服务器 `.env`、backend/frontend 镜像 tag、后端 health、前端 HTTP 200 均通过；`20260619_post_release_role_e2e_gate_smoke_username_fix` 在测试服为 `APPLIED`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781844737245.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产`，但工作台全局未读消息请求 `net::ERR_ABORTED` 被误判为 route failure，智能排产 smoke 失败，远端 `smoke-report.json` 显示三个合法 smoke 账号登录被拒绝为 `密码已过期，请修改密码后再登录`。
- BDD: 智能排产 smoke 密码有效期契约 -> Given 发布脚本准备登录规则兼容的 smoke 账号 / When 系统密码策略校验 `password_update_time` / Then 三个 smoke 账号必须刷新 `password_update_time`，否则发布后 smoke 登录必须失败并暴露。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，新增合同期望 `20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix.sql`，当前缺少迁移文件。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，7 passed；新增迁移刷新 `messmokeerp/messmokesupervisor/messmokenonapprover` 的 `password_update_time` 并验证 `fresh_password_count=3`。
- RED: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> FAIL，E2E 脚本尚未区分浏览器主动中止的全局未读消息请求。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> PASS，E2E 脚本仅将 `GET /admin-api/system/notify-message/get-unread-count` 且 `net::ERR_ABORTED` 的请求归入 `externalRequestFailures`，其他请求失败仍计入失败。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，114 passed。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=156`，`20260619_post_release_role_e2e_gate_smoke_username_fix` 后包含 `20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix`。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781846618912.json`，releaseTag `release-20260619-1301-role-e2e-gate-smoke-password-freshness`，构建和测试服部署均成功；测试服 `.env`、backend/frontend 镜像 tag、后端 health、前端 HTTP 200 均通过；`20260619_post_release_role_e2e_gate_smoke_username_password_freshness_fix` 在测试服为 `APPLIED`，`messmokeerp/messmokesupervisor/messmokenonapprover` 的 `password_update_time` 均刷新为 `2026-06-19 13:21:31`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781846902055.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产`，6 个子页无页面/接口错误，但智能排产 smoke 失败。远端 `smoke-report.json` 显示 `/admin-api/erp/kingdee-sync/production-order/create` 被 Kingdee 拒绝：`计划完工时间没有落在生产车间关联的工作日历的生产日上`，实际默认 `erpPlannedFinishTime=2026-06-20 17:27:00` 为周六。
- BDD: 智能排产 smoke 工作日完工时间契约 -> Given 发布后 smoke 需要创建真实 Kingdee 生产订单 / When 运行时刻加 36 小时落在周末 / Then 默认 ERP 计划完工时间必须推进到下一个工作日，不能生成会被 Kingdee 车间工作日历拒绝的周末完工时间。
- RED: `node tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js` -> FAIL，新增合同期望默认 ERP planned finish 使用 `nextWeekdayDateTimeAfter(36)`，当前脚本仍为裸 `isoDateTimeAfter(36)`。
- GREEN: `node tests/e2e/smart-scheduling-smoke-real-flow-static.spec.js` -> PASS，smoke 默认 `erpPlannedFinishTime` 已改为下一个工作日固定 17:30；`erpSyncEligibleDateTime()` 在周末回退到最近工作日，保持 Kingdee 同步窗口内的生产日。
- GREEN: experience-preflight -> PASS，第三轮修复仍限定测试服 `172.30.30.58`、芋道源码租户三账号真实 E2E；不操作正式服、不备份/恢复、不 mock、不绕过前端路径。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781848691651.json`，releaseTag `release-20260619-1335-role-e2e-gate-weekday-smoke-finish`，构建和测试服部署均成功；测试服 `.env`、backend/frontend 镜像 tag、后端 health、前端 HTTP 200 均通过。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781848897783.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，但智能排产 smoke 失败。远端 `smoke-report.json` 显示 ERP 冒烟创建员在金蝶同步运行页等待生产工单 `kingdeeProductionOrderSyncJob` 行内“执行一次”按钮超时；截图 `evidence/zhaojie-smoke-job-trigger-failure-1781848897783.png` 显示“手动补跑”列为空。
- GREEN: root-cause-readonly-db -> PASS，只读核对测试服：ERP smoke 用户 `messmokeerp` 绑定角色 `post_release_mes_smoke_erp_creator`；角色已绑定旧菜单 `1075/infra:job:trigger`，但该按钮父菜单为 `110/定时任务`，ERP smoke 角色没有父菜单链；真实登录 `messmokeerp` 后 `get-permission-info` 仅包含 `erp:kingdee-sync:query`，不包含 `infra:job:trigger` 或 `infra:job:query`。代码核对 `filterDisableMenus()` 会过滤父菜单缺失的按钮权限，导致前端 `v-hasPermi="['infra:job:trigger']"` 隐藏按钮。
- BDD: ERP smoke 手动同步权限 -> Given zhaojie 智能排产 smoke 使用 ERP 冒烟创建员创建 Kingdee 工单 / When 打开 ERP 金蝶同步运行页 / Then 页面必须显示生产工单“执行一次”，且该账号具备定时任务查询和触发接口权限。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，新增合同期望 `20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix.sql`，当前缺少迁移文件。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，8 passed；新增迁移在 ERP 同步菜单 `6013` 下补齐 `infra:job:query` 与 `infra:job:trigger` 两个按钮权限，并绑定 ERP smoke 角色。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，115 passed。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=157`，包含 `20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix`。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781851424303.json`，releaseTag `release-20260619-1430-role-e2e-gate-erp-job-permission`，构建和测试服部署均成功。
- GREEN: test-server-release-state -> PASS，测试服 `.env` `IMAGE_TAG=release-20260619-1430-role-e2e-gate-erp-job-permission`；backend/frontend 镜像 tag 匹配并 running；后端 health HTTP 200，前端 HTTP 200；`20260619_post_release_role_e2e_gate_smoke_z_erp_job_permission_fix` 在测试服为 `APPLIED`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781851764170.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，但智能排产 smoke 失败。远端 `output/artifacts/smoke-report.json` 显示 ERP 工单创建、MES 同步、工作台八指标和 `infra/job/trigger` 均通过，失败在 `admit-confirmed-work-order-to-schedule-pool`：工单 `SMART-SCHED-20260619T064800584124551-MO` 不在 `READY_TO_ADMIT` 入池差异列表。
- GREEN: root-cause-readonly-db -> PASS，只读核对测试服真实库：`MES_SMOKE_PRODUCT_CODE=AW.106.03.08.1007`，芋道源码租户同步出的产品 `902476` 无 `mes_pro_route_product` 路线绑定，`route_process` 计数为 0；可路线就绪候选包括 `YXN.069.001.1003` / 单位 `zhi` / route `900026` / 激活版本 `4` / 工序数 `26`。同时发现远端 runner 只保留残留静态 `smart-scheduling-smoke-feedback.xlsx`，其内容写死旧产品 `AW.106.03.08.1007` 和旧工单号，不适配本次 smokeRunId。
- BDD: 智能排产 smoke 路线就绪产品 -> Given smoke 通过 Kingdee 创建真实生产工单 / When MES 同步工单并查询排产入池差异 / Then 默认产品必须已绑定启用路线、激活版本和工序，不能停留在 `BLOCKED_MISSING_ROUTE`。
- BDD: 智能排产 smoke 动态报工 Excel -> Given smoke 每次运行都有新的工单号和产品配置 / When 执行第三方报工导入 / Then 上传 Excel 必须按本次 `smokeRunId`、工单号、产品编码和工序动态生成，不能依赖测试服残留静态文件。
- RED: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> FAIL，发布脚本仍保留旧默认产品 `AW.106.03.08.1007` 且 runner package 未包含 `xlsx`。
- RED: `node tests\e2e\smart-scheduling-smoke-real-flow-static.spec.js` -> FAIL，smoke runner 仍将 `MES_SMOKE_EXCEL_FILE` 作为必填固定 workbook，未动态生成本次运行的报工 Excel。
- GREEN: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> PASS，发布脚本默认产品改为 `YXN.069.001.1003`、单位 `zhi`，并显式迁移旧无路线默认值；runner package 包含 `xlsx`。
- GREEN: `node tests\e2e\smart-scheduling-smoke-real-flow-static.spec.js` -> PASS，smoke runner 改为每次运行生成 `feedback-workbook-<smokeRunId>.xlsx` 并记录 `sourceFileSha256`。
- GREEN: `node --check tests\e2e\smart-scheduling-smoke-real-flow.e2e.js` -> PASS。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\validate-maintenance-publish-contract.cjs` -> PASS，维护仓实际发布脚本包含同样的 route-ready 默认产品、旧值迁移和 `xlsx` runner 依赖。
- GREEN: PowerShell AST -> PASS，维护仓 `ops\deploy\publish-int-ruoyi.ps1` 与业务仓 `script\deploy\publish-int-ruoyi.ps1` 均无解析错误。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py script\tests\test_scheduler_smoke_release_contract.py script\tests\test_showroom_release_sql_contract.py script\tests\test_publish_int_ruoyi_to_test_tooling.py script\tests\test_showroom_product_revision_attachment_sql.py script\tests\test_showroom_sql_scripts.py -q` -> PASS，115 passed。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=157`。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs`、`node tests\e2e\mes-auto-schedule-dependency-post-static.spec.js`、`node tests\e2e\smart-scheduling-smoke-real-flow-static.spec.js` -> PASS。

## 2026-06-19 终轮测试服复测

- 用户需求：每次发布后在测试服务器用 `芋道源码` 租户账号 `gaomin`、`zhaojie`、`wangsiyu` 全量验证角色页签、子页访问和智能排产冒烟；失败先全部记录，统一修复后重新构建发布到测试服并复测直到通过。
- GREEN: experience-preflight -> PASS，已重新核对 `docs/experience-index.md` 命中文档约束仍适用；当前高风险动作仅限测试服 `172.30.30.58` 真实登录 E2E，不涉及正式服、备份/恢复/回滚或接口绕过。
- GREEN: resume-evidence-read -> PASS，最新构建/部署 evidence `evidence/runtime-console-build-deploy-1781854878582.json` 为 PASS，releaseTag `release-20260619-1518-role-e2e-gate-route-ready-smoke` 已部署到测试服，下一步直接运行三角色真实 E2E。

## 2026-06-19 排产工序快照缺列修复

- 用户需求：继续发布后三角色测试服门禁；先记录全部失败，再统一修复、重新构建发布到测试服并完整复测，直到三账号全部通过。
- GREEN: experience-preflight -> PASS，已再次核对 `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`，当前高风险动作仍仅限测试服 `172.30.30.58` 的重发与真实 E2E，不涉及正式服、备份/恢复/回滚。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781856280345.json` 为 FAIL，但仅剩 `zhaojie` 智能排产 smoke 失败；远端 `/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/smoke-report.json` 明确报错 `Unknown column 'process_code' in 'field list'`，发生在 `mes_pro_schedule_order_process` 插入排产工序快照阶段。
- BDD: 排产工序快照 schema 契约 -> Given 智能排产 smoke 会把工单工序写入 `mes_pro_schedule_order_process` 快照表 / When 后端持久化 `process_code` 与 `process_name` / Then 测试服真实库必须先具备对应列并对历史记录完成回填，不能在 `create-from-work-order` 阶段因缺列失败。
- RED: `git -C D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro show HEAD:sql/mysql/20260619_mes_schedule_order_process_snapshot_identity_p8.sql` -> FAIL，`HEAD` 中不存在该迁移文件，说明当前已部署版本未携带本次 schema 修复。
- GREEN: `python -X utf8 -m pytest script\tests\test_mes_scheduling_closed_loop_sql.py -q` -> PASS，6 passed；新增契约覆盖 `20260619_mes_schedule_order_process_snapshot_identity_p8.sql` 的 release metadata、`process_code/process_name` 加列与回填语义。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=158`，包含 `20260619_mes_schedule_order_process_snapshot_identity_p8`。

## 2026-06-19 A03388 设备工序产能冲突发布修复

- 用户需求：继续同一任务，修复重发后仅剩的 `zhaojie` 智能排产 smoke 失败，并在修复后再次构建发布测试服、复跑三账号真实 E2E。
- GREEN: experience-preflight -> PASS，已再次核对当前高风险动作仍仅限测试服 `172.30.30.58` 的重新构建发布和真实浏览器 E2E，不涉及正式服、备份/恢复/回滚。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781858207843.json`，releaseTag `release-20260619-1638-role-e2e-gate-process-snapshot` 已成功构建并部署测试服；远端 `.env` 验证 `IMAGE_TAG=release-20260619-1638-role-e2e-gate-process-snapshot`。
- RED: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> FAIL，证据 `evidence/post-release-role-e2e-1781858432621.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，但智能排产 smoke 失败。远端 `smoke-report.json` 显示 `API /admin-api/mes/pro/auto-schedule/preview failed`，错误为 `设备工序产能存在冲突: machineryId=47, processId=900370`。
- BDD: A03388 同设备同工序唯一产能契约 -> Given `芋道源码` 租户智能排产 smoke 会在自动排产预览读取 A03388 相关设备工序产能 / When 同一设备同一工序存在两条不同 `standard_hourly_capacity` 记录 / Then 发布迁移必须逻辑删除重复高产能记录，仅保留保守容量，避免 `/mes/pro/auto-schedule/preview` 因资源冲突 500。
- GREEN: root-cause-read -> PASS，结合历史任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260608-admin-resource-capacity-unify\` 与当前远端 smoke 报告，可确认 admin 租户 `A03388` 的 `machinery_id=47` 在 `process_id=900370/900371` 上存在已知重复高产能源；本次测试服尚未通过正式发布迁移承接这笔数据治理。
- RED: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> FAIL，新增契约期望 `20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix.sql`，当前缺少迁移文件。
- GREEN: `python -X utf8 -m pytest script\tests\test_post_release_role_e2e_gate_sql.py -q` -> PASS，9 passed；新增迁移会在 `tenant_id=1` 中校验并逻辑删除 `machinery_id=47 / process_id=900370,900371` 的高产能冲突行，保留 `25.714286` 与 `40.000000` 两条基准记录，并在发布时强制 `remaining_conflict_count = 0`。
- GREEN: `python -X utf8 script\release\run-release-migration-policy-gate.py --sql-root sql\mysql` -> PASS，`migrationCount=159`，包含 `20260619_post_release_role_e2e_gate_smoke_admin_resource_capacity_fix`。

## 2026-06-19 自动编码流水恢复与展厅误报收敛

- 用户需求：继续同一任务，在再次发布前先记录全部剩余错误，统一修复 `gaomin` 的误报和 `zhaojie` 智能排产 smoke 的真实后端失败，再构建发布到测试服并复测三账号。
- GREEN: experience-preflight -> PASS，已重新核对 `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`；当前高风险动作仍仅限测试服 `172.30.30.58` 的真实登录、只读排障和后续重发版，不涉及正式服、备份/恢复/回滚。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781865453288.json` 为 FAIL，但仅剩两项：`gaomin` `/showroom/company` 的 `dict-data/simple-list` 浏览器中止误报，以及 `zhaojie` 智能排产 smoke 在 `apply` 阶段失败。
- GREEN: root-cause-readonly-remote -> PASS，只读核对测试服 `172.30.30.58`：`mes_md_auto_code_rule` 已存在 `tenant_id=1 / rule_id=900070 / code=PRO_TASK_CODE` 及 `900071/900072` 两段规则；`mes_md_auto_code_record` 仅保留 `PT-0006(serial_no=6)`、`PT-0007(serial_no=7)`；`intruoyi-redis` 中不存在 `mes:md:auto_code:900070` key；后端日志堆栈固定落在 `MesMdAutoCodeRecordServiceImpl.generateAutoCode(...:90)`，说明失败根因是 Redis 流水缓存丢失后回退撞码，而非规则缺失。
- BDD: 展厅页签切页中的字典请求中止不应误判失败 -> Given `gaomin` 展厅子页真实访问成功 / When 浏览器在页面切换时主动中止 `GET /admin-api/system/dict-data/simple-list` / Then E2E 脚本应将其记为 benign external request，而不是 route failure。
- BDD: 自动编码流水缓存丢失后必须按数据库最大流水恢复 -> Given `PRO_TASK_CODE` 的 Redis key 丢失但数据库已有历史 `serial_no` / When 智能排产 `apply` 再次批量生成任务编码 / Then 系统必须从历史最大流水继续分配，不能回退到起始号并因历史 `PT-0006/PT-0007` 记录抛出 `编码生成失败`。
- RED: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> FAIL，脚本尚未将 `GET /admin-api/system/dict-data/simple-list` 的 `net::ERR_ABORTED` 归为 benign request failure。
- RED: `mvn -pl yudao-module-mes -Dtest=MesMdAutoCodeSerialNumberPartStrategyTest test` -> FAIL，新增自动编码恢复用例前，编译无法找到 `selectLatestSerialRecord(...)` 恢复契约，说明正式恢复逻辑尚未实现。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\post-release-role-e2e-static.test.cjs` -> PASS，展厅脚本已将 `GET /admin-api/system/dict-data/simple-list` 且 `net::ERR_ABORTED` 纳入 benign request failure，避免把已确认 200 的切页中止误报为页面失败。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesMdAutoCodeSerialNumberPartStrategyTest,MesProAutoScheduleServiceImplTest" test` -> PASS，28 passed；新增自动编码恢复用例覆盖 Redis key 丢失后按 `mes_md_auto_code_record` 历史最大 `serial_no` 续号，同时排产服务既有 22 个回归用例未回退。

## 2026-06-19 eDHR 批次触发门禁修复

- 用户需求：继续同一任务，在再次发布前先记录全部剩余错误，统一修复 `zhaojie` 智能排产 smoke 的新后端失败，再构建发布到测试服并复测三账号。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781869546155.json` 显示 `gaomin` 与 `wangsiyu` 已通过，`zhaojie` 的智能排产 smoke 已不再报 `编码生成失败`，但在 `/admin-api/mes/pro/auto-schedule/apply` 新失败为 `排产完成创建 eDHR 批次缺少前置条件：工序与批记录绑定`。
- GREEN: root-cause-readonly-remote -> PASS，只读核对测试服：当前 smoke 路线 `900026` 在 `mes_pro_route_use_process_config` 下无任何 `use_type='BATCH'` 的启用工序配置，在 `mes_pro_route_use_process_batch_record` 下也无任何绑定；与此同时当前代码 `MesProAutoScheduleServiceImpl.apply(...)` 会在排产完成后无条件触发 eDHR 批次创建，说明失败根因是普通路线被误纳入 eDHR 前置校验，而不是 eDHR 已启用路线缺少兜底。
- BDD: 非 eDHR 路线排产完成后不应触发批次创建 -> Given 自动排产 `apply` 成功生成普通路线任务且该路线无启用中的 `BATCH` 配置 / When 排产服务进入排产完成后置动作 / Then 不得调用 eDHR 批次创建服务，也不得因 `工序与批记录绑定` 缺失回滚整个 `apply`。
- BDD: 已启用 eDHR 的路线仍需严格校验前置条件 -> Given 路线存在启用中的 `BATCH` 工序配置 / When 排产服务触发 eDHR 批次创建 / Then 若缺少工序与批记录绑定或首任务责任来源/候选池，系统仍必须明确失败，不得吞错、降级或静默跳过。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesProAutoScheduleServiceImplTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest" test` -> PASS，35 passed；新增调度层回归测试保护普通路线跳过 eDHR 触发、已启用 eDHR 路线继续 fail fast。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesProEdhrBatchExecutionServiceTest,MesProAutoScheduleServiceImplTest,MesProAutoScheduleAlgorithmContractTest,MesProAutoScheduleContractTest" test` -> PASS，72 passed；eDHR 批次服务既有 37 个契约测试保持全绿，说明本次改动仅修正调度触发门禁。

## 2026-06-19 报工审批人身份解析门禁修复

- 用户需求：继续同一任务，在最新发布 `release-20260619-2055-role-e2e-gate-edhr-trigger` 之后先记录全部剩余错误，统一修复 `zhaojie` 智能排产 smoke 的新阻塞，再重新构建发布到测试服并完整复测三账号。
- GREEN: experience-preflight -> PASS，已再次核对 `docs/release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`；当前高风险动作仍仅限测试服 `172.30.30.58` 的重新构建发布与真实浏览器 E2E，不涉及正式服、备份/恢复/回滚。
- GREEN: resume-evidence-read -> PASS，最新真实 E2E 证据 `evidence/post-release-role-e2e-1781875259932.json` 显示 `gaomin` 与 `wangsiyu` 已通过，`zhaojie` 的智能排产 smoke 已越过 eDHR `apply` 门禁，但在 `/admin-api/mes/pro/feedback/import-record/attribute` 新失败为 `第三方报工导管报工第 2 行工段长匹配到多名用户：eDHR矩阵-审批人`。
- GREEN: root-cause-readonly-remote -> PASS，只读核对测试服：`/opt/intruoyi/runtime/.env` 当前包含 `MES_SMOKE_SUPERVISOR_USERNAME=messmokesupervisor` 且未显式设置 `MES_SMOKE_FEEDBACK_APPROVER_NAME`；数据库 `tenant_id=1` 下启用用户 `mes_smoke_supervisor(id=910253)` 与 `messmokesupervisor(id=910260)` 共用 nickname `eDHR矩阵-审批人`，因此依赖默认昵称的第三方报工导入在当前真实数据下稳定不唯一。
- BDD: 第三方报工导入审批人支持唯一 username 解析 -> Given 导入文件的工段长字段填写的是启用用户的唯一 username / When 系统在归属阶段解析审批人 / Then 必须把审批责任绑定到该 username 对应的唯一用户，后续审批人登录与 approveUserId 保持一致。
- BDD: 重复昵称仍然 fail fast -> Given 导入文件的工段长字段填写的是重复 nickname，且没有与之同名的唯一 username / When 系统解析审批人 / Then 必须明确返回“匹配到多名用户”，不得静默任选其一或吞错继续。
- GREEN: `mvn -pl yudao-module-mes "-Dtest=MesProFeedbackImportRecordServiceImplTest" test` -> PASS，6 passed；新增回归覆盖 supervisor username 直绑审批人、唯一 nickname 兼容与重复 nickname 继续 fail-fast。
- GREEN: `node doc\tasks\20260618-post-release-role-e2e-gate\scripts\validate-maintenance-publish-contract.cjs` -> PASS，维护发布脚本已显式输出 `MES_SMOKE_FEEDBACK_APPROVER_NAME=$effectiveMesSmokeFeedbackApproverName`，并将其绑定到当前 supervisor username，避免测试服运行态回退到历史昵称默认值。
- GREEN: root-cause-readonly-remote -> PASS，最新发布 `release-20260619-2143-role-e2e-gate-feedback-approver` 后，测试服 `.env` 已包含 `MES_SMOKE_FEEDBACK_APPROVER_NAME=messmokesupervisor`，但真实 smoke 产物 `/opt/intruoyi/runtime/smoke/yudao-ui-admin-vue3/output/artifacts/config.json` 仍显示 `feedbackApproverName=eDHR矩阵-审批人`；定位到发布链生成的 scheduler smoke `npm` wrapper 白名单缺少 `MES_SMOKE_FEEDBACK_APPROVER_NAME`，导致 Node 容器未继承该变量。
- GREEN: `python -X utf8 -m pytest script\tests\test_scheduler_smoke_release_contract.py -q` -> PASS，3 passed；业务仓发布契约已新增 smoke 变量在 compose、远端 `.env` 与 runner wrapper 三处一致透传的静态门禁。
- GREEN: runtime-console-build-deploy -> PASS，证据 `evidence/runtime-console-build-deploy-1781882335880.json`，releaseTag `release-20260619-2230-role-e2e-gate-feedback-approver-wrapper` 已成功构建并部署测试服；远端 `.env` 验证 `IMAGE_TAG=release-20260619-2230-role-e2e-gate-feedback-approver-wrapper`。
- GREEN: `POST_RELEASE_ROLE_E2E_PASSWORD=111111 node doc/tasks/20260618-post-release-role-e2e-gate/scripts/post-release-role-e2e.cjs` -> PASS，证据 `evidence/post-release-role-e2e-1781882555897.json`：`gaomin` 仅见 `展厅` 且 6 个子页通过；`zhaojie` 仅见 `智能排产` 且 6 个子页通过，真实智能排产 smoke 全链路通过；`wangsiyu` 仅见 `DCC文控中心` 且 16 个子页通过。
- GREEN: final-smoke-proof -> PASS，远端 `config.json` 显示 `feedbackApproverName=messmokesupervisor`，远端 `smoke-report.json` 显示 `status=PASS`、`workOrderCode=SMART-SCHED-20260619T152027017032296-MO`，归属记录 `approverName=messmokesupervisor`，正式报工 `approveUserId=910260`。

## 2026-06-20 收尾清理与提交准备

- GREEN: `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260618-post-release-role-e2e-gate --mode preview` -> PASS，closeout preview 仅保留 `task.md`、`execution-log.md` 与最终 PASS 的构建/三角色 E2E 两份 evidence。
- GREEN: manual-closeout-apply -> PASS，按 `task.md` 中 `Cleanup Candidates` 手工删除 `bug-regression-evidence.md`、`qa-evidence.md`、`scripts/`、中间失败 build/E2E evidence、screenshots 与 MinIO 同步附属产物；任务目录最终仅保留 `task.md`、`execution-log.md`、`evidence/runtime-console-build-deploy-1781882335880.json`、`evidence/post-release-role-e2e-1781882555897.json`。
- GREEN: task-tree-recheck -> PASS，复核 `doc/tasks/20260618-post-release-role-e2e-gate/` 当前目录树与 `Cleanup Keep` 完全一致，无额外附属产物残留。
