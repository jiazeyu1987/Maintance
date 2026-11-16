# 执行记录

- BDD: 后端启动后正常事务 -> Given恢复数据完成且后端启动，When出现一活跃事务，Then仍核UUID/模式/调度器/库范围并继续。
- RED: Python标准库unittest scripts/tests/test_restore_application_database_phase.py -> 4测试中1失败，实际SAFE封包bound抛FORMAL_SQL_DATABASE_CHANGED；其余停写事务拒绝、身份/模式/范围拒绝、导入事务允许通过。
- 环境：bundled Python没有pytest，使用标准库unittest，不安装依赖。实际封包生成函数读取冻结基线并应用正式transforms；测试抽取实际数据库阶段执行代码，不把局部测试当作真实恢复验收。
- 实现：仅SAFE运行时bound在running_applications非空时使用允许事务的既有身份/模式校验，并保留数据库范围校验；停写/导入阶段原行为保持。
- GREEN: 同一unittest命令 -> 4/4 PASS；git diff --check -> PASS。
- REGRESSION NOT RUN：尝试用unittest加载既有test_main_mysql_scheduler.py，其导入依赖pytest，本机bundled Python缺pytest；该错误为验证环境缺依赖，不能记回归通过。后续采用已有可用测试运行环境完成相关回归后再提交及安装，不安装新服务器组件。
- 验证环境补齐：仅任务本地test-venv安装pytest/jsonschema；本地Docker容器/tmp/restore-start-contract-20261117-deps为隔离测试依赖，未改服务器组件和Spug服务依赖。
- REGRESSION：test_restore_application_database_phase、test_main_mysql_scheduler、test_prepared_service_health、test_prepared_database_readback -> 33 PASS、4 subtests PASS。
- 宽回归第一次Windows main_readiness组包含1项CRLF解析失败；本次未改该模块或测试。Linux复制源码验证该明确用例PASS。Linux全组另有两项因Python3.9无sys.exception与测试副本没有Git元数据而失败；不把该轮写为全组通过。
- 最终分环境覆盖：Windows main_readiness -k 'not test_host_frontend_uses_explicit_bound_original_listen' -> 21 PASS、10 subtests PASS；明确排除项在Linux原用例 -> 1 PASS。全部22项均获得真实执行通过，非静默跳过；实际封包生成测试在Windows通过。部署验收仍未完成。
