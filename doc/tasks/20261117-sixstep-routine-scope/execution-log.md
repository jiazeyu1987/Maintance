# Execution log

BDD: Given 同库临时迁移过程创建、实际ROW事务与删除，When 校验整个日志范围，Then 通过并仅将ROW表计入affectedTables；跨库定义、CALL、动态执行拒绝，未闭合生命周期拒绝。

环境首次运行python -m pytest失败No module named pytest，未进入测试，不计业务RED。使用标准库unittest实现同一独立回归用例，仍需后续完整pytest回归环境。

尝试的原型仅通过两个简化测试，但真实6事件在DECLARE EXIT HANDLER处失败，且将过程名放入affectedTables违背下游表名合同。原型已精确恢复为此worktree HEAD版本，未提交、未安装；不得据简化GREEN宣称实现通过。

RED: python -X utf8 -m unittest -v scripts.tests.test_binlog_temporary_procedures -> exit1，正常生命周期在DROP PROCEDURE IF EXISTS处抛FORMAL_CAPTURE_BINLOG_QUERY_SCOPE_UNPROVEN；拒绝测试PASS。

Next: 过程定义需独立状态，不能成为表名；保持原始完整事件回放、禁止CALL，考虑跨日志段的生命周期。过程体含嵌套BEGIN/END、IF及异常处理，禁止用宽正则跳过安全边界。需真实MySQL回放及原始全段严格审计，不允许诊断跳过作为准入。

当前无生产代码改动；仅保留测试和任务文档。工作区C:/SpugHandoff/release/routine-scope-dev-20261117，基线86f37989，无新提交，未合并/删除。

BDD/RED/GREEN: 新增未闭合过程、嵌套handler、游标LOOP及精确affectedTables断言；RED原实现3失败，LOOP扩展先单独RED后GREEN。候选将过程状态独立存储，不加入affectedTables；实际6原事件本地全部通过且affectedTables为空。既有私密test-dependencies运行pytest相关82项PASS，无需安装组件。候选全段只读审计session95392仍运行；无安装、无重提。仍需处理跨segment生命周期、复制recovery模块、真实MySQL回放、封包及更全面负向边界验证。

GREEN（仅候选，只读）: 真实全段审计完成PASS/diagnosticCount0，binlog.000033 121470445至137925229，16454784字节，07:34:59至07:36:28Z；使用内存加载开发候选，服务器磁盘模块未修改，输出installedModulePin仍指旧安装，不能当新安装PASS。原始proof保存在sixstep-20261117/binlog-scope-candidate.private.json。真实恢复/封包验证仍未完成。

BDD/RED/GREEN: 真实格式跨2个日志段创建/删除过程测试先因ROUTINE_INCOMPLETE失败，改为跨段共享过程状态、每段仍核事务闭合、全范围最终核过程清空，83相关测试PASS。两套formal_binlog_scope已同步。GREEN: experience-preflight -> PASS，下一步仅本机隔离mysql:8.0.39容器（无端口、无业务挂载）实际导出与回放，不触及现有数据库。测试结束仅清理本任务精确容器。

跨日志段生命周期RED -> GREEN完成，相关83项PASS；recovery同名模块同步。封包回归Windows实际3FAIL/32PASS/2SKIP：两个NATIVE_LINUX_REQUIRED、一个已有recovery_prepared_storage基线差异，不能判PASS，须Linux及基线核验。本机隔离MySQL第一次60秒启动未就绪，任务容器已精确删除（未触及业务）；第二次session32059运行中，日志显示InnoDB初始化结束，无就绪回执，仍需真实回放。

封包回归调查：漏列模块追溯到既有提交08bebb3，补测试allowed中的recovery_prepared_storage；Linux Docker回归85PASS/35ERROR，错误为Windows worktree的.git绝对路径无法在容器解析，非业务通过。真实MySQL载体误将官方entrypoint临时初始化数据库视为就绪，出现初始化跨库事件/导出失败；已保留失败，不能据此放宽范围。当前诊断重跑session85609及精确容器sixstep-routine-replay-20261117存活；后续必须等待PID1为mysqld且正式端口就绪再取binlog起点，避免继续重复初始化轮次。所有失败容器由载体精确清理。尚无生产安装。

Linux回归最终GREEN: 使用既有linux-test-wheels离线安装到任务容器、Git_DIR/COMMON_DIR只读映射，120 passed/0skip，16.69秒，任务容器自动删除。在线依赖尝试TLS失败，废弃容器已精确删除。MySQL正式PID1门禁修正后范围审计已执行通过，但mysql:8.0.39无mysqlbinlog；只读从已登记57导出工具读取二进制，SHA8b1ed50f...完全匹配（7516496字节），依赖核验后放入本机任务容器。真实回放session93835仍运行；未安装生产修复、未重提备份。

GREEN: 实际MySQL8.0.39 + 登记mysqlbinlog8.0.39回放PASS，11事件/1ROW/3DDL，affectedTables仅roles，SQL5575字节完整导出重放，值0->1，过程最终0，任务容器已清理；证据sixstep-20261117/routine-mysql-replay.private.json。相关Linux120PASS。当前实现可以提交；安装与实际本轮备份恢复尚未完成。
