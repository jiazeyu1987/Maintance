# 执行记录
GREEN: closeout -> PASS。正式cleanup_build_worktree核验并删除build/2026-11-25-08-59-37（25282文件）、build/2026-11-25-09-59-57（25284文件）、test-prod-20261125（5315文件）；成功build/2026-11-25-10-22-04已自动核验25285文件并删除。四目录均registeredAfter=false、physicalPathExists=false、producedNewCommits=false，无需融合。稳定控制台PID21804仍使用C:/SpugHandoff/release/source/ops/spug/release-center/intruoyi_executor.py，无控制台迁移。record-final.py脱敏结果PASS，任务completed。全局request-command-log已追加本次结果，但其既有6171行混合变更不整体暂存，仅提交本任务独立目录。
GREEN: prod public/runtime -> PASS_WITH_OBSERVATIONS。accept-prod JOB-eb73176ba8 succeeded；真实公开菜单与打印认证通过，观察同维护入口6项且逐项归因；prod-final-runtime.py PASS，三阶段数据库契约PASS。发布运行态完成，状态ready_for_closeout。

GREEN: experience-preflight -> PASS（自有worktree收尾）。仅清理本任务维护worktree和两次已由后续成功构建解决的失败构建worktree；调用正式cleanup_build_worktree核对绝对路径、登记、原提交、无改动、无进程消费者后删除，发现未知文件即保留并阻塞。均预期无新提交，无需融合；其他任务工作区和稳定控制台不动。
GREEN: experience-preflight -> PASS（正式开放）。维护入口菜单/版本及打印认证均PASS；每组6观察逐项核实为外部统计失败2、头像ORB1、预声明工作台写入拦截3，记录PASS_WITH_OBSERVATIONS，不冒充工作台或完整业务验证。部署OP-e815d00597f25dd9c673 succeeded；执行同tag accept-prod，开放后复核公开入口与三阶段契约。
GREEN: experience-preflight -> PASS（正式维护入口真实页面）。promote-prod JOB-6eec691c6c succeeded，技术登录通过；按预声明只读路径运行维护入口菜单/版本及打印票据认证检查，保留全部观察，不补业务数据。
GREEN: experience-preflight -> PASS（正式晋级）。同版本测试验收 JOB-9f07f0d8dc 与正式预检 JOB-d79c696464 均 succeeded；使用已登记外部恢复策略和既有正式入口 promote-prod，仅操作57，不补业务数据、不操作59。正式开放前验证维护页，开放后复核运行态和真实页面。
用户授权当前系统发布到测试和正式；继承不补业务数据范围。先只读核查，再记对应阶段preflight。

GREEN: experience-preflight -> PASS（隔离目录准备）。当前应用5b2a0938303abc36740bca1a54e213c317488265等于origin/int_main；仅发布提交内容，保留主目录既有验证文档修改。维护目标5b341d9，新建专用worktree；预检使用现有正式入口，未授权59。

BLOCKER: experience-preflight -> 构建入口固定检查三服。JOB-9bf1ebef49 failed；58/57检查通过，59的SSH运行态读取与暂存目录失败。源码release_precheck.py:205硬编码范围，无可用目标范围参数。不绕过、不改59。维护worktree保留，无新提交；实际命令actions.py action check-prerequisites build-preflight.json。

用户明确不发布59。代码复核修正前结论：check-prerequisites是独立诊断，intruoyi_executor.py明确不以其失败阻断发布；intruoyi_build.py读取三服登记历史但不实时访问59。58/57诊断均通过。GREEN: experience-preflight -> PASS（构建）；保留59诊断失败，不修改历史或59，执行原有构建入口及目标独立预检。

BLOCKER: build-release JOB-a988faab72 -> FAILED，SQL catalog mismatch; unregistered: 20261124_erp_kingdee_auto_sync_retry_budget.sql, 20261124_erp_order_sync_integrity.sql。真实构建失败，未进入服务器部署。当前状态blocked，保留失败与隔离目录，不跳过SQL登记校验。

用户要求同步int_main。两次通过规定127.0.0.1:7890代理fetch origin int_main均失败：schannel SSL/TLS handshake failed。未切换直连、未关闭TLS校验、未merge；本机仍5b2a09383，已有verification.md修改保持。最新远端提交未知，发布继续blocked。

按用户要求再次显式使用http.proxy/https.proxy=http://127.0.0.1:7890执行fetch origin int_main，退出1，仍为schannel SSL/TLS握手失败。未merge、未部署。

通过7890 fetch及ff-only同步成功，当前a330c9004fe1dafcc259de9dcf61ba97a8b07439；原验证文档修改保留。两份ERP SQL登记已修复，新增PQC聚合字段可空迁移含目标preflight，无补业务数据。GREEN: experience-preflight -> PASS（重新构建）。新构建自动新建提交对应worktree，沿原有已验证构建入口，范围58/57。

BLOCKER: build-release JOB-e5d0db2c2d / 2026-11-25-09-59-57 -> test: required target preflight missing (1): 20261124_registration_certificate_workbook_import_permission。原ERP登记已解决；新提交构建未完成，未部署。按持续有效分工通知IntRuoyi线程01a20836-968a-7f72-82df-3b2ddb1b3837修复及提交，等待其结果。

GREEN: experience-preflight -> PASS（构建r3）。IntRuoyi提交462d6647fc484ef4d3433a5a640015c9559c37db，真实干净checkout的917迁移/1240资产、58/57各4待执行迁移预检齐全，反向移除绑定准确拒绝。新构建使用该固定提交，不混入脏内容。

GREEN: experience-preflight -> PASS（只读基线登记）。test schema drift精确证明仅mes_pqc_process_inspection_aggregate_detail.production_submit_event_id IS_NULLABLE变YES；内存翻转后全schema摘要与原98eb33ad一致，实测87b34c9b。镜像/账本及服务保持，新增正式迁移目标即该值。使用register-targets target=test重读登记，不写业务库、不改59；具体谁执行历史DDL未知，保留差异证据schema-drift-summary.json。

GREEN: experience-preflight -> PASS（publish-test）。构建JOB-dd0cd66f8b succeeded，同包2026-11-25-10-22-04；只读测试基线登记JOB-b9981bf500 succeeded，专属预检JOB-651b1d8a28 succeeded。发布仅58，保留恢复与原件身份，真实页面采用预先只读拦截，不补业务数据。

GREEN: test runtime/page -> PASS_WITH_OBSERVATIONS。JOB-58851b5e0e及OP-9414466313c3694155f8成功，三阶段契约PASS，final-runtime.py PASS。真实menu/print每组6观察：统计2/头像1/预声明workbench写拦截3；必要页面、版本、权限读取及认证iframe均PASS，完整入单未验证。GREEN: experience-preflight -> PASS（限定范围mark-tested与正式预检）。同包ef37a84a，未补业务数据。
