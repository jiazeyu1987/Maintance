# r15 后恢复核验

## Bug / Expected

日常 without-data 发布必须在 Windows PowerShell 5.1 中清理本任务的长路径构建上下文；不应误删同级文件。被排除出空结构演练的待应用迁移必须有实际只读前置检查，不能只查询迁移账本或默认通过。

## Reproduction / Root Cause

- r11-r15 的失败发生在本机镜像导出后、manifest/NAS 封存前。r14/r15 移出的目录实际在 `LocalCacheRoot/publish-int-ruoyi`，各残留 763 个文件，最长路径 306 字符。PS5.1/.NET Framework 的普通路径递归删除稳定失败；PS7 手工验证不代表 PS5.1。
- 历史实现用源码字符串测试替代真实清理行为验证，导致重试、移动和成功判定等修改重复失败。新实现用 Windows extended-length 路径，精确限制目录身份并拒绝祖先重解析路径。
- `requiresTargetPreflight` 过去只控制空库演练的排除，没有对应实际数据检查；纯合同函数甚至把缺少执行结果当作成功。新构建门禁重算来源、SQL、账本和计划绑定，先验证整个检查集合，再用只读事务执行查询。
- 从已验证维护提交 8080c0d 恢复的只读 SQL 验证器另有注释/字符串解析和客户端命令缺口；独立审查指出后，统一词法扫描、拒绝反斜线客户端命令/可执行注释，并启用 mysql 非交互 binary-mode。相关反例均未连接服务器。

## RED / GREEN / Verification

- RED: 实际 PS5.1 清理测试，旧函数 5 FAIL / 3 PASS；包含真实超过 350 字符路径和越界目标。
- GREEN: 实际 PS5.1 清理测试 8 PASS；同级哨兵保留、文件占用明确报错、非法/目录穿越目标拒绝。新建 fixture 已清理。
- RED: 目标数据预检入口缺失及未执行结果误放行，9 FAIL；接线/可执行注释/锁函数负例再次得到 3 FAIL / 17 PASS；独立审查的客户端命令和注释解析负例亦得到预期 FAIL。
- GREEN: 新目标数据预检测试 25 PASS（加入构建必跑门禁后再做最终回归，见 execution-log.md）；所有结果都要求精确成功标记，空输出、额外行、摘要/计划篡改及写入语句不放行。
- Verification: 新 SSH 传输在已授权测试服仅执行 `SELECT @@session.transaction_read_only` 返回 1；binary-mode 启用后复验仍为 1。这不证明缺失的 58 条业务检查通过。
- Verification: r15 本地输入审计报告 `E:/Int/CacheData/IntRuoyi/one-button-app-release-20260912/r15-target-preflight-audit.json`，requiredCount=58、passedCount=0、sshStarted=false。未继续使用 r15 作为候选包。
- Reference: [MySQL 8.0 mysql 客户端选项](https://dev.mysql.com/doc/refman/8.0/en/mysql-command-options.html#option_mysql_binary-mode) 描述 binary-mode 在非交互输入下禁用客户端命令，charset/delimiter 仍须由合同拒绝。

## Risk / Blockers

- 58 个实际迁移前置检查文件仍缺失；已验证应用分支中的 16 个检查及 schema/menu 拆分需要选择性融合，不得覆盖当前新增迁移。
- 部署前重新检查、自包含验证器、NAS READY、真实页面验收、合并及收尾尚未验证。P1-P5 全任务不予放行。
- 独立审查反馈已落实到本轮回归；独立全任务复审仍待后续补齐检查后完成，不能把本轮局部 GREEN 写成任务完成。

## R72 Maven/Surefire Startup Guard

- Bug summary and expected behavior: 标准按钮发布在构建前运行后端 Maven 合同测试时，必须在 Windows 跨盘 worktree/Maven repository/surefire temp 组合下稳定进入测试并可终止；不得长期卡在 forked JVM 启动期，也不得跳过 Maven 门禁。
- Reproduction command or path: R72 `build-release` 卡在 `Invoke-StandardReleaseContractTests` 的 Maven 命令；`jcmd` 显示 surefire 子进程主线程停在 `ForkedBooter.lookupDecoderFactory`，dumpstream 提示 Boot Manifest-JAR 绝对 classpath 与 `other has different root`。
- Root cause: 发布脚本没有在 Maven 命令期间向 JDK 21 / Surefire forked JVM 注入 `-Djdk.net.URLClassPath.disableClassPathURLCheck=true`，C/D/E 跨盘路径组合触发 classpath URL 检查启动期阻塞。
- Regression test added: `scripts/tests/test_release_workflow_preflight.py::test_backend_contract_maven_uses_windows_surefire_classpath_guard`。
- RED command and expected failure: `python -X utf8 -m pytest -q scripts\tests\test_release_workflow_preflight.py::test_backend_contract_maven_uses_windows_surefire_classpath_guard --basetemp .tmp-r72-surefire-guard-red` -> FAIL，缺少 `Invoke-CheckedMavenCommand` 和 `JDK_JAVA_OPTIONS` guard。
- GREEN command and passing result: 同目标测试 -> PASS；相邻发布入口回归 `test_release_workflow_preflight.py test_release_target_data_preflight.py test_release_sql_preflight_gate.py test_release_package_governance.py` -> PASS，166 tests；PowerShell AST -> PASS；直接复跑发布脚本同款 Maven 合同命令 10 tests PASS，总耗时 6.468s。
- Risk and regression scope: 只改变发布脚本对 Maven 命令的临时环境，不修改业务代码、不弱化测试、不跳过后端合同；`finally` 恢复原 `JDK_JAVA_OPTIONS`，避免污染后续 node/docker/ssh 阶段。
- Blockers and follow-up actions: R72 半成品判废不复用；提交维护仓修复后使用 R73 重新 build-release，并以同一 tag 继续测试服 publish 验证。
