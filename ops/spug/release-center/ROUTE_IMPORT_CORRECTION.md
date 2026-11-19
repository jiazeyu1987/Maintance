# 工艺路线导入索引纠正与停止态前向发布

这是用户明确授权的专项维护命令。不是普通发布自动修复，不允许用于其他租户、版本或摘要。

- Trigger：跨租户导入只重写配置值、遗漏对象键，5条tenant163冻结版本有74个排程索引错误；正式发布已完成13项迁移后在终端READINESS拒绝，尚未切程序。
- Preflight check：新完整包必须已完成同包测试服部署、技术验证和mark-tested；原失败JOB/OP终结且未核销，旧容器/镜像/配置/数据库身份保持；新包零待执行SQL。Java计划器固定5个版本、原SHA及条数，精确纠正对象键并通过正式Canonicalizer。JDBC重新核原导入登记、签名/受控后继/生产执行引用和InnoDB事务能力。
- Blocker：任何身份/摘要/引用/原worker/SQL计划漂移；已有纠正目录、回执不完整、写入结果未知、缺少实际静态网络配置时停止。已有目录必须先检查原操作及数据库审计，禁止重放命令。
- Verification：原JSON/冻结SHA/原文SHA与纠正计划先封存并读回；同一公共发布锁下用新包固定镜像先只读预演，再SERIALIZABLE事务CAS更新5条JSON/SHA并新增5条审计。其他列、受控登记不变。命令后完整PRECHECK通过，后续新promote-prod仍运行终端READINESS及正常技术/页面/开放验收。
- Forbidden action：禁止改历史SQL、台账状态、原失败状态、关闭Canonicalizer、启动旧writer、拼接releaseTag、直接手改JSON凑摘要、无锁执行、打印凭据、修改NAS挂载。原件封存路径与SHA必须进入审计；不能把external恢复责任确认称为已验证备份。
- Evidence：`doc/tasks/20261119-update-and-release-prod/`；命令输出私密维护记录及各远端operation journal；原失败目录下`route-import-index-correction-v1/plan.private.json`、`dry-run.private.json`、`report.private.json`和业务纠正审计。

阶段必查与命令：

1. 在本次维护worktree运行`python -X utf8 -m unittest test_stopped_origin_recovery test_route_snapshot_handler test_resume_test_tail test_direct_release test_intruoyi_runtime test_interruption test_technical_verification test_source_runtime test_source_binding_entry`；应用Maven专项验证导入映射、拒绝非法源快照、仅纠正索引及固定范围。
2. 新测试包通过后，运行`python -X utf8 route_import_correction.py --config <私密配置> --original-job-id <原失败JOB> --release-tag <新已测试tag> --plan <Java生成的私密计划> --output <全新私密预检记录>`，默认只读；核原停止态起点和零待执行SQL。
3. 写入前记录experience-preflight PASS。用相同参数、全新output，加`--apply --confirm PROD`。命令只读读取发布状态，不写SQLite；以独立维护操作记录并使用既有远端journal/公共锁，原Spug失败保持。
4. 正常Spug新包promote-prod重新核纠正原件/审计及全部身份，以docker cp读取停止容器的真实版本，不启动旧应用。新包技术部署成功后仅追加原失败的前向替代关联；业务开放仍必须单独验收。

必须记录：新提交/tag/manifest和包摘要、原JOB/OP/起点、工作区路径、精确5条范围与计划SHA、原件路径、只读与写入结果、全量快照报告、正式部署/技术/页面/开放证据和最终收尾。Fail Fast保留原件；本合同不提供自动回退、数据恢复或未知结果重试。

构建保存设置门禁：当gxpConfigurationSourceUrl仍指向正式服且maintenanceUnknown=true时，只接受上述唯一原失败和真实停止态身份。构建以SHOW TABLES/DESCRIBE核真实结构，只读infra_config中唯一可见的system.gxp.audit-mode，并与原失败包保存设置一致；证据必须标明未认证、未验证运行模式。正常来源继续真实UI登录。缺原起点、配置漂移或多条配置立即阻断，不改用其他环境、不启动旧应用。运行态技术验收仍须真实登录并核实际模式。推荐先运行test_stopped_source_mode与test_stopped_origin_recovery，再执行新构建；记录来源身份、保存值与原任务，不将保存值读回当作页面验收。
